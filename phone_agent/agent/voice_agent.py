"""Voice Dispatch Agent orchestrator for ZeroMiss Electrical."""

import uuid
from typing import Any, Dict, List, Optional
from phone_agent.agent.gemini_client import Gemini2FlashClient
from phone_agent.agent.prompts import DISPATCHER_SYSTEM_INSTRUCTION
from phone_agent.database import DB
from phone_agent.models import CallSession, CallTurn, ToolExecutionResult
from phone_agent.tools.registry import execute_tool


class VoiceDispatchAgent:
    """
    Main conversational agent managing live phone calls, tool executions,
    emergency triage escalation, and appointment bookings.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.client = Gemini2FlashClient(api_key=api_key, model=model)
        self.system_instruction = DISPATCHER_SYSTEM_INSTRUCTION

    def create_session(self, caller_phone: Optional[str] = None) -> CallSession:
        """Initializes a new phone call session."""
        session_id = f"CALL-{uuid.uuid4().hex[:8].upper()}"
        return CallSession(session_id=session_id, caller_phone=caller_phone)

    def process_caller_turn(
        self,
        session: CallSession,
        caller_speech_text: str,
        max_tool_iterations: int = 5,
    ) -> str:
        """
        Processes a single spoken turn from the caller:
        1. Records the caller's utterance in session history.
        2. Queries Gemini 2.0 Flash.
        3. Executes any requested tools (e.g. check_calendar, triage_emergency, book_service).
        4. Cycles tool results back to Gemini until a final spoken response is produced.
        5. Returns the spoken agent response text.
        """
        # Append user turn to history
        session.history.append(CallTurn(role="user", content=caller_speech_text))

        current_iteration = 0
        final_spoken_response = ""

        while current_iteration < max_tool_iterations:
            current_iteration += 1

            # Prepare history for Gemini
            conversation_payload = [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "tool_calls": turn.tool_calls,
                    "tool_results": turn.tool_results,
                }
                for turn in session.history
            ]

            turn_result = self.client.generate_turn(
                conversation_history=conversation_payload,
                system_instruction=self.system_instruction,
            )

            text_output = turn_result.get("text", "")
            tool_calls = turn_result.get("tool_calls", [])

            if tool_calls:
                # Record model's intent to call tools
                session.history.append(
                    CallTurn(
                        role="model",
                        content=text_output,
                        tool_calls=tool_calls,
                    )
                )

                # Execute each tool call
                tool_results_payload = []
                for tc in tool_calls:
                    tool_name = tc.get("name")
                    args = tc.get("args", {})
                    session.tools_invoked.append(tool_name)

                    exec_res: ToolExecutionResult = execute_tool(tool_name, args)

                    # Update session state with booking or emergency report
                    if tool_name == "book_service_call" and exec_res.success:
                        cid = exec_res.data.get("confirmation_id")
                        if cid and cid in DB.bookings:
                            session.active_booking = DB.bookings[cid]
                    elif tool_name == "triage_fire_shock_emergency" and exec_res.success:
                        case_id = exec_res.data.get("case_id")
                        if case_id and case_id in DB.emergency_reports:
                            session.emergency_triage = DB.emergency_reports[case_id]

                    tool_results_payload.append({
                        "name": tool_name,
                        "result": exec_res.data,
                    })

                # Append tool response turn to conversation
                session.history.append(
                    CallTurn(
                        role="tool",
                        content="",
                        tool_results=tool_results_payload,
                    )
                )

                # If text was also provided, store it
                if text_output:
                    final_spoken_response = text_output

                # Loop to get model's synthesized spoken response to the tool results
                continue
            else:
                # Model provided final spoken text
                final_spoken_response = text_output
                session.history.append(
                    CallTurn(
                        role="model",
                        content=final_spoken_response,
                    )
                )
                break

        return final_spoken_response or "Thank you for calling ZeroMiss Electrical. We are processing your request."
