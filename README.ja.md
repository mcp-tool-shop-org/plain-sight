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

**バージョン:** 1.1.0

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

3つの具体的な制限事項。これらは、実際に試してみると簡単に理解できるため、以下に示します。

- **OCRはテキストが存在しないことを報告できません。** Florence-2は、まったくテキストを含まない画像を含むすべての画像に対してデコードされた文字列を出力します。写真の場合、`'2'`が返されることがあります。この出力は、数字の正しい読み方と構文的に区別できません。したがって、すべてのOCR結果には、
`absence_of_text_unreliable: true`（MCP）または標準エラー出力（CLI）に `[OCR_CAVEAT]`行が含まれます。plain-sightは、短い読み取りが実際のものである可能性があるため、結果を抑制したり空にしたりすることはありません。これは、信号が存在しないことを示します。
- **キャプションは説明するものであり、検証するものではありません。** 画像に関する確信のある文章は、記述されているものが実際に存在するという証拠ではありません。
- **再現性はリビジョンごとに異なります。** 特定のリビジョンに固定することで、時間経過に伴って決定性（再現性）の主張が意味を持つようになります。[Provenance](#provenance)を参照してください。

## ツール（MCP）

| ツール | 機能 |
|------|-------------|
| `describe_image` | 1つの画像 → 文章形式の記述（3つの詳細レベル） |
| `describe_batch` | N個の画像 → `.txt`キャプションサイドカー（データセット用） |
| `read_text` | OCR — 画像からテキストをデコードします。ただし、テキストが存在しない場合に関する注意点があります。 |
| `sight_status` | 健全性チェック：モデル、デバイス、解決されたリビジョン、ロードされた状態 |
| `sight_selftest` | バンドルされた参照画像を記述し、出力を妥当性確認する |

モデルの出力を含むすべてのペイロードには、`model_id`と
`revision_resolved`も含まれます。[Provenance](#provenance)を参照してください。

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

`batch`フラグ：`--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite`
· `--max-new-tokens` · `--manifest` · `--dry-run`。完全なテキストについては、`plain-sight batch --help`を実行してください。`plain-sight --help`は終了コードと、どのストリームが何を含んでいるかを記述しています。

### 長時間の実行の様子

進行状況は**標準エラー出力（stderr）**に、結果は**標準出力（stdout）**に出力されるため、`plain-sight describe x.png > caption.txt`で機能します。

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

処理が開始される前に、実際にキャプションが付けられる画像の数とともにロードが通知されるため、実行中に一時停止が発生することはありません。スキップされた画像は、1行ずつ出力するのではなく、ハートビートでカウントされます。完了したセットに対する再実行では、何も出力されません。エラーは1行ずつ出力されます。

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

- **正確なベース名ペアリング：** `img_0042.png` → `img_0042.txt`。カウンターサフィックスはありません。これは、ComfyUIのSaveTextノードとは異なり、後者に`_00001`を追加します。
- **単純な連結：** サイドカーファイルには、区切り文字が挿入されていない`prefix + caption + suffix`が含まれます。`"mcpt_style, <caption>"`が必要な場合は、カンマとスペースをプレフィックスに配置します。
- **衝突するステムは拒否され、決してマージされません。** 2つの画像のステム（ファイル名の基本部分）が一致する場合（1つのフォルダー内に`img.png`と`img.jpg`がある場合、または1つの`--out-dir`の下にある2つのフォルダーから同じステムのファイルがある場合）、それぞれに単一の`.txt`が割り当てられます。plain-sightは、モデルをロードする前に、これらのすべてのファイルを拒否し、問題のあるファイルを特定して、`1`で終了します。サイドカーの名前を変更して衝突を回避することはありません。トレーニングでは正確なステムを使用してペアリングするため、名前を変更するとキャプションと画像が関連付けられなくなり、画像にキャプションが付けられなくなります。
- **書き込みはアトミックです。** 各サイドカーファイルは、同じディレクトリ内のテンポラリファイルに書き込まれ、その後移動されるため、中断が発生しても、最終的なパスに不完全なキャプションが残ることはありません。存在し​​ていても空のサイドカーファイルは、未完成と見なされ、再キャプション処理が行われます。
- **べき等な再実行：** 既存の空でないサイドカーファイルはスキップされ、コストもかかりません（ただし、`--overwrite` / `overwrite=true`の場合は例外です）。
- **決定性：** `do_sample=false` + 固定されたリビジョンに対するビームサーチ。変更されていない画像を再キャプション処理すると、同じテキストが再現されるため、差分には意味があります。

## Provenance（来歴）

データセットのパイプラインは、トレーニングデータを生成します。6か月後、どのウェイトがどのキャプションを生成したのかという疑問が生じます。したがって、その答えは出力とともに伝達されます。

- **モデルのリビジョンはデフォルトで`4271c66b88cdbc05735372ec13b2360108de5317`に固定されています。** 固定されていない場合、HuggingFaceはリポジトリのデフォルトブランチが現在指しているものに解決され、静かに再タグ付けされると、変更されていない入力に対してキャプションが変更されます。`PLAIN_SIGHT_MODEL_REVISION`を使用してオーバーライドします。
- **すべての出力ペイロードには、使用されているウェイトの名前が含まれています。** `describe_image`、`read_text`、
`describe_batch`、`sight_selftest`、およびCLIの`--json`モードとバッチサマリーにはすべて、`model_id`と`revision_resolved`が含まれます。これは、ロードされたモデルが実際に報告するリビジョンであり、要求された定数ではありません。`sight_status`は両方を報告するため、不一致が見やすくなります。
- **`--manifest PATH`は実行レコードを書き込みます。** ツールバージョン、モデルID、要求されたリビジョンと解決されたリビジョン、デバイス、dtype、詳細レベル、プレフィックス/サフィックス、画像ごとの結果とカウントが含まれます。これはオプトインであり、推測されることはありません。パスが渡されない場合、マニフェストは書き込まれません。また、計算されたサイドカーファイルとパスが衝突する場合、拒否されます。タイムスタンプが含まれているため、キャプションとは異なり、バイト単位で完全に再現可能ではありません。

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
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…`（固定） | モデルリビジョン。これは、再現性の主張の根拠となるメカニズムです。 |
| `PLAIN_SIGHT_MODEL_DIR` | HFのデフォルトキャッシュ | モデルキャッシュディレクトリ |
| `PLAIN_SIGHT_DEVICE` | `auto`（利用可能な場合はcuda、それ以外の場合はcpu） | torchデバイス |
| `PLAIN_SIGHT_DTYPE` | `float16` CUDA上、CPU上はフル精度 | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | デフォルトの生成上限 |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | ビーム幅（決定的なデコード） |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | 設定なし | 真の場合、サーバー起動時にモデルをロードします。 |

**ロギング：** 標準エラー出力のみ（標準出力はMCPプロトコルチャネル）、ロガー名`plain_sight`。`PLAIN_SIGHT_LOG_LEVEL`は両方の場所で尊重されます。

**Eager load:** with `PLAIN_SIGHT_EAGER_LOAD` truthy, the MCP server loads at
start rather than on first call. A failure there never kills the server import —
it is reported by `sight_status` as `eager_load_error` and raised as a `ToolError`
on the first tool call that needs the model.

**初回呼び出し:** モデルは遅延ロードされます。最初のdescribe/OCR呼び出しでFlorence-2がロードされます（GPU上では約10〜20秒、初回のみ約1.5GBをダウンロードします）。その後の呼び出しは、最新のGPU上で`high`の詳細レベルの場合、画像あたり約1〜2秒です。

## ライセンスポリシー

- **このツール:** MIT。
- **モデル:** `florence-community/Florence-2-large`に固定 — MicrosoftのFlorence-2リリースの公式ネイティブtransformers変換。**MIT**（ハブリソースライセンスタグは2026年8月19日に確認済み）。商用利用可能。
- **なぜ`microsoft/Florence-2-large`ではないのか？** 同じ重み、同じMITライセンスですが、元のリポジトリには、`trust_remote_code`経由でのみロードできる事前ネイティブ構成が含まれています。このツールはその原則に反します。コミュニティによる変換は、transformersの組み込みFlorence-2クラスでロードされます。
- **意図的に提供しない:** Florence-2のファインチューン動物園（MiaoshouAI PromptGen、CogFlorence、SD3/Fluxキャプショナー、Castollux）。それらのライセンスは確認されていません。クリアされるまで除外します。`PLAIN_SIGHT_MODEL_ID`をそれらのいずれかにオーバーライドすることは可能ですが、ライセンスに関する責任はユーザーにあります。
- **リモートコードなし:** エンジンはtransformersの*ネイティブ*Florence-2サポートのみを使用します。`trust_remote_code`は渡されません。したがって、ハブから取得したPythonコードは実行されません。これは`transformers >= 4.51`が必要です。

## セキュリティと信頼性

このツールは**ローカルでのみ動作します**。

- **Data touched:** local image files (read-only); the HuggingFace model cache
  (written once on first download); and the files it writes — `.txt` caption
  sidecars, only where the caller asked (`out_dir` or next to the image), plus
  one JSON manifest if and only if `--manifest` / `manifest_path` supplies an
  explicit path. Existing sidecars are replaced only under explicit
  `--overwrite`.
- **No network egress at runtime** — the model downloads once on first use,
  then all inference is local.
- **No remote code execution** — native transformers classes only;
  `trust_remote_code` is never passed, so no hub-fetched Python ever executes.
- **No secrets handling, no telemetry** — nothing is read from or sent anywhere.
- **Structured errors only** — raw stack traces never reach MCP clients or
  CLI users. CLI exit codes: 0 ok · 1 user error · 2 runtime error ·
  3 partial success.

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

# CI-safe suite (no model, no GPU) — this is what CI runs
pytest -m "not dogfood" -v

# Dogfood suite (real model + GPU, local only)
pytest -m dogfood -v

# Everything
pytest

# Full verify: imports, MCP tool surface, CI-safe tests, wheel + sdist build
bash verify.sh
```

テストは、ファイル名ではなくマーカーによって選択されるため、新しいCIセーフなテストファイルが追加されても、CIに影響しません。Windowsでは、共有システムの一時ディレクトリにある古いリパースポイントが、pytestのデフォルトのテンポラリルートを壊す可能性があります。`verify.sh`は、これを`PYTEST_DEBUG_TEMPROOT`を使用して再配置し、`pythonpath = ["."]`はコンソールスクリプトと
`python -m pytest`を一致させます。

## アーキテクチャ

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

このアーキテクチャは、[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp)から意図的に借用したものである。同じエンジン／サーバー分割構造、同じエラー処理方法、同じ自己テストパターンを採用している。クラウド上で動作する同様のシステムが、Comfy Cloud上で`caption-florence2-v1`ワークフロー（1つの画像につき1つのジョブというメタデータ設定；このツールは大量処理に最適）として実行される。

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/)によって作成
