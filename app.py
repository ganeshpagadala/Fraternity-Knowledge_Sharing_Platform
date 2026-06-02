from flask import Flask, render_template, redirect, request, url_for, session, flash, jsonify, abort
import random, os, uuid
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import config
from database.tables import create_tables
from database.utility import (
    addUser, login_user, get_user_by_id, get_user_by_username, get_user_by_email,
    update_profile, change_password, reset_password_by_email, search_users, get_suggested_users,
    create_post, delete_post, get_post, get_post_replies, get_post_media,
    track_view, get_following_feed, get_global_feed, get_intrafield_feed,
    get_user_posts, get_user_liked_posts, get_user_media_posts,
    get_bookmarked_posts, search_posts, get_trending_posts, get_trending_hashtags,
    toggle_like, toggle_repost, toggle_bookmark, get_post_reposters,
    toggle_follow, get_followers, get_following, get_follow_counts, is_following,
    add_comment, delete_comment, get_post_comments,
    add_notification, get_notifications, mark_notifications_read,
    get_unread_notification_count, notify_mentions, extract_mentions,
    send_message, get_conversation, mark_messages_read,
    get_conversations, get_unread_message_count
)
from emailsend import emailSend

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['UPLOAD_FOLDER']      = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

serializer = URLSafeTimedSerializer(app.secret_key)

# ── Startup init (runs under WSGI server too) ──────────────
with app.app_context():
    create_tables()
    for sub in ('media', 'avatars', 'covers'):
        os.makedirs(os.path.join(config.UPLOAD_FOLDER, sub), exist_ok=True)


# ─── Helpers ──────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in config.ALLOWED_EXTENSIONS

