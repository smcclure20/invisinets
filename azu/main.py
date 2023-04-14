import os

import _api
from _api import *
from utils import *
from azu.vnet import *
from azu.subnet import *
from azu.service import *
from azu.endpoint import *
from azu.resource import *
import azure.mgmt.network.models
from typing import Optional, Union

logger = logging.getLogger(__name__)


class InvisinetAzure(_api.Invisinet, AzureResourceMixin):

    teardown: bool = False

    _vnet: VirtualNet

    def __init__(self, deployment_id: str = None):
        super().__init__()
        if deployment_id is None:
            self._vnet = VirtualNet.create()
        else:
            self._vnet = VirtualNet.load(deployment_id)
    
    def __repr__(self):
        return f"invisinet azure deployment {self.deployment_id}"
    
    @property
    def deployment_id(self) -> str:
        return self._vnet.deployment_id

    def list_deployments(self) -> [TInvisinet]:
        return []

    def request_eip(self, name: Optional[str] = None,
                    use_existing_vm_id: Optional[str] = None) -> EndpointIP:
        name = name or f"invisinet-eip-{random_hex(5)}"
        subnet = Subnet.create(f"{name}-subnet", self._vnet)
        instance = Instance.create(
            name,
            self._vnet,
            subnet.name
        )
        return instance

    def active_eip(self) -> [EndpointIP]:
        return []

    def request_sip(self, name: Optional[str] = None) -> ServiceIP:
        name = name or f"invisinet-sip-{random_hex(5)}"
        subnet = Subnet.create(f"{name}-subnet", self._vnet)
        instance = LoadBalancer.create(
            name,
            self._vnet,
            subnet.name
        )

        return instance

    def active_sip(self) -> [Instance]:
        return []

    def bind(self, sip: ServiceIP, eip: EndpointIP):
        logger.info(f"Retrieving backend pool for sip {sip.name}...")
        backend_pool = self.network_client.load_balancer_backend_address_pools.get(
            resource_group_name=self._vnet.resource_group_name,
            load_balancer_name=sip.name,
            backend_address_pool_name=f"{sip.name}-backend-pool"
        )

        logger.info(f"Updating backend address...")
        backend_pool.load_balancer_backend_addresses.append(
            azure.mgmt.network.models.LoadBalancerBackendAddress(
                name=f"{sip.name}-{eip.name}-backend-address",
                virtual_network=self._vnet.vnet,
                ip_address=eip.private_ip,
            )
        )

        self.network_client.load_balancer_backend_address_pools.begin_create_or_update(
            resource_group_name=self._vnet.resource_group_name,
            load_balancer_name=sip.name,
            backend_address_pool_name=backend_pool.name,
            parameters=backend_pool
        )
        logger.info(f"Process finished. IP {eip.private_ip} added to the backend.")

    def annotate(self,
                 endpoints: (EndpointIP, EndpointIP),
                 middlebox: EndpointIP):
        subnets = (
            Subnet.load(endpoints[0].subnet_name, self._vnet),
            Subnet.load(endpoints[1].subnet_name, self._vnet)
        )
        route_tables = [
            azure.mgmt.network.models.RouteTable(id=subnets[0].route_table_id),
            azure.mgmt.network.models.RouteTable(id=subnets[1].route_table_id)
        ]

        route1_params = {
            "address_prefix": subnets[1].cidr,
            "next_hop_type": "VirtualAppliance",
            "next_hop_ip_address": middlebox.private_ip
        }
        route2_params = {
            "address_prefix": subnets[0].cidr,
            "next_hop_type": "VirtualAppliance",
            "next_hop_ip_address": middlebox.private_ip
        }

        logger.info(f"Creating routes for the middleware...")

        self.network_client.routes.begin_create_or_update(
            self._vnet.resource_group_name,
            route_tables[0].name,
            f"{subnets[0].name}-{middlebox.name}-middlebox-route",
            route1_params
        ).result()

        self.network_client.routes.begin_create_or_update(
            self._vnet.resource_group_name,
            route_tables[1].name,
            f"{subnets[1].name}-{middlebox.name}-middlebox-route",
            route2_params
        ).result()

        logger.info("Process finished.")
    
    # def set_permit_list(self, eip_name: str, permit_list: any):
    #     credential = AzureCliCredential()
    #     subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    #     resource_client = ResourceManagementClient(credential, subscription_id)
    #     network_client = NetworkManagementClient(credential, subscription_id)
    #
    #     eip = network_client.public_ip_addresses.get(RESOURCE_GROUP, eip_name)
    #     nic_name = get_nic_name_from_ipconf_id(eip.ip_configuration.id)
    #     nic = network_client.network_interfaces.get(RESOURCE_GROUP, nic_name)
    #
    #     nsg = network_client.network_security_groups.get(RESOURCE_GROUP, get_resource_name_from_id(nic.network_security_group.id))
    #
    #     poller = client.network_security_groups.begin_create_or_update(
    #         resource_group_name=RESOURCE_GROUP_NAME,
    #         network_security_group_name=nsg,
    #         parameters=permit_list,
    #     )
    #     print("Updated rules on NSG {}".format(nsg.name))


if __name__ == '__main__':
    deployment = InvisinetAzure()
    sip = deployment.request_sip()
    eip = deployment.request_eip()
    deployment.bind(sip, eip)
