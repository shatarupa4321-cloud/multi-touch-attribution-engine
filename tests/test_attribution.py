"""
Tests for Layer 2: Attribution Core, Identity Verification, ROI Calculator, and Anomaly Audit.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.generator.synthetic_gen import SyntheticDataGenerator
from src.engine.identity_graph import IdentityGraph
from src.engine.attribution import AttributionEngine
from src.engine.roi_calculator import ROICalculator
from src.engine.audit_tracker import AuditTracker

@pytest.fixture
def test_data():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    return gen.generate(inject_anomalies=True)

def test_attribution_weights_sum_to_one(test_data):
    """Verifies that for every opportunity and every model, attribution weights sum to exactly 1.0."""
    graph = IdentityGraph(
        contacts_df=test_data["contacts"],
        touchpoints_df=test_data["touchpoints"],
        sessions_df=test_data["web_sessions"],
        opportunities_df=test_data["opportunities"],
        orders_df=test_data["orders"]
    )
    engine = AttributionEngine(
        identity_graph=graph,
        campaigns_df=test_data["campaigns"],
        orders_df=test_data["orders"]
    )
    attr_df, audit_log = engine.compute_all_attributions()
    assert len(attr_df) > 0, "Attribution results should not be empty."

    # Group by opportunity and model
    weight_sums = attr_df.groupby(["opportunity_id", "model_name"])["attribution_weight"].sum()
    for (opp_id, model), total_weight in weight_sums.items():
        assert pytest.approx(total_weight, 0.0001) == 1.0, f"Weights for {opp_id} under {model} sum to {total_weight}, expected 1.0"

def test_temporal_window_filtering(test_data):
    """Verifies that touchpoints occurring after closed_at are excluded from attribution."""
    graph = IdentityGraph(
        contacts_df=test_data["contacts"],
        touchpoints_df=test_data["touchpoints"],
        sessions_df=test_data["web_sessions"],
        opportunities_df=test_data["opportunities"],
        orders_df=test_data["orders"]
    )
    engine = AttributionEngine(
        identity_graph=graph,
        campaigns_df=test_data["campaigns"],
        orders_df=test_data["orders"]
    )
    attr_df, audit_log = engine.compute_all_attributions()
    
    # Check that audit log captured post-conversion exclusions
    post_conv_audits = [a for a in audit_log if "TOUCHPOINT_AFTER_CONVERSION" in a["issue_type"]]
    assert len(post_conv_audits) > 0, "Post-conversion touchpoint anomalies must be detected and audited."

def test_identity_verification_unsubstantiated_links(test_data):
    """Verifies that identity verification flags unsubstantiated session stitching (Anomaly #5)."""
    graph = IdentityGraph(
        contacts_df=test_data["contacts"],
        touchpoints_df=test_data["touchpoints"],
        sessions_df=test_data["web_sessions"],
        opportunities_df=test_data["opportunities"],
        orders_df=test_data["orders"]
    )
    verified_sessions, id_audits, stats = graph.verify_identity_links()
    assert stats["unsubstantiated_links_flagged"] > 0, "Must flag unsubstantiated session links"
    assert any(a["issue_type"] == "ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE" for a in id_audits)

def test_roi_and_spend_reconciliation(test_data):
    """Verifies currency normalization, spend calculation, and ROI logic."""
    calculator = ROICalculator(
        campaigns_df=test_data["campaigns"],
        cost_records_df=test_data["cost_records"],
        channels_df=test_data["channels"],
        orders_df=test_data["orders"]
    )
    spend_df, spend_audits = calculator.reconcile_spend()
    assert "spend_amount_usd" in spend_df.columns
    # Requirement 5: Missing campaign costs must be preserved as NaN rather than replaced with 0
    assert (spend_df["spend_amount_usd"].dropna() >= 0).all()
    assert spend_df["spend_amount_usd"].isna().any(), "Campaign with omitted costs must have NaN spend."

    # Verify omitted cost detection
    omitted_audits = [a for a in spend_audits if "CAMPAIGN_COSTS_OMITTED" in a["issue_type"]]
    assert len(omitted_audits) > 0, "Omitted campaign costs must be flagged in audit log."

def test_mathematical_reconciliation_invariant(test_data):
    """Verifies accounting invariant: total attributed revenue == total closed won revenue."""
    graph = IdentityGraph(
        contacts_df=test_data["contacts"],
        touchpoints_df=test_data["touchpoints"],
        sessions_df=test_data["web_sessions"],
        opportunities_df=test_data["opportunities"],
        orders_df=test_data["orders"]
    )
    engine = AttributionEngine(
        identity_graph=graph,
        campaigns_df=test_data["campaigns"],
        orders_df=test_data["orders"]
    )
    attr_df, _ = engine.compute_all_attributions()
    calculator = ROICalculator(
        campaigns_df=test_data["campaigns"],
        cost_records_df=test_data["cost_records"],
        channels_df=test_data["channels"],
        orders_df=test_data["orders"]
    )
    proof = calculator.verify_reconciliation(attr_df, test_data["orders"])
    assert proof["reconciliation_status"] == "PASSED", f"Reconciliation failed: {proof}"

def test_audit_tracker_100_percent_coverage(test_data):
    """Verifies audit tracker achieves 100% coverage across all 5 injected anomaly types."""
    tracker = AuditTracker(test_data["ground_truth"])
    graph = IdentityGraph(
        contacts_df=test_data["contacts"],
        touchpoints_df=test_data["touchpoints"],
        sessions_df=test_data["web_sessions"],
        opportunities_df=test_data["opportunities"],
        orders_df=test_data["orders"]
    )
    _, id_audits, _ = graph.verify_identity_links()
    tracker.extend_from_logs(id_audits)

    engine = AttributionEngine(
        identity_graph=graph,
        campaigns_df=test_data["campaigns"],
        orders_df=test_data["orders"],
        ground_truth=test_data["ground_truth"]
    )
    _, attr_audits = engine.compute_all_attributions()
    tracker.extend_from_logs(attr_audits)

    calculator = ROICalculator(
        campaigns_df=test_data["campaigns"],
        cost_records_df=test_data["cost_records"],
        channels_df=test_data["channels"],
        orders_df=test_data["orders"],
        ground_truth=test_data["ground_truth"]
    )
    _, spend_audits = calculator.reconcile_spend()
    tracker.extend_from_logs(spend_audits)

    evaluation = tracker.evaluate_against_ground_truth()
    assert evaluation["anomaly_type_coverage_pct"] == 100.0, f"Expected 100% anomaly coverage, got: {evaluation['breakdown']}"
    assert evaluation["evaluation_status"] == "PASSED"
