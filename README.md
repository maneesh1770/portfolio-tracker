# Portfolio Tracker (GitHub Pages)

A static portfolio dashboard you host free on GitHub Pages.

- **Holdings** with cost, last close, day change, profit/loss and weight
- **Grouped by sector**, with sector subtotals (click a sector row to collapse it)
- **Market-cap summary**: invested amount and % share in large, mid and small cap (ETFs shown separately)
- **News**: recent headlines and results coverage for the companies you hold, filterable by Results, Orders & deals, Ratings & targets, Dividend & corporate

## How it works

GitHub Pages can only serve files, and browsers can't read prices or news from other sites directly. So a scheduled GitHub Action does that job:

```
GitHub Action (weekdays, 16:15 IST)
  scripts/update_data.py  -> data/prices.json  (last close, previous close, market cap)
                          -> data/news.json    (Google News headlines per company)
  commits the two files   -> Pages serves them -> index.html reads them
```

**Your quantities and costs are never in the repo.** You import your holdings in the browser and they are saved in that browser's local storage. The repo holds only public data: stock tickers, closing prices and headlines.

## Set up (about 10 minutes)

1. Create a new GitHub repository. Use a **public** repo for free Pages hosting (private repos need a paid plan).
2. Put every file from this folder in it, including the hidden `.github` folder. Using git is the surest way:
   ```
   git init && git add . && git commit -m "Portfolio tracker"
   git branch -M main
   git remote add origin https://github.com/YOUR-NAME/YOUR-REPO.git
   git push -u origin main
   ```
3. **Settings → Pages**: Source = *Deploy from a branch*, Branch = `main`, folder = `/ (root)`.
4. **Actions tab → Update prices and news → Run workflow.** This first run fills in live prices, market caps and news. After that it runs every weekday by itself.
5. Open `https://YOUR-NAME.github.io/YOUR-REPO/`, click **Import holdings**, and choose your broker holdings `.xlsx` (the one with an *Equity* sheet) or a CSV (below).

If the workflow fails to push, go to **Settings → Actions → General → Workflow permissions** and choose *Read and write permissions*.

## CSV format (alternative to the broker file)

```
symbol,qty,avg_price,sector,client
HDFCBANK,10,700,FINANCIAL SERVICES,ACCOUNT1
NIFTYIETF,100,250,ETF,ACCOUNT1
```
Use sector `ETF` for ETFs. `client` is optional and creates one tab per value.

## Customise

- **`data/symbols.csv`** lists what the Action fetches. Columns: `symbol` (as your broker writes it), `ticker` (Yahoo, usually `SYMBOL.NS`), `name` (used to search news), `match` (optional regex a headline must match, to cut noise), `kind` (`stock` or `etf`). **Add a row for every new holding**, or it will only show the closing price from your holdings file and no news.
- **`data/config.json`** holds the market-cap cut-offs (`largeMinCr`, `midMinCr`, in crore rupees), your `overrides` (for example `{"HDFCAMC": "Mid"}`), and `fallback` estimates used only when a live market cap is missing.

## Things to know

- **Market-cap groups are approximate.** AMFI ranks companies by a six-month average market cap. This site uses each stock's live market cap against the cut-offs in `config.json`. They are set to roughly the Jan to Jun 2026 AMFI levels (about ₹1,06,300 cr for large and ₹33,500 cr for mid). Update them, or use `overrides`, after each AMFI review.
- **Data sources are unofficial.** Prices come from Yahoo Finance via the `yfinance` library and headlines from Google News RSS. Either can change or break. If a symbol fails, the previous value is kept and the Action log says so.
- **News tags are keyword-based** and can be wrong. Always read the source.
- **Scheduled runs can be paused.** GitHub may disable scheduled workflows in a public repo after about 60 days without repo activity. Re-enable it in the Actions tab if that happens.
- **Pages sites are publicly visible.** That is fine here because holdings aren't in the repo, but don't commit your holdings file (the included `.gitignore` blocks `.xlsx` and a `holdings/` folder).
- **Optional:** use *Export holdings.json* and commit `data/holdings.json` if you want the same holdings on every device. Only do this in a repo and site that only you can access.

## Run locally

```
python -m http.server 8000
```
then open http://localhost:8000. (Opening `index.html` directly from the file system can't read the data files.) To refresh the data by hand: `pip install yfinance` then `python scripts/update_data.py`.

This is a tracking tool, not investment advice.
