import firebase_admin
from firebase_admin import credentials, firestore
import datetime


# Initialize Firestore
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()


def write_to_firestore(collection, data, num_days=0):
    """Writes data to Firestore.

    Args:
        collection (str): The name of the Firestore collection.
        component (str): A string identifier for the data component.
        data (dict): A dictionary containing the data to be written.

    Returns:
        str: The ID of the document written to Firestore.
    """
    try:
        # Generate a key based on publicataion date
        doc_date = datetime.date.today() - datetime.timedelta(days=num_days)
        doc_date_str = doc_date.strftime("%m_%d_%Y")
        doc_ref = db.collection(collection).document(f"{doc_date_str}")
        doc_ref.set(data)
        print(f"Data written to Firestore with ID: {doc_ref.id}")
    except Exception as e:
        print(f"Error writing data to Firestore: {e}")

    return doc_ref.id

def get_components_from_firestore(collection, document_id):
    """Retrieves a document from a Firestore collection.

    Args:
        collection (str): The name of the Firestore collection.
        document_id (str): The ID of the document to retrieve.

    Returns:
        dict: The document data as a dictionary, or None if the document is not found.
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

def get_documents_for_past_week(collection):
    """Retrieves documents for the past seven days from a Firestore collection.

    Args:
        collection (str): The name of the Firestore collection.

    Returns:
        list: A list of dictionaries, where each dictionary represents a document. Returns an empty list if no documents are found or an error occurs.
    """

    try:
        today = datetime.date.today()
        week_docs = []
        for i in range(7):  # Iterate through the past 7 days
            past_date = today - datetime.timedelta(days=i)
            date_str = past_date.strftime("%m_%d_%Y")  # Format the date string
            doc_ref = db.collection(collection).document(date_str)
            doc = doc_ref.get()
            if doc.exists:
                week_docs.append(doc.to_dict())
        return week_docs
    except Exception as e:
        print(f"Error retrieving past week's documents: {e}")
        return []

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
