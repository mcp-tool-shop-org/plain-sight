<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**Versão:** 1.1.0

**Uma IA descreve o que vê.** Gerador de descrições de imagens – servidor MCP + interface de linha de comando.
Florence-2 (licença MIT) para descrições textuais, reconhecimento ótico de caracteres (OCR) e criação de legendas para conjuntos de dados LoRA.
Funciona localmente e é determinístico por padrão.

A versão complementar de [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp):

| | ai-olhos-mcp | à vista de todos / em local visível / sem disfarçar |
|---|---|---|
| Emprego / Trabalho | **judges** images | **describes** images |
| Modelo | SigLIP2 (discriminativo) | Florença-2 (modelo generativo) |
| Resultado / Saída | pontuações calibradas | texto corrido / reconhecimento ótico de caracteres / ficheiros de legendas |
| Tipo de falha / Modo de falha | não consigo fazer a narração / não estou habilitado para narrar | pode alucinar detalhes. |
| Use-o quando precisar. | «Esta imagem contém o elemento X?» | «O que é que se vê nesta imagem?» |

## Contrato de honestidade

As descrições são **gerativas**: fluentes, geralmente precisas e capazes de inventar detalhes. O recurso «plain-sight» torna a saída *reproduzível* (decodificação determinística — a mesma imagem produz a mesma legenda), mas não garante que seja *verdadeira*. Para verificar uma afirmação específica sobre uma imagem, use o `image_verify` do ai-eyes-mcp; ele mede, em vez de descrever. As duas ferramentas pertencem a famílias de modelos diferentes por design, para que uma possa verificar a outra.

Três limites específicos, mencionados porque é fácil descobrir da pior maneira:

