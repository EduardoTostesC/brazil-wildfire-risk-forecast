"""Verify both languages/viewports/tabs and real missing-data browser states."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.i18n import horizon_label, translate


def start(root, port, log):
    process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py",
        "--server.headless=true", f"--server.port={port}", "--browser.gatherUsageStats=false"],
        cwd=root, env=dict(os.environ, WILDFIRE_USE_SAMPLE="1", PYTHONIOENCODING="utf-8"),
        stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    for _ in range(90):
        if process.poll() is not None:
            raise RuntimeError("Dashboard process exited; inspect server log")
        try:
            if requests.get(f"http://127.0.0.1:{port}/_stcore/health", timeout=1).ok:
                return process
        except requests.RequestException:
            pass
        time.sleep(1)
    process.terminate()
    process.wait(timeout=20)
    raise RuntimeError("Dashboard health timeout")


def ready(page, language, error=False):
    text = translate("unavailable" if error else "shown", language)
    page.get_by_text(text, exact=True).first.wait_for(state="visible", timeout=120000)
    page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=120000)
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    if not error:
        expect(page.get_by_role("tab")).to_have_count(5)
        expect(page.locator('[data-testid="stAlert"]').filter(has_text=translate("warning", language))).to_be_visible()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    evidence = ROOT / "reports/evidence/publication"
    figures = ROOT / "reports/figures/publication"
    evidence.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    log = (evidence / "dashboard-server.txt").open("w", encoding="utf-8")
    process = start(args.root.resolve(), 8505, log)
    results, errors = [], []
    try:
        with sync_playwright() as playwright:
            executable = args.browser_executable or shutil.which("google-chrome")
            windows_chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            if not executable and windows_chrome.exists():
                executable = str(windows_chrome)
            browser = playwright.chromium.launch(headless=True, executable_path=executable)
            for language in ("pt-BR", "en"):
                for device, width, height in [("desktop", 1440, 1100), ("mobile", 390, 844)]:
                    page = browser.new_page(viewport={"width": width, "height": height}, locale=language)
                    page.on("pageerror", lambda exc: errors.append(str(exc)))
                    page.goto(f"http://127.0.0.1:8505/?lang={language}", wait_until="domcontentloaded")
                    ready(page, language)
                    if device == "desktop":
                        for horizon in (1, 3, 7):
                            page.locator('[data-testid="stSidebar"]').get_by_text(horizon_label(horizon, language), exact=True).click()
                            expect(page.locator('[data-testid="stCaptionContainer"]').filter(has_text=f"H={horizon}")).to_be_visible()
                            ready(page, language)
                    sidebar = page.locator('[data-testid="stSidebar"]')
                    if device == "mobile" and sidebar.get_attribute("aria-expanded") == "true":
                        page.locator('[data-testid="stSidebarCollapseButton"] button').click()
                    if device == "mobile":
                        expect(sidebar).to_have_attribute("aria-expanded", "false")
                    home = figures / f"{language}-{device}-home.png"
                    page.screenshot(path=str(home), animations="disabled")
                    checks = []
                    for key in ["map_tab", "rank_tab", "shap_tab", "drift_tab", "about_tab"]:
                        tab = page.get_by_role("tab", name=translate(key, language), exact=True)
                        tab.click()
                        expect(tab).to_have_attribute("aria-selected", "true")
                        panel = page.locator('[role="tabpanel"]:visible')
                        expect(panel).to_have_count(1)
                        if key == "map_tab":
                            iframe = panel.locator("iframe").first
                            iframe.wait_for(state="visible")
                            iframe.content_frame.locator(".leaflet-container").wait_for(state="visible", timeout=60000)
                            iframe.scroll_into_view_if_needed()
                            ready(page, language)
                        else:
                            panel.get_by_role("heading").first.scroll_into_view_if_needed()
                            if key in ("rank_tab", "shap_tab", "drift_tab"):
                                plot = panel.locator('[data-testid="stPlotlyChart"]').first
                                plot.locator(".main-svg").first.wait_for(state="visible", timeout=30000)
                                plot.scroll_into_view_if_needed()
                                box = plot.bounding_box()
                                if not box or box["height"] < 200 or box["width"] < 200:
                                    raise RuntimeError(f"Unreadable chart geometry: {key} {box}")
                        expect(page.locator('[data-testid="stException"]')).to_have_count(0)
                        screenshot = figures / f"{language}-{device}-{key}.png"
                        if key == "map_tab":
                            # Capture the actual map element after its native layout settles.
                            iframe.content_frame.locator(".leaflet-container").screenshot(path=str(screenshot), animations="disabled")
                        else:
                            page.screenshot(path=str(screenshot), animations="disabled")
                        checks.append({"tab": key, "screenshot": screenshot.relative_to(ROOT).as_posix()})
                    results.append({"language": language, "device": device, "viewport": [width, height],
                                    "home": home.relative_to(ROOT).as_posix(), "checks": checks,
                                    "horizons_exercised": [1, 3, 7] if device == "desktop" else [7]})
                    page.close()
            # A separate, disposable copy deliberately lacks the sample. Existing data stay untouched.
            temp_parent = ROOT / ".venv"
            temp_parent.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="dashboard-missing-", dir=temp_parent) as directory:
                missing = Path(directory).resolve()
                assert missing.is_relative_to(temp_parent.resolve())
                for name in ["app", "src", "models", "data/geo"]:
                    shutil.copytree(args.root / name, missing / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                shutil.copy2(args.root / "config.yaml", missing / "config.yaml")
                error_log = (evidence / "dashboard-error-server.txt").open("w", encoding="utf-8")
                error_process = start(missing, 8506, error_log)
                try:
                    for language in ("pt-BR", "en"):
                        page = browser.new_page(viewport={"width": 390, "height": 844}, locale=language)
                        page.on("pageerror", lambda exc: errors.append(str(exc)))
                        page.goto(f"http://127.0.0.1:8506/?lang={language}", wait_until="domcontentloaded")
                        ready(page, language, error=True)
                        page.screenshot(path=str(figures / f"{language}-missing-data.png"), animations="disabled")
                        results.append({"language": language, "missing_data_message_verified": True})
                        page.close()
                finally:
                    error_process.terminate()
                    error_process.wait(timeout=20)
                    error_log.close()
            browser.close()
        result = {"mode": "actual public sample in local browser; screenshots are viewports, not whole documents",
                  "cases": results, "browser_errors": errors}
        (evidence / "dashboard-browser.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if errors:
            raise RuntimeError(f"Browser errors: {errors}")
        print(f"Verified 20 tab/view/language combinations, 2 loading failures; {len(errors)} browser errors")
    finally:
        process.terminate()
        process.wait(timeout=20)
        log.close()


if __name__ == "__main__":
    main()
