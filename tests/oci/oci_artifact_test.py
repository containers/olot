from olot.backend.oras_cp import oras_push
from olot.backend.skopeo import skopeo_inspect, skopeo_push
from olot.basics import write_empty_config_in_ocilayoyt
from olot.oci.oci_common import MediaTypes
from olot.oci.oci_image_index import Manifest, OCIImageIndex
from olot.oci.oci_image_layout import OCIImageLayout
from olot.oci.oci_image_manifest import ContentDescriptor, OCIImageManifest, create_oci_image_manifest, empty_config
from olot.oci.oci_utils import get_descriptor_from_manifest
from olot.utils.files import targz_from_file, walk_files
from olot.utils.types import compute_hash_of_str
from tests.common import get_test_data_path, sample_model_path, file_checksums_with_compression, file_checksums_without_compression
from olot.oci_artifact import create_blobs, create_simple_oci_artifact
import pytest
import logging

import os
from pathlib import Path

from tests.conftest import registry_addr


logger = logging.getLogger(__name__)


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


def test_full_artifact(tmp_path):
    ocilayout_path = tmp_path
    lmeh_path = get_test_data_path()

    blobs_path = ocilayout_path / "blobs" / "sha256"
    blobs_path.mkdir(parents=True, exist_ok=True)

    write_empty_config_in_ocilayoyt(ocilayout_path)
    
    lmeh_assets = [
        lmeh_path / "lmeh" / "results_2025-04-30T18-24-41.082644.json",
        lmeh_path / "lmeh" / "samples_gsm8k_2025-04-30T18-24-41.082644.jsonl",
    ]
    cds = []
    for e in lmeh_assets:
        new_layer = targz_from_file(e, blobs_path, prefix="/")
        layer_digest = new_layer.layer_digest
        layer_stat = os.stat(blobs_path / layer_digest)
        size = layer_stat.st_size
        la = {"org.opencontainers.image.title": new_layer.title}
        cd = ContentDescriptor(
            mediaType=MediaTypes.layer_gzip,
            digest="sha256:"+layer_digest,
            size=size,
            urls=None,
            data=None,
            artifactType=None,
            annotations=la
        )
        cds.append(cd)

    manifest = create_oci_image_manifest(config=empty_config(),
        artifactType="application/json",
        layers=cds)
    manifest_json = manifest.model_dump_json(indent=2, exclude_none=True)
    manifest_SHA = compute_hash_of_str(manifest_json)
    manifest_blob_path = blobs_path / manifest_SHA
    with open(manifest_blob_path, "w") as f:
        f.write(manifest.model_dump_json(indent=2, exclude_none=True))
    
    layout = OCIImageLayout(imageLayoutVersion="1.0.0")
    with open(ocilayout_path / "oci-layout", "w") as f:
        f.write(layout.model_dump_json(indent=2, exclude_none=True))

    index = OCIImageIndex(schemaVersion=2,
                          manifests=[
                              Manifest(mediaType=MediaTypes.manifest,
                                       size=os.stat(manifest_blob_path).st_size,
                                       digest="sha256:"+manifest_SHA,
                                       annotations={"org.opencontainers.image.ref.name": "latest"})
                          ])
    with open(ocilayout_path / "index.json", "w") as f:
        f.write(index.model_dump_json(indent=2, exclude_none=True))

    # now let's use oras-copy to transfer from oci-layout to another oci-layout (instead of a OCI registry)
    oras_push(tmp_path, tmp_path / "output:latest", ["--to-oci-layout"])
    print(tmp_path)
    
    # iterate the blobs so to include manifest and config in addition to the layers
    output_blobs_path = tmp_path / "output" / "blobs" / "sha256"
    assert output_blobs_path.exists(), f"Output blobs directory {output_blobs_path} does not exist"
    original_blob_files = set()
    for file_path in blobs_path.iterdir():
        if file_path.is_file():
            original_blob_files.add(file_path.name)
    output_blob_files = set()
    for file_path in output_blobs_path.iterdir():
        if file_path.is_file():
            output_blob_files.add(file_path.name)

    # check same blobs
    missing_files = original_blob_files - output_blob_files
    assert not missing_files, f"Files missing in output: {missing_files}"
    assert len(output_blob_files) >= len(original_blob_files), \
        f"Output has fewer files ({len(output_blob_files)}) than original ({len(original_blob_files)})"

    # check the blobs content are the same
    for filename in original_blob_files:
        original_file_path = blobs_path / filename
        output_file_path = output_blobs_path / filename

        assert output_file_path.exists(), f"Output file {filename} does not exist"
        with open(original_file_path, 'rb') as orig_file, open(output_file_path, 'rb') as out_file:
            original_content = orig_file.read()
            output_content = out_file.read()
        assert original_content == output_content, \
            f"File content mismatch for {filename}: original size={len(original_content)}, output size={len(output_content)}"
        assert len(original_content) == len(output_content), \
            f"File size mismatch for {filename}: original={len(original_content)}, output={len(output_content)}"


