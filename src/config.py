"""
Configuration and constants for Multi-Touch Attribution Engine.
"""
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DOCS_DIR = BASE_DIR / "docs"

DEFAULT_SEED = 20261022

# FX Rates normalized to USD
EXCHANGE_RATES_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27
}

@dataclass
class DatasetScale:
    name: str
    num_campaigns: int
    num_contacts: int
    num_touchpoints: int
    num_opportunities: int

SCALE_CONFIGS = {
    "starter": DatasetScale(
        name="starter",
        num_campaigns=30,
        num_contacts=150,
        num_touchpoints=800,
        num_opportunities=45
    ),
    "medium": DatasetScale(
        name="medium",
        num_campaigns=100,
        num_contacts=2000,
        num_touchpoints=10000,
        num_opportunities=600
    ),
    "full": DatasetScale(
        name="full",
        num_campaigns=500,
        num_contacts=50000,
        num_touchpoints=200000,
        num_opportunities=10000
    )
}
