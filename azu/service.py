from _api import *
from azu.vnet import *
from azu.subnet import *
from azu.resource import *
from typing import TypeVar, Type, Optional
from azure.mgmt.network.models import LoadBalancer as AzureLoadBalancer
from azure.mgmt.network.models import LoadBalancerSku, FrontendIPConfiguration, \
    BackendAddressPool, Probe, LoadBalancingRule

TLoadBalancer = TypeVar("TLoadBalancer", bound="LoadBalancer")
logger = logging.getLogger(__name__)
__all__ = ["TLoadBalancer", "LoadBalancer"]


class LoadBalancer(ServiceIP, AzureResourceMixin):

    instance: AzureLoadBalancer
    resource_group: str

    def __init__(self, instance: AzureLoadBalancer):
        super().__init__()
        self.instance = instance

    @classmethod
    def create(cls: Type[TLoadBalancer], name: str, vnet: VirtualNet,
               subnet_name: str) -> TLoadBalancer:

        logger.info(f"Creating a new load balancer {name}...")
        subnet = Subnet.load(subnet_name, vnet)
        private_ip = cls.private_ip_from_subnet(vnet.resource_group_name, vnet.name, subnet.subnet)
        private_frontend_ip_config = FrontendIPConfiguration(
            name=f"{name}-private-frontend-ip-config",
            subnet=subnet.subnet,
            private_ip_address=private_ip,
            public_ip_address=None,
        )

        logger.info(f"Creating an empty backend pool...")
        backend_pool_name = f"{name}-backend-pool"
        backend_pool = BackendAddressPool(
            name=backend_pool_name,
            load_balancer_backend_addresses=[],
        )

        health_probe = Probe(
            name=f"{name}-health-probe",
            protocol="Http",
            request_path="/",
            port=80,
            interval_in_seconds=5,
            number_of_probes=2
        )

        load_balancing_rule = LoadBalancingRule(
            name="load_balancing_rule",
            frontend_ip_configuration=private_frontend_ip_config,
            backend_address_pool=backend_pool,
            probe=health_probe,
            protocol="Tcp",
            load_distribution="Default",
            frontend_port=0,
            backend_port=0,
            idle_timeout_in_minutes=4,
            enable_floating_ip=False
        )

        poller = cls.network_client.load_balancers.begin_create_or_update(
            resource_group_name=vnet.resource_group_name,
            load_balancer_name=name,
            parameters=AzureLoadBalancer(
                location=cls.location,
                sku=LoadBalancerSku(
                    name="Standard",
                    tier="Regional"
                ),
                frontend_ip_configurations=[private_frontend_ip_config],
                backend_address_pools=[backend_pool],
                probes=[health_probe],
                load_balancing_rule=[load_balancing_rule],
            )
        )

        result = poller.result()

        cls.network_client.load_balancer_backend_address_pools.begin_create_or_update(
            resource_group_name=vnet.resource_group_name,
            load_balancer_name=name,
            backend_address_pool_name=backend_pool_name,
            parameters=backend_pool
        )

        logger.info(f"Success. instance_id: {result.id}")

        return cls(result)

    @property
    def name(self) -> str:
        return self.instance.name

    @property
    def subnet_id(self) -> str:
        return self.instance.frontend_ip_configurations[0].subnet.id

    @property
    def subnet_name(self) -> str:
        return self.instance.frontend_ip_configurations[0].subnet.name

    @property
    def endpoint_id(self) -> str:
        return self.instance.id

    def terminate(self):
        pass  # TODO: Implement this
