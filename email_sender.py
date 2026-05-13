import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os

class EmailSender:
    def __init__(self, host=None, port=587, user=None, password=None):
        self.host = host or os.getenv('SMTP_HOST')
        self.port = int(port or os.getenv('SMTP_PORT', 587))
        self.user = user or os.getenv('SMTP_USER')
        self.password = password or os.getenv('SMTP_PASS')

    def send_email(self, to_email, subject, body, image_data=None, is_html=True):
        if not self.user or not self.password:
            return False, "Credenciales SMTP no configuradas"

        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to_email
            msg['Subject'] = subject

            # Cuerpo del mensaje
            content_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, content_type))

            # Adjuntar imagen si existe
            if image_data:
                img = MIMEImage(image_data.read())
                img.add_header('Content-ID', '<image1>')
                msg.attach(img)

            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()
            return True, "Email enviado con éxito"
        except Exception as e:
            return False, str(e)
