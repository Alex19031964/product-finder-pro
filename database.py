import os
import requests
from dotenv import load_dotenv

load_dotenv()


class EbayClient:
    BASE_URL = "https://api.ebay.com/buy/browse/v1"

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("EBAY_ACCESS_TOKEN")
        self.marketplace = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_GB")

    def is_configured(self) -> bool:
        return bool(self.token)

    def search(self, keyword: str, limit: int = 20) -> dict:
        if not self.token:
            raise RuntimeError("Missing EBAY_ACCESS_TOKEN. Add it to .env.")
        r = requests.get(
            f"{self.BASE_URL}/item_summary/search",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
            },
            params={"q": keyword, "limit": limit},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
