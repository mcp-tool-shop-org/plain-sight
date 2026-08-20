<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**バージョン:** 1.0.0

**AIが目にするものを描写します。** 生成型画像記述ツール — MCPサーバー + CLIラッパー
文章形式の記述、OCR、およびLoRAデータセットキャプションサイドカーにはFlorence-2（MIT）を使用。
ローカルで実行され、デフォルトでは決定的な結果が得られます。

[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp)の兄弟プロジェクトです。

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| ジョブ | **judges** images | **describes** images |
| モデル | SigLIP2（識別的） | Florence-2（生成的） |
| 出力 | 調整されたスコア | 文章 / OCR / キャプションファイル |
| 失敗モード | 描写できない | 詳細を捏造する可能性がある |
| 使用場面 | 「この画像にはXが含まれていますか？」 | 「この画像には何が写っていますか？」 |

## 誠実性の契約

記述は**生成的**です。流暢で、通常は正確であり、詳細を創作する能力があります。plain-sightは出力を*再現可能*にします（決定的なデコード — 同じ画像からは同じキャプションが生成されますが、必ずしも*真実であるとは限りません*）。画像の特定の主張を検証するには、ai-eyes-mcpの`image_verify`を使用してください。これは測定を行い、描写は行いません。これらの2つのツールは設計上、異なるモデルファミリーであり、互いにチェックすることができます。

## ツール（MCP）

| ツール | 機能 |
|------|-------------|
| `describe_image` | 1つの画像 → 文章形式の記述（3つの詳細レベル） |
| `describe_batch` | N個の画像 → `.txt`キャプションサイドカー（データセット用） |
| `read_text` | OCR — 画像から可視テキストを抽出 |
| `sight_status` | 健全性チェック：モデル、デバイス、ロード状態 |
| `sight_selftest` | バンドルされた参照画像を記述し、出力を妥当性確認する |

## クイックスタート

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

または、モジュールとして実行します：`python -m plain_sight`

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

### Claude Code設定

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

## キャプション契約（データセット用）

LoRAトレーニングセット（style-dataset-labおよび関連プロジェクト）向けに構築：

- **正確なベース名ペアリング:** `img_0042.png` → `img_0042.txt`。カウンターサフィックスは不要です。ComfyUIのSaveTextノードとは異なり、`_00001`を付加します。
- **単純な連結:** サイドカーには区切り文字なしで`prefix + caption + suffix`が含まれます。`"mcpt_style, <caption>"`が必要な場合は、先頭にカンマとスペースを追加してください。
- **べき等な再実行:** 既存のサイドカーはスキップされます（コストはかかりません）。ただし、`--overwrite` / `overwrite=true`の場合は例外です。
- **決定性:** `do_sample=false` + ビームサーチ — 変更されていない画像を再キャプションすると、同じテキストが再現されるため、差分には意味があります。

## 詳細レベル

Florence-2のネイティブタスクラダー：

| レベル | タスクトークン | 出力 |
|------|-----------|--------|
| `low` | `<CAPTION>` | 短い文1つ |
| `medium` | `<DETAILED_CAPTION>` | いくつかの文 |
| `high`（デフォルト） | `<MORE_DETAILED_CAPTION>` | 完全な段落 |

`high`は段落であり、エッセイではありません。Florence-2はコンパクトなモデル（0.77Bパラメータ）です。その強みはスループットとライセンスにあり、批評的な深さにはありません。キャプションが途中で切れているように見える場合は、`max_new_tokens`を大きくしてください（デフォルトは1024、最大は4096）。

## 設定

| 環境変数 | デフォルト値 | 目的 |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | HuggingFaceモデル |
| `PLAIN_SIGHT_MODEL_DIR` | HFのデフォルトキャッシュ | モデルキャッシュディレクトリ |
| `PLAIN_SIGHT_DEVICE` | `auto`（利用可能な場合はcuda、それ以外の場合はcpu） | torchデバイス |
| `PLAIN_SIGHT_DTYPE` | `float16` CUDA上、CPU上はフル精度 | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | デフォルトの生成上限 |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | ビーム幅（決定的なデコード） |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | 設定なし | 真の場合、サーバー起動時にモデルをロードします。 |

