<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**Version :** 1.0.0

**Une IA décrit ce qu’elle voit.** Générateur de descriptions d’images — serveur MCP + interface en ligne de commande
Florence-2 (MIT) pour les descriptions narratives, l’OCR et les fichiers secondaires de légendes pour les ensembles de données LoRA.
Fonctionne localement, déterministe par défaut.

Le frère de [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) :

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| Tâche | **judges** images | **describes** images |
| Modèle | SigLIP2 (discriminatif) | Florence-2 (génératif) |
| Sortie | scores calibrés | fichiers de description narrative / OCR / légendes |
| Mode d’échec | incapable de narrer | peut inventer des détails |
| À utiliser lorsque | « Cette image contient-elle X ? » | « Qu’y a-t-il dans cette image ? » |

## Contrat d’honnêteté

Les descriptions sont **génératives** : fluides, généralement précises et capables d’inventer des détails. plain-sight rend la sortie *reproductible* (décodage déterministe — la même image donne la même légende), mais pas *garantie vraie*. Pour vérifier une affirmation spécifique concernant une image, utilisez `image_verify` de ai-eyes-mcp ; il mesure, il ne narre pas. Les deux outils sont conçus pour être issus de familles de modèles différentes, ce qui permet à l’un de vérifier l’autre.

## Outils (MCP)

| Outil | Ce qu’il fait |
|------|-------------|
| `describe_image` | Une image → description narrative (3 niveaux de détail) |
| `describe_batch` | N images → `.txt` fichiers secondaires de légendes (la section des ensembles de données) |
| `read_text` | OCR — extrait le texte visible d’une image |
| `sight_status` | Vérification de l’état : modèle, appareil, état chargé |
| `sight_selftest` | Décrit les images de référence incluses et vérifie la sortie. |

## Démarrage rapide

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

Ou exécutez-le en tant que module : `python -m plain_sight`

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

### Configuration Claude Code

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

## Le contrat de légende (section des ensembles de données)

Conçu pour les ensembles d’entraînement LoRA (style-dataset-lab et autres) :

- **Appariement exact du nom de base :** `img_0042.png` → `img_0042.txt`. Pas de suffixe numérique, contrairement au nœud SaveText de ComfyUI, qui ajoute `_00001`.
- **Concaténation simple :** le fichier secondaire contient `prefix + caption + suffix` sans aucun délimiteur inséré. Vous voulez `"mcpt_style, <caption>"` ? Placez la virgule et l’espace dans le préfixe.
- **Exécutions idempotentes :** les fichiers secondaires existants sont ignorés (et ne coûtent rien) sauf si `--overwrite` / `overwrite=true`.
- **Déterministe :** `do_sample=false` + recherche par faisceau — la légende d’une image inchangée reproduit le même texte, de sorte que les différences ont une signification.

## Niveaux de détail

Échelle des tâches natives de Florence-2 :

| Niveau | Jeton de tâche | Sortie |
|------|-----------|--------|
| `low` | `<CAPTION>` | une courte phrase |
| `medium` | `<DETAILED_CAPTION>` | quelques phrases |
| `high` (par défaut) | `<MORE_DETAILED_CAPTION>` | un paragraphe complet |

`high` est un paragraphe, pas un essai — Florence-2 est un modèle compact (0,77 milliards de paramètres). Son atout réside dans le débit et la licence, et non dans la profondeur d’un critique d’art. Si une légende semble tronquée, augmentez `max_new_tokens` (par défaut : 1 024, maximum : 4 096).

## Configuration

| Variable d’environnement | Valeur par défaut | Objectif |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | Modèle HuggingFace |
| `PLAIN_SIGHT_MODEL_DIR` | Cache par défaut de HF | Répertoire du cache des modèles |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda si disponible, sinon cpu) | Périphérique torch |
| `PLAIN_SIGHT_DTYPE` | `float16` sur CUDA, précision complète sur CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Limite de génération par défaut |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Largeur du faisceau (décodage déterministe) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | non défini | Si la valeur est vraie, le modèle est chargé au démarrage du serveur. |

