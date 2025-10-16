import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter
import datetime
import logging


logger = logging.getLogger(__name__)

# Idempotent initialization of Firestore
if not firebase_admin._apps:
    logger.info("Initializing Firebase App...")
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)
db = firestore.client()


def write_to_firestore(collection, data, num_days=1):
    """Writes data to Firestore.

    Args:
        collection (str): The name of the Firestore collection.
        component (str): A string identifier for the data component.
        data (dict): A dictionary containing the data to be written.

    Returns:
        str: The ID of the document written to Firestore.
    """
    doc_ref = None
    try:
        # Generate a key based on publicataion date
        doc_date = datetime.date.today() - datetime.timedelta(days=num_days)
        doc_date_str = doc_date.strftime("%m_%d_%Y")
        doc_ref = db.collection(collection).document(f"{doc_date_str}")
        doc_ref.set(data)
        logger.info(f"Data written to Firestore collection '{collection}' with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Error writing to Firestore collection '{collection}': {e}", exc_info=True)
        return None

def get_components_from_firestore(collection, document_id):
    """Retrieves a single document from a Firestore collection.

    Args:
        collection (str): The name of the Firestore collection.
        document_id (str): The ID of the document to retrieve.

    Returns:
        dict: The document's data as a dictionary, or None if not found or an error occurs.
    """
    try:
        doc_ref = db.collection(collection).document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            logger.warning(f"Document '{document_id}' not found in collection '{collection}'.")
            return None
    except Exception as e:
        logger.error(f"Error retrieving document '{document_id}' from Firestore: {e}", exc_info=True)
        return None


def get_documents_for_past_n_days(collection, n=7):
    """Retrieves documents for the past N days from a Firestore collection.

    Args:
        collection (str): The name of the Firestore collection.
        n (int): Number of days to go back in time. Defaults to 7 (a week).

    Returns:
        dict: A dictionary with document_id as key and document data as value.
            Returns empty dict for exeptions.
    """

    try:
        today = datetime.date.today()
        n_docs = {}
        # If n=1 (day), we want yesterday's articles. The loop should be range(1, 2) to get `days=1`.
        # If n=7 (week), we want the last 7 days. The loop should be range(1, 8).
        # The data processing job runs for the *previous* day, so we should start from `days=1`.
        start_day = 1
        end_day = n + 1

        for i in range(start_day, end_day):  # Iterate through the past N days, starting from yesterday
            past_date = today - datetime.timedelta(days=i)
            date_str = past_date.strftime("%m_%d_%Y")  # Format the date string
            doc_ref = db.collection(collection).document(date_str)
            doc = doc_ref.get()
            if doc.exists:
                n_docs[date_str] = doc.to_dict()
        return n_docs
    except Exception as e:
        logger.error(f"Error retrieving past {n} days' documents from '{collection}': {e}", exc_info=True)
        return {}

def search_firestore_by_field(collection_name, field_name, field_value):
    """Searches Firestore for documents matching a specific field value.

    Args:
        collection_name (str): The name of the Firestore collection.
        field_name (str): The name of the field to search.
        field_value (str): The value to match in the field.

    Returns:
        list: A list of dictionaries for matching documents. Returns None on error.
    """
    try:
        query = db.collection(collection_name).where(filter=FieldFilter(field_name, '==', field_value))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Error searching Firestore collection '{collection_name}': {e}", exc_info=True)
        return None

# Function to delete documents older than 30
def delete_documents_older_than_30_days(collection_name):
    try:
        thirty_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
        query = db.collection(collection_name).where(filter=FieldFilter('timestamp', '<', thirty_days_ago))
        docs = query.stream()
        for doc in docs:
            doc.reference.delete()
        logger.info(f"Successfully ran cleanup for documents older than 30 days in '{collection_name}'.")
    except Exception as e:
        logger.error(f"Error deleting old documents from '{collection_name}': {e}", exc_info=True)

if __name__ == "__main__":
    delete_documents_older_than_30_days('newsletter_summaries')
    delete_documents_older_than_30_days('newsletter_recommendations')