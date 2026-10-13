"""Central config/flags for the AI layer. Everything degrades gracefully to a
mock/offline mode when API keys are absent, so the full demo works with zero
external credentials configured.
"""
import os
import pathlib

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "").strip()
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", "").strip()
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "curasense-policies")

HAS_OPENAI = bool(OPENAI_API_KEY)
HAS_ANTHROPIC = bool(ANTHROPIC_API_KEY)
HAS_PINECONE = bool(PINECONE_API_KEY)

VECTOR_CACHE_DIR = pathlib.Path(__file__).resolve().parent / ".vector_cache"
VECTOR_CACHE_DIR.mkdir(exist_ok=True)
