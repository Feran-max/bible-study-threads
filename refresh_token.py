"""
refresh_token.py — Renouvelle automatiquement le token Threads (long-lived, 60 jours)
et met à jour le secret GitHub THREADS_ACCESS_TOKEN.

Nécessite dans les secrets GitHub :
  - THREADS_ACCESS_TOKEN  : token actuel
  - META_APP_ID           : App ID de ton app Meta (Bible_Threads_Auto)
  - META_APP_SECRET       : App Secret de ton app Meta
  - GITHUB_TOKEN          : token GitHub (fourni automatiquement par Actions)
"""

import os
import sys
import requests
import base64
import json

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "Feran-max/bible-study-threads"

def exchange_for_long_lived_token(short_token: str) -> str:
    """Échange un token court/existant contre un token longue durée (60 jours)."""
    resp = requests.get(
        "https://graph.facebook.com/v19.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"❌ Token exchange failed: {resp.status_code} — {resp.text}")
        sys.exit(1)
    data = resp.json()
    new_token = data.get("access_token")
    expires_in = data.get("expires_in", "unknown")
    print(f"✅ New long-lived token obtained (expires in {expires_in}s ≈ {int(expires_in)//86400} days)")
    return new_token

def update_github_secret(secret_name: str, secret_value: str):
    """Met à jour un secret GitHub via l'API."""
    # Récupérer la clé publique du repo
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    key_resp = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key",
        headers=headers, timeout=15,
    )
    key_resp.raise_for_status()
    key_data = key_resp.json()
    key_id = key_data["key_id"]
    public_key_b64 = key_data["key"]

    # Chiffrer avec PyNaCl
    from nacl import public, encoding
    public_key_bytes = base64.b64decode(public_key_b64)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

    # Mettre à jour le secret
    put_resp = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted_b64, "key_id": key_id},
        timeout=15,
    )
    if put_resp.status_code in (201, 204):
        print(f"✅ Secret '{secret_name}' updated in GitHub!")
    else:
        print(f"❌ Failed to update secret: {put_resp.status_code} — {put_resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    for var, name in [(THREADS_ACCESS_TOKEN, "THREADS_ACCESS_TOKEN"),
                      (META_APP_ID, "META_APP_ID"),
                      (META_APP_SECRET, "META_APP_SECRET"),
                      (GITHUB_TOKEN, "GITHUB_TOKEN")]:
        if not var:
            print(f"❌ {name} missing.")
            sys.exit(1)

    print("🔄 Refreshing Threads token...")
    new_token = exchange_for_long_lived_token(THREADS_ACCESS_TOKEN)

    print("🔐 Updating GitHub secret...")
    update_github_secret("THREADS_ACCESS_TOKEN", new_token)

    print("✅ Token refreshed and saved successfully!")
