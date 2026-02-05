import os
from pathlib import Path
from olot.utils.files import get_file_hash
import pytest
import shutil
from typing import Dict
import logging

from olot.basics import RemoveOriginals, crawl_ocilayout_blobs_to_extract, crawl_ocilayout_indexes, crawl_ocilayout_manifests, oci_layers_on_top, write_empty_config_in_ocilayoyt
from olot.constants import (
    ANNOTATION_LAYER_CONTENT_DIGEST,
    ANNOTATION_LAYER_CONTENT_TYPE,
    ANNOTATION_LAYER_CONTENT_INLAYERPATH,
)
from olot.oci.oci_config import OCIManifestConfig
from olot.oci.oci_image_index import OCIImageIndex, read_ocilayout_root_index
from olot.oci.oci_image_manifest import OCIImageManifest
from olot.utils.types import compute_hash_of_str
from tests.common import sample_model_path, get_test_data_path

from olot.modelpack import const as modelpack_consts


def test_remove_originals():
    assert [e.value for e in RemoveOriginals] == ["default", "all"]
    assert RemoveOriginals.DEFAULT == "default"


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
    mut: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(ocilayout3_path, ocilayout_indexes, ocilayout_root_index)

    assert len(mut.keys()) == 2
    assert "c23ed8b7e30f5edd2417e1dd99fedad4445f3e835edb58760b2f83f2c0517878" in mut.keys()
    image0 = mut["c23ed8b7e30f5edd2417e1dd99fedad4445f3e835edb58760b2f83f2c0517878"]
    assert image0.mediaType == "application/vnd.oci.image.manifest.v1+json"
    assert len(image0.layers) == 1
    layer0 = image0.layers[0]
    assert layer0.digest == "sha256:1933e30a3373776d5c7155591a6dacbc205cf6a2665b6dced682c6d2ea7b000f"
    assert layer0.size == 1949749
    assert layer0.mediaType == "application/vnd.oci.image.layer.v1.tar+gzip"


def test_crawl_ocilayout_blobs_to_extract(tmp_path: Path):
    """Crawl ocilayout4 which is a ModelCar containing one ML file "model.joblib" and one text file "README.md" as ModelCarD.
    Verify extraction from ModelCar produces those 2 assets.
    """
    ocilayout4_path = Path(__file__).parent / "data" / "ocilayout4"
    mut = crawl_ocilayout_blobs_to_extract(ocilayout4_path, tmp_path)

    assert len(mut) == 2
    assert "models/README.md" in mut
    assert "models/model.joblib" in mut

    assert len([x for x in tmp_path.rglob("*") if x.is_file()]) == 2
    modelcard = tmp_path / "models" / "README.md"
    assert modelcard.exists()
    modelfile = tmp_path / "models" / "model.joblib"
    assert modelfile.exists()


def test_oci_layers_on_top_with_remove_all(tmp_path: Path):
    """put oci_layers_on_top under test with 'remove' option
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout2"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    oci_layers_on_top(target_ocilayout, models, modelcard, remove_originals=RemoveOriginals.ALL)

    for model in models:
        assert not model.exists()
    assert not modelcard.exists()


def test_oci_layers_on_top_with_remove_default(tmp_path: Path):
    """put oci_layers_on_top under test with 'remove' option
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout2"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    oci_layers_on_top(target_ocilayout, models, modelcard, remove_originals=RemoveOriginals.DEFAULT)

    for model in models:
        assert not model.exists()
    assert modelcard.exists()


