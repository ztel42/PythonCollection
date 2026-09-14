import json
import logging
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
import yaml

CONFIG_PATH = "config.yaml"


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logging.error("Configuration file not found.")
        raise SystemExit(1)


config = load_config()

log_level = str(config.get("log_level", "INFO")).upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("honeygrid_agent.log"), logging.StreamHandler()],
)

API_ENDPOINT = config.get("api_endpoint", "https://localhost:8000/api/v1/ingest")
LISTEN_PORTS = config.get("ports", [2222, 8080])
BIND_HOST = config.get("bind_host", "127.0.0.1")
MAX_WORKERS = int(config.get("max_workers", 32))
API_TOKEN = os.environ.get("HONEYGRID_API_TOKEN") or config.get("api_token") or ""
ALLOW_INSECURE_HTTP = bool(config.get("allow_insecure_http", False))
REQUIRE_API_TOKEN = bool(config.get("require_api_token", True))

if BIND_HOST in ("0.0.0.0", "::"):
    logging.warning(
        "bind_host=%s exposes listeners on all interfaces. Use only on isolated lab hosts.",
        BIND_HOST,
    )

if API_ENDPOINT.startswith("http://") and not ALLOW_INSECURE_HTTP:
    logging.error(
        "api_endpoint uses cleartext HTTP. Set https://… or allow_insecure_http: true for local labs only."
    )
    raise SystemExit(2)

if REQUIRE_API_TOKEN and not API_TOKEN:
    logging.error(
        "Collector API token missing. Set HONEYGRID_API_TOKEN or api_token in config.yaml "
        "(or set require_api_token: false for local labs)."
    )
    raise SystemExit(2)

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def handle_client(conn, addr, port):
    try:
        data = conn.recv(2048)
        payload = data.decode(errors="ignore") if data else ""

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_ip": addr[0],
            "source_port": addr[1],
            "destination_port": port,
            "payload": payload.strip(),
        }

        logging.info("[+] Connection from %s:%s on port %s", addr[0], addr[1], port)

        headers = {"Content-Type": "application/json"}
        if API_TOKEN:
            headers["Authorization"] = f"Bearer {API_TOKEN}"

        try:
            response = requests.post(API_ENDPOINT, json=log_entry, headers=headers, timeout=5)
            if response.status_code == 200:
                logging.info("[OK] Event sent to collector.")
            else:
                logging.warning("[!] Collector responded with %s", response.status_code)
        except Exception as e:
            logging.error("[x] Failed to send data to collector: %s", e)
            with open("unsent_logs.json", "a", encoding="utf-8") as backup:
                backup.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logging.error("Error handling client %s: %s", addr, e)
    finally:
        conn.close()


def start_listener(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind((BIND_HOST, port))
        sock.listen(10)
        logging.info("[*] Listening on %s:%s", BIND_HOST, port)
    except Exception as e:
        logging.error("Failed to bind %s:%s: %s", BIND_HOST, port, e)
        return

    while True:
        try:
            conn, addr = sock.accept()
            _executor.submit(handle_client, conn, addr, port)
        except KeyboardInterrupt:
            logging.info("Agent interrupted by user.")
            break
        except Exception as e:
            logging.error("Socket error on port %s: %s", port, e)
            time.sleep(2)


def main():
    logging.info("=== Honeygrid Agent Started ===")
    threads = []

    for port in LISTEN_PORTS:
        t = threading.Thread(target=start_listener, args=(port,), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Shutting down agent...")
        _executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
