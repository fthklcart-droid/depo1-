"""Kısa şakalar. (Fikir: J.A.R.V.I.S 'joke'; harici paket gerekmez. Şakalar bu proje için yazıldı.)"""
import random

JOKES = [
    "Programcı markete gitmiş. Eşi: 'Bir ekmek al, yumurta varsa altı tane al.' Eve altı ekmekle dönmüş: 'Yumurta vardı.'",
    "Bir yazılımcıya neden doğum günü hediyesi almazsın? Çünkü her seferinde 'bu bir özellik, hata değil' diyor.",
    "Yedekleri aldım diyen insan, geri yüklemeyi hiç denememiş insandır.",
    "Çalışıyor, dokunma. Dokundun, çalışmıyor. Geri al.",
    "İki bit karşılaşmış. Biri demiş ki: 'Çok sıfırdan başladın.' Öbürü: 'Sen de bire bir konuşuyorsun.'",
    "Toplantının e-posta olabileceğini düşünen ben, e-postanın toplantı olabileceğini düşünen sen.",
    "Test geçti diye sevinme; belki de hiçbir şeyi test etmiyordur.",
    "Dünyada 10 tür insan vardır: ikilik sistemi bilenler ve bilmeyenler.",
]
TOOL = {"name": "saka", "description": "Kısa bir şaka söyler.", "parameters": {"type": "object", "properties": {}}}


def run(p, ctx):
    return random.choice(JOKES)