def test_oci_layers_on_top_without_remove(tmp_path: Path):
    """put oci_layers_on_top under test withOUT 'remove' option
    complementary to test_oci_layers_on_top_with_remove,
    used for future and non-regression of "API contract"
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout2"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    oci_layers_on_top(target_ocilayout, models, modelcard) # remove_originals=None, ie the default

    for model in models:
        assert model.exists()
    assert modelcard.exists()


def test_write_empty_oci_config(tmp_path: Path):
    """avoid limitation of skopeo that can't read inline empty config
    """
    oci_layout_path = tmp_path
    write_empty_config_in_ocilayoyt(oci_layout_path)

    empty_config_path = oci_layout_path / "blobs" / "sha256" / "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    assert empty_config_path.exists()
    with open(empty_config_path, "r") as f:
        actual = compute_hash_of_str(f.read())
    assert actual == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"


def test_oci_layers_on_top_single_manifest_and_check_annotations(tmp_path: Path):
    """check oci_layers_on_top with an oci-layout directory containing a single manifest
    and check annotations on layers, including the layer containing the ModelCarD to contain
    the expected annotations
    """
    test_sample_model = sample_model_path()
    test_ocilayout5 = get_test_data_path() / "ocilayout5"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout5, target_ocilayout)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    oci_layers_on_top(target_ocilayout, models, modelcard)

    ocilayout_root_index: OCIImageIndex = read_ocilayout_root_index(target_ocilayout)
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 1
    manifest0: OCIImageManifest = next(iter(ocilayout_manifests.values()))
    assert len(manifest0.layers) == 1 + len(models) + 1 # original value (only 1 layer in original oci-layout) + now added model files + now added modelcarD

    for layer in manifest0.layers[1:]: # skip original first layer in original oci-layout
        assert layer.annotations
        assert "org.opencontainers.image.title" in layer.annotations.keys()
    assert manifest0.layers[1].annotations
    assert manifest0.layers[1].annotations["org.opencontainers.image.title"] == "model.joblib"
    assert manifest0.layers[2].annotations
    assert manifest0.layers[2].annotations["org.opencontainers.image.title"] == "hello.md"
    # identify the ModelCarD layer by means of annotation(s) on the layer
    assert manifest0.layers[3].annotations
    assert manifest0.layers[3].annotations["org.opencontainers.image.title"] == "README.md"
    assert "io.opendatahub.modelcar.layer.type" in manifest0.layers[3].annotations.keys()
    assert manifest0.layers[3].annotations["io.opendatahub.modelcar.layer.type"] == "modelcard"

    # identify the ModelCarD by means of annotation from the Image Manifest
    modelcar_digest = manifest0.layers[3].digest
    assert manifest0.annotations
    assert manifest0.annotations["io.opendatahub.layers.modelcard"] == modelcar_digest

    assert len(manifest0.layers) == 4
    # check manifest.config.history contains the appropriate length
    with open(target_ocilayout / "blobs" / "sha256" / manifest0.config.digest.removeprefix("sha256:"), "r") as f:
        mc = OCIManifestConfig.model_validate_json(f.read())
        assert mc.history
        assert len(mc.history) == 5 # check we preserved also previous history, 2 elements, + 3 new history items for the 3 new layers
        assert len(list(x for x in mc.history if not x.empty_layer)) == len(manifest0.layers)


def test_add_modelpack_manifest_using_ocilayout3(tmp_path: Path):
    """add modelpack manifest to oci-layout, using ocilayout3 as the base oci-layout
    """
    test_sample_model = sample_model_path()
    test_ocilayout3 = get_test_data_path() / "ocilayout3"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout3, target_ocilayout, copy_function=shutil.copy2)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model, copy_function=shutil.copy2)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    ocilayout_root_index = read_ocilayout_root_index(target_ocilayout)
    assert len(ocilayout_root_index.manifests) == 3
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    assert len(ocilayout_indexes) == 1
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 2

    # add modelpack manifest
    oci_layers_on_top(target_ocilayout, models, modelcard, add_modelpack=True)
    print(target_ocilayout)
    ocilayout_root_index = read_ocilayout_root_index(target_ocilayout)
    assert len(ocilayout_root_index.manifests) == 4 # as ocilayout3 is from oras, it add Index(1x), the Manifest(2x) of the base image, and the ModelPack Manifest(1x) for a total of 4
    ocilayout_indexes = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    assert len(ocilayout_indexes) == 1 
    ocilayout_manifests = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 3 # the two original base image manifest (2x), plus the ModelPack Manifest(1x)
    # Find the ModelPack manifest
    for digest, manifest in ocilayout_manifests.items():
        if manifest.artifactType == modelpack_consts.ARTIFACTTYPEMODELMANIFEST:
            modelpack_manifest = manifest
            modelpack_manifest_digest = digest
            print(modelpack_manifest_digest)
            print(modelpack_manifest.model_dump_json(exclude_none=True))
            break
    assert modelpack_manifest is not None, "No manifest with artifactType == modelpack_consts.ARTIFACTTYPEMODELMANIFEST found"
    assert modelpack_manifest.config.mediaType == modelpack_consts.MEDIATYPEMODELCONFIG
    assert len(modelpack_manifest.layers) == 3
    # Check that there is a manifest entry in ocilayout_root_index.manifests with the correct annotation and digest
    for manifest_entry in ocilayout_root_index.manifests:
        if manifest_entry.annotations and manifest_entry.annotations.get("io.opendatahub.modelcar.manifest.type") == "modelpack":
            print(manifest_entry.model_dump_json(exclude_none=True))
            assert manifest_entry.digest.removeprefix("sha256:") == modelpack_manifest_digest
    # Check that there is a manifest entry in ocilayout_indexes.manifests with the correct annotation and digest
    for idx in ocilayout_indexes.values():
        for m in idx.manifests:
            if m.annotations and m.annotations.get("io.opendatahub.modelcar.manifest.type") == "modelpack":
                assert m.digest.removeprefix("sha256:") == modelpack_manifest_digest


def test_add_modelpack_manifest_using_ocilayout2(tmp_path: Path):
    """add modelpack manifest to oci-layout, using ocilayout2 as the base oci-layout
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout2"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout, copy_function=shutil.copy2)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model, copy_function=shutil.copy2)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    ocilayout_root_index = read_ocilayout_root_index(target_ocilayout)
    assert len(ocilayout_root_index.manifests) == 1
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    assert len(ocilayout_indexes) == 1
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 2

    # add modelpack manifest
    oci_layers_on_top(target_ocilayout, models, modelcard, add_modelpack=True)
    print(target_ocilayout)
    ocilayout_root_index = read_ocilayout_root_index(target_ocilayout)
    assert len(ocilayout_root_index.manifests) == 2 # as ocilayout2 is from skopeo, we have the ref to the Index(1x), and added here the ModelPack Manifest(1x) for a total of 2
    ocilayout_indexes = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    assert len(ocilayout_indexes) == 1 
    ocilayout_manifests = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 3 # the two original base image manifest (2x), plus the ModelPack Manifest(1x)
    # Find the ModelPack manifest
    modelpack_manifest = None
    modelpack_manifest_digest = None
    for digest, manifest in ocilayout_manifests.items():
        print(manifest.artifactType)
        if manifest.artifactType == modelpack_consts.ARTIFACTTYPEMODELMANIFEST:
            modelpack_manifest = manifest
            modelpack_manifest_digest = digest
            break
    assert modelpack_manifest is not None, "No manifest with artifactType == modelpack_consts.ARTIFACTTYPEMODELMANIFEST found"
    assert modelpack_manifest.config.mediaType == modelpack_consts.MEDIATYPEMODELCONFIG
    assert len(modelpack_manifest.layers) == 3
    # Check that there is a manifest entry in ocilayout_root_index.manifests with the correct annotation and digest
    for manifest_entry in ocilayout_root_index.manifests:
        if manifest_entry.annotations and manifest_entry.annotations.get("io.opendatahub.modelcar.manifest.type") == "modelpack":
            assert manifest_entry.digest.removeprefix("sha256:") == modelpack_manifest_digest
    # Check that there is a manifest entry in ocilayout_indexes.manifests with the correct annotation and digest
    for idx in ocilayout_indexes.values():
        for m in idx.manifests:
            if m.annotations and m.annotations.get("io.opendatahub.modelcar.manifest.type") == "modelpack":
                assert m.digest.removeprefix("sha256:") == modelpack_manifest_digest


