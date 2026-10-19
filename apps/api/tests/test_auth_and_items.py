import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_auth_and_user_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
        email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"

        # 1. Register User A
        reg_a = await client.post("/api/v1/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "display_name": "User Alpha"
        })
        assert reg_a.status_code == 201
        user_a_data = reg_a.json()
        assert user_a_data["email"] == email_a.lower()

        # 2. Login User A
        login_a = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "Password123!"
        })
        assert login_a.status_code == 200
        tokens_a = login_a.json()
        token_a = tokens_a["access_token"]
        refresh_a = tokens_a["refresh_token"]

        # 3. Test /auth/me for User A
        me_a = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
        assert me_a.status_code == 200
        assert me_a.json()["display_name"] == "User Alpha"

        # 4. Refresh token
        ref = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a})
        assert ref.status_code == 200
        assert "access_token" in ref.json()

        # 5. Register & Login User B
        reg_b = await client.post("/api/v1/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "display_name": "User Beta"
        })
        assert reg_b.status_code == 201
        login_b = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "Password123!"
        })
        token_b = login_b.json()["access_token"]

        # 6. User A creates a Wishlist Item
        item_payload = {
            "product_url": "https://shop.example/products/headphones?utm_source=twitter&ref=123",
            "title": "Wireless Studio Headphones",
            "price_minor": 499900,
            "currency": "INR",
            "target_price_minor": 399900,
            "tags": ["audio", "electronics"],
            "notes": "Wait for festive sale"
        }
        create_res = await client.post(
            "/api/v1/items",
            json=item_payload,
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert create_res.status_code == 201
        item_a = create_res.json()
        item_a_id = item_a["id"]
        assert item_a["current_price_minor"] == 499900
        assert item_a["retailer_host"] == "shop.example"
        # Verify URL canonicalization removed tracking parameters
        assert "utm_source" not in item_a["canonical_url"]
        assert "ref" not in item_a["canonical_url"]

        # 7. User A lists items -> sees 1 item
        list_a = await client.get("/api/v1/items", headers={"Authorization": f"Bearer {token_a}"})
        assert list_a.status_code == 200
        assert list_a.json()["total"] == 1

        # 8. Cross-User Isolation: User B lists items -> sees 0 items
        list_b = await client.get("/api/v1/items", headers={"Authorization": f"Bearer {token_b}"})
        assert list_b.status_code == 200
        assert list_b.json()["total"] == 0

        # 9. Cross-User Isolation: User B attempts to access User A's item -> receives 404 (not 403, preventing disclosure)
        get_b = await client.get(f"/api/v1/items/{item_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert get_b.status_code == 404
        assert get_b.json()["error"]["code"] == "ITEM_NOT_FOUND"

        # 10. SSRF Protection: Attempt to preview private/localhost IP
        ssrf_test = await client.post(
            "/api/v1/items/preview",
            json={"product_url": "http://127.0.0.1:8000/secret"},
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert ssrf_test.status_code == 400
        assert ssrf_test.json()["error"]["code"] == "INVALID_URL"

@pytest.mark.asyncio
async def test_manual_observations_and_history_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"hist_{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create item with initial price 500000 (₹5000.00), target 450000 (₹4500.00)
        item_res = await client.post("/api/v1/items", json={
            "product_url": "https://shop.example/products/gadget",
            "title": "Smart Gadget",
            "price_minor": 500000,
            "currency": "INR",
            "target_price_minor": 450000
        }, headers=headers)
        assert item_res.status_code == 201
        item_id = item_res.json()["id"]

        # Add second manual observation: price drops to 440000 (₹4400.00) -> reaches target!
        obs_res = await client.post(f"/api/v1/items/{item_id}/observations", json={
            "price_minor": 440000,
            "currency": "INR",
            "raw_price_text": "4400.00"
        }, headers=headers)
        assert obs_res.status_code == 201
        assert obs_res.json()["price_minor"] == 440000

        # Query history summary
        summary_res = await client.get(f"/api/v1/items/{item_id}/history/summary", headers=headers)
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["current_price_minor"] == 440000
        assert summary["previous_price_minor"] == 500000
        assert summary["change_amount"] == -60000
        assert summary["change_percent"] == -12.0
        assert summary["lowest_365d_price_minor"] == 440000
        assert summary["target_reached"] is True
        assert summary["observation_count"] == 2

        # Query history list
        hist_res = await client.get(f"/api/v1/items/{item_id}/history?range=30d", headers=headers)
        assert hist_res.status_code == 200
        history_list = hist_res.json()
        assert len(history_list) == 2
