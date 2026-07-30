"""
Notification Service Layer for MyGlowTheory.
Abstracts communication channels (Email, SMS, Calendar Invites) from booking logic.
Integrates with future notification APIs (Twilio, SendGrid, Google Calendar).
Currently logs and simulates background notification dispatching.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("notifications")
logger.setLevel(logging.INFO)

# Ensure runtime notifications log directory exists
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runtime", "notifications"))
os.makedirs(LOGS_DIR, exist_ok=True)

class NotificationService:
    @staticmethod
    def log_notification(channel: str, patient_id: str, recipient: str, message: str, details: Dict[str, Any] = None) -> None:
        """Simulates sending a notification by writing to a log file in the runtime directory."""
        log_path = os.path.join(LOGS_DIR, f"{channel}_log.jsonl")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "patient_id": patient_id,
            "recipient": recipient,
            "message": message,
            "details": details or {}
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info(f"Simulated {channel.upper()} sent to {recipient}: {message}")

    @classmethod
    def send_confirmation_email(cls, appointment: Dict[str, Any], patient_name: str, patient_email: str, provider_name: str, service_name: str) -> None:
        """Sends an email notification to the patient confirming their appointment."""
        start_time = appointment.get("start", "N/A")
        price = appointment.get("price", 0.0)
        message = (
            f"Hi {patient_name}, your appointment for {service_name} with {provider_name} "
            f"on {start_time} has been confirmed. Total price: ${price:.2f}. "
            "Thank you for choosing MyGlowTheory!"
        )
        cls.log_notification(
            channel="email",
            patient_id=appointment.get("patient_id"),
            recipient=patient_email,
            message=message,
            details={
                "appointment_id": appointment.get("id"),
                "provider_name": provider_name,
                "service_name": service_name,
                "start": start_time
            }
        )

    @classmethod
    def send_confirmation_sms(cls, appointment: Dict[str, Any], patient_name: str, patient_phone: str, provider_name: str, service_name: str) -> None:
        """Sends an SMS notification to the patient confirming their appointment."""
        start_time = appointment.get("start", "N/A")
        message = (
            f"MyGlowTheory: Hello {patient_name}, your {service_name} with {provider_name} "
            f"on {start_time} is confirmed! Need to reschedule? Please reply to this message."
        )
        cls.log_notification(
            channel="sms",
            patient_id=appointment.get("patient_id"),
            recipient=patient_phone,
            message=message,
            details={
                "appointment_id": appointment.get("id"),
                "provider_name": provider_name,
                "service_name": service_name,
                "start": start_time
            }
        )

    @classmethod
    def generate_calendar_invite(cls, appointment: Dict[str, Any], patient_name: str, patient_email: str, provider_name: str, service_name: str) -> None:
        """Generates an ICS calendar file representation and logs invite dispatch."""
        start_time = appointment.get("start", "N/A")
        duration = appointment.get("duration", 30)
        
        # Build invite description
        invite_desc = f"ICS Calendar invite generated for {patient_name} (Email: {patient_email}) with {provider_name} for {service_name}."
        cls.log_notification(
            channel="calendar",
            patient_id=appointment.get("patient_id"),
            recipient=patient_email,
            message=invite_desc,
            details={
                "appointment_id": appointment.get("id"),
                "provider_name": provider_name,
                "service_name": service_name,
                "start": start_time,
                "duration_minutes": duration
            }
        )
