import time

from navigation import (
    click_hwnd,
    press_escape,
    save_starting_screen,
    search_and_open,
    click_item_detail,
)
from win32_helpers import wc, we, wx
from window_utils import (
    build_hwnd_map,
    find_window_with_controls,
    force_focus,
    wait_for_data_entry,
)


# Starting-screen controls
# DIV starting screen: ListBox=1006, ItemDetail=1002, Save=1007, Cancel=1004
_START_CTRL_IDS = ["1006", "1002", "1007", "1004"]

# Main 1099-DIV form: TSJ=15001, Payer TIN=15006, Box 1a=15018
_MAIN_CTRL_IDS  = ["15001", "15006", "15018"]


# Single-record fill

def fill_1099_div(form_hwnd: int, record: dict, hm: dict | None = None) -> None:
    """Fill all fields for one 1099-DIV record."""
    hdr   = record.get("header", {})
    payer = record.get("payer_information", {})
    ts    = hdr.get("ts", "T")

    print(f"\n  ── 1099-DIV  TS={ts}  [{payer.get('name', '?')[:50]}]")
    t0 = time.time()

    if hm is None:
        hm = build_hwnd_map(form_hwnd)
    print(f"    {len(hm)} controls mapped")

    # Header
    wc(hm, "15001", ts)
    time.sleep(0.15)
    hm = build_hwnd_map(form_hwnd)  # refresh after TSJ change

    # Payer information
    we(hm, "15006", payer.get("tin"))
    wx(hm, "15007", bool(payer.get("check_if_ssn", False)))
    we(hm, "15008", payer.get("name"))
    we(hm, "15009", payer.get("street_address"))
    we(hm, "15010", payer.get("city"))
    wc(hm, "15011", payer.get("state"))
    we(hm, "15012", payer.get("zip"))
    we(hm, "15016", record.get("account_number"))
    wx(hm, "15017", bool(record.get("fatca_filing_requirement", False)))

    # Dividend boxes
    we(hm, "15018", record.get("box_1a_total_ordinary_dividends"))
    we(hm, "15019", record.get("box_1b_qualified_dividends"))
    we(hm, "15020", record.get("box_2a_total_capital_gain_dist"))
    we(hm, "15021", record.get("box_2b_unrecap_sec_1250_gain"))
    we(hm, "15023", record.get("box_2c_section_1202_gain"))
    we(hm, "15024", record.get("box_2d_collectibles_28_rate_gain"))
    we(hm, "15025", record.get("box_2e_section_897_ordinary_dividends"))
    we(hm, "15026", record.get("box_2f_section_897_capital_gain"))
    we(hm, "15027", record.get("box_3_nondividend_distributions"))
    we(hm, "15028", record.get("box_4_federal_income_tax_withheld"))
    we(hm, "15029", record.get("box_5_section_199a_dividends"))
    we(hm, "15030", record.get("box_6_investment_expenses"))
    we(hm, "15031", record.get("box_7_foreign_tax_paid"))
    wc(hm, "15032", record.get("box_8_foreign_country_or_us_possession"))
    we(hm, "15033", record.get("box_9_cash_liquidation_distributions"))
    we(hm, "15034", record.get("box_10_noncash_liquidation_distributions"))
    we(hm, "15035", record.get("box_12_exempt_interest_dividends"))
    we(hm, "15036", record.get("box_13_specified_private_activity_bond_interest_dividends"))

    # State info (up to 2 rows)
    for i, st in enumerate(record.get("state_info", [])[:2]):
        base = 15037 + i * 3
        wc(hm, str(base),     st.get("state"))
        we(hm, str(base + 1), st.get("state_id"))
        we(hm, str(base + 2), st.get("state_tax_withheld"))

    print(f"  ── done in {time.time() - t0:.2f}s ──")


# Orchestration

def process_1099_div(data: dict) -> None:
    """
    Search 'DIV', iterate the starting screen, fill each record, save, close.
    """
    records = data["form_values"].get("div1099", [])
    if not records:
        print("[DIV] No div1099 records — skipping.")
        return

    print(f"\n{'='*60}")
    print(f"  1099-DIV — {len(records)} record(s)")
    print(f"{'='*60}")

    for i, r in enumerate(records):
        ts = r.get("header", {}).get("ts", "?")
        nm = r.get("payer_information", {}).get("name", "")[:45]
        print(f"  {i+1}. TS={ts}  {nm}")

    # [1] Find Data Entry window
    general_hwnd = wait_for_data_entry(timeout=15)
    if not general_hwnd:
        raise RuntimeError("[DIV] Data Entry window not found!")
    print(f"[DIV] General HWND: {general_hwnd}")

    # [2] Search 'DIV' to open starting screen
    search_and_open(general_hwnd, "DIV")
    start_hwnd, start_hm = find_window_with_controls(
        _START_CTRL_IDS, timeout=12, label="DIV starting screen"
    )
    if not start_hwnd:
        raise RuntimeError("[DIV] DIV starting screen not found!")

    # [3] Process each record
    print(f"\n[DIV] Processing {len(records)} record(s)...\n")
    for idx, rec in enumerate(records):
        ts = rec.get("header", {}).get("ts", "?")
        nm = rec.get("payer_information", {}).get("name", "")[:35]
        print(f"{'─'*55}")
        print(f"  Record {idx+1}/{len(records)}  TS={ts}  {nm}")
        print(f"{'─'*55}")

        # Re-acquire starting screen
        start_hwnd, start_hm = find_window_with_controls(
            _START_CTRL_IDS, timeout=8, label="DIV starting screen"
        )
        if not start_hwnd:
            print("  [DIV] Starting screen lost — stopping.")
            break

        # Click Item Detail → opens blank main form
        if not click_item_detail(start_hm):
            break

        main_hwnd, main_hm = find_window_with_controls(
            _MAIN_CTRL_IDS, timeout=10, label="main 1099-DIV form"
        )
        if not main_hwnd:
            print(f"  [DIV] Main form not found — skipping record {idx+1}")
            continue

        force_focus(main_hwnd)
        fill_1099_div(main_hwnd, rec, hm=main_hm)

        print("  ESC → back to starting screen...")
        press_escape(main_hwnd)

    # [4] Save
    print("\n[DIV] Saving...")
    start_hwnd, start_hm = find_window_with_controls(
        ["1006", "1007", "1004"], timeout=8, label="DIV starting screen (save)"
    )
    if start_hwnd:
        save_starting_screen(start_hwnd, start_hm)

    print(f"\n{'='*60}")
    print("  1099-DIV COMPLETE")
    print(f"{'='*60}")