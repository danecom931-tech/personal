"""Tiny stdlib HTTP helper with retries."""

import json
import time
import urllib.error
import urllib.request


def request_json(url, *, method="GET", headers=None, data=None, retries=3, timeout=30):
    body = data.encode() if isinstance(data, str) else data
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
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
