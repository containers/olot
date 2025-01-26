# oci layers on top

1. use simple tool like `skopeo` ( or `oras cp`, or ...) and produce an [oci image layout](https://github.com/opencontainers/image-spec/blob/main/image-layout.md) of the _base image_ for the [Modelcar](https://kserve.github.io/website/latest/modelserving/storage/oci/#prepare-an-oci-image-with-model-data) (ie base image could be: A. `ubi-micro`, B. `busybox`, or C. even [simple base image for KServe Modelcar](https://github.com/tarilabs/demo20241108-base?tab=readme-ov-file#a-minimal-base-image-for-kserve-modelcarsidecar-puposes-that-does-nothing), etc.)
2. (this project) use pure python way to add layers of the ML models, and any metadata like ModelCarD
3. use simple tool from step 1 to push the resulting layout to the remote registry (i.e. `simpletool cp ... quay.io/mmortari/model:car`)
4. ... you now have a Modelcar inside of your OCI registry that can be used with KServe and more!

## Dev Notes

```sh
rm -rf download && skopeo copy --multi-arch all docker://quay.io/mmortari/hello-world-wait:latest oci:download:latest

# oras copy --to-oci-layout quay.io/mmortari/hello-world-wait:latest ./download:latest
# chmod +w download/blobs/sha256/*

poetry run olot download tests/data/sample-model/model.joblib tests/data/sample-model/README.md

skopeo copy --multi-arch all oci:download:latest docker://quay.io/mmortari/demo20241208:latest
```

demo

```
podman run --rm -it quay.io/mmortari/demo20241208 /bin/sh
Trying to pull quay.io/mmortari/demo20241208:latest...
Getting image source signatures
Copying blob sha256:6163eebc9af40cdf3451c0de779eccf4a919d56cd3dd22b57bbcaafb5b07d349
Copying blob sha256:1933e30a3373776d5c7155591a6dacbc205cf6a2665b6dced682c6d2ea7b000f
Copying blob sha256:3dc1903f1fc892d372d30bc05ed7c01dd6aceff05a1917eb2fc5618bfd6ef350
Copying config sha256:37ac52c72d78301fce323e652c00326faee7975837f291acef2ce56a262fc53d
Writing manifest to image destination
/ # ls -la /models/
total 12
drwxr-xr-x    1 root     root            23 Jan 23 16:40 .
dr-xr-xr-x    1 root     root            63 Jan 23 16:40 ..
-rw-rw-r--    1 root     root          6625 Dec 24 09:24 README.md
-rw-rw-r--    1 root     root          3299 Dec 24 09:24 model.joblib
```

or even

```sh
oras cp --from-oci-layout ./download:latest quay.io/mmortari/demo20241208:latest
```

demo

```
podman run --rm -it quay.io/mmortari/demo20241208 /bin/sh
Trying to pull quay.io/mmortari/demo20241208:latest...
Getting image source signatures
Copying blob sha256:a29b139a2e0d0eb615fd1e2d51475834a404f1e2f440784079c7184bdc241289
Copying blob sha256:1933e30a3373776d5c7155591a6dacbc205cf6a2665b6dced682c6d2ea7b000f
Copying blob sha256:3afebe9995515e0bd99890d996ad1aa6340cb9f0f125185011e90882d14b5431
Copying config sha256:f445c8c153c95885e059a66366922c7d5173da0b5c4ceef6f61f005b58b4a0c1
Writing manifest to image destination
/ # ls -la /models
total 8
drwxr-xr-x    1 root     root            23 Dec  8 21:56 .
dr-xr-xr-x    1 root     root            63 Dec  8 21:56 ..
-rw-r--r--    1 501      20             389 Dec  8 21:34 README.md
-rw-r--r--    1 501      20            3299 Dec  8 15:37 model.joblib
/ # exit
```

```sh
podman image rm quay.io/mmortari/demo20241208:latest
```
