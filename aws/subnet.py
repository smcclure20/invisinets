import boto3
import logging
from aws.vpc import *
from typing import Optional, TypeVar, Type

TSubnet = TypeVar("TSubnet", bound="Subnet")
logger = logging.getLogger(__name__)
__all__ = ["Subnet", "TSubnet"]


class Subnet:

    _client = boto3.client("ec2")
    _resource = boto3.resource("ec2")

    def __init__(self, subnet):
        self.subnet = subnet

    @classmethod
    def load(cls: Type[TSubnet], subnet_id: str) -> Optional[TSubnet]:
        if subnet_id is not None:
            subnet = cls._resource.Subnet(subnet_id)
            # Verify that the subnet is valid
            subnet.load()
            return cls(subnet)
        else:

            return None

    @classmethod
    def create(cls: Type[TSubnet], name: str, vpc: VPC) -> TSubnet:
        cidr = vpc.next_available_subnet_cidr()
        logger.info(f"Creating subnet {name} {cidr} for VPC: {vpc.vpc_id}...")
        response = cls._client.create_subnet(
            VpcId=vpc.vpc_id,
            CidrBlock=cidr,
            TagSpecifications=[
                {
                    'ResourceType': 'subnet',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': name
                        },
                        {
                            "Key": "InvisinetsDeployment",
                            "Value": "true"
                        }
                    ]
                },
            ]
        )
        subnet = cls._resource.Subnet(response["Subnet"]["SubnetId"])
        subnet.load()
        result = cls(subnet)
        logger.info(f"Success. subnet_id: {result.subnet_id}.")

        route_table = vpc.vpc.create_route_table()
        route_table.associate_with_subnet(SubnetId=result.subnet_id)
        subnet.create_tags(
            Tags=[
                {
                    "Key": "AssociatedRouteTableID",
                    "Value": route_table.id
                }
            ]
        )
        result.subnet.load()
        return result

    def deallocate(self):
        logger.info(f"Subnet {self.subnet_id} deleted.")
        self.subnet.delete()
        self.subnet = None

    @property
    def cidr(self):
        return self.subnet.cidr_block

    @property
    def subnet_id(self):
        return self.subnet.subnet_id

    @property
    def route_table_id(self):
        return self.subnet.tags["AssociatedRouteTableID"]
