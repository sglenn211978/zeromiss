"""JobLatch AI Voice Dispatch - Story-Driven Interactive Demo & Fleet Command Server.

Designed around the core end-to-end product story:
Missed Call / Live Voice -> AI Triage & Safety Verification -> Instant Dispatch -> Upfront Stripe Deposit.
"""

import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional, List

from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB


# Global state for demo session
ACTIVE_AGENT = VoiceDispatchAgent()
ACTIVE_SESSION = ACTIVE_AGENT.create_session()
DEMO_DISPLAY_EMAIL = "dispatch@apex-electrical-demo.com"
LAST_DIALOGUE = []
LAST_SCENARIO_MODE = "missed_call"

# Rate limiting structures for public demo calls
DEMO_CALL_RATE_LIMIT_IP: Dict[str, List[float]] = {}
DEMO_CALL_RATE_LIMIT_PHONE: Dict[str, List[float]] = {}


def enrich_booking_dict(booking_obj: Any, scenario_hint: Optional[str] = None) -> Dict[str, Any]:
    """Formats raw booking & triage fields into clean, contractor-grade human-readable strings."""
    if not booking_obj:
        return {}
    b = dict(booking_obj.__dict__) if hasattr(booking_obj, "__dict__") else dict(booking_obj)

    urg = str(b.get("urgency_level", "")).upper()
    raw_service = str(b.get("service_type", "")).strip()
    raw_issue = str(b.get("issue_description", "")).strip()
    raw_cust = str(b.get("customer_name", "")).strip()
    raw_date = str(b.get("slot_date", "")).strip()
    raw_time = str(b.get("slot_time", "")).strip()

    is_emerg = "EMERG" in urg or raw_service.lower() == "emergency" or scenario_hint == "emergency"

    # 1. Clean Customer Name (never show "Resident / Caller")
    if not raw_cust or "resident" in raw_cust.lower() or "caller" in raw_cust.lower():
        clean_customer = "David Miller" if is_emerg else "Alex Rivera"
    else:
        clean_customer = raw_cust.replace("(Recouped Lead)", "").strip()
    b["customer_name"] = clean_customer

    # 2. Clean Service Title (never show "emergency — Resident / Caller")
    issue_lower = raw_issue.lower()
    if is_emerg:
        if "burning" in issue_lower or "rubber" in issue_lower or "smell" in issue_lower or scenario_hint == "emergency":
            clean_title = "Electrical Emergency: Burning Smell"
            symptom = "Burning rubber odor coming from wall outlet behind refrigerator"
        elif "spark" in issue_lower or "arc" in issue_lower:
            clean_title = "Electrical Emergency: Active Sparking at Panel"
            symptom = "Visible arcing and popping noises at main breaker panel"
        elif "water" in issue_lower or "flood" in issue_lower:
            clean_title = "Electrical Emergency: Water Near Breaker Panel"
            symptom = "Water intrusion near live electrical panel in basement"
        elif "shock" in issue_lower:
            clean_title = "Electrical Emergency: Live Shock Hazard"
            symptom = "Caller reported electrical shock from appliance/outlet"
        else:
            clean_title = "Electrical Emergency: Priority Hazard Dispatch"
            symptom = raw_issue.replace("EMERGENCY:", "").replace("_", " ").strip() or "Acute electrical thermal/arcing hazard reported"
        hazard_level = "NFPA 70E Code Red — Active Thermal / Fire Risk"
        hazard_short = "🚨 Hazard: NFPA 70E Code Red (Thermal)"
        safety_given = (
            "Stay clear of the appliance and wall outlet; do not touch the cord. "
            "Shut off the main breaker only if the path is dry and safe. Evacuate and call 911 if smoke appears."
        )
    else:
        if "ev" in raw_service.lower() or "ev" in issue_lower or "charger" in issue_lower:
            clean_title = "EV Charger 50A Installation"
            symptom = "50A NEMA 14-50 / Level 2 EV charger installation in residential garage"
            hazard_level = "Routine Service — Non-Hazardous (200A Panel Verified)"
            hazard_short = "🛡️ Triage: 200A Panel Capacity Verified"
        elif "panel" in raw_service.lower() or "panel" in issue_lower or "breaker" in issue_lower:
            clean_title = "200A Main Panel Upgrade"
            symptom = raw_issue or "Flickering lights under load & warm 100A main breaker lug"
            hazard_level = "Priority Load Check — Thermal Lug Inspection"
            hazard_short = "⚠️ Hazard: Warm 100A Breaker Lug"
        elif raw_service:
            clean_title = f"{raw_service.replace('_', ' ').title()}"
            symptom = raw_issue or f"Scheduled {raw_service.replace('_', ' ')} service call"
            hazard_level = "Routine Service — Non-Hazardous"
            hazard_short = "🛡️ Triage: Standard Diagnostic"
        else:
            clean_title = "Residential Electrical Service"
            symptom = raw_issue or "Standard diagnostic and electrical repair"
            hazard_level = "Routine Service — Non-Hazardous"
            hazard_short = "🛡️ Triage: Standard Diagnostic"
        safety_given = "No active thermal or shock hazard detected. Pre-arrival preparation checklist texted to homeowner."

    # Check if DB has an emergency triage report to pull exact details
    if is_emerg and DB.emergency_reports:
        latest_rep = list(DB.emergency_reports.values())[-1]
        if latest_rep.immediate_life_safety_actions:
            safety_given = " ".join(latest_rep.immediate_life_safety_actions[:2])

    # 3. Clean Window (never show "2026-11-04 (Within 45-60 Minutes (Priority Code Red))")
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    tmrw_str = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")

    if is_emerg or "45-60" in raw_time or "priority" in raw_time.lower():
        clean_window = "Today, within 45–60 min"
    else:
        if raw_date == today_str or raw_date.lower() == "today":
            day_label = "Today"
        elif raw_date == tmrw_str or raw_date.lower() == "tomorrow":
            day_label = "Tomorrow"
        else:
            try:
                dt_obj = datetime.strptime(raw_date, "%Y-%m-%d")
                day_label = dt_obj.strftime("%a, %b %-d")
            except Exception:
                day_label = raw_date
        clean_time_part = re.sub(r"\s*\([^)]*\)", "", raw_time).strip().replace("08:00 AM", "8:00 AM").replace("04:00 PM", "4:00 PM").replace("07:00 PM", "7:00 PM")
        clean_window = f"{day_label}, {clean_time_part}"

    tech_str = str(b.get("assigned_technician", "")).lower()
    if not b.get("tech_match_reason"):
        if is_emerg or "marcus" in tech_str:
            b["tech_match_reason"] = "Master Electrician • On-Call Lead • Nearest (14m)"
        elif "sarah" in tech_str:
            b["tech_match_reason"] = "EV & Commercial Certified • 240V Load Specialist"
        elif "luis" in tech_str:
            b["tech_match_reason"] = "Service Electrician • On-Call Shift"
        else:
            b["tech_match_reason"] = "Licensed Journeyman • Panel & Load Balancing"

    if not b.get("booked_by"):
        b["booked_by"] = "Booked by Sarah AI"

    if not b.get("truck_id"):
        if is_emerg or "marcus" in tech_str:
            b["truck_id"] = "TRUCK-01 (Master Emergency Van)"
        elif "sarah" in tech_str:
            b["truck_id"] = "TRUCK-03 (EV & Commercial Van)"
        elif "luis" in tech_str:
            b["truck_id"] = "TRUCK-04 (Rapid Response Van)"
        else:
            b["truck_id"] = "TRUCK-02 (200A Panel & Service Rig)"

    # 4. NEC 220.82 Load Calculation & Pre-Qualified Field Upsell Intelligence
    title_l = clean_title.lower()
    if is_emerg:
        nec_load_summary = "150A/200A Main Service • Branch Circuit #14 Isolated • Thermal Fault Containment Active"
        upsell_rec = "Whole-Home Dual-Function AFCI/GFCI Breaker & Type 2 Surge Protection Package (NEC 230.67)"
        upsell_val = 650
    elif "ev" in title_l:
        nec_load_summary = "NEC 220.82 Calculation: 200A Service • ~114A Existing Peak • +86A Headroom ✓ Approved for 48A EVSE"
        upsell_rec = "Whole-Home Type 2 Surge Protective Device (NEC 230.67 EVSE Protection) — +$485 Add-On"
        upsell_val = 485
    elif "panel" in title_l:
        nec_load_summary = "NEC 220.82 Calculation: Existing 100A Bus @ 112% Peak Load • 200A Copper Bus Upgrade Required"
        upsell_rec = "Whole-Home Generator Interlock Kit + 50A NEMA 14-50 Inlet Box — +$790 Add-On"
        upsell_val = 790
    else:
        nec_load_summary = "NEC 220.82 Calculation: 200A Main Service Verified • Branch Circuit Load Within 80% Continuous Limit"
        upsell_rec = "Whole-Home Type 2 Surge Protective Device (NEC 230.67 Compliance) — +$485 Add-On"
        upsell_val = 485

    if not b.get("panel_photo_analysis"):
        if is_emerg:
            b["panel_photo_analysis"] = {
                "uploaded": False,
                "photo_label": "Awaiting Homeowner SMS Photo (or Click Simulate)",
                "equipment_detected": "Square D QO 150A Main Panel • NEMA 5-15R Branch Circuit",
                "breaker_spec": "Square D QO120DF (20A Dual-Function AFCI/GFCI)",
                "open_spaces": "2 Open Spaces (Pre-Estimated)",
                "ai_finding": "SMS link sent to homeowner to snap photo of affected outlet & main breaker panel prior to arrival.",
                "parts_verification": "⏳ Click '📸 Simulate Customer Photo' to verify exact breaker series",
            }
        elif "ev" in title_l:
            b["panel_photo_analysis"] = {
                "uploaded": False,
                "photo_label": "Awaiting Homeowner SMS Photo (or Click Simulate)",
                "equipment_detected": "200A Main Breaker Loadcenter (Reported by Caller)",
                "breaker_spec": "50A 2-Pole EVSE Breaker (Brand Verified Upon Photo)",
                "open_spaces": "2+ Open Spaces (Reported by Caller)",
                "ai_finding": "SMS link sent to homeowner to snap panel label & breaker directory so tech loads exact 50A breaker brand.",
                "parts_verification": "⏳ Click '📸 Simulate Customer Photo' to lock in breaker brand",
            }
        else:
            b["panel_photo_analysis"] = {
                "uploaded": False,
                "photo_label": "Awaiting Homeowner SMS Photo (or Click Simulate)",
                "equipment_detected": "200A Residential Main Breaker Panel",
                "breaker_spec": "20A Dual-Function AFCI/GFCI Breaker",
                "open_spaces": "4 Open Spaces (Pre-Estimated)",
                "ai_finding": "SMS link sent to homeowner to upload breaker panel photo prior to truck roll.",
                "parts_verification": "⏳ Click '📸 Simulate Customer Photo' to verify breaker brand",
            }

    # 5. Municipal E-Permit & Homeowner Tax Credit / Utility Rebate Packet + 3-Option Flat-Rate Proposal
    conf_num = str(b.get("confirmation_id", "1005")).split("-")[-1]
    if is_emerg:
        permit_info = f"Municipal E-Permit #EL-2026-{conf_num} (Emergency Repair Exemption • Master Lic #EL-49201-MA)"
        rebate_summary = "Qualifies for $600 IRS Sec. 25C Panel/Circuit Safety Credit (30% Federal Tax Credit)"
    elif "ev" in title_l:
        permit_info = f"Municipal E-Permit #EL-2026-{conf_num} (240V EVSE Branch Circuit • Auto-Drafted for 1-Click E-Filing)"
        rebate_summary = "Qualifies for up to $1,100 Customer Incentives ($600 IRS Sec. 30C/25C Credit + $500 Utility EV Rebate)"
    elif "panel" in title_l:
        permit_info = f"Municipal E-Permit #EL-2026-{conf_num} + Utility Service Upgrade Packet (Auto-Drafted for 1-Click Filing)"
        rebate_summary = "Qualifies for up to $1,250 Customer Incentives ($600 IRS Sec. 25C 200A Panel Credit + $650 Utility Rebate)"
    else:
        permit_info = f"Municipal E-Permit #EL-2026-{conf_num} (Master Lic #EL-49201-MA • Ready for 1-Click E-Filing)"
        rebate_summary = "Qualifies for 30% IRS Sec. 25C Electrical Efficiency & Safety Upgrade Tax Credit"

    selected_tier = str(b.get("selected_option_tier") or "GOOD").upper()
    upsell_added = float(b.get("upsell_added_amount") or 0.0)
    total_est_val = float(b.get("estimated_job_value") or (1850.0 if is_emerg else 1450.0))
    base_est_val = max(300.0, total_est_val - upsell_added)

    quote_options = [
        {
            "tier": "GOOD",
            "label": "Option 1: Good (Standard Scope)",
            "desc": f"{clean_title} — Standard NEC-compliant repair & 1-Yr Workmanship Warranty",
            "price": base_est_val,
            "total": base_est_val,
            "delta": 0,
        },
        {
            "tier": "BETTER",
            "label": "Option 2: Better ★ Most Popular (+$485)",
            "desc": f"{clean_title} + Whole-Home Type 2 Surge Protection (NEC 230.67) & 3-Yr Warranty",
            "price": base_est_val + 485.0,
            "total": base_est_val + 485.0,
            "delta": 485,
        },
        {
            "tier": "BEST",
            "label": "Option 3: Best 👑 Complete Protection (+$950)",
            "desc": f"{clean_title} + Surge Protection + Dual-Function AFCI/GFCI Breaker Rejuvenation & 5-Yr Warranty",
            "price": base_est_val + 950.0,
            "total": base_est_val + 950.0,
            "delta": 950,
        },
    ]

    b["display_title"] = clean_title
    b["display_window"] = clean_window
    b["triage_symptom"] = symptom
    b["triage_hazard_level"] = hazard_level
    b["triage_hazard_short"] = hazard_short
    b["triage_safety_instruction"] = safety_given
    b["nec_load_summary"] = nec_load_summary
    b["upsell_recommendation"] = upsell_rec
    b["upsell_value"] = upsell_val
    b["permit_info"] = permit_info
    b["rebate_summary"] = rebate_summary
    b["selected_option_tier"] = selected_tier
    b["upsell_added_amount"] = upsell_added
    b["base_job_value"] = base_est_val
    b["quote_options"] = quote_options
    b["final_balance_paid"] = bool(b.get("final_balance_paid", False))

    # Tech In-Truck Tablet Workflow & Diagnostics
    stage = b.get("tech_workflow_stage") or "DISPATCHED"
    if bool(b.get("final_balance_paid", False)):
        stage = "COMPLETED"
    elif b.get("customer_signature_timestamp"):
        stage = "PROPOSAL_APPROVED"
    elif b.get("diagnostic_readings"):
        stage = "ON_SITE_DIAGNOSTIC"
    elif bool(b.get("en_route_sent", False)):
        stage = "EN_ROUTE"

    default_diags = {
        "voltage_l1_l2": "121V / 122V",
        "panel_amps": "150 Amps" if is_emerg else "200 Amps",
        "thermal_hotspot": "138°F (Breaker Lug Scanned)" if is_emerg else "74°F (Normal Ambient)",
        "ground_bond_pass": True,
        "lug_torque": "45 In-Lbs (Torque Spec Verified)",
        "recorded_at": "1:32 PM (On-Site)",
    }
    diags = b.get("diagnostic_readings") or default_diags
    b["tech_workflow_stage"] = stage
    b["diagnostic_readings"] = diags
    b["customer_signature_name"] = b.get("customer_signature_name") or b.get("customer_name", "David Miller")
    b["customer_signature_timestamp"] = b.get("customer_signature_timestamp")

    # 6. Connected Invoicing & FSM Software (ServiceTitan, Housecall Pro, Jobber, QuickBooks)
    from phone_agent.database import format_fsm_ticket_id, format_fsm_metadata
    connected_fsm = str(b.get("connected_fsm") or getattr(DB, "active_fsm_platform", "HOUSECALL_PRO")).strip().upper()
    fsm_tid = str(b.get("fsm_ticket_id") or format_fsm_ticket_id(connected_fsm, b.get("confirmation_id", "1001")))
    fsm_meta = format_fsm_metadata(connected_fsm, b.get("confirmation_id", "1001"))

    b["connected_fsm"] = connected_fsm
    b["fsm_ticket_id"] = fsm_tid
    b["fsm_name"] = fsm_meta["name"]
    b["fsm_icon"] = fsm_meta["icon"]
    b["fsm_badge"] = fsm_meta["badge"]
    b["fsm_url"] = fsm_meta["url"]
    b["fsm_button_label"] = fsm_meta["button_label"]
    b["fsm_tech_label"] = fsm_meta["tech_label"]
    b["fsm_accent_color"] = fsm_meta["accent_color"]
    return b


