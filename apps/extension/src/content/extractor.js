// WishTrack Content Script: Extracts product metadata from current webpage
(() => {
  function extractProductMetadata() {
    const url = window.location.href;
    const hostname = window.location.hostname.replace(/^www\./, '');

    // Canonical URL
    const canonicalEl = document.querySelector('link[rel="canonical"]');
    const canonicalUrl = canonicalEl ? canonicalEl.href : url;

    // 1. Check Schema.org JSON-LD
    let jsonLdData = null;
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const s of scripts) {
      try {
        const parsed = JSON.parse(s.textContent || '{}');
        const items = parsed['@graph'] || [parsed];
        for (const item of items) {
          if (item['@type'] === 'Product' || item['@type'] === 'IndividualProduct') {
            jsonLdData = item;
            break;
          }
        }
        if (jsonLdData) break;
      } catch (e) {
        // continue
      }
    }

    if (jsonLdData) {
      const offers = Array.isArray(jsonLdData.offers) ? jsonLdData.offers[0] : (jsonLdData.offers || {});
      const priceRaw = offers.price || offers.lowPrice;
      const currency = offers.priceCurrency || 'INR';
      const image = Array.isArray(jsonLdData.image) ? jsonLdData.image[0] : jsonLdData.image;

      return {
        product_url: url,
        canonical_url: canonicalUrl,
        retailer_host: hostname,
        title: jsonLdData.name || document.title,
        image_url: typeof image === 'string' ? image : undefined,
        price_minor: priceRaw ? Math.round(parseFloat(priceRaw.toString().replace(/,/g, '')) * 100) : undefined,
        currency: currency,
        source: 'extension'
      };
    }

    // 2. OpenGraph / Meta Tag Fallback
    const ogTitle = document.querySelector('meta[property="og:title"]')?.content;
    const ogPrice = document.querySelector('meta[property="product:price:amount"]')?.content ||
                    document.querySelector('meta[property="og:price:amount"]')?.content;
    const ogCurr = document.querySelector('meta[property="product:price:currency"]')?.content || 'INR';
    const ogImage = document.querySelector('meta[property="og:image"]')?.content;

    // 3. Document Title / Basic DOM Fallback
    const title = ogTitle || document.title || 'Untitled Product';
    const priceMinor = ogPrice ? Math.round(parseFloat(ogPrice) * 100) : undefined;

    return {
      product_url: url,
      canonical_url: canonicalUrl,
      retailer_host: hostname,
      title: title.trim(),
      image_url: ogImage || undefined,
      price_minor: priceMinor,
      currency: ogCurr,
      source: 'extension'
    };
  }

  // Listen for message from Extension Popup
  chrome.runtime?.onMessage?.addListener((request, sender, sendResponse) => {
    if (request.action === 'EXTRACT_METADATA') {
      const metadata = extractProductMetadata();
      sendResponse({ status: 'ok', data: metadata });
    }
    return true;
  });
})();
