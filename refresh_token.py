"""
refresh_token.py — Renouvelle le token Threads et met à jour le secret GitHub.
"""
import os, sys, requests, base64, json
from nacl import public

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
META_APP_ID          = os.getenv("META_APP_ID")
META_APP_SECRET      = os.getenv("META_APP_SECRET")
GITHUB_TOKEN         = os.getenv("GITHUB_TOKEN")
GITHUB_REPO          = "Feran-max/bible-study-threads"

def exchange_token(token: str) -> tuple[str, int]:
    resp = requests.get(
        "https://graph.facebook.com/v19.0/oauth/access_token",
        params={
            "grant_type":        "fb_exchange_token",
            "client_id":         META_APP_ID,
            "client_secret":     META_APP_SECRET,
            "fb_exchange_token": token,
        },
        timeout=20,
    )
    if not resp.ok:
        print(f"❌ Token exchange error: {resp.status_code} — {resp.text}")
        sys.exit(1)
    data = resp.json()
    if "error" in data:
        print(f"❌ Meta error: {data['error']}")
        sys.exit(1)
    new_token  = data["access_token"]
    expires_in = data.get("expires_in", 0)
    days       = expires_in // 86400
    print(f"✅ New token obtained — expires in ~{days} days")
    return new_token, expires_in

def update_github_secret(name: str, value: str):
    headers = {
        "Authorization":        f"Bearer {GITHUB_TOKEN}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Clé publique
    r = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key",
        headers=headers, timeout=15,
    )
    r.raise_for_status()
    key_id   = r.json()["key_id"]
    pub_key  = base64.b64decode(r.json()["key"])

    # Chiffrement
    box       = public.SealedBox(public.PublicKey(pub_key))
    encrypted = base64.b64encode(box.encrypt(value.encode())).decode()

    # Mise à jour
    put = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/{name}",
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": key_id},
        timeout=15,
    )
    if put.status_code in (201, 204):
        print(f"✅ Secret '{name}' updated in GitHub!")
    else:
        print(f"❌ Failed: {put.status_code} — {put.text}")
        sys.exit(1)

if __name__ == "__main__":
    missing = [n for n, v in [
        ("THREADS_ACCESS_TOKEN", THREADS_ACCESS_TOKEN),
        ("META_APP_ID",          META_APP_ID),
        ("META_APP_SECRET",      META_APP_SECRET),
        ("GITHUB_TOKEN",         GITHUB_TOKEN),
    ] if not v]
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
        sys.exit(1)

    new_token, _ = exchange_token(THREADS_ACCESS_TOKEN)
    update_github_secret("THREADS_ACCESS_TOKEN", new_token)
    print("🎉 Token refresh complete!")
