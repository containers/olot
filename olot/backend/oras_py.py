import os
import typing


def is_oras_py() -> bool:
    """Check if the oras Python library is available."""
    try:
        import oras  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_hostname(reference: str) -> str:
    """Extract the registry hostname from an OCI image reference.
    """
    ref = reference.split("@")[0]
    if "/" not in ref:
        # Bare image name (e.g. "busybox:latest") implies docker.io
        return "docker.io"
    first_component = ref.split("/")[0]
    if "." in first_component or first_component.startswith("localhost"):
        return first_component
    return "docker.io"


def _setup_auth(registry: "typing.Any", reference: str) -> None:
    """Load authentication configs for the registry hostname in the reference."""
    hostname = _extract_hostname(reference)
    registry.auth.hostname = hostname
    registry.auth.load_configs(hostname)


def _normalize_docker_hub(reference: str) -> str:
    """Rewrite docker.io/ hostname references to use registry-1.docker.io/ directly instead.
    """
    return reference.replace("docker.io/", "registry-1.docker.io/", 1)


def oras_py_pull(base_image: str, dest: typing.Union[str, os.PathLike], *, insecure: bool = False, tls_verify: bool = True) -> None:
    """Pull an image from a registry to a local OCI layout directory using oras-py."""
    from oras.provider import Registry
    from oras.layout.layout import NewLayoutFromRegistry

    if isinstance(dest, os.PathLike):
        dest = str(dest)

    base_image = _normalize_docker_hub(base_image)
    registry = Registry(insecure=insecure, tls_verify=tls_verify)
    _setup_auth(registry, base_image)
    NewLayoutFromRegistry(path=dest, provider=registry, target=base_image, tag="latest")


def oras_py_push(src: typing.Union[str, os.PathLike], oci_ref: str, *, insecure: bool = False, tls_verify: bool = True) -> None:
    """Push a local OCI layout directory to a registry using oras-py."""
    from oras.provider import Registry
    from oras.layout.layout import NewLayout

    if isinstance(src, os.PathLike):
        src = str(src)

    oci_ref = _normalize_docker_hub(oci_ref)
    registry = Registry(insecure=insecure, tls_verify=tls_verify)
    _setup_auth(registry, oci_ref)
    layout = NewLayout(src)
    layout.push_to_registry(provider=registry, target=oci_ref, tag="latest")