def render_printable_work_order_html(booking_obj: Any, contractor_email: str) -> str:
    """Renders a dedicated, contractor-grade printable 8.5x11 Field Service Work Order & NFPA 70E Dispatch Sheet."""
    b = enrich_booking_dict(booking_obj)
    conf_id = b.get("confirmation_id", "JL-BOOK-1001")
    is_emerg = "EMERG" in str(b.get("urgency_level", "")).upper() or "emergency" in str(b.get("service_type", "")).lower()
    p_status = b.get("payment_status", "PENDING_AUTHORIZATION")
    is_hold = p_status == "AUTHORIZED_HOLD"
    is_paid = p_status in ("PAID_VERIFIED", "CAPTURED_ON_SITE")
    is_final_paid = bool(b.get("final_balance_paid", False))
    is_manual = "manual" in str(b.get("booked_by", "")).lower()

    title = b.get("display_title", "Electrical Service Dispatch")
    cust_name = b.get("customer_name", "Valued Homeowner")
    cust_phone = b.get("phone_number", "(555) 000-0000")
    cust_addr = b.get("service_address", "Customer Service Address")
    cust_email = b.get("customer_email") or "Confirmed via SMS Dispatch Link"
    access_notes = b.get("notes") or ("Immediate Code Red Dispatch • Gate/Door Unlocked" if is_emerg else "Standard residential service access")

    tech_name = b.get("assigned_technician", "Marcus Vance (Master Electrician)")
    tech_match = b.get("tech_match_reason", "Master Electrician • 24/7 On-Call Lead • Nearest (14m)")
    truck_id = b.get("truck_id", "TRUCK-01 (Master Emergency Van)")
    arrival_win = b.get("display_window", "Today, within 45–60 min")

    created_raw = b.get("created_at", "")
    try:
        dt = datetime.fromisoformat(str(created_raw))
        dispatched_ts = dt.strftime("%b %d, %Y at %I:%M %p EST")
    except Exception:
        dispatched_ts = datetime.now().strftime("%b %d, %Y at %I:%M %p EST")

    symptom = b.get("triage_symptom", "Electrical service request")
    hazard_level = b.get("triage_hazard_level", "Routine Service — Non-Hazardous")
    safety_dir = b.get("triage_safety_instruction", "Isolate affected circuit breaker prior to arrival.")
    nec_load_summary = b.get("nec_load_summary", "NEC 220.82 Load Verified")
    upsell_rec = b.get("upsell_recommendation", "Whole-Home Type 2 Surge Protection (NEC 230.67)")
    permit_info = b.get("permit_info", "Municipal E-Permit Auto-Drafted")
    rebate_summary = b.get("rebate_summary", "IRS Sec. 25C Tax Credit Eligible")
    selected_tier = b.get("selected_option_tier", "GOOD")
    upsell_added = float(b.get("upsell_added_amount", 0.0))
    photo_info = b.get("panel_photo_analysis") or {}
    photo_equip = photo_info.get("equipment_detected", "Square D QO 150A Main Panel")
    photo_breaker = photo_info.get("breaker_spec", "20A Dual-Function AFCI/GFCI")
    fsm_name = b.get("fsm_name", "Housecall Pro")
    fsm_ticket_id = b.get("fsm_ticket_id", f"HCP-{conf_id.split('-')[-1]}")
    photo_status = "✓ AI VISION VERIFIED VIA SMS" if photo_info.get("uploaded") else "📋 PRE-ESTIMATED SPEC (SMS LINK ACTIVE)"

    fee = float(b.get("dispatch_fee", 199.0 if is_emerg else 89.0))
    est_val = float(b.get("estimated_job_value", 1850.0 if is_emerg else 1450.0))
    balance_est = 0.0 if is_final_paid else max(0.0, est_val - (fee if is_paid else 0.0))

    diags = b.get("diagnostic_readings") or {}
    v_l1_l2 = diags.get("voltage_l1_l2", "121V / 122V" if is_emerg else "______ / ______ V")
    p_amps = diags.get("panel_amps", "150 Amps" if is_emerg else "200 Amps")
    t_hotspot = diags.get("thermal_hotspot", "138°F (Breaker Lug)" if is_emerg else "74°F Ambient")
    g_bond = "✓ Pass (0.2Ω Verified)" if diags.get("ground_bond_pass", True) else "Pass / Fail"
    l_torque = diags.get("lug_torque", "45 In-Lbs (NEC 110.14D)" if is_emerg else "_______ In-Lbs")
    sig_ts = b.get("customer_signature_timestamp")

    title_lower = title.lower()
    if is_emerg:
        materials_rows = [
            ("FLIR Thermal Imaging Camera & Non-Contact IR Pyrometer", "1 Unit", "Pre-Arrival Hotspot & Insulation Scan", "Included"),
            ("NFPA 70E Arc-Rated PPE Kit & Class 0 Insulated Gloves", "1 Set", "Live Panel Isolation & Safety Compliance", "Included"),
            ("20A Dual-Function AFCI/GFCI Circuit Breaker (NEMA Spec)", "1–2 Ea", "Faulty Branch Circuit Replacement", " Per Quote"),
            ("20A Commercial Spec-Grade Tamper/Weather Receptacle", "1–2 Ea", "Replace Scorched / Degraded Termination", "Per Quote"),
            ("Megohmmeter 500V/1000V Insulation Resistance Test", "1 Test", "Verify In-Wall Romex Jacket Integrity", "Included"),
        ]
    elif "ev" in title_lower:
        materials_rows = [
            ("50A 2-Pole Thermal-Magnetic Breaker", "1 Ea", "Dedicated 240V EVSE Branch Circuit", "Per Quote"),
            ("#6 AWG Copper THHN / NM-B 6/3 w/ Ground", "35 Ft", "Continuous Duty 40A/48A EV Load Feed", "Per Quote"),
            ("Industrial Grade NEMA 14-50R / Hardwire EVSE Whip", "1 Set", "High-Cycle Torque-Verified Termination", "Per Quote"),
            ("NEC 220.82 Residential Load Calculation Audit", "1 Doc", "200A Main Bus Capacity Certification", "Included"),
            ("Calibrated Torque Wrench Lug Verification", "All Lugs", "NEC 110.14(D) Torque Spec Compliance", "Included"),
        ]
    elif "panel" in title_lower:
        materials_rows = [
            ("200A Copper Bus Main Breaker Loadcenter (40-Space)", "1 Unit", "Primary Service Distribution Upgrade", "Per Quote"),
            ("Whole-Home Type 1/2 Surge Protective Device (SPD)", "1 Unit", "NEC 230.67 Mandatory Surge Protection", "Per Quote"),
            ("#4 AWG Bare Copper GEC & Dual Ground Rod Clamps", "1 Lot", "NEC 250 Grounding & Bonding Verification", "Per Quote"),
            ("Branch Circuit Labeling & Phase Load Balancing", "Full Panel", "Eliminate L1/L2 Voltage Drop & Flicker", "Included"),
            ("Infrared Thermal & Torque Spec Commissioning", "All Lugs", "Final Municipal Inspection Sign-Off", "Included"),
        ]
    else:
        materials_rows = [
            ("True-RMS Digital Multimeter & Circuit Tracer", "1 Kit", "Branch Circuit Fault Isolation", "Included"),
            ("20A Dual-Function AFCI/GFCI Circuit Breaker", "1 Ea", "NEC Code-Compliant Protection", "Per Quote"),
            ("Spec-Grade Wiring Devices & Wago/Buchanan Splice Kit", "1 Lot", "High-Resistance Connection Remediation", "Per Quote"),
            ("Panel Schedule & Voltage Drop Load Test", "1 Test", "Verify < 3% Branch Voltage Drop", "Included"),
        ]

    materials_html = "".join(
        f"""
        <tr>
          <td><span class="chk-box"></span> <strong>{item}</strong></td>
          <td>{qty}</td>
          <td>{purpose}</td>
          <td style="text-align:right; font-weight:700;">{price_note}</td>
        </tr>
        """
        for item, qty, purpose, price_note in materials_rows
    )

    priority_banner_color = "#991b1b" if is_emerg else "#0f172a"
    priority_label = "🚨 PRIORITY CODE RED — EMERGENCY FIELD WORK ORDER" if is_emerg else "⚡ OFFICIAL FIELD SERVICE WORK ORDER & DISPATCH SHEET"
    source_tag = "Manual Dispatcher Entry" if is_manual else "Autonomous AI Triage & Dispatch (Sarah AI)"
    pay_badge_html = (
        f'<span class="wo-badge badge-paid">✓ ${fee:,.2f} CAPTURED ON-SITE (STRIPE)</span>'
        if is_paid
        else (
            f'<span class="wo-badge" style="background:#dbeafe; color:#1e40af; border:1px solid #93c5fd; font-weight:800; font-size:12px; padding:4px 10px; border-radius:6px;">⏳ ${fee:,.2f} PRE-AUTH HOLD ACTIVE (CARD NOT CHARGED)</span>'
            if is_hold
            else f'<span class="wo-badge badge-pending">⏳ ${fee:,.2f} DEPOSIT PENDING AUTHORIZATION</span>'
        )
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Work Order #{conf_id} — {cust_name} | JobLatch AI Electrical</title>
  <link rel="icon" type="image/jpeg" href="/assets/joblatch_ai_logo.jpg">
  <style>
    @page {{
      size: letter portrait;
      margin: 0.4in;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
      background: #e2e8f0;
      color: #0f172a;
      font-size: 12px;
      line-height: 1.4;
      padding: 24px 16px;
    }}
    .print-toolbar {{
      max-width: 820px;
      margin: 0 auto 16px;
      background: #0f172a;
      color: #ffffff;
      padding: 12px 20px;
      border-radius: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.2);
    }}
    .toolbar-btn {{
      background: #2563eb;
      color: #ffffff;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 800;
      font-size: 13px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .toolbar-btn.secondary {{
      background: #334155;
    }}
    .sheet {{
      max-width: 820px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
      padding: 28px 32px;
    }}
    .letterhead {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 3px solid {priority_banner_color};
      padding-bottom: 14px;
      margin-bottom: 12px;
    }}
    .shop-brand {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }}
    .shop-logo {{
      width: 46px;
      height: 46px;
      background: #0b1329;
      color: #ffffff;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border: 1.5px solid rgba(56, 189, 248, 0.4);
      flex-shrink: 0;
    }}
    .shop-logo img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .shop-name {{
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -0.02em;
      color: #0f172a;
    }}
    .shop-meta {{
      font-size: 11px;
      color: #475569;
      font-weight: 600;
      margin-top: 2px;
    }}
    .wo-box {{
      text-align: right;
    }}
    .wo-type-pill {{
      display: inline-block;
      background: {priority_banner_color};
      color: #ffffff;
      font-size: 10px;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 4px;
      white-space: nowrap;
    }}
    .wo-number {{
      font-size: 20px;
      font-weight: 900;
      color: #0f172a;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    .wo-timestamp {{
      font-size: 11px;
      color: #475569;
      font-weight: 600;
    }}
    .meta-strip {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 8px 12px;
      margin-bottom: 12px;
      font-size: 11px;
      font-weight: 700;
    }}
    .wo-badge {{
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 800;
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .badge-paid {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
    .badge-pending {{ background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 12px;
    }}
    .panel {{
      border: 1px solid #94a3b8;
      border-radius: 6px;
      overflow: hidden;
    }}
    .panel-head {{
      background: #f1f5f9;
      border-bottom: 1px solid #94a3b8;
      padding: 6px 10px;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #1e293b;
      display: flex;
      justify-content: space-between;
      align-items: center;
      white-space: nowrap;
      gap: 6px;
    }}
    .panel-body {{
      padding: 8px 10px;
    }}
    .kv {{
      display: flex;
      justify-content: space-between;
      padding: 3px 0;
      border-bottom: 1px dotted #e2e8f0;
      font-size: 11.5px;
    }}
    .kv:last-child {{ border-bottom: none; }}
    .kv-k {{ color: #475569; font-weight: 600; }}
    .kv-v {{ color: #0f172a; font-weight: 800; text-align: right; max-width: 65%; }}
    .triage-section {{
      border: 1.5px solid {"#dc2626" if is_emerg else "#2563eb"};
      background: {"#fff1f2" if is_emerg else "#eff6ff"};
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 14px;
    }}
    .triage-head {{
      font-size: 11px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: {"#991b1b" if is_emerg else "#1e3a8a"};
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }}
    .triage-grid {{
      display: grid;
      grid-template-columns: 145px 1fr;
      gap: 4px 10px;
      font-size: 11.5px;
    }}
    .tbl {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 14px;
      font-size: 11.5px;
    }}
    .tbl th {{
      background: #0f172a;
      color: #ffffff;
      text-align: left;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 6px 8px;
      border: 1px solid #0f172a;
    }}
    .tbl td {{
      padding: 6px 8px;
      border: 1px solid #cbd5e1;
      vertical-align: middle;
    }}
    .chk-box {{
      display: inline-block;
      width: 11px;
      height: 11px;
      border: 1.5px solid #0f172a;
      border-radius: 2px;
      margin-right: 5px;
      vertical-align: -1px;
    }}
    .diag-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 8px;
      margin-bottom: 14px;
    }}
    .diag-cell {{
      border: 1px solid #94a3b8;
      border-radius: 5px;
      padding: 6px 8px;
      background: #f8fafc;
    }}
    .diag-label {{
      font-size: 9.5px;
      font-weight: 800;
      text-transform: uppercase;
      color: #475569;
      margin-bottom: 8px;
    }}
    .diag-blank {{
      border-bottom: 1px solid #475569;
      height: 16px;
      font-size: 11px;
      font-weight: 700;
      color: #64748b;
      text-align: right;
    }}
    .sign-box {{
      border: 1px solid #94a3b8;
      border-radius: 6px;
      padding: 10px 12px;
      background: #f8fafc;
    }}
    .sign-terms {{
      font-size: 10px;
      color: #334155;
      line-height: 1.35;
      margin-bottom: 16px;
    }}
    .sign-lines {{
      display: grid;
      grid-template-columns: 2fr 1fr 2fr 1fr;
      gap: 14px;
      align-items: end;
    }}
    .sign-line {{
      border-top: 1.5px solid #0f172a;
      padding-top: 3px;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      color: #334155;
    }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .print-toolbar {{ display: none !important; }}
      .sheet {{ box-shadow: none; border: none; padding: 0; max-width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="print-toolbar">
    <div>
      <strong style="font-size:14px;">🖨️ Official Contractor Field Work Order (#{conf_id})</strong>
      <span style="font-size:12px; color:#cbd5e1; margin-left:10px;">Formatted for 8.5&quot; &times; 11&quot; Print or Save as PDF</span>
    </div>
    <div style="display:flex; gap:8px;">
      <button class="toolbar-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
      <button class="toolbar-btn secondary" onclick="window.close()">✕ Close Window</button>
    </div>
  </div>

  <div class="sheet">
    <!-- 1. CONTRACTOR LETTERHEAD -->
    <div class="letterhead">
      <div class="shop-brand">
        <div class="shop-logo">
          <img src="/assets/joblatch_ai_logo.jpg" alt="JobLatch AI" onerror="this.onerror=null; this.parentElement.innerHTML='⚡';">
        </div>
        <div>
          <div class="shop-name">APEX ELECTRICAL SERVICES &bull; JOBLATCH AI DISPATCH</div>
          <div class="shop-meta">
            Master Electrical License #EL-49201-MA &bull; NFPA 70E &amp; NEC 2026 Certified Contractor<br>
            24/7 Emergency Dispatch Control: (800) 555-LATCH &bull; Shop Dispatch Alert: {contractor_email}
          </div>
        </div>
      </div>
      <div class="wo-box">
        <div class="wo-type-pill">{priority_label}</div>
        <div class="wo-number">WO #{conf_id}</div>
        <div class="wo-timestamp">Dispatched: {dispatched_ts}</div>
      </div>
    </div>

    <!-- 2. SUMMARY STRIP -->
    <div class="meta-strip">
      <span>📋 <strong>Primary Scope:</strong> {title}</span>
      <span>🔌 <strong>Connected Invoicing App:</strong> {fsm_name} (#{fsm_ticket_id})</span>
      <span>🤖 <strong>Intake Source:</strong> {source_tag}</span>
      {pay_badge_html}
    </div>

    <!-- 3. CUSTOMER SITE RECORD & ASSIGNED FLEET ELECTRICIAN -->
    <div class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <span>👤 Customer &amp; Site Location Record</span>
          <span style="color:#15803d;">✓ SMS Confirmed</span>
        </div>
        <div class="panel-body">
          <div class="kv"><span class="kv-k">Customer / Contact:</span><span class="kv-v">{cust_name}</span></div>
          <div class="kv"><span class="kv-k">Callback Phone:</span><span class="kv-v">{cust_phone}</span></div>
          <div class="kv"><span class="kv-k">Service Address:</span><span class="kv-v">{cust_addr}</span></div>
          <div class="kv"><span class="kv-k">Notification / Email:</span><span class="kv-v">{cust_email}</span></div>
          <div class="kv"><span class="kv-k">Site Access &amp; Gate Notes:</span><span class="kv-v">{access_notes}</span></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <span>👷 Fleet Assignment &amp; Arrival Window</span>
          <span style="color:#1d4ed8;">📅 GCal Synced ✓</span>
        </div>
        <div class="panel-body">
          <div class="kv"><span class="kv-k">Assigned Electrician:</span><span class="kv-v">{tech_name}</span></div>
          <div class="kv"><span class="kv-k">Dispatch Match Logic:</span><span class="kv-v">{tech_match}</span></div>
          <div class="kv"><span class="kv-k">Scheduled Window:</span><span class="kv-v">{arrival_win}</span></div>
          <div class="kv"><span class="kv-k">Dispatch Status:</span><span class="kv-v">{"DISPATCHED CODE RED (45–60M ETA)" if is_emerg else "CONFIRMED ON FLEET SCHEDULE"}</span></div>
          <div class="kv"><span class="kv-k">Truck / Route ID:</span><span class="kv-v">🚐 {truck_id} &bull; GPS Active</span></div>
        </div>
      </div>
    </div>

    <!-- 4. AI TECHNICAL TRIAGE, PANEL PHOTO AUDIT & NEC 220.82 LOAD VERIFICATION -->
    <div class="triage-section">
      <div class="triage-head">
        <span>{"🚨 NFPA 70E EMERGENCY HAZARD TRIAGE & LIFE-SAFETY RECORD" if is_emerg else "🛡️ AI TECHNICAL TRIAGE & PRE-ARRIVAL LOAD VERIFICATION"}</span>
        <span>{photo_status}</span>
      </div>
      <div class="triage-grid">
        <strong style="color:#475569;">Reported Symptom:</strong>
        <strong style="color:#0f172a;">{symptom}</strong>
        <strong style="color:#475569;">Hazard Classification:</strong>
        <strong style="color:{"#991b1b" if is_emerg else "#1e3a8a"};">{hazard_level}</strong>
        <strong style="color:#475569;">Safety Directive Issued:</strong>
        <span style="font-weight:600; color:#1e293b;">{safety_dir}</span>
        <strong style="color:#475569;">📸 Panel / Breaker Spec:</strong>
        <span style="font-weight:700; color:#0f172a;">{photo_equip} &bull; {photo_breaker}</span>
        <strong style="color:#475569;">⚡ NEC 220.82 Load Audit:</strong>
        <span style="font-weight:700; color:#1e3a8a;">{nec_load_summary}</span>
        <strong style="color:#475569;">🏛️ Municipal E-Permit:</strong>
        <span style="font-weight:700; color:#0f172a;">{permit_info}</span>
        <strong style="color:#475569;">💰 Customer Rebate / 25C:</strong>
        <span style="font-weight:800; color:#15803d;">{rebate_summary}</span>
        <strong style="color:#475569;">💡 Pre-Qualified Upsell:</strong>
        <span style="font-weight:800; color:#15803d;">{upsell_rec}</span>
      </div>
    </div>

    <!-- 5. FIELD TECHNICIAN SCOPE, TRUCK STOCK & NEC CHECKLIST -->
    <table class="tbl">
      <thead>
        <tr>
          <th style="width:44%;">Field Procedure / Truck Stock Material Item</th>
          <th style="width:12%;">Qty / Spec</th>
          <th style="width:30%;">NEC / NFPA 70E Inspection Purpose</th>
          <th style="width:14%; text-align:right;">Billing Basis</th>
        </tr>
      </thead>
      <tbody>
        {materials_html}
      </tbody>
    </table>

    <!-- 6. ON-SITE ELECTRICAL DIAGNOSTIC & COMMISSIONING LOG (FOR FIELD TECH) -->
    <div style="font-size:10px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; color:#334155; margin-bottom:5px;">
      🔬 On-Site Electrical Diagnostic &amp; Commissioning Readings (To Be Completed by Field Electrician)
    </div>
    <div class="diag-grid">
      <div class="diag-cell">
        <div class="diag-label">Supply Voltage (L1/L2)</div>
        <div class="diag-blank" style="color:#0f172a; font-weight:700;">{v_l1_l2}</div>
      </div>
      <div class="diag-cell">
        <div class="diag-label">Main Panel Rating</div>
        <div class="diag-blank" style="color:#0f172a; font-weight:700;">{p_amps}</div>
      </div>
      <div class="diag-cell">
        <div class="diag-label">IR Thermal Hotspot</div>
        <div class="diag-blank" style="color:{"#b91c1c" if is_emerg else "#0f172a"}; font-weight:700;">{t_hotspot}</div>
      </div>
      <div class="diag-cell">
        <div class="diag-label">Ground / Neutral Bond</div>
        <div class="diag-blank" style="color:#15803d; font-weight:700;">{g_bond}</div>
      </div>
      <div class="diag-cell">
        <div class="diag-label">Lug Torque Verified</div>
        <div class="diag-blank" style="color:#0f172a; font-weight:700;">{l_torque}</div>
      </div>
    </div>

    <!-- 7. FINANCIAL ESTIMATE & UPFRONT STRIPE DEPOSIT LEDGER -->
    <table class="tbl" style="margin-bottom:14px;">
      <thead>
        <tr>
          <th style="width:52%;">Financial Summary &amp; Deposit Ledger</th>
          <th style="width:28%;">Payment / Escrow Status</th>
          <th style="width:20%; text-align:right;">Amount (USD)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <strong>Upfront Dispatch &amp; Diagnostic Fee (2-Step Stripe Authorization Hold)</strong>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">
              {"PaymentIntent: " + (b.get("stripe_payment_intent_id") or "pi_hold_...") + " • capture_method=manual (7-Day Hold) • Dest: " + (b.get("stripe_connect_account_id") or "acct_apex_electric_101")}
            </div>
          </td>
          <td style="font-weight:800; color:{"#15803d" if (is_paid or is_final_paid) else ("#2563eb" if is_hold else "#b45309")};">
            {"✓ CAPTURED & SETTLED ON-SITE" if (is_paid or is_final_paid) else ("⏳ 7-DAY PRE-AUTH HOLD ACTIVE (CARD NOT CHARGED)" if is_hold else "⏳ PENDING AUTHORIZATION HOLD")}
          </td>
          <td style="text-align:right; font-weight:800;">${fee:,.2f}</td>
        </tr>
        <tr>
          <td>
            <strong>Electrical Scope &amp; Materials:</strong> {title}
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Billed using contractor's native {fsm_name} price book &amp; on-site tech authorization.</div>
          </td>
          <td style="color:{"#15803d" if is_final_paid else "#475569"}; font-weight:700;">
            {"✓ FINAL INVOICE PAID IN FULL" if is_final_paid else f"Synced to {fsm_name} • Work Order #{fsm_ticket_id}"}
          </td>
          <td style="text-align:right; font-weight:800;">${est_val:,.2f}</td>
        </tr>
        <tr style="background:#f8fafc;">
          <td colspan="2" style="text-align:right; font-weight:900; text-transform:uppercase; color:{"#15803d" if is_final_paid else "#0f172a"};">
            {"✓ PAID IN FULL VIA STRIPE — REMAINING BALANCE DUE:" if is_final_paid else f"Estimated Balance Billed via {fsm_name} (After ${fee:,.0f} Paid Deposit Credit):"}
          </td>
          <td style="text-align:right; font-size:13px; font-weight:900; color:{"#15803d" if is_final_paid else "#0f172a"};">${balance_est:,.2f}</td>
        </tr>
      </tbody>
    </table>

    <!-- 8. CUSTOMER WORK AUTHORIZATION & NEC COMPLIANCE SIGN-OFF -->
    <div class="sign-box">
      <div class="sign-terms">
        <strong>WORK AUTHORIZATION &amp; SAFETY ACKNOWLEDGMENT:</strong> I hereby authorize Apex Electrical Services to perform the diagnostic inspection and electrical scope described above. All work is performed in strict accordance with the National Electrical Code (NFPA 70) and NFPA 70E workplace electrical safety standards. The upfront dispatch deposit is applied toward approved repairs.
      </div>
      <div class="sign-lines">
        <div class="sign-line" style="color:{"#15803d" if sig_ts else "#475569"}; font-weight:{"800" if sig_ts else "600"};">
          {"✓ Digitally Signed by " + cust_name if sig_ts else f"Customer / Authorized Signature ({cust_name})"}
        </div>
        <div class="sign-line" style="color:#1e293b; font-weight:600;">
          {sig_ts if sig_ts else "Date / Time"}
        </div>
        <div class="sign-line">Lead Electrician Sign-Off ({tech_name.split('(')[0].strip()})</div>
        <div class="sign-line">License #EL-49201-MA</div>
      </div>
    </div>
  </div>

  <script>
    const params = new URLSearchParams(window.location.search);
    if (params.get('autoprint') === '1') {{
      window.addEventListener('load', () => {{
        setTimeout(() => window.print(), 350);
      }});
    }}
  </script>
</body>
</html>
"""


HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JobLatch AI Voice Dispatch | Interactive Product Demo</title>
  <link rel="icon" type="image/jpeg" href="/assets/joblatch_ai_logo.jpg">
  <style>
    :root {
      --bg: #f1f5f9;
      --surface: #ffffff;
      --surface-muted: #f8fafc;
      --border: #cbd5e1;
      --border-strong: #94a3b8;
      --navy: #0f172a;
      --text-main: #0f172a;
      --text-body: #1e293b;
      --text-muted: #475569;
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --primary-soft: #eff6ff;
      --success: #16a34a;
      --success-soft: #dcfce7;
      --success-text: #15803d;
      --warning: #d97706;
      --warning-soft: #fef3c7;
      --warning-text: #b45309;
      --danger: #dc2626;
      --danger-soft: #fee2e2;
      --danger-text: #b91c1c;
      --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.06);
      --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
      --shadow-lg: 0 12px 28px rgba(15, 23, 42, 0.12);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      font-size: 17px;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }

    /* TOP HEADER BAR */
    header {
      background: var(--navy);
      color: #ffffff;
      padding: 16px 36px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .brand-icon {
      background: #0b1329;
      color: white;
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border: 1.5px solid rgba(56, 189, 248, 0.45);
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.25);
      flex-shrink: 0;
    }
    .brand-icon img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .brand-title-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 1.4rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
    }
    .demo-mode-pill {
      background: #f59e0b;
      color: #0f172a;
      font-size: 0.8rem;
      font-weight: 800;
      padding: 4px 12px;
      border-radius: 999px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .brand p {
      font-size: 0.95rem;
      color: #cbd5e1;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .nav-tabs {
      display: flex;
      background: rgba(255, 255, 255, 0.09);
      padding: 4px;
      border-radius: 10px;
      gap: 4px;
    }
    .nav-tab {
      background: transparent;
      border: none;
      color: #e2e8f0;
      padding: 9px 16px;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .nav-tab:hover { color: #ffffff; background: rgba(255, 255, 255, 0.08); }
    .nav-tab.active {
      background: #2563eb;
      color: #ffffff;
    }
    .nav-count {
      background: rgba(255, 255, 255, 0.22);
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 800;
    }

    .utility-btn {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.22);
      color: #f8fafc;
      padding: 9px 15px;
      border-radius: 8px;
      font-size: 0.92rem;
      font-weight: 700;
      cursor: pointer;
    }
    .utility-btn:hover { background: rgba(255, 255, 255, 0.18); }

    /* FSM & INVOICING APP SWITCHER BAR */
    .fsm-switch-container {
      display: flex;
      align-items: center;
      gap: 7px;
      background: rgba(15, 23, 42, 0.55);
      border: 1px solid rgba(255, 255, 255, 0.22);
      border-radius: 9px;
      padding: 4px 10px;
    }
    .fsm-label {
      font-size: 0.8rem;
      font-weight: 700;
      color: #94a3b8;
      white-space: nowrap;
    }
    .fsm-select {
      background: #0f172a;
      color: #f8fafc;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 0.86rem;
      font-weight: 800;
      cursor: pointer;
    }
    .fsm-select:focus {
      outline: none;
      border-color: #38bdf8;
    }
    .fsm-payload-btn {
      background: rgba(56, 189, 248, 0.16);
      border: 1px solid rgba(56, 189, 248, 0.38);
      color: #38bdf8;
      padding: 6px 11px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .fsm-payload-btn:hover {
      background: rgba(56, 189, 248, 0.3);
    }

    /* MAIN CONTAINER — WIDENED TO 1400PX FOR SCREEN-SHARING */
    main {
      max-width: 1400px;
      width: 96%;
      margin: 0 auto;
      padding: 22px 16px 36px;
      flex: 1;
    }
    .tab-view { display: none; }
    .tab-view.active { display: block; }

    /* VISUAL BACKBONE: 4-STEP END-TO-END STORY BAR */
    .story-backbone {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 24px;
      margin-bottom: 22px;
      box-shadow: var(--shadow-sm);
    }
    .backbone-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .backbone-label {
      font-size: 0.92rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .next-step-banner {
      background: #eff6ff;
      border: 2px solid #93c5fd;
      color: #1e3a8a;
      padding: 8px 16px;
      border-radius: 10px;
      font-size: 1rem;
      font-weight: 600;
    }
    .next-step-banner strong { font-weight: 800; }

    .journey-steps {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }
    @media (max-width: 960px) {
      .journey-steps { grid-template-columns: repeat(2, 1fr); }
    }
    .j-step {
      background: var(--surface-muted);
      border: 2px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .j-step.active-step {
      background: #eff6ff;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
    }
    .j-step.done-step {
      background: #f0fdf4;
      border-color: #16a34a;
    }
    .j-num {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: #cbd5e1;
      color: #0f172a;
      font-weight: 800;
      font-size: 0.98rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .j-step.active-step .j-num { background: #2563eb; color: #ffffff; }
    .j-step.done-step .j-num { background: #16a34a; color: #ffffff; }
    .j-title { font-size: 1.02rem; font-weight: 800; color: var(--text-main); line-height: 1.25; }
    .j-desc { font-size: 0.92rem; color: var(--text-body); margin-top: 3px; font-weight: 500; }

    /* PRIMARY WORKSPACE GRID */
    .demo-stage-grid {
      display: grid;
      grid-template-columns: 490px 1fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
    }
    @media (max-width: 1180px) {
      .demo-stage-grid { grid-template-columns: 1fr; }
    }

    /* DYNAMIC FOCUS HIGHLIGHT RING (MOVES TO WHICHEVER PANEL NEEDS ATTENTION) */
    .panel-card {
      background: var(--surface);
      border: 2px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: var(--shadow-sm);
    }
    .panel-card.active-focus-panel {
      border-color: var(--primary);
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14), var(--shadow-md);
    }

    /* LEFT: SIMULATOR CARD (STRETCHES FULL HEIGHT WITH ZERO DEAD SPACE) */
    .primary-simulator-card {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .sim-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 14px;
    }
    .step-status-pill {
      display: inline-block;
      background: #2563eb;
      color: white;
      font-size: 0.8rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 4px 11px;
      border-radius: 6px;
      margin-bottom: 6px;
    }
    .step-status-pill.quiet-pill {
      background: #e2e8f0;
      color: #334155;
    }
    .sim-header h2 {
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--text-main);
    }

    /* HERO ACTION BUTTON */
    .btn-hero-start {
      width: 100%;
      background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
      color: #ffffff;
      border: none;
      border-radius: 12px;
      padding: 16px 20px;
      text-align: left;
      cursor: pointer;
      box-shadow: 0 6px 16px rgba(37, 99, 235, 0.25);
      margin-bottom: 12px;
      transition: transform 0.12s, box-shadow 0.12s;
    }
    .btn-hero-start:hover {
      transform: translateY(-1px);
      box-shadow: 0 8px 22px rgba(37, 99, 235, 0.35);
    }
    .hero-btn-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 1.1rem;
      font-weight: 800;
      margin-bottom: 4px;
    }
    .hero-btn-sub {
      font-size: 0.94rem;
      color: #dbeafe;
      font-weight: 500;
    }

    /* SECONDARY SCENARIOS */
    .secondary-scenarios {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 14px;
    }
    .btn-sec-scenario {
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      color: var(--text-body);
      padding: 11px 12px;
      border-radius: 10px;
      font-size: 0.94rem;
      font-weight: 700;
      cursor: pointer;
      text-align: center;
    }
    .btn-sec-scenario:hover { background: #e2e8f0; }
    .btn-sec-emerg {
      background: #fff1f2;
      border-color: #fda4af;
      color: #be123c;
    }
    .btn-sec-emerg:hover { background: #ffe4e6; }

    /* FIRST-CLASS VOICE CONTROL & SPEAKING WAVEFORM BAR */
    .voice-primary-bar {
      background: #0f172a;
      color: #ffffff;
      border-radius: 12px;
      padding: 12px 16px;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .voice-status-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .waveform-bars {
      display: flex;
      align-items: center;
      gap: 3px;
      height: 22px;
    }
    .waveform-bars span {
      display: block;
      width: 4px;
      height: 6px;
      background: #38bdf8;
      border-radius: 999px;
      transition: height 0.15s ease;
    }
    .waveform-bars.active-wave span:nth-child(1) { animation: waveBounce 0.55s infinite ease-in-out 0.0s; }
    .waveform-bars.active-wave span:nth-child(2) { animation: waveBounce 0.55s infinite ease-in-out 0.12s; }
    .waveform-bars.active-wave span:nth-child(3) { animation: waveBounce 0.55s infinite ease-in-out 0.24s; }
    .waveform-bars.active-wave span:nth-child(4) { animation: waveBounce 0.55s infinite ease-in-out 0.12s; }
    .waveform-bars.active-wave span:nth-child(5) { animation: waveBounce 0.55s infinite ease-in-out 0.0s; }
    @keyframes waveBounce {
      0%, 100% { height: 6px; background: #38bdf8; }
      50% { height: 22px; background: #4ade80; }
    }
    .voice-state-label {
      font-size: 0.94rem;
      font-weight: 700;
      color: #f8fafc;
    }
    .voice-state-sub {
      font-size: 0.82rem;
      color: #94a3b8;
    }
    .btn-voice-primary {
      background: #2563eb;
      color: #ffffff;
      border: 1px solid #60a5fa;
      padding: 9px 16px;
      border-radius: 9px;
      font-size: 0.94rem;
      font-weight: 800;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 7px;
      white-space: nowrap;
    }
    .btn-voice-primary:hover { background: #1d4ed8; }
    .btn-voice-primary.listening {
      background: #dc2626;
      border-color: #fca5a5;
    }

    /* LIVE CALL TRANSCRIPT — FILLS REMAINING CARD HEIGHT WITH ZERO DEAD SPACE */
    .transcript-label {
      font-size: 0.86rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .chat-container {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      flex: 1 1 auto;
      min-height: 300px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 12px;
    }
    .bubble {
      padding: 13px 16px;
      border-radius: 12px;
      font-size: 1rem;
      line-height: 1.5;
      max-width: 94%;
    }
    .bubble-sarah {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e3a8a;
      align-self: flex-start;
    }
    .bubble-user {
      background: #0f172a;
      color: #ffffff;
      align-self: flex-end;
    }
    .speaker-name {
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 4px;
      opacity: 0.88;
    }

    .input-row {
      display: flex;
      gap: 8px;
      margin-top: auto;
    }
    .input-row input {
      flex: 1;
      border: 1px solid var(--border-strong);
      border-radius: 10px;
      padding: 11px 14px;
      font-size: 0.98rem;
      color: var(--text-main);
    }
    .input-row input:focus { outline: 2px solid var(--primary); border-color: transparent; }
    .btn-send {
      background: var(--navy);
      color: white;
      border: none;
      border-radius: 10px;
      padding: 0 20px;
      font-weight: 800;
      font-size: 0.96rem;
      cursor: pointer;
    }

    /* RIGHT: LIVE RESULTS STAGE (PHONE + DISPATCH TICKET) */
    .outcomes-stage {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .outcomes-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 10px;
    }
    .outcomes-header h2 {
      font-size: 1.3rem;
      font-weight: 800;
      color: var(--text-main);
    }

    .outcomes-split {
      display: grid;
      grid-template-columns: 350px 1fr;
      gap: 24px;
      align-items: stretch;
      flex: 1;
    }
    @media (max-width: 980px) {
      .outcomes-split { grid-template-columns: 1fr; }
    }

    /* CUSTOMER PHONE SIMULATOR — LARGER & CLEARER TEXT */
    .phone-column-wrap {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .phone-chassis {
      width: 350px;
      background: #0f172a;
      border-radius: 34px;
      padding: 11px;
      box-shadow: var(--shadow-md);
      border: 3px solid #334155;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
    .phone-chassis.highlight-phone {
      border-color: #2563eb;
      box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.25), var(--shadow-lg);
    }
    .phone-screen {
      background: #0f172a;
      border-radius: 24px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 520px;
      border: 1px solid #1e293b;
    }
    .phone-dynamic-island {
      width: 84px;
      height: 18px;
      background: #020617;
      border-radius: 999px;
      margin: 8px auto 4px;
    }
    .phone-status-bar {
      display: flex;
      justify-content: space-between;
      padding: 2px 18px 8px;
      font-size: 0.85rem;
      font-weight: 700;
      color: #e2e8f0;
    }
    .phone-imessage-header {
      background: #1e293b;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid #334155;
    }
    .imessage-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: #0b1329;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border: 1.5px solid rgba(56, 189, 248, 0.5);
      font-weight: 800;
      font-size: 0.95rem;
      flex-shrink: 0;
    }
    .imessage-avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .imessage-name { font-size: 1rem; font-weight: 800; color: #ffffff; }
    .imessage-sub { font-size: 0.86rem; color: #cbd5e1; }

    .phone-messages {
      padding: 16px;
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .sms-bubble {
      background: #1e293b;
      border: 1px solid #475569;
      border-radius: 14px;
      padding: 15px;
      color: #f8fafc;
      font-size: 0.98rem;
      line-height: 1.5;
    }
    .sms-tag {
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
      color: #60a5fa;
      margin-bottom: 6px;
      letter-spacing: 0.03em;
    }
    .sms-action-card {
      margin-top: 12px;
      background: rgba(37, 99, 235, 0.2);
      border: 2px solid #60a5fa;
      border-radius: 12px;
      padding: 14px;
      cursor: pointer;
    }
    .btn-action-claim {
      margin-top: 10px;
      width: 100%;
      background: #2563eb;
      color: white;
      border: none;
      padding: 12px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 0.96rem;
      cursor: pointer;
    }
    .btn-action-claim:hover { background: #1d4ed8; }

    .sms-stripe-sheet {
      margin-top: 12px;
      background: #0f172a;
      border: 2px solid #6366f1;
      border-radius: 12px;
      padding: 14px;
    }
    .btn-stripe-pay {
      margin-top: 10px;
      width: 100%;
      background: #4f46e5;
      color: white;
      border: none;
      padding: 12px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 0.96rem;
      cursor: pointer;
    }
    .btn-stripe-pay:hover { background: #4338ca; }
    .btn-stripe-pay.paid {
      background: #16a34a;
      cursor: default;
    }
    .recoup-won-badge {
      background: #16a34a;
      color: white;
      font-size: 0.88rem;
      font-weight: 800;
      padding: 8px 12px;
      border-radius: 8px;
      text-align: center;
    }
    .phone-home-bar {
      width: 100px;
      height: 4px;
      background: #475569;
      border-radius: 999px;
      margin: 8px auto 10px;
    }

    /* DEVICE VIEW SWITCHER (CUSTOMER PHONE VS IN-TRUCK TABLET) */
    .device-switch-bar {
      display: flex;
      background: #e2e8f0;
      padding: 4px;
      border-radius: 12px;
      margin-bottom: 12px;
      gap: 6px;
    }
    .device-tab-btn {
      flex: 1;
      background: transparent;
      border: none;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.88rem;
      font-weight: 800;
      color: #475569;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .device-tab-btn.active {
      background: #0f172a;
      color: #ffffff;
      box-shadow: var(--shadow-sm);
    }
    .device-tab-btn:hover:not(.active) {
      background: #cbd5e1;
      color: #0f172a;
    }

    /* RUGGED IN-TRUCK TABLET STYLING */
    .phone-chassis.tech-tablet-mode {
      background: #020617;
      border: 5px solid #334155;
      border-radius: 26px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.25), inset 0 0 0 2px #475569;
    }
    .tech-top-bar {
      background: #1e293b;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1.5px solid #334155;
    }
    .tech-body-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .tech-card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 11px;
    }
    .tech-card-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 6px;
      color: #cbd5e1;
    }
    .tech-btn {
      border: none;
      border-radius: 6px;
      padding: 7px 10px;
      color: #ffffff;
      font-size: 0.78rem;
      font-weight: 800;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      transition: filter 0.15s ease;
    }
    .tech-btn:hover { filter: brightness(1.1); }
    .tech-field-input {
      width: 100%;
      background: #0f172a;
      border: 1px solid #475569;
      border-radius: 5px;
      color: #f8fafc;
      font-size: 0.76rem;
      font-weight: 700;
      padding: 4px 6px;
      margin-top: 2px;
    }

    /* CONTRACTOR DISPATCH TICKET COLUMN */
    .cockpit-column {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .waiting-quiet-box {
      border: 2px dashed #cbd5e1;
      border-radius: 14px;
      padding: 36px 26px;
      text-align: center;
      background: var(--surface-muted);
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .waiting-icon {
      font-size: 2.4rem;
      margin-bottom: 12px;
    }
    .waiting-quiet-box h3 {
      font-size: 1.2rem;
      font-weight: 800;
      color: var(--text-main);
      margin-bottom: 8px;
    }
    .waiting-quiet-box p {
      font-size: 1rem;
      color: var(--text-body);
      max-width: 400px;
      margin-bottom: 18px;
    }
    .quiet-checklist {
      text-align: left;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 20px;
      font-size: 0.96rem;
      color: var(--text-body);
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 100%;
      max-width: 420px;
    }

    /* ACTIVE DISPATCH TICKET */
    .dispatch-hero {
      display: none;
      background: var(--surface);
      border: 2px solid #2563eb;
      border-radius: 14px;
      padding: 22px;
      box-shadow: var(--shadow-md);
      flex: 1;
    }
    .dispatch-hero.active { display: flex; flex-direction: column; }
    .dispatch-hero.is-emergency { border-color: #dc2626; }
    .hero-badge {
      display: inline-block;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 0.84rem;
      font-weight: 800;
      text-transform: uppercase;
    }
    .badge-standard { background: #dcfce7; color: #15803d; }
    .badge-emergency { background: #fee2e2; color: #b91c1c; }
    .hero-title { font-size: 1.35rem; font-weight: 800; margin: 8px 0 4px; color: var(--text-main); }
    .hero-subtitle { font-size: 0.96rem; color: var(--text-muted); margin-bottom: 14px; }

    /* CREDIBILITY MOMENT: AI HAZARD & TRIAGE VERIFICATION BOX */
    .triage-credibility-box {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-left: 5px solid #2563eb;
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .triage-credibility-box.is-emerg-triage {
      background: #fff1f2;
      border-color: #fecdd3;
      border-left: 5px solid #dc2626;
    }
    .triage-box-header {
      font-size: 0.84rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #1e293b;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .triage-credibility-box.is-emerg-triage .triage-box-header {
      color: #991b1b;
    }
    .triage-detail-row {
      font-size: 0.95rem;
      color: #0f172a;
      line-height: 1.45;
    }
    .triage-detail-row strong {
      color: #1e293b;
      font-weight: 800;
    }

    .ticket-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.98rem;
      margin-top: 6px;
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
    }
    .ticket-table tr { border-bottom: 1px solid var(--border); }
    .ticket-table td { padding: 11px 14px; }
    .ticket-table td:first-child {
      background: var(--surface-muted);
      color: #1e293b;
      font-weight: 700;
      width: 155px;
    }
    .ticket-table td:last-child { font-weight: 700; color: var(--text-main); }

    .btn-cal-magic {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #16a34a;
      color: white;
      text-decoration: none;
      padding: 10px 16px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.95rem;
    }

    /* SUPPORTING DEMO METRICS BAR */
    .demo-metrics-section {
      background: var(--surface);
      border: 2px solid var(--border);
      border-radius: 14px;
      padding: 20px 24px;
      box-shadow: var(--shadow-sm);
    }
    .metrics-bar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .metrics-context-title {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .demo-data-tag {
      background: #e0e7ff;
      color: #1e1b4b;
      border: 1px solid #a5b4fc;
      font-size: 0.84rem;
      font-weight: 800;
      padding: 5px 12px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .metrics-context-sub {
      font-size: 0.96rem;
      color: var(--text-body);
      font-weight: 600;
    }

    /* HIGH-VISIBILITY 30-DAY BENCHMARK BUTTON */
    .btn-benchmark-toggle {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #ffffff;
      border: 2px solid #3b82f6;
      padding: 10px 18px;
      border-radius: 10px;
      font-size: 0.95rem;
      font-weight: 800;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
      transition: transform 0.12s, box-shadow 0.12s;
    }
    .btn-benchmark-toggle:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
    }
    .bench-pill-highlight {
      background: #f59e0b;
      color: #0f172a;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 0.84rem;
      font-weight: 800;
    }

    .rev-metrics-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
    }
    @media (max-width: 860px) {
      .rev-metrics-grid { grid-template-columns: 1fr; }
    }
    .rev-metric-card {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 22px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: transform 0.25s, border-color 0.25s, background-color 0.25s;
    }
    .rev-metric-card.metric-pulse {
      transform: scale(1.02);
      border-color: #2563eb;
      background: #eff6ff;
    }
    .rev-label {
      font-size: 0.9rem;
      font-weight: 800;
      color: #1e293b;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 4px;
    }
    .rev-subtext {
      font-size: 0.94rem;
      color: var(--text-muted);
      font-weight: 600;
    }
    .rev-val {
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-main);
      font-variant-numeric: tabular-nums;
    }

    /* VIEW 2: CALENDAR & VIEW 3: FLEET */
    .gcal-sync-banner {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #f8fafc;
      border: 2px solid #3b82f6;
      border-radius: 14px;
      padding: 16px 22px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      box-shadow: var(--shadow-sm);
    }
    .gcal-sync-left {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }
    .gcal-live-pill {
      background: #16a34a;
      color: #ffffff;
      font-size: 0.82rem;
      font-weight: 800;
      padding: 5px 12px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .gcal-sync-title {
      font-size: 1.05rem;
      font-weight: 800;
      color: #ffffff;
    }
    .gcal-sync-sub {
      font-size: 0.9rem;
      color: #cbd5e1;
    }
    .gcal-sync-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .btn-gcal-sync {
      background: #2563eb;
      color: #ffffff;
      border: 1px solid #60a5fa;
      padding: 9px 15px;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 800;
      cursor: pointer;
    }
    .btn-gcal-sync:hover { background: #1d4ed8; }
    .btn-gcal-outline {
      background: rgba(255, 255, 255, 0.1);
      color: #f8fafc;
      border: 1px solid rgba(255, 255, 255, 0.25);
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
    }
    .btn-gcal-outline:hover { background: rgba(255, 255, 255, 0.18); }

    /* ACTIVE DISPATCHES LIVE QUEUE STRIP */
    .active-dispatch-strip {
      margin-bottom: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .dispatch-queue-card {
      background: #f0fdf4;
      border: 2px solid #22c55e;
      border-radius: 12px;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      box-shadow: var(--shadow-sm);
    }
    .dispatch-queue-card.is-emerg-queue {
      background: #fff1f2;
      border: 2px solid #dc2626;
    }
    .dq-badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 800;
      text-transform: uppercase;
      background: #dcfce7;
      color: #15803d;
      margin-right: 8px;
    }
    .dispatch-queue-card.is-emerg-queue .dq-badge {
      background: #dc2626;
      color: #ffffff;
    }
    .dq-title {
      font-size: 1.1rem;
      font-weight: 800;
      color: var(--text-main);
    }
    .dq-meta {
      font-size: 0.94rem;
      color: var(--text-body);
      margin-top: 4px;
    }
    .dq-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .reassign-select {
      background: #ffffff;
      border: 1px solid #94a3b8;
      border-radius: 8px;
      padding: 7px 11px;
      font-size: 0.88rem;
      font-weight: 700;
      color: #0f172a;
    }

    .cal-controls-bar {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 20px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
    }
    .cal-controls-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    .cal-controls-left select {
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 700;
    }
    .btn-cal-action {
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      color: var(--text-body);
      padding: 9px 15px;
      border-radius: 8px;
      font-size: 0.92rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
    }
    .btn-cal-primary { background: var(--primary); color: white; border-color: var(--primary); }

    .cal-day-tabs-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }
    .cal-day-tab {
      background: var(--surface);
      border: 1px solid var(--border-strong);
      color: var(--text-body);
      padding: 7px 14px;
      border-radius: 999px;
      font-size: 0.88rem;
      font-weight: 800;
      cursor: pointer;
    }
    .cal-day-tab.active {
      background: var(--navy);
      color: #ffffff;
      border-color: var(--navy);
    }

    .full-calendar-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
    }
    .full-calendar-grid.single-day-mode {
      grid-template-columns: 1fr;
      max-width: 720px;
    }
    @media (max-width: 1180px) { .full-calendar-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 720px) { .full-calendar-grid { grid-template-columns: 1fr; } }

    .cal-col {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .cal-col.has-emergency-col {
      border: 2px solid #dc2626;
      box-shadow: 0 4px 16px rgba(220, 38, 38, 0.12);
    }
    .cal-col-header {
      background: var(--surface-muted);
      border-bottom: 1px solid var(--border);
      padding: 12px;
      text-align: center;
    }
    .cal-col.has-emergency-col .cal-col-header {
      background: #fef2f2;
      border-bottom-color: #fecaca;
    }
    .cal-col-day { font-size: 1.05rem; font-weight: 800; }
    .cal-col-sub { font-size: 0.86rem; color: var(--text-muted); font-weight: 700; margin-top: 2px; }
    .cal-col-body { padding: 12px; display: flex; flex-direction: column; gap: 10px; flex: 1; }

    .slot-box {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      background: var(--surface-muted);
    }
    .slot-box.is-elapsed-slot {
      background: #f1f5f9;
      border: 1px dashed #cbd5e1;
      color: #64748b;
    }
    .slot-time-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      font-size: 0.88rem;
      margin-bottom: 8px;
      font-weight: 800;
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 0.76rem;
      font-weight: 800;
      white-space: nowrap;
    }
    .pill-open {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
    }
    .pill-elapsed {
      background: #e2e8f0;
      color: #475569;
      border: 1px solid #cbd5e1;
    }
    .pill-blocked {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #cbd5e1;
    }

    .slot-tech-avail { font-size: 0.85rem; color: var(--text-body); margin-bottom: 8px; line-height: 1.4; }
    .slot-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
    .btn-slot-act { padding: 6px 11px; border-radius: 6px; font-size: 0.8rem; font-weight: 800; cursor: pointer; border: none; }
    .btn-slot-book { background: var(--primary); color: white; }
    .btn-slot-book:hover { background: var(--primary-hover); }
    .btn-slot-block { background: #e2e8f0; color: var(--text-body); }
    .btn-slot-block:hover { background: #cbd5e1; }

    /* DESIGNED BOOKED CARDS (SARAH AI VALUE PROP) */
    .slot-box.is-booked-routine {
      background: #f0fdf4;
      border: 2px solid #16a34a;
      box-shadow: 0 2px 8px rgba(22, 163, 74, 0.08);
    }
    .slot-box.is-booked-emergency {
      background: #fff1f2;
      border: 2px solid #dc2626;
      box-shadow: 0 3px 10px rgba(220, 38, 38, 0.14);
    }
    .slot-box.is-gcal-busy {
      background: #eff6ff;
      border: 1.5px dashed #3b82f6;
    }
    .booked-top-tags {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 7px;
    }
    .booked-ai-tag {
      background: #4f46e5;
      color: #ffffff;
      font-size: 0.74rem;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .booked-ai-tag.emerg-ai-tag {
      background: #dc2626;
      color: #ffffff;
    }
    .booked-manual-tag {
      background: #334155;
      color: #ffffff;
      font-size: 0.74rem;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 6px;
    }
    .dep-pill {
      font-size: 0.73rem;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 6px;
    }
    .dep-paid {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
    }
    .dep-pending {
      background: #fef3c7;
      color: #b45309;
      border: 1px solid #fde68a;
    }
    .booked-job-title {
      font-size: 0.96rem;
      font-weight: 800;
      color: var(--text-main);
      line-height: 1.25;
      margin-bottom: 4px;
    }
    .booked-hazard-line {
      font-size: 0.78rem;
      font-weight: 800;
      padding: 4px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(15, 23, 42, 0.12);
      color: #0f172a;
      margin-bottom: 6px;
    }
    .slot-box.is-booked-emergency .booked-hazard-line {
      background: #ffe4e6;
      border-color: #fda4af;
      color: #991b1b;
    }
    .booked-cust-name { font-size: 0.88rem; font-weight: 800; margin-bottom: 3px; color: var(--text-main); }
    .booked-cust-meta { font-size: 0.82rem; line-height: 1.4; color: var(--text-body); }
    .match-logic-badge {
      display: inline-block;
      margin-top: 4px;
      font-size: 0.74rem;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #cbd5e1;
      padding: 2px 6px;
      border-radius: 5px;
      color: #1e293b;
    }

    /* AVATAR CHIPS & MATCHING LOGIC PER WINDOW */
    .tech-chip-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 8px;
    }
    .tech-chip {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 7px;
      padding: 4px 7px;
      font-size: 0.78rem;
    }
    .tech-chip.busy-chip {
      background: #fff1f2;
      border-color: #fecdd3;
      color: #991b1b;
    }
    .tech-chip.gcal-chip {
      background: #eff6ff;
      border-color: #bfdbfe;
      color: #1e40af;
    }
    .chip-left {
      display: flex;
      align-items: center;
      gap: 5px;
      font-weight: 800;
      color: #0f172a;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .chip-avatar {
      width: 20px;
      height: 20px;
      border-radius: 999px;
      background: #dbeafe;
      color: #1e3a8a;
      font-size: 0.66rem;
      font-weight: 800;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .tech-chip.busy-chip .chip-avatar {
      background: #dc2626;
      color: #ffffff;
    }
    .chip-role {
      font-size: 0.68rem;
      color: #475569;
      font-weight: 700;
      white-space: nowrap;
    }

    /* FLEET ROSTER */
    .fleet-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 22px; }
    .kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
    .kpi-label { font-size: 0.88rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; }
    .kpi-val { font-size: 1.7rem; font-weight: 800; margin-top: 4px; }
    .kpi-sub { font-size: 0.9rem; color: var(--primary); margin-top: 2px; font-weight: 600; }
    .fleet-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
    .btn-add-electrician { background: var(--primary); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-size: 0.95rem; font-weight: 700; cursor: pointer; }
    .fleet-cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 18px; }
    .tech-card-pro { background: var(--surface); border: 2px solid var(--border); border-radius: 14px; padding: 18px; display: flex; flex-direction: column; gap: 12px; }
    .tech-card-pro.is-dispatched-emerg { border-color: #dc2626; background: #fffafa; }
    .tech-card-pro.is-dispatched-routine { border-color: #22c55e; }
    .tech-card-top { display: flex; align-items: center; gap: 12px; }
    .tech-avatar { width: 48px; height: 48px; border-radius: 10px; background: var(--surface-muted); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
    .tech-name { font-size: 1.12rem; font-weight: 800; }
    .tech-license, .tech-phone { font-size: 0.9rem; color: var(--text-muted); }
    .tech-badge-oncall { background: #dcfce7; color: #15803d; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 800; }
    .tech-badge-emerg { background: #dc2626; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 800; }
    .tech-badge-offduty { background: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; }
    .tech-gcal-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.84rem;
      font-weight: 700;
      color: #1e293b;
    }
    .tech-active-job-box {
      background: #fff1f2;
      border: 1px solid #fecdd3;
      border-left: 4px solid #dc2626;
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.88rem;
    }
    .tech-active-job-box.routine-job {
      background: #f0fdf4;
      border-color: #bbf7d0;
      border-left-color: #16a34a;
    }
    .tech-specialties-row { display: flex; flex-wrap: wrap; gap: 6px; }
    .spec-pill { font-size: 0.84rem; background: var(--surface-muted); padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); font-weight: 600; }
    .tech-actions-row { display: flex; gap: 8px; padding-top: 10px; border-top: 1px solid var(--border); margin-top: auto; }
    .btn-tech-toggle-oncall { flex: 1; background: #f0fdf4; border: 1px solid #86efac; color: #15803d; padding: 8px; border-radius: 6px; font-weight: 700; cursor: pointer; }
    .btn-tech-edit, .btn-tech-del { padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-strong); background: var(--surface-muted); cursor: pointer; font-weight: 600; }

    /* MODALS */
    .modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.6);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-overlay.active { display: flex; }
    .modal-card {
      background: var(--surface);
      border-radius: 16px;
      width: 100%;
      max-width: 560px;
      padding: 26px;
      box-shadow: var(--shadow-lg);
    }
    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
    .modal-header h3 { font-size: 1.2rem; font-weight: 800; }
    .modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-muted); }
    .form-group { margin-bottom: 14px; display: flex; flex-direction: column; gap: 6px; }
    .form-group label { font-size: 0.92rem; font-weight: 700; }
    .form-group input, .form-group select, .form-group textarea { padding: 10px 12px; border: 1px solid var(--border-strong); border-radius: 8px; font-size: 0.96rem; }
    .btn-modal-submit { background: var(--primary); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 700; font-size: 1rem; width: 100%; cursor: pointer; margin-top: 10px; }
    .slider-row { display: flex; justify-content: space-between; margin: 14px 0 6px; font-weight: 700; }
    .roi-result-banner { background: #f0fdf4; border: 1px solid #86efac; border-radius: 12px; padding: 18px; margin: 18px 0; text-align: center; }
    .roi-big-gain { font-size: 2.1rem; font-weight: 800; color: #15803d; }

    /* WORK ORDER TICKET DOSSIER MODAL */
    .modal-card.ticket-dossier-card {
      max-width: 860px;
      padding: 0;
      overflow: hidden;
      border: 2px solid #cbd5e1;
      max-height: 95vh;
      display: flex;
      flex-direction: column;
    }
    .modal-card.ticket-dossier-card.is-emerg-dossier {
      border-color: #dc2626;
      box-shadow: 0 25px 50px -12px rgba(220, 38, 38, 0.25);
    }
    .dossier-top-banner {
      background: #0f172a;
      color: #ffffff;
      padding: 14px 22px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 14px;
      border-bottom: 3px solid #2563eb;
    }
    .modal-card.ticket-dossier-card.is-emerg-dossier .dossier-top-banner {
      background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
      border-bottom-color: #f87171;
    }
    .dossier-wo-stamp {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.76rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background: rgba(255, 255, 255, 0.15);
      padding: 3px 9px;
      border-radius: 6px;
      margin-bottom: 4px;
    }
    .dossier-main-title {
      font-size: 1.28rem;
      font-weight: 800;
      line-height: 1.2;
      color: #ffffff;
    }
    .dossier-sub-bar {
      background: #f8fafc;
      padding: 8px 22px;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.83rem;
      font-weight: 700;
      color: #334155;
    }
    .dossier-body {
      padding: 14px 22px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 11px;
      background: #ffffff;
    }
    .dossier-two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    @media (max-width: 720px) {
      .dossier-two-col { grid-template-columns: 1fr; }
    }
    .dossier-box {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      padding: 11px 14px;
    }
    .dossier-box-title {
      font-size: 0.75rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #475569;
      margin-bottom: 7px;
      padding-bottom: 5px;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .dossier-kv-row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 0.85rem;
      padding: 3px 0;
    }
    .dossier-kv-label { color: #64748b; font-weight: 600; flex-shrink: 0; }
    .dossier-kv-val { color: #0f172a; font-weight: 800; text-align: right; }
    .dossier-triage-banner {
      background: #eff6ff;
      border: 1px solid #93c5fd;
      border-left: 5px solid #2563eb;
      border-radius: 10px;
      padding: 11px 14px;
    }
    .dossier-triage-banner.is-emerg-triage {
      background: #fff1f2;
      border-color: #fda4af;
      border-left-color: #dc2626;
    }
    .dossier-checklist {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin-top: 6px;
    }
    .dossier-check-item {
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 0.82rem;
      font-weight: 700;
      color: #1e293b;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      padding: 5px 9px;
      border-radius: 6px;
    }
    .dossier-invoice-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }
    .dossier-invoice-table th {
      text-align: left;
      font-size: 0.73rem;
      text-transform: uppercase;
      color: #64748b;
      padding: 4px 8px;
      border-bottom: 1px solid #cbd5e1;
    }
    .dossier-invoice-table td {
      padding: 6px 8px;
      border-bottom: 1px solid #e2e8f0;
      font-weight: 700;
      color: #0f172a;
    }
    .dossier-footer-actions {
      background: #f1f5f9;
      padding: 12px 22px;
      border-top: 1px solid #cbd5e1;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }

    footer {
      background: var(--navy);
      color: #cbd5e1;
      text-align: center;
      padding: 16px;
      font-size: 0.9rem;
      margin-top: auto;
    }
  </style>
</head>
<body>

  <!-- TOP HEADER -->
  <header>
    <div class="brand">
      <div class="brand-icon">
        <img src="/assets/joblatch_ai_logo.jpg" alt="JobLatch AI" onerror="this.onerror=null; this.parentElement.innerHTML='⚡';">
      </div>
      <div>
        <div class="brand-title-row">
          <h1>JobLatch AI Voice Dispatch</h1>
          <span class="demo-mode-pill">Interactive Product Demo</span>
        </div>
        <p>Missed Call Recovery, AI Hazard Triage &amp; Autonomous Scheduling for Contractors</p>
      </div>
    </div>

    <div class="header-right">
      <div class="nav-tabs">
        <button class="nav-tab active" id="btnTabConsole" onclick="switchPortalTab('console')">
          🎙️ Interactive Demo
        </button>
        <button class="nav-tab" id="btnTabMonitor" onclick="switchPortalTab('monitor')">
          📊 Dispatch Monitor
        </button>
        <button class="nav-tab" id="btnTabCalendar" onclick="switchPortalTab('calendar')">
          📅 Dispatch Calendar <span class="nav-count" id="calCountPill">0</span>
        </button>
        <button class="nav-tab" id="btnTabFleet" onclick="switchPortalTab('fleet')">
          👷 Tech Roster <span class="nav-count" id="techCountPill">4</span>
        </button>
        <a href="/monitor" target="_blank" class="nav-tab" style="text-decoration:none; display:inline-flex; align-items:center; gap:5px; color:#38bdf8; background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.3); border-radius:8px;">
          ⚡ Full-Screen React Client ↗
        </a>
      </div>

      <div class="fsm-switch-container" title="Select contractor's existing invoicing &amp; FSM software">
        <span class="fsm-label">Invoicing App:</span>
        <select id="fsmPlatformSelect" class="fsm-select" onchange="switchFsmPlatform(this.value)">
          <option value="HOUSECALL_PRO" selected>🏠 Housecall Pro</option>
          <option value="SERVICETITAN">⚡ ServiceTitan</option>
          <option value="JOBBER">💼 Jobber</option>
          <option value="QUICKBOOKS">📗 QuickBooks Online</option>
        </select>
        <button class="fsm-payload-btn" onclick="openFsmPayloadModal()" title="View outgoing API webhook payload">📋 View FSM Webhook</button>
      </div>

      <button class="utility-btn" onclick="openRoiModal()">📊 ROI Calculator</button>
      <button class="utility-btn" onclick="openPitchModal()">💡 Sales Guide</button>
      <button class="utility-btn" onclick="openTwilioModal()">📞 Connect Phone</button>
    </div>
  </header>

  <main>
    <!-- TAB 1: STORY-DRIVEN INTERACTIVE DEMO -->
    <div class="tab-view active" id="viewConsole">

      <!-- THE VISUAL BACKBONE: SCENARIO-ADAPTIVE 4-STEP END-TO-END JOURNEY -->
      <div class="story-backbone">
        <div class="backbone-top">
          <div class="backbone-label" id="journeyModeTitle">
            ⚡ DROPPED-CALL RECOVERY JOURNEY
          </div>
          <!-- SINGLE AUTHORITATIVE NEXT-STEP BANNER (NO DUPLICATE PILLS) -->
          <div class="next-step-banner" id="guidedNextStepBanner">
            👉 <strong>What to do first:</strong> Click <strong>"▶ Start Demo: Simulate Dropped Call"</strong> or <strong>"🎙️ Speak to Sarah AI"</strong> below.
          </div>
        </div>

        <div class="journey-steps">
          <div class="j-step active-step" id="jStep1">
            <div class="j-num" id="jNum1">1</div>
            <div>
              <div class="j-title" id="jTitle1">Missed or Inbound Call</div>
              <div class="j-desc" id="jDesc1">Caller hangs up or speaks issue</div>
            </div>
          </div>
          <div class="j-step" id="jStep2">
            <div class="j-num" id="jNum2">2</div>
            <div>
              <div class="j-title" id="jTitle2">AI Triage &amp; 3s Text-Back</div>
              <div class="j-desc" id="jDesc2">Sarah intercepts lead via SMS</div>
            </div>
          </div>
          <div class="j-step" id="jStep3">
            <div class="j-num" id="jNum3">3</div>
            <div>
              <div class="j-title" id="jTitle3">Instant Dispatch</div>
              <div class="j-desc" id="jDesc3">Slot locked &amp; tech assigned</div>
            </div>
          </div>
          <div class="j-step" id="jStep4">
            <div class="j-num" id="jNum4">4</div>
            <div>
              <div class="j-title" id="jTitle4">Upfront Stripe Deposit</div>
              <div class="j-desc" id="jDesc4">$89 paid — Revenue Won</div>
            </div>
          </div>
        </div>
      </div>

      <!-- PRIMARY STAGE: LEFT = SIMULATOR, RIGHT = LIVE RESULTS -->
      <div class="demo-stage-grid">

        <!-- LEFT: LIVE CALLER SIMULATOR -->
        <div class="panel-card primary-simulator-card active-focus-panel" id="simulatorPanelCard">
          <div class="sim-header">
            <div>
              <span class="step-status-pill" id="simFocusBadge">● Step 1 — Start Here</span>
              <h2>Live Caller Simulator</h2>
            </div>
            <button class="utility-btn" style="background:#f1f5f9; color:#1e293b; border-color:#cbd5e1;" onclick="resetCall()">↺ Reset Demo</button>
          </div>

          <!-- PRIMARY ACTION: DROPPED CALL STORY -->
          <button class="btn-hero-start" onclick="simulateMissedCallLead()">
            <div class="hero-btn-top">
              <span>▶ Start Demo: Simulate Dropped Call</span>
              <span style="background:rgba(255,255,255,0.22); padding:3px 10px; border-radius:6px; font-size:0.88rem;">+$1,200 Story</span>
            </div>
            <div class="hero-btn-sub">
              Caller hangs up after hours &rarr; Sarah texts back in 3s &rarr; Customer books &amp; pays deposit
            </div>
          </button>

          <!-- SECONDARY SCENARIOS -->
          <div class="secondary-scenarios">
            <button class="btn-sec-scenario btn-sec-emerg" onclick="runScenario('emergency')">
              🚨 Test Burning Smell Emergency
            </button>
            <button class="btn-sec-scenario" onclick="runScenario('ev_charger')">
              ⚡ Test EV Charger Quote
            </button>
          </div>

          <!-- FIRST-CLASS VOICE CONTROL & LIVE SPEAKING INDICATOR -->
          <div class="voice-primary-bar">
            <div class="voice-status-left">
              <div class="waveform-bars" id="voiceWaveform">
                <span></span><span></span><span></span><span></span><span></span>
              </div>
              <div>
                <div class="voice-state-label" id="voiceStatusTitle">Sarah Voice AI Ready</div>
                <div class="voice-state-sub" id="voiceStatusSub">Click button to talk live via microphone</div>
              </div>
            </div>
            <button class="btn-voice-primary" id="micBtn" onclick="toggleMic()">
              🎙️ Speak to Sarah
            </button>
          </div>

          <div class="transcript-label">
            <span>Live Call &amp; AI Event Transcript</span>
            <span id="transcriptTurnCount" style="color:#2563eb;">Live Audio + Text</span>
          </div>

          <div class="chat-container" id="chatStream">
            <div class="bubble bubble-sarah">
              <div class="speaker-name">Sarah (JobLatch AI Dispatcher)</div>
              Thank you for calling JobLatch AI Electrical 24/7 Dispatch. Click <strong>"▶ Start Demo"</strong> above, press <strong>"🎙️ Speak to Sarah"</strong>, or type any electrical issue below!
            </div>
          </div>

          <div class="input-row">
            <input type="text" id="userInput" placeholder="Or type what a caller would say..." onkeydown="if(event.key==='Enter') sendUserMessage()">
            <button class="btn-send" onclick="sendUserMessage()">Send</button>
          </div>
        </div>

        <!-- RIGHT: LIVE RESULTS (PHONE + CONTRACTOR DISPATCH TICKET) -->
        <div class="panel-card outcomes-stage" id="outcomesStageCard">
          <div class="outcomes-header">
            <h2>Live Results (Updates Automatically During Call)</h2>
            <div style="display:flex; align-items:center; gap:8px; font-size:0.92rem; color:var(--text-body);">
              <span>Demo Alert Email:</span>
              <input type="email" id="contractorEmail" value="dispatch@apex-electrical-demo.com" style="border:1px solid #94a3b8; border-radius:6px; padding:5px 10px; font-size:0.9rem; width:240px;">
              <button class="btn-slot-act btn-slot-book" onclick="saveContractorEmail()">Save</button>
            </div>
          </div>

          <div class="outcomes-split">
            <!-- Device Switcher (Customer Phone vs In-Truck Rugged Tablet) -->
            <div class="phone-column-wrap">
              <div class="device-switch-bar">
                <button class="device-tab-btn active" id="btnDeviceCustomer" onclick="switchDeviceMode('customer')">
                  👤 Customer Phone
                </button>
                <button class="device-tab-btn" id="btnDeviceTech" onclick="switchDeviceMode('tech')">
                  👷 Electrician Tablet
                </button>
              </div>

              <div class="phone-chassis" id="phoneChassis">
                <div class="phone-screen" id="phoneScreen">
                  <!-- SUBVIEW 1: Customer Smartphone SMS -->
                  <div id="customerPhoneView" style="display:flex; flex-direction:column; flex:1; height:100%;">
                    <div class="phone-dynamic-island"></div>
                    <div class="phone-status-bar">
                      <span>9:41</span>
                      <span>5G &bull; 92%</span>
                    </div>
                    <div class="phone-imessage-header">
                      <div class="imessage-avatar"><img src="/assets/joblatch_ai_logo.jpg" alt="JobLatch AI" onerror="this.onerror=null; this.parentElement.innerText='JL';"></div>
                      <div>
                        <div class="imessage-name">JobLatch AI Dispatch ✓</div>
                        <div class="imessage-sub">Customer SMS Feed</div>
                      </div>
                    </div>

                    <div class="phone-messages" id="phoneMessages">
                      <div class="sms-bubble">
                        <div class="sms-tag">Customer Phone Preview</div>
                        When Sarah sends a 3-second missed-call recovery link or Stripe deposit prompt, it appears right here for the homeowner to tap.
                      </div>
                    </div>

                    <div class="phone-home-bar"></div>
                  </div>

                  <!-- SUBVIEW 2: Electrician In-Truck Rugged Tablet (TRUCK-01) -->
                  <div id="techTabletView" style="display:none; flex-direction:column; flex:1; height:100%; background:#0f172a; color:#f8fafc; overflow:hidden;">
                    <!-- Tech Header Top Bar -->
                    <div class="tech-top-bar">
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.15rem;">🚐</span>
                        <div>
                          <div style="font-size:0.86rem; font-weight:800; color:#ffffff;" id="techTabletTruckId">TRUCK-01 (Marcus Vance)</div>
                          <div style="font-size:0.72rem; color:#94a3b8;" id="techTabletSubStatus">Master Tech &bull; GPS Active &bull; On-Call</div>
                        </div>
                      </div>
                      <span id="techWorkflowBadge" style="background:#dc2626; color:#ffffff; font-size:0.72rem; font-weight:800; padding:3px 8px; border-radius:5px; text-transform:uppercase;">DISPATCHED</span>
                    </div>

                    <!-- Scrollable Tech Action Stages -->
                    <div class="tech-body-scroll" id="techBodyScroll">
                      <!-- Stage 1: En Route GPS & Customer Contact -->
                      <div class="tech-card">
                        <div class="tech-card-title">
                          <span>📍 Job Site &amp; GPS Dispatch Routing</span>
                          <span style="color:#38bdf8;" id="techGpsEtaLabel">14m ETA</span>
                        </div>
                        <div style="font-size:0.86rem; font-weight:800; color:#ffffff; margin-bottom:2px;" id="techCustNameAddress">David Miller • 742 Evergreen Terrace</div>
                        <div style="font-size:0.78rem; color:#94a3b8; margin-bottom:8px;" id="techCustPhoneWindow">(555) 482-9104 &bull; Scheduled: Today, within 45–60 min</div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
                          <a href="https://maps.google.com" target="_blank" id="techGpsNavBtn" class="tech-btn" style="background:#0369a1; text-decoration:none; text-align:center;">🗺️ GPS Nav</a>
                          <button class="tech-btn" id="techEnRouteActionBtn" style="background:#2563eb;" onclick="techTriggerEnRoute()">🚐 Mark En Route</button>
                        </div>
                      </div>

                      <!-- Stage 2: AI NFPA 70E Safety & Truck Stock Pre-Check -->
                      <div class="tech-card" style="border-left:3px solid #ef4444; background:rgba(30,41,59,0.85);">
                        <div class="tech-card-title">
                          <span style="color:#fca5a5;">🚨 AI NFPA 70E Safety &amp; Truck Stock</span>
                          <span style="color:#86efac; font-size:0.72rem;">✓ Pre-Verified</span>
                        </div>
                        <div style="font-size:0.8rem; color:#f8fafc; margin-bottom:4px;">
                          <strong style="color:#fca5a5;">Hazard:</strong> <span id="techHazardText">NFPA 70E Code Red — Active Thermal / Fire Risk</span>
                        </div>
                        <div style="font-size:0.76rem; color:#cbd5e1; margin-bottom:6px;">
                          <strong style="color:#e2e8f0;">Directive Issued:</strong> <span id="techSafetyText">Shut off circuit breaker immediately; do not touch scorched outlets.</span>
                        </div>
                        <div style="background:rgba(15,23,42,0.6); border:1px solid #334155; border-radius:6px; padding:6px 8px; font-size:0.76rem;">
                          <strong style="color:#60a5fa;">📸 Panel / Breaker Loaded:</strong><br>
                          <span id="techPanelStockText" style="color:#86efac; font-weight:700;">Square D QO 150A &bull; QO120DF AFCI/GFCI Loaded on TRUCK-01 ✓</span>
                        </div>
                      </div>

                      <!-- Stage 3: On-Site Electrical Diagnostic Log -->
                      <div class="tech-card">
                        <div class="tech-card-title">
                          <span>🔬 On-Site Diagnostics Log (NEC 110.14D)</span>
                          <span style="color:#a855f7;" id="techDiagStatusBadge">Ready to Record</span>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:8px; font-size:0.78rem;">
                          <div>
                            <span style="color:#94a3b8; font-size:0.7rem;">Voltage (L1/L2):</span>
                            <input type="text" id="techInputVoltage" value="121V / 122V" class="tech-field-input">
                          </div>
                          <div>
                            <span style="color:#94a3b8; font-size:0.7rem;">Panel Rating:</span>
                            <input type="text" id="techInputAmps" value="150 Amps" class="tech-field-input">
                          </div>
                          <div>
                            <span style="color:#94a3b8; font-size:0.7rem;">IR Hotspot:</span>
                            <input type="text" id="techInputThermal" value="138°F (Lug)" class="tech-field-input" style="color:#f87171;">
                          </div>
                          <div>
                            <span style="color:#94a3b8; font-size:0.7rem;">Lug Torque:</span>
                            <input type="text" id="techInputTorque" value="45 In-Lbs ✓" class="tech-field-input" style="color:#4ade80;">
                          </div>
                        </div>
                        <button class="tech-btn" id="techRecordDiagBtn" style="background:#4f46e5; width:100%;" onclick="techSaveDiagnosticsAction()">
                          ✓ Record &amp; Seal Diagnostic Log
                        </button>
                      </div>

                      <!-- Stage 4: FSM Job Sync, Deposit Credit & Customer Work Authorization -->
                      <div class="tech-card" style="border:1.5px solid #3b82f6; background:rgba(30,41,59,0.92);">
                        <div class="tech-card-title">
                          <span style="color:#93c5fd;" id="techFsmStageTitle">🔌 FSM Scope &amp; Customer Authorization</span>
                          <span style="background:rgba(37,99,235,0.3); color:#93c5fd; font-weight:800; font-size:0.72rem; padding:2px 6px; border-radius:4px;" id="techFsmTicketPill">HCP-1001</span>
                        </div>

                        <div style="background:#0f172a; border:1px solid #334155; border-radius:6px; padding:7px 9px; margin-bottom:8px; font-size:0.76rem;">
                          <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                            <span style="color:#94a3b8;">Connected Platform:</span>
                            <span style="color:#ffffff; font-weight:700;" id="techFsmNameDisplay">Housecall Pro</span>
                          </div>
                          <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                            <span style="color:#94a3b8;">Upfront Deposit Credited:</span>
                            <span style="color:#4ade80; font-weight:800;" id="techFsmDepositDisplay">-$89.00 (Stripe Paid ✓)</span>
                          </div>
                          <div style="display:flex; justify-content:space-between;">
                            <span style="color:#94a3b8;">Invoicing &amp; Price Book:</span>
                            <span style="color:#cbd5e1;">Native Shop Flat-Rate</span>
                          </div>
                        </div>

                        <div style="margin-bottom:8px;">
                          <a href="#" id="techFsmDeepLinkBtn" target="_blank" class="tech-btn" style="background:#2563eb; text-decoration:none; text-align:center; display:flex; align-items:center; justify-content:center; gap:6px; font-weight:800; padding:8px;">
                            <span id="techFsmButtonText">↗ Open Job &amp; Price Book in Housecall Pro</span>
                          </a>
                        </div>

                        <!-- Digital Signature Pad -->
                        <div style="background:#020617; border:1px solid #334155; border-radius:8px; padding:8px; margin-bottom:6px;">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <span style="font-size:0.74rem; font-weight:800; color:#e2e8f0;">✍️ Customer Authorization Signature:</span>
                            <button onclick="techClearSignature()" style="background:transparent; border:none; color:#94a3b8; font-size:0.7rem; cursor:pointer;">Clear</button>
                          </div>
                          <canvas id="techSigCanvas" width="280" height="55" style="background:#0f172a; border-radius:4px; width:100%; border:1px dashed #475569; cursor:crosshair;"></canvas>
                          <div id="techSigTimestamp" style="font-size:0.7rem; color:#86efac; font-weight:700; margin-top:3px; display:none;"></div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
                          <button class="tech-btn" style="background:#059669;" onclick="techAdoptSignature()">✍️ 1-Tap Adopt Sign</button>
                          <button class="tech-btn" style="background:#16a34a;" onclick="techAuthorizeScopeAction()">✓ Confirm Scope</button>
                        </div>
                      </div>

                      <!-- Stage 5: Final Stripe Balance & 5-Star Review Engine -->
                      <div class="tech-card" style="background:rgba(22,163,74,0.15); border:1.5px solid #22c55e;">
                        <div class="tech-card-title">
                          <span style="color:#86efac;">💰 Final Balance &amp; 5-Star Google Review</span>
                          <span id="techFinalPayStatusPill" style="color:#4ade80; font-weight:800;">PENDING</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                          <span style="font-size:0.8rem; color:#cbd5e1;">Remaining Balance:</span>
                          <span style="font-size:1.1rem; font-weight:900; color:#4ade80;" id="techBalanceDueAmt">$2,136.00</span>
                        </div>
                        <div style="display:flex; flex-direction:column; gap:6px;">
                          <button class="tech-btn" id="techFinalCollectBtn" style="background:#16a34a; font-size:0.86rem;" onclick="techCollectFinalBalanceAction()">
                            💳 Collect Final Balance via Stripe
                          </button>
                          <button class="tech-btn" id="techReviewActionBtn" style="background:#d97706;" onclick="techSendReviewSmsAction()">
                            ⭐ Request 5-Star Google Review SMS
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Contractor Dispatch Ticket Outcome -->
            <div class="cockpit-column">
              <!-- Quiet Placeholder Before Booking -->
              <div id="waitingPlaceholder" class="waiting-quiet-box">
                <div class="waiting-icon">📋</div>
                <h3>Contractor Dispatch Ticket</h3>
                <p>Once a caller books a slot or claims a missed-call recovery link, the complete work order and safety triage appear here.</p>
                <div class="quiet-checklist">
                  <div>✓ <strong>NFPA 70E Hazard Triage</strong> (Symptom, Severity &amp; Safety Given)</div>
                  <div>✓ <strong>Auto-Assigned Electrician</strong> from active roster</div>
                  <div>✓ <strong>1-Click Google Calendar</strong> &amp; iCal dispatch sync</div>
                  <div>✓ <strong>Upfront Stripe Deposit</strong> verification status</div>
                </div>
              </div>

              <!-- Active Ticket Card -->
              <div class="dispatch-hero" id="dispatchHero">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
                  <span class="hero-badge badge-standard" id="heroBadge">Confirmed Dispatch</span>
                  <span id="heroPayBadge" style="font-size:0.88rem; font-weight:800; color:#b45309; background:#fef3c7; padding:5px 12px; border-radius:6px; border:1px solid #fde68a;">
                    💳 Pending $89 Deposit
                  </span>
                </div>
                <div class="hero-title" id="heroTitle">Electrical Emergency: Burning Smell</div>
                <div class="hero-subtitle">Dispatched to <strong id="heroContractor">dispatch@apex-electrical-demo.com</strong></div>

                <!-- CREDIBILITY MOMENT: AI TRIAGE & SAFETY SUMMARY -->
                <div class="triage-credibility-box" id="triageCredibilityBox">
                  <div class="triage-box-header" id="triageBoxHeader">
                    🛡️ AI TRIAGE &amp; LIFE-SAFETY VERIFICATION
                  </div>
                  <div class="triage-detail-row">
                    <strong>Reported Symptom:</strong> <span id="triageSymptom">-</span>
                  </div>
                  <div class="triage-detail-row">
                    <strong>Hazard Classification:</strong> <span id="triageHazardLevel">-</span>
                  </div>
                  <div class="triage-detail-row">
                    <strong>Safety Instruction Given:</strong> <span id="triageSafetyGiven">-</span>
                  </div>
                </div>

                <div style="display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap;">
                  <button class="btn-cal-action" style="background:#0f172a; color:#fff; border-color:#0f172a;" onclick="openTicketDossierModal(ACTIVE_HERO_BOOKING)">
                    📋 Expand Full Work Order Ticket
                  </button>
                  <a href="#" id="heroCalBtn" target="_blank" class="btn-cal-magic">
                    📅 Add to Google Calendar
                  </a>
                  <button class="btn-cal-action" onclick="switchPortalTab('calendar')">
                    View on Fleet Calendar &rarr;
                  </button>
                </div>

                <table class="ticket-table" id="ticketTable">
                  <tr><td>Confirmation:</td><td id="tktConf">-</td></tr>
                  <tr><td>Customer:</td><td id="tktCustomer">-</td></tr>
                  <tr><td>Callback Phone:</td><td id="tktPhone">-</td></tr>
                  <tr><td>Service Address:</td><td id="tktAddress">-</td></tr>
                  <tr><td>Assigned Tech:</td><td id="tktTech">-</td></tr>
                  <tr><td>Arrival Window:</td><td id="tktWindow">-</td></tr>
                  <tr><td>Upfront Deposit:</td><td id="tktFee">-</td></tr>
                  <tr><td>Est. Job Value:</td><td id="tktVal" style="color:#15803d; font-weight:800;">-</td></tr>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SUPPORTING DEMO METRICS BAR (PIPELINE BOOKED -> REVENUE WON AFTER DEPOSIT) -->
      <div class="demo-metrics-section" id="demoMetricsSection">
        <div class="metrics-bar-header">
          <div class="metrics-context-title">
            <span class="demo-data-tag" id="benchmarkIndicator">🧪 Simulated Demo Session Data</span>
            <span class="metrics-context-sub">Starts at $0 — tallies live with count-up animation as you test calls</span>
          </div>
          <button class="btn-benchmark-toggle" id="btnBenchmarkToggle" onclick="toggleBenchmarkMode()">
            <span>📈 Preview 30-Day Contractor Benchmark</span>
            <span class="bench-pill-highlight" id="benchPillBadge">+$18,450 / mo</span>
          </button>
        </div>

        <div class="rev-metrics-grid">
          <div class="rev-metric-card" id="cardMetricPipeline">
            <div>
              <div class="rev-label" id="kpiPipelineLabel">Pipeline Booked (Pending Deposit)</div>
              <div class="rev-subtext" id="kpiPipelineSub">0 Dispatches Booked in Session</div>
            </div>
            <div class="rev-val" id="kpiPipelineRev">$0</div>
          </div>

          <div class="rev-metric-card" id="cardMetricMissed">
            <div>
              <div class="rev-label">Missed Calls Recouped</div>
              <div class="rev-subtext" id="kpiMissedSub">0 Dropped Calls Tested</div>
            </div>
            <div class="rev-val" id="kpiMissedRec">0 Saved</div>
          </div>

          <div class="rev-metric-card" id="cardMetricFees">
            <div>
              <div class="rev-label">Upfront Deposits Collected</div>
              <div class="rev-subtext" id="kpiFeesSubtext">0 Stripe Deposits Paid</div>
            </div>
            <div class="rev-val" id="kpiFeesCol">$0</div>
          </div>
        </div>
      </div>

    </div>

    <!-- TAB 2: FLEET DISPATCH CALENDAR -->
    <div class="tab-view" id="viewCalendar">
      <!-- GOOGLE CALENDAR TWO-WAY SYNC BAR -->
      <div class="gcal-sync-banner" id="gcalSyncBanner">
        <div class="gcal-sync-left">
          <span class="gcal-live-pill" id="gcalLiveBadge">● Google Calendar Two-Way Sync</span>
          <div>
            <div class="gcal-sync-title" id="gcalSyncStatusTitle">Connected: Master Dispatch + 4 Technician Google Calendars</div>
            <div class="gcal-sync-sub" id="gcalSyncStatusSub">Dispatches push instantly to Google Calendar &bull; External Google Calendar busy blocks prevent double-booking</div>
          </div>
        </div>
        <div class="gcal-sync-actions">
          <button class="btn-gcal-sync" onclick="triggerGcalTwoWaySync()">🔄 Sync Google Calendar Busy Blocks</button>
          <button class="btn-gcal-outline" onclick="openGcalSyncModal()">🔗 Configure Google Calendar Sync</button>
          <a href="/api/calendar.ics" class="btn-gcal-outline" download="joblatch_schedule.ics">⬇️ Export .ICS</a>
        </div>
      </div>

      <!-- LIVE ACTIVE DISPATCHES STRIP (INSTANTLY SHOWS EMERGENCIES & BOOKINGS) -->
      <div class="active-dispatch-strip" id="activeDispatchStrip"></div>

      <div class="cal-controls-bar">
        <div class="cal-controls-left">
          <label style="font-weight:800;">Filter Electrician:</label>
          <select id="calTechFilter" onchange="renderCalendar()">
            <option value="ALL">⚡ All Electricians (Full 4-Tech Dispatch Board)</option>
          </select>
          <span id="calOccupancySummary" style="font-size:0.9rem; color:var(--text-muted); font-weight:700;"></span>
        </div>

        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn-cal-action" onclick="copyIcalFeedUrl()">📋 Copy Live iCal Feed URL</button>
          <button class="btn-cal-action btn-cal-primary" onclick="openManualBookModal()">+ Manual Dispatch Booking</button>
        </div>
      </div>

      <!-- DAY SWITCHER TABS FOR SINGLE-DAY OR 5-DAY VIEW -->
      <div class="cal-day-tabs-bar" id="calDayTabsBar"></div>

      <div class="full-calendar-grid" id="fullCalendarGrid"></div>
    </div>

    <!-- TAB 3: ELECTRICIAN FLEET ROSTER -->
    <div class="tab-view" id="viewFleet">
      <div class="fleet-kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Active Fleet Roster</div>
          <div class="kpi-val" id="kpiFleetTotal">4</div>
          <div class="kpi-sub">Google Calendar Linked ✓</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">24/7 On-Call Lead</div>
          <div class="kpi-val" id="kpiFleetOnCall" style="font-size:1.35rem; color:#15803d;">Marcus Vance</div>
          <div class="kpi-sub">45m Emergency Dispatch</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Open Weekly Slots</div>
          <div class="kpi-val" id="kpiFleetOpenSlots">42</div>
          <div class="kpi-sub">Synced with GCal Busy Blocks</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Active Dispatches</div>
          <div class="kpi-val" id="kpiFleetBookedJobs">0</div>
          <div class="kpi-sub">Live on Fleet Calendar</div>
        </div>
      </div>

      <div class="fleet-header-row">
        <div>
          <h2 style="font-size:1.35rem; font-weight:800;">Electrician Roster, Live Dispatch Status &amp; Google Calendar Sync</h2>
          <p style="color:var(--text-muted); font-size:0.95rem;">Each electrician's Google Calendar syncs two-way with Sarah AI so she never double-books an occupied truck.</p>
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn-cal-action" onclick="triggerGcalTwoWaySync()">🔄 Sync Tech Google Calendars</button>
          <button class="btn-add-electrician" onclick="openAddTechModal()">+ Add Electrician</button>
        </div>
      </div>

      <div class="fleet-cards-grid" id="fleetCardsGrid"></div>
    </div>

    <!-- TAB 4: LIVE DISPATCH MONITOR TABLE -->
    <div class="tab-view" id="viewMonitor">
      <div class="fleet-kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Total Work Orders</div>
          <div class="kpi-val" id="monitorKpiTotal">0</div>
          <div class="kpi-sub">Live REST API Synced ✓</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Active Field Dispatches</div>
          <div class="kpi-val" id="monitorKpiActive" style="color:#15803d;">0</div>
          <div class="kpi-sub">Real-Time In-Flight Calls</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Code Red Emergencies</div>
          <div class="kpi-val" id="monitorKpiEmerg" style="color:#dc2626;">0</div>
          <div class="kpi-sub">NFPA 70E Life-Safety Triage</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Stripe Pre-Auth Holds</div>
          <div class="kpi-val" id="monitorKpiHolds" style="color:#2563eb;">$0</div>
          <div class="kpi-sub">Guaranteed Dispatch Revenue</div>
        </div>
      </div>

      <div class="fleet-header-row" style="margin-top:16px;">
        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
          <div style="position:relative; width:300px;">
            <input type="text" id="monitorSearchInput" oninput="renderMonitorView()" placeholder="Search caller, WO#, trade, or scope..." style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:0.88rem; outline:none;" />
          </div>
          <div style="display:flex; gap:6px;">
            <button class="nav-tab active" id="monitorFilterAll" onclick="setMonitorFilter('ALL')" style="padding:6px 12px; font-size:0.8rem; background:#2563eb; color:#fff;">All</button>
            <button class="nav-tab" id="monitorFilterActive" onclick="setMonitorFilter('ACTIVE')" style="padding:6px 12px; font-size:0.8rem;">Active</button>
            <button class="nav-tab" id="monitorFilterEmerg" onclick="setMonitorFilter('EMERGENCY')" style="padding:6px 12px; font-size:0.8rem;">🚨 Emergency</button>
            <button class="nav-tab" id="monitorFilterComp" onclick="setMonitorFilter('COMPLETED')" style="padding:6px 12px; font-size:0.8rem;">Completed</button>
          </div>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <div style="font-size:0.82rem; color:var(--text-muted); display:flex; align-items:center; gap:6px;">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#16a34a;"></span>
            <span>REST Poller: <strong>Live</strong></span>
          </div>
          <a href="/monitor" target="_blank" class="btn-cal-action" style="text-decoration:none;">⚡ Open React Client ↗</a>
        </div>
      </div>

      <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; overflow-x:auto; margin-top:14px; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
        <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.88rem;">
          <thead>
            <tr style="background:#f8fafc; border-bottom:1px solid #e2e8f0; color:#475569; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.04em;">
              <th style="padding:12px 14px; font-weight:700;">Work Order</th>
              <th style="padding:12px 14px; font-weight:700;">Status</th>
              <th style="padding:12px 14px; font-weight:700;">Caller &amp; Contact</th>
              <th style="padding:12px 14px; font-weight:700;">Trade &amp; Scope</th>
              <th style="padding:12px 14px; font-weight:700;">AI Voice Summary</th>
              <th style="padding:12px 14px; font-weight:700;">Assigned Tech</th>
              <th style="padding:12px 14px; font-weight:700;">Pre-Auth Fee</th>
              <th style="padding:12px 14px; font-weight:700; text-align:right;">Action</th>
            </tr>
          </thead>
          <tbody id="monitorTableBody"></tbody>
        </table>
      </div>
    </div>
  </main>

  <!-- MODAL: Sales Pitch & Live Shop Audit Playbook -->
  <div class="modal-overlay" id="pitchModal">
    <div class="modal-card" style="max-width:740px; width:95%; max-height:90vh; overflow-y:auto;">
      <div class="modal-header">
        <h3>💡 JobLatch AI Sales Guide &amp; Live Shop Audit Playbook</h3>
        <button class="modal-close" onclick="closePitchModal()">&times;</button>
      </div>
      <div style="font-size:0.93rem; color:var(--text-body); line-height:1.55;">
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:12px 14px; margin-bottom:14px;">
          <div style="font-size:0.8rem; font-weight:800; color:#4f46e5; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px;">
            ⏱️ The First 180 Seconds After a Missed Call (Why Contractors Lose $12K+/Mo)
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:0.84rem;">
            <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:9px 11px;">
              <strong style="color:#b91c1c;">❌ Competitor / Voicemail / Call Center:</strong>
              <ul style="margin:5px 0 0 16px; color:#7f1d1d;">
                <li><strong>0:03s:</strong> Caller hits voicemail or hold music; 80% hang up.</li>
                <li><strong>0:45s:</strong> Homeowner clicks the next electrical shop on Google LSA.</li>
                <li><strong>3:00m:</strong> Competitor answers and books the $1,850 panel repair.</li>
              </ul>
            </div>
            <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:9px 11px;">
              <strong style="color:#15803d;">⚡ JobLatch AI Voice &amp; SMS Dispatch Engine:</strong>
              <ul style="margin:5px 0 0 16px; color:#14532d;">
                <li><strong>0:03s:</strong> Sarah AI answers or fires instant 3-Sec SMS Booking Link.</li>
                <li><strong>0:45s:</strong> Triages NFPA 70E hazard, matches truck &amp; collects $89–$199 Stripe deposit.</li>
                <li><strong>2:00m:</strong> Sends 3-Option Flat-Rate Proposal (+$485 Surge upsell) + Panel Photo check.</li>
              </ul>
            </div>
          </div>
        </div>

        <div style="font-weight:800; font-size:0.86rem; text-transform:uppercase; color:#0f172a; margin-bottom:8px;">
          🛡️ Top 3 Contractor Objections &amp; Instant Demo Rebuttals
        </div>
        <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px; font-size:0.86rem;">
          <div style="border:1px solid #e2e8f0; border-radius:8px; padding:9px 12px; background:#ffffff;">
            <strong style="color:#0f172a;">1. &ldquo;We already pay $600/mo for an answering service.&rdquo;</strong><br>
            <span style="color:#475569;"><strong>Rebuttal:</strong> Call centers only take a name and number—by morning the homeowner already hired someone else. JobLatch AI locks the calendar slot, verifies panel photos, and collects the Stripe deposit on the spot.</span>
          </div>
          <div style="border:1px solid #e2e8f0; border-radius:8px; padding:9px 12px; background:#ffffff;">
            <strong style="color:#0f172a;">2. &ldquo;I answer my own cell phone when I'm in the field.&rdquo;</strong><br>
            <span style="color:#475569;"><strong>Rebuttal:</strong> When you're troubleshooting a live 200A panel in an attic or talking to an inspector, you can't answer. Missing just <strong>two</strong> panel/EV calls a month costs $4,500+ in high-margin revenue.</span>
          </div>
          <div style="border:1px solid #e2e8f0; border-radius:8px; padding:9px 12px; background:#ffffff;">
            <strong style="color:#0f172a;">3. &ldquo;Homeowners won't pay an upfront deposit before we arrive.&rdquo;</strong><br>
            <span style="color:#475569;"><strong>Rebuttal:</strong> It's credited 100% toward their repair—and when they also see their IRS 25C $600 Tax Credit &amp; Good/Better/Best options in the SMS, it filters out tire-kickers and increases average ticket by +$485.</span>
          </div>
        </div>

        <button class="btn-modal-submit" onclick="closePitchModal()">Got It — Back to Live Demo</button>
      </div>
    </div>
  </div>

  <!-- MODAL: ROI Calculator & Answering Service Comparison -->
  <div class="modal-overlay" id="roiModal">
    <div class="modal-card" style="max-width:680px; width:95%;">
      <div class="modal-header">
        <h3>📊 Contractor ROI Calculator &amp; Answering Service Comparison</h3>
        <button class="modal-close" onclick="closeRoiModal()">&times;</button>
      </div>
      <div>
        <div class="slider-row">
          <span>Monthly Inbound Calls:</span>
          <span id="valSliderCalls" style="color:var(--primary);">50 Calls / Mo</span>
        </div>
        <input type="range" id="sliderCalls" min="10" max="250" value="50" oninput="updateRoiCalculation()" style="width:100%;">

        <div class="slider-row">
          <span>Average Job Ticket:</span>
          <span id="valSliderTicket" style="color:var(--primary);">$1,200</span>
        </div>
        <input type="range" id="sliderTicket" min="300" max="4000" step="50" value="1200" oninput="updateRoiCalculation()" style="width:100%;">

        <div class="roi-result-banner" style="margin-bottom:14px;">
          <div style="font-size:0.86rem; font-weight:800; color:#15803d; text-transform:uppercase;">Projected Recouped Annual Revenue + Pre-Qualified Upsells</div>
          <div class="roi-big-gain" id="roiAnnualGain">+$128,808 / yr</div>
          <div style="font-size:0.9rem; color:var(--text-muted);" id="roiBreakdown">Based on recovering 7.6 missed after-hours jobs/month + $7,800/yr answering service savings</div>
        </div>

        <!-- Side-by-Side Comparison: Traditional Answering Service vs JobLatch AI -->
        <div style="border:1px solid #cbd5e1; border-radius:10px; overflow:hidden; margin-bottom:14px; font-size:0.85rem;">
          <table style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="background:#0f172a; color:#ffffff; text-align:left;">
                <th style="padding:8px 10px;">Capability</th>
                <th style="padding:8px 10px; color:#fca5a5;">Old Way: Call Center ($650/mo)</th>
                <th style="padding:8px 10px; color:#86efac;">⚡ JobLatch AI Dispatcher</th>
              </tr>
            </thead>
            <tbody>
              <tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:7px 10px; font-weight:700;">After-Hours / Dropped Calls</td>
                <td style="padding:7px 10px; color:#64748b;">Takes "name &amp; number" message; 65% call a competitor before morning</td>
                <td style="padding:7px 10px; font-weight:800; color:#15803d;">✓ 3-Sec SMS + Instant Calendar Slot Booking</td>
              </tr>
              <tr style="border-bottom:1px solid #e2e8f0; background:#f8fafc;">
                <td style="padding:7px 10px; font-weight:700;">Upfront Diagnostic Deposit</td>
                <td style="padding:7px 10px; color:#64748b;">$0 collected (high next-day no-show rate)</td>
                <td style="padding:7px 10px; font-weight:800; color:#15803d;">✓ Collects $89–$199 via Stripe in SMS</td>
              </tr>
              <tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:7px 10px; font-weight:700;">NFPA 70E &amp; Panel Pre-Check</td>
                <td style="padding:7px 10px; color:#64748b;">Scripts have zero electrical knowledge; wrong parts on truck</td>
                <td style="padding:7px 10px; font-weight:800; color:#15803d;">✓ AI Panel Photo Audit + NEC 220.82 Load Check</td>
              </tr>
              <tr style="background:#f8fafc;">
                <td style="padding:7px 10px; font-weight:700;">Fleet Truck &amp; GCal Sync</td>
                <td style="padding:7px 10px; color:#64748b;">Manual email note; double-books busy techs</td>
                <td style="padding:7px 10px; font-weight:800; color:#15803d;">✓ Two-Way Google Calendar + Truck Assignment</td>
              </tr>
            </tbody>
          </table>
        </div>

        <button class="btn-modal-submit" onclick="closeRoiModal()">Close Calculator</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Twilio Setup -->
  <div class="modal-overlay" id="twilioModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>📞 Connect Live Twilio Phone Number</h3>
        <button class="modal-close" onclick="closeTwilioModal()">&times;</button>
      </div>
      <div style="font-size:0.96rem; color:var(--text-body);">
        <p style="margin-bottom:12px;">Paste this webhook URL into your Twilio Console under <strong>A Call Comes In (HTTP POST)</strong>:</p>
        <div class="form-group">
          <div style="display:flex; gap:8px;">
            <input type="text" id="twilioUrlInput" readonly style="flex:1; font-family:monospace;">
            <button class="utility-btn" style="background:#0f172a; color:#fff;" onclick="copyTwilioWebhook()">Copy</button>
          </div>
        </div>
        <button class="btn-modal-submit" onclick="closeTwilioModal()">Done</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Add/Edit Tech -->
  <div class="modal-overlay" id="techModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="techModalTitle">Add Electrician</h3>
        <button class="modal-close" onclick="closeAddTechModal()">&times;</button>
      </div>
      <div>
        <input type="hidden" id="techIdInput">
        <div class="form-group"><label>Full Name:</label><input type="text" id="techNameInput"></div>
        <div class="form-group">
          <label>License Type:</label>
          <select id="techLicenseInput">
            <option value="Master Electrician">Master Electrician</option>
            <option value="Journeyman Electrician" selected>Journeyman Electrician</option>
            <option value="EV & Commercial Specialist">EV &amp; Commercial Specialist</option>
            <option value="Service Electrician">Service Electrician</option>
          </select>
        </div>
        <div class="form-group"><label>Phone:</label><input type="text" id="techPhoneInput" value="(555) 019-3321"></div>
        <div class="form-group">
          <label>Assigned Service Truck / Van ID:</label>
          <select id="techTruckInput">
            <option value="TRUCK-01 (Master Emergency Van)">🚐 TRUCK-01 (Master Emergency Van)</option>
            <option value="TRUCK-02 (200A Panel & Service Rig)">🚐 TRUCK-02 (200A Panel &amp; Service Rig)</option>
            <option value="TRUCK-03 (EV & Commercial Van)">🚐 TRUCK-03 (EV &amp; Commercial Van)</option>
            <option value="TRUCK-04 (Rapid Response Van)">🚐 TRUCK-04 (Rapid Response Van)</option>
            <option value="BUCKET-05 (Aerial Boom Truck)">🚛 BUCKET-05 (Aerial Boom Truck)</option>
          </select>
        </div>
        <div class="form-group">
          <label>On-Call Status:</label>
          <select id="techOnCallInput">
            <option value="false">Standard Hours</option>
            <option value="true">On-Call 24/7 Lead</option>
          </select>
        </div>
        <div class="form-group"><label>Specialties:</label><input type="text" id="techSpecsInput" value="residential_repair, lighting"></div>
        <button class="btn-modal-submit" onclick="submitTechForm()">Save Electrician &amp; Truck</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Manual Booking -->
  <div class="modal-overlay" id="manualBookModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>+ Dispatch &amp; Schedule Electrician</h3>
        <button class="modal-close" onclick="closeManualBookModal()">&times;</button>
      </div>
      <div>
        <div class="form-group"><label>Available Window &amp; Matched Electrician:</label><select id="manualSlotSelect"></select></div>
        <div class="form-group">
          <label>Service / Job Type:</label>
          <select id="manualServiceType" onchange="updateManualJobPreset()">
            <option value="200A Main Panel Upgrade">200A Main Panel Upgrade ($3,200 Est. Job)</option>
            <option value="EV Charger Installation">EV Charger 50A Installation ($1,450 Est. Job)</option>
            <option value="Commercial Electrical Repair">Commercial Switchgear &amp; Lighting ($2,100 Est. Job)</option>
            <option value="Residential Circuit Repair">Residential Breaker / Outlet Diagnostic ($650 Est. Job)</option>
          </select>
        </div>
        <div class="form-group"><label>Customer Name:</label><input type="text" id="manualCustomerName" value="Elena Rostova"></div>
        <div class="form-group"><label>Phone:</label><input type="text" id="manualCustomerPhone" value="(555) 614-8920"></div>
        <div class="form-group"><label>Email (Syncs Google Calendar Invite):</label><input type="email" id="manualCustomerEmail" value="elena.rostova@example.com"></div>
        <div class="form-group"><label>Service Address:</label><input type="text" id="manualCustomerAddress" value="88 Beacon Hill Rd, Boston"></div>
        <div class="form-group"><label>Triage &amp; Scope Notes:</label><textarea id="manualIssueDesc" rows="2">200A Main Breaker Panel Upgrade — flickering lights when dryer runs; thermal check requested</textarea></div>
        <button class="btn-modal-submit" onclick="submitManualBooking()">✓ Confirm Dispatch &amp; Sync Google Calendar</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Google Calendar Two-Way Sync -->
  <div class="modal-overlay" id="gcalSyncModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>📅 Google Calendar Two-Way Fleet Sync</h3>
        <button class="modal-close" onclick="closeGcalSyncModal()">&times;</button>
      </div>
      <div style="font-size:0.95rem; color:var(--text-body); line-height:1.5;">
        <p style="margin-bottom:12px;">
          JobLatch AI syncs two-way with your shop's <strong>Google Calendar</strong> so dispatches appear immediately on your phone and external events block Sarah from double-booking your electricians:
        </p>
        <div class="form-group">
          <label>1. Outbound Feed (Add JobLatch AI Dispatches to Your Google Calendar):</label>
          <div style="display:flex; gap:8px;">
            <input type="text" id="gcalOutboundInput" readonly style="flex:1; font-family:monospace; background:#f8fafc;">
            <button class="utility-btn" style="background:#0f172a; color:#fff;" onclick="copyIcalFeedUrl()">Copy URL</button>
          </div>
          <span style="font-size:0.82rem; color:var(--text-muted);">Paste into Google Calendar &rarr; Settings &rarr; Add Calendar &rarr; From URL</span>
        </div>
        <div class="form-group" style="margin-top:14px;">
          <label>2. Inbound Busy-Block Sync (Your Google Calendar .ICS URL):</label>
          <input type="text" id="gcalInboundInput" value="https://calendar.google.com/calendar/ical/apex-electrical-fleet%40group.calendar.google.com/public/basic.ics" style="font-family:monospace;">
          <span style="font-size:0.82rem; color:var(--text-muted);">Imports external busy events (inspections, supply runs, time off) onto the Fleet Dispatch Board</span>
        </div>
        <button class="btn-modal-submit" onclick="submitGcalSyncModal()">🔄 Sync Google Calendar Now</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Official Field Service Work Order & Dispatch Ticket Dossier -->
  <div class="modal-overlay" id="ticketDossierModal">
    <div class="modal-card ticket-dossier-card" id="ticketDossierCard">
      <div class="dossier-top-banner">
        <div>
          <div class="dossier-wo-stamp" id="dossierStamp">⚡ OFFICIAL FIELD WORK ORDER &bull; BOOKED BY SARAH AI</div>
          <div class="dossier-main-title" id="dossierJobTitle">Electrical Emergency: Burning Smell</div>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <span id="dossierStatusBadge" style="background:#dc2626; color:#fff; font-size:0.78rem; font-weight:800; padding:5px 11px; border-radius:6px;">DISPATCHED CODE RED</span>
          <button class="modal-close" style="color:#ffffff; font-size:1.7rem; line-height:1;" onclick="closeTicketDossierModal()">&times;</button>
        </div>
      </div>

      <div class="dossier-sub-bar">
        <span>📋 Work Order ID: <strong id="dossierConfId">#JL-EMERG-1005</strong></span>
        <span>🕒 Dispatched At: <strong id="dossierCreatedAt">Today, 12:45 PM EST</strong></span>
        <span>📧 Shop Copy: <strong id="dossierContractorEmail">dispatch@apex-electrical-demo.com</strong></span>
      </div>

      <div class="dossier-body">
        <!-- Section 1: Customer & Assigned Electrician Two-Col -->
        <div class="dossier-two-col">
          <div class="dossier-box">
            <div class="dossier-box-title">
              <span>👤 Customer &amp; Site Record</span>
              <span style="color:#16a34a;">✓ SMS Confirmed</span>
            </div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">Homeowner / Contact:</span><span class="dossier-kv-val" id="dossierCustName">David Miller</span></div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">Callback Phone:</span><span class="dossier-kv-val" id="dossierCustPhone">(555) 482-9104</span></div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">Service Address:</span><span class="dossier-kv-val" id="dossierCustAddress">742 Evergreen Terrace</span></div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">Site Access / Notes:</span><span class="dossier-kv-val" id="dossierAccessNotes">Immediate Code Red Dispatch</span></div>
          </div>

          <div class="dossier-box">
            <div class="dossier-box-title">
              <span>👷 Fleet Dispatch, Truck &amp; Routing</span>
              <span style="color:#2563eb;">📅 GCal Synced</span>
            </div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">Assigned Electrician:</span><span class="dossier-kv-val" id="dossierTechName">Marcus Vance (Master)</span></div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">AI Dispatch Match:</span><span class="dossier-kv-val" id="dossierTechMatch" style="color:#4338ca;">Master • On-Call • Nearest (14m)</span></div>
            <div class="dossier-kv-row"><span class="dossier-kv-label">Arrival Window:</span><span class="dossier-kv-val" id="dossierArrivalWin">Today, within 45–60 min</span></div>
            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #cbd5e1; display:flex; align-items:center; justify-content:space-between; gap:8px;">
              <span style="font-size:0.74rem; font-weight:800; color:#475569; text-transform:uppercase;">Reassign Tech:</span>
              <select id="dossierReassignSelect" class="reassign-select" style="flex:1; padding:4px 8px; font-size:0.8rem;" onchange="reassignFromDossierModal(this.value)"></select>
            </div>
            <div style="margin-top:5px; display:flex; align-items:center; justify-content:space-between; gap:8px;">
              <span style="font-size:0.74rem; font-weight:800; color:#475569; text-transform:uppercase;">Truck / Van ID:</span>
              <select id="dossierTruckSelect" class="reassign-select" style="flex:1; padding:4px 8px; font-size:0.8rem;" onchange="updateTruckFromDossierModal(this.value)">
                <option value="TRUCK-01 (Master Emergency Van)">🚐 TRUCK-01 (Master Emergency Van)</option>
                <option value="TRUCK-02 (200A Panel & Service Rig)">🚐 TRUCK-02 (200A Panel &amp; Service Rig)</option>
                <option value="TRUCK-03 (EV & Commercial Van)">🚐 TRUCK-03 (EV &amp; Commercial Van)</option>
                <option value="TRUCK-04 (Rapid Response Van)">🚐 TRUCK-04 (Rapid Response Van)</option>
                <option value="BUCKET-05 (Aerial Boom Truck)">🚛 BUCKET-05 (Aerial Boom Truck)</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Section 2: AI Technical Triage, NEC 220.82 Load, Municipal Permit & Rebate Protocol -->
        <div class="dossier-triage-banner" id="dossierTriageBanner">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:6px;">
            <span style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.04em;" id="dossierTriageTitle">🚨 NFPA 70E HAZARD TRIAGE &amp; SAFETY PROTOCOL LOG</span>
            <span style="font-size:0.76rem; font-weight:800; background:rgba(255,255,255,0.85); padding:3px 8px; border-radius:5px; border:1px solid rgba(15,23,42,0.15);" id="dossierHazardPill">Code Red Thermal Risk</span>
          </div>
          <div style="display:grid; grid-template-columns: 165px 1fr; gap:5px 12px; font-size:0.86rem; line-height:1.42;">
            <span style="font-weight:700; color:#475569;">Caller Symptom:</span>
            <span style="font-weight:800; color:#0f172a;" id="dossierSymptom">Burning rubber odor behind refrigerator</span>
            <span style="font-weight:700; color:#475569;">Hazard Classification:</span>
            <span style="font-weight:800; color:#b91c1c;" id="dossierHazardFull">NFPA 70E Code Red — Active Thermal / Fire Risk</span>
            <span style="font-weight:700; color:#475569;">Safety Directive Issued:</span>
            <span style="font-weight:600; color:#1e293b;" id="dossierSafetyDirective">Shut off circuit breaker immediately if safe; do not touch scorched outlets.</span>
            <span style="font-weight:700; color:#475569;">⚡ NEC 220.82 Load Audit:</span>
            <span style="font-weight:800; color:#1e3a8a;" id="dossierNecLoad">150A/200A Main Service Verified</span>
            <span style="font-weight:700; color:#475569;">🏛️ Municipal E-Permit:</span>
            <span style="font-weight:700; color:#0f172a;" id="dossierPermitInfo">Municipal Electrical Repair Permit Pre-Drafted</span>
            <span style="font-weight:700; color:#475569;">💰 Customer Rebate / 25C:</span>
            <span style="font-weight:800; color:#15803d;" id="dossierRebateInfo">Homeowner Insurance &amp; IRS 25C Safety Upgrade Eligible</span>
            <span style="font-weight:700; color:#475569;">💡 Pre-Qualified Upsell:</span>
            <span style="font-weight:800; color:#15803d;" id="dossierUpsellRec">Whole-Home Type 2 Surge Protection (NEC 230.67) — +$485 Add-On</span>
          </div>
        </div>

        <!-- Section 2.5: AI Panel & Equipment Photo Pre-Check Audit (Eliminates Wasted Truck Rolls) -->
        <div class="dossier-box" id="dossierPhotoBox" style="background:#f0fdf4; border:1.5px solid #86efac;">
          <div class="dossier-box-title" style="border-bottom-color:#bbf7d0;">
            <span>📸 AI Panel &amp; Breaker Photo Pre-Check (Eliminates Wasted Truck Rolls)</span>
            <span id="dossierPhotoStatusPill" style="background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:5px; font-weight:800;">📋 Pre-Arrival SMS Active</span>
          </div>
          <div style="display:grid; grid-template-columns: 165px 1fr; gap:4px 12px; font-size:0.85rem; line-height:1.4;">
            <span style="font-weight:700; color:#475569;">Detected Panel / Device:</span>
            <span style="font-weight:800; color:#0f172a;" id="dossierPhotoEquip">Square D QO 150A Main Panel</span>
            <span style="font-weight:700; color:#475569;">Required Breaker / Part:</span>
            <span style="font-weight:800; color:#1e3a8a;" id="dossierPhotoBreaker">Square D QO120DF (20A Dual-Function AFCI/GFCI)</span>
            <span style="font-weight:700; color:#475569;">AI Vision Inspection:</span>
            <span style="font-weight:600; color:#1e293b;" id="dossierPhotoFinding">SMS link sent to homeowner to verify panel label prior to arrival.</span>
          </div>
          <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <span style="font-size:0.8rem; font-weight:800; color:#15803d;" id="dossierPhotoPartsCheck">✓ Prevents rolling a truck without the matching breaker series</span>
            <button class="btn-cal-action" id="dossierUploadPhotoBtn" style="background:#16a34a; color:#fff; border-color:#15803d; padding:5px 12px; font-size:0.8rem;" onclick="simulatePhotoUploadFromDossier()">
              📸 Simulate Homeowner Panel Photo Upload
            </button>
          </div>
        </div>

        <!-- Section 3: Field Electrician Pre-Arrival Checklist & Truck Stock -->
        <div class="dossier-box">
          <div class="dossier-box-title">
            <span>🧰 Field Technician Pre-Arrival Checklist &amp; Recommended Truck Stock</span>
            <span>NEC / NFPA 70 Compliant</span>
          </div>
          <div class="dossier-checklist" id="dossierChecklistGrid"></div>
        </div>

        <!-- Section 4: Connected Invoicing & FSM Integration Bridge -->
        <div class="dossier-box" style="background:#ffffff;">
          <div class="dossier-box-title">
            <span>🔌 Connected Invoicing &amp; FSM Integration</span>
            <span id="dossierPaymentPill">⏳ Pending Authorization</span>
          </div>
          <div style="margin-bottom:10px; background:#f0fdf4; border:1.5px solid #86efac; border-radius:8px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <div>
                <div style="font-size:0.86rem; font-weight:800; color:#166534;" id="dossierFsmNameText">🏠 Connected to Housecall Pro &bull; Synced Ticket <strong>#HCP-8921</strong></div>
                <div style="font-size:0.76rem; color:#475569; margin-top:2px;" id="dossierFsmSubText">Upfront diagnostic deposit credited &bull; Price book &amp; quotes managed in external FSM</div>
              </div>
              <div style="display:flex; gap:6px; flex-wrap:wrap;">
                <a href="#" target="_blank" class="btn-cal-action" id="dossierFsmDeepLink" style="background:#0284c7; color:#fff; border-color:#0369a1; padding:4px 10px; font-size:0.78rem; text-decoration:none;">↗ Open in Invoicing App</a>
                <button class="btn-cal-action" style="background:#0f172a; color:#fff; border-color:#0f172a; padding:4px 10px; font-size:0.78rem;" onclick="openFsmPayloadModal(ACTIVE_DOSSIER_BOOKING ? ACTIVE_DOSSIER_BOOKING.confirmation_id : null)">📋 View FSM Webhook</button>
              </div>
            </div>
          </div>
          <table class="dossier-invoice-table">
            <thead>
              <tr>
                <th>Line Item Description</th>
                <th>Billing Stage</th>
                <th style="text-align:right;">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td id="dossierFeeDesc">Upfront Dispatch &amp; Diagnostic Deposit (Stripe Escrow)</td>
                <td id="dossierFeeStatusText" style="color:#b45309;">Pending Customer SMS Tap</td>
                <td style="text-align:right; font-size:0.95rem;" id="dossierFeeAmt">$199.00</td>
              </tr>
              <tr>
                <td id="dossierJobEstDesc">Diagnostic Deposit Credited Toward Final Scope</td>
                <td id="dossierJobStageText" style="color:#15803d; font-weight:700;">Credited to Connected FSM Invoice</td>
                <td style="text-align:right; font-size:0.95rem; color:#15803d; font-weight:800;" id="dossierJobValAmt">-$199.00 Credit</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="dossier-footer-actions">
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <a href="#" target="_blank" id="dossierGcalBtn" class="btn-cal-magic" style="padding:8px 12px; font-size:0.84rem;">📅 Open in Google Calendar</a>
          <button class="btn-cal-action" id="dossierStripePayBtn" style="background:#4f46e5; color:#fff; border-color:#4338ca; padding:8px 12px; font-size:0.84rem;" onclick="authorizeDepositFromDossier()">💳 Authorize Deposit</button>
          <button class="btn-cal-action" id="dossierReleaseHoldBtn" style="background:#dc2626; color:#fff; border-color:#b91c1c; padding:8px 12px; font-size:0.84rem; display:none;" onclick="releaseHoldFromDossier()">⊘ Drop / Cancel Hold</button>
          <button class="btn-cal-action" id="dossierFinalPayBtn" style="background:#15803d; color:#fff; border-color:#166534; padding:8px 12px; font-size:0.84rem;" onclick="payFinalBalanceFromDossier()">💰 Collect Final Balance</button>
          <button class="btn-cal-action" id="dossierEnRouteBtn" style="background:#0284c7; color:#fff; border-color:#0369a1; padding:8px 12px; font-size:0.84rem;" onclick="sendEnRouteSmsFromDossier()">🚐 Send "Tech En-Route" SMS</button>
          <button class="btn-cal-action" id="dossierReviewBtn" style="background:#f59e0b; color:#fff; border-color:#d97706; padding:8px 12px; font-size:0.84rem;" onclick="sendReviewSmsFromDossier()">⭐ Request 5-Star Review</button>
          <button class="btn-cal-action" style="background:#0f172a; color:#fff; border-color:#0f172a; padding:8px 12px; font-size:0.84rem;" onclick="openPrintableWorkOrder()">🖨️ Print Work Order (PDF)</button>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn-cal-action" style="padding:8px 12px; font-size:0.84rem;" onclick="jumpToCallConsoleFromDossier()">🎙️ Call Console</button>
          <button class="btn-cal-action" style="background:#0f172a; color:#fff; padding:8px 12px; font-size:0.84rem;" onclick="closeTicketDossierModal()">Done</button>
        </div>
      </div>
    </div>
  </div>

  <!-- FSM & INVOICING WEBHOOK PAYLOAD INSPECTOR MODAL -->
  <div class="modal-overlay" id="fsmPayloadModal">
    <div class="modal-card" style="max-width:760px; max-height:92vh; display:flex; flex-direction:column; padding:22px;">
      <div class="modal-header" style="margin-bottom:12px; padding-bottom:10px;">
        <div>
          <h3 style="font-size:1.15rem; font-weight:800; color:#0f172a; display:flex; align-items:center; gap:8px;">
            <span>🔌 Outgoing FSM &amp; Invoicing Webhook Bridge</span>
          </h3>
          <p style="font-size:0.82rem; color:#64748b; margin-top:2px;">
            JobLatch AI synchronizes customer records, NFPA triage logs, panel photos, and deposit receipts directly into your existing software.
          </p>
        </div>
        <button class="modal-close" onclick="closeFsmPayloadModal()">&times;</button>
      </div>

      <!-- Platform Tabs -->
      <div style="display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap;">
        <button class="fsm-modal-tab active" data-platform="HOUSECALL_PRO" onclick="previewFsmPlatformPayload('HOUSECALL_PRO')" style="padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; cursor:pointer; background:#2563eb; color:#ffffff; border:1.5px solid #3b82f6;">
          🏠 Housecall Pro
        </button>
        <button class="fsm-modal-tab" data-platform="SERVICETITAN" onclick="previewFsmPlatformPayload('SERVICETITAN')" style="padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; cursor:pointer; background:#f1f5f9; color:#334155; border:1px solid #cbd5e1;">
          ⚡ ServiceTitan
        </button>
        <button class="fsm-modal-tab" data-platform="JOBBER" onclick="previewFsmPlatformPayload('JOBBER')" style="padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; cursor:pointer; background:#f1f5f9; color:#334155; border:1px solid #cbd5e1;">
          💼 Jobber
        </button>
        <button class="fsm-modal-tab" data-platform="QUICKBOOKS" onclick="previewFsmPlatformPayload('QUICKBOOKS')" style="padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; cursor:pointer; background:#f1f5f9; color:#334155; border:1px solid #cbd5e1;">
          📗 QuickBooks Online
        </button>
      </div>

      <!-- Target API Endpoint Header -->
      <div style="background:#0f172a; border-radius:8px 8px 0 0; padding:8px 14px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="background:#22c55e; color:#0f172a; font-weight:800; font-size:0.7rem; padding:2px 6px; border-radius:4px;">SYNCED</span>
          <span style="font-family:monospace; font-size:0.78rem; color:#93c5fd;" id="fsmEndpointDisplay">POST https://api.housecallpro.com/v1/jobs</span>
        </div>
        <span style="font-size:0.72rem; color:#94a3b8;">JSON Webhook Payload</span>
      </div>

      <!-- JSON Viewer -->
      <pre id="fsmPayloadJsonPre" style="margin:0; background:#020617; color:#38bdf8; font-family:monospace; font-size:0.8rem; padding:14px; border-radius:0 0 8px 8px; max-height:360px; overflow:auto; line-height:1.45; border:1px solid #334155; border-top:none; flex:1;">// Loading payload...</pre>

      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; flex-wrap:wrap; gap:8px;">
        <span style="font-size:0.78rem; color:#64748b;">
          💡 Your price book, inventory, and final invoicing remain 100% inside your chosen platform.
        </span>
        <div style="display:flex; gap:8px;">
          <button id="btnCopyFsmPayload" class="btn-cal-action" style="background:#0284c7; color:#fff; border-color:#0369a1; padding:7px 14px; font-size:0.82rem;" onclick="copyFsmPayloadJson()">
            📋 Copy JSON Payload
          </button>
          <button class="btn-cal-action" style="background:#0f172a; color:#fff; border-color:#0f172a; padding:7px 14px; font-size:0.82rem;" onclick="closeFsmPayloadModal()">
            Done
          </button>
        </div>
      </div>
    </div>
  </div>

  <footer>
    JobLatch AI Voice Dispatch &bull; Interactive Product Demo Environment (Simulated Data)
  </footer>

  <script>
    let BOARD_DATA = { bookings: [], technicians: [], slots: [], roi_metrics: {} };
    let DEFAULT_CONFIG_EMAIL = 'dispatch@apex-electrical-demo.com';
    let PREV_METRICS = { pipeline: 0, missed: 0, fees: 0 };

    const chatStream = document.getElementById('chatStream');
    const userInput = document.getElementById('userInput');
    const dispatchHero = document.getElementById('dispatchHero');
    const waitingPlaceholder = document.getElementById('waitingPlaceholder');
    const phoneMessages = document.getElementById('phoneMessages');
    const contractorInput = document.getElementById('contractorEmail');

    // Scenario-Adaptive Step Definitions
    const JOURNEY_FLOWS = {
      missed_call: {
        header: '⚡ DROPPED-CALL RECOVERY JOURNEY',
        steps: [
          { title: 'Dropped Call', desc: 'Caller hangs up after hours' },
          { title: '3-Sec SMS Recovery', desc: 'Sarah texts instant booking link' },
          { title: '1-Tap Self-Dispatch', desc: 'Customer locks in slot & tech' },
          { title: 'Upfront Stripe Deposit', desc: '$89 paid — Revenue Won' }
        ]
      },
      emergency: {
        header: '🚨 LIVE VOICE & NFPA 70E TRIAGE JOURNEY',
        steps: [
          { title: 'Inbound Voice Call', desc: 'Caller reports burning smell' },
          { title: 'NFPA 70E Hazard Triage', desc: 'Code Red & safety directive given' },
          { title: 'Priority 45m Dispatch', desc: 'On-call Master Tech assigned' },
          { title: 'Upfront Stripe Deposit', desc: '$199 paid — Revenue Won' }
        ]
      },
      routine: {
        header: '⚡ LIVE VOICE SCHEDULING JOURNEY',
        steps: [
          { title: 'Inbound Voice Call', desc: 'Caller requests service quote' },
          { title: 'AI Spec & Slot Check', desc: 'Panel capacity & calendar verified' },
          { title: 'Instant Slot Dispatch', desc: 'Tech & arrival window locked' },
          { title: 'Upfront Stripe Deposit', desc: '$89 paid — Revenue Won' }
        ]
      }
    };

    function applyScenarioJourneyLabels(modeKey) {
      const flow = JOURNEY_FLOWS[modeKey] || JOURNEY_FLOWS.missed_call;
      const headerEl = document.getElementById('journeyModeTitle');
      if (headerEl) headerEl.innerText = flow.header;
      flow.steps.forEach((st, idx) => {
        const n = idx + 1;
        const tEl = document.getElementById(`jTitle${n}`);
        const dEl = document.getElementById(`jDesc${n}`);
        if (tEl) tEl.innerText = st.title;
        if (dEl) dEl.innerText = st.desc;
      });
    }

    // Update the 4-Step Visual Backbone & Move Active Highlight Border to the Right Panel
    function setJourneyProgress(stepNum, bannerHtml, focusTarget = 'simulator') {
      for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`jStep${i}`);
        const numEl = document.getElementById(`jNum${i}`);
        if (!el || !numEl) continue;
        el.classList.remove('active-step', 'done-step');
        if (i < stepNum) {
          el.classList.add('done-step');
          numEl.innerText = '✓';
        } else if (i === stepNum) {
          el.classList.add('active-step');
          numEl.innerText = String(i);
        } else {
          numEl.innerText = String(i);
        }
      }

      const banner = document.getElementById('guidedNextStepBanner');
      if (banner && bannerHtml) banner.innerHTML = bannerHtml;

      const simCard = document.getElementById('simulatorPanelCard');
      const outCard = document.getElementById('outcomesStageCard');
      const chassis = document.getElementById('phoneChassis');
      const simBadge = document.getElementById('simFocusBadge');

      simCard.classList.remove('active-focus-panel');
      outCard.classList.remove('active-focus-panel');
      chassis.classList.remove('highlight-phone');

      if (focusTarget === 'simulator') {
        simCard.classList.add('active-focus-panel');
        simBadge.className = 'step-status-pill';
        simBadge.innerText = '● Step 1 — Start Here';
      } else if (focusTarget === 'phone') {
        outCard.classList.add('active-focus-panel');
        chassis.classList.add('highlight-phone');
        simBadge.className = 'step-status-pill quiet-pill';
        simBadge.innerText = '✓ Call Simulated';
      } else if (focusTarget === 'complete') {
        simBadge.className = 'step-status-pill quiet-pill';
        simBadge.innerText = '✓ Demo Complete';
      }
    }

    // Count-Up Animation Helper for Metrics
    function animateMetricCountUp(el, cardEl, startVal, endVal, formatFn) {
      if (!el) return;
      if (startVal === endVal) {
        el.innerText = formatFn(endVal);
        return;
      }
      if (cardEl) {
        cardEl.classList.add('metric-pulse');
        setTimeout(() => cardEl.classList.remove('metric-pulse'), 650);
      }
      const duration = 600;
      const startTime = performance.now();
      function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(startVal + (endVal - startVal) * eased);
        el.innerText = formatFn(current);
        if (progress < 1) {
          requestAnimationFrame(tick);
        } else {
          el.innerText = formatFn(endVal);
        }
      }
      requestAnimationFrame(tick);
    }

    function switchPortalTab(tabKey) {
      document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
      document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));

      if (tabKey === 'console') {
        document.getElementById('viewConsole').classList.add('active');
        document.getElementById('btnTabConsole').classList.add('active');
      } else if (tabKey === 'monitor') {
        document.getElementById('viewMonitor').classList.add('active');
        document.getElementById('btnTabMonitor').classList.add('active');
        renderMonitorView();
      } else if (tabKey === 'calendar') {
        document.getElementById('viewCalendar').classList.add('active');
        document.getElementById('btnTabCalendar').classList.add('active');
        renderCalendar();
      } else if (tabKey === 'fleet') {
        document.getElementById('viewFleet').classList.add('active');
        document.getElementById('btnTabFleet').classList.add('active');
        renderFleetView();
      }
    }

    let MONITOR_STATUS_FILTER = 'ALL';

    function setMonitorFilter(filterVal) {
      MONITOR_STATUS_FILTER = filterVal;
      ['ALL', 'ACTIVE', 'EMERGENCY', 'COMPLETED'].forEach(f => {
        const btnId = 'monitorFilter' + f.charAt(0) + f.slice(1).toLowerCase();
        const btn = document.getElementById(btnId);
        if (btn) {
          if (f === filterVal) {
            btn.style.background = '#2563eb';
            btn.style.color = '#ffffff';
          } else {
            btn.style.background = 'transparent';
            btn.style.color = '#475569';
          }
        }
      });
      renderMonitorView();
    }

    function renderMonitorView() {
      const tbody = document.getElementById('monitorTableBody');
      if (!tbody) return;

      const rawDispatches = BOARD_DATA.dispatches || BOARD_DATA.bookings || [];
      const searchVal = (document.getElementById('monitorSearchInput')?.value || '').toLowerCase().trim();

      const filtered = rawDispatches.filter(job => {
        const urg = String(job.urgency_level || '').toUpperCase();
        const isEmerg = urg.includes('EMERG') || urg.includes('CRITICAL') || String(job.service_type || '').toLowerCase().includes('emergency');
        const status = isEmerg ? 'Emergency' : (job.status === 'Completed' || job.payment_status === 'PAID_VERIFIED' ? 'Completed' : 'Active');
        
        const matchesStatus = MONITOR_STATUS_FILTER === 'ALL' ||
          (MONITOR_STATUS_FILTER === 'ACTIVE' && status === 'Active') ||
          (MONITOR_STATUS_FILTER === 'EMERGENCY' && isEmerg) ||
          (MONITOR_STATUS_FILTER === 'COMPLETED' && status === 'Completed');

        const caller = String(job.caller || job.customer_name || '').toLowerCase();
        const id = String(job.id || job.confirmation_id || '').toLowerCase();
        const desc = String(job.ai_summary || job.symptom || job.issue_description || '').toLowerCase();
        const svc = String(job.service_type || job.service_title || '').toLowerCase();

        const matchesSearch = !searchVal || caller.includes(searchVal) || id.includes(searchVal) || desc.includes(searchVal) || svc.includes(searchVal);
        return matchesStatus && matchesSearch;
      });

      // Update KPIs
      const totalCount = rawDispatches.length;
      const emergCount = rawDispatches.filter(j => String(j.urgency_level || '').includes('EMERG') || String(j.urgency_level || '').includes('CRIT')).length;
      const activeCount = rawDispatches.filter(j => j.status === 'CONFIRMED' || j.status === 'DISPATCHED' || j.status === 'Active').length;
      const holdsTotal = rawDispatches.reduce((acc, j) => acc + Number(j.dispatch_fee || 89), 0);

      if (document.getElementById('monitorKpiTotal')) document.getElementById('monitorKpiTotal').innerText = totalCount;
      if (document.getElementById('monitorKpiActive')) document.getElementById('monitorKpiActive').innerText = activeCount;
      if (document.getElementById('monitorKpiEmerg')) document.getElementById('monitorKpiEmerg').innerText = emergCount;
      if (document.getElementById('monitorKpiHolds')) document.getElementById('monitorKpiHolds').innerText = '$' + holdsTotal.toFixed(0);

      if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="padding:32px; text-align:center; color:#64748b;">No dispatches found matching filter criteria.</td></tr>';
        return;
      }

      tbody.innerHTML = filtered.map(job => {
        const id = job.id || job.confirmation_id;
        const urg = String(job.urgency_level || '').toUpperCase();
        const isEmerg = urg.includes('EMERG') || urg.includes('CRITICAL');
        const caller = job.caller || job.customer_name || 'Resident / Caller';
        const phone = job.phone || job.phone_number || '(555) 000-0000';
        const trade = job.trade || 'Electrical';
        const svc = job.service_type || job.service_title || 'Residential Service';
        const summary = job.ai_summary || job.symptom || job.issue_description || 'Inbound service call';
        const tech = job.assigned_technician || 'On-Call Electrician';
        const fee = Number(job.dispatch_fee || 89).toFixed(2);
        const pStatus = job.payment_status || 'AUTHORIZED_HOLD';
        const time = job.time || job.slot_window || 'Today';

        const statusBadge = isEmerg 
          ? '<span style="background:#fee2e2; color:#dc2626; font-weight:800; font-size:0.75rem; padding:4px 8px; border-radius:999px; border:1px solid #fecaca; display:inline-flex; align-items:center; gap:4px;">🚨 Code Red</span>'
          : job.status === 'Completed' || pStatus === 'PAID_VERIFIED'
          ? '<span style="background:#f1f5f9; color:#475569; font-weight:700; font-size:0.75rem; padding:4px 8px; border-radius:999px;">✓ Completed</span>'
          : '<span style="background:#dcfce7; color:#15803d; font-weight:800; font-size:0.75rem; padding:4px 8px; border-radius:999px; border:1px solid #bbf7d0; display:inline-flex; align-items:center; gap:4px;">⏳ Active</span>';

        const pBadge = pStatus === 'PAID_VERIFIED'
          ? '<span style="color:#15803d; font-weight:700; font-size:0.75rem;">✓ Settled</span>'
          : pStatus === 'AUTHORIZED_HOLD'
          ? '<span style="color:#2563eb; font-weight:700; font-size:0.75rem;">⏳ 7-Day Hold</span>'
          : '<span style="color:#b45309; font-weight:700; font-size:0.75rem;">Pending</span>';

        return `
          <tr style="border-bottom:1px solid #f1f5f9; transition:background 0.15s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='transparent'">
            <td style="padding:12px 14px; font-family:monospace; font-weight:800; color:#2563eb;">
              ${id}
              <div style="font-family:sans-serif; font-size:0.75rem; color:#64748b; font-weight:400; margin-top:2px;">${time}</div>
            </td>
            <td style="padding:12px 14px;">${statusBadge}</td>
            <td style="padding:12px 14px;">
              <div style="font-weight:700; color:#0f172a;">${caller}</div>
              <div style="font-size:0.78rem; color:#64748b; margin-top:2px;">${phone}</div>
            </td>
            <td style="padding:12px 14px;">
              <span style="display:inline-block; font-size:0.72rem; font-weight:800; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; padding:2px 6px; border-radius:4px;">${trade}</span>
              <div style="font-weight:600; font-size:0.82rem; color:#334155; margin-top:3px;">${svc}</div>
            </td>
            <td style="padding:12px 14px; font-size:0.8rem; color:#475569; max-width:280px; line-height:1.4;">${summary}</td>
            <td style="padding:12px 14px; font-size:0.82rem;">
              <div style="font-weight:700; color:#1e293b;">${tech}</div>
            </td>
            <td style="padding:12px 14px;">
              <div style="font-weight:800; color:#0f172a;">$${fee}</div>
              <div>${pBadge}</div>
            </td>
            <td style="padding:12px 14px; text-align:right;">
              <button onclick="openTicketDossier('${id}')" style="background:#f1f5f9; border:1px solid #cbd5e1; padding:5px 10px; border-radius:6px; font-size:0.78rem; font-weight:700; color:#334155; cursor:pointer;">Inspect</button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function setVoiceIndicatorState(mode, titleText, subText) {
      const wave = document.getElementById('voiceWaveform');
      const titleEl = document.getElementById('voiceStatusTitle');
      const subEl = document.getElementById('voiceStatusSub');
      if (!wave || !titleEl || !subEl) return;

      if (mode === 'speaking' || mode === 'listening') {
        wave.classList.add('active-wave');
      } else {
        wave.classList.remove('active-wave');
      }
      titleEl.innerText = titleText;
      subEl.innerText = subText;
    }

    function speakText(text) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text.replace(/[*_#]/g, ''));
        utter.rate = 1.05;
        utter.onstart = () => {
          setVoiceIndicatorState('speaking', '🔊 Sarah AI is Speaking...', 'Live neural voice response active');
        };
        utter.onend = () => {
          setVoiceIndicatorState('idle', 'Sarah Voice AI Ready', 'Click button to talk live via microphone');
        };
        utter.onerror = () => {
          setVoiceIndicatorState('idle', 'Sarah Voice AI Ready', 'Click button to talk live via microphone');
        };
        window.speechSynthesis.speak(utter);
      }
    }

    function scrollTranscriptToBottom() {
      chatStream.scrollTop = chatStream.scrollHeight;
      requestAnimationFrame(() => {
        chatStream.scrollTop = chatStream.scrollHeight;
      });
      setTimeout(() => {
        chatStream.scrollTop = chatStream.scrollHeight;
      }, 40);
    }

    function appendMessage(speaker, text, isSarah = false) {
      const bubble = document.createElement('div');
      bubble.className = `bubble ${isSarah ? 'bubble-sarah' : 'bubble-user'}`;
      bubble.innerHTML = `<div class="speaker-name">${speaker}</div><div>${text.replace(/\n/g, '<br>')}</div>`;
      chatStream.appendChild(bubble);
      scrollTranscriptToBottom();
    }

    async function sendUserMessage() {
      const msg = userInput.value.trim();
      if (!msg) return;
      userInput.value = '';
      const isEmergMsg = /burn|smoke|spark|shock|fire|water|buzz|emerg/i.test(msg);
      applyScenarioJourneyLabels(isEmergMsg ? 'emergency' : 'routine');
      appendMessage('Caller (You)', msg, false);
      setJourneyProgress(
        2,
        '🎙️ <strong>Step 2 of 4:</strong> Sarah AI is triaging your issue and checking technician availability...',
        'simulator'
      );

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        appendMessage('Sarah (JobLatch AI)', data.response, true);
        speakText(data.response);

        if (data.booking) {
          showBookingInHero(data.booking);
          pushCustomerSmsBooking(data.booking);
          setJourneyProgress(
            3,
            `👉 <strong>Next Step (Step 3 of 4):</strong> Work order dispatched! Click <strong>"Authorize $${data.booking.dispatch_fee} Deposit via Stripe"</strong> inside the highlighted phone on the right.`,
            'phone'
          );
        }
        await fetchBoardData();
      } catch (e) {
        appendMessage('System', 'Connection error.', false);
      }
    }

    let ACTIVE_HERO_BOOKING = null;

    function showBookingInHero(booking) {
      ACTIVE_HERO_BOOKING = booking;
      waitingPlaceholder.style.display = 'none';
      dispatchHero.classList.add('active');

      const isEmerg = (booking.urgency_level || '').includes('EMERG') || (booking.service_type || '').toLowerCase() === 'emergency';
      dispatchHero.className = `dispatch-hero active ${isEmerg ? 'is-emergency' : ''}`;

      const bBadge = document.getElementById('heroBadge');
      bBadge.className = `hero-badge ${isEmerg ? 'badge-emergency' : 'badge-standard'}`;
      bBadge.innerText = isEmerg ? '🚨 Code Red Emergency (45m)' : '✓ Confirmed Service Dispatch';

      const payBadge = document.getElementById('heroPayBadge');
      if (booking.payment_status === 'CAPTURED_ON_SITE' || booking.payment_status === 'PAID_VERIFIED') {
        payBadge.style.color = '#15803d';
        payBadge.style.background = '#dcfce7';
        payBadge.style.borderColor = '#86efac';
        payBadge.innerText = `✓ $${booking.dispatch_fee} Captured On-Site`;
      } else if (booking.payment_status === 'AUTHORIZED_HOLD') {
        payBadge.style.color = '#1d4ed8';
        payBadge.style.background = '#dbeafe';
        payBadge.style.borderColor = '#93c5fd';
        payBadge.innerText = `⏳ $${booking.dispatch_fee} Pre-Auth Hold Active`;
      } else if (booking.payment_status === 'RELEASED_CANCELED') {
        payBadge.style.color = '#991b1b';
        payBadge.style.background = '#fee2e2';
        payBadge.style.borderColor = '#fca5a5';
        payBadge.innerText = `⊘ Hold Released (No Charge)`;
      } else {
        payBadge.style.color = '#b45309';
        payBadge.style.background = '#fef3c7';
        payBadge.style.borderColor = '#fde68a';
        payBadge.innerText = `💳 Pending $${booking.dispatch_fee} Hold`;
      }

      // Clean human-readable title & window
      document.getElementById('heroTitle').innerText = booking.display_title || 'Electrical Service Dispatch';
      document.getElementById('heroContractor').innerText = DEFAULT_CONFIG_EMAIL;

      // Populate Triage Credibility Box
      const triageBox = document.getElementById('triageCredibilityBox');
      triageBox.className = `triage-credibility-box ${isEmerg ? 'is-emerg-triage' : ''}`;
      document.getElementById('triageBoxHeader').innerHTML = isEmerg
        ? '🚨 NFPA 70E EMERGENCY TRIAGE &amp; SAFETY DIRECTIVE'
        : '🛡️ AI TECHNICAL TRIAGE &amp; PRE-ARRIVAL CHECK';
      document.getElementById('triageSymptom').innerText = booking.triage_symptom || booking.issue_description || 'Electrical service request';
      document.getElementById('triageHazardLevel').innerText = booking.triage_hazard_level || (isEmerg ? 'NFPA 70E Code Red — Active Thermal Hazard' : 'Routine Service (Non-Hazardous)');
      document.getElementById('triageSafetyGiven').innerText = booking.triage_safety_instruction || 'Stay clear of affected circuit until technician arrives.';

      document.getElementById('tktConf').innerText = booking.confirmation_id;
      document.getElementById('tktCustomer').innerText = booking.customer_name;
      document.getElementById('tktPhone').innerText = booking.phone_number;
      document.getElementById('tktAddress').innerText = booking.service_address;
      document.getElementById('tktTech').innerText = booking.assigned_technician;
      document.getElementById('tktWindow').innerText = booking.display_window || `${booking.slot_date} (${booking.slot_time})`;
      document.getElementById('tktFee').innerText = `$${Number(booking.dispatch_fee || 89).toFixed(2)}`;
      document.getElementById('tktVal').innerText = `$${Number(booking.estimated_job_value || 850).toLocaleString()}`;

      const calBtn = document.getElementById('heroCalBtn');
      if (booking.google_calendar_link) {
        calBtn.href = booking.google_calendar_link;
        calBtn.style.display = 'inline-flex';
      } else {
        calBtn.style.display = 'none';
      }
      if (typeof renderTechTabletView === 'function') {
        renderTechTabletView(booking);
      }
    }

    function pushCustomerSmsBooking(booking) {
      const cleanWin = booking.display_window || 'Today, within 45–60 min';
      const techShort = (booking.assigned_technician || 'Marcus Vance').split('(')[0].trim();
      const truckShort = (booking.truck_id || 'TRUCK-01').split('(')[0].trim();
      const isFinalPaid = Boolean(booking.final_balance_paid);
      const isHold = booking.payment_status === 'AUTHORIZED_HOLD';
      const isCaptured = booking.payment_status === 'CAPTURED_ON_SITE' || booking.payment_status === 'PAID_VERIFIED' || isFinalPaid;
      const isCanceled = booking.payment_status === 'RELEASED_CANCELED';
      const isPaid = isCaptured;
      const photoInfo = booking.panel_photo_analysis || {};
      const photoUploaded = Boolean(photoInfo.uploaded);
      const selTier = (booking.selected_option_tier || 'GOOD').toUpperCase();
      const quoteOpts = booking.quote_options || [];
      const fee = Number(booking.dispatch_fee || 89);
      const totalVal = Number(booking.estimated_job_value || 1200);
      const remBalance = isFinalPaid ? 0 : Math.max(0, totalVal - (isPaid ? fee : 0));

      let stripeButtonHtml = '';
      if (isCaptured) {
        stripeButtonHtml = `
          <button class="btn-stripe-pay paid" disabled style="background:#15803d; color:#fff;">✓ $${fee} Diagnostic Fee Settled &amp; Captured</button>
          <div style="margin-top:6px; font-size:0.72rem; color:#86efac; line-height:1.35;">
            ✓ Captured upon technician on-site arrival • Applied toward final work order.
          </div>
        `;
      } else if (isHold) {
        stripeButtonHtml = `
          <button class="btn-stripe-pay" disabled style="background:#1d4ed8; color:#fff; cursor:default;">⏳ $${fee} Pre-Auth Hold Active (Card Not Charged)</button>
          <div style="margin-top:6px; font-size:0.72rem; color:#bfdbfe; line-height:1.35; background:rgba(30,58,138,0.3); border:1px solid #3b82f6; border-radius:6px; padding:6px 8px;">
            ℹ️ <strong>Card-Brand Disclosure:</strong> An authorization hold of $${fee} has been placed to reserve your technician. Your card will not be charged until the technician arrives at your property.
          </div>
        `;
      } else if (isCanceled) {
        stripeButtonHtml = `
          <button class="btn-stripe-pay" disabled style="background:#475569; color:#cbd5e1;">⊘ Pre-Auth Hold Dropped / Canceled</button>
          <div style="margin-top:6px; font-size:0.72rem; color:#94a3b8; line-height:1.35;">
            ✓ Hold released immediately upon cancellation. Zero card charges incurred.
          </div>
        `;
      } else {
        stripeButtonHtml = `
          <button class="btn-stripe-pay" onclick="payStripeDeposit('${booking.confirmation_id}')">👉 Place $${fee} Authorization Hold</button>
          <div style="margin-top:6px; font-size:0.72rem; color:#cbd5e1; line-height:1.35;">
            🔒 <strong>2-Step Guarantee:</strong> Places a temporary hold to reserve your slot. Funds are <strong>only charged once our electrician arrives on-site</strong>.
          </div>
        `;
      }

      const photoCardHtml = photoUploaded
        ? `
          <div style="margin-top:8px; background:rgba(22,163,74,0.22); border:1px solid #4ade80; border-radius:8px; padding:8px 10px; font-size:0.8rem;">
            <div style="font-weight:800; color:#4ade80; margin-bottom:2px;">📸 PANEL PHOTO VERIFIED BY SARAH AI ✓</div>
            <div style="color:#f8fafc; font-weight:700;">${photoInfo.equipment_detected || '200A Main Breaker Panel'}</div>
            <div style="color:#cbd5e1; font-size:0.76rem; margin-top:2px;">${photoInfo.parts_verification || 'Exact breaker series loaded on truck'}</div>
          </div>
        `
        : `
          <div style="margin-top:8px; background:rgba(15,23,42,0.55); border:1px dashed #93c5fd; border-radius:8px; padding:8px 10px; font-size:0.8rem;">
            <div style="font-weight:800; color:#93c5fd; margin-bottom:3px;">📸 OPTIONAL: 1-TAP PANEL / OUTLET PRE-CHECK</div>
            <div style="color:#e2e8f0; font-size:0.76rem; margin-bottom:6px;">Snap your breaker panel or outlet so ${techShort} brings the exact breaker on ${truckShort}:</div>
            <button onclick="simulateCustomerPhotoUpload('${booking.confirmation_id}')" style="width:100%; background:#0284c7; color:#ffffff; border:none; border-radius:6px; padding:7px 10px; font-weight:800; font-size:0.8rem; cursor:pointer;">
              📸 Simulate Customer Panel Photo Upload
            </button>
          </div>
        `;

      const fsmName = booking.fsm_name || 'Housecall Pro';
      const fsmIcon = booking.fsm_icon || '🏠';
      const fsmTicketId = booking.fsm_ticket_id || ('HCP-' + (booking.confirmation_id || '8921').replace(/\D/g, '').slice(-4));
      const fsmUrl = booking.fsm_url || 'https://app.housecallpro.com/jobs';
      const fsmBtnLabel = booking.fsm_button_label || `Open in ${fsmName}`;
      const fsmColor = booking.fsm_accent_color || '#0284c7';

      const fsmBridgeHtml = `
        <div class="sms-bubble" style="border-left:3px solid ${fsmColor};">
          <div class="sms-tag" style="color:#38bdf8; display:flex; justify-content:space-between; align-items:center;">
            <span>${fsmIcon} Synced with ${fsmName}</span>
            <span style="background:rgba(56,189,248,0.18); color:#38bdf8; padding:2px 6px; border-radius:4px; font-weight:800; font-size:0.72rem;">Job #${fsmTicketId}</span>
          </div>
          <div style="font-size:0.78rem; color:#e2e8f0; margin-bottom:8px; line-height:1.4;">
            Your dispatch details and upfront diagnostic deposit have been synchronized with <strong>${fsmName}</strong>.
          </div>
          <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(148,163,184,0.25); border-radius:7px; padding:7px 9px; margin-bottom:8px; font-size:0.75rem;">
            <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
              <span style="color:#cbd5e1;">Upfront Diagnostic Deposit:</span>
              <span style="color:#4ade80; font-weight:800;">-$${fee.toFixed(2)} Credited</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
              <span style="color:#cbd5e1;">Assigned Field Unit:</span>
              <span style="color:#f8fafc; font-weight:700;">${techShort} &bull; 🚐 ${truckShort}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:#cbd5e1;">Municipal E-Permit / 25C:</span>
              <span style="color:#facc15; font-weight:700;">${booking.rebate_summary || 'Eligible ($600 Tax Credit)'}</span>
            </div>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <a href="${fsmUrl}" target="_blank" style="flex:1; text-align:center; background:${fsmColor}; color:#ffffff; text-decoration:none; border-radius:6px; padding:6px 10px; font-weight:800; font-size:0.76rem; display:inline-block;">
              ↗ ${fsmBtnLabel}
            </a>
            <button onclick="openFsmPayloadModal('${booking.confirmation_id}')" style="background:#0f172a; color:#94a3b8; border:1px solid rgba(148,163,184,0.4); border-radius:6px; padding:6px 8px; font-size:0.74rem; font-weight:700; cursor:pointer;">
              📋 View Payload
            </button>
          </div>
        </div>
      `;

      const enRouteHtml = booking.en_route_sent
        ? `
          <div class="sms-bubble" style="border-left:3px solid #38bdf8;">
            <div class="sms-tag" style="color:#38bdf8;">🚐 Live GPS Dispatch Tracker</div>
            <strong>${techShort}</strong> is en route in <strong>🚐 ${truckShort}</strong>!<br>
            <span style="font-size:0.82rem; color:#cbd5e1;">📍 Live GPS ETA: <strong>14 mins</strong> &bull; Parts &amp; Breaker Loaded ✓</span>
          </div>
        `
        : '';

      const reviewHtml = booking.review_requested
        ? `
          <div class="sms-bubble" style="border-left:3px solid #facc15;">
            <div class="sms-tag" style="color:#facc15;">⭐ Job Complete • 5-Star Review</div>
            Thank you for choosing JobLatch AI Electrical, ${booking.customer_name}! Tap below to leave ${techShort} a 5-star Google review:<br>
            <span style="display:inline-block; margin-top:5px; background:#f59e0b; color:#0f172a; font-weight:800; font-size:0.78rem; padding:4px 10px; border-radius:6px;">⭐⭐⭐⭐⭐ Leave Google Review &rarr;</span>
          </div>
        `
        : '';

      const smsHtml = `
        <div class="sms-bubble">
          <div class="sms-tag">Appointment Dispatched • 🚐 ${truckShort}</div>
          Hi ${booking.customer_name}, your electrician <strong>${techShort}</strong> is scheduled for <strong>${cleanWin}</strong>.
          <div class="sms-stripe-sheet">
            <div style="display:flex; justify-content:space-between; font-weight:800; font-size:0.86rem; color:#c7d2fe;">
              <span>💳 STRIPE UPFRONT DEPOSIT</span>
              <span style="color:#4ade80;">$${fee.toFixed(2)}</span>
            </div>
            ${stripeButtonHtml}
          </div>
          ${photoCardHtml}
        </div>
        ${fsmBridgeHtml}
        ${enRouteHtml}
        ${reviewHtml}
      `;
      phoneMessages.innerHTML = smsHtml;
      phoneMessages.scrollTop = phoneMessages.scrollHeight;
      if (typeof renderTechTabletView === 'function') {
        renderTechTabletView(booking);
      }
    }

    async function selectCustomerQuoteOption(confirmationId, tier) {
      if (!confirmationId && ACTIVE_HERO_BOOKING) confirmationId = ACTIVE_HERO_BOOKING.confirmation_id;
      if (!confirmationId) return;
      const res = await fetch('/api/bookings/select-option', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: confirmationId, tier })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        const b = data.booking;
        const addAmt = Number(b.upsell_added_amount || 0);
        appendMessage(
          'JobLatch AI Proposal Engine',
          `📑 Homeowner selected <strong>${b.selected_option_tier} Package</strong>${addAmt > 0 ? ` (+$${addAmt} Add-On)` : ''} — Ticket updated to <strong>$${Number(b.estimated_job_value).toLocaleString()}</strong>!`,
          true
        );
        showBookingInHero(b);
        pushCustomerSmsBooking(b);
        renderTechTabletView(b);
        await fetchBoardData();
        if (document.getElementById('ticketDossierModal').classList.contains('active')) {
          openTicketDossierModal(b);
        }
      }
    }

    async function payCustomerFinalBalance(confirmationId) {
      if (!confirmationId && ACTIVE_HERO_BOOKING) confirmationId = ACTIVE_HERO_BOOKING.confirmation_id;
      if (!confirmationId) return;
      const res = await fetch('/api/bookings/pay-balance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: confirmationId })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        const b = data.booking;
        appendMessage(
          'Stripe Payment Gateway',
          `💰 <strong>FINAL INVOICE PAID IN FULL:</strong> ${b.customer_name} completed full payment of <strong>$${Number(b.estimated_job_value).toLocaleString()}.00</strong> (${b.selected_option_tier} Package). Work order closed!`,
          true
        );
        setJourneyStep(3);
        showBookingInHero(b);
        pushCustomerSmsBooking(b);
        renderTechTabletView(b);
        await fetchBoardData();
        if (document.getElementById('ticketDossierModal').classList.contains('active')) {
          openTicketDossierModal(b);
        }
      }
    }

    async function simulateCustomerPhotoUpload(confirmationId) {
      if (!confirmationId && ACTIVE_HERO_BOOKING) confirmationId = ACTIVE_HERO_BOOKING.confirmation_id;
      if (!confirmationId) return;
      const res = await fetch('/api/bookings/upload-photo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: confirmationId })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        const pInfo = data.booking.panel_photo_analysis || {};
        appendMessage(
          'Sarah AI Vision (Panel Pre-Check)',
          `📸 Analyzed homeowner photo (${pInfo.photo_label || 'panel.jpg'}): Detected <strong>${pInfo.equipment_detected}</strong>. Required part: <strong>${pInfo.breaker_spec}</strong> (${pInfo.open_spaces}). Verified on ${data.booking.truck_id}!`,
          true
        );
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        renderTechTabletView(data.booking);
        await fetchBoardData();
        if (document.getElementById('ticketDossierModal').classList.contains('active')) {
          openTicketDossierModal(data.booking);
        }
      }
    }

    /* ELECTRICIAN IN-TRUCK TABLET WORKFLOW & TWO-WAY SYNC */
    let CURRENT_DEVICE_MODE = 'customer';
    let TECH_SIG_CANVAS_INIT = false;

    function switchDeviceMode(mode) {
      CURRENT_DEVICE_MODE = mode;
      const btnCust = document.getElementById('btnDeviceCustomer');
      const btnTech = document.getElementById('btnDeviceTech');
      const chassis = document.getElementById('phoneChassis');
      const custView = document.getElementById('customerPhoneView');
      const techView = document.getElementById('techTabletView');

      if (mode === 'tech') {
        if (btnCust) btnCust.classList.remove('active');
        if (btnTech) btnTech.classList.add('active');
        if (chassis) chassis.classList.add('tech-tablet-mode');
        if (custView) custView.style.display = 'none';
        if (techView) techView.style.display = 'flex';
        initTechSignatureCanvas();
        if (ACTIVE_HERO_BOOKING) renderTechTabletView(ACTIVE_HERO_BOOKING);
      } else {
        if (btnCust) btnCust.classList.add('active');
        if (btnTech) btnTech.classList.remove('active');
        if (chassis) chassis.classList.remove('tech-tablet-mode');
        if (custView) custView.style.display = 'flex';
        if (techView) techView.style.display = 'none';
      }
    }

    function initTechSignatureCanvas() {
      const canvas = document.getElementById('techSigCanvas');
      if (!canvas || TECH_SIG_CANVAS_INIT) return;
      TECH_SIG_CANVAS_INIT = true;
      const ctx = canvas.getContext('2d');
      let isDrawing = false;
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';

      function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
          x: (clientX - rect.left) * (canvas.width / rect.width),
          y: (clientY - rect.top) * (canvas.height / rect.height)
        };
      }

      function startDraw(e) {
        isDrawing = true;
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
      }
      function draw(e) {
        if (!isDrawing) return;
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
      }
      function endDraw() {
        isDrawing = false;
      }

      canvas.addEventListener('mousedown', startDraw);
      canvas.addEventListener('mousemove', draw);
      window.addEventListener('mouseup', endDraw);
      canvas.addEventListener('touchstart', (e) => { e.preventDefault(); startDraw(e); }, { passive: false });
      canvas.addEventListener('touchmove', (e) => { e.preventDefault(); draw(e); }, { passive: false });
      window.addEventListener('touchend', endDraw);
    }

    function techClearSignature() {
      const canvas = document.getElementById('techSigCanvas');
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      const tsEl = document.getElementById('techSigTimestamp');
      if (tsEl) tsEl.style.display = 'none';
    }

    function techAdoptSignature() {
      const canvas = document.getElementById('techSigCanvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.font = 'italic 24px "Brush Script MT", cursive, sans-serif';
      const name = (ACTIVE_HERO_BOOKING && ACTIVE_HERO_BOOKING.customer_name) || 'David Miller';
      ctx.fillStyle = '#38bdf8';
      ctx.fillText(name, 20, 36);
      techAuthorizeScopeAction();
    }

    function renderTechTabletView(booking) {
      if (!booking) return;
      const techShort = (booking.assigned_technician || 'Marcus Vance').split('(')[0].trim();
      const truckShort = (booking.truck_id || 'TRUCK-01').split('(')[0].trim();
      const isFinalPaid = Boolean(booking.final_balance_paid);
      const isHold = booking.payment_status === 'AUTHORIZED_HOLD';
      const isCaptured = booking.payment_status === 'CAPTURED_ON_SITE' || booking.payment_status === 'PAID_VERIFIED' || isFinalPaid;
      const isPaid = isCaptured;
      const isEnRoute = Boolean(booking.en_route_sent);
      const fee = Number(booking.dispatch_fee || 89);
      const totalVal = Number(booking.estimated_job_value || 1200);
      const selTier = (booking.selected_option_tier || 'GOOD').toUpperCase();
      const remBalance = isFinalPaid ? 0 : Math.max(0, totalVal - (isPaid ? fee : 0));

      const truckEl = document.getElementById('techTabletTruckId');
      if (truckEl) truckEl.innerText = `${truckShort} (${techShort})`;

      const badge = document.getElementById('techWorkflowBadge');
      if (badge) {
        if (isFinalPaid) {
          badge.style.background = '#16a34a';
          badge.innerText = 'PAID IN FULL';
        } else if (booking.customer_signature_timestamp) {
          badge.style.background = '#059669';
          badge.innerText = 'AUTHORIZED';
        } else if (booking.diagnostic_readings && booking.diagnostic_readings.recorded_at) {
          badge.style.background = '#7c3aed';
          badge.innerText = 'DIAGNOSTIC SEALED';
        } else if (isEnRoute) {
          badge.style.background = '#0284c7';
          badge.innerText = 'EN ROUTE';
        } else {
          badge.style.background = '#dc2626';
          badge.innerText = 'DISPATCHED';
        }
      }

      const nameAddr = document.getElementById('techCustNameAddress');
      if (nameAddr) nameAddr.innerText = `${booking.customer_name || 'David Miller'} • ${booking.service_address || '742 Evergreen Terrace'}`;
      const phoneWin = document.getElementById('techCustPhoneWindow');
      if (phoneWin) phoneWin.innerText = `${booking.phone_number || '(555) 482-9104'} • Scheduled: ${booking.display_window || 'Today, within 45–60 min'}`;

      const enRouteBtn = document.getElementById('techEnRouteActionBtn');
      if (enRouteBtn) {
        if (isEnRoute) {
          enRouteBtn.innerText = '✓ En Route (GPS 14m ETA)';
          enRouteBtn.style.background = '#16a34a';
        } else {
          enRouteBtn.innerText = '🚐 Mark En Route';
          enRouteBtn.style.background = '#2563eb';
        }
      }

      const hazText = document.getElementById('techHazardText');
      if (hazText) hazText.innerText = booking.triage_hazard_level || 'NFPA 70E Code Red — Active Thermal / Fire Risk';
      const safeText = document.getElementById('techSafetyText');
      if (safeText) safeText.innerText = booking.triage_safety_instruction || 'Shut off circuit breaker immediately; do not touch scorched outlets.';

      const photo = booking.panel_photo_analysis || {};
      const panelStock = document.getElementById('techPanelStockText');
      if (panelStock) {
        panelStock.innerText = `${photo.equipment_detected || 'Square D QO 150A Main Panel'} • ${photo.breaker_spec || 'Square D QO120DF AFCI/GFCI'} Loaded on ${truckShort} ✓`;
      }

      const diags = booking.diagnostic_readings || {};
      const vEl = document.getElementById('techInputVoltage');
      if (vEl && diags.voltage_l1_l2) vEl.value = diags.voltage_l1_l2;
      const aEl = document.getElementById('techInputAmps');
      if (aEl && diags.panel_amps) aEl.value = diags.panel_amps;
      const tEl = document.getElementById('techInputThermal');
      if (tEl && diags.thermal_hotspot) tEl.value = diags.thermal_hotspot;
      const trqEl = document.getElementById('techInputTorque');
      if (trqEl && diags.lug_torque) trqEl.value = diags.lug_torque;

      const diagBadge = document.getElementById('techDiagStatusBadge');
      if (diagBadge) {
        if (diags.recorded_at) {
          diagBadge.style.color = '#4ade80';
          diagBadge.innerText = `✓ Recorded (${diags.recorded_at})`;
        } else {
          diagBadge.style.color = '#a855f7';
          diagBadge.innerText = 'Ready to Record';
        }
      }

      // Stage 4: Connected Invoicing & FSM Bridge
      const fsmName = booking.fsm_name || 'Housecall Pro';
      const fsmIcon = booking.fsm_icon || '🏠';
      const fsmTicketId = booking.fsm_ticket_id || ('HCP-' + (booking.confirmation_id || '8921').replace(/\D/g, '').slice(-4));
      const fsmUrl = booking.fsm_url || 'https://app.housecallpro.com/jobs';
      const fsmBtnLabel = booking.fsm_tech_label || `↗ Open Job & Price Book in ${fsmName}`;
      const fsmColor = booking.fsm_accent_color || '#2563eb';

      const fsmStageTitle = document.getElementById('techFsmStageTitle');
      if (fsmStageTitle) fsmStageTitle.innerHTML = `${fsmIcon} ${fsmName} Scope &amp; Authorization`;

      const fsmPill = document.getElementById('techFsmTicketPill');
      if (fsmPill) fsmPill.innerText = fsmTicketId;

      const fsmNameDisp = document.getElementById('techFsmNameDisplay');
      if (fsmNameDisp) fsmNameDisp.innerText = fsmName;

      const fsmDepositDisp = document.getElementById('techFsmDepositDisplay');
      if (fsmDepositDisp) {
        if (isCaptured) {
          fsmDepositDisp.innerText = `-$${fee.toFixed(2)} (Stripe Captured ✓)`;
          fsmDepositDisp.style.color = '#4ade80';
        } else if (isHold) {
          fsmDepositDisp.innerText = `-$${fee.toFixed(2)} (Pre-Auth Hold Active)`;
          fsmDepositDisp.style.color = '#60a5fa';
        } else {
          fsmDepositDisp.innerText = `-$${fee.toFixed(2)} (Pending)`;
          fsmDepositDisp.style.color = '#fbbf24';
        }
      }

      const fsmLinkBtn = document.getElementById('techFsmDeepLinkBtn');
      if (fsmLinkBtn) {
        fsmLinkBtn.href = fsmUrl;
        fsmLinkBtn.style.background = fsmColor;
      }
      const fsmBtnText = document.getElementById('techFsmButtonText');
      if (fsmBtnText) fsmBtnText.innerText = fsmBtnLabel;

      const sigTsEl = document.getElementById('techSigTimestamp');
      if (sigTsEl) {
        if (booking.customer_signature_timestamp) {
          sigTsEl.style.display = 'block';
          sigTsEl.innerText = `✓ ${booking.customer_signature_timestamp}`;
        } else {
          sigTsEl.style.display = 'none';
        }
      }

      const balAmt = document.getElementById('techBalanceDueAmt');
      if (balAmt) balAmt.innerText = `$${remBalance.toLocaleString()}.00`;

      const finBadge = document.getElementById('techFinalPayStatusPill');
      const finBtn = document.getElementById('techFinalCollectBtn');
      if (isFinalPaid) {
        if (finBadge) {
          finBadge.style.color = '#4ade80';
          finBadge.innerText = '✓ PAID IN FULL';
        }
        if (finBtn) {
          finBtn.innerText = '✓ Final Balance Paid in Full via Stripe';
          finBtn.style.background = '#16a34a';
          finBtn.disabled = true;
        }
      } else {
        if (finBadge) {
          finBadge.style.color = '#fbbf24';
          finBadge.innerText = 'PENDING';
        }
        if (finBtn) {
          finBtn.innerText = `💳 Collect $${remBalance.toLocaleString()} Final Balance via Stripe`;
          finBtn.style.background = '#16a34a';
          finBtn.disabled = false;
        }
      }

      const revBtn = document.getElementById('techReviewActionBtn');
      if (revBtn) {
        if (booking.review_requested) {
          revBtn.innerText = '✓ 5-Star Review Request Sent to Phone';
          revBtn.style.background = '#16a34a';
        } else {
          revBtn.innerText = '⭐ Request 5-Star Google Review SMS';
          revBtn.style.background = '#d97706';
        }
      }
    }

    async function techTriggerEnRoute() {
      if (!ACTIVE_HERO_BOOKING) return;
      const res = await fetch('/api/bookings/en-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_HERO_BOOKING.confirmation_id })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        const techShort = (data.booking.assigned_technician || 'Marcus Vance').split('(')[0].trim();
        const truckShort = (data.booking.truck_id || 'TRUCK-01').split('(')[0].trim();
        appendMessage('In-Truck Tablet (TRUCK-01)', `🚐 ${techShort} hit "Mark En Route" on tablet! Pushed live GPS tracking link (ETA 14m) to homeowner's phone.`, true);
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        renderTechTabletView(data.booking);
        await fetchBoardData();
      }
    }

    async function techSaveDiagnosticsAction() {
      if (!ACTIVE_HERO_BOOKING) return;
      const readings = {
        voltage_l1_l2: document.getElementById('techInputVoltage').value,
        panel_amps: document.getElementById('techInputAmps').value,
        thermal_hotspot: document.getElementById('techInputThermal').value,
        ground_bond_pass: true,
        lug_torque: document.getElementById('techInputTorque').value,
        recorded_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' (Tablet Logged)'
      };
      const res = await fetch('/api/tech/save-diagnostics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_HERO_BOOKING.confirmation_id, readings })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        appendMessage('In-Truck Tablet (TRUCK-01)', `🔬 Marcus Vance recorded on-site electrical diagnostics (${readings.voltage_l1_l2}, ${readings.thermal_hotspot}, ${readings.lug_torque}). Sealed on Work Order PDF!`, true);
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        renderTechTabletView(data.booking);
        await fetchBoardData();
      }
    }

    async function techAuthorizeScopeAction() {
      if (!ACTIVE_HERO_BOOKING) return;
      const custName = ACTIVE_HERO_BOOKING.customer_name || 'David Miller';
      const res = await fetch('/api/tech/sign-authorization', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_HERO_BOOKING.confirmation_id, signer_name: custName })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        appendMessage('In-Truck Tablet (TRUCK-01)', `✍️ Homeowner ${custName} signed digital work authorization on Marcus Vance's tablet! Scope locked.`, true);
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        renderTechTabletView(data.booking);
        await fetchBoardData();
      }
    }

    async function techCollectFinalBalanceAction() {
      if (!ACTIVE_HERO_BOOKING) return;
      await payCustomerFinalBalance(ACTIVE_HERO_BOOKING.confirmation_id);
    }

    async function techSendReviewSmsAction() {
      if (!ACTIVE_HERO_BOOKING) return;
      const res = await fetch('/api/bookings/request-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_HERO_BOOKING.confirmation_id })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        appendMessage('In-Truck Tablet (TRUCK-01)', `⭐ Sent 1-Tap 5-Star Google Review request SMS to ${data.booking.customer_name} from tablet!`, true);
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        renderTechTabletView(data.booking);
        await fetchBoardData();
      }
    }

    // STEP 1 -> STEP 2: Simulate Dropped Call
    async function simulateMissedCallLead() {
      applyScenarioJourneyLabels('missed_call');
      try {
        const res = await fetch('/api/simulate-missed-call', { method: 'POST' });
        const data = await res.json();
        const mc = data.missed_call || {};

        const smsHtml = `
          <div class="sms-bubble sms-recoup-card" id="smsCard_${mc.missed_call_id}">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
              <span style="background:rgba(245,158,11,0.25); color:#fbbf24; font-size:0.78rem; font-weight:800; padding:3px 9px; border-radius:4px;">⚠️ MISSED CALL RECOVERY</span>
              <span style="font-size:0.8rem; color:#cbd5e1;">3s ago</span>
            </div>
            <div>
              Hi! This is Sarah from JobLatch AI Electrical. We noticed your call dropped! Tap below to lock in tomorrow's 8:00 AM slot right now:
            </div>
            <div class="sms-action-card" onclick="convertMissedCallLead('${mc.missed_call_id}')">
              <div style="font-size:0.82rem; font-weight:800; color:#4ade80;">⚡ 1-TAP SELF-SCHEDULE ($1,200 JOB)</div>
              <div style="font-size:0.98rem; font-weight:800; color:#ffffff; margin:4px 0;">Tomorrow, 8:00 AM &bull; Tech: Sarah Chen (🚐 TRUCK-03)</div>
              <button class="btn-action-claim" id="btnClaim_${mc.missed_call_id}">
                👉 Tap to Confirm &amp; Book ($1,200)
              </button>
            </div>
          </div>
        `;
        phoneMessages.innerHTML = smsHtml;
        phoneMessages.scrollTop = phoneMessages.scrollHeight;

        chatStream.innerHTML = '';
        appendMessage('System Alert', `📵 Caller from ${mc.caller_phone || '(555) 329-8471'} hung up after hours. $1,200 EV Charger job at risk of calling a competitor.`, false);
        appendMessage('Sarah (3s SMS Recovery)', `⚡ Sent instant self-scheduling SMS link to the homeowner's phone in 2.8 seconds.`, true);

        setJourneyProgress(
          2,
          '👉 <strong>Next Step (Step 2 of 4):</strong> Look at the highlighted <strong>Customer Phone</strong> on the right and click <strong>"Tap to Confirm &amp; Book ($1,200)"</strong>.',
          'phone'
        );

        await fetchBoardData();
      } catch (e) {
        alert('Error simulating missed call.');
      }
    }

    // STEP 2 -> STEP 3: Customer Taps Self-Schedule Link
    async function convertMissedCallLead(mcId) {
      try {
        const res = await fetch('/api/missed-calls/convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ missed_call_id: mcId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          if (data.booking) {
            showBookingInHero(data.booking);
            pushCustomerSmsBooking(data.booking);
          }

          appendMessage('Sarah (JobLatch AI)', `✓ Customer booked Tomorrow 8:00 AM – 12:00 PM with Sarah Chen ($1,200 Pipeline Booked). Awaiting $89 Stripe deposit to lock in Revenue Won.`, true);

          setJourneyProgress(
            3,
            '👉 <strong>Next Step (Step 3 of 4):</strong> Slot booked! Now click <strong>"Authorize $89 Deposit via Stripe"</strong> (or test <strong>"📸 Simulate Customer Panel Photo Upload"</strong>) inside the phone.',
            'phone'
          );

          await fetchBoardData();
        }
      } catch (e) {
        alert('Error converting missed call.');
      }
    }

    // STEP 3 -> STEP 4: Place Stripe Pre-Authorization Hold
    async function payStripeDeposit(confirmationId) {
      if (!confirmationId && BOARD_DATA.bookings && BOARD_DATA.bookings.length) {
        confirmationId = BOARD_DATA.bookings[BOARD_DATA.bookings.length - 1].confirmation_id;
      }
      try {
        const res = await fetch('/api/bookings/hold', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation_id: confirmationId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          const feePaid = data.booking ? data.booking.dispatch_fee : 89;
          const jobVal = data.booking ? data.booking.estimated_job_value : 1200;
          const pid = data.booking ? data.booking.stripe_payment_intent_id : 'pi_hold';
          appendMessage('JobLatch AI Billing', `🔒 $${Number(feePaid).toFixed(2)} authorization hold placed via Stripe (${pid}, capture_method=manual). Card will NOT be charged until technician arrives on-site.`, true);

          setJourneyProgress(
            4,
            `🔒 <strong>Pre-Auth Hold Placed!</strong> $${feePaid} hold active on card — <strong>$${Number(jobVal).toLocaleString()} Revenue Won</strong> locked!`,
            'complete'
          );
          document.getElementById('jStep4').classList.remove('active-step');
          document.getElementById('jStep4').classList.add('done-step');
          document.getElementById('jNum4').innerText = '✓';

          await fetchBoardData();
        }
      } catch (e) {
        alert('Payment hold error.');
      }
    }

    async function captureStripeHold(confirmationId) {
      if (!confirmationId && BOARD_DATA.bookings && BOARD_DATA.bookings.length) {
        confirmationId = BOARD_DATA.bookings[BOARD_DATA.bookings.length - 1].confirmation_id;
      }
      try {
        const res = await fetch('/api/bookings/capture', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation_id: confirmationId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          const fee = data.booking ? data.booking.dispatch_fee : 89;
          const pid = data.booking ? data.booking.stripe_payment_intent_id : '';
          appendMessage('JobLatch AI Billing', `⚡ Tech arrived on-site! Pre-authorized $${Number(fee).toFixed(2)} hold captured & settled via Stripe Connect (Intent: ${pid}).`, true);
          await fetchBoardData();
        }
      } catch (e) {
        alert('Capture error.');
      }
    }

    async function releaseStripeHold(confirmationId) {
      if (!confirmationId && BOARD_DATA.bookings && BOARD_DATA.bookings.length) {
        confirmationId = BOARD_DATA.bookings[BOARD_DATA.bookings.length - 1].confirmation_id;
      }
      try {
        const res = await fetch('/api/bookings/release', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation_id: confirmationId, reason: 'customer_cancellation' })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          appendMessage('JobLatch AI Billing', `⊘ Pre-authorization hold dropped immediately upon cancellation. Zero card charges incurred.`, true);
          await fetchBoardData();
        }
      } catch (e) {
        alert('Release error.');
      }
    }

    async function toggleBenchmarkMode() {
      await fetch('/api/benchmark/toggle', { method: 'POST' });
      await fetchBoardData();
    }

    async function saveContractorEmail() {
      const email = contractorInput.value.trim();
      if (!email) return;
      await fetch('/api/set-contractor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      DEFAULT_CONFIG_EMAIL = email;
      document.getElementById('heroContractor').innerText = email;
      alert(`Demo alert email updated to: ${email}`);
    }

    async function runScenario(scenarioKey) {
      applyScenarioJourneyLabels(scenarioKey === 'emergency' ? 'emergency' : 'routine');
      chatStream.innerHTML = '';
      const res = await fetch('/api/run-scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioKey })
      });
      const data = await res.json();

      for (let i = 0; i < data.dialogue.length; i++) {
        const item = data.dialogue[i];
        appendMessage(item.speaker, item.text, item.isSarah);
        if (i === data.dialogue.length - 1 && item.isSarah) speakText(item.text);
      }

      if (data.booking) {
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        const fee = data.booking.dispatch_fee || (scenarioKey === 'emergency' ? 149 : 89);
        setJourneyProgress(
          3,
          `👉 <strong>Next Step (Step 3 of 4):</strong> ${scenarioKey === 'emergency' ? 'Code Red Emergency' : 'Service'} dispatched! Click <strong>"Authorize $${fee} Deposit via Stripe"</strong> inside the highlighted phone.`,
          'phone'
        );
      }
      await fetchBoardData();
    }

    async function resetCall() {
      await fetch('/api/reset', { method: 'POST' });
      applyScenarioJourneyLabels('missed_call');
      chatStream.innerHTML = `
        <div class="bubble bubble-sarah">
          <div class="speaker-name">Sarah (JobLatch AI Dispatcher)</div>
          Thank you for calling JobLatch AI Electrical 24/7 Dispatch. Click <strong>"▶ Start Demo"</strong> above, press <strong>"🎙️ Speak to Sarah"</strong>, or type any electrical issue below!
        </div>
      `;
      dispatchHero.classList.remove('active');
      waitingPlaceholder.style.display = 'flex';
      phoneMessages.innerHTML = `
        <div class="sms-bubble">
          <div class="sms-tag">Customer Phone Preview</div>
          When Sarah sends a 3-second missed-call recovery link or Stripe deposit prompt, it appears right here for the homeowner to tap.
        </div>
      `;
      setJourneyProgress(
        1,
        '👉 <strong>What to do first:</strong> Click <strong>"▶ Start Demo: Simulate Dropped Call"</strong> or <strong>"🎙️ Speak to Sarah AI"</strong> below.',
        'simulator'
      );
      fetchBoardData();
    }

    function applyBoardData(data, animate = true) {
      BOARD_DATA = data;
      if (data.contractor_email) {
        DEFAULT_CONFIG_EMAIL = data.contractor_email;
        contractorInput.value = data.contractor_email;
      }
      if (data.active_fsm_platform) {
        const fsmSelect = document.getElementById('fsmPlatformSelect');
        if (fsmSelect) fsmSelect.value = data.active_fsm_platform;
      }

      const bookingsCount = (data.bookings || []).length;
      const techsCount = (data.technicians || []).length;
      document.getElementById('calCountPill').innerText = bookingsCount;
      document.getElementById('techCountPill').innerText = techsCount;

      const roi = data.roi_metrics || {};
      const isBench = roi.is_benchmark || false;

      const btnBench = document.getElementById('btnBenchmarkToggle');
      const indBench = document.getElementById('benchmarkIndicator');
      if (btnBench && indBench) {
        if (isBench) {
          btnBench.innerHTML = '<span>🎯 Return to Live Demo Session</span><span class="bench-pill-highlight">$0 Baseline</span>';
          indBench.innerText = '📈 30-Day Contractor Benchmark (Projected Data)';
          indBench.style.background = '#dcfce7';
          indBench.style.color = '#15803d';
        } else {
          btnBench.innerHTML = '<span>📈 Preview 30-Day Contractor Benchmark</span><span class="bench-pill-highlight">+$18,450 / mo</span>';
          indBench.innerText = '🧪 Simulated Demo Session Data';
          indBench.style.background = '#e0e7ff';
          indBench.style.color = '#1e1b4b';
        }
      }

      // 1. PIPELINE BOOKED vs REVENUE WON (Only "Revenue Won" once deposit is paid!)
      const pipelineBooked = Math.round(roi.total_pipeline_revenue || 0);
      const revenueWon = Math.round(roi.revenue_won || 0);
      const paidCount = roi.paid_count || 0;
      const elPipe = document.getElementById('kpiPipelineRev');
      const elPipeLabel = document.getElementById('kpiPipelineLabel');
      const elPipeSub = document.getElementById('kpiPipelineSub');
      const cardPipe = document.getElementById('cardMetricPipeline');

      if (isBench) {
        elPipeLabel.innerText = 'Revenue Won (30-Day Benchmark)';
        elPipe.style.color = '#15803d';
        elPipeSub.innerText = '18 Monthly Dispatches • Deposits Verified';
        animateMetricCountUp(elPipe, cardPipe, animate ? PREV_METRICS.pipeline : 18450, 18450, v => `$${v.toLocaleString()}`);
        PREV_METRICS.pipeline = 18450;
      } else if (revenueWon > 0) {
        elPipeLabel.innerText = 'Revenue Won (Deposit Locked)';
        elPipe.style.color = '#15803d';
        elPipeSub.innerText = `✓ ${paidCount} Job${paidCount === 1 ? '' : 's'} Locked In with Paid Deposit`;
        animateMetricCountUp(elPipe, cardPipe, animate ? PREV_METRICS.pipeline : revenueWon, revenueWon, v => `$${v.toLocaleString()}`);
        PREV_METRICS.pipeline = revenueWon;
      } else if (pipelineBooked > 0) {
        const liveBookingsCount = (data.bookings || []).filter(b => !b.is_demo_seed).length;
        elPipeLabel.innerText = 'Pipeline Booked (Pending Deposit)';
        elPipe.style.color = '#2563eb';
        elPipeSub.innerText = `${liveBookingsCount} Booked • Moves to "Won" after deposit`;
        animateMetricCountUp(elPipe, cardPipe, animate ? PREV_METRICS.pipeline : pipelineBooked, pipelineBooked, v => `$${v.toLocaleString()}`);
        PREV_METRICS.pipeline = pipelineBooked;
      } else {
        elPipeLabel.innerText = 'Pipeline Booked / Revenue Won';
        elPipe.style.color = '#0f172a';
        elPipeSub.innerText = '0 Dispatches Booked in Session';
        animateMetricCountUp(elPipe, cardPipe, animate ? PREV_METRICS.pipeline : 0, 0, v => `$${v.toLocaleString()}`);
        PREV_METRICS.pipeline = 0;
      }

      // 2. UPFRONT DEPOSITS COLLECTED & PRE-AUTH HOLDS
      const fees = Math.round(roi.fees_collected || 0);
      const feesOnHold = Math.round(roi.fees_on_hold || 0);
      const elFees = document.getElementById('kpiFeesCol');
      const cardFees = document.getElementById('cardMetricFees');
      elFees.style.color = (fees > 0 || feesOnHold > 0) ? '#15803d' : '#0f172a';
      document.getElementById('kpiFeesSubtext').innerText = isBench
        ? '16 Verified Deposits (Simulated Benchmark)'
        : (fees > 0 ? `✓ $${fees} Captured On-Site` + (feesOnHold > 0 ? ` (+$${feesOnHold} on Hold)` : '') : (feesOnHold > 0 ? `⏳ $${feesOnHold} Pre-Auth Hold Active` : (pipelineBooked > 0 ? '⏳ Awaiting Customer Pre-Auth Hold' : '0 Stripe Deposits Paid')));
      animateMetricCountUp(elFees, cardFees, animate ? PREV_METRICS.fees : (fees + feesOnHold), (fees + feesOnHold), v => `$${v.toLocaleString()}`);
      PREV_METRICS.fees = fees + feesOnHold;

      // 3. MISSED CALLS RECOUPED
      const missedRec = isBench ? 7 : (roi.missed_recovered || 0);
      const atRisk = roi.missed_at_risk_value || 0;
      const elMissed = document.getElementById('kpiMissedRec');
      const elMissedSub = document.getElementById('kpiMissedSub');
      const cardMissed = document.getElementById('cardMetricMissed');

      if (isBench) {
        elMissed.style.color = '#2563eb';
        elMissedSub.innerText = '+$8,400 Recouped (Simulated Benchmark)';
      } else if (missedRec > 0) {
        elMissed.style.color = '#2563eb';
        elMissedSub.innerText = `+$${(roi.recouped_revenue || 0).toLocaleString()} Intercepted via 3s SMS`;
      } else if (atRisk > 0) {
        elMissed.style.color = '#d97706';
        elMissedSub.innerText = `⚠️ $${atRisk.toLocaleString()} Currently at Risk!`;
      } else {
        elMissed.style.color = '#0f172a';
        elMissedSub.innerText = '0 Dropped Calls Tested';
      }
      animateMetricCountUp(elMissed, cardMissed, animate ? PREV_METRICS.missed : missedRec, missedRec, v => `${v} Saved`);
      PREV_METRICS.missed = missedRec;

      updateTechFilterOptions(data.technicians || []);
      renderCalendar();
      renderFleetView();

      const sessionBookings = (data.bookings || []).filter(b => !b.is_demo_seed);
      if (!dispatchHero.classList.contains('active') && sessionBookings.length > 0) {
        const latestBooking = sessionBookings[sessionBookings.length - 1];
        const mode = data.last_scenario_mode || ((latestBooking.urgency_level || '').includes('EMERG') ? 'emergency' : 'routine');
        applyScenarioJourneyLabels(mode);
        if (data.last_dialogue && data.last_dialogue.length > 0 && chatStream.children.length <= 1) {
          chatStream.innerHTML = '';
          data.last_dialogue.forEach(item => appendMessage(item.speaker, item.text, item.isSarah));
        }
        showBookingInHero(latestBooking);
        pushCustomerSmsBooking(latestBooking);
        if (latestBooking.payment_status === 'PAID_VERIFIED') {
          setJourneyProgress(
            4,
            `🎉 <strong>Journey Complete!</strong> Deposit verified via Stripe — <strong>$${Number(latestBooking.estimated_job_value || 1200).toLocaleString()} Revenue Won</strong> + <strong>$${latestBooking.dispatch_fee} Deposit Collected</strong>!`,
            'complete'
          );
          document.getElementById('jStep4').classList.remove('active-step');
          document.getElementById('jStep4').classList.add('done-step');
          document.getElementById('jNum4').innerText = '✓';
        } else {
          setJourneyProgress(
            3,
            `👉 <strong>Next Step (Step 3 of 4):</strong> Work order dispatched! Click <strong>"Authorize $${latestBooking.dispatch_fee} Deposit via Stripe"</strong> inside the highlighted phone.`,
            'phone'
          );
        }
      }
    }

    async function fetchBoardData() {
      try {
        const res = await fetch('/api/board');
        const data = await res.json();
        applyBoardData(data, true);
      } catch (err) {
        console.error('Error fetching board data:', err);
      }
    }

    function updateTechFilterOptions(techs) {
      const select = document.getElementById('calTechFilter');
      if (!select) return;
      const currentVal = select.value;
      let html = '<option value="ALL">⚡ All Electricians (Full 4-Tech Dispatch Board)</option>';
      techs.forEach(t => {
        html += `<option value="${t.technician_id}">${t.name} (${t.license_type})</option>`;
      });
      select.innerHTML = html;
      select.value = currentVal || 'ALL';
    }

    let SELECTED_CAL_DATE = 'ALL';

    function selectCalendarDayTab(dateVal) {
      SELECTED_CAL_DATE = dateVal;
      renderCalendar();
    }

    function isSlotWindowElapsed(slotDate, winKey, todayStr) {
      if (slotDate !== todayStr) return false;
      const curHour = new Date().getHours();
      if (winKey === 'morning' && curHour >= 12) return true;
      if (winKey === 'afternoon' && curHour >= 16) return true;
      if (winKey === 'evening' && curHour >= 19) return true;
      return false;
    }

    function getTechAvatarAndRole(techName, techs) {
      const clean = (techName || '').split('(')[0].trim();
      const parts = clean.split(/\s+/);
      const initials = ((parts[0] || 'T').charAt(0) + (parts[1] || 'E').charAt(0)).toUpperCase();
      const shortName = parts[0] + (parts[1] ? ' ' + parts[1].charAt(0) + '.' : '');
      const tObj = (techs || []).find(t => t.name.toLowerCase() === clean.toLowerCase());
      let roleLabel = 'Journeyman • Panel';
      if (clean.toLowerCase().includes('marcus')) {
        roleLabel = 'Master • On-Call Lead';
      } else if (clean.toLowerCase().includes('sarah')) {
        roleLabel = 'EV & Comm. Cert.';
      } else if (clean.toLowerCase().includes('luis')) {
        roleLabel = 'Service • On-Call';
      } else if (tObj && tObj.is_on_call) {
        roleLabel = 'On-Call Tech';
      }
      return { initials, shortName, roleLabel, fullName: clean };
    }

    function renderBookedSlotCard(b, windowShortLabel = '') {
      const isEmerg = (b.urgency_level || '').includes('EMERG') || (b.service_type || '').toLowerCase() === 'emergency';
      const isPaid = b.payment_status === 'PAID_VERIFIED';
      const isManual = (b.booked_by || '').toLowerCase().includes('manual');
      const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
      const techShort = (b.assigned_technician || 'Marcus Vance').split('(')[0].trim();
      const truckShort = (b.truck_id || 'TRUCK-01').split('(')[0].trim();

      const sourceBadge = isManual
        ? `<span class="booked-manual-tag">🛠️ Manual Dispatch</span>`
        : `<span class="booked-ai-tag ${isEmerg ? 'emerg-ai-tag' : ''}">🤖 ${isEmerg ? 'Booked by Sarah AI • Code Red' : 'Booked by Sarah AI'}</span>`;

      const depBadge = isPaid
        ? `<span class="dep-pill dep-paid">✓ $${b.dispatch_fee} Paid</span>`
        : `<span class="dep-pill dep-pending">⏳ $${b.dispatch_fee} Pending</span>`;

      return `
        <div class="slot-box ${isEmerg ? 'is-booked-emergency' : 'is-booked-routine'}" style="cursor:pointer;" onclick='selectCalendarBooking(${safeObj})'>
          <div class="booked-top-tags">
            ${sourceBadge}
            ${depBadge}
          </div>
          <div class="booked-job-title">${b.display_title || b.service_type}</div>
          <div class="booked-hazard-line">${b.triage_hazard_short || (isEmerg ? '🚨 Hazard: NFPA 70E Code Red (Thermal)' : '🛡️ Triage: 200A Panel Verified')}</div>
          <div class="booked-cust-name">👤 ${b.customer_name} ${windowShortLabel ? `<span style="font-weight:600; color:#475569;">(${windowShortLabel})</span>` : ''}</div>
          <div class="booked-cust-meta">
            📍 ${b.service_address}<br>
            <span class="match-logic-badge">👷 ${techShort} • 🚐 ${truckShort}</span>
          </div>
        </div>
      `;
    }

    function renderCalendar() {
      const grid = document.getElementById('fullCalendarGrid');
      if (!grid) return;

      const techFilter = document.getElementById('calTechFilter').value;
      const slots = BOARD_DATA.slots || [];
      const bookings = BOARD_DATA.bookings || [];
      const techs = BOARD_DATA.technicians || [];
      const filteredSlots = techFilter === 'ALL' ? slots : slots.filter(s => s.technician_id === techFilter);

      const allDates = [...new Set(slots.map(s => s.date))].slice(0, 5);
      const todayStr = allDates[0] || new Date().toISOString().slice(0, 10);

      // Update Day Switcher Tabs (for Single-Day / Mobile vs 5-Day View)
      const dayTabsEl = document.getElementById('calDayTabsBar');
      if (dayTabsEl) {
        let tabsHtml = `<button class="cal-day-tab ${SELECTED_CAL_DATE === 'ALL' ? 'active' : ''}" onclick="selectCalendarDayTab('ALL')">📅 All 5 Days</button>`;
        allDates.forEach((dt, idx) => {
          const dObj = new Date(dt + 'T12:00:00');
          const dayShort = dObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
          const dayBookings = bookings.filter(b => b.slot_date === dt).length;
          const badge = dayBookings > 0 ? ` (${dayBookings} Booked)` : '';
          tabsHtml += `<button class="cal-day-tab ${SELECTED_CAL_DATE === dt ? 'active' : ''}" onclick="selectCalendarDayTab('${dt}')">${idx === 0 ? 'Today · ' : ''}${dayShort}${badge}</button>`;
        });
        dayTabsEl.innerHTML = tabsHtml;
      }

      // Update Google Calendar Two-Way Sync Banner
      const gcalTitle = document.getElementById('gcalSyncStatusTitle');
      const gcalSub = document.getElementById('gcalSyncStatusSub');
      const gcalBlockedCount = slots.filter(s => s.is_blocked && (s.blocked_reason || '').includes('Google Calendar')).length;
      if (gcalTitle && gcalSub) {
        gcalTitle.innerText = `Connected: Master Dispatch + ${techs.length} Technician Google Calendars (${BOARD_DATA.gcal_last_sync || 'Two-Way Active'})`;
        gcalSub.innerText = `${bookings.length} AI & Manual Dispatch${bookings.length === 1 ? '' : 'es'} Synced to Google Calendar • ${gcalBlockedCount} External Google Calendar Busy Block${gcalBlockedCount === 1 ? '' : 's'} Imported`;
      }

      const occEl = document.getElementById('calOccupancySummary');
      if (occEl) {
        const openFutureCount = filteredSlots.filter(s => s.time_window_key !== 'emergency_asap' && !s.is_booked && !s.is_blocked && !isSlotWindowElapsed(s.date, s.time_window_key, todayStr)).length;
        occEl.innerText = `${bookings.length} Booked on Schedule • ${gcalBlockedCount} GCal Busy Block${gcalBlockedCount === 1 ? '' : 's'} • ${openFutureCount} Open Future Tech Slots`;
      }

      // Render Active Dispatches Live Strip at Top of Calendar
      const stripEl = document.getElementById('activeDispatchStrip');
      if (stripEl) {
        if (bookings.length === 0) {
          stripEl.innerHTML = '';
        } else {
          // Put emergencies and newest session bookings first
          const sortedBookings = [...bookings].reverse();
          stripEl.innerHTML = sortedBookings.map(b => {
            const isEmerg = (b.urgency_level || '').includes('EMERG') || (b.service_type || '').toLowerCase() === 'emergency';
            const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
            const assignedShort = (b.assigned_technician || '').split('(')[0].trim();
            const truckShort = (b.truck_id || 'TRUCK-01').split('(')[0].trim();
            const techOptions = techs.map(t => {
              const sel = assignedShort.toLowerCase() === t.name.toLowerCase() ? 'selected' : '';
              const tTruckShort = (t.truck_id || 'TRUCK-01').split('(')[0].trim();
              return `<option value="${t.technician_id}" ${sel}>👷 ${t.name} (${tTruckShort})</option>`;
            }).join('');
            let payPill = '';
            if (b.payment_status === 'CAPTURED_ON_SITE' || b.payment_status === 'PAID_VERIFIED') {
              payPill = `<span style="background:#dcfce7; color:#15803d; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:800;">✓ $${b.dispatch_fee} Captured</span>`;
            } else if (b.payment_status === 'AUTHORIZED_HOLD') {
              payPill = `<span style="background:#dbeafe; color:#1e40af; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:800;">⏳ $${b.dispatch_fee} Pre-Auth Hold</span>`;
            } else if (b.payment_status === 'RELEASED_CANCELED') {
              payPill = `<span style="background:#fee2e2; color:#991b1b; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:800;">⊘ Hold Released</span>`;
            } else {
              payPill = `<span style="background:#fef3c7; color:#b45309; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:800;">💳 Pending $${b.dispatch_fee} Hold</span>`;
            }

            return `
              <div class="dispatch-queue-card ${isEmerg ? 'is-emerg-queue' : ''}">
                <div>
                  <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:4px;">
                    <span class="dq-badge">${isEmerg ? '🚨 CODE RED EMERGENCY DISPATCH' : '🤖 BOOKED BY SARAH AI'}</span>
                    <span style="font-weight:800; font-size:0.86rem; color:#475569;">#${b.confirmation_id}</span>
                    <span style="background:#f1f5f9; color:#0f172a; border:1px solid #cbd5e1; padding:4px 10px; border-radius:6px; font-size:0.78rem; font-weight:800;">🚐 ${truckShort}</span>
                    ${payPill}
                    <span style="background:#dbeafe; color:#1e40af; padding:4px 10px; border-radius:6px; font-size:0.78rem; font-weight:800;">📅 Google Calendar Synced ✓</span>
                  </div>
                  <div class="dq-title">${b.display_title || b.service_type} — ${b.customer_name} (${b.phone_number})</div>
                  <div class="dq-meta">
                    📍 <strong>${b.service_address}</strong> &bull; 🕒 <strong>${b.display_window || b.slot_time}</strong> &bull; 🛡️ <strong>${b.triage_hazard_short || 'Triage Verified'}</strong>
                  </div>
                </div>
                <div class="dq-actions">
                  <div style="display:flex; flex-direction:column; gap:3px;">
                    <span style="font-size:0.74rem; font-weight:800; color:#475569; text-transform:uppercase;">Assigned Electrician &amp; Truck:</span>
                    <select class="reassign-select" onchange="reassignBookingTech('${b.confirmation_id}', this.value)">
                      ${techOptions}
                    </select>
                  </div>
                  ${b.google_calendar_link ? `<a href="${b.google_calendar_link}" target="_blank" class="btn-cal-magic" style="padding:9px 14px; font-size:0.86rem;">📅 Open in Google Calendar</a>` : ''}
                  <button class="btn-cal-action" onclick='selectCalendarBooking(${safeObj})'>📋 View Ticket</button>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      const visibleDates = SELECTED_CAL_DATE === 'ALL' ? allDates : allDates.filter(d => d === SELECTED_CAL_DATE);
      grid.className = `full-calendar-grid ${visibleDates.length === 1 ? 'single-day-mode' : ''}`;

      const curHour = new Date().getHours();
      const activeEmergWinKey = curHour < 12 ? 'morning' : (curHour < 16 ? 'afternoon' : 'evening');

      grid.innerHTML = visibleDates.map(dt => {
        const dayIdx = allDates.indexOf(dt);
        const dObj = new Date(dt + 'T12:00:00');
        const dayName = dObj.toLocaleDateString('en-US', { weekday: 'short' });
        const dateStr = dObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const dayLabel = dayIdx === 0 ? `Today (${dayName})` : (dayIdx === 1 ? `Tomorrow (${dayName})` : dayName);

        // 1. Check for Emergency Dispatches on this date
        const dayEmergencies = bookings.filter(bk => {
          const isEm = (bk.urgency_level || '').includes('EMERG') || (bk.slot_time || '').toLowerCase().includes('45-60') || (bk.service_type || '').toLowerCase() === 'emergency';
          if (!isEm || bk.slot_date !== dt) return false;
          if (techFilter === 'ALL') return true;
          const tObj = techs.find(t => t.technician_id === techFilter);
          return tObj && (bk.assigned_technician || '').toLowerCase().includes(tObj.name.toLowerCase());
        });

        const emergCardsHtml = dayEmergencies.map(eb => renderBookedSlotCard(eb, '45–60m ETA')).join('');

        const windows = [
          { label: 'Morning · 8–12', wKey: 'morning', key: '08:00 AM - 12:00 PM', fullRange: '8:00 AM – 12:00 PM' },
          { label: 'Afternoon · 12–4', wKey: 'afternoon', key: '12:00 PM - 04:00 PM', fullRange: '12:00 PM – 4:00 PM' },
          { label: 'Evening · 4–7', wKey: 'evening', key: '04:00 PM - 07:00 PM', fullRange: '4:00 PM – 7:00 PM' }
        ];

        const slotsHtml = windows.map(w => {
          const isElapsed = isSlotWindowElapsed(dt, w.wKey, todayStr);

          // Find routine bookings in this window
          const winBookings = bookings.filter(bk => {
            const isEm = (bk.urgency_level || '').includes('EMERG') || (bk.slot_time || '').toLowerCase().includes('45-60') || (bk.service_type || '').toLowerCase() === 'emergency';
            if (isEm || bk.slot_date !== dt) return false;
            const timeMatch = (bk.slot_time || '').includes(w.key) || w.key.includes(bk.slot_time || '---') || (bk.slot_time || '').toLowerCase().includes(w.wKey);
            if (!timeMatch) return false;
            if (techFilter === 'ALL') return true;
            const tObj = techs.find(t => t.technician_id === techFilter);
            return tObj && (bk.assigned_technician || '').toLowerCase().includes(tObj.name.toLowerCase());
          });

          const windowSlots = filteredSlots.filter(s => s.date === dt && s.time_window_key === w.wKey);
          const gcalBusySlots = windowSlots.filter(s => s.is_blocked && (s.blocked_reason || '').includes('Google Calendar'));
          const manualBlockedSlots = windowSlots.filter(s => s.is_blocked && !(s.blocked_reason || '').includes('Google Calendar'));

          // Check which techs are occupied by an emergency during this active window
          const emergTechNamesInWin = (w.wKey === activeEmergWinKey)
            ? dayEmergencies.map(eb => (eb.assigned_technician || '').split('(')[0].trim().toLowerCase())
            : [];
          const routineTechNamesInWin = winBookings.map(rb => (rb.assigned_technician || '').split('(')[0].trim().toLowerCase());

          const openWindowSlots = windowSlots.filter(s => {
            const sTechLower = s.technician_name.split('(')[0].trim().toLowerCase();
            if (s.is_booked || s.is_blocked) return false;
            if (emergTechNamesInWin.includes(sTechLower) || routineTechNamesInWin.includes(sTechLower)) return false;
            return true;
          });

          let cards = [];

          // Render routine booked cards in this window using the rich Booked by Sarah AI card design
          winBookings.forEach(b => {
            cards.push(renderBookedSlotCard(b, w.label));
          });

          // Render Google Calendar Busy blocks imported via Two-Way Sync
          gcalBusySlots.forEach(gs => {
            cards.push(`
              <div class="slot-box is-gcal-busy">
                <div class="slot-time-header">
                  <span style="color:#1e40af;">${w.label}</span>
                  <span class="status-pill" style="background:#dbeafe; color:#1e40af; border:1px solid #93c5fd;">📅 GCal Busy</span>
                </div>
                <div class="booked-job-title" style="color:#1e3a8a;">${(gs.blocked_reason || 'Google Calendar Event').replace('📅 Google Calendar Busy: ', '')}</div>
                <div class="booked-cust-meta">
                  👷 Tech: <strong>${gs.technician_name}</strong> (Synced via GCal)<br>
                  <button class="btn-slot-act btn-slot-block" style="margin-top:6px;" onclick="toggleBlockSlot('${gs.slot_id}')">Restore availability</button>
                </div>
              </div>
            `);
          });

          // 1. ELAPSED WINDOW ON TODAY: Gray out and remove + Book button!
          if (isElapsed && cards.length === 0) {
            return `
              <div class="slot-box is-elapsed-slot">
                <div class="slot-time-header">
                  <span>${w.label}</span>
                  <span class="status-pill pill-elapsed">⏳ Elapsed</span>
                </div>
                <div style="font-size:0.8rem; color:#64748b; font-weight:600; line-height:1.35;">
                  ${w.fullRange} window has passed for today. Booking closed.
                </div>
              </div>
            `;
          }

          // 2. FUTURE / ACTIVE WINDOW CAPACITY CARD ("3 of 4 Techs Open" with Avatar Chips & Matching Logic)
          if (openWindowSlots.length > 0 && !isElapsed) {
            const primarySlot = openWindowSlots[0];
            const totalTechsInWin = windowSlots.length;
            const techRowsHtml = windowSlots.map(ws => {
              const info = getTechAvatarAndRole(ws.technician_name, techs);
              const sTechLower = info.fullName.toLowerCase();
              if (ws.is_blocked && (ws.blocked_reason || '').includes('Google Calendar')) {
                return `
                  <div class="tech-chip gcal-chip" title="${ws.blocked_reason}">
                    <span class="chip-left"><span class="chip-avatar">${info.initials}</span><span>${info.shortName}</span></span>
                    <span class="chip-role" style="color:#1e40af;">📅 GCal Busy</span>
                  </div>
                `;
              }
              if (emergTechNamesInWin.includes(sTechLower)) {
                return `
                  <div class="tech-chip busy-chip">
                    <span class="chip-left"><span class="chip-avatar">${info.initials}</span><span>${info.shortName}</span></span>
                    <span class="chip-role" style="color:#b91c1c;">🚨 Dispatched (45m)</span>
                  </div>
                `;
              }
              if (ws.is_booked || ws.is_blocked || routineTechNamesInWin.includes(sTechLower)) {
                return `
                  <div class="tech-chip busy-chip">
                    <span class="chip-left"><span class="chip-avatar">${info.initials}</span><span>${info.shortName}</span></span>
                    <span class="chip-role" style="color:#b91c1c;">🔴 Booked</span>
                  </div>
                `;
              }
              return `
                <div class="tech-chip">
                  <span class="chip-left"><span class="chip-avatar">${info.initials}</span><span>${info.shortName}</span></span>
                  <span class="chip-role">${info.roleLabel}</span>
                </div>
              `;
            }).join('');

            cards.push(`
              <div class="slot-box">
                <div class="slot-time-header">
                  <span>${w.label}</span>
                  <span class="status-pill pill-open">● ${openWindowSlots.length} of ${totalTechsInWin} Techs Open</span>
                </div>
                <div class="tech-chip-list">${techRowsHtml}</div>
                <div class="slot-actions">
                  <button class="btn-slot-act btn-slot-book" onclick="openManualBookModal('${primarySlot.slot_id}')">+ Book</button>
                  <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${primarySlot.slot_id}')">Mark unavailable</button>
                </div>
              </div>
            `);
          } else if (cards.length === 0 && manualBlockedSlots.length > 0) {
            const bs = manualBlockedSlots[0];
            cards.push(`
              <div class="slot-box">
                <div class="slot-time-header">
                  <span>${w.label}</span>
                  <span class="status-pill pill-blocked">⛔ Unavailable</span>
                </div>
                <div class="slot-tech-avail">${bs.blocked_reason || 'Marked Unavailable / Off-Duty'}</div>
                <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${bs.slot_id}')">Restore availability</button>
              </div>
            `);
          }

          return cards.join('');
        }).join('');

        return `
          <div class="cal-col ${dayEmergencies.length > 0 ? 'has-emergency-col' : ''}">
            <div class="cal-col-header">
              <div class="cal-col-day">${dayLabel}</div>
              <div class="cal-col-sub">${dateStr} ${dayEmergencies.length > 0 ? '• 🚨 CODE RED ACTIVE' : ''}</div>
            </div>
            <div class="cal-col-body">
              ${emergCardsHtml}
              ${slotsHtml}
            </div>
          </div>
        `;
      }).join('');
    }

    let ACTIVE_DOSSIER_BOOKING = null;

    function selectCalendarBooking(booking) {
      openTicketDossierModal(booking);
    }

    function openTicketDossierModal(booking) {
      if (!booking) return;
      ACTIVE_DOSSIER_BOOKING = booking;
      showBookingInHero(booking);

      const isEmerg = (booking.urgency_level || '').includes('EMERG') || (booking.service_type || '').toLowerCase() === 'emergency';
      const isFinalPaid = Boolean(booking.final_balance_paid);
      const isHold = booking.payment_status === 'AUTHORIZED_HOLD';
      const isCaptured = booking.payment_status === 'CAPTURED_ON_SITE' || booking.payment_status === 'PAID_VERIFIED' || isFinalPaid;
      const isCanceled = booking.payment_status === 'RELEASED_CANCELED';
      const isPaid = isCaptured;
      const isManual = (booking.booked_by || '').toLowerCase().includes('manual');

      const cardEl = document.getElementById('ticketDossierCard');
      cardEl.className = `modal-card ticket-dossier-card ${isEmerg ? 'is-emerg-dossier' : ''}`;

      document.getElementById('dossierStamp').innerHTML = isManual
        ? '🛠️ OFFICIAL FIELD WORK ORDER &bull; MANUAL DISPATCH'
        : (isEmerg ? '🚨 PRIORITY CODE RED WORK ORDER &bull; BOOKED BY SARAH AI' : '🤖 OFFICIAL FIELD WORK ORDER &bull; BOOKED BY SARAH AI');

      document.getElementById('dossierJobTitle').innerText = booking.display_title || booking.service_type || 'Electrical Service Dispatch';

      const statusBadge = document.getElementById('dossierStatusBadge');
      if (isEmerg) {
        statusBadge.style.background = '#dc2626';
        statusBadge.innerText = '🚨 DISPATCHED CODE RED';
      } else {
        statusBadge.style.background = '#16a34a';
        statusBadge.innerText = '✓ CONFIRMED ON SCHEDULE';
      }

      document.getElementById('dossierConfId').innerText = `#${booking.confirmation_id}`;
      let createdClean = 'Today, Live Session';
      if (booking.created_at) {
        try {
          const dt = new Date(booking.created_at);
          createdClean = dt.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
        } catch (e) {}
      }
      document.getElementById('dossierCreatedAt').innerText = createdClean;
      document.getElementById('dossierContractorEmail').innerText = DEFAULT_CONFIG_EMAIL;

      // Customer & Site Record
      document.getElementById('dossierCustName').innerText = booking.customer_name || 'Resident';
      document.getElementById('dossierCustPhone').innerText = booking.phone_number || '(555) 000-0000';
      document.getElementById('dossierCustAddress').innerText = booking.service_address || 'Service Address';
      document.getElementById('dossierAccessNotes').innerText = booking.notes || (isEmerg ? 'Immediate Code Red Dispatch • Gate/Door Unlocked' : 'Standard residential service access');

      // Fleet Dispatch & Routing
      document.getElementById('dossierTechName').innerText = booking.assigned_technician || 'Marcus Vance (Master Electrician)';
      document.getElementById('dossierTechMatch').innerText = booking.tech_match_reason || (isEmerg ? 'Master Electrician • On-Call Lead • Nearest (14m)' : 'Certified Specialist • Route Optimized');
      document.getElementById('dossierArrivalWin').innerText = booking.display_window || `${booking.slot_date} (${booking.slot_time})`;

      const techs = BOARD_DATA.technicians || [];
      const assignedShort = (booking.assigned_technician || '').split('(')[0].trim().toLowerCase();
      const reassignSel = document.getElementById('dossierReassignSelect');
      if (reassignSel) {
        reassignSel.innerHTML = techs.map(t => {
          const sel = t.name.toLowerCase() === assignedShort ? 'selected' : '';
          const tTruckShort = (t.truck_id || 'TRUCK-01').split('(')[0].trim();
          return `<option value="${t.technician_id}" ${sel}>👷 ${t.name} (${tTruckShort})</option>`;
        }).join('');
      }
      const truckSel = document.getElementById('dossierTruckSelect');
      if (truckSel) {
        truckSel.value = booking.truck_id || 'TRUCK-01 (Master Emergency Van)';
      }

      // Triage & Safety Log
      const triageBanner = document.getElementById('dossierTriageBanner');
      triageBanner.className = `dossier-triage-banner ${isEmerg ? 'is-emerg-triage' : ''}`;
      document.getElementById('dossierTriageTitle').innerHTML = isEmerg
        ? '🚨 NFPA 70E HAZARD TRIAGE &amp; SAFETY PROTOCOL LOG'
        : '🛡️ AI TECHNICAL TRIAGE &amp; LOAD VERIFICATION LOG';
      document.getElementById('dossierHazardPill').innerText = booking.triage_hazard_short || (isEmerg ? '🚨 NFPA 70E Code Red' : '🛡️ 200A Panel Verified');
      document.getElementById('dossierSymptom').innerText = booking.triage_symptom || booking.issue_description || 'Electrical service request';
      const hazFullEl = document.getElementById('dossierHazardFull');
      hazFullEl.innerText = booking.triage_hazard_level || (isEmerg ? 'NFPA 70E Code Red — Active Thermal / Fire Risk' : 'Routine Service (Non-Hazardous)');
      hazFullEl.style.color = isEmerg ? '#b91c1c' : '#1e40af';
      document.getElementById('dossierSafetyDirective').innerText = booking.triage_safety_instruction || 'Isolate affected circuit breaker prior to arrival.';
      document.getElementById('dossierNecLoad').innerText = booking.nec_load_summary || 'NEC 220.82 Service Load Verified';
      const permEl = document.getElementById('dossierPermitInfo');
      if (permEl) permEl.innerText = booking.permit_info || 'Municipal Electrical Repair Permit Pre-Drafted';
      const rebEl = document.getElementById('dossierRebateInfo');
      if (rebEl) rebEl.innerText = booking.rebate_summary || 'Homeowner Insurance & IRS 25C Safety Upgrade Eligible';
      document.getElementById('dossierUpsellRec').innerText = booking.upsell_recommendation || 'Whole-Home Type 2 Surge Protection (NEC 230.67) — +$485 Add-On';

      // AI Panel & Equipment Photo Pre-Check Audit
      const photoInfo = booking.panel_photo_analysis || {};
      const photoUploaded = Boolean(photoInfo.uploaded);
      document.getElementById('dossierPhotoEquip').innerText = photoInfo.equipment_detected || '200A Main Breaker Panel';
      document.getElementById('dossierPhotoBreaker').innerText = `${photoInfo.breaker_spec || '20A Dual-Function AFCI/GFCI'} (${photoInfo.open_spaces || 'Spaces Verified'})`;
      document.getElementById('dossierPhotoFinding').innerText = photoInfo.ai_finding || 'SMS link sent to homeowner to verify panel label prior to arrival.';
      document.getElementById('dossierPhotoPartsCheck').innerText = photoInfo.parts_verification || '✓ Prevents rolling a truck without the matching breaker series';
      const photoStatusPill = document.getElementById('dossierPhotoStatusPill');
      const photoUploadBtn = document.getElementById('dossierUploadPhotoBtn');
      if (photoUploaded) {
        photoStatusPill.style.background = '#16a34a';
        photoStatusPill.style.color = '#ffffff';
        photoStatusPill.innerText = `✓ AI Vision Verified (${photoInfo.uploaded_at || 'Live'})`;
        photoUploadBtn.style.display = 'none';
      } else {
        photoStatusPill.style.background = '#dcfce7';
        photoStatusPill.style.color = '#15803d';
        photoStatusPill.innerText = '📋 Pre-Arrival SMS Active';
        photoUploadBtn.style.display = 'inline-flex';
      }

      // Field Technician Pre-Arrival Checklist & Truck Stock
      const titleLower = (booking.display_title || booking.service_type || '').toLowerCase();
      let checklistItems = [];
      if (isEmerg) {
        checklistItems = [
          '✓ FLIR Thermal Imaging Camera (Hotspot Scan)',
          '✓ NFPA 70E Arc-Rated PPE & Insulated Gloves',
          '✓ 15A/20A Spec-Grade Receptacles & AFCI/GFCI Breakers',
          '✓ Megohmmeter Insulation Resistance Tester'
        ];
      } else if (titleLower.includes('ev')) {
        checklistItems = [
          '✓ 50A 2-Pole Breaker & #6 AWG Cu THHN/Romex',
          '✓ Industrial NEMA 14-50 / Hardwire EVSE Whip',
          '✓ NEC 220.82 Service Load Calculation Sheet',
          '✓ Torque Wrench (In-Lbs Lug Verification)'
        ];
      } else if (titleLower.includes('panel')) {
        checklistItems = [
          '✓ 200A Copper Bus Main Breaker Loadcenter',
          '✓ Whole-Home Type 1/2 Surge Protective Device (NEC 230.67)',
          '✓ Ground Rod & #4 Cu GEC Bonding Clamps',
          '✓ Thermal Scan & Torque Spec Log'
        ];
      } else {
        checklistItems = [
          '✓ True-RMS Digital Multimeter & Circuit Tracer',
          '✓ 20A Dual-Function AFCI/GFCI Breakers',
          '✓ Commercial Spec-Grade Wiring Devices',
          '✓ Panel Schedule & Load Balancing Audit'
        ];
      }
      document.getElementById('dossierChecklistGrid').innerHTML = checklistItems
        .map(item => `<div class="dossier-check-item">${item}</div>`)
        .join('');

      // Connected Invoicing & FSM Integration Bridge
      const fee = Number(booking.dispatch_fee || 89);
      const jobVal = Number(booking.estimated_job_value || 1200);

      const fsmName = booking.fsm_name || 'Housecall Pro';
      const fsmIcon = booking.fsm_icon || '🏠';
      const fsmTicketId = booking.fsm_ticket_id || ('HCP-' + (booking.confirmation_id || '8921').replace(/\D/g, '').slice(-4));
      const fsmUrl = booking.fsm_url || 'https://app.housecallpro.com/jobs';
      const fsmBtnLabel = booking.fsm_button_label || `Open in ${fsmName}`;

      const fsmNameEl = document.getElementById('dossierFsmNameText');
      if (fsmNameEl) {
        fsmNameEl.innerHTML = `${fsmIcon} Connected to ${fsmName} &bull; Synced Ticket <strong>#${fsmTicketId}</strong>`;
      }
      const fsmSubEl = document.getElementById('dossierFsmSubText');
      if (fsmSubEl) {
        fsmSubEl.innerText = `Upfront diagnostic deposit credited • Price book & quotes managed in external ${fsmName}`;
      }
      const fsmDeepLink = document.getElementById('dossierFsmDeepLink');
      if (fsmDeepLink) {
        fsmDeepLink.href = fsmUrl;
        fsmDeepLink.innerText = `↗ ${fsmBtnLabel}`;
      }

      document.getElementById('dossierFeeDesc').innerText = isEmerg
        ? 'Priority Code Red Emergency Dispatch & Diagnostic Deposit'
        : 'Upfront Dispatch & Diagnostic Deposit (Stripe Escrow)';
      document.getElementById('dossierFeeAmt').innerText = `$${fee.toFixed(2)}`;

      const jobEstDesc = document.getElementById('dossierJobEstDesc');
      if (jobEstDesc) jobEstDesc.innerText = `Diagnostic Deposit Credited Toward Final Scope`;

      const jobValAmt = document.getElementById('dossierJobValAmt');
      if (jobValAmt) jobValAmt.innerText = isPaid ? `-$${fee.toFixed(2)} Credit Applied` : `-$${fee.toFixed(2)} Credit (Pending)`;

      const jobStageEl = document.getElementById('dossierJobStageText');
      if (jobStageEl) {
        jobStageEl.style.color = '#15803d';
        jobStageEl.style.fontWeight = '700';
        jobStageEl.innerText = `Synced to ${fsmName} Invoice #${fsmTicketId}`;
      }

      const payPill = document.getElementById('dossierPaymentPill');
      const feeStatus = document.getElementById('dossierFeeStatusText');
      const payBtn = document.getElementById('dossierStripePayBtn');
      const releaseBtn = document.getElementById('dossierReleaseHoldBtn');
      const finalPayBtn = document.getElementById('dossierFinalPayBtn');
      const pid = booking.stripe_payment_intent_id || 'pi_hold_demo';
      const dest = booking.stripe_connect_account_id || 'acct_apex_electric_101';

      if (isFinalPaid) {
        payPill.innerHTML = '<span style="background:#16a34a; color:#ffffff; padding:3px 9px; border-radius:6px; font-weight:800;">✓ PAID IN FULL VIA STRIPE ($0 Balance)</span>';
        feeStatus.style.color = '#15803d';
        feeStatus.innerText = `✓ Final Invoice Paid in Full • Stripe Connect Dest: ${dest}`;
        payBtn.style.display = 'none';
        if (releaseBtn) releaseBtn.style.display = 'none';
        if (finalPayBtn) {
          finalPayBtn.innerText = '✓ Final Balance Paid in Full';
          finalPayBtn.style.background = '#15803d';
          finalPayBtn.disabled = true;
        }
      } else if (isCaptured) {
        payPill.innerHTML = '<span style="background:#dcfce7; color:#15803d; padding:3px 9px; border-radius:6px; font-weight:800;">✓ Diagnostic Fee Captured On-Site</span>';
        feeStatus.style.color = '#15803d';
        feeStatus.innerText = `✓ Captured & Settled upon On-Site Arrival (${pid}) • Stripe Dest: ${dest}`;
        payBtn.style.display = 'none';
        if (releaseBtn) releaseBtn.style.display = 'none';
        if (finalPayBtn) {
          const rem = Math.max(0, jobVal - fee);
          finalPayBtn.innerText = `💰 Collect $${rem.toLocaleString()} Final Balance`;
          finalPayBtn.style.background = '#15803d';
          finalPayBtn.disabled = false;
        }
      } else if (isHold) {
        payPill.innerHTML = `<span style="background:#dbeafe; color:#1e40af; padding:3px 9px; border-radius:6px; font-weight:800;">⏳ Pre-Auth Hold Active ($${fee})</span>`;
        feeStatus.style.color = '#1e40af';
        feeStatus.innerText = `⏳ Authorized (capture_method=manual) • Card not yet charged • Intent: ${pid}`;
        payBtn.style.display = 'inline-flex';
        payBtn.style.background = '#2563eb';
        payBtn.innerText = `⚡ Settle / Capture $${fee} On-Site`;
        if (releaseBtn) releaseBtn.style.display = 'inline-flex';
        if (finalPayBtn) {
          finalPayBtn.innerText = `💰 Collect $${jobVal.toLocaleString()} Final Balance`;
          finalPayBtn.style.background = '#15803d';
          finalPayBtn.disabled = false;
        }
      } else if (isCanceled) {
        payPill.innerHTML = `<span style="background:#fee2e2; color:#991b1b; padding:3px 9px; border-radius:6px; font-weight:800;">⊘ Pre-Auth Hold Released ($0)</span>`;
        feeStatus.style.color = '#991b1b';
        feeStatus.innerText = `⊘ Pre-authorization hold cancelled prior to arrival • $0 charged to customer`;
        payBtn.style.display = 'none';
        if (releaseBtn) releaseBtn.style.display = 'none';
        if (finalPayBtn) finalPayBtn.style.display = 'none';
      } else {
        payPill.innerHTML = `<span style="background:#fef3c7; color:#b45309; padding:3px 9px; border-radius:6px; font-weight:800;">⏳ Pending $${fee} Pre-Auth Hold</span>`;
        feeStatus.style.color = '#b45309';
        feeStatus.innerText = 'Pending Customer Stripe Authorization';
        payBtn.style.display = 'inline-flex';
        payBtn.style.background = '#4f46e5';
        payBtn.innerText = `💳 Place $${fee} Pre-Auth Hold`;
        if (releaseBtn) releaseBtn.style.display = 'none';
        if (finalPayBtn) {
          finalPayBtn.innerText = `💰 Collect $${jobVal.toLocaleString()} Final Balance`;
          finalPayBtn.style.background = '#15803d';
          finalPayBtn.disabled = false;
        }
      }

      const enRouteBtn = document.getElementById('dossierEnRouteBtn');
      if (enRouteBtn) {
        const truckShort = (booking.truck_id || 'TRUCK-01').split('(')[0].trim();
        enRouteBtn.innerText = booking.en_route_sent ? `✓ ${truckShort} En-Route SMS Sent` : `🚐 Send "Tech En-Route (${truckShort})" SMS`;
        enRouteBtn.style.background = booking.en_route_sent ? '#16a34a' : '#0284c7';
      }

      const revBtn = document.getElementById('dossierReviewBtn');
      if (revBtn) {
        revBtn.innerText = booking.review_requested ? '✓ 5-Star Review Sent' : '⭐ Request 5-Star Review';
        revBtn.style.background = booking.review_requested ? '#16a34a' : '#f59e0b';
      }

      const gcalBtn = document.getElementById('dossierGcalBtn');
      if (booking.google_calendar_link) {
        gcalBtn.href = booking.google_calendar_link;
        gcalBtn.style.display = 'inline-flex';
      } else {
        gcalBtn.style.display = 'none';
      }

      document.getElementById('ticketDossierModal').classList.add('active');
    }

    function closeTicketDossierModal() {
      document.getElementById('ticketDossierModal').classList.remove('active');
    }

    let CURRENT_PAYLOAD_BOOKING_ID = null;
    let CURRENT_PREVIEW_PLATFORM = null;

    async function switchFsmPlatform(platform) {
      try {
        const res = await fetch('/api/fsm/switch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ platform: platform })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          BOARD_DATA.active_fsm_platform = data.active_fsm_platform;
          if (data.bookings) BOARD_DATA.bookings = data.bookings;
          if (data.roi_metrics) updateRoiKpiCards(data.roi_metrics);

          const sel = document.getElementById('fsmPlatformSelect');
          if (sel) sel.value = data.active_fsm_platform;

          if (ACTIVE_HERO_BOOKING) {
            const updated = (data.bookings || []).find(b => b.confirmation_id === ACTIVE_HERO_BOOKING.confirmation_id) || ACTIVE_HERO_BOOKING;
            ACTIVE_HERO_BOOKING = updated;
            showBookingInHero(updated);
            pushCustomerSmsBooking(updated);
            renderTechTabletView(updated);
            if (document.getElementById('ticketDossierModal').classList.contains('active')) {
              openTicketDossierModal(updated);
            }
          }

          const platformNames = {
            'HOUSECALL_PRO': 'Housecall Pro',
            'SERVICETITAN': 'ServiceTitan',
            'JOBBER': 'Jobber',
            'QUICKBOOKS': 'QuickBooks Online'
          };
          const pName = platformNames[platform] || platform;
          appendMessage('JobLatch AI Integration Engine', `🔌 Connected Invoicing &amp; FSM system switched to <strong>${pName}</strong>. All tickets, live links, and webhooks updated.`);
        }
      } catch (err) {
        console.error('Failed to switch FSM platform:', err);
      }
    }

    async function openFsmPayloadModal(bookingId) {
      if (!bookingId && ACTIVE_DOSSIER_BOOKING) bookingId = ACTIVE_DOSSIER_BOOKING.confirmation_id;
      if (!bookingId && ACTIVE_HERO_BOOKING) bookingId = ACTIVE_HERO_BOOKING.confirmation_id;
      CURRENT_PAYLOAD_BOOKING_ID = bookingId;
      CURRENT_PREVIEW_PLATFORM = BOARD_DATA.active_fsm_platform || 'HOUSECALL_PRO';

      document.getElementById('fsmPayloadModal').classList.add('active');
      previewFsmPlatformPayload(CURRENT_PREVIEW_PLATFORM);
    }

    function closeFsmPayloadModal() {
      document.getElementById('fsmPayloadModal').classList.remove('active');
    }

    async function previewFsmPlatformPayload(platform) {
      CURRENT_PREVIEW_PLATFORM = platform;
      const tabs = document.querySelectorAll('.fsm-modal-tab');
      tabs.forEach(t => {
        if (t.dataset.platform === platform) {
          t.classList.add('active');
          t.style.background = '#2563eb';
          t.style.color = '#ffffff';
          t.style.borderColor = '#3b82f6';
        } else {
          t.classList.remove('active');
          t.style.background = '#f1f5f9';
          t.style.color = '#334155';
          t.style.borderColor = '#cbd5e1';
        }
      });
      await refreshFsmPayloadDisplay();
    }

    async function refreshFsmPayloadDisplay() {
      const platform = CURRENT_PREVIEW_PLATFORM || BOARD_DATA.active_fsm_platform || 'HOUSECALL_PRO';
      const bId = CURRENT_PAYLOAD_BOOKING_ID || '';
      const endpointEl = document.getElementById('fsmEndpointDisplay');
      const jsonPre = document.getElementById('fsmPayloadJsonPre');

      const endpoints = {
        'HOUSECALL_PRO': 'POST https://api.housecallpro.com/v1/jobs',
        'SERVICETITAN': 'POST https://api.servicetitan.io/jpm/v2/tenant/391028/jobs',
        'JOBBER': 'POST https://api.getjobber.com/api/graphql (jobCreate)',
        'QUICKBOOKS': 'POST https://quickbooks.api.intuit.com/v3/company/913035.../invoice'
      };
      if (endpointEl) {
        endpointEl.innerText = endpoints[platform] || `POST /api/fsm/${platform.toLowerCase()}/webhook`;
      }

      if (jsonPre) {
        jsonPre.innerText = '// Fetching live synchronized webhook payload...';
        try {
          const url = `/api/fsm/payload?id=${encodeURIComponent(bId)}&platform=${encodeURIComponent(platform)}`;
          const res = await fetch(url);
          const data = await res.json();
          jsonPre.innerText = JSON.stringify(data, null, 2);
        } catch (e) {
          jsonPre.innerText = `// Error fetching payload: ${e.message}`;
        }
      }
    }

    function copyFsmPayloadJson() {
      const jsonPre = document.getElementById('fsmPayloadJsonPre');
      if (jsonPre && navigator.clipboard) {
        navigator.clipboard.writeText(jsonPre.innerText);
        const btn = document.getElementById('btnCopyFsmPayload');
        if (btn) {
          const oldText = btn.innerText;
          btn.innerText = '✓ Copied to Clipboard!';
          setTimeout(() => { btn.innerText = oldText; }, 2000);
        }
      }
    }

    async function sendQuoteFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      const res = await fetch('/api/bookings/send-quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_DOSSIER_BOOKING.confirmation_id })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        appendMessage(
          'JobLatch AI Proposal Engine',
          `📑 Sent interactive <strong>Good / Better (+$485) / Best (+$950)</strong> Flat-Rate Proposal &amp; IRS 25C Rebate packet to ${data.booking.customer_name}'s smartphone.`,
          true
        );
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        await fetchBoardData();
        openTicketDossierModal(data.booking);
      }
    }

    async function payFinalBalanceFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      await payCustomerFinalBalance(ACTIVE_DOSSIER_BOOKING.confirmation_id);
    }

    async function simulatePhotoUploadFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      await simulateCustomerPhotoUpload(ACTIVE_DOSSIER_BOOKING.confirmation_id);
    }

    async function sendEnRouteSmsFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      const res = await fetch('/api/bookings/en-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_DOSSIER_BOOKING.confirmation_id })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        const techShort = (data.booking.assigned_technician || 'Marcus Vance').split('(')[0].trim();
        const truckShort = (data.booking.truck_id || 'TRUCK-01').split('(')[0].trim();
        appendMessage('JobLatch AI Fleet GPS', `🚐 Sent live "Tech En-Route" SMS to ${data.booking.customer_name}: ${techShort} is en route in ${truckShort} (ETA 14 mins).`, true);
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        await fetchBoardData();
        openTicketDossierModal(data.booking);
      }
    }

    async function sendReviewSmsFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      const res = await fetch('/api/bookings/request-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_DOSSIER_BOOKING.confirmation_id })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.booking) {
        appendMessage('JobLatch AI Reputation Engine', `⭐ Sent 1-Tap 5-Star Google Review request SMS to ${data.booking.customer_name}.`, true);
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
        await fetchBoardData();
        openTicketDossierModal(data.booking);
      }
    }

    async function reassignFromDossierModal(newTechId) {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      await reassignBookingTech(ACTIVE_DOSSIER_BOOKING.confirmation_id, newTechId);
      const updated = (BOARD_DATA.bookings || []).find(b => b.confirmation_id === ACTIVE_DOSSIER_BOOKING.confirmation_id);
      if (updated) openTicketDossierModal(updated);
    }

    async function updateTruckFromDossierModal(newTruckId) {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      const res = await fetch('/api/bookings/update-truck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: ACTIVE_DOSSIER_BOOKING.confirmation_id, truck_id: newTruckId })
      });
      const data = await res.json();
      if (data.booking) {
        showBookingInHero(data.booking);
      }
      await fetchBoardData();
      const updated = (BOARD_DATA.bookings || []).find(b => b.confirmation_id === ACTIVE_DOSSIER_BOOKING.confirmation_id);
      if (updated) openTicketDossierModal(updated);
    }

    async function authorizeDepositFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      if (ACTIVE_DOSSIER_BOOKING.payment_status === 'AUTHORIZED_HOLD') {
        await captureStripeHold(ACTIVE_DOSSIER_BOOKING.confirmation_id);
      } else {
        await payStripeDeposit(ACTIVE_DOSSIER_BOOKING.confirmation_id);
      }
      const updated = (BOARD_DATA.bookings || []).find(b => b.confirmation_id === ACTIVE_DOSSIER_BOOKING.confirmation_id);
      if (updated) openTicketDossierModal(updated);
    }

    async function releaseHoldFromDossier() {
      if (!ACTIVE_DOSSIER_BOOKING) return;
      if (!confirm(`Are you sure you want to release the pre-authorization hold for ${ACTIVE_DOSSIER_BOOKING.customer_name}? This drops the hold with zero card charges.`)) return;
      await releaseStripeHold(ACTIVE_DOSSIER_BOOKING.confirmation_id);
      const updated = (BOARD_DATA.bookings || []).find(b => b.confirmation_id === ACTIVE_DOSSIER_BOOKING.confirmation_id);
      if (updated) openTicketDossierModal(updated);
    }

    function jumpToCallConsoleFromDossier() {
      closeTicketDossierModal();
      switchPortalTab('console');
    }

    function openPrintableWorkOrder(confId = '') {
      const targetId = confId || (ACTIVE_DOSSIER_BOOKING && ACTIVE_DOSSIER_BOOKING.confirmation_id) || (ACTIVE_HERO_BOOKING && ACTIVE_HERO_BOOKING.confirmation_id) || '';
      const url = `/work-order?id=${encodeURIComponent(targetId)}&autoprint=1`;
      window.open(url, '_blank');
    }

    function renderFleetView() {
      const grid = document.getElementById('fleetCardsGrid');
      if (!grid) return;

      const techs = BOARD_DATA.technicians || [];
      const slots = BOARD_DATA.slots || [];
      const bookings = BOARD_DATA.bookings || [];
      const allDates = [...new Set(slots.map(s => s.date))];
      const todayStr = allDates[0] || new Date().toISOString().slice(0, 10);

      document.getElementById('kpiFleetTotal').innerText = techs.length;
      const onCallTech = techs.find(t => t.is_on_call);
      document.getElementById('kpiFleetOnCall').innerText = onCallTech ? onCallTech.name : 'None';
      document.getElementById('kpiFleetOpenSlots').innerText = slots.filter(s => s.time_window_key !== 'emergency_asap' && !s.is_booked && !s.is_blocked && !isSlotWindowElapsed(s.date, s.time_window_key, todayStr)).length;
      document.getElementById('kpiFleetBookedJobs').innerText = bookings.length;

      grid.innerHTML = techs.map(t => {
        const specHtml = (t.specialties || []).map(s => `<span class="spec-pill">${s.replace(/_/g, ' ')}</span>`).join('');
        const safeTech = JSON.stringify(t).replace(/'/g, "&#39;");
        const techBookings = bookings.filter(b => (b.assigned_technician || '').toLowerCase().includes(t.name.toLowerCase()));
        const hasEmerg = techBookings.some(b => (b.urgency_level || '').includes('EMERG') || (b.service_type || '').toLowerCase() === 'emergency');
        const gcalBusy = slots.filter(s => s.technician_id === t.technician_id && s.is_blocked && (s.blocked_reason || '').includes('Google Calendar'));
        const gcalEmail = `${t.name.toLowerCase().replace(/\s+/g, '.')}@apex-electrical.com`;

        let statusBadge = `<span class="${t.is_on_call ? 'tech-badge-oncall' : 'tech-badge-offduty'}">${t.is_on_call ? '● ON-CALL 24/7 LEAD' : 'STANDARD SHIFT'}</span>`;
        if (hasEmerg) {
          statusBadge = `<span class="tech-badge-emerg">🚨 DISPATCHED: CODE RED</span>`;
        } else if (techBookings.length > 0) {
          statusBadge = `<span class="tech-badge-oncall">⚡ ASSIGNED (${techBookings.length} JOB${techBookings.length > 1 ? 'S' : ''})</span>`;
        }

        const activeJobsHtml = techBookings.map(tb => {
          const isEm = (tb.urgency_level || '').includes('EMERG') || (tb.service_type || '').toLowerCase() === 'emergency';
          const safeBooking = JSON.stringify(tb).replace(/'/g, "&#39;");
          const tbTruckShort = (tb.truck_id || t.truck_id || 'TRUCK-01').split('(')[0].trim();
          return `
            <div class="tech-active-job-box ${isEm ? '' : 'routine-job'}">
              <div style="display:flex; justify-content:space-between; align-items:center; font-weight:800; margin-bottom:3px;">
                <span>${isEm ? '🚨 CODE RED DISPATCH' : '🤖 BOOKED BY SARAH AI'} (#${tb.confirmation_id} • 🚐 ${tbTruckShort})</span>
                <span style="font-size:0.78rem;">${tb.display_window || tb.slot_time}</span>
              </div>
              <div><strong>${tb.display_title || tb.service_type}</strong> — ${tb.customer_name}</div>
              <div style="color:#475569; font-size:0.82rem; margin-top:2px;">📍 ${tb.service_address}</div>
              <div style="display:flex; gap:8px; margin-top:8px;">
                ${tb.google_calendar_link ? `<a href="${tb.google_calendar_link}" target="_blank" style="background:#16a34a; color:#fff; text-decoration:none; padding:4px 10px; border-radius:6px; font-size:0.78rem; font-weight:800;">📅 Google Calendar</a>` : ''}
                <button class="btn-slot-act btn-slot-block" onclick='selectCalendarBooking(${safeBooking})'>Inspect Ticket</button>
              </div>
            </div>
          `;
        }).join('');

        const gcalBusyHtml = gcalBusy.map(gb => `
          <div style="background:#eff6ff; border:1px dashed #3b82f6; border-radius:8px; padding:8px 10px; font-size:0.82rem; color:#1e3a8a; font-weight:700;">
            ${gb.blocked_reason} (${gb.date} • ${gb.time_window})
          </div>
        `).join('');

        return `
          <div class="tech-card-pro ${hasEmerg ? 'is-dispatched-emerg' : (techBookings.length > 0 ? 'is-dispatched-routine' : '')}">
            <div class="tech-card-top">
              <div class="tech-avatar">${hasEmerg ? '🚨' : '👷'}</div>
              <div style="flex:1;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap;">
                  <div class="tech-name">${t.name}</div>
                  ${statusBadge}
                </div>
                <div class="tech-license">${t.license_type} &bull; ⭐ ${t.rating || 4.95}</div>
                <div class="tech-phone">${t.phone} &bull; <strong style="color:#0f172a;">🚐 ${t.truck_id || 'TRUCK-01 (Master Emergency Van)'}</strong></div>
              </div>
            </div>

            <div class="tech-gcal-row">
              <span>📅 GCal: <strong>${gcalEmail}</strong></span>
              <span style="color:#16a34a;">✓ Two-Way Synced</span>
            </div>

            ${activeJobsHtml}
            ${gcalBusyHtml}

            <div class="tech-specialties-row">${specHtml}</div>
            <div class="tech-actions-row">
              <button class="btn-tech-toggle-oncall" onclick="toggleTechOnCall('${t.technician_id}')">
                ${t.is_on_call ? 'Remove On-Call' : 'Make On-Call Lead'}
              </button>
              <button class="btn-tech-edit" onclick='openEditTechModal(${safeTech})'>Edit</button>
              <button class="btn-tech-del" onclick="deleteTech('${t.technician_id}', '${t.name}')">✕</button>
            </div>
          </div>
        `;
      }).join('');
    }

    async function triggerGcalTwoWaySync(customUrl = '') {
      const res = await fetch('/api/calendar/gcal-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ external_ics_url: customUrl })
      });
      await res.json();
      await fetchBoardData();
    }

    async function reassignBookingTech(confirmationId, technicianId) {
      const res = await fetch('/api/bookings/reassign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_id: confirmationId, technician_id: technicianId })
      });
      const data = await res.json();
      if (data.booking) {
        showBookingInHero(data.booking);
      }
      await fetchBoardData();
    }

    function openGcalSyncModal() {
      document.getElementById('gcalOutboundInput').value = `${window.location.origin}/api/calendar.ics`;
      document.getElementById('gcalSyncModal').classList.add('active');
    }
    function closeGcalSyncModal() {
      document.getElementById('gcalSyncModal').classList.remove('active');
    }
    async function submitGcalSyncModal() {
      const url = document.getElementById('gcalInboundInput').value.trim();
      closeGcalSyncModal();
      await triggerGcalTwoWaySync(url);
    }

    async function toggleTechOnCall(techId) {
      await fetch('/api/technicians/toggle-on-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ technician_id: techId })
      });
      await fetchBoardData();
    }

    async function toggleBlockSlot(slotId) {
      await fetch('/api/slots/toggle-block', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_id: slotId })
      });
      await fetchBoardData();
    }

    async function deleteTech(techId, name) {
      if (!confirm(`Remove ${name} from demo roster?`)) return;
      await fetch('/api/technicians/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ technician_id: techId })
      });
      await fetchBoardData();
    }

    function openAddTechModal() {
      document.getElementById('techModalTitle').innerText = 'Add Electrician';
      document.getElementById('techIdInput').value = '';
      document.getElementById('techNameInput').value = '';
      document.getElementById('techTruckInput').value = 'TRUCK-05 (Spare Fleet Van)';
      document.getElementById('techModal').classList.add('active');
    }
    function openEditTechModal(tech) {
      document.getElementById('techModalTitle').innerText = `Edit ${tech.name}`;
      document.getElementById('techIdInput').value = tech.technician_id;
      document.getElementById('techNameInput').value = tech.name;
      document.getElementById('techLicenseInput').value = tech.license_type;
      document.getElementById('techPhoneInput').value = tech.phone;
      document.getElementById('techTruckInput').value = tech.truck_id || 'TRUCK-01 (Master Emergency Van)';
      document.getElementById('techOnCallInput').value = tech.is_on_call ? 'true' : 'false';
      document.getElementById('techSpecsInput').value = (tech.specialties || []).join(', ');
      document.getElementById('techModal').classList.add('active');
    }
    function closeAddTechModal() { document.getElementById('techModal').classList.remove('active'); }

    async function submitTechForm() {
      const tid = document.getElementById('techIdInput').value.trim();
      const name = document.getElementById('techNameInput').value.trim();
      if (!name) return alert('Enter a name');
      const payload = {
        technician_id: tid,
        name,
        license_type: document.getElementById('techLicenseInput').value,
        phone: document.getElementById('techPhoneInput').value.trim(),
        truck_id: document.getElementById('techTruckInput').value,
        is_on_call: document.getElementById('techOnCallInput').value === 'true',
        specialties: document.getElementById('techSpecsInput').value.split(',').map(s => s.trim()).filter(Boolean)
      };
      await fetch(tid ? '/api/technicians/update' : '/api/technicians', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      closeAddTechModal();
      await fetchBoardData();
    }

    function updateManualJobPreset() {
      const st = document.getElementById('manualServiceType').value;
      const descEl = document.getElementById('manualIssueDesc');
      if (st.includes('Panel')) {
        descEl.value = '200A Main Breaker Panel Upgrade — flickering lights when dryer runs; thermal check requested';
      } else if (st.includes('EV')) {
        descEl.value = '50A NEMA 14-50 / Level 2 EV Charger installation in attached garage (200A service)';
      } else if (st.includes('Commercial')) {
        descEl.value = 'Commercial 3-phase subpanel & warehouse high-bay LED circuit troubleshooting';
      } else {
        descEl.value = 'Kitchen GFCI circuit tripping intermittently; diagnostic and receptacle replacement';
      }
    }

    function openManualBookModal(preselectedSlotId = '') {
      const select = document.getElementById('manualSlotSelect');
      const allSlots = BOARD_DATA.slots || [];
      const techs = BOARD_DATA.technicians || [];
      const allDates = [...new Set(allSlots.map(s => s.date))];
      const todayStr = allDates[0] || new Date().toISOString().slice(0, 10);

      const slots = allSlots.filter(s => s.time_window_key !== 'emergency_asap' && !s.is_booked && !s.is_blocked && !isSlotWindowElapsed(s.date, s.time_window_key, todayStr));
      select.innerHTML = slots.map(s => {
        const tObj = techs.find(t => t.technician_id === s.technician_id);
        const tTruckShort = tObj && tObj.truck_id ? tObj.truck_id.split('(')[0].trim() : 'TRUCK-01';
        return `<option value="${s.slot_id}">${s.date} • ${s.time_window} — 👷 ${s.technician_name} (🚐 ${tTruckShort})</option>`;
      }).join('');
      if (preselectedSlotId) select.value = preselectedSlotId;

      if (!document.getElementById('manualCustomerName').value.trim()) {
        document.getElementById('manualCustomerName').value = 'Elena Rostova';
        document.getElementById('manualCustomerPhone').value = '(555) 614-8920';
        document.getElementById('manualCustomerEmail').value = 'elena.rostova@example.com';
        document.getElementById('manualCustomerAddress').value = '88 Beacon Hill Rd, Boston';
        updateManualJobPreset();
      }
      document.getElementById('manualBookModal').classList.add('active');
    }
    function closeManualBookModal() { document.getElementById('manualBookModal').classList.remove('active'); }

    async function submitManualBooking() {
      const payload = {
        slot_id: document.getElementById('manualSlotSelect').value,
        service_type: document.getElementById('manualServiceType').value,
        customer_name: document.getElementById('manualCustomerName').value.trim(),
        phone_number: document.getElementById('manualCustomerPhone').value.trim(),
        customer_email: document.getElementById('manualCustomerEmail').value.trim(),
        service_address: document.getElementById('manualCustomerAddress').value.trim(),
        issue_description: document.getElementById('manualIssueDesc').value.trim()
      };
      if (!payload.customer_name || !payload.service_address) return alert('Fill in customer name and address.');
      await fetch('/api/slots/manual-book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      closeManualBookModal();
      await fetchBoardData();
    }

    function copyIcalFeedUrl() {
      const url = `${window.location.origin}/api/calendar.ics`;
      navigator.clipboard.writeText(url).then(() => alert(`Copied iCal URL:\n${url}`));
    }

    function openRoiModal() { document.getElementById('roiModal').classList.add('active'); updateRoiCalculation(); }
    function closeRoiModal() { document.getElementById('roiModal').classList.remove('active'); }
    function updateRoiCalculation() {
      const calls = parseInt(document.getElementById('sliderCalls').value);
      const ticket = parseInt(document.getElementById('sliderTicket').value);
      document.getElementById('valSliderCalls').innerText = `${calls} Calls / Mo`;
      document.getElementById('valSliderTicket').innerText = `$${ticket.toLocaleString()}`;
      const afterHoursCalls = calls * 0.35;
      const recoveredJobsMonthly = afterHoursCalls * 0.62 * 0.70;
      const callCenterAnnualSavings = 650 * 12; // $7,800/yr saved replacing $650/mo human call center
      const upsellAnnualGain = Math.round(recoveredJobsMonthly * 0.35 * 485 * 12);
      const annualGain = Math.round(recoveredJobsMonthly * ticket * 12) + callCenterAnnualSavings + upsellAnnualGain;
      document.getElementById('roiAnnualGain').innerText = `+$${annualGain.toLocaleString()} / yr`;
      document.getElementById('roiBreakdown').innerText = `Based on recovering ${recoveredJobsMonthly.toFixed(1)} missed after-hours jobs/mo + $7,800/yr call center savings`;
    }

    function openTwilioModal() {
      document.getElementById('twilioModal').classList.add('active');
      document.getElementById('twilioUrlInput').value = `${window.location.origin}/api/twilio/voice`;
    }
    function closeTwilioModal() { document.getElementById('twilioModal').classList.remove('active'); }
    function copyTwilioWebhook() {
      navigator.clipboard.writeText(document.getElementById('twilioUrlInput').value).then(() => alert('Copied Webhook URL!'));
    }

    function openPitchModal() { document.getElementById('pitchModal').classList.add('active'); }
    function closePitchModal() { document.getElementById('pitchModal').classList.remove('active'); }

    let recognition;
    let isListening = false;
    function toggleMic() {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) return alert('Speech recognition requires Chrome or Edge.');
      if (!recognition) {
        recognition = new SpeechRec();
        recognition.onresult = (e) => {
          userInput.value = e.results[0][0].transcript;
          sendUserMessage();
        };
        recognition.onend = () => {
          isListening = false;
          const mBtn = document.getElementById('micBtn');
          mBtn.classList.remove('listening');
          mBtn.innerHTML = '🎙️ Speak to Sarah';
          setVoiceIndicatorState('idle', 'Sarah Voice AI Ready', 'Click button to talk live via microphone');
        };
      }
      if (!isListening) {
        recognition.start();
        isListening = true;
        const mBtn = document.getElementById('micBtn');
        mBtn.classList.add('listening');
        mBtn.innerHTML = '⏹️ Listening...';
        setVoiceIndicatorState('listening', '🎙️ Listening to Caller...', 'Speak your electrical issue clearly');
      } else {
        recognition.stop();
      }
    }

    applyBoardData(BOARD_DATA, false);
    const urlParams = new URLSearchParams(window.location.search);
    const initTab = urlParams.get('tab');
    if (initTab === 'calendar' || initTab === 'fleet' || initTab === 'console') {
      switchPortalTab(initTab);
    }
    if (urlParams.get('ticket') === 'true' && BOARD_DATA.bookings && BOARD_DATA.bookings.length > 0) {
      openTicketDossierModal(BOARD_DATA.bookings[BOARD_DATA.bookings.length - 1]);
    }
    if (urlParams.get('roi') === 'true') {
      openRoiModal();
    }
    window.addEventListener('DOMContentLoaded', () => fetchBoardData());
  </script>
</body>
</html>
"""


class DemoRequestHandler(BaseHTTPRequestHandler):
    """Handles web requests for the JobLatch AI Client Demonstration Dashboard."""

    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With")
        self.end_headers()

    def _send_twiml(self, twiml_xml: str):
        data = twiml_xml.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _get_dispatches_list(self) -> List[Dict[str, Any]]:
        dispatches = []
        for b_obj in DB.bookings.values():
            b = enrich_booking_dict(b_obj)
            urg = str(b.get("urgency_level", "")).upper()
            is_emerg = "EMERG" in urg or "emergency" in str(b.get("service_type", "")).lower()
            status_raw = str(b.get("status", "CONFIRMED")).upper()
            if is_emerg:
                status_display = "Active"
            elif status_raw in ("CONFIRMED", "DISPATCHED"):
                status_display = "Active"
            elif status_raw in ("COMPLETED", "PAID_VERIFIED"):
                status_display = "Completed"
            else:
                status_display = status_raw.title()

            dispatches.append({
                "id": b.get("confirmation_id", "WO-1000"),
                "status": status_display,
                "caller": b.get("customer_name", "Resident / Caller"),
                "phone": b.get("phone_number", "(555) 000-0000"),
                "address": b.get("service_address", "Local Service Area"),
                "trade": "Electrical",
                "service_type": b.get("service_title") or b.get("service_type") or "Residential Electrical Service",
                "ai_summary": b.get("symptom") or b.get("issue_description") or "Electrical service call",
                "time": b.get("slot_window") or b.get("slot_time") or "Today",
                "assigned_technician": b.get("assigned_technician", "On-Call Electrician"),
                "truck_id": b.get("truck_id", "TRUCK-01"),
                "urgency_level": b.get("urgency_level", "STANDARD"),
                "payment_status": b.get("payment_status", "PENDING_AUTHORIZATION"),
                "dispatch_fee": float(b.get("dispatch_fee", 89.0)),
                "created_at": str(b.get("created_at", "")),
                # Canonical alias keys for immediate access
                "confirmation_id": b.get("confirmation_id", "WO-1000"),
                "customer_name": b.get("customer_name", "Resident / Caller"),
                "issue_description": b.get("issue_description", "Electrical service call"),
            })
        return dispatches

    def _get_board_payload(self) -> Dict[str, Any]:
        roi = DB.calculate_contractor_roi_metrics()
        return {
            "dispatches": self._get_dispatches_list(),
            "bookings": [enrich_booking_dict(b) for b in DB.bookings.values()],
            "emergencies": [e.__dict__ for e in DB.emergency_reports.values()],
            "technicians": [t.__dict__ for t in DB.technicians.values()],
            "slots": [s.__dict__ for s in DB.calendar_slots.values()],
            "missed_calls": list(DB.missed_calls.values()),
            "roi_metrics": roi,
            "contractor_email": DEMO_DISPLAY_EMAIL,
            "contractor_phone": DEFAULT_CONFIG.contractor_phone,
            "last_dialogue": LAST_DIALOGUE,
            "last_scenario_mode": LAST_SCENARIO_MODE,
            "gcal_connected": getattr(DB, "gcal_connected", True),
            "gcal_last_sync": getattr(DB, "gcal_last_sync", "Two-Way Sync Active"),
            "gcal_external_url": getattr(DB, "gcal_external_url", ""),
            "active_fsm_platform": getattr(DB, "active_fsm_platform", "HOUSECALL_PRO"),
        }

    def do_GET(self):
        global DEMO_DISPLAY_EMAIL
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html", "/landing", "/home"):
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    page_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(page_data)))
                self.end_headers()
                self.wfile.write(page_data)
                return
            board_json = json.dumps(self._get_board_payload())
            page_html = HTML_DASHBOARD.replace(
                "let BOARD_DATA = { bookings: [], technicians: [], slots: [], roi_metrics: {} };",
                f"let BOARD_DATA = {board_json};",
                1,
            )
            data = page_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        elif parsed.path in ("/dashboard", "/console", "/app", "/demo"):
            board_json = json.dumps(self._get_board_payload())
            page_html = HTML_DASHBOARD.replace(
                "let BOARD_DATA = { bookings: [], technicians: [], slots: [], roi_metrics: {} };",
                f"let BOARD_DATA = {board_json};",
                1,
            )
            data = page_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        elif parsed.path == "/api/board":
            self._send_json(self._get_board_payload())

        elif parsed.path == "/api/dispatches":
            self._send_json(self._get_dispatches_list())

        elif parsed.path == "/api/fsm/payload":
            qs = urllib.parse.parse_qs(parsed.query)
            cid = (qs.get("id", [""])[0] or "").strip()
            platform = (qs.get("platform", [""])[0] or "").strip() or None
            if not cid and DB.bookings:
                live_b = [b for b in DB.bookings.values() if not getattr(b, "is_demo_seed", False)]
                cid = live_b[-1].confirmation_id if live_b else list(DB.bookings.values())[-1].confirmation_id
            payload_data = DB.generate_fsm_webhook_payload(cid, platform)
            self._send_json(payload_data)

        elif parsed.path == "/work-order":
            qs = urllib.parse.parse_qs(parsed.query)
            cid = (qs.get("id", [""])[0] or "").strip()
            target_booking = DB.bookings.get(cid) if cid else None
            if not target_booking and DB.bookings:
                live_b = [b for b in DB.bookings.values() if not getattr(b, "is_demo_seed", False)]
                target_booking = live_b[-1] if live_b else list(DB.bookings.values())[-1]
            if not target_booking:
                self.send_response(404)
                self.end_headers()
                return
            wo_html = render_printable_work_order_html(target_booking, DEMO_DISPLAY_EMAIL)
            data = wo_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif parsed.path in ("/monitor", "/react"):
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "joblatch_react_dashboard.html")
            if not os.path.exists(html_path):
                html_path = "/home/sglenn21/.gemini/antigravity/brain/0c957ebd-6431-4284-8987-1b9ba147bc8e/joblatch_react_dashboard.html"
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    page_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(page_data)))
                self.end_headers()
                self.wfile.write(page_data)
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        elif parsed.path in ("/privacy", "/privacy.html"):
            privacy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "privacy.html")
            if os.path.exists(privacy_path):
                with open(privacy_path, "rb") as f:
                    page_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page_data)))
                self.end_headers()
                self.wfile.write(page_data)
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        elif parsed.path in ("/terms", "/terms.html"):
            terms_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terms.html")
            if os.path.exists(terms_path):
                with open(terms_path, "rb") as f:
                    page_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page_data)))
                self.end_headers()
                self.wfile.write(page_data)
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        elif parsed.path == "/api/calendar.ics":
            from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
            ics_content = CALENDAR_SYNC.generate_master_feed_ics(list(DB.bookings.values()))
            data = ics_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="joblatch_dispatch.ics"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path == "/favicon.ico":
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "joblatch_soundwave_icon.jpg")
            if os.path.exists(ico_path):
                with open(ico_path, "rb") as f:
                    img_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(len(img_data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(img_data)
            else:
                self.send_response(404)
                self.end_headers()
            return

        elif parsed.path.startswith("/assets/"):
            rel_path = parsed.path[len("/assets/"):]
            base_assets = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
            full_path = os.path.abspath(os.path.join(base_assets, rel_path))
            # Security: avoid directory traversal
            if full_path.startswith(base_assets) and os.path.isfile(full_path):
                ext = os.path.splitext(full_path)[1].lower()
                mime_map = {
                    ".mp3": "audio/mpeg",
                    ".wav": "audio/wav",
                    ".json": "application/json",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                }
                content_type = mime_map.get(ext, "application/octet-stream")
                with open(full_path, "rb") as f:
                    file_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(file_data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(file_data)
            else:
                self.send_response(404)
                self.end_headers()
            return

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global ACTIVE_SESSION, DEMO_DISPLAY_EMAIL, LAST_DIALOGUE, LAST_SCENARIO_MODE
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
        content_type = self.headers.get("Content-Type", "")

        if "application/x-www-form-urlencoded" in content_type:
            parsed_form = urllib.parse.parse_qs(post_body)
            req_data = {k: v[0] if len(v) == 1 else v for k, v in parsed_form.items()}
        else:
            try:
                req_data = json.loads(post_body) if post_body else {}
            except Exception:
                req_data = {}

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/twilio/voice":
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Response>\n'
                '  <Gather input="speech" action="https://zeromissdispatch.com/api/twilio/gather" timeout="4" speechTimeout="auto">\n'
                '    <Say voice="Polly.Joanna-Neural">'
                'Thank you for calling JobLatch AI Electrical 24/7 Dispatch. My name is Sarah. '
                'Are you reporting an electrical emergency, or calling to schedule service?'
                '</Say>\n'
                '  </Gather>\n'
                '  <Redirect>/api/twilio/voice</Redirect>\n'
                '</Response>'
            )
            self._send_twiml(twiml)
            return

        elif parsed.path == "/api/twilio/gather":
            speech_result = req_data.get("SpeechResult", "").strip() or "Hello, I need an electrician."
            speech_lower = speech_result.lower()

            # Catch escalation keywords directly without relying on Gemini's exact phrasing
            transfer_keywords = ["sean", "glenn", "speak to a human", "speak to someone", "operator", "transfer", "owner"]
            if any(kw in speech_lower for kw in transfer_keywords):
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    '  <Say voice="Polly.Joanna-Neural">Hold on one moment, I will transfer you directly to Sean Glenn right now.</Say>\n'
                    '  <Dial timeout="20">609-972-4328</Dial>\n'
                    '</Response>'
                )
                self._send_twiml(twiml)
                return

            try:
                sarah_reply = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, speech_result)
            except Exception as e:
                print(f"[ERROR] Voice agent processing error: {e}")
                sarah_reply = "I understand. Let me get an electrician dispatched to your location right away."

            clean_reply = sarah_reply.replace("&", "and").replace("<", "").replace(">", "")

            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Response>\n'
                '  <Gather input="speech" action="https://zeromissdispatch.com/api/twilio/gather" timeout="4" speechTimeout="auto">\n'
                f'    <Say voice="Polly.Joanna-Neural">{clean_reply}</Say>\n'
                '  </Gather>\n'
                '  <Say voice="Polly.Joanna-Neural">Thank you for calling JobLatch AI. Goodbye.</Say>\n'
                '  <Hangup/>\n'
                '</Response>'
            )
            self._send_twiml(twiml)
            return

        elif parsed.path == "/api/bookings/hold":
            cid = req_data.get("confirmation_id", "").strip()
            pm_id = req_data.get("payment_method_id", "pm_card_visa").strip()
            booking = DB.place_authorization_hold(cid, pm_id)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/capture":
            cid = req_data.get("confirmation_id", "").strip()
            amt_cents = req_data.get("amount_cents")
            booking = DB.capture_dispatch_fee(cid, amt_cents)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/release":
            cid = req_data.get("confirmation_id", "").strip()
            reason = req_data.get("reason", "customer_requested").strip()
            booking = DB.release_dispatch_hold(cid, reason)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/pay":
            cid = req_data.get("confirmation_id", "").strip()
            target = DB.bookings.get(cid)
            if target and target.payment_status == "PENDING_AUTHORIZATION":
                booking = DB.place_authorization_hold(cid)
            elif target and target.payment_status == "AUTHORIZED_HOLD":
                booking = DB.capture_dispatch_fee(cid)
            else:
                booking = DB.mark_booking_paid(cid)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/reassign":
            cid = req_data.get("confirmation_id", "").strip()
            tid = req_data.get("technician_id", "").strip()
            booking = DB.reassign_booking_technician(cid, tid)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking or technician not found"}, 404)

        elif parsed.path == "/api/bookings/update-truck":
            cid = req_data.get("confirmation_id", "").strip()
            truck_id = req_data.get("truck_id", "").strip()
            booking = DB.update_booking_truck(cid, truck_id)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/upload-photo":
            cid = req_data.get("confirmation_id", "").strip()
            booking = DB.attach_panel_photo_analysis(cid)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/en-route":
            cid = req_data.get("confirmation_id", "").strip()
            booking = DB.mark_tech_en_route(cid)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/request-review":
            cid = req_data.get("confirmation_id", "").strip()
            booking = DB.mark_review_requested(cid)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/send-quote":
            cid = req_data.get("confirmation_id", "").strip()
            booking = DB.send_three_option_quote(cid)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/select-option":
            cid = req_data.get("confirmation_id", "").strip()
            tier = req_data.get("tier", "GOOD").strip()
            booking = DB.select_quote_option(cid, tier)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/bookings/pay-balance":
            cid = req_data.get("confirmation_id", "").strip()
            booking = DB.mark_final_balance_paid(cid)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking), "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/tech/update-stage":
            cid = req_data.get("confirmation_id", "").strip()
            stage = req_data.get("stage", "DISPATCHED").strip()
            booking = DB.update_tech_workflow_stage(cid, stage)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/tech/save-diagnostics":
            cid = req_data.get("confirmation_id", "").strip()
            readings = req_data.get("readings", {})
            booking = DB.save_diagnostic_readings(cid, readings)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/tech/sign-authorization":
            cid = req_data.get("confirmation_id", "").strip()
            signer_name = req_data.get("signer_name", "").strip()
            booking = DB.sign_customer_work_authorization(cid, signer_name)
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/calendar/gcal-sync":
            ext_url = req_data.get("external_ics_url", "").strip() or None
            sync_info = DB.sync_google_calendar_busy_blocks(ext_url)
            self._send_json({"status": "SUCCESS", "sync_info": sync_info})

        elif parsed.path == "/api/simulate-missed-call":
            LAST_SCENARIO_MODE = "missed_call"
            mc = DB.record_missed_call(
                caller_phone="(555) 329-8471",
                estimated_value=1200.0,
                caller_name="Alex Rivera",
            )
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "missed_call": mc,
                "message": "Automated text-back fired to lost lead within 3 seconds.",
                "roi_metrics": roi,
            })

        elif parsed.path == "/api/missed-calls/convert":
            LAST_SCENARIO_MODE = "missed_call"
            mc_id = req_data.get("missed_call_id")
            mc = DB.convert_missed_call(mc_id)
            booking_dict = None
            if mc and mc.get("booking_confirmation_id"):
                b = DB.bookings.get(mc["booking_confirmation_id"])
                if b:
                    booking_dict = enrich_booking_dict(b, scenario_hint="missed_call")
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "missed_call": mc,
                "booking": booking_dict,
                "roi_metrics": roi,
                "bookings": [enrich_booking_dict(b) for b in DB.bookings.values()],
                "slots": [s.__dict__ for s in DB.calendar_slots.values()],
            })

        elif parsed.path == "/api/benchmark/toggle":
            is_bench = DB.toggle_benchmark_mode()
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "is_benchmark": is_bench,
                "roi_metrics": roi,
            })

        elif parsed.path == "/api/fsm/switch":
            platform = req_data.get("platform", "HOUSECALL_PRO").strip()
            DB.set_active_fsm_platform(platform)
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "active_fsm_platform": DB.active_fsm_platform,
                "bookings": [enrich_booking_dict(b) for b in DB.bookings.values()],
                "roi_metrics": roi,
            })

        elif parsed.path == "/api/set-contractor":
            new_email = req_data.get("email", "").strip()
            if new_email:
                DEMO_DISPLAY_EMAIL = new_email
                DEFAULT_CONFIG.contractor_email = new_email
            self._send_json({"status": "SUCCESS", "contractor_email": DEMO_DISPLAY_EMAIL})

        elif parsed.path == "/api/technicians":
            name = req_data.get("name", "").strip()
            if not name:
                self._send_json({"status": "ERROR", "message": "Technician name required"}, 400)
                return
            new_tech = DB.add_technician(
                name=name,
                license_type=req_data.get("license_type", "Journeyman Electrician").strip(),
                phone=req_data.get("phone", "(555) 019-0000").strip(),
                is_on_call=bool(req_data.get("is_on_call", False)),
                specialties=req_data.get("specialties", ["residential_repair", "lighting"]),
                truck_id=req_data.get("truck_id", "").strip(),
            )
            self._send_json({
                "status": "SUCCESS",
                "technician": new_tech.__dict__,
                "technicians": [t.__dict__ for t in DB.technicians.values()],
                "slots": [s.__dict__ for s in DB.calendar_slots.values()],
            })

        elif parsed.path == "/api/technicians/update":
            tid = req_data.get("technician_id", "").strip()
            tech = DB.update_technician(
                tid,
                req_data.get("name", "").strip(),
                req_data.get("license_type", "Journeyman Electrician").strip(),
                req_data.get("phone", "(555) 019-0000").strip(),
                bool(req_data.get("is_on_call", False)),
                req_data.get("specialties", ["residential_repair"]),
                truck_id=req_data.get("truck_id", "").strip(),
            )
            if tech:
                self._send_json({"status": "SUCCESS", "technician": tech.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Technician not found"}, 404)

        elif parsed.path == "/api/technicians/toggle-on-call":
            tid = req_data.get("technician_id", "").strip()
            tech = DB.toggle_technician_on_call(tid)
            if tech:
                self._send_json({"status": "SUCCESS", "technician": tech.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Technician not found"}, 404)

        elif parsed.path == "/api/technicians/delete":
            tid = req_data.get("technician_id", "").strip()
            ok = DB.delete_technician(tid)
            self._send_json({"status": "SUCCESS" if ok else "ERROR"})

        elif parsed.path == "/api/slots/toggle-block":
            slot_id = req_data.get("slot_id", "").strip()
            slot = DB.toggle_block_slot(slot_id, req_data.get("reason", "Unavailable / Off-Duty").strip())
            if slot:
                self._send_json({"status": "SUCCESS", "slot": slot.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Slot not found"}, 404)

        elif parsed.path == "/api/slots/manual-book":
            booking = DB.manual_book_slot(
                slot_id=req_data.get("slot_id", "").strip(),
                customer_name=req_data.get("customer_name", "Valued Customer").strip(),
                phone_number=req_data.get("phone_number", "(555) 000-0000").strip(),
                service_address=req_data.get("service_address", "Customer Address").strip(),
                issue_description=req_data.get("issue_description", "Electrical service call").strip(),
                customer_email=req_data.get("customer_email", "").strip() or None,
                service_type=req_data.get("service_type", "200A Main Panel Upgrade").strip(),
            )
            if booking:
                self._send_json({"status": "SUCCESS", "booking": enrich_booking_dict(booking)})
            else:
                self._send_json({"status": "ERROR", "message": "Failed to book slot"}, 400)

        elif parsed.path == "/api/chat":
            msg = req_data.get("message", "").strip()
            sarah_response = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, msg)
            booking_dict = None
            if ACTIVE_SESSION.active_booking:
                booking_dict = enrich_booking_dict(ACTIVE_SESSION.active_booking)
            else:
                live_bookings = [b for b in DB.bookings.values() if not getattr(b, "is_demo_seed", False)]
                if live_bookings:
                    booking_dict = enrich_booking_dict(live_bookings[-1])
            self._send_json({
                "status": "SUCCESS",
                "response": sarah_response,
                "booking": booking_dict,
            })

        elif parsed.path == "/api/run-scenario":
            DB.reset()
            ACTIVE_SESSION = ACTIVE_AGENT.create_session()
            scenario = req_data.get("scenario", "emergency")
            LAST_SCENARIO_MODE = "emergency" if scenario == "emergency" else "routine"
            dialogue = []

            if scenario == "emergency":
                t1_user = "Help, I smell burning rubber coming from the wall behind my refrigerator!"
                dialogue.append({"speaker": "David Miller (Caller)", "text": t1_user, "isSarah": False})
                t1_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t1_user)
                dialogue.append({"speaker": "Sarah (JobLatch AI)", "text": t1_sarah, "isSarah": True})

                t2_user = "My name is David Miller, 742 Evergreen Terrace, callback number is (555) 482-9104"
                dialogue.append({"speaker": "David Miller (Caller)", "text": t2_user, "isSarah": False})
                t2_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t2_user)
                dialogue.append({"speaker": "Sarah (JobLatch AI)", "text": t2_sarah, "isSarah": True})
            else:
                t1_user = "Hi Sarah, I just bought an EV and need a 50-amp Level 2 charger installed in my garage."
                dialogue.append({"speaker": "Alex Rivera (Caller)", "text": t1_user, "isSarah": False})
                t1_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t1_user)
                dialogue.append({"speaker": "Sarah (JobLatch AI)", "text": t1_sarah, "isSarah": True})

                t2_user = "Tomorrow morning works. My name is Alex Rivera, 45 Innovation Way in Cambridge, (555) 829-1044, alex@example.com"
                dialogue.append({"speaker": "Alex Rivera (Caller)", "text": t2_user, "isSarah": False})
                t2_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t2_user)
                dialogue.append({"speaker": "Sarah (JobLatch AI)", "text": t2_sarah, "isSarah": True})

            LAST_DIALOGUE = dialogue
            live_bookings = [b for b in DB.bookings.values() if not getattr(b, "is_demo_seed", False)]
            booking_dict = enrich_booking_dict(live_bookings[-1], scenario_hint=scenario) if live_bookings else None
            self._send_json({
                "status": "SUCCESS",
                "scenario": scenario,
                "dialogue": dialogue,
                "booking": booking_dict,
            })

        elif parsed.path == "/api/reset":
            DB.reset()
            ACTIVE_SESSION = ACTIVE_AGENT.create_session()
            LAST_DIALOGUE = []
            LAST_SCENARIO_MODE = "missed_call"
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({"status": "RESET_COMPLETED", "roi_metrics": roi})

        elif parsed.path == "/api/call-demo":
            client_ip = self.client_address[0] if hasattr(self, "client_address") and self.client_address else "unknown"
            phone = req_data.get("phone", "").strip()
            consent = req_data.get("consent", False)
            captcha_answer = str(req_data.get("captcha_answer", "")).strip()

            # 1. Require explicit consent checkbox
            if not consent:
                self._send_json({"status": "ERROR", "message": "Consent is required: please check the box agreeing to receive an automated demo call."}, 400)
                return

            # 2. Basic verification challenge validation
            if captcha_answer and captcha_answer != "7":
                self._send_json({"status": "ERROR", "message": "Security verification answer is incorrect. Please try again."}, 400)
                return

            # 3. Clean and validate 10-digit North American phone number
            digits = re.sub(r"\D", "", phone)
            if digits.startswith("1") and len(digits) == 11:
                digits = digits[1:]
            if len(digits) != 10 or digits[0] in ("0", "1") or digits[3] in ("0", "1"):
                self._send_json({"status": "ERROR", "message": "Please enter a valid 10-digit North American mobile phone number."}, 400)
                return

            now = time.time()

            # 4. IP-based rate limiting (maximum 3 demo calls per hour per IP)
            ip_times = [t for t in DEMO_CALL_RATE_LIMIT_IP.get(client_ip, []) if now - t < 3600]
            if len(ip_times) >= 3:
                self._send_json({"status": "ERROR", "message": "Rate limit exceeded: maximum 3 demo calls per hour for your network. Book a 15-min shop setup for a full walkthrough."}, 429)
                return

            # 5. Phone-based rate limiting (maximum 1 demo call per 5 minutes per number)
            phone_times = [t for t in DEMO_CALL_RATE_LIMIT_PHONE.get(digits, []) if now - t < 300]
            if len(phone_times) >= 1:
                self._send_json({"status": "ERROR", "message": "A demo call was recently requested for this number. Please wait 5 minutes before requesting another."}, 429)
                return

            # Record request timestamps
            ip_times.append(now)
            DEMO_CALL_RATE_LIMIT_IP[client_ip] = ip_times
            phone_times.append(now)
            DEMO_CALL_RATE_LIMIT_PHONE[digits] = phone_times

            print(f"[DEMO CALL INITIATED] Sarah AI dispatch dialing {phone} (IP: {client_ip})...")
            self._send_json({
                "status": "SUCCESS",
                "phone": phone,
                "message": f"Sarah is dialing you now at {phone}. Answer your phone for the live emergency dispatch demo!"
            })

        elif parsed.path == "/api/shop-setup":
            shop_name = req_data.get("shop_name", "").strip() or "Trade Contractor Shop"
            contact_name = req_data.get("contact_name", "").strip() or "Shop Owner"
            phone = req_data.get("phone", "").strip()
            email = req_data.get("email", "").strip()
            trade = req_data.get("trade", "Electrical").strip()
            window = req_data.get("time_window", "Morning").strip()
            print(f"[SHOP SETUP REQUESTED] {shop_name} ({contact_name}, {phone}, {email}, {trade}, {window})")
            self._send_json({
                "status": "SUCCESS",
                "message": f"Shop setup requested for {shop_name}. An engineer will confirm your slot at {phone}."
            })

        elif parsed.path == "/api/tier-onboard":
            tier_key = req_data.get("tier_key", "pro").strip()
            shop_name = req_data.get("shop_name", "").strip() or "Trade Contractor Shop"
            contact_name = req_data.get("contact_name", "").strip() or "Shop Owner"
            phone = req_data.get("phone", "").strip()
            email = req_data.get("email", "").strip()
            fsm = req_data.get("fsm", "ServiceTitan").strip()
            print(f"[TIER ONBOARDING] {tier_key.upper()} - {shop_name} ({contact_name}, {phone}, {email}, FSM: {fsm})")
            self._send_json({
                "status": "SUCCESS",
                "message": f"Onboarding initiated for {tier_key} tier for {shop_name}."
            })

        else:
            self.send_response(404)
            self.end_headers()


def run_demo_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), DemoRequestHandler)
    print("\n" + "=" * 80)
    print("  JobLatch AI Voice Dispatch - Story-Driven Interactive Demo Server")
    print(f"  Live Demo Web Dashboard: http://localhost:{port}")
    print(f"  Demo Alert Destination:  {DEMO_DISPLAY_EMAIL}")
    print(f"  Live Twilio Voice Webhook: http://localhost:{port}/api/twilio/voice")
    print("=" * 80 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo Server Stopped.")
        server.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("PORT", "8080"))
    run_demo_server(port_arg)
