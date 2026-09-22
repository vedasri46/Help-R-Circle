from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)

app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME="helprcircle.support@gmail.com",
    MAIL_PASSWORD="hcovwlryoxbbdzqi",
    MAIL_DEFAULT_SENDER="Help R Circle <helprcircle.support@gmail.com>"
)

mail = Mail(app)

with app.app_context():
    msg = Message(
        subject="SMTP Test",
        recipients=["helprcircle.support@gmail.com"],  # Replace with your own email
        body="Hello! This is a test email from Flask."
    )

    mail.send(msg)
    print("✅ Email sent successfully!")