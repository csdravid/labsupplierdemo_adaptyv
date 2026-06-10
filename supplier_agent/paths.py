"""Repository paths — all data relative to repo root (L0 scaffold)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INVENTORY = DATA / "inventory.csv"
INVENTORY_DEMO = DATA / "inventory.demo.csv"
POLICY = DATA / "policy.md"
SPEND_LOG = DATA / "spend_log.csv"
BENCHLING_SAMPLE = DATA / "benchling_export_sample.csv"
DRAFTS = ROOT / "drafts"
PENDING = DRAFTS / "pending"
APPROVED = DRAFTS / "approved"
ACTIVITY = ROOT / "activity.md"
PROMPTS = ROOT / "prompts"
DRAFT_PO_PROMPT = PROMPTS / "draft_po.txt"
