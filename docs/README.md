# Public Suffix List Explorer - Web Interface

This is a static web application that uses DuckDB WASM to query the Public Suffix List database directly in your browser.

## Features

- **Real-time Search**: Search by submitter email domain or domain suffix
- **Statistics Dashboard**: View total domains, submitters, and latest update date
- **Quick Filters**: One-click access to major cloud providers
- **CSV Export**: Export search results to CSV
- **No Backend**: Everything runs client-side using WebAssembly

## Technology Stack

- **DuckDB WASM**: Database engine running in the browser
- **Vanilla JavaScript**: No frameworks, pure ES6 modules
- **GitHub Pages**: Static hosting
- **Remote Database**: Attaches directly to the `psl.db` file from GitHub

## How It Works

1. When the page loads, DuckDB WASM is initialized
2. The database file is attached from the GitHub raw URL
3. All queries run client-side in your browser
4. No data is sent to any server - everything is private

## Local Development

Simply open `index.html` in a web browser. Note that you may need to run a local server due to CORS restrictions:

```bash
python -m http.server 8000
# Then visit http://localhost:8000
```

## Deployment

This site is automatically deployed to GitHub Pages from the `/docs` folder on the `main` branch.
