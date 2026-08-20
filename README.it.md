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

**Versione:** 1.1.0

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

Tre limiti specifici, indicati perché è facile scoprirli a proprie spese:

- **L'OCR non può segnalare l'assenza di testo.** Florence-2 emette una stringa decodificata per ogni immagine, comprese le immagini che non contengono affatto testo; una fotografia potrebbe restituire `'2'`. Questo output è lessicalmente indistinguibile da una corretta lettura di un numero. Di conseguenza, ogni risultato OCR contiene `absence_of_text_unreliable: true` (MCP) o una riga `[OCR_CAVEAT]` su stderr (CLI). plain-sight non sopprime né svuota mai il risultato, perché una breve lettura potrebbe essere valida; indica che il segnale non esiste.
- **Le didascalie descrivono; non verificano.** Una frase affermativa su un'immagine non è una prova della presenza dell'elemento descritto.
- **La riproducibilità si riferisce a una specifica revisione.** Il blocco della versione è ciò che rende significativa l'affermazione di determinismo nel tempo; vedere [Provenienza](#provenienza).

## Strumenti (MCP)

| Strumento | Cosa fa |
|------|-------------|
| `describe_image` | Un'immagine → descrizione in prosa (3 livelli di dettaglio) |
| `describe_batch` | N immagini → `.txt` file secondari di didascalie (la sezione del dataset) |
| `read_text` | OCR: decodifica il testo da un'immagine, con la precisazione sull'assenza di testo. |
| `sight_status` | Controllo dello stato: modello, dispositivo, revisione risolta, stato caricato. |
| `sight_selftest` | Descrive le immagini di riferimento incluse, verifica l'output |

Ogni payload che contiene l'output del modello contiene anche `model_id` e `revision_resolved`; vedere [Provenienza](#provenienza).

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

Flag `batch`: `--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite` · `--max-new-tokens` · `--manifest` · `--dry-run`. Esegui `plain-sight batch --help` per il testo completo; `plain-sight --help` documenta i codici di uscita e indica quale flusso contiene quali dati.

### Come appare un'esecuzione lunga

I progressi vengono inviati a **stderr**; i risultati vengono inviati a **stdout**, quindi `plain-sight describe x.png > caption.txt` funziona.

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

Il caricamento viene annunciato **prima** dell'inizio del lavoro, con il conteggio delle immagini che verranno effettivamente corredate di didascalie, in modo che una pausa non appaia mai durante l'esecuzione. Le immagini saltate vengono conteggiate nel segnale di heartbeat anziché stampate riga per riga; un'altra esecuzione su un set completato è silenziosa. I fallimenti rimangono una riga ciascuno.

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

- **Abbinamento esatto del nome base:** `img_0042.png` → `img_0042.txt`. Nessun suffisso numerico, a differenza del nodo SaveText di ComfyUI, che aggiunge `_00001`.
- **Concatenazione semplice:** il file secondario contiene `prefix + caption + suffix` senza alcun delimitatore inserito. Vuoi `"mcpt_style, <caption>"`? Inserisci la virgola e lo spazio nel prefisso.
- **I nomi base in conflitto vengono rifiutati, non uniti.** Due immagini i cui nomi base corrispondono (`img.png` e `img.jpg` in una cartella o file con lo stesso nome base provenienti da due cartelle sotto una `--out-dir`) richiederebbero un singolo `.txt`. plain-sight rifiuta l'intero batch prima di caricare il modello, identifica gli elementi problematici ed esce con codice `1`. Non rinominerà un file secondario per evitare il conflitto: i modelli vengono abbinati in base al nome base esatto, quindi una ridenominazione lascerebbe la didascalia orfana e l'immagine senza didascalia.
- **Le scritture sono atomiche.** Ogni file secondario viene scritto in un file temporaneo nella stessa directory e quindi spostato nella posizione corretta, in modo che un'interruzione non lasci mai una didascalia parziale nel percorso finale. Un file secondario che esiste ma è vuoto viene trattato come incompleto e viene rielaborato per aggiungere la didascalia.
- **Esecuzioni idempotenti:** i file secondari esistenti e non vuoti vengono ignorati e non comportano alcun costo, a meno che non si verifichino `--overwrite` / `overwrite=true`.
- **Deterministico:** `do_sample=false` + ricerca beam su una revisione bloccata; la rielaborazione di un'immagine invariata riproduce lo stesso testo, quindi le differenze hanno significato.

## Provenienza

Il flusso del set di dati produce i dati di addestramento. Sei mesi dopo, la domanda è quale modello ha prodotto quali didascalie; quindi la risposta viaggia con l'output.

