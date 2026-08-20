"""
plain-sight CLI — the dataset-captioning lane from a shell.

    plain-sight describe image.png [--detail high] [--json]
    plain-sight ocr image.png [--json]
    plain-sight batch ./dataset --prefix "mcpt_style, " [--out-dir caps/]
    plain-sight status
    plain-sight selftest

Exit codes: 0 success · 1 any item failed · 2 usage error (argparse).
Errors print one structured line to stderr: ``plain-sight: [CODE] message — hint``.
"""

import argparse
import json
import sys

from plain_sight import __version__
from plain_sight.engine import Florence2Engine, DETAIL_TASKS
from plain_sight.sidecars import compose_caption, iter_image_files, sidecar_path_for


def _err(code: str, message: str, hint: str) -> None:
    print(f"plain-sight: [{code}] {message} — {hint}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plain-sight",
        description="An AI says what it sees — Florence-2 image describer (local, MIT).",
    )
    parser.add_argument("--version", action="version", version=f"plain-sight {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_desc = sub.add_parser("describe", help="Describe one image in prose")
    p_desc.add_argument("image", help="Path to the image file")
    p_desc.add_argument("--detail", choices=sorted(DETAIL_TASKS), default="high",
                        help="Detail tier (default: high — full paragraph)")
    p_desc.add_argument("--max-new-tokens", type=int, default=None,
                        help="Generation length cap (default 1024, max 4096)")
    p_desc.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")

    p_ocr = sub.add_parser("ocr", help="Extract visible text from one image")
    p_ocr.add_argument("image", help="Path to the image file")
    p_ocr.add_argument("--max-new-tokens", type=int, default=None)
    p_ocr.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")

    p_batch = sub.add_parser(
        "batch",
        help="Caption files/directories into .txt sidecars (exact basename pairing)",
    )
    p_batch.add_argument("paths", nargs="+", help="Image files and/or directories")
    p_batch.add_argument("--detail", choices=sorted(DETAIL_TASKS), default="high")
    p_batch.add_argument("--prefix", default="",
                         help="Prepended to every caption, bare concatenation — "
                              "include your own separator (e.g. 'mcpt_style, ')")
    p_batch.add_argument("--suffix", default="", help="Appended to every caption")
    p_batch.add_argument("--out-dir", default=None,
                         help="Directory for sidecars (default: next to each image)")
    p_batch.add_argument("--overwrite", action="store_true",
                         help="Re-caption images whose sidecar already exists")
    p_batch.add_argument("--max-new-tokens", type=int, default=None)

    sub.add_parser("status", help="Show engine status (does not load the model)")
    sub.add_parser("selftest", help="Describe bundled reference images and sanity-check output")

    return parser


def _cmd_describe(args: argparse.Namespace, engine: Florence2Engine) -> int:
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
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    total = len(images)
    written = skipped = failed = 0
    for i, image in enumerate(images, 1):
        sidecar = sidecar_path_for(image, out_dir)
        if sidecar.exists() and not args.overwrite:
            skipped += 1
            print(f"[{i}/{total}] skip (exists) {sidecar.name}", file=sys.stderr)
            continue
        try:
            caption = engine.describe(
                str(image), detail=args.detail, max_new_tokens=args.max_new_tokens
            )
            sidecar.write_text(
                compose_caption(args.prefix, caption, args.suffix), encoding="utf-8"
            )
            written += 1
            print(f"[{i}/{total}] wrote {sidecar.name}", file=sys.stderr)
        except (FileNotFoundError, ValueError) as exc:
            failed += 1
            print(f"[{i}/{total}] FAILED {image.name}: {exc}", file=sys.stderr)

    print(json.dumps({
        "total": total,
        "written": written,
        "skipped_existing": skipped,
        "failed": failed,
        "detail": args.detail,
        "out_dir": str(out_dir) if out_dir else None,
    }, indent=2))
    return 0 if failed == 0 else 1


def _cmd_status(engine: Florence2Engine) -> int:
    print(json.dumps(engine.status(), indent=2, default=str))
    return 0


def _cmd_selftest(engine: Florence2Engine) -> int:
    result = engine.selftest()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = Florence2Engine()
    try:
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
        _err("INTERRUPTED", "cancelled by user", "partial sidecars from `batch` are kept")
        code = 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary: no raw stacks
        _err("INTERNAL", f"{exc.__class__.__name__}: {exc}",
             "set PLAIN_SIGHT_LOG_LEVEL=DEBUG for details; try PLAIN_SIGHT_DEVICE=cpu")
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