def save_upload(file, subfolder='media'):
    if file and allowed_file(file.filename):
        ext  = file.filename.rsplit('.',1)[1].lower()
        name = f"{uuid.uuid4().hex}.{ext}"
        dest = os.path.join(config.UPLOAD_FOLDER, subfolder, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file.save(dest)
        return f"uploads/{subfolder}/{name}"
    return None

def media_type_for(path):
    if not path: return None
    ext = path.rsplit('.',1)[-1].lower()
    if ext in config.ALLOWED_IMAGE_EXTENSIONS: return 'image'
    if ext in config.ALLOWED_VIDEO_EXTENSIONS: return 'video'
    if ext in config.ALLOWED_FILE_EXTENSIONS:  return 'file'
    return None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper

def current_user():
    uid = session.get('user_id')
    return get_user_by_id(uid) if uid else None

@app.context_processor
def inject_globals():
    user        = current_user()
    notif_count = get_unread_notification_count(user['id']) if user else 0
    msg_count   = get_unread_message_count(user['id'])      if user else 0
    return dict(current_user=user, notif_count=notif_count, msg_count=msg_count,
                field_categories=config.FIELD_CATEGORIES, now=datetime.utcnow())

@app.template_filter('timeago')
def timeago_filter(dt):
    if not dt: return ''
    if isinstance(dt, str):
        try: dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except: return dt
    diff = datetime.utcnow() - dt
    s = int(diff.total_seconds())
    if s < 60:     return f"{s}s ago"
    if s < 3600:   return f"{s//60}m ago"
    if s < 86400:  return f"{s//3600}h ago"
    if s < 604800: return f"{s//86400}d ago"
    return dt.strftime('%b %d')

@app.template_filter('mentionify')
def mentionify_filter(text):
    if not text: return ''
    import re
    return re.sub(r'@([A-Za-z0-9_]+)',
        r'<a href="/profile/\1" class="mention-link">@\1</a>', str(text))

# ─── OTP helpers ──────────────────────────────────────────
def generate_otp_token(email, salt='register_otp'):
    otp   = random.randint(1000, 9999)
    token = serializer.dumps({"email": email, "otp": otp}, salt=salt)
    return otp, token

# ═══ ROUTES ════════════════════════════════════════════════

@app.route('/')
@app.route('/index')
def home():
    if 'user_id' in session: return redirect(url_for('feed'))
    return render_template('index.html')

# ── Signup ────────────────────────────────────────────────
@app.route('/signup', methods=['GET','POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('feed'))
    if request.method == 'POST':
        for f in ('name','username','email','phonenumber','password'):
            session[f'reg_{f}'] = request.form.get(f,'').strip()
        otp, token = generate_otp_token(session['reg_email'])
        session['register_otp_token'] = token
        body = (f"Hi {session['reg_username']},\n\n"
                f"Your Fraternity verification OTP: {otp}\nValid for 2 minutes.\n\nTeam Fraternity")
        emailSend(session['reg_email'], "Fraternity — Email Verification", body)
        flash("OTP sent to your email.", "info")
        return redirect(url_for('verify_otp'))
    return render_template('auth/signup.html')

@app.route('/register/verifyOtp', methods=['GET','POST'])
def verify_otp():
    if 'register_otp_token' not in session: return redirect(url_for('signup'))
    if request.method == 'POST':
        entered = request.form.get('otp','').strip()
        try:
            data = serializer.loads(session['register_otp_token'], salt="register_otp", max_age=120)
            if str(data['otp']) == entered:
                ok = addUser(name=session['reg_name'], username=session['reg_username'],
                             email=session['reg_email'], phonenumber=session['reg_phonenumber'],
                             password=session['reg_password'])
                if ok:
                    for k in ('reg_name','reg_username','reg_email','reg_phonenumber','reg_password','register_otp_token'):
                        session.pop(k, None)
                    flash("Account created. Welcome to Fraternity.", "success")
                    return redirect(url_for('login'))
                flash("Username or email already taken.", "danger")
            else:
                flash("Incorrect OTP.", "danger")
        except SignatureExpired:
            flash("OTP expired. Please try again.", "danger")
            return redirect(url_for('signup'))
        except BadSignature:
            flash("Invalid OTP.", "danger")
    return render_template('auth/verifyotp.html')

# ── Forgot / Reset Password ───────────────────────────────
@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        user  = get_user_by_email(email)
        if user:
            otp, token = generate_otp_token(email, salt='reset_otp')
            session['reset_otp_token'] = token
            session['reset_email']     = email
            body = (f"Hi {user['name']},\n\n"
                    f"Your Fraternity password reset OTP: {otp}\n"
                    f"Valid for 5 minutes.\n\nIf you didn't request this, ignore this email.\n\nTeam Fraternity")
            emailSend(email, "Fraternity — Password Reset OTP", body)
            flash("OTP sent to your email.", "info")
            return redirect(url_for('reset_password'))
        else:
            flash("No account found with that email.", "danger")
    return render_template('auth/forgot_password.html')

@app.route('/reset-password', methods=['GET','POST'])
def reset_password():
    if 'reset_otp_token' not in session:
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        entered  = request.form.get('otp','').strip()
        new_pw   = request.form.get('new_password','')
        confirm  = request.form.get('confirm_password','')
        if new_pw != confirm:
            flash("Passwords don't match.", "danger")
            return render_template('auth/reset_password.html')
        if len(new_pw) < 6:
            flash("Minimum 6 characters.", "danger")
            return render_template('auth/reset_password.html')
        try:
            data = serializer.loads(session['reset_otp_token'], salt='reset_otp', max_age=300)
            if str(data['otp']) == entered:
                reset_password_by_email(session['reset_email'], new_pw)
                session.pop('reset_otp_token', None)
                session.pop('reset_email', None)
                flash("Password reset successful. Please sign in.", "success")
                return redirect(url_for('login'))
            else:
                flash("Incorrect OTP.", "danger")
        except SignatureExpired:
            flash("OTP expired. Please request a new one.", "danger")
            return redirect(url_for('forgot_password'))
        except BadSignature:
            flash("Invalid token.", "danger")
    return render_template('auth/reset_password.html')

# ── Login / Logout ────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session: return redirect(url_for('feed'))
    if request.method == 'POST':
        user = login_user(request.form.get('email','').strip(), request.form.get('password',''))
        if user:
            session['user_id'] = user['id']
            flash(f"Welcome back, {user['name']}.", "success")
            return redirect(request.args.get('next') or url_for('feed'))
        flash("Invalid email or password.", "danger")
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for('home'))

# ── Feed ──────────────────────────────────────────────────
@app.route('/feed')
@login_required
def feed():
    uid  = session['user_id']
    user = current_user()
    tab  = request.args.get('tab', 'following')
    page = int(request.args.get('page', 1))
    if tab == 'global':
        posts = get_global_feed(uid, page)
    elif tab == 'intrafield':
        posts = get_intrafield_feed(uid, user['field_category'], page)
    else:
        posts = get_following_feed(uid, page)
    for p in posts:
        p['media_list'] = get_post_media(p['id'])
    return render_template('app/feed.html', posts=posts, tab=tab, page=page,
        suggestions=get_suggested_users(uid, 4),
        trending=get_trending_posts(uid, 5),
        trending_tags=get_trending_hashtags(8))

# ── Post Create ───────────────────────────────────────────
@app.route('/post/create', methods=['POST'])
@login_required
def post_create():
    uid     = session['user_id']
    content = request.form.get('content','').strip()
    link    = request.form.get('link_url','').strip()
    field   = request.form.get('field_category', current_user()['field_category'])
    parent  = request.form.get('parent_post_id') or None
    quoted  = request.form.get('quoted_post_id')  or None
    ptype   = 'reply' if parent else ('quote' if quoted else 'post')

    media_files = []
    for f in request.files.getlist('media[]')[:4]:
        if f and f.filename:
            path = save_upload(f, 'media')
            if path:
                media_files.append((path, media_type_for(path)))

    if not content and not media_files:
        flash("Post cannot be empty.", "warning")
        return redirect(request.referrer or url_for('feed'))

    post_id = create_post(uid, content,
                          media_files=media_files or None,
                          link_url=link or None,
                          field_category=field,
                          post_type=ptype,
                          parent_post_id=int(parent) if parent else None,
                          quoted_post_id=int(quoted) if quoted else None)
    notify_mentions(content, uid, post_id)
    if parent:
        pp = get_post(int(parent), uid)
        if pp and pp['user_id'] != uid:
            add_notification(pp['user_id'], uid, 'reply', post_id=int(parent))
    if quoted:
        qp = get_post(int(quoted), uid)
        if qp and qp['user_id'] != uid:
            add_notification(qp['user_id'], uid, 'quote', post_id=int(quoted))
    return redirect(request.referrer or url_for('feed'))

# ── Post Detail ───────────────────────────────────────────
@app.route('/post/<int:post_id>')
@login_required
def post_detail(post_id):
    uid  = session['user_id']
    post = get_post(post_id, uid)
    if not post: abort(404)
    post['media_list'] = get_post_media(post_id)
    track_view(post_id, uid)
    replies = get_post_replies(post_id, uid)
    for r in replies:
        r['media_list'] = get_post_media(r['id'])
    comments = get_post_comments(post_id)
    return render_template('app/post_detail.html', post=post, replies=replies, comments=comments)

@app.route('/post/<int:post_id>/delete', methods=['GET','POST'])
@login_required
def post_delete(post_id):
    if request.method == 'POST':
        delete_post(post_id, session['user_id'])
    return redirect(url_for('feed'))

@app.route('/post/<int:post_id>/reposts')
@login_required
def post_reposts(post_id):
    uid  = session['user_id']
    post = get_post(post_id, uid)
    if not post: abort(404)
    post['media_list'] = []
    return render_template('app/post_reposts.html', post=post,
                           reposters=get_post_reposters(post_id, uid))

# ── AJAX ─────────────────────────────────────────────────
@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def post_like(post_id):
    uid = session['user_id']
    res = toggle_like(uid, post_id)
    post = get_post(post_id, uid)
    if post and res['action'] == 'liked':
        add_notification(post['user_id'], uid, 'like', post_id=post_id)
    return jsonify(res)

@app.route('/post/<int:post_id>/repost', methods=['POST'])
@login_required
def post_repost(post_id):
    uid   = session['user_id']
    field = (current_user() or {}).get('field_category','General')
    res   = toggle_repost(uid, post_id, field)
    post  = get_post(post_id, uid)
    if post and res['action'] == 'reposted':
        add_notification(post['user_id'], uid, 'repost', post_id=post_id)
    return jsonify(res)

@app.route('/post/<int:post_id>/bookmark', methods=['POST'])
@login_required
def post_bookmark(post_id):
    return jsonify(toggle_bookmark(session['user_id'], post_id))

# ── Comments ──────────────────────────────────────────────
@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def post_comment(post_id):
    uid     = session['user_id']
    content = request.form.get('content','').strip()
    if content:
        add_comment(post_id, uid, content)
        post = get_post(post_id, uid)
        if post and post['user_id'] != uid:
            add_notification(post['user_id'], uid, 'comment', post_id=post_id)
        notify_mentions(content, uid, post_id)
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/comment/<int:comment_id>/delete', methods=['GET','POST'])
@login_required
def comment_delete(comment_id):
    if request.method == 'POST':
        delete_comment(comment_id, session['user_id'])
    return redirect(request.referrer or url_for('feed'))

# ── Profile ───────────────────────────────────────────────
@app.route('/profile/<username>')
@login_required
def profile(username):
    uid = session['user_id']
    pu  = get_user_by_username(username)
    if not pu: abort(404)
    tab = request.args.get('tab','posts')
    if tab == 'likes':   posts = get_user_liked_posts(pu['id'], uid)
    elif tab == 'media': posts = get_user_media_posts(pu['id'], uid)
    else:                posts = get_user_posts(pu['id'], uid)
    for p in posts:
        p['media_list'] = get_post_media(p['id'])
    counts     = get_follow_counts(pu['id'])
    following  = is_following(uid, pu['id'])
    post_count = len(get_user_posts(pu['id'], uid, per_page=9999))
    return render_template('app/profile.html', profile_user=pu, posts=posts,
        counts=counts, is_following=following, post_count=post_count, tab=tab)

@app.route('/profile/<username>/followers')
@login_required
def profile_followers(username):
    uid = session['user_id']
    pu  = get_user_by_username(username)
    if not pu: abort(404)
    return render_template('app/follow_list.html', users=get_followers(pu['id'], uid),
                           profile_user=pu, list_type='Followers')

@app.route('/profile/<username>/following')
@login_required
def profile_following(username):
    uid = session['user_id']
    pu  = get_user_by_username(username)
    if not pu: abort(404)
    return render_template('app/follow_list.html', users=get_following(pu['id'], uid),
                           profile_user=pu, list_type='Following')

# ── Follow ────────────────────────────────────────────────
@app.route('/user/<int:user_id>/follow', methods=['POST'])
@login_required
def follow_user(user_id):
    uid = session['user_id']
    res = toggle_follow(uid, user_id)
    if res['action'] == 'followed':
        add_notification(user_id, uid, 'follow')
    return jsonify(res)

# ── Explore ───────────────────────────────────────────────
@app.route('/explore')
@login_required
def explore():
    uid   = session['user_id']
    query = request.args.get('q','').strip()
    field = request.args.get('field','')
    tab   = request.args.get('tab','posts')
    posts = []; users = []
    if query:
        if tab == 'users': users = search_users(query, uid)
        else:              posts = search_posts(query, uid)
    elif field: posts = get_intrafield_feed(uid, field, per_page=30)
    else:       posts = get_trending_posts(uid, limit=20)
    for p in posts:
        p['media_list'] = get_post_media(p['id'])
    return render_template('app/explore.html', posts=posts, users=users,
        query=query, field=field, tab=tab, trending_tags=get_trending_hashtags(10))

# ── Notifications ─────────────────────────────────────────
@app.route('/notifications')
@login_required
def notifications():
    uid    = session['user_id']
    notifs = get_notifications(uid)
    mark_notifications_read(uid)
    return render_template('app/notifications.html', notifications=notifs)

# ── Bookmarks ─────────────────────────────────────────────
@app.route('/bookmarks')
@login_required
def bookmarks():
    uid   = session['user_id']
    posts = get_bookmarked_posts(uid)
    for p in posts:
        p['media_list'] = get_post_media(p['id'])
    return render_template('app/bookmarks.html', posts=posts)

# ── Messages ──────────────────────────────────────────────
@app.route('/messages')
@login_required
def messages():
    uid   = session['user_id']
    convs = get_conversations(uid)
    return render_template('app/messages.html', conversations=convs)

@app.route('/messages/<int:other_id>', methods=['GET','POST'])
@login_required
def conversation(other_id):
    uid   = session['user_id']
    other = get_user_by_id(other_id)
    if not other: abort(404)
    if request.method == 'POST':
        content   = request.form.get('content','').strip()
        media_url = None
        mf        = request.files.get('media')
        if mf and mf.filename:
            media_url = save_upload(mf, 'media')
        if content or media_url:
            send_message(uid, other_id, content or None, media_url)
        return redirect(url_for('conversation', other_id=other_id))
    mark_messages_read(other_id, uid)
    msgs  = get_conversation(uid, other_id)
    convs = get_conversations(uid)
    return render_template('app/messages.html', conversations=convs,
                           active_user=other, msgs=msgs, other_id=other_id)

@app.route('/api/messages/<int:other_id>/poll')
@login_required
def messages_poll(other_id):
    uid   = session['user_id']
    after = request.args.get('after', 0, type=int)
    msgs  = get_conversation(uid, other_id)
    new   = [m for m in msgs if m['id'] > after]
    mark_messages_read(other_id, uid)
    return jsonify([{
        'id': m['id'], 'sender_id': m['sender_id'],
        'content': m['content'], 'media_url': m['media_url'],
        'created_at': m['created_at'].strftime('%H:%M') if m.get('created_at') else '',
        'is_mine': m['sender_id'] == uid
    } for m in new])

# ── Settings ──────────────────────────────────────────────
@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    uid  = session['user_id']
    user = current_user()
    tab  = request.args.get('tab','profile')
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            ap = save_upload(request.files.get('profile_pic'), 'avatars') \
                 if request.files.get('profile_pic') and request.files['profile_pic'].filename else None
            cp = save_upload(request.files.get('cover_pic'), 'covers') \
                 if request.files.get('cover_pic') and request.files['cover_pic'].filename else None
            update_profile(uid, request.form.get('name','').strip(),
                           request.form.get('bio','').strip(),
                           request.form.get('website','').strip(),
                           request.form.get('location_text','').strip(),
                           request.form.get('field_category','General'), ap, cp)
            flash("Profile updated.", "success")
            return redirect(url_for('settings', tab='profile'))
        elif action == 'change_password':
            old = request.form.get('old_password','')
            new = request.form.get('new_password','')
            cnf = request.form.get('confirm_password','')
            if new != cnf:       flash("Passwords don't match.", "danger")
            elif len(new) < 6:   flash("Minimum 6 characters.", "danger")
            elif change_password(uid, old, new): flash("Password changed.", "success")
            else:                flash("Current password incorrect.", "danger")
            return redirect(url_for('settings', tab='security'))
    return render_template('app/settings.html', user=user, tab=tab)

# ── Search API ────────────────────────────────────────────
@app.route('/api/search/users')
@login_required
def api_search_users():
    q   = request.args.get('q','').strip()
    uid = session['user_id']
    if len(q) < 2: return jsonify([])
    users = search_users(q, uid)
    return jsonify([{'id':u['id'],'name':u['name'],'username':u['username'],
                     'profile_pic':u['profile_pic']} for u in users[:6]])

# ── Entry ─────────────────────────────────────────────────
if __name__ == '__main__':
    create_tables()
    for sub in ('media','avatars','covers'):
        os.makedirs(os.path.join(config.UPLOAD_FOLDER, sub), exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
