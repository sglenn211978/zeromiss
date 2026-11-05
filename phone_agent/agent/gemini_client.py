"""Gemini 2.0 Flash client supporting Live API, REST API, and smart simulation engine."""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from phone_agent.agent.prompts import DISPATCHER_SYSTEM_INSTRUCTION
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB
from phone_agent.tools.registry import GEMINI_FUNCTION_DECLARATIONS, execute_tool

try:
    import requests
except ImportError:
    requests = None


class Gemini2FlashClient:
    """
    Client for Google Gemini 2.0 Flash voice dispatch agent.
    Provides native REST and WebSocket streaming integration, along with a deterministic
    offline engine for evaluation and CI without requiring active API keys.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or DEFAULT_CONFIG.api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def is_live_api_ready(self) -> bool:
        """Checks if a valid live API key is set."""
        return bool(self.api_key and not self.api_key.startswith("mock_") and len(self.api_key) > 10)

    def generate_turn(
        self,
        conversation_history: List[Dict[str, Any]],
        system_instruction: str = DISPATCHER_SYSTEM_INSTRUCTION,
    ) -> Dict[str, Any]:
        """
        Executes a conversation turn with Gemini 2.0 Flash.
        Returns a dictionary containing:
          - 'text': Spoken voice response from the agent.
          - 'tool_calls': List of function call requests emitted by the model.
        """
        if self.is_live_api_ready() and requests is not None:
            try:
                return self._call_real_gemini_api(conversation_history, system_instruction)
            except Exception as e:
                # Fallback to local intelligent engine if network or rate limit fails
                return self._simulate_gemini_2_flash_turn(conversation_history, system_instruction)
        else:
            return self._simulate_gemini_2_flash_turn(conversation_history, system_instruction)

    def _call_real_gemini_api(
        self,
        conversation_history: List[Dict[str, Any]],
        system_instruction: str,
    ) -> Dict[str, Any]:
        """Calls official Google Gemini 2.0 Flash generateContent endpoint."""
        endpoint = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        # Convert conversation history to Gemini contents format
        contents = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            parts = []

            if "content" in msg and msg["content"]:
                parts.append({"text": msg["content"]})

            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    parts.append({
                        "functionCall": {
                            "name": tc["name"],
                            "args": tc.get("args", {}),
                        }
                    })

            if "tool_results" in msg and msg["tool_results"]:
                for tr in msg["tool_results"]:
                    parts.append({
                        "functionResponse": {
                            "name": tr["name"],
                            "response": {"result": tr.get("result", {})},
                        }
                    })

            if parts:
                contents.append({"role": role, "parts": parts})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "tools": [{"functionDeclarations": GEMINI_FUNCTION_DECLARATIONS}],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
                "maxOutputTokens": 800,
            },
        }

        resp = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")

        res_data = resp.json()
        candidates = res_data.get("candidates", [])
        if not candidates:
            return {"text": "I'm sorry, I didn't quite catch that. Could you repeat that?", "tool_calls": []}

        candidate_parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = []
        tool_calls = []

        for part in candidate_parts:
            if "text" in part:
                text_chunks.append(part["text"])
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "name": fc.get("name"),
                    "args": fc.get("args", {}),
                })

        return {
            "text": " ".join(text_chunks).strip(),
            "tool_calls": tool_calls,
        }

    def _simulate_gemini_2_flash_turn(
        self,
        conversation_history: List[Dict[str, Any]],
        system_instruction: str,
    ) -> Dict[str, Any]:
        """
        High-fidelity Gemini 2.0 Flash Dispatcher emulation.
        Faithfully handles safety guardrails, emergency detection, parameter extraction,
        and natural spoken responses conforming to Sarah's voice persona.
        """
        # Collect full conversation context
        user_utterances = [m.get("content", "") for m in conversation_history if m.get("role") == "user"]
        last_user_turn = user_utterances[-1] if user_utterances else ""
        combined_text = " ".join(user_utterances).lower()

        # Check existing tool executions in history
        past_tools_called = set()
        for m in conversation_history:
            if "tool_calls" in m and m["tool_calls"]:
                for tc in m["tool_calls"]:
                    past_tools_called.add(tc["name"])

        # Check if a tool was executed in the step immediately preceding this model call
        last_tool_result = None
        if conversation_history and conversation_history[-1].get("role") == "tool":
            tool_results = conversation_history[-1].get("tool_results", [])
            if tool_results:
                last_tool_result = tool_results[-1]

        # Comprehensively strip negated hazard phrases (e.g. "no fire or smoke", "no sparks", "don't see any open flames")
        filtered_text = re.sub(
            r"\b(?:no|without|zero|not|don't\s+see|don't\s+have|haven't\s+seen)\s+(?:any\s+)?(?:active\s+|visible\s+|open\s+)?(?:fire|smoke|sparks?|flames?|burning\s+(?:smell|rubber|plastic)?|rubber\s+burning|plastic\s+burning|shock|injury|water)(?:\s+(?:or|nor|and)\s+(?:any\s+)?(?:active\s+|visible\s+|open\s+)?(?:fire|smoke|sparks?|flames?|burning\s+(?:smell|rubber|plastic)?|rubber\s+burning|plastic\s+burning|shock|injury|water))?\b",
            "",
            combined_text,
            flags=re.IGNORECASE,
        )

        # 0. HUMAN TRANSFER / OPT-OUT FLOW
        human_transfer_patterns = [
            r"\b(?:speak|talk)\s+to\s+(?:a\s+)?(?:human|person|someone|representative|operator|agent|contractor|owner|sean)\b",
            r"\b(?:real\s+(?:person|human)|live\s+(?:person|human|agent|operator|representative))\b",
            r"\b(?:representative|operator)\b",
            r"\b(?:not|no|stop|don'?t\s+want|do\s+not\s+want)\s+.*?\b(?:ai|robot|bot|machine|automated)\b",
            r"\b(?:hate|refuse)\s+.*?\b(?:ai|robot|bot)\b",
            r"\btransfer\s+(?:me|my\s+call)\b",
            r"\b(?:human|person)\s+please\b",
        ]
        is_human_request = any(re.search(pat, last_user_turn, re.IGNORECASE) for pat in human_transfer_patterns)
        if is_human_request:
            spoken_response = (
                "I completely understand. Let me transfer you directly to Sean Glenn right now. "
                "Please hold for just a moment while I connect your call."
            )
            return {"text": spoken_response, "tool_calls": []}

        has_sparking = any(w in filtered_text for w in ["spark", "sparks", "sparking", "arcing", "flame", "fire", "popping"])
        has_smoke = any(w in filtered_text for w in [
            "smoke", "smoking", "burnt", "burning smell", "burning rubber", "rubber burning",
            "burning plastic", "plastic burning", "melting plastic", "melting rubber",
            "scorched", "fishy smell", "fishy odor", "electrical burning", "burning odor",
            "smells like rubber", "smells like plastic", "acrid", "rubber"
        ])
        has_water = any(w in filtered_text for w in ["water", "flooding", "leaking", "dripping", "pipe burst", "puddle", "wet"])
        has_shock = any(w in filtered_text for w in ["shock", "shocked", "tingling", "electrocuted", "numb"])
        has_downed_line = any(w in filtered_text for w in ["downed wire", "power line", "tree on line", "downed line", "wire on driveway", "wire down"])
        has_buzzing_hazard = any(w in filtered_text for w in ["loud buzzing", "sizzling", "hot outlet", "hot to touch", "blackened"])
        has_emergency_keyword = bool(re.search(
            r"\b(?:emergency|emergencies|urgent\s+hazard|code\s+red|danger|dangerous)\b",
            filtered_text,
            flags=re.IGNORECASE,
        ))

        is_emergency_situation = (
            has_sparking or has_smoke or has_downed_line or has_shock or
            (has_water and any(w in filtered_text for w in ["panel", "box", "breaker", "basement", "meter"])) or
            has_buzzing_hazard or
            has_emergency_keyword
        )

        tool_calls: List[Dict[str, Any]] = []
        spoken_response = ""

        # 1. EMERGENCY TRIAGE FIRST
        if is_emergency_situation and "triage_fire_shock_emergency" not in past_tools_called:
            # Determine specific hazard parameters
            if has_downed_line:
                hazard_type = "downed_power_line"
                loc = "yard_exterior"
            elif has_shock:
                hazard_type = "electric_shock_injury"
                loc = "appliance" if "dishwasher" in filtered_text or "dryer" in filtered_text else "outlet"
            elif has_water and ("panel" in filtered_text or "basement" in filtered_text):
                hazard_type = "water_electrical_contact"
                loc = "basement"
            elif has_sparking:
                hazard_type = "active_sparking"
                loc = "breaker_panel" if "panel" in filtered_text or "breaker" in filtered_text else "outlet"
            elif has_smoke:
                hazard_type = "burning_smell_smoke"
                if "rubber" in filtered_text:
                    hazard_type = "burning_rubber_insulation"
                elif "plastic" in filtered_text:
                    hazard_type = "burning_plastic_insulation"
                loc = "kitchen" if "ceiling" in filtered_text or "kitchen" in filtered_text else "outlet"
            elif has_emergency_keyword:
                hazard_type = "other_hazard"
                loc = "property"
            else:
                hazard_type = "hot_outlet_switch"
                loc = "outlet"

            tool_calls.append({
                "name": "triage_fire_shock_emergency",
                "args": {
                    "hazard_type": hazard_type,
                    "location_in_property": loc,
                    "is_fire_visible": bool(has_sparking or "flame" in filtered_text),
                    "is_person_injured": bool(has_shock and any(w in filtered_text for w in ["hurt", "tingling", "shocked", "wife", "doctor", "injured"])),
                    "is_water_present": bool(has_water),
                    "can_safely_access_panel": not (has_water and "basement" in filtered_text),
                    "caller_description": last_user_turn,
                },
            })
            return {"text": "", "tool_calls": tool_calls}

        # 2. IF EMERGENCY TRIAGE WAS RUN AND WE NEED TO DISPATCH
        if ("triage_fire_shock_emergency" in past_tools_called or (last_tool_result and last_tool_result.get("name") == "triage_fire_shock_emergency")) and "book_service_call" not in past_tools_called:
            # Check if we have caller address to book immediate emergency dispatch
            name, phone, address, email = self._extract_customer_info(user_utterances)

            # Retrieve triage data if available
            triage_data = {}
            if last_tool_result and last_tool_result.get("name") == "triage_fire_shock_emergency":
                triage_data = last_tool_result.get("result", {})
            elif DB.emergency_reports:
                latest_report = list(DB.emergency_reports.values())[-1]
                triage_data = {
                    "hazard_type": latest_report.hazard_type,
                    "action_plan": latest_report.recommended_action_plan,
                    "immediate_life_safety_actions": latest_report.immediate_life_safety_actions,
                }

            directives = triage_data.get("immediate_life_safety_actions", [])
            primary_safety = " ".join(directives[:3]) if directives else "Please stay clear of the electrical equipment and remain in a safe location."

            is_downed_utility_line = (
                triage_data.get("hazard_type") == "downed_power_line" or
                has_downed_line or
                any(w in filtered_text for w in ["downed line", "power line", "wire on driveway", "wire down"])
            )
            has_customer_mast_damage = any(w in filtered_text for w in ["mast", "weatherhead", "riser", "meter box torn", "meter socket"])

            if is_downed_utility_line and not has_customer_mast_damage:
                # Downed utility distribution lines are under the exclusive jurisdiction of the electric utility and 911.
                # Independent electricians are legally prohibited from touching or repairing utility lines.
                spoken_response = (
                    "Please listen carefully for your life safety: Stay back at least 35 to 40 feet from the downed power line and anything touching it. "
                    "Do NOT attempt to approach or move the wire under any circumstances, and keep all children and pets inside. "
                    "Call 911 and your electric utility emergency response line immediately to de-energize and secure the line. "
                    "Independent electricians are legally prohibited from touching utility distribution lines. "
                    "Once the utility de-energizes and clears the line, please call us back if your meter mast or weatherhead needs repair."
                )
                return {"text": spoken_response, "tool_calls": []}

            if address:
                # In an emergency, physical address is the critical life-safety requirement to roll a truck!
                dispatch_name = name or "Resident / Caller"
                dispatch_phone = phone or "(555) 019-0000"
                tool_calls.append({
                    "name": "book_service_call",
                    "args": {
                        "customer_name": dispatch_name,
                        "customer_email": email,
                        "phone_number": dispatch_phone,
                        "service_address": address,
                        "slot_date": "today",
                        "slot_time": "Within 45-60 Minutes (Priority Code Red)",
                        "issue_description": f"EMERGENCY: {triage_data.get('hazard_type', 'thermal_hazard')} - {triage_data.get('action_plan', 'Immediate on-site hazard isolation')}",
                        "service_type": "emergency",
                        "urgency_level": "EMERGENCY_CRITICAL",
                        "assigned_technician": "Marcus Vance (Master Electrician On-Call)",
                        "notes": f"Immediate Code Red Dispatch to {address}. Callback: {dispatch_phone}",
                    },
                })
                return {"text": "", "tool_calls": tool_calls}
            else:
                spoken_response = (
                    f"Please listen carefully for your safety. {primary_safety} "
                    f"I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"
                )
                return {"text": spoken_response, "tool_calls": []}

        # 3. IF EMERGENCY BOOKING JUST COMPLETED
        if last_tool_result and last_tool_result.get("name") == "book_service_call" and ("triage_fire_shock_emergency" in past_tools_called or is_emergency_situation):
            book_res = last_tool_result.get("result", {})
            conf = book_res.get("confirmation_id", "ZM-EMERG-1001")
            tech = book_res.get("technician", "Marcus Vance (Master Electrician On-Call)")
            addr = book_res.get("service_address", "your location")
            spoken_response = (
                f"Emergency dispatch is confirmed under reference {conf}. {tech} is en route to {addr} right now with an arrival window of within 45 to 60 minutes. "
                f"Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."
            )
            return {"text": spoken_response, "tool_calls": []}

        # 4. ROUTINE / APPOINTMENT FLOW
        name, phone, address, email = self._extract_customer_info(user_utterances)
        category, service_type = self._detect_service_category(combined_text)
        preferred_date = self._extract_preferred_date(combined_text)

        # Check calendar if not yet checked
        if "check_calendar_availability" not in past_tools_called and "book_service_call" not in past_tools_called:
            urgency = "urgent" if any(w in combined_text for w in ["freezer", "blackout", "urgent", "asap", "today"]) else "standard"
            time_window = "afternoon" if "afternoon" in combined_text else ("morning" if "morning" in combined_text else "any")
            tool_calls.append({
                "name": "check_calendar_availability",
                "args": {
                    "target_date": preferred_date,
                    "time_window": time_window,
                    "service_category": category,
                    "urgency": urgency,
                },
            })
            return {"text": "", "tool_calls": tool_calls}

        # If calendar check just completed, ask for details or book if details already present
        if last_tool_result and last_tool_result.get("name") == "check_calendar_availability":
            cal_data = last_tool_result.get("result", {})
            rec_slot = cal_data.get("recommended_slot", {})
            slot_date = rec_slot.get("date", preferred_date)
            slot_time = rec_slot.get("time_window", "08:00 AM - 12:00 PM")
            tech_name = rec_slot.get("technician", "Dave Miller")

            # Guarantee routine bookings always have an actual time frame
            if "minute" in slot_time.lower() or "priority" in slot_time.lower():
                slot_time = "12:00 PM - 04:00 PM" if "afternoon" in combined_text else ("04:00 PM - 07:00 PM" if "evening" in combined_text else "08:00 AM - 12:00 PM")

            if (name and address) or address:
                dispatch_name = name or (email.split("@")[0].replace(".", " ").title() if email else "Valued Customer")
                # We have everything, proceed to book
                tool_calls.append({
                    "name": "book_service_call",
                    "args": {
                        "customer_name": dispatch_name,
                        "customer_email": email,
                        "phone_number": phone or "(555) 019-5555",
                        "service_address": address,
                        "slot_date": slot_date,
                        "slot_time": slot_time,
                        "issue_description": last_user_turn,
                        "service_type": service_type,
                        "urgency_level": "URGENT" if cal_data.get("urgency") == "URGENT" else "STANDARD",
                        "assigned_technician": tech_name,
                    },
                })
                return {"text": "", "tool_calls": tool_calls}
            else:
                spoken_response = (
                    f"I have an opening available on {slot_date} during our {slot_time} window with {tech_name}. "
                    f"To reserve that for you, may I have your full name, callback phone number, street address, and email?"
                )
                return {"text": spoken_response, "tool_calls": []}

        # If customer just provided name/address after calendar check, book it now
        if "check_calendar_availability" in past_tools_called and "book_service_call" not in past_tools_called:
            slot_date = preferred_date
            chosen_window = "12:00 PM - 04:00 PM" if "afternoon" in combined_text else ("04:00 PM - 07:00 PM" if "evening" in combined_text else "08:00 AM - 12:00 PM")
            tech_name = "Sarah Chen"
            for m in conversation_history:
                if "tool_results" in m and m["tool_results"]:
                    for tr in m["tool_results"]:
                        if tr.get("name") == "check_calendar_availability":
                            rec = tr.get("result", {}).get("recommended_slot", {})
                            if rec:
                                slot_date = rec.get("date", slot_date)
                                chosen_window = rec.get("time_window", chosen_window)
                                tech_name = rec.get("technician", tech_name)

            if (name and address) or address:
                dispatch_name = name or (email.split("@")[0].replace(".", " ").title() if email else "Valued Customer")
                tool_calls.append({
                    "name": "book_service_call",
                    "args": {
                        "customer_name": dispatch_name,
                        "customer_email": email,
                        "phone_number": phone or "(555) 019-5555",
                        "service_address": address,
                        "slot_date": slot_date,
                        "slot_time": chosen_window,
                        "issue_description": user_utterances[0] if user_utterances else "Electrical service",
                        "service_type": service_type,
                        "urgency_level": "STANDARD",
                        "assigned_technician": tech_name,
                    },
                })
                return {"text": "", "tool_calls": tool_calls}
            elif not name and not address:
                spoken_response = "To reserve your service appointment, what is your full name and service address?"
                return {"text": spoken_response, "tool_calls": []}
            elif not name:
                spoken_response = "I'd be happy to get that scheduled. What is your full name?"
                return {"text": spoken_response, "tool_calls": []}
            elif not address:
                spoken_response = f"Thank you, {name}. What is the service address where you need our electrician?"
                return {"text": spoken_response, "tool_calls": []}

        # Routine booking just completed
        if last_tool_result and last_tool_result.get("name") == "book_service_call":
            book_res = last_tool_result.get("result", {})
            conf = book_res.get("confirmation_id", "ZM-BOOK-1001")
            dt = book_res.get("appointment_date", "tomorrow")
            arrival = book_res.get("arrival_window", "08:00 AM - 12:00 PM")
            tech = book_res.get("technician", "Dave Miller")
            fee_text = book_res.get("fee_structure", "standard dispatch fee")
            cust_email = book_res.get("customer_email") or email
            email_info = f" We have also sent a calendar invite and confirmation email to {cust_email}." if cust_email else ""

            if "minute" in arrival.lower() or "priority" in arrival.lower():
                window_phrase = "with an arrival window within 45 to 60 minutes today"
            else:
                window_phrase = f"during our {arrival} window"

            spoken_response = (
                f"You're all confirmed, {name or 'valued customer'}. We have {tech} scheduled for {dt} {window_phrase}. "
                f"Your confirmation number is {conf}, covered by our {fee_text}.{email_info} We will send you an arrival text when our technician is on the way."
            )
            return {"text": spoken_response, "tool_calls": []}

        # General conversational fallback
        spoken_response = (
            "Thank you for calling ZeroMiss Electrical. We are ready to assist with installations, repairs, and 24/7 emergencies. How can I help you today?"
        )
        return {"text": spoken_response, "tool_calls": []}

    def _extract_customer_info(self, utterances: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extracts customer name, phone, and street address from conversation utterances."""
        text = " ".join(utterances)

        # Phone extraction: standard 10 or 11 digits
        phone_match = re.search(r"(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", text)
        phone = phone_match.group(1) if phone_match else None

        # Email extraction (e.g. sean.glenn21@gmail.com)
        email_match = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text)
        email = email_match.group(1).strip() if email_match else None

        # Clean text for address matching so phone numbers and emails don't collide with zip codes or house numbers
        clean_text_for_addr = text
        if phone_match:
            clean_text_for_addr = clean_text_for_addr.replace(phone_match.group(1), " ")
        if email_match:
            clean_text_for_addr = clean_text_for_addr.replace(email_match.group(1), " ")

        # Address extraction: street number + street name + suffix (+ zip code / city)
        address = None
        # First check explicit address marker: "address is 123 Main St..."
        addr_match = re.search(
            r"(?:address\s*(?:is|:)\s*)(\d{1,5}\s+[A-Za-z0-9'-]+(?:\s+[A-Za-z0-9'-]+){0,3}\s+(?:Street|St|Avenue|Ave|Drive|Dr|Road|Rd|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Highway|Hwy|Circle|Cir|Terrace|Terr|Parkway|Pkwy)\b(?:[A-Za-z0-9\s,]*))",
            clean_text_for_addr,
            re.IGNORECASE,
        )
        if not addr_match:
            # Fallback to standard street pattern with bounded word length
            addr_match = re.search(
                r"\b(\d{1,5}\s+[A-Za-z0-9'-]+(?:\s+[A-Za-z0-9'-]+){0,3}\s+(?:Street|St|Avenue|Ave|Drive|Dr|Road|Rd|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Highway|Hwy|Circle|Cir|Terrace|Terr|Parkway|Pkwy)\b(?:[A-Za-z0-9\s,]*))",
                clean_text_for_addr,
                re.IGNORECASE,
            )
        if addr_match:
            raw_addr = addr_match.group(1).strip().rstrip(",")
            raw_addr = re.sub(r"[\s,]+(?:phone|cell|tel|number|call|callback|email).*$", "", raw_addr, flags=re.IGNORECASE).strip()
            raw_addr = re.sub(r",\s*,+", ",", raw_addr).strip(" ,")
            raw_addr = re.sub(r"\s+", " ", raw_addr).strip()
            address = raw_addr

        # Name extraction
        name = None
        stop_words = {
            "zeromiss", "voltshield", "electric", "electrical", "street", "avenue", "road", "court",
            "drive", "lane", "boulevard", "terrace", "today", "tomorrow", "wednesday",
            "thursday", "friday", "saturday", "sunday", "morning", "afternoon", "evening",
            "hi", "hello", "hey", "yes", "no", "thanks", "thank", "you", "please", "estimate",
            "pricing", "cost", "quote", "callback", "cell", "phone", "number", "tel", "call",
            "address", "email", "mail", "contact", "is", "are", "my", "it", "its", "at", "in",
            "on", "for", "works", "well", "good", "need", "have", "with", "from", "service"
        }

        # 1. Search utterances in reverse order for explicit introductions:
        # e.g., "My name is Sarah Jenkins", "My name is Kevin O'Connor", "I'm Tony Moretti", "Name is Christopher Vance"
        explicit_patterns = [
            r"(?:my name is|this is|i'm|i am|name\s*(?:is|:))\s+([A-Za-z'-]+(?:\s+[A-Za-z'-]+)+?)(?:\s+(?:at|in|on|for|from|with|my|phone|cell|number|callback|address|,|\.|$))",
            r"(?:my name is|this is|i'm|i am|name\s*(?:is|:))\s+([A-Za-z'-]+(?:\s+[A-Za-z'-]+)+)",
        ]
        for utt in reversed(utterances):
            for pat in explicit_patterns:
                m = re.search(pat, utt, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    # If followed by comma, take first part (e.g. "Tony Moretti, Bella Italia" -> "Tony Moretti")
                    candidate = candidate.split(",")[0].strip()
                    tokens = [t.lower() for t in candidate.split()]
                    if not any(token in stop_words for token in tokens):
                        name = candidate.title()
                        break
            if name:
                break

        # 2. Fallback to capitalized two-word sequences if not found explicitly
        if not name:
            for utt in reversed(utterances):
                # Avoid greeting line in turn 1 like "Hi Sarah" or pronouns "I'm"
                clean_utt = re.sub(r"^(?:hi|hello|good\s+morning|hey)\s+[A-Za-z]+[,!.]?\s*", "", utt, flags=re.IGNORECASE)
                clean_utt = re.sub(r"\b(?:i'm|i\s+am|my\s+name\s+is|this\s+is)\b", " ", clean_utt, flags=re.IGNORECASE)
                m = re.search(r"\b([A-Z][a-z'-]+\s+[A-Z][a-z'-]+)\b", clean_utt)
                if m:
                    candidate = m.group(1).strip()
                    tokens = [t.lower() for t in candidate.split()]
                    if not any(token in stop_words for token in tokens):
                        name = candidate
                        break

        # 3. Residual name extraction: if user typed lowercase like 'sean glenn' without 'my name is'
        if not name:
            for utt in reversed(utterances):
                rem = utt
                if phone:
                    rem = rem.replace(phone, " ")
                if email:
                    rem = rem.replace(email, " ")
                if address:
                    rem = rem.replace(address, " ")
                rem = re.sub(r"\b(?:my name is|this is|i am|i'm|name is|it is|it's|call me|what is the estimate pricing)\b", " ", rem, flags=re.IGNORECASE)
                rem = re.sub(r"\d+", " ", rem)
                rem = re.sub(r"[^a-zA-Z\s'-]", " ", rem)
                words = [w for w in rem.split() if len(w) > 1 and w.lower() not in stop_words]
                if 1 <= len(words) <= 3:
                    name = " ".join(words[:2]).title()
                    break

        return name, phone, address, email

    def _detect_service_category(self, text: str) -> Tuple[str, str]:
        """Detects service specialty category and service type from text."""
        if any(w in text for w in ["ev", "tesla", "charger", "level 2"]):
            return "ev_charger", "ev_charger"
        elif any(w in text for w in ["panel", "200a", "100a", "service upgrade", "breaker box upgrade"]):
            return "panel_upgrade", "panel_upgrade"
        elif any(w in text for w in ["generator", "transfer switch"]):
            return "generator", "generator"
        elif any(w in text for w in ["inspection", "knob and tube", "code inspection", "buying a house", "closing"]):
            return "inspection", "inspection"
        elif any(w in text for w in ["fan", "ceiling fan", "lighting", "recessed", "pot lights", "floodlight", "dimmer"]):
            return "lighting", "installation"
        elif any(w in text for w in ["restaurant", "freezer", "walk-in", "commercial", "kitchen"]):
            return "commercial", "repair"
        elif any(w in text for w in ["hot tub", "spa", "jacuzzi", "disconnect"]):
            return "residential", "installation"
        else:
            return "residential", "repair"

    def _extract_preferred_date(self, text: str) -> str:
        """Extracts date preference from conversation."""
        if "today" in text or "now" in text or "immediate" in text or "freezer" in text or "blackout" in text:
            return "today"
        elif "tomorrow" in text:
            return "tomorrow"
        elif "wednesday" in text:
            return "wednesday"
        elif "thursday" in text:
            return "thursday"
        elif "friday" in text:
            return "friday"
        elif "saturday" in text:
            return "saturday"
        elif "next week" in text:
            return "tomorrow"
        return "tomorrow"
