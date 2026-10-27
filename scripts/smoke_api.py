"""Exercise the real HTTP server and retain exact response examples."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Exercise an existing server instead of starting a local process")
    args = parser.parse_args()
    (ROOT / "reports/evidence").mkdir(parents=True, exist_ok=True)
    logfile = None
    process = None
    base = args.base_url.rstrip("/") if args.base_url else "http://127.0.0.1:8005"
    if not args.base_url:
        logfile = (ROOT / "reports/evidence/api-server.txt").open("w", encoding="utf-8")
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8005"],
                                   cwd=ROOT, stdout=logfile, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    examples = []
    try:
        for _ in range(60):
            try:
                if requests.get(base + "/health", timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("API did not become ready")
        for endpoint in ["/", "/health", "/drift"]:
            response = requests.get(base + endpoint, timeout=30)
            assert response.status_code == 200
            examples.append({"method": "GET", "endpoint": endpoint, "status": response.status_code,
                             "response": response.json() if endpoint != "/drift" else response.json()["summary"]})
        for horizon in [1, 3, 7]:
            payload = {"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15", "horizon_days": horizon}
            for endpoint in ["/predict", "/explain"]:
                response = requests.post(base + endpoint, json=payload, timeout=30)
                assert response.status_code == 200, response.text
                examples.append({"method": "POST", "endpoint": endpoint, "request": payload,
                                 "status": response.status_code, "response": response.json()})
        for payload, expected in [({"latitude": -12.5, "longitude": -55.0, "date": "2026-08-15"}, 404),
                                  ({"latitude": -22, "longitude": -40, "date": "2024-08-15"}, 422),
                                  ({"latitude": -12.5, "longitude": -55.0, "date": "2026-08-15", "inference_mode": "operational_forecast"}, 503)]:
            response = requests.post(base + "/predict", json=payload, timeout=30)
            assert response.status_code == expected
            examples.append({"method": "POST", "endpoint": "/predict", "request": payload,
                             "status": response.status_code, "response": response.json()})
        (ROOT / "reports/evidence/real-http-examples.json").write_text(json.dumps(examples, indent=2), encoding="utf-8")
        print(f"Verified {len(examples)} actual HTTP responses")
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=20)
        if logfile is not None:
            logfile.close()


if __name__ == "__main__":
    main()
