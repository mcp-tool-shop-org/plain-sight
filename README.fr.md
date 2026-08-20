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

**Version :** 1.1.0

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

Trois limites spécifiques sont mentionnés, car il est facile de les découvrir par l’expérience :

- **L’OCR ne peut pas signaler l’absence de texte.** Florence-2 émet une chaîne décodée pour chaque image, y compris les images qui ne contiennent aucun texte. Une photographie peut renvoyer `'2'`. Cette sortie est lexicalement indiscernable d’une lecture correcte d’un chiffre. Par conséquent, chaque résultat OCR comporte `absence_of_text_unreliable: true` (MCP) ou une ligne `[OCR_CAVEAT]` sur stderr (CLI). plain-sight ne supprime ni n’efface jamais le résultat, car une courte lecture peut être authentique : elle indique que le signal n’existe pas.
- **Les légendes décrivent ; elles ne vérifient pas.** Une phrase affirmative concernant une image n’est pas la preuve que l’élément décrit est présent.
- **La reproductibilité s’applique à chaque révision.** Le blocage est ce qui rend la revendication de déterminisme significative dans le temps ; voir [Provenance](#provenance).

## Outils (MCP)

| Outil | Ce qu’il fait |
|------|-------------|
| `describe_image` | Une image → description narrative (3 niveaux de détail) |
| `describe_batch` | N images → `.txt` fichiers secondaires de légendes (la section des ensembles de données) |
| `read_text` | OCR : décoder le texte d’une image, avec une réserve concernant l’absence de texte. |
| `sight_status` | Vérification de l’état : modèle, appareil, révision résolue, état chargé. |
| `sight_selftest` | Décrit les images de référence incluses et vérifie la sortie. |

Chaque charge utile qui contient la sortie du modèle contient également `model_id` et `revision_resolved` ; voir [Provenance](#provenance).

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

Indicateurs `batch` : `--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite` · `--max-new-tokens` · `--manifest` · `--dry-run`. Exécutez `plain-sight batch --help` pour obtenir le texte complet ; `plain-sight --help` documente les codes de sortie et indique quel flux contient quoi.

### À quoi ressemble une longue exécution

Les informations d’état sont envoyées à **stderr** ; les résultats sont envoyés à **stdout**, donc `plain-sight describe x.png > caption.txt` fonctionne.

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

Le chargement est annoncé **avant** le début du travail, avec le nombre d’images qui seront réellement légendées, de sorte qu’une pause n’apparaît jamais au milieu de l’exécution. Les images ignorées sont comptabilisées dans les informations d’état plutôt que d’être imprimées une ligne à la fois : une nouvelle exécution sur un ensemble terminé est silencieuse. Les échecs restent affichés une ligne à la fois.

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

- **Appariement exact du nom de base :** `img_0042.png` → `img_0042.txt`. Pas de suffixe numérique ; contrairement au nœud SaveText de ComfyUI, qui ajoute `_00001`.
- **Concaténation simple :** le fichier secondaire contient `prefix + caption + suffix` sans aucun délimiteur inséré. Vous voulez `"mcpt_style, <caption>"` ? Placez la virgule et l’espace dans le préfixe.
- **Les noms de fichiers en conflit sont refusés, jamais fusionnés.** Deux images dont les noms correspondent (`img.png` et `img.jpg` dans un même dossier, ou des fichiers portant le même nom provenant de deux dossiers sous un même `--out-dir`) prétendraient avoir un seul `.txt`. plain-sight refuse l’ensemble avant de charger le modèle, identifie les éléments problématiques et quitte `1`. Il ne renommera pas un fichier secondaire pour éviter le conflit : les formateurs appairent par nom exact, donc un renommage orphelinerait la légende et laisserait l’image sans légende.
- **Les écritures sont atomiques.** Chaque fichier secondaire est écrit dans un fichier temporaire dans le même répertoire, puis déplacé à sa place, de sorte qu’une interruption n’entraîne jamais une légende partielle au chemin final. Un fichier secondaire qui existe mais est vide est traité comme non terminé et est relégendé.
- **Nouvelles exécutions idempotentes :** les fichiers secondaires existants et non vides sont ignorés, ce qui ne coûte rien, sauf si `--overwrite` / `overwrite=true`.
- **Déterministe :** `do_sample=false` + recherche par faisceau sur une révision bloquée : la relégendation d’une image inchangée reproduit le même texte, de sorte que les différences ont un sens.

## Provenance

Le processus du jeu de données produit des données d’entraînement. Six mois plus tard, la question est : quels poids ont produit quelles légendes ? La réponse est donc transmise avec la sortie.

- **La révision du modèle est bloquée** par défaut à `4271c66b88cdbc05735372ec13b2360108de5317`. Sans blocage, HuggingFace se résout à ce que la branche par défaut du dépôt pointe actuellement, et un changement silencieux modifierait les légendes pour des entrées inchangées. Remplacez par `PLAIN_SIGHT_MODEL_REVISION`.
- **Chaque charge utile de sortie indique les poids.** `describe_image`, `read_text`, `describe_batch`, `sight_selftest`, et les modes `--json` du CLI ainsi que le résumé du lot contiennent tous `model_id` et `revision_resolved` : la révision que le modèle chargé signale réellement, et non la constante qui a été demandée. `sight_status` indique les deux, de sorte qu’une divergence est visible.
- **`--manifest PATH` écrit un enregistrement d’exécution** : version de l’outil, ID du modèle, révision demandée et résolue, appareil, type de données, niveau de détail, préfixe/suffixe, résultats et décomptes par image. Optionnel et jamais inféré : aucun manifeste n’est écrit à moins que vous ne fournissiez un chemin, et un chemin qui entre en conflit avec un fichier secondaire calculé est refusé. Il contient un horodatage, de sorte qu’il n’est pas reproductible au niveau des octets contrairement aux légendes.

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
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…` (bloqué) | Révision du modèle ; le mécanisme qui sous-tend la revendication de reproductibilité. |
| `PLAIN_SIGHT_MODEL_DIR` | Cache par défaut de HF | Répertoire du cache des modèles |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda si disponible, sinon cpu) | Périphérique torch |
| `PLAIN_SIGHT_DTYPE` | `float16` sur CUDA, précision complète sur CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Limite de génération par défaut |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Largeur du faisceau (décodage déterministe) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | non défini | Si la valeur est vraie, le modèle est chargé au démarrage du serveur. |

**Journalisation :** uniquement stderr (stdout est le canal de protocole MCP), nom du journal `plain_sight`. `PLAIN_SIGHT_LOG_LEVEL` est respecté sur les deux surfaces.

**Chargement immédiat :** si `PLAIN_SIGHT_EAGER_LOAD` est vrai, le serveur MCP se charge au démarrage plutôt qu’au premier appel. Une erreur à ce stade ne tue jamais l’importation du serveur : elle est signalée par `sight_status` en tant que `eager_load_error` et déclenchée sous forme de `ToolError` lors du premier appel d’outil qui nécessite le modèle.

**Premier appel :** le modèle se charge paresseusement — le premier appel à describe/OCR charge Florence-2 (~10 à 20 secondes sur GPU ; le tout premier appel télécharge ~1,5 Go). Les appels suivants durent environ 1 à 2 secondes par image avec `high` détails sur un GPU moderne.

## Posture de licence

- **Cet outil :** MIT.
- **Le modèle :** fixé à `florence-community/Florence-2-large` — la conversion native officielle de Microsoft pour Florence-2. Licence MIT (vérifiée le 19-08-2026). Utilisation commerciale autorisée.
- **Pourquoi pas `microsoft/Florence-2-large` ?** Les mêmes poids, la même licence MIT, mais les référentiels d’origine sont livrés avec des configurations pré-natives qui ne se chargent que via `trust_remote_code` — ce que cet outil refuse par principe. La conversion communautaire se charge à l’aide des classes Florence-2 intégrées de transformers.
- **Délibérément non proposé :** le zoo d’affinage de Florence-2 (MiaoshouAI PromptGen, CogFlorence, légende SD3/Flux, Castollux). Leurs licences ne sont pas vérifiées ; ils restent exclus jusqu’à ce qu’ils soient approuvés. Il est possible de remplacer `PLAIN_SIGHT_MODEL_ID` par l’un d’eux, mais cela vous incombe de vérifier la licence.
- **Pas de code distant :** le moteur n’utilise que la prise en charge *native* de Florence-2 de transformers — `trust_remote_code` n’est jamais transmis, de sorte qu’aucun Python téléchargé depuis le hub ne s’exécute jamais. Cela nécessite `transformers >= 4.51`.

## Sécurité et confiance

Cet outil fonctionne **exclusivement en local**.

- **Données utilisées :** fichiers image locaux (en lecture seule) ; la mémoire cache du modèle HuggingFace (écrite une fois au premier téléchargement) et les fichiers qu’il écrit : `.txt` fichiers secondaires de légende, uniquement là où l’appelant l’a demandé (`out_dir` ou à côté de l’image), plus un manifeste JSON si et seulement si `--manifest` / `manifest_path` fournit un chemin explicite. Les fichiers secondaires existants ne sont remplacés que sous `--overwrite` explicite.
- **Aucune sortie réseau au moment de l’exécution** : le modèle se télécharge une fois lors de la première utilisation, puis toutes les inférences sont locales.
- **Aucune exécution de code à distance** : uniquement les classes natives de transformateurs ; `trust_remote_code` n’est jamais transmis, donc aucun Python récupéré sur le hub ne s’exécute jamais.
- **Aucune gestion des secrets, aucune télémétrie** : rien n’est lu ou envoyé nulle part.
- **Seules les erreurs structurées** : les traces de pile brutes n’atteignent jamais les clients MCP ni les utilisateurs du CLI. Codes de sortie du CLI : 0 ok, 1 erreur utilisateur, 2 erreur d’exécution, 3 succès partiel.

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

# CI-safe suite (no model, no GPU) — this is what CI runs
pytest -m "not dogfood" -v

# Dogfood suite (real model + GPU, local only)
pytest -m dogfood -v

# Everything
pytest

# Full verify: imports, MCP tool surface, CI-safe tests, wheel + sdist build
bash verify.sh
```

Les tests sélectionnent par marqueur, et non par nom de fichier, de sorte qu’un nouveau fichier de test compatible CI est pris en charge sans toucher à CI. Sous Windows, un point de réanalyse obsolète dans le répertoire temp système partagé peut perturber la racine temporaire par défaut de pytest ; `verify.sh` le déplace via `PYTEST_DEBUG_TEMPROOT`, et `pythonpath = ["."]` maintient le script de console et `python -m pytest` en accord.

## Architecture

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

L’architecture a été délibérément empruntée à [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) — même séparation moteur/serveur, même gestion des erreurs, même schéma d’autotest. Une version « cloud » de la même application est exécutée sur Comfy Cloud en tant que flux de travail `caption-florence2-v1` (métadonnées avec une image par tâche ; cet outil constitue le principal canal).

## Licence

MIT

---

Créé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
