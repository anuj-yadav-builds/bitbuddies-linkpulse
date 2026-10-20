# LinkPulse - URL Shortener & Analytics Platform

> Team **BitBuddies** | Tech Geeks Hackathon, Round 2

**Live demo:** https://bitbuddies-linkpulse.onrender.com

## Problem statement
Long links are hard to share, and normal short links tell you nothing about who clicked them.

## Our solution
LinkPulse turns any long link into a short one and shows analytics for every click:
how many people clicked, when, on which device and browser, and from which website.

## Features
- Register and sign in (passwords are stored hashed, never as plain text)
- Create short links with a custom alias or an auto-generated code
- Link options: expiry date, click limit, password protection, campaign, tags
- Fast redirect that counts every click (QR scans are counted separately)
- Dashboard: totals, clicks this week, link alerts, campaign performance, top links
- Analytics per link: clicks over time, devices, browsers, traffic sources
- Campaigns to group links
- Bulk import of links from a CSV file (with a row-by-row report)
- Admin: see all links, disable or re-enable a link, block unsafe domains
- QR code for every short link (download as PNG)

## Tech stack
| Part | Technology |
|------|------------|
| Backend | Python, Flask, Flask-SQLAlchemy |
| Database | MySQL (Aiven cloud MySQL in production) |
| Frontend | Jinja2 templates, Bootstrap 5, Chart.js, qrcodejs |
| Hosting | Render |

## Run it on your laptop
1. Install Python 3.9+ and MySQL, then create an empty database:
   `CREATE DATABASE linkpulse CHARACTER SET utf8mb4;`
2. Clone the repo and open the folder in a terminal:
   ```
   git clone https://github.com/anuj-yadav-builds/bitbuddies-linkpulse.git
   cd bitbuddies-linkpulse
   python -m venv venv
   venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`, fill in your MySQL password, and set `ADMIN_EMAIL`
   to the email you will register with (that account becomes the admin).
4. Start the app: `python app.py` and open http://127.0.0.1:5000
5. Register with the admin email, sign in, and create your first link.
6. Check everything works: `python smoke_test.py`

The tables are created automatically on the first start.

## Pages
| URL | What it shows |
|-----|---------------|
| `/register`, `/login`, `/logout` | Account pages |
| `/` | Dashboard |
| `/links`, `/links/new`, `/links/<code>` | Links list, create wizard, link details with QR code |
| `/links/<code>/analytics` | Charts for one link |
| `/campaigns`, `/import` | Campaigns, bulk CSV import |
| `/admin` | Admin: all links, block domains (admin only) |
| `/<code>` | The short link itself: redirect, or a status/password page |
| `/health` | Is the app and database working? |

## Screenshots
Add 3-4 screenshots here (dashboard, new link, analytics, admin).

## Team BitBuddies
Anuj Yadav, Muskan Samant, Harshit Singh, Pooja Joshi, Gaurav Joshi
