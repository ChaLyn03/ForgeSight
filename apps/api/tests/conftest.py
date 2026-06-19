import sys
import asyncio
from pathlib import Path

import httpx

# Ensure the apps/api package is importable when running tests from repository root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ASGITestClient:
    def __init__(self, app):
        self.app = app

    def get(self, url: str, **kwargs):
        return asyncio.run(self._request("GET", url, **kwargs))

    def post(self, url: str, **kwargs):
        return asyncio.run(self._request("POST", url, **kwargs))

    async def _request(self, method: str, url: str, **kwargs):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, url, **kwargs)
