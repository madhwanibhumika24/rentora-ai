import smtplib
from email.mime.text import MIMEText

from app.config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.email_user or not settings.email_password:
        print(f"[DEV MODE] Email to {to}: {subject}\n{body}")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.email_user
    msg["To"] = to

    with smtplib.SMTP(settings.email_host, settings.email_port) as server:
        server.starttls()
        server.login(settings.email_user, settings.email_password)
        server.sendmail(settings.email_user, [to], msg.as_string())

    return True