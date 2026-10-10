"""Pure signal maths for the HUD: loudness and mouth shapes. No device, no UI, no network."""
from __future__ import annotations

LEVEL_FLOOR = 60.0     # RMS below this is room silence
LEVEL_FULL = 2600.0    # RMS at/above this is a full-height waveform
VIS_WIN = 1024         # ~43 ms analysis window at 24 kHz
VIS_HOP = 480          # 20 ms -> 50 shapes a second


def pcm_level(samples) -> float:
    """int16 PCM block -> 0..1 loudness. Never raises."""
    try:
        import numpy as np
        x = np.asarray(samples, dtype=np.float32)
        if x.size == 0:
            return 0.0
        rms = float(np.sqrt(np.mean(x * x)))
    except Exception:  # noqa: BLE001
        return 0.0
    return 0.0 if rms <= LEVEL_FLOOR else min(1.0, (rms - LEVEL_FLOOR) / (LEVEL_FULL - LEVEL_FLOOR))


def pcm_visemes(samples, sr: int = 24000) -> list[tuple[float, float, float]]:
    """Block -> [(level, openness, width)] every 20 ms, from formant bands. [] on anything odd."""
    try:
        import numpy as np
        x = np.asarray(samples, dtype=np.float32)
        if x.size < VIS_WIN:
            return []
        win = np.hanning(VIS_WIN).astype(np.float32)
        f = np.fft.rfftfreq(VIS_WIN, 1.0 / sr)
        band = lambda lo, hi: (f >= lo) & (f < hi)  # noqa: E731
        f1l, f1h, f2b, f2f, hs = band(150, 450), band(450, 1100), band(600, 1300), band(1700, 3200), band(3800, 8000)
        out = []
        for start in range(0, x.size, VIS_HOP):  # whole block, not only where a full window fits
            level = pcm_level(x[start:start + VIS_HOP])
            seg = x[start:start + VIS_WIN]
            if level <= 0.0:
                out.append((0.0, 0.0, 0.0))
                continue
            if seg.size < VIS_WIN:
                seg = np.concatenate([seg, np.zeros(VIS_WIN - seg.size, dtype=np.float32)])
            mag = np.abs(np.fft.rfft((seg - seg.mean()) * win))
            a, b, c, d, h = (float(mag[m].sum()) for m in (f1l, f1h, f2b, f2f, hs))
            openness = b / (a + b + 1e-6)
            width = (d - c) / (d + c + 1e-6) * (1.0 - openness) ** 0.8   # a wide jaw cannot purse
            openness *= 1.0 - 0.65 * min(1.0, h / (a + b + c + d + h + 1e-6) * 2.5)  # fricatives: near-closed
            out.append((level, min(1.0, max(0.0, openness)), min(1.0, max(-1.0, width))))
        return out
    except Exception:  # noqa: BLE001
        return []
