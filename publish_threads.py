import os
import requests
import random
import time
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"

# ─── Post types avec leurs prompts ───────────────────────────────────────────
POST_TYPES = {
    "verse_reflection": {
        "prompt": """You are an inspiring Christian content creator for Threads targeting an English-speaking audience.
Generate a short post (max 480 characters) that includes:
- A Bible verse with its full reference (KJV or NIV)
- A short sincere personal reflection (1-2 sentences)
- An engaging question for the community
- 2-3 hashtags: #BibleStudy #Faith and one other
Reply ONLY with the post text, no introduction, no quotes.""",
        "fallbacks": [
            "📖 Psalm 23:1 — \"The Lord is my shepherd; I shall not want.\"\n\nEven in our most uncertain moments, He provides. We just need to trust.\n\nWhat promise are you holding onto from God today?\n\n#BibleStudy #Faith #Hope",
            "✨ John 3:16 — \"For God so loved the world that He gave His only Son.\"\n\nThis love is unconditional, unearned, and never-ending.\n\nHow has God's love shown up in your life this week?\n\n#Bible #Faith #Grace",
            "🌟 Philippians 4:13 — \"I can do all things through Christ who strengthens me.\"\n\nNot in our own power — but in His.\n\nWhat challenge are you facing with His strength today?\n\n#BibleStudy #Faith #Strength",
        ]
    },
    "engagement_question": {
        "prompt": """You are a Christian community builder on Threads targeting an English-speaking audience.
Generate a short engaging question post (max 400 characters) that:
- Asks a genuine, thought-provoking faith question
- Relates to everyday Christian life or Bible study
- Invites people to share their experience in the comments
- Ends with 2 hashtags: #Faith and one other
No introduction, no quotes, just the post.""",
        "fallbacks": [
            "What Bible verse has carried you through your hardest season? 👇\n\nDrop it in the comments — someone here needs it today.\n\n#Faith #BibleStudy",
            "Be honest — how often do you actually open your Bible each week? 📖\n\nNo judgment here. Just curious where you're at on your faith journey.\n\n#Faith #ChristianLife",
            "Which book of the Bible do you keep coming back to, and why? 🤔\n\nMine changes every season of life.\n\n#BibleStudy #Faith",
        ]
    },
    "study_tip": {
        "prompt": """You are a Bible study coach on Threads targeting English-speaking beginners.
Generate a practical Bible study tip post (max 480 characters) that:
- Gives ONE specific, actionable tip for studying the Bible
- Is beginner-friendly and encouraging
- Connects to the 30-Day Bible Study Starter Kit concept
- Ends with 2-3 hashtags: #BibleStudy and others
Reply ONLY with the post text.""",
        "fallbacks": [
            "💡 Bible study tip: Start with just 5 minutes a day.\n\nPick ONE verse. Read it slowly. Ask yourself: What does this tell me about God? What does it tell me about myself?\n\nConsistency beats marathon sessions every time.\n\n#BibleStudy #Faith #Devotional",
            "💡 Try reading a Psalm out loud today.\n\nThere's something powerful about hearing the words — not just seeing them. Psalm 91 is a great place to start.\n\nWhich Psalm speaks to you most?\n\n#BibleStudy #Faith #Psalms",
            "💡 Context is everything in Bible study.\n\nBefore diving into a verse, read the whole chapter. The meaning changes completely when you see the full picture.\n\nWhich verse hit differently once you understood the context?\n\n#BibleStudy #Faith",
        ]
    },
    "testimony_story": {
        "prompt": """You are a Christian storyteller on Threads targeting an English-speaking audience.
Generate a short testimony-style or faith story post (max 480 characters) that:
- Shares a relatable faith moment or struggle (written as universal experience, not personal)
- Shows how faith or scripture provided clarity or comfort
- Ends with an encouraging line and 2 hashtags
Make it warm, authentic, and human. Reply ONLY with the post text.""",
        "fallbacks": [
            "There was a season where prayer felt like talking to an empty room. 🙏\n\nNo answers. Just silence.\n\nThen I read Psalm 34:18 — \"He is close to the brokenhearted.\"\n\nHe wasn't absent. He was right there. In the silence.\n\n#Faith #Hope",
            "Ever opened your Bible at random and landed on exactly what you needed? 📖\n\nThat's happened too many times to call coincidence.\n\nGod speaks in ways we don't always expect.\n\nShare yours below 👇\n\n#Faith #BibleStudy",
            "Some days faith looks like reading one verse and crying. 😢\n\nAnd that's okay.\n\nGod meets us exactly where we are — not where we think we should be.\n\n#Faith #Grace #ChristianLife",
        ]
    },
    "product_cta": {
        "prompt": """You are a Christian content creator on Threads promoting the \"30-Day Bible Study Starter Kit\" — a beginner-friendly guide to building a daily Bible study habit.
Generate a soft, value-first promotional post (max 480 characters) that:
- Leads with a genuine encouragement or pain point (not a sales pitch)
- Naturally mentions the 30-Day Bible Study Starter Kit as a solution
- Feels helpful, not salesy
- Ends with a gentle CTA and 2 hashtags: #BibleStudy and one other
Reply ONLY with the post text.""",
        "fallbacks": [
            "If you've ever said \"I want to read my Bible more\" but don't know where to start — you're not alone. 📖\n\nThe 30-Day Bible Study Starter Kit was made exactly for that moment.\n\nSimple. Structured. Beginner-friendly.\n\nStart your 30 days today. 👇\n\n#BibleStudy #Faith",
            "Building a daily Bible habit doesn't have to be complicated. ✨\n\nThe 30-Day Bible Study Starter Kit gives you a simple plan — one chapter, one reflection, one prayer prompt per day.\n\n30 days. Life-changing habit.\n\n#BibleStudy #ChristianLife",
        ]
    }
}

