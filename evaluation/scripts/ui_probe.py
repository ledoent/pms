#!/usr/bin/env python3
# pylint: disable=print-used
"""Native browser walkthroughs against the isolated synthetic evaluation DB.

Actions are an explicit JSON array, not a replacement for observing each screen.
Every invocation saves console errors, final text, controls and a screenshot.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

os.environ["PW_TEST_SCREENSHOT_NO_FONTS_READY"] = "1"
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/ui"
OUT.mkdir(parents=True, exist_ok=True)


def locator(page, action):
    if "selector" in action:
        result = page.locator(action["selector"])
    elif "label" in action:
        result = page.get_by_label(action["label"], exact=action.get("exact", True))
    elif "text" in action:
        result = page.get_by_text(action["text"], exact=action.get("exact", True))
    else:
        result = page.get_by_role(
            action.get("role", "button"),
            name=action["name"],
            exact=action.get("exact", True),
        )
    if "nth" in action:
        result = result.nth(action["nth"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="probe")
    parser.add_argument("--actions", default="[]")
    parser.add_argument("--hoot", action="store_true")
    parser.add_argument("--debug-assets", action="store_true")
    parser.add_argument("--mobile", action="store_true")
    args = parser.parse_args()
    errors, console, steps = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 375, "height": 667}
            if args.mobile
            else (
                {"width": 1366, "height": 768}
                if args.hoot
                else {"width": 1440, "height": 1000}
            )
        )
        page = context.new_page()
        page.set_default_navigation_timeout(120000)
        page.set_default_timeout(90000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: console.append(
                {"type": message.type, "text": message.text}
            ),
        )
        # Authenticate the synthetic admin through Odoo's session API; all
        # business operations below are still driven through visible UI controls.
        response = context.request.post(
            "http://127.0.0.1:19320/web/session/authenticate",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {"db": "pms20_ui", "login": "admin", "password": "admin"},
                }
            ),
            headers={"Content-Type": "application/json"},
            timeout=120000,
        )
        if not response.json().get("result", {}).get("uid"):
            raise RuntimeError("Synthetic UI session authentication failed")
        failure = None
        try:
            if args.hoot:
                # Same module hash and URL as Odoo 20 web.tests.test_js.WebSuite.
                module_hash = 0
                for char in "@pms_sale":
                    module_hash = (
                        (module_hash << 5) - module_hash + ord(char)
                    ) & 0xFFFFFFFF
                page.goto(
                    f"http://127.0.0.1:19320/web/tests?headless&loglevel=2&preset={'mobile' if args.mobile else 'desktop'}&timeout=15000&id={module_hash:08x}{'&debug=assets' if args.debug_assets else ''}",
                    wait_until="domcontentloaded",
                )
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    messages = "\n".join(row["text"] for row in console)
                    if (
                        "Test suite succeeded" in messages
                        or "Test suite failed" in messages
                        or "Some tests failed:" in messages
                    ):
                        break
                    page.wait_for_timeout(1000)
                else:
                    raise RuntimeError(
                        "Hoot did not report a nonzero completed test suite"
                    )
                if "Test suite succeeded" not in messages:
                    raise RuntimeError("Hoot reported failure")
            for action in json.loads(args.actions):
                kind = action["do"]
                if kind == "goto":
                    page.goto(
                        "http://127.0.0.1:19320" + action["url"],
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_timeout(action.get("wait", 2000))
                elif kind == "wait":
                    page.wait_for_timeout(action.get("ms", 1500))
                elif kind == "shot":
                    page.screenshot(
                        path=str(OUT / (action["name"] + ".png")), full_page=True
                    )
                elif kind == "click":
                    locator(page, action).click()
                    page.wait_for_timeout(action.get("wait", 1000))
                elif kind == "hover":
                    locator(page, action).hover()
                elif kind == "fill":
                    locator(page, action).fill(action["value"])
                elif kind == "select":
                    locator(page, action).select_option(label=action["value"])
                elif kind == "press":
                    locator(page, action).press(action["value"])
                elif kind == "check":
                    locator(page, action).check()
                elif kind == "expect":
                    locator(page, action).wait_for(state=action.get("state", "visible"))
                else:
                    raise ValueError(kind)
                steps.append(action)
        except Exception as error:
            failure = str(error)
        page.wait_for_timeout(1000)
        page.locator(".o_blockUI").wait_for(state="hidden", timeout=120000)
        data = {
            "evaluation_lock_sha256": hashlib.sha256(
                (ROOT / "evaluation-lock.json").read_bytes()
            ).hexdigest(),
            "url": page.url,
            "steps": steps,
            "failure": failure,
            "errors": errors,
            "console": console,
            "text": page.locator("body").inner_text(),
            "configuration_buttons": page.locator(
                ".o_configuration_button"
            ).evaluate_all(
                "(els) => els.map(e => ({html:e.outerHTML,visible:!!e.offsetParent,parents:[e.parentElement?.outerHTML,e.parentElement?.parentElement?.outerHTML]}))"
            ),
            "description_fields": page.locator(
                ".o_field_widget[name=name]"
            ).evaluate_all("(els) => els.map(e => e.outerHTML)"),
            "controls": page.locator("input,button,select,textarea").evaluate_all(
                '(els) => els.map(e => ({tag:e.tagName, name:e.name, id:e.id, role:e.getAttribute("role"), placeholder:e.placeholder, label:e.getAttribute("aria-label"), text:e.innerText, value:e.value, title:e.title, type:e.type, classes:e.className}))'
            ),
        }
        (OUT / (args.name + ".json")).write_text(json.dumps(data, indent=2))
        page.screenshot(
            path=str(OUT / (args.name + ".png")), full_page=True, timeout=60000
        )
        print(
            json.dumps(
                {
                    key: data[key]
                    for key in ("url", "failure", "errors", "text", "controls")
                },
                indent=2,
            )[:8000]
        )
        browser.close()
    if failure or errors:
        raise SystemExit(failure or repr(errors))


if __name__ == "__main__":
    main()
