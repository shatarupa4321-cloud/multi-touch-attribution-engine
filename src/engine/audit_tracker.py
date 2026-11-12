"""
Comprehensive Audit Trail, Traceability, and Anomaly Detection Evaluator.
Implements strict record-level anomaly matching using issue_type and record_id.
Calculates genuine True Positives (TP), False Positives (FP), False Negatives (FN),
Precision, Recall, and F1-scores across all 5 injected edge cases:
1. REVENUE_COUNTED_MORE_THAN_ONCE
2. TOUCHPOINT_AFTER_CONVERSION_ATTRIBUTED
3. SPEND_CURRENCY_MISMATCH
4. CAMPAIGN_COSTS_OMITTED
5. ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE
"""
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

class AuditTracker:
    def __init__(self, ground_truth: List[Dict[str, Any]]):
        self.ground_truth = ground_truth
        self.audit_events: List[Dict[str, Any]] = []

    def record_event(
        self,
        issue_type: str,
        entity: str,
        record_id: str,
        description: str,
        action_taken: str
    ):
        """Records an explicit exception handling event into the audit trail."""
        self.audit_events.append({
            "audit_id": f"AUD-EVT-{len(self.audit_events) + 1:05d}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "issue_type": issue_type,
            "entity": entity,
            "record_id": str(record_id).strip(),
            "description": description,
            "action_taken": action_taken
        })

    def extend_from_logs(self, logs: List[Dict[str, Any]]):
        """Ingests list of audit dictionary events with record_id normalization."""
        for item in logs:
            rec_id = item.get("record_id") or item.get("touchpoint_id") or item.get("opportunity_id") or item.get("campaign_id") or "N/A"
            self.audit_events.append({
                "audit_id": item.get("audit_id", f"AUD-EVT-{len(self.audit_events) + 1:05d}"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "issue_type": item.get("issue_type", "GENERIC_EXCEPTION"),
                "entity": item.get("entity", "AttributionEngine"),
                "record_id": str(rec_id).strip(),
                "related_parent_id": str(item.get("related_parent_id", "")).strip(),
                "description": item.get("description") or item.get("resolution", ""),
                "action_taken": item.get("resolution") or item.get("action_taken", "Audited and handled")
            })

    def evaluate_against_ground_truth(self) -> Dict[str, Any]:
        """
        Calculates genuine record-level evaluation metrics:
        Matches ground truth records against audit events using exact (issue_type, record_id).
        Computes genuine TP, FP, FN, Precision, Recall, and F1-Scores.
        """
        # Map ground truth items by normalized issue_type and record_id
        gt_by_type: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for gt in self.ground_truth:
            norm_type = self._normalize_issue_type(gt["issue_type"])
            rec_id = str(gt.get("record_id", "")).strip()
            gt_by_type.setdefault(norm_type, {})[rec_id] = gt

        # Map detected audit events by normalized issue_type and record_id
        detected_by_type: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for evt in self.audit_events:
            norm_type = self._normalize_issue_type(evt["issue_type"])
            rec_id = str(evt.get("record_id", "")).strip()
            detected_by_type.setdefault(norm_type, {}).setdefault(rec_id, []).append(evt)

        core_issue_types = [
            "REVENUE_COUNTED_MORE_THAN_ONCE",
            "TOUCHPOINT_AFTER_CONVERSION_ATTRIBUTED",
            "SPEND_CURRENCY_MISMATCH",
            "CAMPAIGN_COSTS_OMITTED",
            "ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE"
        ]

        breakdown = {}
        total_tp = 0
        total_fn = 0
        total_fp = 0

        for itype in core_issue_types:
            gt_records = gt_by_type.get(itype, {})
            det_records = detected_by_type.get(itype, {})

            gt_ids = set(gt_records.keys())
            det_ids = set(det_records.keys())

            # Genuine record-level matching
            tp_ids = gt_ids & det_ids
            fn_ids = gt_ids - det_ids
            fp_ids = det_ids - gt_ids

            tp = len(tp_ids)
            fn = len(fn_ids)
            fp = len(fp_ids)

            total_tp += tp
            total_fn += fn
            total_fp += fp

            # Calculate genuine Precision, Recall, and F1
            prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
            rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
            f1 = round(2 * (prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

            breakdown[itype] = {
                "ground_truth_count": len(gt_ids),
                "detected_count": len(det_ids),
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "matched_record_ids": sorted(list(tp_ids)),
                "unmatched_gt_ids": sorted(list(fn_ids)),
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "status": "RECOVERED" if tp > 0 else "MISSED"
            }

        overall_precision = round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = round(2 * (overall_precision * overall_recall) / (overall_precision + overall_recall), 4) if (overall_precision + overall_recall) > 0 else 0.0

        recovered_types = sum(1 for b in breakdown.values() if b["status"] == "RECOVERED")
        coverage_pct = round((recovered_types / len(core_issue_types)) * 100.0, 1)

        return {
            "evaluation_status": (
                "PASSED"
                if coverage_pct == 100.0
                and total_fn == 0
                and overall_precision >= 0.80
                else "NEEDS_IMPROVEMENT"
            ),
            "anomaly_type_coverage_pct": coverage_pct,
            "overall_precision": overall_precision,
            "overall_recall": overall_recall,
            "overall_f1": overall_f1,
            "total_ground_truth_anomalies": len(self.ground_truth),
            "total_audit_events_logged": len(self.audit_events),
            "confusion_totals": {
                "true_positives": total_tp,
                "false_positives": total_fp,
                "false_negatives": total_fn
            },
            "breakdown": breakdown
        }

    def _normalize_issue_type(self, raw_type: str) -> str:
        s = str(raw_type).upper()
        if "REVENUE_COUNTED_MORE_THAN_ONCE" in s or "DEDUP" in s:
            return "REVENUE_COUNTED_MORE_THAN_ONCE"
        if "TOUCHPOINT_AFTER_CONVERSION" in s:
            return "TOUCHPOINT_AFTER_CONVERSION_ATTRIBUTED"
        if "SPEND_CURRENCY" in s or "CURR" in s:
            return "SPEND_CURRENCY_MISMATCH"
        if "CAMPAIGN_COSTS_OMITTED" in s or "NO-COST" in s:
            return "CAMPAIGN_COSTS_OMITTED"
        if "ANONYMOUS_SESSION_LINKED" in s or "IDENTITY" in s:
            return "ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE"
        return raw_type
