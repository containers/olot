# oci layers on top

`olot` is a python-based tool to append layers (files) onto an OCI-compatible image.
It is meant to be used in conjunction with command-line based tools to fetch and upload these images. Tools such as [skopeo](https://github.com/containers/skopeo) or [oras](https://github.com/oras-project/oras).
It leverages standard oci-layout format from the [OCI Image Layout Specification](https://github.com/opencontainers/image-spec/blob/main/image-layout.md).
It can be used either as a CLI tool, or via standard python interface. The package is published to [pypy](https://pypi.org/p/olot).

## Usage

### As a CLI

1. use simple tool like `skopeo` ( or `oras cp`, or ...) and produce an [oci image layout](https://github.com/opencontainers/image-spec/blob/main/image-layout.md) of the _base image_ for the [Modelcar](https://kserve.github.io/website/latest/modelserving/storage/oci/#prepare-an-oci-image-with-model-data) (ie base image could be: A. `ubi-micro`, B. `busybox`, or C. even [simple base image for KServe Modelcar](https://github.com/tarilabs/demo20241108-base?tab=readme-ov-file#a-minimal-base-image-for-kserve-modelcarsidecar-puposes-that-does-nothing), etc.)
2. (this project) use pure python way to add layers of the ML models, and any metadata like ModelCarD
3. use simple tool from step 1 to push the resulting layout to the remote registry (i.e. `simpletool cp ... quay.io/mmortari/model:car`)
4. ... you now have a Modelcar inside of your OCI registry that can be used with KServe and more!

```sh
IMAGE_DIR=download
OCI_REGISTRY_SOURCE=quay.io/mmortari/hello-world-wait:latest
OCI_REGISTRY_DESTINATION=quay.io/mmortari/demo20241208:latest
rm -rf $IMAGE_DIR

# Downloads the image `/quay.io/mmortari/hello-world-wait:latest` to the folder `download` with tag `latest`
skopeo copy --multi-arch all docker://${OCI_REGISTRY_SOURCE} oci:${IMAGE_DIR}:latest

# If using oras, you will need to also need to add write permissions
# oras copy --to-oci-layout $OCI_REGISTRY_SOURCE ./${IMAGE_DIR}:latest
# chmod +w ${IMAGE_DIR}/blobs/sha256/*

# Appends to the image found in `download` the files `model.joblib` and as ModelCarD the `README.md`
poetry run olot $IMAGE_DIR --modelcard tests/data/sample-model/README.md tests/data/sample-model/model.joblib

# Pushes the (updated) image found in `download` folder to the registry `quay.io/mmortari/demo20241208` with tag `latest`
skopeo copy --multi-arch all oci:${IMAGE_DIR}:latest docker://${OCI_REGISTRY_DESTINATION}

# If using oras
# oras cp --from-oci-layout ./${IMAGE_DIR}:latest $OCI_REGISTRY_DESTINATION
```

You can now test the image to validate the files exist in it


```bash
podman run --rm -it $OCI_REGISTRY_DESTINATION ls -la /models/
```

Expected Output:

```sh
Unable to find image 'quay.io/mmortari/demo20241208:latest' locally
latest: Pulling from mmortari/demo20241208
6163eebc9af4: Download complete 
1933e30a3373: Download complete 
3dc1903f1fc8: Download complete 
Digest: sha256:6effaec653c4ba4711c8bda5d18211014016e543e6657eb36ced186fb9aed9e4
Status: Downloaded newer image for quay.io/mmortari/demo20241208:latest
total 20
drwxr-xr-x    1 root     root          4096 Feb 13 15:17 .
drwxr-xr-x    1 root     root          4096 Feb 13 15:17 ..
-rw-rw-r--    1 root     root          6625 Dec 24 09:24 README.md
-rw-rw-r--    1 root     root          3299 Dec 24 09:24 model.joblib
```

Cleanup your local image

```sh
podman image rm quay.io/mmortari/demo20241208:latest
```

### Dev notes

If copying the resulting image to local filesystem oci-layout using skopeo, make sure to enable `--dest-oci-accept-uncompressed-layers` option.

### As a Python Package

Install the package

```sh
pip install olot
# poetry add olot
```

Import and add layers onto a locally available model (using skopeo):

```python
from olot.basic import oci_layers_on_top
from olot.backend.skopeo import skopeo_pull, skopeo_push

model_dir = 'download'
oci_registry_source='quay.io/mmortari/hello-world-wait:latest'
oci_registry_destination='quay.io/mmortari/demo20241208:latest'

model_files = [
    'tests/data/sample-model/model.joblib',
    'tests/data/sample-model/README.md',
]

# Download the model
skopeo_pull(oci_registry_source, model_dir)

# Add the layers
oci_layers_on_top(model_dir, model_files)

# Push the model
skopeo_push(model_dir, oci_registry_destination)
```
