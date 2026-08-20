<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.md">English</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**संस्करण:** 1.0.0

**एक एआई जो कुछ भी देखता है, उसे बताता है।** जेनरेटिव इमेज डिस्क्राइबर — एमसीपी सर्वर + सीएलआई रैपिंग
फ्लोरेंस-2 (एमआईटी) का उपयोग वर्णनात्मक पाठ, ओसीआर और एलओआरए-डेटासेट कैप्शन साइडकार के लिए किया जाता है।
यह स्थानीय रूप से चलता है, और डिफ़ॉल्ट रूप से यह निश्चित होता है।

[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) का सहयोगी:

| | ai-eyes-mcp | प्लेन-साइट |
|---|---|---|
| कार्य | **judges** images | **describes** images |
| मॉडल | सिगएलआईपी2 (भेदभावपूर्ण) | फ्लोरेंस-2 (जेनरेटिव) |
| आउटपुट | कैलिब्रेटेड स्कोर | वर्णनात्मक पाठ / ओसीआर / कैप्शन फ़ाइलें |
| विफलता का तरीका | वर्णन नहीं कर सकता | विवरण में बदलाव कर सकता है |
| इसका उपयोग कब करें | "क्या इस छवि में एक्स है?" | "इस छवि में क्या है?" |

## ईमानदारी का अनुबंध

वर्णन **जेनरेटिव** होते हैं: धाराप्रवाह, आमतौर पर सटीक और विवरण बनाने में सक्षम। प्लेन-साइट आउटपुट को *पुनरुत्पादित* बनाता है (निश्चित डिकोडिंग — एक ही छवि से एक ही कैप्शन प्राप्त होता है), न कि *पूरी तरह से सही*। किसी छवि के बारे में विशिष्ट दावे की पुष्टि करने के लिए, ai-eyes-mcp के `image_verify` का उपयोग करें — यह मापता है, वर्णन नहीं करता। डिज़ाइन द्वारा दोनों उपकरण अलग-अलग मॉडल परिवार हैं, इसलिए एक दूसरे की जांच कर सकता है।

## उपकरण (एमसीपी)

| उपकरण | यह क्या करता है |
|------|-------------|
| `describe_image` | एक छवि → वर्णनात्मक पाठ (3 विवरण स्तर) |
| `describe_batch` | एन छवियां → `.txt` कैप्शन साइडकार (डेटासेट लेन) |
| `read_text` | ओसीआर — किसी छवि से दृश्यमान पाठ निकालें |
| `sight_status` | स्वास्थ्य जांच: मॉडल, डिवाइस, लोड की गई स्थिति |
| `sight_selftest` | बंडल किए गए संदर्भ छवियों का वर्णन करें, आउटपुट की जांच करें |

## त्वरित शुरुआत

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

या इसे एक मॉड्यूल के रूप में चलाएं: `python -m plain_sight`

### सीएलआई

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

### क्लॉड कोड कॉन्फ़िगरेशन

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

## कैप्शन अनुबंध (डेटासेट लेन)

एलओआरए प्रशिक्षण सेट के लिए बनाया गया (स्टाइल-डेटासेट-लैब और अन्य):

- **सटीक बेसनेम युग्मन:** `img_0042.png` → `img_0042.txt`। कोई काउंटर प्रत्यय नहीं — ComfyUI के SaveText नोड के विपरीत, जो `_00001` जोड़ता है।
- **सादा संयोजन:** साइडकार में `prefix + caption + suffix` होता है जिसमें कोई विभाजक नहीं डाला गया है। क्या आप `"mcpt_style, <caption>"` चाहते हैं? उपसर्ग में अल्पविराम-स्थान रखें।
- **आइडेंमपोटेंट पुन: रन:** मौजूदा साइडकार को छोड़ दिया जाता है (और इसकी कोई लागत नहीं होती) जब तक कि `--overwrite` / `overwrite=true` न हो।
- **निश्चित:** `do_sample=false` + बीम खोज — अपरिवर्तित छवि का पुन: कैप्शनिंग समान पाठ उत्पन्न करता है, इसलिए अंतर का कुछ अर्थ होता है।

