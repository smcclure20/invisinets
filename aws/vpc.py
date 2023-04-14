import boto3
import logging
from utils import *
from typing import Optional, TypeVar, Type

DEFAULT_VPC_CIDR_BLOCK = "10.10.0.0/16"
TVPC = TypeVar('TVPC', bound='VPC')
logger = logging.getLogger(__name__)
__all__ = ["VPC"]


class VPC:

    _resource = boto3.resource("ec2")
    _client = boto3.client("ec2")
    vpc = None

    def __init__(self, vpc):
        super().__init__()
        self.vpc = vpc

    @classmethod
    def load(cls: Type[TVPC], deployment_id: str) -> Optional[TVPC]:
        """
        Load the VPC with the specified deployment id
        """
        deployment_id = deployment_id.lower()

        vpcs = cls._client.describe_vpcs(
            Filters=[
                {
                    "Name": "tag:DeploymentID",
                    "Values": [deployment_id]
                }
            ]
        )["Vpcs"]

        if len(vpcs) > 0:
            vpc = cls._resource.Vpc(vpcs[0]["VpcId"])
            vpc.load()
            return cls(vpc)
        else:
            return None

    @classmethod
    def create(cls: Type[TVPC], deployment_id: Optional[str] = None) -> TVPC:
        """
        Create a VPC with the deployment id. A deployment id will be randomly
        generated if it's not specified.
        """
        if deployment_id is not None:
            deployment_id = deployment_id.lower()
            vpc = cls.load(deployment_id)
            if vpc is not None:
                raise ValueError(f"VPC with deployment id {deployment_id} already exist")
        else:
            deployment_id = random_hex(5)
            while cls.load(deployment_id) is not None:
                deployment_id = random_hex(5)

        name = f"invisinet-vpc-{deployment_id}"
        logger.info(f"Creating a new VPC named {name}...")
        response = cls._client.create_vpc(
            CidrBlock=DEFAULT_VPC_CIDR_BLOCK,
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": name
                        },
                        {
                            "Key": "DeploymentID",
                            "Value": deployment_id
                        },
                        {
                            "Key": "InvisinetsDeployment",
                            "Value": "true"
                        }
                    ]
                },
            ]
        )
        vpc = cls._resource.Vpc(response["Vpc"]["VpcId"])
        vpc.load()
        result = cls(vpc)

        logger.info(f"Success. Now attaching a gateway for the VPC...")
        gateway = cls._client.create_internet_gateway()
        cls._client.attach_internet_gateway(
            InternetGatewayId=gateway["InternetGateway"]["InternetGatewayId"],
            VpcId=result.vpc_id
        )
        return result

    @classmethod
    def list_deployment_ids(cls: Type[TVPC]) -> [str]:
        vpcs = cls._client.describe_vpcs()["Vpcs"]
        deployment_ids = []
        for vpc in vpcs:
            for tag in vpc["Tags"]:
                if tag["Key"] == "DeploymentID":
                    deployment_ids.append(tag["Value"].lower())
                    break

        return deployment_ids

    @property
    def cidr_block(self) -> str:
        assert self.vpc is not None, "VPC wrapper not initialized"
        return self.vpc.cidr_block

    @property
    def vpc_id(self):
        assert self.vpc is not None, "VPC wrapper not initialized"
        return self.vpc.vpc_id

    @property
    def deployment_id(self) -> str:
        assert self.vpc is not None, "VPC wrapper not initialized"
        for tag in self.vpc.tags:
            if tag["Key"] == "DeploymentID":
                return tag["Value"].lower()
        raise ValueError("This VPC was not initialized with a deployment ID")

    def next_available_subnet_cidr(self, size: int = 16) -> Optional[str]:
        subnets_cidr = [
            subnet["CidrBlock"]
            for subnet in self._client.describe_subnets(
                Filters=[
                    {
                        "Name": "vpc-id",
                        "Values": [self.vpc_id]
                    }
                ]
            )["Subnets"]
        ]

        return next_available_cidr([self.cidr_block], subnets_cidr, size)
