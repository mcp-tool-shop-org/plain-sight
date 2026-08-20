"""
Sidecar + template helpers — the training-data contract, pure stdlib.

These functions define the caption-file conventions plain-sight guarantees:

  - EXACT basename pairing: ``img_0042.png`` → ``img_0042.txt`` (no counter
    suffix — this is the local advantage over the Comfy Cloud SaveText node,
    which appends ``_00001``).
  - BARE concatenation: ``prefix + caption + suffix`` with no injected
    delimiter (mirrors the verified cloud graph: delimiter=""). If you want
    ``"trigger, caption"``, put the comma-space in the prefix yourself.

Kept free of torch/PIL imports so the contract is testable without a model.
"""

from pathlib import Path

# Extensions treated as images when expanding directories.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def compose_caption(prefix: str, caption: str, suffix: str) -> str:
    """Bare concatenation — no delimiter is ever injected."""
    return f"{prefix}{caption}{suffix}"


def sidecar_path_for(image_path: str | Path, out_dir: str | Path | None = None) -> Path:
    """The ``.txt`` sidecar path for an image: same stem, ``.txt`` extension.

    With ``out_dir`` the sidecar lands there (created by the writer, not
    here); otherwise it sits next to the image.
    """
    image = Path(image_path)
    name = image.stem + ".txt"
    if out_dir is not None:
        return Path(out_dir) / name
    return image.with_name(name)


def iter_image_files(paths: list[str | Path]) -> list[Path]:
    """Expand a mixed list of files and directories into a sorted image list.

    Files are passed through regardless of extension (the caller asked for
    them explicitly). Directories are scanned non-recursively for
    ``IMAGE_EXTS`` files. A missing path raises ``FileNotFoundError`` —
    silently skipping typo'd inputs would corrupt dataset runs.
    """
    if not paths:
        raise ValueError("At least one file or directory is required")
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(
                child
                for child in sorted(p.iterdir())
                if child.is_file() and child.suffix.lower() in IMAGE_EXTS
            )
        else:
            raise FileNotFoundError(f"Path not found: {raw}")
    return out
