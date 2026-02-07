# Layer Content Annotations

## Overview

This feature adds layer annotations to track metadata about the original files packaged into OCI layers. This enables traceability from OCI layers back to the original input files and provides integrity verification for model files without extracting the layers.

## Layer Annotations

Olot automatically adds four annotations to each layer in the OCI manifest:

### `olot.layer.content.digest`

The SHA256 hash of the original input file before being packaged into a tar/gzip layer.

- **Type**: String (SHA256 digest with `sha256:` prefix)
- **When populated**: Only for file inputs (empty for directory inputs)
- **Purpose**: Enables verification of the original file's integrity without extracting the layer

Example: `"olot.layer.content.digest": "sha256:abc123..."`

### `olot.layer.content.type`

Indicates whether the layer was created from a file or a directory.

- **Type**: String enum
- **Values**: `"file"` or `"directory"`
- **Always populated**: Yes

Example: `"olot.layer.content.type": "file"`

### `olot.layer.content.inlayerpath`

The full path where the content will appear in the container filesystem (e.g. default path of OCI Image KServe's ModelCar `/models/<filename>`).

- **Type**: String (absolute path)
- **Always populated**: Yes
- **Format**: Typically `/models/<filename>` for model files

Example: `"olot.layer.content.inlayerpath": "/models/model.joblib"`

### `olot.layer.content.name`

The original filename (path.name) of the input file or directory.

- **Type**: String (filename)
- **Always populated**: Yes
- **Purpose**: Provides the original file or directory name, simplifying traceability and model signing workflows (e.g., TAS/Konflux use-cases)

Example: `"olot.layer.content.name": "model.joblib"`

## Example Manifest Layer

Here's how these annotations appear in an OCI image manifest:

```json
{
  "mediaType": "application/vnd.oci.image.layer.v1.tar",
  "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size": 12345,
  "annotations": {
    "olot.layer.content.digest": "sha256:d91aa8aa7b56706b89e4a9aa27d57f45785082ba40e8a67e58ede1ed5709afd8",
    "olot.layer.content.type": "file",
    "olot.layer.content.inlayerpath": "/models/model.joblib",
    "olot.layer.content.name": "model.joblib"
  }
}
```

**Key Points**:
- The layer's `digest` is the hash of the compressed tar.gz layer
- The `olot.layer.content.digest` is the hash of the **original file** before packaging
- These are different values, allowing verification at both levels

## Implementation Details

### Original File Hashing

**New Class**: `HashingFileReader` in `olot/utils/files.py`

This class computes the SHA256 hash of a file while reading it, enabling efficient hash computation during the tar creation process without requiring multiple file reads.
This is consistent with current Olot principles that avoid writing files multiple times, etc.

### Annotation Attachment

**Modified**: `olot/basics.py`

The `oci_layers_on_top()` function automatically attaches the four annotations when creating layer descriptors:

```python
if new_layer.input_hash:
    la[ANNOTATION_LAYER_CONTENT_DIGEST] = "sha256:"+new_layer.input_hash
la[ANNOTATION_LAYER_CONTENT_TYPE] = new_layer.input_type
la[ANNOTATION_LAYER_CONTENT_INLAYERPATH] = new_layer.in_layer_path
la[ANNOTATION_LAYER_CONTENT_NAME] = new_layer.title
```

Note that `olot.layer.content.digest` is only added if the input was a file (not a directory).

### Enhanced Layer Statistics

**Modified**: `LayerStats` dataclass in `olot/utils/files.py`

The layer creation functions (`tarball_from_file()` and `targz_from_file()`) now track:
- `input_hash`: SHA256 of the original file (not available for directories)
- `input_type`: Either `LayerInputType.FILE` or `LayerInputType.DIRECTORY`
- `in_layer_path`: The arcname used in the tar (e.g., `/models/model.joblib`)

## Use Cases

### Integrity Verification
Support _verification_ that the original file used to build a layer hasn't been tampered with by comparing the stored `olot.layer.content.digest` with a hash of the original file, without needing to extract the layer.

### Traceability
Support tracking exactly which files went into each layer of a ModelCar, enabling audit trails and provenance tracking for ML models.

### Debugging
Quickly understand better what files are in each layer by examining the annotations, without extracting tar/tar.gz layers.

### Provenance
Document the exact file hashes that were used in model builds, _supporting_ reproducibility and compliance requirements.

## Testing

### Unit Tests
**File**: `tests/utils/files_test.py`

Tests for:
- `HashingFileReader` class functionality
- Hash computation during tar/targz creation
- Correct population of `input_hash` in `LayerStats`

### Integration Tests
**File**: `tests/basic_test.py`

End-to-end test (`test_add_labels_and_annotations`) that:
1. Run Olot as usual, to create layers from actual model files
2. Builds an OCI layout with annotations
3. Verifies all four annotations appear correctly in the manifest
4. Validates that the digests match the original files

Example assertions from the test:
```python
assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_TYPE] == "file"
assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_INLAYERPATH] == "/models/model.joblib"
assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_DIGEST] == "sha256:"+checksum_from_disk0
assert manifest0.layers[-3].annotations[ANNOTATION_LAYER_CONTENT_NAME] == "model.joblib"
```

## References

- [OCI Image Manifest Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
- [OCI Annotations](https://github.com/opencontainers/image-spec/blob/main/annotations.md)
- [OCI Descriptor](https://github.com/opencontainers/image-spec/blob/main/descriptor.md#properties)
