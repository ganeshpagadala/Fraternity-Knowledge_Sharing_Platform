import sqlite3, os
import config

def get_connection():
    conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        username      TEXT UNIQUE NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        phonenumber   TEXT,
        password      TEXT NOT NULL,
        bio           TEXT,
        profile_pic   TEXT DEFAULT 'uploads/default_avatar.png',
        cover_pic     TEXT DEFAULT 'uploads/default_cover.jpg',
        website       TEXT,
        location_text TEXT,
        field_category TEXT DEFAULT 'General',
        is_verified   INTEGER DEFAULT 0,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS posts (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        content          TEXT,
        media_url        TEXT,
        media_type       TEXT,
        link_url         TEXT,
        link_title       TEXT,
        post_type        TEXT DEFAULT 'post',
        original_post_id INTEGER,
        quoted_post_id   INTEGER,
        parent_post_id   INTEGER,
        field_category   TEXT DEFAULT 'General',
        repost_count     INTEGER DEFAULT 0,
        like_count       INTEGER DEFAULT 0,
        reply_count      INTEGER DEFAULT 0,
        view_count       INTEGER DEFAULT 0,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id)          REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (original_post_id) REFERENCES posts(id) ON DELETE SET NULL,
        FOREIGN KEY (quoted_post_id)   REFERENCES posts(id) ON DELETE SET NULL,
        FOREIGN KEY (parent_post_id)   REFERENCES posts(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS post_media (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL,
        media_url  TEXT NOT NULL,
        media_type TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS post_views (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id   INTEGER NOT NULL,
        user_id   INTEGER NOT NULL,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(post_id, user_id),
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS comments (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        content    TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS likes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        post_id    INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS reposts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        post_id    INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS follows (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id  INTEGER NOT NULL,
        following_id INTEGER NOT NULL,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(follower_id, following_id),
        FOREIGN KEY (follower_id)  REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bookmarks (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        post_id    INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        from_user_id INTEGER NOT NULL,
        type         TEXT NOT NULL,
        post_id      INTEGER,
        message      TEXT,
        is_read      INTEGER DEFAULT 0,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id)      REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS messages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id   INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        content     TEXT,
        media_url   TEXT,
        is_read     INTEGER DEFAULT 0,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id)   REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print("[DB] Fraternity SQLite tables ready.")
