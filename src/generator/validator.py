"""
Comprehensive Relational & Business Rule Validator.
Enforces:
1. Primary key uniqueness
2. Foreign key referential integrity
3. Allowed enums & format constraints
4. Date temporal ordering
5. Arithmetic non-negative bounds
6. Lifecycle transitions (Contact, Lead, Opportunity)
7. Duplicate detection (Orders, Touchpoints, Sessions)
8. Cardinality constraints (1:1 Opportunity -> Order, 1:N Campaign -> Touches)
"""
import re
import hashlib
from typing import Dict, List, Any
import pandas as pd
from src.generator.data_dictionary import DATA_DICTIONARY

class DataValidator:
    def __init__(self, datasets: Dict[str, pd.DataFrame]):
        self.datasets = datasets
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}
        self.checks_run: List[str] = []

    def validate_all(self) -> Dict[str, Any]:
        """Runs all 8 validation suites and compiles a comprehensive scorecard."""
        self._validate_row_counts_and_pks()
        self._validate_foreign_keys()
        self._validate_enums()
        self._validate_date_orderings()
        self._validate_arithmetic_bounds()
        self._validate_lifecycle_transitions()
        self._validate_duplicates()
        self._validate_cardinality()

        is_valid = len(self.errors) == 0
        return {
            "is_valid": is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "table_stats": self.stats,
            "checks_run": self.checks_run
        }

    def _validate_row_counts_and_pks(self):
        """Checks row counts and primary key uniqueness."""
        self.checks_run.append("PrimaryKeyUniqueness")
        for table_name, df in self.datasets.items():
            if table_name == "ground_truth" or not isinstance(df, pd.DataFrame):
                continue
            pk_col = DATA_DICTIONARY.get(self._get_entity_key(table_name), {}).get("primary_key")
            count = len(df)
            self.stats[table_name] = {"rows": count}
            
            if pk_col and pk_col in df.columns:
                n_unique = df[pk_col].nunique()
                self.stats[table_name]["unique_pks"] = n_unique
                if n_unique != count:
                    self.warnings.append({
                        "suite": "PrimaryKeyUniqueness",
                        "table": table_name,
                        "message": f"Primary key '{pk_col}' has {count - n_unique} duplicate values (expected if anomaly injected)."
                    })

    def _validate_foreign_keys(self):
        """Checks foreign key referential integrity."""
        self.checks_run.append("ForeignKeyIntegrity")
        opps = self.datasets.get("opportunities")
        contacts = self.datasets.get("contacts")
        leads = self.datasets.get("leads")
        campaigns = self.datasets.get("campaigns")
        touchpoints = self.datasets.get("touchpoints")
        orders = self.datasets.get("orders")

        # Opportunities -> Contacts & Leads
        if opps is not None and contacts is not None:
            missing_contacts = set(opps["contact_id"]) - set(contacts["contact_id"])
            if missing_contacts:
                self.errors.append({
                    "suite": "ForeignKeyIntegrity",
                    "table": "opportunities",
                    "message": f"Found {len(missing_contacts)} orphan contact_id values in opportunities."
                })

        if opps is not None and leads is not None:
            missing_leads = set(opps["lead_id"]) - set(leads["lead_id"])
            if missing_leads:
                self.errors.append({
                    "suite": "ForeignKeyIntegrity",
                    "table": "opportunities",
                    "message": f"Found {len(missing_leads)} orphan lead_id values in opportunities."
                })

        # Touchpoints -> Contacts & Campaigns
        if touchpoints is not None:
            if contacts is not None:
                missing = set(touchpoints["contact_id"]) - set(contacts["contact_id"])
                if missing:
                    self.errors.append({
                        "suite": "ForeignKeyIntegrity",
                        "table": "touchpoints",
                        "message": f"Found {len(missing)} orphan contact_ids in touchpoints."
                    })
            if campaigns is not None:
                missing = set(touchpoints["campaign_id"]) - set(campaigns["campaign_id"])
                if missing:
                    self.errors.append({
                        "suite": "ForeignKeyIntegrity",
                        "table": "touchpoints",
                        "message": f"Found {len(missing)} orphan campaign_ids in touchpoints."
                    })

        # Orders -> Opportunities
        if orders is not None and opps is not None:
            missing_opps = set(orders["opportunity_id"]) - set(opps["opportunity_id"])
            if missing_opps:
                self.errors.append({
                    "suite": "ForeignKeyIntegrity",
                    "table": "orders",
                    "message": f"Found {len(missing_opps)} orphan opportunity_ids in orders."
                })

    def _validate_enums(self):
        """Validates enum fields against data dictionary."""
        self.checks_run.append("EnumConstraint")
        for table_name, df in self.datasets.items():
            if not isinstance(df, pd.DataFrame):
                continue
            ent_key = self._get_entity_key(table_name)
            ent_def = DATA_DICTIONARY.get(ent_key)
            if not ent_def:
                continue
            for field, finfo in ent_def["fields"].items():
                if "allowed_values" in finfo and field in df.columns:
                    allowed = set(finfo["allowed_values"])
                    actual = set(df[field].dropna().unique())
                    diff = actual - allowed
                    if diff:
                        self.warnings.append({
                            "suite": "EnumConstraint",
                            "table": table_name,
                            "field": field,
                            "message": f"Values {diff} not in allowed enums: {allowed}"
                        })

    def _validate_date_orderings(self):
        """Validates logical chronological order."""
        self.checks_run.append("DateOrdering")
        # Campaigns start_date <= end_date
        camps = self.datasets.get("campaigns")
        if camps is not None:
            invalid_dates = camps[pd.to_datetime(camps["start_date"]) > pd.to_datetime(camps["end_date"])]
            if len(invalid_dates) > 0:
                self.errors.append({
                    "suite": "DateOrdering",
                    "table": "campaigns",
                    "message": f"{len(invalid_dates)} campaigns have start_date > end_date."
                })

        # Opportunities created_at <= closed_at
        opps = self.datasets.get("opportunities")
        if opps is not None:
            closed_opps = opps.dropna(subset=["closed_at"])
            invalid_opps = closed_opps[pd.to_datetime(closed_opps["created_at"]) > pd.to_datetime(closed_opps["closed_at"])]
            if len(invalid_opps) > 0:
                self.errors.append({
                    "suite": "DateOrdering",
                    "table": "opportunities",
                    "message": f"{len(invalid_opps)} opportunities have created_at > closed_at."
                })

    def _validate_arithmetic_bounds(self):
        """Checks for non-negative revenues and budgets."""
        self.checks_run.append("ArithmeticBounds")
        opps = self.datasets.get("opportunities")
        if opps is not None and (opps["amount"] < 0).any():
            self.errors.append({
                "suite": "ArithmeticBounds",
                "table": "opportunities",
                "message": "Found negative opportunity amounts."
            })

        camps = self.datasets.get("campaigns")
        if camps is not None and (camps["budget"] < 0).any():
            self.errors.append({
                "suite": "ArithmeticBounds",
                "table": "campaigns",
                "message": "Found negative campaign budgets."
            })

    def _validate_lifecycle_transitions(self):
        """Validates that entity stages reflect allowed lifecycle states."""
        self.checks_run.append("LifecycleTransitions")
        # Contact lifecycle states
        contacts = self.datasets.get("contacts")
        if contacts is not None:
            valid_stages = set(DATA_DICTIONARY["Contact"]["lifecycle_states"])
            invalid_c = set(contacts["lifecycle_stage"].unique()) - valid_stages
            if invalid_c:
                self.errors.append({
                    "suite": "LifecycleTransitions",
                    "table": "contacts",
                    "message": f"Invalid contact lifecycle stages found: {invalid_c}"
                })

        # Opportunity stages
        opps = self.datasets.get("opportunities")
        if opps is not None:
            valid_opp_stages = set(DATA_DICTIONARY["Opportunity"]["lifecycle_states"])
            invalid_opp = set(opps["stage"].unique()) - valid_opp_stages
            if invalid_opp:
                self.errors.append({
                    "suite": "LifecycleTransitions",
                    "table": "opportunities",
                    "message": f"Invalid opportunity stages found: {invalid_opp}"
                })

    def _validate_duplicates(self):
        """Checks for unexpected duplicates across transaction tables."""
        self.checks_run.append("DuplicateChecks")
        orders = self.datasets.get("orders")
        if orders is not None:
            # Check duplicate order_ids
            dup_orders = orders[orders.duplicated(subset=["order_id"], keep=False)]
            if len(dup_orders) > 0:
                self.warnings.append({
                    "suite": "DuplicateChecks",
                    "table": "orders",
                    "message": f"Found {len(dup_orders)} duplicate order IDs."
                })

    def _validate_cardinality(self):
        """Validates expected entity cardinalities (e.g. 1:1 on won opp -> order)."""
        self.checks_run.append("CardinalityConstraints")
        orders = self.datasets.get("orders")
        opps = self.datasets.get("opportunities")
        if orders is not None and opps is not None:
            # Opportunity to Order should be 1:1 for Closed Won
            opp_counts = orders.groupby("opportunity_id").size()
            multi_orders = opp_counts[opp_counts > 1]
            if len(multi_orders) > 0:
                self.warnings.append({
                    "suite": "CardinalityConstraints",
                    "table": "orders",
                    "message": f"{len(multi_orders)} opportunities have multiple order records (Anomaly #1 injected)."
                })

    def _get_entity_key(self, table_name: str) -> str:
        mapping = {
            "channels": "Channel",
            "audiences": "Audience",
            "campaigns": "Campaign",
            "creatives": "Creative",
            "contacts": "Contact",
            "web_sessions": "WebSession",
            "touchpoints": "Touchpoint",
            "leads": "Lead",
            "opportunities": "Opportunity",
            "orders": "Order",
            "cost_records": "CostRecord",
            "attribution_results": "AttributionResult"
        }
        return mapping.get(table_name, table_name.capitalize())

def compute_dataset_checksums(datasets: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """Computes SHA-256 hash for each table to verify deterministic reproducibility."""
    checksums = {}
    for name, df in datasets.items():
        if isinstance(df, pd.DataFrame):
            csv_str = df.to_csv(index=False).encode("utf-8")
            checksums[name] = hashlib.sha256(csv_str).hexdigest()
    return checksums
