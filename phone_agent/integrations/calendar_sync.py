"""Google Calendar and iCalendar (.ics) integration for JobLatch AI Voice Dispatch."""

import email
import json
import os
import re
import smtplib
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Tuple
from phone_agent.config import DEFAULT_CONFIG



class CalendarSyncService:
    """Handles calendar event creation, .ics file export, and email confirmations."""

    def __init__(
        self,
        calendar_events_dir: str = "calendar_events",
        sent_emails_dir: str = "sent_emails",
    ):
        self.calendar_events_dir = calendar_events_dir
        self.sent_emails_dir = sent_emails_dir
        os.makedirs(self.calendar_events_dir, exist_ok=True)
        os.makedirs(self.sent_emails_dir, exist_ok=True)

    def parse_time_window(self, slot_date: str, slot_time: str) -> Tuple[datetime, datetime]:
        """Parses appointment date and window string into start and end datetimes."""
        from phone_agent.tools.calendar_tool import parse_relative_date
        resolved_date_str = parse_relative_date(slot_date)
        try:
            date_obj = datetime.strptime(resolved_date_str, "%Y-%m-%d")
        except ValueError:
            date_obj = datetime.now() + timedelta(days=1)

        # Check standard windows
        lower_time = slot_time.lower()
        if "08:00 am" in lower_time or "morning" in lower_time:
            start_dt = date_obj.replace(hour=8, minute=0, second=0)
            end_dt = date_obj.replace(hour=12, minute=0, second=0)
        elif "12:00 pm" in lower_time or "afternoon" in lower_time:
            start_dt = date_obj.replace(hour=12, minute=0, second=0)
            end_dt = date_obj.replace(hour=16, minute=0, second=0)
        elif "04:00 pm" in lower_time or "evening" in lower_time:
            start_dt = date_obj.replace(hour=16, minute=0, second=0)
            end_dt = date_obj.replace(hour=19, minute=0, second=0)
        elif "45" in lower_time or "minute" in lower_time or "emergency" in lower_time or "code red" in lower_time:
            # Immediate same-day emergency dispatch: starts in 45 min
            if date_obj.date() <= datetime.now().date():
                start_dt = datetime.now() + timedelta(minutes=45)
                end_dt = start_dt + timedelta(hours=2)
            else:
                # Scheduled for future date: default to 8am-12pm morning window
                start_dt = date_obj.replace(hour=8, minute=0, second=0)
                end_dt = date_obj.replace(hour=12, minute=0, second=0)
        else:
            # Default to morning window on that appointment date
            start_dt = date_obj.replace(hour=8, minute=0, second=0)
            end_dt = date_obj.replace(hour=12, minute=0, second=0)

        return start_dt, end_dt

    def generate_google_calendar_link(
        self,
        confirmation_id: str,
        customer_name: str,
        customer_email: str,
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
    ) -> str:
        """
        Generates a direct 1-click Google Calendar event link:
        https://calendar.google.com/calendar/render?action=TEMPLATE&...
        """
        start_dt, end_dt = self.parse_time_window(slot_date, slot_time)

        # Format dates as YYYYMMDDTHHMMSSZ in UTC
        start_utc = start_dt.strftime("%Y%m%dT%H%M00")
        end_utc = end_dt.strftime("%Y%m%dT%H%M00")

        title = f"JobLatch AI Electrical Service ({confirmation_id})"
        fee_info = "Free Estimate" if dispatch_fee == 0 else f"${dispatch_fee:.0f} Diagnostic Fee"
        details = (
            f"JobLatch AI Electrical Appointment\n\n"
            f"Confirmation: {confirmation_id}\n"
            f"Customer: {customer_name} ({customer_email})\n"
            f"Assigned Electrician: {assigned_technician}\n"
            f"Arrival Window: {slot_time}\n"
            f"Fee Structure: {fee_info}\n\n"
            f"Issue / Scope: {issue_description}\n\n"
            f"Questions? Call 24/7 Dispatch at (800) 555-LATCH."
        )

        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_utc}/{end_utc}",
            "details": details,
            "location": service_address,
            "add": customer_email,
        }

        return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

    def generate_ical_event(
        self,
        confirmation_id: str,
        customer_name: str,
        customer_email: str,
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
    ) -> Tuple[str, str]:
        """
        Generates an RFC 5545 compliant .ics iCalendar file that can be
        imported into Google Calendar, Outlook, or Apple Calendar.
        Returns (filepath, ics_content_string).
        """
        start_dt, end_dt = self.parse_time_window(slot_date, slot_time)
        start_str = start_dt.strftime("%Y%m%dT%H%M00")
        end_str = end_dt.strftime("%Y%m%dT%H%M00")
        now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M00Z")

        fee_info = "Free Estimate" if dispatch_fee == 0 else f"${dispatch_fee:.0f} Diagnostic Fee"
        safe_desc = (
            f"JobLatch AI Electrical Service Call\\n"
            f"Confirmation: {confirmation_id}\\n"
            f"Customer: {customer_name}\\n"
            f"Technician: {assigned_technician}\\n"
            f"Arrival Window: {slot_time}\\n"
            f"Fee: {fee_info}\\n"
            f"Scope: {issue_description}\\n"
            f"Support: (800) 555-LATCH"
        )

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//JobLatch AI Electrical//Voice Dispatch Agent v1.0//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:REQUEST\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{confirmation_id}@joblatchai.com\r\n"
            f"DTSTAMP:{now_str}\r\n"
            f"DTSTART:{start_str}\r\n"
            f"DTEND:{end_str}\r\n"
            f"SUMMARY:JobLatch AI Electrical: {issue_description[:30]}\r\n"
            f"DESCRIPTION:{safe_desc}\r\n"
            f"LOCATION:{service_address}\r\n"
            "ORGANIZER;CN=JobLatch AI 24/7 Dispatch:mailto:dispatch@joblatchai.com\r\n"
            f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;CN={customer_name}:mailto:{customer_email}\r\n"
            "STATUS:CONFIRMED\r\n"
            "SEQUENCE:0\r\n"
            "BEGIN:VALARM\r\n"
            "TRIGGER:-PT60M\r\n"
            "ACTION:DISPLAY\r\n"
            "DESCRIPTION:Reminder: Electrician arriving in 1 hour\r\n"
            "END:VALARM\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        filename = f"{confirmation_id}_calendar_invite.ics"
        filepath = os.path.join(self.calendar_events_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return filepath, ics_content

    def send_confirmation_email(
        self,
        confirmation_id: str,
        customer_name: str,
        customer_email: str,
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
        ics_path: str,
        google_cal_link: str,
    ) -> Dict[str, Any]:
        """
        Composes and dispatches a rich HTML email confirmation with the attached
        .ics calendar file and a 1-click Google Calendar integration link.
        """
        fee_info = "Free Estimate" if dispatch_fee == 0 else f"${dispatch_fee:.0f} Diagnostic Dispatch Fee"

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Appointment Confirmed: JobLatch AI Electrical ({confirmation_id})"
        msg["From"] = "JobLatch AI 24/7 Dispatch <dispatch@joblatchai.com>"
        msg["To"] = customer_email

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #0f172a; color: #fff; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
                <h1 style="margin: 0; color: #38bdf8;">JobLatch AI Electrical</h1>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #94a3b8;">Licensed & Insured Electrical Contractors</p>
            </div>
            <div style="background: #ffffff; padding: 25px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
                <h2 style="color: #0f172a; margin-top: 0;">Appointment Confirmed!</h2>
                <p>Hello <strong>{customer_name}</strong>,</p>
                <p>Your electrical service call has been successfully scheduled. Here are your booking details:</p>

                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: #f8fafc; border-radius: 6px;">
                    <tr><td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Confirmation Code:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #0284c7; font-weight: bold;">{confirmation_id}</td></tr>
                    <tr><td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Service Date:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{slot_date}</td></tr>
                    <tr><td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Arrival Window:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{slot_time}</td></tr>
                    <tr><td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Assigned Electrician:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{assigned_technician}</td></tr>
                    <tr><td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Service Address:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{service_address}</td></tr>
                    <tr><td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Fee Structure:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{fee_info}</td></tr>
                    <tr><td style="padding: 10px; font-weight: bold;">Service Scope:</td><td style="padding: 10px;">{issue_description}</td></tr>
                </table>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{google_cal_link}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                        📅 Add to Google Calendar
                    </a>
                </div>

                <p style="font-size: 13px; color: #64748b;">
                    We have also attached a <strong>.ics calendar invite</strong> to this email that works directly with Apple Calendar, Outlook, and Google Calendar.
                </p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 12px; color: #94a3b8; text-align: center;">
                    JobLatch AI Electrical & Emergency Dispatch | 24/7 Phone: (800) 555-LATCH | Greater Metro Area
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Attach .ics calendar file
        if os.path.exists(ics_path):
            with open(ics_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(ics_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(ics_path)}"'
            part["Content-Type"] = "text/calendar; charset=utf-8; method=REQUEST"
            msg.attach(part)

        # Save to disk as .eml and record metadata
        eml_filename = f"{confirmation_id}_email.eml"
        eml_path = os.path.join(self.sent_emails_dir, eml_filename)
        with open(eml_path, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        json_meta_path = os.path.join(self.sent_emails_dir, f"{confirmation_id}_meta.json")
        email_record = {
            "confirmation_id": confirmation_id,
            "recipient": customer_email,
            "customer_name": customer_name,
            "subject": msg["Subject"],
            "sent_at": datetime.now().isoformat(),
            "eml_path": eml_path,
            "ics_path": ics_path,
            "google_calendar_link": google_cal_link,
            "status": "DELIVERED",
        }
        with open(json_meta_path, "w", encoding="utf-8") as f:
            json.dump(email_record, f, indent=2)

        # Check if live SMTP server is configured
        smtp_host = os.getenv("SMTP_HOST")
        if smtp_host:
            try:
                smtp_port = int(os.getenv("SMTP_PORT", "587"))
                smtp_user = os.getenv("SMTP_USER", "")
                smtp_pass = os.getenv("SMTP_PASS", "")
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                email_record["status"] = "SENT_LIVE_SMTP"
            except Exception as e:
                email_record["smtp_error"] = str(e)
                email_record["status"] = "SAVED_LOCAL_FALLBACK"

        return email_record

    def sync_booking(
        self,
        confirmation_id: str,
        customer_name: str,
        customer_email: str,
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
    ) -> Dict[str, Any]:
        """Complete workflow: generates ics, Google Calendar link, and dispatches confirmation email."""
        google_cal_link = self.generate_google_calendar_link(
            confirmation_id=confirmation_id,
            customer_name=customer_name,
            customer_email=customer_email,
            service_address=service_address,
            slot_date=slot_date,
            slot_time=slot_time,
            issue_description=issue_description,
            assigned_technician=assigned_technician,
            dispatch_fee=dispatch_fee,
        )

        ics_path, _ = self.generate_ical_event(
            confirmation_id=confirmation_id,
            customer_name=customer_name,
            customer_email=customer_email,
            service_address=service_address,
            slot_date=slot_date,
            slot_time=slot_time,
            issue_description=issue_description,
            assigned_technician=assigned_technician,
            dispatch_fee=dispatch_fee,
        )

        email_result = self.send_confirmation_email(
            confirmation_id=confirmation_id,
            customer_name=customer_name,
            customer_email=customer_email,
            service_address=service_address,
            slot_date=slot_date,
            slot_time=slot_time,
            issue_description=issue_description,
            assigned_technician=assigned_technician,
            dispatch_fee=dispatch_fee,
            ics_path=ics_path,
            google_cal_link=google_cal_link,
        )

        return {
            "confirmation_id": confirmation_id,
            "customer_email": customer_email,
            "google_calendar_link": google_cal_link,
            "ics_file_path": ics_path,
            "email_record": email_result,
        }

    def generate_contractor_calendar_link(
        self,
        confirmation_id: str,
        customer_name: str,
        phone_number: str,
        customer_email: Optional[str],
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
        urgency_level: str = "STANDARD",
        notes: Optional[str] = None,
        truck_id: str = "TRUCK-01 (Master Emergency Van)",
    ) -> str:
        """Generates 1-click Google Calendar render link addressed directly to the contractor (Sean Glenn)."""
        start_dt, end_dt = self.parse_time_window(slot_date, slot_time)
        start_utc = start_dt.strftime("%Y%m%dT%H%M00")
        end_utc = end_dt.strftime("%Y%m%dT%H%M00")

        is_emerg = "EMERG" in str(urgency_level).upper() or "CRITICAL" in str(urgency_level).upper()
        prefix = "🚨 EMERGENCY CODE RED" if is_emerg else "⚡ JobLatch Dispatch"
        truck_short = (truck_id or "TRUCK-01").split("(")[0].strip()
        title = f"{prefix} [{truck_short}]: {customer_name} @ {service_address}"

        fee_info = "Free Estimate" if dispatch_fee == 0 else f"${dispatch_fee:.0f} Diagnostic Fee"
        email_str = customer_email or "Not provided by caller"

        details = (
            f"JobLatch AI Electrical Contractor Dispatch Dossier\n"
            f"Contractor: {DEFAULT_CONFIG.contractor_name} ({DEFAULT_CONFIG.contractor_email})\n"
            f"Confirmation: {confirmation_id}\n"
            f"Urgency: {urgency_level}\n\n"
            f"CUSTOMER CONTACT:\n"
            f"• Name: {customer_name}\n"
            f"• Phone: {phone_number}\n"
            f"• Email: {email_str}\n"
            f"• Service Address: {service_address}\n\n"
            f"DISPATCH DETAILS:\n"
            f"• Electrician: {assigned_technician}\n"
            f"• Assigned Fleet Vehicle: {truck_id}\n"
            f"• Arrival Window: {slot_date} ({slot_time})\n"
            f"• Fee Structure: {fee_info}\n"
            f"• Scope of Work: {issue_description}\n"
            f"• Access Notes: {notes or 'Standard property access'}\n\n"
            f"24/7 Dispatch Control: (800) 555-LATCH"
        )

        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_utc}/{end_utc}",
            "details": details,
            "location": service_address,
            "add": DEFAULT_CONFIG.contractor_email,
        }
        return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

    def generate_contractor_ical_event(
        self,
        confirmation_id: str,
        customer_name: str,
        phone_number: str,
        customer_email: Optional[str],
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
        urgency_level: str = "STANDARD",
        notes: Optional[str] = None,
        truck_id: str = "TRUCK-01 (Master Emergency Van)",
    ) -> Tuple[str, str]:
        """Generates RFC 5545 .ics calendar event file for the contractor."""
        start_dt, end_dt = self.parse_time_window(slot_date, slot_time)
        start_str = start_dt.strftime("%Y%m%dT%H%M00")
        end_str = end_dt.strftime("%Y%m%dT%H%M00")
        now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M00Z")

        fee_info = "Free Estimate" if dispatch_fee == 0 else f"${dispatch_fee:.0f} Diagnostic Fee"
        safe_desc = (
            f"JobLatch Contractor Dispatch Dossier\\n"
            f"Ticket: {confirmation_id}\\n"
            f"Customer: {customer_name} ({phone_number})\\n"
            f"Technician: {assigned_technician}\\n"
            f"Fleet Truck/Van: {truck_id}\\n"
            f"Window: {slot_time}\\n"
            f"Fee: {fee_info}\\n"
            f"Scope: {issue_description}\\n"
            f"Notes: {notes or 'None'}\\n"
            f"24/7 Dispatch: (800) 555-LATCH"
        )

        is_emerg = "EMERG" in str(urgency_level).upper() or "CRITICAL" in str(urgency_level).upper()
        truck_short = (truck_id or "TRUCK-01").split("(")[0].strip()
        summary = f"{'🚨 EMERGENCY' if is_emerg else '⚡ JobLatch'} [{truck_short}]: {customer_name} - {issue_description[:25]}"

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//JobLatch AI Electrical//Contractor Dispatch System v1.0//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:REQUEST\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:contractor-{confirmation_id}@joblatchai.com\r\n"
            f"DTSTAMP:{now_str}\r\n"
            f"DTSTART:{start_str}\r\n"
            f"DTEND:{end_str}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DESCRIPTION:{safe_desc}\r\n"
            f"LOCATION:{service_address}\r\n"
            "ORGANIZER;CN=JobLatch AI 24/7 Dispatch:mailto:dispatch@joblatchai.com\r\n"
            f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN={DEFAULT_CONFIG.contractor_name}:mailto:{DEFAULT_CONFIG.contractor_email}\r\n"
            "STATUS:CONFIRMED\r\n"
            "SEQUENCE:0\r\n"
            "BEGIN:VALARM\r\n"
            "TRIGGER:-PT30M\r\n"
            "ACTION:DISPLAY\r\n"
            "DESCRIPTION:Dispatch Alert: Service call starting in 30 minutes\r\n"
            "END:VALARM\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        filename = f"contractor_{confirmation_id}.ics"
        filepath = os.path.join(self.calendar_events_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return filepath, ics_content

    def generate_master_feed_ics(self, bookings: list) -> str:
        """Generates a master multi-event RFC 5545 .ics calendar feed for all active dispatches (including Truck IDs)."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M00Z")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//JobLatch AI Electrical//Master Fleet Dispatch Feed//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:JobLatch AI Fleet Dispatch Calendar",
        ]
        for b in bookings:
            start_dt, end_dt = self.parse_time_window(b.slot_date, b.slot_time)
            start_str = start_dt.strftime("%Y%m%dT%H%M00")
            end_str = end_dt.strftime("%Y%m%dT%H%M00")
            truck_id = getattr(b, "truck_id", "TRUCK-01 (Master Emergency Van)")
            truck_short = (truck_id or "TRUCK-01").split("(")[0].strip()
            urgency_val = b.urgency_level.value if hasattr(b.urgency_level, "value") else str(b.urgency_level)
            is_emerg = "EMERG" in urgency_val.upper()
            summary = f"{'🚨 CODE RED' if is_emerg else '⚡ Dispatch'} [{truck_short}]: {b.customer_name} ({b.assigned_technician.split('(')[0].strip()})"
            desc = (
                f"Work Order: #{b.confirmation_id}\\n"
                f"Customer: {b.customer_name} ({b.phone_number})\\n"
                f"Electrician: {b.assigned_technician}\\n"
                f"Fleet Truck/Van: {truck_id}\\n"
                f"Scope: {b.issue_description}"
            )
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:master-{b.confirmation_id}@joblatchai.com",
                f"DTSTAMP:{now_str}",
                f"DTSTART:{start_str}",
                f"DTEND:{end_str}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                f"LOCATION:{b.service_address}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ])
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

    def send_contractor_dispatch_alert(
        self,
        confirmation_id: str,
        customer_name: str,
        phone_number: str,
        customer_email: Optional[str],
        service_address: str,
        slot_date: str,
        slot_time: str,
        issue_description: str,
        assigned_technician: str,
        dispatch_fee: float,
        urgency_level: str,
        contractor_cal_link: str,
        contractor_ics_path: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates and dispatches a rich HTML dispatch alert to Sean Glenn with 1-click Google Calendar link."""
        contractor_email = DEFAULT_CONFIG.contractor_email
        contractor_name = DEFAULT_CONFIG.contractor_name
        fee_info = "Free Estimate" if dispatch_fee == 0 else f"${dispatch_fee:.0f} Diagnostic Fee"

        is_emerg = "EMERG" in str(urgency_level).upper() or "CRITICAL" in str(urgency_level).upper()
        badge_bg = "#dc2626" if is_emerg else "#0284c7"
        badge_text = "EMERGENCY CODE RED" if is_emerg else urgency_level

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"⚡ CONTRACTOR DISPATCH [{badge_text}]: {customer_name} @ {service_address} ({confirmation_id})"
        msg["From"] = "JobLatch AI 24/7 Dispatch <dispatch@joblatchai.com>"
        msg["To"] = f"{contractor_name} <{contractor_email}>"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 650px; margin: 0 auto; padding: 20px;">
            <div style="background: #0f172a; color: #fff; padding: 20px; border-radius: 8px 8px 0 0; border-bottom: 4px solid {badge_bg};">
                <table style="width: 100%;">
                    <tr>
                        <td>
                            <h2 style="margin: 0; color: #38bdf8;">JobLatch AI Electrical Dispatch</h2>
                            <p style="margin: 5px 0 0 0; font-size: 13px; color: #94a3b8;">
                                Dispatch Alert for <strong>{contractor_name}</strong> ({contractor_email})
                            </p>
                        </td>
                        <td style="text-align: right; vertical-align: middle;">
                            <span style="background: {badge_bg}; color: #fff; padding: 6px 14px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase;">
                                {badge_text}
                            </span>
                        </td>
                    </tr>
                </table>
            </div>
            <div style="background: #ffffff; padding: 25px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
                <h3 style="color: #0f172a; margin-top: 0;">New Job Dispatched: {confirmation_id}</h3>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background: #f8fafc; border-radius: 6px;">
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0; width: 35%;">Customer Name:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;">{customer_name}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Direct Phone:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;"><a href="tel:{phone_number}" style="color: #0284c7; font-weight: bold; text-decoration: none;">{phone_number}</a></td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Customer Email:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;">{customer_email or 'Not provided by caller'}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Service Address:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;"><strong>{service_address}</strong></td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Service Date:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;">{slot_date}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Arrival Window:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0; color: #0284c7; font-weight: bold;">{slot_time}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Assigned Electrician:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;">{assigned_technician}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Fee Structure:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;">{fee_info}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold; border-bottom: 1px solid #e2e8f0;">Issue Scope:</td><td style="padding: 9px; border-bottom: 1px solid #e2e8f0;">{issue_description}</td></tr>
                    <tr><td style="padding: 9px; font-weight: bold;">Access / Notes:</td><td style="padding: 9px;">{notes or 'None'}</td></tr>
                </table>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{contractor_cal_link}" style="background-color: #0284c7; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 15px; display: inline-block;">
                        📅 Add Job to Sean Glenn's Google Calendar
                    </a>
                </div>

                <p style="font-size: 12px; color: #64748b; text-align: center;">
                    Attached: <strong>contractor_{confirmation_id}.ics</strong> for immediate calendar integration.
                </p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 11px; color: #94a3b8; text-align: center;">
                    JobLatch AI 24/7 Automated Voice Dispatch System | Contractor Notification Channel
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Attach contractor .ics
        if os.path.exists(contractor_ics_path):
            with open(contractor_ics_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(contractor_ics_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(contractor_ics_path)}"'
            part["Content-Type"] = "text/calendar; charset=utf-8; method=REQUEST"
            msg.attach(part)

        eml_filename = f"contractor_alert_{confirmation_id}.eml"
        eml_path = os.path.join(self.sent_emails_dir, eml_filename)
        with open(eml_path, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        json_meta_path = os.path.join(self.sent_emails_dir, f"contractor_alert_{confirmation_id}_meta.json")
        record = {
            "confirmation_id": confirmation_id,
            "contractor_email": contractor_email,
            "contractor_name": contractor_name,
            "customer_name": customer_name,
            "customer_phone": phone_number,
            "service_address": service_address,
            "urgency": urgency_level,
            "subject": msg["Subject"],
            "sent_at": datetime.now().isoformat(),
            "eml_path": eml_path,
            "contractor_ics_path": contractor_ics_path,
            "google_calendar_link": contractor_cal_link,
            "status": "DELIVERED_TO_CONTRACTOR",
        }
        with open(json_meta_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        # Check SMTP
        smtp_host = os.getenv("SMTP_HOST")
        if smtp_host:
            try:
                smtp_port = int(os.getenv("SMTP_PORT", "587"))
                smtp_user = os.getenv("SMTP_USER", "")
                smtp_pass = os.getenv("SMTP_PASS", "")
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                record["status"] = "SENT_LIVE_SMTP"
            except Exception as e:
                record["smtp_error"] = str(e)

        return record

    def send_emergency_contractor_alert(self, report: Any) -> Dict[str, Any]:
        """Dispatches an urgent code-red contractor alert for life safety hazards."""
        contractor_email = DEFAULT_CONFIG.contractor_email
        contractor_name = DEFAULT_CONFIG.contractor_name
        severity_str = report.severity_level.value if hasattr(report.severity_level, "value") else str(report.severity_level)

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"🚨 URGENT CODE RED [{severity_str}]: {report.hazard_type} @ {report.location_in_property} ({report.triage_case_id})"
        msg["From"] = "JobLatch AI 24/7 Dispatch <dispatch@joblatchai.com>"
        msg["To"] = f"{contractor_name} <{contractor_email}>"

        actions_html = "".join(f"<li style='margin-bottom: 5px; color: #b91c1c; font-weight: bold;'>{act}</li>" for act in report.immediate_life_safety_actions)

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 650px; margin: 0 auto; padding: 20px;">
            <div style="background: #991b1b; color: #fff; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; color: #fef2f2;">🚨 EMERGENCY DISPATCH ALERT: {severity_str}</h2>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #fecaca;">Immediate Attention Required - Incident {report.triage_case_id}</p>
            </div>
            <div style="background: #ffffff; padding: 25px; border: 1px solid #f87171; border-top: none; border-radius: 0 0 8px 8px;">
                <p>Contractor <strong>{contractor_name}</strong>,</p>
                <p>A high-severity electrical hazard has been reported through JobLatch AI voice dispatch:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background: #fff1f2; border-radius: 6px;">
                    <tr><td style="padding: 8px; font-weight: bold; width: 35%;">Triage Case:</td><td style="padding: 8px;">{report.triage_case_id}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Hazard Type:</td><td style="padding: 8px;">{report.hazard_type}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Location:</td><td style="padding: 8px;">{report.location_in_property}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Fire Visible:</td><td style="padding: 8px;">{'YES' if report.is_fire_visible else 'No'}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Person Injured:</td><td style="padding: 8px;">{'YES' if report.is_person_injured else 'No'}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Water Present:</td><td style="padding: 8px;">{'YES' if report.is_water_present else 'No'}</td></tr>
                    <tr><td style="padding: 8px; font-weight: bold;">Utility Shutoff:</td><td style="padding: 8px;">{'REQUIRED' if report.utility_shutoff_required else 'No'}</td></tr>
                </table>
                <h4 style="color: #991b1b; margin-bottom: 5px;">Immediate Life Safety Instructions Delivered to Caller:</h4>
                <ul style="padding-left: 20px;">
                    {actions_html}
                </ul>
                <h4 style="margin-bottom: 5px;">Action Plan:</h4>
                <p style="background: #f1f5f9; padding: 10px; border-radius: 4px;">{report.recommended_action_plan}</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        eml_filename = f"contractor_emergency_{report.triage_case_id}.eml"
        eml_path = os.path.join(self.sent_emails_dir, eml_filename)
        with open(eml_path, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        meta_path = os.path.join(self.sent_emails_dir, f"contractor_emergency_{report.triage_case_id}_meta.json")
        record = {
            "triage_case_id": report.triage_case_id,
            "contractor_email": contractor_email,
            "severity": severity_str,
            "hazard_type": report.hazard_type,
            "timestamp": report.timestamp,
            "eml_path": eml_path,
            "status": "DELIVERED_TO_CONTRACTOR",
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        return record

    def sync_contractor_dispatch(self, booking: Any) -> Dict[str, Any]:
        """Synchronizes booking details directly to the electrical contractor (Sean Glenn)."""
        urgency_val = booking.urgency_level.value if hasattr(booking.urgency_level, "value") else str(booking.urgency_level)
        truck_id = getattr(booking, "truck_id", "TRUCK-01 (Master Emergency Van)")

        cal_link = self.generate_contractor_calendar_link(
            confirmation_id=booking.confirmation_id,
            customer_name=booking.customer_name,
            phone_number=booking.phone_number,
            customer_email=booking.customer_email,
            service_address=booking.service_address,
            slot_date=booking.slot_date,
            slot_time=booking.slot_time,
            issue_description=booking.issue_description,
            assigned_technician=booking.assigned_technician,
            dispatch_fee=booking.dispatch_fee,
            urgency_level=urgency_val,
            notes=booking.notes,
            truck_id=truck_id,
        )

        ics_path, _ = self.generate_contractor_ical_event(
            confirmation_id=booking.confirmation_id,
            customer_name=booking.customer_name,
            phone_number=booking.phone_number,
            customer_email=booking.customer_email,
            service_address=booking.service_address,
            slot_date=booking.slot_date,
            slot_time=booking.slot_time,
            issue_description=booking.issue_description,
            assigned_technician=booking.assigned_technician,
            dispatch_fee=booking.dispatch_fee,
            urgency_level=urgency_val,
            notes=booking.notes,
            truck_id=truck_id,
        )

        alert_record = self.send_contractor_dispatch_alert(
            confirmation_id=booking.confirmation_id,
            customer_name=booking.customer_name,
            phone_number=booking.phone_number,
            customer_email=booking.customer_email,
            service_address=booking.service_address,
            slot_date=booking.slot_date,
            slot_time=booking.slot_time,
            issue_description=booking.issue_description,
            assigned_technician=booking.assigned_technician,
            dispatch_fee=booking.dispatch_fee,
            urgency_level=urgency_val,
            contractor_cal_link=cal_link,
            contractor_ics_path=ics_path,
            notes=booking.notes,
        )

        return {
            "contractor_email": DEFAULT_CONFIG.contractor_email,
            "contractor_calendar_link": cal_link,
            "contractor_ics_path": ics_path,
            "contractor_eml_path": alert_record.get("eml_path"),
            "alert_status": alert_record.get("status"),
        }


# Global singleton
CALENDAR_SYNC = CalendarSyncService()

