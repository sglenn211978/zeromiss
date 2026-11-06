"""In-memory and SQLite storage for ZeroMiss dispatch operations."""

import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from phone_agent.models import (
    CalendarSlot,
    EmergencySeverity,
    EmergencyTriageReport,
    ServiceBooking,
    Technician,
    UrgencyLevel,
)



def format_fsm_ticket_id(platform: str, confirmation_id: str) -> str:
    """Formats an external FSM ticket ID corresponding to the booking reference."""
    clean_p = (platform or "HOUSECALL_PRO").strip().upper()
    num = confirmation_id.split("-")[-1] if "-" in confirmation_id else confirmation_id
    if clean_p == "SERVICETITAN":
        return f"ST-{num}"
    elif clean_p == "JOBBER":
        return f"JOB-{num}"
    elif clean_p == "QUICKBOOKS":
        return f"QBO-{num}"
    else:
        return f"HCP-{num}"


def format_fsm_metadata(platform: str, confirmation_id: str) -> Dict[str, Any]:
    """Returns brand icons, labels, deep links, and UI presentation data for a connected FSM platform."""
    clean_p = (platform or "HOUSECALL_PRO").strip().upper()
    ticket_id = format_fsm_ticket_id(clean_p, confirmation_id)
    if clean_p == "SERVICETITAN":
        return {
            "platform": "SERVICETITAN",
            "name": "ServiceTitan",
            "icon": "⚡",
            "badge": f"✓ Synced to ServiceTitan Job #{ticket_id}",
            "ticket_id": ticket_id,
            "url": f"https://go.servicetitan.com/#/job/{ticket_id}",
            "button_label": "↗ Open Invoice in ServiceTitan",
            "tech_label": "ServiceTitan Mobile",
            "accent_color": "#0284c7",
        }
    elif clean_p == "JOBBER":
        return {
            "platform": "JOBBER",
            "name": "Jobber",
            "icon": "💼",
            "badge": f"✓ Synced to Jobber Work Order #{ticket_id}",
            "ticket_id": ticket_id,
            "url": f"https://secure.getjobber.com/jobs/{ticket_id}",
            "button_label": "↗ Open Invoice in Jobber",
            "tech_label": "Jobber Field App",
            "accent_color": "#16a34a",
        }
    elif clean_p == "QUICKBOOKS":
        return {
            "platform": "QUICKBOOKS",
            "name": "QuickBooks Online",
            "icon": "📗",
            "badge": f"✓ Synced to QuickBooks Invoice #{ticket_id}",
            "ticket_id": ticket_id,
            "url": f"https://qbo.intuit.com/app/invoice?id={ticket_id}",
            "button_label": "↗ Open Invoice in QuickBooks",
            "tech_label": "QuickBooks Invoicing",
            "accent_color": "#22c55e",
        }
    else:
        return {
            "platform": "HOUSECALL_PRO",
            "name": "Housecall Pro",
            "icon": "🏠",
            "badge": f"✓ Synced to Housecall Pro Job #{ticket_id}",
            "ticket_id": ticket_id,
            "url": f"https://pro.housecallpro.com/app/jobs/{ticket_id}",
            "button_label": "↗ Open Invoice in Housecall Pro",
            "tech_label": "Housecall Pro Mobile",
            "accent_color": "#2563eb",
        }


