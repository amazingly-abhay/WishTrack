import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.url_validator import validate_and_canonicalize_url
from app.core.exceptions import InvalidURLException

@pytest.mark.asyncio
async def test_security_headers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Verify Security Headers
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        headers = resp.headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "X-Request-ID" in headers
        assert "X-Process-Time" in headers

def test_ssrf_edge_cases():
    # Test localhost and link-local blocked
    with pytest.raises(InvalidURLException):
        validate_and_canonicalize_url("http://127.0.0.1:6379")

    with pytest.raises(InvalidURLException):
        validate_and_canonicalize_url("http://localhost:5432/db")

    with pytest.raises(InvalidURLException):
        validate_and_canonicalize_url("http://169.254.169.254/latest/meta-data")

    with pytest.raises(InvalidURLException):
        validate_and_canonicalize_url("ftp://shop.example/item")

    # Valid HTTPS public URL should pass
    raw, canon, host = validate_and_canonicalize_url("https://shop.example/item?utm_source=fb&sku=123")
    assert host == "shop.example"
    assert "utm_source" not in canon
    assert "sku=123" in canon
