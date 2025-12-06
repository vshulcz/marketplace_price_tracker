from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.wb_client import (
    WBBlockedError,
    WBProductInfo,
    _extract_product_id,
    _get_api_url,
    fetch_product_info,
)


def test_extract_product_id():
    assert (
        _extract_product_id("https://www.wildberries.ru/catalog/123456789/detail.aspx") == 123456789
    )
    assert _extract_product_id("https://wildberries.ru/catalog/987654321/detail.aspx") == 987654321
    assert _extract_product_id("https://www.wildberries.ru/catalog/12345/detail.aspx") == 12345
    assert _extract_product_id("https://example.com/product/123") is None
    assert _extract_product_id("invalid-url") is None


def test_get_api_url():
    url1 = _get_api_url(12345)
    assert "card.wb.ru/cards/v2/detail" in url1
    assert "nm=12345" in url1
    assert "appType=1" in url1

    url2 = _get_api_url(1234567)
    assert "card.wb.ru/cards/v2/detail" in url2
    assert "nm=1234567" in url2

    url3 = _get_api_url(234624452)
    assert "card.wb.ru/cards/v2/detail" in url3
    assert "nm=234624452" in url3


def test_product_info_dataclass():
    info = WBProductInfo(
        title="Test Product", price_with_card=Decimal("1000"), price_no_card=Decimal("1500")
    )
    assert info.title == "Test Product"
    assert info.price_with_card == Decimal("1000")
    assert info.price_no_card == Decimal("1500")
    assert info.price_for_compare == Decimal("1000")

    info2 = WBProductInfo(title="Test", price_with_card=Decimal("500"), price_no_card=None)
    assert info2.price_for_compare == Decimal("500")

    info3 = WBProductInfo(title="Test3", price_with_card=None, price_no_card=Decimal("700"))
    assert info3.price_for_compare == Decimal("700")


@pytest.mark.asyncio
async def test_fetch_product_info_invalid_url():
    with pytest.raises(ValueError, match="Not a Wildberries product URL"):
        await fetch_product_info("https://ozon.ru/product/123")

    with pytest.raises(ValueError, match="Not a Wildberries product URL"):
        await fetch_product_info("https://example.com/product")


@pytest.mark.asyncio
async def test_fetch_product_info_invalid_url_format():
    with pytest.raises(ValueError, match="Not a Wildberries product URL"):
        await fetch_product_info("https://www.wildberries.ru/catalog/detail.aspx")


@pytest.mark.asyncio
async def test_fetch_product_info_success():
    mock_response_data = {
        "data": {
            "products": [
                {
                    "name": "Смартфон Apple iPhone 15 Pro 256GB",
                    "sizes": [
                        {
                            "price": {
                                "basic": 14999000,
                                "product": 12999000,
                                "total": 12279000,
                            }
                        }
                    ],
                }
            ]
        }
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock()

    with patch("app.services.wb_client.aiohttp.ClientSession", return_value=mock_session):
        result = await fetch_product_info(
            "https://www.wildberries.ru/catalog/123456789/detail.aspx"
        )

        assert result.title == "Смартфон Apple iPhone 15 Pro 256GB"
        assert result.price_with_card == Decimal("122790.00")
        assert result.price_no_card == Decimal("129990.00")


@pytest.mark.asyncio
async def test_fetch_product_info_fallback_name():
    mock_response_data = {
        "data": {
            "products": [
                {
                    "name": "Product Name",
                    "sizes": [
                        {
                            "price": {
                                "product": 50000,
                            }
                        }
                    ],
                }
            ]
        }
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock()

    with patch("app.services.wb_client.aiohttp.ClientSession", return_value=mock_session):
        result = await fetch_product_info(
            "https://www.wildberries.ru/catalog/123456789/detail.aspx"
        )

        assert result.title == "Product Name"
        assert result.price_with_card is None
        assert result.price_no_card == Decimal("500.00")


@pytest.mark.asyncio
async def test_fetch_product_info_no_prices():
    mock_response_data = {
        "data": {
            "products": [
                {
                    "name": "Test Product",
                    "sizes": [],
                }
            ]
        }
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock()

    with patch("app.services.wb_client.aiohttp.ClientSession", return_value=mock_session):
        result = await fetch_product_info(
            "https://www.wildberries.ru/catalog/123456789/detail.aspx"
        )

        assert result.title == "Test Product"
        assert result.price_with_card is None
        assert result.price_no_card is None


@pytest.mark.asyncio
async def test_fetch_product_info_http_error():
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock()

    with patch("app.services.wb_client.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(WBBlockedError):
            await fetch_product_info("https://www.wildberries.ru/catalog/123456789/detail.aspx")


@pytest.mark.asyncio
async def test_fetch_product_info_network_error():
    import aiohttp

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))

    with patch("app.services.wb_client.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(WBBlockedError):
            await fetch_product_info("https://www.wildberries.ru/catalog/123456789/detail.aspx")


@pytest.mark.asyncio
async def test_fetch_product_info_invalid_json():
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock()

    with patch("app.services.wb_client.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(WBBlockedError):
            await fetch_product_info("https://www.wildberries.ru/catalog/123456789/detail.aspx")
