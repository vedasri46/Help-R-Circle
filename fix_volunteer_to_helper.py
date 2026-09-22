from pathlib import Path
path = Path('local_helper_network/templates/base.html')
text = path.read_text(encoding='utf-8')
text = text.replace("<li><a href='{{ url_for('go_volunteer') }}'    class='nav-link {% if request.endpoint=='volunteer' or request.endpoint=='go_volunteer' %}active{% endif %}'>Volunteer</a></li>", "<li><a href='{{ url_for('go_helper') }}' class='nav-link {% if request.endpoint=='helper_registration' or request.endpoint=='go_helper' %}active{% endif %}'>Helper</a></li>")
text = text.replace("{% if session.get('role') == 'volunteer' %}", "{% if session.get('role') == 'helper' %}")
path.write_text(text, encoding='utf-8')
print('done')
