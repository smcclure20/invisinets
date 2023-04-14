import uuid
import boto3
import logging
import aws.vpc
import aws.subnet
from _api import *

TLoadBalancer = TypeVar("TLoadBalancer", bound="LoadBalancer")
logger = logging.getLogger(__name__)
__all__ = ["LoadBalancer", "TLoadBalancer"]


class LoadBalancer(ServiceIP):
    
    _elb_client = boto3.client('elbv2')
    
    def __init__(self, arn: str) -> None:
        super().__init__()
        self.arn = arn

    @classmethod
    def load(cls: Type[TLoadBalancer], arn: str) -> TLoadBalancer:
        return cls(arn)

    @classmethod
    def create(cls: Type[TLoadBalancer], name: str, subnet: aws.subnet.Subnet,
               vpc: aws.vpc.VPC, port: int = 80) -> TLoadBalancer:
        """
        Create an internet-facing load balancer. Return the load balancer ARN.
        """

        if port < 0 or port > 65535:
            raise ValueError(f"Port number {port} is out of range")
        
        logger.info("Creating network load balancer...")
        response = cls._elb_client.create_load_balancer(
            Name=name,
            Subnets=[subnet.subnet_id],
            Scheme="internet-facing",
            Type="network",
            Tags=[
                {
                    "Key": "Name",
                    "Value": name
                },
                {
                    "Key": "SubnetID",
                    "Value": subnet.subnet_id
                },
                {
                    "Key": "InvisinetsDeployment",
                    "Value": "true"
                },
            ],
        )
        arn = response["LoadBalancers"][0]["LoadBalancerArn"]
        
        target_group_name = uuid.uuid4().hex
        logger.info(f"Creating target group {target_group_name}...")
        target_group = cls._elb_client.create_target_group(
            Name=target_group_name,
            Protocol="TCP",
            Port=port,
            VpcId=vpc.vpc_id,
            TargetType="instance"
        )
        
        logger.info("Assigning target group to listener...")
        cls._elb_client.create_listener(
            LoadBalancerArn=arn,
            Protocol="TCP",
            Port=port,
            DefaultActions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group["TargetGroups"]
                    [0]["TargetGroupArn"]
                }
            ]
        )
        logger.info("Success.")

        return cls(arn)

    @property
    def name(self) -> str:
        assert self.arn is not None, "Load balancer not initialized."

        response = self._elb_client.describe_tags(
            ResourceArns=[self.arn]
        )
        response = list(filter(
            lambda entry: entry["Key"] == "Name",
            response["TagDescriptions"][0]["Tags"]
        ))
        return response[0]["Value"]

    @property
    def subnet_id(self):
        assert self.arn is not None, "Load balancer not initialized."

        response = self._elb_client.describe_tags(
            ResourceArns=[self.arn]
        )
        response = list(filter(
            lambda entry: entry["Key"] == "SubnetID",
            response["TagDescriptions"][0]["Tags"]
        ))
        return response[0]["Value"]

    @property
    def endpoint_id(self) -> str:
        assert self.arn is not None, "Load balancer not initialized."

        return self.arn

    @property
    def target_group_arn(self) -> [str]:
        assert self.arn is not None, "Load balancer not initialized."

        response = self._elb_client.describe_target_groups(
            LoadBalancerArn=self.arn,
        )["TargetGroups"]
        return list(map(lambda elem: elem["TargetGroupArn"], response))

    @property
    def listener_arn(self) -> [str]:
        assert self.arn is not None, "Load balancer not initialized."

        response = self._elb_client.describe_listeners(
            LoadBalancerArn=self.arn,
        )["Listeners"]
        return list(map(lambda elem: elem["ListenerArn"], response))

    def terminate(self):
        assert self.arn is not None, "Load balancer not initialized."

        logger.info(f"Deleting listeners...")
        for listener in self.listener_arn:
            self._elb_client.delete_listener(
                ListenerArn=listener
            )
            logger.info(f"Listener {listener} deleted.")

        for target_group in self.target_group_arn:
            self._elb_client.delete_target_group(
                TargetGroupArn=target_group
            )
            logger.info(f"Target group {target_group} deleted.")

        self._elb_client.delete_load_balancer(
            LoadBalancerArn=self.arn
        )
        logger.info(f"Load balancer {self.arn} deleted.")

        subnet = aws.subnet.Subnet(self.subnet_id)
        subnet.deallocate()

        self.arn = None
