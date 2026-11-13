"""Service-area filter: detects the town a caller names and checks it against the configured area."""

import os
import re
from typing import Any, Dict, Iterable, Optional

from phone_agent.config import DEFAULT_CONFIG

# Phrases callers use to say where they are, e.g. "I'm calling from Princeton", "we're in Ewing Township".
_LOCATION_PHRASE = re.compile(
    r"\b(?i:calling\s+from|i'?m\s+in|i\s+am\s+in|we'?re\s+in|we\s+are\s+in|located\s+in|live\s+in|"
    r"house\s+is\s+in|home\s+is\s+in|property\s+is\s+in|over\s+in|out\s+in|up\s+in|down\s+in)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
)
# Town that follows a street address: "418 Oakwood Ave, Cherry Hill, New Jersey"
_ADDRESS_TOWN = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9'. -]+?\s+(?:Street|St|Avenue|Ave|Drive|Dr|Road|Rd|Lane|Ln|Boulevard|Blvd|"
    r"Court|Ct|Way|Circle|Cir|Terrace|Pkwy|Parkway|Place|Pl)\.?,\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
)
_STATE_WORDS = {"new jersey", "nj", "pennsylvania", "pa", "new york", "ny", "delaware", "de"}


def _normalize(town: str) -> str:
    town = re.sub(r"\s+(?:township|twp|borough|boro|city)$", "", town.strip(), flags=re.IGNORECASE)
    return town.lower()


def extract_caller_town(text: str) -> Optional[str]:
    """Returns the town the caller names (from a location phrase or an address), if any."""
    for pattern in (_ADDRESS_TOWN, _LOCATION_PHRASE):
        for match in pattern.finditer(text):
            candidate = match.group(1).strip()
            if _normalize(candidate) not in _STATE_WORDS:
                return candidate
    return None


def check_service_area(text: str, towns: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """
    Checks whether the caller's stated town is inside the service area.

    Returns {"town": str|None, "in_service_area": bool|None, "service_area": [...]}.
    in_service_area is None when no town could be identified (callers are never blocked on a guess).
    """
    if towns is not None:
        area = list(towns)
    elif DEFAULT_CONFIG.service_area_towns:
        area = list(DEFAULT_CONFIG.service_area_towns)
    else:
        env_val = os.getenv("SERVICE_AREA_TOWNS", "").strip()
        area = [t.strip() for t in env_val.split(",") if t.strip()]

    if not area:  # filter disabled
        return {"town": None, "in_service_area": None, "service_area": []}
    town = extract_caller_town(text)
    if town is None:
        return {"town": None, "in_service_area": None, "service_area": area}
    allowed = {_normalize(t) for t in area}
    return {"town": town, "in_service_area": _normalize(town) in allowed, "service_area": area}
