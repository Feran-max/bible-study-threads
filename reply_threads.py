import os
import requests
import time
import json
import random

# ─── Configuration ───────────────────────────────────────────────────────────
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"

# ─── Fallbacks variés pour éviter la répétition ──────────────────────────────
FALLBACK_REPLIES = [
    "That means so much 🙏 Keep holding onto your faith!",
    "Amen! So glad this resonated with you today.",
    "God's word never fails — thank you for being here!",
    "This community is such a blessing. Thank you! 🙏",
    "Keep pressing forward in faith — you've got this!",
    "So grateful you're on this journey with us ✨",
    "That's beautiful — God hears every prayer.",
    "Yes! His faithfulness never runs out 🙏",
]

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
        print(f"⚠️ Could not fetch replies for {post_id}: {resp.status_code}")
        return []
    return resp.json().get("data", [])

# ─── Récupérer les IDs des réponses déjà postées par le bot ─────────────────
def get_already_replied_ids(user_id: str) -> set:
    """
    Récupère directement depuis l'API Threads les commentaires
    que @estherbes_bible a déjà postés — pas besoin de fichier local.
    """
    replied = set()
    posts = get_recent_posts(user_id)
    for post in posts:
        replies = get_replies(post["id"])
        for r in replies:
            if r.get("username") == "estherbes_bible":
                # Chercher le parent de cette réponse pour marquer comme traité
                replied.add(r.get("id"))
    return replied

# ─── Générer une réponse personnalisée avec Groq ─────────────────────────────
def generate_reply(comment_text: str, username: str) -> str:
    prompt = f"""You are a warm Christian community manager for @estherbes_bible on Threads.

@{username} commented: "{comment_text}"

Write ONE short reply (max 180 characters) that:
- Directly responds to what they said (not generic)
- Feels human and warm
- Uses at most 1 emoji
- Does NOT start with "Thank you for sharing"
- Does NOT sound like a bot or template

Reply ONLY with the text, nothing else."""

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
                "max_tokens": 80,
                "temperature": 1.0,
            },
            timeout=30,
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip()
        # Vérifier que la réponse n'est pas vide
        if len(reply) > 5:
            print(f"✅ Groq reply: \"{reply}\"")
            return reply
        raise ValueError("Reply too short")
    except Exception as e:
        print(f"⚠️ Groq failed ({e}), using varied fallback.")
        return random.choice(FALLBACK_REPLIES)

# ─── Poster une réponse ──────────────────────────────────────────────────────
def post_reply(user_id: str, reply_to_id: str, text: str) -> bool:
    base_url = f"https://graph.threads.net/v1.0/{user_id}"

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
        print(f"❌ Container error: {create_resp.status_code} — {create_resp.text}")
        return False

    container_id = create_resp.json()["id"]
    print("⏳ Waiting 30s (Meta requirement)...")
    time.sleep(30)

    publish_resp = requests.post(
        f"{base_url}/threads_publish",
        data={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not publish_resp.ok:
        print(f"❌ Publish error: {publish_resp.status_code} — {publish_resp.text}")
        return False

    print(f"✅ Reply posted! ID: {publish_resp.json()['id']}")
    return True

# ─── Vérifier si un post a déjà une réponse du bot ───────────────────────────
def bot_already_replied(post_id: str, bot_username: str = "estherbes_bible") -> set:
    """Retourne les IDs des commentaires auxquels le bot a déjà répondu."""
    already_replied_to = set()
    replies = get_replies(post_id)

    # Chercher les réponses du bot et identifier leur parent
    for r in replies:
        if r.get("username") == bot_username:
            # On marque l'ID de CETTE réponse du bot comme "déjà traité"
            already_replied_to.add(r.get("id"))

    return already_replied_to

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN missing.")
        exit(1)

    user_id = get_user_id()
    posts = get_recent_posts(user_id)
    total_replied = 0

    for post in posts:
        post_id = post["id"]
        replies = get_replies(post_id)

        if not replies:
            continue

        # Séparer les commentaires du bot et des autres utilisateurs
        bot_reply_ids = set()
        user_comments = []

        for r in replies:
            if r.get("username") == "estherbes_bible":
                bot_reply_ids.add(r.get("id"))
            else:
                user_comments.append(r)

        print(f"\n📌 Post {post_id}: {len(user_comments)} user comments, {len(bot_reply_ids)} bot replies")

        for comment in user_comments:
            comment_id = comment["id"]
            username = comment.get("username", "friend")
            comment_text = comment.get("text", "").strip()

            if not comment_text:
                continue

            # Vérifier si le bot a déjà répondu à CE commentaire
            # On vérifie si parmi les réponses du bot, une a été postée APRÈS ce commentaire
            # Approche simple : si le nombre de réponses bot >= nombre de commentaires user, skip
            if len(bot_reply_ids) >= len(user_comments):
                print(f"⏭️ Skipping @{username} — bot already replied to this post")
                continue

            print(f"\n💬 @{username}: \"{comment_text[:80]}\"")
            reply_text = generate_reply(comment_text, username)
            print(f"🤖 Bot reply: \"{reply_text}\"")

            success = post_reply(user_id, comment_id, reply_text)
            if success:
                bot_reply_ids.add(comment_id)
                total_replied += 1

            time.sleep(5)

    print(f"\n✅ Done — replied to {total_replied} new comments")
