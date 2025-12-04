"""HTTP utilities for fetching remote schema files.

Provides functions to fetch schema content from URLs and join URL references.
HTTP(S) URLs require the 'http' extra: `pip install 'datamodel-code-generator[http]'`.
file:// URLs are handled without additional dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


def _get_httpx() -> Any:
    """Lazily import httpx, raising a helpful error if not installed."""
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        msg = "Please run `$pip install 'datamodel-code-generator[http]`' to resolve HTTP(S) URL references"
        raise Exception(msg) from exc  # noqa: TRY002
    return httpx


def get_body(
    url: str,
    headers: Sequence[tuple[str, str]] | None = None,
    ignore_tls: bool = False,  # noqa: FBT001, FBT002
    query_parameters: Sequence[tuple[str, str]] | None = None,
) -> str:
    """Fetch content from a URL with optional headers and query parameters."""
    httpx = _get_httpx()
    return httpx.get(
        url,
        headers=headers,
        verify=not ignore_tls,
        follow_redirects=True,
        params=query_parameters,  # pyright: ignore[reportArgumentType]
        # TODO: Improve params type
    ).text


def join_url(url: str, ref: str = ".") -> str:
    """Join a base URL with a relative reference."""
    if url.startswith("file://"):
        from urllib.parse import urljoin  # noqa: PLC0415

        return urljoin(url, ref)
    httpx = _get_httpx()
    return str(httpx.URL(url).join(ref))