## विवरण स्तर

फ्लोरेंस-2 की मूल कार्य श्रृंखला:

| स्तर | कार्य टोकन | आउटपुट |
|------|-----------|--------|
| `low` | `<CAPTION>` | एक छोटा वाक्य |
| `medium` | `<DETAILED_CAPTION>` | कुछ वाक्य |
| `high` (डिफ़ॉल्ट) | `<MORE_DETAILED_CAPTION>` | एक पूरा पैराग्राफ |

`high` एक पैराग्राफ है, निबंध नहीं — फ्लोरेंस-2 एक कॉम्पैक्ट (0.77B) मॉडल है। इसकी ताकत थ्रूपुट और लाइसेंस है, न कि कला-आलोचक की गहराई। यदि कोई कैप्शन छोटा दिखाई देता है, तो `max_new_tokens` बढ़ाएं (डिफ़ॉल्ट 1024, अधिकतम 4096)।

## कॉन्फ़िगरेशन

| पर्यावरण चर | डिफ़ॉल्ट | उद्देश्य |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | हगिंगफेस मॉडल |
| `PLAIN_SIGHT_MODEL_DIR` | एचएफ डिफ़ॉल्ट कैश | मॉडल कैश निर्देशिका |
| `PLAIN_SIGHT_DEVICE` | `auto` (यदि उपलब्ध हो तो cuda, अन्यथा cpu) | टॉर्च डिवाइस |
| `PLAIN_SIGHT_DTYPE` | `float16` CUDA पर, CPU पर पूर्ण परिशुद्धता | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | डिफ़ॉल्ट पीढ़ी कैप |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | बीम चौड़ाई (निश्चित डिकोडिंग) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | सेट नहीं है | यदि सत्य है, तो सर्वर शुरू होने पर मॉडल लोड करें |

**लॉगिंग:** केवल stderr (stdout एमसीपी प्रोटोकॉल चैनल है), लॉगर नाम `plain_sight`।

**पहला कॉल:** मॉडल आलसी रूप से लोड होता है — पहला वर्णन/ओसीआर कॉल फ्लोरेंस-2 को लोड करता है (~10–20 सेकंड जीपीयू पर; पहले कॉल में ~1.5 जीबी डाउनलोड होता है)। बाद के कॉल आधुनिक जीपीयू पर `high` विवरण पर प्रति छवि ~1–2 सेकंड होते हैं।

## लाइसेंस स्थिति

- **यह उपकरण:** एमआईटी।
- **मॉडल:** `florence-community/Florence-2-large` से पिन किया गया — माइक्रोसॉफ्ट के फ्लोरेंस-2 रिलीज़ का आधिकारिक मूल-ट्रांसफॉर्मर रूपांतरण। **एमआईटी** (हब लाइसेंस टैग 2026-08-19 को सत्यापित)। वाणिज्यिक उपयोग के लिए सुरक्षित।
- **क्यों नहीं `microsoft/Florence-2-large`?** समान वजन, समान एमआईटी लाइसेंस, लेकिन मूल रिपॉजिटरी पूर्व-मूल कॉन्फ़िगरेशन भेजते हैं जो केवल `trust_remote_code` के माध्यम से लोड होते हैं — जिसे यह उपकरण सिद्धांत रूप में अस्वीकार करता है। सामुदायिक रूपांतरण ट्रांसफॉर्मर के अंतर्निहित फ्लोरेंस-2 कक्षाओं के साथ लोड होता है।
- **जानबूझकर नहीं दिया गया:** फ्लोरेंस-2 फाइन-ट्यून चिड़ियाघर (मियोशौएआई प्रॉम्प्टजेन, कॉगफ्लोरेंस, एसडी3/फ्लक्स कैप्शनर, कैस्टोलक्स)। उनके लाइसेंस सत्यापित नहीं हैं; वे तब तक बाहर रहेंगे जब तक कि उन्हें मंजूरी नहीं मिल जाती। उनमें से किसी एक को `PLAIN_SIGHT_MODEL_ID` पर ओवरराइड करना संभव है लेकिन इससे लाइसेंस का प्रश्न आप पर आ जाएगा।
- **कोई दूरस्थ कोड नहीं:** इंजन केवल ट्रांसफॉर्मर के *मूल* फ्लोरेंस-2 समर्थन का उपयोग करता है — `trust_remote_code` कभी भी पास नहीं किया जाता है, इसलिए हब से प्राप्त कोई भी पायथन निष्पादित नहीं होता है। इसके लिए `transformers >= 4.51` की आवश्यकता होती है।

