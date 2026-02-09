import ipaddress
import re

_host_re = re.compile(r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$")

def is_valid_registry_host_port(registry_host: str) -> bool:
    host = registry_host

    if registry_host.startswith("["):  # IPv6 bracket notation: [ipv6] or [ipv6]:port
        bracket_end = registry_host.find("]")
        if bracket_end == -1:
            return False
        host = registry_host[1:bracket_end]  # host is what's inside [brakets]
        if len(registry_host) > bracket_end + 1:  # let's check what's after the [] brakets
            if registry_host[bracket_end + 1] != ":":
                return False
            port = registry_host[bracket_end + 2:]
            if not port.isdigit() or not (0 < int(port) < 65536):
                return False
    elif ":" in registry_host:  # Could be plain IPv6 or host:port
        try:
            ipaddress.ip_address(registry_host)
            return True
        except ValueError:
            pass
        host, port = registry_host.rsplit(":", 1)
        if not port.isdigit() or not (0 < int(port) < 65536):
            return False

    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass

    if len(host) > 255:
        return False

    for label in host.split("."):  # RFC 1035 "label" max 63 chars; a label is chunk between dots
        if len(label) > 63:
            return False

    return bool(_host_re.match(host))
