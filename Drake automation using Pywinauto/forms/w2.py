# =============================================================================
# forms/w2.py — W-2 Wages form for Drake 2024
# =============================================================================

import time

from pywinauto.application import Application

import config
from navigation import press_escape, press_page_down
from win32_helpers import wc, we, wx
from window_utils import (
    build_hwnd_map,
    force_focus,
    wait_for_data_entry,
)


# ── Control-ID tables ─────────────────────────────────────────────────────────

# Box 12: (code, amount, year) per entry slot
_BOX12_IDS = [
    ("15034", "15035", "15036"),
    ("15037", "15038", "15039"),
    ("15040", "15041", "15042"),
    ("15043", "15044", "15045"),
]

# Box 14: (description, amount) per entry slot
_BOX14_IDS = [
    ("15049", "15050"),
    ("15051", "15052"),
    ("15053", "15054"),
    ("15055", "15056"),
]

# State info: (state, state_id, state_wages, state_tax, local_wages, local_tax, locality)
_STATE_IDS = [
    ("15057", "15058", "15059", "15060", "15061", "15062", "15063"),
    ("15064", "15065", "15066", "15067", "15068", "15069", "15070"),
    ("15071", "15072", "15073", "15074", "15075", "15076", "15077"),
    ("15078", "15079", "15080", "15081", "15082", "15083", "15084"),
]


# ── Single-record fill ────────────────────────────────────────────────────────

def fill_w2(parent_hwnd: int, record: dict) -> None:
    """Fill all fields for one W-2 record into the currently-open W-2 form."""
    hdr     = record.get("header", {})
    emp_er  = record.get("employer_information", {})
    emp_ee  = record.get("employee_information", {})
    wages   = record.get("wages_and_taxes", {})
    b12     = record.get("box_12", {})
    b13     = record.get("box_13", {})
    b14     = record.get("box_14", {})
    st_info = record.get("state_info", {})
    ts      = hdr.get("ts", "T")

    print(f"\n  ── W-2  TS={ts}  [{emp_er.get('name', '?')}]")
    t0 = time.time()

    hm = build_hwnd_map(parent_hwnd)
    print(f"    HWND map: {len(hm)} controls")

    # TS selector — rebuild map after Drake redraws
    wc(hm, "15001", ts)
    time.sleep(0.2)
    hm = build_hwnd_map(parent_hwnd)

    # Corrected checkbox
    wx(hm, "15086", hdr.get("Corrected", False))

    # Employer
    we(hm, "15004", emp_er.get("ein"))
    we(hm, "15005", emp_er.get("name"))
    we(hm, "15006", emp_er.get("name_cont"))
    we(hm, "15007", emp_er.get("street"))
    we(hm, "15008", emp_er.get("city"))
    wc(hm, "15009", emp_er.get("state"))
    we(hm, "15010", emp_er.get("zip"))

    # Employee
    we(hm, "15014", emp_ee.get("first_name"))
    we(hm, "15015", emp_ee.get("last_name"))
    we(hm, "15016", emp_ee.get("street"))
    we(hm, "15017", emp_ee.get("city"))
    wc(hm, "15018", emp_ee.get("state"))
    we(hm, "15019", emp_ee.get("zip"))

    # Boxes 1–11
    we(hm, "15023", wages.get("box_1"))
    we(hm, "15024", wages.get("box_2"))
    we(hm, "15025", wages.get("box_3"))
    we(hm, "15026", wages.get("box_4"))
    we(hm, "15027", wages.get("box_5"))
    we(hm, "15028", wages.get("box_6"))
    we(hm, "15029", wages.get("box_7"))
    we(hm, "15030", wages.get("box_8"))
    we(hm, "15032", wages.get("box_10"))
    we(hm, "15033", wages.get("box_11"))

    # Box 12 entries
    for i, entry in enumerate(b12.get("entries", [])[:4]):
        c, a, y = _BOX12_IDS[i]
        wc(hm, c, entry.get("code"))
        we(hm, a, entry.get("amount"))
        we(hm, y, entry.get("year"))

    # Box 13 checkboxes
    wx(hm, "15046", b13.get("statutory_employee",   False))
    wx(hm, "15047", b13.get("retirement_plan",      False))
    wx(hm, "15048", b13.get("third_party_sick_pay", False))

    # Box 14 entries
    for i, entry in enumerate(b14.get("entries", [])[:4]):
        d, a = _BOX14_IDS[i]
        we(hm, d, entry.get("description"))
        we(hm, a, entry.get("amount"))

    # State info (boxes 15–20)
    for i, entry in enumerate(st_info.get("entries", [])[:4]):
        ids = _STATE_IDS[i]
        wc(hm, ids[0], entry.get("state"))
        we(hm, ids[1], entry.get("state_id"))
        we(hm, ids[2], entry.get("state_wages"))
        we(hm, ids[3], entry.get("state_tax"))
        we(hm, ids[4], entry.get("local_wages"))
        we(hm, ids[5], entry.get("local_tax"))
        wc(hm, ids[6], entry.get("locality"))

    print(f"  ── done in {time.time() - t0:.2f}s ──")


# Orchestration

def process_w2(data: dict) -> None:
    """
    Open the W-2 / Wages form, iterate over all records in *data*, and close.
    """
    records = data["form_values"].get("w2", [])
    if not records:
        print("[W2] No w2 records found in data — skipping.")
        return

    print(f"\n{'='*55}")
    print(f"  W-2 — {len(records)} record(s)")
    print(f"{'='*55}")

    # [1] Find Data Entry window
    hwnd = wait_for_data_entry(timeout=15)
    if not hwnd:
        raise RuntimeError("[W2] Data Entry window not found!")
    print(f"[W2] Data Entry HWND: {hwnd}")
    force_focus(hwnd)

    # [2] Open Wages/W-2 form via UIA nav link
    app = Application(backend="uia").connect(handle=hwnd)
    win = app.window(handle=hwnd)
    win.child_window(title="Wages", auto_id="2016", control_type="Text").click_input()
    time.sleep(config.FORM_OPEN_DELAY)

    # [3] Re-find window after form loads
    hwnd = wait_for_data_entry(timeout=10)
    if not hwnd:
        raise RuntimeError("[W2] Window lost after opening W-2 form!")
    force_focus(hwnd)
    print(f"[W2] W-2 form ready. HWND: {hwnd}")

    # [4] Fill each record
    for idx, rec in enumerate(records):
        print(f"\n{'─'*50}")
        print(f"  Record {idx + 1}/{len(records)}")
        print(f"{'─'*50}")

        if idx > 0:
            print("  PgDn → new blank screen")
            press_page_down(hwnd)
            hwnd = wait_for_data_entry(timeout=8)
            if not hwnd:
                print(f"[W2] Window lost at record {idx + 1} — stopping.")
                break
            force_focus(hwnd)

        fill_w2(hwnd, rec)

    # [5] Close
    press_escape(hwnd)
    print(f"\n{'='*55}")
    print("  W-2 COMPLETE")
    print(f"{'='*55}")