## सुरक्षा और विश्वास

यह उपकरण **केवल स्थानीय रूप से** काम करता है।

- **स्पर्श किया गया डेटा:** स्थानीय छवि फ़ाइलें (केवल पढ़ने के लिए); हगिंगफेस मॉडल कैश (पहली डाउनलोड पर एक बार लिखा जाता है); `.txt` कैप्शन साइडकार — एकमात्र फ़ाइलें जो यह लिखता है, केवल वहीं जहां कॉलर ने अनुरोध किया है (`out_dir` या छवि के बगल में), और मौजूदा साइडकार को केवल स्पष्ट `--overwrite` के तहत प्रतिस्थापित किया जाता है।
- **रनटाइम पर कोई नेटवर्क आउटपुट नहीं** — मॉडल पहली बार उपयोग करने पर एक बार डाउनलोड होता है, फिर सभी अनुमान स्थानीय होते हैं।
- **कोई दूरस्थ कोड निष्पादन नहीं** — केवल मूल ट्रांसफॉर्मर कक्षाएं; `trust_remote_code` कभी भी पास नहीं किया जाता है, इसलिए हब से प्राप्त कोई भी पायथन निष्पादित नहीं होता है।
- **कोई गुप्त जानकारी हैंडलिंग, कोई टेलीमेट्री नहीं** — कहीं से कुछ भी नहीं पढ़ा या भेजा जाता है।
- **केवल संरचित त्रुटियां** — कच्चे स्टैक ट्रेस एमसीपी क्लाइंट या सीएलआई उपयोगकर्ताओं तक कभी नहीं पहुंचते हैं। सीएलआई निकास कोड: 0 ठीक · 1 उपयोगकर्ता त्रुटि · 2 रनटाइम त्रुटि · 3 आंशिक सफलता।

पूर्ण नीति: [SECURITY.md](SECURITY.md)। सक्रिय रूप से बनाए रखा गया; समर्थित संस्करण वहां सूचीबद्ध हैं।

## आवश्यकताएं

- पायथन >= 3.10
- `transformers >= 4.51` (मूल फ्लोरेंस-2)
- CUDA GPU की अनुशंसा की जाती है (~2 GB VRAM, FP16 पर); CPU फॉलबैक काम करता है (धीमा)।
- मॉडल पहली बार उपयोग करने पर लगभग 1.5 GB डाउनलोड होता है।

## विकास

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

## आर्किटेक्चर

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

यह आर्किटेक्चर जानबूझकर [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) से लिया गया है — समान इंजन/सर्वर विभाजन, समान त्रुटि संरचना, समान स्व-परीक्षण पैटर्न। एक ही अनुबंध का क्लाउड संस्करण कॉम्फी क्लाउड पर `caption-florence2-v1` वर्कफ़्लो के रूप में चलता है (प्रति कार्य एक छवि मेटाडेटा राइडर; यह उपकरण मुख्य प्रक्रिया है)।

## लाइसेंस

एमआईटी

---

[MCP टूल शॉप](https://mcp-tool-shop.github.io/) द्वारा निर्मित।
