import re
import json
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from app.core.url_validator import validate_and_canonicalize_url
from app.core.exceptions import InvalidURLException

async def extract_product_preview(raw_url: str) -> Dict[str, Any]:
    """
    Safely resolves redirects and auto-captures product details (title, image, price, currency)
    from standard HTML markup, JSON-LD, and OpenGraph tags without requiring manual entry.
    """
    normalized_url, canonical_url, retailer_host = validate_and_canonicalize_url(raw_url)

    title: Optional[str] = None
    image_url: Optional[str] = None
    price_minor: Optional[int] = None
    currency: str = "INR" if ("flipkart" in retailer_host or "amazon.in" in retailer_host or ".in" in retailer_host) else "USD"
    availability: str = "in_stock"

    # Fetch page with redirect resolution (e.g. dl.flipkart.com -> flipkart.com)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(normalized_url, headers=headers)
            if resp.status_code == 200:
                final_url = str(resp.url)
                # Re-validate destination URL for safety after redirects
                _, canonical_url, retailer_host = validate_and_canonicalize_url(final_url)

                soup = BeautifulSoup(resp.text, "html.parser")

                # 1. Try Schema.org JSON-LD
                scripts = soup.find_all("script", type="application/ld+json")
                for s in scripts:
                    try:
                        data = json.loads(s.string or "{}")
                        items = data.get("@graph", [data]) if isinstance(data, dict) else [data]
                        for item in items:
                            if isinstance(item, dict) and item.get("@type") in ("Product", "IndividualProduct"):
                                if not title and item.get("name"):
                                    title = str(item["name"]).strip()
                                
                                img = item.get("image")
                                if not image_url and img:
                                    image_url = img[0] if isinstance(img, list) and img else (img if isinstance(img, str) else None)
                                
                                offers = item.get("offers", {})
                                if isinstance(offers, list) and offers:
                                    offers = offers[0]
                                if isinstance(offers, dict):
                                    p_raw = offers.get("price") or offers.get("lowPrice")
                                    if p_raw and price_minor is None:
                                        p_clean = re.sub(r'[^\d.]', '', str(p_raw))
                                        if p_clean:
                                            price_minor = int(round(float(p_clean) * 100))
                                    if offers.get("priceCurrency"):
                                        currency = str(offers["priceCurrency"]).strip().upper()
                    except Exception:
                        continue

                # 2. Try OpenGraph / Twitter Cards
                if not title:
                    og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
                    if og_title and og_title.get("content"):
                        title = og_title["content"].strip()

                if not image_url:
                    og_img = (
                        soup.find("meta", property="og:image") or 
                        soup.find("meta", attrs={"name": "twitter:image"}) or
                        soup.find("link", rel="image_src")
                    )
                    if og_img:
                        image_url = og_img.get("content") or og_img.get("href")

                if price_minor is None:
                    og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
                    og_curr = soup.find("meta", property="product:price:currency") or soup.find("meta", property="og:price:currency")
                    if og_price and og_price.get("content"):
                        p_clean = re.sub(r'[^\d.]', '', og_price["content"])
                        if p_clean:
                            price_minor = int(round(float(p_clean) * 100))
                    if og_curr and og_curr.get("content"):
                        currency = og_curr["content"].strip().upper()

                # 3. Document Title fallback if still missing
                if not title and soup.title and soup.title.string:
                    clean_title = re.sub(r'\s*\|\s*.*$', '', soup.title.string) # strip suffix like '| Flipkart'
                    clean_title = re.sub(r'\s*:\s*Buy\s.*$', '', clean_title)
                    title = clean_title.strip()
    except Exception:
        # Graceful fallback: return canonical structure if network request is unreachable
        pass

    # If title still empty, fallback to clean path slug
    if not title:
        parts = normalized_url.split("?")[0].strip("/").split("/")
        last_part = parts[-1] if parts else "product"
        title = last_part.replace("-", " ").title()

    return {
        "product_url": normalized_url,
        "canonical_url": canonical_url,
        "retailer_host": retailer_host,
        "title": title,
        "image_url": image_url,
        "price_minor": price_minor,
        "currency": currency,
        "availability": availability
    }
