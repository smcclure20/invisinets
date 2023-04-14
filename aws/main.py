import boto3
import logging
from _api import *
from utils import *
from aws.vpc import *
from aws.subnet import *
from aws.endpoint import *
from aws.service import *
import transactions.actions
from typing import Optional, Union

ubuntu_20_ami_id = "ami-0f4feb99425e13b50"
key_name = "Main"
logger = logging.getLogger(__name__)


class InvisinetAWS(Invisinet):

    teardown: bool = False

    # TODO: Implement this
    dryrun: bool = False

    _ec2_resource = boto3.resource('ec2')
    _ec2_client = boto3.client('ec2')

    _elb_client = boto3.client('elbv2')

    _vpc: VPC

    def __init__(self, deployment_id: Optional[str] = None):
        super().__init__()
        if deployment_id is None:
            self._vpc = VPC.create()
        else:
            self._vpc = VPC.load(deployment_id)

    def __repr__(self):
        return f"invisinet aws deployment {self.deployment_id}"

    @property
    def deployment_id(self) -> str:
        return self._vpc.deployment_id

    @staticmethod
    def list_deployments() -> [TInvisinet]:
        return list(map(lambda x: VPC.load(x), VPC.list_deployment_ids()))

    @transactions.actions.ResourceAction.register()
    def request_eip(self, name: Optional[str] = None,
                    use_existing_vm_id: Optional[str] = None) -> EndpointIP:
        image = Instance.get_images([ubuntu_20_ami_id])[0]
        subnet = Subnet.create(f"invisinet-eip-subnet-{random_hex(5)}", self._vpc)

        name = name or f"invisinet-eip-{random_hex(5)}"

        key_pairs = self._ec2_client.describe_key_pairs()["KeyPairs"]
        key_pairs = list(
            filter(
                lambda k: k["KeyName"] == key_name,
                key_pairs
            )
        )
        if len(key_pairs) == 0:
            logger.info(f"Creating a new ed25519 key pair {key_name}...")
            self._ec2_client.create_key_pair(
                KeyName=key_name, DryRun=False, KeyType="ed25519")

        key = self._ec2_resource.KeyPair(key_name)

        instance_type = "t2.micro"
        ec2_instance = Instance.create(
            name=name,
            image=image,
            instance_type=instance_type,
            key_pair=key,
            subnet_id=subnet.subnet_id,
        )
        logger.info("Process finished.")

        if self.teardown:
            logger.info(f"Tearing down...")
            ec2_instance.terminate()
            logger.info("Done.")

        return ec2_instance

    def active_eip(self) -> [EndpointIP]:
        instances = self._ec2_client.describe_instances(
            Filters=[
                {
                    "Name": "tag:InvisinetsDeployment",
                    "Values": ["true"]
                }
            ]
        )["Reservations"]["Instances"]
        return [Instance.load(i["InstanceId"]) for i in instances]

    @transactions.actions.ResourceAction.register()
    def request_sip(self, name: Optional[str] = None) -> ServiceIP:
        subnet = Subnet.create(f"invisinet-sip-subnet-{random_hex(5)}", self._vpc)

        lb_wrapper = LoadBalancer()
        name = name or f"invisinet-sip-{random_hex(5)}"
        arn = lb_wrapper.create(name, subnet=subnet,
                                vpc=self._vpc)
        logger.info("Process finished.")
        return lb_wrapper

    def active_sip(self) -> [ServiceIP]:
        instances = self._elb_client.client.describe_load_balancers(
            Filters=[
                {
                    "Name": "tag:InvisinetsDeployment",
                    "Value": ["true"]
                }
            ]
        )["LoadBalancers"]
        return [LoadBalancer(i["LoadBalancerArn"]) for i in instances]

    @transactions.actions.Action.register(undo_callback=lambda: None)
    def bind(self, sip: ServiceIP, eip: EndpointIP):
        target_group = self._elb_client.describe_target_groups(
            LoadBalancerArn=sip,
        )["TargetGroups"][0]["TargetGroupArn"]
        self._elb_client.register_targets(
            TargetGroupArn=target_group,
            Targets=[{
                    "Id": eip.endpoint_id,
            }]
        )
        logger.info("Process finished.")

    @transactions.actions.Action.register(undo_callback=lambda: None)
    def annotate(self,
                 endpoints: (EndpointIP, EndpointIP),
                 middlebox: Instance):

        subnet_wrappers = (
            Subnet(endpoints[0].subnet_id),
            Subnet(endpoints[1].subnet_id)
        )
        route_table = self._ec2_resource.RouteTable(subnet_wrappers[0].route_table_id)
        route_table.create_route(
            DestinationCidrBlock=subnet_wrappers[1].cidr,
            InstanceId=middlebox.endpoint_id
        )

        route_table = self._ec2_resource.RouteTable(subnet_wrappers[1].route_table_id)
        route_table.create_route(
            DestinationCidrBlock=subnet_wrappers[0].cidr,
            InstanceId=middlebox.endpoint_id
        )
        logger.info("Process finished.")

    def set_permit_list(self, sg_id, sg_permit_list):
        """
        Update the rules in the security group for the VM
        """
        logger.info(
            f"Updating security group rules for security group: {sg_id}")
        response = self._ec2_client.modify_security_group_rules(
            GroupId=sg_id,
            SecurityGroupRules=sg_permit_list,
            DryRun=False
        )
        logger.info(
            f"Successfully updated security group rules for security group: {sg_id}")

    def _describe_security_groups(self):
        """
        Helper function that returns the default security group
        """
        response = self._ec2_client.describe_security_groups(
            DryRun=False,
            GroupNames=[
                'default',
            ],
        )
        return response['SecurityGroups']

    def set_tag(self, load_balancer, tags_request):
        # First remove the existing tags
        describe_tags_response = self._ec2_client.describe_tags(
            LoadBalancerNames=[
                load_balancer,
            ],
        )
        tags = []
        if describe_tags_response:
            tags = describe_tags_response['TagDescriptions']['Tags']
        for tag in tags:
            response = self._ec2_client.remove_tags(
                LoadBalancerNames=[
                    load_balancer,
                ],
                Tags=[
                    {
                        'Key': tag,
                    },
                ]
            )
        logger.info(
            f"Successfully removed tags for load balancer: {load_balancer} "
            f"tags: {tags}"
        )
        # Add new tags
        for key, value in tags_request:
            response = self._ec2_client.add_tags(
                LoadBalancerNames=[
                    load_balancer,
                ],
                Tags=[
                    {
                        'Key': key,
                        'Value': value
                    },
                ]
            )
        logger.info(
            f"Successfully updated tags for load balancer: {load_balancer} "
            f"with tags: {tags_request}"
        )
