import boto3
import logging
import aws.subnet
from _api import *
from botocore.exceptions import ClientError
from typing import Type, TypeVar, Optional

logger = logging.getLogger(__name__)
TInstance = TypeVar("TInstance", bound="Instance")
__all__ = ["Instance", "TInstance"]


class Instance(EndpointIP):
    """Encapsulates Amazon Elastic Compute Cloud (Amazon EC2) instance actions."""

    _resource = boto3.resource('ec2')

    def __init__(self, instance):
        super().__init__()
        self.instance = instance

    @classmethod
    def from_resource(cls):
        ec2_resource = boto3.resource('ec2')
        return cls(ec2_resource)

    @classmethod
    def load(cls: Type[TInstance], instance_id: str) -> TInstance:
        instance = cls._resource.Instance(instance_id)
        instance.load()
        return cls(instance)

    @classmethod
    def create(cls: Type[TInstance], name, image, instance_type, key_pair,
               subnet_id, security_groups=None) -> TInstance:
        """
               Creates a new EC2 instance. The instance starts immediately after
               it is created.
               The instance is created in the default VPC of the current account.
        """
        logger.info(
            f"Creating a new {instance_type} instance using image {image.name}..."
        )

        instance_params = {
            "ImageId": image.id, "InstanceType": instance_type,
            "KeyName": key_pair.name, "SubnetId": subnet_id,
            "TagSpecifications": [{
                "ResourceType": "instance",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": name
                    },
                    {
                        "Key": "InvisinetsDeployment",
                        "Value": "true"
                    },
                ]
            }]
        }
        if security_groups is not None:
            instance_params['SecurityGroupIds'] = [sg.id for sg in security_groups]
        instance = cls._resource.create_instances(**instance_params, MinCount=1, MaxCount=1)[0]
        instance.wait_until_running()

        result = cls(instance)
        logger.info(f"Success. instance_id: {result.endpoint_id}")
        return result

    @classmethod
    def get_images(cls, image_ids):
        """
        Gets information about Amazon Machine Images (AMIs) from a list of AMI IDs.
        :param image_ids: The list of AMIs to look up.
        :return: A list of Boto3 Image objects that represent the requested AMIs.
        """
        try:
            images = list(cls._resource.images.filter(ImageIds=image_ids))
        except ClientError as err:
            logger.error(
                "Couldn't get images. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return images

    @property
    def name(self) -> str:
        assert self.instance is not None, "Endpoint not initialized"
        for tag in self.instance.tags:
            if tag["Key"] == "Name":
                return tag["Value"]
        raise ValueError("Couldn't find the instance name")

    @property
    def subnet_id(self) -> str:
        assert self.instance is not None, "Endpoint not initialized"
        return self.instance.subnet_id

    @property
    def endpoint_id(self):
        assert self.instance is not None, "Endpoint not initialized"
        return self.instance.id

    @property
    def public_ip(self) -> str:
        assert self.instance is not None, "Endpoint not initialized"
        return self.instance.public_ip_address

    def display(self, indent=1):
        """
        Displays information about an instance.
        :param indent: The visual indent to apply to the output.
        """
        assert self.instance is not None, "Endpoint not initialized"

        try:
            self.instance.load()
            ind = '\t'*indent
            print(f"{ind}ID: {self.instance.id}")
            print(f"{ind}Image ID: {self.instance.image_id}")
            print(f"{ind}Instance type: {self.instance.instance_type}")
            print(f"{ind}Key name: {self.instance.key_name}")
            print(f"{ind}VPC ID: {self.instance.vpc_id}")
            print(f"{ind}Public IP: {self.instance.public_ip_address}")
            print(f"{ind}State: {self.instance.state['Name']}")
        except ClientError as err:
            logger.error(
                "Couldn't display your instance. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

    def terminate(self):
        """
        Terminates an instance and waits for it to be in a terminated state.
        """
        assert self.instance is not None, "Endpoint not initialized"

        instance_id = self.instance.id
        try:
            self.instance.terminate()
            self.instance.wait_until_terminated()
            subnet = aws.subnet.Subnet(self.subnet_id)
            subnet.deallocate()

            self.instance = None
        except ClientError as err:
            logging.error(
                "Couldn't terminate instance %s. Here's why: %s: %s", instance_id,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

    def start(self):
        """
        Starts an instance and waits for it to be in a running state.
        :return: The response to the start request.
        """
        assert self.instance is not None, "Endpoint not initialized"

        try:
            response = self.instance.start()
            self.instance.wait_until_running()
        except ClientError as err:
            logger.error(
                "Couldn't start instance %s. Here's why: %s: %s", self.instance.id,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return response

    def stop(self):
        """
        Stops an instance and waits for it to be in a stopped state.
        :return: The response to the stop request.
        """
        assert self.instance is not None, "Endpoint not initialized"

        try:
            response = self.instance.stop()
            self.instance.wait_until_stopped()
        except ClientError as err:
            logger.error(
                "Couldn't stop instance %s. Here's why: %s: %s", self.instance.id,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return response

    def get_instance_types(self, architecture):
        """
        Gets instance types that support the specified architecture and are designated
        as either 'micro' or 'small'. When an instance is created, the instance type
        you specify must support the architecture of the AMI you use.
        :param architecture: The kind of architecture the instance types must support,
                             such as 'x86_64'.
        :return: A list of instance types that support the specified architecture
                 and are either 'micro' or 'small'.
        """
        try:
            inst_types = []
            it_paginator = self._resource.meta.client.get_paginator('describe_instance_types')
            for page in it_paginator.paginate(
                    Filters=[{
                        'Name': 'processor-info.supported-architecture', 'Values': [architecture]},
                        {'Name': 'instance-type', 'Values': ['*.micro', '*.small']}]):
                inst_types += page['InstanceTypes']
        except ClientError as err:
            logger.error(
                "Couldn't get instance types. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return inst_types
