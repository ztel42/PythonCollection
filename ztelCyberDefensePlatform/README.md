# Honeygrid Agent

Lightweight honeypot listener for lab / authorized testing. Captures connection metadata and optional payloads, then forwards telemetry to a collector API.

## Security defaults (read this)

- Binds to **`127.0.0.1`** by default (not `0.0.0.0`).
- Collector calls expect **HTTPS** and an **API bearer token** (`HONEYGRID_API_TOKEN` or `api_token`).
- Concurrent handlers are capped with `max_workers`.
- Default ports are **2222 / 8080** so they do not stomp real SSH/HTTP/SMB.
- Runtime logs are **gitignored** — do not commit `honeygrid_agent.log`.

Only run on systems you own or are authorized to instrument.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml config.local.yaml  # optional
export HONEYGRID_API_TOKEN='your-collector-token'
python Honeygrid_Agent.py
```

## Config

See `config.yaml`. Notable keys:

| Key | Default | Notes |
| --- | --- | --- |
| `bind_host` | `127.0.0.1` | Set `0.0.0.0` only on isolated lab hosts |
| `api_endpoint` | `https://localhost:8000/api/v1/ingest` | HTTPS preferred |
| `require_api_token` | `true` | Set false only for local dry-runs |
| `allow_insecure_http` | `false` | Required to use `http://` endpoints |
| `max_workers` | `32` | Caps accept-handler threads |
| `ports` | `2222`, `8080` | Avoid privileged service ports by default |

## Disclaimer

For authorized cybersecurity research and portfolio demos. Misuse on production or third-party networks is prohibited.


## Changelog

### 2026-09-07 — Security hardening
- Default bind changed from `0.0.0.0` to `127.0.0.1` (`bind_host`)
- Collector calls prefer HTTPS; cleartext HTTP requires `allow_insecure_http: true`
- Collector API bearer token required (`HONEYGRID_API_TOKEN` / `api_token`)
- Concurrent accept handlers capped via `max_workers`
- Default ports moved to `2222` / `8080` to avoid colliding with real SSH/HTTP/SMB
- Pinned `requirements.txt`; added `.gitignore`; removed committed `honeygrid_agent.log`
- README security defaults and authorized-use disclaimer documented
