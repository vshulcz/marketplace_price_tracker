from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_OZON_RE = re.compile(r"^https?://(www\.)?ozon\.[^/]+/.+", re.IGNORECASE)
_WB_RE = re.compile(r"^https?://(www\.)?(wildberries|wb)\.[^/]+/catalog/\d+", re.IGNORECASE)


def is_marketplace_url(url: str) -> bool:
    url = url.strip()
    return bool(_OZON_RE.match(url)) or bool(_WB_RE.match(url))


def parse_price(text: str) -> Decimal | None:
    s = text.strip().replace(" ", "").replace(",", ".")
    try:
        value = Decimal(s)
    except (InvalidOperation, ValueError):
        return None

    if value <= 0:
        return None

    return value.quantize(Decimal("0.01"))
