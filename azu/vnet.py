from utils import *
from azu.resource import *
import azure.mgmt.network.models
from typing import Optional, Union, TypeVar, Type


TVirtualNet = TypeVar('TVirtualNet', bound='VirtualNet')
logger = logging.getLogger(__name__)
__all__ = ["VirtualNet"]


class VirtualNet(AzureResourceMixin):

    vnet: Optional[azure.mgmt.network.models.VirtualNetwork] = None
    
    def __init__(self, vnet: Optional[azure.mgmt.network.models.VirtualNetwork] = None):
        super().__init__()
        self.vnet = vnet

    @classmethod
    def load(cls: Type[TVirtualNet], deployment_id: str) -> Optional[TVirtualNet]:
        deployment_id = deployment_id.lower()

        resource_group_name = cls.resource_group_name_from_deployment_id(deployment_id)
        if cls.resource_client.resource_groups.check_existence(resource_group_name):
            vnet_name = cls.vnet_name_from_deployment_id(deployment_id)
            vnet = cls.network_client.virtual_networks.get(
                resource_group_name=resource_group_name,
                virtual_network_name=vnet_name,
            )
            return cls(vnet)

        return None

    @classmethod
    def create(cls: Type[TVirtualNet], deployment_id: Optional[str] = None) -> TVirtualNet:
        """
        Create a Virtual Network with the deployment id. A deployment id will be randomly
        generated if it's not specified.
        """
        if deployment_id is None:
            deployment_id = random_hex(5)
            while cls.load(deployment_id) is not None:
                deployment_id = random_hex(5)
        else:
            deployment_id = deployment_id.lower()
            if cls.load_vnet(deployment_id) is not None:
                raise ValueError(f"VirtualNet with deployment id {deployment_id} already exist")

        deployment_id = deployment_id.lower()
        vnet_name = cls.vnet_name_from_deployment_id(deployment_id)

        logger.info(f"Creating a new resource group {deployment_id} in {cls.location}")
        resource_group_name = cls.resource_group_name_from_deployment_id(deployment_id)
        cls.resource_client.resource_groups.create_or_update(resource_group_name, {
            "location": cls.location
        })

        vnet_cidr = "10.0.0.0/16"
        logger.info(f"Creating a new VirtualNet CIDR block: {vnet_cidr}...")
        poller = cls.network_client.virtual_networks.begin_create_or_update(
            resource_group_name,
            vnet_name,
            {
                "location": cls.location,
                "address_space": {"address_prefixes": [vnet_cidr]},
            },
        )

        result = cls(poller.result())
        logger.info(f"Success. vnet_id: {result.vnet_id}")

        return result

    def next_available_subnet_cidr(self, size: int = 16) -> str:
        subnets = self.network_client.subnets.list(
            self.resource_group_name,
            self.name
        )

        subnets_cidr = [
            subnet.address_prefix for subnet in subnets
        ]

        return next_available_cidr([self.cidr], subnets_cidr, size)

    def deallocate(self):
        pass  # TODO: Implement deallocate

    @property
    def vnet_id(self) -> str:
        return self.vnet.id

    @property
    def deployment_id(self) -> str:
        name: str = self.vnet.name
        return name.split("-")[-1]

    @property
    def cidr(self) -> str:
        return self.vnet.address_space.address_prefixes[0]

    @property
    def resource_group_name(self) -> str:
        return self.resource_group_name_from_deployment_id(self.deployment_id)

    @property
    def name(self):
        return self.vnet.name
