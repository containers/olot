#!/usr/bin/env python3
import argparse
import shutil
import tempfile
from pathlib import Path

from olot.backend.oras_py import oras_py_pull, oras_py_push
from olot.basics import oci_layers_on_top


def main():
    parser = argparse.ArgumentParser(description="Create a modelcar and push to a registry using oras-py.")
    parser.add_argument("model_dir", type=Path, help="Local directory containing model files")
    parser.add_argument("--base-image", default="quay.io/mmortari/hello-world-wait:latest", help="Base OCI image reference (default: quay.io/mmortari/hello-world-wait:latest)")
    parser.add_argument("dest", help="Destination OCI image reference (e.g. quay.io/yourns/modelcar:latest)")
    parser.add_argument("--insecure", action="store_true", help="Use HTTP instead of HTTPS")
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    if not model_dir.is_dir():
        parser.error(f"Model directory does not exist: {model_dir}")

    # Collect model files, using README.md as the modelcard if present
    all_files = [f for f in model_dir.rglob("*") if f.is_file() and ".git" not in f.parts]
    readme = model_dir / "README.md"
    modelcard = readme if readme.exists() else None
    model_files = [f for f in all_files if f != modelcard]

    work_dir = Path(tempfile.mkdtemp())
    try:
        layout_dir = work_dir / "layout"

        print(f"Pulling base image {args.base_image} ...")
        oras_py_pull(args.base_image, layout_dir, insecure=args.insecure)

        print(f"Adding {len(model_files)} model files as layers:")
        if modelcard:
            print(f"  modelcard: {modelcard.relative_to(model_dir)}")
        for f in model_files:
            print(f"  {f.relative_to(model_dir)}")
        oci_layers_on_top(layout_dir, model_files, modelcard)

        print(f"Pushing to {args.dest} ...")
        oras_py_push(layout_dir, args.dest, insecure=args.insecure)
        print("Done.")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
