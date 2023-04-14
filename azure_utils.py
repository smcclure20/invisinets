import string
import random
from enum import Enum
from azure.mgmt.network.models import SecurityRule, AzureFirewall

DEFAULT_OFF_RULE_NAME="DENY_ALL"
VM_USERNAME="adminuser"
PW_LENGTH=10
LOCATION="westus2"


class Middlebox(Enum):
    FIREWALL = 1


def generate_vm_creds(vm_name, cred_file_path):
    letters = string.ascii_letters
    digits = string.digits
    punct = '!#$%&()*+,-./:;<=>?@[]^_{|}~'

    all_char_options = letters + digits + punct
    pw = ''.join(random.choice(all_char_options) for i in range(PW_LENGTH))

    creds = {"username": VM_USERNAME, "password": pw}
    cred_file = open(cred_file_path+vm_name, "w")
    cred_file.write(str(creds))
    cred_file.close()
    return creds


def set_security_rule_variable(rule, attribute_name, plural_attribute_name, value):
    """Sets value for appropriate security rule attribute depending on list length.
    Enables create_security_rules to not differentiate between a single port/prefix and a list
    """
    if len(value) == 1:
        rule.__setattr__(attribute_name, value[0])
    else:
        rule.__setattr__(plural_attribute_name, value)


# TODO: This can be simplified since one end's IP will be known
def create_security_rule(name, direction, protocol="*", source_ports=None, dest_ports=None,
                         source_addresses=None, dest_addresses=None, description=None):
    """Helper function to hide details of security rule constructor.
    :param name: name of the security rule
    :param direction: direction rule applies to ("Inbound" or "Outbound")
    :param protocol: rule protocol ("Tcp", "Udp", "Icmp", "Esp", "*", or "Ah")
    :param source_ports: list of source port ranges
    :param source_addresses: list of source prefixes
    :param dest_ports: list of destination port ranges
    :param dest_addresses: list of destination prefixes
    :param description: optional description for the rule
    """
    if source_ports is None: # or is empty list (TODO)
        source_ports = "*"
    if dest_ports is None:
        dest_ports = "*"
    if source_addresses is None:
        source_addresses = "*"
    if dest_addresses is None:
        dest_addresses = "*"

    rule = SecurityRule(name=name, direction=direction, protocol=protocol, description=description, access="Allow")

    set_security_rule_variable(rule, "source_port_range", "source_port_ranges", source_ports)
    set_security_rule_variable(rule, "destination_port_range", "destination_port_ranges", dest_ports)
    set_security_rule_variable(rule, "source_address_prefix", "source_address_prefixes", source_addresses)
    set_security_rule_variable(rule, "destination_address_prefix", "destination_address_prefixes", dest_addresses)

    return rule


def get_highest_rule_priority(rules):
    """Get the lowest available rule priority in a list of security rules."""
    highest = 99
    for rule in rules:
        if rule.priority > highest and not(rule.name.startswith(DEFAULT_OFF_RULE_NAME)):
            highest = rule.priority
    return highest


def get_resource_name_from_id(id):
    """Get the name of a resource from its ID."""
    return id.split("/")[-1]


def get_nic_name_from_ipconf_id(id):
    """Get the name of the NIC for a given IP configuration."""
    return id.split("/")[-3]


def select_primary(list):
    """Select the primary of a list of sdk objects (ex. IP configurations)."""
    for item in list:
        if item.primary or item.primary is None:
            return item
    return None


def wait_for_complete(poller, wait_increment=1):
    """Wait on SDK poller until response is back."""
    while not poller.done():
        poller.wait(wait_increment)
        print("Waiting...")


def increment_subnet(subnet):
    """Increments subnet address space"""
    tokens = subnet.split(".")
    tokens[2] = tokens[2] + 1
    return ".".join(tokens)