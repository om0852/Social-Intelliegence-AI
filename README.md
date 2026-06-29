---
title: TorProxyPool
emoji: 🐳
colorFrom: indigo
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Portable Rotating Tor Proxy Pool Server

A high-performance asynchronous HTTP CONNECT tunneling proxy that round-robins incoming traffic over a pool of active Tor instances with automated IP circuit rotation.

## Table of Contents

- [What is this?](#what-is-this)
- [Why use it?](#why-use-it)
- [How it works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [Docker](#docker)
  - [Local](#local)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## What is this?

This project is a **portable rotating Tor proxy pool server**. In simple terms:

- It creates a **pool of Tor connections** (think of each Tor connection as a different, anonymous internet identity with its own IP address).
- It accepts **HTTP CONNECT requests** from your application, tool, or script.
- It then **automatically rotates** the outbound request through a different Tor exit node so the destination sees a different IP address on each new connection.

This is useful for web scraping, testing, privacy research, and any workflow that needs many unique IPs without manually managing Tor circuits.

## Why use it?

- **No manual IP rotation**: manage a pool of Tor instances, not a single browser or proxy.
- **High performance**: built with asyncio for concurrent connections.
- **Portable**: Dockerized and config-driven, so it runs the same way locally, on a VPS, or on platforms like Hugging Face Spaces.
- **Minimal dependencies**: Python + Tor + a few packages.

## How it works

1. Start `N` Tor daemon processes.
2. Each Tor daemon listens on a local SOCKS port (e.g., `9050`, `9051`, ...).
3. The proxy server accepts inbound `CONNECT host:port` requests.
4. It assigns each new request to the next Tor daemon in round-robin order.
5. The request is tunneled through that Tor daemon to the destination.
6. Future requests continue rotating, giving you a rotating pool of exit IPs.

## Tech Stack

| Component | Purpose |
|---|---|
| Python 3.10 | Runtime |
| Tor | Anonymous network / IP rotation |
| asyncio | Concurrent request handling |
| Docker | Containerized deployment |
| Hugging Face Spaces | One-click hosted deployment |

## Project Structure

```
├── backend/                 # Backend logic / API or service code
├── tor_proxy_pool/         # Core proxy pool server implementation
│   ├── main.py
│   └── requirements.txt
├── proxy_scraper_server/   # Related proxy scraping/validation service
├── tor_proxy_pool/         # Tor pool implementation
├── Dockerfile              # Container build instructions
├── test_raw.py             # Raw connectivity test
├── test_search.py          # Search/HTML parsing tests
├── test_search2.py         # Additional search tests
└── README.md               # You are here
```

## Prerequisites

- Docker and Docker Compose
- OR Python 3.10+ with `pip`
- Tor (system package) if running locally without Docker

## Setup

### Docker

```bash
docker build -t tor-proxy-pool .
docker run -p 7860:7860 tor-proxy-pool
```

### Local (Python)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
python tor_proxy_pool/main.py
```

### Hugging Face Spaces

Use the standard Hugging Face Spaces Docker workflow. The `Dockerfile` is already configured for Spaces with:
- user UID 1000
- port 7860
- `tor_proxy_pool/main.py` as entrypoint

## Usage

Once running, configure your application to use the proxy on `http://localhost:7860` as an HTTP CONNECT proxy depending on how your client is set up.

### Quick test

Send an HTTP CONNECT request through the proxy:

```bash
curl -x http://localhost:7860 https://check.torproject.org
```

Repeated requests should alternate exit IPs as the request rotates through the pool.

## Configuration

Current configuration is mostly defined in code. Key areas to inspect:

- `tor_proxy_pool/main.py` — startup and rotation logic
- `Dockerfile` — port, user, dependencies
- Requirement files in subpackages — per-service dependency lists

Recommended additions for production:
- Env var configuration for pool size, ports, timeouts
- Health checks for each Tor daemon before routing traffic
- Logging rotation and request tracing

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| Connection timeout | Tor daemon slow to bootstrap | Wait 30-60s after startup |
| Port 9050 already in use | Local Tor running | Stop local Tor or change ports |
| Empty HTML body when scraping | Anti-bot blocking | Combine with a browser/profile rotation strategy |
| High memory usage | Each Tor daemon is a separate process | Reduce pool size or use swap |

## Security Considerations

- This project is intended for **authorized use only**: research, testing, and public web access.
- Do not use this service to access systems, networks, or content without explicit permission.
- Tor exit node traffic is subject to exit node policies and legal jurisdictions.
- Running a misconfigured open proxy can expose your server to abuse. Bind appropriately and add authentication if exposed externally.
