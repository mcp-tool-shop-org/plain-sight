"""
plain-sight MCP server — generative image describer.

Exposes Florence-2 as MCP tools: an AI says what it sees. The complement to
ai-eyes-mcp — plain-sight NARRATES (prose, OCR, dataset captions), ai-eyes
MEASURES (scores). Descriptions are generative and can hallucinate detail;
for verifying a specific claim, use a discriminative tool.

Tools:
  describe_image   — one image → prose description (3 detail tiers)
  describe_batch   — N images → .txt caption sidecars (dataset lane)
  read_text        — OCR: extract visible text from an image
  sight_status     — health check (does not trigger model load)
  sight_selftest   — describe bundled reference images, sanity-check output
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from plain_sight.engine import (
    Florence2Engine,
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    DEFAULT_CACHE_DIR,
    DEFAULT_DEVICE,
    DEFAULT_DTYPE,
    DEFAULT_MAX_NEW_TOKENS,
    DETAIL_TASKS,
    configure_logging,
)
from plain_sight.sidecars import (
    compose_caption,
    find_sidecar_collisions,
    manifest_collides_with_sidecars,
    sidecar_is_complete,
    sidecar_path_for,
    write_batch_manifest,
    write_sidecar_atomic,
)

logger = logging.getLogger("plain_sight")

# Logs go to STDERR only: STDOUT is the MCP STDIO protocol channel and must
# never be polluted. Shared setup lives on the engine so the CLI inherits it.
configure_logging()

def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Server + engine setup — constructed at import so sight_status can report
# identity without loading weights. Construction itself never eager-loads
# (import must not die on a bad MODEL_ID). If PLAIN_SIGHT_EAGER_LOAD is
# truthy we then attempt the load in a try: success leaves the model hot;
# failure is stored and surfaced as ToolError on the first tool that needs
# it. sight_status never calls _ensure_model().
# ---------------------------------------------------------------------------

mcp = FastMCP(name="plain-sight")

engine = Florence2Engine(
    model_id=DEFAULT_MODEL_ID,
    revision=os.environ.get("PLAIN_SIGHT_MODEL_REVISION", DEFAULT_MODEL_REVISION),
    cache_dir=DEFAULT_CACHE_DIR,
    device=DEFAULT_DEVICE,
    dtype=DEFAULT_DTYPE,
    eager_load=False,
)

_eager_load_error: BaseException | None = None
if _env_truthy("PLAIN_SIGHT_EAGER_LOAD"):
    try:
        engine._ensure_loaded()
    except Exception as exc:
        _eager_load_error = exc
        logger.error("PLAIN_SIGHT_EAGER_LOAD failed at server start: %s", exc)

_HONESTY_GUIDANCE = (
    "Descriptions are GENERATIVE (Florence-2): fluent, usually accurate, but "
    "they can hallucinate detail. For verifying a specific claim about an "
    "image ('does it contain X?'), use ai-eyes-mcp (SigLIP2), which measures "
    "instead of narrating."
)


# ---------------------------------------------------------------------------
# Error mapping — one place so every tool returns the same actionable shape
# ---------------------------------------------------------------------------

def _tool_error(exc: Exception) -> ToolError:
    """Map an engine exception to a consistent, actionable ToolError."""
    if isinstance(exc, FileNotFoundError):
        return ToolError(f"{exc} — check the path exists and points to a readable image file.")
    if isinstance(exc, ValueError):
        return ToolError(f"Invalid input: {exc}")
    if "out of memory" in str(exc).lower() or exc.__class__.__name__ == "OutOfMemoryError":
        return ToolError(
            "GPU out of memory. Try PLAIN_SIGHT_DTYPE=float16 (halves VRAM), "
            "or PLAIN_SIGHT_DEVICE=cpu."
        )
    logger.debug("unexpected engine error", exc_info=exc)
    return ToolError(
        "Description failed (unexpected internal error). Set "
        "PLAIN_SIGHT_LOG_LEVEL=DEBUG on the server for the full traceback."
    )


def _ensure_model() -> None:
    if engine.loaded:
        return
    if _eager_load_error is not None:
        raise ToolError(
            f"Model not loaded: {_eager_load_error}. "
            "PLAIN_SIGHT_EAGER_LOAD failed at server start. Check "
            "PLAIN_SIGHT_MODEL_ID / PLAIN_SIGHT_MODEL_DIR / PLAIN_SIGHT_DEVICE."
        )
    try:
        engine._ensure_loaded()
    except Exception as e:
        raise ToolError(
            f"Model not loaded: {e}. Check PLAIN_SIGHT_MODEL_DIR, "
            "PLAIN_SIGHT_DEVICE, and network (first load downloads ~1.5 GB)."
        )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
def describe_image(
    image_path: Annotated[str, Field(description="Absolute path to the image file")],
    detail: Annotated[str, Field(description="Detail tier: 'low' (one sentence), 'medium' (a few sentences), 'high' (full paragraph — default)")] = "high",
    max_new_tokens: Annotated[int | None, Field(description="Generation length cap (default 1024, max 4096) — raise if a high-detail caption looks truncated")] = None,
) -> dict:
    """Describe an image in prose — an AI says what it sees.

    Uses Florence-2 (MIT-licensed, runs locally) with deterministic decoding:
    the same image at the same tier reproduces the same description.

    Descriptions are generative and can hallucinate detail — for verifying a
    specific claim about the image, prefer ai-eyes-mcp's image_verify.
    """
    t0 = time.perf_counter()
    resolved = str(Path(image_path).resolve())
    try:
        engine._validate_detail(detail)
        engine._validate_max_new_tokens(max_new_tokens)
        engine._validate_image_path(resolved)
    except Exception as e:
        raise _tool_error(e) from None
    _ensure_model()
    try:
        description = engine.describe(resolved, detail=detail, max_new_tokens=max_new_tokens)
    except Exception as e:
        raise _tool_error(e) from None

    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.debug("describe_image completed in %.3fs", elapsed / 1000)
    return {
        "description": description,
        "detail": detail,
        "task": DETAIL_TASKS[detail],
        "model_id": engine.model_id,
        "image_path": resolved,
        "elapsed_ms": elapsed,
    }


@mcp.tool
def describe_batch(
    image_paths: Annotated[list[str], Field(description="List of absolute image file paths (max 100)")],
    detail: Annotated[str, Field(description="Detail tier: 'low' | 'medium' | 'high' (default)")] = "high",
    prefix: Annotated[str, Field(description="Text prepended to every caption, bare concatenation — include your own separator (e.g. 'mcpt_style, ')")] = "",
    suffix: Annotated[str, Field(description="Text appended to every caption, bare concatenation")] = "",
    write_sidecars: Annotated[bool, Field(description="Write each caption to <image-stem>.txt (exact basename pairing). When false, captions are returned in the response instead")] = True,
    out_dir: Annotated[str | None, Field(description="Directory for sidecar files (created if missing). Default: next to each image")] = None,
    overwrite: Annotated[bool, Field(description="Re-caption images whose sidecar already exists (default false: skip them, so re-runs are idempotent and cheap)")] = False,
    max_new_tokens: Annotated[int | None, Field(description="Generation length cap (default 1024, max 4096)")] = None,
    manifest_path: Annotated[str | None, Field(description="Optional explicit JSON provenance path. Default none — no manifest is written. Refused if it collides with a sidecar.")] = None,
) -> dict:
    """Blocks until every image completes -- roughly 1-2 s per image plus
    ~10-20 s if the model is not yet loaded. Chunk large sets. Existing
    sidecars are skipped unless overwrite=true, so a retry is cheap.

    Caption a batch of images, writing .txt sidecars -- the dataset lane.
    The training-data contract: EXACT basename pairing (img_0042.png ->
    img_0042.txt, no counter suffix) and BARE prefix+caption+suffix
    concatenation (no delimiter injected).
    """
    if not image_paths:
        raise ToolError("At least one image path is required")
    if len(image_paths) > 100:
        raise ToolError("Maximum 100 images per batch")
    t0 = time.perf_counter()
    try:
        engine._validate_detail(detail)
        engine._validate_max_new_tokens(max_new_tokens)
    except Exception as e:
        raise _tool_error(e) from None

    out_dir_path: Path | None = None
    if out_dir is not None:
        out_dir_path = Path(out_dir).resolve()

    resolved = [str(Path(p).resolve()) for p in image_paths]
    results: list[dict] = []
    errors: list[dict] = []
    skipped = 0
    image_entries: list[dict] = []

    if write_sidecars:
        collisions = find_sidecar_collisions(resolved, out_dir_path)
        if collisions:
            n = len(collisions)
            lines = [
                f"Sidecar collision: {n} output path"
                f"{'s are' if n != 1 else ' is'} claimed by 2+ images — captioning would "
                "silently mislabel training data. Give the images distinct stems, or drop the "
                "duplicates, then retry."
            ]
            for sidecar, claimants in collisions.items():
                names = ", ".join(str(p) for p in claimants)
                lines.append(f"  {sidecar}  <-  {names}")
            raise ToolError("\n".join(lines))

    manifest: Path | None = Path(manifest_path).resolve() if manifest_path else None
    if manifest is not None:
        hit = manifest_collides_with_sidecars(manifest, resolved, out_dir_path)
        if hit is not None:
            raise ToolError(
                f"Manifest path collides with sidecar {hit} — pick a .json path "
                "that is not a caption sidecar."
            )

    if out_dir_path is not None:
        out_dir_path.mkdir(parents=True, exist_ok=True)

    _ensure_model()
    for path in resolved:
        sidecar = sidecar_path_for(path, out_dir_path) if write_sidecars else None
        if sidecar is not None and sidecar_is_complete(sidecar) and not overwrite:
            skipped += 1
            results.append({"path": path, "sidecar": str(sidecar), "skipped_existing": True})
            image_entries.append({"image": path, "sidecar": str(sidecar), "status": "skipped_existing"})
            continue
        try:
            caption = engine.describe(path, detail=detail, max_new_tokens=max_new_tokens)
            text = compose_caption(prefix, caption, suffix)
            item: dict = {"path": path}
            if sidecar is not None:
                write_sidecar_atomic(sidecar, text)
                item["sidecar"] = str(sidecar)
                item["chars"] = len(text)
                item["preview"] = text if len(text) <= 80 else text[:79] + "…"
            else:
                item["caption"] = text
            results.append(item)
            image_entries.append({
                "image": path,
                "sidecar": str(sidecar) if sidecar is not None else None,
                "status": "written",
            })
        except FileNotFoundError:
            errors.append({"path": path, "error": "not found"})
            image_entries.append({"image": path, "sidecar": str(sidecar) if sidecar else None, "status": "failed"})
        except ValueError as e:
            logger.debug("batch item failed (invalid input): %s", e)
            errors.append({"path": path, "error": "invalid image"})
            image_entries.append({"image": path, "sidecar": str(sidecar) if sidecar else None, "status": "failed"})
        except OSError as e:
            logger.debug("batch item failed (write/IO): %s", e)
            detail_msg = e.strerror or str(e)
            errors.append({
                "path": path,
                "error": f"sidecar write failed (disk/IO): {detail_msg}",
            })
            image_entries.append({"image": path, "sidecar": str(sidecar) if sidecar else None, "status": "failed"})
        except Exception as e:
            logger.debug("batch item failed: %s", e)
            errors.append({"path": path, "error": "description failed"})
            image_entries.append({"image": path, "sidecar": str(sidecar) if sidecar else None, "status": "failed"})

    if manifest is not None:
        info = engine.status()
        write_batch_manifest(manifest, {
            "plain_sight_version": info["plain_sight_version"],
            "torch_version": info["torch_version"],
            "transformers_version": info["transformers_version"],
            "model_id": info["model_id"],
            "revision_requested": info["revision_requested"],
            "revision_resolved": info["revision_resolved"],
            "device": info["device"],
            "dtype": info["dtype"],
            "num_beams": info["num_beams"],
            "detail": detail,
            "max_new_tokens": max_new_tokens if max_new_tokens is not None else DEFAULT_MAX_NEW_TOKENS,
            "prefix": prefix,
            "suffix": suffix,
            "total": len(resolved),
            "written": len(results) - skipped,
            "skipped_existing": skipped,
            "failed": len(errors),
            "images": image_entries,
        })

    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.debug("describe_batch completed in %.3fs", elapsed / 1000)
    return {
        "total": len(resolved),
        "described": len(results) - skipped,
        "skipped_existing": skipped,
        "errors": len(errors),
        "detail": detail,
        "write_sidecars": write_sidecars,
        "out_dir": str(out_dir_path) if out_dir_path else None,
        "manifest": str(manifest) if manifest else None,
        "results": results,
        "error_details": errors if errors else None,
        "elapsed_ms": elapsed,
    }


@mcp.tool
def read_text(
    image_path: Annotated[str, Field(description="Absolute path to the image file")],
    max_new_tokens: Annotated[int | None, Field(description="Generation length cap (default 1024, max 4096)")] = None,
) -> dict:
    """Extract visible text from an image (Florence-2 <OCR> task).

    Returns the text the model reads off the pixels — signage, UI labels,
    documents. Like all generative output it can misread; treat low-stakes.
    """
    t0 = time.perf_counter()
    resolved = str(Path(image_path).resolve())
    try:
        engine._validate_max_new_tokens(max_new_tokens)
        engine._validate_image_path(resolved)
    except Exception as e:
        raise _tool_error(e) from None
    _ensure_model()
    try:
        text = engine.ocr(resolved, max_new_tokens=max_new_tokens)
    except Exception as e:
        raise _tool_error(e) from None

    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.debug("read_text completed in %.3fs", elapsed / 1000)
    return {
        "text": text,
        "model_id": engine.model_id,
        "image_path": resolved,
        "elapsed_ms": elapsed,
    }


@mcp.tool
def sight_status() -> dict:
    """Check plain-sight server status.

    Returns model info, device, and whether the model is currently loaded.
    The model loads lazily on first tool call — this tool does NOT trigger loading.
    """
    t0 = time.perf_counter()
    result = engine.status()
    if _eager_load_error is not None and not result.get("loaded"):
        result["eager_load_attempted"] = True
        result["eager_load_error"] = str(_eager_load_error)
        result["note"] = (
            f"PLAIN_SIGHT_EAGER_LOAD failed at server start: {_eager_load_error}"
        )
    elif not result.get("loaded"):
        result["note"] = (
            "Model not loaded yet — the first describe/OCR call loads Florence-2 "
            "(~10-20s on GPU; the first-ever call downloads ~1.5 GB). Set "
            "PLAIN_SIGHT_EAGER_LOAD=1 to load at server start instead."
        )
    result["honesty_guidance"] = _HONESTY_GUIDANCE
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    return result


@mcp.tool
def sight_selftest() -> dict:
    """Self-test: describe the bundled reference images and confirm the
    outputs are sane (non-trivial, on-subject, tier ordering holds) — proves
    the install loaded correctly. Loads the model if it isn't already.

    Returns `{passed, checks: [{name, expected, measured, ok}], model_id,
    device, torch_version, transformers_version}`.
    """
    t0 = time.perf_counter()
    try:
        result = engine.selftest()
    except Exception as e:
        raise _tool_error(e) from None
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()
