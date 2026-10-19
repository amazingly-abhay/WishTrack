import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from app.adapters.base import ProductSnapshot
from app.core.exceptions import WishTrackException

class JsonLdRetailerAdapter:
    """
    Generic permitted adapter for sites providing Schema.org Product / Offer JSON-LD or meta tags.
    """
    adapter_name = "json_ld_schema"
    supported_hosts = {"openstore.example", "teststore.in"}

    def __init__(self, http_client: httpx.AsyncClient = None):
        self.http_client = http_client

    async def fetch_product(self, url: str) -> ProductSnapshot:
        client = self.http_client or httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        try:
            response = await client.get(url, headers={
                "User-Agent": "WishTrack/1.0 (+https://wishtrack.example/bot)",
                "Accept": "text/html,application/xhtml+xml,application/json"
            })
            if response.status_code != 200:
                raise WishTrackException(
                    code="FETCH_FAILED",
                    message=f"Failed to fetch product page, HTTP {response.status_code}",
                    status_code=502
                )
            
            html = response.text
            return self.parse_html(url, html)
        finally:
            if not self.http_client:
                await client.aclose()

    def parse_html(self, url: str, html: str) -> ProductSnapshot:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Attempt JSON-LD Schema extraction
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string or "{}")
                # Handle @graph or direct object
                items = data.get("@graph", [data]) if isinstance(data, dict) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") in ("Product", "IndividualProduct"):
                        return self._extract_from_json_ld(url, item)
            except Exception:
                continue

        # 2. OpenGraph Fallback
        og_title = soup.find("meta", property="og:title")
        og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
        og_curr = soup.find("meta", property="product:price:currency") or soup.find("meta", property="og:price:currency")
        og_image = soup.find("meta", property="og:image")

        if og_title and og_price:
            title = og_title.get("content", "").strip()
            price_val = float(og_price.get("content", "0"))
            curr = og_curr.get("content", "INR").strip().upper() if og_curr else "INR"
            image_url = og_image.get("content", "").strip() if og_image else None
            price_minor = int(round(price_val * 100))

            return ProductSnapshot(
                canonical_url=url,
                title=title,
                image_url=image_url,
                price_minor=price_minor,
                currency=curr,
                availability="in_stock",
                source="adapter",
                confidence=0.85,
                adapter_name=self.adapter_name,
                adapter_version="1.0.0",
                raw_price_text=str(price_val)
            )

        raise WishTrackException(
            code="PRICE_NOT_FOUND",
            message="Could not extract reliable price from page markup.",
            status_code=422
        )

    def _extract_from_json_ld(self, url: str, item: dict) -> ProductSnapshot:
        title = item.get("name", "Product").strip()
        image = item.get("image")
        image_url = image[0] if isinstance(image, list) and image else (image if isinstance(image, str) else None)

        offers = item.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]

        price_raw = offers.get("price") or offers.get("lowPrice")
        currency = (offers.get("priceCurrency") or "INR").strip().upper()
        avail_str = offers.get("availability", "")
        availability = "out_of_stock" if "OutOfStock" in avail_str else "in_stock"

        if price_raw is None:
            raise WishTrackException(code="PRICE_NOT_FOUND", message="Offer price not found in JSON-LD", status_code=422)

        price_minor = int(round(float(str(price_raw).replace(",", "")) * 100))

        return ProductSnapshot(
            canonical_url=url,
            title=title,
            image_url=image_url,
            price_minor=price_minor,
            currency=currency,
            availability=availability,
            source="adapter",
            confidence=0.95,
            adapter_name=self.adapter_name,
            adapter_version="1.0.0",
            raw_price_text=str(price_raw)
        )
