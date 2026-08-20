"""
plain-sight CLI — the dataset-captioning lane from a shell.

    plain-sight describe image.png [--detail high] [--json]
    plain-sight ocr image.png [--json]
    plain-sight batch ./dataset --prefix "mcpt_style, " [--out-dir caps/]
    plain-sight status
    plain-sight selftest

Exit codes: 0 ok · 1 user error (bad input, bad usage) · 2 runtime error
(model/internal failure, failed selftest) · 3 partial success (batch with
some failures). Errors print one structured line to stderr:
``plain-sight: [CODE] message -- hint``.
"""

import argparse
import json
import logging
import sys
import time

from plain_sight import __version__
from plain_sight.engine import (
    Florence2Engine,
    DETAIL_TASKS,
    DEFAULT_MAX_NEW_TOKENS,
    configure_logging,
)
from plain_sight.sidecars import (
    compose_caption,
    find_sidecar_collisions,
    iter_image_files,
    manifest_collides_with_sidecars,
    sidecar_is_complete,
    sidecar_path_for,
    write_batch_manifest,
    write_sidecar_atomic,
)

logger = logging.getLogger("plain_sight")


def _err(code: str, message: str, hint: str) -> None:
    print(f"plain-sight: [{code}] {message} -- {hint}", file=sys.stderr)


