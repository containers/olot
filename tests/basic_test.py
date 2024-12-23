from pathlib import Path
from typing import Dict

from olot.basics import crawl_ocilayout_indexes, crawl_ocilayout_manifests

from olot.oci.oci_image_index import OCIImageIndex, read_ocilayout_root_index
from olot.oci.oci_image_manifest import OCIImageManifest


def test_crawl_ocilayout_indexes():
    """Crawl for indexes models (the index content itself, not a manifest ref) in given oci-layout
    """
    ocilayout3_path = Path(__file__).parent / "data" / "ocilayout3"
    mut: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(ocilayout3_path, read_ocilayout_root_index(ocilayout3_path))
    assert len(mut.keys()) == 1
    assert "d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b" in mut.keys()
    index0 = mut["d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"]
    assert index0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert len(index0.manifests) == 2

    # I will redo the same fo ocilayout2 which is simplified from ocilayout3 as a sanity check
    ocilayout2_path = Path(__file__).parent / "data" / "ocilayout2"
    mut: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(ocilayout2_path, read_ocilayout_root_index(ocilayout2_path))
    assert len(mut.keys()) == 1
    assert "d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b" in mut.keys()
    index0 = mut["d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"]
    assert index0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert len(index0.manifests) == 2


def test_crawl_ocilayout_manifests():
    """Crawl for image manifest models (the image manifest content itself, not a manifest ref) in given oci-layout
    """
    ocilayout3_path = Path(__file__).parent / "data" / "ocilayout3"
    ocilayout_root_index = read_ocilayout_root_index(ocilayout3_path)
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(ocilayout3_path, ocilayout_root_index)
    mut: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(ocilayout3_path, ocilayout_indexes)

    assert len(mut.keys()) == 2
    assert "c23ed8b7e30f5edd2417e1dd99fedad4445f3e835edb58760b2f83f2c0517878" in mut.keys()
    image0 = mut["c23ed8b7e30f5edd2417e1dd99fedad4445f3e835edb58760b2f83f2c0517878"]
    assert image0.mediaType == "application/vnd.oci.image.manifest.v1+json"
    assert len(image0.layers) == 1
    layer0 = image0.layers[0]
    assert layer0.digest == "sha256:1933e30a3373776d5c7155591a6dacbc205cf6a2665b6dced682c6d2ea7b000f"
    assert layer0.size == 1949749
    assert layer0.mediaType == "application/vnd.oci.image.layer.v1.tar+gzip"