def test_full_artifact_with_directory_structure(tmp_path: Path):
    ocilayout_path = tmp_path / "working"
    ocilayout_path.mkdir(parents=True, exist_ok=True)
    
    lmeh_path = get_test_data_path() / "lmeh2"
    walked_files = walk_files(lmeh_path)
    expected_walked_files = [
        Path("README.md"),
        Path("lmeh/results_2025-04-30T18-24-41.082644.json"),
        Path("lmeh/samples_gsm8k_2025-04-30T18-24-41.082644.jsonl"),
        Path("some.log"),
    ]
    assert walked_files == expected_walked_files
    test_annotations = {"org.opencontainers.image.description": "test artifact", "io.opendatahub.author": "olot"}
    create_simple_oci_artifact(lmeh_path, ocilayout_path, annotations=test_annotations)

    # verify annotations are present in the image manifest
    blobs_path = ocilayout_path / "blobs" / "sha256"
    index = OCIImageIndex.model_validate_json((ocilayout_path / "index.json").read_text())
    manifest_hash = index.manifests[0].digest.removeprefix("sha256:")
    manifest = OCIImageManifest.model_validate_json((blobs_path / manifest_hash).read_text())
    assert manifest.annotations is not None
    for k, v in test_annotations.items():
        assert manifest.annotations[k] == v

    # now let's use oras-copy to transfer from oci-layout to another oci-layout (instead of a OCI registry)
    oras_push(ocilayout_path, str(tmp_path / "output:latest"), ["--to-oci-layout"])
    print(tmp_path)

    # iterate the blobs so to include manifest and config in addition to the layers
    output_blobs_path = tmp_path / "output" / "blobs" / "sha256"
    assert output_blobs_path.exists(), f"Output blobs directory {output_blobs_path} does not exist"
    original_blob_files = set()
    for file_path in blobs_path.iterdir():
        if file_path.is_file():
            original_blob_files.add(file_path.name)
    output_blob_files = set()
    for file_path in output_blobs_path.iterdir():
        if file_path.is_file():
            output_blob_files.add(file_path.name)

    # check same blobs
    missing_files = original_blob_files - output_blob_files
    assert not missing_files, f"Files missing in output: {missing_files}"
    assert len(output_blob_files) >= len(original_blob_files), \
        f"Output has fewer files ({len(output_blob_files)}) than original ({len(original_blob_files)})"

    # check the blobs content are the same
    for filename in original_blob_files:
        original_file_path = blobs_path / filename
        output_file_path = output_blobs_path / filename

        assert output_file_path.exists(), f"Output file {filename} does not exist"
        with open(original_file_path, 'rb') as orig_file, open(output_file_path, 'rb') as out_file:
            original_content = orig_file.read()
            output_content = out_file.read()
        assert original_content == output_content, \
            f"File content mismatch for {filename}: original size={len(original_content)}, output size={len(output_content)}"
        assert len(original_content) == len(output_content), \
            f"File size mismatch for {filename}: original={len(original_content)}, output={len(output_content)}"


@pytest.mark.e2e_skopeo
def test_artifact_and_referrer_with_skopeo(tmp_path: Path):
    ocilayout_path = tmp_path / "working1"
    ocilayout_path.mkdir(parents=True, exist_ok=True)
    
    lmeh_path = get_test_data_path() / "lmeh"
    walked_files = walk_files(lmeh_path)
    expected_walked_files = [
        Path("results_2025-04-30T18-24-41.082644.json"),
        Path("samples_gsm8k_2025-04-30T18-24-41.082644.jsonl"),
    ]
    assert walked_files == expected_walked_files
    create_simple_oci_artifact(lmeh_path, ocilayout_path)

    ref = registry_addr() + "/myorg/myartifact:latest"
    skopeo_push(ocilayout_path, ref, ["--dest-tls-verify=false"])

    # reminder: should prefer digest based reference to Tag based reference
    if "@" not in ref:
        logger.warning("Should prefer to use a digest based reference, instead of Tag reference")
    
    manifest = skopeo_inspect("docker://"+ref, ["--tls-verify=false"])
    subject = get_descriptor_from_manifest(manifest)
    ocilayout_path = tmp_path / "working2"
    ocilayout_path.mkdir(parents=True, exist_ok=True)
    create_simple_oci_artifact(lmeh_path, ocilayout_path, subject=subject)
    skopeo_push(ocilayout_path, registry_addr()+"/myorg/myartifact:referrer", ["--dest-tls-verify=false"])
    # TODO At this point cannot do much more since the Distribution Registry does not support Referrers API,
    # but Quay and other registry do; can reconsider expanding the test by using a pure OCI registry.
    # The above already works with `oras discover ...` when persisted on Quay, for example.
