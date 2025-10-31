# Docker Distribution format support

Original tracker issue: https://github.com/containers/olot/issues/119

# Overview

This feature adds comprehensive support for Docker distribution format manifests in Olot, enabling automatic detection of `FROM ...` _base-image_ being Docker distribution manifests, and converting them to OCI format. This ensures compatibility with the current OCI-based workflows in Olot, while maintaining support for legacy Docker distribution format images.

# Key Features

## 1. Docker Distribution Format Detection and Conversion

**New Module**: `olot/dockerdist/convert.py`

This module provides utilities to detect and convert Docker distribution manifests to OCI format:

- **`check_if_oci_layout_contains_docker_manifests()`**: Scans the OCI layout blobs directory to detect if any Docker distribution manifests are present
- **`convert_docker_manifests_to_oci()`**: Converts Docker distribution manifests and list manifests to OCI format
- **`convert_docker_manifest_to_oci()`**: Handles single, individual Image manifest conversion with proper media type mapping

### Supported MediaTypes

The converter handles the following Docker distribution media types:

- Index(/list): `application/vnd.docker.distribution.manifest.list.v2+json` → `application/vnd.oci.image.index.v1+json`
- Image manifest: `application/vnd.docker.distribution.manifest.v2+json` → `application/vnd.oci.image.manifest.v1+json`
- Image Config: `application/vnd.docker.container.image.v1+json` → `application/vnd.oci.image.config.v1+json`
- Image Layer(s): `application/vnd.docker.image.rootfs.diff.tar.gzip` → `application/vnd.oci.image.layer.v1.tar+gzip`

### Conversion Process

1. Scans the `blobs/sha256/` directory for Docker manifests
2. Converts each Docker manifest to OCI format:
   - Updates layer media types from Docker to OCI format
   - Converts config blob media type
   - Recalculates digests for modified config, manifests (layer blobs are unchanged)
   - Creates new blob files with OCI-compliant content
3. Updates list (index) manifests (multi-arch indexes) with new digest references
4. Updates the root `index.json` with new manifest references
5. Logs all conversions for traceability

## 2. Automatic Conversion in Olot Execution Flow

**Modified**: `olot/basics.py`

The main `oci_layers_on_top()` function now automatically detects and converts Docker distribution manifests:

```python
if check_if_oci_layout_contains_docker_manifests(ocilayout):
    logger.warning("OCI layout contains Docker distribution manifests, converting them to OCI format")
    convert_docker_manifests_to_oci(ocilayout)
```

This ensures that any OCI layout containing Docker distribution manifests is automatically converted before processing, providing a seamless user experience.

# Updated Execution Flow

```mermaid
flowchart TD
    A[Input OCI Layout] --> B[Check for Docker Manifests]
    B -->|if found| C[Convert to OCI Format]
    B -->|if not found| D[Update Index References]
    C --> D[Update Index References]
    D --> E[Add Model Layers]
    E --> F[(Optional) Add ModelPack Manifest]
    F --> G[Output OCI Layout]
```

# Validation

The conversion process includes validation at multiple levels:

1. **Media Type Validation**: Ensures all media types are expected values
2. **Digest Recomputation**: Recalculates and validates all digests after conversion
3. **Manifest update**: Create new manifests structure and references

# Testing

## Unit Tests

**New Test Files**:
- `tests/dockerdist/convert_test.py`: Tests for Docker distribution conversion

## Test Data

**New Test Data**:
- `tests/data/dockerdist1/`: Sample Docker distribution format persisted in OCI layout structure (layers blob elided)

## E2E Tests

**Enhanced**: `.github/workflows/e2e.yaml`

Expanded E2E testing with 2 comprehensive test scenarios:

### Scenario 1: Multi-arch Docker distribution format conversion
- Uses `quay.io/mmortari/hello-world-wait:dockerdistribution` as the _base-image_
- Uses [Konflux ORAS copy mechanism](https://github.com/konflux-ci/build-definitions/blob/5bd79d493ca1ba04512c5f6e1f41f427a3c94e03/task/modelcar-oci-ta/0.1/modelcar-oci-ta.yaml#L161-L162) to prepare the input OCI layout
- Performs Olot to build the ModelCar in the OCI layout
- Upload multi-arch ModelCar to the test registry and to the KinD cluster
- Verifies the multi-arch ModelCar with KServe

### Scenario 2: Docker distribution format conversion (single-arch)
- (continuing in the same ci/GHA workflow)
- From `quay.io/mmortari/hello-world-wait:dockerdistribution` detect the SHA of the AMD64 image
- Uses the `quay.io/mmortari/hello-world-wait@sha256:...` as the _base-image_
- Uses [Konflux ORAS copy mechanism](https://github.com/konflux-ci/build-definitions/blob/5bd79d493ca1ba04512c5f6e1f41f427a3c94e03/task/modelcar-oci-ta/0.1/modelcar-oci-ta.yaml#L161-L162) to prepare the input OCI layout
- Performs Olot to build the ModelCar in the OCI layout
- Upload the (single-arch) ModelCar to the test registry and to the KinD cluster
- Verifies the (single-arch) ModelCar with KServe

# Lessons learned on the way

The command `oras copy --to-oci-layout ...` does NOT convert Docker Distribution format into OCI format,
while the command `skopeo copy ...` does implicitly make the conversion from Docker Distribution to OCI format in the OCI layout directory.

# References

- [OCI Image Manifest Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
- [OCI Image Index Specification](https://github.com/opencontainers/image-spec/blob/main/image-index.md)
- [OCI MediaTypes Specification](https://github.com/opencontainers/image-spec/blob/26647a49f642c7d22a1cd3aa0a48e4650a542269/media-types.md?plain=1#L35)
- [Konflux ORAS copy to prepare the base-image](https://github.com/konflux-ci/build-definitions/blob/5bd79d493ca1ba04512c5f6e1f41f427a3c94e03/task/modelcar-oci-ta/0.1/modelcar-oci-ta.yaml#L161-L162)
