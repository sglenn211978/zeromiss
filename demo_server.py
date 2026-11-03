"""ZeroMiss Voice Dispatch - 1-Click Client Demonstration Web Server.

Serves an interactive, zero-clutter web dashboard for client sales presentations.
Prospective contractors can enter their email, trigger 1-click emergency or routine
scenarios, speak via live microphone, and see dispatches land in Google Calendar in real time.
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
  <title>ZeroMiss Voice Dispatch | Live Client Demonstration</title>
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

    /* Top Navigation Bar */
    header {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      padding: 14px 24px;
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
      font-size: 22px;
      font-weight: bold;
    }
    .brand h1 { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; }
    .brand p { font-size: 0.8rem; color: var(--text-muted); }

    /* Contractor Config Header Bar */
    .contractor-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      background: #1e293b;
      padding: 6px 14px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .contractor-bar label {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
    }
    .contractor-bar input {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: #38bdf8;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-family: monospace;
      outline: none;
      width: 230px;
    }
    .contractor-bar button {
      background: var(--primary);
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      font-weight: 600;
    }
    .contractor-bar button:hover { background: var(--primary-hover); }

    /* Main Grid Layout */
    main {
      flex: 1;
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 20px;
      padding: 20px;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
    }

    @media (max-width: 1024px) {
      main { grid-template-columns: 1fr; }
    }

    /* Cards */
    .panel-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }

    .card-header {
      padding: 14px 18px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(15, 23, 42, 0.6);
    }
    .card-header h2 {
      font-size: 1rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(34, 197, 94, 0.15);
      color: #4ade80;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #22c55e;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.95); opacity: 0.8; }
      50% { transform: scale(1.2); opacity: 1; }
      100% { transform: scale(0.95); opacity: 0.8; }
    }

    /* Scenario Quick Triggers */
    .scenario-triggers {
      padding: 14px 18px;
      border-bottom: 1px solid var(--card-border);
      background: #0f172a;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .scenario-btn {
      flex: 1;
      min-width: 180px;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s;
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

    .btn-reset {
      background: #334155;
      color: #cbd5e1;
      flex: 0 0 auto;
      min-width: 80px;
    }
    .btn-reset:hover { background: #475569; color: white; }

    /* Conversation Stream */
    .chat-container {
      flex: 1;
      height: 380px;
      overflow-y: auto;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: #0b1120;
    }
    .bubble {
      max-width: 82%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 0.92rem;
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

    /* Audio wave simulation bar */
    .audio-bar {
      height: 32px;
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
    .speaking .wave-line:nth-child(odd) { height: 22px; animation: wave 0.4s infinite alternate; }
    .speaking .wave-line:nth-child(even) { height: 16px; animation: wave 0.4s infinite 0.2s alternate; }
    @keyframes wave {
      0% { height: 6px; }
      100% { height: 26px; }
    }

    /* Live Input Control */
    .input-row {
      padding: 14px 18px;
      border-top: 1px solid var(--card-border);
      background: #0f172a;
      display: flex;
      gap: 10px;
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
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-mic {
      background: #334155 !important;
      font-size: 1.1rem;
      padding: 10px 14px !important;
    }
    .btn-mic.listening {
      background: #dc2626 !important;
      animation: pulse 1s infinite;
    }

    /* Contractor Cockpit (Right Pane) */
    .cockpit-body {
      flex: 1;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 18px;
      overflow-y: auto;
    }

    /* Magic Moment Card */
    .dispatch-hero {
      background: linear-gradient(135deg, rgba(2, 132, 199, 0.2), rgba(15, 23, 42, 0.8));
      border: 1px solid rgba(56, 189, 248, 0.4);
      border-radius: 12px;
      padding: 20px;
      text-align: center;
      display: none;
      animation: fadeIn 0.4s ease;
    }
    .dispatch-hero.active { display: block; }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .hero-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    .badge-emergency { background: #dc2626; color: white; }
    .badge-standard { background: #0284c7; color: white; }

    .hero-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 6px; }
    .hero-subtitle { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px; }

    .btn-cal-magic {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      background: #0284c7;
      color: white;
      text-decoration: none;
      padding: 14px 28px;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 700;
      transition: all 0.2s;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
    }
    .btn-cal-magic:hover {
      background: #0369a1;
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(2, 132, 199, 0.6);
    }

    /* Ticket Detail Table */
    .ticket-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      background: #0f172a;
      border-radius: 8px;
      overflow: hidden;
      margin-top: 14px;
      text-align: left;
    }
    .ticket-table td {
      padding: 8px 12px;
      border-bottom: 1px solid var(--card-border);
    }
    .ticket-table td:first-child {
      font-weight: 600;
      color: var(--text-muted);
      width: 35%;
    }

    /* Technician Roster Grid */
    .tech-roster {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
    }
    .tech-card {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .tech-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .tech-name { font-weight: 600; font-size: 0.85rem; }
    .tech-status { font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
    .on-call { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
    .standard { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
    .tech-specs { font-size: 0.75rem; color: var(--text-muted); }

    /* Visual On-Screen Calendar Grid */
    .calendar-section {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px;
    }
    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }
    .cal-day-col {
      background: #1e293b;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .cal-day-header {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      color: #38bdf8;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 4px;
      text-align: center;
    }
    .cal-slot {
      background: #0f172a;
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 0.72rem;
      transition: all 0.2s;
      cursor: pointer;
    }
    .cal-slot:hover {
      border-color: #38bdf8;
      transform: translateY(-1px);
    }
    .cal-slot-time {
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 2px;
    }
    .cal-slot-tech {
      color: #94a3b8;
      font-size: 0.68rem;
    }
    .cal-slot.booked-routine {
      background: rgba(22, 163, 74, 0.25);
      border: 1px solid #22c55e;
      color: #86efac;
      box-shadow: 0 0 10px rgba(34, 197, 94, 0.2);
    }
    .cal-slot.booked-routine .cal-slot-time {
      color: #86efac;
      font-weight: 700;
    }
    .cal-slot.booked-routine .cal-slot-tech {
      color: #dcfce7;
      font-weight: 600;
    }
    .cal-slot.booked-emergency {
      background: rgba(220, 38, 38, 0.3);
      border: 1px solid #ef4444;
      color: #fca5a5;
      animation: pulse 1.5s infinite;
      box-shadow: 0 0 12px rgba(239, 68, 68, 0.35);
    }
    .cal-slot.booked-emergency .cal-slot-time {
      color: #fca5a5;
      font-weight: 700;
    }
    .cal-slot.booked-emergency .cal-slot-tech {
      color: #fee2e2;
      font-weight: 600;
    }

    /* Add Technician Button & Modal */
    .btn-add-tech {
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      color: white;
      border: none;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-add-tech:hover {
      opacity: 0.9;
      transform: translateY(-1px);
    }
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
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
      max-width: 480px;
      padding: 22px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
      animation: fadeIn 0.25s ease;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
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
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      margin-bottom: 4px;
      margin-top: 10px;
    }
    .modal-body input[type="text"], .modal-body select {
      width: 100%;
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.88rem;
      outline: none;
      box-sizing: border-box;
    }
    .btn-save-tech {
      width: 100%;
      background: #0284c7;
      color: white;
      border: none;
      padding: 11px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.9rem;
      margin-top: 18px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-save-tech:hover { background: #0369a1; }

    /* Footer */
    footer {
      background: #0f172a;
      border-top: 1px solid var(--card-border);
      padding: 12px 24px;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }
  </style>
</head>
<body>

  <!-- Top Navigation & Prospect Email Switcher -->
  <header>
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div>
        <h1>ZeroMiss Voice Dispatch</h1>
        <p>AI Emergency Triage & Automated Scheduling for Electrical Contractors</p>
      </div>
    </div>
    <div class="contractor-bar">
      <label>Contractor Email:</label>
      <input type="email" id="contractorEmail" value="sean.glenn21@gmail.com" placeholder="contractor@domain.com">
      <button onclick="saveContractorEmail()">Set Client</button>
    </div>
  </header>

  <main>
    <!-- LEFT PANE: Telephone Call Simulator -->
    <div class="panel-card">
      <div class="card-header">
        <h2>📞 Live Caller Simulator (Sarah Engine)</h2>
        <span class="status-badge"><span class="status-dot"></span> Ring 1 Answer</span>
      </div>

      <!-- Quick 1-Click Scenario Buttons -->
      <div class="scenario-triggers">
        <button class="scenario-btn btn-emergency" onclick="runScenario('emergency')">
          🚨 Demo: Burning Rubber Emergency
        </button>
        <button class="scenario-btn btn-routine" onclick="runScenario('ev_charger')">
          ⚡ Demo: Tesla EV Charger Quote
        </button>
        <button class="scenario-btn btn-reset" onclick="resetCall()">
          🔄 Reset
        </button>
      </div>

      <!-- Live Dialogue Stream -->
      <div class="chat-container" id="chatStream">
        <div class="bubble bubble-sarah">
          <div class="speaker-name">Sarah (ZeroMiss Dispatcher)</div>
          Thank you for calling ZeroMiss Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?
        </div>
      </div>

      <!-- Audio Waveform Indicator -->
      <div class="audio-bar" id="audioBar">
        <div class="wave-line"></div>
        <div class="wave-line"></div>
        <div class="wave-line"></div>
        <div class="wave-line"></div>
        <div class="wave-line"></div>
        <div class="wave-line"></div>
        <div class="wave-line"></div>
      </div>

      <!-- Interactive Input -->
      <div class="input-row">
        <button class="btn-mic" id="micBtn" onclick="toggleMic()" title="Push-to-Talk via Microphone">🎙️</button>
        <input type="text" id="userInput" placeholder="Speak or type a customer issue..." onkeydown="if(event.key==='Enter') sendUserMessage()">
        <button onclick="sendUserMessage()">Call</button>
      </div>
    </div>

    <!-- RIGHT PANE: Contractor Cockpit & The Magic Moment -->
    <div class="panel-card">
      <div class="card-header">
        <h2>⚡ Contractor Dispatch Cockpit (What You Receive)</h2>
        <span style="font-size: 0.8rem; color: var(--accent); font-weight: 600;">Real-Time Feed</span>
      </div>

      <div class="cockpit-body">
        <!-- Magic Moment Hero Card -->
        <div class="dispatch-hero" id="dispatchHero">
          <span class="hero-badge badge-standard" id="heroBadge">Confirmed Dispatch</span>
          <div class="hero-title" id="heroTitle">New Service Call Scheduled</div>
          <div class="hero-subtitle" id="heroSubtitle">Dispatched directly to <strong id="heroContractor">sean.glenn21@gmail.com</strong></div>

          <a href="#" id="heroCalBtn" target="_blank" class="btn-cal-magic">
            📅 Click to Add to Google Calendar
          </a>

          <table class="ticket-table" id="ticketTable">
            <tr><td>Confirmation Code:</td><td id="tktConf">-</td></tr>
            <tr><td>Customer Name:</td><td id="tktCustomer">-</td></tr>
            <tr><td>Callback Phone:</td><td id="tktPhone">-</td></tr>
            <tr><td>Service Address:</td><td id="tktAddress">-</td></tr>
            <tr><td>Assigned Electrician:</td><td id="tktTech">-</td></tr>
            <tr><td>Arrival Window:</td><td id="tktWindow">-</td></tr>
            <tr><td>Fee Structure:</td><td id="tktFee">-</td></tr>
          </table>
        </div>

        <!-- Waiting Placeholder if no booking yet -->
        <div id="waitingPlaceholder" style="background: #0f172a; padding: 30px; border-radius: 8px; text-align: center; border: 1px dashed var(--card-border);">
          <div style="font-size: 28px; margin-bottom: 10px;">📲</div>
          <h3 style="font-size: 0.95rem; margin-bottom: 6px;">Awaiting Next Customer Call</h3>
          <p style="font-size: 0.8rem; color: var(--text-muted); max-width: 320px; margin: 0 auto;">
            Click one of the demo buttons on the left or type an electrical inquiry to see live Google Calendar sync in real time.
          </p>
        </div>

        <!-- Live Visual On-Screen Calendar Grid -->
        <div class="calendar-section">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="font-size:0.85rem; font-weight:700; color:var(--text); text-transform:uppercase; letter-spacing:0.04em;">
              📅 Live Dispatch Schedule (On-Screen Calendar)
            </h3>
            <span style="font-size:0.75rem; color:#38bdf8; font-weight:600;">Real-Time Fleet Grid</span>
          </div>
          <div class="calendar-grid" id="calendarGrid">
            <!-- Populated dynamically by renderCalendar() -->
          </div>
        </div>

        <!-- Real-Time Technician Fleet Roster with + Add Technician Button -->
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <h3 style="font-size:0.85rem; font-weight:700; color:var(--text-muted); text-transform:uppercase;">
              Active Electrician Fleet Roster
            </h3>
            <button class="btn-add-tech" onclick="openAddTechModal()">+ Add Technician</button>
          </div>
          <div class="tech-roster" id="techRoster">
            <!-- Populated dynamically by renderTechRoster() -->
          </div>
        </div>

      </div>
    </div>
  </main>

  <!-- Modal: + Add Technician -->
  <div class="modal-overlay" id="techModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3>⚡ Add Electrician to Dispatch Fleet</h3>
        <button class="modal-close" onclick="closeAddTechModal()">&times;</button>
      </div>
      <div class="modal-body">
        <label>Technician Full Name</label>
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
            <label>Mobile Phone (for SMS)</label>
            <input type="text" id="newTechPhone" placeholder="(555) 019-3388">
          </div>
        </div>

        <label>On-Call Status</label>
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

        <button class="btn-save-tech" onclick="submitNewTech()">Save Technician & Sync Schedule</button>
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

    // Speech synthesis for Sarah's voice
    function speakText(text) {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      audioBar.classList.add('speaking');

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;

      // Prefer a natural English female voice if available
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
        }
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
      }
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
      fetchBoardData();
    }

    // Global board state
    let BOARD_DATA = { technicians: [], slots: [], bookings: [] };

    async function fetchBoardData() {
      try {
        const res = await fetch('/api/board');
        const data = await res.json();
        BOARD_DATA = data;
        renderTechRoster(data.technicians || []);
        renderCalendar(data.bookings || [], data.slots || []);
      } catch (err) {
        console.error('Error fetching board data:', err);
      }
    }

    function renderTechRoster(technicians) {
      const container = document.getElementById('techRoster');
      if (!container) return;
      if (!technicians.length) {
        container.innerHTML = '<div style="color:var(--text-muted); font-size:0.8rem;">No technicians registered yet.</div>';
        return;
      }

      container.innerHTML = technicians.map(t => {
        const specs = (t.specialties || []).map(s => s.replace(/_/g, ' ')).join(', ');
        const isOnCall = t.is_on_call;
        return `
          <div class="tech-card">
            <div class="tech-header">
              <span class="tech-name">${t.name}</span>
              <span class="tech-status ${isOnCall ? 'on-call' : 'standard'}">
                ${isOnCall ? '🟢 ON-CALL (24/7)' : '⚪ STANDARD'}
              </span>
            </div>
            <div class="tech-specs">${t.license_type} • ${t.phone}</div>
            <div style="font-size:0.7rem; color:#38bdf8; margin-top:2px;">⭐ ${t.rating || 4.95} • ${specs || 'Residential Electrical'}</div>
          </div>
        `;
      }).join('');
    }

    function renderCalendar(bookings, slots) {
      const grid = document.getElementById('calendarGrid');
      if (!grid) return;

      const dates = [...new Set((slots || []).map(s => s.date))].slice(0, 5);
      if (!dates.length) {
        const today = new Date();
        for (let i = 1; i <= 4; i++) {
          const d = new Date(today);
          d.setDate(today.getDate() + i);
          dates.push(d.toISOString().split('T')[0]);
        }
      }

      grid.innerHTML = dates.map(dt => {
        const dObj = new Date(dt + 'T12:00:00');
        const dayLabel = dObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

        const windows = [
          { label: 'Morning', key: '08:00 AM - 12:00 PM' },
          { label: 'Afternoon', key: '12:00 PM - 04:00 PM' },
          { label: 'Evening', key: '04:00 PM - 07:00 PM' }
        ];

        const slotsHtml = windows.map(w => {
          const b = (bookings || []).find(bk => {
            const dateMatch = bk.slot_date === dt || bk.slot_date === 'today' || bk.slot_date === 'tomorrow';
            const timeMatch = (bk.slot_time || '').includes(w.key) || (w.key.includes(bk.slot_time || '---'));
            return dateMatch && timeMatch;
          });

          const isEmergBooking = (bookings || []).find(bk => {
            const isEmerg = (bk.urgency_level || '').includes('EMERG');
            return isEmerg && (bk.slot_date === dt || bk.slot_date === 'today');
          });

          if (isEmergBooking && w.label === 'Morning') {
            const safeObj = JSON.stringify(isEmergBooking).replace(/'/g, "&#39;");
            return `
              <div class="cal-slot booked-emergency" onclick='selectCalendarBooking(${safeObj})' title="Click to view Code Red dispatch dossier">
                <div class="cal-slot-time">🚨 CODE RED</div>
                <div class="cal-slot-tech">${isEmergBooking.assigned_technician.split('(')[0].trim()} • ${isEmergBooking.customer_name}</div>
              </div>
            `;
          }

          if (b) {
            const safeObj = JSON.stringify(b).replace(/'/g, "&#39;");
            return `
              <div class="cal-slot booked-routine" onclick='selectCalendarBooking(${safeObj})' title="Click to view booking">
                <div class="cal-slot-time">⚡ ${w.label} (Booked)</div>
                <div class="cal-slot-tech">${b.assigned_technician.split('(')[0].trim()} • ${b.customer_name}</div>
              </div>
            `;
          }

          const matchingSlot = (slots || []).find(s => s.date === dt && s.time_window.includes(w.key));
          const techName = matchingSlot ? matchingSlot.technician_name.split('(')[0].trim() : 'On-Call Tech';

          return `
            <div class="cal-slot" title="Available Slot">
              <div class="cal-slot-time">${w.label} (${w.key.split('-')[0].trim()})</div>
              <div class="cal-slot-tech">Avail: ${techName}</div>
            </div>
          `;
        }).join('');

        return `
          <div class="cal-day-col">
            <div class="cal-day-header">${dayLabel}</div>
            ${slotsHtml}
          </div>
        `;
      }).join('');
    }

    function selectCalendarBooking(b) {
      if (b) {
        showBookingInHero(b);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }

    // Modal Controls
    function openAddTechModal() {
      document.getElementById('techModal').classList.add('active');
      document.getElementById('newTechName').focus();
    }

    function closeAddTechModal() {
      document.getElementById('techModal').classList.remove('active');
    }

    async function submitNewTech() {
      const name = document.getElementById('newTechName').value.trim();
      if (!name) {
        alert('Please enter technician full name.');
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

      try {
        const res = await fetch('/api/technicians', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            license_type,
            phone,
            is_on_call,
            specialties
          })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          closeAddTechModal();
          document.getElementById('newTechName').value = '';
          await fetchBoardData();
          alert(`⚡ Success! ${name} (${license_type}) added to active fleet and scheduled on calendar!`);
        } else {
          alert('Failed to add technician: ' + (data.message || 'Unknown error'));
        }
      } catch (e) {
        alert('Error connecting to server.');
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
            self._send_json({
                "contractor_email": DEFAULT_CONFIG.contractor_email,
                "contractor_name": DEFAULT_CONFIG.contractor_name,
                "bookings": bookings_data,
                "technicians": techs_data,
                "slots": slots_data,
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global ACTIVE_SESSION
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(post_body)
        except Exception:
            req_data = {}

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/set-contractor":
            new_email = req_data.get("email", "").strip()
            if new_email:
                DEFAULT_CONFIG.contractor_email = new_email
            self._send_json({"status": "SUCCESS", "contractor_email": DEFAULT_CONFIG.contractor_email})

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
    print("  ZeroMiss Voice Dispatch - 1-Click Client Demonstration Server")
    print(f"  Live Demo Web Dashboard: http://localhost:{port}")
    print(f"  Contractor Destination:   {DEFAULT_CONFIG.contractor_name} ({DEFAULT_CONFIG.contractor_email})")
    print("=" * 80 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo Server Stopped.")
        server.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("PORT", "8080"))
    run_demo_server(port=port_arg)
