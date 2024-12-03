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
        sha256 = writer.hash_func
        with tarfile.open(fileobj=writer, mode="w") as tar:
            tar.add(hello_path, arcname=hello_path.name)

    checksum = sha256.hexdigest()
    print(f"digest of the tar file: {checksum}")

    final_tar_filename = f"{checksum}.tar"
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)

    print(f"tar file renamed to: {final_tar_filename}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)


@pytest.skip("not yet clear how to have this stable when adding compression yet")
def test_single_file_gz(tmp_path):
    hello_path = Path(__file__).parent / "data" / "hello.md"
    sha256_path = tmp_path / "blobs" / "sha256"
    sha256_path.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = sha256_path / "temp_layer.tar.gz"
    
    fixed_timestamp = 1638316800
    # only bz2 looks stable
    with tarfile.open(str(temp_tar_filename), mode="w:bz2") as tar:
        info = tarfile.TarInfo(name=hello_path.name)
        info.mtime = fixed_timestamp
        tar.add(hello_path, arcname=hello_path.name)

    checksum = get_file_hash(temp_tar_filename)
    print(f"digest of the tar.gz file: {checksum}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)
