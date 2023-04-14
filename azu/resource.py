import logging
import netaddr
from definitions import *
import azure.mgmt.network.models
from typing import ClassVar, Optional
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient

logger = logging.getLogger(__name__)
credential = AzureCliCredential()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]


class AzureResourceMixin:

    resource_client = ResourceManagementClient(credential, subscription_id)
    compute_client = ComputeManagementClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    location: ClassVar[str] = "westus3"

    @staticmethod
    def vnet_name_from_deployment_id(deployment_id: str) -> str:
        return f"invisinet-vnet-{deployment_id}"

    @staticmethod
    def resource_group_name_from_deployment_id(deployment_id: str) -> str:
        return f"invisinet-deployment-{deployment_id}"

    @classmethod
    def new_public_ip(cls, name: str, resource_group_name: str) \
            -> azure.mgmt.network.models.PublicIPAddress:
        logger.info(f"Creating a new public ip...")
        public_ip = cls.network_client.public_ip_addresses.begin_create_or_update(
            resource_group_name=resource_group_name,
            public_ip_address_name=name,
            parameters={
                "location": cls.location,
                "sku": {"name": "Basic"},
                "public_ip_allocation_method": "Dynamic",
                "public_ip_address_version": "IPv4",
            }
        ).result()
        return public_ip

    @classmethod
    def private_ip_from_subnet(cls, resource_group_name: str, vnet_name: str,
                               subnet: azure.mgmt.network.models.Subnet) -> Optional[str]:
        private_ip = subnet.address_prefix.split("/")[0]
        options = cls.network_client.virtual_networks.check_ip_address_availability(
            resource_group_name,
            vnet_name,
            private_ip
        )
        if not options.available:
            private_ip = options.available_ip_addresses[0]

        if netaddr.IPAddress(private_ip) in netaddr.IPNetwork(subnet.address_prefix):
            return private_ip
        else:
            return None
