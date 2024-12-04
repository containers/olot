import gzip
import hashlib
import io
import os
from pathlib import Path
import tarfile

import pytest

from olot.basics import HashingWriter, get_file_hash

def test_single_file_tar(tmp_path):
    hello_path = Path(__file__).parent / "data" / "hello.md"
    sha256_path = tmp_path / "blobs" / "sha256"
    sha256_path.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = sha256_path / "temp_layer"
    
    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with tarfile.open(fileobj=writer, mode="w") as tar:
            tar.add(hello_path, arcname=hello_path.name)

    checksum = writer.hash_func.hexdigest()
    print(f"digest of the tar file: {checksum}")
    assert checksum == "08e87bd00a65bebed3cabc34b4cf9a005b3bf31c25078ebd44a30fa1ad0778e3"

    checksum2 = get_file_hash(temp_tar_filename)
    print(f"to double-check, here is the checksum of .tar.gz re-reading it: {checksum2}")

    final_tar_filename = f"{checksum}.tar"
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)
    print(f"tar file renamed to: {final_tar_filename}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)


def test_single_file_gz(tmp_path):
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

    tar_checksum = inner_writer.hash_func.hexdigest()
    print(f"digest of the tar file: {tar_checksum}")
    assert tar_checksum == "08e87bd00a65bebed3cabc34b4cf9a005b3bf31c25078ebd44a30fa1ad0778e3"
    checksum = writer.hash_func.hexdigest()
    print(f"digest of the tar.gz file: {checksum}")
    assert checksum == "42ebad9bfd3ace9ea36c96957b41a0ab3d8f7b0528700a1a154887c459b33587"

    checksum2 = get_file_hash(temp_tar_filename)
    print(f"to double-check, here is the checksum of .tar.gz re-reading it: {checksum2}")

    final_tar_filename = f"{checksum}.tar.gz"
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)
    print(f"tar file renamed to: {final_tar_filename}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)
