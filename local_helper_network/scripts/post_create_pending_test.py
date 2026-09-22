import urllib.request, urllib.parse, sys
url = 'http://127.0.0.1:5000/create-pending'
data = {
    'username': 'Test Debugger',
    'email': 'debug+test@example.com',
    'phone': '9876543210',
    'password': 'Password123!',
    'confirm_password': 'Password123!',
    'role': 'user'
}
post = urllib.parse.urlencode(data).encode()
req = urllib.request.Request(url, data=post)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print('STATUS', r.status)
        print(r.read().decode())
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
