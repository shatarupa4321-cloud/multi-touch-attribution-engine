"""
Labelled Anomaly and Edge Case Injector.
Injects controlled, documented anomalies into clean baseline datasets
and logs them into a separate ground truth registry.
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
from datetime import timedelta

class AnomalyInjector:
    def __init__(self, rng):
        self.rng = rng
        self.ground_truth_records: List[Dict[str, Any]] = []

    def inject_all(
        self,
        campaigns_df: pd.DataFrame,
        contacts_df: pd.DataFrame,
        touchpoints_df: pd.DataFrame,
        sessions_df: pd.DataFrame,
        opportunities_df: pd.DataFrame,
        orders_df: pd.DataFrame,
        costs_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
        """
        Injects the 5 required domain anomalies into clean copies of DataFrames.
        """
        touchpoints = touchpoints_df.copy()
        sessions = sessions_df.copy()
        opportunities = opportunities_df.copy()
        orders = orders_df.copy()
        costs = costs_df.copy()
        campaigns = campaigns_df.copy()

        # 1. Revenue counted more than once (duplicate order injected)
        orders = self._inject_duplicate_revenue(orders, opportunities)

        # 2. Touchpoint after conversion attributed
        touchpoints = self._inject_post_conversion_touchpoints(touchpoints, opportunities)

        # 3. Spend currency mismatch (unconverted currency treated as USD)
        costs = self._inject_spend_currency_mismatch(costs)

        # 4. Campaign costs omitted (campaign with revenue but missing cost records)
        costs = self._inject_omitted_campaign_costs(costs, campaigns, touchpoints, orders)

        # 5. Anonymous session linked without evidence
        sessions = self._inject_unsubstantiated_session_link(sessions, contacts_df)

        return (
            campaigns,
            contacts_df,
            touchpoints,
            sessions,
            opportunities,
            orders,
            costs,
            self.ground_truth_records
        )

    def _inject_duplicate_revenue(self, orders: pd.DataFrame, opportunities: pd.DataFrame) -> pd.DataFrame:
        """Injects duplicate order records for closed-won opportunities, creating double revenue counting."""
        if len(orders) == 0:
            return orders
        
        sample_size = max(1, min(5, int(len(orders) * 0.05)))
        dup_indices = self.rng.sample(range(len(orders)), sample_size)
        
        duplicates = []
        for idx in dup_indices:
            row = orders.iloc[idx].to_dict()
            dup_id = f"{row['order_id']}-DUP"
            dup_row = row.copy()
            dup_row['order_id'] = dup_id
            duplicates.append(dup_row)

            self.ground_truth_records.append({
                "anomaly_id": f"ANO-REV-DUP-{len(self.ground_truth_records) + 1:04d}",
                "issue_type": "REVENUE_COUNTED_MORE_THAN_ONCE",
                "entity": "Order",
                "record_id": dup_id,
                "related_parent_id": row["opportunity_id"],
                "description": f"Duplicate order transaction created for opportunity {row['opportunity_id']}, inflating gross revenue by {row['gross_revenue']}.",
                "expected_handling": "Deduplicate order by opportunity_id or discard duplicate order reference before attribution."
            })

        if duplicates:
            orders = pd.concat([orders, pd.DataFrame(duplicates)], ignore_index=True)
        return orders

    def _inject_post_conversion_touchpoints(self, touchpoints: pd.DataFrame, opportunities: pd.DataFrame) -> pd.DataFrame:
        """Modifies touchpoint timestamps to occur AFTER deal close date."""
        closed_opps = opportunities[opportunities["stage"] == "Closed Won"].copy()
        if len(closed_opps) == 0 or len(touchpoints) == 0:
            return touchpoints

        sample_opps = closed_opps.sample(n=min(len(closed_opps), 5), random_state=42)
        for _, opp in sample_opps.iterrows():
            opp_contact_id = opp["contact_id"]
            contact_touches = touchpoints[touchpoints["contact_id"] == opp_contact_id]
            if len(contact_touches) > 0:
                t_idx = contact_touches.index[-1]
                late_time = pd.to_datetime(opp["closed_at"]) + timedelta(days=self.rng.randint(2, 20))
                touch_id = touchpoints.loc[t_idx, "touchpoint_id"]
                touchpoints.loc[t_idx, "timestamp"] = late_time.strftime("%Y-%m-%d %H:%M:%S")

                self.ground_truth_records.append({
                    "anomaly_id": f"ANO-POST-TOUCH-{len(self.ground_truth_records) + 1:04d}",
                    "issue_type": "TOUCHPOINT_AFTER_CONVERSION_ATTRIBUTED",
                    "entity": "Touchpoint",
                    "record_id": touch_id,
                    "related_parent_id": opp["opportunity_id"],
                    "description": f"Touchpoint {touch_id} occurred at {late_time} which is after opportunity {opp['opportunity_id']} closed at {opp['closed_at']}.",
                    "expected_handling": "Filter out touchpoints where timestamp > opportunity.closed_at during attribution weighting."
                })
        return touchpoints

    def _inject_spend_currency_mismatch(self, costs: pd.DataFrame) -> pd.DataFrame:
        """Injects non-USD currency spend without FX tagging / rate normalization."""
        non_usd = costs[costs["currency"].isin(["EUR", "GBP"])]
        if len(non_usd) == 0:
            return costs

        sample_indices = non_usd.sample(n=min(len(non_usd), 4), random_state=42).index
        for idx in sample_indices:
            cid = costs.loc[idx, "cost_record_id"]
            orig_currency = costs.loc[idx, "currency"]
            # Intentionally flip currency flag or leave unadjusted
            costs.loc[idx, "cost_category"] = "Media Spend (Unconverted Foreign Currency)"
            self.ground_truth_records.append({
                "anomaly_id": f"ANO-CURR-MISMATCH-{len(self.ground_truth_records) + 1:04d}",
                "issue_type": "SPEND_CURRENCY_MISMATCH",
                "entity": "CostRecord",
                "record_id": cid,
                "related_parent_id": costs.loc[idx, "campaign_id"],
                "description": f"Cost record {cid} recorded in {orig_currency} ({costs.loc[idx, 'spend_amount']}) without automated FX normalization to USD reporting base.",
                "expected_handling": "Convert spend_amount to USD using historical or configured exchange rate before computing campaign ROI."
            })
        return costs

    def _inject_omitted_campaign_costs(
        self,
        costs: pd.DataFrame,
        campaigns: pd.DataFrame,
        touchpoints: pd.DataFrame,
        orders: pd.DataFrame
    ) -> pd.DataFrame:
        """Omits cost records for an active campaign that generated revenue, artificially inflating its ROI."""
        # Find active campaigns that have touchpoints
        active_camps = touchpoints["campaign_id"].unique()
        if len(active_camps) == 0:
            return costs

        target_camp = active_camps[0]
        # Drop cost records for this campaign
        dropped_records = costs[costs["campaign_id"] == target_camp]
        costs = costs[costs["campaign_id"] != target_camp].copy()

        self.ground_truth_records.append({
            "anomaly_id": f"ANO-OMITTED-COST-{len(self.ground_truth_records) + 1:04d}",
            "issue_type": "CAMPAIGN_COSTS_OMITTED",
            "entity": "CostRecord",
            "record_id": f"CAMP-COST-OMITTED-{target_camp}",
            "related_parent_id": target_camp,
            "description": f"Campaign {target_camp} has valid touchpoints and pipeline generation but all cost records ({len(dropped_records)} dropped) were omitted.",
            "expected_handling": "Flag campaign as having missing cost data (Cost = $0.00 / NaN) and alert operator before ROI calculation."
        })
        return costs

    def _inject_unsubstantiated_session_link(self, sessions: pd.DataFrame, contacts: pd.DataFrame) -> pd.DataFrame:
        """Attaches a random contact_id to an anonymous web session without matching cookie/evidence."""
        if len(sessions) == 0 or len(contacts) == 0:
            return sessions

        # Find anonymous sessions (contact_id is None)
        anon_sessions = sessions[sessions["contact_id"].isna() | (sessions["contact_id"] == "")].index
        if len(anon_sessions) == 0:
            anon_sessions = sessions.index[:2]

        sample_idx = anon_sessions[0]
        random_contact = contacts.iloc[self.rng.randint(0, len(contacts))]["contact_id"]
        sess_id = sessions.loc[sample_idx, "session_id"]
        sessions.loc[sample_idx, "contact_id"] = random_contact
        sessions.loc[sample_idx, "cookie_id"] = f"ck_anon_{sample_idx:07d}"

        self.ground_truth_records.append({
            "anomaly_id": f"ANO-ANON-LINK-{len(self.ground_truth_records) + 1:04d}",
            "issue_type": "ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE",
            "entity": "WebSession",
            "record_id": sess_id,
            "related_parent_id": random_contact,
            "description": f"WebSession {sess_id} was forcefully stitched to Contact {random_contact} with zero cookie correlation or form submission event.",
            "expected_handling": "Validate identity graph edges against verified authentication or cookie-binding events; reject unsubstantiated links."
        })
        return sessions
