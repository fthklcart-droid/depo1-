# SIRIUS — yeniden tasarlanmış kişisel asistan

Gemini ile çalışan, bilgisayarını kontrol edebilen, ses ve metin modlu asistan. Önceki sürümün
2300 satırlık tek parça `main.py` dosyası, test edilebilir küçük modüllere bölündü; yetenek sayısı
12'den **20 araca** çıktı.

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...        # ya da config/api_keys.json -> {"gemini_api_key": "..."}
python main.py                   # terminalde metin asistanı
python main.py --live            # sesli mod (Gemini Live)
python -m pytest tests           # 35 test, ağ ve donanım gerekmez
```

## Yetenekler

| Alan | Araçlar |
|---|---|
| Dosyalar | `file_controller` — listele, oku, yaz, ekle, taşı, kopyala, yeniden adlandır, ara, sil (çöp kutusuna); hepsi **geri alınabilir** |
| Hesap | `calculate` (güvenli AST, `eval` yok), `convert_units`, `datetime_info` (saat dilimleri, tarih farkı) |
| İnternet | `web_search`, `fetch_page`, `weather` (anahtar gerekmez) |
| Zaman | `reminder` — hatırlatıcılar yeniden başlatmada kaybolmaz |
| Not / yapılacaklar | `notes` — ekle, listele, ara, tamamla, sil |
| Bilgisayar | `open_app`, `clipboard`, `system_info`, `look_at_screen` (ekranı görür) |
| Kod | `run_python`, `run_shell` — **her zaman insana sorar**, model kendi kendine onaylayamaz |
| Bellek | `remember`, `recall_memory`, `forget`; sınırsız depolama, prompt'a sığan çekirdek + anahtar dizini |
| Kontrol | `undo`, `shutdown_assistant` |

### Yeni eklenenler

| Alan | Araçlar |
|---|---|
| Belgelerinde ara | `doc_search` — klasörleri indeksler (txt, md, kod, csv, docx, isteğe bağlı pdf), saf Python BM25 ile arar. Artımlı: yalnızca değişen dosyalar yeniden okunur. Hiçbir şey dışarı gönderilmez |
| Takvim | `calendar` — ekle, bugün, yaklaşan, sil, **çakışma uyarısı**, `.ics` içe/dışa aktarma |
| Sabah brifingi | `daily_briefing` — hava, takvim, yapılacaklar, hatırlatıcılar ve manşetleri tek çağrıda toplar; biri çökerse diğerleri gelir |
| E-posta | `email` — okunmamışları listele/oku (posta "okundu" olarak işaretlenmez); **göndermek her zaman insana sorar** |
| Akıllı ev | `home_assistant` — durumlar ve servis çağrıları; kilit, alarm, kapı, sirene onay gerekir |
| Para | `expenses` (harcama kaydı ve aylık özet), `currency_convert` (ECB kuru) |
| Haberler | `rss_feed` — world / turkce / tech / science / business ya da kendi RSS adresin |
| Metin | `summarize`, `translate` — metin, dosya ya da web sayfası |
| Dosya bakımı | `organize_folder` (önce kuru çalıştırma, sonra tek komutla **geri alınır**), `find_duplicates`, `largest_files`, `make_zip` |
| Yardımcılar | `utilities` — parola, uuid, hash, base64, JSON, regex, zar, zaman damgası |
| Hatırlatıcı | artık `hourly / daily / weekly` tekrarlı |
| Şeffaflık | `audit_log` — asistanın bu bilgisayarda ne yaptığını gösterir (`memory/audit.jsonl`; içerik ve parolalar kaydedilmez) |

Ayarlar `config/api_keys.json` içinde:

```json
{"gemini_api_key": "...",
 "email": {"user": "ben@ornek.com", "password": "uygulama-parolası", "imap_host": "imap.ornek.com", "smtp_host": "smtp.ornek.com"},
 "home_assistant": {"url": "http://homeassistant.local:8123", "token": "uzun-ömürlü-token"}}
