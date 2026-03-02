import time

import win32gui

from navigation import press_escape, press_page_down, search_and_open
from win32_helpers import wc, we, wx
from window_utils import (
    build_hwnd_map,
    find_window_with_controls,
    force_focus,
    wait_for_data_entry,
)


# Window finder

def _find_8606_window(timeout: int = 15) -> tuple[int | None, dict]:
    """
    Find the Form 8606 window.
    Identified by ctrl 15001 (TS) + 15004 (retirement checkbox) + 15009 (line 6).
    """
    return find_window_with_controls(
        ["15001", "15004", "15009"],
        timeout=timeout,
        label="Form 8606",
    )


# Single-record fill

def fill_8606_from_5498(form_hwnd: int, record: dict, hm: dict | None = None) -> None:
    """
    Fill Form 8606 using data from a Form 5498 record.

    Mapped fields:
        header.ts                              → 15001 (TS combo)
        header.ira                             → 15004 (retirement plan checkbox)
        ira.total_ira_contribution_made        → 15005 (total contributions)
        ira.box_6                              → 15009 (line 6 — IRA FMV Dec 31)
    """
    hdr = record.get("header", {})
    ira = record.get("ira", {})
    ts  = hdr.get("ts", "T")

    print(f"\n  ── 8606 (from 5498)  TS={ts}")
    t0 = time.time()

    if hm is None:
        hm = build_hwnd_map(form_hwnd)
    print(f"    {len(hm)} controls mapped")

    # TS combo — rebuild map after Drake redraws
    wc(hm, "15001", ts)
    time.sleep(0.25)
    hm = build_hwnd_map(form_hwnd)

    # Covered by retirement plan at work
    wx(hm, "15004", bool(hdr.get("ira", False)))

    # Total IRA contributions made for the tax year
    we(hm, "15005", ira.get("total_ira_contribution_made", ""))

    # Line 6: Total value of all IRAs on Dec 31
    we(hm, "15009", ira.get("box_6", ""))

    print(f"  ── done in {time.time() - t0:.2f}s ──")


# Orchestration

def process_5498(data: dict) -> None:
    """
    Navigate to Form 8606, fill each 5498 record, then close.
    """
    records = data["form_values"].get("form5498", [])
    if not records:
        print("[5498] No form5498 records — skipping.")
        return

    print(f"\n{'='*55}")
    print(f"  Form 5498 → 8606 — {len(records)} record(s)")
    print(f"{'='*55}")

    # Preview what we will fill
    for i, r in enumerate(records):
        ts  = r.get("header", {}).get("ts", "?")
        b6  = r.get("ira", {}).get("box_6", "")
        con = r.get("ira", {}).get("total_ira_contribution_made", "")
        print(f"  Record {i+1}: TS={ts}  box_6={b6}  contributions={con}")

    # [1] Find Data Entry window
    general_hwnd = wait_for_data_entry(timeout=15)
    if not general_hwnd:
        raise RuntimeError("[5498] Data Entry window not found!")
    print(f"[5498] General HWND: {general_hwnd}")

    # [2] Search for Form 8606
    search_and_open(general_hwnd, "8606")
    form_hwnd, hm = _find_8606_window(timeout=15)
    if not form_hwnd:
        raise RuntimeError("[5498] Form 8606 window not found!")
    force_focus(form_hwnd)

    # [3] Verify key controls are present
    hm_check = build_hwnd_map(form_hwnd)
    for ctrl, label in [
        ("15001", "TS combo"),
        ("15004", "Retirement checkbox"),
        ("15005", "Total contributions"),
        ("15009", "Line 6 IRA value"),
    ]:
        ok  = ctrl in hm_check
        cls = win32gui.GetClassName(hm_check[ctrl]) if ok else "---"
        status = "OK" if ok else "MISSING"
        print(f"    ctrl {ctrl} ({label:22}): {status}  cls={cls}")

    # [4] Fill records
    print(f"\n[5498] Filling {len(records)} record(s) into 8606...")
    for idx, rec in enumerate(records):
        print(f"\n{'─'*50}")
        print(f"  Record {idx + 1}/{len(records)}")
        print(f"{'─'*50}")

        if idx == 0:
            fill_8606_from_5498(form_hwnd, rec, hm=hm)
        else:
            press_page_down(form_hwnd)
            fresh_hm = build_hwnd_map(form_hwnd)
            fill_8606_from_5498(form_hwnd, rec, hm=fresh_hm)

    # [5] Close
    press_escape(form_hwnd)
    print(f"\n{'='*55}")
    print("  5498 → 8606 COMPLETE")
    print(f"{'='*55}")