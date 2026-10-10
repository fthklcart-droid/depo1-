"""Kamerayla el hareketleriyle notları kontrol eden HOLO panelini tarayıcıda açar (MIT, zubair-trabzada/holo-gestures)."""
import webbrowser

TOOL = {
    "name": "holo_ac",
    "description": "HOLO el hareketi panelini açar: kamerayla havada tutup fırlattığın notlar. Web arayüzü (--web) çalışıyorsa kullanılabilir. Görüntü bilgisayardan çıkmaz.",
    "parameters": {"type": "object", "properties": {}},
}


def run(p, ctx):
    if not ctx.holo_url:
        return "Panel yalnızca web arayüzü açıkken kullanılabilir: python main.py --web"
    webbrowser.open(ctx.holo_url)
    return "HOLO paneli açıldı. Kamera iznini ver ve elini kaldır; sıfırlamak için ✌ işareti yap."
