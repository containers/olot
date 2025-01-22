from tests.common import sample_model_path, file_checksums_with_compression, file_checksums_without_compression
from olot.oci.oci_common import create_blobs



def test_create_blobs(tmp_path):
    source_dir = sample_model_path()
    dest_dir = tmp_path

    layers = create_blobs(source_dir, dest_dir)

    expected_layers = {}
    result = file_checksums_with_compression(source_dir / "README.md", dest_dir)
    expected_layers[result[0]] = result[1]

    result = file_checksums_without_compression(source_dir / "hello.md", dest_dir)
    expected_layers[result] = result

    result = file_checksums_without_compression(source_dir / "model.joblib", dest_dir)
    expected_layers[result] = result

    assert sorted(layers) == sorted(expected_layers)