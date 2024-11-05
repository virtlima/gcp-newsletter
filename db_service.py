import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

# Initialize Firestore
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()

def write_to_firestore(type, newsletter):
    """Writes newsletter data to Firestore.

    Args:
        newsletter_data (dict): A dictionary containing newsletter data.  Must include a 'user_email' key.
    """
    try:
        # Generate a key based on today's date
        today = datetime.date.today().strftime("%Y-%m-%d")
        doc_ref = db.collection('newsletters').document(f"{type}-{today}")
        doc_ref.set({
            'newsletter': newsletter
        })
        print(f"Newsletter written to Firestore with ID: {doc_ref.id}")
    except Exception as e:
        print(f"Error writing newsletter to Firestore: {e}")


def get_newsletter_from_firestore(document_id):
    """Retrieves newsletter data from Firestore.

    Args:
        user_email (str): The email address associated with the newsletter.

    Returns:
        dict: The newsletter data, or None if not found.
    """
    try:
        doc_ref = db.collection('newsletters').document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"No newsletter found for {document_id}")
            return None
    except Exception as e:
        print(f"Error retrieving newsletter from Firestore: {e}")
        return None
