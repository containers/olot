import ipaddress
import re

_host_re = re.compile(r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$")

# OCI reference validation patterns

# Repository component: lowercase alphanumerics with separators (., -, _, __)
# Note: __ (double underscore) must be checked before _ (single underscore) in alternation
# ref: [a-z0-9]+((\.|_|__|-+)[a-z0-9]+)*(\/[a-z0-9]+((\.|_|__|-+)[a-z0-9]+)*)*
_repository_re = re.compile(r'^[a-z0-9]+((__|[._-])[a-z0-9]+)*(/[a-z0-9]+((__|[._-])[a-z0-9]+)*)*$')

# Tag pattern: max 128 chars, starts with alphanumeric or underscore
_tag_re = re.compile(r'^[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}$')

# Digest pattern: algorithm:encoded (e.g., sha256:abc123...)
_digest_re = re.compile(r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$')

def is_valid_registry_host_port(registry_host: str) -> bool:
    """Validate a registry host with optional port.

    Intended to validate a registry, for example as "quay.io" or "quay.my.svc.cluster.local:5000" or "localhost:5000".
    Supports IPv4, IPv6 (plain or bracketed), and hostnames, with optional port numbers.
    Port must be in range 1-65535.
    Hostnames follow RFC 1035 (max 255 chars, labels max 63 chars).

    Args:
        registry_host: Host string (e.g., "localhost:5000", "[::1]:8080", "registry.io")

    Returns:
        True if valid, False otherwise
    """
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
    elif ":" in registry_host:  # Could be a plain IPv6 (e.g.: "::1") or host:port (e.g.: "localhost:5000")
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

    # important: check max length first to avoid regex induced issues
    if len(host) > 255:
        return False

    for label in host.split("."):  # RFC 1035 "label" max 63 chars; a label is chunk between dots
        if len(label) > 63:
            return False

    return bool(_host_re.match(host))


def is_valid_oci_reference(reference: str) -> bool:
    """Validate an OCI image reference.

    Supports formats:
    - repository[:tag|@digest]
    - registry/repository[:tag|@digest]
    - registry:port/repository[:tag|@digest]

    Examples:
    - mycontainer:tag
    - myorg/mycontainer:tag
    - registry.com/myorg/mycontainer:tag
    - mycontainer@sha256:abc123...
    - registry.com:5000/myorg/mycontainer@sha256:abc123...

    Missing registry would default to docker.io or similar, and missing tag defaults to :latest.
    Both are considered valid per OCI spec.

    Note: using tag+digest might be as well be valid in some implementations.
    The intent of this function is to validate oci_reference by the spec.
    That is:
    > <reference> MUST be either (a) the digest of the manifest or (b) a tag. The <reference> MUST NOT be in any other format

    Args:
        reference: OCI image reference string to validate

    Returns:
        True if the reference is valid, False otherwise
    """
    if not reference or not isinstance(reference, str):
        return False

    # Extract digest if present (split on last @)
    digest = None
    if '@' in reference:
        parts = reference.rsplit('@', 1)
        if len(parts) != 2 or not parts[1]:  # Empty digest
            return False
        reference, digest = parts

    # Extract tag if present (and no digest)
    tag = None
    if digest is None and ':' in reference:
        # Split from right to check if it could be a tag
        parts = reference.rsplit(':', 1)
        if len(parts) == 2:
            potential_tag = parts[1]
            # If it contains /, it's part of the path, not a tag
            # If it's empty, invalid
            if not potential_tag:
                return False
            if '/' not in potential_tag:
                # Could be a tag or a port number
                # If there's no / in potential_tag and it's a valid tag, it must be a tag
                # (registry:port MUST be followed by /repository)
                if _tag_re.match(potential_tag):
                    reference, tag = parts

    # Separate registry from repository
    # Registry is present if first component has '.', ':', or is 'localhost'
    registry = None
    repository = reference

    if '/' in reference:
        first_component, rest = reference.split('/', 1)
        # Check if first component looks like a registry
        if '.' in first_component or ':' in first_component or first_component == 'localhost':
            registry = first_component
            repository = rest

    # Validate registry if present
    if registry is not None:
        if not is_valid_registry_host_port(registry):
            return False

    # Validate repository (required)
    if not repository:
        return False

    # Check length before regex
    if len(repository) > 255:
        return False

    if not _repository_re.match(repository):
        return False

    # Validate tag if present
    if tag is not None:
        if not _tag_re.match(tag):
            return False

    # Validate digest if present
    if digest is not None:
        if not _digest_re.match(digest):
            return False

    return True
