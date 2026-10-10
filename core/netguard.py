"""Refuse URLs that point at this machine or the local network (a prompt-injected model must not probe them)."""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse


def check_url(url: str) -> str | None:
    """Returns an error message, or None if the URL is a public http(s) address."""
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return "Geçersiz adres."
    if u.scheme not in ("http", "https") or not u.hostname:
        return "Yalnızca http(s) adresleri açılır."
    host = u.hostname
    try:
        infos = socket.getaddrinfo(host, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except OSError:
        return None   # cannot resolve here; the request itself will fail with a clear error
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return "Yerel ağ ve bu bilgisayar adreslerine erişim kapalı."
    return None
