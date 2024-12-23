from olot.oci.oci_image_index import read_ocilayout_root_index

from tests.common import test_data_path

def test_read_ocilayout_root_index():
    """Read correctly the ocilayout_root_index in a given oci-layout
    """
    ocilayout3_path = test_data_path() / "ocilayout3"
    mut = read_ocilayout_root_index(ocilayout3_path)
    assert mut.schemaVersion == 2
    assert len(mut.manifests) == 3
    manifest0 = mut.manifests[0]
    assert manifest0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert manifest0.digest == "sha256:d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    assert manifest0.size == 491