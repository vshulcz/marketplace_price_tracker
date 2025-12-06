from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal

import aiohttp

logger = logging.getLogger(__name__)


class WBBlockedError(RuntimeError):
    """Raised when Wildberries blocks the request"""

    pass


@dataclass
class WBProductInfo:
    title: str
    price_with_card: Decimal | None
    price_no_card: Decimal | None

    @property
    def price_for_compare(self) -> Decimal | None:
        return self.price_with_card or self.price_no_card


def _extract_product_id(url: str) -> int | None:
    match = re.search(r"/catalog/(\d+)/", url)
    if match:
        return int(match.group(1))
    return None


def _get_api_url(product_id: int) -> str:
    return (
        f"https://card.wb.ru/cards/v2/detail"
        f"?appType=1&curr=rub&dest=-1257786&spp=30&nm={product_id}"
    )


async def fetch_product_info(url: str, *, timeout: int = 10) -> WBProductInfo:
    if not re.search(r"wildberries\.ru/catalog/\d+", url, re.IGNORECASE):
        logger.warning("Invalid Wildberries URL: %s", url[:100])
        raise ValueError("Not a Wildberries product URL")

    product_id = _extract_product_id(url)
    if not product_id:
        raise ValueError("Could not extract product ID from URL")

    logger.debug("Fetching WB product ID: %d", product_id)

    api_url = _get_api_url(product_id)
    logger.debug("API URL: %s", api_url)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.wildberries.ru/",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    logger.error("WB API returned status %d", response.status)
                    raise WBBlockedError(f"WB API returned status {response.status}")

                data = await response.json()

        products = data.get("data", {}).get("products", [])
        if not products:
            raise WBBlockedError("No product data in API response")

        product = products[0]

        title = product.get("name", "Wildberries item")
        logger.info("Found WB product: %s", title[:50])

        price_with_card = None
        price_no_card = None

        sizes = product.get("sizes", [])
        if sizes and "price" in sizes[0]:
            price_info = sizes[0]["price"]

            total_price = price_info.get("total")
            product_price = price_info.get("product")

            if total_price:
                price_with_card = Decimal(str(total_price)) / 100
            if product_price:
                price_no_card = Decimal(str(product_price)) / 100

        logger.info("WB prices - with card: %s, no card: %s", price_with_card, price_no_card)

        result = WBProductInfo(
            title=title,
            price_with_card=price_with_card,
            price_no_card=price_no_card,
        )

        logger.info(
            "WB product fetched | ID: %d | Title: %s | With card: %s | No card: %s",
            product_id,
            result.title[:50],
            result.price_with_card,
            result.price_no_card,
        )

        return result

    except WBBlockedError:
        raise
    except aiohttp.ClientError as e:
        logger.error("Failed to fetch WB product: %s", e)
        raise WBBlockedError(f"Network error: {e}") from e
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        logger.error("Failed to parse WB product data: %s", e)
        raise WBBlockedError(f"Failed to parse product data: {e}") from e
    except Exception as e:
        logger.error("Unexpected error fetching WB product: %s", e)
        raise WBBlockedError(f"Unexpected error: {e}") from e
