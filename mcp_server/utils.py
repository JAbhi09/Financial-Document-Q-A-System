import asyncio
import time
import httpx

class RateLimiter:
    """
    Simple rate limiter to enforce a minimum interval between requests.
    SEC EDGAR imposes a limit of 10 requests per second.
    我们 use a slightly more conservative limit (e.g. 0.15s) to be safe.
    """
    def __init__(self, requests_per_second: float = 10.0):
        self.interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self.last_request_time = time.time()

# Global limiter instance
# SEC allows 10 req/s. We set it to 8 to be safe.
limiter = RateLimiter(requests_per_second=8.0)

async def fetch_with_retry(client: httpx.AsyncClient, url: str, headers: dict, retries: int = 3):
    """Fetch a URL with rate limiting and exponential backoff."""
    for attempt in range(retries):
        await limiter.wait()
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = (2 ** attempt) + 1
                print(f"Rate limited. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise e
        except Exception as e:
            if attempt == retries - 1:
                raise e
            await asyncio.sleep(1)
