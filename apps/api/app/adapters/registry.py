from typing import Dict, Optional
from app.adapters.base import RetailerAdapter
from app.adapters.mock import MockRetailerAdapter
from app.adapters.json_ld import JsonLdRetailerAdapter

class AdapterRegistry:
    def __init__(self):
        self._adapters: list[RetailerAdapter] = []
        self._host_map: Dict[str, RetailerAdapter] = {}

    def register(self, adapter: RetailerAdapter):
        self._adapters.append(adapter)
        for host in adapter.supported_hosts:
            self._host_map[host.lower()] = adapter

    def get_adapter_for_host(self, host: str) -> Optional[RetailerAdapter]:
        cleaned_host = host.lower()
        if cleaned_host.startswith("www."):
            cleaned_host = cleaned_host[4:]
        
        # Check direct host match
        if cleaned_host in self._host_map:
            return self._host_map[cleaned_host]

        # Domain family matches (e.g. dl.flipkart.com -> flipkart.com)
        if "flipkart.com" in cleaned_host:
            return self._host_map.get("flipkart.com") or self._host_map.get("teststore.in")
        if "amazon." in cleaned_host:
            return self._host_map.get("amazon.in")

        return None

    def is_host_supported(self, host: str) -> bool:
        return self.get_adapter_for_host(host) is not None

# Global registry instance configured with defaults
registry = AdapterRegistry()
registry.register(MockRetailerAdapter())
registry.register(JsonLdRetailerAdapter())
