<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**版本：**1.1.0

**人工智能描述它所看到的事物。** 生成式图像描述器——MCP 服务器 + CLI 包装
Florence-2 (MIT) 用于散文描述、OCR 和 LoRA 数据集字幕文件。
本地运行，默认情况下是确定性的。

它是 [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) 的姊妹项目：

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| 任务 | **judges** images | **describes** images |
| 模型 | SigLIP2（判别式） | Florence-2（生成式） |
| 输出 | 校准后的分数 | 散文/OCR/字幕文件 |
| 失败模式 | 无法进行描述 | 可能会虚构细节 |
| 何时使用 | “这张图片是否包含 X？” | “这张图片里有什么？” |

## 诚实协议

描述是**生成式的**：流畅、通常准确，并且能够创造细节。plain-sight 使输出具有*可重现性*（确定性解码——相同的图像产生相同的字幕），而不是*保证真实*。要验证关于图像的特定声明，请使用 ai-eyes-mcp 的 `image_verify` ——它进行测量，而不是描述。这两个工具的设计目的是不同的模型系列，因此一个可以检查另一个。

以下是三个具体的限制，之所以说明这些限制是因为它们很容易通过实践来发现：

- **OCR无法报告文本的缺失。** Florence-2 会为每个图像输出一个解码后的字符串，包括完全不包含文本的图像——一张照片可能会返回 `'2'`。该输出在词法上与正确读取数字的结果没有区别。因此，每个 OCR 结果都带有 `absence_of_text_unreliable: true`（MCP）或在 stderr 上的一行 `[OCR_CAVEAT]`（CLI）。plain-sight 从不会抑制或清空结果，因为简短的读取结果可能是真实的——它会告诉你信号不存在。
- **标题是对图像的描述；它们不进行验证。** 关于图像的一个确定的句子并不能证明所描述的事物确实存在。
- **可重复性是针对特定版本的。** 固定版本才能使确定性的声明在时间上具有意义；请参阅[Provenance](#provenance)。

## 工具（MCP）

| 工具 | 它的作用 |
|------|-------------|
| `describe_image` | 一张图像 → 散文描述（3 个细节级别） |
| `describe_batch` | N 张图像 → `.txt` 字幕文件（数据集通道） |
| `read_text` | OCR——从图像中解码文本，但需要注意其局限性。 |
| `sight_status` | 健康检查：模型、设备、已解析的版本、加载状态。 |
| `sight_selftest` | 描述捆绑的参考图像，进行输出的合理性检查 |

每个包含模型输出的有效负载也包含 `model_id` 和 `revision_resolved`——请参阅[Provenance](#provenance)。

## 快速入门

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

或者作为模块运行：`python -m plain_sight`

### CLI

```bash
# One image, full paragraph
plain-sight describe hero.png

# One short sentence
plain-sight describe hero.png --detail low

# OCR (the absence caveat goes to stderr; the text goes to stdout)
plain-sight ocr screenshot.png

# See the plan before writing anything — no model load, no files
plain-sight batch ./dataset --prefix "mcpt_style, " --dry-run

# The dataset lane: caption a directory into .txt sidecars with a trigger token
plain-sight batch ./dataset --prefix "mcpt_style, " --detail high

# Record provenance for the run alongside it
plain-sight batch ./dataset --prefix "mcpt_style, " --manifest ./dataset-run.json

# Re-runs are idempotent — existing sidecars are skipped unless you --overwrite
plain-sight batch ./dataset --prefix "mcpt_style, " --overwrite
```

`batch` 标志：`--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite` · `--max-new-tokens` · `--manifest` · `--dry-run`。运行 `plain-sight batch --help` 以获取完整文本；`plain-sight --help` 文档记录了退出代码以及哪个流包含哪些内容。

### 长时间运行的效果

进度输出到 **stderr**；结果输出到 **stdout**，因此 `plain-sight describe x.png > caption.txt` 可以正常工作。

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

在开始工作之前会先声明负载，并提供将实际生成标题的图像数量，因此不会出现运行过程中间暂停的情况。跳过的图像会在心跳周期中进行计数，而不是逐行打印——对已完成数据集的重新运行是静默的。失败情况仍然以每行显示。

### Claude Code 配置

```json
{
  "mcpServers": {
    "plain-sight": {
      "command": "plain-sight-mcp",
      "env": {
        "PLAIN_SIGHT_MODEL_DIR": "/path/to/model/cache"
      }
    }
  }
}
```

## 字幕协议（数据集通道）

专为 LoRA 训练集（style-dataset-lab 和相关工具）构建：

- **精确的基本名称配对：** `img_0042.png` → `img_0042.txt`。没有计数器后缀——与 ComfyUI 的 SaveText 节点不同，该节点会附加 `_00001`。
- **简单连接：** 副文件包含 `prefix + caption + suffix`，不插入任何分隔符。想要 `"mcpt_style, <caption>"`？将逗号和空格放在前缀中。
- **冲突的词干会被拒绝，绝不会合并。** 如果两个图像的词干匹配——一个文件夹中的 `img.png` 和 `img.jpg`，或者来自两个文件夹且具有相同词干的文件位于同一个 `--out-dir` 下——它们会声称只有一个 `.txt`。plain-sight 会在加载模型之前拒绝整个批次，并标明违规者，然后退出 `1`。它不会重命名副文件以避免冲突：训练器通过精确的词干进行配对，因此重命名会导致标题与图像分离，从而使图像无法生成标题。
- **写入是原子性的。** 每个副文件都会被写入到同一目录中的一个临时文件中，然后移动到位，因此中断操作不会在最终路径中留下部分标题。如果存在但为空的副文件将被视为未完成，并重新生成标题。
- **幂等性重新运行：** 现有的非空副文件会被跳过，并且不会产生任何影响，除非是 `--overwrite` / `overwrite=true`。
- **确定性：** `do_sample=false` + 对固定版本的进行光束搜索——对未更改的图像重新生成标题会生成相同的文本，因此差异是有意义的。

## 溯源

数据集流程会生成训练数据。六个月后，问题是哪个权重生成了哪些标题——因此答案会与输出一起传递。

- **默认情况下，模型版本被固定为** `4271c66b88cdbc05735372ec13b2360108de5317`。如果没有固定版本，HuggingFace 会解析到仓库的默认分支当前指向的版本，并且无声地重新标记会导致在未更改的输入下生成不同的标题。使用 `PLAIN_SIGHT_MODEL_REVISION` 进行覆盖。
- **每个输出有效负载都会命名权重。** `describe_image`、`read_text`、`describe_batch`、`sight_selftest` 以及 CLI 的 `--json` 模式和批处理摘要都包含 `model_id` 和 `revision_resolved`——加载的模型实际报告的版本，而不是请求的常量。`sight_status` 会报告两者，因此可以清楚地看到是否存在不匹配的情况。
- **`--manifest PATH` 会写入运行记录**——工具版本、模型 ID、请求的和已解析的版本、设备、dtype、详细程度、前缀/后缀、每个图像的结果和计数。可以选择启用，并且不会自动推断：除非传递了路径，否则不会写入清单，并且如果路径与计算出的副文件冲突，则会被拒绝。它包含一个时间戳，因此与标题不同，它不是字节可重现的。

## 细节级别

Florence-2 的原生任务层级：

| 层级 | 任务令牌 | 输出 |
|------|-----------|--------|
| `low` | `<CAPTION>` | 一个简短的句子 |
| `medium` | `<DETAILED_CAPTION>` | 几个句子 |
| `high`（默认） | `<MORE_DETAILED_CAPTION>` | 一个完整的段落 |

`high` 是一个段落，而不是一篇论文——Florence-2 是一种紧凑的模型（0.77B）。它的优势在于吞吐量和许可证，而不是艺术评论的深度。如果字幕看起来被截断了，请提高 `max_new_tokens`（默认值为 1024，最大值为 4096）。

## 配置

| 环境变量 | 默认值 | 用途 |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | HuggingFace 模型 |
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…`（已固定） | 模型版本；确定性声明背后的机制。 |
| `PLAIN_SIGHT_MODEL_DIR` | HF 默认缓存 | 模型缓存目录 |
| `PLAIN_SIGHT_DEVICE` | `auto`（如果可用，则使用 cuda；否则使用 cpu） | torch 设备 |
| `PLAIN_SIGHT_DTYPE` | `float16` 在 CUDA 上，在 CPU 上使用完全精度 | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | 默认生成上限 |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | 集束宽度（确定性解码） |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | 未设置 | 如果为真，则在服务器启动时加载模型 |

**日志记录：** 仅限 stderr（stdout 是 MCP 协议通道），logger 名称为 `plain_sight`。`PLAIN_SIGHT_LOG_LEVEL` 在两个表面上都有效。

**即时加载：** 如果 `PLAIN_SIGHT_EAGER_LOAD` 为真，则 MCP 服务器会在启动时而不是在第一次调用时进行加载。如果加载失败，不会终止服务器导入——它会通过 `sight_status` 报告为 `eager_load_error`，并在需要模型的第一个工具调用中引发 `ToolError`。

**首次调用：**模型会延迟加载——第一次 describe/OCR 调用会加载 Florence-2（GPU 上大约需要 10–20 秒；第一次调用会下载约 1.5 GB）。后续调用的速度约为每张图像 1–2 秒，细节级别为 `high`。

## 许可证策略

- **此工具：**MIT。
- **该模型：**固定到 `florence-community/Florence-2-large` ——Microsoft 的 Florence-2 发布版本的官方 native-transformers 转换版本。**MIT**（hub 许可证标签已于 2026-08-19 验证）。可以进行商业使用。
- **为什么不使用 `microsoft/Florence-2-large`？**权重相同，许可证也相同，但原始存储库会提供预先配置的 native 版本，这些版本只能通过 `trust_remote_code` 加载——而此工具出于原则原因拒绝这样做。社区转换版本使用 transformers 内置的 Florence-2 类进行加载。
- **故意不提供：**Florence-2 微调动物园（MiaoshouAI PromptGen、CogFlorence、SD3/Flux 字幕生成器、Castollux）。它们的许可证未经验证；在获得批准之前，它们将不会被使用。可以将 `PLAIN_SIGHT_MODEL_ID` 重写为其中之一，但这会将许可证问题交由您自行决定。
- **没有远程代码：**该引擎仅使用 transformers 的*原生* Florence-2 支持——`trust_remote_code` 不会被传递，因此没有任何从 hub 获取的 Python 代码会执行。这需要 `transformers >= 4.51`。

## 安全性和信任

此工具仅在**本地运行**。

- **访问的数据：** 本地图像文件（只读）；HuggingFace 模型缓存（首次下载时写入一次）；以及它写入的文件——`.txt` 标题副文件，仅在调用方请求的位置（`out_dir` 或位于图像旁边），此外还有一个 JSON 清单，如果且仅当 `--manifest` / `manifest_path` 提供了一个显式路径时。只有在显式 `--overwrite` 的情况下才会替换现有的副文件。
- **运行时没有网络输出**——模型会在首次使用时下载一次，然后所有推理都是本地的。
- **没有远程代码执行**——仅使用本机 transformers 类；`trust_remote_code` 从未传递，因此不会执行从 hub 获取的 Python 代码。
- **不处理任何机密信息，也不进行遥测**——不会读取或发送任何内容到任何地方。
- **仅结构化错误**——原始堆栈跟踪不会到达 MCP 客户端或 CLI 用户。CLI 退出代码：0 表示正常；1 表示用户错误；2 表示运行时错误；3 表示部分成功。

完整策略：[SECURITY.md](SECURITY.md)。积极维护；支持的版本列在其中。

## 要求

- Python >= 3.10
- `transformers >= 4.51`（原生 Florence-2）
- 建议使用 CUDA GPU（FP16 时大约需要 2GB VRAM）；CPU 回退方案可用（速度较慢）
- 模型首次使用时，下载量约为 1.5 GB

## 开发

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# CI-safe suite (no model, no GPU) — this is what CI runs
pytest -m "not dogfood" -v

# Dogfood suite (real model + GPU, local only)
pytest -m dogfood -v

# Everything
pytest

# Full verify: imports, MCP tool surface, CI-safe tests, wheel + sdist build
bash verify.sh
```

测试通过标记进行选择，而不是通过文件名，因此无需修改 CI 配置即可选取新的 CI 安全测试文件。在 Windows 上，共享系统临时文件夹中的陈旧重新解析点可能会破坏 pytest 的默认临时根目录；`verify.sh` 通过 `PYTEST_DEBUG_TEMPROOT` 将其重定位，并且 `pythonpath = ["."]` 使控制台脚本和 `python -m pytest` 保持一致。

## 架构

```
engine.py    Standalone Florence-2 wrapper — no MCP dependency.
             Lazy-loads the model; validation runs BEFORE the load.
             Owns the provenance stamp and the shared logging setup.
             Importable directly: from plain_sight.engine import Florence2Engine

sidecars.py  The training-data contract, pure stdlib: basename pairing,
             bare concatenation, collision detection, atomic writes,
             directory expansion. Testable without torch.

server.py    FastMCP wrapper exposing engine methods as MCP tools.
             Thin layer: validation, error shaping, tool metadata.

cli.py       argparse CLI over the same engine (describe / ocr / batch /
             status / selftest). Structured errors, meaningful exit codes.
```

该架构有意借鉴了 [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp)——相同的引擎/服务器分离方式、相同的错误处理方式、相同的自检模式。与此类似的云端版本在 Comfy Cloud 上运行，作为 `caption-florence2-v1` 工作流程（每个任务一个图像的元数据附加项；该工具是批量处理的主要通道）。

## 许可

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建
