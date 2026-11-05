# ZeroMiss Electrical 24/7 Voice Dispatch Agent (Gemini 2.0 Flash)

A production-grade Python voice dispatch system for electrical contracting operations powered by **Google Gemini 2.0 Flash**. Designed for real-time telephone interactions, handling 24/7 emergency fire/shock triage, calendar scheduling, and automated service dispatch.

---

## 🌟 Key Features

1. **Powered by Gemini 2.0 Flash**:
   - Spoken-audio optimized prompt engineering (voice-first persona "Sarah", concise phrasing, zero raw markdown in speech).
   - Support for Gemini 2.0 Flash REST `generateContent` with function calling.
   - Support for Gemini 2.0 Flash Multimodal Live Bidirectional WebSocket API (`BidiGenerateContent`) for streaming audio chunks.
   - Built-in deterministic simulation engine for offline CI and automated testing without external API key dependencies.

2. **Core Dispatch Tools**:
   - `triage_fire_shock_emergency`: CRITICAL SAFETY GUARDRAIL. Detects active fires, arcing sparks, water contact near electrical panels, electric shock injuries, and downed power lines. Delivers immediate spoken life-safety instructions (evacuation, 911, stay back 40ft, isolate circuits) and triggers Priority Code Red dispatch.
   - `check_calendar_availability`: Queries technician availability across date windows (morning, afternoon, emergency 24/7 on-call) and specialties (EV chargers, panel upgrades, lighting, inspections, commercial).
   - `book_service_call`: Validates customer credentials, address, and issue scope. Assigns qualified licensed electricians (Master Electrician on-call or Journeyman), calculates fees (free quotes vs diagnostic fee vs emergency fee), and generates confirmation codes.

3. **Audio Streaming & Telephony Simulator**:
   - Raw PCM16 16kHz mono audio generation for simulating real telephone calls.
   - Telephony effects: dual-frequency ring tone (440Hz + 480Hz), voice syllabic modulation, and `.wav` call recording exports.

4. **Comprehensive 20-Scenario Test Suite**:
   - Rigorous evaluation runner testing 20 diverse real-world customer calls.
   - Validates tool invocations, emergency triage accuracy, life-safety spoken instructions, booking generation, and voice friendliness.
   - Exports rich colored terminal reports, JSON audit logs, and Markdown documentation.

---

## 🏗️ Architecture

```
phone_agent/
├── cli.py                     # Interactive CLI: call dispatcher, test suite, dispatch board
├── phone_agent/
│   ├── config.py              # Company info, fee schedules, emergency tiers
│   ├── models.py              # Data structures: Bookings, Slots, Triage Reports
│   ├── database.py            # Thread-safe SQLite / memory store for roster & bookings
│   ├── tools/
│   │   ├── calendar_tool.py   # check_calendar_availability implementation
│   │   ├── booking_tool.py    # book_service_call implementation
│   │   ├── emergency_tool.py  # triage_fire_shock_emergency implementation
│   │   └── registry.py        # Gemini 2.0 Flash function declarations & dispatcher
│   └── agent/
│       ├── prompts.py         # Voice persona & safety guardrail prompts
│       ├── gemini_client.py   # Gemini 2.0 Flash client (Live WebSocket + REST + Emulator)
│       ├── voice_agent.py     # Conversation session manager & turn orchestrator
│       └── audio_sim.py       # PCM16 audio streamer & WAV generator
├── tests/
│   ├── scenarios.py           # 20 customer calling scenarios
│   ├── test_runner.py         # Automated evaluation engine with rich reporting
│   └── test_tools.py          # Unit tests for tools and database
└── reports/                   # Generated evaluation reports (JSON & Markdown)
```

---

## ⚡ Quick Start

### 1. Run the 20-Scenario Test Runner
Evaluate all 20 calling scenarios with the automated grader:
```bash
PYTHONPATH=. python3 tests/test_runner.py
# or via CLI:
PYTHONPATH=. python3 cli.py test
```

### 2. Run a Single Scenario
```bash
PYTHONPATH=. python3 cli.py test --scenario SCENARIO_01
```

### 3. Start an Interactive Phone Call
Dial in to Sarah, the ZeroMiss Voice Dispatcher:
```bash
PYTHONPATH=. python3 cli.py call
# With audio recording saved to WAV:
PYTHONPATH=. python3 cli.py call --record-wav
```

