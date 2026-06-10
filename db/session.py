import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings


def _ssl_context(verify: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify:
        # sslmode=require → encrypt, but don't verify the cert chain. Managed
        # Postgres poolers (Supabase :6543, some Neon/RDS) present a chain the
        # system CA bundle won't validate; require-mode is the standard choice.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _normalize_driver(url: str) -> str:
    """Accept standard Postgres URLs (postgresql:// or postgres://) and route
    them through the asyncpg driver the app uses."""
    if url.startswith(("postgresql+asyncpg://", "sqlite")):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    return url


def _clean_url(url: str) -> tuple[str, dict]:
    """Normalize driver + strip sslmode (asyncpg takes ssl via connect_args).

    SSL defaults ON for remote hosts (e.g. Supabase/Neon require it) and OFF for
    localhost, unless an explicit sslmode is given. statement_cache_size=0 keeps
    us compatible with transaction-pooled Postgres (pgBouncer, Supabase :6543).
    """
    url = _normalize_driver(url)
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    ssl_mode = (params.pop("sslmode", [None])[0] or "").lower()
    clean = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
    host = (parsed.hostname or "").lower()
    is_local = host in ("localhost", "127.0.0.1", "::1", "")
    connect_args: dict = {"statement_cache_size": 0}
    if ssl_mode in ("verify-ca", "verify-full"):
        connect_args["ssl"] = _ssl_context(verify=True)
    elif ssl_mode == "disable":
        pass  # no SSL
    elif ssl_mode == "require" or not is_local:
        connect_args["ssl"] = _ssl_context(verify=False)  # encrypt, don't verify
    # else: local, no sslmode → plain connection
    return clean, connect_args


_raw_url = settings.database_url or "postgresql+asyncpg://localhost/donna"

if _raw_url.startswith("sqlite"):
    # Offline/local dev (e.g. sqlite+aiosqlite:///./donna.db): no Postgres,
    # no Docker. Skip the asyncpg-specific connect_args and pg pool sizing.
    _engine = create_async_engine(_raw_url)
else:
    _url, _connect_args = _clean_url(_raw_url)
    _engine = create_async_engine(
        _url, pool_pre_ping=True, pool_size=5, max_overflow=10,
        connect_args=_connect_args,
    )

async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
