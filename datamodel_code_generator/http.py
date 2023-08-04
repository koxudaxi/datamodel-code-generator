from __future__ import annotations

import logging
import os
from typing import Optional, Sequence, Tuple

from datamodel_code_generator.http_vmanage_auth import vManageAuth

logger = logging.getLogger('vmanage-logger')
logging.basicConfig(level=logging.INFO)

try:
    import httpx
except ImportError:  # pragma: no cover
    raise Exception(
        'Please run $pip install datamodel-code-generator[http] to resolve URL Reference'
    )

USER = os.getenv('VMANAGE_USER')
PASSWORD = os.environ.get('VMANAGE_PASSWORD')
CLIENT = httpx.Client()

if USER and PASSWORD:
    CLIENT = httpx.Client(
        auth=vManageAuth(username=USER, password=PASSWORD), verify=False
    )


def get_body(
    url: str,
    headers: Optional[Sequence[Tuple[str, str]]] = None,
    ignore_tls: bool = False,
) -> str:
    logger.info(url)
    body = CLIENT.get(url, headers=headers, follow_redirects=True).text
    logger.debug(body)
    return body


def join_url(url: str, ref: str = '.') -> str:
    return str(httpx.URL(url).join(ref))
