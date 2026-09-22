import os, smtplib, sys
server = os.environ.get('MAIL_SERVER')
port = int(os.environ.get('MAIL_PORT') or 0)
use_tls = os.environ.get('MAIL_USE_TLS', 'False').lower() in ('true','1','yes')
use_ssl = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true','1','yes')
username = os.environ.get('MAIL_USERNAME')
password = os.environ.get('MAIL_PASSWORD')
print('MAIL_SERVER configured' if server else 'MAIL_SERVER missing')
print('MAIL_PORT configured' if port else 'MAIL_PORT missing')
print('MAIL_USERNAME configured' if username else 'MAIL_USERNAME missing')
print('MAIL_PASSWORD configured' if password else 'MAIL_PASSWORD missing')
try:
    if use_ssl:
        smtp = smtplib.SMTP_SSL(server, port, timeout=10)
    else:
        smtp = smtplib.SMTP(server, port, timeout=10)
    smtp.set_debuglevel(0)
    smtp.ehlo()
    if use_tls:
        smtp.starttls()
        smtp.ehlo()
    if username and password:
        try:
            smtp.login(username, password)
            print('SMTP login: OK')
        except Exception as e:
            print('SMTP login failed:', str(e))
    else:
        print('Skipping login: no credentials')
    smtp.quit()
except Exception as e:
    print('SMTP connection failed:', str(e))
    sys.exit(1)
