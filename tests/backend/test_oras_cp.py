import os
import subprocess
import time
import docker # type: ignore
from pathlib import Path
import pytest
from olot.backend.oras_cp import is_oras, oras_pull, oras_push
from olot.basics import check_ocilayout, oci_layers_on_top, read_ocilayout_root_index

@pytest.mark.e2e_oras
def test_is_oras():
    assert is_oras()


@pytest.mark.e2e_oras
def test_oras_pull(tmp_path):
    """Test oras to pull/dl a known base-image to an oci-layout
    """
    oras_pull("quay.io/mmortari/hello-world-wait:latest", tmp_path)

    assert check_ocilayout(tmp_path)

    mut = read_ocilayout_root_index(tmp_path)
    assert mut.schemaVersion == 2
    assert len(mut.manifests) == 3
    manifest0 = mut.manifests[0]
    assert manifest0.mediaType == "application/vnd.oci.image.index.v1+json"
    assert manifest0.digest == "sha256:d437889e826ecce2116ac711469bd09b1bb3c64d45055cbf23a6f8f3db223b8b"
    assert manifest0.size == 491


@pytest.mark.e2e_oras
def test_oras_scenario(tmp_path):
    """Test oras with an end-to-end scenario
    """
    oras_pull("quay.io/mmortari/hello-world-wait:latest", tmp_path)
    model_joblib = Path(__file__).parent / ".." / "data" / "model.joblib"
    model_files = [
        model_joblib,
        Path(__file__).parent / ".." / "data" / "hello.md",
    ]
    oci_layers_on_top(tmp_path, model_files)
    oras_push(tmp_path, "localhost:5001/nstestorg/modelcar:latest")

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


@pytest.mark.e2e_oras
def test_oras_scenario_modelcard(tmp_path):
    """Test oras with an end-to-end scenario with modelcard as separate layer
    """
    oras_pull("quay.io/mmortari/hello-world-wait:latest", tmp_path)
    model_joblib = Path(__file__).parent / ".." / "data" / "model.joblib"
    model_files = [
        model_joblib,
        Path(__file__).parent / ".." / "data" / "hello.md",
    ]
    modelcard = Path(__file__).parent / ".." / "data" / "README.md"
    oci_layers_on_top(tmp_path, model_files, modelcard)
    oras_push(tmp_path, "localhost:5001/nstestorg/modelcar:latest")

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
