from pathlib import Path
import filecmp

from olot.embedded_oci_layout import embedded_oci_layout


def test_check_embedded_oci_layout(tmp_path: Path):
    """check that the embedded oci-layout is valid
    """
    embedded_oci_layout(tmp_path)
    
    # list recursively all files in the tmp_path
    for file in tmp_path.rglob("*"):
        print(file)

    assert (tmp_path / "oci-layout").exists()
    assert (tmp_path / "index.json").exists()
    
    # Check that all files from embedded_oci_layout are copied correctly
    import olot
    package_root = Path(olot.__file__).parent
    embedded_path = package_root / "embedded_oci_layout"
    
    # Verify the entire directory structure is copied correctly
    assert filecmp.dircmp(embedded_path, tmp_path).diff_files == [], \
        f"Files differ between {embedded_path} and {tmp_path}"
    
    # Verify that all files have the same content
    for file_path in embedded_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(embedded_path)
            dest_path = tmp_path / relative_path
            assert dest_path.exists(), f"File {relative_path} not found in destination"
            assert filecmp.cmp(file_path, dest_path, shallow=False), \
                f"File content differs for {relative_path}"
