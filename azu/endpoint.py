import string
import secrets
from _api import *
from azu.vnet import *
from azu.subnet import *
from azu.resource import *
from azure.mgmt.network.models import PublicIPAddress, NetworkInterface, NetworkInterfaceIPConfiguration
from azure.mgmt.compute.models import VirtualMachine, VirtualMachineSizeTypes

logger = logging.getLogger(__name__)
TInstance = TypeVar("TInstance", bound="Instance")
__all__ = ["Instance", "TInstance"]


class Instance(EndpointIP, AzureResourceMixin):

    instance: VirtualMachine
    resource_group_name: str

    def __init__(self, instance: VirtualMachine, resource_group_name: str):
        super().__init__()
        self.instance = instance
        self.resource_group_name = resource_group_name

    @classmethod
    def create(cls: Type[TInstance], name: str, vnet: VirtualNet,
               subnet_name: str) -> TInstance:
        public_ip = cls.new_public_ip(f"{name}-ip-address", vnet.resource_group_name)
        subnet = Subnet.load(subnet_name, vnet)
        private_ip = cls.private_ip_from_subnet(vnet.resource_group_name, vnet.name, subnet.subnet)

        ip_configuration = NetworkInterfaceIPConfiguration(
            name=f"{name}-ip-config",
            private_ip_allocation_method="Static",
            private_ip_address_version="IPv4",
            private_ip_address=private_ip,
            public_ip_address=public_ip,
            subnet=subnet.subnet,
            primary=True
        )
        network_interface = cls.network_client.network_interfaces.begin_create_or_update(
            vnet.resource_group_name,
            f"{name}-nic-primary",
            NetworkInterface(
                location=cls.location,
                ip_configurations=[ip_configuration],
            )
        ).result()

        alphabet = string.ascii_letters + string.digits
        username = "invisinet"
        password = ''.join(secrets.choice(alphabet) for i in range(16))

        logger.info(
            f"Creating a new instance using Ubuntu 16.04 LTS..."
        )
        logger.info(f"\t*username: {username}")
        logger.info(f"\t*password: {password}")

        poller = cls.compute_client.virtual_machines.begin_create_or_update(
            vnet.resource_group_name,
            name,
            {
                "location": cls.location,
                "storage_profile": {
                    "image_reference": {
                        "publisher": "Canonical",
                        "offer": "UbuntuServer",
                        "sku": "16.04.0-LTS",
                        "version": "latest",
                    }
                },
                "hardware_profile": {"vm_size": VirtualMachineSizeTypes.Standard_DS1_V2},
                "os_profile": {
                    "computer_name": name,
                    "admin_username": username,
                    "admin_password": password,
                },
                "network_profile": {
                    "network_interfaces": [
                        {
                            "id": network_interface.id,
                        }
                    ]
                },
            },
        )

        result = poller.result()
        logger.info(f"Success. instance_id: {result.id}")

        return cls(result, vnet.resource_group_name)

    @property
    def _primary_nic(self) -> NetworkInterface:
        nic_ids = [nic_ref.id for nic_ref in self.instance.network_profile.network_interfaces]
        for nic_id in nic_ids:
            name = nic_id.split("/")[-1]
            nic = self.network_client.network_interfaces.get(
                self.resource_group_name,
                name,
            )
            if nic.primary:
                return nic

        raise ValueError(f"No primary NIC found.")

    @property
    def name(self) -> str:
        return self.instance.name

    @property
    def subnet_id(self) -> str:
        primary_nic = self._primary_nic
        return primary_nic.ip_configurations[0].subnet.id

    @property
    def subnet_name(self) -> str:
        primary_nic = self._primary_nic
        return primary_nic.ip_configurations[0].subnet.name

    @property
    def endpoint_id(self) -> str:
        return self.instance.id

    @property
    def public_ip(self) -> str:
        primary_nic = self._primary_nic
        return primary_nic.ip_configurations[0].public_ip_address.ip_address

    @property
    def private_ip(self) -> str:
        primary_nic = self._primary_nic
        return primary_nic.ip_configurations[0].private_ip_address

    def terminate(self):
        logger.info(f"Deallocating instance {self.endpoint_id}...")
        poller = self.compute_client.virtual_machines.begin_deallocate(
            self.resource_group_name,
            self.name
        )
        poller.result()
        logger.info(f"Success.")
