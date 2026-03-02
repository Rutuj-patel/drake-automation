import ctypes
import time

import win32gui

from navigation import (
    click_item_detail,
    press_escape,
    save_starting_screen,
    search_and_open,
)
from win32_helpers import CBN_SELCHANGE, wc, we, wx, wc_index
from window_utils import (
    build_hwnd_map,
    find_window_with_controls,
    force_focus,
    wait_for_data_entry,
)

user32 = ctypes.windll.user32

# Starting-screen / main-form control fingerprints
_START_CTRL_IDS = ["1006", "1002", "1007", "1004"]
_MAIN_CTRL_IDS  = ["15001", "15006", "15012"]   # TSJ, description, proceeds

WM_COMMAND      = 0x0111
CB_SETCURSEL    = 0x014E


# Single-record fill

def fill_capital_gain(form_hwnd: int, record: dict, hm: dict | None = None) -> None:
    """Fill all fields for one capital-gains / 1099-B record."""
    hdr      = record.get("header", {})
    payer    = record.get("payer_information", {})
    add_info = record.get("additional_info", {})

    ts               = hdr.get("ts", "T")
    description      = record.get("description", "")
    ein              = payer.get("tin", "")
    date_acquired    = record.get("date_acquired", "")
    date_sold        = record.get("date_sold", "")
    transaction_type = record.get("transaction_type", "")
    proceeds         = record.get("total_proceeds", "")
    cost_or_basis    = record.get("total_cost_basis", "")
    wash_sale        = record.get("wash_sale_loss_disallowed", "")
    adj_w            = record.get("adjustment_codes_W", "")
    adj_d            = record.get("adjustment_codes_D", "")
    adj_m            = record.get("adjustment_codes_M", "")
    collectibles     = bool(add_info.get("collectibles_proceeds_checked", False))
    fed_tax          = add_info.get("federal_income_tax_withheld", "")
    loss_not_allowed = bool(add_info.get("loss_not_allowed_checked", False))
    state_rows       = record.get("state_info", [])
    box_code         = record.get("box_code", 1)  # 1=covered, 2=noncovered

    print(f"\n  ── 1099-B  TS={ts}  box={box_code}  [{str(description)[:50]}]")
    t0 = time.time()

    if hm is None:
        hm = build_hwnd_map(form_hwnd)
    print(f"    {len(hm)} controls mapped")

    # Header combos
    wc(hm, "15001", ts)
    time.sleep(0.15)
    hm = build_hwnd_map(form_hwnd)

    we(hm, "15002", hdr.get("f", ""))
    wc(hm, "15003", hdr.get("st", ""))
    wc(hm, "15004", hdr.get("city", ""))

    # Applicable Part I/Part II combo (15005) — by index
    # Index 0=blank, 1=covered (Box A/D), 2=noncovered (Box B/E)
    hwnd_15005 = hm.get("15005")
    if hwnd_15005 and box_code:
        idx = int(box_code)
        user32.SendMessageW(hwnd_15005, CB_SETCURSEL, idx, 0)
        parent  = win32gui.GetParent(hwnd_15005)
        cid_int = 15005
        user32.PostMessageW(
            parent, WM_COMMAND,
            (CBN_SELCHANGE << 16) | (cid_int & 0xFFFF),
            hwnd_15005,
        )
        print(f"    [C] 15005 = box_code {box_code} (index {idx})")

    # Transaction details
    we(hm, "15006", description)
    we(hm, "15007", ein)
    we(hm, "15008", date_acquired)
    we(hm, "15009", date_sold)
    wc(hm, "15010", transaction_type)
    we(hm, "15012", proceeds)
    we(hm, "15013", cost_or_basis)
    we(hm, "15017", wash_sale)

    # Adjustments
    if adj_w:
        wc(hm, "15019", "W")
        we(hm, "15020", adj_w)
    if adj_d:
        wc(hm, "15022", "D")
        we(hm, "15023", adj_d)
    if adj_m:
        wc(hm, "15025", "M")
        we(hm, "15026", adj_m)

    # Checkboxes
    wx(hm, "15028", collectibles)
    we(hm, "15029", fed_tax)
    wx(hm, "15030", loss_not_allowed)

    # State rows (up to 2)
    for i, st in enumerate(state_rows[:2]):
        base = 15033 + i * 3
        wc(hm, str(base),     st.get("state_name", ""))
        we(hm, str(base + 1), st.get("state_id_no", ""))
        we(hm, str(base + 2), st.get("state_tax_withheld", ""))

    print(f"  ── done in {time.time() - t0:.2f}s ──")


# Orchestration

def process_8949(data: dict) -> None:
    """
    Search 'D' to open the capital-gains starting screen, fill each record,
    save, and close.
    """
    records = data["form_values"].get("capital_gains_transactions", [])
    if not records:
        print("[8949] No capital_gains_transactions records — skipping.")
        return

    print(f"\n{'='*60}")
    print(f"  Form 8949 / Capital Gains — {len(records)} record(s)")
    print(f"{'='*60}")

    for i, r in enumerate(records):
        ts  = r.get("header", {}).get("ts", "?")
        typ = r.get("transaction_type", "?")
        dsc = str(r.get("description", ""))[:45]
        print(f"  {i+1:3}. TS={ts}  {typ}  {dsc}")

    # [1] Find Data Entry window
    general_hwnd = wait_for_data_entry(timeout=15)
    if not general_hwnd:
        raise RuntimeError("[8949] Data Entry window not found!")
    print(f"[8949] General HWND: {general_hwnd}")

    # [2] Search 'D' to open capital-gains starting screen
    search_and_open(general_hwnd, "D")
    start_hwnd, start_hm = find_window_with_controls(
        _START_CTRL_IDS, timeout=12, label="D starting screen"
    )
    if not start_hwnd:
        raise RuntimeError("[8949] Capital-gains starting screen not found!")

    # [3] Process each record
    print(f"\n[8949] Processing {len(records)} record(s)...\n")
    for idx, rec in enumerate(records):
        ts  = rec.get("header", {}).get("ts", "?")
        typ = rec.get("transaction_type", "?")
        dsc = str(rec.get("description", ""))[:40]
        print(f"{'─'*55}")
        print(f"  Record {idx+1}/{len(records)}  TS={ts}  {typ}  {dsc}")
        print(f"{'─'*55}")

        start_hwnd, start_hm = find_window_with_controls(
            _START_CTRL_IDS, timeout=8, label="D starting screen"
        )
        if not start_hwnd:
            print("  [8949] Starting screen lost — stopping.")
            break

        if not click_item_detail(start_hm):
            break

        main_hwnd, main_hm = find_window_with_controls(
            _MAIN_CTRL_IDS, timeout=10, label="main 1099-B form"
        )
        if not main_hwnd:
            print(f"  [8949] Main form not found — skipping record {idx+1}")
            continue

        force_focus(main_hwnd)
        fill_capital_gain(main_hwnd, rec, hm=main_hm)

        print("  ESC → back to starting screen...")
        press_escape(main_hwnd)

    # [4] Save
    print("\n[8949] Saving...")
    start_hwnd, start_hm = find_window_with_controls(
        ["1006", "1007", "1004"], timeout=8, label="D starting screen (save)"
    )
    if start_hwnd:
        save_starting_screen(start_hwnd, start_hm)

    print(f"\n{'='*60}")
    print("  FORM 8949 / CAPITAL GAINS COMPLETE")
    print(f"{'='*60}")