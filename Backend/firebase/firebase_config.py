import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage

STORAGE_BUCKET = "hmates-d052b.firebasestorage.app"

if not firebase_admin._apps:

    if "FIREBASE_CREDENTIALS" in os.environ:
        firebase_creds = json.loads(os.environ["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(firebase_creds)
    else:
        cred = credentials.Certificate(
            os.path.join(
                os.path.dirname(__file__),
                "hmates-d052b-firebase-adminsdk.json"
            )
        )

    firebase_admin.initialize_app(
        cred,
        {
            "storageBucket": STORAGE_BUCKET
        }
    )

db = firestore.client()
bucket = storage.bucket()