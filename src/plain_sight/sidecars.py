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

import json
import os
from datetime import datetime, timezone
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


def sidecar_is_complete(path: str | Path) -> bool:
    """True only when the sidecar exists and has at least one byte.

    Empty files are leftover from a failed write, not finished captions.
    """
    p = Path(path)
    try:
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False


def write_sidecar_atomic(path: str | Path, text: str) -> None:
    """Write ``text`` to ``path`` via a same-directory temp + ``os.replace``.

    The final path is never a partial file: interrupt or OSError during the
    temp write leaves the destination untouched and the temp discarded.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, dest)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def manifest_collides_with_sidecars(
    manifest_path: str | Path,
    images: list[str | Path],
    out_dir: str | Path | None = None,
) -> Path | None:
    """Return the sidecar path that equals ``manifest_path``, else None."""
    target = Path(manifest_path).resolve()
    for raw in images:
        sidecar = sidecar_path_for(raw, out_dir).resolve()
        if sidecar == target:
            return sidecar
    return None


def write_batch_manifest(path: str | Path, payload: dict) -> None:
    """Write a JSON provenance record atomically. Not a ``.txt`` sidecar.

    Injects ``created_at`` (UTC ISO-8601) if the caller omitted it. That
    timestamp means two runs of the same batch are not byte-identical —
    the captions are; the provenance record is not.
    """
    body = dict(payload)
    body.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    write_sidecar_atomic(path, json.dumps(body, indent=2, default=str) + "\n")


def find_sidecar_collisions(
    images: list[str | Path],
    out_dir: str | Path | None = None,
) -> dict[Path, list[Path]]:
    """Map each contested sidecar path to the images competing for it.

    Only genuinely contested paths appear — a sidecar claimed by exactly one
    image is not in the result. An empty dict means the batch is safe to write.
    """
    groups: dict[Path, list[Path]] = {}
    for raw in images:
        image = Path(raw)
        sidecar = sidecar_path_for(image, out_dir)
        groups.setdefault(sidecar, []).append(image)
    return {path: claimants for path, claimants in groups.items() if len(claimants) > 1}


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
