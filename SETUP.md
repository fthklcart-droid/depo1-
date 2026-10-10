# SIRIUS kurulum rehberi

**Gerekenler:** Python 3.11 ya da üstü ve internet (paket indirmek için). Windows, macOS ve Linux desteklenir.

## Hızlı kurulum (3 adım)

1. Zip'i bir klasöre aç.
2. Kurulumu çalıştır:
   - **Windows:** `KURULUM.bat` dosyasına çift tıkla
   - **macOS / Linux:** `./kurulum.sh`
   - ya da her yerde: `python kurulum.py`
3. Sorulara cevap ver (Gemini anahtarını yapıştır; yazarken görünmez). Bitince:
   ```
   .venv/bin/python main.py --web        # Windows: .venv\Scripts\python main.py --web
   ```

Kurulum **yeniden çalıştırılabilir**: yarım kalırsa ya da hata verirse aynı komutu tekrar çalıştır; yaptıklarını atlar.

## Kurulum ne yapar

| Adım | İş |
|---|---|
| 1 | `.venv` sanal ortamı oluşturur (sistem Python'una dokunmaz) |
| 2 | `requirements.txt` paketlerini kurar; sesli mod için `requirements-voice.txt` (isteğe bağlı) |
| 3 | Gemini anahtarını alır: `GEMINI_API_KEY` ortam değişkeni, mevcut `config/api_keys.json` ya da gizli giriş. **Komut satırından anahtar kabul edilmez** (kabuk geçmişine düşer) |
| 4 | Anahtarı doğrular (yalnızca model listesini ister; üretim yapmaz, ücret doğurmaz) |
| 5 | İsteğe bağlı: testler, masaüstü kısayolu, başlatma |

Anahtar `config/api_keys.json` dosyasına **yalnızca sahibinin okuyabileceği izinle** yazılır ve git'e girmez. Kurulum günlüğü `memory/kurulum.log`; anahtarlar orada `***` olarak maskelenir.

## Otomatik kurulum (bir araç ya da betik için)

Soru sormadan, hata kodu döndürerek:
```bash
GEMINI_API_KEY="…" python kurulum.py --yes                 # çekirdek kurulum + anahtarı kaydet + doğrula
python kurulum.py --yes --voice --shortcut --test          # sesli paketler + kısayol + testler dahil
python kurulum.py --dry-run                                # hiçbir şey değiştirmeden planı yazar
```
`--yes` hiçbir soru sormaz; anahtar yoksa atlar ve uyarır (çıkış kodu yine 0). **Çıkış kodu:** `0` = tamam, `1` = Python sürümü uygun değil, sanal ortam kurulamadı ya da paketler indirilemedi.

**Başarı ölçütü:** çıktıda `✓ sanal ortam`, `✓ çekirdek paketler` ve (anahtar verdiysen) `✓ anahtar doğrulandı` satırları. Ayrıca:
```bash
.venv/bin/python -m pytest -q tests      # 142 test geçmeli (sesli paketler yoksa 1 test atlanır)
.venv/bin/python main.py                 # terminalde "saat kaç" yaz; anahtarsız da cevap verir
```

## Elle kurulum
```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY="…"                                # ya da config/api_keys.example.json → config/api_keys.json
python main.py --web
```

## Çalıştırma
| Komut | Ne yapar |
|---|---|
| `python main.py` | terminalde sohbet |
| `python main.py --web` | tarayıcıda arayüz (3B avatarlar, Bağlantılar, el kontrolü) |
| `python main.py --live` | sesli mod (Gemini Live; mikrofon ve kulaklık önerilir) |
| `python kisayol.py --run` | masaüstü kısayolu oluşturur ve açar |

Başka bir yapay zekâ sağlayıcısı (OpenAI, Ollama, OpenRouter…) için `config/api_keys.example.json` içindeki `llm` bölümüne bak; ayrıntı `README.md`'de.

## Sorun giderme
| Belirti | Çözüm |
|---|---|
| `Python 3.11 ya da üstü gerekir` | https://www.python.org/downloads/ ; Windows'ta kurarken "Add to PATH" işaretle |
| `sanal ortam kurulamadı` (Linux) | `sudo apt install python3-venv`, sonra tekrar çalıştır; ya da `--no-venv` |
| Sesli paketler kurulmadı (Linux) | `sudo apt install libportaudio2`, sonra `python kurulum.py --voice` |
| `anahtar doğrulanamadı` | Anahtarı AI Studio'dan kontrol et; ağ erişimini dene. Sohbet dışında her şey çalışır |
| Tarayıcıda kamera açılmıyor (HOLO) | Adres `127.0.0.1` ile açılmalı (kurulum bunu yapar); kamera iznini ver |
| Port dolu | `python main.py --web --port 4890` |

## Güvenlik notları
- Anahtarı e-postaya, sohbete ya da herkese açık bir depoya yapıştırma; yapıştırdıysan AI Studio'dan iptal edip yenisini üret.
- Web arayüzü yalnızca bu bilgisayardan erişilebilir ve her oturum için ayrı bir belirteç kullanır.
- Kod çalıştırma, komut, e-posta gönderme, kapatma gibi işler **her zaman sana sorar**; model kendi kendine onaylayamaz.
- Üçüncü taraf kaynaklar ve lisanslar: `THIRD_PARTY.md`, `licenses/`.
