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

def write_to_firestore(collection, component,type='none'):
    """Writes newsletter data to Firestore.

    Args:
        newsletter_data (dict): A dictionary containing newsletter data.  Must include a 'user_email' key.
    """
    try:
        # Generate a key based on today's date
        today = datetime.date.today().strftime("%m-%d-%Y")
        if type != 'none':
            doc_ref = db.collection(collection).document()
            doc_ref.set({
                type: component,
                'timestamp': datetime.datetime.now()
                })
        else:
            doc_ref = db.collection(collection).document()
            doc_ref.set(component)
        print(f"Newsletter written to Firestore with ID: {doc_ref.id}")
    except Exception as e:
        print(f"Error writing newsletter to Firestore: {e}")

    return doc_ref.id

def get_newsletter_from_firestore(collection, document_id):
    """Retrieves newsletter data from Firestore.

    Args:
        user_email (str): The email address associated with the newsletter.

    Returns:
        dict: The newsletter data, or None if not found.
    """
    try:
        doc_ref = db.collection(collection).document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print(f"No newsletter found for {document_id}")
            return None
    except Exception as e:
        print(f"Error retrieving newsletter from Firestore: {e}")
        return None

def search_firestore_by_field(collection_name, field_name, field_value):
    """Searches Firestore for documents matching a specific field value.

    Args:
        collection_name (str): The name of the Firestore collection.
        field_name (str): The name of the field to search.
        field_value (str): The value to match in the field.

    Returns:
        list: A list of dictionaries representing matching documents, or an empty list if none are found.
    """
    try:
        docs = db.collection(collection_name).where(field_name, '==', field_value).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Error searching Firestore: {e}")
        return []
