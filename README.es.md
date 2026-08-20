<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**Versión:** 1.1.0

**Una IA dice lo que ve.** Generador de descripciones de imágenes: servidor MCP + interfaz de línea de comandos (CLI).
Florence-2 (MIT) para descripciones en prosa, OCR y archivos complementarios de subtítulos para conjuntos de datos LoRA.
Se ejecuta localmente, determinista por defecto.

Es el hermano de [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp):

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| Tarea | **judges** images | **describes** images |
| Modelo | SigLIP2 (discriminativo) | Florence-2 (generativo) |
| Salida | puntuaciones calibradas | archivos de prosa / OCR / subtítulos |
| Modo de fallo | no puede narrar | puede alucinar detalles |
| Úsalo cuando | "¿contiene esta imagen X?" | "¿qué hay en esta imagen?" |

## Acuerdo de honestidad

Las descripciones son **generativas**: fluidas, generalmente precisas y capaces de inventar detalles. plain-sight hace que la salida sea *reproducible* (decodificación determinista: la misma imagen produce el mismo subtítulo), no *garantizada como verdadera*. Para verificar una afirmación específica sobre una imagen, use `image_verify` de ai-eyes-mcp; mide, no narra. Las dos herramientas son familias de modelos diferentes por diseño, por lo que una puede verificar a la otra.

Tres límites específicos, que se indican porque es fácil descubrirlos por las malas:

