import html
import smtplib
from email.mime.text import MIMEText

import markdown


def markdown_to_html(md_text):
    return markdown.markdown(md_text)


def send_email(gmail_address, gmail_app_password, recipient_email, subject, html_body):
    recipients = [addr.strip() for addr in recipient_email.split(",") if addr.strip()]

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())


def send_debug_email(gmail_address, gmail_app_password, recipient_email, errors):
    body = "<h2>Debug report</h2><ul>" + "".join(f"<li>{html.escape(str(e))}</li>" for e in errors) + "</ul>"
    send_email(gmail_address, gmail_app_password, recipient_email, "⚠️ Debug report", body)
