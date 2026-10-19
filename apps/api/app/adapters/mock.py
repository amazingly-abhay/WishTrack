import re
from urllib.parse import urlparse
from app.adapters.base import ProductSnapshot
from app.core.exceptions import WishTrackException

class MockRetailerAdapter:
    adapter_name = "mock_retailer"
    supported_hosts = {"shop.example", "mock.example", "example.com"}

    def __init__(self, override_prices: dict[str, int] = None):
        self.override_prices = override_prices or {}

    async def fetch_product(self, url: str) -> ProductSnapshot:
        parsed = urlparse(url)
        host = parsed.hostname.lower() if parsed.hostname else ""
        if host.startswith("www."):
            host = host[4:]

        if host not in self.supported_hosts:
            raise WishTrackException(
                code="UNSUPPORTED_HOST",
                message=f"Mock adapter does not support host: {host}",
                status_code=422
            )

        # Check explicit price override or extract price pattern from URL/path
        if url in self.override_prices:
            price_minor = self.override_prices[url]
        else:
            match = re.search(r'price=(\d+)', url)
            if match:
                price_minor = int(match.group(1))
            else:
                price_minor = 399900 # default: ₹3,999.00

        # Title heuristic
        path_slug = parsed.path.strip("/").split("/")[-1] or "example-product"
        title = path_slug.replace("-", " ").title()

        return ProductSnapshot(
            canonical_url=url,
            title=f"Mock {title}",
            image_url=f"https://{host}/images/{path_slug}.jpg",
            price_minor=price_minor,
            currency="INR" if "in" in host else "USD",
            availability="in_stock",
            source="adapter",
            confidence=1.0,
            adapter_name=self.adapter_name,
            adapter_version="1.0.0",
            raw_price_text=f"{price_minor / 100:.2f}"
        )
