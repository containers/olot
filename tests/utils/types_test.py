from olot.utils.types import compute_hash_of_str

def test_compute_hash_of_str():
    """Basis compute_hash_of_str() fn testing
    """
    my_string = "Hello, World! Thanks Andrew, Roland, Syed and Quay team for the idea :)"
    actual = compute_hash_of_str(my_string)
    assert actual == "8695589abd30ec83cde42fabc3b4f6fd7da629eca94cf146c7920c6b067f4087" # can use echo -n "Hello, World! Thanks Andrew, Roland, Syed and Quay team for the idea :)" | shasum -a 256
