from olot.utils.validation import is_valid_registry_host_port, is_valid_oci_reference


def test_valid_ipv4_address():
    """Test valid IPv4 addresses"""
    assert is_valid_registry_host_port("192.168.1.1")
    assert is_valid_registry_host_port("127.0.0.1")
    assert is_valid_registry_host_port("0.0.0.0")
    assert is_valid_registry_host_port("255.255.255.255")


def test_valid_ipv4_with_port():
    """Test valid IPv4 addresses with port"""
    assert is_valid_registry_host_port("192.168.1.1:5000")
    assert is_valid_registry_host_port("127.0.0.1:8080")
    assert is_valid_registry_host_port("10.0.0.1:443")
    assert is_valid_registry_host_port("172.16.0.1:1")
    assert is_valid_registry_host_port("192.168.1.1:65535")


def test_valid_ipv6_address():
    """Test valid IPv6 addresses"""
    assert is_valid_registry_host_port("::1")
    assert is_valid_registry_host_port("2001:db8::1")
    assert is_valid_registry_host_port("fe80::1")
    assert is_valid_registry_host_port("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
    # Bracket notation
    assert is_valid_registry_host_port("[::1]")
    assert is_valid_registry_host_port("[2001:db8::1]")
    # Bracket notation with port
    assert is_valid_registry_host_port("[::1]:5000")
    assert is_valid_registry_host_port("[2001:db8::1]:8080")
    assert is_valid_registry_host_port("[fe80::1]:443")


def test_valid_hostname():
    """Test valid hostnames"""
    assert is_valid_registry_host_port("localhost")
    assert is_valid_registry_host_port("example.com")
    assert is_valid_registry_host_port("registry.example.com")
    assert is_valid_registry_host_port("my-registry.io")
    assert is_valid_registry_host_port("registry-1.example.com")
    assert is_valid_registry_host_port("a.b.c.d.e.f.g")


def test_valid_hostname_with_port():
    """Test valid hostnames with port"""
    assert is_valid_registry_host_port("localhost:5000")
    assert is_valid_registry_host_port("example.com:443")
    assert is_valid_registry_host_port("registry.example.com:8080")
    assert is_valid_registry_host_port("my-registry.io:5000")


def test_invalid_port_out_of_range():
    """Test invalid ports that are out of valid range"""
    assert not is_valid_registry_host_port("localhost:0")
    assert not is_valid_registry_host_port("localhost:65536")
    assert not is_valid_registry_host_port("localhost:99999")
    assert not is_valid_registry_host_port("192.168.1.1:-1")


def test_invalid_port_non_numeric():
    """Test invalid non-numeric ports"""
    assert not is_valid_registry_host_port("localhost:abc")
    assert not is_valid_registry_host_port("example.com:port")
    assert not is_valid_registry_host_port("192.168.1.1:80a")


def test_invalid_hostname_too_long():
    """Test hostname exceeding maximum length"""
    long_hostname = "a" * 256
    assert not is_valid_registry_host_port(long_hostname)
    assert not is_valid_registry_host_port(f"{long_hostname}:5000")


def test_invalid_label_too_long():
    """Test label (DNS label between dots) exceeding maximum length of 63"""
    long_label = "a" * 64
    assert not is_valid_registry_host_port(f"{long_label}.example.com")
    assert not is_valid_registry_host_port(f"example.{long_label}.com")
    assert not is_valid_registry_host_port(f"example.com.{long_label}")
    assert not is_valid_registry_host_port(f"{long_label}.com:5000")
    # Valid label with exactly 63 characters should pass
    valid_label = "a" * 63
    assert is_valid_registry_host_port(f"{valid_label}.example.com")


def test_invalid_hostname_characters():
    """Test hostnames with invalid characters"""
    assert not is_valid_registry_host_port("host_name")
    assert not is_valid_registry_host_port("host name")
    assert not is_valid_registry_host_port("host@name")
    assert not is_valid_registry_host_port("-hostname")
    assert not is_valid_registry_host_port("hostname-")
    assert not is_valid_registry_host_port(".hostname")
    assert not is_valid_registry_host_port("hostname.")


def test_edge_cases():
    """Test edge cases"""
    assert is_valid_registry_host_port("a")  # Single character hostname
    assert is_valid_registry_host_port("a1")  # Hostname with number
    assert is_valid_registry_host_port("1a")  # Hostname starting with number
    assert not is_valid_registry_host_port("")  # Empty string
    assert not is_valid_registry_host_port(":")  # Only colon
    assert not is_valid_registry_host_port(":5000")  # Port without host


# OCI Reference Validation Tests

def test_valid_simple_references():
    """Test valid simple repository references without registry"""
    assert is_valid_oci_reference("mycontainer")
    assert is_valid_oci_reference("mycontainer:latest")
    assert is_valid_oci_reference("my-container:v1.0")
    assert is_valid_oci_reference("my.container:tag")
    assert is_valid_oci_reference("my_container:tag")
    assert is_valid_oci_reference("my__container:tag")
    assert is_valid_oci_reference("container123:v2")
    assert is_valid_oci_reference("123container:tag")


def test_valid_multi_component_repositories():
    """Test valid multi-component repository paths"""
    assert is_valid_oci_reference("myorg/mycontainer")
    assert is_valid_oci_reference("myorg/mycontainer:tag")
    assert is_valid_oci_reference("myorg/team/project:tag")
    assert is_valid_oci_reference("a/b/c/d/e/image:latest")
    assert is_valid_oci_reference("org/app-name:v1.0")
    assert is_valid_oci_reference("org/app.name:v1.0")
    assert is_valid_oci_reference("org/app_name:v1.0")


def test_valid_references_with_registry():
    """Test valid references with registry hostname"""
    assert is_valid_oci_reference("docker.io/library/busybox:latest")
    assert is_valid_oci_reference("quay.io/mmortari/hello-world-wait")
    assert is_valid_oci_reference("localhost:5000/myorg/myimage")
    assert is_valid_oci_reference("registry.io:443/path/to/image:tag")
    assert is_valid_oci_reference("127.0.0.1:5000/myimage:tag")
    assert is_valid_oci_reference("192.168.1.1:8080/myapp:v1")
    assert is_valid_oci_reference("example.com/myimage")
    assert is_valid_oci_reference("registry.example.com/org/image:latest")


def test_valid_references_with_ipv6_registry():
    """Test valid references with IPv6 registry addresses"""
    assert is_valid_oci_reference("[::1]:5000/myimage:tag")
    assert is_valid_oci_reference("[2001:db8::1]:5000/myimage:latest")
    assert is_valid_oci_reference("[fe80::1]:8080/org/app:v1")


def test_valid_references_with_digest():
    """Test valid references with digest instead of tag"""
    assert is_valid_oci_reference("mycontainer@sha256:0123456789abcdef")
    assert is_valid_oci_reference("myorg/mycontainer@sha256:abcdef0123456789")
    assert is_valid_oci_reference("registry.io/myorg/mycontainer@sha256:abc123def456")
    assert is_valid_oci_reference("registry.io:5000/myimage@sha256:fedcba9876543210")
    assert is_valid_oci_reference("localhost:5000/app@sha256:1234567890abcdef")
    # Digest with different algorithms
    assert is_valid_oci_reference("myimage@sha512:abcdef123456")
    assert is_valid_oci_reference("myimage@sha256+b64:ABCDEF123_-=")


def test_valid_references_missing_tag():
    """Test that missing tag is valid (implies :latest)"""
    assert is_valid_oci_reference("mycontainer")
    assert is_valid_oci_reference("myorg/mycontainer")
    assert is_valid_oci_reference("registry.io/myorg/mycontainer")
    assert is_valid_oci_reference("localhost:5000/myimage")


def test_valid_tag_patterns():
    """Test various valid tag patterns"""
    assert is_valid_oci_reference("myimage:latest")
    assert is_valid_oci_reference("myimage:v1.0.0")
    assert is_valid_oci_reference("myimage:2024.01.15")
    assert is_valid_oci_reference("myimage:release-candidate-1")
    assert is_valid_oci_reference("myimage:build_123")
    assert is_valid_oci_reference("myimage:UPPERCASE")
    assert is_valid_oci_reference("myimage:MixedCase")
    assert is_valid_oci_reference("myimage:_underscore")
    assert is_valid_oci_reference("myimage:1234567890")
    # Tag with maximum length (128 chars)
    assert is_valid_oci_reference("myimage:" + "a" * 128)


def test_invalid_empty_reference():
    """Test invalid empty or malformed references"""
    assert not is_valid_oci_reference("")
    assert not is_valid_oci_reference(None)
    assert not is_valid_oci_reference(":")
    assert not is_valid_oci_reference("@")
    assert not is_valid_oci_reference("/")


def test_invalid_uppercase_repository():
    """Test that uppercase in repository name is invalid"""
    assert not is_valid_oci_reference("UPPERCASE")
    assert not is_valid_oci_reference("MyContainer:tag")
    assert not is_valid_oci_reference("my-Container:tag")
    assert not is_valid_oci_reference("myOrg/myContainer:tag")


def test_invalid_both_tag_and_digest():
    """Test that having both tag and digest is invalid (for this validation helper fn)"""
    assert not is_valid_oci_reference("mycontainer:tag@sha256:abc123")
    assert not is_valid_oci_reference("mycontainer:latest@sha256:def456")
    assert not is_valid_oci_reference("registry.io/app:v1@sha256:123abc")


def test_invalid_empty_tag_or_digest():
    """Test that empty tag or digest is invalid"""
    assert not is_valid_oci_reference("mycontainer:")
    assert not is_valid_oci_reference("mycontainer@")
    assert not is_valid_oci_reference("myorg/mycontainer:")
    assert not is_valid_oci_reference("myorg/mycontainer@")
    assert not is_valid_oci_reference("registry.io/myimage:")
    assert not is_valid_oci_reference("registry.io/myimage@")


def test_invalid_missing_repository():
    """Test that missing repository is invalid"""
    assert not is_valid_oci_reference(":tag")
    assert not is_valid_oci_reference("@sha256:abc123")
    assert not is_valid_oci_reference("registry.io/")
    assert not is_valid_oci_reference("registry.io/:tag")
    assert not is_valid_oci_reference("localhost:5000/")


def test_invalid_repository_separators():
    """Test invalid separator patterns in repository"""
    assert not is_valid_oci_reference("my--container")
    assert not is_valid_oci_reference("my..container")
    assert not is_valid_oci_reference("my___container")
    assert not is_valid_oci_reference("-mycontainer")
    assert not is_valid_oci_reference("mycontainer-")
    assert not is_valid_oci_reference(".mycontainer")
    assert not is_valid_oci_reference("mycontainer.")
    assert not is_valid_oci_reference("_mycontainer")
    assert not is_valid_oci_reference("my/container-")
    assert not is_valid_oci_reference("my/-container")


def test_invalid_tag_patterns():
    """Test invalid tag patterns"""
    assert not is_valid_oci_reference("myimage:.tag")
    assert not is_valid_oci_reference("myimage:-tag")
    assert not is_valid_oci_reference("myimage:tag with spaces")
    # Tag too long (> 128 chars)
    assert not is_valid_oci_reference("myimage:" + "a" * 129)


def test_invalid_digest_patterns():
    """Test invalid digest patterns"""
    assert not is_valid_oci_reference("myimage@sha256")
    assert not is_valid_oci_reference("myimage@sha256:")
    assert not is_valid_oci_reference("myimage@:abc123")
    assert not is_valid_oci_reference("myimage@SHA256:abc123")  # Algorithm must be lowercase


def test_invalid_repository_too_long():
    """Test that repository path exceeding max length is invalid"""
    long_repo = "a" * 256
    assert not is_valid_oci_reference(long_repo)
    assert not is_valid_oci_reference(f"repo/{long_repo}")


def test_registry_port_disambiguation():
    """Test correct disambiguation between registry:port and repo:tag"""
    # These should be interpreted as registry:port/repo
    assert is_valid_oci_reference("localhost:5000/myimage")
    assert is_valid_oci_reference("registry.io:443/myimage")
    assert is_valid_oci_reference("example.com:8080/org/app")

    # These should be interpreted as repo:tag
    assert is_valid_oci_reference("myrepo:tag")
    assert is_valid_oci_reference("myrepo:latest")

    # Registry with port AND tag
    assert is_valid_oci_reference("registry.io:5000/myimage:tag")
    assert is_valid_oci_reference("localhost:5000/org/app:v1.0")
