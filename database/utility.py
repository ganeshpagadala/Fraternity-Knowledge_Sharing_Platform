from database.tables import get_connection
import hashlib, re
from datetime import datetime, timedelta

# ─── Helpers ──────────────────────────────────────────────
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def rows_as_dicts(cursor):
    return [dict(row) for row in cursor.fetchall()]

def row_as_dict(cursor):
    row = cursor.fetchone()
    return dict(row) if row else None

def _fix_dates(row):
    """Convert SQLite timestamp strings → datetime objects."""
    if not row: return row
    for k in ('created_at','viewed_at','last_time'):
        v = row.get(k)
        if isinstance(v, str):
            for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M:%S.%f'):
                try: row[k] = datetime.strptime(v, fmt); break
                except ValueError: pass
    return row

def _fix_list(rows):
    return [_fix_dates(r) for r in rows]

# ══════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════

def addUser(name, username, email, phonenumber, password):
    try:
        conn = get_connection(); c = conn.cursor()
        c.execute("INSERT INTO users (name,username,email,phonenumber,password) VALUES (?,?,?,?,?)",
                  (name, username, email, phonenumber, hash_password(password)))
        conn.commit(); conn.close(); return True
    except Exception as e:
        print(f"[addUser] {e}"); return False

def get_user_by_email(email):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    r = row_as_dict(c); conn.close(); return _fix_dates(r)

def login_user(email, password):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    r = row_as_dict(c); conn.close()
    if not r or r.get('password','') != hash_password(password): return None
    return _fix_dates(r)

def get_user_by_id(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    r = row_as_dict(c); conn.close(); return _fix_dates(r)

def get_user_by_username(username):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    r = row_as_dict(c); conn.close(); return _fix_dates(r)

def update_profile(user_id, name, bio, website, location_text, field_category,
                   profile_pic=None, cover_pic=None):
    conn = get_connection(); c = conn.cursor()
    if profile_pic and cover_pic:
        c.execute("UPDATE users SET name=?,bio=?,website=?,location_text=?,field_category=?,profile_pic=?,cover_pic=? WHERE id=?",
                  (name,bio,website,location_text,field_category,profile_pic,cover_pic,user_id))
    elif profile_pic:
        c.execute("UPDATE users SET name=?,bio=?,website=?,location_text=?,field_category=?,profile_pic=? WHERE id=?",
                  (name,bio,website,location_text,field_category,profile_pic,user_id))
    elif cover_pic:
        c.execute("UPDATE users SET name=?,bio=?,website=?,location_text=?,field_category=?,cover_pic=? WHERE id=?",
                  (name,bio,website,location_text,field_category,cover_pic,user_id))
    else:
        c.execute("UPDATE users SET name=?,bio=?,website=?,location_text=?,field_category=? WHERE id=?",
                  (name,bio,website,location_text,field_category,user_id))
    conn.commit(); conn.close()

def change_password(user_id, old_password, new_password):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id=? AND password=?", (user_id, hash_password(old_password)))
    if c.fetchone():
        c.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_password), user_id))
        conn.commit(); conn.close(); return True
    conn.close(); return False

def reset_password_by_email(email, new_password):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE email=?", (hash_password(new_password), email))
    affected = c.rowcount
    conn.commit(); conn.close()
    return affected > 0

