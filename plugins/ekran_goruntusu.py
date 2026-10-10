"""Ekran görüntüsünü dosyaya kaydeder (sabit klasör yolu yok). Geri alınabilir."""
import time

from core import store

TOOL = {
    "name": "ekran_goruntusu",
    "description": "Ekran görüntüsü alıp memory/outputs/ altına PNG olarak kaydeder. (Modelin ekrana bakması için look_at_screen kullan.)",
    "parameters": {"type": "object", "properties": {}},
}


def run(p, ctx):
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
    except ImportError:
        return "Ekran görüntüsü için: pip install pillow"
    except OSError as e:
        return f"Ekran alınamadı (ekran yok ya da izin verilmedi): {e}"
    d = store.DIR / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"ekran-{time.strftime('%Y%m%d-%H%M%S')}.png"
    img.save(path)
    ctx.undo.push("ekran görüntüsü", lambda: (path.unlink(missing_ok=True), "Dosya silindi.")[1])
    return f"Kaydedildi: {path}"
