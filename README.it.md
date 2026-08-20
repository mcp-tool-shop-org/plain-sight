<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**Versione:** 1.0.0

**Un'IA descrive ciò che vede.** Generatore di descrizioni di immagini — server MCP + wrapper CLI
Florence-2 (MIT) per descrizioni in prosa, OCR e file secondari di didascalie per dataset LoRA.
Funziona localmente, è deterministico per impostazione predefinita.

È il fratello di [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp):

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| Lavoro | **judges** images | **describes** images |
| Modello | SigLIP2 (discriminativo) | Florence-2 (generativo) |
| Output | punteggi calibrati | file di prosa / OCR / didascalie |
| Modalità di errore | non può narrare | può inventare dettagli |
| Quando usarlo | "questa immagine contiene X?" | "cosa c'è in questa immagine?" |

## Accordo di onestà

Le descrizioni sono **generative**: fluide, generalmente accurate e capaci di inventare
dettagli. plain-sight rende l'output *riproducibile* (decodifica deterministica: la stessa
immagine produce la stessa didascalia), non *garantisce la veridicità*. Per verificare un'affermazione specifica su un'immagine, utilizzare `image_verify` di ai-eyes-mcp: misura, non narra. I due strumenti sono famiglie di modelli diverse per progettazione, quindi uno può controllare l'altro.

## Strumenti (MCP)

| Strumento | Cosa fa |
|------|-------------|
| `describe_image` | Un'immagine → descrizione in prosa (3 livelli di dettaglio) |
| `describe_batch` | N immagini → `.txt` file secondari di didascalie (la sezione del dataset) |
| `read_text` | OCR: estrae il testo visibile da un'immagine |
| `sight_status` | Controllo dello stato: modello, dispositivo, stato caricato |
| `sight_selftest` | Descrive le immagini di riferimento incluse, verifica l'output |

## Guida rapida

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

Oppure eseguilo come modulo: `python -m plain_sight`

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

### Configurazione Claude Code

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

## L'accordo sulle didascalie (sezione del dataset)

Creato per i set di addestramento LoRA (style-dataset-lab e simili):

- **Abbinamento esatto dei nomi base:** `img_0042.png` → `img_0042.txt`. Nessun suffisso numerico, a differenza del nodo SaveText di ComfyUI, che aggiunge `_00001`.
- **Concatenazione semplice:** il file secondario contiene `prefix + caption + suffix` senza alcun delimitatore inserito. Vuoi `"mcpt_style, <caption>"`? Metti la virgola e lo spazio nel prefisso.
- **Esecuzioni idempotenti:** i file secondari esistenti vengono ignorati (e non costano nulla) a meno che non vengano modificati `--overwrite` / `overwrite=true`.
- **Deterministico:** `do_sample=false` + ricerca beam: la ripetizione della didascalia di un'immagine invariata riproduce lo stesso testo, quindi le differenze hanno significato.

## Livelli di dettaglio

La scala delle attività nativa di Florence-2:

| Livello | Token dell'attività | Output |
|------|-----------|--------|
| `low` | `<CAPTION>` | una breve frase |
| `medium` | `<DETAILED_CAPTION>` | alcune frasi |
| `high` (predefinito) | `<MORE_DETAILED_CAPTION>` | un intero paragrafo |

`high` è un paragrafo, non un saggio: Florence-2 è un modello compatto (0,77B). Il suo punto di forza è la velocità e la licenza, non l'approfondimento critico. Se una didascalia sembra troncata, aumenta `max_new_tokens` (predefinito 1024, massimo 4096).

## Configurazione

| Variabile d'ambiente | Predefinito | Scopo |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | Modello HuggingFace |
| `PLAIN_SIGHT_MODEL_DIR` | Cache predefinita di HF | Directory della cache del modello |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda se disponibile, altrimenti cpu) | Dispositivo torch |
| `PLAIN_SIGHT_DTYPE` | `float16` su CUDA, precisione completa su CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Limite di generazione predefinito |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Larghezza del beam (decodifica deterministica) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | non impostato | Se è vero, carica il modello all'avvio del server |