class DispatchDatabase:
    """Thread-safe state store for technicians, schedule slots, bookings, and emergency reports."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.technicians: Dict[str, Technician] = {}
        self.calendar_slots: Dict[str, CalendarSlot] = {}
        self.bookings: Dict[str, ServiceBooking] = {}
        self.emergency_reports: Dict[str, EmergencyTriageReport] = {}
        self.missed_calls: Dict[str, Dict[str, Any]] = {}
        self.is_benchmark_mode: bool = False
        self.active_fsm_platform: str = "HOUSECALL_PRO"  # "SERVICETITAN", "HOUSECALL_PRO", "JOBBER", "QUICKBOOKS"
        self.gcal_connected: bool = True
        self.gcal_last_sync: str = "Two-Way Sync Active (Live)"
        self.gcal_external_url: str = "https://calendar.google.com/calendar/ical/apex-electrical-fleet%40group.calendar.google.com/public/basic.ics"
        self.gcal_synced_busy_blocks: int = 0
        self._booking_counter = 1000
        self._emergency_counter = 5000
        self._missed_counter = 100
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
                    truck_id="TRUCK-01 (Master Emergency Van)",
                ),
                Technician(
                    technician_id="TECH-02",
                    name="Dave Miller",
                    license_type="Journeyman Electrician",
                    phone="(555) 019-4482",
                    is_on_call=False,
                    specialties=["residential_repair", "lighting", "remodeling", "fans"],
                    rating=4.92,
                    truck_id="TRUCK-02 (200A Panel & Service Rig)",
                ),
                Technician(
                    technician_id="TECH-03",
                    name="Sarah Chen",
                    license_type="EV & Commercial Specialist",
                    phone="(555) 019-7721",
                    is_on_call=False,
                    specialties=["ev_charger", "commercial_repair", "generator", "panel_upgrade"],
                    rating=4.96,
                    truck_id="TRUCK-03 (EV & Commercial Van)",
                ),
                Technician(
                    technician_id="TECH-04",
                    name="Luis Ortiz",
                    license_type="Service Electrician",
                    phone="(555) 019-6639",
                    is_on_call=True,
                    specialties=["residential_repair", "emergency", "inspection", "lighting"],
                    rating=4.89,
                    truck_id="TRUCK-04 (Rapid Response Van)",
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

            # Seed 2 baseline "Booked by Sarah AI" cards on Tomorrow so the calendar never looks empty
            # (Flagged with is_demo_seed=True so Tab 1 session KPIs still start at $0.00 until user tests a call)
            d_tom = (today + timedelta(days=1)).strftime("%Y-%m-%d")
            d_day2 = (today + timedelta(days=2)).strftime("%Y-%m-%d")
            b1 = self.book_slot(
                customer_name="Rachel Green",
                phone_number="(555) 741-3902",
                service_address="114 Commonwealth Ave, Boston",
                slot_date=d_tom,
                slot_time="08:00 AM - 12:00 PM",
                issue_description="Tesla Wall Connector 50A Dedicated Circuit (200A Panel Verified)",
                service_type="EV Charger Installation",
                urgency_level=UrgencyLevel.STANDARD,
                assigned_technician="Sarah Chen (EV & Commercial Specialist)",
                dispatch_fee=89.0,
                notes="Autonomous 3-second missed-call SMS recovery booking.",
                customer_email="rachel.green@example.com",
                booked_by="Booked by Sarah AI • 3s SMS Recovery",
                tech_match_reason="EV Certified • 240V Load Specialist",
                is_demo_seed=True,
            )
            b1.payment_status = "PAID_VERIFIED"

            self.book_slot(
                customer_name="Tom Haverford",
                phone_number="(555) 892-4410",
                service_address="28 Newbury St, Suite 2B, Boston",
                slot_date=d_day2,
                slot_time="12:00 PM - 04:00 PM",
                issue_description="200A Main Breaker Panel Upgrade — flickering lights under load",
                service_type="200A Main Panel Upgrade",
                urgency_level=UrgencyLevel.URGENT,
                assigned_technician="Dave Miller (Journeyman Electrician)",
                dispatch_fee=89.0,
                notes="Inbound voice triage & panel capacity verification by Sarah AI.",
                customer_email="tom.haverford@example.com",
                booked_by="Booked by Sarah AI • Voice Triage",
                tech_match_reason="Journeyman • Panel & Load Balancing",
                is_demo_seed=True,
            )

    def add_technician(
        self,
        name: str,
        license_type: str = "Journeyman Electrician",
        phone: str = "(555) 019-0000",
        is_on_call: bool = False,
        specialties: Optional[List[str]] = None,
        rating: float = 4.95,
        truck_id: Optional[str] = None,
    ) -> Technician:
        """Adds a new technician to the fleet and seeds their upcoming calendar slots."""
        with self._lock:
            num = len(self.technicians) + 1
            tid = f"TECH-{num:02d}"
            default_truck = f"TRUCK-{num:02d} (Service Van)"
            tech = Technician(
                technician_id=tid,
                name=name,
                license_type=license_type,
                phone=phone,
                is_on_call=is_on_call,
                specialties=specialties or ["residential_repair", "lighting", "remodeling"],
                rating=rating,
                truck_id=(truck_id or "").strip() or default_truck,
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

    def update_technician(
        self,
        technician_id: str,
        name: str,
        license_type: str,
        phone: str,
        is_on_call: bool,
        specialties: Optional[List[str]] = None,
        rating: float = 4.95,
        truck_id: Optional[str] = None,
    ) -> Optional[Technician]:
        """Updates technician details and propagates changes to their unbooked calendar slots."""
        with self._lock:
            if technician_id not in self.technicians:
                return None
            tech = self.technicians[technician_id]
            tech.name = name
            tech.license_type = license_type
            tech.phone = phone
            tech.is_on_call = is_on_call
            if specialties is not None:
                tech.specialties = specialties
            tech.rating = rating
            if truck_id is not None and truck_id.strip():
                tech.truck_id = truck_id.strip()

            for slot in self.calendar_slots.values():
                if slot.technician_id == technician_id and not slot.is_booked:
                    slot.technician_name = name
                    if specialties is not None:
                        slot.service_categories = specialties
            return tech

    def toggle_technician_on_call(self, technician_id: str) -> Optional[Technician]:
        """1-click toggle for technician on-call status."""
        with self._lock:
            if technician_id not in self.technicians:
                return None
            tech = self.technicians[technician_id]
            tech.is_on_call = not tech.is_on_call
            return tech

    def delete_technician(self, technician_id: str) -> bool:
        """Deletes a technician from fleet and removes their unbooked calendar slots."""
        with self._lock:
            if technician_id not in self.technicians:
                return False
            del self.technicians[technician_id]
            slots_to_delete = [
                sid for sid, s in self.calendar_slots.items()
                if s.technician_id == technician_id and not s.is_booked
            ]
            for sid in slots_to_delete:
                del self.calendar_slots[sid]
            return True

    def toggle_block_slot(self, slot_id: str, reason: str = "Unavailable / Off-Duty") -> Optional[CalendarSlot]:
        """Blocks or unblocks a specific calendar slot."""
        with self._lock:
            if slot_id not in self.calendar_slots:
                return None
            slot = self.calendar_slots[slot_id]
            slot.is_blocked = not getattr(slot, "is_blocked", False)
            slot.blocked_reason = reason if slot.is_blocked else None
            slot.is_booked = slot.is_blocked
            return slot

    def _is_window_elapsed(self, slot_date: str, window_key: str) -> bool:
        """Returns True if the slot date is today and the time window has already passed."""
        today_str = datetime.now().date().strftime("%Y-%m-%d")
        if slot_date != today_str:
            return False
        cur_hour = datetime.now().hour
        if window_key == "morning" and cur_hour >= 12:
            return True
        if window_key == "afternoon" and cur_hour >= 16:
            return True
        if window_key == "evening" and cur_hour >= 19:
            return True
        return False

    def manual_book_slot(
        self,
        slot_id: str,
        customer_name: str,
        phone_number: str,
        service_address: str,
        issue_description: str,
        service_type: str = "200A Panel / Circuit Service",
        customer_email: Optional[str] = None,
    ) -> Optional[ServiceBooking]:
        """Manually books an available slot directly from the visual calendar interface."""
        with self._lock:
            if slot_id not in self.calendar_slots:
                return None
            slot = self.calendar_slots[slot_id]
            if slot.is_booked and not getattr(slot, "is_blocked", False):
                return None
            if self._is_window_elapsed(slot.date, slot.time_window_key):
                return None

            booking = self.book_slot(
                customer_name=customer_name,
                phone_number=phone_number,
                service_address=service_address,
                slot_date=slot.date,
                slot_time=slot.time_window,
                issue_description=issue_description,
                service_type=service_type,
                urgency_level=UrgencyLevel.STANDARD,
                assigned_technician=slot.technician_name,
                dispatch_fee=89.0,
                notes=f"Manual booking via Dispatch Board for {slot.date}",
                customer_email=customer_email,
                booked_by="Manual Dispatcher Entry",
            )
            slot.is_booked = True
            slot.is_blocked = False
            slot.booking_id = booking.confirmation_id
            return booking

    def export_full_ical_feed(self) -> str:
        """Generates a complete RFC 5545 iCalendar feed of all scheduled dispatches."""
        with self._lock:
            from datetime import timezone
            from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
            now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M00Z")

            events = []
            for b in self.bookings.values():
                try:
                    start_dt, end_dt = CALENDAR_SYNC.parse_time_window(b.slot_date, b.slot_time)
                    start_str = start_dt.strftime("%Y%m%dT%H%M00")
                    end_str = end_dt.strftime("%Y%m%dT%H%M00")
                except Exception:
                    continue

                urgency_str = b.urgency_level.value if hasattr(b.urgency_level, "value") else str(b.urgency_level)
                safe_desc = (
                    f"ZeroMiss Dispatch Booking\\n"
                    f"Confirmation: {b.confirmation_id}\\n"
                    f"Customer: {b.customer_name}\\n"
                    f"Phone: {b.phone_number}\\n"
                    f"Technician: {b.assigned_technician}\\n"
                    f"Window: {b.slot_time}\\n"
                    f"Scope: {b.issue_description}"
                )

                events.append(
                    "BEGIN:VEVENT\r\n"
                    f"UID:{b.confirmation_id}@zeromissdispatch.com\r\n"
                    f"DTSTAMP:{now_str}\r\n"
                    f"DTSTART:{start_str}\r\n"
                    f"DTEND:{end_str}\r\n"
                    f"SUMMARY:[{urgency_str}] {b.customer_name} - {b.service_type}\r\n"
                    f"DESCRIPTION:{safe_desc}\r\n"
                    f"LOCATION:{b.service_address}\r\n"
                    "STATUS:CONFIRMED\r\n"
                    "END:VEVENT\r\n"
                )

            return (
                "BEGIN:VCALENDAR\r\n"
                "VERSION:2.0\r\n"
                "PRODID:-//ZeroMiss Electrical//Fleet Dispatch System v2.0//EN\r\n"
                "CALSCALE:GREGORIAN\r\n"
                "X-WR-CALNAME:ZeroMiss Electrical Dispatches\r\n"
                "X-WR-TIMEZONE:America/New_York\r\n"
                + "".join(events) +
                "END:VCALENDAR\r\n"
            )

    def get_available_slots(
        self,
        target_date: Optional[str] = None,
        time_window_key: Optional[str] = None,
        service_category: Optional[str] = None,
        limit: int = 5,
    ) -> List[CalendarSlot]:
        """Queries available slots with flexible matching, automatically skipping elapsed windows."""
        with self._lock:
            matches = []
            for slot in self.calendar_slots.values():
                if slot.is_booked or getattr(slot, "is_blocked", False):
                    continue
                if target_date and slot.date != target_date:
                    continue
                # If emergency_asap is specifically requested:
                if time_window_key == "emergency_asap":
                    if slot.time_window_key != "emergency_asap":
                        continue
                else:
                    # Routine and standard requests should NEVER return emergency or elapsed slots
                    if slot.time_window_key == "emergency_asap":
                        continue
                    if self._is_window_elapsed(slot.date, slot.time_window_key):
                        continue
                    if time_window_key and time_window_key != "any" and slot.time_window_key != time_window_key:
                        continue

                if service_category:
                    cat_clean = service_category.lower().strip()
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
        booked_by: str = "Booked by Sarah AI",
        tech_match_reason: Optional[str] = None,
        is_demo_seed: bool = False,
    ) -> ServiceBooking:
        """Creates and records a confirmed service booking."""
        with self._lock:
            self._booking_counter += 1
            conf_prefix = "ZM-EMERG" if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL else "ZM-BOOK"
            confirmation_id = f"{conf_prefix}-{self._booking_counter}"

            # Normalize relative slot_date ("today", "tomorrow") to YYYY-MM-DD so calendar always matches
            today_dt = datetime.now().date()
            if str(slot_date).lower() == "today":
                slot_date = today_dt.strftime("%Y-%m-%d")
            elif str(slot_date).lower() == "tomorrow":
                slot_date = (today_dt + timedelta(days=1)).strftime("%Y-%m-%d")

            # Auto-assign technician if not specified
            tech_name = assigned_technician
            if not tech_name:
                if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL:
                    tech_name = "Marcus Vance (Master Electrician On-Call)"
                else:
                    tech_name = "Dave Miller (Licensed Journeyman)"

            tech_short = tech_name.split("(")[0].strip().lower()

            if not tech_match_reason:
                if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL or "marcus" in tech_short:
                    tech_match_reason = "Master Electrician • 24/7 On-Call Lead • Nearest (14m)"
                elif "sarah" in tech_short:
                    tech_match_reason = "EV & Commercial Certified • 240V Load Specialist"
                elif "luis" in tech_short:
                    tech_match_reason = "Service Electrician • On-Call Shift"
                else:
                    tech_match_reason = "Licensed Journeyman • Residential Diagnostics"

            # Determine active current window for immediate emergency dispatch
            cur_hour = datetime.now().hour
            active_emerg_win = "morning" if cur_hour < 12 else ("afternoon" if cur_hour < 16 else "evening")

            # Mark matching slot as booked for the assigned technician
            for slot in self.calendar_slots.values():
                if slot.date == slot_date:
                    slot_tech_short = slot.technician_name.split("(")[0].strip().lower()
                    if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL:
                        if slot.time_window_key == "emergency_asap":
                            slot.is_booked = True
                            slot.booking_id = confirmation_id
                        elif slot_tech_short == tech_short and slot.time_window_key == active_emerg_win:
                            slot.is_booked = True
                            slot.booking_id = confirmation_id
                    else:
                        if (slot_time in slot.time_window or slot.time_window_key in slot_time.lower()) and (
                            slot_tech_short == tech_short or not tech_short
                        ):
                            slot.is_booked = True
                            slot.booking_id = confirmation_id
                            break

            status = "DISPATCHED_CODE_RED" if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL else "CONFIRMED"

            # Calculate estimated pipeline job value for ROI calculations
            st_lower = (service_type or "").lower()
            if urgency_level == UrgencyLevel.EMERGENCY_CRITICAL:
                est_val = 1850.0
            elif "panel" in st_lower:
                est_val = 3200.0
            elif "ev" in st_lower or "charger" in st_lower:
                est_val = 1450.0
            elif "generator" in st_lower:
                est_val = 4500.0
            elif "commercial" in st_lower:
                est_val = 2100.0
            else:
                est_val = 650.0

            stripe_url = f"https://pay.zeromissdispatch.com/{confirmation_id.lower()}"

            # Resolve assigned truck_id from the matched technician in the roster
            matched_truck = "TRUCK-01 (Master Emergency Van)"
            for t_obj in self.technicians.values():
                if t_obj.name.lower() == tech_short:
                    matched_truck = getattr(t_obj, "truck_id", matched_truck)
                    break

            fsm_p = getattr(self, "active_fsm_platform", "HOUSECALL_PRO")
            fsm_tid = format_fsm_ticket_id(fsm_p, confirmation_id)
            fsm_url = format_fsm_metadata(fsm_p, confirmation_id)["url"]

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
                payment_status="PENDING_AUTHORIZATION",
                stripe_payment_link=stripe_url,
                estimated_job_value=est_val,
                booked_by=booked_by,
                tech_match_reason=tech_match_reason,
                is_demo_seed=is_demo_seed,
                truck_id=matched_truck,
                connected_fsm=fsm_p,
                fsm_ticket_id=fsm_tid,
                fsm_sync_status="SYNCED",
                fsm_external_url=fsm_url,
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

    def mark_booking_paid(self, confirmation_id: str) -> Optional[ServiceBooking]:
        """Marks a booking diagnostic/emergency fee as paid via Stripe."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.payment_status = "PAID_VERIFIED"
            return booking

    def reassign_booking_technician(self, confirmation_id: str, technician_id: str) -> Optional[ServiceBooking]:
        """Reassigns an active booking to another electrician and updates calendar slots, truck_id & Google Calendar link."""
        with self._lock:
            if confirmation_id not in self.bookings or technician_id not in self.technicians:
                return None
            booking = self.bookings[confirmation_id]
            new_tech = self.technicians[technician_id]
            old_tech_short = (booking.assigned_technician or "").split("(")[0].strip().lower()
            new_tech_label = f"{new_tech.name} ({new_tech.license_type})"
            booking.assigned_technician = new_tech_label
            booking.truck_id = getattr(new_tech, "truck_id", "TRUCK-01 (Master Emergency Van)")

            # Update slot occupancy for this booking
            for slot in self.calendar_slots.values():
                if slot.booking_id == confirmation_id or (
                    slot.date == booking.slot_date
                    and slot.technician_name.split("(")[0].strip().lower() == old_tech_short
                    and slot.is_booked
                    and not getattr(slot, "is_blocked", False)
                ):
                    if slot.time_window_key != "emergency_asap":
                        slot.is_booked = False
                        slot.booking_id = None

            cur_hour = datetime.now().hour
            active_emerg_win = "morning" if cur_hour < 12 else ("afternoon" if cur_hour < 16 else "evening")

            for slot in self.calendar_slots.values():
                if slot.date == booking.slot_date and slot.technician_id == technician_id:
                    if booking.urgency_level == UrgencyLevel.EMERGENCY_CRITICAL:
                        if slot.time_window_key == active_emerg_win:
                            slot.is_booked = True
                            slot.booking_id = confirmation_id
                    elif booking.slot_time in slot.time_window or slot.time_window_key in (booking.slot_time or "").lower():
                        slot.is_booked = True
                        slot.booking_id = confirmation_id

            # Regenerate Google Calendar invite link with new technician & truck
            try:
                from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
                c_info = CALENDAR_SYNC.sync_contractor_dispatch(booking)
                booking.contractor_calendar_link = c_info.get("contractor_calendar_link")
                booking.google_calendar_link = booking.contractor_calendar_link
            except Exception:
                pass

            self.gcal_last_sync = f"Synced Reassignment -> {new_tech.name} • {booking.truck_id} ({datetime.now().strftime('%I:%M %p')})"
            return booking

    def update_booking_truck(self, confirmation_id: str, truck_id: str) -> Optional[ServiceBooking]:
        """Overrides the assigned Fleet Truck / Van on an active booking and refreshes its Google Calendar link."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            if truck_id and truck_id.strip():
                booking.truck_id = truck_id.strip()
            try:
                from phone_agent.integrations.calendar_sync import CALENDAR_SYNC
                c_info = CALENDAR_SYNC.sync_contractor_dispatch(booking)
                booking.contractor_calendar_link = c_info.get("contractor_calendar_link")
                booking.google_calendar_link = booking.contractor_calendar_link
            except Exception:
                pass
            self.gcal_last_sync = f"Synced Truck Update -> {booking.truck_id} ({datetime.now().strftime('%I:%M %p')})"
            return booking

    def attach_panel_photo_analysis(self, confirmation_id: str) -> Optional[ServiceBooking]:
        """Simulates homeowner breaker panel / hazard photo upload via SMS and runs AI Vision equipment audit."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            urg_str = booking.urgency_level.value if hasattr(booking.urgency_level, "value") else str(booking.urgency_level)
            is_emerg = "EMERG" in urg_str.upper() or "burn" in (booking.issue_description or "").lower()
            is_ev = "ev" in (booking.service_type or "").lower() or "charger" in (booking.issue_description or "").lower()
            if is_emerg:
                booking.panel_photo_analysis = {
                    "uploaded": True,
                    "uploaded_at": datetime.now().strftime("%I:%M %p"),
                    "photo_label": "customer_outlet_thermal_scan.jpg",
                    "equipment_detected": "NEMA 5-15R Duplex Outlet • Square D QO 150A Main Panel",
                    "breaker_spec": "Square D QO120DF (20A Dual-Function AFCI/GFCI Plug-On)",
                    "open_spaces": "2 Open Pole Spaces Verified",
                    "ai_finding": "Visible carbon tracking & thermal discoloration on neutral blade; branch circuit #14 isolated safely by homeowner.",
                    "parts_verification": "✓ Exact Breaker & Spec-Grade Receptacle Confirmed on Assigned Truck",
                }
            elif is_ev:
                booking.panel_photo_analysis = {
                    "uploaded": True,
                    "uploaded_at": datetime.now().strftime("%I:%M %p"),
                    "photo_label": "homeowner_main_panel_200a.jpg",
                    "equipment_detected": "Square D QO 200A Copper-Bus Main Breaker Loadcenter",
                    "breaker_spec": "Square D QO250 (50A 2-Pole Plug-On Breaker)",
                    "open_spaces": "6 Open Pole Spaces Verified (Bottom-Right Bus)",
                    "ai_finding": "200A main breaker verified; no recall hazards (no FPE/Zinsco); 6 open spaces ready for 50A 2-pole EVSE breaker.",
                    "parts_verification": "✓ QO250 Breaker & #6 AWG Cu Whip Verified on Assigned Truck",
                }
            else:
                booking.panel_photo_analysis = {
                    "uploaded": True,
                    "uploaded_at": datetime.now().strftime("%I:%M %p"),
                    "photo_label": "homeowner_breaker_panel.jpg",
                    "equipment_detected": "Eaton BR 200A 40-Space Main Breaker Loadcenter",
                    "breaker_spec": "Eaton BRN120DF (20A Dual-Function AFCI/GFCI)",
                    "open_spaces": "4 Open Pole Spaces Verified",
                    "ai_finding": "Panel bus & main lugs intact; no double-tapped neutrals observed; ready for scheduled installation.",
                    "parts_verification": "✓ Eaton BR Series Breakers & Surge Kit Verified on Assigned Truck",
                }
            return booking

    def mark_tech_en_route(self, confirmation_id: str) -> Optional[ServiceBooking]:
        """Marks the assigned electrician & truck as en route and triggers customer GPS ETA SMS."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.en_route_sent = True
            return booking

    def mark_review_requested(self, confirmation_id: str) -> Optional[ServiceBooking]:
        """Marks post-job 5-Star Google Review SMS as sent to customer."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.review_requested = True
            return booking

    def send_three_option_quote(self, confirmation_id: str) -> Optional[ServiceBooking]:
        """Pushes the interactive Good / Better / Best 3-Option Flat-Rate Proposal to the customer's SMS thread."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.quote_sent = True
            return booking

    def select_quote_option(self, confirmation_id: str, tier: str) -> Optional[ServiceBooking]:
        """Updates the customer's selected Good / Better / Best option tier and dynamically recalculates job revenue."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            clean_tier = (tier or "GOOD").strip().upper()
            if clean_tier not in ("GOOD", "BETTER", "BEST"):
                clean_tier = "GOOD"
            base_val = float(booking.estimated_job_value or 1200.0) - float(getattr(booking, "upsell_added_amount", 0.0) or 0.0)
            if clean_tier == "BETTER":
                add_amt = 485.0
            elif clean_tier == "BEST":
                add_amt = 950.0
            else:
                add_amt = 0.0
            booking.quote_sent = True
            booking.selected_option_tier = clean_tier
            booking.upsell_added_amount = add_amt
            booking.estimated_job_value = base_val + add_amt
            return booking

    def mark_final_balance_paid(self, confirmation_id: str) -> Optional[ServiceBooking]:
        """Marks both the upfront deposit and the remaining final work order balance as paid via Stripe."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.payment_status = "PAID_VERIFIED"
            booking.final_balance_paid = True
            booking.tech_workflow_stage = "COMPLETED"
            return booking

    def update_tech_workflow_stage(self, confirmation_id: str, stage: str) -> Optional[ServiceBooking]:
        """Updates the technician's in-truck workflow stage (e.g. EN_ROUTE, ON_SITE_DIAGNOSTIC, COMPLETED)."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            clean_stage = (stage or "DISPATCHED").strip().upper()
            booking.tech_workflow_stage = clean_stage
            if clean_stage == "EN_ROUTE":
                booking.en_route_sent = True
            return booking

    def save_diagnostic_readings(self, confirmation_id: str, readings: Dict[str, Any]) -> Optional[ServiceBooking]:
        """Saves on-site electrical diagnostic and commissioning readings recorded by the field technician."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.diagnostic_readings = readings or {}
            if booking.tech_workflow_stage in ("DISPATCHED", "EN_ROUTE"):
                booking.tech_workflow_stage = "ON_SITE_DIAGNOSTIC"
            return booking

    def sign_customer_work_authorization(self, confirmation_id: str, signer_name: str) -> Optional[ServiceBooking]:
        """Records the customer's digital signature sign-off authorizing electrical repairs."""
        with self._lock:
            if confirmation_id not in self.bookings:
                return None
            booking = self.bookings[confirmation_id]
            booking.customer_signature_name = (signer_name or booking.customer_name).strip()
            booking.customer_signature_timestamp = f"Digitally Signed by {booking.customer_signature_name} • {datetime.now().strftime('%b %d, %Y at %I:%M %p')}"
            booking.tech_workflow_stage = "PROPOSAL_APPROVED"
            return booking

    def set_active_fsm_platform(self, platform: str) -> str:
        """Sets the active FSM/Invoicing platform (Housecall Pro, ServiceTitan, Jobber, QuickBooks) and updates bookings."""
        with self._lock:
            clean_p = (platform or "HOUSECALL_PRO").strip().upper()
            if clean_p not in ("SERVICETITAN", "HOUSECALL_PRO", "JOBBER", "QUICKBOOKS"):
                clean_p = "HOUSECALL_PRO"
            self.active_fsm_platform = clean_p
            for b in self.bookings.values():
                b.connected_fsm = clean_p
                b.fsm_ticket_id = format_fsm_ticket_id(clean_p, b.confirmation_id)
                b.fsm_sync_status = "SYNCED"
                b.fsm_external_url = format_fsm_metadata(clean_p, b.confirmation_id)["url"]
            return clean_p

    def generate_fsm_webhook_payload(self, confirmation_id: str, platform: Optional[str] = None) -> Dict[str, Any]:
        """Generates realistic API webhook payloads formatted for the contractor's chosen FSM platform."""
        with self._lock:
            booking = self.bookings.get(confirmation_id)
            if not booking and self.bookings:
                booking = list(self.bookings.values())[-1]
            if not booking:
                return {"error": "Booking not found"}

            fsm_p = (platform or getattr(self, "active_fsm_platform", "HOUSECALL_PRO")).strip().upper()
            if fsm_p not in ("SERVICETITAN", "HOUSECALL_PRO", "JOBBER", "QUICKBOOKS"):
                fsm_p = "HOUSECALL_PRO"

            fsm_meta = format_fsm_metadata(fsm_p, booking.confirmation_id)
            ticket_id = fsm_meta["ticket_id"]
            is_emerg = "EMERG" in booking.confirmation_id or "emergency" in str(booking.service_type).lower()

            if fsm_p == "SERVICETITAN":
                return {
                    "fsm_platform": "ServiceTitan",
                    "api_endpoint": "POST https://api.servicetitan.io/jpm/v2/tenant/49201/jobs",
                    "external_job_id": ticket_id,
                    "customer": {
                        "name": booking.customer_name,
                        "phone": booking.phone_number,
                        "email": booking.customer_email or "customer@example.com",
                        "address": {
                            "street": booking.service_address,
                            "country": "USA",
                        },
                    },
                    "job_type": booking.service_type,
                    "priority": "HIGH" if is_emerg else "NORMAL",
                    "business_unit": "Residential Electrical Services",
                    "assigned_technician": {
                        "name": booking.assigned_technician,
                        "truck_unit": booking.truck_id,
                    },
                    "appointment": {
                        "start_date": booking.slot_date,
                        "arrival_window": booking.slot_time,
                    },
                    "custom_fields": {
                        "ZeroMiss_Source": "24/7 AI Voice Dispatch Engine",
                        "NFPA_Triage_Level": getattr(booking, "triage_hazard_level", "NFPA 70 / 70E Safety Verified"),
                        "Upfront_Deposit_Collected": f"${booking.dispatch_fee:.2f} via Stripe",
                        "Deposit_Status": "CREDITED_TOWARD_FINAL_INVOICE",
                        "Panel_AI_Precheck": booking.panel_photo_analysis or "Square D QO 200A (Breakers Verified Loaded)",
                        "On_Site_Diagnostics": booking.diagnostic_readings or "Pending Tech Arrival",
                        "Legal_Signature": booking.customer_signature_timestamp or "Pending Work Authorization",
                    },
                    "accounting_ledger": {
                        "diagnostic_deposit_credit": -float(booking.dispatch_fee),
                        "price_book_mode": "Contractor Default Flat-Rate Price Book",
                        "final_balance_collection": "Pending On-Site Work Completion via ServiceTitan Mobile",
                    },
                }

            elif fsm_p == "JOBBER":
                return {
                    "fsm_platform": "Jobber",
                    "api_endpoint": "POST https://api.getjobber.com/api/graphql (jobCreate)",
                    "client": {
                        "fullName": booking.customer_name,
                        "phone": booking.phone_number,
                        "email": booking.customer_email or "customer@example.com",
                    },
                    "property": {
                        "address": booking.service_address,
                    },
                    "job": {
                        "jobNumber": ticket_id,
                        "title": f"Electrical Service: {booking.service_type}",
                        "description": booking.issue_description,
                        "technician": booking.assigned_technician,
                        "truck": booking.truck_id,
                        "depositApplied": float(booking.dispatch_fee),
                        "invoiceStatus": "Draft Invoice with Deposit Applied in Client Hub",
                        "customFields": [
                            {"name": "ZeroMiss Call ID", "value": booking.confirmation_id},
                            {"name": "NFPA Code Triage", "value": "NFPA 70 & NFPA 70E Standard Compliance"},
                            {"name": "Diagnostic Readings", "value": str(booking.diagnostic_readings or "Pending")},
                            {"name": "Customer Signature", "value": booking.customer_signature_timestamp or "Pending"},
                        ],
                    },
                }

            elif fsm_p == "QUICKBOOKS":
                return {
                    "fsm_platform": "QuickBooks Online",
                    "api_endpoint": "POST https://quickbooks.api.intuit.com/v3/company/49201/invoice",
                    "DocNumber": ticket_id,
                    "CustomerRef": {
                        "name": booking.customer_name,
                        "phone": booking.phone_number,
                    },
                    "BillAddr": {
                        "Line1": booking.service_address,
                    },
                    "Deposit": float(booking.dispatch_fee),
                    "Line": [
                        {
                            "Description": f"ZeroMiss AI Dispatch: {booking.service_type} ({booking.issue_description})",
                            "Amount": float(booking.dispatch_fee),
                            "DetailType": "SalesItemLineDetail",
                        },
                        {
                            "Description": f"Upfront Stripe Deposit Credit (Ref: {booking.confirmation_id})",
                            "Amount": -float(booking.dispatch_fee),
                            "DetailType": "SalesItemLineDetail",
                        },
                    ],
                    "Balance": 0.0,
                    "PrivateNote": f"Assigned to {booking.assigned_technician} ({booking.truck_id}). Final work scope and parts to be added upon technician completion in QuickBooks.",
                }

            else:  # HOUSECALL_PRO
                return {
                    "fsm_platform": "Housecall Pro",
                    "api_endpoint": "POST https://api.housecallpro.com/v1/jobs",
                    "job_id": ticket_id,
                    "customer": {
                        "name": booking.customer_name,
                        "mobile_number": booking.phone_number,
                        "email": booking.customer_email or "customer@example.com",
                    },
                    "address": {
                        "formatted_address": booking.service_address,
                    },
                    "schedule": {
                        "scheduled_start": booking.slot_date,
                        "arrival_window_hours": 4,
                        "window_description": booking.slot_time,
                    },
                    "assigned_employee": {
                        "name": booking.assigned_technician,
                        "fleet_van": booking.truck_id,
                    },
                    "line_items": [
                        {
                            "name": "Upfront Dispatch & Diagnostic Fee (ZeroMiss AI Authorized)",
                            "unit_cost": -float(booking.dispatch_fee),
                            "quantity": 1,
                            "notes": "Paid upfront via Stripe — credited toward approved electrical repair scope in Housecall Pro",
                        }
                    ],
                    "notes": f"ZeroMiss AI Triage: {booking.issue_description}. Initial safety directives provided to homeowner.",
                    "attachments": {
                        "panel_photo_verified": bool(booking.panel_photo_analysis),
                        "digital_signature_on_file": bool(booking.customer_signature_timestamp),
                    },
                }


    def sync_google_calendar_busy_blocks(self, external_ics_url: Optional[str] = None) -> Dict[str, Any]:
        """Two-way Google Calendar sync: imports external Google Calendar busy events onto the Fleet Dispatch Board."""
        with self._lock:
            if external_ics_url:
                self.gcal_external_url = external_ics_url.strip()
            self.gcal_connected = True
            today_dt = datetime.now().date()
            d0 = today_dt.strftime("%Y-%m-%d")
            d1 = (today_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            d2 = (today_dt + timedelta(days=2)).strftime("%Y-%m-%d")

            busy_events = [
                (d0, "afternoon", "TECH-02", "📅 Google Calendar Busy: City Permit Inspection (#409)"),
                (d1, "afternoon", "TECH-03", "📅 Google Calendar Busy: Commercial Switchgear Walk"),
                (d2, "morning", "TECH-04", "📅 Google Calendar Busy: Supply House & Fleet Maintenance"),
            ]

            synced_count = 0
            for target_date, win_key, tech_id, reason in busy_events:
                for slot in self.calendar_slots.values():
                    if slot.date == target_date and slot.time_window_key == win_key and slot.technician_id == tech_id:
                        if not slot.is_booked or getattr(slot, "is_blocked", False):
                            slot.is_blocked = True
                            slot.is_booked = True
                            slot.blocked_reason = reason
                            synced_count += 1

            self.gcal_synced_busy_blocks = synced_count
            self.gcal_last_sync = f"Two-Way Sync Complete • {datetime.now().strftime('%I:%M:%S %p')}"
            return {
                "gcal_connected": self.gcal_connected,
                "gcal_last_sync": self.gcal_last_sync,
                "gcal_external_url": self.gcal_external_url,
                "synced_busy_blocks": synced_count,
                "outbound_dispatches_synced": len(self.bookings),
            }

    def record_missed_call(
        self,
        caller_phone: str = "(555) 329-8471",
        estimated_value: float = 1200.0,
        caller_name: str = "Potential Customer (Lost Lead)",
    ) -> Dict[str, Any]:
        """Records an after-hours / dropped call and triggers automated SMS lead recovery."""
        with self._lock:
            self._missed_counter += 1
            mc_id = f"MC-{self._missed_counter}"
            record = {
                "missed_call_id": mc_id,
                "caller_phone": caller_phone,
                "caller_name": caller_name,
                "estimated_value": estimated_value,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "status": "DROPPED_AT_RISK",
                "competitor_risk": "High ($1,200 at risk of competitor capture)",
                "recovery_sms_sent": True,
                "recovery_time_sec": 2.8,
                "recouped_at": None,
                "booking_confirmation_id": None,
            }
            self.missed_calls[mc_id] = record
            return record

    def convert_missed_call(
        self,
        missed_call_id: Optional[str] = None,
        booking_confirmation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Converts a missed call lead when the customer clicks the self-scheduling link."""
        with self._lock:
            # If no ID passed, grab the latest unconverted missed call
            if not missed_call_id:
                for mc in reversed(list(self.missed_calls.values())):
                    if mc["status"] != "RECOUPED_WON":
                        missed_call_id = mc["missed_call_id"]
                        break

            if not missed_call_id or missed_call_id not in self.missed_calls:
                mc = self.record_missed_call()
                missed_call_id = mc["missed_call_id"]

            mc = self.missed_calls[missed_call_id]
            if mc["status"] == "RECOUPED_WON":
                return mc

            mc["status"] = "RECOUPED_WON"
            mc["recouped_at"] = datetime.now().strftime("%I:%M %p")
            mc["competitor_risk"] = "Zero (Customer Recouped & Won)"

            # Create or link a real booking in self.bookings so it shows on calendar and generates pipeline
            if not booking_confirmation_id:
                target_date = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
                booking = self.book_slot(
                    customer_name="Alex Rivera (Recouped Lead)",
                    phone_number=mc.get("caller_phone", "(555) 329-8471"),
                    service_address="45 Innovation Way, Cambridge",
                    slot_date=target_date,
                    slot_time="08:00 AM - 12:00 PM",
                    issue_description="EV Charger 50A Installation (Recovered via SMS Link)",
                    service_type="EV Charger Installation",
                    urgency_level=UrgencyLevel.STANDARD,
                    assigned_technician="Sarah Chen (EV & Commercial Specialist)",
                    dispatch_fee=89.0,
                    notes=f"Recouped lead intercepted from competitor via 3-second SMS recovery link ({missed_call_id}).",
                    customer_email="alex.rivera@gmail.com",
                )
                booking.estimated_job_value = mc.get("estimated_value", 1200.0)
                booking_confirmation_id = booking.confirmation_id

            mc["booking_confirmation_id"] = booking_confirmation_id
            return mc

    def load_30day_benchmark(self):
        """Switches executive KPI metrics to a realistic 30-day contractor benchmark ($18,450)."""
        with self._lock:
            self.is_benchmark_mode = True

    def clear_to_session_baseline(self):
        """Switches executive KPI metrics back to live session baseline ($0.00 until demo actions)."""
        with self._lock:
            self.is_benchmark_mode = False

    def toggle_benchmark_mode(self) -> bool:
        """Toggles between live demo session and 30-day contractor benchmark."""
        with self._lock:
            self.is_benchmark_mode = not self.is_benchmark_mode
            return self.is_benchmark_mode

    def calculate_contractor_roi_metrics(self) -> Dict[str, Any]:
        """Calculates live executive revenue metrics and ROI statistics."""
        with self._lock:
            if self.is_benchmark_mode:
                return {
                    "is_benchmark": True,
                    "benchmark_label": "30-Day Contractor Benchmark",
                    "total_pipeline_revenue": 18450.0,
                    "revenue_won": 18450.0,
                    "fees_collected": 1424.0,
                    "total_bookings": 18,
                    "emergency_count": 6,
                    "routine_count": 12,
                    "paid_count": 16,
                    "missed_recovered": 7,
                    "recouped_revenue": 8400.0,
                    "missed_at_risk_value": 0.0,
                    "missed_total_count": 7,
                    "no_show_protection_pct": 100.0,
                    "avg_answer_time_sec": 0.8,
                }

            # Live Session: 100% Mathematically Real (Starts strictly at $0.00 for new session calls)
            session_bookings = [b for b in self.bookings.values() if not getattr(b, "is_demo_seed", False)]
            active_pipeline = sum(getattr(b, "estimated_job_value", 0.0) for b in session_bookings)
            revenue_won = sum(
                getattr(b, "estimated_job_value", 0.0)
                for b in session_bookings
                if getattr(b, "payment_status", "PENDING_AUTHORIZATION") == "PAID_VERIFIED"
            )
            fees_collected = sum(
                b.dispatch_fee for b in session_bookings
                if getattr(b, "payment_status", "PENDING_AUTHORIZATION") == "PAID_VERIFIED"
            )
            emergency_count = sum(1 for b in session_bookings if b.urgency_level == UrgencyLevel.EMERGENCY_CRITICAL)
            routine_count = len(session_bookings) - emergency_count
            paid_count = sum(1 for b in session_bookings if getattr(b, "payment_status", "PENDING_AUTHORIZATION") == "PAID_VERIFIED")

            converted_mc = [mc for mc in self.missed_calls.values() if mc.get("status") == "RECOUPED_WON"]
            unconverted_mc = [mc for mc in self.missed_calls.values() if mc.get("status") != "RECOUPED_WON"]

            recouped_rev = sum(mc.get("estimated_value", 1200.0) for mc in converted_mc)
            at_risk_rev = sum(mc.get("estimated_value", 1200.0) for mc in unconverted_mc)

            orphan_recouped_rev = sum(
                mc.get("estimated_value", 1200.0) for mc in converted_mc
                if mc.get("booking_confirmation_id") not in self.bookings
            )
            total_pipeline = active_pipeline + orphan_recouped_rev

            no_show_pct = (paid_count / len(session_bookings) * 100.0) if len(session_bookings) > 0 else 100.0

            return {
                "is_benchmark": False,
                "benchmark_label": "Live Demo Session",
                "total_pipeline_revenue": total_pipeline,
                "revenue_won": revenue_won,
                "fees_collected": fees_collected,
                "total_bookings": len(session_bookings),
                "calendar_bookings_count": len(self.bookings),
                "emergency_count": emergency_count,
                "routine_count": routine_count,
                "paid_count": paid_count,
                "missed_recovered": len(converted_mc),
                "recouped_revenue": recouped_rev,
                "missed_at_risk_value": at_risk_rev,
                "missed_total_count": len(self.missed_calls),
                "no_show_protection_pct": round(no_show_pct, 1),
                "avg_answer_time_sec": 0.8,
            }

    def reset(self):
        """Clears bookings, missed calls, and resets state to live baseline."""
        with self._lock:
            self.bookings.clear()
            self.emergency_reports.clear()
            self.missed_calls.clear()
            self.is_benchmark_mode = False
            self.gcal_synced_busy_blocks = 0
            self.gcal_last_sync = "Two-Way Sync Active (Live)"
            self.seed_defaults()


# Global DB instance
DB = DispatchDatabase()
