import os
import shutil
import subprocess
import time
import docker # type: ignore
from pathlib import Path
import pytest
from olot.backend.skopeo import is_skopeo, skopeo_pull, skopeo_push, skopeo_inspect
from olot.basics import oci_layers_on_top
from olot.oci.oci_image_layout import verify_ocilayout
from olot.oci.oci_image_index import read_ocilayout_root_index
from tests.common import get_test_data_path, sample_model_path

@pytest.mark.e2e_skopeo
def test_is_skopeo():
    assert is_skopeo()


@pytest.mark.e2e_skopeo
def test_skopeo_pull(tmp_path):
    """Test skopeo to pull/dl a known base-image to an oci-layout
    """
    skopeo_pull("quay.io/mmortari/hello-world-wait", tmp_path)

    assert verify_ocilayout(tmp_path)

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

    model_joblib = Path(__file__).parent / ".." / "data" / "sample-model" / "model.joblib"
    hello_md = Path(__file__).parent / ".." / "data" / "sample-model" / "hello.md"
    model_files = [
        model_joblib,
        hello_md,
    ]

    oci_layers_on_top(tmp_path, model_files)
    skopeo_push(tmp_path, "localhost:5001/nstestorg/modelcar", ["--dest-tls-verify=false"])

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
    container = client.containers.run("localhost:5001/nstestorg/modelcar", detach=True, remove=True)
    print(container.logs())
    _, stat = container.get_archive('/models/model.joblib')
    print(str(stat["size"]))
    # assert the model.joblib from the KServe modelcar is in expected location (above) and expected size
    assert stat["size"] == os.stat(model_joblib).st_size
    container.kill()
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            if client.containers.get(container.id):
                container.kill()
                time.sleep(2**attempt)
            else:
                break
        except docker.errors.NotFound:
            print("test container terminated")
            break
        except Exception as e:
            print(f"Attempt to terminate {attempt + 1} failed: {e}")
        attempt += 1
    if attempt == max_attempts:
        print("Was unable to terminate the test container")
    client.images.remove("localhost:5001/nstestorg/modelcar")


@pytest.mark.e2e_skopeo
def test_skopeo_scenario_modelcard(tmp_path):
    """Test skopeo with an end-to-end scenario with modelcard as separate layer
    """
    skopeo_pull("quay.io/mmortari/hello-world-wait", tmp_path)

    model_joblib = Path(__file__).parent / ".." / "data" / "sample-model" / "model.joblib"
    modelcard = Path(__file__).parent / ".." / "data" / "sample-model" / "README.md"
    hello_md = Path(__file__).parent / ".." / "data" / "sample-model" / "hello.md"
    model_files = [
        model_joblib,
        hello_md,
    ]

    oci_layers_on_top(tmp_path, model_files, modelcard)
    skopeo_push(tmp_path, "localhost:5001/nstestorg/modelcar", ["--dest-tls-verify=false"])

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
    container = client.containers.run("localhost:5001/nstestorg/modelcar", detach=True, remove=True)
    print(container.logs())

    _, stat = container.get_archive('/models/model.joblib')
    print(str(stat["size"]))
    # assert the model.joblib from the KServe modelcar is in expected location (above) and expected size
    assert stat["size"] == os.stat(model_joblib).st_size

    # assert the README.md modelcard is in expected location and expected size
    _, stat = container.get_archive('/models/README.md')
    print(str(stat["size"]))
    assert stat["size"] == os.stat(modelcard).st_size

    container.kill()
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            if client.containers.get(container.id):
                container.kill()
                time.sleep(2**attempt)
            else:
                break
        except docker.errors.NotFound:
            print("test container terminated")
            break
        except Exception as e:
            print(f"Attempt to terminate {attempt + 1} failed: {e}")
        attempt += 1
    if attempt == max_attempts:
        print("Was unable to terminate the test container")
    client.images.remove("localhost:5001/nstestorg/modelcar")


@pytest.mark.e2e_skopeo
def test_skopeo_with_docker_attestated_base_image(tmp_path):
    """Test skopeo with an end-to-end scenario for docker image with docker vendor specific attestation format
    """
    test_sample_model = sample_model_path()
    target_model = tmp_path / "models"
    shutil.copytree(test_sample_model, target_model)
    print(os.listdir(target_model))
    target_ocilayout = tmp_path / "myocilayout"

    models = [
        target_model / "model.joblib",
        target_model / "hello.md"
    ]
    for model in models:
        assert model.exists()
    modelcard = target_model / "README.md"
    assert modelcard.exists()

    skopeo_pull("busybox", target_ocilayout)

    oci_layers_on_top(target_ocilayout, models, modelcard)


@pytest.mark.e2e_skopeo
def test_skopeo_inspect():
    data_path = str(get_test_data_path().absolute())
    result = skopeo_inspect("oci:"+data_path+"/ocilayout2:latest")
    assert result
    assert len(result) == 491
    result = skopeo_inspect("oci:"+data_path+"/ocilayout3:latest")
    assert result
    assert len(result) == 491
    result = skopeo_inspect("oci:"+data_path+"/ocilayout4:latest")
    assert result
    assert len(result) == 1077
    result = skopeo_inspect("oci:"+data_path+"/ocilayout5:latest")
    assert result
    assert len(result) == 731
