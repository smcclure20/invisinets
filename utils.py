import math
import string
import random
import netaddr
from typing import Optional


def random_hex(n):
    result = ''.join(random.choice(string.hexdigits) for _ in range(n))
    return result.lower()


def next_available_cidr(available: [str], used: [str], size: int = 16) -> Optional[str]:
    available_ip_set = netaddr.IPSet(available) - netaddr.IPSet(used)
    prefix = 32 - math.ceil(math.log2(size))
    for block in available_ip_set.iter_cidrs():
        if block.prefixlen <= prefix:
            return str(next(block.subnet(prefix, 1)))

    return None
