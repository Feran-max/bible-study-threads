import os
import requests
import time
import json
import random
import base64

# ─── Configuration ───────────────────────────────────────────────────────────
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GH_TOKEN")
GITHUB_REPO = "Feran-max/bible-study-threads"
REPLIED_FILE = "replied_ids.json"
GROQ_MODEL = "llama3-8b-8192"
BOT_USERNAME = "estherbes_bible"

FALLBACK_REPLIES = [
    "Amen! So glad this resonated with you today 🙏",
    "God's word never fails — keep holding on!",
    "That's beautiful, keep pressing forward in faith!",
    "So grateful you're on this journey with us ✨",
    "Yes! His faithfulness never runs out 🙏",
    "Keep seeking Him — He's always faithful!",
    "That's so encouraging, thank you for sharing!",
    "God hears every prayer — never stop believing!",
]

# ─── Persistance via GitHub API ───────────────────────────────────────────────
def load_replied_ids_from_github() -> tuple[set, str | None]:
    """Charge les IDs depuis le repo GitHub. Retourne (ids, sha_du_fichier)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{REPLIED_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 404:
        print("📂 No replied_ids.json yet — starting fresh.")
        return set(), None
    resp.raise_for_status()
    data = resp.json()
    content = json.loads(base64.b64decode(data["content"]).decode())
    print(f"📂 Loaded {len(content)} already-replied IDs from GitHub.")
    return set(content), data["sha"]

def save_replied_ids_to_github(ids: set, sha: str | None):
    """Sauvegarde les IDs dans le repo GitHub (crée ou met à jour le fichier)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{REPLIED_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    content_b64 = base64.b64encode(json.dumps(list(ids)).encode()).decode()
    payload = {
        "message": "chore: update replied comment IDs",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=headers, json=payload, timeout=15)
    if resp.ok:
        print(f"✅ Saved {len(ids)} replied IDs to GitHub repo.")
    else:
        print(f"⚠️ Could not save IDs: {resp.status_code} — {resp.text}")

# ─── API Threads ──────────────────────────────────────────────────────────────
def get_user_id() -> str:
    resp = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"✅ User: @{data['username']} ({data['id']})")
    return data["id"]

def get_recent_posts(user_id: str) -> list:
    resp = requests.get(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        params={"fields": "id,text,timestamp", "limit": 10, "access_token": THREADS_ACCESS_TOKEN},
        timeout=15,
    )
    resp.raise_for_status()
    posts = resp.json().get("data", [])
    print(f"📋 Found {len(posts)} recent posts")
    return posts

def get_comments(post_id: str) -> list:
    resp = requests.get(
        f"https://graph.threads.net/v1.0/{post_id}/replies",
        params={"fields": "id,text,timestamp,username", "access_token": THREADS_ACCESS_TOKEN},
        timeout=15,
    )
    if not resp.ok:
        return []
    return resp.json().get("data", [])

def generate_reply(comment_text: str, username: str) -> str:
    if not GROQ_API_KEY:
        return random.choice(FALLBACK_REPLIES)
    prompt = f"""You are a warm Christian community manager for @estherbes_bible on Threads.

@{username} commented: "{comment_text}"

Write ONE short reply (max 180 characters) that:
- Directly responds to what they actually said
- Feels human and warm, not robotic
- Uses at most 1 emoji
- Does NOT start with "Thank you for sharing"
- Is NOT generic — reference their specific words

Reply ONLY with the text."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
                "temperature": 1.0,
            },
            timeout=30,
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip()
        if len(reply) > 5:
            return reply
        return random.choice(FALLBACK_REPLIES)
    except Exception as e:
        print(f"⚠️ Groq failed ({e})")
        return random.choice(FALLBACK_REPLIES)

def post_reply(user_id: str, reply_to_id: str, text: str) -> bool:
    base_url = f"https://graph.threads.net/v1.0/{user_id}"
    create_resp = requests.post(
        f"{base_url}/threads",
        data={"media_type": "TEXT", "text": text, "reply_to_id": reply_to_id, "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    if not create_resp.ok:
        print(f"❌ Container error: {create_resp.text}")
        return False
    container_id = create_resp.json()["id"]
    print("⏳ Waiting 30s...")
    time.sleep(30)
    publish_resp = requests.post(
        f"{base_url}/threads_publish",
        data={"creation_id": container_id, "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    if not publish_resp.ok:
        print(f"❌ Publish error: {publish_resp.text}")
        return False
    print(f"✅ Reply posted!")
    return True

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN missing.")
        exit(1)
    if not GITHUB_TOKEN:
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        print("❌ GITHUB_TOKEN missing.")
        exit(1)

    # Charger les IDs déjà traités depuis GitHub
    replied_ids, file_sha = load_replied_ids_from_github()

    user_id = get_user_id()
    posts = get_recent_posts(user_id)
    total_replied = 0

    for post in posts:
        comments = get_comments(post["id"])
        for comment in comments:
            comment_id = comment["id"]
            username = comment.get("username", "")
            text = comment.get("text", "").strip()

            # Skip si bot, si déjà traité, si vide
            if username == BOT_USERNAME:
                continue
            if comment_id in replied_ids:
                print(f"⏭️ Already replied to @{username} ({comment_id[:10]}...) — skipping")
                continue
            if not text:
                continue

            print(f"\n💬 @{username}: \"{text[:80]}\"")
            reply_text = generate_reply(text, username)
            print(f"🤖 Reply: \"{reply_text}\"")

            success = post_reply(user_id, comment_id, reply_text)
            if success:
                replied_ids.add(comment_id)
                total_replied += 1
            time.sleep(5)

    # Sauvegarder les IDs mis à jour dans GitHub
    if total_replied > 0:
        save_replied_ids_to_github(replied_ids, file_sha)
    else:
        print("✅ No new comments to reply to.")

    print(f"\n✅ Done — replied to {total_replied} new comments")
