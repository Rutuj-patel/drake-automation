import json
import sys
import time

from pywinauto.application import Application

import config
from auth import launch_and_login, submit_mfa
from window_utils import force_focus, wait_for_data_entry
from forms import (
    fill_name_and_address,
    open_or_create_return,
    process_1098,
    process_1099_div,
    process_5498,
    process_8889,
    process_8949,
    process_w2,
)

# Helpers

def load_data() -> dict:
    with open(config.DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def banner(title: str) -> None:
    width = 60
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")


# Main

def main() -> None:
    banner("Drake 2024 Tax Software — Automation Start")

    # Load JSON data
    print("\n[MAIN] Loading data.json...")
    data = load_data()
    ssn  = data["client_basic_details"]["section_1"]["ssn_or_itin"]
    print(f"[MAIN] SSN: {ssn}")

    # Launch Drake
    print("\n[MAIN] Launching Drake 2024...")
    app = Application(backend="uia").start(config.DRAKE_PATH)
    time.sleep(config.STARTUP_DELAY)

    # Login + MFA
    banner("Step 2 — Login")
    main_win = launch_and_login(app)

    mfa_ok = submit_mfa(max_retries=config.MFA_MAX_RETRIES)
    if not mfa_ok:
        print("\n[MAIN] MFA failed — aborting.")
        sys.exit(1)

    main_win.set_focus()
    main_win.wait("visible", timeout=30)
    print("[MAIN] Main window ready after login.")

    # Open / Create return
    banner("Step 3 — Open / Create Return")
    open_or_create_return(main_win, ssn, data)

    # Step 4: Name & Address
    banner("Step 4 — Name and Address")
    de_hwnd = wait_for_data_entry(timeout=20)
    if not de_hwnd:
        print("[MAIN] Data Entry window not found — aborting.")
        sys.exit(1)
    fill_name_and_address(de_hwnd, data)
    force_focus(de_hwnd)

    # Step 5: W-2
    banner("Step 5 — W-2 Wages")
    process_w2(data)

    # Step 6: Form 1098
    banner("Step 6 — Form 1098 (Mortgage Interest)")
    process_1098(data)

    # Form 5498 → 8606
    banner("Step 7 — Form 5498 → 8606 (IRA)")
    process_5498(data)

    # 1099-DIV
    banner("Step 8 — Form 1099-DIV")
    process_1099_div(data)

    # Form 8949 / Capital Gains
    banner("Step 9 — Form 8949 / Capital Gains")
    process_8949(data)

    # Form 8889
    banner("Step 10 — Form 8889 (HSA)")
    process_8889(data)

    banner("All Forms Complete ✓")
    print("[MAIN] Drake automation finished successfully.\n")


if __name__ == "__main__":
    main()