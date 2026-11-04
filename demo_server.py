"""ZeroMiss Voice Dispatch - Story-Driven Interactive Demo & Fleet Command Server.

Designed around the core end-to-end product story:
Missed Call -> AI Triage & 3s SMS Recovery -> Instant Dispatch -> Upfront Stripe Deposit.
"""

import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB


# Global state for demo session
ACTIVE_AGENT = VoiceDispatchAgent()
ACTIVE_SESSION = ACTIVE_AGENT.create_session()


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
      --border: #e2e8f0;
      --border-strong: #cbd5e1;
      --navy: #0f172a;
      --text-main: #0f172a;
      --text-body: #334155;
      --text-muted: #64748b;
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
      font-size: 16px;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }

    /* TOP HEADER BAR - CLEAN & UNCLUTTERED */
    header {
      background: var(--navy);
      color: #ffffff;
      padding: 14px 32px;
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
      width: 42px;
      height: 42px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      font-weight: 800;
    }
    .brand-title-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand h1 {
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #ffffff;
    }
    .demo-mode-pill {
      background: #f59e0b;
      color: #0f172a;
      font-size: 0.75rem;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 999px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .brand p {
      font-size: 0.88rem;
      color: #94a3b8;
    }

    /* NAVIGATION & UTILITY TOOLS */
    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .nav-tabs {
      display: flex;
      background: #1e293b;
      padding: 4px;
      border-radius: 10px;
      gap: 4px;
    }
    .nav-tab {
      background: transparent;
      color: #cbd5e1;
      border: none;
      padding: 8px 16px;
      border-radius: 7px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s;
    }
    .nav-tab:hover { color: #ffffff; background: rgba(255,255,255,0.06); }
    .nav-tab.active {
      background: #2563eb;
      color: #ffffff;
      font-weight: 700;
    }
    .nav-count {
      background: rgba(255,255,255,0.2);
      padding: 1px 7px;
      border-radius: 999px;
      font-size: 0.78rem;
    }

    .utility-btn {
      background: #1e293b;
      color: #e2e8f0;
      border: 1px solid #334155;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .utility-btn:hover { background: #334155; color: #ffffff; }

    /* MAIN CONTAINER */
    main {
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
      padding: 24px 32px 40px;
      flex: 1;
    }
    .tab-view { display: none; }
    .tab-view.active { display: block; }

    /* VISUAL BACKBONE: 4-STEP END-TO-END STORY JOURNEY */
    .story-backbone {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 24px;
      margin-bottom: 20px;
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
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .next-step-banner {
      background: #eff6ff;
      border: 1.5px solid #93c5fd;
      color: #1e3a8a;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.92rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .journey-steps {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }
    @media (max-width: 980px) {
      .journey-steps { grid-template-columns: repeat(2, 1fr); }
    }
    .j-step {
      background: var(--surface-muted);
      border: 2px solid var(--border);
      border-radius: 10px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      transition: all 0.2s;
      opacity: 0.65;
    }
    .j-step.active-step {
      background: #eff6ff;
      border-color: #2563eb;
      opacity: 1;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }
    .j-step.done-step {
      background: #f0fdf4;
      border-color: #22c55e;
      opacity: 1;
    }
    .j-num {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #cbd5e1;
      color: #0f172a;
      font-weight: 800;
      font-size: 0.9rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .j-step.active-step .j-num { background: #2563eb; color: #ffffff; }
    .j-step.done-step .j-num { background: #16a34a; color: #ffffff; }
    .j-title { font-size: 0.92rem; font-weight: 700; color: var(--text-main); }
    .j-desc { font-size: 0.8rem; color: var(--text-muted); }

    /* PRIMARY WORKSPACE: CLEAR HIERARCHY (START ON LEFT -> RESULTS ON RIGHT) */
    .demo-stage-grid {
      display: grid;
      grid-template-columns: 460px 1fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
    }
    @media (max-width: 1180px) {
      .demo-stage-grid { grid-template-columns: 1fr; }
    }

    /* PRIMARY ACTION PANEL (LEFT) */
    .primary-simulator-card {
      background: var(--surface);
      border: 2px solid #2563eb;
      border-radius: 16px;
      padding: 22px;
      box-shadow: var(--shadow-md);
      display: flex;
      flex-direction: column;
      position: relative;
    }
    .step-one-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #2563eb;
      color: #ffffff;
      font-size: 0.75rem;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .sim-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }
    .sim-header h2 {
      font-size: 1.2rem;
      font-weight: 800;
      color: var(--text-main);
      margin-top: 6px;
    }

    /* HERO PRIMARY CTA BUTTON */
    .btn-hero-start {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff;
      border: none;
      border-radius: 12px;
      padding: 16px 20px;
      text-align: left;
      cursor: pointer;
      box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
      transition: all 0.2s;
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .btn-hero-start:hover {
      background: linear-gradient(135deg, #1d4ed8, #1e40af);
      transform: translateY(-1px);
      box-shadow: 0 8px 20px rgba(37, 99, 235, 0.36);
    }
    .hero-btn-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 1.05rem;
      font-weight: 800;
    }
    .hero-btn-sub {
      font-size: 0.85rem;
      color: #dbeafe;
      font-weight: 500;
    }

    /* SECONDARY SCENARIO PILLS */
    .secondary-scenarios {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }
    .btn-sec-scenario {
      flex: 1;
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      color: var(--text-body);
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 0.84rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
      text-align: center;
    }
    .btn-sec-scenario:hover {
      background: #e2e8f0;
      color: var(--text-main);
    }
    .btn-sec-emerg {
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }
    .btn-sec-emerg:hover { background: #fee2e2; }

    /* LIVE CALL TRANSCRIPT STREAM */
    .transcript-label {
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }
    .chat-container {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      border-radius: 12px;
      height: 270px;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 12px;
    }
    .bubble {
      max-width: 90%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 0.92rem;
      line-height: 1.5;
    }
    .bubble-user {
      align-self: flex-end;
      background: #ffffff;
      color: var(--text-main);
      border: 1px solid var(--border-strong);
    }
    .bubble-sarah {
      align-self: flex-start;
      background: #eff6ff;
      color: #1e3a8a;
      border: 1px solid #bfdbfe;
    }
    .speaker-name {
      font-size: 0.75rem;
      font-weight: 800;
      margin-bottom: 4px;
      text-transform: uppercase;
      color: #2563eb;
    }

    .input-row {
      display: flex;
      gap: 8px;
      margin-top: auto;
    }
    .btn-mic {
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      border-radius: 8px;
      padding: 0 14px;
      font-size: 1.15rem;
      cursor: pointer;
    }
    .btn-mic.listening { background: #dc2626; color: white; }
    .input-row input {
      flex: 1;
      border: 1px solid var(--border-strong);
      padding: 11px 14px;
      border-radius: 8px;
      font-size: 0.92rem;
      outline: none;
    }
    .input-row input:focus { border-color: var(--primary); }
    .input-row button.btn-send {
      background: var(--navy);
      color: white;
      border: none;
      padding: 0 18px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
    }

    /* RIGHT STAGE: LIVE OUTCOMES (PHONE + DISPATCH TICKET) */
    .outcomes-stage {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 22px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
    }
    .outcomes-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 10px;
    }
    .outcomes-header h2 {
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--text-main);
    }
    .outcomes-split {
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 24px;
      align-items: start;
      flex: 1;
    }
    @media (max-width: 920px) {
      .outcomes-split { grid-template-columns: 1fr; }
    }

    /* REALISTIC SMARTPHONE SIMULATOR */
    .phone-column-wrap {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .phone-step-callout {
      background: #fef3c7;
      border: 1.5px solid #f59e0b;
      color: #92400e;
      font-size: 0.85rem;
      font-weight: 800;
      padding: 6px 14px;
      border-radius: 999px;
      margin-bottom: 10px;
      display: none;
      align-items: center;
      gap: 6px;
    }
    .phone-step-callout.visible { display: inline-flex; }

    .phone-chassis {
      background: linear-gradient(145deg, #cbd5e1, #94a3b8, #cbd5e1);
      padding: 10px;
      border-radius: 42px;
      box-shadow: var(--shadow-lg);
      width: 330px;
      transition: all 0.25s;
    }
    .phone-chassis.highlight-phone {
      box-shadow: 0 0 0 4px #2563eb, 0 16px 32px rgba(37, 99, 235, 0.25);
    }
    .phone-screen {
      background: #0f172a;
      border-radius: 34px;
      padding: 10px 12px 14px;
      height: 500px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .phone-dynamic-island {
      width: 84px;
      height: 18px;
      background: #000000;
      border-radius: 12px;
      margin: 0 auto 6px;
    }
    .phone-status-bar {
      display: flex;
      justify-content: space-between;
      padding: 0 8px 8px;
      font-size: 0.78rem;
      color: #f8fafc;
      font-weight: 700;
    }
    .phone-imessage-header {
      background: #1e293b;
      border-radius: 10px;
      padding: 8px 12px;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .imessage-avatar {
      width: 32px;
      height: 32px;
      background: #2563eb;
      border-radius: 50%;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.8rem;
    }
    .imessage-name { font-size: 0.88rem; font-weight: 700; color: #ffffff; }
    .imessage-sub { font-size: 0.72rem; color: #94a3b8; }

    .phone-messages {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 4px 2px;
    }
    .sms-bubble {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 12px 14px;
      font-size: 0.86rem;
      line-height: 1.45;
      color: #f1f5f9;
    }
    .sms-tag {
      font-size: 0.72rem;
      font-weight: 800;
      color: #38bdf8;
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .sms-recoup-card {
      border: 2px solid #f59e0b;
      background: #1c1917;
    }
    .sms-action-card {
      background: #0f172a;
      border: 1.5px solid #38bdf8;
      border-radius: 10px;
      padding: 12px;
      margin-top: 10px;
      text-align: center;
      cursor: pointer;
    }
    .btn-action-claim {
      background: #2563eb;
      color: white;
      border: none;
      padding: 11px 14px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 0.88rem;
      cursor: pointer;
      width: 100%;
      margin-top: 8px;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
    .btn-action-claim:hover { background: #1d4ed8; }

    .recoup-won-badge {
      background: rgba(34, 197, 94, 0.2);
      border: 1.5px solid #22c55e;
      color: #4ade80;
      padding: 10px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 0.88rem;
      text-align: center;
    }
    .sms-stripe-sheet {
      border: 1.5px solid #6366f1;
      background: #1e1b4b;
      border-radius: 10px;
      padding: 12px;
      margin-top: 10px;
    }
    .btn-stripe-pay {
      background: #4f46e5;
      color: white;
      border: none;
      padding: 11px 14px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 0.88rem;
      cursor: pointer;
      width: 100%;
      margin-top: 8px;
    }
    .btn-stripe-pay.paid { background: #16a34a; cursor: default; }
    .phone-home-bar {
      width: 100px;
      height: 4px;
      background: #64748b;
      border-radius: 2px;
      margin: 10px auto 0;
    }

    /* CONTRACTOR DISPATCH TICKET (QUIET UNTIL BOOKED) */
    .cockpit-column {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .waiting-quiet-box {
      background: var(--surface-muted);
      border: 2px dashed var(--border-strong);
      border-radius: 14px;
      padding: 36px 24px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 480px;
      color: var(--text-muted);
    }
    .waiting-icon {
      font-size: 2.4rem;
      margin-bottom: 12px;
      opacity: 0.7;
    }
    .waiting-quiet-box h3 {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-body);
      margin-bottom: 8px;
    }
    .waiting-quiet-box p {
      font-size: 0.95rem;
      max-width: 380px;
      margin-bottom: 20px;
    }
    .quiet-checklist {
      text-align: left;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 18px;
      font-size: 0.88rem;
      color: var(--text-body);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .dispatch-hero {
      background: #ffffff;
      border: 2px solid #16a34a;
      border-radius: 14px;
      padding: 20px;
      display: none;
      box-shadow: var(--shadow-md);
    }
    .dispatch-hero.active { display: block; }
    .dispatch-hero.is-emergency { border-color: #dc2626; background: #fffafa; }
    .hero-badge {
      display: inline-block;
      font-size: 0.8rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 4px 12px;
      border-radius: 6px;
    }
    .badge-emergency { background: #fee2e2; color: #b91c1c; }
    .badge-standard { background: #dcfce7; color: #15803d; }
    .hero-title { font-size: 1.25rem; font-weight: 800; margin: 10px 0 4px; color: var(--text-main); }
    .hero-subtitle { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 16px; }

    .ticket-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      margin-top: 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }
    .ticket-table tr { border-bottom: 1px solid var(--border); }
    .ticket-table td { padding: 10px 14px; }
    .ticket-table td:first-child {
      background: var(--surface-muted);
      color: var(--text-muted);
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
      font-size: 0.9rem;
    }

    /* SUPPORTING DEMO METRICS BAR (CLEARLY LABELED AS DEMO DATA) */
    .demo-metrics-section {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 24px;
      box-shadow: var(--shadow-sm);
    }
    .metrics-bar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .metrics-context-title {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .demo-data-tag {
      background: #e0e7ff;
      color: #3730a3;
      border: 1px solid #c7d2fe;
      font-size: 0.78rem;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .metrics-context-sub {
      font-size: 0.9rem;
      color: var(--text-muted);
      font-weight: 500;
    }
    .btn-benchmark-toggle {
      background: var(--surface-muted);
      color: var(--primary);
      border: 1px solid #bfdbfe;
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 0.86rem;
      font-weight: 700;
      cursor: pointer;
    }
    .btn-benchmark-toggle:hover { background: #eff6ff; }

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
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .rev-label {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 4px;
    }
    .rev-subtext {
      font-size: 0.88rem;
      color: var(--text-body);
      font-weight: 600;
    }
    .rev-val {
      font-size: 1.85rem;
      font-weight: 800;
      color: var(--text-main);
      font-variant-numeric: tabular-nums;
    }

    /* VIEW 2: CALENDAR & VIEW 3: FLEET */
    .cal-controls-bar {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 22px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .cal-controls-left { display: flex; align-items: center; gap: 12px; }
    .cal-controls-left select {
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 0.92rem;
      font-weight: 600;
    }
    .btn-cal-action {
      background: var(--surface-muted);
      border: 1px solid var(--border-strong);
      color: var(--text-body);
      padding: 9px 14px;
      border-radius: 8px;
      font-size: 0.88rem;
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
    }
    .cal-col-header {
      background: var(--surface-muted);
      border-bottom: 1px solid var(--border);
      padding: 12px;
      text-align: center;
    }
    .cal-col-day { font-size: 1rem; font-weight: 800; }
    .cal-col-sub { font-size: 0.82rem; color: var(--text-muted); }
    .cal-col-body { padding: 12px; display: flex; flex-direction: column; gap: 10px; }
    .slot-box {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      background: var(--surface-muted);
    }
    .slot-time-header { display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 6px; font-weight: 700; }
    .slot-tech-avail { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 8px; }
    .slot-actions { display: flex; gap: 6px; }
    .btn-slot-act { padding: 5px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; cursor: pointer; border: none; }
    .btn-slot-book { background: var(--primary); color: white; }
    .btn-slot-block { background: #e2e8f0; color: var(--text-body); }
    .slot-box.is-booked-routine { background: #f0fdf4; border-color: #86efac; }
    .slot-box.is-booked-emergency { background: #fef2f2; border-color: #fca5a5; }
    .booked-cust-name { font-size: 0.95rem; font-weight: 800; margin-bottom: 4px; }
    .booked-cust-meta, .booked-emerg-meta { font-size: 0.82rem; line-height: 1.4; }

    /* FLEET ROSTER */
    .fleet-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 22px; }
    .kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
    .kpi-label { font-size: 0.82rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; }
    .kpi-val { font-size: 1.6rem; font-weight: 800; margin-top: 4px; }
    .kpi-sub { font-size: 0.84rem; color: var(--primary); margin-top: 2px; font-weight: 600; }
    .fleet-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
    .btn-add-electrician { background: var(--primary); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-size: 0.9rem; font-weight: 700; cursor: pointer; }
    .fleet-cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; }
    .tech-card-pro { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 12px; }
    .tech-card-top { display: flex; align-items: center; gap: 12px; }
    .tech-avatar { width: 48px; height: 48px; border-radius: 10px; background: var(--surface-muted); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
    .tech-name { font-size: 1.05rem; font-weight: 800; }
    .tech-license, .tech-phone { font-size: 0.84rem; color: var(--text-muted); }
    .tech-badge-oncall { background: #dcfce7; color: #15803d; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 800; }
    .tech-badge-offduty { background: #f1f5f9; color: #64748b; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; }
    .tech-specialties-row { display: flex; flex-wrap: wrap; gap: 6px; }
    .spec-pill { font-size: 0.78rem; background: var(--surface-muted); padding: 3px 9px; border-radius: 6px; border: 1px solid var(--border); font-weight: 600; }
    .tech-actions-row { display: flex; gap: 8px; padding-top: 10px; border-top: 1px solid var(--border); }
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
    .modal-header h3 { font-size: 1.15rem; font-weight: 800; }
    .modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-muted); }
    .form-group { margin-bottom: 14px; display: flex; flex-direction: column; gap: 6px; }
    .form-group label { font-size: 0.88rem; font-weight: 700; }
    .form-group input, .form-group select, .form-group textarea { padding: 10px 12px; border: 1px solid var(--border-strong); border-radius: 8px; font-size: 0.92rem; }
    .btn-modal-submit { background: var(--primary); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 700; font-size: 0.95rem; width: 100%; cursor: pointer; margin-top: 10px; }
    .slider-row { display: flex; justify-content: space-between; margin: 14px 0 6px; font-weight: 700; }
    .roi-result-banner { background: #f0fdf4; border: 1px solid #86efac; border-radius: 12px; padding: 18px; margin: 18px 0; text-align: center; }
    .roi-big-gain { font-size: 2rem; font-weight: 800; color: #15803d; }

    footer {
      background: var(--navy);
      color: #94a3b8;
      text-align: center;
      padding: 16px;
      font-size: 0.85rem;
      margin-top: auto;
    }
  </style>
</head>
<body>

  <!-- CLEAN TOP HEADER -->
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

      <!-- THE VISUAL BACKBONE: 4-STEP END-TO-END STORY -->
      <div class="story-backbone">
        <div class="backbone-top">
          <div class="backbone-label">
            <span>⚡ END-TO-END PRODUCT JOURNEY</span>
          </div>
          <div class="next-step-banner" id="guidedNextStepBanner">
            👉 <strong>What to do first:</strong> Click <strong>"▶ Start Demo: Simulate Dropped Call"</strong> below to see ZeroMiss save a $1,200 job.
          </div>
        </div>

        <div class="journey-steps">
          <div class="j-step active-step" id="jStep1">
            <div class="j-num">1</div>
            <div>
              <div class="j-title">Missed or Inbound Call</div>
              <div class="j-desc">Caller hangs up or reports hazard</div>
            </div>
          </div>
          <div class="j-step" id="jStep2">
            <div class="j-num">2</div>
            <div>
              <div class="j-title">AI Triage &amp; 3s Text-Back</div>
              <div class="j-desc">Sarah intercepts lead via SMS</div>
            </div>
          </div>
          <div class="j-step" id="jStep3">
            <div class="j-num">3</div>
            <div>
              <div class="j-title">Instant Dispatch</div>
              <div class="j-desc">Slot locked &amp; tech assigned</div>
            </div>
          </div>
          <div class="j-step" id="jStep4">
            <div class="j-num">4</div>
            <div>
              <div class="j-title">Upfront Stripe Deposit</div>
              <div class="j-desc">$89 fee eliminates no-shows</div>
            </div>
          </div>
        </div>
      </div>

      <!-- PRIMARY STAGE: LEFT = CLEAR STARTING POINT, RIGHT = LIVE RESULTS -->
      <div class="demo-stage-grid">

        <!-- LEFT: CLEAR STARTING POINT (SIMULATOR) -->
        <div class="primary-simulator-card">
          <div class="sim-header">
            <div>
              <span class="step-one-pill">● Step 1 — Start Here</span>
              <h2>Live Caller Simulator</h2>
            </div>
            <button class="utility-btn" style="background:#f1f5f9; color:#334155; border-color:#cbd5e1;" onclick="resetCall()">↺ Reset Demo</button>
          </div>

          <!-- UNMISTAKABLE PRIMARY ACTION -->
          <button class="btn-hero-start" onclick="simulateMissedCallLead()">
            <div class="hero-btn-top">
              <span>▶ Start Demo: Simulate Dropped Call</span>
              <span style="background:rgba(255,255,255,0.2); padding:2px 8px; border-radius:6px; font-size:0.82rem;">+$1,200 Story</span>
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

          <div class="transcript-label">
            <span>Live Call &amp; AI Event Transcript</span>
            <span id="audioStatusText" style="color:#16a34a;">● Sarah AI Ready</span>
          </div>

          <div class="chat-container" id="chatStream">
            <div class="bubble bubble-sarah">
              <div class="speaker-name">Sarah (ZeroMiss AI Dispatcher)</div>
              Thank you for calling ZeroMiss Electrical 24/7 Dispatch. Click <strong>"▶ Start Demo"</strong> above, or type/speak any electrical issue below to test me live!
            </div>
          </div>

          <div class="input-row">
            <button class="btn-mic" id="micBtn" onclick="toggleMic()" title="Speak via Microphone">🎙️</button>
            <input type="text" id="userInput" placeholder="Or type what a caller would say..." onkeydown="if(event.key==='Enter') sendUserMessage()">
            <button class="btn-send" onclick="sendUserMessage()">Send</button>
          </div>
        </div>

        <!-- RIGHT: SUPPORTING RESULTS (PHONE + COCKPIT) -->
        <div class="outcomes-stage">
          <div class="outcomes-header">
            <h2>Live Results (Updates Automatically During Call)</h2>
            <div style="display:flex; align-items:center; gap:8px; font-size:0.85rem; color:var(--text-muted);">
              <span>Contractor Alert Email:</span>
              <input type="email" id="contractorEmail" value="sean.glenn21@gmail.com" style="border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px; font-size:0.84rem; width:190px;">
              <button class="btn-slot-act btn-slot-book" onclick="saveContractorEmail()">Save</button>
            </div>
          </div>

          <div class="outcomes-split">
            <!-- Customer Smartphone Outcome -->
            <div class="phone-column-wrap">
              <div class="phone-step-callout" id="phoneStepCallout">
                👇 Click the blue button inside the phone!
              </div>
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
                      When Sarah sends a 3-second missed-call recovery link or Stripe deposit request, it appears right here for the homeowner to tap.
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
                <p>Once a caller books a slot or claims a missed-call recovery link, the complete work order appears here.</p>
                <div class="quiet-checklist">
                  <div>✓ <strong>NFPA 70E Hazard Triage</strong> (Code Red vs. Routine)</div>
                  <div>✓ <strong>Auto-Assigned Electrician</strong> from active roster</div>
                  <div>✓ <strong>1-Click Google Calendar</strong> &amp; iCal dispatch sync</div>
                  <div>✓ <strong>Upfront Stripe Deposit</strong> verification status</div>
                </div>
              </div>

              <!-- Active Ticket Card -->
              <div class="dispatch-hero" id="dispatchHero">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
                  <span class="hero-badge badge-standard" id="heroBadge">Confirmed Dispatch</span>
                  <span id="heroPayBadge" style="font-size:0.82rem; font-weight:800; color:#b45309; background:#fef3c7; padding:4px 10px; border-radius:6px; border:1px solid #fde68a;">
                    💳 Pending $89 Deposit
                  </span>
                </div>
                <div class="hero-title" id="heroTitle">New Service Call Scheduled</div>
                <div class="hero-subtitle">Dispatched to <strong id="heroContractor">sean.glenn21@gmail.com</strong></div>

                <div style="display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap;">
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
                  <tr><td>Phone:</td><td id="tktPhone">-</td></tr>
                  <tr><td>Address:</td><td id="tktAddress">-</td></tr>
                  <tr><td>Assigned Tech:</td><td id="tktTech">-</td></tr>
                  <tr><td>Window:</td><td id="tktWindow">-</td></tr>
                  <tr><td>Deposit Fee:</td><td id="tktFee">-</td></tr>
                  <tr><td>Est. Job Value:</td><td id="tktVal" style="color:#15803d; font-weight:800;">-</td></tr>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SUPPORTING DEMO METRICS BAR (WITH CLEAR DEMO CONTEXT) -->
      <div class="demo-metrics-section">
        <div class="metrics-bar-header">
          <div class="metrics-context-title">
            <span class="demo-data-tag" id="benchmarkIndicator">🧪 Simulated Demo Session Data</span>
            <span class="metrics-context-sub">Starts at $0 — tallies live as you test calls above</span>
          </div>
          <button class="btn-benchmark-toggle" id="btnBenchmarkToggle" onclick="toggleBenchmarkMode()">
            📈 Preview 30-Day Contractor Benchmark ($18,450)
          </button>
        </div>

        <div class="rev-metrics-grid">
          <div class="rev-metric-card">
            <div>
              <div class="rev-label">Demo Pipeline Revenue Won</div>
              <div class="rev-subtext" id="kpiPipelineSub">0 Dispatches Booked in Session</div>
            </div>
            <div class="rev-val" id="kpiPipelineRev">$0</div>
          </div>

          <div class="rev-metric-card">
            <div>
              <div class="rev-label">Missed Calls Recouped</div>
              <div class="rev-subtext" id="kpiMissedSub">0 Dropped Calls Tested</div>
            </div>
            <div class="rev-val" id="kpiMissedRec">0 Saved</div>
          </div>

          <div class="rev-metric-card">
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
      <div class="cal-controls-bar">
        <div class="cal-controls-left">
          <label style="font-weight:800;">Filter Electrician:</label>
          <select id="calTechFilter" onchange="renderCalendar()">
            <option value="ALL">⚡ All Electricians (4 Simulated Techs)</option>
          </select>
        </div>

        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn-cal-action" onclick="copyIcalFeedUrl()">📋 Copy iCal Feed URL</button>
          <a href="/api/calendar.ics" class="btn-cal-action" download="zeromiss_schedule.ics">⬇️ Download .ICS</a>
          <button class="btn-cal-action btn-cal-primary" onclick="openManualBookModal()">+ Manual Booking</button>
        </div>
      </div>

      <div class="full-calendar-grid" id="fullCalendarGrid"></div>
    </div>

    <!-- TAB 3: ELECTRICIAN FLEET ROSTER -->
    <div class="tab-view" id="viewFleet">
      <div class="fleet-kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Simulated Fleet Roster</div>
          <div class="kpi-val" id="kpiFleetTotal">4</div>
          <div class="kpi-sub">Demo Electricians</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">24/7 On-Call Lead</div>
          <div class="kpi-val" id="kpiFleetOnCall" style="font-size:1.3rem; color:#15803d;">Marcus Vance</div>
          <div class="kpi-sub">45m Emergency Dispatch</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Open Weekly Slots</div>
          <div class="kpi-val" id="kpiFleetOpenSlots">42</div>
          <div class="kpi-sub">Available Windows</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Session Jobs Booked</div>
          <div class="kpi-val" id="kpiFleetBookedJobs">0</div>
          <div class="kpi-sub">Synced to Calendar</div>
        </div>
      </div>

      <div class="fleet-header-row">
        <div>
          <h2 style="font-size:1.3rem; font-weight:800;">Electrician Roster &amp; On-Call Status (Demo Data)</h2>
          <p style="color:var(--text-muted); font-size:0.9rem;">Toggle on-call status or add technicians to see how Sarah assigns jobs.</p>
        </div>
        <button class="btn-add-electrician" onclick="openAddTechModal()">+ Add Electrician</button>
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
      <div style="font-size:0.95rem; color:var(--text-body); line-height:1.6;">
        <p style="margin-bottom:14px;">
          <strong>The Problem:</strong> 35% of homeowner calls happen after hours or while electricians are on a ladder. 80% of callers who hit voicemail hang up and call the next contractor on Google.
        </p>
        <p style="margin-bottom:14px;">
          <strong>The ZeroMiss Journey:</strong>
        </p>
        <ol style="margin-left:20px; margin-bottom:18px; display:flex; flex-direction:column; gap:8px;">
          <li><strong>Missed Call Intercepted:</strong> Sarah detects the dropped call and texts the customer within 3 seconds.</li>
          <li><strong>Instant Booking:</strong> Customer taps the link on their phone to lock in tomorrow's 8:00 AM slot (+$1,200 job saved).</li>
          <li><strong>No-Show Elimination:</strong> Customer authorizes the $89 diagnostic deposit via Stripe right inside the SMS thread.</li>
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
          <div style="font-size:0.85rem; font-weight:800; color:#15803d; text-transform:uppercase;">Projected Recouped Annual Revenue</div>
          <div class="roi-big-gain" id="roiAnnualGain">+$109,368 / yr</div>
          <div style="font-size:0.85rem; color:var(--text-muted);" id="roiBreakdown">Based on recovering 7.6 missed after-hours jobs/month</div>
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
      <div style="font-size:0.92rem; color:var(--text-body);">
        <p style="margin-bottom:12px;">Paste this webhook URL into your Twilio Console under <strong>A Call Comes In (HTTP POST)</strong>:</p>
        <div class="form-group">
          <div style="display:flex; gap:8px;">
            <input type="text" id="twilioUrlInput" readonly style="flex:1; font-family:monospace;">
            <button class="utility-btn" onclick="copyTwilioWebhook()">Copy</button>
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

  <footer>
    ZeroMiss Voice Dispatch &bull; Interactive Product Demo Environment (Simulated Data)
  </footer>

  <script>
    let BOARD_DATA = { bookings: [], technicians: [], slots: [], roi_metrics: {} };
    let DEFAULT_CONFIG_EMAIL = 'sean.glenn21@gmail.com';

    const chatStream = document.getElementById('chatStream');
    const userInput = document.getElementById('userInput');
    const dispatchHero = document.getElementById('dispatchHero');
    const waitingPlaceholder = document.getElementById('waitingPlaceholder');
    const phoneMessages = document.getElementById('phoneMessages');
    const contractorInput = document.getElementById('contractorEmail');

    // Update the 4-Step Visual Backbone & Guided Next Step Banner
    function setJourneyProgress(stepNum, bannerHtml, highlightPhone = false) {
      for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`jStep${i}`);
        if (!el) continue;
        el.classList.remove('active-step', 'done-step');
        if (i < stepNum) el.classList.add('done-step');
        else if (i === stepNum) el.classList.add('active-step');
      }
      const banner = document.getElementById('guidedNextStepBanner');
      if (banner && bannerHtml) banner.innerHTML = bannerHtml;

      const chassis = document.getElementById('phoneChassis');
      const callout = document.getElementById('phoneStepCallout');
      if (chassis && callout) {
        if (highlightPhone) {
          chassis.classList.add('highlight-phone');
          callout.classList.add('visible');
        } else {
          chassis.classList.remove('highlight-phone');
          callout.classList.remove('visible');
        }
      }
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

    function speakText(text) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text.replace(/[*_#]/g, ''));
        utter.rate = 1.05;
        window.speechSynthesis.speak(utter);
      }
    }

    function appendMessage(speaker, text, isSarah = false) {
      const bubble = document.createElement('div');
      bubble.className = `bubble ${isSarah ? 'bubble-sarah' : 'bubble-user'}`;
      bubble.innerHTML = `<div class="speaker-name">${speaker}</div><div>${text.replace(/\n/g, '<br>')}</div>`;
      chatStream.appendChild(bubble);
      chatStream.scrollTop = chatStream.scrollHeight;
    }

    async function sendUserMessage() {
      const msg = userInput.value.trim();
      if (!msg) return;
      userInput.value = '';
      appendMessage('Caller (You)', msg, false);
      setJourneyProgress(2, '🎙️ <strong>Step 2 of 4:</strong> Sarah AI is triaging your request and checking technician availability...');

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
          setJourneyProgress(3, '👉 <strong>Next Step (Step 3 of 4):</strong> Job dispatched! Click <strong>"Authorize Deposit via Stripe"</strong> on the phone to complete the flow.', true);
        }
        await fetchBoardData();
      } catch (e) {
        appendMessage('System', 'Connection error.', false);
      }
    }

    function showBookingInHero(booking) {
      waitingPlaceholder.style.display = 'none';
      dispatchHero.classList.add('active');

      const isEmerg = (booking.urgency_level || '').includes('EMERG');
      dispatchHero.className = `dispatch-hero active ${isEmerg ? 'is-emergency' : ''}`;

      const bBadge = document.getElementById('heroBadge');
      bBadge.className = `hero-badge ${isEmerg ? 'badge-emergency' : 'badge-standard'}`;
      bBadge.innerText = isEmerg ? '🚨 Code Red Emergency (45m)' : '✓ Confirmed Service Dispatch';

      const payBadge = document.getElementById('heroPayBadge');
      if (booking.payment_status === 'PAID_VERIFIED') {
        payBadge.style.color = '#15803d';
        payBadge.style.background = '#dcfce7';
        payBadge.style.borderColor = '#86efac';
        payBadge.innerText = '✓ Stripe Deposit Paid';
      } else {
        payBadge.style.color = '#b45309';
        payBadge.style.background = '#fef3c7';
        payBadge.style.borderColor = '#fde68a';
        payBadge.innerText = `💳 Pending $${booking.dispatch_fee} Deposit`;
      }

      document.getElementById('heroTitle').innerText = `${booking.service_type || 'Electrical Service'} — ${booking.customer_name}`;
      document.getElementById('heroContractor').innerText = DEFAULT_CONFIG_EMAIL;
      document.getElementById('tktConf').innerText = booking.confirmation_id;
      document.getElementById('tktCustomer').innerText = booking.customer_name;
      document.getElementById('tktPhone').innerText = booking.phone_number;
      document.getElementById('tktAddress').innerText = booking.service_address;
      document.getElementById('tktTech').innerText = booking.assigned_technician;
      document.getElementById('tktWindow').innerText = `${booking.slot_date} (${booking.slot_time})`;
      document.getElementById('tktFee').innerText = `$${booking.dispatch_fee.toFixed(2)}`;
      document.getElementById('tktVal').innerText = `$${(booking.estimated_job_value || 850).toLocaleString()}`;

      const calBtn = document.getElementById('heroCalBtn');
      if (booking.google_calendar_link) {
        calBtn.href = booking.google_calendar_link;
        calBtn.style.display = 'inline-flex';
      } else {
        calBtn.style.display = 'none';
      }
    }

    function pushCustomerSmsBooking(booking) {
      const smsHtml = `
        <div class="sms-bubble">
          <div class="sms-tag">Appointment Confirmed</div>
          Hi ${booking.customer_name}, your technician <strong>${booking.assigned_technician.split('(')[0].trim()}</strong> is scheduled for <strong>${booking.slot_date} (${booking.slot_time})</strong>.
          <div class="sms-stripe-sheet">
            <div style="display:flex; justify-content:space-between; font-weight:800; font-size:0.8rem; color:#c7d2fe;">
              <span>💳 STRIPE DEPOSIT</span>
              <span style="color:#4ade80;">$${booking.dispatch_fee.toFixed(2)}</span>
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
      try {
        const res = await fetch('/api/simulate-missed-call', { method: 'POST' });
        const data = await res.json();
        const mc = data.missed_call || {};

        const smsHtml = `
          <div class="sms-bubble sms-recoup-card" id="smsCard_${mc.missed_call_id}">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
              <span style="background:rgba(245,158,11,0.25); color:#fbbf24; font-size:0.72rem; font-weight:800; padding:2px 8px; border-radius:4px;">⚠️ MISSED CALL RECOVERY</span>
              <span style="font-size:0.72rem; color:#94a3b8;">3s ago</span>
            </div>
            <div>
              Hi! This is Sarah from ZeroMiss Electrical. We noticed your call dropped! Tap below to lock in tomorrow's 8:00 AM slot right now:
            </div>
            <div class="sms-action-card" onclick="convertMissedCallLead('${mc.missed_call_id}')">
              <div style="font-size:0.75rem; font-weight:800; color:#4ade80;">⚡ 1-TAP SELF-SCHEDULE (+$1,200 SAVED)</div>
              <div style="font-size:0.92rem; font-weight:800; color:#ffffff; margin:4px 0;">Tomorrow 8:00 AM &bull; Tech: Sarah Chen</div>
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
        appendMessage('Sarah (3s SMS Recovery)', `⚡ Sent instant self-scheduling SMS link to customer's phone. Look at the phone on the right and click "Tap to Confirm & Book"!`, true);

        setJourneyProgress(
          2,
          '👉 <strong>Next Step (Step 2 of 4):</strong> Look at the <strong>Customer Phone</strong> on the right and click <strong>"👉 Tap to Confirm &amp; Book ($1,200)"</strong>!',
          true
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
              <div class="recoup-won-badge">🎉 JOB RECOUPED! +$1,200 WON</div>
              <div style="margin:10px 0; font-size:0.85rem;">
                ✓ Confirmed for <strong>Tomorrow 8:00 AM - 12:00 PM</strong> with <strong>Sarah Chen</strong>.
              </div>
              <div class="sms-stripe-sheet">
                <div style="display:flex; justify-content:space-between; font-weight:800; font-size:0.8rem; color:#c7d2fe;">
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

          appendMessage('Sarah (ZeroMiss AI)', `🎉 Customer tapped the SMS link! $1,200 job recouped and dispatched to Sarah Chen. Now click "Authorize $89 Deposit" on the phone!`, true);

          setJourneyProgress(
            3,
            '👉 <strong>Next Step (Step 3 of 4):</strong> Ticket dispatched! Now click <strong>"👉 Authorize $89 Deposit via Stripe"</strong> on the phone to finish.',
            true
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
          document.querySelectorAll('.btn-stripe-pay').forEach(btn => {
            btn.classList.add('paid');
            btn.innerHTML = '✓ $89 Deposit Paid & Verified';
            btn.disabled = true;
          });
          const heroPay = document.getElementById('heroPayBadge');
          if (heroPay) {
            heroPay.style.color = '#15803d';
            heroPay.style.background = '#dcfce7';
            heroPay.style.borderColor = '#86efac';
            heroPay.innerHTML = '✓ Stripe Deposit Verified (PAID)';
          }
          appendMessage('ZeroMiss Billing', `💳 $89.00 diagnostic fee verified via Stripe. No-show risk eliminated!`, true);

          setJourneyProgress(
            4,
            '🎉 <strong>Journey Complete!</strong> You turned a dropped call into <strong>$1,200 pipeline revenue + $89 paid deposit</strong>. Check the metrics below!',
            false
          );
          document.getElementById('jStep4').classList.remove('active-step');
          document.getElementById('jStep4').classList.add('done-step');

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
      alert(`Contractor alert email updated to: ${email}`);
    }

    async function runScenario(scenarioKey) {
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
        setJourneyProgress(
          3,
          '👉 <strong>Next Step (Step 3 of 4):</strong> Emergency/Routine call dispatched! Click <strong>"👉 Authorize Deposit via Stripe"</strong> on the phone.',
          true
        );
      }
      await fetchBoardData();
    }

    async function resetCall() {
      await fetch('/api/reset', { method: 'POST' });
      chatStream.innerHTML = `
        <div class="bubble bubble-sarah">
          <div class="speaker-name">Sarah (ZeroMiss AI Dispatcher)</div>
          Thank you for calling ZeroMiss Electrical 24/7 Dispatch. Click <strong>"▶ Start Demo"</strong> above, or type/speak any electrical issue below to test me live!
        </div>
      `;
      dispatchHero.classList.remove('active');
      waitingPlaceholder.style.display = 'flex';
      phoneMessages.innerHTML = `
        <div class="sms-bubble">
          <div class="sms-tag">Customer Phone Preview</div>
          When Sarah sends a 3-second missed-call recovery link or Stripe deposit request, it appears right here for the homeowner to tap.
        </div>
      `;
      setJourneyProgress(
        1,
        '👉 <strong>What to do first:</strong> Click <strong>"▶ Start Demo: Simulate Dropped Call"</strong> below to see ZeroMiss save a $1,200 job.',
        false
      );
      fetchBoardData();
    }

    async function fetchBoardData() {
      try {
        const res = await fetch('/api/board');
        const data = await res.json();
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
            btnBench.innerText = '🎯 Return to Live Demo Session ($0 Baseline)';
            indBench.innerText = '📈 30-Day Contractor Benchmark (Projected Data)';
            indBench.style.background = '#dcfce7';
            indBench.style.color = '#15803d';
          } else {
            btnBench.innerText = '📈 Preview 30-Day Contractor Benchmark ($18,450)';
            indBench.innerText = '🧪 Simulated Demo Session Data';
            indBench.style.background = '#e0e7ff';
            indBench.style.color = '#3730a3';
          }
        }

        const pipeline = roi.total_pipeline_revenue || 0;
        const elPipe = document.getElementById('kpiPipelineRev');
        elPipe.innerText = `$${pipeline.toLocaleString()}`;
        elPipe.style.color = pipeline > 0 ? '#15803d' : '#0f172a';
        document.getElementById('kpiPipelineSub').innerText = isBench
          ? '18 Monthly Dispatches (Simulated Benchmark)'
          : `${bookingsCount} Dispatch${bookingsCount === 1 ? '' : 'es'} Booked in Session`;

        const fees = roi.fees_collected || 0;
        const elFees = document.getElementById('kpiFeesCol');
        elFees.innerText = `$${fees.toLocaleString()}`;
        elFees.style.color = fees > 0 ? '#15803d' : '#0f172a';
        document.getElementById('kpiFeesSubtext').innerText = isBench
          ? '16 Verified Deposits (Simulated Benchmark)'
          : (fees > 0 ? `✓ $${fees} Verified via Stripe` : '0 Stripe Deposits Paid');

        const missedRec = roi.missed_recovered || 0;
        const atRisk = roi.missed_at_risk_value || 0;
        const elMissed = document.getElementById('kpiMissedRec');
        const elMissedSub = document.getElementById('kpiMissedSub');

        if (isBench) {
          elMissed.innerText = '7 Saved';
          elMissed.style.color = '#2563eb';
          elMissedSub.innerText = '+$8,400 Recouped (Simulated Benchmark)';
        } else if (missedRec > 0) {
          elMissed.innerText = `${missedRec} Saved`;
          elMissed.style.color = '#2563eb';
          elMissedSub.innerText = `+$${roi.recouped_revenue.toLocaleString()} Recouped in Demo`;
        } else if (atRisk > 0) {
          elMissed.innerText = '0 Saved';
          elMissed.style.color = '#d97706';
          elMissedSub.innerText = `⚠️ $${atRisk.toLocaleString()} Currently at Risk!`;
        } else {
          elMissed.innerText = '0 Saved';
          elMissed.style.color = '#0f172a';
          elMissedSub.innerText = '0 Dropped Calls Tested';
        }

        updateTechFilterOptions(data.technicians || []);
        renderCalendar();
        renderFleetView();
      } catch (err) {
        console.error('Error fetching board data:', err);
      }
    }

    function updateTechFilterOptions(techs) {
      const select = document.getElementById('calTechFilter');
      if (!select) return;
      const currentVal = select.value;
      let html = '<option value="ALL">⚡ All Electricians (Full Demo Fleet)</option>';
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
      const filteredSlots = techFilter === 'ALL' ? slots : slots.filter(s => s.technician_id === techFilter);

      const dates = [...new Set(slots.map(s => s.date))].slice(0, 5);
      grid.innerHTML = dates.map(dt => {
        const dObj = new Date(dt + 'T12:00:00');
        const dayName = dObj.toLocaleDateString('en-US', { weekday: 'short' });
        const dateStr = dObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        const windows = [
          { label: 'Morning', key: '08:00 AM - 12:00 PM', shortTime: '8 AM - 12 PM' },
          { label: 'Afternoon', key: '12:00 PM - 04:00 PM', shortTime: '12 PM - 4 PM' },
          { label: 'Evening', key: '04:00 PM - 07:00 PM', shortTime: '4 PM - 7 PM' }
        ];

        const slotsHtml = windows.map(w => {
          const b = bookings.find(bk => bk.slot_date === dt && ((bk.slot_time || '').includes(w.key) || w.key.includes(bk.slot_time || '---')));
          if (b) {
            const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
            return `
              <div class="slot-box is-booked-routine" style="cursor:pointer;" onclick='selectCalendarBooking(${safeObj})'>
                <div class="slot-time-header">
                  <span style="color:#15803d;">⚡ ${w.label}</span>
                  <span style="color:#15803d;">✓ BOOKED</span>
                </div>
                <div class="booked-cust-name">${b.customer_name}</div>
                <div class="booked-cust-meta">${b.service_type}<br>${b.assigned_technician.split('(')[0]}</div>
              </div>
            `;
          }

          const matchingSlot = filteredSlots.find(s => s.date === dt && (s.time_window || '').includes(w.key));
          if (!matchingSlot || matchingSlot.is_blocked) {
            return `
              <div class="slot-box">
                <div class="slot-time-header"><span>${w.label}</span><span style="color:#64748b;">BLOCKED</span></div>
                <div class="slot-tech-avail">Unavailable</div>
              </div>
            `;
          }

          return `
            <div class="slot-box">
              <div class="slot-time-header"><span>${w.label} (${w.shortTime})</span><span style="color:#16a34a;">OPEN</span></div>
              <div class="slot-tech-avail">Tech: ${matchingSlot.technician_name}</div>
              <div class="slot-actions">
                <button class="btn-slot-act btn-slot-book" onclick="openManualBookModal('${matchingSlot.slot_id}')">+ Book</button>
                <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${matchingSlot.slot_id}')">Block</button>
              </div>
            </div>
          `;
        }).join('');

        return `
          <div class="cal-col">
            <div class="cal-col-header">
              <div class="cal-col-day">${dayName}</div>
              <div class="cal-col-sub">${dateStr}</div>
            </div>
            <div class="cal-col-body">${slotsHtml}</div>
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
      document.getElementById('kpiFleetOpenSlots').innerText = slots.filter(s => !s.is_booked && !s.is_blocked).length;
      document.getElementById('kpiFleetBookedJobs').innerText = bookings.length;

      grid.innerHTML = techs.map(t => {
        const specHtml = (t.specialties || []).map(s => `<span class="spec-pill">${s.replace(/_/g, ' ')}</span>`).join('');
        const safeTech = JSON.stringify(t).replace(/'/g, "&#39;");
        return `
          <div class="tech-card-pro">
            <div class="tech-card-top">
              <div class="tech-avatar">👷</div>
              <div style="flex:1;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div class="tech-name">${t.name}</div>
                  <span class="${t.is_on_call ? 'tech-badge-oncall' : 'tech-badge-offduty'}">${t.is_on_call ? '● ON-CALL 24/7' : 'STANDARD'}</span>
                </div>
                <div class="tech-license">${t.license_type} &bull; ⭐ ${t.rating || 4.95}</div>
                <div class="tech-phone">${t.phone}</div>
              </div>
            </div>
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
          document.getElementById('micBtn').classList.remove('listening');
        };
      }
      if (!isListening) {
        recognition.start();
        isListening = true;
        document.getElementById('micBtn').classList.add('listening');
      } else {
        recognition.stop();
      }
    }

    window.addEventListener('DOMContentLoaded', fetchBoardData);
    fetchBoardData();
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
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))

        elif parsed.path == "/api/board":
            bookings_data = [b.__dict__ for b in DB.bookings.values()]
            techs_data = [t.__dict__ for t in DB.technicians.values()]
            slots_data = [s.__dict__ for s in DB.calendar_slots.values()]
            roi_metrics = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "contractor_email": DEFAULT_CONFIG.contractor_email,
                "contractor_name": DEFAULT_CONFIG.contractor_name,
                "bookings": bookings_data,
                "technicians": techs_data,
                "slots": slots_data,
                "roi_metrics": roi_metrics,
                "missed_calls": list(DB.missed_calls.values()),
                "is_benchmark": DB.is_benchmark_mode,
            })

        elif parsed.path == "/api/calendar.ics" or parsed.path == "/calendar.ics":
            feed_data = DB.export_full_ical_feed().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="zeromiss_schedule.ics"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(feed_data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global ACTIVE_SESSION
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
                self._send_json({"status": "SUCCESS", "booking": booking.__dict__, "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        elif parsed.path == "/api/simulate-missed-call":
            mc = DB.record_missed_call(
                caller_phone="(555) 329-8471",
                estimated_value=1200.0,
                caller_name="Lost Lead (After-Hours)",
            )
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "missed_call": mc,
                "message": "Automated text-back fired to lost lead within 3 seconds.",
                "roi_metrics": roi,
            })

        elif parsed.path == "/api/missed-calls/convert":
            mc_id = req_data.get("missed_call_id")
            mc = DB.convert_missed_call(mc_id)
            booking_dict = None
            if mc and mc.get("booking_confirmation_id"):
                b = DB.bookings.get(mc["booking_confirmation_id"])
                if b:
                    booking_dict = b.__dict__
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "missed_call": mc,
                "booking": booking_dict,
                "roi_metrics": roi,
                "bookings": [b.__dict__ for b in DB.bookings.values()],
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
                DEFAULT_CONFIG.contractor_email = new_email
            self._send_json({"status": "SUCCESS", "contractor_email": DEFAULT_CONFIG.contractor_email})

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
                self._send_json({"status": "SUCCESS", "booking": booking.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Failed to book slot"}, 400)

        elif parsed.path == "/api/chat":
            msg = req_data.get("message", "").strip()
            sarah_response = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, msg)
            booking_dict = None
            if ACTIVE_SESSION.active_booking:
                booking_dict = ACTIVE_SESSION.active_booking.__dict__
            elif DB.bookings:
                booking_dict = list(DB.bookings.values())[-1].__dict__
            self._send_json({
                "status": "SUCCESS",
                "response": sarah_response,
                "booking": booking_dict,
            })

        elif parsed.path == "/api/run-scenario":
            DB.reset()
            ACTIVE_SESSION = ACTIVE_AGENT.create_session()
            scenario = req_data.get("scenario", "emergency")
            dialogue = []

            if scenario == "emergency":
                t1_user = "Help, I smell burning rubber coming from the wall behind my refrigerator!"
                dialogue.append({"speaker": "Customer", "text": t1_user, "isSarah": False})
                t1_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t1_user)
                dialogue.append({"speaker": "Sarah", "text": t1_sarah, "isSarah": True})

                t2_user = "1313 Mockingbird Lane 08360, callback number is 609-972-4328"
                dialogue.append({"speaker": "Customer", "text": t2_user, "isSarah": False})
                t2_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t2_user)
                dialogue.append({"speaker": "Sarah", "text": t2_sarah, "isSarah": True})
            else:
                t1_user = "Hi Sarah, I just bought an EV and need a 50-amp Level 2 charger installed in my garage next Wednesday."
                dialogue.append({"speaker": "Customer", "text": t1_user, "isSarah": False})
                t1_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t1_user)
                dialogue.append({"speaker": "Sarah", "text": t1_sarah, "isSarah": True})

                t2_user = "Tomorrow morning works. My name is Alex Rivera, 45 Innovation Way in Cambridge, 555-829-1044, alex@gmail.com"
                dialogue.append({"speaker": "Customer", "text": t2_user, "isSarah": False})
                t2_sarah = ACTIVE_AGENT.process_caller_turn(ACTIVE_SESSION, t2_user)
                dialogue.append({"speaker": "Sarah", "text": t2_sarah, "isSarah": True})

            booking_dict = list(DB.bookings.values())[-1].__dict__ if DB.bookings else None
            self._send_json({
                "status": "SUCCESS",
                "scenario": scenario,
                "dialogue": dialogue,
                "booking": booking_dict,
            })

        elif parsed.path == "/api/reset":
            DB.reset()
            ACTIVE_SESSION = ACTIVE_AGENT.create_session()
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
    print(f"  Contractor Destination:   {DEFAULT_CONFIG.contractor_name} ({DEFAULT_CONFIG.contractor_email})")
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
