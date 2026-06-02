/* ══════════════════════════════════════════════════════════
   FRATERNITY — app.js
   ══════════════════════════════════════════════════════════ */

// Auto-dismiss toasts
document.querySelectorAll('[data-auto-dismiss]').forEach(el => setTimeout(() => el.remove(), 4000));

/* ── Delete post — fetch-based ──────────────────────────── */
async function deletePost(postId, btn) {
  if (!confirm('Delete this post? This cannot be undone.')) return;
  try {
    const resp = await fetch(`/post/${postId}/delete`, { method: 'POST' });
    if (resp.ok || resp.redirected) {
      // Remove card from feed without reload if possible
      const card = document.getElementById(`post-${postId}`);
      if (card) {
        card.style.opacity = '0';
        card.style.transition = 'opacity .25s';
        setTimeout(() => card.remove(), 260);
        showToast('Post deleted', 'info');
      } else {
        window.location.href = '/feed';
      }
    } else {
      showToast('Could not delete post', 'danger');
    }
  } catch(e) {
    showToast('Network error', 'danger');
  }
}

/* ── Post menu — click-based ────────────────────────────── */
function toggleMenu(postId) {
  const dd = document.getElementById(`dd-${postId}`);
  if (!dd) return;
  const isOpen = dd.classList.contains('open');
  // Close all other open menus
  document.querySelectorAll('.post-menu-dd.open').forEach(el => el.classList.remove('open'));
  if (!isOpen) dd.classList.add('open');
}
// Close menus on outside click
document.addEventListener('click', e => {
  if (!e.target.closest('.post-menu'))
    document.querySelectorAll('.post-menu-dd.open').forEach(el => el.classList.remove('open'));
});

