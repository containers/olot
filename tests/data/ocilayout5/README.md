example only manifests (not layer tarballs) with: `oras copy --platform linux/arm64 --to-oci-layout quay.io/mmortari/hello-world-wait:latest ./tests/data/ocilayout5:latest`

Q: "why you didn't use skopeo for this case?"
A: cannot supply a specific platform
