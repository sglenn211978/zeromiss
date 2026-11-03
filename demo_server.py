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
  <title>ZeroMiss Voice Dispatch | Maximum-ROI Contractor Command Center</title>
  <style>
    :root {
      --bg: #0b1120;
      --card-bg: #1e293b;
      --card-border: #334155;
      --primary: #0284c7;
      --primary-hover: #0369a1;
      --danger: #dc2626;
      --danger-hover: #b91c1c;
      --success: #16a34a;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --gold: #f59e0b;
      --purple: #8b5cf6;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Top Brand & Contractor Bar */
    header {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
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
      width: 42px;
      height: 42px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      font-weight: bold;
      box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
    }
    .brand h1 { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; }
    .brand p { font-size: 0.8rem; color: var(--text-muted); }

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
      padding: 5px 12px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .contractor-bar label {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 600;
    }
    .contractor-bar input {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: white;
      padding: 5px 8px;
      border-radius: 6px;
      font-size: 0.82rem;
      width: 200px;
      outline: none;
    }
    .btn-hdr-action {
      background: var(--primary);
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.82rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.2s;
    }
    .btn-hdr-action:hover { background: var(--primary-hover); }
    .btn-hdr-twilio {
      background: linear-gradient(135deg, #f43f5e, #e11d48);
    }
    .btn-hdr-twilio:hover { background: #be123c; }

    /* EXECUTIVE REVENUE & ROI COMMAND BAR */
    .revenue-kpi-bar {
      background: linear-gradient(90deg, #0b1329, #131f37, #0b1329);
      border-bottom: 1px solid var(--card-border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .rev-metrics-wrap {
      display: flex;
      align-items: stretch;
      gap: 14px;
      flex-wrap: wrap;
    }
    .rev-metric-card {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 8px 14px;
      display: flex;
      flex-direction: column;
      min-width: 195px;
      position: relative;
      transition: all 0.2s;
    }
    .rev-metric-card:hover {
      border-color: var(--accent);
      background: rgba(30, 41, 59, 0.85);
      transform: translateY(-1px);
    }
    .rev-label-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      margin-bottom: 3px;
    }
    .rev-label {
      font-size: 0.68rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .info-icon {
      font-size: 0.75rem;
      color: #64748b;
      cursor: help;
    }
    .rev-val {
      font-size: 1.25rem;
      font-weight: 800;
      color: #38bdf8;
      line-height: 1.2;
    }
    .rev-val.val-green { color: #4ade80; }
    .rev-val.val-gold { color: #fbbf24; }
    .rev-subtext {
      font-size: 0.7rem;
      color: #94a3b8;
      margin-top: 3px;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .rev-action-hint {
      font-size: 0.66rem;
      color: #38bdf8;
      font-weight: 700;
      margin-top: 3px;
    }

    /* Tooltip styles */
    .has-tooltip { position: relative; }
    .has-tooltip .tooltip-text {
      visibility: hidden;
      width: 250px;
      background-color: #0f172a;
      color: #f1f5f9;
      text-align: left;
      border-radius: 8px;
      padding: 9px 12px;
      position: absolute;
      z-index: 200;
      top: calc(100% + 8px);
      left: 50%;
      transform: translateX(-50%);
      opacity: 0;
      transition: opacity 0.2s;
      font-size: 0.72rem;
      line-height: 1.4;
      border: 1px solid var(--accent);
      box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.6);
      font-weight: normal;
      text-transform: none;
      letter-spacing: normal;
      pointer-events: none;
    }
    .has-tooltip:hover .tooltip-text {
      visibility: visible;
      opacity: 1;
    }

    .btn-roi-calc {
      background: linear-gradient(135deg, #10b981, #059669);
      color: white;
      border: none;
      padding: 10px 16px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.82rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
      transition: all 0.2s;
    }
    .btn-roi-calc:hover {
      opacity: 0.95;
      transform: translateY(-1px);
    }
    .btn-hdr-guide {
      background: linear-gradient(135deg, #8b5cf6, #7c3aed);
    }
    .btn-hdr-guide:hover { background: #6d28d9; }

    /* Top Commercial 3-Step Walkthrough Banner */
    .walkthrough-banner {
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.85), rgba(15, 23, 42, 0.95));
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 12px;
      padding: 14px 18px;
      margin-bottom: 18px;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
      position: relative;
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
    .walkthrough-icon {
      font-size: 1.5rem;
    }
    .walkthrough-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: white;
    }
    .walkthrough-subtitle {
      font-size: 0.76rem;
      color: var(--text-muted);
    }
    .btn-toggle-guide {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-toggle-guide:hover {
      background: rgba(255, 255, 255, 0.12);
      color: white;
    }
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
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.2s;
      position: relative;
    }
    .step-card:hover {
      border-color: var(--accent);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(56, 189, 248, 0.15);
    }
    .step-badge {
      display: inline-block;
      font-size: 0.65rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--accent);
      background: rgba(56, 189, 248, 0.15);
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 6px;
    }
    .step-head {
      font-size: 0.88rem;
      font-weight: 700;
      color: white;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .step-body {
      font-size: 0.74rem;
      color: #94a3b8;
      line-height: 1.4;
      margin-bottom: 6px;
    }
    .step-hint {
      font-size: 0.7rem;
      color: #38bdf8;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .step-arrow {
      color: #64748b;
      font-size: 1.3rem;
      font-weight: bold;
      text-align: center;
    }

    /* Column subheader info bar */
    .panel-subhead {
      padding: 8px 14px;
      background: rgba(15, 23, 42, 0.5);
      border-bottom: 1px solid var(--card-border);
      font-size: 0.74rem;
      color: var(--text-muted);
      line-height: 1.4;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Waiting placeholder enhanced preview card */
    .waiting-preview-box {
      background: #0f172a;
      border: 1px dashed var(--card-border);
      border-radius: 12px;
      padding: 24px 20px;
      text-align: center;
    }
    .preview-badge {
      display: inline-block;
      background: rgba(2, 132, 199, 0.2);
      border: 1px solid rgba(2, 132, 199, 0.4);
      color: #38bdf8;
      font-size: 0.68rem;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 12px;
      letter-spacing: 0.04em;
      margin-bottom: 10px;
    }
    .waiting-preview-box h3 {
      font-size: 1.05rem;
      color: white;
      margin-bottom: 6px;
      font-weight: 700;
    }
    .preview-subtitle {
      font-size: 0.8rem;
      color: var(--text-muted);
      max-width: 420px;
      margin: 0 auto 16px;
      line-height: 1.4;
    }
    .preview-features-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      text-align: left;
      margin-bottom: 18px;
    }
    @media (max-width: 600px) {
      .preview-features-grid { grid-template-columns: 1fr; }
    }
    .p-feat {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 8px 10px;
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 0.72rem;
      color: #cbd5e1;
      line-height: 1.35;
    }
    .p-feat-icon {
      font-size: 1.1rem;
      flex-shrink: 0;
    }
    .p-feat strong {
      color: white;
      font-size: 0.76rem;
    }
    .preview-cta {
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 0.78rem;
      color: #e0f2fe;
      display: inline-block;
    }

    /* Portal Navigation Tabs */
    .portal-nav {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      padding: 0 24px;
      gap: 8px;
      overflow-x: auto;
    }
    .nav-btn {
      background: none;
      border: none;
      border-bottom: 3px solid transparent;
      color: var(--text-muted);
      padding: 12px 18px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .nav-btn:hover {
      color: var(--text);
      background: rgba(255, 255, 255, 0.02);
    }
    .nav-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
      background: rgba(56, 189, 248, 0.05);
    }
    .nav-pill {
      background: #334155;
      color: #94a3b8;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 12px;
    }
    .nav-btn.active .nav-pill {
      background: rgba(56, 189, 248, 0.2);
      color: #38bdf8;
    }
    .live-pulse {
      width: 8px;
      height: 8px;
      background: #22c55e;
      border-radius: 50%;
      box-shadow: 0 0 8px #22c55e;
      animation: pulse 2s infinite;
    }

    /* Main Container & Tab Views */
    main {
      flex: 1;
      padding: 20px 24px;
      max-width: 1550px;
      margin: 0 auto;
      width: 100%;
    }
    .tab-view { display: none; }
    .tab-view.active { display: block; animation: fadeIn 0.2s ease-in-out; }

    /* VIEW 1: CONSOLE VIEW (3 Columns: Caller, Cockpit, Customer Phone) */
    .console-triple-grid {
      display: grid;
      grid-template-columns: 1.15fr 1fr 340px;
      gap: 20px;
    }
    @media (max-width: 1300px) {
      .console-triple-grid { grid-template-columns: 1fr 1fr; }
      .phone-column-wrap { grid-column: span 2; }
    }
    @media (max-width: 900px) {
      .console-triple-grid { grid-template-columns: 1fr; }
      .phone-column-wrap { grid-column: span 1; }
    }

    .panel-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .card-header {
      padding: 14px 18px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(15, 23, 42, 0.6);
    }
    .card-header h2 { font-size: 0.98rem; font-weight: 700; }
    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      color: #4ade80;
      background: rgba(34, 197, 94, 0.15);
      padding: 4px 10px;
      border-radius: 12px;
      border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .status-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; }

    /* Scenario triggers */
    .scenario-triggers {
      display: flex;
      gap: 8px;
      padding: 12px 16px;
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      flex-wrap: wrap;
    }
    .scenario-btn {
      flex: 1;
      min-width: 175px;
      padding: 9px 12px;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
      transition: all 0.2s;
      text-align: left;
    }
    .scenario-btn .btn-title {
      font-weight: 700;
      font-size: 0.82rem;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .scenario-btn .btn-sub {
      font-size: 0.68rem;
      opacity: 0.85;
      font-weight: 500;
      line-height: 1.2;
    }
    .btn-emergency {
      background: rgba(220, 38, 38, 0.15);
      color: #f87171;
      border-color: rgba(220, 38, 38, 0.4);
    }
    .btn-emergency:hover { background: #dc2626; color: white; }
    .btn-routine {
      background: rgba(2, 132, 199, 0.15);
      color: #38bdf8;
      border-color: rgba(2, 132, 199, 0.4);
    }
    .btn-routine:hover { background: #0284c7; color: white; }
    .btn-missed {
      background: rgba(139, 92, 246, 0.15);
      color: #c084fc;
      border-color: rgba(139, 92, 246, 0.4);
    }
    .btn-missed:hover { background: #7c3aed; color: white; }
    .scenario-btn.btn-reset {
      background: #334155;
      color: #cbd5e1;
      flex: 0 0 auto;
      min-width: 75px;
      align-items: center;
      justify-content: center;
    }
    .scenario-btn.btn-reset:hover { background: #475569; color: white; }

    /* Chat stream */
    .chat-container {
      height: 380px;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #0b1120;
    }
    .bubble {
      max-width: 84%;
      padding: 11px 15px;
      border-radius: 12px;
      font-size: 0.9rem;
      line-height: 1.5;
    }
    .bubble-user {
      align-self: flex-end;
      background: #0284c7;
      color: white;
      border-bottom-right-radius: 2px;
    }
    .bubble-sarah {
      align-self: flex-start;
      background: #1e293b;
      color: #f1f5f9;
      border: 1px solid var(--card-border);
      border-bottom-left-radius: 2px;
    }
    .speaker-name {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
      color: #94a3b8;
    }
    .bubble-user .speaker-name { color: #bae6fd; text-align: right; }
    .bubble-sarah .speaker-name { color: #38bdf8; }

    /* Audio wave simulation */
    .audio-bar {
      height: 28px;
      background: #0f172a;
      border-top: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 0 16px;
    }
    .wave-line {
      width: 3px;
      height: 8px;
      background: #38bdf8;
      border-radius: 2px;
      transition: height 0.15s ease;
    }
    .speaking .wave-line:nth-child(odd) { height: 20px; animation: wave 0.4s infinite alternate; }
    .speaking .wave-line:nth-child(even) { height: 14px; animation: wave 0.4s infinite 0.2s alternate; }
    @keyframes wave {
      0% { height: 8px; }
      100% { height: 22px; }
    }

    /* Input row */
    .input-row {
      padding: 12px 16px;
      background: #0f172a;
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 10px;
    }
    .btn-mic {
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: #e2e8f0;
      width: 42px;
      height: 42px;
      border-radius: 8px;
      font-size: 1.2rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }
    .btn-mic:hover { background: #334155; }
    .btn-mic.listening {
      background: #dc2626;
      border-color: #ef4444;
      animation: pulse 1s infinite;
    }
    .input-row input {
      flex: 1;
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: white;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 0.92rem;
      outline: none;
    }
    .input-row input:focus { border-color: var(--accent); }
    .input-row button {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0 18px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
    }
    .input-row button:hover { background: var(--primary-hover); }

    /* Center Cockpit / Hero Card */
    .cockpit-body {
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .dispatch-hero {
      background: linear-gradient(135deg, rgba(2, 132, 199, 0.15), rgba(15, 23, 42, 0.9));
      border: 2px solid #0284c7;
      border-radius: 12px;
      padding: 18px;
      display: none;
      animation: fadeIn 0.4s ease;
      position: relative;
    }
    .dispatch-hero.active { display: block; }
    .hero-badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }
    .badge-emergency {
      background: #dc2626;
      color: white;
      animation: pulse 1.5s infinite;
    }
    .badge-standard {
      background: #16a34a;
      color: white;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.85; transform: scale(1.02); }
    }
    .hero-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 4px; }
    .hero-subtitle { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 14px; }

    .btn-cal-magic {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #2563eb;
      color: white;
      text-decoration: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.85rem;
      margin-bottom: 14px;
      transition: background 0.2s, transform 0.1s;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    }
    .btn-cal-magic:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
    }

    .ticket-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      margin-top: 6px;
    }
    .ticket-table td {
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .ticket-table td:first-child {
      color: var(--text-muted);
      width: 140px;
      font-weight: 600;
    }
    .ticket-table td:last-child {
      color: var(--text);
      font-weight: 500;
    }

    /* RIGHT COLUMN: SIMULATED CUSTOMER SMARTPHONE */
    .phone-container {
      background: #0f172a;
      border: 3px solid #334155;
      border-radius: 28px;
      padding: 16px 12px;
      display: flex;
      flex-direction: column;
      height: 540px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      position: relative;
    }
    .phone-notch {
      width: 110px;
      height: 18px;
      background: #1e293b;
      border-radius: 10px;
      margin: 0 auto 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .notch-camera { width: 6px; height: 6px; background: #475569; border-radius: 50%; }
    .notch-speaker { width: 35px; height: 4px; background: #334155; border-radius: 2px; }

    .phone-header {
      text-align: center;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 8px;
      margin-bottom: 10px;
    }
    .phone-header-title { font-size: 0.82rem; font-weight: 700; color: white; }
    .phone-header-sub { font-size: 0.7rem; color: #38bdf8; }

    .phone-messages {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 6px 4px;
    }
    .sms-bubble {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 0.78rem;
      line-height: 1.4;
      color: #e2e8f0;
      animation: fadeIn 0.3s ease;
      position: relative;
    }
    .sms-tag {
      font-size: 0.68rem;
      font-weight: 700;
      color: var(--accent);
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .sms-stripe-box {
      margin-top: 8px;
      background: #0f172a;
      border: 1px dashed var(--accent);
      border-radius: 8px;
      padding: 8px;
      text-align: center;
    }
    .btn-sms-pay {
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      margin-top: 4px;
      transition: all 0.2s;
    }
    .btn-sms-pay:hover { opacity: 0.9; }
    .btn-sms-pay.paid {
      background: #16a34a;
      cursor: default;
    }

    /* VIEW 2: FLEET DISPATCH CALENDAR */
    .cal-controls-bar {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 20px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .cal-controls-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .cal-controls-left label {
      font-size: 0.85rem;
      color: var(--text-muted);
      font-weight: 600;
    }
    .cal-controls-left select {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: white;
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.88rem;
      outline: none;
      min-width: 220px;
    }

    .sync-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .btn-cal-action {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: #e2e8f0;
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      transition: all 0.2s;
    }
    .btn-cal-action:hover {
      background: #334155;
      border-color: #475569;
    }
    .btn-cal-primary {
      background: #0284c7;
      border-color: #0284c7;
      color: white;
    }
    .btn-cal-primary:hover {
      background: #0369a1;
    }

    /* Full-width Calendar Grid */
    .full-calendar-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
    }
    @media (max-width: 1200px) {
      .full-calendar-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 768px) {
      .full-calendar-grid { grid-template-columns: 1fr; }
    }

    .cal-col {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .cal-col-header {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      padding: 10px 12px;
      text-align: center;
    }
    .cal-col-day {
      font-size: 0.95rem;
      font-weight: 700;
      color: white;
    }
    .cal-col-sub {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .cal-col-body {
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex: 1;
    }

    .slot-box {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 12px;
      transition: all 0.2s;
      position: relative;
    }
    .slot-box:hover { border-color: #475569; }
    .slot-time-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 5px;
    }
    .slot-time-title {
      font-size: 0.75rem;
      font-weight: 700;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .slot-tech-avail {
      font-size: 0.72rem;
      color: #38bdf8;
      font-weight: 600;
    }

    .slot-actions {
      display: flex;
      gap: 6px;
      margin-top: 8px;
    }
    .btn-slot-act {
      flex: 1;
      padding: 4px 8px;
      border-radius: 5px;
      font-size: 0.7rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      text-align: center;
    }
    .btn-slot-book { background: #0284c7; color: white; }
    .btn-slot-book:hover { background: #0369a1; }
    .btn-slot-block { background: #334155; color: #cbd5e1; }
    .btn-slot-block:hover { background: #475569; }

    /* Booked Routine Slot */
    .slot-box.is-booked-routine {
      background: rgba(22, 163, 74, 0.18);
      border: 1px solid #22c55e;
      box-shadow: 0 0 10px rgba(34, 197, 94, 0.2);
    }
    .slot-box.is-booked-routine .slot-time-title { color: #86efac; font-weight: 800; }
    .booked-cust-name { font-size: 0.88rem; font-weight: 700; color: white; margin-bottom: 2px; }
    .booked-cust-meta { font-size: 0.75rem; color: #dcfce7; line-height: 1.3; }

    /* Booked Emergency Slot */
    .slot-box.is-booked-emergency {
      background: rgba(220, 38, 38, 0.25);
      border: 1px solid #ef4444;
      box-shadow: 0 0 15px rgba(239, 68, 68, 0.35);
      animation: pulse 1.8s infinite;
    }
    .slot-box.is-booked-emergency .slot-time-title { color: #fca5a5; font-weight: 800; }
    .booked-emerg-meta { font-size: 0.75rem; color: #fee2e2; line-height: 1.3; }

    /* Blocked Slot */
    .slot-box.is-blocked {
      background: repeating-linear-gradient(
        45deg,
        #1e293b,
        #1e293b 10px,
        #0f172a 10px,
        #0f172a 20px
      );
      border: 1px dashed #64748b;
      opacity: 0.7;
    }
    .slot-box.is-blocked .slot-time-title { color: #94a3b8; }
    .blocked-label { font-size: 0.75rem; color: #cbd5e1; font-weight: 600; margin: 4px 0; }

    /* VIEW 3: TECHNICIAN FLEET MANAGEMENT */
    .fleet-kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 20px;
    }
    @media (max-width: 900px) {
      .fleet-kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
    .kpi-card {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px 20px;
    }
    .kpi-label { font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; }
    .kpi-val { font-size: 1.45rem; font-weight: 800; color: white; margin-top: 4px; }
    .kpi-sub { font-size: 0.75rem; color: var(--accent); margin-top: 2px; }

    .fleet-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .fleet-header-row h2 { font-size: 1.15rem; font-weight: 700; }
    .btn-add-electrician {
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      color: white;
      border: none;
      padding: 9px 16px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }
    .btn-add-electrician:hover { opacity: 0.95; transform: translateY(-1px); }

    .fleet-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 18px;
    }
    .tech-card-pro {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      transition: all 0.2s;
    }
    .tech-card-pro:hover {
      border-color: #475569;
      transform: translateY(-2px);
    }
    .tech-card-pro.is-on-call-glow {
      border-color: #22c55e;
      box-shadow: 0 0 15px rgba(34, 197, 94, 0.15);
    }
    .tech-card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }
    .tech-avatar {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: #0f172a;
      border: 2px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--accent);
      flex-shrink: 0;
    }
    .tech-main-info { flex: 1; }
    .tech-full-name { font-size: 1.02rem; font-weight: 700; color: white; }
    .tech-license-tag {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      margin-top: 3px;
    }
    .license-master { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .license-journeyman { background: rgba(2, 132, 199, 0.2); color: #38bdf8; border: 1px solid rgba(2, 132, 199, 0.4); }
    .license-ev { background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }
    .license-service { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }

    .btn-toggle-oncall {
      width: 100%;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn-toggle-oncall.is-active {
      background: rgba(34, 197, 94, 0.2);
      border: 1px solid #22c55e;
      color: #86efac;
    }
    .btn-toggle-oncall.is-active:hover { background: rgba(34, 197, 94, 0.3); }
    .btn-toggle-oncall.is-off {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: #94a3b8;
    }
    .btn-toggle-oncall.is-off:hover { background: #334155; color: white; }

    .tech-details-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 0.78rem;
      color: var(--text-muted);
    }
    .tech-specialties-wrap {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin-top: 4px;
    }
    .spec-pill {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: #cbd5e1;
      font-size: 0.68rem;
      padding: 3px 7px;
      border-radius: 4px;
    }

    .tech-card-bottom {
      display: flex;
      gap: 8px;
      margin-top: auto;
      border-top: 1px solid var(--card-border);
      padding-top: 10px;
    }
    .btn-tech-act {
      flex: 1;
      padding: 6px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--card-border);
      background: #0f172a;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }
    .btn-tech-act:hover { background: #334155; }
    .btn-tech-del {
      flex: 0 0 32px;
      color: #f87171;
    }
    .btn-tech-del:hover { background: rgba(220, 38, 38, 0.2); border-color: #dc2626; }

    /* Modals */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.78);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
    }
    .modal-overlay.active { display: flex; }
    .modal-card {
      background: #1e293b;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      width: 100%;
      max-width: 500px;
      padding: 22px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
      animation: fadeIn 0.2s ease;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
    }
    .modal-header h3 { font-size: 1.05rem; font-weight: 700; color: white; }
    .modal-close {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 1.4rem;
      cursor: pointer;
      line-height: 1;
    }
    .modal-body label {
      display: block;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      margin-bottom: 4px;
      margin-top: 10px;
    }
    .modal-body input[type="text"], .modal-body input[type="email"], .modal-body select, .modal-body textarea {
      width: 100%;
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.88rem;
      outline: none;
      box-sizing: border-box;
      font-family: inherit;
    }
    .btn-modal-submit {
      width: 100%;
      background: #0284c7;
      color: white;
      border: none;
      padding: 11px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.9rem;
      margin-top: 16px;
      cursor: pointer;
    }
    .btn-modal-submit:hover { background: #0369a1; }

    /* ROI Calculator Modal Sliders */
    .slider-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 12px;
    }
    .slider-label { font-size: 0.82rem; font-weight: 600; color: white; }
    .slider-val { font-size: 0.95rem; font-weight: 800; color: var(--accent); }
    input[type=range] {
      width: 100%;
      margin: 6px 0;
      accent-color: var(--primary);
    }
    .roi-result-banner {
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(15, 23, 42, 0.8));
      border: 2px solid #10b981;
      border-radius: 10px;
      padding: 16px;
      margin-top: 16px;
      text-align: center;
    }
    .roi-gain-val {
      font-size: 1.8rem;
      font-weight: 900;
      color: #34d399;
      margin: 4px 0;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    footer {
      background: #0f172a;
      border-top: 1px solid var(--card-border);
      padding: 12px 24px;
      text-align: center;
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: auto;
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
          <span style="background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid rgba(34,197,94,0.3); font-size:0.68rem; font-weight:700; padding:2px 8px; border-radius:10px;">● LIVE DEMO MODE</span>
        </div>
        <p>AI Emergency Triage, Autonomous Scheduling & Fleet Control for Electrical Contractors</p>
      </div>
    </div>
    <div class="header-actions">
      <button class="btn-hdr-action btn-hdr-guide" onclick="openPitchModal()">
        💡 Sales Pitch & Demo Guide
      </button>
      <button class="btn-hdr-action btn-hdr-twilio" onclick="openTwilioModal()">
        📞 Connect Real Phone Number
      </button>
      <div class="contractor-bar">
        <label>Contractor Email:</label>
        <input type="email" id="contractorEmail" value="sean.glenn21@gmail.com" placeholder="contractor@domain.com">
        <button class="btn-hdr-action" onclick="saveContractorEmail()">Set Client</button>
      </div>
    </div>
  </header>

  <!-- EXECUTIVE REVENUE & ROI COMMAND BAR -->
  <div class="revenue-kpi-bar">
    <div class="rev-metrics-wrap">
      <!-- KPI 1: Pipeline Revenue -->
      <div class="rev-metric-card has-tooltip">
        <div class="rev-label-row">
          <span class="rev-label">Pipeline Revenue Captured</span>
          <span class="info-icon">ℹ️</span>
        </div>
        <span class="rev-val val-green" id="kpiPipelineRev">$2,450</span>
        <span class="rev-subtext">⚡ Booked Service Value Won</span>
        <div class="tooltip-text">
          <strong>Pipeline Revenue Captured:</strong><br>
          Total estimated value of jobs booked directly into your schedule by Sarah AI without a human dispatcher (e.g. Panel Upgrades $3,200, Emergencies $1,850, EV Chargers $1,450).
        </div>
      </div>

      <!-- KPI 2: Upfront Fees -->
      <div class="rev-metric-card has-tooltip">
        <div class="rev-label-row">
          <span class="rev-label">Diagnostic Fees Collected</span>
          <span class="info-icon">ℹ️</span>
        </div>
        <span class="rev-val val-gold" id="kpiFeesCol">$0</span>
        <span class="rev-subtext" id="kpiFeesSubtext">💳 Upfront Stripe Deposits</span>
        <div class="rev-action-hint">👉 Click "Authorize Fee" on phone to test</div>
        <div class="tooltip-text">
          <strong>Diagnostic Fees Collected:</strong><br>
          Upfront deposits ($89 routine / $199 emergency) authorized via customer SMS Stripe checkout. Eliminates the industry 22% no-show rate.
        </div>
      </div>

      <!-- KPI 3: Missed Calls -->
      <div class="rev-metric-card has-tooltip">
        <div class="rev-label-row">
          <span class="rev-label">Missed Calls Recovered</span>
          <span class="info-icon">ℹ️</span>
        </div>
        <span class="rev-val" id="kpiMissedRec">2 Recovered</span>
        <span class="rev-subtext">📵 Automated 3s Text-Back</span>
        <div class="rev-action-hint">👉 Click "Simulate Missed Call"</div>
        <div class="tooltip-text">
          <strong>Missed Calls Recovered:</strong><br>
          Callers who hung up before leaving a voicemail, instantly saved within 3 seconds via automated SMS with self-service booking link.
        </div>
      </div>

      <!-- KPI 4: Answer Speed -->
      <div class="rev-metric-card has-tooltip">
        <div class="rev-label-row">
          <span class="rev-label">Zero-Miss Answer Speed</span>
          <span class="info-icon">ℹ️</span>
        </div>
        <span class="rev-val" style="color:#a78bfa;">0.8s (Ring 1)</span>
        <span class="rev-subtext">📞 24/7 Live Carrier Answer</span>
        <div class="tooltip-text">
          <strong>Zero-Miss Answer Speed:</strong><br>
          Live carrier pickup latency via Twilio TwiML. Sarah answers on Ring 1 (24/7/365) before customers hang up and dial your competitors.
        </div>
      </div>
    </div>

    <button class="btn-roi-calc" onclick="openRoiModal()">
      📊 Interactive ROI Calculator
    </button>
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
          <div class="step-body">Sarah triages NFPA 70E electrical hazards (burning smells/sparks) or quotes EV chargers/panels 24/7/365.</div>
          <div class="step-hint">👉 Click to test: <strong>🚨 Burning Rubber Emergency</strong></div>
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
            <span>📞</span> <strong>Step 1: Inbound Call Simulator</strong> — What homeowner hears. Click a scenario to test Sarah's response.
          </div>

          <div class="scenario-triggers">
            <button class="scenario-btn btn-emergency" onclick="runScenario('emergency')">
              <span class="btn-title">🚨 Burning Rubber Emergency</span>
              <span class="btn-sub">Level 2 Hazard • 45m Code Red</span>
            </button>
            <button class="scenario-btn btn-routine" onclick="runScenario('ev_charger')">
              <span class="btn-title">⚡ Tesla EV Charger Quote</span>
              <span class="btn-sub">50A Circuit • Daytime Booking</span>
            </button>
            <button class="scenario-btn btn-missed" onclick="simulateMissedCallLead()">
              <span class="btn-title">📵 Simulate Missed Call</span>
              <span class="btn-sub">Hang-Up • Instant 3s Text Back</span>
            </button>
            <button class="scenario-btn btn-reset" onclick="resetCall()">
              <span class="btn-title">🔄 Reset</span>
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
            <span style="font-size: 0.8rem; color: var(--accent); font-weight: 600;">Real-Time Feed</span>
          </div>
          <div class="panel-subhead">
            <span>⚡</span> <strong>Step 2: Contractor Cockpit</strong> — Real-time ticket details, address, assigned technician, and 1-click Google Calendar sync.
          </div>

          <div class="cockpit-body">
            <!-- Magic Moment Hero Card -->
            <div class="dispatch-hero" id="dispatchHero">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span class="hero-badge badge-standard" id="heroBadge">Confirmed Dispatch</span>
                <span id="heroPayBadge" style="font-size:0.75rem; font-weight:700; color:#fbbf24; background:rgba(245,158,11,0.2); padding:3px 8px; border-radius:4px; border:1px solid rgba(245,158,11,0.4);">
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
                <tr><td>Est. Pipeline Value:</td><td id="tktVal" style="color:#4ade80; font-weight:700;">-</td></tr>
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
                👈 <strong>Try It Live:</strong> Click <strong>"🚨 Burning Rubber Emergency"</strong> on the left to generate a live ticket!
              </div>
            </div>
          </div>
        </div>

        <!-- Col 3: Customer Smartphone Simulator Widget -->
        <div class="phone-column-wrap">
          <div class="phone-container">
            <div class="phone-notch">
              <div class="notch-speaker"></div>
              <div class="notch-camera"></div>
            </div>
            <div class="phone-header">
              <div class="phone-header-title">Customer Smartphone (Live SMS)</div>
              <div class="phone-header-sub">ZeroMiss Automated Dispatch</div>
            </div>
            <div class="panel-subhead" style="margin:-10px -12px 10px; font-size:0.68rem; padding:4px 8px;">
              <span>📱</span> <strong>Step 3: Homeowner SMS</strong> — Live text with 1-click Stripe deposit link.
            </div>

            <div class="phone-messages" id="phoneMessages">
              <div class="sms-bubble">
                <div class="sms-tag">ZeroMiss 24/7 Dispatch</div>
                Welcome! When Sarah books your electrical appointment, your instant SMS confirmation & Stripe diagnostic fee checkout link will land right here.
                <div style="margin-top:6px; font-size:0.72rem; color:#38bdf8; font-weight:600;">
                  👉 Try it: Click a demo call on the left, then click "Authorize Fee" here!
                </div>
              </div>
            </div>

            <div style="font-size:0.68rem; color:#64748b; text-align:center; margin-top:8px;">
              Simulating Real-Time Customer Cellular Feed
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: FLEET DISPATCH CALENDAR -->
    <div class="tab-view" id="viewCalendar">
      <!-- Calendar Explainer Banner -->
      <div class="panel-subhead" style="border-radius:10px; margin-bottom:14px; background:#1e293b; padding:10px 16px;">
        <span style="font-size:1.2rem;">ℹ️</span>
        <div>
          <strong>Live Master Fleet Dispatch Schedule:</strong> Every service call booked by Sarah AI or created manually syncs here in real-time across morning, afternoon, and evening windows. Electricians and dispatchers can subscribe via Google Calendar, Apple Calendar, or Outlook using the iCal feed. Click <strong>"🚫 Block"</strong> to take technicians off-duty, or <strong>"+ Book Job"</strong> for manual walk-ins.
        </div>
      </div>

      <!-- Calendar Legend -->
      <div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap; margin-bottom:14px; padding:0 4px; font-size:0.75rem;">
        <span style="color:var(--text-muted); font-weight:700; text-transform:uppercase;">Color Legend:</span>
        <span style="display:flex; align-items:center; gap:6px; color:#f87171;"><span style="width:10px; height:10px; background:#dc2626; border-radius:3px; display:inline-block;"></span> 🚨 Emergency Code Red (45-60m Priority)</span>
        <span style="display:flex; align-items:center; gap:6px; color:#38bdf8;"><span style="width:10px; height:10px; background:#0284c7; border-radius:3px; display:inline-block;"></span> ⚡ Scheduled Routine Dispatch</span>
        <span style="display:flex; align-items:center; gap:6px; color:#94a3b8;"><span style="width:10px; height:10px; background:#0f172a; border:1px solid #475569; border-radius:3px; display:inline-block;"></span> 🟢 Available Open Slot</span>
        <span style="display:flex; align-items:center; gap:6px; color:#cbd5e1;"><span style="width:10px; height:10px; background:#334155; border-radius:3px; display:inline-block;"></span> 🚫 Blocked / Off-Duty (Personal Time)</span>
      </div>

      <div class="cal-controls-bar">
        <div class="cal-controls-left">
          <label>Filter Electrician:</label>
          <select id="calTechFilter" onchange="renderCalendar()">
            <option value="ALL">⚡ All Electricians (Full Fleet)</option>
          </select>
        </div>

        <div class="sync-actions">
          <span style="font-size:0.8rem; color:#4ade80; display:flex; align-items:center; gap:6px; font-weight:600;">
            <span class="status-dot"></span> Google Calendar Sync Active
          </span>
          <button class="btn-cal-action" onclick="copyIcalFeedUrl()" title="Copy live subscription URL for Google Calendar or iPhone">
            📋 Copy Calendar Feed URL
          </button>
          <a href="/api/calendar.ics" class="btn-cal-action" download="zeromiss_schedule.ics">
            📥 Export Company .ICS
          </a>
          <a href="https://calendar.google.com" target="_blank" class="btn-cal-action btn-cal-primary">
            📅 Open Google Calendar
          </a>
        </div>
      </div>

      <!-- 5-Day Dispatch Calendar Grid -->
      <div class="full-calendar-grid" id="fullCalendarGrid">
        <!-- Rendered dynamically by renderCalendar() -->
      </div>
    </div>

    <!-- TAB 3: ELECTRICIAN FLEET MANAGEMENT -->
    <div class="tab-view" id="viewFleet">
      <!-- Fleet Explainer Banner -->
      <div class="panel-subhead" style="border-radius:10px; margin-bottom:14px; background:#1e293b; padding:10px 16px;">
        <span style="font-size:1.2rem;">ℹ️</span>
        <div>
          <strong>Electrician Fleet Roster & 24/7 Emergency On-Call Routing:</strong> Sarah AI matches inbound service inquiries to certified technicians by license and specialty. The technician toggled <strong>"🟢 ON-CALL TONIGHT"</strong> is automatically dispatched for after-hours emergency electrical hazards.
        </div>
      </div>

      <div class="fleet-kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Active Electricians</div>
          <div class="kpi-val" id="kpiFleetCount">4</div>
          <div class="kpi-sub">Fully Licensed & Vetted</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Emergency On-Call Lead</div>
          <div class="kpi-val" id="kpiOnCallLead" style="font-size:1.15rem; color:#f87171;">Marcus Vance</div>
          <div class="kpi-sub">24/7 Priority Emergency Lead</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Scheduled Dispatches</div>
          <div class="kpi-val" id="kpiBookingsCount">0</div>
          <div class="kpi-sub">Live Active Service Calls</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Fleet Safety Rating</div>
          <div class="kpi-val" style="color:#fbbf24;">4.96 ★</div>
          <div class="kpi-sub">NFPA 70E Certified</div>
        </div>
      </div>

      <div class="fleet-header-row">
        <h2>⚡ Active Electrician Fleet Roster</h2>
        <button class="btn-add-electrician" onclick="openAddTechModal()">
          + Add New Electrician
        </button>
      </div>

      <div class="fleet-cards-grid" id="fleetCardsGrid">
        <!-- Rendered dynamically by renderFleetView() -->
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
      <div class="modal-body" style="font-size:0.83rem; line-height:1.5; color:#cbd5e1; max-height: 70vh; overflow-y:auto;">
        <div style="background:#0f172a; border:1px solid rgba(56,189,248,0.3); border-radius:8px; padding:12px; margin-bottom:14px;">
          <strong style="color:#38bdf8; font-size:0.9rem;">🎯 The Core Pitch to Electrical Contractors:</strong>
          <p style="margin-top:6px; color:#e2e8f0;">
            "35% of homeowner electrical calls happen after 5:00 PM or on weekends. 80% of callers who reach a voicemail hang up and call the next electrician on Google. That is <strong>$150,000+ in lost revenue</strong> every year. ZeroMiss answers on Ring 1 with conversational AI, triages NFPA 70E hazards, books the job directly into your calendar, and collects an upfront diagnostic fee via SMS to eliminate no-shows."
          </p>
        </div>

        <strong style="color:white; font-size:0.88rem;">🚀 5-Step Live Sales Demo Script:</strong>
        <ol style="margin-left:20px; margin-top:8px; margin-bottom:16px; display:flex; flex-direction:column; gap:8px;">
          <li>
            <strong style="color:#f87171;">Simulate an Emergency:</strong> Click <strong>"🚨 Burning Rubber Emergency"</strong> on the left. Listen to Sarah give NFPA 70E safety instructions and dispatch a 45-min Code Red electrician.
          </li>
          <li>
            <strong style="color:#38bdf8;">Review Contractor Cockpit:</strong> Point out the Center Cockpit. Show the contractor their real-time lead ticket, address, and the 1-click Google Calendar button.
          </li>
          <li>
            <strong style="color:#a78bfa;">Inspect the Smartphone Simulator:</strong> Point to the phone on the right. Show the instant customer SMS confirmation with the Stripe diagnostic deposit link.
          </li>
          <li>
            <strong style="color:#34d399;">Simulate Fee Collection:</strong> Click <strong>"💳 Authorize $199 via Stripe"</strong> on the phone. Watch the status turn to "PAID_VERIFIED" and explain how collecting $89/$199 upfront eliminates contractor no-shows.
          </li>
          <li>
            <strong style="color:#fbbf24;">Show Calendar & Fleet:</strong> Switch to the <strong>"Fleet Calendar"</strong> tab to show the master board and Google Calendar iCal feed export.
          </li>
        </ol>

        <div style="background:#0f172a; border:1px solid #10b981; border-radius:8px; padding:12px; margin-bottom:14px;">
          <strong style="color:#34d399;">💰 The ROI Equation (Proven Math):</strong>
          <p style="margin-top:4px; font-size:0.78rem; color:#cbd5e1;">
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
          <div style="font-size:0.8rem; color:#86efac; font-weight:700; text-transform:uppercase;">
            Projected Annual Recovered Revenue Gain
          </div>
          <div class="roi-gain-val" id="roiAnnualGain">+$148,176 / yr</div>
          <div style="font-size:0.75rem; color:#cbd5e1;" id="roiBreakdown">
            Based on 17 after-hours calls saved/mo @ 62% recovery rate
          </div>
        </div>

        <button class="btn-modal-submit" onclick="closeRoiModal()">Apply to Dashboard</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Twilio / Carrier Live Phone Line Setup Wizard -->
  <div class="modal-overlay" id="twilioModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>📞 Connect Real Phone Number (Twilio Live Carrier)</h3>
        <button class="modal-close" onclick="closeTwilioModal()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="font-size:0.82rem; color:var(--text-muted); margin-bottom:12px;">
          Point any Twilio, Telnyx, or carrier phone number directly to Sarah. When anyone dials the number from a cell phone, Sarah will answer on Ring 1!
        </p>

        <label>Your Live Production Webhook URL (HTTP POST):</label>
        <div style="display:flex; gap:6px; margin-top:4px;">
          <input type="text" id="twilioUrlInput" value="https://zeromissdispatch.com/api/twilio/voice" readonly>
          <button class="btn-cal-action" onclick="copyTwilioWebhook()" style="white-space:nowrap;">📋 Copy</button>
        </div>

        <div style="background:#0f172a; border:1px solid var(--card-border); border-radius:8px; padding:12px; margin-top:14px; font-size:0.8rem; line-height:1.5;">
          <strong>⚡ 3-Click Setup Instructions:</strong>
          <ol style="margin-left:18px; margin-top:6px; color:var(--text-muted);">
            <li>Log into your <strong>Twilio Console</strong> &gt; Phone Numbers.</li>
            <li>Click on your phone number &gt; scroll to <strong>Voice & Fax</strong>.</li>
            <li>Paste the URL above into <strong>"A Call Comes In"</strong> (Webhook: <code>HTTP POST</code>). Click Save!</li>
          </ol>
        </div>

        <button class="btn-modal-submit" onclick="closeTwilioModal()">Done</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Add / Edit Technician -->
  <div class="modal-overlay" id="techModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="techModalTitle">⚡ Add Electrician to Dispatch Fleet</h3>
        <button class="modal-close" onclick="closeAddTechModal()">&times;</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="editTechId" value="">
        <label>Electrician Full Name</label>
        <input type="text" id="newTechName" placeholder="e.g. Jason Miller">

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          <div>
            <label>License / Role</label>
            <select id="newTechLicense">
              <option value="Master Electrician">Master Electrician</option>
              <option value="Journeyman Electrician" selected>Journeyman Electrician</option>
              <option value="EV & Solar Specialist">EV & Solar Specialist</option>
              <option value="Service Electrician">Service Electrician</option>
              <option value="Apprentice Helper">Apprentice Helper</option>
            </select>
          </div>
          <div>
            <label>Mobile Phone (for SMS / Dial)</label>
            <input type="text" id="newTechPhone" placeholder="(555) 019-3388">
          </div>
        </div>

        <label>24/7 On-Call Status</label>
        <select id="newTechOnCall">
          <option value="true">🟢 ON-CALL TONIGHT (Dispatched for Emergencies)</option>
          <option value="false" selected>⚪ Standard Daytime Shift</option>
        </select>

        <label>Specialties Covered</label>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:0.8rem; margin-top:4px;">
          <label style="text-transform:none; font-weight:normal; display:flex; align-items:center; gap:6px;"><input type="checkbox" id="specEmerg" checked> 24/7 Emergencies</label>
          <label style="text-transform:none; font-weight:normal; display:flex; align-items:center; gap:6px;"><input type="checkbox" id="specEV" checked> EV Chargers</label>
          <label style="text-transform:none; font-weight:normal; display:flex; align-items:center; gap:6px;"><input type="checkbox" id="specPanel" checked> 200A Panels</label>
          <label style="text-transform:none; font-weight:normal; display:flex; align-items:center; gap:6px;"><input type="checkbox" id="specLighting" checked> Lighting & Repairs</label>
        </div>

        <button class="btn-modal-submit" onclick="submitTechForm()">Save Electrician & Sync Schedule</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Manual Slot Booking -->
  <div class="modal-overlay" id="manualBookModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>⚡ Book Appointment in Schedule Slot</h3>
        <button class="modal-close" onclick="closeManualBookModal()">&times;</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="mbSlotId" value="">
        <div style="font-size:0.85rem; color:#38bdf8; margin-bottom:10px;" id="mbSlotSummary">
          Slot: 2026-11-04 (Morning: 08:00 AM - 12:00 PM)
        </div>

        <label>Customer Full Name</label>
        <input type="text" id="mbCustName" placeholder="e.g. Robert Smith">

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          <div>
            <label>Callback Phone</label>
            <input type="text" id="mbPhone" placeholder="(555) 019-4455">
          </div>
          <div>
            <label>Email (for Google Calendar)</label>
            <input type="email" id="mbEmail" placeholder="client@gmail.com">
          </div>
        </div>

        <label>Service Address</label>
        <input type="text" id="mbAddress" placeholder="e.g. 742 Evergreen Terrace">

        <label>Scope of Work / Issue Description</label>
        <textarea id="mbIssue" rows="2" placeholder="e.g. Tripping breaker in kitchen or Tesla charger installation"></textarea>

        <button class="btn-modal-submit" onclick="submitManualBooking()">Confirm Dispatch & Sync Google Calendar</button>
      </div>
    </div>
  </div>

  <footer>
    ZeroMiss Voice Dispatch System | Enterprise Gemini 2.0 Flash Agent | Fully Compliant with NFPA 70E Safety Standards
  </footer>

  <script>
    const chatStream = document.getElementById('chatStream');
    const userInput = document.getElementById('userInput');
    const audioBar = document.getElementById('audioBar');
    const contractorInput = document.getElementById('contractorEmail');
    const dispatchHero = document.getElementById('dispatchHero');
    const waitingPlaceholder = document.getElementById('waitingPlaceholder');
    const phoneMessages = document.getElementById('phoneMessages');

    let BOARD_DATA = { technicians: [], slots: [], bookings: [], roi_metrics: {} };

    // Tab Switching
    function switchPortalTab(tabKey) {
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

    // Speech synthesis
    function speakText(text) {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      audioBar.classList.add('speaking');

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang.includes('en') && (v.name.includes('Samantha') || v.name.includes('Google') || v.name.includes('Female')));
      if (preferred) utterance.voice = preferred;

      utterance.onend = () => audioBar.classList.remove('speaking');
      utterance.onerror = () => audioBar.classList.remove('speaking');
      window.speechSynthesis.speak(utterance);
    }

    function appendMessage(sender, text, isSarah = false) {
      const bubble = document.createElement('div');
      bubble.className = `bubble ${isSarah ? 'bubble-sarah' : 'bubble-user'}`;
      bubble.innerHTML = `
        <div class="speaker-name">${isSarah ? 'Sarah (ZeroMiss Dispatcher)' : 'Customer'}</div>
        ${text}
      `;
      chatStream.appendChild(bubble);
      chatStream.scrollTop = chatStream.scrollHeight;
    }

    async function sendUserMessage() {
      const text = userInput.value.trim();
      if (!text) return;
      userInput.value = '';
      appendMessage('Customer', text, false);

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        appendMessage('Sarah', data.response, true);
        speakText(data.response);

        if (data.booking) {
          showBookingInHero(data.booking);
          pushCustomerSmsBooking(data.booking);
        }
        await fetchBoardData();
      } catch (err) {
        appendMessage('Sarah', 'Dispatch connection temporarily unavailable. Please retry.', true);
      }
    }

    function showBookingInHero(b) {
      waitingPlaceholder.style.display = 'none';
      dispatchHero.classList.add('active');

      const isEmerg = (b.urgency_level || '').includes('EMERG');
      const badge = document.getElementById('heroBadge');
      badge.className = `hero-badge ${isEmerg ? 'badge-emergency' : 'badge-standard'}`;
      badge.innerText = isEmerg ? '🚨 EMERGENCY CODE RED' : '⚡ SCHEDULED DISPATCH';

      document.getElementById('heroTitle').innerText = `${b.customer_name} @ ${b.service_address}`;
      document.getElementById('heroContractor').innerText = b.contractor_email;

      const calBtn = document.getElementById('heroCalBtn');
      calBtn.href = b.contractor_calendar_link || b.google_calendar_link;

      document.getElementById('tktConf').innerText = b.confirmation_id;
      document.getElementById('tktCustomer').innerText = b.customer_name;
      document.getElementById('tktPhone').innerText = b.phone_number;
      document.getElementById('tktAddress').innerText = b.service_address;
      document.getElementById('tktTech').innerText = b.assigned_technician;
      document.getElementById('tktWindow').innerText = `${b.slot_date} (${b.slot_time})`;
      document.getElementById('tktFee').innerText = b.dispatch_fee === 0 ? 'Free On-Site Estimate' : `$${b.dispatch_fee.toFixed(0)} Diagnostic Fee`;

      const estVal = b.estimated_job_value || (isEmerg ? 1850 : 850);
      document.getElementById('tktVal').innerText = `$${estVal.toLocaleString()}`;

      const payBadge = document.getElementById('heroPayBadge');
      if (b.payment_status === 'PAID_VERIFIED') {
        payBadge.style.color = '#86efac';
        payBadge.style.background = 'rgba(34,197,94,0.2)';
        payBadge.style.borderColor = 'rgba(34,197,94,0.4)';
        payBadge.innerText = '✓ FEE PAID & GUARANTEED (Stripe)';
      } else {
        payBadge.style.color = '#fbbf24';
        payBadge.style.background = 'rgba(245,158,11,0.2)';
        payBadge.style.borderColor = 'rgba(245,158,11,0.4)';
        payBadge.innerText = '💳 Pending Fee Authorization';
      }
    }

    // Push SMS to Simulated Customer Phone
    function pushCustomerSmsBooking(b) {
      const isEmerg = (b.urgency_level || '').includes('EMERG');
      const fee = b.dispatch_fee || (isEmerg ? 199 : 89);
      const conf = b.confirmation_id;

      const smsHtml = `
        <div class="sms-bubble">
          <div class="sms-tag">⚡ ZeroMiss Dispatch Confirmation</div>
          Hi ${b.customer_name}! Your electrical service call is confirmed with <strong>${b.assigned_technician.split('(')[0].trim()}</strong> for ${b.slot_date} (${b.slot_time}). Ref: ${conf}.
          <div class="sms-stripe-box">
            <div style="font-size:0.7rem; color:var(--text-muted);">Secure Diagnostic Fee Authorization:</div>
            <button class="btn-sms-pay" id="btnPay_${conf}" onclick="authorizeStripeFee('${conf}', ${fee})">
              💳 Authorize $${fee} via Stripe
            </button>
          </div>
        </div>
      `;
      phoneMessages.innerHTML += smsHtml;
      phoneMessages.scrollTop = phoneMessages.scrollHeight;
    }

    // Authorize Stripe Fee Mock
    async function authorizeStripeFee(confId, amount) {
      const btn = document.getElementById(`btnPay_${confId}`);
      if (btn) {
        btn.innerText = 'Processing...';
      }

      try {
        const res = await fetch('/api/bookings/pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation_id: confId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          if (btn) {
            btn.className = 'btn-sms-pay paid';
            btn.innerText = `✓ Paid $${amount} (Stripe Verified)`;
          }
          alert(`⚡ Payment Authorized! $${amount} collected. Ticket ${confId} is 100% guaranteed. No-show eliminated!`);
          await fetchBoardData();
          if (BOARD_DATA.bookings) {
            const b = BOARD_DATA.bookings.find(bk => bk.confirmation_id === confId);
            if (b) showBookingInHero(b);
          }
        }
      } catch (e) {
        alert('Payment error.');
      }
    }

    // Simulate Missed Call Lead Recovery
    async function simulateMissedCallLead() {
      try {
        const res = await fetch('/api/simulate-missed-call', { method: 'POST' });
        const data = await res.json();

        const smsHtml = `
          <div class="sms-bubble" style="border-color:#8b5cf6;">
            <div class="sms-tag" style="color:#c084fc;">⚡ Automated Lead Recovery (0s Delay)</div>
            Hi! This is Sarah from ZeroMiss Electrical Dispatch. We noticed you called! To lock in the earliest electrician slot right now, click here:
            <div style="margin-top:6px; font-weight:700; color:#38bdf8; cursor:pointer;" onclick="runScenario('ev_charger')">
              👉 book.zeromissdispatch.com/self-schedule
            </div>
          </div>
        `;
        phoneMessages.innerHTML += smsHtml;
        phoneMessages.scrollTop = phoneMessages.scrollHeight;

        appendMessage('Sarah (SMS Lead Recovery)', '⚡ [AUTOMATED TEXT-BACK FIRED]: Missed after-hours call intercepted within 3 seconds. Self-service booking link dispatched.', true);
        await fetchBoardData();
      } catch (e) {
        alert('Error.');
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

    // Fetch Board Data
    async function fetchBoardData() {
      try {
        const res = await fetch('/api/board');
        const data = await res.json();
        BOARD_DATA = data;

        // Update pills
        const bookingsCount = (data.bookings || []).length;
        const techsCount = (data.technicians || []).length;
        document.getElementById('calCountPill').innerText = `${bookingsCount} Booking${bookingsCount === 1 ? '' : 's'}`;
        document.getElementById('techCountPill').innerText = `${techsCount} Active`;

        // Update KPIs
        document.getElementById('kpiFleetCount').innerText = techsCount;
        document.getElementById('kpiBookingsCount').innerText = bookingsCount;
        const onCallTech = (data.technicians || []).find(t => t.is_on_call);
        document.getElementById('kpiOnCallLead').innerText = onCallTech ? onCallTech.name : 'None Assigned';

        // Update Executive Revenue Bar
        const roi = data.roi_metrics || {};
        const pipeline = roi.total_pipeline_revenue || 2450;
        document.getElementById('kpiPipelineRev').innerText = `$${pipeline.toLocaleString()}`;
        const fees = roi.fees_collected || 0;
        document.getElementById('kpiFeesCol').innerText = `$${fees.toLocaleString()}`;
        const feeSub = document.getElementById('kpiFeesSubtext');
        if (feeSub) {
          feeSub.innerText = fees > 0 ? '✓ Verified Deposits Captured!' : '💳 Upfront Stripe Deposits';
        }
        document.getElementById('kpiMissedRec').innerText = `${roi.missed_recovered || 2} Recovered`;

        // Update tech filter dropdown in calendar
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
                  <span style="font-size:0.7rem; color:#fecaca; font-weight:700;">Within 45-60 Min</span>
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
                  <span class="slot-time-title">⚡ ${w.label} (Booked)</span>
                  <span style="font-size:0.7rem; color:#86efac; font-weight:700;">${b.confirmation_id}</span>
                </div>
                <div class="booked-cust-name">${b.customer_name}</div>
                <div class="booked-cust-meta">
                  📍 ${b.service_address}<br>
                  👷 ${b.assigned_technician.split('(')[0].trim()} • ${b.phone_number}
                </div>
              </div>
            `;
          }

          const matchSlot = filteredSlots.find(s => s.date === dt && s.time_window.includes(w.key));
          if (!matchSlot) {
            return `
              <div class="slot-box" style="opacity:0.5;">
                <div class="slot-time-header">
                  <span class="slot-time-title">${w.label}</span>
                  <span style="font-size:0.7rem; color:#64748b;">Not Scheduled</span>
                </div>
              </div>
            `;
          }

          if (matchSlot.is_blocked) {
            return `
              <div class="slot-box is-blocked">
                <div class="slot-time-header">
                  <span class="slot-time-title">${w.label}</span>
                  <span style="font-size:0.7rem; color:#cbd5e1;">Off-Duty</span>
                </div>
                <div class="blocked-label">🚫 ${matchSlot.blocked_reason || 'Blocked Slot'}</div>
                <div class="slot-actions">
                  <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${matchSlot.slot_id}')">
                    ✓ Unblock Slot
                  </button>
                </div>
              </div>
            `;
          }

          return `
            <div class="slot-box">
              <div class="slot-time-header">
                <span class="slot-time-title">${w.label} (${w.shortTime})</span>
                <span class="slot-tech-avail">${matchSlot.technician_name.split('(')[0].trim()}</span>
              </div>
              <div style="font-size:0.7rem; color:#94a3b8; margin-top:2px;">
                🟢 Open for Dispatch
              </div>
              <div class="slot-actions">
                <button class="btn-slot-act btn-slot-book" onclick="openManualBookModal('${matchSlot.slot_id}', '${dt}', '${w.key}', '${matchSlot.technician_name}')">
                  + Book Job
                </button>
                <button class="btn-slot-act btn-slot-block" onclick="toggleBlockSlot('${matchSlot.slot_id}')">
                  🚫 Block
                </button>
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

    function selectCalendarBooking(b) {
      if (b) {
        showBookingInHero(b);
        switchPortalTab('console');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }

    // RENDER FLEET VIEW
    function renderFleetView() {
      const grid = document.getElementById('fleetCardsGrid');
      if (!grid) return;

      const techs = BOARD_DATA.technicians || [];
      if (!techs.length) {
        grid.innerHTML = '<div style="color:var(--text-muted);">No electricians registered. Click "+ Add New Electrician" above.</div>';
        return;
      }

      grid.innerHTML = techs.map(t => {
        const initials = t.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        const specs = (t.specialties || []).map(s => s.replace(/_/g, ' '));
        const isOnCall = t.is_on_call;

        let licClass = 'license-journeyman';
        if (t.license_type.includes('Master')) licClass = 'license-master';
        else if (t.license_type.includes('EV')) licClass = 'license-ev';
        else if (t.license_type.includes('Service')) licClass = 'license-service';

        const safeObj = JSON.stringify(t).replace(/'/g, "&#39;");

        return `
          <div class="tech-card-pro ${isOnCall ? 'is-on-call-glow' : ''}">
            <div class="tech-card-top">
              <div class="tech-avatar">${initials}</div>
              <div class="tech-main-info">
                <div class="tech-full-name">${t.name}</div>
                <span class="tech-license-tag ${licClass}">${t.license_type}</span>
              </div>
            </div>

            <!-- 1-Click Interactive On-Call Toggle -->
            <button class="btn-toggle-oncall ${isOnCall ? 'is-active' : 'is-off'}" onclick="toggleTechOnCall('${t.technician_id}')">
              ${isOnCall ? '🟢 ON-CALL TONIGHT (Click to change)' : '⚪ Standard Daytime Shift (Click to make On-Call)'}
            </button>

            <div class="tech-details-list">
              <div>📞 <a href="tel:${t.phone}" style="color:var(--accent); text-decoration:none;">${t.phone}</a></div>
              <div>⭐ Rating: <strong>${t.rating || 4.95}</strong> / 5.0</div>
            </div>

            <div>
              <div style="font-size:0.72rem; color:var(--text-muted); font-weight:600; text-transform:uppercase; margin-bottom:4px;">Specialties:</div>
              <div class="tech-specialties-wrap">
                ${specs.map(sp => `<span class="spec-pill">${sp}</span>`).join('')}
              </div>
            </div>

            <div class="tech-card-bottom">
              <button class="btn-tech-act" onclick='openEditTechModal(${safeObj})'>
                ✏️ Edit
              </button>
              <button class="btn-tech-act" onclick="viewTechSchedule('${t.technician_id}')">
                📅 Schedule
              </button>
              <button class="btn-tech-act btn-tech-del" onclick="deleteTech('${t.technician_id}', '${t.name}')" title="Delete Technician">
                🗑️
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

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
        } else {
          alert('Failed to toggle on-call status: ' + data.message);
        }
      } catch (e) {
        alert('Network error communicating with server.');
      }
    }

    async function toggleBlockSlot(slotId) {
      try {
        const res = await fetch('/api/slots/toggle-block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slot_id: slotId, reason: 'Off-Duty / Maintenance' })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          await fetchBoardData();
        } else {
          alert('Failed to update slot.');
        }
      } catch (e) {
        alert('Network error.');
      }
    }

    async function deleteTech(techId, techName) {
      if (!confirm(`Are you sure you want to remove ${techName} from your dispatch fleet?`)) return;
      try {
        const res = await fetch('/api/technicians/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ technician_id: techId })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          await fetchBoardData();
        } else {
          alert('Failed to delete electrician.');
        }
      } catch (e) {
        alert('Network error.');
      }
    }

    function viewTechSchedule(techId) {
      switchPortalTab('calendar');
      document.getElementById('calTechFilter').value = techId;
      renderCalendar();
    }

    function openAddTechModal() {
      document.getElementById('techModalTitle').innerText = '⚡ Add Electrician to Dispatch Fleet';
      document.getElementById('editTechId').value = '';
      document.getElementById('newTechName').value = '';
      document.getElementById('newTechPhone').value = '';
      document.getElementById('newTechLicense').value = 'Journeyman Electrician';
      document.getElementById('newTechOnCall').value = 'false';
      document.getElementById('specEmerg').checked = true;
      document.getElementById('specEV').checked = true;
      document.getElementById('specPanel').checked = true;
      document.getElementById('specLighting').checked = true;
      document.getElementById('techModal').classList.add('active');
    }

    function openEditTechModal(tech) {
      document.getElementById('techModalTitle').innerText = `⚡ Edit Electrician: ${tech.name}`;
      document.getElementById('editTechId').value = tech.technician_id;
      document.getElementById('newTechName').value = tech.name;
      document.getElementById('newTechPhone').value = tech.phone;
      document.getElementById('newTechLicense').value = tech.license_type;
      document.getElementById('newTechOnCall').value = tech.is_on_call ? 'true' : 'false';

      const specs = tech.specialties || [];
      document.getElementById('specEmerg').checked = specs.includes('emergency') || specs.includes('24/7 Emergencies');
      document.getElementById('specEV').checked = specs.includes('ev_charger') || specs.includes('EV Chargers');
      document.getElementById('specPanel').checked = specs.includes('panel_upgrade') || specs.includes('200A Panels');
      document.getElementById('specLighting').checked = specs.includes('lighting') || specs.includes('Lighting & Repairs');

      document.getElementById('techModal').classList.add('active');
    }

    function closeAddTechModal() {
      document.getElementById('techModal').classList.remove('active');
    }

    async function submitTechForm() {
      const editId = document.getElementById('editTechId').value;
      const name = document.getElementById('newTechName').value.trim();
      if (!name) {
        alert('Please enter electrician full name.');
        return;
      }
      const license_type = document.getElementById('newTechLicense').value;
      const phone = document.getElementById('newTechPhone').value.trim() || '(555) 019-3388';
      const is_on_call = document.getElementById('newTechOnCall').value === 'true';

      const specialties = [];
      if (document.getElementById('specEmerg').checked) specialties.push('emergency');
      if (document.getElementById('specEV').checked) specialties.push('ev_charger');
      if (document.getElementById('specPanel').checked) specialties.push('panel_upgrade');
      if (document.getElementById('specLighting').checked) specialties.push('lighting');

      const endpoint = editId ? '/api/technicians/update' : '/api/technicians';
      const payload = {
        technician_id: editId,
        name,
        license_type,
        phone,
        is_on_call,
        specialties
      };

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
          alert(`⚡ Success! Electrician ${name} saved and synchronized with schedule.`);
        } else {
          alert('Failed to save electrician: ' + (data.message || 'Unknown error'));
        }
      } catch (e) {
        alert('Network error connecting to server.');
      }
    }

    // Manual Slot Booking
    function openManualBookModal(slotId, date, timeWindow, techName) {
      document.getElementById('mbSlotId').value = slotId;
      document.getElementById('mbSlotSummary').innerText = `Date: ${date} • Window: ${timeWindow} • Electrician: ${techName}`;
      document.getElementById('mbCustName').value = '';
      document.getElementById('mbPhone').value = '';
      document.getElementById('mbEmail').value = '';
      document.getElementById('mbAddress').value = '';
      document.getElementById('mbIssue').value = '';
      document.getElementById('manualBookModal').classList.add('active');
    }

    function closeManualBookModal() {
      document.getElementById('manualBookModal').classList.remove('active');
    }

    async function submitManualBooking() {
      const slot_id = document.getElementById('mbSlotId').value;
      const customer_name = document.getElementById('mbCustName').value.trim();
      const phone_number = document.getElementById('mbPhone').value.trim();
      const service_address = document.getElementById('mbAddress').value.trim();
      const issue_description = document.getElementById('mbIssue').value.trim() || 'Electrical Service';
      const customer_email = document.getElementById('mbEmail').value.trim();

      if (!customer_name || !phone_number || !service_address) {
        alert('Please fill in customer name, callback phone, and service address.');
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
      const phone = document.querySelector('.phone-container');
      if (phone) {
        phone.scrollIntoView({ behavior: 'smooth', block: 'center' });
        phone.style.borderColor = '#38bdf8';
        phone.style.boxShadow = '0 0 25px rgba(56, 189, 248, 0.6)';
        setTimeout(() => {
          phone.style.borderColor = '#334155';
          phone.style.boxShadow = '0 10px 25px rgba(0,0,0,0.5)';
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
            # Incoming phone call initial greeting
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
            if booking:
                self._send_json({"status": "SUCCESS", "booking": booking.__dict__})
            else:
                self._send_json({"status": "ERROR", "message": "Booking not found"}, 404)

        # 3. SIMULATE MISSED AFTER-HOURS CALL LEAD RECOVERY
        elif parsed.path == "/api/simulate-missed-call":
            self._send_json({
                "status": "SUCCESS",
                "message": "Automated text-back fired to lost lead within 3 seconds.",
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
            self._send_json({"status": "RESET_COMPLETED"})

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
