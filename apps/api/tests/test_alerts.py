import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import async_session_factory
from app.models.entities import WishlistItem
from app.adapters.mock import MockRetailerAdapter
from app.workers.price_checker import process_price_check
from app.notifications.rules import evaluate_and_create_alerts

@pytest.mark.asyncio
async def test_alerts_rules_and_deduplication():
    async with async_session_factory() as db:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = f"alerts_{uuid.uuid4().hex[:8]}@example.com"
            await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
            login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create item: initial price ₹6,000 (600000), target ₹5,000 (500000)
            item_res = await client.post("/api/v1/items", json={
                "product_url": "https://shop.example/products/camera?price=600000",
                "title": "Action Camera",
                "price_minor": 600000,
                "currency": "INR",
                "target_price_minor": 500000
            }, headers=headers)
            item_id = uuid.UUID(item_res.json()["id"])
            item = await db.get(WishlistItem, item_id)

            # Check 1: Price drops to ₹4,800 (reaches target & new low!)
            mock_adapter = MockRetailerAdapter(override_prices={"https://shop.example/products/camera?price=600000": 480000})
            eval_result = await process_price_check(item_id, db, adapter_override=mock_adapter)
            notifs = await evaluate_and_create_alerts(item, eval_result, db)
            
            # Should create 2 notifications: target reached + new 365d low
            assert len(notifs) == 2
            types = {n.type for n in notifs}
            assert "target_reached" in types
            assert "new_365d_low" in types

            # Check 2 (Duplicate check with exact same price ₹4,800): must be deduplicated
            eval_result_2 = await process_price_check(item_id, db, adapter_override=mock_adapter)
            notifs_dup = await evaluate_and_create_alerts(item, eval_result_2, db)
            # Both target_reached and new_low must be suppressed by dedupe_key!
            assert len(notifs_dup) == 0

            # Verify Inbox via API
            inbox_res = await client.get("/api/v1/notifications?unread_only=true", headers=headers)
            assert inbox_res.status_code == 200
            inbox_data = inbox_res.json()
            assert inbox_data["total"] == 2
            notif_id = inbox_data["items"][0]["id"]

            # Mark 1 notification as read
            read_res = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
            assert read_res.status_code == 200
            assert read_res.json()["read_at"] is not None

            # Mark all as read
            mark_all = await client.post("/api/v1/notifications/read-all", headers=headers)
            assert mark_all.status_code == 200
            assert mark_all.json()["updated_count"] == 1

            # Update Preferences: Disable price drop alerts & set min drop 15%
            pref_update = await client.patch("/api/v1/notifications/preferences", json={
                "price_drop_enabled": False,
                "minimum_drop_percent": 15.0
            }, headers=headers)
            assert pref_update.status_code == 200
            assert pref_update.json()["price_drop_enabled"] is False
            assert pref_update.json()["minimum_drop_percent"] == 15.0
