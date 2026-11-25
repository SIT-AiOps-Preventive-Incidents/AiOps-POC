"""The public address people reach the app at (SSO_REDIRECT_BASE), for example https://host/some/folder.

A proxy in front may serve us under a folder, next to other apps on the same host name. What we need from that - the
cookie's path, whether it must be Secure, where single sign-on comes back - is taken from the configured address, never
from something a caller can send. A folder has one written form: /one/two/ - a slash at both ends, no empty, dot or
encoded part. Pure: no database, no network.
"""
from __future__ import annotations

import ipaddress
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*")
_MAX = 200
_DEFAULT_PORT = {"http": 80, "https": 443}

# who may tell us that the browser used https: this machine and the Docker networks our own Caddy runs in
TRUSTED = [ipaddress.ip_network(n.strip()) for n in
           os.environ.get("TRUSTED_PROXIES", "127.0.0.0/8,::1/128,172.16.0.0/12,192.168.0.0/16").split(",") if n.strip()]


def folder(path: str | None) -> str | None:
    """The one written form of a folder, or None when it is not a plain one."""
    if path is None or len(path) > _MAX:
        return None
    path = path.rstrip("/") + "/"
    if path == "/":
        return "/"
    if not path.startswith("/"):
        return None
    parts = path[1:-1].split("/")
    return path if all(_PART.fullmatch(p) for p in parts) else None


def _host(host: str | None, scheme: str) -> str:
    """Host and port in one form: lower case, without the scheme's own port."""
    h = (host or "").strip().lower()
    return h.removesuffix(f":{_DEFAULT_PORT[scheme]}")


@dataclass(frozen=True)
class PublicUrl:
    base: str       # https://host/some/folder - no slash at the end
    path: str       # /some/folder/
    host: str       # host, or host:port
    https: bool

    def join(self, tail: str) -> str:
        return self.base + "/" + tail.lstrip("/")

    def serves(self, host_header: str | None) -> bool:
        return bool(host_header) and _host(host_header, "https" if self.https else "http") == self.host


def parse(raw: str | None) -> PublicUrl | None:
    """The configured address, or None when it is empty or not a plain http(s) address."""
    raw = (raw or "").strip()
    try:
        u = urlsplit(raw)
        port = u.port
    except ValueError:
        return None
    path = folder(u.path)
    if u.scheme not in _DEFAULT_PORT or not u.hostname or u.username or u.password or u.query or u.fragment or not path:
        return None
    host = _host(u.hostname + (f":{port}" if port else ""), u.scheme)
    return PublicUrl(f"{u.scheme}://{host}{path}".rstrip("/"), path, host, u.scheme == "https")


def trusted_proxy(ip: str | None) -> bool:
    try:
        addr = ipaddress.ip_address(ip or "")
    except ValueError:
        return False
    return any(addr in n for n in TRUSTED)