/* ── Toast ─────────────────────────────────────────────── */
function showToast(msg, type = 'info') {
  let c = document.getElementById('toastContainer');
  if (!c) { c = document.createElement('div'); c.id = 'toastContainer'; c.className = 'toast-container'; document.body.appendChild(c); }
  const icons = { success: 'check', danger: 'times', warning: 'exclamation', info: 'info' };
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.innerHTML = `<i class="fas fa-${icons[type]||'info'}-circle"></i><span>${msg}</span><span class="toast-close" onclick="this.parentElement.remove()">×</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/* ── Compose Modal ─────────────────────────────────────── */
let pendingMedia = [];

function openComposeModal(quotedId, quotedText) {
  const ov = document.getElementById('composeOv');
  if (!ov) return;
  if (quotedId) {
    document.getElementById('quotedPostId').value = quotedId;
    const w = document.getElementById('quoteCtxWrap');
    if (w) { w.classList.remove('hidden'); document.getElementById('quoteCtxText').textContent = quotedText || ''; }
  }
  ov.classList.add('open');
  setTimeout(() => document.getElementById('composeTa')?.focus(), 60);
}
function closeCompose(e) {
  if (!e || e.target === document.getElementById('composeOv')) {
    document.getElementById('composeOv')?.classList.remove('open');
    document.getElementById('quotedPostId').value = '';
    document.getElementById('quoteCtxWrap')?.classList.add('hidden');
    pendingMedia = [];
    const g = document.getElementById('mediaPrevGrid');
    if (g) { g.classList.add('hidden'); g.innerHTML = ''; }
    document.getElementById('mediaLbl')?.classList.add('hidden');
  }
}

// Char counter
const cta = document.getElementById('composeTa');
const cc  = document.getElementById('charCount');
if (cta && cc) {
  cta.addEventListener('input', () => {
    const l = cta.value.length;
    cc.textContent = l;
    cc.parentElement.className = `compose-char ${l > 460 ? 'warn' : ''}`;
  });
}

/* ── Multi-media ────────────────────────────────────────── */
function handleMediaSelect(input) {
  const files = Array.from(input.files);
  const left  = 4 - pendingMedia.length;
  if (left <= 0) { showToast('Maximum 4 files per post', 'warning'); input.value = ''; return; }
  files.slice(0, left).forEach(f => {
    const url  = URL.createObjectURL(f);
    const type = f.type.startsWith('image/') ? 'image' : f.type.startsWith('video/') ? 'video' : 'file';
    pendingMedia.push({ file: f, url, type });
  });
  if (files.length > left) showToast(`Only ${left} more file(s) allowed`, 'info');
  renderMediaPrev();
  input.value = '';
}
function renderMediaPrev() {
  const g   = document.getElementById('mediaPrevGrid');
  const lbl = document.getElementById('mediaLbl');
  if (!g) return;
  if (!pendingMedia.length) {
    g.classList.add('hidden'); g.innerHTML = '';
    lbl?.classList.add('hidden'); return;
  }
  g.classList.remove('hidden');
  g.className = `media-prev-grid c${pendingMedia.length}`;
  g.innerHTML = pendingMedia.map((m, i) => `
    <div class="mpg-item">
      ${m.type === 'image' ? `<img src="${m.url}" alt="">` :
        m.type === 'video' ? `<video src="${m.url}" muted></video>` :
        `<div style="display:flex;align-items:center;justify-content:center;height:100%;padding:8px;font-family:var(--font-m);font-size:11px;color:var(--txt3)">${m.file.name}</div>`}
      <span class="mpg-item-rm" onclick="removeMedia(${i})">×</span>
    </div>`).join('');
  if (lbl) { lbl.classList.remove('hidden'); lbl.textContent = `${pendingMedia.length}/4 file${pendingMedia.length > 1 ? 's' : ''}`; }
}
function removeMedia(i) { pendingMedia.splice(i, 1); renderMediaPrev(); }

document.getElementById('composeForm')?.addEventListener('submit', function () {
  if (!pendingMedia.length) return;
  const dt = new DataTransfer();
  pendingMedia.forEach(m => dt.items.add(m.file));
  const inp = document.getElementById('mediaInput');
  if (inp) inp.files = dt.files;
});

/* ── Link & Emoji ───────────────────────────────────────── */
function toggleLink() { document.getElementById('linkRow')?.classList.toggle('hidden'); }
function toggleEmoji() { document.getElementById('emojiPanel')?.classList.toggle('hidden'); }
function insertEmoji(e) {
  const ta = document.getElementById('composeTa');
  if (!ta) return;
  const p = ta.selectionStart;
  ta.value = ta.value.slice(0, p) + e + ta.value.slice(p);
  ta.selectionStart = ta.selectionEnd = p + e.length;
  ta.focus();
  if (cc) cc.textContent = ta.value.length;
  document.getElementById('emojiPanel')?.classList.add('hidden');
}
document.addEventListener('click', ev => {
  const ep = document.getElementById('emojiPanel');
  if (ep && !ep.classList.contains('hidden') && !ev.target.closest('.emoji-toggle') && !ev.target.closest('.emoji-panel'))
    ep.classList.add('hidden');
});

/* ── Reply Modal ────────────────────────────────────────── */
function openReplyModal(postId, username, snippet) {
  const ov = document.getElementById('replyOv');
  if (!ov) return;
  document.getElementById('replyCtx').innerHTML =
    `Replying to <strong style="color:var(--gold)">@${username}</strong>${snippet ? `<br><em style="font-size:12px;color:var(--txt3)">${snippet}</em>` : ''}`;
  document.getElementById('replyParentId').value = postId;
  ov.classList.add('open');
  ov.querySelector('textarea')?.focus();
}
function closeReply(e) {
  if (!e || e.target === document.getElementById('replyOv'))
    document.getElementById('replyOv')?.classList.remove('open');
}
document.addEventListener('keydown', ev => {
  if (ev.key === 'Escape')
    document.querySelectorAll('.modal-ov.open').forEach(m => m.classList.remove('open'));
});

/* ── AJAX: Like ─────────────────────────────────────────── */
async function handleLike(btn) {
  const id = btn.dataset.post;
  try {
    const d = await (await fetch(`/post/${id}/like`, { method: 'POST' })).json();
    btn.querySelector('.lc').textContent = d.count;
    if (d.action === 'liked') {
      btn.classList.add('active');
      btn.querySelector('i').className = 'fas fa-heart';
      btn.style.transform = 'scale(1.3)';
      setTimeout(() => btn.style.transform = '', 160);
    } else {
      btn.classList.remove('active');
      btn.querySelector('i').className = 'far fa-heart';
    }
  } catch (e) {}
}

/* ── AJAX: Repost ───────────────────────────────────────── */
async function handleRepost(btn) {
  const id = btn.dataset.post;
  try {
    const d = await (await fetch(`/post/${id}/repost`, { method: 'POST' })).json();
    btn.querySelector('.rc').textContent = d.count;
    if (d.action === 'reposted') { btn.classList.add('active'); showToast('Reposted', 'success'); }
    else { btn.classList.remove('active'); showToast('Repost removed', 'info'); }
  } catch (e) {}
}

/* ── AJAX: Bookmark ─────────────────────────────────────── */
async function handleBookmark(btn) {
  const id = btn.dataset.post;
  try {
    const d = await (await fetch(`/post/${id}/bookmark`, { method: 'POST' })).json();
    if (d.action === 'bookmarked') {
      btn.classList.add('active');
      btn.querySelector('i').className = 'fas fa-bookmark';
      showToast('Saved', 'success');
    } else {
      btn.classList.remove('active');
      btn.querySelector('i').className = 'far fa-bookmark';
      showToast('Removed from saved', 'info');
    }
  } catch (e) {}
}

/* ── AJAX: Follow ───────────────────────────────────────── */
async function handleFollow(btn) {
  const id = btn.dataset.uid;
  try {
    const d = await (await fetch(`/user/${id}/follow`, { method: 'POST' })).json();
    if (d.action === 'followed') {
      btn.classList.add('following');
      btn.innerHTML = '<i class="fas fa-user-check"></i> Following';
      showToast('Now following', 'success');
    } else {
      btn.classList.remove('following');
      btn.innerHTML = '<i class="fas fa-user-plus"></i> Follow';
    }
    const fc = btn.parentElement?.querySelector('.count-link strong');
    if (fc) fc.textContent = d.follower_count;
  } catch (e) {}
}

/* ── Global search ──────────────────────────────────────── */
const gSearch = document.getElementById('globalSearch');
const gDD     = document.getElementById('searchDD');
let searchTimer;
if (gSearch && gDD) {
  gSearch.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = gSearch.value.trim();
    if (q.length < 2) { gDD.classList.remove('open'); return; }
    searchTimer = setTimeout(async () => {
      try {
        const users = await (await fetch(`/api/search/users?q=${encodeURIComponent(q)}`)).json();
        if (!users.length) { gDD.classList.remove('open'); return; }
        gDD.innerHTML = users.map(u => `
          <a href="/profile/${u.username}" class="sdd-item">
            <img src="/static/${u.profile_pic}" class="av-xs"
                 onerror="this.src='/static/uploads/default_avatar.png'">
            <div><strong>${u.name}</strong><small>@${u.username}</small></div>
          </a>`).join('');
        gDD.classList.add('open');
      } catch (e) {}
    }, 280);
  });
  document.addEventListener('click', e => {
    if (!e.target.closest('.sb-search')) gDD.classList.remove('open');
  });
}

/* ── Lightbox ───────────────────────────────────────────── */
function openLightbox(src) {
  let lb = document.getElementById('lightbox');
  if (!lb) {
    lb = document.createElement('div'); lb.id = 'lightbox';
    lb.innerHTML = `<img id="lb-img" src=""><span id="lb-close" onclick="closeLightbox()">×</span>`;
    lb.onclick = e => { if (e.target === lb) closeLightbox(); };
    document.body.appendChild(lb);
  }
  lb.querySelector('#lb-img').src = src;
  lb.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeLightbox() {
  document.getElementById('lightbox')?.classList.remove('open');
  document.body.style.overflow = '';
}

/* ── Message polling ────────────────────────────────────── */
let lastMsgId = 0;
function startMsgPolling(otherId) {
  const box = document.getElementById('chatMessages');
  if (!box) return;
  lastMsgId = parseInt(box.dataset.lastId || 0);
  setInterval(async () => {
    try {
      const data = await (await fetch(`/api/messages/${otherId}/poll?after=${lastMsgId}`)).json();
      if (!data.length) return;
      data.forEach(m => {
        if (m.id > lastMsgId) lastMsgId = m.id;
        const d = document.createElement('div');
        d.className = `msg-bbl ${m.is_mine ? 'mine' : 'theirs'}`;
        d.innerHTML = `<div class="msg-text">${esc(m.content || '')}</div>
          ${m.media_url ? `<img src="/static/${m.media_url}" class="msg-media" onclick="openLightbox(this.src)">` : ''}
          <span class="msg-ts">${m.created_at}</span>`;
        box.appendChild(d);
      });
      box.scrollTop = box.scrollHeight;
    } catch (e) {}
  }, 3000);
}

/* ── Settings previews ──────────────────────────────────── */
function previewAvatar(input) {
  if (!input.files[0]) return;
  const r = new FileReader();
  r.onload = e => document.getElementById('avatarPreview').src = e.target.result;
  r.readAsDataURL(input.files[0]);
}
function previewCover(input) {
  if (!input.files[0]) return;
  const r = new FileReader();
  r.onload = e => document.getElementById('coverPrev').style.backgroundImage = `url(${e.target.result})`;
  r.readAsDataURL(input.files[0]);
}

/* ── @Mention autocomplete ──────────────────────────────── */
function setupMentionAC(ta) {
  if (!ta) return;
  const ac = document.createElement('div');
  ac.className = 'mention-ac';
  ac.style.cssText = 'display:none;position:absolute;min-width:200px;z-index:600';
  ta.parentElement.style.position = 'relative';
  ta.parentElement.appendChild(ac);
  let atIdx = -1;
  ta.addEventListener('input', async () => {
    const v = ta.value, pos = ta.selectionStart, text = v.slice(0, pos);
    const idx = text.lastIndexOf('@');
    if (idx === -1 || (idx > 0 && !/\s/.test(text[idx-1]) === false)) { ac.style.display = 'none'; return; }
    const q = text.slice(idx + 1);
    if (!q || q.length < 1 || /\s/.test(q)) { ac.style.display = 'none'; return; }
    atIdx = idx;
    try {
      const users = await (await fetch(`/api/search/users?q=${encodeURIComponent(q)}`)).json();
      if (!users.length) { ac.style.display = 'none'; return; }
      ac.innerHTML = users.map(u => `<div class="mac-item" data-un="${u.username}" onclick="doMention(this)">
        <img src="/static/${u.profile_pic}" class="av-xs" onerror="this.src='/static/uploads/default_avatar.png'">
        <div><strong>${u.name}</strong><small>@${u.username}</small></div></div>`).join('');
      ac.style.display = 'block';
    } catch (e) { ac.style.display = 'none'; }
  });
  document.addEventListener('click', e => { if (!e.target.closest('.mention-ac')) ac.style.display = 'none'; });
  ta._getAtIdx = () => atIdx;
  ta._ac = ac;
}
function doMention(item) {
  const ta = item.closest('.compose-fields, .chat-compose, form')?.querySelector('textarea, input[type=text]');
  if (!ta) return;
  const ac = item.closest('.mention-ac');
  const idx = ta._getAtIdx ? ta._getAtIdx() : ta.value.lastIndexOf('@');
  if (idx === -1) return;
  ta.value = ta.value.slice(0, idx) + '@' + item.dataset.un + ' ' + ta.value.slice(ta.selectionStart);
  ta.focus();
  if (ac) ac.style.display = 'none';
}

/* ── Utility ────────────────────────────────────────────── */
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// Init
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.compose-fields textarea, .cc-ta').forEach(setupMentionAC);
});
