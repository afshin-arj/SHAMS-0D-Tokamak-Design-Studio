"""Capture live Deck 5/6 screenshots for QA evidence (Selenium + Edge)."""
from __future__ import annotations

import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".cursor" / "validation" / "reports" / "ui_screenshots" / "20260707"
BASE_URL = os.environ.get("SHAMS_UI_URL", "http://127.0.0.1:8080")


def _open_drawer(driver: webdriver.Edge) -> None:
    try:
        drawer = driver.find_element(By.CSS_SELECTOR, ".shams-left-drawer")
        if drawer.is_displayed():
            return
    except Exception:
        pass
    for xpath in (
        "//button[@title='Toggle study workflow panel (open / close)']",
        "//button[contains(@class,'q-btn') and .//i[contains(text(),'menu')]]",
    ):
        try:
            driver.find_element(By.XPATH, xpath).click()
            time.sleep(0.6)
            return
        except Exception:
            continue


def _nav_deck(driver: webdriver.Edge, deck_short: str, *, timeout: float = 30.0) -> None:
    """Click a numbered deck button in the Helm drawer only."""
    _open_drawer(driver)
    key = deck_short.split(".", 1)[-1].strip() if "." in deck_short else deck_short
    xpaths = [
        f"//div[contains(@class,'shams-left-drawer')]//button[contains(normalize-space(.), '{deck_short}')]",
        f"//div[contains(@class,'shams-left-drawer')]//button[contains(normalize-space(.), '{key}')]",
        f"//button[contains(@class,'helm-deck-btn') and contains(normalize-space(.), '{key}')]",
    ]
    last_err: Exception | None = None
    for xpath in xpaths:
        try:
            el = WebDriverWait(driver, timeout / len(xpaths)).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise last_err or TimeoutException(f"Could not navigate to deck {deck_short!r}")


def _wait_click(driver: webdriver.Edge, text: str, *, timeout: float = 45.0) -> None:
    key = text.split("·", 1)[-1].strip() if "·" in text else text
    xpaths = [
        f"//button[contains(normalize-space(.), '{key}')]",
        f"//*[@role='radio' and contains(normalize-space(.), '{key}')]",
        f"//*[contains(normalize-space(.), '{key}')]",
    ]
    last_err: Exception | None = None
    for xpath in xpaths:
        try:
            el = WebDriverWait(driver, timeout / len(xpaths)).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise last_err or TimeoutException(f"Could not click {text!r}")


def _shot(driver: webdriver.Edge, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    driver.save_screenshot(str(path))
    print(f"saved {path}")


def main() -> None:
    opts = Options()
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    driver = webdriver.Edge(options=opts)
    wait = WebDriverWait(driver, 60)
    try:
        driver.get(BASE_URL)
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'SHAMS')]")))
        time.sleep(1.5)

        _open_drawer(driver)
        try:
            _wait_click(driver, "Anchor a design point", timeout=10.0)
        except TimeoutException:
            pass
        _nav_deck(driver, "1. Point Designer")
        time.sleep(1.0)
        _wait_click(driver, "Truth Console")
        time.sleep(0.5)
        _wait_click(driver, "Configure")
        time.sleep(0.5)
        _wait_click(driver, "Evaluate Point")
        wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(., 'Point evaluation complete') or contains(., 'Dominant:') or contains(., 'Q_DT')]",
                )
            )
        )
        time.sleep(2.0)

        _shot(driver, "pd_post_eval.png")

        try:
            _wait_click(driver, "Compare and trade", timeout=8.0)
        except TimeoutException:
            pass
        _nav_deck(driver, "6. Trade Study Studio")
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[self::h5 or self::div][contains(., 'Trade Study Studio')]")
            )
        )
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(., 'Point evaluation loaded')]")
                )
            )
        except TimeoutException:
            _shot(driver, "ts_gate_debug.png")
            raise
        time.sleep(1.0)
        trade_tabs = [
            ("Setup & Run", "ts_setup_post_eval.png"),
            ("Explore Results", "ts_explore_empty.png"),
            ("Interpret & Families", "ts_interpret_empty.png"),
            ("Export & Handoff", "ts_export_empty.png"),
            ("Advanced Tools", "ts_advanced_tools.png"),
        ]
        for tab, fname in trade_tabs:
            _wait_click(driver, tab)
            time.sleep(0.8)
            _shot(driver, fname)

        # Tiny study for populated explore/interpret.
        _wait_click(driver, "Setup & Run")
        time.sleep(0.5)
        try:
            budget = driver.find_element(By.XPATH, "//input[@type='number']")
            budget.clear()
            budget.send_keys("40")
        except Exception:
            pass
        _wait_click(driver, "Run trade study")
        time.sleep(3.0)
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(., 'feasible') or contains(., 'Pareto')]")
                )
            )
        except TimeoutException:
            time.sleep(25.0)
        _wait_click(driver, "Explore Results")
        time.sleep(1.0)
        _shot(driver, "ts_explore_post_run.png")
        _wait_click(driver, "Interpret & Families")
        time.sleep(0.8)
        _shot(driver, "ts_interpret_post_run.png")

        _nav_deck(driver, "4. Compare")
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Compare')]"))
        )
        time.sleep(1.0)
        _wait_click(driver, "Load Point Designer")
        time.sleep(0.5)
        # Load slot A then slot B (second button).
        buttons = driver.find_elements(
            By.XPATH, "//*[contains(normalize-space(.), 'Load Point Designer')]"
        )
        if buttons:
            buttons[0].click()
            time.sleep(0.5)
        if len(buttons) > 1:
            buttons[1].click()
            time.sleep(0.5)

        cmp_tabs = [
            ("Load A & B", "cmp_load_path_a.png"),
            ("Performance", "cmp_performance_all_outputs.png"),
            ("Constraints", "cmp_constraints_regression.png"),
            ("Inputs & Structure", "cmp_inputs_structure.png"),
            ("Export", "cmp_export.png"),
        ]
        for tab, fname in cmp_tabs:
            _wait_click(driver, tab)
            time.sleep(0.8)
            _shot(driver, fname)

        print("done")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
