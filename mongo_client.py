"""
mongo_client.py — MongoDB Atlas Integration for MedDigit AI
============================================================
Stores AI chat logs, OCR cache, and audit trail in MongoDB Atlas.
SQLite remains the primary database — this is purely additive.

If MONGODB_URI is not set, all functions silently do nothing.
The app works perfectly without MongoDB configured.
"""

import os
from datetime import datetime

# ── Connection ────────────────────────────────────────────────────────────────
_mongo_client = None
_mongo_db = None

def get_mongo_db():
    """Returns MongoDB database instance, or None if not configured."""
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        return None

    try:
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi
        _mongo_client = MongoClient(uri, server_api=ServerApi('1'), serverSelectionTimeoutMS=3000)
        # Ping to confirm connection
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client["meddigit"]
        print("✅ MongoDB Atlas connected → meddigit database")
        return _mongo_db
    except Exception as e:
        print(f"⚠️  MongoDB Atlas not available (app continues without it): {e}")
        return None


# ── Chat Logs ─────────────────────────────────────────────────────────────────
def log_chat_message(user_id: int, user_message: str, ai_response: str, model: str = "unknown"):
    """
    Stores a chatbot conversation turn in MongoDB.
    Collection: meddigit.chat_logs
    """
    db = get_mongo_db()
    if db is None:
        return

    try:
        db["chat_logs"].insert_one({
            "user_id": user_id,
            "user_message": user_message,
            "ai_response": ai_response,
            "model": model,
            "source": "meddigit_chatbot",
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        print(f"⚠️  MongoDB chat log write failed: {e}")


# ── AI Analysis Cache ─────────────────────────────────────────────────────────
def cache_ai_analysis(record_id: int, patient_id: int, ai_result: dict):
    """
    Caches OCR/AI analysis results in MongoDB for fast re-retrieval.
    Collection: meddigit.ai_cache
    """
    db = get_mongo_db()
    if db is None:
        return

    try:
        db["ai_cache"].update_one(
            {"record_id": record_id},
            {"$set": {
                "record_id": record_id,
                "patient_id": patient_id,
                "ai_result": ai_result,
                "cached_at": datetime.utcnow()
            }},
            upsert=True
        )
    except Exception as e:
        print(f"⚠️  MongoDB AI cache write failed: {e}")


# ── Extended Audit Trail ──────────────────────────────────────────────────────
def log_audit_event(user_id: int, action: str, patient_id: int = None, metadata: dict = None):
    """
    Stores a rich audit event in MongoDB (complements SQLite AuditLog).
    Collection: meddigit.audit_trail
    """
    db = get_mongo_db()
    if db is None:
        return

    try:
        db["audit_trail"].insert_one({
            "user_id": user_id,
            "action": action,
            "patient_id": patient_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        print(f"⚠️  MongoDB audit write failed: {e}")
