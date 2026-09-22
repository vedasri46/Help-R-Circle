import urllib.request, sys
url='http://127.0.0.1:5000/signup'
try:
    with urllib.request.urlopen(url, timeout=5) as r:
        html = r.read().decode('utf-8')
        print('SEND_EMAIL_PRESENT:', 'Send Verification Code' in html)
        print('SEND_PHONE_PRESENT:', 'Send OTP' in html)
        print('CREATE_BTN_PRESENT:', 'id="createAccountBtn"' in html)
        # Check disabled attribute presence
        idx = html.find('id="createAccountBtn"')
        if idx!=-1:
            snippet = html[idx:idx+200]
            print('CREATE_BTN_SNIPPET:', snippet)
except Exception as e:
    print('FETCH_ERROR', e)
    sys.exit(1)
