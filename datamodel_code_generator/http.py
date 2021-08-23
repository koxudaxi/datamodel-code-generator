from typing import Optional, Sequence, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover
    raise Exception(
        'Please run $pip install datamodel-code-generator[http] to resolve URL Reference'
    )


def get_body(url: str, headers: Optional[Sequence[Tuple[str, str]]] = None) -> str:
    return httpx.get(url, headers=headers).text


def join_url(url: str, ref: str = '.') -> str:
    return str(httpx.URL(url).join(ref))
