

## Dev Notes

```sh
rm -rf download && skopeo copy --multi-arch all docker://quay.io/mmortari/hello-world-wait:latest oci:download:latest

# oras copy --to-oci-layout quay.io/mmortari/hello-world-wait:latest ./download:latest
# chmod +w download/blobs/sha256/*

poetry run olot download tests/data/model.joblib README.md

skopeo copy --multi-arch all oci:download:latest docker://quay.io/mmortari/demo20241208:latest
```

demo

```
podman run -it quay.io/mmortari/demo20241208 /bin/sh
/ # ls -la /models/
total 8
drwxr-xr-x    1 root     root            23 Dec  8 21:41 .
dr-xr-xr-x    1 root     root            63 Dec  8 21:42 ..
-rw-r--r--    1 501      20             389 Dec  8 21:34 README.md
-rw-r--r--    1 501      20            3299 Dec  8 15:37 model.joblib
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
