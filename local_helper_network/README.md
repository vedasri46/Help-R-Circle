# 🤝 Help R Circle

**Help R Circle** is a community-based platform that connects people who need temporary assistance with local community members willing to help, especially in rural communities.

---

## 📁 Project Structure

```
local_helper_network/
├── app.py              ← Flask server (routes, form handling)
├── database.py         ← SQLite database layer (all DB logic)
├── requirements.txt    ← Python dependencies (just Flask)
├── local_helper.db     ← Auto-created SQLite database (gitignore this)
├── static/
│   ├── css/style.css   ← All styles (responsive, accessible)
│   └── js/main.js      ← JavaScript (nav, animations, validation)
└── templates/
    ├── base.html        ← Shared layout (navbar, footer, flash)
    ├── index.html       ← Home page
    ├── request_help.html← Submit a help request
    ├── volunteer.html   ← Volunteer registration
    ├── dashboard.html   ← View & accept requests
    ├── track.html       ← Track request by ID
    ├── about.html       ← About the project
    └── contact.html     ← Contact form
```

---

## ⚙️ Setup Instructions (Step by Step)

### Step 1 — Make sure Python is installed
```bash
python --version    # Should be 3.8 or higher
```
If not installed, download from https://python.org

---

### Step 2 — Open terminal in the project folder
```bash
cd local_helper_network
```

---

### Step 3 — (Optional but recommended) Create a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```
You'll see `(venv)` in your prompt when it's active.

---

### Step 4 — Install dependencies
```bash
pip install -r requirements.txt
```
This installs Flask (the only dependency).

---

### Step 5 — Run the application
```bash
python app.py
```
You should see:
```
✅ Database initialized.
✅ Sample data seeded.
 * Running on http://127.0.0.1:5000
```

---

### Step 6 — Open in browser
Visit: **http://127.0.0.1:5000**

---

## 🌐 Pages & URLs

| Page              | URL              | Description                    |
|-------------------|------------------|--------------------------------|
| Home              | /                | Landing page with stats        |
| Request Help      | /request-help    | Submit a help request          |
| Volunteer Sign-Up | /volunteer       | Register as a volunteer        |
| Dashboard         | /dashboard       | View & manage all requests     |
| Track Request     | /track           | Check request status by ID     |
| About             | /about           | Project info & mission         |
| Contact           | /contact         | Send a message                 |

---

## 🗄️ Database Schema

### `help_requests` table
| Column         | Type    | Description                            |
|----------------|---------|----------------------------------------|
| id             | INTEGER | Auto-incrementing primary key          |
| name           | TEXT    | Name of person requesting help         |
| phone          | TEXT    | Contact phone number                   |
| location       | TEXT    | Area / locality                        |
| help_type      | TEXT    | Type of help needed                    |
| description    | TEXT    | Detailed description                   |
| urgency        | TEXT    | urgent / normal / low                  |
| status         | TEXT    | pending → accepted → completed         |
| volunteer_name | TEXT    | Name of volunteer who accepted (null)  |
| created_at     | TEXT    | Timestamp when submitted               |
| updated_at     | TEXT    | Timestamp of last status change        |

### `volunteers` table
| Column       | Type    | Description                      |
|--------------|---------|----------------------------------|
| id           | INTEGER | Auto-incrementing primary key    |
| name         | TEXT    | Volunteer's full name            |
| phone        | TEXT    | Contact number                   |
| email        | TEXT    | Email (optional)                 |
| location     | TEXT    | Area they can serve              |
| skills       | TEXT    | Comma-separated help types       |
| availability | TEXT    | When they are available          |
| about        | TEXT    | Short bio (optional)             |
| is_active    | INTEGER | 1 = active, 0 = inactive         |
| created_at   | TEXT    | Registration timestamp           |

### `contact_messages` table
| Column     | Type    | Description              |
|------------|---------|--------------------------|
| id         | INTEGER | Primary key              |
| name       | TEXT    | Sender name              |
| email      | TEXT    | Sender email             |
| message    | TEXT    | Message content          |
| created_at | TEXT    | Timestamp                |

---

## ✨ Features Summary

- ✅ Submit help requests (with urgency levels)
- ✅ Volunteer registration (with skill checkboxes)
- ✅ Volunteer dashboard with search & filter
- ✅ Accept requests (with volunteer name)
- ✅ Mark requests as completed
- ✅ Cancel requests
- ✅ Track any request by ID with visual timeline
- ✅ Contact form
- ✅ Sample data auto-loaded for demo
- ✅ Flash messages for all actions
- ✅ Mobile responsive design
- ✅ Accessible UI (large text, clear labels)
- ✅ Animated statistics on home page

---

## 💡 Suggestions for Improvement

1. **Login / Auth** — Add Flask-Login for volunteer accounts
2. **Email Notifications** — Use Flask-Mail to notify volunteers of new requests
3. **Map Integration** — Show requests on a Google Maps widget
4. **Ratings** — Allow requesters to rate volunteers after completion
5. **Admin Panel** — Flask-Admin for full admin control
6. **Export** — Download requests as CSV / PDF reports

---

## 🔧 Troubleshooting

**Port already in use?**
```bash
python app.py  # Change port at bottom of app.py: app.run(port=5001)
```

**ModuleNotFoundError: flask?**
```bash
pip install flask
```

**Database issues?**
Delete `local_helper.db` and restart — it will be recreated fresh.

---

Built for college project demonstration. 
