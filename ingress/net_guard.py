"""SSRF guard for server-side fetches of user/third-party supplied URLs.

`enrich()` fetches URLs found in inbound messages, and media downloads follow
URLs returned by Meta. Both reach out from inside our network, so an attacker
who controls a URL (or a redirect target) could otherwise pull from internal
services or the cloud metadata endpoint (169.254.169.254). This module rejects
non-http(s) schemes and any host that resolves to a private, loopback,
link-local, reserved, or otherwise non-public address.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _ip_is_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def is_safe_public_url(url: str) -> bool:
    """True only when `url` is http(s) and every resolved IP is public.

    Synchronous (does a DNS lookup) — call via ``asyncio.to_thread`` from
    async code so the event loop is not blocked.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    # A literal IP host is checked directly; a name is resolved and every
    # returned address must be public (defends against DNS rebinding to a
    # mix of public + private records).
    try:
        infos = socket.getaddrinfo(host, parsed.port or None, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    if not infos:
        return False
    return all(_ip_is_public(info[4][0]) for info in infos)
