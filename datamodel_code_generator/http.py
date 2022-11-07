from __future__ import annotations

from typing import Optional, Sequence, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover
    raise Exception(
        'Please run $pip install datamodel-code-generator[http] to resolve URL Reference'
    )


def get_body(
    url: str,
    headers: Optional[Sequence[Tuple[str, str]]] = None,
    ignore_tls: bool = False,
) -> str:
    return httpx.get(url, headers=headers, verify=not ignore_tls).text


def join_url(url: str, ref: str = '.') -> str:
    return str(httpx.URL(url).join(ref))
