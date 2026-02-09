from olot.utils.validation import is_valid_registry_host_port


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
