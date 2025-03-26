import tarfile
import gzip
import shutil
import os
from olot.utils.files import get_file_hash, HashingWriter, tarball_from_file, targz_from_file

from tests.common import sample_model_path, sha256_path

def test_get_file_hash():
    """As get_file_hash() function is used in other test, making sure it is generating the expected digest for known data
    """
    hello_path = sample_model_path() / "hello.md"
    checksum_from_disk = get_file_hash(hello_path)
    assert checksum_from_disk == "d91aa8aa7b56706b89e4a9aa27d57f45785082ba40e8a67e58ede1ed5709afd8"


def test_Hashwriter_tar(tmp_path):
    """Example bespoke use of HashingWriter for .tar
    """
    hello_path = sample_model_path() / "hello.md"
    write_dest = sha256_path(tmp_path)
    write_dest.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = write_dest / "temp_layer"

    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with tarfile.open(fileobj=writer, mode="w") as tar:
            tar.add(hello_path, arcname=hello_path.name)

    checksum_from_disk = get_file_hash(temp_tar_filename)
    checksum = writer.hash_func.hexdigest()
    assert checksum == checksum_from_disk

    final_tar_filename = f"{checksum}.tar"
    os.rename(temp_tar_filename, write_dest / final_tar_filename)
    print(f"tar file renamed to: {final_tar_filename}")

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)


def test_Hashwriter_tar_gz(tmp_path):
    """Example bespoke use of HashingWriter for .tar.gz
    """
    hello_path = sample_model_path() / "hello.md"
    write_dest = sha256_path(tmp_path)
    write_dest.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = write_dest / "temp_layer.tar.gz"

    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with gzip.GzipFile(fileobj=writer, mode="wb", mtime=0, compresslevel=6) as gz:
            inner_writer = HashingWriter(gz)
            with tarfile.open(fileobj=inner_writer, mode="w") as tar:
                tar.add(hello_path, arcname=hello_path.name)

    checksum_from_disk = get_file_hash(temp_tar_filename)
    checksum = writer.hash_func.hexdigest()
    assert checksum == checksum_from_disk

    uncompressed_tar = tmp_path / "uncompressed.tar"
    with tarfile.open(uncompressed_tar, mode="w") as tar:
        tar.add(hello_path, arcname=hello_path.name)

    uncompressed_checksum_from_disk = get_file_hash(uncompressed_tar)
    tar_checksum = inner_writer.hash_func.hexdigest()
    assert tar_checksum == uncompressed_checksum_from_disk

    final_tar_filename = f"{checksum}.tar.gz"
    os.rename(temp_tar_filename, write_dest / final_tar_filename)

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)

def test_tarball_from_file(tmp_path):
    """Test tarball_from_file() function is able to produce the expected tar (uncompressed) layer blob in the oci-layout
    """
    model_path = sample_model_path() / "model.joblib"
    write_dest = sha256_path(tmp_path)
    write_dest.mkdir(parents=True, exist_ok=True)
    tbf = tarball_from_file(model_path, write_dest) # forcing it into a partial temp directory with blobs subdir for tests
    digest = tbf.layer_digest
    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)

    checksum_from_disk = get_file_hash(write_dest / digest) # read the file
    assert digest == checksum_from_disk # filename should match its digest

    found = None
    with tarfile.open(write_dest / digest, "r") as tar:
        for tarinfo in tar:
            if tarinfo.name == "models/model.joblib" and tarinfo.mode == 0o664:
                found = tarinfo # model.joblib is added in models/ inside modelcar with expected permissions
    assert found


def test_targz_from_file(tmp_path):
    """Test targz_from_file() function is able to produce the expected tar.gz layer blob in the oci-layout
    """
    model_path = sample_model_path() / "model.joblib"
    write_dest = sha256_path(tmp_path)
    write_dest.mkdir(parents=True, exist_ok=True)
    tgz = targz_from_file(model_path, write_dest) # forcing it into a partial temp directory with blobs subdir for tests
    postcomp_chksum = tgz.layer_digest
    precomp_chskum = tgz.diff_id

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)

    checksum_from_disk = get_file_hash(write_dest / postcomp_chksum) # read the file
    assert postcomp_chksum == checksum_from_disk # filename should match its digest

    found = None
    with tarfile.open(write_dest / postcomp_chksum, "r:gz") as tar:
        for tarinfo in tar:
            if tarinfo.name == "models/model.joblib" and tarinfo.mode == 0o664:
                found = tarinfo # model.joblib is added in models/ inside modelcar with expected permissions
    assert found

    uncompressed_tar = write_dest / "uncompressed.tar"
    with gzip.open(write_dest / postcomp_chksum, "rb") as g_in:
        with open(uncompressed_tar, "wb") as f_out:
            shutil.copyfileobj(g_in, f_out)
    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)
    tar_checksum_from_disk = get_file_hash(uncompressed_tar) # compute the digest for the .tar from the .tar.gz
    assert precomp_chskum == tar_checksum_from_disk # digests should match