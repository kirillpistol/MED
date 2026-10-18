"""Schemas for private medical records and scanned learning materials.

Only synthetic metadata validation; this module does not persist clinical records.
Private storage and permissions belong to GENESIS L2.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import re

KINDS = {"blood_test", "imaging", "clinical_note", "medical_book", "guideline"}

def validate_submission(item: dict) -> dict:
    required = ("document_id", "kind", "owner_ref", "filename", "consent_scope")
    absent = [key for key in required if not item.get(key)]
    if absent:
        raise ValueError("missing required fields: " + ", ".join(absent))
    if item["kind"] not in KINDS:
        raise ValueError("unsupported medical document type")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{4,100}", item["document_id"]):
        raise ValueError("invalid document identifier")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{4,100}", item["owner_ref"]):
        raise ValueError("invalid owner reference")
    if item["consent_scope"] not in ("private_analysis", "private_reference"):
        raise ValueError("explicit private consent scope required")
    if item["kind"] == "medical_book" and not item.get("rights_basis"):
        raise ValueError("book rights basis required")
    return {
        "document_id": item["document_id"], "kind": item["kind"],
        "owner_ref": item["owner_ref"], "consent_scope": item["consent_scope"],
        "processing": "pending_l2_authorization",
        "storage": "L2_only",
        "indexed_for_public_search": False,
        "trained_into_model": False,
    }
