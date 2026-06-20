"""
integrity.py
──────────────────────────────────────────────────────────────
Feature 5 — Evidence Integrity System

Every evidence image is SHA-256 hashed at write time.
The hash is stored in the metadata JSON and in a separate
integrity ledger (evidence/integrity.jsonl).

Verification:
    python integrity.py verify evidence/images/RID_full.jpg

If the image has been tampered with, the hash won't match and
the evidence is flagged as INVALID — useful for court submissions.

Usage from code:
    from integrity import hash_file, attach_hash, verify_record
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

LEDGER_PATH = Path("evidence/integrity.jsonl")
LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Core hashing ──────────────────────────────────────────────────────────────

def hash_file(path: str | Path) -> str:
    """
    Compute SHA-256 of a file.
    Returns hex digest string, or empty string on error.
    """
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f"[Integrity] Hash error for {path}: {e}")
        return ""


def hash_string(data: str) -> str:
    """SHA-256 of a UTF-8 string (used for JSON metadata hashing)."""
    return hashlib.sha256(data.encode()).hexdigest()


# ── Attach hashes to an evidence record dict ──────────────────────────────────

def attach_hash(record: dict) -> dict:
    """
    Add sha256 hashes for image_path, vehicle_crop, and plate_crop
    to the record dict in-place. Also appends an entry to the ledger.

    Call this AFTER save_evidence() writes the files to disk.
    """
    for key in ("image_path", "vehicle_crop", "plate_crop"):
        path = record.get(key, "")
        if path:
            record[f"{key}_sha256"] = hash_file(path)

    # Hash the metadata JSON itself (without these hash fields)
    meta_clean = {k: v for k, v in record.items()
                  if not k.endswith("_sha256")}
    record["metadata_sha256"] = hash_string(
        json.dumps(meta_clean, sort_keys=True))

    record["integrity_timestamp"] = datetime.now().isoformat()

    _append_ledger(record)
    return record


# ── Ledger ────────────────────────────────────────────────────────────────────

def _append_ledger(record: dict) -> None:
    """Append a one-line entry to the append-only integrity ledger."""
    entry = {
        "record_id":          record.get("record_id", "?"),
        "timestamp":          record.get("integrity_timestamp", ""),
        "image_sha256":       record.get("image_path_sha256", ""),
        "vehicle_sha256":     record.get("vehicle_crop_sha256", ""),
        "plate_sha256":       record.get("plate_crop_sha256", ""),
        "metadata_sha256":    record.get("metadata_sha256", ""),
    }
    try:
        with open(LEDGER_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[Integrity] Ledger write error: {e}")


def load_ledger() -> list[dict]:
    """Load all ledger entries as a list of dicts."""
    entries = []
    if not LEDGER_PATH.exists():
        return entries
    with open(LEDGER_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries


# ── Verification ──────────────────────────────────────────────────────────────

def verify_record(record: dict) -> dict:
    """
    Verify all stored hashes in a metadata record against actual files.

    Returns:
        {
          "valid":   bool,    # True only if ALL present hashes match
          "checks":  dict     # key → "OK" | "TAMPERED" | "MISSING"
        }
    """
    checks: dict[str, str] = {}

    for key in ("image_path", "vehicle_crop", "plate_crop"):
        stored_hash = record.get(f"{key}_sha256", "")
        path        = record.get(key, "")
        if not stored_hash:
            continue                    # hash was never computed
        if not path or not Path(path).exists():
            checks[key] = "MISSING"
        else:
            actual = hash_file(path)
            checks[key] = "OK" if actual == stored_hash else "TAMPERED"

    # Metadata self-check
    stored_meta = record.get("metadata_sha256", "")
    if stored_meta:
        meta_clean = {k: v for k, v in record.items()
                      if not k.endswith("_sha256")
                      and k != "integrity_timestamp"}
        actual_meta = hash_string(json.dumps(meta_clean, sort_keys=True))
        checks["metadata"] = "OK" if actual_meta == stored_meta else "TAMPERED"

    all_ok = all(v == "OK" for v in checks.values())
    return {"valid": all_ok, "checks": checks}


def verify_file(image_path: str, record_id: str) -> dict:
    """
    Look up record_id in the ledger and verify the given image file hash.
    Useful for standalone CLI verification.
    """
    target_hash = hash_file(image_path)
    for entry in load_ledger():
        if entry.get("record_id") == record_id:
            stored = entry.get("image_sha256", "")
            match  = stored == target_hash
            return {
                "record_id":    record_id,
                "image_path":   image_path,
                "computed":     target_hash,
                "stored":       stored,
                "valid":        match,
                "status":       "OK" if match else "TAMPERED",
            }
    return {"record_id": record_id, "status": "NOT_IN_LEDGER",
            "computed": target_hash}


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    """
    Usage:
        python integrity.py verify <image_path> <record_id>
        python integrity.py ledger
    """
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "verify" and len(sys.argv) == 4:
        result = verify_file(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif cmd == "ledger":
        entries = load_ledger()
        print(f"\n{'═'*62}")
        print(f"  INTEGRITY LEDGER  ({len(entries)} entries)")
        print(f"{'═'*62}")
        for e in entries[-20:]:
            status = "✓" if e.get("image_sha256") else "?"
            print(f"  {status}  {e['record_id']:<10}  {e['timestamp'][:19]}")
        print(f"{'═'*62}\n")

    else:
        print("Usage: python integrity.py verify <image_path> <record_id>")
        print("       python integrity.py ledger")


if __name__ == "__main__":
    _cli()