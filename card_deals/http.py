"""Tiny stdlib HTTP helper with retries."""

import json
import time
import urllib.error
import urllib.request


# Some APIs sit behind Cloudflare, which blocks Python's default "Python-urllib"
# User-Agent (error 1010). Identify the tool with a normal User-Agent instead.
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; card-deals/1.0; +https://github.com/danecom931-tech/personal)",
    "Accept": "application/json",
}


def request_json(url, *, method="GET", headers=None, data=None, retries=3, timeout=30):
    body = data.encode() if isinstance(data, str) else data
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method=method, headers={**DEFAULT_HEADERS, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last = RuntimeError(f"HTTP {e.code} for {url.split('?')[0]}: {detail}")
            if e.code < 500 and e.code != 429:
                raise last
        except (urllib.error.URLError, TimeoutError) as e:
            last = RuntimeError(f"Network error for {url.split('?')[0]}: {e}")
        time.sleep(2 ** (attempt + 1))
    raise last
