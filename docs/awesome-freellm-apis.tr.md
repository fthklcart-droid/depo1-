> 🇹🇷 Bu, [open-free-llm-api/awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis) README'sinin Türkçe çevirisidir. Model adları, kimlikler, URL'ler ve kod olduğu gibi bırakılmıştır.

<p align="center">
  <h1 align="center">awesome-free-llm-apis</h1>
  <!-- AUTO_STATS -->
  <p align="center"><strong>30 sağlayıcıdan 506+ ücretsiz LLM API'si</strong> — ücretsiz modelleri saniyeler içinde bul, karşılaştır ve yapılandır.</p>
<!-- END_AUTO_STATS -->
</p>

<p align="center">
  <a href="https://freellm.net" target="_blank" rel="noopener"><strong>🌐 Canlı: freellm.net</strong></a> —
  <a href="https://freellm.net/models/" target="_blank" rel="noopener">Modellere göz at</a> ·
  <a href="https://freellm.net/playground/" target="_blank" rel="noopener">Deneme alanı</a> ·
  <a href="https://freellm.net/config/" target="_blank" rel="noopener">Yapılandırma oluşturucu</a> ·
  <a href="https://freellm.net/free-llm-api-keys/" target="_blank" rel="noopener">API anahtarları</a>
</p>

<p align="center">
  <img alt="Provider Logos" src="https://raw.githubusercontent.com/open-free-llm-api/awesome-freellm-apis/main/assets/provider-logos-marquee.svg" width="100%" />
</p>

<!-- AUTO_UPDATE_BADGE -->
  <p align="center"><strong>🔄 Veriler her gün şuradan yenilenir: <a href="https://freellm.net" target="_blank" rel="noopener">freellm.net</a></strong> — Son güncelleme: 2026-10-12</p>
<!-- END_AUTO_UPDATE_BADGE -->

<p align="center">
  🌐 <a href="https://github.com/open-free-llm-api/awesome-freellm-apis">English (orijinal)</a> · <b>Türkçe</b>
</p>

---

## Bu Proje Neden Var

Ücretsiz bir LLM API'si bulmak; onlarca GitHub README'sini taramak, beş farklı platforma kaydolmak ya da hangi modellerin hâlâ ücretsiz katmanı olduğunu tahmin etmek anlamına gelmemeli.

Bu depo, tüm ücretsiz LLM API'lerinin **yapılandırılmış, makine tarafından okunabilir bir dizinidir** — istek limitleri, bağlam pencereleri, tek tıkla yapılandırma parçacıkları ve doğrudan API anahtarı bağlantıları. Her gün güncellenir.

**Neden bu depo + <a href="https://freellm.net" target="_blank" rel="noopener">freellm.net</a>?**

- ✅ **Her zaman güncel** — veriler otomatik izlemeyle her gün yenilenir, 2 yıllık statik bir liste değil
- ✅ **Kredi kartı şeffaflığı** — hangi sağlayıcıların kart, telefon doğrulaması istediğini veya hiçbir şey istemediğini açıkça gösterir
- ✅ **Tek tıkla yapılandırma** — Claude Code, Cursor, Codex, Aider ve 10'dan fazla araç için kopyalamaya hazır parçacıklar
- ✅ **Yan yana karşılaştırma** — sağlayıcılar arasında bağlam pencerelerini, istek limitlerini ve modaliteleri anında karşılaştır

---

## Nasıl Kullanılır — 3 Adım

