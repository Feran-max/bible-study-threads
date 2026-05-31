import os
import requests
import time
import json

# ─── Configuration ───────────────────────────────────────────────────────────
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"
REPLIED_FILE = "replied_ids.json"  # Fichier pour tracker les commentaires déjà traités

# ─── Charger / sauvegarder les IDs déjà traités ──────────────────────────────
def load_replied_ids() -> set:
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_replied_ids(ids: set):
    with open(REPLIED_FILE, "w") as f:
        json.dump(list(ids), f)

# ─── Récupérer le User ID ────────────────────────────────────────────────────
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

# ─── Récupérer les posts récents ─────────────────────────────────────────────
def get_recent_posts(user_id: str) -> list:
    resp = requests.get(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        params={
            "fields": "id,text,timestamp",
            "limit": 10,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=15,
    )
    resp.raise_for_status()
    posts = resp.json().get("data", [])
    print(f"📋 Found {len(posts)} recent posts")
    return posts

# ─── Récupérer les commentaires d'un post ────────────────────────────────────
def get_replies(post_id: str) -> list:
    resp = requests.get(
        f"https://graph.threads.net/v1.0/{post_id}/replies",
        params={
            "fields": "id,text,timestamp,username",
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"⚠️ Could not fetch replies for post {post_id}: {resp.status_code}")
        return []
    return resp.json().get("data", [])

# ─── Générer une réponse personnalisée avec Groq ─────────────────────────────
def generate_reply(comment_text: str, username: str) -> str:
    prompt = f"""You are a warm, authentic Christian community manager for the Threads account @esther_bes, which promotes Bible study and the 30-Day Bible Study Starter Kit.

Someone named @{username} commented on one of your posts:
\"{comment_text}\"

Write a short, genuine reply (max 200 characters) that:
- Feels personal and warm, not robotic
- Engages with what they actually said
- Occasionally (not always) mentions the 30-Day Bible Study Starter Kit if it feels natural
- Uses 1 emoji max
- Does NOT start with "I" or sound like a bot

Reply ONLY with the response text, nothing else."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.9,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Groq failed ({e}), using fallback reply.")
        return "Thank you for sharing this 🙏 God bless you on your faith journey!"

# ─── Poster une réponse ──────────────────────────────────────────────────────
def post_reply(user_id: str, reply_to_id: str, text: str) -> bool:
    base_url = f"https://graph.threads.net/v1.0/{user_id}"

    # Créer le container de réponse
    create_resp = requests.post(
        f"{base_url}/threads",
        data={
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": reply_to_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not create_resp.ok:
        print(f"❌ Reply container error: {create_resp.status_code} — {create_resp.text}")
        return False

    container_id = create_resp.json()["id"]

    print("⏳ Waiting 30s (Meta requirement)...")
    time.sleep(30)

    # Publier la réponse
    publish_resp = requests.post(
        f"{base_url}/threads_publish",
        data={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not publish_resp.ok:
        print(f"❌ Reply publish error: {publish_resp.status_code} — {publish_resp.text}")
        return False

    print(f"✅ Reply posted! ID: {publish_resp.json()['id']}")
    return True

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN missing.")
        exit(1)

    replied_ids = load_replied_ids()
    print(f"📂 Already replied to {len(replied_ids)} comments")

    user_id = get_user_id()
    posts = get_recent_posts(user_id)

    total_replied = 0

    for post in posts:
        post_id = post["id"]
        post_text = post.get("text", "")[:50]
        replies = get_replies(post_id)

        for reply in replies:
            reply_id = reply["id"]
            username = reply.get("username", "friend")
            comment_text = reply.get("text", "")

            if reply_id in replied_ids:
                continue  # Déjà traité

            if not comment_text.strip():
                continue  # Commentaire vide

            print(f"\n💬 New comment from @{username}: \"{comment_text[:60]}\"")

            reply_text = generate_reply(comment_text, username)
            print(f"💬 Replying: \"{reply_text}\"")

            success = post_reply(user_id, reply_id, reply_text)
            if success:
                replied_ids.add(reply_id)
                save_replied_ids(replied_ids)
                total_replied += 1

            time.sleep(5)  # Petite pause entre les réponses

    print(f"\n✅ Done — replied to {total_replied} new comments")
