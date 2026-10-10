"""Bilgisayarı kapat / yeniden başlat / uyut / kilitle. HER ZAMAN insana sorar. (Fikir: J.A.R.V.I.S 'shutdown'; onaysız poweroff yerine.)"""
import platform
import subprocess

CMDS = {
    "Windows": {"kapat": ["shutdown", "/s", "/t", "30"], "yeniden_baslat": ["shutdown", "/r", "/t", "30"],
                "uyut": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], "kilitle": ["rundll32.exe", "user32.dll,LockWorkStation"], "iptal": ["shutdown", "/a"]},
    "Darwin": {"kapat": ["osascript", "-e", 'tell app "System Events" to shut down'], "yeniden_baslat": ["osascript", "-e", 'tell app "System Events" to restart'],
               "uyut": ["pmset", "sleepnow"], "kilitle": ["pmset", "displaysleepnow"], "iptal": None},
    "Linux": {"kapat": ["systemctl", "poweroff"], "yeniden_baslat": ["systemctl", "reboot"], "uyut": ["systemctl", "suspend"],
              "kilitle": ["loginctl", "lock-session"], "iptal": ["shutdown", "-c"]},
}
TOOL = {
    "name": "guc_islemi",
    "description": "Bilgisayarı kapatır, yeniden başlatır, uyutur ya da kilitler. Kullanıcıya her seferinde sorar; Windows'ta 30 sn gecikmeli, 'iptal' ile durdurulur.",
    "parameters": {"type": "object", "properties": {"islem": {"type": "string", "enum": ["kapat", "yeniden_baslat", "uyut", "kilitle", "iptal"]}}, "required": ["islem"]},
}


def command(islem: str, system: str):
    return (CMDS.get(system) or {}).get(islem)


def run(p, ctx):
    islem, system = p["islem"], platform.system()
    cmd = command(islem, system)
    if cmd is None:
        return "Bu işlem bu sistemde desteklenmiyor."
    if islem != "iptal" and not ctx.confirm(f"Bilgisayar için '{islem.replace('_', ' ')}' işlemi yapılsın mı?\n(Kaydedilmemiş işlerin kaybolabilir.)"):
        return "Kullanıcı onaylamadı, hiçbir şey yapılmadı."
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return f"{islem.replace('_', ' ')} komutu gönderildi." if r.returncode == 0 else f"Komut başarısız: {(r.stderr or r.stdout).strip()[:150]}"
