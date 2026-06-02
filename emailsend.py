import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import SENDER_EMAIL, EMAIL_PASSKEY

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587

def emailSend(to_email: str, header: str, body: str) -> str:
    try:
        msg            = MIMEMultipart()
        msg['From']    = SENDER_EMAIL
        msg['To']      = to_email
        msg['Subject'] = header
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSKEY)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return f"Email sent to {to_email}"
    except Exception as e:
        return f"Email error: {e}"