- **La revisione del modello è bloccata per impostazione predefinita a `4271c66b88cdbc05735372ec13b2360108de5317`.** Senza un blocco, HuggingFace si risolve in qualsiasi cosa la branch predefinita del repository punti attualmente; una rietichettatura silenziosa cambierebbe le didascalie con input invariati. Sovrascrivi con `PLAIN_SIGHT_MODEL_REVISION`.
- **Ogni payload di output indica i pesi.** `describe_image`, `read_text`, `describe_batch`, `sight_selftest` e le modalità CLI `--json` e il riepilogo del batch contengono tutti `model_id` e `revision_resolved`: la revisione che il modello caricato segnala effettivamente, non la costante richiesta. `sight_status` riporta entrambi i valori, quindi una discrepanza è visibile.
- **`--manifest PATH` scrive un record di esecuzione:** versione dello strumento, ID del modello, revisione richiesta e risolta, dispositivo, tipo di dati, livello di dettaglio, prefisso/suffisso, risultati e conteggi per immagine. È possibile attivarlo; non viene mai dedotto: non viene scritto alcun manifesto a meno che tu non fornisca un percorso e un percorso che entra in conflitto con un file secondario calcolato viene rifiutato. Contiene un timestamp, quindi, a differenza delle didascalie, non è riproducibile byte per byte.

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
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…` (bloccato) | Revisione del modello; il meccanismo alla base dell'affermazione di riproducibilità. |
| `PLAIN_SIGHT_MODEL_DIR` | Cache predefinita di HF | Directory della cache del modello |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda se disponibile, altrimenti cpu) | Dispositivo torch |
| `PLAIN_SIGHT_DTYPE` | `float16` su CUDA, precisione completa su CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Limite di generazione predefinito |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Larghezza del beam (decodifica deterministica) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | non impostato | Se è vero, carica il modello all'avvio del server |

**Registrazione:** solo stderr (stdout è il canale del protocollo MCP), nome del logger `plain_sight`. `PLAIN_SIGHT_LOG_LEVEL` viene rispettato su entrambe le superfici.

**Caricamento immediato:** con `PLAIN_SIGHT_EAGER_LOAD` impostato su true, il server MCP si carica all'avvio anziché alla prima chiamata. Un errore lì non interrompe mai l'importazione del server; viene segnalato da `sight_status` come `eager_load_error` e sollevato come un'eccezione `ToolError` alla prima chiamata dello strumento che richiede il modello.

**Prima chiamata:** il modello viene caricato in modo lazy: la prima chiamata a describe/OCR carica Florence-2 (~10–20 secondi su GPU; la prima chiamata scarica ~1,5 GB). Le chiamate successive sono di circa 1–2 secondi per immagine con `high` dettagli su una GPU moderna.

## Politica delle licenze

- **Questo strumento:** MIT.
- **Il modello:** fissato a `florence-community/Florence-2-large`: la conversione ufficiale native-transformers della versione Florence-2 di Microsoft. **MIT** (tag della licenza hub verificato il 2026-08-19). Uso commerciale consentito.
- **Perché non `microsoft/Florence-2-large`?** Gli stessi pesi, la stessa licenza MIT, ma i repository originali forniscono configurazioni pre-native che si caricano solo tramite `trust_remote_code`, cosa che questo strumento rifiuta per principio. La conversione della community viene caricata con le classi Florence-2 integrate di transformers.
- **Deliberatamente non offerto:** lo zoo dei modelli ottimizzati di Florence-2 (MiaoshouAI PromptGen, CogFlorence, didascalie SD3/Flux, Castollux). Le loro licenze non sono verificate; rimangono esclusi fino a quando non saranno chiarite. È possibile sovrascrivere `PLAIN_SIGHT_MODEL_ID` con uno di essi, ma la questione della licenza ricade su di te.
- **Nessun codice remoto:** il motore utilizza solo il supporto *nativo* Florence-2 di transformers: `trust_remote_code` non viene mai passato, quindi nessun Python scaricato dall'hub viene eseguito. Questo richiede `transformers >= 4.51`.

## Sicurezza e affidabilità

Questo strumento funziona **solo localmente**.

- **Dati toccati:** file immagine locali (sola lettura); la cache del modello HuggingFace (scritta una volta al primo download) e i file che scrive: didascalie secondarie `.txt`, solo dove lo chiama l'utente (`out_dir` o accanto all'immagine), più un manifesto JSON se e solo se `--manifest` / `manifest_path` fornisce un percorso esplicito. I file secondari esistenti vengono sostituiti solo con un'esplicita richiesta `--overwrite`.
- **Nessuna trasmissione di rete in fase di esecuzione:** il modello viene scaricato una sola volta al primo utilizzo, quindi tutta l'inferenza è locale.
- **Nessuna esecuzione di codice remoto:** solo classi transformer native; `trust_remote_code` non viene mai passato, quindi nessun Python recuperato dall'hub viene eseguito.
- **Nessuna gestione dei segreti, nessuna telemetria:** nulla viene letto o inviato da nessuna parte.
- **Solo errori strutturati:** le tracce di stack grezze non raggiungono mai i client MCP o gli utenti della CLI. Codici di uscita CLI: 0 ok · 1 errore utente · 2 errore in fase di esecuzione · 3 successo parziale.

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

# CI-safe suite (no model, no GPU) — this is what CI runs
pytest -m "not dogfood" -v

# Dogfood suite (real model + GPU, local only)
pytest -m dogfood -v

# Everything
pytest

# Full verify: imports, MCP tool surface, CI-safe tests, wheel + sdist build
bash verify.sh
```

I test selezionano per marcatore, non per nome file, quindi un nuovo file di test sicuro per CI viene rilevato senza toccare CI. Su Windows, un punto di rianalisi obsoleto nella directory temporanea condivisa del sistema può interrompere la radice temporanea predefinita di pytest; `verify.sh` lo sposta tramite `PYTEST_DEBUG_TEMPROOT` e `pythonpath = ["."]` mantiene in sincronia lo script della console e `python -m pytest`.

## Architettura

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

L'architettura è stata volutamente ripresa da [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp): stessa suddivisione tra motore e server, stesso metodo di gestione degli errori, stesso schema di autotest. Una versione per il cloud dello stesso progetto è in esecuzione su Comfy Cloud come flusso di lavoro `caption-florence2-v1` (con metadati che indicano un'immagine per ogni operazione; questo strumento rappresenta la parte principale del processo).

## Licenza

MIT

---

Realizzato da [MCP Tool Shop](https://mcp-tool-shop.github.io/)
