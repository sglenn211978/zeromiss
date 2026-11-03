"""In-memory and SQLite storage for ZeroMiss dispatch operations."""

import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from phone_agent.models import (
    CalendarSlot,
    EmergencySeverity,
    EmergencyTriageReport,
    ServiceBooking,
    Technician,
    UrgencyLevel,
)


class DispatchDatabase:
    """Thread-safe state store for technicians, schedule slots, bookings, and emergency reports."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.technicians: Dict[str, Technician] = {}
        self.calendar_slots: Dict[str, CalendarSlot] = {}
        self.bookings: Dict[str, ServiceBooking] = {}
        self.emergency_reports: Dict[str, EmergencyTriageReport] = {}
        self._booking_counter = 1000
        self._emergency_counter = 5000
        self._init_sqlite()
        self.seed_defaults()

    def _init_sqlite(self):
        """Initializes SQLite schema if using persistent or file db."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS technicians (
                    technician_id TEXT PRIMARY KEY,
                    name TEXT,
                    license_type TEXT,
                    phone TEXT,
                    is_on_call INTEGER,
                    specialties TEXT,
                    rating REAL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS calendar_slots (
                    slot_id TEXT PRIMARY KEY,
                    date TEXT,
                    time_window TEXT,
                    time_window_key TEXT,
                    technician_id TEXT,
                    technician_name TEXT,
                    is_booked INTEGER,
                    service_categories TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    confirmation_id TEXT PRIMARY KEY,
                    customer_name TEXT,
                    phone_number TEXT,
                    service_address TEXT,
                    slot_date TEXT,
                    slot_time TEXT,
                    issue_description TEXT,
                    service_type TEXT,
                    urgency_level TEXT,
                    assigned_technician TEXT,
                    dispatch_fee REAL,
                    status TEXT,
                    created_at TEXT,
                    notes TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS emergency_reports (
                    triage_case_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    hazard_type TEXT,
                    location_in_property TEXT,
                    severity_level TEXT,
                    is_fire_visible INTEGER,
                    is_person_injured INTEGER,
                    is_water_present INTEGER,
                    can_safely_access_panel INTEGER,
                    immediate_life_safety_actions TEXT,
                    emergency_dispatch_recommended INTEGER,
                    utility_shutoff_required INTEGER,
                    recommended_action_plan TEXT,
                    notes TEXT
                )
                """
            )
            conn.commit()
            conn.close()

    def seed_defaults(self, base_date: Optional[str] = None):
        """Seeds default technician roster and 7 days of calendar availability."""
        with self._lock:
            self.technicians.clear()
            self.calendar_slots.clear()

            # Seed Technicians
            tech_roster = [
                Technician(
                    technician_id="TECH-01",
                    name="Marcus Vance",
                    license_type="Master Electrician",
                    phone="(555) 019-2831",
                    is_on_call=True,
                    specialties=["emergency", "panel_upgrade", "commercial_repair", "high_voltage"],
                    rating=4.98,
                ),
                Technician(
                    technician_id="TECH-02",
                    name="Dave Miller",
                    license_type="Journeyman Electrician",
                    phone="(555) 019-4482",
                    is_on_call=False,
                    specialties=["residential_repair", "lighting", "remodeling", "fans"],
                    rating=4.92,
                ),
                Technician(
                    technician_id="TECH-03",
                    name="Sarah Chen",
                    license_type="EV & Commercial Specialist",
                    phone="(555) 019-7721",
                    is_on_call=False,
                    specialties=["ev_charger", "commercial_repair", "generator", "panel_upgrade"],
                    rating=4.96,
                ),
                Technician(
                    technician_id="TECH-04",
                    name="Luis Ortiz",
                    license_type="Service Electrician",
                    phone="(555) 019-6639",
                    is_on_call=True,
                    specialties=["residential_repair", "emergency", "inspection", "lighting"],
                    rating=4.89,
                ),
            ]
            for t in tech_roster:
                self.technicians[t.technician_id] = t

            # Determine date range starting from base_date or today
            if not base_date:
                today = datetime.now().date()
            else:
                today = datetime.strptime(base_date, "%Y-%m-%d").date()

            slot_idx = 1
            windows = [
                ("morning", "08:00 AM - 12:00 PM"),
                ("afternoon", "12:00 PM - 04:00 PM"),
                ("evening", "04:00 PM - 07:00 PM"),
            ]

            # Generate slots for 7 days
            for d_offset in range(7):
                current_date = (today + timedelta(days=d_offset)).strftime("%Y-%m-%d")

                # Emergency 24/7 on-call slots (always available for on-call techs)
                emergency_slot = CalendarSlot(
                    slot_id=f"SLOT-EMERG-{current_date}",
                    date=current_date,
                    time_window="Within 45-60 Minutes (Priority Code Red)",
                    time_window_key="emergency_asap",
                    technician_id="TECH-01",
                    technician_name="Marcus Vance (Master Electrician On-Call)",
                    is_booked=False,
                    service_categories=["emergency_dispatch", "high_voltage"],
                )
                self.calendar_slots[emergency_slot.slot_id] = emergency_slot

                # Standard technician slots
                for tech in tech_roster:
                    for win_key, win_label in windows:
                        # Stagger slots so some are morning, some afternoon
                        if win_key == "evening" and not tech.is_on_call:
                            continue  # Only on-call techs do standard evening windows

                        s_id = f"SLOT-{slot_idx:04d}"
                        slot_idx += 1
                        slot = CalendarSlot(
                            slot_id=s_id,
                            date=current_date,
                            time_window=win_label,
                            time_window_key=win_key,
                            technician_id=tech.technician_id,
                            technician_name=tech.name,
                            is_booked=False,
                            service_categories=tech.specialties,
                        )
                        self.calendar_slots[s_id] = slot

    def add_technician(
        self,
        name: str,
        license_type: str = "Journeyman Electrician",
        phone: str = "(555) 019-0000",
        is_on_call: bool = False,
        specialties: Optional[List[str]] = None,
        rating: float = 4.95,
    ) -> Technician:
        """Adds a new technician to the fleet and seeds their upcoming calendar slots."""
        with self._lock:
            tid = f"TECH-{len(self.technicians) + 1:02d}"
            tech = Technician(
                technician_id=tid,
                name=name,
                license_type=license_type,
                phone=phone,
                is_on_call=is_on_call,
                specialties=specialties or ["residential_repair", "lighting", "remodeling"],
                rating=rating,
            )
            self.technicians[tid] = tech

            today = datetime.now().date()
            windows = [
                ("08:00 AM - 12:00 PM", "morning"),
                ("12:00 PM - 04:00 PM", "afternoon"),
                ("04:00 PM - 07:00 PM", "evening"),
            ]
            for day_offset in range(1, 8):
                d_str = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                for w_label, w_key in windows:
                    slot_id = f"SLOT-{len(self.calendar_slots) + 1:04d}"
                    self.calendar_slots[slot_id] = CalendarSlot(
                        slot_id=slot_id,
                        date=d_str,
                        time_window=w_label,
                        time_window_key=w_key,
                        technician_id=tid,
                        technician_name=name,
                        is_booked=False,
                        service_categories=specialties or ["residential_repair", "lighting"],
                    )
            return tech

    def get_available_slots(
        self,
        target_date: Optional[str] = None,
        time_window_key: Optional[str] = None,
        service_category: Optional[str] = None,
        limit: int = 5,
    ) -> List[CalendarSlot]:
        """Queries available slots with flexible matching."""
        with self._lock:
            matches = []
            for slot in self.calendar_slots.values():
                if slot.is_booked:
                    continue
                if target_date and slot.date != target_date:
                    continue
                # If emergency_asap is specifically requested:
                if time_window_key == "emergency_asap":
                    if slot.time_window_key != "emergency_asap":
                        continue
                else:
                    # Routine and standard requests should NEVER return emergency slots
                    if slot.time_window_key == "emergency_asap":
                        continue
                    if time_window_key and time_window_key != "any" and slot.time_window_key != time_window_key:
                        continue

                if service_category:
                    cat_clean = service_category.lower().strip()
                    # Allow general match if technician covers it or category is generic
                    if (
                        cat_clean not in ["general", "electrical", "repair"]
                        and cat_clean not in slot.service_categories
                    ):
                        continue
                matches.append(slot)
                if len(matches) >= limit:
                    break
            return matches

    def book_slot(
        self,
        customer_name: str,
        phone_number: str,
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        service_type: str,
        urgency_level: UrgencyLevel,
        assigned_technician: Optional[str] = None,
        dispatch_fee: float = 89.0,
        notes: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> ServiceBooking:
        """Creates and records a confirmed service booking."""
        with self._lock:
            self._booking_counter += 1
            conf_prefix = "ZM-EMERG" if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL else "ZM-BOOK"
            confirmation_id = f"{conf_prefix}-{self._booking_counter}"

            # Auto-assign technician if not specified
            tech_name = assigned_technician
            if not tech_name:
                if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL:
                    tech_name = "Marcus Vance (Master Electrician On-Call)"
                else:
                    tech_name = "Dave Miller (Licensed Journeyman)"

            # Mark matching slot as booked if found
            for slot in self.calendar_slots.values():
                if slot.date == slot_date and (slot_time in slot.time_window or slot.time_window_key in slot_time):
                    slot.is_booked = True
                    break

            status = "DISPATCHED_CODE_RED" if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL else "CONFIRMED"

            booking = ServiceBooking(
                confirmation_id=confirmation_id,
                customer_name=customer_name,
                phone_number=phone_number,
                service_address=service_address,
                slot_date=slot_date,
                slot_time=slot_time,
                issue_description=issue_description,
                service_type=service_type,
                urgency_level=urgency_level,
                assigned_technician=tech_name,
                dispatch_fee=dispatch_fee,
                status=status,
                notes=notes,
                customer_email=customer_email,
                sms_confirmation_sent=True,
            )

            # 1. ALWAYS synchronize dispatch to Electrical Contractor (Sean Glenn: sean.glenn21@gmail.com)
            try:
                from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
                c_info = CALENDAR_SYNC.sync_contractor_dispatch(booking)
                booking.contractor_calendar_link = c_info.get("contractor_calendar_link")
                booking.contractor_ics_path = c_info.get("contractor_ics_path")
                booking.contractor_eml_path = c_info.get("contractor_eml_path")
                booking.contractor_alert_sent = True
            except Exception:
                pass

            # 2. Automatically sync customer confirmation to Google Calendar / iCal if caller email is provided
            if customer_email:
                try:
                    from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
                    sync_info = CALENDAR_SYNC.sync_booking(
                        confirmation_id=confirmation_id,
                        customer_name=customer_name,
                        customer_email=customer_email,
                        service_address=service_address,
                        slot_date=slot_date,
                        slot_time=slot_time,
                        issue_description=issue_description,
                        assigned_technician=tech_name,
                        dispatch_fee=dispatch_fee,
                    )
                    booking.google_calendar_link = sync_info.get("google_calendar_link")
                    booking.calendar_ics_path = sync_info.get("ics_file_path")
                except Exception:
                    pass
            else:
                # Default calendar link to contractor's direct link if customer has no email
                booking.google_calendar_link = booking.contractor_calendar_link
                booking.calendar_ics_path = booking.contractor_ics_path

            self.bookings[confirmation_id] = booking
            return booking

    def record_emergency_triage(
        self,
        hazard_type: str,
        location_in_property: str,
        severity_level: EmergencySeverity,
        is_fire_visible: bool,
        is_person_injured: bool,
        is_water_present: bool,
        can_safely_access_panel: bool,
        immediate_life_safety_actions: List[str],
        emergency_dispatch_recommended: bool,
        utility_shutoff_required: bool,
        recommended_action_plan: str,
        notes: Optional[str] = None,
    ) -> EmergencyTriageReport:
        """Records an emergency triage incident for safety audit and rapid dispatch."""
        with self._lock:
            self._emergency_counter += 1
            triage_case_id = f"EMERG-{self._emergency_counter}"
            report = EmergencyTriageReport(
                triage_case_id=triage_case_id,
                timestamp=datetime.now().isoformat(),
                hazard_type=hazard_type,
                location_in_property=location_in_property,
                severity_level=severity_level,
                is_fire_visible=is_fire_visible,
                is_person_injured=is_person_injured,
                is_water_present=is_water_present,
                can_safely_access_panel=can_safely_access_panel,
                immediate_life_safety_actions=immediate_life_safety_actions,
                emergency_dispatch_recommended=emergency_dispatch_recommended,
                utility_shutoff_required=utility_shutoff_required,
                recommended_action_plan=recommended_action_plan,
                notes=notes,
            )

            # For Level 1 Critical or Level 2 High Hazard, alert contractor Sean Glenn immediately
            if severity_level in (EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY, EmergencySeverity.LEVEL_2_HIGH_HAZARD):
                try:
                    from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
                    alert = CALENDAR_SYNC.send_emergency_contractor_alert(report)
                    report.contractor_alert_sent = True
                    report.contractor_eml_path = alert.get("eml_path")
                except Exception:
                    pass

            self.emergency_reports[triage_case_id] = report
            return report

    def reset(self):
        """Clears bookings and resets state for tests."""
        with self._lock:
            self.bookings.clear()
            self.emergency_reports.clear()
            self.seed_defaults()


# Global DB instance
DB = DispatchDatabase()
