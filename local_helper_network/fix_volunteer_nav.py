from pathlib import Path
path = Path('templates/base.html')
text = path.read_text(encoding='utf-8')
lines = text.splitlines()
old_line = "      <li><a href=\"{{ url_for('go_volunteer') }}\"    class=\"nav-link {% if request.endpoint=='volunteer' or request.endpoint=='go_volunteer' %}active{% endif %}\">Volunteer</a></li>"
new_line = "      <li><a href=\"{{ url_for('go_helper') }}\" class=\"nav-link {% if request.endpoint=='helper_registration' or request.endpoint=='go_helper' %}active{% endif %}\">Helper</a></li>"
old_cond = "      {% if session.get('role') == 'volunteer' %}"
new_cond = "      {% if session.get('role') == 'helper' %}"
updated = False
for i, line in enumerate(lines):
    if line == old_line:
        lines[i] = new_line
        updated = True
    elif line == old_cond:
        lines[i] = new_cond
        updated = True
if not updated:
    raise SystemExit('No matching volunteer lines found')
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('patched', updated)
