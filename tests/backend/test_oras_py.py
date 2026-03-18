import os
import shutil
import subprocess
import time
import docker # type: ignore
from pathlib import Path
import pytest
from olot.backend.oras_py import is_oras_py, oras_py_pull, oras_py_push
from olot.basics import oci_layers_on_top
from olot.oci.oci_image_layout import verify_ocilayout
from olot.oci.oci_image_index import read_ocilayout_root_index
from tests.common import sample_model_path

@pytest.mark.e2e_oras_py
def test_is_oras_py():
    assert is_oras_py()


@pytest.mark.e2e_oras_py
def test_oras_py_pull(tmp_path):
    """Test oras-py to pull/dl a known base-image to an oci-layout
    """
    oras_py_pull("quay.io/mmortari/hello-world-wait:latest", tmp_path)

    assert verify_ocilayout(tmp_path)

    mut = read_ocilayout_root_index(tmp_path)
    assert mut.schemaVersion == 2


@pytest.mark.e2e_oras_py
def test_oras_py_scenario(tmp_path):
    """Test oras-py with an end-to-end scenario
    """
    oras_py_pull("quay.io/mmortari/hello-world-wait:latest", tmp_path)

    model_joblib = Path(__file__).parent / ".." / "data" / "sample-model" / "model.joblib"
    hello_md = Path(__file__).parent / ".." / "data" / "sample-model" / "hello.md"
    model_files = [
        model_joblib,
        hello_md,
    ]

    oci_layers_on_top(tmp_path, model_files)
    oras_py_push(tmp_path, "localhost:5001/nstestorg/modelcar:latest", insecure=True)

    # show what has been copied in Container Registry
    subprocess.run(["skopeo","list-tags","--tls-verify=false","docker://localhost:5001/nstestorg/modelcar"], check=True)

    # pull from Container Registry using Docker client for local running the modelcar as-is
    client = docker.from_env()
    client.images.pull("localhost:5001/nstestorg/modelcar", tag="latest")
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


@pytest.mark.e2e_oras_py
def test_oras_py_scenario_modelcard(tmp_path):
    """Test oras-py with an end-to-end scenario with modelcard as separate layer
    """
    oras_py_pull("quay.io/mmortari/hello-world-wait:latest", tmp_path)

    model_joblib = Path(__file__).parent / ".." / "data" / "sample-model" / "model.joblib"
    modelcard = Path(__file__).parent / ".." / "data" / "sample-model" / "README.md"
    hello_md = Path(__file__).parent / ".." / "data" / "sample-model" / "hello.md"
    model_files = [
        model_joblib,
        hello_md,
    ]

    oci_layers_on_top(tmp_path, model_files, modelcard)
    oras_py_push(tmp_path, "localhost:5001/nstestorg/modelcar:latest", insecure=True)

    # show what has been copied in Container Registry
    subprocess.run(["skopeo","list-tags","--tls-verify=false","docker://localhost:5001/nstestorg/modelcar"], check=True)

    # pull from Container Registry using Docker client for local running the modelcar as-is
    client = docker.from_env()
    client.images.pull("localhost:5001/nstestorg/modelcar", tag="latest")
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


@pytest.mark.e2e_oras_py
def test_oras_py_with_docker_attestated_base_image(tmp_path):
    """Test oras-py with an end-to-end scenario for docker image with docker vendor specific attestation format
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

    oras_py_pull("docker.io/library/busybox:latest", target_ocilayout)

    oci_layers_on_top(target_ocilayout, models, modelcard)