# ─── Rotation intelligente selon l'heure ─────────────────────────────────────
def get_post_type_for_hour() -> str:
    hour = datetime.utcnow().hour
    schedule = {
        0:  "verse_reflection",
        3:  "verse_reflection",
        6:  "study_tip",
        9:  "engagement_question",
        12: "verse_reflection",
        15: "testimony_story",
        18: "verse_reflection",
        21: "product_cta",
    }
    # Trouver le créneau le plus proche
    closest = min(schedule.keys(), key=lambda h: abs(h - hour))
    return schedule[closest]

# ─── Génération du contenu ───────────────────────────────────────────────────
def generate_content(post_type: str) -> str:
    config = POST_TYPES[post_type]

    if not GROQ_API_KEY:
        print(f"⚠️ GROQ_API_KEY missing, using static fallback for [{post_type}].")
        return random.choice(config["fallbacks"])

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": config["prompt"]}],
                "max_tokens": 300,
                "temperature": 0.85,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        print(f"✅ Groq content generated ({len(content)} chars) — type: [{post_type}]")
        return content
    except Exception as e:
        print(f"⚠️ Groq failed ({e}), using static fallback for [{post_type}].")
        return random.choice(config["fallbacks"])

# ─── Récupération User ID ────────────────────────────────────────────────────
def get_threads_user_id() -> str:
    resp = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    user_id = data["id"]
    print(f"✅ User ID: {user_id} (@{data.get('username', '?')})")
    return user_id

# ─── Publication ─────────────────────────────────────────────────────────────
def publish_to_threads(user_id: str, text: str) -> bool:
    base_url = f"https://graph.threads.net/v1.0/{user_id}"

    create_resp = requests.post(
        f"{base_url}/threads",
        data={"media_type": "TEXT", "text": text, "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    if not create_resp.ok:
        print(f"❌ Container error: {create_resp.status_code} — {create_resp.text}")
        create_resp.raise_for_status()

    container_id = create_resp.json()["id"]
    print(f"✅ Container created: {container_id}")

    print("⏳ Waiting 30s (required by Meta)...")
    time.sleep(30)

    publish_resp = requests.post(
        f"{base_url}/threads_publish",
        data={"creation_id": container_id, "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    if not publish_resp.ok:
        print(f"❌ Publish error: {publish_resp.status_code} — {publish_resp.text}")
        publish_resp.raise_for_status()

    post_id = publish_resp.json()["id"]
    print(f"✅ Published! Post ID: {post_id}")
    return True

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN missing.")
        exit(1)

    print("🔍 Getting user ID...")
    user_id = get_threads_user_id()

    post_type = get_post_type_for_hour()
    print(f"🎯 Post type for this hour: [{post_type}]")

    print("🚀 Generating content...")
    content = generate_content(post_type)
    print(f"\n📝 Post:\n{content}\n")

    print("📤 Publishing to Threads...")
    publish_to_threads(user_id, content)
