"""
firebase/firebase_config.py
──────────────────────────────────────────────────────────────
Initialises Firebase Admin SDK once per process.
Place your service-account JSON at:
    firebase/hmates-d052b-firebase-adminsdk.json
"""

import firebase_admin
from firebase_admin import credentials, firestore, storage

FIREBASE_KEY   = (r"E:\traffic_ai\Backend\firebase\hmates-d052b-firebase-adminsdk.json")
STORAGE_BUCKET = "hmates-d052b.firebasestorage.app"

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY)
    firebase_admin.initialize_app(cred, {"storageBucket": STORAGE_BUCKET})

db     = firestore.client()
bucket = storage.bucket()