import gzip
import os
from pathlib import Path
import tarfile

from olot.basics import HashingWriter, get_file_hash


def test_get_file_hash():
    """As get_file_hash() function is used in other test, making sure it is generating the expected digest for known data
    """
    hello_path = Path(__file__).parent / "data" / "hello.md"
    checksum_from_disk = get_file_hash(hello_path)
    assert checksum_from_disk == "d91aa8aa7b56706b89e4a9aa27d57f45785082ba40e8a67e58ede1ed5709afd8"


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
