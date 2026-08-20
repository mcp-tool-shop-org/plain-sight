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

**Versión:** 1.0.0

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

## Herramientas (MCP)

| Herramienta | Qué hace |
|------|-------------|
| `describe_image` | Una imagen → descripción en prosa (3 niveles de detalle) |
| `describe_batch` | N imágenes → `.txt` archivos complementarios de subtítulos (la ruta del conjunto de datos) |
| `read_text` | OCR: extrae el texto visible de una imagen |
| `sight_status` | Verificación de estado: modelo, dispositivo, estado cargado |
| `sight_selftest` | Describe las imágenes de referencia incluidas, verifica la salida |

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

# OCR
plain-sight ocr screenshot.png

# The dataset lane: caption a directory into .txt sidecars with a trigger token
plain-sight batch ./dataset --prefix "mcpt_style, " --detail high

# Re-runs are idempotent — existing sidecars are skipped unless you --overwrite
plain-sight batch ./dataset --prefix "mcpt_style, " --overwrite
```

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

- **Emparejamiento exacto del nombre base:** `img_0042.png` → `img_0042.txt`. No hay sufijo contador, a diferencia del nodo SaveText de ComfyUI, que agrega `_00001`.
- **Concatenación simple:** el archivo complementario contiene `prefix + caption + suffix` sin ningún delimitador insertado. ¿Quieres `"mcpt_style, <caption>"`? Coloca la coma y el espacio en el prefijo.
- **Ejecuciones idempotentes:** los archivos complementarios existentes se omiten (y no cuestan nada) a menos que `--overwrite` / `overwrite=true`.
- **Determinista:** `do_sample=false` + búsqueda de haz: volver a generar subtítulos de una imagen sin cambios reproduce el mismo texto, por lo que las diferencias significan algo.

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
| `PLAIN_SIGHT_MODEL_DIR` | Caché predeterminada de HF | Directorio de caché del modelo |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda si está disponible, de lo contrario cpu) | Dispositivo torch |
| `PLAIN_SIGHT_DTYPE` | `float16` en CUDA, precisión total en CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Límite de generación predeterminado |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Ancho del haz (decodificación determinista) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | no establecido | Si es verdadero, carga el modelo al inicio del servidor |

**Registro:** solo stderr (stdout es el canal de protocolo MCP), nombre del registrador: `plain_sight`.

**Primera llamada:** el modelo se carga de forma diferida; la primera llamada a describe/OCR carga Florence-2 (~10–20 segundos en GPU; la primera llamada descarga ~1,5 GB). Las llamadas posteriores son de ~1–2 segundos por imagen con `high` detalle en una GPU moderna.

## Postura de licencia

- **Esta herramienta:** MIT.
- **El modelo:** fijado a `florence-community/Florence-2-large`: la conversión nativa oficial de Microsoft del lanzamiento de Florence-2. **MIT** (etiqueta de licencia de hub verificada el 19 de agosto de 2026). Uso comercial permitido.
- **¿Por qué no `microsoft/Florence-2-large`?** Los mismos pesos, la misma licencia MIT, pero los repositorios originales envían configuraciones pre-nativas que solo se cargan a través de `trust_remote_code`, lo cual esta herramienta rechaza por principio. La conversión de la comunidad se carga con las clases integradas de Florence-2 de transformers.
- **Deliberadamente no ofrecido:** el conjunto de afinación de Florence-2 (MiaoshouAI PromptGen, CogFlorence, generadores de subtítulos SD3/Flux, Castollux). Sus licencias no están verificadas; permanecen fuera hasta que se aclaren. Anular `PLAIN_SIGHT_MODEL_ID` para usar uno de ellos es posible, pero pone la cuestión de la licencia en tus manos.
- **Sin código remoto:** el motor utiliza solo el soporte *nativo* de Florence-2 de transformers; `trust_remote_code` nunca se pasa, por lo que ningún Python descargado del hub se ejecuta jamás. Esto requiere `transformers >= 4.51`.

## Seguridad y confianza

Esta herramienta funciona **solo localmente**.

- **Datos accedidos:** archivos de imagen locales (solo lectura); la caché del modelo de HuggingFace (se escribe una vez en la primera descarga); `.txt` archivos complementarios de subtítulos: los ÚNICOS archivos que escribe, solo donde lo solicita el llamador (`out_dir` o junto a la imagen), y los archivos complementarios existentes se reemplazan solo bajo un `--overwrite` explícito.
- **No hay salida de red en tiempo de ejecución:** el modelo se descarga una vez durante el primer uso y luego toda la inferencia es local.
- **No hay ejecución de código remoto:** solo clases nativas de transformers; `trust_remote_code` nunca se pasa, por lo que ningún Python descargado del hub se ejecuta jamás.
- **Sin manejo de secretos, sin telemetría:** no se lee ni se envía nada a ninguna parte.
- **Solo errores estructurados:** los rastreos de pila sin procesar nunca llegan a los clientes MCP o a los usuarios de la CLI. Códigos de salida de la CLI: 0 correcto · 1 error de usuario · 2 error en tiempo de ejecución · 3 éxito parcial.

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

# CI-safe tests (no model, no GPU)
pytest tests/test_edge_cases.py -v

# Dogfood tests (real model + GPU)
pytest tests/test_dogfood.py -v

# Full verify: imports, edge tests, build
bash verify.sh
```

## Arquitectura

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

La arquitectura se ha adoptado deliberadamente de
[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp); la misma
división motor/servidor, el mismo formato de errores, el mismo patrón de autocomprobación. Una versión en la nube del mismo programa se ejecuta en Comfy Cloud como el
flujo de trabajo `caption-florence2-v1` (metadatos con una imagen por tarea; esta herramienta
es la principal).

## Licencia

MIT

---

Creado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
