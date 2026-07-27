import shutil
import tarfile
from pathlib import Path

from click.testing import CliRunner

from olot.cli import cli
from tests.common import get_test_data_path


def test_cli_root_dir_preserves_nested_paths(tmp_path: Path):
    """--root-dir should preserve subdirectory structure for CLI invocations,
    so files with the same basename in different subdirectories don't collide
    (e.g. config.json at the model root vs. inference/config.json).
    """
    test_ocilayout5 = get_test_data_path() / "ocilayout5"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout5, target_ocilayout)

    model_dir = tmp_path / "my-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text('{"top": true}')
    inference_dir = model_dir / "inference"
    inference_dir.mkdir()
    (inference_dir / "config.json").write_text('{"inference_only": true}')

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root-dir", str(model_dir),
            str(target_ocilayout),
            str(model_dir / "config.json"),
            str(inference_dir / "config.json"),
        ],
    )
    assert result.exit_code == 0, result.output

    all_archive_paths: list[str] = []
    blobs_dir = target_ocilayout / "blobs" / "sha256"
    for blob in blobs_dir.iterdir():
        try:
            with tarfile.open(str(blob), "r") as tar:
                all_archive_paths.extend(m.name for m in tar.getmembers() if not m.isdir())
        except tarfile.ReadError:
            continue

    assert "models/config.json" in all_archive_paths
    assert "models/inference/config.json" in all_archive_paths


def test_cli_without_root_dir_flattens_paths(tmp_path: Path):
    """Without --root-dir, the CLI keeps its existing flat behavior: only the
    file's basename is used, so same-named files in different directories
    collide on the same archive path.
    """
    test_ocilayout5 = get_test_data_path() / "ocilayout5"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_ocilayout5, target_ocilayout)

    model_dir = tmp_path / "my-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text('{"top": true}')
    inference_dir = model_dir / "inference"
    inference_dir.mkdir()
    (inference_dir / "config.json").write_text('{"inference_only": true}')

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(target_ocilayout),
            str(model_dir / "config.json"),
            str(inference_dir / "config.json"),
        ],
    )
    assert result.exit_code == 0, result.output

    all_archive_paths: list[str] = []
    blobs_dir = target_ocilayout / "blobs" / "sha256"
    for blob in blobs_dir.iterdir():
        try:
            with tarfile.open(str(blob), "r") as tar:
                all_archive_paths.extend(m.name for m in tar.getmembers() if not m.isdir())
        except tarfile.ReadError:
            continue

    assert all_archive_paths.count("models/config.json") == 2
