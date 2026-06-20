"""
firebase/storage_service.py
──────────────────────────────────────────────────────────────
Upload local evidence files to Firebase Storage and return
their public URLs.
"""

import os
from pathlib import Path
from firebase.firebase_config import bucket


def upload_image(local_path: str, remote_path: str) -> str:
    """
    Upload a local file to Firebase Storage.
    Returns the public URL, or "" on failure (so the pipeline never crashes).
    """
    if not local_path or not Path(local_path).exists():
        return ""
    try:
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(local_path)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"[Firebase/Storage] Upload failed for {local_path}: {e}")
        return ""


def upload_evidence_pack(rid: str,
                         full_path:    str = "",
                         vehicle_path: str = "",
                         plate_path:   str = "") -> dict:
    """
    Upload the three evidence images for one record.
    Returns {full_url, vehicle_url, plate_url} — empty string where unavailable.
    """
    full_url    = upload_image(full_path,    f"evidence/full/{os.path.basename(full_path)}")        if full_path    else ""
    vehicle_url = upload_image(vehicle_path, f"evidence/vehicle/{os.path.basename(vehicle_path)}") if vehicle_path else ""
    plate_url   = upload_image(plate_path,   f"evidence/plate/{os.path.basename(plate_path)}")     if plate_path   else ""

    return {"full_url": full_url, "vehicle_url": vehicle_url, "plate_url": plate_url}