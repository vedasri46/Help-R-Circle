import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


def main():
    client = app.test_client()
    paths = ['/', '/signup', '/login', '/helper']
    results = {}
    for p in paths:
        resp = client.get(p)
        results[p] = resp.status_code
    for p, code in results.items():
        print(p, code)
    # Consider 200 or 302 valid (login redirects)
    bad = [p for p,c in results.items() if c not in (200,302)]
    if bad:
        print('Some pages returned unexpected status codes:', bad)
        return 1
    print('All checked pages OK')
    return 0

if __name__ == '__main__':
    exit(main())
