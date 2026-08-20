"""
Florence-2 vision engine — generative image description.

Wraps microsoft/Florence-2-large as a describing instrument: image in, prose
caption (or OCR text) out. The complement to ai-eyes-mcp's SigLIP2 judge —
plain-sight NARRATES, ai-eyes MEASURES. Descriptions are generative and can
hallucinate detail; verify load-bearing claims with a discriminative tool.

No MCP dependency. Can be used standalone or from the MCP server / CLI.

Key design decisions:
  - Native transformers Florence-2 classes ONLY — ``trust_remote_code`` is
    NEVER used (requires transformers >= 4.51).
  - Deterministic by default: ``do_sample=False`` + beam search, so the same
    image reproduces the same caption (mirrors the verified Comfy Cloud
    contract: caption-florence2-v1).
  - Detail tiers map to Florence-2's native task ladder:
    low → <CAPTION>, medium → <DETAILED_CAPTION>, high → <MORE_DETAILED_CAPTION>.
  - Model pinned to florence-community/Florence-2-large — the official
    native-transformers conversion of Microsoft's MIT release (hub license
    tag: mit, verified 2026-08-19). The original microsoft/ repos ship
    pre-native configs that only load via trust_remote_code, which this tool
    refuses. The PromptGen / CogFlorence / Castollux fine-tune family is
    deliberately NOT offered — licenses unverified (see README).
  - Lazy model loading; input validation runs BEFORE the load so bad calls
    fail fast without pulling 1.5 GB of weights.
  - Forward passes serialized by a per-engine lock.
"""

import logging
import os
import sys
import threading
from pathlib import Path

import torch
from PIL import Image

from plain_sight import __version__ as _package_version

logger = logging.getLogger("plain_sight")


def configure_logging(default_level: str = "WARNING") -> int:
    """Configure the ``plain_sight`` logger from PLAIN_SIGHT_LOG_LEVEL.

    Idempotent — safe to call from every entry point. Logs go to STDERR only:
    for the MCP server STDOUT is the STDIO protocol channel and must never be
    polluted, and for the CLI it is the caption itself. Returns the effective
    numeric level.
    """
    raw = os.environ.get("PLAIN_SIGHT_LOG_LEVEL")
    name = raw.strip().upper() if raw and raw.strip() else default_level.strip().upper()
    level = getattr(logging, name, None)
    if not isinstance(level, int):
        fallback_name = default_level.strip().upper()
        level = getattr(logging, fallback_name, logging.WARNING)
        if not isinstance(level, int):
            level = logging.WARNING
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger.level


# ---------------------------------------------------------------------------
# Defaults (overridable via env vars)
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID = os.environ.get(
    "PLAIN_SIGHT_MODEL_ID", "florence-community/Florence-2-large"
)
# Hub commit of florence-community/Florence-2-large as of the v1 suite
# (verified 2026-08-20 against the hub SHA and the rig cache). Env override
# still wins; empty/unset falls back to the pin.
PINNED_MODEL_REVISION = "4271c66b88cdbc05735372ec13b2360108de5317"
DEFAULT_MODEL_REVISION = (
    os.environ.get("PLAIN_SIGHT_MODEL_REVISION") or PINNED_MODEL_REVISION
)
DEFAULT_CACHE_DIR = os.environ.get("PLAIN_SIGHT_MODEL_DIR", None)
DEFAULT_DEVICE = os.environ.get(
    "PLAIN_SIGHT_DEVICE", "cuda" if torch.cuda.is_available() else "cpu"
)
# fp16 on CUDA by default (the verified cloud contract runs fp16); full
# precision on CPU. "float32"/"none" forces full precision on CUDA too.
DEFAULT_DTYPE = os.environ.get(
    "PLAIN_SIGHT_DTYPE", "float16" if DEFAULT_DEVICE.startswith("cuda") else None
)

