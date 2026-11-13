#!/usr/bin/env python3
"""
One-off generator for the landing page "Hear It + See the Ticket" demo section.

What it does
------------
1. Boots the REAL `demo_server.DemoRequestHandler` on 127.0.0.1 (ephemeral port, in-process thread).
2. For each scenario it POSTs to the same routes Twilio would hit, using Twilio's
   form-encoded payload shape:
       POST /api/reset            (fresh DB + call session)
       POST /api/twilio/voice     (greeting TwiML)
       POST /api/twilio/gather    (SpeechResult=<caller turn>)  x N
   and parses the dispatcher's spoken lines out of the returned TwiML <Say> tags.
3. Reads the resulting booking / emergency-triage records straight from the backend's
   in-memory DB and writes them to assets/demo/demo-tickets.json.
4. Synthesizes a two-speaker MP3 per scenario (edge-tts + ffmpeg from imageio-ffmpeg).

Safety
------
* No Twilio SDK exists in this codebase and no number is dialed or texted.
* SMTP / Stripe / Twilio / Gemini env vars are removed BEFORE importing the backend.
* CALENDAR_SYNC side effects (.ics/.eml file writes + SMTP) are replaced with no-op stubs
  that only record what WOULD have been sent.
* `requests` is hard-blocked so nothing in the backend can reach the network
  (unless --live-gemini is passed, which allows only generativelanguage.googleapis.com).
* There is no Twilio signature validation in the current webhook, so nothing needs bypassing.

Usage
-----
    ./venv/bin/pip install edge-tts imageio-ffmpeg     # dev-only, one time
    ./venv/bin/python scripts/generate_demo_assets.py               # tickets + audio
    ./venv/bin/python scripts/generate_demo_assets.py --skip-audio  # tickets only (offline)
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import enum
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import HTTPServer
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "demo"
sys.path.insert(0, str(ROOT))

# --------------------------------------------------------------------------------------
# Scenarios (caller lines only — every dispatcher line comes from the backend's TwiML)
# Note: avoid the words "owner"/"transfer"/"operator" — the gather route treats them as
# human-escalation keywords and would dial the live escalation number in production.
# --------------------------------------------------------------------------------------
SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "emergency",
        "audio_file": "demo-emergency.mp3",
        "title": "After-Hours Emergency",
        "subtitle": "Burning smell + buzzing breaker panel, 11:48 PM",
        "caller_label": "Mike Reynolds",
        "caller_voice": "en-US-GuyNeural",
        "caller_turns": [
            "Hi, this is Mike Reynolds. I smell burning plastic and there's a buzzing sound "
            "coming from the breaker panel in my basement. Half my kitchen just lost power.",
            "It's 418 Oakwood Ave, Cherry Hill, New Jersey. My callback is 856-555-0142.",
        ],
    },
    {
        "id": "ev-charger",
        "audio_file": "demo-ev-charger.mp3",
        "title": "High-Value Estimate Lead",
        "subtitle": "Level 2 Tesla charger install, attached garage",
        "caller_label": "Sarah Jenkins",
        "caller_voice": "en-US-MichelleNeural",
        "caller_turns": [
            "Hi, I'd like a quote to install a Level 2 Tesla charger in my attached garage. "
            "I have a 200 amp main panel in the basement, so it's about a 50 to 60 foot run.",
            "Sure. My name is Sarah Jenkins, address is 92 Maple St, Moorestown, New Jersey. "
            "My phone is 609-555-0188.",
        ],
    },
    {
        "id": "filtered",
        "audio_file": "demo-filtered.mp3",
        "title": "Out-of-Area Filter",
        "subtitle": "Whole-home rewiring request from Princeton, NJ",
        "caller_label": "Caller (Princeton, NJ)",
        "caller_voice": "en-US-EricNeural",
        "caller_turns": [
            "Hi, I'm calling from Princeton, New Jersey. I need my whole house rewired. "
            "Do you cover my area? My number is 609-555-0199.",
        ],
    },
]

DISPATCHER_VOICE = "en-US-AriaNeural"
TURN_GAP_MS = 450
# Fictional demo contractor's coverage (South Jersey). Feeds the backend's opt-in SERVICE_AREA_TOWNS filter.
DEMO_SERVICE_AREA = (
    "Cherry Hill,Moorestown,Haddonfield,Voorhees,Marlton,Mount Laurel,Collingswood,"
    "Maple Shade,Pennsauken,Medford,Evesham,Haddon Heights,Westmont,Audubon,Mount Holly"
)


# --------------------------------------------------------------------------------------
# 1. Sanitize environment BEFORE importing any backend module
# --------------------------------------------------------------------------------------
def sanitize_environment(live_gemini: bool) -> None:
    os.environ["SERVICE_AREA_TOWNS"] = DEMO_SERVICE_AREA
    for key in list(os.environ):
        upper = key.upper()
        if upper.startswith(("SMTP_", "STRIPE_", "TWILIO_")):
            os.environ.pop(key, None)
        if not live_gemini and upper in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            os.environ.pop(key, None)


def block_outbound_requests(live_gemini: bool) -> None:
    try:
        import requests  # noqa: F401
    except ImportError:
        return
    import requests.sessions

    original = requests.sessions.Session.request

    def guarded(self, method, url, *args, **kwargs):
        host = urllib.parse.urlparse(url).hostname or ""
        if live_gemini and host == "generativelanguage.googleapis.com":
            return original(self, method, url, *args, **kwargs)
        raise RuntimeError(f"[demo-generator] outbound request blocked: {method} {host}")

    requests.sessions.Session.request = guarded


SUPPRESSED_SIDE_EFFECTS: List[Dict[str, str]] = []


def stub_calendar_side_effects() -> None:
    from phone_agent.integrations.calendar_sync import CALENDAR_SYNC

    def recorder(name: str):
        def _stub(*args, **kwargs):
            target = args[0] if args else None
            ref = (
                getattr(target, "confirmation_id", None)
                or getattr(target, "triage_case_id", None)
                or kwargs.get("confirmation_id")
                or ""
            )
            SUPPRESSED_SIDE_EFFECTS.append({"call": name, "ref": str(ref)})
            return {}
        return _stub

    for method in (
        "sync_contractor_dispatch",
        "sync_booking",
        "send_emergency_contractor_alert",
        "send_confirmation_email",
        "send_contractor_dispatch_alert",
    ):
        setattr(CALENDAR_SYNC, method, recorder(method))


# --------------------------------------------------------------------------------------
# 2. Drive the real webhook routes
# --------------------------------------------------------------------------------------
SAY_RE = re.compile(r"<Say[^>]*>(.*?)</Say>", re.DOTALL)


class WebhookDriver:
    def __init__(self) -> None:
        import demo_server

        self.mod = demo_server
        self.httpd = HTTPServer(("127.0.0.1", 0), demo_server.DemoRequestHandler)
        self.httpd.RequestHandlerClass.log_message = lambda *a, **k: None  # quiet
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def _post(self, path: str, data: Dict[str, str] | None = None, as_json: bool = False) -> str:
        if as_json:
            body = json.dumps(data or {}).encode()
            ctype = "application/json"
        else:
            body = urllib.parse.urlencode(data or {}).encode()
            ctype = "application/x-www-form-urlencoded"  # Twilio's webhook format
        req = urllib.request.Request(self.base + path, data=body, headers={"Content-Type": ctype})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback only
        with opener.open(req, timeout=60) as resp:
            return resp.read().decode("utf-8")

    @staticmethod
    def _first_say(twiml: str) -> str:
        m = SAY_RE.search(twiml)
        return html.unescape(m.group(1)).strip() if m else ""

    def run(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        self._post("/api/reset", as_json=True)
        caller_phone = re.search(r"\d{3}-\d{3}-\d{4}", " ".join(scenario["caller_turns"]))
        twilio_common = {
            "CallSid": f"CA_DEMO_{scenario['id'].upper().replace('-', '_')}",
            "From": "+1" + caller_phone.group(0).replace("-", "") if caller_phone else "",
            "To": "+15550100000",
        }

        transcript: List[Dict[str, str]] = []
        greeting = self._first_say(self._post("/api/twilio/voice", twilio_common))
        transcript.append({"speaker": "dispatcher", "text": greeting})

        for line in scenario["caller_turns"]:
            transcript.append({"speaker": "caller", "text": line})
            twiml = self._post("/api/twilio/gather", {**twilio_common, "SpeechResult": line})
            if "<Dial" in twiml:
                raise RuntimeError(f"Scenario {scenario['id']} triggered a live <Dial>; reword caller lines.")
            transcript.append({"speaker": "dispatcher", "text": self._first_say(twiml)})

        session = self.mod.ACTIVE_SESSION
        booking = session.active_booking
        triage = session.emergency_triage
        from phone_agent.tools.service_area import check_service_area

        area = check_service_area(" ".join(scenario["caller_turns"]))
        return {
            "transcript": transcript,
            "tools_invoked": list(session.tools_invoked),
            "booking": to_plain(booking) if booking else None,
            "triage": to_plain(triage) if triage else None,
            "service_area_check": {"town": area["town"], "in_service_area": area["in_service_area"]},
        }


def to_plain(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return {k: to_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_plain(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return to_plain(obj.model_dump())
    return obj


BOOKING_FIELDS = (
    "confirmation_id", "customer_name", "phone_number", "service_address", "slot_date", "slot_time",
    "issue_description", "service_type", "urgency_level", "assigned_technician", "dispatch_fee",
    "status", "notes", "payment_status", "estimated_job_value", "truck_id", "tech_match_reason",
    "connected_fsm", "fsm_ticket_id",
)
TRIAGE_FIELDS = (
    "triage_case_id", "hazard_type", "location_in_property", "severity_level", "is_fire_visible",
    "is_person_injured", "is_water_present", "can_safely_access_panel",
    "immediate_life_safety_actions", "emergency_dispatch_recommended", "utility_shutoff_required",
    "recommended_action_plan",
)


def trim(record: Dict[str, Any] | None, fields) -> Dict[str, Any] | None:
    if not record:
        return None
    return {k: record.get(k) for k in fields if k in record}


# --------------------------------------------------------------------------------------
# 3. Audio synthesis
# --------------------------------------------------------------------------------------
def ffmpeg_bin() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


async def tts_segment(text: str, voice: str, out_path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate="+4%").save(str(out_path))


def build_call_audio(transcript: List[Dict[str, str]], caller_voice: str, out_mp3: Path) -> float:
    ff = ffmpeg_bin()
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        wavs: List[Path] = []
        silence = tmpdir / "gap.wav"
        subprocess.run(
            [ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", f"{TURN_GAP_MS / 1000:.3f}", str(silence)],
            check=True,
        )
        for i, turn in enumerate(transcript):
            voice = DISPATCHER_VOICE if turn["speaker"] == "dispatcher" else caller_voice
            seg_mp3 = tmpdir / f"seg{i:02d}.mp3"
            seg_wav = tmpdir / f"seg{i:02d}.wav"
            asyncio.run(tts_segment(turn["text"], voice, seg_mp3))
            subprocess.run(
                [ff, "-y", "-loglevel", "error", "-i", str(seg_mp3), "-ar", "24000", "-ac", "1", str(seg_wav)],
                check=True,
            )
            if wavs:
                wavs.append(silence)
            wavs.append(seg_wav)

        concat_list = tmpdir / "list.txt"
        concat_list.write_text("".join(f"file '{p}'\n" for p in wavs))
        subprocess.run(
            [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1",
             "-codec:a", "libmp3lame", "-b:a", "64k", str(out_mp3)],
            check=True,
        )
    return probe_duration(out_mp3)


def probe_duration(path: Path) -> float:
    proc = subprocess.run([ffmpeg_bin(), "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    matches = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if not matches:
        return 0.0
    h, m, s = matches[-1]
    return round(int(h) * 3600 + int(m) * 60 + float(s), 2)


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-audio", action="store_true", help="Only regenerate demo-tickets.json")
    parser.add_argument("--live-gemini", action="store_true",
                        help="Use GEMINI_API_KEY (live model) instead of the deterministic offline engine")
    args = parser.parse_args()

    sanitize_environment(args.live_gemini)
    block_outbound_requests(args.live_gemini)
    stub_calendar_side_effects()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    driver = WebhookDriver()
    engine = "gemini-live" if driver.mod.ACTIVE_AGENT.client.is_live_api_ready() else "offline-deterministic"
    print(f"[demo-generator] webhook server on {driver.base} | engine={engine}")

    results = []
    try:
        for sc in SCENARIOS:
            SUPPRESSED_SIDE_EFFECTS.clear()
            run = driver.run(sc)
            entry = {
                "id": sc["id"],
                "title": sc["title"],
                "subtitle": sc["subtitle"],
                "caller_label": sc["caller_label"],
                "audio_src": f"/assets/demo/{sc['audio_file']}",
                "duration_seconds": None,
                "transcript": run["transcript"],
                "tools_invoked": run["tools_invoked"],
                "booking": trim(run["booking"], BOOKING_FIELDS),
                "triage": trim(run["triage"], TRIAGE_FIELDS),
                "service_area_check": run.get("service_area_check"),
                "suppressed_side_effects": list(SUPPRESSED_SIDE_EFFECTS),
            }
            print(f"\n=== {sc['id']} === tools={entry['tools_invoked']}")
            for t in entry["transcript"]:
                print(f"  {t['speaker']:>10}: {t['text']}")
            if entry["booking"]:
                b = entry["booking"]
                print(f"  -> booking {b.get('confirmation_id')} {b.get('urgency_level')} {b.get('service_address')}")
            if entry["triage"]:
                print(f"  -> triage {entry['triage'].get('triage_case_id')} {entry['triage'].get('severity_level')}")
            print(f"  suppressed: {entry['suppressed_side_effects']}")
            results.append(entry)
    finally:
        driver.close()

    tickets_path = OUT_DIR / "demo-tickets.json"
    previous = {}
    if tickets_path.exists():
        try:
            previous = {s["id"]: s for s in json.loads(tickets_path.read_text()).get("scenarios", [])}
        except Exception:
            previous = {}

    if not args.skip_audio:
        for sc, entry in zip(SCENARIOS, results):
            out_mp3 = OUT_DIR / sc["audio_file"]
            dur = build_call_audio(entry["transcript"], sc["caller_voice"], out_mp3)
            if dur <= 0:
                raise RuntimeError(f"{out_mp3.name} has zero duration")
            entry["duration_seconds"] = dur
            print(f"[audio] {out_mp3.relative_to(ROOT)}  {dur:.1f}s  {out_mp3.stat().st_size // 1024} KB")
    else:
        for entry in results:
            entry["duration_seconds"] = previous.get(entry["id"], {}).get("duration_seconds")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": engine,
        "source": "demo_server.py /api/twilio/voice + /api/twilio/gather (in-process, side effects stubbed)",
        "disclaimer": "Simulated calls. Callers, phone numbers (555 range) and addresses are fictional demo data.",
        "scenarios": results,
    }
    tickets_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n[tickets] {tickets_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
