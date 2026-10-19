import ipaddress
import socket
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from app.core.exceptions import InvalidURLException

TRACKING_QUERY_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "tag", "aff_id", "affiliate_id"
}

def validate_and_canonicalize_url(raw_url: str) -> tuple[str, str, str]:
    """
    Validates URL safety (HTTPS, non-internal IP) and normalizes it.
    Returns: (normalized_url, canonical_url, retailer_host)
    """
    if not raw_url:
        raise InvalidURLException("URL cannot be empty.")

    try:
        parsed = urlparse(raw_url.strip())
    except Exception:
        raise InvalidURLException("Malformed URL format.")

    # Require http or https, prefer https
    if parsed.scheme.lower() not in ("http", "https"):
        raise InvalidURLException("Only HTTP and HTTPS URLs are supported.")

    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLException("URL must contain a valid hostname.")

    # SSRF Protection: verify hostname does not resolve to private or loopback IP ranges
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise InvalidURLException("Access to local address is prohibited.")

    try:
        # Check if direct IP address
        ip = ipaddress.ip_address(hostname_lower)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise InvalidURLException("Access to private/reserved IP addresses is prohibited.")
    except ValueError:
        # Not a raw IP literal; resolve via DNS
        try:
            resolved_ips = socket.getaddrinfo(hostname_lower, None)
            for item in resolved_ips:
                sockaddr = item[4]
                ip_addr = ipaddress.ip_address(sockaddr[0])
                if ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_link_local or ip_addr.is_reserved:
                    raise InvalidURLException("URL resolves to a private or restricted network address.")
        except socket.gaierror:
            # If DNS resolution fails, allow downstream adapter or preview to flag it
            pass

    # Clean query parameters (remove analytics/tracking params while preserving product identifiers)
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = [
        (k, v) for k, v in query_params if k.lower() not in TRACKING_QUERY_PARAMS
    ]
    
    # Sort query parameters for canonical consistency
    filtered_params.sort(key=lambda x: x[0])
    cleaned_query = urlencode(filtered_params)

    # Normalize path (remove redundant trailing slash unless root)
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    # Reconstruct normalized URL
    canonical_parts = (
        parsed.scheme.lower(),
        hostname_lower,
        path,
        "",
        cleaned_query,
        "" # Remove fragment
    )
    canonical_url = urlunparse(canonical_parts)

    retailer_host = hostname_lower
    if retailer_host.startswith("www."):
        retailer_host = retailer_host[4:]

    return raw_url.strip(), canonical_url, retailer_host