- **OCR no puede informar de la ausencia de texto.** Florence-2 emite una cadena decodificada para cada imagen, incluidas las imágenes que no contienen ningún texto; una fotografía podría devolver `'2'`. Esta salida es léxicamente indistinguible de una lectura correcta de un número. Por lo tanto, cada resultado de OCR lleva `absence_of_text_unreliable: true` (MCP) o una línea `[OCR_CAVEAT]` en stderr (CLI). plain-sight nunca suprime ni vacía el resultado, porque una lectura corta puede ser genuina; te indica que la señal no existe.
- **Las descripciones describen; no verifican.** Una afirmación contundente sobre una imagen no es evidencia de que el objeto descrito esté presente.
- **La reproducibilidad se aplica por versión.** Fijar la versión es lo que hace que la afirmación de determinismo tenga sentido a lo largo del tiempo; consulte [Provenance](#provenance).

## Herramientas (MCP)

| Herramienta | Qué hace |
|------|-------------|
| `describe_image` | Una imagen → descripción en prosa (3 niveles de detalle) |
| `describe_batch` | N imágenes → `.txt` archivos complementarios de subtítulos (la ruta del conjunto de datos) |
| `read_text` | OCR: decodificar texto de una imagen, con una advertencia sobre la ausencia de texto. |
| `sight_status` | Comprobación de estado: modelo, dispositivo, versión resuelta, estado cargado. |
| `sight_selftest` | Describe las imágenes de referencia incluidas, verifica la salida |

Cada carga útil que contiene la salida del modelo también contiene `model_id` y `revision_resolved`; consulte [Provenance](#provenance).

## Primeros pasos

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

O ejecútalo como un módulo: `python -m plain_sight`

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

Indicadores `batch`: `--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite` · `--max-new-tokens` · `--manifest` · `--dry-run`. Ejecute `plain-sight batch --help` para obtener el texto completo; `plain-sight --help` documenta los códigos de salida y qué flujo contiene qué información.

### Cómo se ve una ejecución prolongada

El progreso se envía a **stderr**; los resultados se envían a **stdout**, por lo que `plain-sight describe x.png > caption.txt` funciona.

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

La carga se anuncia **antes** de que comience el trabajo, con el recuento de las imágenes que realmente tendrán una descripción, por lo que nunca aparece una pausa en medio de la ejecución. Las imágenes omitidas se cuentan en el latido del corazón en lugar de imprimirse línea por línea; una nueva ejecución sobre un conjunto terminado es silenciosa. Los errores permanecen en una línea cada uno.

### Configuración de Claude Code

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

## El acuerdo del subtítulo (ruta del conjunto de datos)

Diseñado para conjuntos de entrenamiento LoRA (style-dataset-lab y similares):

- **Emparejamiento exacto del nombre base:** `img_0042.png` → `img_0042.txt`. Sin sufijo contador, a diferencia del nodo SaveText de ComfyUI, que agrega `_00001`.
- **Concatenación simple:** el archivo complementario contiene `prefix + caption + suffix` sin ningún delimitador insertado. ¿Quiere `"mcpt_style, <caption>"`? Coloque la coma y el espacio en el prefijo.
- **Se rechazan los nombres base coincidentes; nunca se fusionan.** Dos imágenes cuyos nombres base coincidan (`img.png` y `img.jpg` en una carpeta, o archivos con el mismo nombre base de dos carpetas bajo un `--out-dir`) reclamarían un único `.txt`. plain-sight rechaza todo el lote antes de cargar el modelo, nombra a los infractores y sale con `1`. No cambiará el nombre de un archivo complementario para evitar la colisión: los entrenadores se emparejan por el nombre base exacto, por lo que un cambio de nombre dejaría la descripción huérfana y la imagen sin describir.
- **Las escrituras son atómicas.** Cada archivo complementario se escribe en un archivo temporal en el mismo directorio y luego se mueve a su lugar, por lo que una interrupción nunca deja una descripción parcial en la ruta final. Un archivo complementario que existe pero está vacío se trata como incompleto y se vuelve a describir.
- **Nuevas ejecuciones idempotentes:** los archivos complementarios existentes no vacíos se omiten y no tienen costo, a menos que `--overwrite` / `overwrite=true`.
- **Determinista:** `do_sample=false` + búsqueda de haz contra una versión fija; volver a describir una imagen sin cambios reproduce el mismo texto, por lo que las diferencias significan algo.

## Procedencia

El flujo del conjunto de datos produce datos de entrenamiento. Seis meses después, la pregunta es qué pesos produjeron qué descripciones; por lo tanto, la respuesta viaja con la salida.

- **La versión del modelo está fijada** por defecto a `4271c66b88cdbc05735372ec13b2360108de5317`. Sin una fijación, HuggingFace se resuelve en lo que sea que la rama predeterminada del repositorio apunte actualmente, y un cambio silencioso volvería a describir imágenes con entradas sin cambios. Anule con `PLAIN_SIGHT_MODEL_REVISION`.
- **Cada carga útil de salida nombra los pesos.** `describe_image`, `read_text`, `describe_batch`, `sight_selftest` y los modos `--json` del CLI y el resumen por lotes contienen `model_id` y `revision_resolved`: la versión que el modelo cargado realmente informa, no la constante que se solicitó. `sight_status` informa ambos, por lo que una discrepancia es visible.
- **`--manifest PATH` escribe un registro de ejecución:** versión de la herramienta, ID del modelo, versión solicitada y resuelta, dispositivo, tipo de datos, nivel de detalle, prefijo/sufijo, resultados y recuentos por imagen. Se activa opcionalmente y nunca se infiere: no se escribe ningún manifiesto a menos que proporcione una ruta, y se rechaza una ruta que coincida con un archivo complementario calculado. Contiene una marca de tiempo, por lo que, a diferencia de las descripciones, no es reproducible byte a byte.

## Niveles de detalle

La escala de tareas nativa de Florence-2:

| Nivel | Token de tarea | Salida |
|------|-----------|--------|
| `low` | `<CAPTION>` | una frase corta |
| `medium` | `<DETAILED_CAPTION>` | unas pocas frases |
| `high` (predeterminado) | `<MORE_DETAILED_CAPTION>` | un párrafo completo |

`high` es un párrafo, no un ensayo; Florence-2 es un modelo compacto (0.77B). Su punto fuerte es el rendimiento y la licencia, no la profundidad de un crítico de arte. Si un subtítulo parece truncado, aumenta `max_new_tokens` (predeterminado: 1024, máximo: 4096).

## Configuración

| Variable de entorno | Predeterminado | Propósito |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | Modelo de HuggingFace |
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…` (fijo) | Versión del modelo; el mecanismo detrás de la afirmación de reproducibilidad. |
| `PLAIN_SIGHT_MODEL_DIR` | Caché predeterminada de HF | Directorio de caché del modelo |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda si está disponible, de lo contrario cpu) | Dispositivo torch |
| `PLAIN_SIGHT_DTYPE` | `float16` en CUDA, precisión total en CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Límite de generación predeterminado |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Ancho del haz (decodificación determinista) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | no establecido | Si es verdadero, carga el modelo al inicio del servidor |

**Registro:** solo stderr (stdout es el canal de protocolo MCP), nombre del registrador `plain_sight`. `PLAIN_SIGHT_LOG_LEVEL` se respeta en ambas superficies.

**Carga activa:** con `PLAIN_SIGHT_EAGER_LOAD` verdadero, el servidor MCP se carga al inicio en lugar de en la primera llamada. Un error allí nunca mata la importación del servidor; se informa mediante `sight_status` como `eager_load_error` y se genera como un `ToolError` en la primera llamada a la herramienta que necesita el modelo.

**Primera llamada:** el modelo se carga de forma diferida; la primera llamada a describe/OCR carga Florence-2 (~10–20 segundos en GPU; la primera llamada descarga ~1,5 GB). Las llamadas posteriores son de ~1–2 segundos por imagen con `high` detalle en una GPU moderna.

## Postura de licencia

- **Esta herramienta:** MIT.
- **El modelo:** fijado a `florence-community/Florence-2-large`: la conversión nativa oficial de Microsoft del lanzamiento de Florence-2. **MIT** (etiqueta de licencia de hub verificada el 19 de agosto de 2026). Uso comercial permitido.
- **¿Por qué no `microsoft/Florence-2-large`?** Los mismos pesos, la misma licencia MIT, pero los repositorios originales envían configuraciones pre-nativas que solo se cargan a través de `trust_remote_code`, lo cual esta herramienta rechaza por principio. La conversión de la comunidad se carga con las clases integradas de Florence-2 de transformers.
- **Deliberadamente no ofrecido:** el conjunto de afinación de Florence-2 (MiaoshouAI PromptGen, CogFlorence, generadores de subtítulos SD3/Flux, Castollux). Sus licencias no están verificadas; permanecen fuera hasta que se aclaren. Anular `PLAIN_SIGHT_MODEL_ID` para usar uno de ellos es posible, pero pone la cuestión de la licencia en tus manos.
- **Sin código remoto:** el motor utiliza solo el soporte *nativo* de Florence-2 de transformers; `trust_remote_code` nunca se pasa, por lo que ningún Python descargado del hub se ejecuta jamás. Esto requiere `transformers >= 4.51`.

## Seguridad y confianza

Esta herramienta funciona **solo localmente**.

- **Datos accedidos:** archivos de imagen locales (solo lectura); la caché del modelo HuggingFace (escrita una vez en la primera descarga) y los archivos que escribe: archivos complementarios de descripción `.txt`, solo donde lo solicitó el llamador (`out_dir` o junto a la imagen), más un manifiesto JSON si y solo si `--manifest` / `manifest_path` proporciona una ruta explícita. Los archivos complementarios existentes se reemplazan solo bajo `--overwrite` explícito.
- **No hay salida de red en tiempo de ejecución:** el modelo se descarga una vez en el primer uso, luego toda la inferencia es local.
- **No hay ejecución de código remoto:** solo clases nativas de transformadores; `trust_remote_code` nunca se pasa, por lo que ningún Python descargado del centro se ejecuta.
- **No hay manejo de secretos, no hay telemetría:** nada se lee ni se envía a ninguna parte.
- **Solo errores estructurados:** los rastreos de pila sin procesar nunca llegan a los clientes MCP o a los usuarios de la CLI. Códigos de salida de la CLI: 0 correcto · 1 error del usuario · 2 error en tiempo de ejecución · 3 éxito parcial.

Política completa: [SECURITY.md](SECURITY.md). Se mantiene activamente; las versiones compatibles se enumeran allí.

## Requisitos

- Python >= 3.10
- `transformers >= 4.51` (Florence-2 nativo)
- Se recomienda una GPU CUDA (~2 GB de VRAM en FP16); la opción de CPU funciona (más lenta)
- La descarga del modelo ocupa aproximadamente 1,5 GB durante el primer uso

## Desarrollo

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

Las pruebas se seleccionan por marcador, no por nombre de archivo, por lo que se detecta un nuevo archivo de prueba seguro para CI sin tocar CI. En Windows, un punto de reanálisis obsoleto en el directorio temporal compartido del sistema puede romper la raíz temporal predeterminada de pytest; `verify.sh` lo reubica a través de `PYTEST_DEBUG_TEMPROOT`, y `pythonpath = ["."]` mantiene el script de consola y `python -m pytest` en concordancia.

## Arquitectura

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

La arquitectura se ha adoptado deliberadamente de
[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp); la misma
división motor/servidor, el mismo formato de errores, el mismo patrón de autocomprobación. Una versión en la nube del mismo programa se ejecuta en Comfy Cloud como el
flujo de trabajo `caption-florence2-v1` (metadatos con una imagen por tarea; esta herramienta
es la principal).

## Licencia

MIT

---

Creado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
