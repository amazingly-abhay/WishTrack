import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.entities import WishlistItem
from app.adapters.mock import MockRetailerAdapter
from app.adapters.json_ld import JsonLdRetailerAdapter
from app.workers.price_checker import process_price_check
from app.workers.scheduler import get_due_items_for_check

@pytest.mark.asyncio
async def test_mock_and_json_ld_adapters():
    # 1. Test MockRetailerAdapter
    mock_adapter = MockRetailerAdapter(override_prices={"https://shop.example/headphones": 450000})
    snapshot = await mock_adapter.fetch_product("https://shop.example/headphones")
    assert snapshot.price_minor == 450000
    assert snapshot.currency == "USD"
    assert snapshot.title == "Mock Headphones"
    assert snapshot.confidence == 1.0

    # 2. Test JsonLdRetailerAdapter with Schema.org fixture
    json_ld_fixture = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Noise Cancelling Headphones</title>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org/",
          "@type": "Product",
          "name": "Noise Cancelling Headphones",
          "image": "https://teststore.in/img.jpg",
          "offers": {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": "14,999.00",
            "availability": "https://schema.org/InStock"
          }
        }
        </script>
      </head>
      <body></body>
    </html>
    """
    json_ld_adapter = JsonLdRetailerAdapter()
    snapshot_json_ld = json_ld_adapter.parse_html("https://teststore.in/headphones", json_ld_fixture)
    assert snapshot_json_ld.title == "Noise Cancelling Headphones"
    assert snapshot_json_ld.price_minor == 1499900 # ₹14,999.00
    assert snapshot_json_ld.currency == "INR"
    assert snapshot_json_ld.availability == "in_stock"
    assert snapshot_json_ld.confidence == 0.95

@pytest.mark.asyncio
async def test_price_checker_worker_and_summary_calculations():
    async with async_session_factory() as db:
        # Register user and item via API
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = f"engine_{uuid.uuid4().hex[:8]}@example.com"
            await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
            login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create item with initial observation: ₹10,000.00 (1000000 paise), target ₹8,500.00
            item_res = await client.post("/api/v1/items", json={
                "product_url": "https://shop.example/products/watch?price=1000000",
                "title": "Smart Watch",
                "price_minor": 1000000,
                "currency": "INR",
                "target_price_minor": 850000
            }, headers=headers)
            assert item_res.status_code == 201
            item_id = uuid.UUID(item_res.json()["id"])

            # Execute background price worker check #1: price drops to ₹8,000.00 (800000 paise)
            mock_adapter = MockRetailerAdapter(override_prices={"https://shop.example/products/watch?price=1000000": 800000})
            eval_result = await process_price_check(item_id, db, adapter_override=mock_adapter)
            assert eval_result["status"] == "success"
            assert eval_result["is_price_drop"] is True
            assert eval_result["drop_amount"] == 200000 # 10000 - 8000 = 2000 INR
            assert eval_result["drop_percent"] == 20.0 # 20% drop
            assert eval_result["is_new_365d_low"] is True
            assert eval_result["target_reached"] is True

            # Verify POST /items/{id}/refresh returns 202 Accepted
            refresh_res = await client.post(f"/api/v1/items/{item_id}/refresh", headers=headers)
            assert refresh_res.status_code == 202
            assert refresh_res.json()["status"] == "accepted"

            # Check scheduler finds due items
            async with async_session_factory() as check_db:
                due_items = await get_due_items_for_check(check_db, limit=200)
                assert any(it.id == item_id for it in due_items)