**Logging:** solo stderr (stdout è il canale di protocollo MCP), nome del logger `plain_sight`.

**Prima chiamata:** il modello viene caricato in modo lazy: la prima chiamata a describe/OCR carica Florence-2 (~10–20 secondi su GPU; la prima chiamata scarica ~1,5 GB). Le chiamate successive sono di circa 1–2 secondi per immagine con `high` dettagli su una GPU moderna.

## Politica delle licenze

- **Questo strumento:** MIT.
- **Il modello:** fissato a `florence-community/Florence-2-large`: la conversione ufficiale native-transformers della versione Florence-2 di Microsoft. **MIT** (tag della licenza hub verificato il 2026-08-19). Uso commerciale consentito.
- **Perché non `microsoft/Florence-2-large`?** Gli stessi pesi, la stessa licenza MIT, ma i repository originali forniscono configurazioni pre-native che si caricano solo tramite `trust_remote_code`, cosa che questo strumento rifiuta per principio. La conversione della community viene caricata con le classi Florence-2 integrate di transformers.
- **Deliberatamente non offerto:** lo zoo dei modelli ottimizzati di Florence-2 (MiaoshouAI PromptGen, CogFlorence, didascalie SD3/Flux, Castollux). Le loro licenze non sono verificate; rimangono esclusi fino a quando non saranno chiarite. È possibile sovrascrivere `PLAIN_SIGHT_MODEL_ID` con uno di essi, ma la questione della licenza ricade su di te.
- **Nessun codice remoto:** il motore utilizza solo il supporto *nativo* Florence-2 di transformers: `trust_remote_code` non viene mai passato, quindi nessun Python scaricato dall'hub viene eseguito. Questo richiede `transformers >= 4.51`.

## Sicurezza e affidabilità

Questo strumento funziona **solo localmente**.

- **Dati elaborati:** file di immagini locali (sola lettura); la cache del modello HuggingFace (scritta una sola volta al primo download); `.txt` file secondari di didascalie: gli UNICI file che scrive, solo dove richiesto dal chiamante (`out_dir` o accanto all'immagine) e i file secondari esistenti vengono sostituiti solo con un esplicito `--overwrite`.
- **Nessuna trasmissione di dati in rete durante l'esecuzione:** il modello viene scaricato una sola volta al primo utilizzo, quindi tutta l'inferenza è locale.
- **Nessuna esecuzione di codice remoto:** solo classi transformers native; `trust_remote_code` non viene mai passato, quindi nessun Python scaricato dall'hub viene eseguito.
- **Nessuna gestione di segreti, nessuna telemetria:** nulla viene letto o inviato da nessuna parte.
- **Solo errori strutturati:** le tracce dello stack grezze non raggiungono i client MCP o gli utenti della CLI. Codici di uscita della CLI: 0 ok · 1 errore utente · 2 errore di runtime · 3 successo parziale.

Politica completa: [SECURITY.md](SECURITY.md). Mantenuta attivamente; le versioni supportate sono elencate lì.

## Requisiti

- Python >= 3.10
- `transformers >= 4.51` (Florence-2 nativo)
- Si consiglia una GPU CUDA (~2 GB di VRAM a FP16); è disponibile un fallback sulla CPU (più lento).
- Il download del modello richiede circa 1,5 GB al primo utilizzo.

## Sviluppo

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

## Architettura

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

L'architettura è stata volutamente ripresa da [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp): stessa suddivisione tra motore e server, stesso metodo di gestione degli errori, stesso schema di autotest. Una versione per il cloud dello stesso progetto è in esecuzione su Comfy Cloud come flusso di lavoro `caption-florence2-v1` (con metadati che indicano un'immagine per ogni operazione; questo strumento rappresenta la parte principale del processo).

## Licenza

MIT

---

Realizzato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
