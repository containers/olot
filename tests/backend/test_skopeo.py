
import pytest
from olot.backend.skopeo import is_skopeo, skopeo_pull
from olot.basics import check_ocilayout, read_ocilayout_root_index

@pytest.mark.e2e_skopeo
def test_is_skopeo():
    assert is_skopeo()


@pytest.mark.e2e_skopeo
def test_skopeo_pull(tmp_path):
    """Test skopeo to pull/dl a known base-image to an oci-layout
    """
    skopeo_pull("quay.io/mmortari/hello-world-wait", tmp_path)

    assert check_ocilayout(tmp_path)

    mut = read_ocilayout_root_index(tmp_path)
    assert mut.schemaVersion == 2
    assert len(mut.manifests) == 1
    manifest0 = mut.manifests[0]
    assert manifest0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert manifest0.digest == "sha256:d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    assert manifest0.size == 491

