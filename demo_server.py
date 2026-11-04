"""ZeroMiss Voice Dispatch - Story-Driven Interactive Demo & Fleet Command Server.

Designed around the core end-to-end product story:
Missed Call / Live Voice -> AI Triage & Safety Verification -> Instant Dispatch -> Upfront Stripe Deposit.
"""

import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB


# Global state for demo session
ACTIVE_AGENT = VoiceDispatchAgent()
ACTIVE_SESSION = ACTIVE_AGENT.create_session()
DEMO_DISPLAY_EMAIL = "dispatch@apex-electrical-demo.com"
LAST_DIALOGUE = []
LAST_SCENARIO_MODE = "missed_call"


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
        safety_given = (
            "Stay clear of the appliance and wall outlet; do not touch the cord. "
            "Shut off the main breaker only if the path is dry and safe. Evacuate and call 911 if smoke appears."
        )
    else:
        if "ev" in raw_service.lower() or "ev" in issue_lower or "charger" in issue_lower:
            clean_title = f"EV Charger Installation — {clean_customer}"
            symptom = "50A NEMA 14-50 / Level 2 EV charger installation in residential garage"
        elif raw_service:
            clean_title = f"{raw_service.replace('_', ' ').title()} — {clean_customer}"
            symptom = raw_issue or f"Scheduled {raw_service.replace('_', ' ')} service call"
        else:
            clean_title = f"Residential Electrical Service — {clean_customer}"
            symptom = raw_issue or "Standard diagnostic and electrical repair"
        hazard_level = "Routine Service — Non-Hazardous (200A Panel Verified)"
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

    b["display_title"] = clean_title
    b["display_window"] = clean_window
    b["triage_symptom"] = symptom
    b["triage_hazard_level"] = hazard_level
    b["triage_safety_instruction"] = safety_given
    return b


HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ZeroMiss Voice Dispatch | Interactive Product Demo</title>
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
      background: #2563eb;
      color: white;
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      font-weight: 800;
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
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: #2563eb;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.95rem;
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

    .full-calendar-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
    }
    @media (max-width: 1100px) { .full-calendar-grid { grid-template-columns: repeat(2, 1fr); } }
    .cal-col {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
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
    .cal-col-sub { font-size: 0.88rem; color: var(--text-muted); font-weight: 600; }
    .cal-col-body { padding: 12px; display: flex; flex-direction: column; gap: 10px; flex: 1; }
    .slot-box {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      background: var(--surface-muted);
    }
    .slot-time-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.88rem; margin-bottom: 6px; font-weight: 800; }
    .slot-tech-avail { font-size: 0.86rem; color: var(--text-body); margin-bottom: 8px; line-height: 1.4; }
    .slot-actions { display: flex; gap: 6px; flex-wrap: wrap; }
    .btn-slot-act { padding: 6px 11px; border-radius: 6px; font-size: 0.82rem; font-weight: 700; cursor: pointer; border: none; }
    .btn-slot-book { background: var(--primary); color: white; }
    .btn-slot-block { background: #e2e8f0; color: var(--text-body); }
    .slot-box.is-booked-routine { background: #f0fdf4; border: 2px solid #22c55e; }
    .slot-box.is-booked-emergency { background: #fff1f2; border: 2px solid #dc2626; }
    .slot-box.is-gcal-busy { background: #eff6ff; border: 1.5px dashed #3b82f6; }
    .booked-cust-name { font-size: 0.98rem; font-weight: 800; margin-bottom: 4px; color: var(--text-main); }
    .booked-cust-meta { font-size: 0.86rem; line-height: 1.4; color: var(--text-body); }
    .tech-avail-pills { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
    .tech-mini-pill {
      font-size: 0.78rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      color: #1e293b;
    }
    .tech-mini-pill.busy-pill {
      background: #fee2e2;
      border-color: #fca5a5;
      color: #991b1b;
    }
    .tech-mini-pill.gcal-pill {
      background: #dbeafe;
      border-color: #93c5fd;
      color: #1e40af;
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
      <div class="brand-icon">⚡</div>
      <div>
        <div class="brand-title-row">
          <h1>ZeroMiss Voice Dispatch</h1>
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
        <button class="nav-tab" id="btnTabCalendar" onclick="switchPortalTab('calendar')">
          📅 Dispatch Calendar <span class="nav-count" id="calCountPill">0</span>
        </button>
        <button class="nav-tab" id="btnTabFleet" onclick="switchPortalTab('fleet')">
          👷 Tech Roster <span class="nav-count" id="techCountPill">4</span>
        </button>
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
              <div class="speaker-name">Sarah (ZeroMiss AI Dispatcher)</div>
              Thank you for calling ZeroMiss Electrical 24/7 Dispatch. Click <strong>"▶ Start Demo"</strong> above, press <strong>"🎙️ Speak to Sarah"</strong>, or type any electrical issue below!
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
            <!-- Customer Smartphone Outcome -->
            <div class="phone-column-wrap">
              <div class="phone-chassis" id="phoneChassis">
                <div class="phone-screen">
                  <div class="phone-dynamic-island"></div>
                  <div class="phone-status-bar">
                    <span>9:41</span>
                    <span>5G &bull; 92%</span>
                  </div>
                  <div class="phone-imessage-header">
                    <div class="imessage-avatar">ZM</div>
                    <div>
                      <div class="imessage-name">ZeroMiss Dispatch ✓</div>
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
          <a href="/api/calendar.ics" class="btn-gcal-outline" download="zeromiss_schedule.ics">⬇️ Export .ICS</a>
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
  </main>

  <!-- MODAL: Sales Pitch -->
  <div class="modal-overlay" id="pitchModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>💡 The End-to-End Story: Why Contractors Buy ZeroMiss</h3>
        <button class="modal-close" onclick="closePitchModal()">&times;</button>
      </div>
      <div style="font-size:1rem; color:var(--text-body); line-height:1.6;">
        <p style="margin-bottom:14px;">
          <strong>The Problem:</strong> 35% of homeowner calls happen after hours or while electricians are on a ladder. 80% of callers who hit voicemail hang up and call the next contractor on Google.
        </p>
        <p style="margin-bottom:14px;">
          <strong>The ZeroMiss Journey:</strong>
        </p>
        <ol style="margin-left:20px; margin-bottom:18px; display:flex; flex-direction:column; gap:8px;">
          <li><strong>Missed Call Intercepted:</strong> Sarah detects the dropped call and texts the customer within 3 seconds.</li>
          <li><strong>Instant Booking:</strong> Customer taps the link on their phone to lock in tomorrow's 8:00 AM slot (+$1,200 pipeline booked).</li>
          <li><strong>No-Show Elimination:</strong> Customer authorizes the $89 diagnostic deposit via Stripe right inside the SMS thread, moving the job to <strong>Revenue Won</strong>.</li>
        </ol>
        <button class="btn-modal-submit" onclick="closePitchModal()">Got It — Back to Demo</button>
      </div>
    </div>
  </div>

  <!-- MODAL: ROI Calculator -->
  <div class="modal-overlay" id="roiModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>📊 Contractor ROI Calculator</h3>
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

        <div class="roi-result-banner">
          <div style="font-size:0.88rem; font-weight:800; color:#15803d; text-transform:uppercase;">Projected Recouped Annual Revenue</div>
          <div class="roi-big-gain" id="roiAnnualGain">+$109,368 / yr</div>
          <div style="font-size:0.9rem; color:var(--text-muted);" id="roiBreakdown">Based on recovering 7.6 missed after-hours jobs/month</div>
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
          <label>On-Call Status:</label>
          <select id="techOnCallInput">
            <option value="false">Standard Hours</option>
            <option value="true">On-Call 24/7 Lead</option>
          </select>
        </div>
        <div class="form-group"><label>Specialties:</label><input type="text" id="techSpecsInput" value="residential_repair, lighting"></div>
        <button class="btn-modal-submit" onclick="submitTechForm()">Save Electrician</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Manual Booking -->
  <div class="modal-overlay" id="manualBookModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>+ Manual Dispatch Booking</h3>
        <button class="modal-close" onclick="closeManualBookModal()">&times;</button>
      </div>
      <div>
        <div class="form-group"><label>Select Slot:</label><select id="manualSlotSelect"></select></div>
        <div class="form-group"><label>Customer Name:</label><input type="text" id="manualCustomerName"></div>
        <div class="form-group"><label>Phone:</label><input type="text" id="manualCustomerPhone"></div>
        <div class="form-group"><label>Email:</label><input type="email" id="manualCustomerEmail"></div>
        <div class="form-group"><label>Address:</label><input type="text" id="manualCustomerAddress"></div>
        <div class="form-group"><label>Issue Description:</label><textarea id="manualIssueDesc" rows="2"></textarea></div>
        <button class="btn-modal-submit" onclick="submitManualBooking()">Confirm Booking</button>
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
          ZeroMiss syncs two-way with your shop's <strong>Google Calendar</strong> so dispatches appear immediately on your phone and external events block Sarah from double-booking your electricians:
        </p>
        <div class="form-group">
          <label>1. Outbound Feed (Add ZeroMiss Dispatches to Your Google Calendar):</label>
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

  <footer>
    ZeroMiss Voice Dispatch &bull; Interactive Product Demo Environment (Simulated Data)
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
        appendMessage('Sarah (ZeroMiss AI)', data.response, true);
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

    function showBookingInHero(booking) {
      waitingPlaceholder.style.display = 'none';
      dispatchHero.classList.add('active');

      const isEmerg = (booking.urgency_level || '').includes('EMERG') || (booking.service_type || '').toLowerCase() === 'emergency';
      dispatchHero.className = `dispatch-hero active ${isEmerg ? 'is-emergency' : ''}`;

      const bBadge = document.getElementById('heroBadge');
      bBadge.className = `hero-badge ${isEmerg ? 'badge-emergency' : 'badge-standard'}`;
      bBadge.innerText = isEmerg ? '🚨 Code Red Emergency (45m)' : '✓ Confirmed Service Dispatch';

      const payBadge = document.getElementById('heroPayBadge');
      if (booking.payment_status === 'PAID_VERIFIED') {
        payBadge.style.color = '#15803d';
        payBadge.style.background = '#dcfce7';
        payBadge.style.borderColor = '#86efac';
        payBadge.innerText = `✓ $${booking.dispatch_fee} Deposit Paid`;
      } else {
        payBadge.style.color = '#b45309';
        payBadge.style.background = '#fef3c7';
        payBadge.style.borderColor = '#fde68a';
        payBadge.innerText = `💳 Pending $${booking.dispatch_fee} Deposit`;
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
    }

    function pushCustomerSmsBooking(booking) {
      const cleanWin = booking.display_window || 'Today, within 45–60 min';
      const smsHtml = `
        <div class="sms-bubble">
          <div class="sms-tag">Appointment Dispatched</div>
          Hi ${booking.customer_name}, your technician <strong>${booking.assigned_technician.split('(')[0].trim()}</strong> is scheduled for <strong>${cleanWin}</strong>.
          <div class="sms-stripe-sheet">
            <div style="display:flex; justify-content:space-between; font-weight:800; font-size:0.86rem; color:#c7d2fe;">
              <span>💳 STRIPE UPFRONT DEPOSIT</span>
              <span style="color:#4ade80;">$${Number(booking.dispatch_fee).toFixed(2)}</span>
            </div>
            <button class="btn-stripe-pay" onclick="payStripeDeposit('${booking.confirmation_id}')">
              👉 Authorize $${booking.dispatch_fee} Deposit via Stripe
            </button>
          </div>
        </div>
      `;
      phoneMessages.innerHTML = smsHtml;
      phoneMessages.scrollTop = phoneMessages.scrollHeight;
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
              Hi! This is Sarah from ZeroMiss Electrical. We noticed your call dropped! Tap below to lock in tomorrow's 8:00 AM slot right now:
            </div>
            <div class="sms-action-card" onclick="convertMissedCallLead('${mc.missed_call_id}')">
              <div style="font-size:0.82rem; font-weight:800; color:#4ade80;">⚡ 1-TAP SELF-SCHEDULE ($1,200 JOB)</div>
              <div style="font-size:0.98rem; font-weight:800; color:#ffffff; margin:4px 0;">Tomorrow, 8:00 AM &bull; Tech: Sarah Chen</div>
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
          const cid = data.booking ? data.booking.confirmation_id : '';
          phoneMessages.innerHTML = `
            <div class="sms-bubble">
              <div class="recoup-won-badge">✓ SLOT BOOKED ($1,200 PIPELINE)</div>
              <div style="margin:10px 0; font-size:0.95rem;">
                Confirmed for <strong>Tomorrow, 8:00 AM – 12:00 PM</strong> with <strong>Sarah Chen</strong>.
              </div>
              <div class="sms-stripe-sheet">
                <div style="display:flex; justify-content:space-between; font-weight:800; font-size:0.86rem; color:#c7d2fe;">
                  <span>💳 STEP 4: UPFRONT DEPOSIT</span>
                  <span style="color:#4ade80;">$89.00</span>
                </div>
                <button class="btn-stripe-pay" onclick="payStripeDeposit('${cid}')">
                  👉 Authorize $89 Deposit via Stripe
                </button>
              </div>
            </div>
          `;

          if (data.booking) showBookingInHero(data.booking);

          appendMessage('Sarah (ZeroMiss AI)', `✓ Customer booked Tomorrow 8:00 AM – 12:00 PM with Sarah Chen ($1,200 Pipeline Booked). Awaiting $89 Stripe deposit to lock in Revenue Won.`, true);

          setJourneyProgress(
            3,
            '👉 <strong>Next Step (Step 3 of 4):</strong> Slot booked! Now click <strong>"Authorize $89 Deposit via Stripe"</strong> inside the phone to move Pipeline Booked to <strong>Revenue Won</strong>.',
            'phone'
          );

          await fetchBoardData();
        }
      } catch (e) {
        alert('Error converting missed call.');
      }
    }

    // STEP 3 -> STEP 4: Authorize Stripe Deposit
    async function payStripeDeposit(confirmationId) {
      if (!confirmationId && BOARD_DATA.bookings && BOARD_DATA.bookings.length) {
        confirmationId = BOARD_DATA.bookings[BOARD_DATA.bookings.length - 1].confirmation_id;
      }
      try {
        const res = await fetch('/api/bookings/pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation_id: confirmationId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          const feePaid = data.booking ? data.booking.dispatch_fee : 89;
          const jobVal = data.booking ? data.booking.estimated_job_value : 1200;
          document.querySelectorAll('.btn-stripe-pay').forEach(btn => {
            btn.classList.add('paid');
            btn.innerHTML = `✓ $${feePaid} Deposit Paid & Verified`;
            btn.disabled = true;
          });
          const heroPay = document.getElementById('heroPayBadge');
          if (heroPay) {
            heroPay.style.color = '#15803d';
            heroPay.style.background = '#dcfce7';
            heroPay.style.borderColor = '#86efac';
            heroPay.innerHTML = `✓ $${feePaid} Deposit Paid (Locked)`;
          }
          appendMessage('ZeroMiss Billing', `💳 $${Number(feePaid).toFixed(2)} deposit verified via Stripe. $${Number(jobVal).toLocaleString()} job moved from Pipeline Booked to Revenue Won!`, true);

          setJourneyProgress(
            4,
            `🎉 <strong>Journey Complete!</strong> Deposit verified via Stripe — <strong>$${Number(jobVal).toLocaleString()} Revenue Won</strong> + <strong>$${feePaid} Deposit Collected</strong>!`,
            'complete'
          );
          document.getElementById('jStep4').classList.remove('active-step');
          document.getElementById('jStep4').classList.add('done-step');
          document.getElementById('jNum4').innerText = '✓';

          await fetchBoardData();
        }
      } catch (e) {
        alert('Payment error.');
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
          <div class="speaker-name">Sarah (ZeroMiss AI Dispatcher)</div>
          Thank you for calling ZeroMiss Electrical 24/7 Dispatch. Click <strong>"▶ Start Demo"</strong> above, press <strong>"🎙️ Speak to Sarah"</strong>, or type any electrical issue below!
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
        elPipeLabel.innerText = 'Pipeline Booked (Pending Deposit)';
        elPipe.style.color = '#2563eb';
        elPipeSub.innerText = `${bookingsCount} Booked • Moves to "Won" after deposit`;
        animateMetricCountUp(elPipe, cardPipe, animate ? PREV_METRICS.pipeline : pipelineBooked, pipelineBooked, v => `$${v.toLocaleString()}`);
        PREV_METRICS.pipeline = pipelineBooked;
      } else {
        elPipeLabel.innerText = 'Pipeline Booked / Revenue Won';
        elPipe.style.color = '#0f172a';
        elPipeSub.innerText = '0 Dispatches Booked in Session';
        animateMetricCountUp(elPipe, cardPipe, animate ? PREV_METRICS.pipeline : 0, 0, v => `$${v.toLocaleString()}`);
        PREV_METRICS.pipeline = 0;
      }

      // 2. UPFRONT DEPOSITS COLLECTED
      const fees = Math.round(roi.fees_collected || 0);
      const elFees = document.getElementById('kpiFeesCol');
      const cardFees = document.getElementById('cardMetricFees');
      elFees.style.color = fees > 0 ? '#15803d' : '#0f172a';
      document.getElementById('kpiFeesSubtext').innerText = isBench
        ? '16 Verified Deposits (Simulated Benchmark)'
        : (fees > 0 ? `✓ $${fees} Verified via Stripe` : (pipelineBooked > 0 ? '⏳ Awaiting Customer Stripe Authorization' : '0 Stripe Deposits Paid'));
      animateMetricCountUp(elFees, cardFees, animate ? PREV_METRICS.fees : fees, fees, v => `$${v.toLocaleString()}`);
      PREV_METRICS.fees = fees;

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

      if (!dispatchHero.classList.contains('active') && data.bookings && data.bookings.length > 0) {
        const latestBooking = data.bookings[data.bookings.length - 1];
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

    function renderCalendar() {
      const grid = document.getElementById('fullCalendarGrid');
      if (!grid) return;

      const techFilter = document.getElementById('calTechFilter').value;
      const slots = BOARD_DATA.slots || [];
      const bookings = BOARD_DATA.bookings || [];
      const techs = BOARD_DATA.technicians || [];
      const filteredSlots = techFilter === 'ALL' ? slots : slots.filter(s => s.technician_id === techFilter);

      // Update Google Calendar Two-Way Sync Banner
      const gcalTitle = document.getElementById('gcalSyncStatusTitle');
      const gcalSub = document.getElementById('gcalSyncStatusSub');
      const gcalBlockedCount = slots.filter(s => s.is_blocked && (s.blocked_reason || '').includes('Google Calendar')).length;
      if (gcalTitle && gcalSub) {
        gcalTitle.innerText = `Connected: Master Dispatch + ${techs.length} Technician Google Calendars (${BOARD_DATA.gcal_last_sync || 'Two-Way Active'})`;
        gcalSub.innerText = `${bookings.length} Outbound Dispatch${bookings.length === 1 ? '' : 'es'} Pushed to Google Calendar • ${gcalBlockedCount} External Google Calendar Busy Block${gcalBlockedCount === 1 ? '' : 's'} Imported`;
      }

      const occEl = document.getElementById('calOccupancySummary');
      if (occEl) {
        const openCount = filteredSlots.filter(s => s.time_window_key !== 'emergency_asap' && !s.is_booked && !s.is_blocked).length;
        occEl.innerText = `${bookings.length} Active Dispatch${bookings.length === 1 ? '' : 'es'} • ${gcalBlockedCount} GCal Busy Block${gcalBlockedCount === 1 ? '' : 's'} • ${openCount} Open Tech Windows`;
      }

      // Render Active Dispatches Live Strip at Top of Calendar
      const stripEl = document.getElementById('activeDispatchStrip');
      if (stripEl) {
        if (bookings.length === 0) {
          stripEl.innerHTML = '';
        } else {
          stripEl.innerHTML = bookings.map(b => {
            const isEmerg = (b.urgency_level || '').includes('EMERG') || (b.service_type || '').toLowerCase() === 'emergency';
            const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
            const assignedShort = (b.assigned_technician || '').split('(')[0].trim();
            const techOptions = techs.map(t => {
              const sel = assignedShort.toLowerCase() === t.name.toLowerCase() ? 'selected' : '';
              return `<option value="${t.technician_id}" ${sel}>👷 ${t.name} (${t.license_type})</option>`;
            }).join('');
            const payPill = b.payment_status === 'PAID_VERIFIED'
              ? `<span style="background:#dcfce7; color:#15803d; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:800;">✓ $${b.dispatch_fee} Deposit Paid</span>`
              : `<span style="background:#fef3c7; color:#b45309; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:800;">💳 Pending $${b.dispatch_fee} Deposit</span>`;

            return `
              <div class="dispatch-queue-card ${isEmerg ? 'is-emerg-queue' : ''}">
                <div>
                  <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:4px;">
                    <span class="dq-badge">${isEmerg ? '🚨 CODE RED EMERGENCY DISPATCH' : '⚡ CONFIRMED SERVICE DISPATCH'}</span>
                    <span style="font-weight:800; font-size:0.88rem; color:#475569;">#${b.confirmation_id}</span>
                    ${payPill}
                    <span style="background:#dbeafe; color:#1e40af; padding:4px 10px; border-radius:6px; font-size:0.78rem; font-weight:800;">📅 Synced to Google Calendar ✓</span>
                  </div>
                  <div class="dq-title">${b.display_title || b.service_type} — ${b.customer_name} (${b.phone_number})</div>
                  <div class="dq-meta">
                    📍 <strong>${b.service_address}</strong> &bull; 🕒 <strong>${b.display_window || b.slot_time}</strong> &bull; 💰 Est. Job: <strong>$${Number(b.estimated_job_value || 850).toLocaleString()}</strong>
                  </div>
                </div>
                <div class="dq-actions">
                  <div style="display:flex; flex-direction:column; gap:3px;">
                    <span style="font-size:0.74rem; font-weight:800; color:#475569; text-transform:uppercase;">Assigned Electrician (Reassign):</span>
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

      const dates = [...new Set(slots.map(s => s.date))].slice(0, 5);
      grid.innerHTML = dates.map((dt, dayIdx) => {
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

        const emergCardsHtml = dayEmergencies.map(eb => {
          const safeObj = JSON.stringify(eb).replace(/'/g, "&#39;");
          const techShort = (eb.assigned_technician || 'Marcus Vance').split('(')[0].trim();
          return `
            <div class="slot-box is-booked-emergency" style="cursor:pointer;" onclick='selectCalendarBooking(${safeObj})'>
              <div class="slot-time-header">
                <span style="color:#dc2626;">🚨 CODE RED (45–60m)</span>
                <span style="background:#dc2626; color:#fff; padding:2px 7px; border-radius:4px; font-size:0.74rem;">DISPATCHED</span>
              </div>
              <div class="booked-cust-name">${eb.customer_name}</div>
              <div class="booked-cust-meta">
                <strong>${eb.display_title || 'Electrical Emergency'}</strong><br>
                📍 ${eb.service_address}<br>
                👷 Tech: <strong>${techShort}</strong><br>
                <span style="color:#1e40af; font-weight:800; font-size:0.78rem;">📅 Synced to Google Calendar ✓</span>
              </div>
            </div>
          `;
        }).join('');

        const windows = [
          { label: 'Morning', wKey: 'morning', key: '08:00 AM - 12:00 PM', shortTime: '8 AM - 12 PM' },
          { label: 'Afternoon', wKey: 'afternoon', key: '12:00 PM - 04:00 PM', shortTime: '12 PM - 4 PM' },
          { label: 'Evening', wKey: 'evening', key: '04:00 PM - 07:00 PM', shortTime: '4 PM - 7 PM' }
        ];

        const slotsHtml = windows.map(w => {
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
          const openWindowSlots = windowSlots.filter(s => !s.is_booked && !s.is_blocked);

          let cards = [];

          // Render routine booked cards in this window
          winBookings.forEach(b => {
            const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
            const techShort = (b.assigned_technician || '').split('(')[0].trim();
            cards.push(`
              <div class="slot-box is-booked-routine" style="cursor:pointer;" onclick='selectCalendarBooking(${safeObj})'>
                <div class="slot-time-header">
                  <span style="color:#15803d;">⚡ ${w.label} (${w.shortTime})</span>
                  <span style="background:#16a34a; color:#fff; padding:2px 7px; border-radius:4px; font-size:0.74rem;">BOOKED</span>
                </div>
                <div class="booked-cust-name">${b.customer_name}</div>
                <div class="booked-cust-meta">
                  <strong>${b.display_title || b.service_type}</strong><br>
                  📍 ${b.service_address}<br>
                  👷 Tech: <strong>${techShort}</strong><br>
                  <span style="color:#1e40af; font-weight:800; font-size:0.78rem;">📅 Synced to Google Calendar ✓</span>
                </div>
              </div>
            `);
          });

          // Render Google Calendar Busy blocks imported via Two-Way Sync
          gcalBusySlots.forEach(gs => {
            cards.push(`
              <div class="slot-box is-gcal-busy">
                <div class="slot-time-header">
                  <span style="color:#1e40af;">📅 ${w.label} (${w.shortTime})</span>
                  <span style="background:#2563eb; color:#fff; padding:2px 7px; border-radius:4px; font-size:0.72rem;">GCAL BUSY</span>
                </div>
                <div class="booked-cust-name" style="font-size:0.9rem; color:#1e3a8a;">${(gs.blocked_reason || 'Google Calendar Event').replace('📅 Google Calendar Busy: ', '')}</div>
                <div class="booked-cust-meta">
                  👷 Tech: <strong>${gs.technician_name}</strong> (Blocked via GCal)<br>
                  <button class="btn-slot-act btn-slot-block" style="margin-top:6px;" onclick="toggleBlockSlot('${gs.slot_id}')">Clear Busy Block</button>
                </div>
              </div>
            `);
          });

          // Render Open / Multi-Tech Availability box for remaining slots in this window
          if (openWindowSlots.length > 0) {
            const primarySlot = openWindowSlots[0];
            const techPills = windowSlots.map(ws => {
              const shortName = ws.technician_name.split(' ')[0] + ' ' + (ws.technician_name.split(' ')[1] || '').charAt(0) + '.';
              if (ws.is_blocked && (ws.blocked_reason || '').includes('Google Calendar')) {
                return `<span class="tech-mini-pill gcal-pill" title="${ws.blocked_reason}">📅 ${shortName} (GCal)</span>`;
              }
              if (ws.is_booked || ws.is_blocked) {
                return `<span class="tech-mini-pill busy-pill">🔴 ${shortName} ( Dispatched )</span>`;
              }
              return `<span class="tech-mini-pill">🟢 ${shortName}</span>`;
            }).join('');

            cards.push(`
              <div class="slot-box">
                <div class="slot-time-header">
                  <span>${w.label} (${w.shortTime})</span>
                  <span style="color:#16a34a;">${openWindowSlots.length} TECH${openWindowSlots.length === 1 ? '' : 'S'} OPEN</span>
                </div>
                <div class="tech-avail-pills">${techPills}</div>
                <div class="slot-actions">
                  <button class="btn-slot-act btn-slot-book" onclick="openManualBookModal('${primarySlot.slot_id}')">+ Book Tech</button>
                  <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${primarySlot.slot_id}')">Block</button>
                </div>
              </div>
            `);
          } else if (cards.length === 0 && manualBlockedSlots.length > 0) {
            const bs = manualBlockedSlots[0];
            cards.push(`
              <div class="slot-box">
                <div class="slot-time-header"><span>${w.label}</span><span style="color:#64748b;">BLOCKED</span></div>
                <div class="slot-tech-avail">${bs.blocked_reason || 'Unavailable / Off-Duty'}</div>
                <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${bs.slot_id}')">Unblock</button>
              </div>
            `);
          }

          return cards.join('');
        }).join('');

        return `
          <div class="cal-col ${dayEmergencies.length > 0 ? 'has-emergency-col' : ''}">
            <div class="cal-col-header">
              <div class="cal-col-day">${dayLabel}</div>
              <div class="cal-col-sub">${dateStr} ${dayEmergencies.length > 0 ? '• 🚨 CODE RED' : ''}</div>
            </div>
            <div class="cal-col-body">
              ${emergCardsHtml}
              ${slotsHtml}
            </div>
          </div>
        `;
      }).join('');
    }

    function selectCalendarBooking(booking) {
      showBookingInHero(booking);
      switchPortalTab('console');
    }

    function renderFleetView() {
      const grid = document.getElementById('fleetCardsGrid');
      if (!grid) return;

      const techs = BOARD_DATA.technicians || [];
      const slots = BOARD_DATA.slots || [];
      const bookings = BOARD_DATA.bookings || [];

      document.getElementById('kpiFleetTotal').innerText = techs.length;
      const onCallTech = techs.find(t => t.is_on_call);
      document.getElementById('kpiFleetOnCall').innerText = onCallTech ? onCallTech.name : 'None';
      document.getElementById('kpiFleetOpenSlots').innerText = slots.filter(s => s.time_window_key !== 'emergency_asap' && !s.is_booked && !s.is_blocked).length;
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
          return `
            <div class="tech-active-job-box ${isEm ? '' : 'routine-job'}">
              <div style="display:flex; justify-content:space-between; align-items:center; font-weight:800; margin-bottom:3px;">
                <span>${isEm ? '🚨 CODE RED DISPATCH' : '⚡ SCHEDULED DISPATCH'} (#${tb.confirmation_id})</span>
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
                <div class="tech-phone">${t.phone}</div>
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
      document.getElementById('techModal').classList.add('active');
    }
    function openEditTechModal(tech) {
      document.getElementById('techModalTitle').innerText = `Edit ${tech.name}`;
      document.getElementById('techIdInput').value = tech.technician_id;
      document.getElementById('techNameInput').value = tech.name;
      document.getElementById('techLicenseInput').value = tech.license_type;
      document.getElementById('techPhoneInput').value = tech.phone;
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

    function openManualBookModal(preselectedSlotId = '') {
      const select = document.getElementById('manualSlotSelect');
      const slots = (BOARD_DATA.slots || []).filter(s => !s.is_booked && !s.is_blocked);
      select.innerHTML = slots.map(s => `<option value="${s.slot_id}">${s.date} - ${s.time_window} (${s.technician_name})</option>`).join('');
      if (preselectedSlotId) select.value = preselectedSlotId;
      document.getElementById('manualBookModal').classList.add('active');
    }
    function closeManualBookModal() { document.getElementById('manualBookModal').classList.remove('active'); }

    async function submitManualBooking() {
      const payload = {
        slot_id: document.getElementById('manualSlotSelect').value,
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
      const annualGain = Math.round(recoveredJobsMonthly * ticket * 12);
      document.getElementById('roiAnnualGain').innerText = `+$${annualGain.toLocaleString()} / yr`;
      document.getElementById('roiBreakdown').innerText = `Based on recovering ${recoveredJobsMonthly.toFixed(1)} missed after-hours jobs/month`;
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
    const initTab = new URLSearchParams(window.location.search).get('tab');
    if (initTab === 'calendar' || initTab === 'fleet' || initTab === 'console') {
      switchPortalTab(initTab);
    }
    window.addEventListener('DOMContentLoaded', () => fetchBoardData());
  </script>
</body>
</html>
"""


class DemoRequestHandler(BaseHTTPRequestHandler):
    """Handles web requests for the ZeroMiss Client Demonstration Dashboard."""

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_twiml(self, twiml_xml: str):
        data = twiml_xml.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _get_board_payload(self) -> Dict[str, Any]:
        roi = DB.calculate_contractor_roi_metrics()
        return {
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
        }

    def do_GET(self):
        global DEMO_DISPLAY_EMAIL
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            board_json = json.dumps(self._get_board_payload())
            page_html = HTML_DASHBOARD.replace(
                "let BOARD_DATA = { bookings: [], technicians: [], slots: [], roi_metrics: {} };",
                f"let BOARD_DATA = {board_json};",
                1,
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page_html.encode("utf-8"))

        elif parsed.path == "/api/board":
            self._send_json(self._get_board_payload())

        elif parsed.path == "/api/calendar.ics":
            from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
            ics_content = CALENDAR_SYNC.generate_master_feed_ics(list(DB.bookings.values()))
            data = ics_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="zeromiss_dispatch.ics"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
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
                '  <Gather input="speech" action="/api/twilio/gather" timeout="3" speechTimeout="auto">\n'
                '    <Say voice="Polly.Joanna-Neural">'
                'Thank you for calling ZeroMiss Electrical 24/7 Dispatch. My name is Sarah. '
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
            sarah_reply = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, speech_result)
            clean_reply = sarah_reply.replace("&", "and").replace("<", "").replace(">", "")

            if "transfer you directly to Sean Glenn" in sarah_reply:
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    f'  <Say voice="Polly.Joanna-Neural">{clean_reply}</Say>\n'
                    '  <Dial timeout="20">609-972-4328</Dial>\n'
                    '</Response>'
                )
            else:
                twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<Response>\n'
                    '  <Gather input="speech" action="/api/twilio/gather" timeout="4" speechTimeout="auto">\n'
                    f'    <Say voice="Polly.Joanna-Neural">{clean_reply}</Say>\n'
                    '  </Gather>\n'
                    '  <Say voice="Polly.Joanna-Neural">Thank you for calling ZeroMiss. Goodbye.</Say>\n'
                    '  <Hangup/>\n'
                    '</Response>'
                )
            self._send_twiml(twiml)
            return

        elif parsed.path == "/api/bookings/pay":
            cid = req_data.get("confirmation_id", "").strip()
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
            elif DB.bookings:
                booking_dict = enrich_booking_dict(list(DB.bookings.values())[-1])
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
                dialogue.append({"speaker": "Sarah (ZeroMiss AI)", "text": t1_sarah, "isSarah": True})

                t2_user = "My name is David Miller, 742 Evergreen Terrace, callback number is (555) 482-9104"
                dialogue.append({"speaker": "David Miller (Caller)", "text": t2_user, "isSarah": False})
                t2_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t2_user)
                dialogue.append({"speaker": "Sarah (ZeroMiss AI)", "text": t2_sarah, "isSarah": True})
            else:
                t1_user = "Hi Sarah, I just bought an EV and need a 50-amp Level 2 charger installed in my garage."
                dialogue.append({"speaker": "Alex Rivera (Caller)", "text": t1_user, "isSarah": False})
                t1_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t1_user)
                dialogue.append({"speaker": "Sarah (ZeroMiss AI)", "text": t1_sarah, "isSarah": True})

                t2_user = "Tomorrow morning works. My name is Alex Rivera, 45 Innovation Way in Cambridge, (555) 829-1044, alex@example.com"
                dialogue.append({"speaker": "Alex Rivera (Caller)", "text": t2_user, "isSarah": False})
                t2_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t2_user)
                dialogue.append({"speaker": "Sarah (ZeroMiss AI)", "text": t2_sarah, "isSarah": True})

            LAST_DIALOGUE = dialogue
            booking_dict = enrich_booking_dict(list(DB.bookings.values())[-1], scenario_hint=scenario) if DB.bookings else None
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

        else:
            self.send_response(404)
            self.end_headers()


def run_demo_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), DemoRequestHandler)
    print("\n" + "=" * 80)
    print("  ZeroMiss Voice Dispatch - Story-Driven Interactive Demo Server")
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
