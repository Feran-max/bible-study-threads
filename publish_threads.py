import os
import requests
import random
import time

# ─── Configuration ───────────────────────────────────────────────────────────
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"

FALLBACK_POSTS = [
    "📖 Psaumes 23:1 — L'Éternel est mon berger : je ne manquerai de rien.\n\nQuelle promesse tiens-tu de Dieu aujourd'hui ?\n\n#BibleStudy #Foi #Espoir",
    "✨ Jean 3:16 — Car Dieu a tant aimé le monde qu'il a donné son Fils unique.\n\nComment ressens-tu cet amour dans ta vie ?\n\n#Bible #Amour #Grace",
    "🙏 Proverbes 3:5 — Confie-toi en l'Éternel de tout ton cœur.\n\nDans quel domaine dois-tu lui faire confiance aujourd'hui ?\n\n#Sagesse #Confiance #Bible",
    "🌟 Philippiens 4:13 — Je puis tout par celui qui me fortifie.\n\nQuel défi affrontes-tu avec cette force aujourd'hui ?\n\n#BibleStudy #Force #Foi",
    "💛 Jérémie 29:11 — Je connais les projets que j'ai formés sur vous.\n\nFais-tu confiance au plan de Dieu pour ta vie ?\n\n#Espoir #Bible #Bénédiction",
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
    print(f"✅ User ID récupéré : {user_id} (@{data.get('username', '?')})")
    return user_id

def generate_content_with_groq() -> str:
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY manquante, contenu statique utilisé.")
        return random.choice(FALLBACK_POSTS)

    prompt = """Tu es un créateur de contenu chrétien inspirant pour Threads.
Génère un post court (max 480 caractères) qui inclut :
- Un verset biblique avec sa référence complète
- Une réflexion personnelle courte et sincère
- Une question pour engager la communauté
- 2-3 hashtags : #BibleStudy #Foi et un autre pertinent
Réponds uniquement avec le texte du post, sans introduction ni guillemets."""

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
        print(f"✅ Contenu Groq généré ({len(content)} caractères)")
        return content
    except Exception as e:
        print(f"⚠️ Groq échoué ({e}), fallback statique.")
        return random.choice(FALLBACK_POSTS)

def publish_to_threads(user_id: str, text: str) -> bool:
    base_url = f"https://graph.threads.net/v1.0/{user_id}"

    # Étape 1 : Créer le container
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
        print(f"❌ Erreur création container : {create_resp.status_code} — {create_resp.text}")
        create_resp.raise_for_status()

    container_id = create_resp.json()["id"]
    print(f"✅ Container créé : {container_id}")

    # Attente obligatoire — Meta exige que le container soit prêt
    print("⏳ Attente 30 secondes (délai requis par Meta)...")
    time.sleep(30)

    # Étape 2 : Publier
    publish_resp = requests.post(
        f"{base_url}/threads_publish",
        data={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not publish_resp.ok:
        print(f"❌ Erreur publication : {publish_resp.status_code} — {publish_resp.text}")
        publish_resp.raise_for_status()

    post_id = publish_resp.json()["id"]
    print(f"✅ Post publié sur Threads ! ID : {post_id}")
    return True

if __name__ == "__main__":
    if not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_ACCESS_TOKEN manquant.")
        exit(1)

    print("🔍 Récupération du User ID...")
    user_id = get_threads_user_id()

    print("🚀 Génération du contenu...")
    content = generate_content_with_groq()
    print(f"\n📝 Post :\n{content}\n")

    print("📤 Publication sur Threads...")
    publish_to_threads(user_id, content)