def search_users(query, current_user_id):
    conn = get_connection(); c = conn.cursor()
    like = f"%{query}%"
    c.execute("""SELECT u.*,
        (SELECT COUNT(*) FROM follows WHERE follower_id=? AND following_id=u.id) AS is_following
        FROM users u WHERE (u.name LIKE ? OR u.username LIKE ?) AND u.id!=? LIMIT 20""",
        (current_user_id, like, like, current_user_id))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_suggested_users(current_user_id, limit=5):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT u.*, 0 AS is_following FROM users u
        WHERE u.id!=? AND u.id NOT IN (SELECT following_id FROM follows WHERE follower_id=?)
        ORDER BY RANDOM() LIMIT ?""", (current_user_id, current_user_id, limit))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

# ══════════════════════════════════════════════════════════
#  POSTS
# ══════════════════════════════════════════════════════════

def _post_base(uid):
    return f"""SELECT p.*,
        u.name, u.username, u.profile_pic, u.field_category AS user_field, u.is_verified,
        (SELECT COUNT(*) FROM likes     WHERE post_id=p.id) AS like_count,
        (SELECT COUNT(*) FROM reposts   WHERE post_id=p.id) AS repost_count,
        (SELECT COUNT(*) FROM comments  WHERE post_id=p.id) AS comment_count,
        (SELECT COUNT(*) FROM post_views WHERE post_id=p.id) AS view_count,
        (SELECT COUNT(*) FROM likes     WHERE post_id=p.id AND user_id={uid}) AS user_liked,
        (SELECT COUNT(*) FROM reposts   WHERE post_id=p.id AND user_id={uid}) AS user_reposted,
        (SELECT COUNT(*) FROM bookmarks WHERE post_id=p.id AND user_id={uid}) AS user_bookmarked,
        op.content AS orig_content, ou.name AS orig_name,
        ou.username AS orig_username, ou.profile_pic AS orig_profile_pic,
        qp.content AS quoted_content, qp.media_url AS quoted_media_url,
        qu.name AS quoted_name, qu.username AS quoted_username,
        qu.profile_pic AS quoted_profile_pic, qu.field_category AS quoted_field
        FROM posts p
        JOIN users u ON u.id=p.user_id
        LEFT JOIN posts op ON op.id=p.original_post_id
        LEFT JOIN users ou ON ou.id=op.user_id
        LEFT JOIN posts qp ON qp.id=p.quoted_post_id
        LEFT JOIN users qu ON qu.id=qp.user_id"""

def get_post_media(post_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM post_media WHERE post_id=? ORDER BY sort_order", (post_id,))
    r = rows_as_dicts(c); conn.close(); return r

def create_post(user_id, content, media_files=None, link_url=None, link_title=None,
                field_category='General', post_type='post', original_post_id=None,
                parent_post_id=None, quoted_post_id=None):
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO posts
        (user_id,content,link_url,link_title,field_category,post_type,original_post_id,parent_post_id,quoted_post_id)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, content, link_url, link_title, field_category, post_type,
         original_post_id, parent_post_id, quoted_post_id))
    post_id = c.lastrowid
    if media_files:
        for i, (url, mtype) in enumerate(media_files):
            c.execute("INSERT INTO post_media (post_id,media_url,media_type,sort_order) VALUES (?,?,?,?)",
                      (post_id, url, mtype, i))
    if original_post_id and post_type == 'repost':
        c.execute("UPDATE posts SET repost_count=repost_count+1 WHERE id=?", (original_post_id,))
        c.execute("INSERT OR IGNORE INTO reposts (user_id,post_id) VALUES (?,?)", (user_id, original_post_id))
    if parent_post_id:
        c.execute("UPDATE posts SET reply_count=reply_count+1 WHERE id=?", (parent_post_id,))
    conn.commit(); conn.close()
    return post_id

def delete_post(post_id, user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
    affected = c.rowcount
    conn.commit(); conn.close()
    return affected > 0

def get_post(post_id, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.id=?", (post_id,))
    r = row_as_dict(c); conn.close(); return _fix_dates(r)

def track_view(post_id, user_id):
    conn = get_connection(); c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO post_views (post_id,user_id) VALUES (?,?)", (post_id, user_id))
        conn.commit()
    except Exception: pass
    conn.close()

def get_following_feed(user_id, page=1, per_page=20):
    offset = (page-1)*per_page
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(user_id) + """
        WHERE (p.user_id IN (SELECT following_id FROM follows WHERE follower_id=?) OR p.user_id=?)
        AND p.parent_post_id IS NULL ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
        (user_id, user_id, per_page, offset))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_global_feed(current_user_id, page=1, per_page=20):
    offset = (page-1)*per_page
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.parent_post_id IS NULL ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
              (per_page, offset))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_intrafield_feed(user_id, field, page=1, per_page=20):
    offset = (page-1)*per_page
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(user_id) + " WHERE p.field_category=? AND p.parent_post_id IS NULL ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
              (field, per_page, offset))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_user_posts(profile_user_id, current_user_id, page=1, per_page=20):
    offset = (page-1)*per_page
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.user_id=? AND p.parent_post_id IS NULL ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
              (profile_user_id, per_page, offset))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_user_liked_posts(profile_user_id, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.id IN (SELECT post_id FROM likes WHERE user_id=?) ORDER BY p.created_at DESC LIMIT 50",
              (profile_user_id,))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_user_media_posts(profile_user_id, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.user_id=? AND p.id IN (SELECT DISTINCT post_id FROM post_media) ORDER BY p.created_at DESC LIMIT 50",
              (profile_user_id,))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_bookmarked_posts(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(user_id) + " WHERE p.id IN (SELECT post_id FROM bookmarks WHERE user_id=?) ORDER BY p.created_at DESC",
              (user_id,))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_post_replies(post_id, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.parent_post_id=? ORDER BY p.created_at ASC", (post_id,))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def search_posts(query, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + " WHERE p.content LIKE ? ORDER BY p.created_at DESC LIMIT 30",
              (f"%{query}%",))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_trending_posts(current_user_id, limit=10):
    conn = get_connection(); c = conn.cursor()
    c.execute(_post_base(current_user_id) + """
        WHERE p.parent_post_id IS NULL
        AND p.created_at >= datetime('now','-7 days')
        ORDER BY (p.like_count + p.repost_count*2 + p.reply_count) DESC LIMIT ?""", (limit,))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_trending_hashtags(limit=10):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT content FROM posts WHERE created_at >= datetime('now','-7 days')
                 AND content IS NOT NULL LIMIT 500""")
    rows = c.fetchall(); conn.close()
    counts = {}
    for row in rows:
        for tag in re.findall(r'#([A-Za-z0-9_]+)', row[0] or ''):
            counts[f'#{tag}'] = counts.get(f'#{tag}', 0) + 1
    sorted_tags = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{'tag': t, 'count': n} for t, n in sorted_tags]

# ── Likes ──────────────────────────────────────────────────
def toggle_like(user_id, post_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM likes WHERE user_id=? AND post_id=?", (user_id, post_id))
    if c.fetchone():
        c.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (user_id, post_id))
        c.execute("UPDATE posts SET like_count=MAX(like_count-1,0) WHERE id=?", (post_id,))
        action = 'unliked'
    else:
        c.execute("INSERT OR IGNORE INTO likes (user_id,post_id) VALUES (?,?)", (user_id, post_id))
        c.execute("UPDATE posts SET like_count=like_count+1 WHERE id=?", (post_id,))
        action = 'liked'
    c.execute("SELECT like_count FROM posts WHERE id=?", (post_id,))
    count = c.fetchone()[0]
    conn.commit(); conn.close()
    return {'action': action, 'count': count}

# ── Reposts ────────────────────────────────────────────────
def toggle_repost(user_id, post_id, field_category='General'):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM reposts WHERE user_id=? AND post_id=?", (user_id, post_id))
    if c.fetchone():
        c.execute("DELETE FROM reposts WHERE user_id=? AND post_id=?", (user_id, post_id))
        c.execute("DELETE FROM posts WHERE user_id=? AND original_post_id=? AND post_type='repost'", (user_id, post_id))
        c.execute("UPDATE posts SET repost_count=MAX(repost_count-1,0) WHERE id=?", (post_id,))
        action = 'unreposted'
    else:
        c.execute("INSERT OR IGNORE INTO reposts (user_id,post_id) VALUES (?,?)", (user_id, post_id))
        c.execute("INSERT INTO posts (user_id,post_type,original_post_id,field_category) VALUES (?,'repost',?,?)",
                  (user_id, post_id, field_category))
        c.execute("UPDATE posts SET repost_count=repost_count+1 WHERE id=?", (post_id,))
        action = 'reposted'
    c.execute("SELECT repost_count FROM posts WHERE id=?", (post_id,))
    count = c.fetchone()[0]
    conn.commit(); conn.close()
    return {'action': action, 'count': count}

def get_post_reposters(post_id, viewer_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT u.id, u.name, u.username, u.profile_pic, u.field_category, u.is_verified,
               (SELECT COUNT(*) FROM follows WHERE follower_id=? AND following_id=u.id) AS is_following
        FROM reposts r JOIN users u ON u.id=r.user_id
        WHERE r.post_id=? ORDER BY r.created_at DESC""", (viewer_id, post_id))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

