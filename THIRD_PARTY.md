# Üçüncü taraf kaynaklar ve teşekkürler

SIRIUS aşağıdaki iki açık kaynak projeden esinlenir ya da onların kodunu içerir. İkisi de **MIT** lisanslıdır; lisans metinleri `licenses/` altındadır.

## 1. zubair-trabzada/holo-gestures: kodu **dahil edildi**
- https://github.com/zubair-trabzada/holo-gestures (commit `55626ff`), © 2026 Zubair Trabzada / AI Workshop Studio LLC
- `holo/` klasöründedir; kaynak, lisans ve yapılan değişiklikler `holo/NOTICE.md` içinde. İçindeki MediaPipe (Apache-2.0) ve three.js (MIT) kendi lisanslarıyla gelir.

## 2. GauravSingh9356/J.A.R.V.I.S: fikirler **yeniden yazıldı**, kod kopyalanmadı
- https://github.com/GauravSingh9356/J.A.R.V.I.S (commit `a1227a7`), © 2020 GauravSingh9356
- Bu depo Windows'a sabit yazılmış (`D:\RoiNa.mp3`, `exec(open(...))`, onaysız `poweroff`, gömülü e-posta bilgileri) olduğundan satır satır
  taşınmadı; değerli fikirleri SIRIUS'un araç sistemine uygun, çapraz platform ve güvenli olarak **sıfırdan** yazdım:

| J.A.R.V.I.S özelliği | SIRIUS karşılığı | Fark |
|---|---|---|
| `wikipedia` komutu | `plugins/vikipedi.py` | Kütüphanesiz, resmi REST API; Türkçe önce, bulamazsa İngilizce; içerik "güvenilmez veri" etiketli |
| "intelligent dictionary" | `plugins/sozluk.py` | `difflib` ile yazım önerisi; çevrimdışı dosya isteğe bağlı (aşağıya bak) |
| `search youtube`, `location` | `plugins/hizli_baglantilar.py` | Sabit Chrome yolu yok; varsayılan tarayıcı |
| `OCR.py` | `plugins/ocr.py` | Canlı kamera döngüsü yerine tek dosya; sabit yol yok; Tesseract isteğe bağlı |
| `screenshot` | `plugins/ekran_goruntusu.py` | Gerçek klasör, geri alınabilir |
| `joke` | `plugins/saka.py` | Paketsiz; şakalar bu proje için yazıldı |
| `shutdown` | `plugins/guc_islemi.py` | **Her zaman onay ister**, Windows'ta 30 sn gecikmeli ve "iptal" edilebilir |

### Bilerek alınmayanlar
- **`Face-Recognition/trainer/trainer.yml`**: yazarın kendi yüzünden eğitilmiş biyometrik modeldir; başkasının yüz verisini dağıtmak doğru değil ve bizim için işe yaramaz.
- **`amazon.py`**: tek bir ürüne sabitlenmiş, kırılgan bir sayfa kazıyıcı.
- **`youtube_downloader.py`**: bozulmuş `pytube` sürümüne dayanıyor ve YouTube kullanım koşullarıyla çelişebilir.
- **`data.json`** (49.537 kelimelik sözlük, 4,9 MB): **pakete eklenmedi.** Dosyanın asıl kaynağı belirtilmemiş; yeniden dağıtmanın hakkı olduğundan emin değilim.
  İstersen `sozluk` aracını `action=indir` ile çalıştır (onay sorar): dosyayı doğrudan kendi bilgisayarına, özgün depodan indirir.
