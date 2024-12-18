import os
import subprocess
import docker # type: ignore
from pathlib import Path
import pytest
from olot.backend.skopeo import is_skopeo, skopeo_pull, skopeo_push
from olot.basics import check_ocilayout, oci_layers_on_top, read_ocilayout_root_index

@pytest.mark.e2e_skopeo
def test_is_skopeo():
    assert is_skopeo()


@pytest.mark.e2e_skopeo
def test_skopeo_pull(tmp_path):
    """Test skopeo to pull/dl a known base-image to an oci-layout
    """
    skopeo_pull("quay.io/mmortari/hello-world-wait", tmp_path)

    assert check_ocilayout(tmp_path)

    mut = read_ocilayout_root_index(tmp_path)
    assert mut.schemaVersion == 2
    assert len(mut.manifests) == 1
    manifest0 = mut.manifests[0]
    assert manifest0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert manifest0.digest == "sha256:d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    assert manifest0.size == 491


@pytest.mark.e2e_skopeo
def test_skopeo_scenario(tmp_path):
    """Test skopeo with an end-to-end scenario
    """
    skopeo_pull("quay.io/mmortari/hello-world-wait", tmp_path)
    model_joblib = Path(__file__).parent / ".." / "data" / "model.joblib"
    model_files = [
        model_joblib,
        Path(__file__).parent / ".." / "data" / "hello.md",
    ]
    oci_layers_on_top(tmp_path, model_files)
    skopeo_push(tmp_path, "localhost:5001/nstestorg/modelcar")

    # show what has been copied in Container Registry
    subprocess.run(["skopeo","list-tags","--tls-verify=false","docker://localhost:5001/nstestorg/modelcar"], check=True)

    # copy from Container Registry to Docker daemon for local running the modelcar as-is
    result = subprocess.run("skopeo inspect --tls-verify=false --raw docker://localhost:5001/nstestorg/modelcar | jq -r '.manifests[] | select(.platform.architecture == \"amd64\") | .digest'", shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0
    digest = result.stdout.strip()
    print(digest)
    # use by convention the linux/amd64
    subprocess.run(["skopeo", "copy", "--src-tls-verify=false", f"docker://localhost:5001/nstestorg/modelcar@{digest}", "docker-daemon:localhost:5001/nstestorg/modelcar:latest"], check=True)
    client = docker.from_env()
    container = client.containers.run("localhost:5001/nstestorg/modelcar", detach=True)
    print(container.logs())
    _, stat = container.get_archive('/models/model.joblib')
    print(str(stat["size"]))
    # assert the model.joblib from the KServe modelcar is in expected location (above) and expected size
    assert stat["size"] == os.stat(model_joblib).st_size