- **O OCR não pode indicar a ausência de texto.** O Florence-2 emite uma string decodificada para cada imagem, incluindo imagens que não contêm nenhum texto — uma fotografia pode retornar `'2'`. Essa saída é lexicalmente indistinguível de uma leitura correta de um numeral. Portanto, cada resultado do OCR carrega `absence_of_text_unreliable: true` (MCP) ou uma linha `[OCR_CAVEAT]` no stderr (CLI). O plain-sight nunca suprime ou esvazia o resultado, porque uma leitura curta pode ser genuína — ele informa que o sinal não existe.
- **As legendas descrevem; elas não verificam.** Uma frase confiante sobre uma imagem não é evidência de que o objeto descrito está presente.
- **A reprodutibilidade é por revisão.** Fixar a versão é o que torna a alegação de determinismo significativa ao longo do tempo; veja [Provenance](#provenance).

## Ferramentas (MCP)

| Ferramenta | Para que serve? / Qual a sua função? |
|------|-------------|
| `describe_image` | Uma imagem → descrição em prosa (3 níveis de detalhe) |
| `describe_batch` | N imagens → `.txt` arquivos de legenda associados (o conjunto de dados) |
| `read_text` | OCR — decodifica texto de uma imagem, com uma ressalva sobre a ausência de texto. |
| `sight_status` | Verificação de saúde: modelo, dispositivo, revisão resolvida, estado carregado. |
| `sight_selftest` | Descreva as imagens de referência agrupadas e os resultados dos testes de verificação. |

Cada carga útil que carrega a saída do modelo também carrega `model_id` e `revision_resolved` — veja [Provenance](#provenance).

## Guia de Início Rápido

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

Ou execute como um módulo: `python -m plain_sight`

### Interface de linha de comandos

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

Flags `batch`: `--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite` · `--max-new-tokens` · `--manifest` · `--dry-run`. Execute `plain-sight batch --help` para obter o texto completo; `plain-sight --help` documenta os códigos de saída e qual fluxo carrega o quê.

### Como é uma execução longa

O progresso vai para **stderr**; os resultados vão para **stdout**, então `plain-sight describe x.png > caption.txt` funciona.

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

A carga é anunciada **antes** do início do trabalho, com a contagem das imagens que realmente terão legendas, para que uma pausa nunca apareça no meio da execução. As imagens ignoradas são contadas no sinal de atividade (heartbeat) em vez de serem impressas linha por linha — uma nova execução sobre um conjunto concluído é silenciosa. As falhas permanecem em uma linha cada.

### Configuração do Claude Code

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

## O contrato de legendagem (conjunto de dados)

Criado para conjuntos de dados de treino LoRA (style-dataset-lab e projetos relacionados):

- **Correspondência exata do nome base:** `img_0042.png` → `img_0042.txt`. Sem sufixo de contador — diferente do nó SaveText do ComfyUI, que adiciona `_00001`.
- **Concatenação simples:** o arquivo auxiliar contém `prefix + caption + suffix` sem nenhum delimitador inserido. Quer `"mcpt_style, <caption>"`? Coloque a vírgula e o espaço no prefixo.
- **Radicais conflitantes são rejeitados, nunca mesclados.** Duas imagens cujos radicais correspondem — `img.png` e `img.jpg` em uma pasta ou arquivos com o mesmo radical de duas pastas sob um `--out-dir` — reivindicariam um único `.txt`. O plain-sight rejeita todo o lote antes de carregar o modelo, nomeia os infratores e sai `1`. Ele não renomeará um arquivo auxiliar para evitar o conflito: os treinadores usam a correspondência exata do radical, portanto, uma alteração de nome deixaria a legenda órfã e a imagem sem legenda.
- **As gravações são atômicas.** Cada arquivo auxiliar é gravado em um arquivo temporário no mesmo diretório e movido para o local correto, para que uma interrupção nunca deixe uma legenda parcial no caminho final. Um arquivo auxiliar que existe, mas está vazio, é tratado como incompleto e recebe uma nova legenda.
- **Novas execuções idempotentes:** arquivos auxiliares existentes não vazios são ignorados e não têm custo, a menos que `--overwrite` / `overwrite=true`.
- **Determinístico:** `do_sample=false` + busca em feixe contra uma versão fixa — relegendar uma imagem inalterada reproduz o mesmo texto, portanto, as diferenças significam algo.

## Provenance (Procedência)

O fluxo de dados do conjunto de dados produz dados de treinamento. Seis meses depois, a pergunta é: quais pesos produziram quais legendas — então a resposta acompanha a saída.

- **A revisão do modelo é fixada** por padrão para `4271c66b88cdbc05735372ec13b2360108de5317`. Sem uma fixação, o HuggingFace resolve para qualquer que seja o ramo padrão do repositório atualmente apontado, e uma retag silenciosa alteraria as legendas sob entradas inalteradas. Substitua com `PLAIN_SIGHT_MODEL_REVISION`.
- **Cada carga útil de saída nomeia os pesos.** `describe_image`, `read_text`, `describe_batch`, `sight_selftest` e os modos `--json` do CLI e o resumo do lote carregam `model_id` e `revision_resolved` — a revisão que o modelo carregado realmente relata, não a constante que foi solicitada. `sight_status` relata ambos, para que uma incompatibilidade seja visível.
- **`--manifest PATH` grava um registro de execução** — versão da ferramenta, ID do modelo, revisão solicitada e resolvida, dispositivo, dtype, nível de detalhe, prefixo/sufixo, resultados e contagens por imagem. Opt-in e nunca inferido: nenhum manifesto é gravado a menos que você passe um caminho, e um caminho que entre em conflito com um arquivo auxiliar calculado é rejeitado. Ele contém um carimbo de data/hora, portanto, ao contrário das legendas, não é reproduzível byte a byte.

## Níveis de detalhe

A hierarquia de tarefas nativas do Florence-2:

| Nível; camada; degrau. | Token de tarefa | Resultado / Saída |
|------|-----------|--------|
| `low` | `<CAPTION>` | uma frase curta |
| `medium` | `<DETAILED_CAPTION>` | algumas frases |
| `high` (valor predefinido) | `<MORE_DETAILED_CAPTION>` | um parágrafo completo |

`high` é um parágrafo, não um ensaio — o Florence-2 é um modelo compacto (0,77 mil milhões de parâmetros).

O seu ponto forte é a eficiência e a licença, não a profundidade da análise crítica. Se uma legenda parecer truncada, aumente o valor de `max_new_tokens` (o padrão é 1024, o máximo é 4096).

## Configuração

| Variável de ambiente | Padrão / Predefinido | Objetivo / Finalidade |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | Modelo da Hugging Face |
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…` (fixado) | Revisão do modelo; o mecanismo por trás da alegação de reprodutibilidade. |
| `PLAIN_SIGHT_MODEL_DIR` | Cache padrão do HF | Diretório de cache do modelo |
| `PLAIN_SIGHT_DEVICE` | `auto` (CUDA se disponível, caso contrário, CPU) | dispositivo de iluminação portátil |
| `PLAIN_SIGHT_DTYPE` | `float16` em CUDA, precisão total na CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Limite padrão de geração. |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Largura do feixe (decodificação determinística) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | desativar; remover; anular; desconfigurar | Se o valor for verdadeiro, carregue o modelo no início da execução do servidor. |

**Registro:** apenas stderr (stdout é o canal de protocolo MCP), nome do registrador `plain_sight`. `PLAIN_SIGHT_LOG_LEVEL` é respeitado em ambas as superfícies.

**Carregamento antecipado:** com `PLAIN_SIGHT_EAGER_LOAD` verdadeiro, o servidor MCP carrega no início em vez de na primeira chamada. Uma falha nunca mata a importação do servidor — ela é relatada por `sight_status` como `eager_load_error` e lançada como um `ToolError` na primeira chamada da ferramenta que precisa do modelo.

**Primeira chamada:** o modelo é carregado de forma preguiçosa — a primeira chamada para descrever/fazer OCR carrega o Florence-2 (~10–20 segundos em uma GPU; a primeira chamada baixa cerca de 1,5 GB). As chamadas subsequentes demoram aproximadamente 1–2 segundos por imagem com o nível de detalhe `high` em uma GPU moderna.

## Posição em relação à licença

- **Esta ferramenta:** MIT.
- **O modelo:** fixado em `florence-community/Florence-2-large` – a conversão oficial nativa do Microsoft Florence-2.
**MIT** (a licença do hub foi verificada em 19 de agosto de 2026). Uso comercial permitido.
- **Por que não `microsoft/Florence-2-large`?** Os mesmos pesos, a mesma licença MIT, mas os repositórios originais incluem configurações pré-nativas que só podem ser carregadas através de `trust_remote_code` – o que esta ferramenta recusa por princípio. A conversão da comunidade é carregada com as classes Florence-2 integradas do transformers.
- **Deliberadamente não oferecido:** o conjunto de modelos ajustados do Florence-2 (MiaoshouAI PromptGen, CogFlorence, SD3/Flux captioners, Castollux). As licenças deles não foram verificadas; eles permanecerão fora até que isso seja resolvido. Substituir `PLAIN_SIGHT_MODEL_ID` por um deles é possível, mas coloca a questão da licença sob sua responsabilidade.
- **Sem código remoto:** o motor usa apenas o suporte *nativo* do transformers para o Florence-2 – `trust_remote_code` nunca é transmitido, portanto, nenhum Python baixado do hub é executado. Isso requer `transformers >= 4.51`.

## Segurança e Confiança

Esta ferramenta funciona apenas em modo local.

- **Dados acessados:** arquivos de imagem locais (somente leitura); o cache do modelo HuggingFace (gravado uma vez no primeiro download); e os arquivos que ele grava — legendas `.txt`, apenas onde o chamador solicitou (`out_dir` ou ao lado da imagem), mais um manifesto JSON se e somente se `--manifest` / `manifest_path` fornecerem um caminho explícito. Os arquivos auxiliares existentes são substituídos apenas sob `--overwrite` explícito.
- **Nenhuma saída de rede em tempo de execução** — o modelo é baixado uma vez no primeiro uso, então toda a inferência é local.
- **Nenhuma execução de código remoto** — apenas classes nativas do transformador; `trust_remote_code` nunca é passado, portanto, nenhum Python buscado no hub é executado.
- **Sem tratamento de segredos, sem telemetria** — nada é lido ou enviado para lugar algum.
- **Apenas erros estruturados** — rastreamentos de pilha brutos nunca chegam aos clientes MCP ou aos usuários do CLI. Códigos de saída do CLI: 0 ok · 1 erro do usuário · 2 erro em tempo de execução · 3 sucesso parcial.

Política completa: [SECURITY.md](SECURITY.md). Mantida ativamente; as versões suportadas estão listadas ali.

## Requisitos

- Python >= 3.10
- `transformers >= 4.51` (Florence-2 nativo)
- GPU CUDA recomendada (~2 GB de VRAM em FP16); o fallback para CPU funciona (mais lento)
- O download do modelo ocupa cerca de 1,5 GB na primeira utilização

## Desenvolvimento

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

Os testes selecionam por marcador, não por nome de arquivo, portanto, um novo arquivo de teste seguro para CI é detectado sem tocar no CI. No Windows, um ponto de análise desatualizado no sistema temporário compartilhado pode quebrar a raiz temporária padrão do pytest; `verify.sh` o realoca via `PYTEST_DEBUG_TEMPROOT`, e `pythonpath = ["."]` mantém o script do console e `python -m pytest` em sincronia.

## Arquitetura

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

A arquitetura foi deliberadamente inspirada em [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) — a mesma divisão entre motor/servidor, o mesmo tratamento de erros e o mesmo padrão de autoteste. Uma versão para a nuvem do mesmo projeto é executada no Comfy Cloud como o fluxo de trabalho `caption-florence2-v1` (metadados com uma imagem por tarefa; esta ferramenta é o componente principal).

## Licença

MIT

---

Criado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
