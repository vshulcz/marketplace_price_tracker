from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.marketplace_client import (
    MarketplaceBlockedError,
    ProductInfo,
    detect_marketplace,
    fetch_product_info,
)


def test_detect_marketplace_ozon():
    assert detect_marketplace("https://www.ozon.ru/product/123") == "ozon"
    assert detect_marketplace("https://ozon.ru/product/123") == "ozon"
    assert detect_marketplace("http://www.ozon.ru/item/456") == "ozon"
    assert detect_marketplace("HTTPS://OZON.RU/PRODUCT/123") == "ozon"


def test_detect_marketplace_wildberries():
    assert detect_marketplace("https://www.wildberries.ru/catalog/123/detail.aspx") == "wildberries"
    assert detect_marketplace("https://wildberries.ru/catalog/123/detail.aspx") == "wildberries"
    assert detect_marketplace("http://wb.ru/product/123") == "wildberries"
    assert detect_marketplace("HTTPS://WILDBERRIES.RU/CATALOG/123") == "wildberries"


def test_detect_marketplace_unknown():
    assert detect_marketplace("https://amazon.com/product/123") == "unknown"
    assert detect_marketplace("https://yandex.ru/market/123") == "unknown"
    assert detect_marketplace("https://example.com") == "unknown"


def test_product_info_price_for_compare():
    info1 = ProductInfo(
        marketplace="ozon",
        title="Test",
        price_with_card=Decimal("100"),
        price_no_card=Decimal("150"),
    )
    assert info1.price_for_compare == Decimal("100")

    info2 = ProductInfo(
        marketplace="ozon", title="Test", price_with_card=None, price_no_card=Decimal("150")
    )
    assert info2.price_for_compare == Decimal("150")

    info3 = ProductInfo(marketplace="ozon", title="Test", price_with_card=None, price_no_card=None)
    assert info3.price_for_compare is None


@pytest.mark.asyncio
async def test_fetch_product_info_unsupported_marketplace():
    with pytest.raises(ValueError, match="Unsupported marketplace URL"):
        await fetch_product_info("https://amazon.com/product/123")


@pytest.mark.asyncio
async def test_fetch_product_info_ozon():
    from app.services.ozon_client import OzonProductInfo as OzonProductInfo

    mock_ozon_info = OzonProductInfo(
        title="iPhone", price_with_card=Decimal("100"), price_no_card=Decimal("150")
    )

    with patch("app.services.ozon_client.fetch_product_info", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_ozon_info

        result = await fetch_product_info("https://www.ozon.ru/product/123", retries=2)

        assert result.marketplace == "ozon"
        assert result.title == "iPhone"
        assert result.price_with_card == Decimal("100")
        assert result.price_no_card == Decimal("150")


@pytest.mark.asyncio
async def test_fetch_product_info_ozon_only_no_card_price():
    from app.services.ozon_client import OzonProductInfo as OzonProductInfo

    mock_ozon_info = OzonProductInfo(
        title="iPhone", price_with_card=None, price_no_card=Decimal("150")
    )

    with patch("app.services.ozon_client.fetch_product_info", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_ozon_info

        result = await fetch_product_info("https://www.ozon.ru/product/123")

        assert result.marketplace == "ozon"
        assert result.price_with_card is None
        assert result.price_no_card == Decimal("150")


@pytest.mark.asyncio
async def test_fetch_product_info_wildberries():
    from app.services.wb_client import WBProductInfo

    mock_wb_info = WBProductInfo(
        title="Samsung Phone", price_with_card=Decimal("50000"), price_no_card=Decimal("60000")
    )

    with patch("app.services.wb_client.fetch_product_info", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_wb_info

        result = await fetch_product_info("https://www.wildberries.ru/catalog/123456/detail.aspx")

        assert result.marketplace == "wildberries"
        assert result.title == "Samsung Phone"
        assert result.price_with_card == Decimal("50000")
        assert result.price_no_card == Decimal("60000")


@pytest.mark.asyncio
async def test_fetch_product_info_ozon_blocked():
    from app.services.ozon_client import OzonBlockedError

    with patch("app.services.ozon_client.fetch_product_info", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = OzonBlockedError("Blocked")

        with pytest.raises(MarketplaceBlockedError):
            await fetch_product_info("https://www.ozon.ru/product/123")


@pytest.mark.asyncio
async def test_fetch_product_info_wb_blocked():
    from app.services.wb_client import WBBlockedError

    with patch("app.services.wb_client.fetch_product_info", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = WBBlockedError("Blocked")

        with pytest.raises(MarketplaceBlockedError):
            await fetch_product_info("https://www.wildberries.ru/catalog/123/detail.aspx")


@pytest.mark.asyncio
async def test_shutdown_browser():
    from app.services import marketplace_client

    with patch(
        "app.services.ozon_client.shutdown_browser", new_callable=AsyncMock
    ) as mock_shutdown:
        await marketplace_client.shutdown_browser()
        assert mock_shutdown.called