def test_add_modelpack_manifest_using_ocilayout5(tmp_path: Path):
    """attempt to add modelpack manifest to oci-layout, using ocilayout5 as the base oci-layout
    which is a single-arch oci-layout, hence, should fail.
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout5"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout, copy_function=shutil.copy2)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model, copy_function=shutil.copy2)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    ocilayout_root_index = read_ocilayout_root_index(target_ocilayout)
    assert len(ocilayout_root_index.manifests) == 1
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    assert len(ocilayout_indexes) == 0
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 1

    # attempt to add modelpack manifest
    with pytest.raises(ValueError, match="Can't add a ModelPack manifest to a single-arch oci-layout"):
        oci_layers_on_top(target_ocilayout, models, modelcard, add_modelpack=True)


def test_modelcard_in_model_files_and_remove_originals(tmp_path: Path, caplog):
    """put oci_layers_on_top under test with 'remove' option and modelcard in model_files
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout2"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout, copy_function=shutil.copy2)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model, copy_function=shutil.copy2)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md",
        target_model / ".." / "models"/ "README.md", # tricky just to account for malicious use or edge-cases too (in ModelCar each layer is a single file typically just under container /models/<file>, no sub-directory nesting)
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    print("checking for simple warning:")
    # Set log level to capture warnings
    caplog.set_level(logging.WARNING)
    oci_layers_on_top(target_ocilayout, models, modelcard)
    assert "ModelCard detected in model_files, this will result in duplicated layers for the ModelCard (negligible, but not optimal)." in caplog.text

    print("checking for remove_originals=RemoveOriginals.DEFAULT")
    with pytest.raises(ValueError, match="ModelCard detected in model_files, while remove_originals flag is set; this is not allowed as it would remove the original ModelCard before having a chance of adding it as its proper layer."):
        oci_layers_on_top(target_ocilayout, models, modelcard, remove_originals=RemoveOriginals.DEFAULT)

    print("checking for remove_originals=RemoveOriginals.ALL")
    with pytest.raises(ValueError, match="ModelCard detected in model_files, while remove_originals flag is set; this is not allowed as it would remove the original ModelCard before having a chance of adding it as its proper layer."):
        oci_layers_on_top(target_ocilayout, models, modelcard, remove_originals=RemoveOriginals.ALL)