**Journalisation :** uniquement stderr (stdout est le canal de protocole MCP), nom du journal `plain_sight`.

**Premier appel :** le modèle se charge paresseusement — le premier appel à describe/OCR charge Florence-2 (~10 à 20 secondes sur GPU ; le tout premier appel télécharge ~1,5 Go). Les appels suivants durent environ 1 à 2 secondes par image avec `high` détails sur un GPU moderne.

## Posture de licence

- **Cet outil :** MIT.
- **Le modèle :** fixé à `florence-community/Florence-2-large` — la conversion native officielle de Microsoft pour Florence-2. Licence MIT (vérifiée le 19-08-2026). Utilisation commerciale autorisée.
- **Pourquoi pas `microsoft/Florence-2-large` ?** Les mêmes poids, la même licence MIT, mais les référentiels d’origine sont livrés avec des configurations pré-natives qui ne se chargent que via `trust_remote_code` — ce que cet outil refuse par principe. La conversion communautaire se charge à l’aide des classes Florence-2 intégrées de transformers.
- **Délibérément non proposé :** le zoo d’affinage de Florence-2 (MiaoshouAI PromptGen, CogFlorence, légende SD3/Flux, Castollux). Leurs licences ne sont pas vérifiées ; ils restent exclus jusqu’à ce qu’ils soient approuvés. Il est possible de remplacer `PLAIN_SIGHT_MODEL_ID` par l’un d’eux, mais cela vous incombe de vérifier la licence.
- **Pas de code distant :** le moteur n’utilise que la prise en charge *native* de Florence-2 de transformers — `trust_remote_code` n’est jamais transmis, de sorte qu’aucun Python téléchargé depuis le hub ne s’exécute jamais. Cela nécessite `transformers >= 4.51`.

## Sécurité et confiance

Cet outil fonctionne **exclusivement en local**.

- **Données traitées :** fichiers image locaux (en lecture seule) ; le cache de modèles HuggingFace (écrit une fois lors du premier téléchargement) ; `.txt` fichiers secondaires de légendes — les SEULS fichiers qu’il écrit, uniquement là où l’appelant l’a demandé (`out_dir` ou à côté de l’image), et les fichiers secondaires existants ne sont remplacés que sur demande explicite `--overwrite`.
- **Aucune sortie réseau pendant l’exécution** — le modèle se télécharge une fois lors de la première utilisation, puis toutes les inférences sont locales.
- **Pas d’exécution de code distant** — uniquement les classes natives de transformers ; `trust_remote_code` n’est jamais transmis, de sorte qu’aucun Python téléchargé depuis le hub ne s’exécute jamais.
- **Aucune gestion des secrets, aucun suivi** — rien n’est lu ou envoyé nulle part.
- **Seulement les erreurs structurées** — les traces de pile brutes n’atteignent jamais les clients MCP ou les utilisateurs de la CLI. Codes de sortie de la CLI : 0 ok · 1 erreur utilisateur · 2 erreur d’exécution · 3 succès partiel.

Politique complète : [SECURITY.md](SECURITY.md). Activement maintenu ; les versions prises en charge sont répertoriées ici.

## Exigences

- Python >= 3.10
- `transformers >= 4.51` (Florence-2 natif)
- Une carte graphique CUDA est recommandée (~2 Go de VRAM en FP16) ; une solution de repli sur CPU fonctionne (mais est plus lente).
- Le téléchargement du modèle représente environ 1,5 Go lors de la première utilisation.

## Développement

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

## Architecture

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

L’architecture a été délibérément empruntée à [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) — même séparation moteur/serveur, même gestion des erreurs, même schéma d’autotest. Une version « cloud » de la même application est exécutée sur Comfy Cloud en tant que flux de travail `caption-florence2-v1` (métadonnées avec une image par tâche ; cet outil constitue le principal canal).

## Licence

MIT

---

Créé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