```

### Araştırmadan çıkan kararlar

* 2026 kişisel asistan karşılaştırmaları, değeri **gösteriden çok günlük kullanımda** görüyor: takvim, e-posta, görev ve bellek bir arada
  ([Lindy](https://www.lindy.ai/blog/ai-personal-assistant), [Vellum](https://vellum.ai/blog/best-personal-ai-assistants),
  [Nexos](https://nexos.ai/blog/ai-personal-assistant/)). Bu yüzden `daily_briefing` ayrı özelliklerin üstüne kurulu bir araç.
* Aynı kaynaklar asıl ödünleşimi **izinler** olarak gösteriyor. Karşılığı: göndermeden/kilit açmadan önce insan onayı,
  `audit_log`, ve yerel-öncelikli belge araması.
* Açık kaynak SIRIUS benzerleri ([isair/sirius](https://docsearch.algolia.com/mcp/docs/repo/isair/sirius)) Home Assistant ve yerel bilgi
  tabanı sunuyor; ikisini de ekledim. (MCP istemcisi eklenmedi: ek bağımlılık ve ayrı güvenlik incelemesi gerektirir.)
* Gemini 3 çok turlu araç çağrılarında **thought signature**'ların geri gönderilmesini istiyor
  ([belgeler](https://ai.google.dev/gemini-api/docs/tools)). Önceki sürümüm geçmişi yeniden kurarken bunları düşürüyordu; şimdi modelin
  orijinal `Content` nesnesi aynen saklanıyor (`test_gemini_history_keeps_raw_content_for_thought_signatures`). Bu davranışı doğrudan
  resmi belgeden değil, üçüncü taraf özetlerden öğrendim; canlı API ile doğrulanmadı.
* **Prompt injection savunması:** web sayfası ve e-posta içeriği `[UNTRUSTED ...]` etiketiyle döner, sistem prompt'u bu içeriğin
  talimat olmadığını söyler, `summarize/translate` metni veri olarak çerçeveler.

**Yeni yetenek eklemek tek dosyadır:** `plugins/_template.py` dosyasını kopyalayıp adının başındaki
`_` işaretini kaldırın. Bozuk bir eklenti yalnızca kendi hatasını raporlar, oturumu düşürmez.

## Mimari (eski `main.py` → yeni yapı)

```
main.py                  ince giriş noktası: kablolama + mod seçimi
core/
  bootstrap.py           konsol UTF-8, Windows'ta pencere açmayan subprocess
  config.py              config/api_keys.json için tek okuyucu
  gemini.py              9 modelli merdiven, zaman aşımı, bekleme süreleri (kota 5dk / kesinti 30dk / erişim yok 6sa)
  agent.py, backends.py  araç döngüsü (metin modu) ve model arka uçları
  action_loader.py       actions/ ve plugins/ içindeki TOOL+run keşfi, hata yalıtımı
  result.py              araç sonucu: metin + isteğe bağlı görüntü
  sysprompt.py           modelin kendini bilmesi: yetenekler ve sınırlar canlı sistemden üretilir
  transcript.py          transkript temizleme ve tekrar engelleme
  audio_math.py          ses seviyesi ve ağız şekilleri (saf fonksiyonlar)
  ui.py                  motorun UI hakkında bildiği tek şey (Protocol) + ConsoleUI
  live/
    policy.py            bağlantı koptuğunda ne yapılır: saf `decide()` fonksiyonu
    state.py             MicGate (uyku/uyanma, push-to-talk, yankı kuyruğu) + EchoGuard
    audio.py             mikrofon/hoparlör akışları, avatar zamanlaması
    session.py           Live oturumu düzenleyicisi
```

### Tasarım kararları ve eski koda göre düzeltmeler

* **Tek sınıf yerine sorumluluklar.** `SiriusLive` ses, vizyon, onay, kayıt, bağlantı politikası ve
  araç dağıtımını bir arada tutuyordu. Şimdi her biri ayrı ve donanımsız test edilebilir.
* **TaskGroup hatalarının asıl sebebi artık okunuyor.** Eski kod `str(e)` ile kota / API anahtarı /
  ağ hatalarını arıyordu, ama `TaskGroup` hataları `"unhandled errors in a TaskGroup (1 sub-exception)"`
  olarak sarar — gerçek neden içindedir. `policy.leaves()` gruplara iniyor; bu yüzden model merdiveni
  ve yeniden bağlanma kararları gerçekten tetikleniyor (`tests/test_core.py::test_policy_sees_through_task_groups`).
* **`except` zinciri → `decide()`.** ~100 satırlık iç içe koşul, tek giriş/çıkışlı saf fonksiyon.
* **Görüntü, özel durum değil.** `screen_process` ve `_pending_vision` bayrak yığını yerine, herhangi
  bir araç `ToolResult(text, image=...)` döndürebilir; görüntü araç yanıtının hemen arkasından gönderilir
  (tek cevap, ikinci bir doğaçlama cevap yok).
* **Tüm araçlar kayıt defterinde.** Satır içi `TOOL_DECLARATIONS` kalktı; `shutdown`, `undo`, bellek
  araçları da kendi kendini tanımlayan modüller. `ctx.shutdown` gibi kancalar oturuma bağlanıyor.
* **Onay yalnızca arayüzden.** `confirmed=yes` gibi model parametresi yok; `ctx.confirm` insana sorar.
* **Oturum sürekliliği** korundu: devam tutamacı yalnızca RAM'de, ses değişince bilerek sıfırlanır,
  reddedilen tutamaç bir kez bırakılır.

## Sınırlar (dürüstçe)

* Sesli mod (`--live`) gerçek mikrofon, hoparlör ve Gemini Live anahtarı gerektirir; bu ortamda
  yalnızca yapılandırma kurulumu ve saf mantık test edildi, **uçtan uca canlı oturum denenmedi**.
* Avatar çizimi, uyandırma kelimesi motoru, push-to-talk kısayolu ve telefon panosu bu depoda yok;
  `UI` Protocol'ü, `LiveSession.wake_detector` ve `MicGate.ptt()` bunlar için takılma noktalarıdır.
* E-posta, Home Assistant ve `currency_convert`/`rss_feed` gerçek sunucularla denenmedi; testler onay kapılarını, ayrıştırmayı ve hata yollarını doğrular.
* Prompt injection savunması azaltır, ortadan kaldırmaz; onay kapıları asıl güvencedir.
* `web_search` DuckDuckGo HTML sayfasını ayrıştırır; sayfa biçimi değişirse bozulabilir.
