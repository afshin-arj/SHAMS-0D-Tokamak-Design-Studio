"""Capture Deck 10 (Control Room) screenshots for QA evidence."""
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
OUT = ROOT / ".cursor" / "validation" / "reports" / "ui_screenshots" / "20260712"
BASE_URL = os.environ.get("SHAMS_UI_URL", "http://127.0.0.1:8080")
DRAWER = "//div[contains(@class,'shams-left-drawer')]"
MAIN = "//div[contains(@class,'p-4') or contains(@class,'q-page')][not(ancestor::div[contains(@class,'shams-left-drawer')])]"


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


def _expand_nav_group(driver: webdriver.Edge, group_hint: str, *, timeout: float = 12.0) -> None:
    _open_drawer(driver)
    key = group_hint.split("·", 1)[-1].strip() if "·" in group_hint else group_hint
    opened = driver.execute_script(
        """
        const key = arguments[0];
        const drawer = document.querySelector('.shams-left-drawer');
        if (!drawer) return false;
        const visible = [...drawer.querySelectorAll('button')].some(
          b => (b.innerText||'').includes('Control Room') && b.offsetParent !== null
        );
        if (visible) return true;
        const el = [...drawer.querySelectorAll('*')].find(
          n => (n.innerText||'').includes(key) && (n.innerText||'').length < 80
        );
        if (el) { el.click(); return true; }
        return false;
        """,
        key,
    )
    if opened:
        time.sleep(0.5)
        return
    xpaths = [
        f"{DRAWER}//div[contains(@class,'q-expansion-item')]//div[contains(@class,'q-item') and contains(., '{key}')]",
        f"{DRAWER}//button[contains(@aria-label, '{key}')]",
        f"{DRAWER}//*[contains(normalize-space(.), '{key}') and contains(@class,'q-expansion-item__toggle')]",
        f"{DRAWER}//*[contains(normalize-space(.), '{key}')]",
    ]
    for xpath in xpaths:
        try:
            el = WebDriverWait(driver, timeout / len(xpaths)).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            time.sleep(0.5)
            return
        except Exception:
            continue


def _nav_deck(driver: webdriver.Edge, deck_short: str, *, timeout: float = 45.0) -> None:
    _open_drawer(driver)
    key = deck_short.split(".", 1)[-1].strip() if "." in deck_short else deck_short
    clicked = driver.execute_script(
        """
        const short = arguments[0], key = arguments[1];
        const drawer = document.querySelector('.shams-left-drawer');
        if (!drawer) return null;
        const btns = [...drawer.querySelectorAll('button')];
        const b = btns.find(x => (x.innerText||'').includes(short))
               || btns.find(x => (x.innerText||'').includes(key));
        if (!b) return null;
        b.scrollIntoView({block:'center'});
        b.click();
        return b.innerText;
        """,
        deck_short,
        key,
    )
    if clicked:
        time.sleep(0.8)
        return
    xpaths = [
        f"{DRAWER}//button[contains(@class,'helm-deck-btn') and contains(normalize-space(.), '{deck_short}')]",
        f"{DRAWER}//button[contains(@class,'helm-deck-btn') and contains(normalize-space(.), '{key}')]",
        f"{DRAWER}//button[contains(normalize-space(.), '{deck_short}')]",
        f"{DRAWER}//button[contains(normalize-space(.), '{key}')]",
    ]
    last_err: Exception | None = None
    for xpath in xpaths:
        try:
            el = WebDriverWait(driver, timeout / len(xpaths)).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            time.sleep(0.8)
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise last_err or TimeoutException(f"Could not navigate to deck {deck_short!r}")


def _main_click(driver: webdriver.Edge, text: str, *, timeout: float = 45.0) -> None:
    key = text.split("·", 1)[-1].strip() if "·" in text else text
    xpaths = [
        f"({MAIN}//button[contains(normalize-space(.), '{key}')])[1]",
        f"({MAIN}//*[@role='radio' and contains(normalize-space(.), '{key}')])[1]",
        f"({MAIN}//*[contains(@class,'q-btn-toggle')]//button[contains(normalize-space(.), '{key}')])[1]",
        f"({MAIN}//*[contains(@class,'q-tab') and contains(normalize-space(.), '{key}')])[1]",
        f"({MAIN}//button[contains(normalize-space(.), '{key}')])[1]",
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
    raise last_err or TimeoutException(f"Could not click {text!r} in main deck body")


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
    wait = WebDriverWait(driver, 90)
    try:
        driver.get(BASE_URL)
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'SHAMS')]")))
        time.sleep(1.5)

        _expand_nav_group(driver, "Anchor a design point")
        _nav_deck(driver, "1. Point Designer")
        time.sleep(0.8)
        _main_click(driver, "Truth Console", timeout=15.0)
        time.sleep(0.4)
        _main_click(driver, "Configure", timeout=15.0)
        time.sleep(0.4)
        _main_click(driver, "Evaluate Point", timeout=20.0)
        wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"{MAIN}//*[contains(., 'Point evaluation complete') or contains(., 'Dominant:') or contains(., 'Q_DT')]",
                )
            )
        )
        time.sleep(1.5)

        _expand_nav_group(driver, "Evidence and audit")
        _nav_deck(driver, "10. Control Room")
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"{MAIN}//*[self::div or self::h5][contains(., 'Control Room')]")
            )
        )
        time.sleep(1.0)
        _shot(driver, "cr_shell_governance.png")

        _open_drawer(driver)
        _shot(driver, "cr_helm_group5.png")

        sections = [
            ("1 · Orient", "cr_orient_launchpad.png"),
            ("2 · Constitution", "cr_constitution_assumptions.png"),
            ("3 · Provenance", "cr_provenance_protocol.png"),
            ("4 · Artifacts", "cr_artifacts_explorer.png"),
            ("5 · Diagnostics", "cr_diagnostics_gatechecks.png"),
            ("6 · Chronicle", "cr_chronicle_sensitivity.png"),
        ]
        for tab, fname in sections:
            _main_click(driver, tab)
            time.sleep(0.9)
            _shot(driver, fname)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
