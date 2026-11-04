"""ZeroMiss Voice Dispatch - Fleet, Schedule & Revenue Command Center Server.

Serves an enterprise-grade, maximum-ROI web dashboard for electrical contractors.
Features:
1. Executive Revenue Command Center & Interactive ROI Calculator (pipeline value, fees, annual gain).
2. Customer Smartphone Simulator with 1-click Stripe fee payment and missed-call lead recovery.
3. Full-width Fleet Dispatch Calendar with 1-click Google Calendar subscription feed (/api/calendar.ics).
4. Electrician Fleet Management with 1-click live on-call switching and complete CRUD.
5. Production Twilio Voice Webhook (/api/twilio/voice) & Phone Setup Wizard for live mobile calls.
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


HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ZeroMiss Voice Dispatch | Contractor Fleet & Revenue Command Center</title>
  <style>
    :root {
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --card-border: #e2e8f0;
      --card-border-hover: #cbd5e1;
      --navy-header: #0f172a;
      --navy-subhead: #1e293b;
      --primary: #0284c7;
      --primary-hover: #0369a1;
      --text-main: #0f172a;
      --text-secondary: #334155;
      --text-muted: #64748b;
      --success: #16a34a;
      --success-bg: #dcfce7;
      --success-text: #15803d;
      --danger: #dc2626;
      --danger-bg: #fee2e2;
      --danger-text: #b91c1c;
      --warning: #d97706;
      --warning-bg: #fef3c7;
      --warning-text: #b45309;
      --accent: #2563eb;
      --accent-bg: #eff6ff;
      --purple: #7c3aed;
      --purple-bg: #f3e8ff;
      --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
      --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }

    /* TOP COMMERCIAL HEADER (DEEP NAVY) */
    header {
      background: var(--navy-header);
      color: #ffffff;
      border-bottom: 1px solid #1e293b;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      color: white;
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: bold;
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }
    .brand h1 { font-size: 1.22rem; font-weight: 700; letter-spacing: -0.02em; color: #ffffff; }
    .brand p { font-size: 0.78rem; color: #94a3b8; }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .contractor-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #1e293b;
      padding: 5px 10px;
      border-radius: 8px;
      border: 1px solid #334155;
    }
    .contractor-bar label {
      font-size: 0.76rem;
      color: #94a3b8;
      font-weight: 600;
    }
    .contractor-bar input {
      background: #0f172a;
      border: 1px solid #334155;
      color: white;
      padding: 5px 8px;
      border-radius: 6px;
      font-size: 0.8rem;
      width: 190px;
      outline: none;
    }
    .btn-hdr-action {
      background: #0284c7;
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.8rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.2s;
    }
    .btn-hdr-action:hover { background: #0369a1; }
    .btn-hdr-twilio {
      background: #e11d48;
    }
    .btn-hdr-twilio:hover { background: #be123c; }

    /* EXECUTIVE REVENUE & ROI COMMAND BAR */
    .revenue-kpi-bar {
      background: #ffffff;
      border-bottom: 1px solid var(--card-border);
      padding: 14px 24px 16px;
      width: 100%;
      box-shadow: var(--shadow-sm);
    }
    .kpi-top-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
      padding-bottom: 10px;
      border-bottom: 1px solid #f1f5f9;
    }
    .kpi-mode-wrap {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .kpi-mode-label {
      font-size: 0.75rem;
      font-weight: 800;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .btn-benchmark-toggle {
      background: #f1f5f9;
      color: #0f172a;
      border: 1px solid #cbd5e1;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn-benchmark-toggle:hover {
      background: #e2e8f0;
      border-color: #94a3b8;
    }
    .benchmark-indicator {
      font-size: 0.76rem;
      font-weight: 700;
      color: #15803d;
      background: #dcfce7;
      padding: 3px 8px;
      border-radius: 12px;
      border: 1px solid #86efac;
    }
    .kpi-actions-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .btn-hdr-roi {
      background: #10b981;
    }
    .btn-hdr-roi:hover { background: #059669; }
    .btn-hdr-guide {
      background: #8b5cf6;
    }
    .btn-hdr-guide:hover { background: #7c3aed; }
    .btn-hdr-reset {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #cbd5e1;
    }
    .btn-hdr-reset:hover {
      background: #e2e8f0;
      color: #0f172a;
    }

    .rev-metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      width: 100%;
    }
    @media (max-width: 1100px) {
      .rev-metrics-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 640px) {
      .rev-metrics-grid { grid-template-columns: 1fr; }
    }
    .rev-metric-card {
      background: #f8fafc;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 98px;
      transition: all 0.2s;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    .rev-metric-card:hover {
      border-color: #94a3b8;
      background: #ffffff;
      transform: translateY(-1px);
      box-shadow: var(--shadow-sm);
    }
    .rev-label-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      margin-bottom: 2px;
    }
    .rev-label {
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      white-space: nowrap;
    }
    .rev-pill-badge {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      white-space: nowrap;
    }
    .badge-green { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .badge-blue { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-gold { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
    .badge-purple { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }

    .rev-val {
      font-size: 1.45rem;
      font-weight: 800;
      color: var(--text-main);
      line-height: 1.2;
      margin: 3px 0;
      font-variant-numeric: tabular-nums;
    }
    .rev-subtext {
      font-size: 0.74rem;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
    }
    .rev-desc {
      font-size: 0.68rem;
      color: var(--text-muted);
      margin-top: 2px;
      line-height: 1.3;
    }

    /* PORTAL NAVIGATION TABS */
    .portal-nav {
      background: #ffffff;
      border-bottom: 1px solid var(--card-border);
      padding: 0 24px;
      display: flex;
      gap: 8px;
    }
    .nav-btn {
      background: transparent;
      border: none;
      border-bottom: 3px solid transparent;
      color: var(--text-secondary);
      padding: 12px 18px;
      font-size: 0.86rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .nav-btn:hover {
      color: var(--primary);
      background: #f8fafc;
    }
    .nav-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
      background: #f0f9ff;
      font-weight: 700;
    }
    .nav-pill {
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 10px;
      background: #e2e8f0;
      color: #334155;
    }
    .nav-btn.active .nav-pill {
      background: #0284c7;
      color: white;
    }
    .live-pulse {
      width: 8px;
      height: 8px;
      background: #16a34a;
      border-radius: 50%;
      box-shadow: 0 0 0 rgba(22, 163, 74, 0.4);
      animation: pulseGreen 1.6s infinite;
    }
    @keyframes pulseGreen {
      0% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.7); }
      70% { box-shadow: 0 0 0 8px rgba(22, 163, 74, 0); }
      100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
    }

    /* MAIN CONTAINER & VIEWS */
    main {
      padding: 20px 24px;
      max-width: 1680px;
      margin: 0 auto;
      width: 100%;
      flex: 1;
    }
    .tab-view { display: none; }
    .tab-view.active { display: block; }

    /* COMMERCIAL 3-STEP WALKTHROUGH BANNER */
    .walkthrough-banner {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 18px;
      margin-bottom: 18px;
      box-shadow: var(--shadow-sm);
    }
    .walkthrough-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .walkthrough-title-wrap {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .walkthrough-icon { font-size: 1.4rem; }
    .walkthrough-title { font-size: 0.95rem; font-weight: 700; color: var(--text-main); }
    .walkthrough-subtitle { font-size: 0.76rem; color: var(--text-muted); }
    .btn-toggle-guide {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: var(--text-secondary);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-toggle-guide:hover { background: #e2e8f0; color: #0f172a; }
    .walkthrough-steps {
      display: grid;
      grid-template-columns: 1fr auto 1fr auto 1fr;
      gap: 12px;
      align-items: center;
    }
    @media (max-width: 960px) {
      .walkthrough-steps { grid-template-columns: 1fr; }
      .step-arrow { display: none; }
    }
    .step-card {
      background: #f8fafc;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .step-card:hover {
      border-color: #0284c7;
      background: #ffffff;
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
    .step-badge {
      display: inline-block;
      font-size: 0.65rem;
      font-weight: 800;
      text-transform: uppercase;
      color: #0284c7;
      background: #e0f2fe;
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 6px;
    }
    .step-head {
      font-size: 0.88rem;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .step-body {
      font-size: 0.74rem;
      color: var(--text-muted);
      line-height: 1.4;
      margin-bottom: 6px;
    }
    .step-hint {
      font-size: 0.72rem;
      color: #0284c7;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .step-arrow {
      color: #94a3b8;
      font-size: 1.2rem;
      font-weight: bold;
      text-align: center;
    }

    /* 3-COLUMN COCKPIT GRID */
    .console-triple-grid {
      display: grid;
      grid-template-columns: 1fr 1.35fr 360px;
      gap: 20px;
      align-items: start;
    }
    @media (max-width: 1280px) {
      .console-triple-grid {
        grid-template-columns: 1fr 1fr;
      }
      .phone-column-wrap {
        grid-column: span 2;
        display: flex;
        justify-content: center;
      }
    }
    @media (max-width: 860px) {
      .console-triple-grid {
        grid-template-columns: 1fr;
      }
      .phone-column-wrap {
        grid-column: span 1;
      }
    }

    .panel-card {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-sm);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
    }
    .card-header h2 { font-size: 0.96rem; font-weight: 700; color: var(--text-main); }
    .status-badge {
      font-size: 0.72rem;
      background: #dcfce7;
      color: #15803d;
      padding: 3px 8px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      gap: 5px;
      font-weight: 700;
      border: 1px solid #86efac;
    }
    .status-dot { width: 6px; height: 6px; background: #16a34a; border-radius: 50%; }

    .panel-subhead {
      background: #f8fafc;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.74rem;
      color: var(--text-secondary);
      line-height: 1.4;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* SCENARIO ACTION BUTTONS */
    .scenario-triggers {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 14px;
    }
    .scenario-btn {
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      text-align: left;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .scenario-btn .btn-title {
      font-size: 0.8rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .scenario-btn .btn-sub {
      font-size: 0.68rem;
      color: var(--text-muted);
    }
    .btn-emergency {
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }
    .btn-emergency:hover {
      background: #dc2626;
      border-color: #dc2626;
      color: white;
    }
    .btn-emergency:hover .btn-sub { color: #fecaca; }

    .btn-routine {
      background: #f0fdf4;
      border-color: #bbf7d0;
      color: #166534;
    }
    .btn-routine:hover {
      background: #0284c7;
      border-color: #0284c7;
      color: white;
    }
    .btn-routine:hover .btn-sub { color: #e0f2fe; }

    .btn-missed {
      background: #fffbeb;
      border-color: #fde68a;
      color: #92400e;
    }
    .btn-missed:hover {
      background: #d97706;
      border-color: #d97706;
      color: white;
    }
    .btn-missed:hover .btn-sub { color: #fef3c7; }

    .scenario-btn.btn-reset {
      background: #f8fafc;
      border-color: #cbd5e1;
      color: #475569;
    }
    .scenario-btn.btn-reset:hover {
      background: #475569;
      color: white;
    }

    /* CONVERSATION & DISPATCH AUDIO */
    .chat-container {
      background: #f8fafc;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      height: 310px;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 10px;
    }
    .bubble {
      max-width: 88%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 0.8rem;
      line-height: 1.45;
    }
    .bubble-user {
      align-self: flex-end;
      background: #ffffff;
      color: #0f172a;
      border: 1px solid #cbd5e1;
      border-bottom-right-radius: 2px;
    }
    .bubble-sarah {
      align-self: flex-start;
      background: #eff6ff;
      color: #1e3a8a;
      border: 1px solid #bfdbfe;
      border-bottom-left-radius: 2px;
    }
    .speaker-name {
      font-size: 0.68rem;
      font-weight: 700;
      margin-bottom: 3px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .bubble-user .speaker-name { color: #0284c7; text-align: right; }
    .bubble-sarah .speaker-name { color: #1d4ed8; }

    .audio-bar {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      height: 24px;
      margin-bottom: 10px;
      opacity: 0.3;
      transition: opacity 0.3s;
    }
    .audio-bar.speaking { opacity: 1; }
    .wave-line {
      width: 3px;
      height: 6px;
      background: #0284c7;
      border-radius: 3px;
      transition: height 0.15s ease;
    }
    .speaking .wave-line:nth-child(odd) { height: 18px; animation: wave 0.4s infinite alternate; }
    .speaking .wave-line:nth-child(even) { height: 12px; animation: wave 0.4s infinite alternate 0.2s; }
    @keyframes wave {
      0% { height: 6px; }
      100% { height: 20px; }
    }

    .input-row {
      display: flex;
      gap: 8px;
    }
    .btn-mic {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #0f172a;
      border-radius: 8px;
      padding: 0 12px;
      font-size: 1.1rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-mic:hover { background: #e2e8f0; }
    .btn-mic.listening {
      background: #ef4444;
      color: white;
      border-color: #dc2626;
      animation: pulseMic 1s infinite;
    }
    @keyframes pulseMic {
      0% { transform: scale(1); }
      50% { transform: scale(1.06); }
      100% { transform: scale(1); }
    }
    .input-row input {
      flex: 1;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      color: #0f172a;
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 0.82rem;
      outline: none;
    }
    .input-row input:focus { border-color: #0284c7; }
    .input-row button {
      background: #0284c7;
      color: white;
      border: none;
      padding: 0 16px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .input-row button:hover { background: #0369a1; }

    /* CENTER COCKPIT / HERO DISPATCH CARD */
    .cockpit-body {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .dispatch-hero {
      background: #ffffff;
      border: 2px solid #0284c7;
      border-radius: 12px;
      padding: 16px;
      display: none;
      box-shadow: var(--shadow-sm);
    }
    .dispatch-hero.active { display: block; }
    .dispatch-hero.is-emergency {
      border-color: #dc2626;
      background: #fffafa;
    }
    .hero-badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 4px 10px;
      border-radius: 6px;
    }
    .badge-emergency {
      background: #fee2e2;
      color: #b91c1c;
      border: 1px solid #fca5a5;
    }
    .badge-standard {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
    }
    .hero-title { font-size: 1.12rem; font-weight: 700; margin-bottom: 3px; color: var(--text-main); }
    .hero-subtitle { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px; }

    .btn-cal-magic {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #16a34a;
      color: white;
      text-decoration: none;
      padding: 8px 14px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.82rem;
      box-shadow: 0 2px 6px rgba(22, 163, 74, 0.3);
      transition: all 0.2s;
    }
    .btn-cal-magic:hover {
      background: #15803d;
      transform: translateY(-1px);
    }

    .ticket-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.78rem;
      margin-top: 10px;
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
    }
    .ticket-table tr {
      border-bottom: 1px solid #f1f5f9;
    }
    .ticket-table tr:last-child { border-bottom: none; }
    .ticket-table td {
      padding: 7px 10px;
    }
    .ticket-table td:first-child {
      color: var(--text-muted);
      width: 130px;
      font-weight: 600;
      background: #f8fafc;
    }
    .ticket-table td:last-child {
      color: var(--text-main);
      font-weight: 600;
    }

    .waiting-preview-box {
      background: #f8fafc;
      border: 1px dashed #cbd5e1;
      border-radius: 12px;
      padding: 20px;
      text-align: center;
    }
    .preview-badge {
      font-size: 0.68rem;
      font-weight: 800;
      color: #0284c7;
      background: #e0f2fe;
      padding: 3px 8px;
      border-radius: 6px;
      display: inline-block;
      margin-bottom: 8px;
    }
    .waiting-preview-box h3 { font-size: 1.05rem; font-weight: 700; color: var(--text-main); margin-bottom: 6px; }
    .preview-subtitle { font-size: 0.78rem; color: var(--text-muted); margin-bottom: 16px; }
    .preview-features-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      text-align: left;
      margin-bottom: 16px;
    }
    .p-feat {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 0.76rem;
      background: #ffffff;
      padding: 10px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .p-feat-icon { font-size: 1.2rem; }
    .p-feat strong { color: var(--text-main); }
    .preview-cta {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 10px;
      font-size: 0.8rem;
      color: #1d4ed8;
      font-weight: 600;
    }

    /* RIGHT COLUMN: REALISTIC SMARTPHONE CHASSIS */
    .phone-column-wrap {
      display: flex;
      justify-content: center;
    }
    .phone-chassis {
      background: linear-gradient(145deg, #d1d5db, #9ca3af, #cbd5e1);
      padding: 11px;
      border-radius: 44px;
      box-shadow: 0 20px 40px -10px rgba(15, 23, 42, 0.28), inset 0 1px 2px rgba(255, 255, 255, 0.9);
      width: 340px;
      position: relative;
    }
    .phone-screen {
      background: #090d16;
      border-radius: 36px;
      padding: 8px 10px 12px;
      height: 560px;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      border: 1px solid #1e293b;
    }
    .phone-dynamic-island {
      width: 90px;
      height: 20px;
      background: #000000;
      border-radius: 12px;
      margin: 0 auto 6px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding: 0 8px;
      border: 1px solid #1f2937;
    }
    .island-lens {
      width: 7px;
      height: 7px;
      background: #1e293b;
      border-radius: 50%;
      border: 1px solid #334155;
    }
    .phone-status-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 8px 6px;
      font-size: 0.72rem;
      color: #f8fafc;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    .phone-imessage-header {
      background: #182234;
      border: 1px solid #283548;
      border-radius: 12px;
      padding: 6px 10px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .imessage-avatar {
      width: 30px;
      height: 30px;
      background: linear-gradient(135deg, #0284c7, #2563eb);
      border-radius: 50%;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.72rem;
      flex-shrink: 0;
    }
    .imessage-info {
      flex: 1;
      min-width: 0;
      text-align: left;
    }
    .imessage-name {
      font-size: 0.8rem;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .imessage-sub {
      font-size: 0.65rem;
      color: #94a3b8;
    }
    .phone-messages {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 4px 2px;
    }
    .sms-bubble {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 10px 12px;
      font-size: 0.76rem;
      line-height: 1.4;
      color: #e2e8f0;
      position: relative;
    }
    .sms-tag {
      font-size: 0.65rem;
      font-weight: 800;
      color: #38bdf8;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 4px;
    }
    .sms-recoup-card {
      border: 1.5px solid #f59e0b;
      background: #1c1917;
    }
    .sms-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .sms-badge-risk {
      font-size: 0.62rem;
      font-weight: 800;
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .sms-action-card {
      background: #0f172a;
      border: 1px solid #38bdf8;
      border-radius: 10px;
      padding: 10px;
      margin-top: 8px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
    }
    .sms-action-card:hover {
      background: #1e293b;
      transform: translateY(-1px);
    }
    .action-card-tag {
      font-size: 0.62rem;
      font-weight: 800;
      color: #38bdf8;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .action-card-val {
      font-size: 0.7rem;
      font-weight: 800;
      color: #4ade80;
      margin-left: 6px;
    }
    .action-card-title {
      font-size: 0.85rem;
      font-weight: 700;
      color: #ffffff;
      margin: 4px 0 2px;
    }
    .action-card-desc {
      font-size: 0.72rem;
      color: #94a3b8;
      margin-bottom: 8px;
    }
    .btn-action-claim {
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: white;
      border: none;
      padding: 8px 14px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.76rem;
      cursor: pointer;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn-action-claim:hover {
      background: #0369a1;
    }
    .recoup-won-badge {
      background: rgba(34, 197, 94, 0.2);
      border: 1px solid #22c55e;
      color: #4ade80;
      padding: 8px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 0.78rem;
      text-align: center;
      animation: fadeIn 0.3s ease;
    }
    .sms-stripe-sheet {
      border: 1.5px solid #6366f1;
      background: #1e1b4b;
      border-radius: 10px;
      padding: 10px;
      margin-top: 8px;
    }
    .stripe-sheet-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      font-weight: 800;
      color: #c7d2fe;
      margin-bottom: 4px;
    }
    .stripe-sheet-desc {
      font-size: 0.7rem;
      color: #a5b4fc;
      margin-bottom: 8px;
    }
    .btn-stripe-pay {
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: white;
      border: none;
      padding: 8px 12px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.76rem;
      cursor: pointer;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      transition: all 0.2s;
    }
    .btn-stripe-pay:hover { opacity: 0.95; }
    .btn-stripe-pay.paid {
      background: #16a34a;
      cursor: default;
    }
    .phone-home-bar {
      width: 110px;
      height: 4px;
      background: #64748b;
      border-radius: 2px;
      margin: 8px auto 0;
    }

    /* VIEW 2: FLEET DISPATCH CALENDAR */
    .cal-controls-bar {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 20px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      box-shadow: var(--shadow-sm);
    }
    .cal-controls-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .cal-controls-left label {
      font-size: 0.85rem;
      color: var(--text-secondary);
      font-weight: 700;
    }
    .cal-controls-left select {
      background: #f8fafc;
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
      min-width: 220px;
      font-weight: 600;
    }

    .sync-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .btn-cal-action {
      background: #f1f5f9;
      border: 1px solid var(--card-border);
      color: var(--text-secondary);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      transition: all 0.2s;
    }
    .btn-cal-action:hover {
      background: #e2e8f0;
      color: var(--text-main);
    }
    .btn-cal-primary {
      background: #0284c7;
      color: white;
      border-color: #0284c7;
    }
    .btn-cal-primary:hover {
      background: #0369a1;
      color: white;
    }

    .full-calendar-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
      align-items: start;
    }
    @media (max-width: 1200px) {
      .full-calendar-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 768px) {
      .full-calendar-grid { grid-template-columns: 1fr; }
    }
    .cal-col {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-sm);
    }
    .cal-col-header {
      background: #f8fafc;
      border-bottom: 1px solid var(--card-border);
      padding: 10px 14px;
      text-align: center;
    }
    .cal-col-day { font-size: 0.95rem; font-weight: 700; color: var(--text-main); }
    .cal-col-sub { font-size: 0.72rem; color: var(--text-muted); font-weight: 600; }
    .cal-col-body {
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .slot-box {
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 9px 10px;
      background: #f8fafc;
      transition: all 0.2s;
      position: relative;
    }
    .slot-box:hover { border-color: #94a3b8; }
    .slot-time-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      margin-bottom: 4px;
    }
    .slot-time-title { font-weight: 700; color: var(--text-secondary); }
    .slot-tech-avail { font-size: 0.7rem; color: var(--text-muted); margin-bottom: 6px; }
    .slot-actions {
      display: flex;
      gap: 6px;
      margin-top: 6px;
    }
    .btn-slot-act {
      border: none;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.68rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-slot-book { background: #0284c7; color: white; }
    .btn-slot-book:hover { background: #0369a1; }
    .btn-slot-block { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    .btn-slot-block:hover { background: #e2e8f0; color: #0f172a; }

    .slot-box.is-booked-routine {
      background: #f0fdf4;
      border: 1px solid #86efac;
    }
    .slot-box.is-booked-routine .slot-time-title { color: #15803d; font-weight: 800; }
    .booked-cust-name { font-size: 0.86rem; font-weight: 700; color: var(--text-main); margin-bottom: 2px; }
    .booked-cust-meta { font-size: 0.72rem; color: #166534; line-height: 1.35; }

    .slot-box.is-booked-emergency {
      background: #fef2f2;
      border: 1.5px solid #fca5a5;
    }
    .slot-box.is-booked-emergency .slot-time-title { color: #b91c1c; font-weight: 800; }
    .booked-emerg-meta { font-size: 0.72rem; color: #991b1b; line-height: 1.35; }

    .slot-box.is-blocked {
      background: #f1f5f9;
      border: 1px dashed #cbd5e1;
      opacity: 0.85;
    }
    .slot-box.is-blocked .slot-time-title { color: #64748b; }
    .blocked-label { font-size: 0.72rem; color: #64748b; font-weight: 600; margin: 4px 0; }

    /* VIEW 3: FLEET ROSTER MANAGEMENT */
    .fleet-kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 20px;
    }
    @media (max-width: 900px) {
      .fleet-kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
    .kpi-card {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px 18px;
      box-shadow: var(--shadow-sm);
    }
    .kpi-label { font-size: 0.76rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
    .kpi-val { font-size: 1.45rem; font-weight: 800; color: var(--text-main); margin-top: 4px; font-variant-numeric: tabular-nums; }
    .kpi-sub { font-size: 0.74rem; color: #0284c7; margin-top: 2px; font-weight: 600; }

    .fleet-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .fleet-header-row h2 { font-size: 1.15rem; font-weight: 700; color: var(--text-main); }
    .btn-add-electrician {
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 2px 6px rgba(2, 132, 199, 0.3);
      transition: all 0.2s;
    }
    .btn-add-electrician:hover { background: #0369a1; transform: translateY(-1px); }

    .fleet-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }
    .tech-card-pro {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: var(--shadow-sm);
      transition: all 0.2s;
      position: relative;
    }
    .tech-card-pro:hover {
      border-color: #94a3b8;
      box-shadow: var(--shadow-md);
      transform: translateY(-2px);
    }
    .tech-card-pro.is-on-call-glow {
      border: 1.5px solid #86efac;
      background: #fcfdfc;
    }
    .tech-card-top {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .tech-avatar {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      background: #f1f5f9;
      color: #0f172a;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.3rem;
      border: 1px solid #cbd5e1;
    }
    .tech-title-wrap { flex: 1; }
    .tech-name { font-size: 0.98rem; font-weight: 700; color: var(--text-main); }
    .tech-license { font-size: 0.74rem; color: var(--text-muted); font-weight: 600; }
    .tech-phone { font-size: 0.72rem; color: var(--text-secondary); margin-top: 1px; }

    .tech-badge-oncall {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #86efac;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .tech-badge-offduty {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #f1f5f9;
      color: #64748b;
      border: 1px solid #cbd5e1;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 0.68rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .tech-specialties-row {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }
    .spec-pill {
      font-size: 0.68rem;
      background: #f1f5f9;
      color: #334155;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid #e2e8f0;
      font-weight: 600;
    }
    .spec-pill.spec-emerg {
      background: #fee2e2;
      color: #b91c1c;
      border-color: #fca5a5;
      font-weight: 700;
    }

    .tech-actions-row {
      display: flex;
      gap: 8px;
      margin-top: 4px;
      border-top: 1px solid #f1f5f9;
      padding-top: 10px;
    }
    .btn-tech-toggle-oncall {
      flex: 1;
      background: #f0fdf4;
      border: 1px solid #86efac;
      color: #15803d;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-tech-toggle-oncall:hover { background: #dcfce7; }
    .btn-tech-toggle-oncall.is-active-btn {
      background: #fff1f2;
      border-color: #fca5a5;
      color: #b91c1c;
    }
    .btn-tech-toggle-oncall.is-active-btn:hover { background: #fee2e2; }

    .btn-tech-edit {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      color: var(--text-secondary);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-tech-edit:hover { background: #e2e8f0; color: #0f172a; }

    .btn-tech-del {
      background: #fee2e2;
      border: 1px solid #fca5a5;
      color: #b91c1c;
      padding: 6px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-tech-del:hover { background: #fecaca; }

    /* MODAL WINDOWS (CLEAN LIGHT THEME) */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(4px);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-overlay.active { display: flex; }
    .modal-card {
      background: #ffffff;
      border: 1px solid var(--card-border);
      border-radius: 14px;
      width: 100%;
      max-width: 540px;
      padding: 22px;
      box-shadow: var(--shadow-lg);
      animation: modalPop 0.2s ease-out;
      color: var(--text-main);
    }
    @keyframes modalPop {
      from { transform: scale(0.96); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 12px;
    }
    .modal-header h3 { font-size: 1.05rem; font-weight: 700; color: var(--text-main); }
    .modal-close {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 1.4rem;
      cursor: pointer;
      padding: 0 4px;
    }
    .modal-close:hover { color: #0f172a; }
    .form-group {
      margin-bottom: 14px;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }
    .form-group label {
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-secondary);
    }
    .form-group input, .form-group select, .form-group textarea {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      color: #0f172a;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
    }
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
      border-color: #0284c7;
    }
    .btn-modal-submit {
      background: #0284c7;
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.85rem;
      cursor: pointer;
      width: 100%;
      margin-top: 10px;
      transition: all 0.2s;
    }
    .btn-modal-submit:hover { background: #0369a1; }

    /* ROI CALCULATOR MODAL STYLING */
    .slider-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin: 14px 0 6px;
    }
    .slider-label { font-size: 0.82rem; font-weight: 700; color: var(--text-secondary); }
    .slider-val { font-size: 0.92rem; font-weight: 800; color: #0284c7; }
    input[type=range] {
      width: 100%;
      accent-color: #0284c7;
      cursor: pointer;
    }
    .roi-result-banner {
      background: #f0fdf4;
      border: 1px solid #86efac;
      border-radius: 10px;
      padding: 14px;
      margin: 16px 0;
      text-align: center;
    }
    .roi-big-gain {
      font-size: 1.8rem;
      font-weight: 800;
      color: #15803d;
      margin: 4px 0;
    }

    footer {
      background: #0f172a;
      border-top: 1px solid #1e293b;
      padding: 14px 24px;
      text-align: center;
      font-size: 0.78rem;
      color: #94a3b8;
      margin-top: auto;
    }

    @keyframes fadeIn {
      from { opacity: 1; transform: translateY(0); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>

  <!-- Top Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div>
        <div style="display:flex; align-items:center; gap:8px;">
          <h1>ZeroMiss Voice Dispatch</h1>
          <span style="background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid rgba(34,197,94,0.3); font-size:0.68rem; font-weight:700; padding:2px 8px; border-radius:10px;">● CONTRACTOR FLEET OS</span>
        </div>
        <p>Autonomous Voice Reception, Emergency Triage & Lead Recovery for Electrical Contractors</p>
      </div>
    </div>
    <div class="header-actions">
      <div class="contractor-bar">
        <label>Contractor Email:</label>
        <input type="email" id="contractorEmail" value="sean.glenn21@gmail.com" placeholder="contractor@domain.com">
        <button class="btn-hdr-action" onclick="saveContractorEmail()">Set Client</button>
      </div>
    </div>
  </header>

  <!-- EXECUTIVE REVENUE & ROI COMMAND BAR -->
  <div class="revenue-kpi-bar">
    <div class="kpi-top-controls">
      <div class="kpi-mode-wrap">
        <span class="kpi-mode-label">EXECUTIVE METRICS:</span>
        <button class="btn-benchmark-toggle" id="btnBenchmarkToggle" onclick="toggleBenchmarkMode()">
          📈 Load 30-Day Benchmark ($18,450)
        </button>
        <span class="benchmark-indicator" id="benchmarkIndicator">● Live Demo Session ($0.00 Baseline)</span>
      </div>
      <div class="kpi-actions-wrap">
        <button class="btn-hdr-action btn-hdr-roi" onclick="openRoiModal()">
          📊 ROI Calculator
        </button>
        <button class="btn-hdr-action btn-hdr-guide" onclick="openPitchModal()">
          💡 Sales Pitch Script
        </button>
        <button class="btn-hdr-action btn-hdr-twilio" onclick="openTwilioModal()">
          📞 Connect Twilio Phone
        </button>
        <button class="btn-hdr-action btn-hdr-reset" onclick="resetCall()">
          ↺ Reset Session
        </button>
      </div>
    </div>

    <div class="rev-metrics-grid">
      <!-- Card 1: Pipeline Revenue -->
      <div class="rev-metric-card">
        <div class="rev-label-row">
          <span class="rev-label">Pipeline Revenue Won</span>
          <span class="rev-pill-badge badge-green" id="badgePipeline">Real-Time</span>
        </div>
        <span class="rev-val" id="kpiPipelineRev">$0.00</span>
        <span class="rev-subtext" id="kpiPipelineSub">⚡ 0 Scheduled Dispatches</span>
        <span class="rev-desc" id="kpiPipelineDesc">Closed by Sarah AI without human dispatcher</span>
      </div>

      <!-- Card 2: Missed Calls Recouped -->
      <div class="rev-metric-card">
        <div class="rev-label-row">
          <span class="rev-label">Missed Calls Recouped</span>
          <span class="rev-pill-badge badge-blue" id="badgeMissed">3s Recovery</span>
        </div>
        <span class="rev-val" id="kpiMissedRec">0 Recouped</span>
        <span class="rev-subtext" id="kpiMissedSub">📵 0 Dropped Calls</span>
        <span class="rev-desc" id="kpiMissedDesc">Intercepts lost leads before calling competitor</span>
      </div>

      <!-- Card 3: Upfront Diagnostic Fees -->
      <div class="rev-metric-card">
        <div class="rev-label-row">
          <span class="rev-label">Diagnostic Fees Collected</span>
          <span class="rev-pill-badge badge-gold" id="badgeFees">Stripe Link</span>
        </div>
        <span class="rev-val" id="kpiFeesCol">$0.00</span>
        <span class="rev-subtext" id="kpiFeesSubtext">💳 0 Verified Deposits</span>
        <span class="rev-desc" id="kpiFeesDesc">Eliminates 22% contractor no-shows</span>
      </div>

      <!-- Card 4: Fleet & Pickup -->
      <div class="rev-metric-card">
        <div class="rev-label-row">
          <span class="rev-label">Electrician Fleet / Answer</span>
          <span class="rev-pill-badge badge-purple">Twilio TwiML</span>
        </div>
        <span class="rev-val" id="kpiFleetCount">4 Electricians</span>
        <span class="rev-subtext" id="kpiOnCallLead">Marcus Vance (Master On-Call)</span>
        <span class="rev-desc">⚡ Ring 1 Answer (0.8s) • 24/7/365</span>
      </div>
    </div>
  </div>

  <!-- Portal Navigation Tabs -->
  <nav class="portal-nav">
    <button class="nav-btn active" id="btnTabConsole" onclick="switchPortalTab('console')">
      <span class="live-pulse"></span>
      🎙️ Live Voice Dispatch
    </button>
    <button class="nav-btn" id="btnTabCalendar" onclick="switchPortalTab('calendar')">
      📅 Fleet Dispatch Calendar
      <span class="nav-pill" id="calCountPill">0 Bookings</span>
    </button>
    <button class="nav-btn" id="btnTabFleet" onclick="switchPortalTab('fleet')">
      👷 Electrician Fleet Management
      <span class="nav-pill" id="techCountPill">4 Active</span>
    </button>
  </nav>

  <main>
    <!-- 3-STEP COMMERCIAL DEMO WALKTHROUGH -->
    <div class="walkthrough-banner" id="walkthroughBanner">
      <div class="walkthrough-header">
        <div class="walkthrough-title-wrap">
          <span class="walkthrough-icon">🎯</span>
          <div>
            <div class="walkthrough-title">How ZeroMiss Works (3-Step Commercial Sales Walkthrough)</div>
            <div class="walkthrough-subtitle">Watch how ZeroMiss captures lost phone calls and converts them into booked, paid electrical jobs.</div>
          </div>
        </div>
        <button class="btn-toggle-guide" onclick="toggleWalkthrough()" id="btnToggleGuide">Hide Guide ✕</button>
      </div>
      <div class="walkthrough-steps">
        <div class="step-card" onclick="runScenario('emergency')">
          <span class="step-badge">STEP 1: INBOUND CALL</span>
          <div class="step-head">📞 AI Answers on Ring 1 (0.8s)</div>
          <div class="step-body">Sarah triages NFPA 70E hazards (burning smells/sparks) or quotes EV chargers/panels 24/7/365.</div>
          <div class="step-hint">👉 Click: <strong>🚨 Burning Rubber Emergency</strong></div>
        </div>
        <div class="step-arrow">➔</div>
        <div class="step-card" onclick="switchPortalTab('calendar')">
          <span class="step-badge">STEP 2: DISPATCH & SYNC</span>
          <div class="step-head">⚡ Real-Time Calendar Sync</div>
          <div class="step-body">ZeroMiss matches an available certified electrician, locks the time slot, and sends an instant Google/Outlook calendar invite.</div>
          <div class="step-hint">👉 View in: <strong>Center Cockpit & Calendar Tab</strong></div>
        </div>
        <div class="step-arrow">➔</div>
        <div class="step-card" onclick="focusPhoneSimulator()">
          <span class="step-badge">STEP 3: NO-SHOW ELIMINATION</span>
          <div class="step-head">💳 Upfront Stripe Deposit</div>
          <div class="step-body">Customer's phone receives an SMS with a secure Stripe link for the $89 routine or $199 emergency diagnostic fee.</div>
          <div class="step-hint">👉 Click: <strong>"Authorize Fee" on Phone Simulator</strong></div>
        </div>
      </div>
    </div>

    <!-- TAB 1: LIVE VOICE DISPATCH CONSOLE -->
    <div class="tab-view active" id="viewConsole">
      <div class="console-triple-grid">
        <!-- Col 1: Call Simulator -->
        <div class="panel-card">
          <div class="card-header">
            <h2>📞 Live Caller Simulator (Sarah Engine)</h2>
            <span class="status-badge"><span class="status-dot"></span> Ring 1 Answer</span>
          </div>
          <div class="panel-subhead">
            <span>📞</span> <strong>Step 1: Test Inbound Actions</strong> — Click any test below to run Sarah's response.
          </div>

          <div class="scenario-triggers">
            <button class="scenario-btn btn-emergency" onclick="runScenario('emergency')">
              <span class="btn-title">🚨 Burning Rubber Emergency</span>
              <span class="btn-sub">Level 2 Hazard • 45m Code Red</span>
            </button>
            <button class="scenario-btn btn-routine" onclick="runScenario('ev_charger')">
              <span class="btn-title">⚡ Tesla EV Charger Quote</span>
              <span class="btn-sub">50A Circuit • Standard Booking</span>
            </button>
            <button class="scenario-btn btn-missed" onclick="simulateMissedCallLead()">
              <span class="btn-title">📵 Simulate Dropped Call ($1,200 at Risk)</span>
              <span class="btn-sub">Lost Lead • 3s Recovery SMS</span>
            </button>
            <button class="scenario-btn btn-reset" onclick="resetCall()">
              <span class="btn-title">🔄 Reset Demo</span>
            </button>
          </div>

          <div class="chat-container" id="chatStream">
            <div class="bubble bubble-sarah">
              <div class="speaker-name">Sarah (ZeroMiss Dispatcher)</div>
              Thank you for calling ZeroMiss Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?
            </div>
          </div>

          <div class="audio-bar" id="audioBar">
            <div class="wave-line"></div>
            <div class="wave-line"></div>
            <div class="wave-line"></div>
            <div class="wave-line"></div>
            <div class="wave-line"></div>
            <div class="wave-line"></div>
            <div class="wave-line"></div>
          </div>

          <div class="input-row">
            <button class="btn-mic" id="micBtn" onclick="toggleMic()" title="Push-to-Talk via Microphone">🎙️</button>
            <input type="text" id="userInput" placeholder="Speak or type a customer issue..." onkeydown="if(event.key==='Enter') sendUserMessage()">
            <button onclick="sendUserMessage()">Call</button>
          </div>
        </div>

        <!-- Col 2: Dispatch Cockpit / Hero Card -->
        <div class="panel-card">
          <div class="card-header">
            <h2>⚡ Contractor Dispatch Cockpit (What You Receive)</h2>
            <span style="font-size: 0.8rem; color: #0284c7; font-weight: 700;">Real-Time Feed</span>
          </div>
          <div class="panel-subhead">
            <span>⚡</span> <strong>Step 2: Contractor Cockpit</strong> — Real-time ticket details, address, assigned technician, and 1-click Google Calendar sync.
          </div>

          <div class="cockpit-body">
            <!-- Magic Moment Hero Card -->
            <div class="dispatch-hero" id="dispatchHero">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span class="hero-badge badge-standard" id="heroBadge">Confirmed Dispatch</span>
                <span id="heroPayBadge" style="font-size:0.75rem; font-weight:700; color:#b45309; background:#fef3c7; padding:3px 8px; border-radius:4px; border:1px solid #fde68a;">
                  💳 Pending Fee Authorization
                </span>
              </div>
              <div class="hero-title" id="heroTitle">New Service Call Scheduled</div>
              <div class="hero-subtitle" id="heroSubtitle">Dispatched directly to <strong id="heroContractor">sean.glenn21@gmail.com</strong></div>

              <div style="display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap;">
                <a href="#" id="heroCalBtn" target="_blank" class="btn-cal-magic">
                  📅 Click to Add to Google Calendar
                </a>
                <button class="btn-cal-action" onclick="switchPortalTab('calendar')">
                  📅 View on Calendar →
                </button>
              </div>

              <table class="ticket-table" id="ticketTable">
                <tr><td>Confirmation Code:</td><td id="tktConf">-</td></tr>
                <tr><td>Customer Name:</td><td id="tktCustomer">-</td></tr>
                <tr><td>Callback Phone:</td><td id="tktPhone">-</td></tr>
                <tr><td>Service Address:</td><td id="tktAddress">-</td></tr>
                <tr><td>Assigned Electrician:</td><td id="tktTech">-</td></tr>
                <tr><td>Arrival Window:</td><td id="tktWindow">-</td></tr>
                <tr><td>Diagnostic Fee:</td><td id="tktFee">-</td></tr>
                <tr><td>Est. Pipeline Value:</td><td id="tktVal" style="color:#15803d; font-weight:800;">-</td></tr>
              </table>
            </div>

            <!-- Waiting Placeholder Enhanced Preview Card -->
            <div id="waitingPlaceholder" class="waiting-preview-box">
              <div class="preview-badge">⚡ REAL-TIME DISPATCH COCKPIT</div>
              <h3>Live Service Ticket Preview</h3>
              <p class="preview-subtitle">
                When a homeowner calls, Sarah AI handles the entire dispatch workflow in real-time. This cockpit displays:
              </p>
              <div class="preview-features-grid">
                <div class="p-feat">
                  <span class="p-feat-icon">🚨</span>
                  <div><strong>NFPA 70E Safety Triage</strong><br>Instant hazard categorization (Level 1, 2, or 3)</div>
                </div>
                <div class="p-feat">
                  <span class="p-feat-icon">👷</span>
                  <div><strong>Electrician Matching</strong><br>Auto-assigned to qualified on-call technician</div>
                </div>
                <div class="p-feat">
                  <span class="p-feat-icon">📅</span>
                  <div><strong>1-Click Google Calendar</strong><br>Direct calendar invite pushed to your inbox</div>
                </div>
                <div class="p-feat">
                  <span class="p-feat-icon">💳</span>
                  <div><strong>Stripe Deposit Verification</strong><br>Eliminates no-shows via upfront SMS checkout</div>
                </div>
              </div>
              <div class="preview-cta">
                👈 <strong>Try It Live:</strong> Click <strong>"🚨 Burning Rubber Emergency"</strong> or <strong>"Simulate Dropped Call"</strong> on the left!
              </div>
            </div>
          </div>
        </div>

        <!-- Col 3: Customer Smartphone Simulator Widget -->
        <div class="phone-column-wrap">
          <div class="phone-chassis">
            <div class="phone-screen">
              <!-- Dynamic Island -->
              <div class="phone-dynamic-island">
                <div class="island-lens"></div>
              </div>
              <!-- Cellular Status Bar -->
              <div class="phone-status-bar">
                <span>9:41</span>
                <span>●●●● 5G 92%</span>
              </div>
              <!-- iMessage Header -->
              <div class="phone-imessage-header">
                <div class="imessage-avatar">ZM</div>
                <div class="imessage-info">
                  <div class="imessage-name">ZeroMiss Dispatch <span style="color:#38bdf8; font-size:0.7rem;">✓</span></div>
                  <div class="imessage-sub">iMessage • Today 9:41 AM</div>
                </div>
              </div>

              <!-- Message Stream -->
              <div class="phone-messages" id="phoneMessages">
                <div class="sms-bubble">
                  <div class="sms-tag">ZeroMiss 24/7 Dispatch</div>
                  Welcome! When Sarah books your electrical appointment, your instant SMS confirmation & Stripe diagnostic fee checkout link will land right here.
                  <div style="margin-top:6px; font-size:0.72rem; color:#38bdf8; font-weight:600;">
                    👉 Try it: Click a demo call on the left, then click "Authorize Fee" here!
                  </div>
                </div>
              </div>

              <!-- Home Bar -->
              <div class="phone-home-bar"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: FLEET DISPATCH CALENDAR -->
    <div class="tab-view" id="viewCalendar">
      <!-- Calendar Explainer Banner -->
      <div class="panel-subhead" style="border-radius:10px; margin-bottom:14px; background:#ffffff; padding:12px 16px;">
        <span style="font-size:1.2rem;">ℹ️</span>
        <div>
          <strong>Live Master Fleet Dispatch Schedule:</strong> Every service call booked by Sarah AI or created manually syncs here in real-time across morning, afternoon, and evening windows. Electricians and dispatchers can subscribe via Google Calendar, Apple Calendar, or Outlook using the iCal feed. Click <strong>"🚫 Block"</strong> to take technicians off-duty, or <strong>"+ Book Job"</strong> for manual walk-ins.
        </div>
      </div>

      <!-- Calendar Legend -->
      <div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap; margin-bottom:14px; padding:0 4px; font-size:0.75rem;">
        <span style="color:var(--text-muted); font-weight:700; text-transform:uppercase;">Color Legend:</span>
        <span style="display:flex; align-items:center; gap:6px; color:#b91c1c;"><span style="width:10px; height:10px; background:#dc2626; border-radius:3px; display:inline-block;"></span> 🚨 Emergency Code Red (45-60m Priority)</span>
        <span style="display:flex; align-items:center; gap:6px; color:#15803d;"><span style="width:10px; height:10px; background:#16a34a; border-radius:3px; display:inline-block;"></span> ⚡ Scheduled Routine Dispatch</span>
        <span style="display:flex; align-items:center; gap:6px; color:#475569;"><span style="width:10px; height:10px; background:#f8fafc; border:1px solid #94a3b8; border-radius:3px; display:inline-block;"></span> 🟢 Available Open Slot</span>
        <span style="display:flex; align-items:center; gap:6px; color:#64748b;"><span style="width:10px; height:10px; background:#e2e8f0; border-radius:3px; display:inline-block;"></span> 🚫 Blocked / Off-Duty (Personal Time)</span>
      </div>

      <div class="cal-controls-bar">
        <div class="cal-controls-left">
          <label>Filter Electrician:</label>
          <select id="calTechFilter" onchange="renderCalendar()">
            <option value="ALL">⚡ All Electricians (Full Fleet)</option>
          </select>
        </div>

        <div class="sync-actions">
          <button class="btn-cal-action" onclick="copyIcalFeedUrl()">
            📋 Copy iCal Feed URL
          </button>
          <a href="/api/calendar.ics" class="btn-cal-action" download="zeromiss_schedule.ics">
            ⬇️ Download .ICS File
          </a>
          <button class="btn-cal-action btn-cal-primary" onclick="openManualBookModal()">
            + Manual Dispatch Booking
          </button>
        </div>
      </div>

      <div class="full-calendar-grid" id="fullCalendarGrid">
        <!-- Rendered dynamically via renderCalendar() -->
      </div>
    </div>

    <!-- TAB 3: ELECTRICIAN FLEET ROSTER & ON-CALL MANAGEMENT -->
    <div class="tab-view" id="viewFleet">
      <!-- Fleet KPI Summary -->
      <div class="fleet-kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Active Technicians</div>
          <div class="kpi-val" id="kpiFleetTotal">4</div>
          <div class="kpi-sub">Certified Electricians</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">24/7 On-Call Lead</div>
          <div class="kpi-val" id="kpiFleetOnCall" style="font-size:1.15rem; color:#15803d;">Marcus Vance</div>
          <div class="kpi-sub">Priority 45m Emergency Dispatch</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Weekly Open Capacity</div>
          <div class="kpi-val" id="kpiFleetOpenSlots">42</div>
          <div class="kpi-sub">Available Dispatch Windows</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Confirmed Jobs Booked</div>
          <div class="kpi-val" id="kpiFleetBookedJobs">0</div>
          <div class="kpi-sub">Synced Across Fleet</div>
        </div>
      </div>

      <div class="fleet-header-row">
        <div>
          <h2>Electrician Fleet Roster & On-Call Status</h2>
          <p style="font-size:0.78rem; color:var(--text-muted); margin-top:2px;">
            Manage electricians, set on-call night/weekend emergency leads, and configure specialties for Sarah AI's matching engine.
          </p>
        </div>
        <button class="btn-add-electrician" onclick="openAddTechModal()">
          + Add New Electrician
        </button>
      </div>

      <div class="fleet-cards-grid" id="fleetCardsGrid">
        <!-- Rendered dynamically via renderFleetView() -->
      </div>
    </div>
  </main>

  <!-- MODAL: Sales Pitch & Live Demo Guide -->
  <div class="modal-overlay" id="pitchModal">
    <div class="modal-card" style="max-width: 620px;">
      <div class="modal-header">
        <h3>💡 Contractor Sales Pitch & Demo Walkthrough Guide</h3>
        <button class="modal-close" onclick="closePitchModal()">&times;</button>
      </div>
      <div class="modal-body" style="font-size:0.83rem; line-height:1.5; color:var(--text-secondary); max-height: 70vh; overflow-y:auto;">
        <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:12px; margin-bottom:14px;">
          <strong style="color:#1d4ed8; font-size:0.9rem;">🎯 The Core Pitch to Electrical Contractors:</strong>
          <p style="margin-top:6px; color:#1e3a8a;">
            "35% of homeowner electrical calls happen after 5:00 PM or on weekends. 80% of callers who reach a voicemail hang up and call the next electrician on Google. That is <strong>$150,000+ in lost revenue</strong> every year. ZeroMiss answers on Ring 1 with conversational AI, triages NFPA 70E hazards, books the job directly into your calendar, and collects an upfront diagnostic fee via SMS to eliminate no-shows."
          </p>
        </div>

        <strong style="color:var(--text-main); font-size:0.88rem;">🚀 5-Step Live Sales Demo Script:</strong>
        <ol style="margin-left:20px; margin-top:8px; margin-bottom:16px; display:flex; flex-direction:column; gap:8px;">
          <li>
            <strong style="color:#b91c1c;">Simulate Dropped Call:</strong> Click <strong>"Simulate Dropped Call ($1,200 at Risk)"</strong> on the left. Show the contractor how Sarah detects the drop and fires an automated SMS recovery link to the homeowner's phone within 3 seconds.
          </li>
          <li>
            <strong style="color:#15803d;">Tap to Recoup:</strong> Tap <strong>"👉 Tap to Confirm & Book ($1,200)"</strong> on the phone simulator. Watch the missed call flip to "RECOUPED_WON" and instantly add $1,200 to the live pipeline!
          </li>
          <li>
            <strong style="color:#0284c7;">Simulate Emergency:</strong> Click <strong>"🚨 Burning Rubber Emergency"</strong>. Listen to Sarah give NFPA 70E safety instructions and dispatch a 45-min Code Red electrician.
          </li>
          <li>
            <strong style="color:#6366f1;">Simulate Fee Collection:</strong> Click <strong>"💳 Authorize $89 via Stripe"</strong> on the phone. Watch the status turn to "PAID_VERIFIED" and explain how upfront deposits eliminate 22% contractor no-shows.
          </li>
          <li>
            <strong style="color:#d97706;">Show Calendar & Fleet:</strong> Switch to the <strong>"Fleet Calendar"</strong> tab to show the master board and Google Calendar iCal feed export.
          </li>
        </ol>

        <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:12px; margin-bottom:14px;">
          <strong style="color:#15803d;">💰 The ROI Equation (Proven Math):</strong>
          <p style="margin-top:4px; font-size:0.78rem; color:#166534;">
            Saving just <strong>10 to 15 after-hours calls per month</strong> @ $1,200 average electrical ticket = <strong>+$140,000 to +$216,000 in net annual revenue</strong> that otherwise went to competitors.
          </p>
        </div>

        <button class="btn-modal-submit" onclick="closePitchModal()">Start Demo Walkthrough</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Interactive Contractor ROI Calculator -->
  <div class="modal-overlay" id="roiModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>📊 Contractor ROI & Revenue Recovery Calculator</h3>
        <button class="modal-close" onclick="closeRoiModal()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="font-size:0.82rem; color:var(--text-muted); margin-bottom:14px;">
          Adjust your company's metrics below to see how ZeroMiss eliminates lost calls and unlocks guaranteed revenue.
        </p>

        <div class="slider-row">
          <span class="slider-label">Monthly Inbound Calls:</span>
          <span class="slider-val" id="valSliderCalls">50 Calls / Mo</span>
        </div>
        <input type="range" id="sliderCalls" min="10" max="250" value="50" oninput="updateRoiCalculation()">

        <div class="slider-row">
          <span class="slider-label">Average Job Revenue Ticket:</span>
          <span class="slider-val" id="valSliderTicket">$1,200</span>
        </div>
        <input type="range" id="sliderTicket" min="300" max="4000" step="50" value="1200" oninput="updateRoiCalculation()">

        <div class="roi-result-banner">
          <div style="font-size:0.8rem; color:#15803d; font-weight:700; text-transform:uppercase;">
            Projected Recouped Annual Revenue:
          </div>
          <div class="roi-big-gain" id="roiAnnualGain">+$147,000 / yr</div>
          <div style="font-size:0.75rem; color:var(--text-muted);" id="roiBreakdown">
            Based on ~17 after-hours calls/mo & recovering 10.2 jobs/mo with ZeroMiss
          </div>
        </div>

        <button class="btn-modal-submit" onclick="closeRoiModal()">Apply & Close</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Twilio Setup Wizard -->
  <div class="modal-overlay" id="twilioModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>📞 Connect Real Phone Number (Twilio Setup)</h3>
        <button class="modal-close" onclick="closeTwilioModal()">&times;</button>
      </div>
      <div class="modal-body" style="font-size:0.82rem; color:var(--text-secondary); line-height:1.5;">
        <p style="margin-bottom:12px;">
          You can test Sarah directly by dialing a real phone number from your mobile device!
        </p>
        <ol style="margin-left:18px; margin-bottom:14px; display:flex; flex-direction:column; gap:6px;">
          <li>Log in to your <strong>Twilio Console</strong>.</li>
          <li>Navigate to <strong>Phone Numbers &gt; Manage &gt; Active Numbers</strong>.</li>
          <li>Under <strong>Voice & Fax &gt; A Call Comes In</strong>, select <strong>Webhook (HTTP POST)</strong>.</li>
          <li>Paste the live webhook URL below and click Save.</li>
        </ol>

        <div class="form-group">
          <label>Your Live Twilio Voice Webhook URL:</label>
          <div style="display:flex; gap:6px;">
            <input type="text" id="twilioUrlInput" readonly style="font-family:monospace; font-size:0.78rem;">
            <button class="btn-hdr-action" onclick="copyTwilioWebhook()">Copy</button>
          </div>
        </div>

        <button class="btn-modal-submit" onclick="closeTwilioModal()">Done</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Add/Edit Technician -->
  <div class="modal-overlay" id="techModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="techModalTitle">Add New Electrician</h3>
        <button class="modal-close" onclick="closeAddTechModal()">&times;</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="techIdInput">
        <div class="form-group">
          <label>Full Name:</label>
          <input type="text" id="techNameInput" placeholder="e.g. John Doe">
        </div>
        <div class="form-group">
          <label>License Type:</label>
          <select id="techLicenseInput">
            <option value="Master Electrician">Master Electrician</option>
            <option value="Journeyman Electrician" selected>Journeyman Electrician</option>
            <option value="EV & Commercial Specialist">EV & Commercial Specialist</option>
            <option value="Service Electrician">Service Electrician</option>
            <option value="Apprentice / Helper">Apprentice / Helper</option>
          </select>
        </div>
        <div class="form-group">
          <label>Contact Phone:</label>
          <input type="text" id="techPhoneInput" placeholder="(555) 000-0000" value="(555) 019-3321">
        </div>
        <div class="form-group">
          <label>On-Call Status (24/7 Priority Lead):</label>
          <select id="techOnCallInput">
            <option value="false">Off-Duty (Standard Daytime Hours)</option>
            <option value="true">On-Call 24/7 (Emergency Code Red Lead)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Specialties (comma-separated):</label>
          <input type="text" id="techSpecsInput" placeholder="emergency, panel_upgrade, ev_charger" value="residential_repair, lighting">
        </div>
        <button class="btn-modal-submit" onclick="submitTechForm()">Save Technician</button>
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
      <div class="modal-body">
        <div class="form-group">
          <label>Select Calendar Window Slot:</label>
          <select id="manualSlotSelect">
            <!-- Dynamically populated -->
          </select>
        </div>
        <div class="form-group">
          <label>Customer Full Name:</label>
          <input type="text" id="manualCustomerName" placeholder="e.g. Robert Smith">
        </div>
        <div class="form-group">
          <label>Phone Number:</label>
          <input type="text" id="manualCustomerPhone" placeholder="(555) 000-0000">
        </div>
        <div class="form-group">
          <label>Customer Email (for Google Calendar Invite):</label>
          <input type="email" id="manualCustomerEmail" placeholder="customer@gmail.com">
        </div>
        <div class="form-group">
          <label>Service Address:</label>
          <input type="text" id="manualCustomerAddress" placeholder="123 Main St, Springfield">
        </div>
        <div class="form-group">
          <label>Scope of Work / Issue Description:</label>
          <textarea id="manualIssueDesc" rows="3" placeholder="e.g. Install 240V 50A outlet for Tesla charger"></textarea>
        </div>
        <button class="btn-modal-submit" onclick="submitManualBooking()">Confirm & Schedule Dispatch</button>
      </div>
    </div>
  </div>

  <footer>
    ZeroMiss Voice Dispatch &copy; 2026 • Autonomous Fleet Command Center &bull; Designed for Commercial Electrical Contractors
  </footer>

  <script>
    let BOARD_DATA = { bookings: [], technicians: [], slots: [], roi_metrics: {} };
    let CURRENT_TAB = 'console';

    const chatStream = document.getElementById('chatStream');
    const userInput = document.getElementById('userInput');
    const audioBar = document.getElementById('audioBar');
    const dispatchHero = document.getElementById('dispatchHero');
    const waitingPlaceholder = document.getElementById('waitingPlaceholder');
    const phoneMessages = document.getElementById('phoneMessages');
    const contractorInput = document.getElementById('contractorEmail');

    // Tab Switching
    function switchPortalTab(tabKey) {
      CURRENT_TAB = tabKey;
      document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

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

    // TTS Voice Simulation
    function speakText(text) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const clean = text.replace(/[*_#]/g, '');
        const utter = new SpeechSynthesisUtterance(clean);
        utter.rate = 1.05;
        utter.pitch = 1.0;
        utter.onstart = () => audioBar.classList.add('speaking');
        utter.onend = () => audioBar.classList.remove('speaking');
        utter.onerror = () => audioBar.classList.remove('speaking');
        window.speechSynthesis.speak(utter);
      }
    }

    function appendMessage(speaker, text, isSarah = false) {
      const bubble = document.createElement('div');
      bubble.className = `bubble ${isSarah ? 'bubble-sarah' : 'bubble-user'}`;
      bubble.innerHTML = `
        <div class="speaker-name">${speaker}</div>
        <div>${text.replace(/\n/g, '<br>')}</div>
      `;
      chatStream.appendChild(bubble);
      chatStream.scrollTop = chatStream.scrollHeight;
    }

    async function sendUserMessage() {
      const msg = userInput.value.trim();
      if (!msg) return;
      userInput.value = '';
      appendMessage('Caller (You)', msg, false);

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        appendMessage('Sarah (ZeroMiss Dispatcher)', data.response, true);
        speakText(data.response);

        if (data.booking) {
          showBookingInHero(data.booking);
          pushCustomerSmsBooking(data.booking);
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
      bBadge.innerText = isEmerg ? '🚨 Emergency Code Red (45m Dispatch)' : '✓ Confirmed Standard Service';

      const payBadge = document.getElementById('heroPayBadge');
      if (booking.payment_status === 'PAID_VERIFIED') {
        payBadge.style.color = '#15803d';
        payBadge.style.background = '#dcfce7';
        payBadge.style.borderColor = '#86efac';
        payBadge.innerText = '✓ Stripe Deposit Verified (PAID)';
      } else {
        payBadge.style.color = '#b45309';
        payBadge.style.background = '#fef3c7';
        payBadge.style.borderColor = '#fde68a';
        payBadge.innerText = `💳 Pending $${booking.dispatch_fee} Deposit`;
      }

      document.getElementById('heroTitle').innerText = `${booking.service_type || 'Electrical Service'} - ${booking.customer_name}`;
      document.getElementById('heroContractor').innerText = DEFAULT_CONFIG_EMAIL || 'sean.glenn21@gmail.com';

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
      const isEmerg = (booking.urgency_level || '').includes('EMERG');
      const smsHtml = `
        <div class="sms-bubble">
          <div class="sms-tag">${isEmerg ? '🚨 Priority Code Red' : 'ZeroMiss Confirmed'}</div>
          Hi ${booking.customer_name}, your electrician <strong>${booking.assigned_technician.split('(')[0].trim()}</strong> is locked for <strong>${booking.slot_date} (${booking.slot_time})</strong>.
          <br><br>
          Service Address: <em>${booking.service_address}</em>
          <div class="sms-stripe-sheet">
            <div class="stripe-sheet-header">
              <span>💳 STRIPE DEPOSIT AUTHORIZATION</span>
              <span style="color:#4ade80;">$${booking.dispatch_fee.toFixed(2)}</span>
            </div>
            <div class="stripe-sheet-desc">Lock in arrival window & eliminate contractor no-show fee.</div>
            <button class="btn-stripe-pay ${booking.payment_status === 'PAID_VERIFIED' ? 'paid' : ''}" id="smsPayBtn_${booking.confirmation_id}" onclick="payStripeDeposit('${booking.confirmation_id}')">
              ${booking.payment_status === 'PAID_VERIFIED' ? '✓ $89 Deposit Paid & Verified' : `💳 Authorize $${booking.dispatch_fee} via Stripe`}
            </button>
          </div>
        </div>
      `;
      phoneMessages.innerHTML += smsHtml;
      phoneMessages.scrollTop = phoneMessages.scrollHeight;
    }

    // Step 1: Simulate Dropped Call -> Logs to Cockpit, Shows $1,200 At Risk, Dispatches 3s SMS Recovery
    async function simulateMissedCallLead() {
      try {
        const res = await fetch('/api/simulate-missed-call', { method: 'POST' });
        const data = await res.json();
        const mc = data.missed_call || {};

        const smsHtml = `
          <div class="sms-bubble sms-recoup-card" id="smsCard_${mc.missed_call_id}">
            <div class="sms-card-header">
              <span class="sms-badge-risk">⚠️ MISSED CALL INTERCEPTED</span>
              <span style="font-size:0.65rem; color:#94a3b8;">${mc.timestamp || 'Just now'}</span>
            </div>
            <div style="font-size:0.75rem; color:#f8fafc; line-height:1.4; margin-bottom:8px;">
              Hi! This is Sarah from ZeroMiss Electrical Dispatch. We noticed your call dropped! To lock in the earliest certified electrician in your area without waiting on hold, tap below:
            </div>
            <div class="sms-action-card" onclick="convertMissedCallLead('${mc.missed_call_id}')">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span class="action-card-tag">⚡ 1-TAP SELF-SCHEDULE</span>
                <span class="action-card-val">+$1,200 Job Saved</span>
              </div>
              <div class="action-card-title">Reserve Earliest Open Slot</div>
              <div class="action-card-desc">Tomorrow 8:00 AM • Tech: Sarah Chen</div>
              <button class="btn-action-claim" id="btnClaim_${mc.missed_call_id}">
                👉 Tap to Confirm & Book ($1,200)
              </button>
            </div>
          </div>
        `;
        phoneMessages.innerHTML += smsHtml;
        phoneMessages.scrollTop = phoneMessages.scrollHeight;

        appendMessage('Sarah (SMS Lead Recovery)', `⚠️ [LOST CALL DETECTED]: Caller from ${mc.caller_phone || '(555) 329-8471'} hung up without booking. Estimated $1,200 revenue at risk.
⚡ [3s TEXT-BACK FIRED]: Dispatched dynamic self-scheduling link to customer's smartphone. Tap on phone to claim!`, true);

        await fetchBoardData();
      } catch (e) {
        alert('Error simulating missed call.');
      }
    }

    // Step 2: Customer Taps Self-Schedule Link on Phone -> Flips to Won, Adds $1,200 to Pipeline, Confirms Booking
    async function convertMissedCallLead(mcId) {
      const claimBtn = document.getElementById(`btnClaim_${mcId}`);
      if (claimBtn) {
        claimBtn.innerText = '⏳ Booking slot...';
      }
      try {
        const res = await fetch('/api/missed-calls/convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ missed_call_id: mcId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          const card = document.getElementById(`smsCard_${mcId}`);
          if (card) {
            card.innerHTML = `
              <div class="recoup-won-badge">
                🎉 RECOUPED WON! +$1,200 CAPTURED
              </div>
              <div style="font-size:0.75rem; color:#e2e8f0; margin:8px 0; line-height:1.4;">
                ✓ Appointment Confirmed: Tomorrow 8:00 AM - 12:00 PM with Sarah Chen (EV Specialist).
              </div>
              <div class="sms-stripe-sheet">
                <div class="stripe-sheet-header">
                  <span>💳 UPFRONT STRIPE DEPOSIT</span>
                  <span style="color:#4ade80;">$89.00</span>
                </div>
                <div class="stripe-sheet-desc">Locks in technician arrival window & prevents competitor jump.</div>
                <button class="btn-stripe-pay" id="btnPayRecoup_${data.booking ? data.booking.confirmation_id : ''}" onclick="payStripeDeposit('${data.booking ? data.booking.confirmation_id : ''}')">
                  💳 Authorize $89 Deposit via Stripe
                </button>
              </div>
            `;
          }

          if (data.booking) {
            showBookingInHero(data.booking);
          }

          appendMessage('Sarah (ZeroMiss Dispatcher)', `🎉 [REVENUE RECOUPED]: Customer tapped self-schedule link! Booked $1,200 service call for tomorrow 8:00 AM. Contractor Sean Glenn dispatched!`, true);

          await fetchBoardData();
        }
      } catch (e) {
        alert('Error converting missed call lead.');
      }
    }

    // Step 3: Upfront Stripe Deposit Authorization
    async function payStripeDeposit(confirmationId) {
      if (!confirmationId) {
        if (BOARD_DATA && BOARD_DATA.bookings && BOARD_DATA.bookings.length) {
          confirmationId = BOARD_DATA.bookings[BOARD_DATA.bookings.length - 1].confirmation_id;
        }
      }
      try {
        const res = await fetch('/api/bookings/pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation_id: confirmationId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          document.querySelectorAll('.btn-stripe-pay, .btn-sms-pay').forEach(btn => {
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
          appendMessage('ZeroMiss Billing', `💳 [PAYMENT VERIFIED]: $89.00 diagnostic fee confirmed via Stripe for ${confirmationId}. No-show risk eliminated!`, true);
          await fetchBoardData();
        }
      } catch (e) {
        alert('Payment authorization failed.');
      }
    }

    // Toggle 30-Day Benchmark Mode vs Live Demo Session ($0 Baseline)
    async function toggleBenchmarkMode() {
      try {
        const res = await fetch('/api/benchmark/toggle', { method: 'POST' });
        const data = await res.json();
        await fetchBoardData();
      } catch (e) {
        alert('Error toggling benchmark mode.');
      }
    }

    async function saveContractorEmail() {
      const email = contractorInput.value.trim();
      if (!email) return;
      try {
        await fetch('/api/set-contractor', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email })
        });
        DEFAULT_CONFIG_EMAIL = email;
        alert(`Contractor destination updated to: ${email}`);
      } catch (e) {
        alert('Failed to update contractor email');
      }
    }

    async function runScenario(scenarioKey) {
      waitingPlaceholder.style.display = 'none';
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
        if (i === data.dialogue.length - 1 && item.isSarah) {
          speakText(item.text);
        }
      }

      if (data.booking) {
        showBookingInHero(data.booking);
        pushCustomerSmsBooking(data.booking);
      }
      await fetchBoardData();
    }

    async function resetCall() {
      await fetch('/api/reset', { method: 'POST' });
      chatStream.innerHTML = `
        <div class="bubble bubble-sarah">
          <div class="speaker-name">Sarah (ZeroMiss Dispatcher)</div>
          Thank you for calling ZeroMiss Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?
        </div>
      `;
      dispatchHero.classList.remove('active');
      waitingPlaceholder.style.display = 'block';
      phoneMessages.innerHTML = `
        <div class="sms-bubble">
          <div class="sms-tag">ZeroMiss 24/7 Dispatch</div>
          Welcome! When Sarah books your electrical appointment, your instant SMS confirmation & Stripe fee checkout link will land right here.
        </div>
      `;
      fetchBoardData();
    }

    let DEFAULT_CONFIG_EMAIL = 'sean.glenn21@gmail.com';

    // Fetch Board Data
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
        document.getElementById('calCountPill').innerText = `${bookingsCount} Booking${bookingsCount === 1 ? '' : 's'}`;
        document.getElementById('techCountPill').innerText = `${techsCount} Active`;

        document.getElementById('kpiFleetCount').innerText = `${techsCount} Electricians`;
        const onCallTech = (data.technicians || []).find(t => t.is_on_call);
        document.getElementById('kpiOnCallLead').innerText = onCallTech ? `${onCallTech.name} (On-Call)` : 'None Assigned';

        const roi = data.roi_metrics || {};
        const isBench = roi.is_benchmark || false;

        // Mode Toggle Button & Indicator
        const btnBench = document.getElementById('btnBenchmarkToggle');
        const indBench = document.getElementById('benchmarkIndicator');
        if (btnBench && indBench) {
          if (isBench) {
            btnBench.innerText = '🎯 Switch to Live Session ($0 Baseline)';
            indBench.innerText = '● 30-Day Benchmark ($18,450)';
            indBench.style.color = '#2563eb';
            indBench.style.background = '#eff6ff';
            indBench.style.borderColor = '#bfdbfe';
          } else {
            btnBench.innerText = '📈 Load 30-Day Benchmark ($18,450)';
            indBench.innerText = '● Live Demo Session ($0.00 Baseline)';
            indBench.style.color = '#15803d';
            indBench.style.background = '#dcfce7';
            indBench.style.borderColor = '#86efac';
          }
        }

        // 1. Pipeline Revenue (Tabular, 100% real math)
        const pipeline = roi.total_pipeline_revenue || 0;
        const elPipe = document.getElementById('kpiPipelineRev');
        elPipe.innerText = `$${pipeline.toLocaleString(undefined, { minimumFractionDigits: pipeline % 1 === 0 ? 0 : 2 })}`;
        if (pipeline > 0) {
          elPipe.style.color = '#15803d';
        } else {
          elPipe.style.color = '#0f172a';
        }
        document.getElementById('kpiPipelineSub').innerText = isBench ? '⚡ 18 Monthly Dispatches' : `⚡ ${bookingsCount} Scheduled Dispatch${bookingsCount === 1 ? '' : 'es'}`;

        // 2. Diagnostic Fees
        const fees = roi.fees_collected || 0;
        const elFees = document.getElementById('kpiFeesCol');
        elFees.innerText = `$${fees.toLocaleString(undefined, { minimumFractionDigits: fees % 1 === 0 ? 0 : 2 })}`;
        if (fees > 0) {
          elFees.style.color = '#15803d';
        } else {
          elFees.style.color = '#0f172a';
        }
        const feeSub = document.getElementById('kpiFeesSubtext');
        if (feeSub) {
          feeSub.innerText = isBench ? '✓ 16 Verified Deposits' : (fees > 0 ? `✓ $${fees} Deposits Paid` : '💳 0 Deposits Collected');
        }

        // 3. Missed Calls
        const missedRec = roi.missed_recovered || 0;
        const atRisk = roi.missed_at_risk_value || 0;
        const elMissed = document.getElementById('kpiMissedRec');
        const elMissedSub = document.getElementById('kpiMissedSub');
        const badgeMissed = document.getElementById('badgeMissed');

        if (isBench) {
          elMissed.innerText = '7 Recovered';
          elMissed.style.color = '#2563eb';
          elMissedSub.innerText = '+$8,400 Recouped Revenue';
          if (badgeMissed) badgeMissed.innerText = '+$8,400 Won';
        } else if (missedRec > 0) {
          elMissed.innerText = `${missedRec} Recovered`;
          elMissed.style.color = '#2563eb';
          elMissedSub.innerText = `+$${roi.recouped_revenue.toLocaleString()} Recouped Won`;
          if (badgeMissed) badgeMissed.innerText = `+$${roi.recouped_revenue.toLocaleString()} Won`;
        } else if (atRisk > 0) {
          elMissed.innerText = '0 Recovered';
          elMissed.style.color = '#d97706';
          elMissedSub.innerText = `⚠️ $${atRisk.toLocaleString()} at Risk!`;
          if (badgeMissed) badgeMissed.innerText = 'At Risk';
        } else {
          elMissed.innerText = '0 Recovered';
          elMissed.style.color = '#0f172a';
          elMissedSub.innerText = '📵 0 Dropped Calls';
          if (badgeMissed) badgeMissed.innerText = '3s Recovery';
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
      const currentVal = select.value;
      let html = '<option value="ALL">⚡ All Electricians (Full Fleet)</option>';
      techs.forEach(t => {
        html += `<option value="${t.technician_id}">${t.name} (${t.license_type})</option>`;
      });
      select.innerHTML = html;
      select.value = currentVal || 'ALL';
    }

    // RENDER FULL CALENDAR
    function renderCalendar() {
      const grid = document.getElementById('fullCalendarGrid');
      if (!grid) return;

      const techFilter = document.getElementById('calTechFilter').value;
      const slots = BOARD_DATA.slots || [];
      const bookings = BOARD_DATA.bookings || [];

      const filteredSlots = techFilter === 'ALL'
        ? slots
        : slots.filter(s => s.technician_id === techFilter);

      const dates = [...new Set(slots.map(s => s.date))].slice(0, 5);
      if (!dates.length) {
        const today = new Date();
        for (let i = 1; i <= 5; i++) {
          const d = new Date(today);
          d.setDate(today.getDate() + i);
          dates.push(d.toISOString().split('T')[0]);
        }
      }

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
          const isEmergBooking = bookings.find(bk => {
            const isEmerg = (bk.urgency_level || '').includes('EMERG');
            const dateMatch = bk.slot_date === dt || (bk.slot_date === 'today' && dt === dates[0]);
            return isEmerg && dateMatch;
          });

          if (isEmergBooking && w.label === 'Morning') {
            const safeObj = JSON.stringify(isEmergBooking).replace(/'/g, "&#39;");
            return `
              <div class="slot-box is-booked-emergency" onclick='selectCalendarBooking(${safeObj})'>
                <div class="slot-time-header">
                  <span class="slot-time-title">🚨 EMERGENCY CODE RED</span>
                  <span style="font-size:0.7rem; color:#b91c1c; font-weight:700;">Within 45-60 Min</span>
                </div>
                <div class="booked-cust-name">${isEmergBooking.customer_name}</div>
                <div class="booked-emerg-meta">
                  📍 ${isEmergBooking.service_address}<br>
                  ⚡ ${isEmergBooking.assigned_technician.split('(')[0].trim()}<br>
                  Ref: ${isEmergBooking.confirmation_id}
                </div>
              </div>
            `;
          }

          const b = bookings.find(bk => {
            const dateMatch = bk.slot_date === dt;
            const timeMatch = (bk.slot_time || '').includes(w.key) || (w.key.includes(bk.slot_time || '---'));
            return dateMatch && timeMatch;
          });

          if (b) {
            const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
            return `
              <div class="slot-box is-booked-routine" onclick='selectCalendarBooking(${safeObj})'>
                <div class="slot-time-header">
                  <span class="slot-time-title">⚡ ${w.label.toUpperCase()} (${w.shortTime})</span>
                  <span style="font-size:0.68rem; color:#15803d; font-weight:700;">✓ BOOKED</span>
                </div>
                <div class="booked-cust-name">${b.customer_name}</div>
                <div class="booked-cust-meta">
                  🔧 ${b.service_type || 'Electrical Service'}<br>
                  ⚡ ${b.assigned_technician.split('(')[0].trim()}<br>
                  📍 ${b.service_address}
                </div>
              </div>
            `;
          }

          const matchingSlot = filteredSlots.find(s => s.date === dt && (s.time_window || '').includes(w.key));
          if (!matchingSlot) {
            return `
              <div class="slot-box is-blocked">
                <div class="slot-time-header">
                  <span class="slot-time-title">${w.label} (${w.shortTime})</span>
                  <span style="font-size:0.68rem; color:#64748b;">OFF-DUTY</span>
                </div>
                <div class="blocked-label">No Tech Scheduled</div>
              </div>
            `;
          }

          if (matchingSlot.is_blocked) {
            return `
              <div class="slot-box is-blocked">
                <div class="slot-time-header">
                  <span class="slot-time-title">${w.label} (${w.shortTime})</span>
                  <span style="font-size:0.68rem; color:#64748b;">🚫 BLOCKED</span>
                </div>
                <div class="blocked-label">${matchingSlot.blocked_reason || 'Unavailable / Off-Duty'}</div>
                <div style="font-size:0.7rem; color:#64748b; margin-top:4px;">Tech: ${matchingSlot.technician_name}</div>
                <div class="slot-actions">
                  <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${matchingSlot.slot_id}')">Unblock</button>
                </div>
              </div>
            `;
          }

          return `
            <div class="slot-box">
              <div class="slot-time-header">
                <span class="slot-time-title">${w.label} (${w.shortTime})</span>
                <span style="font-size:0.68rem; color:#15803d; font-weight:700;">● OPEN</span>
              </div>
              <div class="slot-tech-avail">⚡ Tech: ${matchingSlot.technician_name}</div>
              <div class="slot-actions">
                <button class="btn-slot-act btn-slot-book" onclick="openManualBookModal('${matchingSlot.slot_id}')">+ Book</button>
                <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${matchingSlot.slot_id}')">🚫 Block</button>
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
            <div class="cal-col-body">
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

    // RENDER FLEET ROSTER MANAGEMENT VIEW
    function renderFleetView() {
      const grid = document.getElementById('fleetCardsGrid');
      if (!grid) return;

      const techs = BOARD_DATA.technicians || [];
      const slots = BOARD_DATA.slots || [];
      const bookings = BOARD_DATA.bookings || [];

      document.getElementById('kpiFleetTotal').innerText = techs.length;
      const onCallTech = techs.find(t => t.is_on_call);
      document.getElementById('kpiFleetOnCall').innerText = onCallTech ? onCallTech.name : 'None Assigned';

      const openSlots = slots.filter(s => !s.is_booked && !s.is_blocked).length;
      document.getElementById('kpiFleetOpenSlots').innerText = openSlots;
      document.getElementById('kpiFleetBookedJobs').innerText = bookings.length;

      grid.innerHTML = techs.map(t => {
        const specHtml = (t.specialties || []).map(s => {
          const isEmerg = s.includes('emergency') || s.includes('voltage');
          return `<span class="spec-pill ${isEmerg ? 'spec-emerg' : ''}">${s.replace(/_/g, ' ')}</span>`;
        }).join('');

        const safeTech = JSON.stringify(t).replace(/'/g, "&#39;");

        return `
          <div class="tech-card-pro ${t.is_on_call ? 'is-on-call-glow' : ''}">
            <div class="tech-card-top">
              <div class="tech-avatar">👷</div>
              <div class="tech-title-wrap">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div class="tech-name">${t.name}</div>
                  <span class="${t.is_on_call ? 'tech-badge-oncall' : 'tech-badge-offduty'}">
                    ${t.is_on_call ? '● ON-CALL 24/7' : '○ REGULAR HOURS'}
                  </span>
                </div>
                <div class="tech-license">${t.license_type} &bull; Rating: ⭐ ${t.rating || 4.95}</div>
                <div class="tech-phone">📞 ${t.phone} &bull; ID: ${t.technician_id}</div>
              </div>
            </div>

            <div class="tech-specialties-row">
              ${specHtml}
            </div>

            <div class="tech-actions-row">
              <button class="btn-tech-toggle-oncall ${t.is_on_call ? 'is-active-btn' : ''}" onclick="toggleTechOnCall('${t.technician_id}')">
                ${t.is_on_call ? 'Remove from On-Call' : '⚡ Make On-Call Lead'}
              </button>
              <button class="btn-tech-edit" onclick='openEditTechModal(${safeTech})'>
                Edit
              </button>
              <button class="btn-tech-del" onclick="deleteTech('${t.technician_id}', '${t.name}')" title="Delete Technician">
                ✕
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    // Technician API actions
    async function toggleTechOnCall(techId) {
      try {
        const res = await fetch('/api/technicians/toggle-on-call', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ technician_id: techId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          await fetchBoardData();
        }
      } catch (e) {
        alert('Failed to update on-call status');
      }
    }

    async function toggleBlockSlot(slotId) {
      try {
        const res = await fetch('/api/slots/toggle-block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slot_id: slotId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          await fetchBoardData();
        }
      } catch (e) {
        alert('Failed to update slot');
      }
    }

    async function deleteTech(techId, name) {
      if (!confirm(`Are you sure you want to remove ${name} from the active fleet roster?`)) return;
      try {
        const res = await fetch('/api/technicians/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ technician_id: techId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          await fetchBoardData();
        }
      } catch (e) {
        alert('Failed to delete technician');
      }
    }

    // Modal forms: Add/Edit Tech
    function openAddTechModal() {
      document.getElementById('techModalTitle').innerText = 'Add New Electrician';
      document.getElementById('techIdInput').value = '';
      document.getElementById('techNameInput').value = '';
      document.getElementById('techPhoneInput').value = '(555) 019-5512';
      document.getElementById('techOnCallInput').value = 'false';
      document.getElementById('techSpecsInput').value = 'residential_repair, lighting';
      document.getElementById('techModal').classList.add('active');
    }

    function openEditTechModal(tech) {
      document.getElementById('techModalTitle').innerText = `Edit: ${tech.name}`;
      document.getElementById('techIdInput').value = tech.technician_id;
      document.getElementById('techNameInput').value = tech.name;
      document.getElementById('techLicenseInput').value = tech.license_type;
      document.getElementById('techPhoneInput').value = tech.phone;
      document.getElementById('techOnCallInput').value = tech.is_on_call ? 'true' : 'false';
      document.getElementById('techSpecsInput').value = (tech.specialties || []).join(', ');
      document.getElementById('techModal').classList.add('active');
    }

    function closeAddTechModal() {
      document.getElementById('techModal').classList.remove('active');
    }

    async function submitTechForm() {
      const tid = document.getElementById('techIdInput').value.trim();
      const name = document.getElementById('techNameInput').value.trim();
      const license = document.getElementById('techLicenseInput').value;
      const phone = document.getElementById('techPhoneInput').value.trim();
      const onCall = document.getElementById('techOnCallInput').value === 'true';
      const specsRaw = document.getElementById('techSpecsInput').value;
      const specs = specsRaw.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);

      if (!name) {
        alert('Please enter technician full name.');
        return;
      }

      const endpoint = tid ? '/api/technicians/update' : '/api/technicians';
      const payload = {
        name: name,
        license_type: license,
        phone: phone,
        is_on_call: onCall,
        specialties: specs
      };
      if (tid) payload.technician_id = tid;

      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          closeAddTechModal();
          await fetchBoardData();
        } else {
          alert('Error saving technician: ' + (data.message || 'Unknown'));
        }
      } catch (e) {
        alert('Network error saving technician.');
      }
    }

    // Manual Booking Modal
    function openManualBookModal(preselectedSlotId = '') {
      const select = document.getElementById('manualSlotSelect');
      const slots = (BOARD_DATA.slots || []).filter(s => !s.is_booked && !s.is_blocked);
      if (!slots.length) {
        alert('No open slots available to book.');
        return;
      }
      select.innerHTML = slots.map(s => {
        return `<option value="${s.slot_id}">${s.date} - ${s.time_window} (${s.technician_name})</option>`;
      }).join('');

      if (preselectedSlotId) select.value = preselectedSlotId;
      document.getElementById('manualBookModal').classList.add('active');
    }

    function closeManualBookModal() {
      document.getElementById('manualBookModal').classList.remove('active');
    }

    async function submitManualBooking() {
      const slot_id = document.getElementById('manualSlotSelect').value;
      const customer_name = document.getElementById('manualCustomerName').value.trim();
      const phone_number = document.getElementById('manualCustomerPhone').value.trim();
      const customer_email = document.getElementById('manualCustomerEmail').value.trim();
      const service_address = document.getElementById('manualCustomerAddress').value.trim();
      const issue_description = document.getElementById('manualIssueDesc').value.trim();

      if (!customer_name || !service_address || !issue_description) {
        alert('Please fill out customer name, service address, and issue description.');
        return;
      }

      try {
        const res = await fetch('/api/slots/manual-book', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            slot_id,
            customer_name,
            phone_number,
            service_address,
            issue_description,
            customer_email
          })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          closeManualBookModal();
          await fetchBoardData();
          alert(`⚡ Confirmed! Appointment booked under confirmation ${data.booking.confirmation_id}. Added to Google Calendar.`);
        } else {
          alert('Booking failed: ' + (data.message || 'Slot unavailable'));
        }
      } catch (e) {
        alert('Network error.');
      }
    }

    // Copy iCal Feed URL
    function copyIcalFeedUrl() {
      const url = `${window.location.origin}/api/calendar.ics`;
      navigator.clipboard.writeText(url).then(() => {
        alert(`📋 Copied live calendar feed URL to clipboard:\n\n${url}\n\nYou can paste this into Google Calendar ("From URL") or Apple Calendar to sync dispatches automatically.`);
      }).catch(() => {
        prompt('Copy calendar subscription URL:', url);
      });
    }

    // ROI Calculator Modal
    function openRoiModal() {
      document.getElementById('roiModal').classList.add('active');
      updateRoiCalculation();
    }
    function closeRoiModal() {
      document.getElementById('roiModal').classList.remove('active');
    }

    function updateRoiCalculation() {
      const calls = parseInt(document.getElementById('sliderCalls').value);
      const ticket = parseInt(document.getElementById('sliderTicket').value);

      document.getElementById('valSliderCalls').innerText = `${calls} Calls / Mo`;
      document.getElementById('valSliderTicket').innerText = `$${ticket.toLocaleString()}`;

      // Industry benchmark: 35% after hours, 62% abandoned without AI, 70% booking close rate with ZeroMiss
      const afterHoursCalls = calls * 0.35;
      const recoveredJobsMonthly = afterHoursCalls * 0.62 * 0.70;
      const annualGain = Math.round(recoveredJobsMonthly * ticket * 12);

      document.getElementById('roiAnnualGain').innerText = `+$${annualGain.toLocaleString()} / yr`;
      document.getElementById('roiBreakdown').innerText = `Based on ~${Math.round(afterHoursCalls)} after-hours calls/mo & recovering ${recoveredJobsMonthly.toFixed(1)} high-ticket jobs/mo`;
    }

    // Twilio Setup Modal
    function openTwilioModal() {
      document.getElementById('twilioModal').classList.add('active');
      document.getElementById('twilioUrlInput').value = `${window.location.origin}/api/twilio/voice`;
    }
    function closeTwilioModal() {
      document.getElementById('twilioModal').classList.remove('active');
    }
    function copyTwilioWebhook() {
      const url = document.getElementById('twilioUrlInput').value;
      navigator.clipboard.writeText(url).then(() => alert('📋 Webhook URL copied to clipboard! Paste into Twilio Voice Webhook URL.'));
    }

    // Sales Pitch & Demo Walkthrough Modal
    function openPitchModal() {
      document.getElementById('pitchModal').classList.add('active');
    }
    function closePitchModal() {
      document.getElementById('pitchModal').classList.remove('active');
    }

    // Toggle 3-Step Walkthrough Banner
    function toggleWalkthrough() {
      const banner = document.getElementById('walkthroughBanner');
      if (!banner) return;
      const steps = banner.querySelector('.walkthrough-steps');
      const btn = document.getElementById('btnToggleGuide');
      if (steps.style.display === 'none') {
        steps.style.display = 'grid';
        btn.innerText = 'Hide Guide ✕';
      } else {
        steps.style.display = 'none';
        btn.innerText = 'Show Guide ▾';
      }
    }

    // Focus on Customer Phone Simulator
    function focusPhoneSimulator() {
      const phone = document.querySelector('.phone-chassis');
      if (phone) {
        phone.scrollIntoView({ behavior: 'smooth', block: 'center' });
        phone.style.boxShadow = '0 0 25px rgba(2, 132, 199, 0.6)';
        setTimeout(() => {
          phone.style.boxShadow = '0 20px 40px -10px rgba(15, 23, 42, 0.28), inset 0 1px 2px rgba(255, 255, 255, 0.9)';
        }, 2200);
      }
    }

    // Microphone speech recognition
    let recognition;
    let isListening = false;
    const micBtn = document.getElementById('micBtn');

    function toggleMic() {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {
        alert('Microphone speech recognition requires Google Chrome or MS Edge.');
        return;
      }

      if (!recognition) {
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.onresult = (e) => {
          const transcript = e.results[0][0].transcript;
          userInput.value = transcript;
          sendUserMessage();
        };
        recognition.onend = () => {
          isListening = false;
          micBtn.classList.remove('listening');
        };
      }

      if (!isListening) {
        recognition.start();
        isListening = true;
        micBtn.classList.add('listening');
      } else {
        recognition.stop();
        isListening = false;
        micBtn.classList.remove('listening');
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

        # Parse form data (Twilio webhooks) or JSON
        if "application/x-www-form-urlencoded" in content_type:
            parsed_form = urllib.parse.parse_qs(post_body)
            req_data = {k: v[0] if len(v) == 1 else v for k, v in parsed_form.items()}
        else:
            try:
                req_data = json.loads(post_body) if post_body else {}
            except Exception:
                req_data = {}

        parsed = urllib.parse.urlparse(self.path)

        # 1. TWILIO PRODUCTION VOICE WEBHOOKS
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
            speech_result = req_data.get("SpeechResult", "").strip()
            if not speech_result:
                speech_result = "Hello, I need an electrician."

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

        # 2. STRIPE UPFRONT FEE AUTHORIZATION
        elif parsed.path == "/api/bookings/pay":
            cid = req_data.get("confirmation_id", "").strip()
            booking = DB.mark_booking_paid(cid)
            roi = DB.calculate_contractor_roi_metrics()
            if booking:
                self._send_json({"status": "SUCCESS", "booking": booking.__dict__, "roi_metrics": roi})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        # 3. SIMULATE MISSED AFTER-HOURS CALL LEAD RECOVERY
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

        # 3b. CONVERT MISSED CALL (CUSTOMER TAPS SELF-SCHEDULE LINK)
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

        # 3c. BENCHMARK MODE TOGGLE (LIVE SESSION VS 30-DAY BENCHMARK)
        elif parsed.path == "/api/benchmark/toggle":
            is_bench = DB.toggle_benchmark_mode()
            roi = DB.calculate_contractor_roi_metrics()
            self._send_json({
                "status": "SUCCESS",
                "is_benchmark": is_bench,
                "roi_metrics": roi,
            })

        # 4. CONTRACTOR DESTINATION EMAIL
        elif parsed.path == "/api/set-contractor":
            new_email = req_data.get("email", "").strip()
            if new_email:
                DEFAULT_CONFIG.contractor_email = new_email
            self._send_json({"status": "SUCCESS", "contractor_email": DEFAULT_CONFIG.contractor_email})

        # 5. TECHNICIAN FLEET MANAGEMENT
        elif parsed.path == "/api/technicians":
            name = req_data.get("name", "").strip()
            if not name:
                self._send_json({"status": "ERROR", "message": "Technician name required"}, 400)
                return
            license_type = req_data.get("license_type", "Journeyman Electrician").strip()
            phone = req_data.get("phone", "(555) 019-0000").strip()
            is_on_call = bool(req_data.get("is_on_call", False))
            specialties = req_data.get("specialties", ["residential_repair", "lighting"])
            new_tech = DB.add_technician(
                name=name,
                license_type=license_type,
                phone=phone,
                is_on_call=is_on_call,
                specialties=specialties,
            )
            self._send_json({
                "status": "SUCCESS",
                "technician": new_tech.__dict__,
                "technicians": [t.__dict__ for t in DB.technicians.values()],
                "slots": [s.__dict__ for s in DB.calendar_slots.values()],
            })

        elif parsed.path == "/api/technicians/update":
            tid = req_data.get("technician_id", "").strip()
            name = req_data.get("name", "").strip()
            license_type = req_data.get("license_type", "Journeyman Electrician").strip()
            phone = req_data.get("phone", "(555) 019-0000").strip()
            is_on_call = bool(req_data.get("is_on_call", False))
            specialties = req_data.get("specialties", ["residential_repair"])
            tech = DB.update_technician(tid, name, license_type, phone, is_on_call, specialties)
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

        # 6. CALENDAR SLOTS
        elif parsed.path == "/api/slots/toggle-block":
            slot_id = req_data.get("slot_id", "").strip()
            reason = req_data.get("reason", "Unavailable / Off-Duty").strip()
            slot = DB.toggle_block_slot(slot_id, reason)
            if slot:
                self._send_json({"status": "SUCCESS", "slot": slot.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Slot not found"}, 404)

        elif parsed.path == "/api/slots/manual-book":
            slot_id = req_data.get("slot_id", "").strip()
            customer_name = req_data.get("customer_name", "Valued Customer").strip()
            phone_number = req_data.get("phone_number", "(555) 000-0000").strip()
            service_address = req_data.get("service_address", "Customer Address").strip()
            issue_description = req_data.get("issue_description", "Electrical service call").strip()
            customer_email = req_data.get("customer_email", "").strip() or None
            booking = DB.manual_book_slot(
                slot_id=slot_id,
                customer_name=customer_name,
                phone_number=phone_number,
                service_address=service_address,
                issue_description=issue_description,
                customer_email=customer_email,
            )
            if booking:
                self._send_json({"status": "SUCCESS", "booking": booking.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Failed to book slot or slot already booked"}, 400)

        # 7. LIVE CONVERSATION CHAT
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

        # 8. SCENARIOS & RESET
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

            else:  # ev_charger routine
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
    print("  ZeroMiss Voice Dispatch - Maximum-ROI Contractor Command Center Server")
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
