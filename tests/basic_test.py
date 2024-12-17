import gzip
import os
from pathlib import Path
import tarfile
from typing import Dict

import pytest

from olot.basics import HashingWriter, get_file_hash, check_ocilayout, read_ocilayout_root_index, crawl_ocilayout_indexes, crawl_ocilayout_manifests, compute_hash_of_str, tar_into_ocilayout
from olot.oci.oci_image_index import OCIImageIndex
from olot.oci.oci_image_manifest import OCIImageManifest


def test_get_file_hash():
    """As get_file_hash() function is used in other test, making sure it is generating the expected digest for known data
    """
    hello_path = Path(__file__).parent / "data" / "hello.md"
    checksum_from_disk = get_file_hash(hello_path)
    assert checksum_from_disk == "d91aa8aa7b56706b89e4a9aa27d57f45785082ba40e8a67e58ede1ed5709afd8"


def test_compute_hash_of_str():
    """Basis compute_hash_of_str() fn testing
    """
    my_string = "Hello, World! Thanks Andrew, Roland, Syed and Quay team for the idea :)"
    actual = compute_hash_of_str(my_string)
    assert actual == "8695589abd30ec83cde42fabc3b4f6fd7da629eca94cf146c7920c6b067f4087" # can use echo -n "Hello, World! Thanks Andrew, Roland, Syed and Quay team for the idea :)" | shasum -a 256


def test_bespoke_single_file_tar(tmp_path):
    """Example bespoke use of HashingWriter for .tar
    """
    hello_path = Path(__file__).parent / "data" / "hello.md"
    sha256_path = tmp_path / "blobs" / "sha256"
    sha256_path.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = sha256_path / "temp_layer"
    
    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with tarfile.open(fileobj=writer, mode="w") as tar:
            tar.add(hello_path, arcname=hello_path.name)

    checksum_from_disk = get_file_hash(temp_tar_filename)
    print(f"to double-check, here is the checksum of .tar re-reading it: {checksum_from_disk}")

    checksum = writer.hash_func.hexdigest()
    print(f"digest of the tar file: {checksum}")
    assert checksum == checksum_from_disk

    final_tar_filename = f"{checksum}.tar"
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)
    print(f"tar file renamed to: {final_tar_filename}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)


def test_tar_into_ocilayout(tmp_path):
    """Test tar_into_ocilayout() function is able to produce the expected tar (uncompressed) layer blob in the oci-layout
    """
    model_path = Path(__file__).parent / "data" / "model.joblib"
    sha256_path = tmp_path / "blobs" / "sha256"
    sha256_path.mkdir(parents=True, exist_ok=True)
    digest = tar_into_ocilayout(tmp_path, model_path) # forcing it into a partial temp directory with blobs subdir for tests

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)

    checksum_from_disk = get_file_hash(sha256_path / digest) # read the file
    assert digest == checksum_from_disk # filename should match its digest


def test_bespoke_single_file_gz(tmp_path):
    """Example bespoke use of HashingWriter for .tar.gz
    """
    hello_path = Path(__file__).parent / "data" / "hello.md"
    sha256_path = tmp_path / "blobs" / "sha256"
    sha256_path.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = sha256_path / "temp_layer.tar.gz"
    
    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with gzip.GzipFile(fileobj=writer, mode="wb", mtime=0, compresslevel=6) as gz:
            inner_writer = HashingWriter(gz)
            with tarfile.open(fileobj=inner_writer, mode="w") as tar:
                tar.add(hello_path, arcname=hello_path.name)

    checksum_from_disk = get_file_hash(temp_tar_filename)
    print(f"to double-check, here is the checksum of .tar.gz re-reading it: {checksum_from_disk}")

    throwaway_tar = tmp_path / "throwaway.tar"
    with tarfile.open(throwaway_tar, mode="w") as tar:
        tar.add(hello_path, arcname=hello_path.name)
    throwaway_checksum_from_disk = get_file_hash(throwaway_tar)
    print(f"to double-check, here is the checksum of throwaway_tar .tar re-reading it: {throwaway_checksum_from_disk}")

    tar_checksum = inner_writer.hash_func.hexdigest()
    print(f"digest of the tar file: {tar_checksum}")
    assert tar_checksum == throwaway_checksum_from_disk
    checksum = writer.hash_func.hexdigest()
    print(f"digest of the tar.gz file: {checksum}")
    assert checksum == checksum_from_disk

    final_tar_filename = f"{checksum}.tar.gz"
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)
    print(f"tar file renamed to: {final_tar_filename}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)


def test_check_ocilayout():
    """Verify check_ocilayout() fn on known oci-layout and not
    """
    data_path = Path(__file__).parent / "data"
    check_ocilayout(data_path / "ocilayout1")
    check_ocilayout(data_path / "ocilayout2")
    check_ocilayout(data_path / "ocilayout3")
    with pytest.raises(Exception):
        check_ocilayout(data_path)


def test_read_ocilayout_root_index():
    """Read correctly the ocilayout_root_index in a given oci-layout
    """
    ocilayout3_path = Path(__file__).parent / "data" / "ocilayout3"
    mut = read_ocilayout_root_index(ocilayout3_path)
    assert mut.schemaVersion == 2
    assert len(mut.manifests) == 3
    manifest0 = mut.manifests[0]
    assert manifest0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert manifest0.digest == "sha256:d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    assert manifest0.size == 491


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

