from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.services import ozon_client, wb_client

logger = logging.getLogger(__name__)

Marketplace = Literal["ozon", "wildberries", "unknown"]


class MarketplaceBlockedError(RuntimeError):
    """Raised when marketplace blocks the request"""

    pass


@dataclass
class ProductInfo:
    marketplace: Marketplace
    title: str
    price_with_card: Decimal | None
    price_no_card: Decimal | None

    @property
    def price_for_compare(self) -> Decimal | None:
        return self.price_with_card or self.price_no_card


def detect_marketplace(url: str) -> Marketplace:
    url_lower = url.lower()

    if "ozon.ru" in url_lower:
        return "ozon"
    elif "wildberries.ru" in url_lower or "wb.ru" in url_lower:
        return "wildberries"
    else:
        return "unknown"


async def fetch_product_info(url: str, *, retries: int = 2) -> ProductInfo:
    marketplace = detect_marketplace(url)

    if marketplace == "unknown":
        raise ValueError(f"Unsupported marketplace URL: {url}")

    logger.info("Detected marketplace: %s for URL: %s", marketplace, url[:100])

    try:
        if marketplace == "ozon":
            ozon_info = await ozon_client.fetch_product_info(url, retries=retries)
            return ProductInfo(
                marketplace="ozon",
                title=ozon_info.title,
                price_with_card=ozon_info.price_with_card,
                price_no_card=ozon_info.price_no_card,
            )
        elif marketplace == "wildberries":
            wb_info = await wb_client.fetch_product_info(url)
            return ProductInfo(
                marketplace="wildberries",
                title=wb_info.title,
                price_with_card=wb_info.price_with_card,
                price_no_card=wb_info.price_no_card,
            )
        else:
            raise ValueError(f"Unsupported marketplace: {marketplace}")

    except (ozon_client.OzonBlockedError, wb_client.WBBlockedError) as e:
        logger.error("Marketplace blocked or failed: %s", e)
        raise MarketplaceBlockedError(str(e)) from e
    except Exception as e:
        logger.error("Unexpected error fetching product: %s", e)
        raise MarketplaceBlockedError(f"Unexpected error: {e}") from e


async def shutdown_browser() -> None:
    await ozon_client.shutdown_browser()
