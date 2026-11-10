"""JobLatch AI Electrical Voice Dispatch Agent package."""

from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.config import DEFAULT_CONFIG, DispatchConfig
from phone_agent.database import DB, DispatchDatabase

__version__ = "1.0.0"

__all__ = [
    "VoiceDispatchAgent",
    "DispatchConfig",
    "DEFAULT_CONFIG",
    "DB",
    "DispatchDatabase",
]
