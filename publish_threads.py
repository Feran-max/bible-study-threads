import os
import requests
import random
import time

# ─── Configuration ───────────────────────────────────────────────────────────
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"

FALLBACK_POSTS = [
    "📖 Psalm 23:1 — The Lord is my shepherd; I shall not want.\n\nWhat promise are you holding onto from God today?\n\n#BibleStudy #Faith #Hope",
    "✨ John 3:16 — For God so loved the world that He gave His only Son.\n\nHow do you experience this love in your daily life?\n\n#Bible #Love #Grace",
    "🙏 Proverbs 3:5 — Trust in the Lord with all your heart.\n\nWhat area of your life do you need to surrender to Him today?\n\n#Wisdom #Trust #Bible",
    "🌟 Philippians 4:13 — I can do all things through Christ who strengthens me.\n\nWhat challenge are you facing with His strength today?\n\n#BibleStudy #Strength #Faith",
    "💛 Jeremiah 29:11 — For I know the plans I have for you, declares the Lord.\n\nDo you trust God's plan for your life right now?\n\n#Hope #Bible #Blessing",
]

def get_threads_user_id() -> str:
    resp = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    user_id = data["id"]
    print(f"✅ User ID retrieved: {user_id} (@{data.get('username', '?')})")
    return user_id

def generate_content_with_groq() -> str:
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY missing, using static content.")
        return random.choice(FALLBACK_POSTS)

    prompt = """You are an inspiring Christian content creator for Threads targeting an English-speaking audience.
Generate a short post (max 480 characters) that includes:
- A Bible verse with its full reference (KJV or NIV translation)
- A short, sincere personal reflection
- An engaging question for the community
- 2-3 hashtags: #BibleStudy #Faith and one other relevant one
Reply ONLY with the post text, no introduction, no quotes."""

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
                "max_tokens": 300,
                "temperature": 0.85,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        print(f"✅ Groq content generated ({len(content)} characters)")
        return content
    except Exception as e:
        print(f"⚠️ Groq failed ({e}), using static fallback.")
        return random.choice(FALLBACK_POSTS)

def publish_to_threads(user_id: str, text: str) -> bool:
    base_url = f"https://graph.threads.net/v1.0/{user_id}"

    create_resp = requests.post(
        f"{base_url}/threads",
        data={
            "media_type": "TEXT",
            "text": text,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not create_resp.ok:
        print(f"❌ Container error: {create_resp.status_code} — {create_resp.text}")
        create_resp.raise_for_status()

    container_id = create_resp.json()["id"]
    print(f"✅ Container created: {container_id}")

    print("⏳ Waiting 30 seconds (required by Meta)...")
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
        publish_resp.raise_for_status()

    post_id = publish_resp.json()["id"]
    print(f"✅ Post published on Threads! ID: {post_id}")
    return True

if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN missing.")
        exit(1)

    print("🔍 Retrieving User ID...")
    user_id = get_threads_user_id()

    print("🚀 Generating content...")
    content = generate_content_with_groq()
    print(f"\n📝 Post:\n{content}\n")

    print("📤 Publishing to Threads...")
    publish_to_threads(user_id, content)
