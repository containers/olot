
from olot.oci.oci_utils import get_descriptor_from_manifest
from tests.common import get_test_data_path

def test_get_descriptor_from_manifest():
    data_path = get_test_data_path()

    sha = "d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    image = (data_path / "ocilayout2" / "blobs" / "sha256" / sha).read_text()
    descriptor = get_descriptor_from_manifest(image)
    assert descriptor
    assert descriptor.size == 491
    assert descriptor.digest == "sha256:" + sha
    assert descriptor.mediaType == "application/vnd.oci.image.index.v1+json"
    
    sha = "d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    image = (data_path / "ocilayout3" / "blobs" / "sha256" / sha).read_text()
    descriptor = get_descriptor_from_manifest(image)
    assert descriptor
    assert descriptor.size == 491
    assert descriptor.digest == "sha256:" + sha
    assert descriptor.mediaType == "application/vnd.oci.image.index.v1+json"

    sha = "6b679ab88ee14309a20d40544941f67b890e4ca49e1c40cfa133357f59b134d0"
    image = (data_path / "ocilayout4" / "blobs" / "sha256" / sha).read_text()
    descriptor = get_descriptor_from_manifest(image)
    assert descriptor
    assert descriptor.size == 1077
    assert descriptor.digest == "sha256:" + sha
    assert descriptor.mediaType == "application/vnd.oci.image.manifest.v1+json"

    sha = "c23ed8b7e30f5edd2417e1dd99fedad4445f3e835edb58760b2f83f2c0517878"
    image = (data_path / "ocilayout5" / "blobs" / "sha256" / sha).read_text()
    descriptor = get_descriptor_from_manifest(image)
    assert descriptor
    assert descriptor.size == 731
    assert descriptor.digest == "sha256:" + sha
    assert descriptor.mediaType == "application/vnd.oci.image.manifest.v1+json"
