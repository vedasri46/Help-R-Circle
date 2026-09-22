from pathlib import Path
from jinja2 import Environment
base = Path('local_helper_network')
errs = []
patterns = []
for path in base.rglob('*.html'):
    text = path.read_text(encoding='utf-8')
    rel = str(path.relative_to(base))
    if "\\'" in text or '\\"' in text:
        lines = [(i+1, line) for i, line in enumerate(text.splitlines()) if "\\'" in line or '\\"' in line]
        patterns.append((rel, lines))
    try:
        Environment().parse(text)
    except Exception as e:
        errs.append((rel, str(e)))
print('PATTERN_MATCHES')
for rel, lines in patterns:
    print(rel)
    for lineno, line in lines:
        print(f'{lineno}: {line}')
print('PARSE_ERRORS')
for rel, err in errs:
    print(rel)
    print(err)
