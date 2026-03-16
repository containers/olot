# Analysis: ORAS pull and file mtime (modified timestamp)

Original tracker PR: https://github.com/containers/olot/pull/165

## Addressed in Konflux CI/CD

This behaviour has already been addressed in the Konflux CI/CD pipeline via [konflux-ci/build-definitions PR #3358](https://github.com/konflux-ci/build-definitions/pull/3358). Since several ModelCar architectures are produced by different and separate pipeline runs consuming the ORAS-pulled model files, the Konflux task fixes the model files' mtime to a deterministic timestamp after `oras pull`. This ensures that when Olot packages those files into tar layers for the OCI Image KServe ModelCars, the resulting digests are artificially made identical across pipeline runs, effectively achieving layer re-use across architectures.

This workaround at the CI/CD level confirms the problem is real and impactful. The analysis below documents the root cause and upstream status.

## Problem

When ORAS pulls **a file** (blob), the pulled file gets the current system timestamp as its mtime, not the original file's modification time. This means repeated `oras pull` of the same artifact produces files with different mtime values.

Since Olot packages files into tar layers (via `tarball_from_file()` / `targz_from_file()`), and tar archives include the mtime of each entry in the tar header, the resulting layer digest changes even when the file content is identical.

Therefore sourcing content from repeated `oras pull` instead of a single `oras pull`, breaks reproducibility/determinism of the files metadata.

## Demonstration

The test `test_tarball_from_file_oras_pull_nondeterministic` in `tests/utils/files_test.py` demonstrates this:

1. Pull the same OCI artifact twice (with a delay between pulls)
2. Create tarballs from each pulled file
3. The tar digests differ due to different mtime on the pulled files
4. Normalize both files to the same mtime (using `touch -t` with the manifest's `org.opencontainers.image.created` annotation)
5. Re-create tarballs — digests now match

## ORAS project upstream analysis

A search across `oras-project/oras`, `oras-project/oras-go`, and related repositories found no dedicated discussion about preserving file mtime during `oras pull`. The topic has been discussed on the **push side** only.

### Relevant upstream issues and PRs

| Reference | Summary |
|---|---|
| [oras PR #126](https://github.com/oras-project/oras/pull/126) | Proposed stripping file times from tar archives on push. Maintainer (@shizhMSFT) pushed back: *"File times are useful for many scenarios"*. Settled on making it an opt-in flag. |
| [oras #1464](https://github.com/oras-project/oras/issues/1464) (open, milestone v1.4.0) | *"The last modified time (mtime) is included in the archive so the digest of the packed tarball changes even when file content are identical. `oras` CLI should provide a flag to strip out the time info so the packing is deterministic."* |
| [oras-go #712](https://github.com/oras-project/oras-go/issues/712) | Non-deterministic digests due to `org.opencontainers.image.created` annotation timestamp. Solution: allow overriding via `PackManifestOptions`. |
| [oras-go #748](https://github.com/oras-project/oras-go/issues/748) | Document `PackManifestOptions` for reproducible `PackManifest`. |
| [oras-go #886](https://github.com/oras-project/oras-go/issues/886) | File permissions not retained on pull. User @sammy-da noted using custom annotations to record `mode` and `modtime` for individual files as a workaround (not in ORAS per-se out of the box). |
| [oras #1776](https://github.com/oras-project/oras/issues/1776) | Added `--preserve-permissions` flag for pull. No equivalent `--preserve-mtime` flag exists. |

### Key takeaway

- **Directories** are packed as tar archives by ORAS, so mtime from tar headers is preserved through push/pull.
- **Individual files** (blobs) lose their mtime entirely — ORAS stores them as raw blobs with only annotation-based metadata (e.g. `org.opencontainers.image.title` for filename). There is no built-in mechanism or standard annotation for mtime.
- No upstream issue requests mtime restoration on pull for individual file blobs.

## Implications for Olot

When Olot is invoked in separate pipeline runs (as in the Konflux CI/CD scenario, where each architecture gets its own pipeline run), each run performs its own `oras pull`. The non-deterministic mtime from each pull propagates into different tar digests for identical content, preventing layer re-use across architectures.

By contrast, when Olot natively handles the multi-arch builds within a single invocation, layers are naturally re-used across architectures, also because the files share the same mtime.

As demonstrated by the [Konflux workaround](https://github.com/konflux-ci/build-definitions/pull/3358), the current mitigation is to fix file mtime externally (e.g. via `touch -t`) before invoking Olot in separate pipeline runs in Konflux.

Did not consider adding a feature to Olot to "pin the mtime", since the Konflux workaround at least can fix the mtime of the files to the OCI Artifact created time, which is meaningful; the separate invocations of Olot within Konflux *instead* has no access/knowledge of the OCI Artifact, which is the actual source for the content/files of the OCI Image KServe ModelCar.
