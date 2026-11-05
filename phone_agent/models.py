"""Data models and schemas for ZeroMiss Voice Dispatch Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class UrgencyLevel(str, Enum):
    STANDARD = "STANDARD"
    URGENT = "URGENT"
    EMERGENCY_CRITICAL = "EMERGENCY_CRITICAL"


class EmergencySeverity(str, Enum):
    LEVEL_1_CRITICAL_LIFE_SAFETY = "LEVEL_1_CRITICAL_LIFE_SAFETY"
    LEVEL_2_HIGH_HAZARD = "LEVEL_2_HIGH_HAZARD"
    LEVEL_3_MODERATE_RISK = "LEVEL_3_MODERATE_RISK"
    NONE = "NONE"


class ServiceCategory(str, Enum):
    RESIDENTIAL_REPAIR = "residential_repair"
    COMMERCIAL_REPAIR = "commercial_repair"
    PANEL_UPGRADE = "panel_upgrade"
    EV_CHARGER = "ev_charger"
    LIGHTING = "lighting"
    INSPECTION = "inspection"
    GENERATOR = "generator"
    EMERGENCY_DISPATCH = "emergency_dispatch"


@dataclass
class Technician:
    technician_id: str
    name: str
    license_type: str  # "Master Electrician", "Journeyman Electrician", "Commercial Specialist", "EV Certified Tech"
    phone: str
    is_on_call: bool = False
    specialties: List[str] = field(default_factory=list)
    rating: float = 4.9
    truck_id: str = "TRUCK-01 (Master Emergency Van)"


@dataclass
class CalendarSlot:
    slot_id: str
    date: str  # YYYY-MM-DD
    time_window: str  # "08:00 AM - 12:00 PM"
    time_window_key: str  # "morning", "afternoon", "evening", "emergency_asap"
    technician_id: str
    technician_name: str
    is_booked: bool = False
    service_categories: List[str] = field(default_factory=list)
    is_blocked: bool = False
    blocked_reason: Optional[str] = None
    booking_id: Optional[str] = None


@dataclass
class ServiceBooking:
    confirmation_id: str
    customer_name: str
    phone_number: str
    service_address: str
    slot_date: str
    slot_time: str
    issue_description: str
    service_type: str
    urgency_level: UrgencyLevel
    assigned_technician: str
    dispatch_fee: float
    status: str  # "CONFIRMED", "DISPATCHED_CODE_RED", "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    customer_email: Optional[str] = None
    google_calendar_link: Optional[str] = None
    calendar_ics_path: Optional[str] = None
    notes: Optional[str] = None
    sms_confirmation_sent: bool = True
    # Contractor Dispatch Credentials & Integration
    contractor_name: str = "Sean Glenn"
    contractor_email: str = "sean.glenn21@gmail.com"
    contractor_calendar_link: Optional[str] = None
    contractor_ics_path: Optional[str] = None
    contractor_alert_sent: bool = False
    contractor_eml_path: Optional[str] = None
    # Maximum-ROI Revenue & Payment Integration
    payment_status: str = "PENDING_AUTHORIZATION"  # "PENDING_AUTHORIZATION", "PAID_VERIFIED", "EXEMPT"
    stripe_payment_link: Optional[str] = None
    sms_lead_recovery_sent: bool = False
    estimated_job_value: float = 850.0
    booked_by: str = "Booked by Sarah AI"
    tech_match_reason: str = "Certified • Nearest Available"
    is_demo_seed: bool = False
    truck_id: str = "TRUCK-01 (Master Emergency Van)"
    panel_photo_analysis: Optional[Dict[str, Any]] = None
    en_route_sent: bool = False
    review_requested: bool = False


@dataclass
class EmergencyTriageReport:
    triage_case_id: str
    timestamp: str
    hazard_type: str
    location_in_property: str
    severity_level: EmergencySeverity
    is_fire_visible: bool
    is_person_injured: bool
    is_water_present: bool
    can_safely_access_panel: bool
    immediate_life_safety_actions: List[str]
    emergency_dispatch_recommended: bool
    utility_shutoff_required: bool
    recommended_action_plan: str
    notes: Optional[str] = None
    contractor_alert_sent: bool = False
    contractor_eml_path: Optional[str] = None


@dataclass
class ToolExecutionResult:
    tool_name: str
    success: bool
    data: Dict[str, Any]
    message: str


@dataclass
class CallTurn:
    role: str  # "user" | "model" | "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CallSession:
    session_id: str
    caller_phone: Optional[str] = None
    history: List[CallTurn] = field(default_factory=list)
    active_booking: Optional[ServiceBooking] = None
    emergency_triage: Optional[EmergencyTriageReport] = None
    tools_invoked: List[str] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "IN_PROGRESS"  # "IN_PROGRESS", "COMPLETED", "EMERGENCY_DISPATCHED"