**ロギング:** stderrのみ（stdoutはMCPプロトコルチャネルです）。ロガー名：`plain_sight`。

**初回呼び出し:** モデルは遅延ロードされます。最初のdescribe/OCR呼び出しでFlorence-2がロードされます（GPU上では約10〜20秒、初回のみ約1.5GBをダウンロードします）。その後の呼び出しは、最新のGPU上で`high`の詳細レベルの場合、画像あたり約1〜2秒です。

## ライセンスポリシー

- **このツール:** MIT。
- **モデル:** `florence-community/Florence-2-large`に固定 — MicrosoftのFlorence-2リリースの公式ネイティブtransformers変換。**MIT**（ハブリソースライセンスタグは2026年8月19日に確認済み）。商用利用可能。
- **なぜ`microsoft/Florence-2-large`ではないのか？** 同じ重み、同じMITライセンスですが、元のリポジトリには、`trust_remote_code`経由でのみロードできる事前ネイティブ構成が含まれています。このツールはその原則に反します。コミュニティによる変換は、transformersの組み込みFlorence-2クラスでロードされます。
- **意図的に提供しない:** Florence-2のファインチューン動物園（MiaoshouAI PromptGen、CogFlorence、SD3/Fluxキャプショナー、Castollux）。それらのライセンスは確認されていません。クリアされるまで除外します。`PLAIN_SIGHT_MODEL_ID`をそれらのいずれかにオーバーライドすることは可能ですが、ライセンスに関する責任はユーザーにあります。
- **リモートコードなし:** エンジンはtransformersの*ネイティブ*Florence-2サポートのみを使用します。`trust_remote_code`は渡されません。したがって、ハブから取得したPythonコードは実行されません。これは`transformers >= 4.51`が必要です。

## セキュリティと信頼性

このツールは**ローカルでのみ動作します**。

- **アクセスされるデータ:** ローカルの画像ファイル（読み取り専用）。HuggingFaceモデルキャッシュ（初回ダウンロード時に1回書き込まれます）。`.txt`キャプションサイドカー — これが唯一書き込むファイルであり、呼び出し元が要求した場所（`out_dir`または画像の隣）にのみ書き込まれ、既存のサイドカーは明示的な`--overwrite`でのみ置き換えられます。
- **実行時のネットワークへのデータ送信はありません** — モデルは初回使用時に一度ダウンロードされ、その後すべての推論はローカルで行われます。
- **リモートコードの実行はありません** — ネイティブtransformersクラスのみを使用します。`trust_remote_code`は渡されないため、ハブから取得したPythonコードは実行されません。
- **機密情報の処理やテレメトリーはありません** — どこにもデータを読み込んだり送信したりしません。
- **構造化されたエラーのみ** — 生のスタックトレースはMCPクライアントまたはCLIユーザーに到達することはありません。CLI終了コード：0 OK · 1 ユーザーエラー · 2 ランタイムエラー · 3 部分的な成功。

完全なポリシー：[SECURITY.md](SECURITY.md)。積極的にメンテナンスされています。サポートされているバージョンはそこにリストされています。

## 要件

- Python >= 3.10
- `transformers >= 4.51`（ネイティブのFlorence-2）
- CUDA GPUを推奨（FP16で約2GBのVRAM）；CPUでの代替も可能だが、処理速度は遅くなる
- モデルの初回使用時のダウンロードサイズは約1.5GB

## 開発

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

## アーキテクチャ

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

このアーキテクチャは、[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp)から意図的に借用したものである。同じエンジン／サーバー分割構造、同じエラー処理方法、同じ自己テストパターンを採用している。クラウド上で動作する同様のシステムが、Comfy Cloud上で`caption-florence2-v1`ワークフロー（1つの画像につき1つのジョブというメタデータ設定；このツールは大量処理に最適）として実行される。

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/)によって作成
