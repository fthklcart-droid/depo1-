# HOLO el hareketi paneli: kaynak ve değişiklikler

- **Kaynak:** https://github.com/zubair-trabzada/holo-gestures (commit `55626ff`)
- **Yazar / lisans:** Zubair Trabzada, AI Workshop Studio LLC. **MIT** (bkz. `LICENSE`).
- **Üçüncü taraf:** `vendor/` içinde Google MediaPipe Tasks Vision (Apache-2.0) ve three.js + GLTFLoader (MIT). Her iki
  `vendor/wasm/vision_wasm_*.js` dosyasının başında yazarın eklediği tek satırlık `HOLO SHIM` düzeltmesi vardır.

## SIRIUS'a uyarlarken yapılan değişiklikler
1. **Sunucu değişti.** Özgün `server.py` kullanılmıyor; sayfa SIRIUS sunucusunun `/holo/` yolundan servis edilir
   (`core/web/server.py`): oturum belirteci, Host denetimi ve SameSite=Strict çerezi ile korunur.
2. **Tüm kaynak yolları `/holo/` önekine taşındı** (`/vendor/…` → `/holo/vendor/…`, `/api/…` → `/holo/api/…`).
3. **CDN yedekleri kaldırıldı** (three.js ve MediaPipe için üç yer). Yerel dosya yüklenemezse sayfa hata verir, uzaktan kod çekmez.
4. **Sıkı CSP** (`connect-src 'self'`): kamera görüntüsü ve notlar bu sayfadan dışarıya gönderilemez.
5. **Notlar SIRIUS'tan gelir** (notların + Bağlantılar'a eklediğin klasörler), `holo.json` kullanılmaz.
6. **Jest olayları SIRIUS'a akar** (`/holo/api/state` → etkinlik günlüğü).
7. **`props/` (3B modeller) pakete dahil değil** (19 MB, isteğe bağlı). `holo/props/` içine herhangi bir `.glb` koyarsan sahnede görünür;
   özgün depodaki Smithsonian modelleri (CC0) için kaynak deponun `props/` klasörüne bak.
8. `sample-notes/`, `assets/banner.png` ve özgün `server.py` alınmadı.
