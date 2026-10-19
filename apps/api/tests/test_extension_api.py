import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_extension_pairing_and_item_creation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register and login user on web
        email = f"ext_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        web_token = login.json()["access_token"]
        web_headers = {"Authorization": f"Bearer {web_token}"}

        # 1. Web app authorizes and pairs browser extension
        pair_res = await client.post("/api/v1/extension/pair", json={"client_name": "Chrome MV3"}, headers=web_headers)
        assert pair_res.status_code == 200
        ext_token = pair_res.json()["extension_token"]
        assert ext_token is not None
        ext_headers = {"Authorization": f"Bearer {ext_token}"}

        # 2. Extension checks auth status and supported hosts
        status_res = await client.get("/api/v1/extension/status", headers=ext_headers)
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "authenticated"
        assert status_data["email"] == email.lower()
        assert "shop.example" in status_data["supported_hosts"]

        # 3. Extension adds an item extracted from browser DOM
        add_res = await client.post("/api/v1/extension/items", json={
            "product_url": "https://shop.example/products/mechanical-keyboard?ref=twitter_ad",
            "title": "RGB Mechanical Keyboard",
            "image_url": "https://shop.example/img/keyboard.jpg",
            "price_minor": 899900,
            "currency": "INR",
            "target_price_minor": 750000,
            "notes": "Added from browser extension"
        }, headers=ext_headers)
        assert add_res.status_code == 201
        created_item = add_res.json()
        assert created_item["title"] == "RGB Mechanical Keyboard"
        assert created_item["current_price_minor"] == 899900
        assert "ref" not in created_item["canonical_url"]
        assert "extension" in created_item["tags"]

        # 4. Verify extension item is visible in user's PWA wishlist
        wishlist_res = await client.get("/api/v1/items", headers=web_headers)
        assert wishlist_res.status_code == 200
        assert any(it["id"] == created_item["id"] for it in wishlist_res.json()["items"])
