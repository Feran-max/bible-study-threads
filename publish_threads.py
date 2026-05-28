import requests
import time
import random
import os # Pour potentiellement lire des variables d'environnement plus tard

# --- Configuration Générale ---
# Pour l'instant, on garde le token ici pour le développement local.
# Dans Google Cloud, on le chargera depuis le Secret Manager.
ACCESS_TOKEN = "THAAcYZAMDTUAJBYllFWnBvVDhjWWJLSndjc2FjZA0dqaWN5b01UZA0J1TlVXeUlRWXV6QzdTdGhUQWNmeVJJYUZA4MlZAOSzhfbVFCX09CVi1jSzNST0pQR1pVcDZABZAUR1Y2NDUDRDUGdubVBkYXFEUmFqZATFHWm5paU1mZAFhtNmlKejFqYk8wUnZAJMXczNWd2QnZA0elNwem90dzdSTXU0emxVSGtkZAWUZD"
# On aura besoin du THREADS_USER_ID, mais on va le récupérer via l'API pour être sûr
# THREADS_USER_ID = "32979938793" # On le récupérera dynamiquement

# --- Contenu pour les Posts ---

POST_TYPES = {
    "verse": {
        "template": """📖 Verse of the Day: {verse} 

{reflection}

#BibleStudy #Faith""",
        "data": [
            {
                "reference": "Psalm 23:1",
                "verse": "The LORD is my shepherd; I shall not want.",
                "reflection": "In times of doubt, let's remember that God watches over us and provides for our needs."
            },
            {
                "reference": "Jeremiah 29:11",
                "verse": "For I know the plans I have for you,” declares the LORD, “plans to prosper you and not to harm you, plans to give you hope and a future.",
                "reflection": "God has a wonderful plan for us. Let's trust in His promises."
            },
            {
                "reference": "John 3:16",
                "verse": "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.",
                "reflection": "God's love is the foundation of our salvation. Let's embrace this precious gift."
            }
        ]
    },
    "question": {
        "template": """❓ Question of the Day: {question}

What are your thoughts? Share your insights in the comments! 👇

#BibleStudy #Community""",
        "data": [
            {"question": "What is your favorite Bible verse for finding comfort?"},
            {"question": "How do you incorporate prayer into your daily life?"},
            {"question": "What Bible lesson has impacted you the most recently?"}
        ]
    },
    "promotion": {
        "template": """✨ Discover the '30-Day Bible Study Starter Kit'! Perfect for starting your Bible study journey. Get it here: https://estherbes.netlify.app 

#BibleStudyKit #ChristianLife #FaithJourney""",
        "data": [{}] # No specific data, just the template
    }
}

def get_content_to_publish():
    """Chooses a content type (verse, question, promotion) and generates the message."""
    
    # For now, we'll alternate between verse and question. Promotion added later.
    # We could add logic to publish a promotion once a week.
    post_type_choice = random.choice(["verse", "question"])
    
    content_config = POST_TYPES.get(post_type_choice)
    
    if not content_config:
        return None # Should not happen with our current list

    template = content_config["template"]
    data_list = content_config["data"]
    
    # Choose a random data item from the list
    selected_data = random.choice(data_list)
    
    # Fill the template with the data
    try:
        message = template.format(**selected_data)
        return message
    except KeyError as e:
        print(f"Error filling template: missing key {e}")
        return None

# --- API Functions (Adapted) ---

def get_threads_user_id(access_token):
    """Retrieves the Threads user ID using the access token."""
    url = f"https://graph.threads.net/v1.0/me?fields=id,username&access_token={access_token}"
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        if "id" in data:
            print(f"👤 Account found: @{data.get('username', 'N/A')} (ID: {data['id']})")
            return data["id"]
        else:
            print(f"❌ Could not retrieve Threads ID: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying for Threads ID: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error retrieving ID: {e}")
        return None

def publish_to_threads(access_token, user_id, text_message):
    """Publishes a text post to Threads."""
    if not text_message:
        print("❌ Empty message, nothing to publish.")
        return False

    print(f"🚀 Attempting to publish: '{text_message[:50]}...'") # Display the beginning of the message

    # 1. Create the container (Container)
    container_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    payload_creation = {
        'text': text_message,
        'access_token': access_token
    }
    
    try:
        response_creation = requests.post(container_url, data=payload_creation)
        response_creation.raise_for_status()
        resultat_creation = response_creation.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating container: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating container: {e}")
        return False

    if "id" not in resultat_creation:
        print(f"❌ Unexpected response when creating container: {resultat_creation}")
        return False
        
    container_id = resultat_creation["id"]
    print(f"📦 Container created successfully! ID: {container_id}")
    time.sleep(2) # Short pause for synchronization on Meta's side
    
    # 2. Publish the container (Publish)
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    payload_publication = {
        'creation_id': container_id,
        'access_token': access_token
    }
    
    try:
        response_publication = requests.post(publish_url, data=payload_publication)
        response_publication.raise_for_status()
        resultat_publication = response_publication.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during final publication: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during final publication: {e}")
        return False

    if "id" in resultat_publication:
        print(f"✅ Success! Post published. ID: {resultat_publication['id']}")
        return True
    else:
        print(f"❌ Unexpected response during final publication: {resultat_publication}")
        return False

# --- Main function for Cloud Functions ---
# This function will be called by Google Cloud Scheduler
def main_handler(event, context):
    """
    Main function triggered by Google Cloud Functions.
    It retrieves content and then publishes to Threads.
    """
    print("--- Starting Cloud Function execution ---")
    
    # Retrieve token and ID dynamically (best practice)
    # For now, using hardcoded ACCESS_TOKEN, to be changed to Secret Manager
    access_token = ACCESS_TOKEN 
    
    if not access_token:
        print("❌ Error: Access token not found.")
        return {"status": "error", "message": "Access token not found."}
        
    threads_user_id = get_threads_user_id(access_token)
    
    if not threads_user_id:
        print("❌ Could not obtain Threads user ID.")
        return {"status": "error", "message": "Could not retrieve Threads user ID."}
        
    # Get content to publish
    message_to_publish = get_content_to_publish()
    
    if not message_to_publish:
        print("❌ Could not generate content to publish.")
        return {"status": "error", "message": "Could not generate content to publish."}
        
    # Publish content
    success = publish_to_threads(access_token, threads_user_id, message_to_publish)
    
    if success:
        print("--- Execution completed successfully ---")
        return {"status": "success", "message": "Post published successfully."}
    else:
        print("--- Execution completed with errors ---")
        return {"status": "error", "message": "Failed to publish post."}

# --- Local execution for testing ---
if __name__ == "__main__":
    print("--- Starting local script test ---")
    
    # Simulate a call to the main handler
    test_message = get_content_to_publish()
    
    if test_message:
        print(f"Message to publish (local test): {test_message}")
        
        # Use the known ID for local testing to ensure it passes,
        # as accessing /me?fields=id,username might need different scopes.
        hardcoded_user_id_for_test = "37008471638752388" 
        
        if publish_to_threads(ACCESS_TOKEN, hardcoded_user_id_for_test, test_message):
            print("Local test completed SUCCESSFULLY")
        else:
            print("Local test completed with FAILURE")
    else:
        print("Error: Could not generate a message for local test.")
