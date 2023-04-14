from _api import *
from azu.vnet import *
from azu.resource import *
import azure.mgmt.network.models
import azure.core.exceptions


TSubnet = TypeVar("TSubnet", bound="Subnet")
logger = logging.getLogger(__name__)
__all__ = ["Subnet", "TSubnet"]


class Subnet(AzureResourceMixin):

    subnet: Optional[azure.mgmt.network.models.Subnet] = None

    def __init__(self, subnet: azure.mgmt.network.models.Subnet):
        super().__init__()
        self.subnet = subnet

    @classmethod
    def load(cls: Type[TSubnet], name: str, vnet: VirtualNet) -> Optional[TSubnet]:
        try:
            subnet = cls.network_client.subnets.get(
                vnet.resource_group_name,
                vnet.name,
                name
            )
            return cls(subnet)
        except azure.core.exceptions.HttpResponseError:
            pass

        return None

    @classmethod
    def create(cls: Type[TSubnet], name: str, vnet: VirtualNet) -> TSubnet:
        cidr = vnet.next_available_subnet_cidr()

        logger.info(f"Creating an empty route table for the subnet...")
        route_table: azure.mgmt.network.models.RouteTable = cls.network_client.route_tables.begin_create_or_update(
            vnet.resource_group_name,
            f"{name}-route-table",
            {
                "location": cls.location,
                "routes": []
            }
        ).result()
        logger.info(f"Success. route_table_id: {route_table.id}")

        logger.info(f"Creating subnet {name} {cidr} for VirtualNet: {vnet.vnet_id}...")
        poller = cls.network_client.subnets.begin_create_or_update(
            vnet.resource_group_name,
            vnet.name,
            name,
            {
                "address_prefix": vnet.next_available_subnet_cidr(size=16),
                "route_table": {
                    "id": route_table.id
                }
            }
        )

        result = cls(poller.result())
        logger.info(f"Success. subnet_id: {result.subnet_id}")

        return result

    @property
    def cidr(self):
        return self.subnet.address_prefix

    @property
    def subnet_id(self):
        return self.subnet.id

    @property
    def name(self):
        return self.subnet.name

    @property
    def route_table_id(self):
        return self.subnet.route_table.id