1. **Bir sağlayıcı seç** — aşağıdaki [Sağlayıcı Dizini](#provider-directory) bölümüne bak. **Groq** ile başla (kredi kartı yok, ücretsiz 30 RPM).
2. **API anahtarını al** — aşağıdaki herhangi bir [Anahtar Al →](#quick-reference--base-urls--api-keys) bağlantısına tıkla, kaydol (çoğu yalnızca e-posta ister) ve anahtarını kopyala. 1 dakikadan az sürer.
3. **Bağla** — temel URL'yi ve model kimliğini kopyala, aşağıdaki [Hızlı Başlangıç](#quick-start--use-any-free-api-in-30-seconds) örneklerine yapıştır.

Belirli bir aracı mı yapılandırıyorsun? <a href="https://freellm.net/config/#claude-code" target="_blank" rel="noopener">Claude Code</a> · <a href="https://freellm.net/config/#cursor" target="_blank" rel="noopener">Cursor</a> · <a href="https://freellm.net/config/#codex" target="_blank" rel="noopener">Codex</a> · <a href="https://freellm.net/config/#openhuman" target="_blank" rel="noopener">OpenHuman</a> · <a href="https://freellm.net/config/#opencode" target="_blank" rel="noopener">OpenCode</a> · <a href="https://freellm.net/config/#openclaw" target="_blank" rel="noopener">OpenClaw</a> — tek tıkla yapılandırmalar: <a href="https://freellm.net/config/" target="_blank" rel="noopener">freellm.net/config/</a>.



## Hızlı Başlangıç — Herhangi Bir Ücretsiz API'yi 30 Saniyede Kullan

**Daha önce hiç API kullanmadın mı?** En basit yol: şuraya git: <a href="https://console.groq.com/keys" target="_blank" rel="noopener">console.groq.com/keys</a>, yalnızca e-postayla kaydol (kredi kartı yok), ücretsiz anahtarını kopyala ve aşağıdaki herhangi bir örneğe yapıştır. Bir dakikadan kısa sürede çalışır hale gelirsin.

Aşağıdaki tüm sağlayıcılar **OpenAI uyumlu bir uç nokta** sunar. `baseURL` + `apiKey` kabul eden her araç çalışır — yalnızca temel URL'yi ve anahtarı değiştir.

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",  # ücretsiz, kredi kartı yok
    api_key="GROQ_API_KEY",                     # console.groq.com/keys adresinden al
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",            # aşağıdaki En İyi Modeller tablosuna bak
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
# Groq ücretsiz katman: 30 RPM, 14.400 RPD — kişisel kullanım için cömert
```

### Codex CLI

```bash
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"
export OPENAI_API_KEY="your-groq-key"          # console.groq.com/keys adresinden al
codex --model "llama-3.3-70b-versatile"
```

### Cursor

```
Settings → Models → Add Model
  Model name: llama-3.3-70b-versatile
  Base URL: https://api.groq.com/openai/v1
  API key: your-groq-key                       # console.groq.com/keys adresinden al
```

### Claude Code

```bash
# Claude Code, Anthropic uyumlu bir API gerektirir — OpenRouter kullan
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="sk-or-v1-your-key"  # openrouter.ai/keys
export ANTHROPIC_API_KEY=""                       # boş olmalı
# Not: OpenRouter Anthropic modelleri için bir kerelik 10$ yükleme gerekir
```

### Başka Araçlar mı Kullanıyorsun?

Çoğu yapay zekâ geliştirme aracı özel API uç noktalarını kabul eder — onları yukarıdaki herhangi bir sağlayıcıya yönlendirmen yeterli. Ücretsiz anahtarını al, sonra:

- **Claude Code** — `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` ayarla. <a href="https://freellm.net/config/#claude-code" target="_blank" rel="noopener">Adım adım →</a>
- **Cursor** — Settings → Models → Add Model. <a href="https://freellm.net/config/#cursor" target="_blank" rel="noopener">Adım adım →</a>
- **Codex CLI** — `OPENAI_BASE_URL` + `OPENAI_API_KEY` ayarla. <a href="https://freellm.net/config/#codex" target="_blank" rel="noopener">Adım adım →</a>
- **OpenHuman** — `config.toml` dosyasını düzenle. <a href="https://freellm.net/config/#openhuman" target="_blank" rel="noopener">Adım adım →</a>
- **Aider** — `.aider.conf.yml` dosyasını düzenle. <a href="https://freellm.net/config/#aider" target="_blank" rel="noopener">Adım adım →</a>
- **Cline** (VS Code) — API sağlayıcı ayarları. <a href="https://freellm.net/config/#cline" target="_blank" rel="noopener">Adım adım →</a>
- **Open WebUI** — Settings → Connections. <a href="https://freellm.net/config/#open-webui" target="_blank" rel="noopener">Adım adım →</a>

Kopyalamaya hazır daha fazla yapılandırma: <a href="https://freellm.net/config/" target="_blank" rel="noopener"><strong>freellm.net/config/</strong></a>.

> **Tüm sağlayıcılar, temel URL'ler ve API anahtarı bağlantıları** aşağıdaki [Hızlı Başvuru](#quick-reference--base-urls--api-keys) bölümündedir.


---

## Sağlayıcı Dizini

### ⚡ Kalıcı Ücretsiz Katmanlar

Bu sağlayıcılar **kalıcı ücretsiz katman** sunar — çoğu için kredi kartı gerekmez.

<!-- BEGIN_PERMANENT_FREE -->
| Sağlayıcı | Ücretsiz Model | Kredi Kartı? | Maks. Bağlam | Modaliteler | API Anahtarı Al |
|---|---|---|---|---|---|
| NVIDIA NIM | 132 | Telefon doğrulaması | 1M | audio, embedding, image, pdf, reasoning, rerank, text, video, vision | <a href="https://build.nvidia.com/settings/api-keys" target="_blank" rel="noopener">→</a> |
| ModelScope | 61 | Kayıt | 1M | audio, image, reasoning, text, video, vision | <a href="https://modelscope.cn/my/myaccesstoken" target="_blank" rel="noopener">→</a> |
| Cloudflare Workers AI | 40 | Hayır | 262K | code, image, reasoning, text, video | <a href="https://dash.cloudflare.com/profile/api-token" target="_blank" rel="noopener">→</a> |
| OpenCode Zen | 34 | Kayıt | 1M | audio, reasoning, vision | <a href="https://opencode.ai/auth" target="_blank" rel="noopener">→</a> |
| LLM7.io | 24 | Hayır | 1M | audio, code, image, pdf, reasoning, text, video, vision | <a href="https://token.llm7.io" target="_blank" rel="noopener">→</a> |
| Kilo Code | 22 | Hayır | 1M | audio, code, image, reasoning, text, video | <a href="https://app.kilo.ai/profile" target="_blank" rel="noopener">→</a> |
| Google Gemini | 19 | Hayır | 1M | audio, image, pdf, reasoning, text, video, vision | <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener">→</a> |
| Ollama Cloud | 17 | Kayıt | 1M | code, image, reasoning, text, video, vision | <a href="https://ollama.com/settings/keys" target="_blank" rel="noopener">→</a> |
| Mistral AI | 15 | Hayır | 256K | code, image, text | <a href="https://console.mistral.ai/api-keys" target="_blank" rel="noopener">→</a> |
| OVHcloud AI Endpoints | 15 | Kayıt | 262K | audio, code, image, reasoning, text, video | <a href="https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/" target="_blank" rel="noopener">→</a> |
| Groq | 12 | Hayır | 262K | image, reasoning, text, video | <a href="https://console.groq.com/keys" target="_blank" rel="noopener">→</a> |
| Cohere | 12 | Hayır | 256K | image, text | <a href="https://dashboard.cohere.com/api-keys" target="_blank" rel="noopener">→</a> |
| Aion Labs | 11 | Kayıt | 131K | text | <a href="https://www.aionlabs.ai/app/api-keys/" target="_blank" rel="noopener">→</a> |
| Hugging Face | 9 | Hayır | 131K | code, image, text | <a href="https://huggingface.co/settings/token" target="_blank" rel="noopener">→</a> |
| Z AI (Zhipu AI) | 8 | Hayır | 200K | image, reasoning, text, video | <a href="https://open.bigmodel.cn/usercenter/apikeys" target="_blank" rel="noopener">→</a> |
| Cerebras | 6 | Hayır | 131K | reasoning, text | <a href="https://cloud.cerebras.ai/" target="_blank" rel="noopener">→</a> |
| Agnes AI | 5 | Kayıt | 256K | image, reasoning, text, video, vision | <a href="https://platform.agnes-ai.com/settings/apiKeys" target="_blank" rel="noopener">→</a> |
| Alibaba Cloud Model Studio | 5 | Kayıt | 1M | code, image, text | <a href="https://bailian.console.alibabacloud.com/?apiKey=1" target="_blank" rel="noopener">→</a> |
| SiliconFlow | 4 | Kayıt | 131K | reasoning, text | <a href="https://cloud.siliconflow.cn/account/ak" target="_blank" rel="noopener">→</a> |
| SambaNova | 4 | Kayıt | 128K | image, reasoning, text | <a href="https://cloud.sambanova.ai/apis" target="_blank" rel="noopener">→</a> |
| Cline | 4 | Kayıt | 0 | text | <a href="" target="_blank" rel="noopener">→</a> |
| xAI | 3 | Kayıt | 2M | text | <a href="https://console.x.ai" target="_blank" rel="noopener">→</a> |
| Chutes.ai | 2 | Kayıt | 131K | reasoning, text | <a href="https://chutes.ai/" target="_blank" rel="noopener">→</a> |
| Glhf.chat | 2 | Kayıt | 131K | text | <a href="https://glhf.chat/" target="_blank" rel="noopener">→</a> |
| Grok (xAI) | 2 | Kayıt | 131K | text | <a href="https://console.x.ai/" target="_blank" rel="noopener">→</a> |
| AI21 Labs | 2 | Kayıt | 256K | text | <a href="https://studio.ai21.com/account/api-key" target="_blank" rel="noopener">→</a> |
| DeepSeek | 2 | Kayıt | 128K | text | <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener">→</a> |
| Nscale | 2 | Kayıt | 128K | text | <a href="https://console.nscale.com/" target="_blank" rel="noopener">→</a> |
| Nebius | 1 | Kayıt | 128K | text | <a href="https://studio.nebius.com/settings/api-keys" target="_blank" rel="noopener">→</a> |
<!-- END_PERMANENT_FREE -->

### 💰 Yenilenen Krediler

Ücretsiz kredilerini düzenli olarak yenileyen sağlayıcılar.

<!-- BEGIN_RENEWABLE -->
| Sağlayıcı | Ücretsiz Model | Kredi Modeli | Maks. Bağlam | Modaliteler | API Anahtarı Al |
|---|---|---|---|---|---|
| OpenRouter | 31 | Ücretsiz katman + 10$ yükleme → 1K RPD | 1M | audio, code, decisions, embeddings, image, reasoning, rerank, speech, text, video | <a href="https://openrouter.ai/workspaces/default/keys" target="_blank" rel="noopener">→</a> |
<!-- END_RENEWABLE -->

## Hızlı Başvuru — Temel URL'ler ve API Anahtarları

<!-- BEGIN_QUICK_REF -->
| Sağlayıcı | Temel URL | API Anahtarı Al | Kredi Kartı? |
|---|---|---|---|
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | <a href="https://build.nvidia.com/settings/api-keys" target="_blank" rel="noopener">Anahtar Al →</a> | Telefon doğrulaması |
| ModelScope | `https://api-inference.modelscope.cn/v1` | <a href="https://modelscope.cn/my/myaccesstoken" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Cloudflare Workers AI | `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run` | <a href="https://dash.cloudflare.com/profile/api-token" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| OpenCode Zen | `https://opencode.ai/zen/v1` | <a href="https://opencode.ai/auth" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| OpenRouter | `https://openrouter.ai/api/v1` | <a href="https://openrouter.ai/workspaces/default/keys" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| LLM7.io | `https://api.llm7.io/v1` | <a href="https://token.llm7.io" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Kilo Code | `https://api.kilo.ai/api/gateway` | <a href="https://app.kilo.ai/profile" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta` | <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Ollama Cloud | `https://ollama.com/api` | <a href="https://ollama.com/settings/keys" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Mistral AI | `https://api.mistral.ai/v1` | <a href="https://console.mistral.ai/api-keys" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| OVHcloud AI Endpoints | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` | <a href="https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Groq | `https://api.groq.com/openai/v1` | <a href="https://console.groq.com/keys" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Cohere | `https://api.cohere.com/v2` | <a href="https://dashboard.cohere.com/api-keys" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Aion Labs | `https://api.aionlabs.ai/v1` | <a href="https://www.aionlabs.ai/app/api-keys/" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Hugging Face | `https://router.huggingface.co/v1` | <a href="https://huggingface.co/settings/token" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Z AI (Zhipu AI) | `https://open.bigmodel.cn/api/paas/v4` | <a href="https://open.bigmodel.cn/usercenter/apikeys" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Cerebras | `https://api.cerebras.ai/v1` | <a href="https://cloud.cerebras.ai/" target="_blank" rel="noopener">Anahtar Al →</a> | Hayır |
| Agnes AI | `https://apihub.agnes-ai.com/v1` | <a href="https://platform.agnes-ai.com/settings/apiKeys" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Alibaba Cloud Model Studio | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | <a href="https://bailian.console.alibabacloud.com/?apiKey=1" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| SiliconFlow | `https://api.siliconflow.cn/v1` | <a href="https://cloud.siliconflow.cn/account/ak" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| SambaNova | `https://api.sambanova.ai/v1` | <a href="https://cloud.sambanova.ai/apis" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Cline | `` | <a href="" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| xAI | `https://api.x.ai/v1` | <a href="https://console.x.ai" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Chutes.ai | `https://api.chutes.ai/v1` | <a href="https://chutes.ai/" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Glhf.chat | `https://glhf.chat/api/openai/v1` | <a href="https://glhf.chat/" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Grok (xAI) | `https://api.x.ai/v1` | <a href="https://console.x.ai/" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| AI21 Labs | `https://api.ai21.com/studio/v1` | <a href="https://studio.ai21.com/account/api-key" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| DeepSeek | `https://api.deepseek.com/v1` | <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Nscale | `https://inference.api.nscale.com/v1` | <a href="https://console.nscale.com/" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
| Nebius | `https://api.studio.nebius.com/v1` | <a href="https://studio.nebius.com/settings/api-keys" target="_blank" rel="noopener">Anahtar Al →</a> | Kayıt |
<!-- END_QUICK_REF -->

## Sağlayıcıya Göre En İyi Ücretsiz Modeller

<!-- BEGIN_BEST_MODELS -->
| Sağlayıcı | En İyi Ücretsiz Model | Model Kimliği | Maks. Bağlam | İstek Limiti |
|---|---|---|---|---|
| NVIDIA NIM | <a href="https://freellm.net/models/nvidia-nim/z-ai-glm-5-3-flash/" target="_blank" rel="noopener">z-ai/glm-5.3-flash</a> | `z-ai/glm-5.3-flash` | 1M | Up to 40 RPM |
|  | <a href="https://freellm.net/models/nvidia-nim/z-ai-glm-5-2/" target="_blank" rel="noopener">z-ai/glm-5.2</a> | `z-ai/glm-5.2` | 1M | Up to 40 RPM |
|  | <a href="https://freellm.net/models/nvidia-nim/z-ai-glm-5-1/" target="_blank" rel="noopener">z-ai/glm-5.1</a> | `z-ai/glm-5.1` | 202K | Up to 40 RPM |
| ModelScope | <a href="https://freellm.net/models/modelscope/minimax-minimax-m2-5/" target="_blank" rel="noopener">MiniMax-M2.5-highspeed</a> | `MiniMax/MiniMax-M2.5` | 204K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/modelscope/qwen-qwen3-5-35b-a3b/" target="_blank" rel="noopener">Qwen/Qwen3.5-35B-A3B</a> | `qwen-qwen3-5-35b-a3b` | 256K | 2,000 RPD total; <=500 .. |
|  | <a href="https://freellm.net/models/modelscope/qwen-qwen3-5-27b/" target="_blank" rel="noopener">Qwen/Qwen3.5-27B</a> | `qwen-qwen3-5-27b` | 256K | 2,000 RPD total; <=500 .. |
| Cloudflare Workers AI | <a href="https://freellm.net/models/cloudflare-workers-ai/mistral-mistral-7b-instruct-v0-1/" target="_blank" rel="noopener">Mistral 7B</a> | `@cf/mistral/mistral-7b-instruct-v0.1` | 32K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/cloudflare-workers-ai/qwen-qwen1-5-7b-chat/" target="_blank" rel="noopener">Qwen 1.5 7B</a> | `@cf/qwen/qwen1.5-7b-chat` | 32K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/cloudflare-workers-ai/cf-meta-llama-3-3-70b-instruct-fp8-fast/" target="_blank" rel="noopener">@cf/meta/llama-3.3-70b-instruct-fp8-fast</a> | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | 24K | 10K neurons/day (shared) |
| OpenCode Zen | <a href="https://freellm.net/models/opencode/big-pickle/" target="_blank" rel="noopener">big-pickle</a> | `big-pickle` | 0 |  |
|  | <a href="https://freellm.net/models/opencode/deepseek-v4-flash-free/" target="_blank" rel="noopener">DeepSeek V4 Flash</a> | `deepseek-v4-flash-free` | 1M |  |
|  | <a href="https://freellm.net/models/opencode/mimo-v2-5-free/" target="_blank" rel="noopener">MiMo-V2.5</a> | `mimo-v2.5-free` | 1M |  |
| OpenRouter | <a href="https://freellm.net/models/openrouter/nvidia-nemotron-3-ultra-550b-a55b/" target="_blank" rel="noopener">NVIDIA: Nemotron 3 Ultra (free)</a> | `nvidia/nemotron-3-ultra-550b-a55b:free` | 1M | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/openrouter/poolside-laguna-s-2.1/" target="_blank" rel="noopener">Poolside: Laguna S 2.1 (free)</a> | `poolside/laguna-s-2.1:free` | 262K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/openrouter/nvidia-nemotron-3.5-lightning/" target="_blank" rel="noopener">NVIDIA: Nemotron 3.5 Lightning (free)</a> | `nvidia/nemotron-3.5-lightning:free` | 1M | Sağlayıcıya bak |
| LLM7.io | <a href="https://freellm.net/models/llm7-io/gpt-oss-20b/" target="_blank" rel="noopener">gpt-oss:20b</a> | `gpt-oss-20b` | 128K | 60 RPM, 250 req/hr (fre.. |
|  | <a href="https://freellm.net/models/llm7-io/mistral-nemo-instruct-2407/" target="_blank" rel="noopener">mistral-Nemo-Instruct-2407</a> | `mistral-Nemo-Instruct-2407` | 128K | 60 RPM, 250 req/hr (fre.. |
|  | <a href="https://freellm.net/models/llm7-io/minimax-m2-7/" target="_blank" rel="noopener">minimax-m2.7</a> | `minimax-m2-7` | 180K | 60 RPM, 250 req/hr (fre.. |
| Kilo Code | <a href="https://freellm.net/models/kilo-code/nvidia-nemotron-3-ultra-550b-a55b-free/" target="_blank" rel="noopener">nvidia/nemotron-3-ultra-550b-a55b:free</a> | `nvidia/nemotron-3-ultra-550b-a55b:free` | 1M | 200 req/hr |
|  | <a href="https://freellm.net/models/kilo-code/stepfun-step-3-7-flash-free/" target="_blank" rel="noopener">stepfun/step-3.7-flash:free</a> | `stepfun/step-3.7-flash` | 262K | 200 req/hr |
|  | <a href="https://freellm.net/models/kilo-code/nvidia-nemotron-3-super-120b-a12b-free/" target="_blank" rel="noopener">nvidia/nemotron-3-super-120b-a12b:free</a> | `nvidia/nemotron-3-super-120b-a12b:free` | 262K | 200 req/hr |
| Google Gemini | <a href="https://freellm.net/models/google-gemini/gemini-3-8-flash/" target="_blank" rel="noopener">Gemini 3.8 Flash</a> | `gemini-3.8-flash` | 1M | — |
|  | <a href="https://freellm.net/models/google-gemini/gemini-3-7-flash/" target="_blank" rel="noopener">Gemini 3.7 Flash</a> | `gemini-3.7-flash` | 1M | — |
|  | <a href="https://freellm.net/models/google-gemini/gemini-3-6-flash/" target="_blank" rel="noopener">Gemini 3.6 Flash</a> | `gemini-3.6-flash` | 1M | 15 RPM, 1,500 RPD |
| Ollama Cloud | <a href="https://freellm.net/models/ollama-cloud/deepseek-v4-pro/" target="_blank" rel="noopener">deepseek-v4-pro</a> | `deepseek-v4-pro` | 1M | Session/weekly limits (.. |
|  | <a href="https://freellm.net/models/ollama-cloud/deepseek-v4-flash/" target="_blank" rel="noopener">deepseek-v4-flash</a> | `deepseek-v4-flash` | 1M | Session/weekly limits (.. |
|  | <a href="https://freellm.net/models/ollama-cloud/minimax-m3/" target="_blank" rel="noopener">minimax-m3</a> | `minimax-m3` | 512K | Session/weekly limits (.. |
| Mistral AI | <a href="https://freellm.net/models/mistral-ai/open-mistral-7b/" target="_blank" rel="noopener">Mistral 7B</a> | `open-mistral-7b` | 32K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/mistral-ai/open-mixtral-8x7b/" target="_blank" rel="noopener">Mixtral 8x7B</a> | `open-mixtral-8x7b` | 32K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/mistral-ai/mistral-medium-3-5-128b/" target="_blank" rel="noopener">Mistral Medium 3.5 (128B)</a> | `mistral-medium-3-5-128b` | 256K | ~1 RPS, 500K TPM |
| OVHcloud AI Endpoints | <a href="https://freellm.net/models/ovhcloud-ai-endpoints/qwen3-5-397b-a17b/" target="_blank" rel="noopener">Qwen3.5-397B-A17B</a> | `qwen3.5-397b-a17b` | 262K | 2 RPM (anonim) |
|  | <a href="https://freellm.net/models/ovhcloud-ai-endpoints/meta-llama-3-3-70b-instruct/" target="_blank" rel="noopener">Meta-Llama-3_3-70B-Instruct</a> | `meta-llama-3_3-70b-instruct` | 131K | 2 RPM (anonim) |
|  | <a href="https://freellm.net/models/ovhcloud-ai-endpoints/qwen3-8-27b/" target="_blank" rel="noopener">Qwen3.8-27B</a> | `qwen3.8-27b` | 262K | 2 RPM (anonim) |
| Groq | <a href="https://freellm.net/models/groq/moonshotai-kimi-k2-instruct/" target="_blank" rel="noopener">Moonshot Kimi K2</a> | `moonshotai/kimi-k2-instruct` | 131K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/groq/moonshotai-kimi-k2-instruct-0905/" target="_blank" rel="noopener">Moonshot Kimi K2 0905</a> | `moonshotai/kimi-k2-instruct-0905` | 131K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/groq/groq-compound/" target="_blank" rel="noopener">groq/compound</a> | `groq/compound` | 131K | 30 RPM, 250 RPD |
| Cohere | <a href="https://freellm.net/models/cohere/command-a-218b/" target="_blank" rel="noopener">Command A+ (218B)</a> | `command-a-218b` | 128K | 20 RPM |
|  | <a href="https://freellm.net/models/cohere/command-a-111b/" target="_blank" rel="noopener">Command A (111B)</a> | `command-a-111b` | 256K | 20 RPM |
|  | <a href="https://freellm.net/models/cohere/command-r/" target="_blank" rel="noopener">Command R+</a> | `command-r` | 128K | 20 RPM |
| Aion Labs | <a href="https://freellm.net/models/aion-labs/aion-labs-aion-2-0/" target="_blank" rel="noopener">aion-labs/aion-2.0</a> | `aion-labs-aion-2-0` | 128K | 15 RPM, 20K TPD |
|  | <a href="https://freellm.net/models/aion-labs/aion-labs-aion-rp-llama-3-1-8b/" target="_blank" rel="noopener">aion-labs/aion-rp-llama-3.1-8b</a> | `aion-labs-aion-rp-llama-3-1-8b` | 32K | 15 RPM, 20K TPD |
|  | <a href="https://freellm.net/models/aion-labs/aion-labs-aion-3-0/" target="_blank" rel="noopener">aion-labs/aion-3.0</a> | `aion-labs-aion-3-0` | 128K | 15 RPM, 20K TPD |
| Hugging Face | <a href="https://freellm.net/models/hugging-face/meta-llama-3-1-8b-instruct/" target="_blank" rel="noopener">Meta-Llama-3.1-8B-Instruct</a> | `meta-llama-3-1-8b-instruct` | 128K | Krediye bağlı |
|  | <a href="https://freellm.net/models/hugging-face/gemma-3-4b-it/" target="_blank" rel="noopener">gemma-3-4b-it</a> | `google/gemma-3-4b-it` | 131K | Krediye bağlı |
|  | <a href="https://freellm.net/models/hugging-face/phi-4/" target="_blank" rel="noopener">phi-4</a> | `phi-4` | 16K | Krediye bağlı |
| Z AI (Zhipu AI) | <a href="https://freellm.net/models/z-ai-zhipu-ai/glm-4-7-flash/" target="_blank" rel="noopener">GLM-4.7-Flash</a> | `glm-4.7-flash` | 200K | 1 eşzamanlı istek |
|  | <a href="https://freellm.net/models/z-ai-zhipu-ai/glm-4-5-flash-retirement-announced/" target="_blank" rel="noopener">GLM-4.5-Flash (retirement announced)</a> | `glm-4-5-flash-retirement-announced` | 128K | 1 eşzamanlı istek |
|  | <a href="https://freellm.net/models/z-ai-zhipu-ai/glm-4-6v-flash/" target="_blank" rel="noopener">GLM-4.6V-Flash</a> | `glm-4.6v-flash` | 128K | 1 eşzamanlı istek |
| Cerebras | <a href="https://freellm.net/models/cerebras/llama3-1-70b/" target="_blank" rel="noopener">Llama 3.1 70B</a> | `llama3.1-70b` | 131K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/cerebras/zai-glm-4-7-deprecated-aug-2026/" target="_blank" rel="noopener">zai-glm-4.7 (deprecated Aug 2026)</a> | `zai-glm-4-7-deprecated-aug-2026` | 131K | 5 RPM, 30K TPM, 1M TPD |
|  | <a href="https://freellm.net/models/cerebras/zai-glm-4-7/" target="_blank" rel="noopener">zai-glm-4.7</a> | `zai-glm-4.7` | 128K | 10 RPM, 100 RPD, 1M TPD |
| Agnes AI | <a href="https://freellm.net/models/agnes-ai/agnes-1.5-flash/" target="_blank" rel="noopener">agnes-1.5-flash</a> | `agnes-1.5-flash` | 256K | 30 RPM |
|  | <a href="https://freellm.net/models/agnes-ai/agnes-2.0-flash/" target="_blank" rel="noopener">agnes-2.0-flash</a> | `agnes-2.0-flash` | 256K | 30 RPM |
|  | <a href="https://freellm.net/models/agnes-ai/agnes-image-2.0-flash/" target="_blank" rel="noopener">agnes-image-2.0-flash</a> | `agnes-image-2.0-flash` | 4K | 30 RPM (1K) |
| Alibaba Cloud Model Studio | <a href="https://freellm.net/models/alibaba-cloud-model-studio/qwen3-max/" target="_blank" rel="noopener">Qwen3-Max</a> | `qwen3-max` | 128K | Bölgeye göre kademeli |
|  | <a href="https://freellm.net/models/alibaba-cloud-model-studio/qwen3-plus/" target="_blank" rel="noopener">Qwen3-Plus</a> | `qwen3-plus` | 1M | Bölgeye göre kademeli |
|  | <a href="https://freellm.net/models/alibaba-cloud-model-studio/qwen3-vl-plus/" target="_blank" rel="noopener">Qwen3-VL-Plus</a> | `qwen3-vl-plus` | 128K | Bölgeye göre kademeli |
| SiliconFlow | <a href="https://freellm.net/models/siliconflow/qwen-qwen3-8b/" target="_blank" rel="noopener">Qwen/Qwen3-8B</a> | `Qwen/Qwen3-8B` | 128K | 1,000 RPM, 50,000 TPM |
|  | <a href="https://freellm.net/models/siliconflow/abbreviation/" target="_blank" rel="noopener">Abbreviation</a> | `abbreviation` | 131K | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/siliconflow/deepseek-ai-deepseek-r1-distill-qwen-7b/" target="_blank" rel="noopener">deepseek-ai/DeepSeek-R1-Distill-Qwen-7B</a> | `deepseek-ai-deepseek-r1-distill-qwen-7b` | 131K | 30 RPM, 60K TPM |
| SambaNova | <a href="https://freellm.net/models/sambanova/deepseek-v3-1/" target="_blank" rel="noopener">DeepSeek-V3.1</a> | `deepseek-v3-1` | 128K | 20 RPM, 20 RPD, 200K TPD |
|  | <a href="https://freellm.net/models/sambanova/deepseek-v3-2-preview/" target="_blank" rel="noopener">DeepSeek-V3.2 (Preview)</a> | `deepseek-v3-2-preview` | 128K | 20 RPM, 20 RPD, 200K TPD |
|  | <a href="https://freellm.net/models/sambanova/minimax-m2-7/" target="_blank" rel="noopener">MiniMax-M2.7</a> | `minimax-m2-7` | 128K | 20 RPM, 20 RPD, 200K TPD |
| Cline | <a href="https://freellm.net/models/cline/cline-free-muse-spark-1-3-contributor/" target="_blank" rel="noopener">Muse Spark 1.3 Contributor</a> | `cline-free/muse-spark-1.3-contributor` | 0 | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/cline/cline-free-mimo-v2-6-flash/" target="_blank" rel="noopener">Mimo V2.6 Flash</a> | `cline-free/mimo-v2.6-flash` | 0 | Sağlayıcıya bak |
|  | <a href="https://freellm.net/models/cline/cline-free-solar-mini4/" target="_blank" rel="noopener">Solar Mini 4</a> | `cline-free/solar-mini4` | 0 | Sağlayıcıya bak |
| xAI | <a href="https://freellm.net/models/xai/grok-4-3/" target="_blank" rel="noopener">grok-4.3</a> | `grok-4-3` | 1M | Kredi tabanlı |
|  | <a href="https://freellm.net/models/xai/grok-4-1-fast/" target="_blank" rel="noopener">grok-4.1-fast</a> | `grok-4-1-fast` | 2M | Kredi tabanlı |
|  | <a href="https://freellm.net/models/xai/grok-3-mini/" target="_blank" rel="noopener">grok-3-mini</a> | `grok-3-mini` | 131K | Kredi tabanlı |
| Chutes.ai | <a href="https://freellm.net/models/chutes-ai/deepseek-ai-deepseek-r1/" target="_blank" rel="noopener">DeepSeek-R1</a> | `deepseek-ai/DeepSeek-R1` | 131K | Community-powered, no h.. |
|  | <a href="https://freellm.net/models/chutes-ai/meta-llama-meta-llama-3-1-70b-instruct/" target="_blank" rel="noopener">Llama 3.1 70B</a> | `meta-llama/Meta-Llama-3.1-70B-Instruct` | 131K | Community-powered, no h.. |
| Glhf.chat | <a href="https://freellm.net/models/glhf-chat/meta-llama-meta-llama-3-1-70b-instruct-2/" target="_blank" rel="noopener">Llama 3.1 70B</a> | `meta-llama/Meta-Llama-3.1-70B-Instruct` | 131K | Ücretsiz modeller için sınırsız |
|  | <a href="https://freellm.net/models/glhf-chat/mistralai-mixtral-8x7b-instruct-v0-1/" target="_blank" rel="noopener">Mixtral 8x7B</a> | `mistralai/Mixtral-8x7B-Instruct-v0.1` | 32K | Ücretsiz modeller için sınırsız |
| Grok (xAI) | <a href="https://freellm.net/models/grok-(xai)/grok-2/" target="_blank" rel="noopener">Grok-2</a> | `grok-2` | 131K | $25/month free credits,.. |
|  | <a href="https://freellm.net/models/grok-(xai)/grok-2-mini/" target="_blank" rel="noopener">Grok-2 Mini</a> | `grok-2-mini` | 131K | $25/month free credits,.. |
| AI21 Labs | <a href="https://freellm.net/models/ai21-labs/jamba-large-1-7/" target="_blank" rel="noopener">Jamba Large 1.7</a> | `jamba-large-1-7` | 256K | 200 RPM, 10 RPS |
|  | <a href="https://freellm.net/models/ai21-labs/jamba-mini-2/" target="_blank" rel="noopener">Jamba Mini 2</a> | `jamba-mini-2` | 256K | 200 RPM, 10 RPS |
| DeepSeek | <a href="https://freellm.net/models/deepseek/deepseek-chat-v3-2/" target="_blank" rel="noopener">deepseek-chat (V3.2)</a> | `deepseek-chat-v3-2` | 128K | Dinamik |
|  | <a href="https://freellm.net/models/deepseek/deepseek-reasoner-r1/" target="_blank" rel="noopener">deepseek-reasoner (R1)</a> | `deepseek-reasoner-r1` | 128K | Dinamik |
| Nscale | <a href="https://freellm.net/models/nscale/llama-3-3-70b-instruct/" target="_blank" rel="noopener">Llama-3.3-70B-Instruct</a> | `llama-3-3-70b-instruct` | 128K | Adil kullanım |
|  | <a href="https://freellm.net/models/nscale/deepseek-r1-distill-llama-70b/" target="_blank" rel="noopener">DeepSeek-R1-Distill-Llama-70B</a> | `deepseek-r1-distill-llama-70b` | 128K | Adil kullanım |
| Nebius | <a href="https://freellm.net/models/nebius/qwen3-235b-a22b/" target="_blank" rel="noopener">Qwen3-235B-A22B</a> | `qwen3-235b-a22b` | 128K | Kademeli |
<!-- END_BEST_MODELS -->



### 🖥️ Yerel / Kendi Sunucunda (Sınırsız, Özel, Sonsuza Dek Ücretsiz)

| Araç | Tür | Öne Çıkanlar |
|---|---|---|
| <a href="https://ollama.com" target="_blank" rel="noopener">Ollama</a> | CLI + API | 100+ model, GPU hızlandırma, OpenAI uyumlu uç nokta |
| <a href="https://lmstudio.ai" target="_blank" rel="noopener">LM Studio</a> | Masaüstü arayüz | Her GGUF modeli, yerleşik model tarayıcı, çevrimdışı |
| <a href="https://github.com/ggerganov/llama.cpp" target="_blank" rel="noopener">llama.cpp</a> | C/C++ motoru | Her GGUF'yi çalıştırır, minimum bağımlılık |
| <a href="https://gpt4all.io" target="_blank" rel="noopener">GPT4All</a> | Masaüstü uygulama | Yalnızca CPU, GPU gerekmez, açık kaynak |
| <a href="https://jan.ai" target="_blank" rel="noopener">Jan.ai</a> | Masaüstü uygulama | Gizlilik odaklı, %100 çevrimdışı ChatGPT alternatifi |
| <a href="https://github.com/LostRuins/koboldcpp" target="_blank" rel="noopener">KoboldCpp</a> | Tek çalıştırılabilir dosya | Yaratıcı yazım için optimize, GGUF |

---

## En Popüler Ücretsiz Modeller (Haftalık Kullanıma Göre)

Veriler freellm.net'ten alınır, API izlemesiyle her gün güncellenir.

<!-- BEGIN_TOP_MODELS -->
| Model | Sağlayıcı | Bağlam | Haftalık Kullanım |
|---|---|---|---|
| <a href="https://freellm.net/models/openrouter/nvidia-nemotron-3-ultra-550b-a55b/" target="_blank" rel="noopener">NVIDIA: Nemotron 3 Ultra (free)</a> | OpenRouter | 1M | 6873B token |
| <a href="https://freellm.net/models/nvidia-nim/z-ai-glm-5-3-flash/" target="_blank" rel="noopener">z-ai/glm-5.3-flash</a> | NVIDIA NIM | 1M | 3786B token |
| <a href="https://freellm.net/models/nvidia-nim/z-ai-glm-5-2/" target="_blank" rel="noopener">z-ai/glm-5.2</a> | NVIDIA NIM | 1M | 2998B token |
| <a href="https://freellm.net/models/openrouter/poolside-laguna-s-2.1/" target="_blank" rel="noopener">Poolside: Laguna S 2.1 (free)</a> | OpenRouter | 262K | 993B token |
| <a href="https://freellm.net/models/openrouter/nvidia-nemotron-3.5-lightning/" target="_blank" rel="noopener">NVIDIA: Nemotron 3.5 Lightning (free)</a> | OpenRouter | 1M | 913B token |
| <a href="https://freellm.net/models/openrouter/dots-studio-dots-3-note-preview/" target="_blank" rel="noopener">Dots Studio: Dots3-Note Preview (free)</a> | OpenRouter | 512K | 773B token |
| <a href="https://freellm.net/models/openrouter/poolside-laguna-m-1/" target="_blank" rel="noopener">Poolside: Laguna M.1 (free)</a> | OpenRouter | 262K | 768B token |
| <a href="https://freellm.net/models/openrouter/inclusionai-ling-3.1-flash/" target="_blank" rel="noopener">inclusionAI: Ling 3.1 Flash</a> | OpenRouter | 262K | 630B token |
| <a href="https://freellm.net/models/openrouter/nvidia-nemotron-3-super-120b-a12b/" target="_blank" rel="noopener">NVIDIA: Nemotron 3 Super (free)</a> | OpenRouter | 262K | 625B token |
| <a href="https://freellm.net/models/openrouter/apodex-apodex-1.1-mini/" target="_blank" rel="noopener">Apodex: Apodex 1.1 Mini (free)</a> | OpenRouter | 262K | 285B token |
<!-- END_TOP_MODELS -->

---

## Depo Yapısı

```
awesome-free-llm-apis/
├── README.md              ← Tam sağlayıcı dizini ve kod örnekleri
├── code-examples/          ← Kullanıma hazır yapılandırma parçacıkları
│   ├── claude-code.md
│   ├── cursor.md
│   └── codex.md
└── LICENSE                 ← MIT
```

> 453 modelin yer aldığı, günlük güncellenen tam yapılandırılmış veri seti için şu adresi ziyaret et: **<a href="https://freellm.net" target="_blank" rel="noopener">freellm.net</a>**.

---

## Katkıda Bulunma

Katkılara açığız!

- **Eksik bir ücretsiz modeli ekle** — <a href="https://github.com/open-free-llm-api/awesome-free-llm-apis/issues" target="_blank" rel="noopener">issue</a> aç veya PR gönder
- **Yanlış verileri düzelt** — İstek limitleri değişir, sağlayıcılar ücretsiz katmandan çıkar. PR'lar memnuniyetle karşılanır
- **Yapılandırma parçacığı ekle** — Kapsamadığımız bir araç için çalışan bir yapılandırman var mı? `code-examples/` içine ekle

### Dahil Edilme Ölçütleri

Bir model şu durumlarda bu listeye dahil edilir:
1. Sağlayıcı açıkça bir **ücretsiz katman** sunuyorsa (yalnızca deneme kredisi değil)
2. API **herkese açıksa** (bekleme listesi, kapalı beta veya tersine mühendislik yok)
3. Deneme kredileri için: açıkça etiketlenmiş ve en az 1$ kredi değerinde

---

## Bağlantılar

- 🌐 **Canlı site**: <a href="https://freellm.net" target="_blank" rel="noopener">freellm.net</a> — arama, karşılaştırma, deneme alanı, yapılandırma oluşturucu
- 🔑 **API anahtarı dizini**: <a href="https://freellm.net/free-llm-api-keys/" target="_blank" rel="noopener">freellm.net/free-llm-api-keys/</a>
- ⚙️ **Yapılandırma oluşturucu**: <a href="https://freellm.net/config/" target="_blank" rel="noopener">freellm.net/config/</a>
- 🎮 **Deneme alanı**: <a href="https://freellm.net/playground/" target="_blank" rel="noopener">freellm.net/playground/</a>
- 📊 **Modelleri karşılaştır**: <a href="https://freellm.net/compare/" target="_blank" rel="noopener">freellm.net/compare/</a>

## Lisans

MIT © <a href="https://github.com/open-free-llm-api" target="_blank" rel="noopener">open-free-llm-api</a>

---

<p align="center">
  <sub>Son güncelleme: <!-- AUTO_LAST_UPDATED -->
2026-10-12
<!-- END_AUTO_LAST_UPDATED --></sub>
</p>
