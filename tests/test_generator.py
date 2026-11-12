"""
Tests for Synthetic Data Generator, Validation Suite, and Exporter.
Verifies:
- Fixed seed reproducibility (identical row counts & checksums across runs)
- Referential integrity & Lifecycle transitions
- Ground truth anomaly registry
- Multi-format file export (CSV, JSON, SQLite, SQL seed)
"""
import pytest
from pathlib import Path
from src.generator.synthetic_gen import SyntheticDataGenerator
from src.generator.validator import DataValidator, compute_dataset_checksums
from src.generator.exporter import DataExporter

def test_fixed_seed_reproducibility():
    """Step 10: Regenerate twice with the same seed and compare checksums/row counts."""
    seed = 20261022
    gen1 = SyntheticDataGenerator(seed=seed, scale="starter")
    data1 = gen1.generate(inject_anomalies=True)
    chk1 = compute_dataset_checksums(data1)

    gen2 = SyntheticDataGenerator(seed=seed, scale="starter")
    data2 = gen2.generate(inject_anomalies=True)
    chk2 = compute_dataset_checksums(data2)

    assert chk1 == chk2, "Datasets generated with the same seed must produce identical SHA-256 checksums."
    for table_name in data1:
        if table_name != "ground_truth":
            assert len(data1[table_name]) == len(data2[table_name]), f"Row counts mismatch for {table_name}"

def test_schema_and_referential_integrity():
    """Step 8: Runs schema validation on clean generated dataset."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    data = gen.generate(inject_anomalies=False)
    validator = DataValidator(data)
    result = validator.validate_all()

    assert result["is_valid"], f"Validation failed with errors: {result['errors']}"
    assert result["error_count"] == 0
    assert "LifecycleTransitions" in result["checks_run"]
    assert "CardinalityConstraints" in result["checks_run"]

def test_ground_truth_registry_separation():
    """Step 7: Verifies anomalies are recorded separately and not leaked into clean flags."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    data = gen.generate(inject_anomalies=True)
    ground_truth = data["ground_truth"]

    assert len(ground_truth) > 0, "Ground truth must record injected anomalies."
    issue_types = {item["issue_type"] for item in ground_truth}
    expected_issues = {
        "REVENUE_COUNTED_MORE_THAN_ONCE",
        "TOUCHPOINT_AFTER_CONVERSION_ATTRIBUTED",
        "SPEND_CURRENCY_MISMATCH",
        "CAMPAIGN_COSTS_OMITTED",
        "ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE"
    }
    assert expected_issues == issue_types, f"Mismatch in injected issue types: {expected_issues ^ issue_types}"

def test_multi_format_exports(tmp_path):
    """Step 9: Verifies full export to CSV, JSON, SQLite and SQL seed dump."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    data = gen.generate(inject_anomalies=True)
    gt = data.pop("ground_truth")

    exporter = DataExporter(tmp_path)
    manifest = exporter.export_all(
        datasets=data,
        ground_truth=gt,
        seed=20261022,
        scale="starter",
        validation_summary={"is_valid": True}
    )

    # Check files exist
    assert (tmp_path / "attribution.db").exists()
    assert (tmp_path / "seed_data.sql").exists()
    assert (tmp_path / "seed_data.json").exists()
    assert (tmp_path / "ground_truth.json").exists()
    assert (tmp_path / "ground_truth.csv").exists()
    assert (tmp_path / "data_dictionary.json").exists()
    assert (tmp_path / "raw" / "campaigns.csv").exists()
    assert (tmp_path / "raw" / "campaigns.json").exists()
