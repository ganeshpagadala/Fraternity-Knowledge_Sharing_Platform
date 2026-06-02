# Quire — Social Network for Queries & Ideas

A full-featured Flask social media application with feed, intra-field/inter-field timelines, rich media posts, follows, likes, reposts, and more.

## Features

| Feature | Description |
|---|---|
| **Feed — Following** | Chronological posts from people you follow |
| **Feed — Intra-Field** | Posts from your field/discipline only |
| **Feed — Inter-Field** | All posts across every field (global) |
| **Post Types** | Text · Image · Video · File attachments · Links |
| **Emoji** | Built-in emoji picker in composer |
| **Requery** | Repost/amplify any query to your followers |
| **Like / Bookmark** | React and save posts |
| **Replies / Threads** | Nested reply threads on any post |
| **Follow / Unfollow** | Build your network |
| **Profiles** | Full profile with posts, media, liked tabs |
| **Explore** | Search posts & people; browse by field |
| **Notifications** | Likes, requeries, follows, replies |
| **Trending** | Hot posts & hashtags this week |
| **Settings** | Edit profile, cover, bio, change password |
| **OTP Email Verification** | Secure signup flow |

## Project Structure

```
quire/
├── app.py                  # All routes & Flask setup
├── config.py               # DB / upload / email config
├── emailsend.py            # SMTP email helper
├── requirements.txt
├── database/
│   ├── tables.py           # CREATE TABLE statements
│   └── utility.py          # All DB operations (CRUD)
├── templates/
│   ├── base.html           # Root layout + toast system
│   ├── app_shell.html      # 3-column app shell + compose modal
│   ├── index.html          # Landing page
│   ├── macros/
│   │   └── post_card.html  # Reusable post card macro
│   ├── auth/
│   │   ├── login.html
│   │   ├── signup.html
│   │   └── verifyotp.html
│   └── app/
│       ├── feed.html        # Main timeline (3 tabs)
│       ├── explore.html     # Search + field browse
│       ├── profile.html     # User profile
│       ├── post_detail.html # Thread view
│       ├── notifications.html
│       ├── bookmarks.html
│       ├── settings.html
│       └── follow_list.html
└── static/
    ├── css/main.css         # Full design system
    ├── js/app.js            # AJAX interactions
    └── uploads/             # User media (auto-created)
```

## Setup

### 1. MySQL Database

```sql
-- config.py defaults to these, change as needed:
-- host: localhost · user: root · password: '' · db: quire_db
-- The app auto-creates the database and all tables on first run.
```

### 2. Install Dependencies

```bash
pip install flask mysql-connector-python itsdangerous werkzeug
```

### 3. Configure Email (config.py)

```python
SENDER_EMAIL = "your.email@gmail.com"
EMAIL_PASSKEY = "your_app_password"  # Gmail App Password
```

### 4. Run

```bash
python app.py
```

Visit `http://localhost:5000`

## Feed Tabs Explained

- **Following** — Posts only from users you follow (your curated stream)
- **Intra-Field** — All posts tagged with your field category (e.g., "Technology")
- **Inter-Field** — Every public post on the platform, sorted by newest first

## Field Categories

General · Technology · Science · Engineering · Medicine · Law · Business · Arts · Education · Sports · Politics · Environment · Philosophy · History · Mathematics

## Tech Stack

- **Backend**: Flask + MySQL (mysql-connector-python)
- **Auth**: Session-based + OTP email verification (itsdangerous)
- **Uploads**: Werkzeug secure file handling
- **Frontend**: Vanilla JS + CSS custom design system
- **Fonts**: Outfit + Manrope (Google Fonts)
- **Icons**: Font Awesome 6
