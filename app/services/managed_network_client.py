import asyncio
import os
import random
import time
from dataclasses import dataclass

import httpx


@dataclass
class ManagedRequestResult:
    status_code: int
    json_data: dict | list | None
    text: str
    attempts: int
    duration_seconds: float


class ManagedNetworkClient:
    """Managed outbound client that improves reliability and attribution safety.

    Intelligence value:
    - Consistent timeout/retry behavior reduces silent data gaps.
    - Jitter and UA rotation reduce request fingerprint consistency.
    - Proxy routing from environment variables supports managed attribution.
    - Central handling of HTTP 429 responses preserves collection continuity.
    """

    _DEFAULT_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]

    def __init__(self) -> None:
        timeout_seconds = float(os.getenv("MANAGED_HTTP_TIMEOUT", "15"))
        self.max_retries = int(os.getenv("MANAGED_HTTP_RETRIES", "2"))
        self.jitter_min = float(os.getenv("MANAGED_JITTER_MIN", "0.5"))
        self.jitter_max = float(os.getenv("MANAGED_JITTER_MAX", "3.0"))

        proxy_url = os.getenv("MANAGED_PROXY_URL") or os.getenv("SOCKS5_PROXY")
        mounts = None
        if proxy_url:
            mounts = {
                "http://": httpx.AsyncHTTPTransport(proxy=proxy_url),
                "https://": httpx.AsyncHTTPTransport(proxy=proxy_url),
            }

        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds), mounts=mounts)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ManagedNetworkClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict | None = None,
    ) -> ManagedRequestResult:
        """Execute a managed request and return typed transport metadata and payload."""
        start = time.monotonic()
        attempts = 0
        request_headers = dict(headers or {})

        while True:
            attempts += 1
            await self._request_jitter()
            request_headers["User-Agent"] = self._random_user_agent()

            try:
                response = await self._client.request(
                    method=method.upper(),
                    url=url,
                    headers=request_headers,
                    params=params,
                )
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempts > self.max_retries + 1:
                    raise
                await asyncio.sleep(0.25 * attempts)
                continue

            if response.status_code == 429 and attempts <= self.max_retries + 1:
                retry_after = self._retry_after_seconds(response)
                await asyncio.sleep(retry_after)
                continue

            if response.status_code >= 500 and attempts <= self.max_retries + 1:
                await asyncio.sleep(0.3 * attempts)
                continue

            payload: dict | list | None
            try:
                payload = response.json()
            except ValueError:
                payload = None

            return ManagedRequestResult(
                status_code=response.status_code,
                json_data=payload,
                text=response.text,
                attempts=attempts,
                duration_seconds=time.monotonic() - start,
            )

    async def _request_jitter(self) -> None:
        await asyncio.sleep(random.uniform(self.jitter_min, self.jitter_max))

    @classmethod
    def _random_user_agent(cls) -> str:
        return random.choice(cls._DEFAULT_USER_AGENTS)

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float:
        retry_after = response.headers.get("Retry-After", "1")
        try:
            return max(float(retry_after), 0.5)
        except ValueError:
            return 1.0
