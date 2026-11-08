# PSA 10 Auction Deals

A web page, refreshed every 12 hours, listing eBay **auctions** for **PSA 10**
Pokémon, One Piece, Dragon Ball and Weiss Schwarz cards that:

- have a current bid of **$200 or more**
- **end within 13 hours** of the refresh

Each card shows the current bid, time left (live countdown), shipping, the
PSA 10 market price, **% under/over market**, and the **max bid** that keeps you
10% under market. A **deal** = current bid at least **10% under** the PSA 10
market price. You star the ones you like and bid on eBay yourself; nothing is
ever bid automatically.

Data comes from eBay's official **Browse API** (free). PSA 10 market prices come
from the **PriceCharting API** if you add a key (paid). Without a key, click
"PriceCharting" on a card and type the PSA 10 price in; the page does the math
and remembers it in your browser.

## Preview it now (no keys needed)

```bash
python3 -m card_deals.build --demo --out site/index.html
```

Then open `site/index.html` in a browser. Demo listings are made up.

## One-time setup

### 1. eBay developer keys (free, ~10 minutes)

1. Sign up at <https://developer.ebay.com> and verify your email.
2. Go to **Application Keysets** and create a **Production** keyset.
   (If eBay asks about marketplace account deletion notifications, choose the
   option saying you don't store eBay user data. This tool only reads public listings.)
3. Copy the **App ID (Client ID)** and **Cert ID (Client Secret)**.

### 2. Add them to GitHub

In this repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `EBAY_CLIENT_ID` | App ID |
| `EBAY_CLIENT_SECRET` | Cert ID |
| `PRICECHARTING_TOKEN` | *(optional)* your PriceCharting API token |

Optional: under the **Variables** tab, add `SHIP_TO_ZIP` (your ZIP code) so
eBay returns shipping costs to you.

### 3. Turn on the web page

**Settings → Pages → Source: GitHub Actions.**

GitHub Pages on a **private** repo needs a paid GitHub plan. Pick one:
- make the repo public (no secrets live in the code; keys stay in GitHub Secrets), or
- skip Pages: every run also saves the page as a download named **deals-page**
  on the workflow run's summary page (Actions tab).

The page URL is `https://<your-username>.github.io/<repo-name>/`. Bookmark it.
Stars and typed prices are kept in that browser between refreshes.

### 4. Run it

The schedule runs at 01:17 and 13:17 UTC once this code is on the repo's
**default branch**. To refresh on demand: **Actions → Build card deals page → Run workflow**.

## Running locally

```bash
export EBAY_CLIENT_ID=...
export EBAY_CLIENT_SECRET=...
export PRICECHARTING_TOKEN=...   # optional
python3 -m card_deals.build --out site/index.html
```

Tests: `python3 -m unittest discover -s tests -v`

## Changing the rules

Everything is in `card_deals/config.py`: games and search words, minimum
price, hours ahead, and the deal threshold. The schedule is the `cron` line in
`.github/workflows/deals.yml`.

## Limitations

- **The current bid isn't the final price.** Most auctions jump in the last
  minutes. Use **Max bid** as your ceiling, not the current bid as a promise.
- **PriceCharting matching is automatic but not perfect.** Each match shows its
  confidence. Low-confidence matches are never counted as deals until you type
  the price in yourself. Weiss Schwarz has the weakest coverage.
- **PSA 10 check is title-based.** Listings must say "PSA 10" in the title; lots
  ("lot of 3") are skipped.
- On card listings, PriceCharting's `manual-only-price` field is the PSA 10 price.
  It's worth spot-checking a few against the PriceCharting website at first.

## Cost

- eBay Browse API: free (default limit of 5,000 calls/day; one run uses about 4–20).
- GitHub Actions: free; each run takes a few minutes.
- PriceCharting API: needs a paid PriceCharting subscription. Optional.