MAX_NEW_TOKENS_CEILING = 4096  # mirrors the Florence2Run node's schema max
try:
    DEFAULT_MAX_NEW_TOKENS = int(os.environ.get("PLAIN_SIGHT_MAX_NEW_TOKENS", "1024"))
except (ValueError, TypeError):
    DEFAULT_MAX_NEW_TOKENS = 1024
    logger.warning(
        "Invalid PLAIN_SIGHT_MAX_NEW_TOKENS (%r), using %s",
        os.environ.get("PLAIN_SIGHT_MAX_NEW_TOKENS"),
        DEFAULT_MAX_NEW_TOKENS,
    )
try:
    DEFAULT_NUM_BEAMS = int(os.environ.get("PLAIN_SIGHT_NUM_BEAMS", "3"))
except (ValueError, TypeError):
    DEFAULT_NUM_BEAMS = 3

# Detail ladder — Florence-2's three native caption tiers.
DETAIL_TASKS = {
    "low": "<CAPTION>",
    "medium": "<DETAILED_CAPTION>",
    "high": "<MORE_DETAILED_CAPTION>",
}
OCR_TASK = "<OCR>"


class Florence2Engine:
    """Florence-2 describing engine.

    Lazy-loads the model on first inference call. ``describe`` and ``ocr``
    return plain strings — templating (prefix/suffix, sidecars) is the
    caller's concern via :mod:`plain_sight.sidecars`.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        cache_dir: str | Path | None = DEFAULT_CACHE_DIR,
        device: str = DEFAULT_DEVICE,
        revision: str | None = DEFAULT_MODEL_REVISION,
        dtype: str | None = DEFAULT_DTYPE,
        num_beams: int = DEFAULT_NUM_BEAMS,
        eager_load: bool | None = None,
    ):
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.device = device
        self.revision = revision
        self.dtype = None if dtype in (None, "", "none", "float32") else dtype
        self.num_beams = num_beams
        self._model = None
        self._processor = None
        # Serialize GPU forward passes — safe for concurrent callers, and
        # effectively free (inference is GPU-bound and serial on one device).
        self._forward_lock = threading.Lock()
        if eager_load is None:
            eager_load = os.environ.get("PLAIN_SIGHT_EAGER_LOAD", "").strip().lower() in (
                "1", "true", "yes", "on",
            )
        if eager_load:
            self._ensure_loaded()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    # -- loading ------------------------------------------------------------

    def _ensure_loaded(self):
        """Load model and processor on first use.

        Uses local variables during the load sequence so ``self._model`` /
        ``self._processor`` are only set after the entire chain succeeds; on
        failure both stay ``None`` and the next call retries cleanly.

        Native transformers classes only — ``trust_remote_code`` is never
        passed, so no hub-fetched Python ever executes.
        """
        if self._model is not None:
            return

        from transformers import AutoProcessor

        logger.info("Loading %s ...", self.model_id)

        kwargs = {}
        if self.cache_dir:
            kwargs["cache_dir"] = self.cache_dir
        if self.revision:
            kwargs["revision"] = self.revision

        try:
            processor = AutoProcessor.from_pretrained(self.model_id, **kwargs)
            model = None
            try:
                from transformers import AutoModelForImageTextToText

                model = AutoModelForImageTextToText.from_pretrained(self.model_id, **kwargs)
            except (ValueError, KeyError, OSError) as auto_exc:
                # Older transformers without the florence2 auto-mapping — try
                # the direct native class before giving up.
                try:
                    from transformers import Florence2ForConditionalGeneration
                except ImportError:
                    raise auto_exc
                model = Florence2ForConditionalGeneration.from_pretrained(
                    self.model_id, **kwargs
                )
            model = model.eval().to(self.device)

            if self.dtype == "float16":
                model = model.half()
                logger.info("Applied float16 (half precision)")
            elif self.dtype == "bfloat16":
                model = model.bfloat16()
                logger.info("Applied bfloat16 precision")
            elif self.dtype is not None:
                logger.warning(
                    "Unknown PLAIN_SIGHT_DTYPE '%s', keeping full precision", self.dtype
                )
                self.dtype = None
        except Exception as exc:
            self._model = None
            self._processor = None
            logger.error(
                "Failed to load model '%s': %s\n"
                "  Hints:\n"
                "  - Check network connectivity (model may need downloading, ~1.5 GB)\n"
                "  - Check transformers >= 4.51 (native Florence-2 support; this tool never uses trust_remote_code)\n"
                "  - Check HuggingFace cache dir for corruption (%s)\n"
                "  - Check GPU memory (device=%s) — try PLAIN_SIGHT_DEVICE=cpu as fallback",
                self.model_id,
                exc,
                self.cache_dir or "~/.cache/huggingface",
                self.device,
            )
            raise

        # Commit only after full success
        self._processor = processor
        self._model = model

        param_count = sum(p.numel() for p in self._model.parameters())
        logger.info("Loaded on %s, %.0fM params", self.device, param_count / 1e6)

    # -- validation (runs BEFORE model load) ---------------------------------

    @staticmethod
    def _validate_detail(detail: str) -> str:
        """Map a detail tier to its Florence-2 task token, or raise."""
        task = DETAIL_TASKS.get(detail)
        if task is None:
            raise ValueError(
                f"Unknown detail tier {detail!r} -- choose one of: "
                f"{', '.join(DETAIL_TASKS)}"
            )
        return task

    @staticmethod
    def _validate_max_new_tokens(value: int | None) -> int:
        if value is None:
            return DEFAULT_MAX_NEW_TOKENS
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("max_new_tokens must be an integer")
        if not (1 <= value <= MAX_NEW_TOKENS_CEILING):
            raise ValueError(
                f"max_new_tokens must be between 1 and {MAX_NEW_TOKENS_CEILING}"
            )
        return value

    @staticmethod
    def _validate_image_path(image_path: str) -> Path:
        """Check the path names a real file — before the model loads."""
        path = Path(image_path)
        if path.exists() and not path.is_file():
            raise FileNotFoundError(f"Path is not a file: {image_path}")
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")
        return path

    @staticmethod
    def _open_image(path: Path) -> Image.Image:
        """Open a validated path as RGB, with actionable errors."""
        try:
            return Image.open(path).convert("RGB")
        except Image.DecompressionBombError:
            raise ValueError(f"Image too large (possible decompression bomb): {path}")
        except (Image.UnidentifiedImageError, OSError) as exc:
            raise ValueError(
                f"Cannot open image (corrupt or unsupported format): {path}"
            ) from exc

    # -- inference ------------------------------------------------------------

    def _generate(self, image: Image.Image, task_token: str, max_new_tokens: int) -> str:
        """Run one Florence-2 task on an opened image, return the parsed text.

        Deterministic: ``do_sample=False`` + beam search. The same
        model/image/task reproduces the same text.
        """
        inputs = self._processor(
            text=task_token, images=image, return_tensors="pt"
        ).to(self.device)
        if self.dtype == "float16":
            inputs["pixel_values"] = inputs["pixel_values"].half()
        elif self.dtype == "bfloat16":
            inputs["pixel_values"] = inputs["pixel_values"].bfloat16()

        with self._forward_lock, torch.no_grad():
            generated_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_beams=self.num_beams,
                do_sample=False,
            )

        raw = self._processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed = self._processor.post_process_generation(
            raw, task=task_token, image_size=(image.width, image.height)
        )
        text = parsed.get(task_token, "")
        if not isinstance(text, str):  # region tasks return dicts; ours never should
            text = str(text)
        return text.strip()

    def describe(
        self,
        image_path: str,
        detail: str = "high",
        max_new_tokens: int | None = None,
    ) -> str:
        """Describe an image at the given detail tier. Returns prose.

        ``high`` (default) is <MORE_DETAILED_CAPTION> — a full paragraph.
        ``medium`` is a few sentences; ``low`` is one short sentence.
        """
        task = self._validate_detail(detail)
        tokens = self._validate_max_new_tokens(max_new_tokens)
        path = self._validate_image_path(image_path)
        self._ensure_loaded()
        image = self._open_image(path)
        return self._generate(image, task, tokens)

    def ocr(self, image_path: str, max_new_tokens: int | None = None) -> str:
        """Extract visible text from an image (<OCR> task). Returns the text."""
        tokens = self._validate_max_new_tokens(max_new_tokens)
        path = self._validate_image_path(image_path)
        self._ensure_loaded()
        image = self._open_image(path)
        return self._generate(image, OCR_TASK, tokens)

    # -- status / selftest ------------------------------------------------------

    def status(self) -> dict:
        """Return engine status info."""
        import transformers

        info = {
            "plain_sight_version": _package_version,
            "model_id": self.model_id,
            "device": self.device,
            "dtype": self.dtype or "float32",
            "loaded": self.loaded,
            "cache_dir": self.cache_dir or "default",
            "num_beams": self.num_beams,
            "default_max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
            "detail_tiers": dict(DETAIL_TASKS),
            "revision_requested": self.revision,
            "revision_resolved": None,
            "python_version": sys.version,
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
        }
        if self.loaded:
            param_count = sum(p.numel() for p in self._model.parameters())
            info["parameters"] = f"{param_count / 1e6:.0f}M"
            cfg = getattr(self._model, "config", None)
            info["revision_resolved"] = getattr(cfg, "_commit_hash", None)
            if self.device.startswith("cuda") and torch.cuda.is_available():
                dev = torch.device(self.device)
                info["vram_mb"] = round(torch.cuda.memory_allocated(dev) / 1024 / 1024)
        return info

    def selftest(self) -> dict:
        """Describe the bundled reference images and check the outputs are
        sane — proves the install loaded and the caption ladder behaves.

        Generative outputs can't be byte-asserted, so checks are structural:
        non-trivial length, expected subject keywords, and the tier ordering
        (high detail longer than low). Deterministic decoding keeps these
        stable for a given model revision.
        """
        refs = Path(__file__).resolve().parent / "assets" / "selftest"
        knight = str(refs / "knight.png")
        cheetah = str(refs / "cheetah.jpg")
        checks: list[dict] = []

        def _snippet(text: str, limit: int = 120) -> str:
            return text if len(text) <= limit else text[: limit - 1] + "…"

        def _keyword_check(name: str, text: str, keywords: tuple[str, ...]) -> None:
            lowered = text.lower()
            hit = any(k in lowered for k in keywords)
            checks.append({
                "name": name,
                "expected": f"non-trivial caption mentioning any of {keywords}",
                "measured": _snippet(text),
                "ok": bool(len(text) >= 20 and hit),
            })

        cheetah_high = self.describe(cheetah, detail="high")
        _keyword_check(
            "cheetah_subject",
            cheetah_high,
            ("cheetah", "leopard", "feline", "cat", "animal"),
        )

        knight_high = self.describe(knight, detail="high")
        _keyword_check(
            "knight_subject",
            knight_high,
            ("knight", "armor", "armour", "sword", "shield", "helmet", "warrior"),
        )

        knight_low = self.describe(knight, detail="low")
        checks.append({
            "name": "tier_ordering",
            "expected": "high-detail caption longer than low-detail caption",
            "measured": f"high={len(knight_high)} chars, low={len(knight_low)} chars",
            "ok": len(knight_high) > len(knight_low) > 0,
        })

        info = self.status()
        return {
            "passed": all(c["ok"] for c in checks),
            "checks": checks,
            "model_id": info["model_id"],
            "device": info["device"],
            "torch_version": info["torch_version"],
            "transformers_version": info["transformers_version"],
        }
