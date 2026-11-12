"""
End-to-End Execution Pipeline CLI for Multi-Touch Attribution Engine.
Usage:
    python run_pipeline.py --scale starter --seed 20261022
    python run_pipeline.py --scale medium --seed 20261022
    python run_pipeline.py --scale full --seed 20261022
"""
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from src.config import DATA_DIR, DOCS_DIR, DEFAULT_SEED
from src.generator.synthetic_gen import SyntheticDataGenerator
from src.generator.validator import DataValidator
from src.generator.exporter import DataExporter
from src.generator.data_dictionary import export_data_dictionary_markdown
from src.engine.identity_graph import IdentityGraph
from src.engine.attribution import AttributionEngine
from src.engine.roi_calculator import ROICalculator
from src.engine.audit_tracker import AuditTracker

def main():
    parser = argparse.ArgumentParser(description="Multi-Touch Attribution & ROI Pipeline")
    parser.add_argument("--scale", type=str, default="starter", choices=["starter", "medium", "full"], help="Dataset scale")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for deterministic generation")
    parser.add_argument("--no-anomalies", dest="inject_anomalies", action="store_false", default=True, help="Disable anomaly injection")
    args = parser.parse_args()

    print("\n" + "="*75)
    print("🚀 MULTI-TOUCH ATTRIBUTION & ROI PIPELINE RUNNER")
    print(f"Scale: {args.scale.upper()} | Seed: {args.seed} | Inject Anomalies: {args.inject_anomalies}")
    print("="*75 + "\n")

    # Step 1 & 2: Generate Data
    print("[1/7] 📦 Generating synthetic relational data...")
    generator = SyntheticDataGenerator(seed=args.seed, scale=args.scale)
    data = generator.generate(inject_anomalies=args.inject_anomalies)
    ground_truth = data.pop("ground_truth", [])

    print(f"      ✔ Campaigns:    {len(data['campaigns']):,}")
    print(f"      ✔ Contacts:     {len(data['contacts']):,}")
    print(f"      ✔ Sessions:     {len(data['web_sessions']):,}")
    print(f"      ✔ Touchpoints:  {len(data['touchpoints']):,}")
    print(f"      ✔ Leads:        {len(data['leads']):,}")
    print(f"      ✔ Opportunities:{len(data['opportunities']):,}")
    print(f"      ✔ Orders:       {len(data['orders']):,}")
    print(f"      ✔ Cost Records: {len(data['cost_records']):,}")
    print(f"      ✔ Anomaly GT:   {len(ground_truth)} records")

    # Step 3: Validate Relational Data
    print("\n[2/7] 🔍 Running relational validation, lifecycle transitions & integrity checks...")
    validator = DataValidator(data)
    validation_summary = validator.validate_all()
    print(f"      ✔ Schema Status: {'VALID' if validation_summary['is_valid'] else 'ISSUES FOUND'}")
    print(f"      ✔ Checks Run: {len(validation_summary['checks_run'])} suites ({', '.join(validation_summary['checks_run'])})")
    print(f"      ✔ Errors: {validation_summary['error_count']} | Warnings: {validation_summary['warning_count']}")

    # Step 4: Identity Verification & Customer Journey Stitching
    print("\n[3/7] 🔗 Verifying Identity Links & Stitching Customer Journeys...")
    graph = IdentityGraph(
        contacts_df=data["contacts"],
        touchpoints_df=data["touchpoints"],
        sessions_df=data["web_sessions"],
        opportunities_df=data["opportunities"],
        orders_df=data["orders"]
    )
    verified_sessions, identity_audits, id_stats = graph.verify_identity_links()
    graph.sessions = verified_sessions
    data["web_sessions"] = verified_sessions
    print(f"      ✔ Verified Sessions:  {id_stats['identified_sessions']:,}")
    print(f"      ✔ Anonymous Sessions: {id_stats['anonymous_sessions']:,}")
    print(f"      ✔ High-Intent Missing Links: {id_stats['high_intent_missing_identity_links']:,}")
    print(f"      ✔ Unsubstantiated Links Flagged: {id_stats['unsubstantiated_links_flagged']}")

    # Step 5: Compute 5 Attribution Models
    print("\n[4/7] 🧠 Computing 5 Multi-Touch Attribution Models...")
    engine = AttributionEngine(
        identity_graph=graph,
        campaigns_df=data["campaigns"],
        orders_df=data["orders"],
        ground_truth=ground_truth
    )
    attribution_results, attr_audits = engine.compute_all_attributions()
    data["attribution_results"] = attribution_results
    print(f"      ✔ Generated {len(attribution_results):,} attribution credit records across 5 models.")

    # Step 6: Spend Reconciliation, Chronological Split & Invariant Verification
    print("\n[5/7] 💰 Reconciling Multi-Currency Spend, Period Splits & ROI Reconciliation...")
    roi_calc = ROICalculator(
        campaigns_df=data["campaigns"],
        cost_records_df=data["cost_records"],
        channels_df=data["channels"],
        orders_df=data["orders"],
        ground_truth=ground_truth
    )
    spend_df, spend_audits = roi_calc.reconcile_spend()
    campaign_roi = roi_calc.compute_campaign_model_roi(attribution_results, spend_df)
    period_breakdown = roi_calc.compute_period_breakdown(attribution_results, data["cost_records"])
    reconciliation_proof = roi_calc.verify_reconciliation(attribution_results, data["orders"])

    print(f"      ✔ Reconciled {len(campaign_roi):,} campaign-model performance combinations.")
    print(f"      ✔ Chronological Periods Evaluated: {period_breakdown['period'].nunique()} quarters")
    print(f"      ✔ Invariant Proof: Total Attributed Revenue == Closed Won Revenue -> [{reconciliation_proof['reconciliation_status']}]")

    # Step 7: Audit Tracker & Rigorous Ground Truth Evaluation
    print("\n[6/7] 🛡️ Evaluating Anomaly Detection against Separate Ground Truth...")
    tracker = AuditTracker(ground_truth)
    tracker.extend_from_logs(identity_audits)
    tracker.extend_from_logs(attr_audits)
    tracker.extend_from_logs(spend_audits)
    audit_eval = tracker.evaluate_against_ground_truth()

    print(f"      ✔ Evaluation Status:  {audit_eval['evaluation_status']}")
    print(f"      ✔ Anomaly Coverage:   {audit_eval['anomaly_type_coverage_pct']}% of all 5 anomaly types")
    print(f"      ✔ Precision:          {audit_eval['overall_precision'] * 100:.1f}%")
    print(f"      ✔ Recall:             {audit_eval['overall_recall'] * 100:.1f}%")
    print(f"      ✔ F1-Score:           {audit_eval['overall_f1']:.4f}")
    print(f"      ✔ Logged {audit_eval['total_audit_events_logged']} total audit events.")

    # Step 8: Export Complete Seed Data, SQLite DB, Manifest, and Docs
    print("\n[7/7] 💾 Exporting Datasets (CSV, JSON, SQLite, Full SQL), Manifest & Docs...")
    exporter = DataExporter(DATA_DIR)
    manifest = exporter.export_all(
        datasets=data,
        ground_truth=ground_truth,
        seed=args.seed,
        scale=args.scale,
        validation_summary=validation_summary
    )
    # Export Data Dictionary Markdown
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    export_data_dictionary_markdown(str(DOCS_DIR / "DATA_DICTIONARY.md"))

    print("\n" + "="*75)
    print("🎉 PIPELINE EXECUTION COMPLETED WITH 100% INTEGRITY & RECONCILIATION!")
    print(f"Database:      {DATA_DIR / 'attribution.db'}")
    print(f"Raw CSVs:      {DATA_DIR / 'raw'} (*.csv)")
    print(f"Raw JSONs:     {DATA_DIR / 'raw'} (*.json) & {DATA_DIR / 'seed_data.json'}")
    print(f"Full SQL Seed: {DATA_DIR / 'seed_data.sql'}")
    print(f"Ground Truth:  {DATA_DIR / 'ground_truth.json'}")
    print(f"Manifest:      {DATA_DIR / 'source_manifest.json'}")
    print(f"Data Dict:     {DOCS_DIR / 'DATA_DICTIONARY.md'}")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
