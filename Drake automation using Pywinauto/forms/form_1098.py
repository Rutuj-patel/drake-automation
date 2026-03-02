import time

from navigation import press_escape, press_page_down, search_and_open
from win32_helpers import wc, we, wx
from window_utils import (
    build_hwnd_map,
    find_window_with_controls,
    force_focus,
    wait_for_data_entry,
)


# Window finder

def _find_1098_window(timeout: int = 15) -> tuple[int | None, dict]:
    """
    Scan all top-level windows for the 1098 form.
    Identified by the presence of ctrl 15001 (TSJ combo) + 15024 (box 1).
    """
    return find_window_with_controls(["15001", "15024"], timeout=timeout,
                                     label="1098 form")


# Single-record fill

def fill_1098(form_hwnd: int, record: dict, hm: dict | None = None) -> None:
    """Fill all fields for one Form 1098 record."""
    hdr      = record.get("header", {})
    lender   = record.get("lender_information", {})
    borrower = record.get("borrower_information", {})
    boxes    = record.get("box_details", {})
    extra    = record.get("additional_info", {})
    ts       = hdr.get("ts", "T")

    print(f"\n  ── 1098  TS={ts}  [{lender.get('name', '?')}]")
    t0 = time.time()

    if hm is None:
        hm = build_hwnd_map(form_hwnd)
    print(f"    {len(hm)} controls mapped")

    # Header
    wc(hm, "15001", ts)
    time.sleep(0.25)
    hm = build_hwnd_map(form_hwnd)  # rebuild after potential redraw

    st_val = hdr.get("st", "")
    if st_val:
        wc(hm, "15002", st_val)

    wc(hm, "15003", hdr.get("for", hdr.get("For", "A")))

    multi = str(hdr.get("multi_form", "")).strip()
    if multi:
        we(hm, "15004", multi)

    wx(hm, "15005", hdr.get("not_issued_in_taxpayer_name", False))

    # Lender / Recipient
    we(hm, "15006", lender.get("tin"))
    we(hm, "15007", lender.get("name"))
    we(hm, "15008", lender.get("street_address"))
    we(hm, "15009", lender.get("city"))
    wc(hm, "15010", lender.get("state"))
    we(hm, "15011", lender.get("zip"))

    # Borrower / Payer
    b_name = borrower.get("name", "")
    if b_name:
        parts = b_name.rsplit(" ", 1)
        we(hm, "15015", parts[0])
        we(hm, "15016", parts[1] if len(parts) > 1 else "")
    we(hm, "15017", borrower.get("street_address"))
    we(hm, "15018", borrower.get("city"))
    wc(hm, "15019", borrower.get("state"))
    we(hm, "15020", borrower.get("zip"))

    # Boxes 1–11
    we(hm, "15024", boxes.get("box_1"))

    box1_ded = boxes.get("box_1_deductible", "")
    if box1_ded and box1_ded != boxes.get("box_1"):
        we(hm, "15025", box1_ded)

    we(hm, "15026", boxes.get("box_2"))

    box3 = boxes.get("box_3", "")
    if box3:
        we(hm, "15027", box3.replace("/", "").replace("-", ""))

    we(hm, "15028", boxes.get("box_5"))
    we(hm, "15030", boxes.get("box_6"))
    wx(hm, "15031", bool(boxes.get("box_7", False)))

    box8 = boxes.get("box_8", {})
    if isinstance(box8, dict):
        we(hm, "15032", box8.get("street"))
        we(hm, "15033", box8.get("city"))
        wc(hm, "15034", box8.get("state"))
        we(hm, "15035", box8.get("zip"))

    we(hm, "15036", boxes.get("box_9"))
    we(hm, "15037", boxes.get("box_10"))

    box11 = boxes.get("box_11", "")
    if box11:
        we(hm, "15038", box11.replace("/", "").replace("-", ""))

    # Additional info
    we(hm, "15039", extra.get("account_number"))
    we(hm, "15040", extra.get("real_estate_taxes"))
    wx(hm, "15041", bool(extra.get("primary_residence", False)))
    we(hm, "15042", extra.get("taxes_state_property_credit", ""))
    we(hm, "15043", extra.get("explain_more_interest", ""))
    wx(hm, "15044", bool(extra.get("loans_not_used_to_buy", False)))
    we(hm, "15045", extra.get("nondeductible_home_equity", ""))
    wx(hm, "15046", bool(extra.get("do_not_update_to_2025", False)))

    print(f"  ── done in {time.time() - t0:.2f}s ──")


# Orchestration

def process_1098(data: dict) -> None:
    """
    Search for '1098', fill all records, then press ESC to close.
    """
    records = data["form_values"].get("form1098", [])
    if not records:
        print("[1098] No form1098 records — skipping.")
        return

    print(f"\n{'='*55}")
    print(f"  Form 1098 — {len(records)} record(s)")
    print(f"{'='*55}")

    # [1] Find Data Entry window (General tab)
    general_hwnd = wait_for_data_entry(timeout=15)
    if not general_hwnd:
        raise RuntimeError("[1098] Data Entry window not found!")
    print(f"[1098] General HWND: {general_hwnd}")

    # [2] Search and open 1098
    search_and_open(general_hwnd, "1098")
    form_hwnd, hm = _find_1098_window(timeout=15)
    if not form_hwnd:
        raise RuntimeError("[1098] 1098 form window not found!")
    force_focus(form_hwnd)

    # [3] Fill records
    print(f"\n[1098] Processing {len(records)} record(s)...")
    for idx, rec in enumerate(records):
        print(f"\n{'─'*50}")
        print(f"  Record {idx + 1}/{len(records)}")
        print(f"{'─'*50}")

        if idx == 0:
            fill_1098(form_hwnd, rec, hm=hm)
        else:
            press_page_down(form_hwnd)
            fresh_hm = build_hwnd_map(form_hwnd)
            fill_1098(form_hwnd, rec, hm=fresh_hm)

    # [4] Close
    press_escape(form_hwnd)
    print(f"\n{'='*55}")
    print("  1098 COMPLETE")
    print(f"{'='*55}")