class _Parser(argparse.ArgumentParser):
    """Usage errors are USER errors — exit 1 per the studio exit-code canon
    (0 ok · 1 user error · 2 runtime error · 3 partial success). argparse's
    native usage-exit of 2 would collide with 'runtime error'.
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(
            1,
            "plain-sight: [USAGE] "
            f"{message} -- try 'plain-sight --help' "
            "(commands: describe, ocr, batch, status, selftest)\n",
        )


_DETAIL_HELP = "Detail tier: low (one sentence), medium (a few sentences), high (full paragraph, default)"
_TOKENS_HELP = "Generation length cap (default 1024, max 4096)"


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="plain-sight",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="An AI says what it sees - Florence-2 image describer (local, MIT).",
        epilog=(
            "Exit codes: 0 ok, 1 user error, 2 runtime error, "
            "3 partial success (batch).\n"
            "Progress goes to stderr; results go to stdout.\n"
            "First invocation loads Florence-2 (~10s on GPU; "
            "first-ever run downloads ~1.5 GB)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"plain-sight {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_desc = sub.add_parser("describe", help="Describe one image in prose")
    p_desc.add_argument("image", help="Path to the image file")
    p_desc.add_argument("--detail", choices=sorted(DETAIL_TASKS), default="high",
                        help=_DETAIL_HELP)
    p_desc.add_argument("--max-new-tokens", type=int, default=None,
                        help=_TOKENS_HELP)
    p_desc.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")

    p_ocr = sub.add_parser("ocr", help="Extract visible text from one image")
    p_ocr.add_argument("image", help="Path to the image file")
    p_ocr.add_argument("--max-new-tokens", type=int, default=None, help=_TOKENS_HELP)
    p_ocr.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")

    p_batch = sub.add_parser(
        "batch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help="Caption files/directories into .txt sidecars (exact basename pairing)",
        epilog=(
            "Existing .txt sidecars are skipped unless --overwrite. "
            "A dataset-scale run takes hours (~1-2s per image after load)."
        ),
    )
    p_batch.add_argument("paths", nargs="+", help="Image files and/or directories")
    p_batch.add_argument("--detail", choices=sorted(DETAIL_TASKS), default="high",
                         help=_DETAIL_HELP)
    p_batch.add_argument("--prefix", default="",
                         help="Prepended to every caption, bare concatenation -- "
                              "include your own separator (e.g. 'mcpt_style, ')")
    p_batch.add_argument("--suffix", default="", help="Appended to every caption")
    p_batch.add_argument("--out-dir", default=None,
                         help="Directory for sidecars (default: next to each image)")
    p_batch.add_argument("--overwrite", action="store_true",
                         help="Re-caption images whose sidecar already exists")
    p_batch.add_argument("--max-new-tokens", type=int, default=None, help=_TOKENS_HELP)
    p_batch.add_argument(
        "--manifest",
        default=None,
        help="Write a JSON provenance record at this exact path (opt-in; never inferred)",
    )
    p_batch.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan (counts, skip, prefix, model) and exit; load nothing, write nothing",
    )

    sub.add_parser("status", help="Show engine status (does not load the model)")
    sub.add_parser("selftest", help="Describe bundled reference images and sanity-check output")

    return parser


def _announce_load(engine: Florence2Engine, *, n_caption: int | None = None, n_skip: int | None = None) -> None:
    """Default-verbosity stderr: the tool is alive and may pause on first caption."""
    rev = engine.revision or "unpinned"
    extra = ""
    if n_caption is not None:
        extra = f"  caption={n_caption} skip={n_skip or 0}"
    print(
        f"plain-sight: loading {engine.model_id} rev={rev}{extra}  "
        f"(first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)",
        file=sys.stderr,
        flush=True,
    )


def _fmt_eta(seconds: float) -> str:
    if seconds <= 0 or seconds != seconds or seconds == float("inf"):
        return "?"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    mins, secs = divmod(secs, 60)
    if mins < 60:
        return f"{mins}m {secs:02d}s"
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins:02d}m"


def _heartbeat(i: int, total: int, written: int, skipped: int, failed: int, elapsed: float, n_caption: int) -> None:
    rate = written / elapsed if elapsed > 0 else 0.0
    work_left = max(n_caption - written - failed, 0)
    eta = _fmt_eta(work_left / rate) if rate > 0 else "?"
    print(
        f"[heartbeat] {i}/{total} written={written} skipped={skipped} "
        f"failed={failed}  {rate:.1f} img/s  ETA {eta}",
        file=sys.stderr,
        flush=True,
    )


def _plan_counts(images, out_dir, overwrite: bool) -> tuple[int, int]:
    to_write = to_skip = 0
    for image in images:
        sidecar = sidecar_path_for(image, out_dir)
        if sidecar_is_complete(sidecar) and not overwrite:
            to_skip += 1
        else:
            to_write += 1
    return to_write, to_skip


def _cmd_describe(args: argparse.Namespace, engine: Florence2Engine) -> int:
    _announce_load(engine)
    text = engine.describe(args.image, detail=args.detail, max_new_tokens=args.max_new_tokens)
    if args.json:
        print(json.dumps({
            "description": text,
            "detail": args.detail,
            "task": DETAIL_TASKS[args.detail],
            "model_id": engine.model_id,
            "image": args.image,
        }, indent=2))
    else:
        print(text)
    return 0


def _cmd_ocr(args: argparse.Namespace, engine: Florence2Engine) -> int:
    _announce_load(engine)
    text = engine.ocr(args.image, max_new_tokens=args.max_new_tokens)
    if args.json:
        print(json.dumps({"text": text, "model_id": engine.model_id, "image": args.image}, indent=2))
    else:
        print(text)
    return 0


def _cmd_batch(args: argparse.Namespace, engine: Florence2Engine) -> int:
    from pathlib import Path

    images = iter_image_files(args.paths)
    if not images:
        _err("EMPTY_BATCH", "No image files found in the given paths",
             "check the directory contents and extensions")
        return 1

    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    collisions = find_sidecar_collisions(images, out_dir)
    if collisions:
        n = len(collisions)
        path_word = "sidecar path is" if n == 1 else "sidecar paths are"
        _err(
            "SIDECAR_COLLISION",
            f"{n} {path_word} claimed by 2+ images",
            "captioning would silently mislabel training data -- resolve the clash or pass --out-dir with unique stems",
        )
        for sidecar, claimants in collisions.items():
            names = ", ".join(str(p) for p in claimants)
            print(f"  {sidecar}  <-  {names}", file=sys.stderr)
        return 1

    manifest_path = Path(args.manifest).resolve() if args.manifest else None
    if manifest_path is not None:
        hit = manifest_collides_with_sidecars(manifest_path, images, out_dir)
        if hit is not None:
            _err(
                "MANIFEST_COLLISION",
                f"manifest path collides with sidecar {hit}",
                "pick a .json path that is not a caption sidecar",
            )
            return 1

    to_write, to_skip = _plan_counts(images, out_dir, args.overwrite)

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "model_id": engine.model_id,
            "revision": engine.revision,
            "prefix": args.prefix,
            "suffix": args.suffix,
            "out_dir": str(out_dir) if out_dir else None,
            "detail": args.detail,
            "total": len(images),
            "would_write": to_write,
            "would_skip": to_skip,
            "collisions": 0,
        }, indent=2))
        return 0

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    if to_write:
        _announce_load(engine, n_caption=to_write, n_skip=to_skip)

    total = len(images)
    written = skipped = failed = 0
    image_entries: list[dict] = []
    t0 = time.perf_counter()
    last_beat_t = t0
    last_beat_i = 0
    for i, image in enumerate(images, 1):
        sidecar = sidecar_path_for(image, out_dir)
        if sidecar_is_complete(sidecar) and not args.overwrite:
            skipped += 1
            image_entries.append({
                "image": str(image),
                "sidecar": str(sidecar),
                "status": "skipped_existing",
            })
        else:
            try:
                caption = engine.describe(
                    str(image), detail=args.detail, max_new_tokens=args.max_new_tokens
                )
                write_sidecar_atomic(
                    sidecar, compose_caption(args.prefix, caption, args.suffix)
                )
                written += 1
                print(f"[{i}/{total}] wrote {sidecar.name}", file=sys.stderr)
                image_entries.append({
                    "image": str(image),
                    "sidecar": str(sidecar),
                    "status": "written",
                })
            except Exception as exc:
                failed += 1
                logger.debug("batch item failed", exc_info=exc)
                print(f"[{i}/{total}] FAILED {image.name}: {exc}", file=sys.stderr)
                image_entries.append({
                    "image": str(image),
                    "sidecar": str(sidecar),
                    "status": "failed",
                })
        now = time.perf_counter()
        if (i - last_beat_i) >= 25 or (now - last_beat_t) >= 30 or i == total:
            _heartbeat(i, total, written, skipped, failed, now - t0, to_write)
            last_beat_t = now
            last_beat_i = i

    if manifest_path is not None:
        info = engine.status()
        write_batch_manifest(manifest_path, {
            "plain_sight_version": info["plain_sight_version"],
            "torch_version": info["torch_version"],
            "transformers_version": info["transformers_version"],
            "model_id": info["model_id"],
            "revision_requested": info["revision_requested"],
            "revision_resolved": info["revision_resolved"],
            "device": info["device"],
            "dtype": info["dtype"],
            "num_beams": info["num_beams"],
            "detail": args.detail,
            "max_new_tokens": args.max_new_tokens if args.max_new_tokens is not None else DEFAULT_MAX_NEW_TOKENS,
            "prefix": args.prefix,
            "suffix": args.suffix,
            "total": total,
            "written": written,
            "skipped_existing": skipped,
            "failed": failed,
            "images": image_entries,
        })

    print(json.dumps({
        "total": total,
        "written": written,
        "skipped_existing": skipped,
        "failed": failed,
        "detail": args.detail,
        "out_dir": str(out_dir) if out_dir else None,
        "manifest": str(manifest_path) if manifest_path else None,
    }, indent=2))
    if failed == 0:
        return 0
    return 1 if written == 0 else 3  # all failed = user error; some = partial success


def _cmd_status(engine: Florence2Engine) -> int:
    print(json.dumps(engine.status(), indent=2, default=str))
    return 0


def _cmd_selftest(engine: Florence2Engine) -> int:
    result = engine.selftest()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 2  # a failing instrument is a runtime error


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    try:
        engine = Florence2Engine()
        if args.command == "describe":
            code = _cmd_describe(args, engine)
        elif args.command == "ocr":
            code = _cmd_ocr(args, engine)
        elif args.command == "batch":
            code = _cmd_batch(args, engine)
        elif args.command == "status":
            code = _cmd_status(engine)
        elif args.command == "selftest":
            code = _cmd_selftest(engine)
        else:  # pragma: no cover — argparse enforces the choices
            code = 2
    except FileNotFoundError as exc:
        _err("NOT_FOUND", str(exc), "check the path exists and is a readable image")
        code = 1
    except ValueError as exc:
        _err("INVALID_INPUT", str(exc), "see --help for valid values")
        code = 1
    except KeyboardInterrupt:
        _err(
            "INTERRUPTED",
            "cancelled by user",
            "in-flight sidecar discarded; completed sidecars kept",
        )
        code = 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary: no raw stacks
        logger.debug("internal error", exc_info=exc)
        _err("INTERNAL", f"{exc.__class__.__name__}: {exc}",
             "set PLAIN_SIGHT_LOG_LEVEL=DEBUG for details; try PLAIN_SIGHT_DEVICE=cpu")
        code = 2
    return code


if __name__ == "__main__":
    sys.exit(main())