def test_add_labels_and_annotations(tmp_path: Path):
    """Test adding labels and annotations to the OCI Image Config and the OCI Image Manifest
    """
    test_sample_model = sample_model_path()
    test_ocilayout2 = get_test_data_path() / "ocilayout5"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout2, target_ocilayout, copy_function=shutil.copy2)
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model, copy_function=shutil.copy2)
    print(os.listdir(target_model))

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()
    checksum_from_disk0 = get_file_hash(models[0])
    checksum_from_disk1 = get_file_hash(models[1])
    checksum_from_disk2 = get_file_hash(modelcard)

    # typically labels and annotations are the same, but here we test both separately
    oci_layers_on_top(target_ocilayout, models, modelcard, labels={"a": "b"}, annotations={"c": "d"})
    ocilayout_root_index = read_ocilayout_root_index(target_ocilayout)
    assert len(ocilayout_root_index.manifests) == 1
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(target_ocilayout, ocilayout_root_index)
    assert len(ocilayout_indexes) == 0
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(target_ocilayout, ocilayout_indexes, ocilayout_root_index)
    assert len(ocilayout_manifests) == 1
    manifest0: OCIImageManifest = next(iter(ocilayout_manifests.values()))
    assert manifest0.annotations
    assert manifest0.annotations["c"] == "d"
    config_digest = manifest0.config.digest.removeprefix("sha256:")
    with open(target_ocilayout / "blobs" / "sha256" / config_digest, "r") as f:
        mc = OCIManifestConfig.model_validate_json(f.read())
        assert mc.config
        assert mc.config.Labels
        assert mc.config.Labels["a"] == "b"
    assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_TYPE] == "file"
    assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_INLAYERPATH] == "/models/model.joblib"
    assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_DIGEST] == "sha256:"+checksum_from_disk0
    assert manifest0.layers[-2].annotations[ANNOTATION_LAYER_CONTENT_TYPE] == "file"
    assert manifest0.layers[-2].annotations[ANNOTATION_LAYER_CONTENT_INLAYERPATH] == "/models/hello.md"
    assert manifest0.layers[-2].annotations[ANNOTATION_LAYER_CONTENT_DIGEST] == "sha256:"+checksum_from_disk1
    assert manifest0.layers[-1].annotations[ANNOTATION_LAYER_CONTENT_TYPE] == "file"
    assert manifest0.layers[-1].annotations[ANNOTATION_LAYER_CONTENT_INLAYERPATH] == "/models/README.md"
    assert manifest0.layers[-1].annotations[ANNOTATION_LAYER_CONTENT_DIGEST] == "sha256:"+checksum_from_disk2
