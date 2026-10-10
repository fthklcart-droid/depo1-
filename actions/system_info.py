"""CPU / RAM / disk / battery / OS telemetry (psutil optional)."""
import os
import platform
import shutil

TOOL = {
    "name": "system_info",
    "description": "Report this computer's OS, CPU load, RAM, disk space, battery and top processes.",
    "parameters": {"type": "object", "properties": {}, },
}


def run(params, ctx):
    lines = [f"OS: {platform.platform()}", f"Python: {platform.python_version()}", f"CPU cores: {os.cpu_count()}"]
    d = shutil.disk_usage(os.path.expanduser("~"))
    lines.append(f"Disk: {d.free / 1e9:.1f} GB free of {d.total / 1e9:.1f} GB")
    try:
        import psutil
        lines.append(f"CPU: {psutil.cpu_percent(interval=0.3)}%")
        m = psutil.virtual_memory()
        lines.append(f"RAM: {m.used / 1e9:.1f}/{m.total / 1e9:.1f} GB ({m.percent}%)")
        b = psutil.sensors_battery()
        if b:
            lines.append(f"Battery: {b.percent:.0f}%{' (charging)' if b.power_plugged else ''}")
        top = sorted(psutil.process_iter(["name", "memory_percent"]), key=lambda p: -(p.info["memory_percent"] or 0))[:5]
        lines.append("Top by RAM: " + ", ".join(f"{p.info['name']} {p.info['memory_percent']:.1f}%" for p in top))
    except ImportError:
        try:
            lines.append("Load avg: " + ", ".join(f"{x:.2f}" for x in os.getloadavg()))
        except (AttributeError, OSError):
            pass
        lines.append("(install psutil for RAM/battery/process details)")
    return "\n".join(lines)