# ── Bookmarks ──────────────────────────────────────────────
def toggle_bookmark(user_id, post_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM bookmarks WHERE user_id=? AND post_id=?", (user_id, post_id))
    if c.fetchone():
        c.execute("DELETE FROM bookmarks WHERE user_id=? AND post_id=?", (user_id, post_id))
        action = 'unbookmarked'
    else:
        c.execute("INSERT OR IGNORE INTO bookmarks (user_id,post_id) VALUES (?,?)", (user_id, post_id))
        action = 'bookmarked'
    conn.commit(); conn.close()
    return {'action': action}

# ── Follows ────────────────────────────────────────────────
def toggle_follow(follower_id, following_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=?", (follower_id, following_id))
    if c.fetchone():
        c.execute("DELETE FROM follows WHERE follower_id=? AND following_id=?", (follower_id, following_id))
        action = 'unfollowed'
    else:
        c.execute("INSERT OR IGNORE INTO follows (follower_id,following_id) VALUES (?,?)", (follower_id, following_id))
        action = 'followed'
    c.execute("SELECT COUNT(*) FROM follows WHERE following_id=?", (following_id,))
    follower_count = c.fetchone()[0]
    conn.commit(); conn.close()
    return {'action': action, 'follower_count': follower_count}

def get_followers(user_id, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT u.*,
        (SELECT COUNT(*) FROM follows WHERE follower_id=? AND following_id=u.id) AS is_following
        FROM users u INNER JOIN follows f ON f.follower_id=u.id WHERE f.following_id=?""",
        (current_user_id, user_id))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_following(user_id, current_user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT u.*,
        (SELECT COUNT(*) FROM follows WHERE follower_id=? AND following_id=u.id) AS is_following
        FROM users u INNER JOIN follows f ON f.following_id=u.id WHERE f.follower_id=?""",
        (current_user_id, user_id))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def get_follow_counts(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM follows WHERE following_id=?", (user_id,))
    followers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (user_id,))
    following = c.fetchone()[0]
    conn.close()
    return {'followers': followers, 'following': following}

def is_following(follower_id, following_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=?", (follower_id, following_id))
    r = c.fetchone(); conn.close(); return r is not None

# ── Comments ───────────────────────────────────────────────
def add_comment(post_id, user_id, content):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO comments (post_id,user_id,content) VALUES (?,?,?)", (post_id, user_id, content))
    cid = c.lastrowid
    conn.commit(); conn.close()
    return cid

def delete_comment(comment_id, user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM comments WHERE id=? AND user_id=?", (comment_id, user_id))
    affected = c.rowcount
    conn.commit(); conn.close()
    return affected > 0

def get_post_comments(post_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT c.*, u.name, u.username, u.profile_pic, u.is_verified
        FROM comments c JOIN users u ON u.id=c.user_id
        WHERE c.post_id=? ORDER BY c.created_at ASC""", (post_id,))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

# ── Notifications ──────────────────────────────────────────
def add_notification(user_id, from_user_id, ntype, post_id=None, message=None):
    if user_id == from_user_id: return
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO notifications (user_id,from_user_id,type,post_id,message) VALUES (?,?,?,?,?)",
              (user_id, from_user_id, ntype, post_id, message))
    conn.commit(); conn.close()

def get_notifications(user_id, limit=50):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT n.*, u.name AS from_name, u.username AS from_username, u.profile_pic AS from_avatar
        FROM notifications n JOIN users u ON u.id=n.from_user_id
        WHERE n.user_id=? ORDER BY n.created_at DESC LIMIT ?""", (user_id, limit))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def mark_notifications_read(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()

def get_unread_notification_count(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user_id,))
    count = c.fetchone()[0]; conn.close(); return count

# ── @Mentions ──────────────────────────────────────────────
def extract_mentions(content):
    return re.findall(r'@([A-Za-z0-9_]+)', content or '')

def notify_mentions(content, from_user_id, post_id):
    for username in extract_mentions(content):
        user = get_user_by_username(username)
        if user and user['id'] != from_user_id:
            add_notification(user['id'], from_user_id, 'mention', post_id=post_id)

# ── Messages ───────────────────────────────────────────────
def send_message(sender_id, receiver_id, content, media_url=None):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO messages (sender_id,receiver_id,content,media_url) VALUES (?,?,?,?)",
              (sender_id, receiver_id, content, media_url))
    mid = c.lastrowid
    conn.commit(); conn.close()
    return mid

def get_conversation(user_a, user_b, limit=100):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT m.*, u.name AS sender_name, u.username AS sender_username, u.profile_pic AS sender_pic
        FROM messages m JOIN users u ON u.id=m.sender_id
        WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?)
        ORDER BY m.created_at ASC LIMIT ?""",
        (user_a, user_b, user_b, user_a, limit))
    r = rows_as_dicts(c); conn.close(); return _fix_list(r)

def mark_messages_read(sender_id, receiver_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?", (sender_id, receiver_id))
    conn.commit(); conn.close()

def get_conversations(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT DISTINCT CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END AS other_id
        FROM messages WHERE sender_id=? OR receiver_id=?""", (user_id, user_id, user_id))
    other_ids = [r[0] for r in c.fetchall()]; conn.close()
    result = []
    for oid in other_ids:
        u = get_user_by_id(oid)
        if not u: continue
        conn2 = get_connection(); c2 = conn2.cursor()
        c2.execute("""SELECT content, created_at FROM messages
            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
            ORDER BY created_at DESC LIMIT 1""", (user_id, oid, oid, user_id))
        last = c2.fetchone()
        c2.execute("SELECT COUNT(*) FROM messages WHERE sender_id=? AND receiver_id=? AND is_read=0", (oid, user_id))
        unread = c2.fetchone()[0]; conn2.close()
        u['last_message'] = last[0] if last else None
        u['last_time']    = last[1] if last else None
        u['unread_count'] = unread
        _fix_dates(u)
        result.append(u)
    result.sort(key=lambda x: x.get('last_time') or datetime.min, reverse=True)
    return result

def get_unread_message_count(user_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0", (user_id,))
    count = c.fetchone()[0]; conn.close(); return count
