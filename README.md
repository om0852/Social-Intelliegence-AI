# Social-Intelliegence-AI

End-to-end social intelligence and proxy tooling for scraping, automation, and analytics workflows.

## What this project does

This repo combines three related systems under one working directory:
- A browser/social scraping and analytics backend
- A proxy scraping service
- A Tor proxy pool server

It is designed for research and automation use cases involving profile, reel, post, search, and bulk extraction workflows.

## Tech stack

- Python
- Node.js
- Playwright
- Tor
- Docker
- FastAPI/Flask-style Python services
- JSON and CSV data files for local datasets

## Repo structure

```
backend/
  app.py
  bulk_extract.py
  parse_urls.py
  analytics.html
  test_final.py
  test_profile.py
  test_reel.py
  core/
    config.py
    domain_util.py
    intelligence.py
    orchestrator.py
    profiles.py
    radar_util.py
    reels.py
    scraper.py
    search_util.py
  social-intel-backend/
    package.json
    server.js
    test.js
    test_reel.js
    core/
      ai.js
      orchestrator.js
      reels.js
      scraper.js
      search.js
  node_scraper/
    index.js
    package.json
proxy_scraper_server/
  app.py
  config.py
  requirements.txt
  scraper.py
  scrape_spys_one.py
  tester.py
  test_client.py
  test_live_proxies.py
  test_ssl_playwright.py
tor_proxy_pool/
  main.py
  proxy_server.py
  config.py
  tor_manager.py
  requirements.txt
  test_proxy.py
```

## Requirements

- Python 3.10+
- Node.js and npm
- Tor
- Playwright browsers if using browser automation
- Docker optional

## Setup

- Use each service folder’s requirements or package manifest as the source of truth.
- `proxy_scraper_server/requirements.txt`
- `tor_proxy_pool/requirements.txt`
- `backend/social-intel-backend/package.json`
- `backend/node_scraper/package.json`

Run Python services with Python, Node services with Node.

## Running

Start the relevant service folders depending on workflow. Proxy services expose local HTTP ports; inspect their main entry files for host/port values.

## Notes

- Some folders include local JSON/CSV scratch artifacts from testing.
- Use only for authorized use, respecting platform terms and data rules.

## License

MIT
