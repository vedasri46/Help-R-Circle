from pathlib import Path
p = Path('local_helper_network/templates/base.html')
text = p.read_text(encoding='utf-8')
text = text.replace("<li><a href=\"{{ url_for('go_volunteer') }}\">Become a Volunteer</a></li>", "<li><a href=\"{{ url_for('go_helper') }}\">Become a Helper</a></li>")
text = text.replace("<li><a href=\"{{ url_for('go_volunteer') }}\">Dashboard</a></li>", "<li><a href=\"{{ url_for('go_helper') }}\">Dashboard</a></li>")
p.write_text(text, encoding='utf-8')
print('patched')
