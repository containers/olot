from tests.common import sample_model_path, file_checksums_with_compression, file_checksums_without_compression
from olot.oci_artifact import create_blobs

import os
from pathlib import Path


def test_create_blobs(tmp_path):
    source_dir = sample_model_path()
    dest_dir = tmp_path

    model_files = [source_dir / Path(f) for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]

    layers = create_blobs(model_files, dest_dir)

    expected_layers = {}
    result = file_checksums_with_compression(source_dir / "README.md", dest_dir)
    expected_layers["README.md"] = result[1]

    result = file_checksums_without_compression(source_dir / "hello.md", dest_dir)
    expected_layers["hello.md"] = result

    result = file_checksums_without_compression(source_dir / "model.joblib", dest_dir)
    expected_layers["model.joblib"] = result

    assert sorted(layers) == sorted(expected_layers)