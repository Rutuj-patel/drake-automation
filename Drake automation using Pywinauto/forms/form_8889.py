import time

from navigation import press_escape, search_and_open
from win32_helpers import wc, we, wx
from window_utils import (
    build_hwnd_map,
    find_window_with_controls,
    force_focus,
    wait_for_data_entry,
)


# Window fingerprint
# Form 8889 is identified by: TSJ combo (15001) + Taxpayer-only checkbox (15004)
# + line-2 contributions edit (15006)
_FORM_CTRL_IDS = ["15001", "15004", "15006"]


# Single-record fill

def fill_8889(form_hwnd: int, record: dict, hm: dict | None = None) -> None:
    """
    Fill Form 8889 fields for one record.

    JSON mapping (from sa8889[]):
        header.ts                           → 15001  TS combo (T/S)
        form_value.box_1_taxpayer           → 15004 (True) or 15005 (False) checkbox
        form_value.total_contributions_in_year_2  → 15006  Line 2
        form_value.box_4_contribution_of_archer_msa → 15011  Line 4
        form_value.box_14a_and_15           → 15017 (14a) and 15019 (15)
    """
    hdr = record.get("header", {})
    fv  = record.get("form_value", {})

    ts             = hdr.get("ts", "T")
    box_1_taxpayer = str(fv.get("box_1_taxpayer", "")).strip().lower()
    contributions  = fv.get("total_contributions_in_year_2", "")
    archer_msa     = fv.get("box_4_contribution_of_archer_msa", "")
    box_14a_15     = fv.get("box_14a_and_15", "")

    print(f"\n  ── Form 8889  TS={ts}")
    t0 = time.time()

    if hm is None:
        hm = build_hwnd_map(form_hwnd)
    print(f"    {len(hm)} controls mapped")

    # TS combo
    wc(hm, "15001", ts)
    time.sleep(0.3)     # Drake refreshes fields after TS switch
    hm = build_hwnd_map(form_hwnd)

    # Line 1: Coverage type
    # "true"  → Taxpayer-only  (15004)
    # "false" → Family         (15005)
    if box_1_taxpayer == "true":
        wx(hm, "15004", True)
    elif box_1_taxpayer == "false":
        wx(hm, "15005", True)

    # Line 2: HSA contributions
    we(hm, "15006", contributions)

    # Line 4: Archer MSA contributions
    we(hm, "15011", archer_msa)

    # Lines 14a and 15 (share same JSON value)
    if box_14a_15:
        we(hm, "15017", box_14a_15)   # 14a — total distributions
        we(hm, "15019", box_14a_15)   # 15  — qualified medical expenses

    print(f"  ── done in {time.time() - t0:.2f}s ──")


# Orchestration

def process_8889(data: dict) -> None:
    """
    Search for Form 8889, fill each sa8889 record (switching TS per record),
    then close.
    """
    records = data["form_values"].get("sa8889", [])
    if not records:
        print("[8889] No sa8889 records — skipping.")
        return

    print(f"\n{'='*60}")
    print(f"  Form 8889 (HSA) — {len(records)} record(s)")
    print(f"{'='*60}")

    for i, r in enumerate(records):
        ts = r.get("header", {}).get("ts", "?")
        fv = r.get("form_value", {})
        print(f"  {i+1}. TS={ts}  "
              f"box1={fv.get('box_1_taxpayer','')}  "
              f"contrib={fv.get('total_contributions_in_year_2','')}  "
              f"archer={fv.get('box_4_contribution_of_archer_msa','')}  "
              f"14a/15={fv.get('box_14a_and_15','')}")

    # [1] Find Data Entry window
    general_hwnd = wait_for_data_entry(timeout=15)
    if not general_hwnd:
        raise RuntimeError("[8889] Data Entry window not found!")
    print(f"[8889] General HWND: {general_hwnd}")

    # [2] Search '8889'
    search_and_open(general_hwnd, "8889")
    form_hwnd, form_hm = find_window_with_controls(
        _FORM_CTRL_IDS, timeout=12, label="Form 8889"
    )
    if not form_hwnd:
        raise RuntimeError("[8889] Form 8889 window not found!")
    force_focus(form_hwnd)
    time.sleep(0.3)

    # [3] Fill each record
    # Form 8889 is a single window — changing the TS combo switches between
    # taxpayer and spouse data; no PgDn needed.
    print(f"\n[8889] Processing {len(records)} record(s)...\n")
    for idx, rec in enumerate(records):
        ts = rec.get("header", {}).get("ts", "?")
        print(f"{'─'*55}")
        print(f"  Record {idx+1}/{len(records)}  TS={ts}")
        print(f"{'─'*55}")

        force_focus(form_hwnd)
        form_hm = build_hwnd_map(form_hwnd)
        fill_8889(form_hwnd, rec, hm=form_hm)
        time.sleep(0.4)

    # [4] Close (ESC saves in Drake)
    press_escape(form_hwnd)
    print(f"\n{'='*60}")
    print("  FORM 8889 COMPLETE")
    print(f"{'='*60}")