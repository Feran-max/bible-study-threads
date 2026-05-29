import requests
import time
import random
import os

# --- Configuration Générale ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "37008471638752388")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def generate_content_with_groq():
    """Génère du contenu biblique dynamique via Groq API."""
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY non trouvée. Utilisation du contenu statique.")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # On choisit aléatoirement un type de prompt
    prompts = [
        "Give me a powerful Bible verse with a 2-sentence reflection for someone building their faith. Format: 'Verse | Reflection'.",
        "Ask a thought-provoking question about daily Christian life to engage a Bible study community.",
        "Give me a short inspiring message about Bible study and mention the '30-Day Bible Study Starter Kit'."
    ]
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": random.choice(prompts)}],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return content + "\n\n#BibleStudy #Faith #ChristianLife"
    except Exception as e:
        print(f"❌ Erreur Groq : {e}")
        return None

# --- Contenu de Secours (Statique) ---
POST_TYPES = {
    "verse": {
        "template": "📖 Verse of the Day: {verse} \n\n{reflection}\n\n#BibleStudy #Faith",
        "data": [
            {"verse": "Psalm 23:1", "reflection": "The LORD is my shepherd; I shall not want."},
            {"verse": "Jeremiah 29:11", "reflection": "God has a wonderful plan for us. Let's trust in His promises."}
        ]
    }
}

def get_content():
    # On essaie d'abord Groq
    content = generate_content_with_groq()
    if content:
        return content
    
    # Sinon, on utilise le statique
    vt = POST_TYPES["verse"]
    item = random.choice(vt["data"])
    return vt["template"].format(**item)

def publish_to_threads(token, user_id, text):
    if not token or not user_id:
        print("❌ Token ou ID manquant.")
        return False

    base_url = "https://graph.threads.net/v1.0"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Créer le conteneur
    print(f"🔄 Création du conteneur...")
    res = requests.post(f"{base_url}/{user_id}/threads", headers=headers, json={"text": text})
    if res.status_code != 200:
        print(f"❌ Erreur conteneur : {res.json()}")
        return False
    
    container_id = res.json().get("id")
    time.sleep(2)

    # 2. Publier
    print(f"🚀 Publication...")
    res = requests.post(f"{base_url}/{user_id}/threads_publish", headers=headers, json={"creation_id": container_id})
    if res.status_code == 200:
        print(f"✅ Succès ! ID : {res.json().get('id')}")
        return True
    else:
        print(f"❌ Erreur publication : {res.json()}")
        return False

if __name__ == "__main__":
    message = get_content()
    publish_to_threads(ACCESS_TOKEN, THREADS_USER_ID, message)