### 4. View the Live Dispatch Board
Inspect technician roster, current calendar slots, and active emergency logs:
```bash
PYTHONPATH=. python3 cli.py board
```

### 5. Run Unit Tests
```bash
PYTHONPATH=. python3 -m unittest tests/test_tools.py
```

---

## 📋 The 20 Customer Calling Scenarios

| Scenario ID | Title | Category | Severity / Urgency | Tools Expected |
|---|---|---|---|---|
| `SCENARIO_01` | Active Breaker Panel Fire and Arcing Sparks | `EMERGENCY_FIRE` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency`, `book_service_call` |
| `SCENARIO_02` | Water Leaking Directly Over Main Panel | `EMERGENCY_WATER` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency`, `book_service_call` |
| `SCENARIO_03` | Electric Shock Injury from Dishwasher Metal Frame | `EMERGENCY_SHOCK` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency`, `book_service_call` |
| `SCENARIO_04` | Downed Power Line Arcing on Wet Driveway | `EMERGENCY_DOWNED_LINE` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency` *(utility jurisdiction; `book_service_call` only if weatherhead/mast damaged)* |
| `SCENARIO_05` | Sizzling Scorched Wall Outlet with Burning Fishy Odor | `EMERGENCY_HAZARD` | `LEVEL_2_HIGH_HAZARD` | `triage_fire_shock_emergency`, `book_service_call` |
| `SCENARIO_06` | Smoke Emitting from Kitchen Ceiling Light Fixture | `EMERGENCY_SMOKE` | `LEVEL_2_HIGH_HAZARD` | `triage_fire_shock_emergency`, `book_service_call` |
| `SCENARIO_07` | Routine Ceiling Fan Installation in Master Bedroom | `ROUTINE_INSTALLATION` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_08` | Level 2 Tesla Wall Connector EV Charger Installation | `SPECIALTY_EV` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_09` | 100-Amp to 200-Amp Electrical Panel Service Upgrade | `SPECIALTY_PANEL` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_10` | Kitchen Renovation Recessed LED Lighting and Dimmer | `ROUTINE_INSTALLATION` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_11` | Kitchen Circuit Breaker Tripping on Microwave Overload | `OVERLOAD_TRIAGE` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_12` | Complete Single-Home Power Outage Diagnostic | `URGENT_OUTAGE` | `URGENT` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_13` | Commercial Restaurant Walk-in Freezer Circuit Tripped | `COMMERCIAL_URGENT` | `URGENT` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_14` | Bathroom GFCI Receptacle Tripped and Won't Reset | `ROUTINE_REPAIR` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_15` | Historic Home Knob-and-Tube Wiring Safety Inspection | `SAFETY_INSPECTION` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_16` | Outdoor Hot Tub 50-Amp GFCI Spa Disconnect | `RESIDENTIAL_240V_DEDICATED_CIRCUIT` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_17` | Whole-House Generator Transfer Switch & Inlet Box | `SPECIALTY_GENERATOR` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_18` | Whole-House Lights Flickering During AC Startup | `DIAGNOSTIC_VOLTAGE_DROP` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_19` | Commercial Property Security LED Motion Floodlights | `COMMERCIAL_LIGHTING` | `STANDARD` | `check_calendar_availability`, `book_service_call` |
| `SCENARIO_20` | Panicked Caller: Dryer Popping with Sparks Behind Wall | `EMERGENCY_PANIC` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency`, `book_service_call` |

---

## 🔒 Safety & Triage Protocols

The agent enforces NFPA 70 (National Electrical Code) and NFPA 70E life-safety triage standards:
- **Level 1 Critical Life-Safety**: Triggered on active flames, sparks, water submersion of panels, downed wires, or shock injuries. Mandates immediate evacuation (or staying back 40 feet from downed utility lines), 911/utility notification from outside, warnings against touching water/metal, and dispatches the on-call Master Electrician (note: downed utility lines are exclusive utility jurisdiction; contractor dispatch applies strictly to customer-owned meter mast/riser damage post-isolation).
- **Level 2 High Hazard**: Triggered on burning plastic/fishy odors, sizzling outlets, or smoking fixtures. Advises turning off specific circuit breakers only if safe and dry, isolating the area, and dispatching an urgent technician within 1-2 hours.
- **Level 3 Moderate / Overload**: Tripped breakers from appliance overload (microwave + toaster). Advises unplugging high-wattage devices and schedules diagnostic service without unsafe breaker forcing.
