import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

class EmailSender:
    def __init__(self):
        self.host = os.getenv('SMTP_HOST')
        self.port = int(os.getenv('SMTP_PORT', 587))
        self.user = os.getenv('SMTP_USER')
        self.password = os.getenv('SMTP_PASS')

    def send_email(self, to_email, subject, body, is_html=True):
        if not self.user or not self.password:
            return False, "SMTP credentials not configured"

        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to_email
            msg['Subject'] = subject

            content_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, content_type))

            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()
            return True, "Email sent successfully"
        except Exception as e:
            return False, str(e)
