"""Audio streaming and PCM16 waveform generator for Gemini 2.0 Flash Voice simulation."""

import io
import math
import struct
import wave
from typing import Generator, List, Optional


class AudioStreamSimulator:
    """
    Simulates raw PCM16 audio input and output as used by Gemini 2.0 Flash
    Multimodal Live API (16kHz / 24kHz single-channel 16-bit PCM).
    """

    SAMPLE_RATE = 16000  # 16 kHz
    NUM_CHANNELS = 1     # Mono
    SAMPLE_WIDTH = 2     # 16-bit (2 bytes per sample)

    @classmethod
    def generate_tone_pcm(cls, frequency: float = 440.0, duration_seconds: float = 0.5, volume: float = 0.3) -> bytes:
        """Generates raw PCM16 audio bytes of a pure sine tone (e.g. phone beep/ring)."""
        num_samples = int(cls.SAMPLE_RATE * duration_seconds)
        raw_bytes = bytearray()
        max_amplitude = 32767 * volume

        for i in range(num_samples):
            val = int(max_amplitude * math.sin(2 * math.pi * frequency * (i / cls.SAMPLE_RATE)))
            raw_bytes.extend(struct.pack("<h", val))

        return bytes(raw_bytes)

    @classmethod
    def generate_phone_ring(cls) -> bytes:
        """Generates a standard dual-frequency telephone ring tone (440Hz + 480Hz)."""
        duration = 1.0
        num_samples = int(cls.SAMPLE_RATE * duration)
        raw_bytes = bytearray()
        max_amplitude = 32767 * 0.25

        for i in range(num_samples):
            t = i / cls.SAMPLE_RATE
            val = int(max_amplitude * (0.5 * math.sin(2 * math.pi * 440 * t) + 0.5 * math.sin(2 * math.pi * 480 * t)))
            raw_bytes.extend(struct.pack("<h", val))

        return bytes(raw_bytes)

    @classmethod
    def simulate_speech_pcm(cls, text: str, duration_per_word: float = 0.25) -> bytes:
        """
        Synthesizes simulated vocalized PCM16 audio frames modulated
        according to the syllabic cadence of the input text.
        """
        words = text.split()
        total_duration = max(0.5, len(words) * duration_per_word)
        num_samples = int(cls.SAMPLE_RATE * total_duration)
        raw_bytes = bytearray()

        base_freq = 180.0  # Natural female/male fundamental pitch
        for i in range(num_samples):
            t = i / cls.SAMPLE_RATE
            # Modulate pitch with slight vibrato and syllabic envelope
            envelope = (math.sin(2 * math.pi * 3.5 * t) ** 2) * 0.7 + 0.3
            f0 = base_freq + 20.0 * math.sin(2 * math.pi * 2.0 * t)
            # Add harmonic overtones
            sample_val = (
                0.6 * math.sin(2 * math.pi * f0 * t)
                + 0.3 * math.sin(2 * math.pi * (2 * f0) * t)
                + 0.1 * math.sin(2 * math.pi * (3 * f0) * t)
            )
            val = int(32767 * 0.25 * envelope * sample_val)
            # Clamp
            val = max(-32768, min(32767, val))
            raw_bytes.extend(struct.pack("<h", val))

        return bytes(raw_bytes)

    @classmethod
    def stream_chunks(cls, pcm_bytes: bytes, chunk_size_bytes: int = 1024) -> Generator[bytes, None, None]:
        """Yields streaming chunks of PCM audio to simulate real-time WebSocket frames."""
        for i in range(0, len(pcm_bytes), chunk_size_bytes):
            yield pcm_bytes[i : i + chunk_size_bytes]

    @classmethod
    def save_to_wav(cls, pcm_bytes: bytes, filepath: str):
        """Saves raw PCM16 bytes as a standard playable .wav audio file."""
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(cls.NUM_CHANNELS)
            wf.setsampwidth(cls.SAMPLE_WIDTH)
            wf.setframerate(cls.SAMPLE_RATE)
            wf.writeframes(pcm_bytes)
