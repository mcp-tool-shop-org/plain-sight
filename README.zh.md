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

**版本：**1.0.0

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

## 工具（MCP）

| 工具 | 它的作用 |
|------|-------------|
| `describe_image` | 一张图像 → 散文描述（3 个细节级别） |
| `describe_batch` | N 张图像 → `.txt` 字幕文件（数据集通道） |
| `read_text` | OCR — 从图像中提取可见文本 |
| `sight_status` | 健康检查：模型、设备、加载状态 |
| `sight_selftest` | 描述捆绑的参考图像，进行输出的合理性检查 |

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

# OCR
plain-sight ocr screenshot.png

# The dataset lane: caption a directory into .txt sidecars with a trigger token
plain-sight batch ./dataset --prefix "mcpt_style, " --detail high

# Re-runs are idempotent — existing sidecars are skipped unless you --overwrite
plain-sight batch ./dataset --prefix "mcpt_style, " --overwrite
```

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
- **简单连接：**字幕文件中包含 `prefix + caption + suffix`，不插入任何分隔符。想要 `"mcpt_style, <caption>"`？将逗号空格放在前缀中。
- **幂等重复运行：**除非 `--overwrite` / `overwrite=true`，否则跳过现有的字幕文件（并且不会产生任何费用）。
- **确定性：** `do_sample=false` + 集束搜索——重新对未更改的图像进行字幕处理，可以重现相同的文本，因此差异是有意义的。

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
| `PLAIN_SIGHT_MODEL_DIR` | HF 默认缓存 | 模型缓存目录 |
| `PLAIN_SIGHT_DEVICE` | `auto`（如果可用，则使用 cuda；否则使用 cpu） | torch 设备 |
| `PLAIN_SIGHT_DTYPE` | `float16` 在 CUDA 上，在 CPU 上使用完全精度 | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | 默认生成上限 |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | 集束宽度（确定性解码） |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | 未设置 | 如果为真，则在服务器启动时加载模型 |

**日志记录：**仅使用 stderr（stdout 是 MCP 协议通道），logger 名称 `plain_sight`。

**首次调用：**模型会延迟加载——第一次 describe/OCR 调用会加载 Florence-2（GPU 上大约需要 10–20 秒；第一次调用会下载约 1.5 GB）。后续调用的速度约为每张图像 1–2 秒，细节级别为 `high`。

## 许可证策略

- **此工具：**MIT。
- **该模型：**固定到 `florence-community/Florence-2-large` ——Microsoft 的 Florence-2 发布版本的官方 native-transformers 转换版本。**MIT**（hub 许可证标签已于 2026-08-19 验证）。可以进行商业使用。
- **为什么不使用 `microsoft/Florence-2-large`？**权重相同，许可证也相同，但原始存储库会提供预先配置的 native 版本，这些版本只能通过 `trust_remote_code` 加载——而此工具出于原则原因拒绝这样做。社区转换版本使用 transformers 内置的 Florence-2 类进行加载。
- **故意不提供：**Florence-2 微调动物园（MiaoshouAI PromptGen、CogFlorence、SD3/Flux 字幕生成器、Castollux）。它们的许可证未经验证；在获得批准之前，它们将不会被使用。可以将 `PLAIN_SIGHT_MODEL_ID` 重写为其中之一，但这会将许可证问题交由您自行决定。
- **没有远程代码：**该引擎仅使用 transformers 的*原生* Florence-2 支持——`trust_remote_code` 不会被传递，因此没有任何从 hub 获取的 Python 代码会执行。这需要 `transformers >= 4.51`。

## 安全性和信任

此工具仅在**本地运行**。

- **涉及的数据：**本地图像文件（只读）；HuggingFace 模型缓存（首次下载时写入一次）；`.txt` 字幕文件——这是它唯一会写入的文件，并且仅在调用者要求的情况下（`out_dir` 或位于图像旁边），并且现有的字幕文件只有在明确 `--overwrite` 的情况下才会替换。
- **运行时没有网络外发**——模型会在首次使用时下载一次，然后所有推理都在本地进行。
- **没有远程代码执行**——仅使用 native transformers 类；`trust_remote_code` 不会被传递，因此没有任何从 hub 获取的 Python 代码会执行。
- **不处理任何密钥，也没有遥测数据**——不会读取或发送任何内容。
- **仅提供结构化错误**——原始堆栈跟踪永远不会到达 MCP 客户端或 CLI 用户。CLI 退出代码：0 表示正常；1 表示用户错误；2 表示运行时错误；3 表示部分成功。

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

# CI-safe tests (no model, no GPU)
pytest tests/test_edge_cases.py -v

# Dogfood tests (real model + GPU)
pytest tests/test_dogfood.py -v

# Full verify: imports, edge tests, build
bash verify.sh
```

## 架构

```
engine.py    Standalone Florence-2 wrapper — no MCP dependency.
             Lazy-loads the model; validation runs BEFORE the load.
             Importable directly: from plain_sight.engine import Florence2Engine

sidecars.py  The training-data contract, pure stdlib: basename pairing,
             bare concatenation, directory expansion. Testable without torch.

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
