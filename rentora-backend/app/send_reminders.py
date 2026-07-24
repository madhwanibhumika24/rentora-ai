from app.database import SessionLocal
from app.services.reminders import get_reminders_due_today


def main():
    db = SessionLocal()
    try:
        reminders = get_reminders_due_today(db)
        if not reminders:
            print("No reminders to send today.")
            return

        for r in reminders:
            # TODO: replace this print with a real SMS/push/WhatsApp call,
            # e.g. Twilio, MSG91, or Firebase Cloud Messaging.
            print(
                f"[{r['stage']}] Reminder to {r['tenant_name']} ({r['tenant_phone']}): "
                f"Rs {r['amount']} due on {r['due_date']}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()