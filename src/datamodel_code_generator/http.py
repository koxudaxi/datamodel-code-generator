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


DEFAULT_HTTP_TIMEOUT = 30.0


def get_body(
    url: str,
    headers: Sequence[tuple[str, str]] | None = None,
    ignore_tls: bool = False,  # noqa: FBT001, FBT002
    query_parameters: Sequence[tuple[str, str]] | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
) -> str:
    """Fetch content from a URL with optional headers and query parameters."""
    httpx = _get_httpx()
    return httpx.get(
        url,
        headers=headers,
        verify=not ignore_tls,
        follow_redirects=True,
        params=query_parameters,  # pyright: ignore[reportArgumentType]
        timeout=timeout,
    ).text


def join_url(url: str, ref: str = ".") -> str:  # noqa: PLR0912
    """Join a base URL with a relative reference."""
    if url.startswith("file://"):
        from urllib.parse import urlparse  # noqa: PLC0415

        parsed = urlparse(url)

        if ref.startswith("file://"):
            return ref

        ref_path, *frag = ref.split("#", 1)

        # Fragment-only ref: keep the original path
        if not ref_path:
            joined = url.split("#", maxsplit=1)[0]
            if frag:
                joined += f"#{frag[0]}"
            return joined

        if ref_path.startswith("/"):
            joined_path = ref_path
        else:
            base_segments = parsed.path.lstrip("/").split("/")
            if base_segments and not base_segments[0]:
                base_segments = []
            if base_segments:
                base_segments = base_segments[:-1]

            min_depth = 1 if parsed.netloc else 0
            for segment in ref_path.split("/"):
                if segment in {"", "."}:
                    continue
                if segment == "..":
                    if len(base_segments) > min_depth:
                        base_segments.pop()
                    continue
                base_segments.append(segment)

            joined_path = "/" + "/".join(base_segments)
            if ref_path.endswith("/"):
                joined_path += "/"

        joined = f"file://{parsed.netloc}{joined_path}"
        if frag:
            joined += f"#{frag[0]}"
        return joined
    httpx = _get_httpx()
    return str(httpx.URL(url).join(ref))
