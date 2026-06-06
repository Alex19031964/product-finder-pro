import os
import requests
from dotenv import load_dotenv

load_dotenv()


class KeepaClient:
    BASE_URL = "https://api.keepa.com"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("KEEPA_API_KEY")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, keyword: str, domain: int = 2) -> dict:
        if not self.api_key:
            raise RuntimeError("Missing KEEPA_API_KEY. Add it to .env.")
        r = requests.get(
            f"{self.BASE_URL}/search",
            params={"key": self.api_key, "domain": domain, "term": keyword},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def product_by_asin(self, asin: str, domain: int = 2) -> dict:
        if not self.api_key:
            raise RuntimeError("Missing KEEPA_API_KEY. Add it to .env.")
        r = requests.get(
            f"{self.BASE_URL}/product",
            params={"key": self.api_key, "domain": domain, "asin": asin, "stats": 90},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
