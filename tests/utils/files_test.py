from pathlib import Path
import tarfile
import gzip
import shutil
import os

import pytest
from olot.utils.files import get_file_hash, HashingWriter, tarball_from_file, targz_from_file, walk_files_recursive

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


def test_tarball_from_file_using_prefix(tmp_path):
    """Test tarball_from_file() function is able to produce the expected tar (uncompressed) layer blob in the oci-layout
    but providing a custom prefix location for the file.
    """
    model_path = sample_model_path() / "model.joblib"
    write_dest = sha256_path(tmp_path)
    write_dest.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match=r"should end with '/'"):
        tarball_from_file(model_path, write_dest, "wrong")
    tbf = tarball_from_file(model_path, write_dest, "custom/") # forcing it into a partial temp directory with blobs subdir for tests
    digest = tbf.layer_digest
    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)

    checksum_from_disk = get_file_hash(write_dest / digest) # read the file
    assert digest == checksum_from_disk # filename should match its digest

    # explode the tar file in the root oftmp_path, for the scope of the test
    with tarfile.open(write_dest / digest, "r") as tar:
        tar.extractall(path=tmp_path)
    print(Path(tmp_path / "custom" / "model.joblib"))
    assert Path(tmp_path / "custom" / "model.joblib").exists()
    assert Path(tmp_path / "custom" / "model.joblib").is_file()


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


def test_targz_from_file_using_prefix(tmp_path):
    """Test targz_from_file() function is able to produce the expected tar.gz layer blob in the oci-layout
    but providing a custom prefix for the location of the file in the tar.gz.
    """
    model_path = sample_model_path() / "model.joblib"
    write_dest = sha256_path(tmp_path)
    write_dest.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match=r"should end with '/'"):
        targz_from_file(model_path, write_dest, "wrong")
    tgz = targz_from_file(model_path, write_dest, "custom/") # forcing it into a partial temp directory with blobs subdir for tests
    postcomp_chksum = tgz.layer_digest

    for file in tmp_path.rglob('*'):
        if file.is_file():
            print(file)

    checksum_from_disk = get_file_hash(write_dest / postcomp_chksum) # read the file
    assert postcomp_chksum == checksum_from_disk # filename should match its digest

    # explode the targz file in the root of tmp_path, for the scope of the test
    with tarfile.open(write_dest / postcomp_chksum, "r:gz") as tar:
        tar.extractall(path=tmp_path)
    print(Path(tmp_path / "custom" / "model.joblib"))
    assert Path(tmp_path / "custom" / "model.joblib").exists()
    assert Path(tmp_path / "custom" / "model.joblib").is_file()


def test_walk_files_recursive_empty_dir(tmp_path):
    """Test walk_files_recursive() with an empty directory"""
    result = walk_files_recursive(tmp_path)
    assert result == []


def test_walk_files_recursive_basic(tmp_path):
    """Test walk_files_recursive() with a basic directory structure"""
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir2").mkdir()
    (tmp_path / "dir1" / "subdir").mkdir()
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.py").write_text("content2")
    (tmp_path / "dir1" / "file3.md").write_text("content3")
    (tmp_path / "dir1" / "subdir" / "file4.json").write_text("content4")
    (tmp_path / "dir2" / "file5.txt").write_text("content5")
    
    result = walk_files_recursive(tmp_path)
    
    expected = [
        "dir1/file3.md",
        "dir1/subdir/file4.json", 
        "dir2/file5.txt",
        "file1.txt",
        "file2.py",
    ]
    assert result == expected


