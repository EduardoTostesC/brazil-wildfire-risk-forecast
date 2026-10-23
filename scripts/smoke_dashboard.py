"""Capture real desktop/mobile screenshots against a local Streamlit process."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    environment = dict(os.environ, WILDFIRE_USE_SAMPLE="1", PYTHONIOENCODING="utf-8")
    stdout = (ROOT / "reports/evidence/dashboard-server.txt").open("w", encoding="utf-8")
    stderr = (ROOT / "reports/evidence/dashboard-stderr.txt").open("w", encoding="utf-8")
    command = [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py", "--server.headless=true",
               "--server.port=8505", "--browser.gatherUsageStats=false"]
    process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        for _ in range(60):
            try:
                if requests.get("http://localhost:8505/_stcore/health", timeout=2).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Streamlit did not become healthy")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
            errors = []
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://localhost:8505", wait_until="domcontentloaded")
            page.get_by_text("Cells Shown", exact=False).first.wait_for(timeout=120000)
            page.wait_for_timeout(4000)
            if page.locator('[data-testid="stException"]').count():
                raise RuntimeError(page.locator('[data-testid="stException"]').inner_text())
            page.screenshot(path=str(ROOT / "reports/figures/dashboard-desktop.png"), full_page=True)
            for label in ["Cell Ranking", "SHAP Explanation", "Model Health", "About"]:
                page.get_by_role("tab", name=label, exact=False).click()
                page.wait_for_timeout(400)
                if page.locator('[data-testid="stException"]').count():
                    raise RuntimeError("Dashboard tab failed: " + label)
            page.get_by_role("tab", name="Risk Map", exact=False).click()
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(1000)
            page.locator('iframe').first.scroll_into_view_if_needed()
            page.screenshot(path=str(ROOT / "reports/figures/dashboard-mobile.png"), full_page=True)
            browser.close()
        result = {"url": "http://localhost:8505", "mode": "real versioned historical demonstration sample",
                  "browser_errors": errors, "tabs_checked": 5, "viewports": [[1440, 1100], [390, 844]],
                  "screenshots": ["reports/figures/dashboard-desktop.png", "reports/figures/dashboard-mobile.png"]}
        (ROOT / "reports/evidence/dashboard-browser.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        process.terminate()
        process.wait(timeout=20)
        stdout.close()
        stderr.close()


if __name__ == "__main__":
    main()
