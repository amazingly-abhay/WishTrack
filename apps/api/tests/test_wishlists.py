import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_wishlists_crud_and_item_assignment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"wl_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Listing wishlists automatically provisions default "My Wishlist"
        wl_list = await client.get("/api/v1/wishlists", headers=headers)
        assert wl_list.status_code == 200
        wishlists = wl_list.json()
        assert len(wishlists) == 1
        default_wl = wishlists[0]
        assert default_wl["name"] == "My Wishlist"
        assert default_wl["is_default"] is True
        assert default_wl["item_count"] == 0

        # 2. Create custom wishlist
        new_wl_res = await client.post("/api/v1/wishlists", json={
            "name": "Audio & Electronics",
            "description": "Headphones and TVs"
        }, headers=headers)
        assert new_wl_res.status_code == 201
        custom_wl = new_wl_res.json()
        assert custom_wl["name"] == "Audio & Electronics"
        assert custom_wl["is_default"] is False

        # 3. Add item directly into custom wishlist
        item_res = await client.post("/api/v1/items", json={
            "product_url": "https://shop.example/headphones-pro",
            "title": "Audiophile Headphones",
            "price_minor": 1500000,
            "currency": "INR",
            "wishlist_id": custom_wl["id"],
            "tags": ["audio", "gadgets"]
        }, headers=headers)
        assert item_res.status_code == 201
        item_id = item_res.json()["id"]
        assert item_res.json()["wishlist_id"] == custom_wl["id"]

        # 4. Verify item counts in wishlist listing
        wl_list_after = await client.get("/api/v1/wishlists", headers=headers)
        wl_map = {w["id"]: w for w in wl_list_after.json()}
        assert wl_map[custom_wl["id"]]["item_count"] == 1
        assert wl_map[default_wl["id"]]["item_count"] == 0

        # 5. Filter items by wishlist_id
        items_filtered = await client.get(f"/api/v1/items?wishlist_id={custom_wl['id']}", headers=headers)
        assert items_filtered.status_code == 200
        assert items_filtered.json()["total"] == 1

        items_default = await client.get(f"/api/v1/items?wishlist_id={default_wl['id']}", headers=headers)
        assert items_default.status_code == 200
        assert items_default.json()["total"] == 0

        # 6. Delete item (soft delete)
        del_item = await client.delete(f"/api/v1/items/{item_id}?archive=false", headers=headers)
        assert del_item.status_code == 200

        # Check item count decreased
        wl_list_post_del = await client.get("/api/v1/wishlists", headers=headers)
        wl_map_post = {w["id"]: w for w in wl_list_post_del.json()}
        assert wl_map_post[custom_wl["id"]]["item_count"] == 0

        # 7. Cannot delete default wishlist
        del_default = await client.delete(f"/api/v1/wishlists/{default_wl['id']}", headers=headers)
        assert del_default.status_code == 400

        # 8. Delete custom wishlist
        del_custom = await client.delete(f"/api/v1/wishlists/{custom_wl['id']}", headers=headers)
        assert del_custom.status_code == 200

        final_list = await client.get("/api/v1/wishlists", headers=headers)
        assert len(final_list.json()) == 1