def test_walk_files_recursive_nested_structure(tmp_path):
    """Test walk_files_recursive() with deeply nested directory structure"""
    (tmp_path / "a" / "b" / "c" / "d").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c" / "e").mkdir(parents=True)
    (tmp_path / "a" / "f").mkdir(parents=True)
    (tmp_path / "root_file.txt").write_text("root")
    (tmp_path / "a" / "a_file.txt").write_text("a")
    (tmp_path / "a" / "b" / "b_file.txt").write_text("b")
    (tmp_path / "a" / "b" / "c" / "c_file.txt").write_text("c")
    (tmp_path / "a" / "b" / "c" / "d" / "d_file.txt").write_text("d")
    (tmp_path / "a" / "b" / "c" / "e" / "e_file.txt").write_text("e")
    (tmp_path / "a" / "f" / "f_file.txt").write_text("f")
    
    result = walk_files_recursive(tmp_path)
    
    expected = [
        "a/a_file.txt",
        "a/b/b_file.txt", 
        "a/b/c/c_file.txt",
        "a/b/c/d/d_file.txt",
        "a/b/c/e/e_file.txt",
        "a/f/f_file.txt",
        "root_file.txt"
    ]
    assert result == expected


def test_walk_files_recursive_with_symlinks(tmp_path):
    """Test walk_files_recursive() with symbolic links"""
    (tmp_path / "original.txt").write_text("original content")
    (tmp_path / "link.txt").symlink_to("original.txt")
    (tmp_path / "real_dir").mkdir()
    (tmp_path / "real_dir" / "file_in_dir.txt").write_text("content")
    (tmp_path / "dir_link").symlink_to("real_dir")
    
    result = walk_files_recursive(tmp_path)
    
    expected = [
        "original.txt",  # original file
        "real_dir/file_in_dir.txt"  # original directory content
    ]
    assert result == expected


def test_walk_files_recursive_with_symlinks(tmp_path):
    """Test walk_files_recursive() with different path types"""
    (tmp_path / "test_file.txt").write_text("test")
    
    # Test with Path object
    result1 = walk_files_recursive(tmp_path)
    
    # Test with string path
    result2 = walk_files_recursive(str(tmp_path))
    
    # Test with os.PathLike (Path)
    result3 = walk_files_recursive(Path(tmp_path))
    
    expected = ["test_file.txt"]
    assert result1 == expected
    assert result2 == expected
    assert result3 == expected


def test_walk_files_recursive_error_cases(tmp_path):
    """Test walk_files_recursive() error cases"""
    # Test with non-existent path
    with pytest.raises(ValueError, match="does not exist"):
        walk_files_recursive(tmp_path / "nonexistent")
    
    # Test with file instead of directory
    (tmp_path / "not_a_dir.txt").write_text("content")
    with pytest.raises(ValueError, match="is not a directory"):
        walk_files_recursive(tmp_path / "not_a_dir.txt")


def test_walk_files_recursive_special_files(tmp_path):
    """Test walk_files_recursive() with files having special characters"""
    (tmp_path / "file with spaces.txt").write_text("content1")
    (tmp_path / "file-with-dashes.txt").write_text("content2")
    (tmp_path / "file_with_underscores.txt").write_text("content3")
    (tmp_path / "file.with.dots.txt").write_text("content4")
    (tmp_path / "file(1).txt").write_text("content5")
    (tmp_path / "file[2].txt").write_text("content6")
    
    result = walk_files_recursive(tmp_path)
    
    expected = [
        "file with spaces.txt",
        "file(1).txt",
        "file-with-dashes.txt",
        "file.with.dots.txt",
        "file[2].txt",
        "file_with_underscores.txt",
    ]
    assert result == expected


def test_walk_files_recursive_hidden_files(tmp_path):
    """Test walk_files_recursive() with hidden files and directories"""
    (tmp_path / ".hidden_file").write_text("hidden")
    (tmp_path / ".hidden_dir").mkdir()
    (tmp_path / ".hidden_dir" / "file_in_hidden.txt").write_text("content")
    (tmp_path / "normal_file.txt").write_text("normal")
    (tmp_path / "normal_dir").mkdir()
    (tmp_path / "normal_dir" / "file_in_normal.txt").write_text("content")
    
    result = walk_files_recursive(tmp_path)
    
    expected = [
        ".hidden_dir/file_in_hidden.txt",
        ".hidden_file",
        "normal_dir/file_in_normal.txt",
        "normal_file.txt"
    ]
    assert result == expected
