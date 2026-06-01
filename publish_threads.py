import os, requests, random, time
from datetime import datetime

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
GROQ_MODEL           = "llama3-8b-8192"
BOT_USERNAME         = "estherbes_bible"

# ─── Hashtags dynamiques par niche ───────────────────────────────────────────
HASHTAG_POOLS = {
    "verse":     ["#BibleStudy", "#Faith", "#DailyVerse", "#Scripture", "#ChristianLife", "#WordOfGod", "#Bible", "#Devotional"],
    "question":  ["#Faith", "#ChristianCommunity", "#BibleStudy", "#GodIsGood", "#ChristianLife", "#Blessed"],
    "tip":       ["#BibleStudy", "#Devotional", "#ChristianGrowth", "#Faith", "#BibleTip", "#Scripture"],
    "story":     ["#Faith", "#Testimony", "#ChristianLife", "#Hope", "#Grace", "#GodIsGood"],
    "cta":       ["#BibleStudy", "#Faith", "#ChristianLife", "#Devotional", "#BibleChallenge"],
}

def pick_hashtags(pool_key: str, n: int = 3) -> str:
    pool = HASHTAG_POOLS.get(pool_key, HASHTAG_POOLS["verse"])
    return " ".join(random.sample(pool, min(n, len(pool))))

POST_TYPES = {
    "verse_reflection": {
        "pool": "verse",
        "prompt": lambda tags: f"""You are an inspiring Christian content creator for Threads targeting an English-speaking audience.
Generate a short post (max 460 characters, NOT counting hashtags) that includes:
- A Bible verse with its full reference (KJV or NIV)
- A short sincere personal reflection (1-2 sentences)
- An engaging question for the community
End with exactly these hashtags on a new line: {tags}
Reply ONLY with the post text.""",
        "fallbacks": [
            "📖 Psalm 23:1 — \"The Lord is my shepherd; I shall not want.\"\n\nEven in uncertainty, He provides. We just need to trust.\n\nWhat promise are you holding onto from God today?\n\n",
            "✨ John 3:16 — \"For God so loved the world that He gave His only Son.\"\n\nThis love is unconditional and never-ending.\n\nHow has God's love shown up in your life this week?\n\n",
            "🌟 Philippians 4:13 — \"I can do all things through Christ who strengthens me.\"\n\nNot in our own power — but in His.\n\nWhat challenge are you facing with His strength today?\n\n",
        ]
    },
    "engagement_question": {
        "pool": "question",
        "prompt": lambda tags: f"""You are a Christian community builder on Threads targeting an English-speaking audience.
Generate a short engaging question post (max 380 characters) that invites people to share in comments.
End with exactly these hashtags on a new line: {tags}
Reply ONLY with the post text.""",
        "fallbacks": [
            "What Bible verse has carried you through your hardest season? 👇\n\nDrop it in the comments — someone here needs it today.\n\n",
            "Be honest — how often do you actually open your Bible each week? 📖\n\nNo judgment. Just curious where you're at.\n\n",
            "Which book of the Bible do you keep coming back to, and why? 🤔\n\n",
        ]
    },
    "study_tip": {
        "pool": "tip",
        "prompt": lambda tags: f"""You are a Bible study coach on Threads for English-speaking beginners.
Generate a practical, actionable Bible study tip post (max 460 characters).
End with exactly these hashtags on a new line: {tags}
Reply ONLY with the post text.""",
        "fallbacks": [
            "💡 Start with just 5 minutes a day.\n\nPick ONE verse. Read it slowly. Ask: What does this say about God? What does it say about me?\n\nConsistency beats marathon sessions every time.\n\n",
            "💡 Try reading a Psalm out loud today.\n\nThere's something powerful about hearing the words. Psalm 91 is a great place to start.\n\n",
        ]
    },
    "testimony_story": {
        "pool": "story",
        "prompt": lambda tags: f"""You are a Christian storyteller on Threads for an English-speaking audience.
Generate a short relatable faith story/testimony post (max 460 characters). Make it warm and human.
End with exactly these hashtags on a new line: {tags}
Reply ONLY with the post text.""",
        "fallbacks": [
            "There was a season where prayer felt like talking to an empty room. 🙏\n\nThen I read Psalm 34:18 — \"He is close to the brokenhearted.\"\n\nHe wasn't absent. He was right there in the silence.\n\n",
            "Ever opened your Bible at random and landed on exactly what you needed? 📖\n\nToo many times to call coincidence. God speaks in ways we don't expect.\n\n",
        ]
    },
    "product_cta": {
        "pool": "cta",
        "prompt": lambda tags: f"""You are a Christian content creator promoting the \"30-Day Bible Study Starter Kit\" on Threads.
Write a soft, value-first post (max 460 characters) that feels helpful not salesy. Lead with encouragement.
End with exactly these hashtags on a new line: {tags}
Reply ONLY with the post text.""",
        "fallbacks": [
            "If you've ever said \"I want to read my Bible more\" but don't know where to start — you're not alone. 📖\n\nThe 30-Day Bible Study Starter Kit was made for that moment. Simple. Structured. Beginner-friendly.\n\n",
        ]
    },
}

SCHEDULE = {0: "verse_reflection", 3: "verse_reflection", 6: "study_tip",
            9: "engagement_question", 12: "verse_reflection",
            15: "testimony_story", 18: "verse_reflection", 21: "product_cta"}

def get_post_type() -> str:
    hour = datetime.utcnow().hour
    return SCHEDULE[min(SCHEDULE.keys(), key=lambda h: abs(h - hour))]

def generate_content(post_type: str) -> str:
    config  = POST_TYPES[post_type]
    tags    = pick_hashtags(config["pool"])
    prompt  = config["prompt"](tags)

    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 300, "temperature": 0.85},
                timeout=30,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            if len(content) > 10:
                print(f"✅ Groq content ({len(content)} chars) — type: [{post_type}]")
                return content
        except Exception as e:
            print(f"⚠️ Groq failed ({e}), using fallback.")

    fallback = random.choice(config["fallbacks"]) + tags
    print(f"📝 Using fallback — type: [{post_type}]")
    return fallback

def get_user_id() -> str:
    r = requests.get("https://graph.threads.net/v1.0/me",
                     params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN}, timeout=15)
    r.raise_for_status()
    d = r.json()
    print(f"✅ @{d['username']} ({d['id']})")
    return d["id"]

def publish(user_id: str, text: str):
    base = f"https://graph.threads.net/v1.0/{user_id}"
    r = requests.post(f"{base}/threads",
                      data={"media_type": "TEXT", "text": text, "access_token": THREADS_ACCESS_TOKEN}, timeout=30)
    r.raise_for_status()
    cid = r.json()["id"]
    print(f"✅ Container: {cid} — waiting 30s...")
    time.sleep(30)
    r2 = requests.post(f"{base}/threads_publish",
                       data={"creation_id": cid, "access_token": THREADS_ACCESS_TOKEN}, timeout=30)
    r2.raise_for_status()
    print(f"✅ Published! ID: {r2.json()['id']}")

if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN missing."); exit(1)
    user_id   = get_user_id()
    post_type = get_post_type()
    print(f"🎯 Post type: [{post_type}]")
    content   = generate_content(post_type)
    print(f"\n📝 Post:\n{content}\n")
    publish(user_id, content)
