"""
Identity Resolution, Verification, and Customer Journey Reconstruction Engine.
Reconstructs unified chronological timelines per contact and opportunity across:
- Web Sessions (Anonymous and Identified)
- Marketing Touchpoints (Online and Offline)
- Lead Capture Events
- Opportunity Pipeline Transitions
- Closed-Won Orders

Performs rigorous identity verification:
- Validates identity_verified flag (must be True)
- Validates identity_evidence_type (rejects NONE evidence)
- Validates linked contact exists in master registry
- Rejects unsubstantiated or unverified identity links and records audit events
- Updates internal graph sessions to verified state
"""
from typing import Dict, List, Any, Tuple
import pandas as pd
from datetime import datetime

class IdentityGraph:
    def __init__(
        self,
        contacts_df: pd.DataFrame,
        touchpoints_df: pd.DataFrame,
        sessions_df: pd.DataFrame,
        opportunities_df: pd.DataFrame,
        orders_df: pd.DataFrame
    ):
        self.contacts = contacts_df.copy()
        self.touchpoints = touchpoints_df.copy()
        self.sessions = sessions_df.copy()
        self.opportunities = opportunities_df.copy()
        self.orders = orders_df.copy()

        # Parse datetime columns
        self.touchpoints["timestamp_dt"] = pd.to_datetime(self.touchpoints["timestamp"])
        self.sessions["started_at_dt"] = pd.to_datetime(self.sessions["started_at"])
        self.opportunities["created_at_dt"] = pd.to_datetime(self.opportunities["created_at"])
        if "closed_at" in self.opportunities.columns:
            self.opportunities["closed_at_dt"] = pd.to_datetime(self.opportunities["closed_at"])
        else:
            self.opportunities["closed_at_dt"] = None

    def verify_identity_links(self) -> Tuple[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Verifies identity resolution edges between WebSessions and Contacts:
        1. Validates identity_verified is True.
        2. Validates identity_evidence_type is not 'NONE' or empty.
        3. Checks that the linked contact actually exists in master Contacts.
        4. Rejects sessions with NONE evidence or invalid links, records audit events,
           and updates self.sessions.
        """
        audit_log: List[Dict[str, Any]] = []
        verified_sessions = self.sessions.copy()
        valid_contact_ids = set(self.contacts["contact_id"].dropna().unique())

        rejected_mask = []
        for idx, row in verified_sessions.iterrows():
            cid = row.get("contact_id")
            session_id = row.get("session_id")
            cookie = str(row.get("cookie_id", ""))
            evidence_type = str(row.get("identity_evidence_type", "")).upper().strip()
            is_verified = bool(row.get("identity_verified", False))

            is_rejected = False
            rejection_reason = ""

            # Only evaluate sessions claiming a contact link
            if pd.notna(cid) and str(cid).strip() != "" and str(cid).upper() != "NONE":
                # Check 1: Linked contact must exist in master Contact entity
                if str(cid) not in valid_contact_ids:
                    is_rejected = True
                    rejection_reason = f"Linked contact_id '{cid}' does not exist in master Contacts registry."

                # Check 2: Reject sessions with NONE evidence type
                elif evidence_type in ["NONE", "", "NAN", "NULL"]:
                    is_rejected = True
                    rejection_reason = f"Session linked to contact {cid} with identity_evidence_type='NONE'."

                # Check 3: Validate identity_verified flag
                elif not is_verified:
                    is_rejected = True
                    rejection_reason = f"Session linked to contact {cid} has identity_verified=False."

                # Check 4: Unsubstantiated anonymous cookie check
                elif "anon_" in cookie:
                    is_rejected = True
                    rejection_reason = f"Session linked to contact {cid} carries unverified anonymous cookie '{cookie}'."

            if is_rejected:
                rejected_mask.append(True)
                audit_log.append({
                    "audit_id": f"AUD-IDENTITY-{len(audit_log)+1:04d}",
                    "issue_type": "ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE",
                    "entity": "WebSession",
                    "record_id": session_id,
                    "related_parent_id": str(cid),
                    "description": f"Rejected identity link for WebSession {session_id}: {rejection_reason}",
                    "action_taken": "Severed unsubstantiated identity edge; reset contact_id to None and marked evidence as NONE."
                })
            else:
                rejected_mask.append(False)

        # Sever rejected links
        verified_sessions.loc[rejected_mask, "contact_id"] = None
        verified_sessions.loc[rejected_mask, "identity_verified"] = False
        verified_sessions.loc[rejected_mask, "identity_evidence_type"] = "NONE"

        # Update internal graph sessions so all downstream processing uses verified state
        self.sessions = verified_sessions
        self.sessions["started_at_dt"] = pd.to_datetime(self.sessions["started_at"])

        # Identify missing identity links (high-intent traffic that remained anonymous)
        anonymous_sessions = verified_sessions[
            verified_sessions["contact_id"].isna() | (verified_sessions["contact_id"] == "")
        ]
        high_intent_missing = anonymous_sessions[
            anonymous_sessions["landing_page"].str.contains("pricing|roi|enterprise", case=False, na=False)
        ]

        stats = {
            "total_sessions": len(verified_sessions),
            "identified_sessions": len(verified_sessions) - len(anonymous_sessions),
            "anonymous_sessions": len(anonymous_sessions),
            "high_intent_missing_identity_links": len(high_intent_missing),
            "unsubstantiated_links_flagged": sum(rejected_mask)
        }

        return verified_sessions, audit_log, stats

    def get_valid_journey(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Reconstructs the end-to-end customer journey for an opportunity using verified sessions:
        - Touchpoints (online & offline)
        - Web sessions
        - Temporal boundary filtering (excludes touches after deal close date)
        """
        opp_rows = self.opportunities[self.opportunities["opportunity_id"] == opportunity_id]
        if opp_rows.empty:
            return {"opportunity": None, "valid_touches": [], "excluded_touches": [], "timeline": []}

        opp = opp_rows.iloc[0].to_dict()
        contact_id = opp["contact_id"]
        close_dt = opp.get("closed_at_dt")
        create_dt = opp.get("created_at_dt")

        # Contact touchpoints
        cnt_touches = self.touchpoints[self.touchpoints["contact_id"] == contact_id].sort_values("timestamp_dt")
        
        valid_touches = []
        excluded_touches = []
        timeline_events = []

        # 1. Add verified Web Sessions to timeline
        cnt_sessions = self.sessions[self.sessions["contact_id"] == contact_id].sort_values("started_at_dt")
        for _, sess in cnt_sessions.iterrows():
            timeline_events.append({
                "event_type": "WEB_SESSION",
                "event_id": sess["session_id"],
                "timestamp": sess["started_at"],
                "channel_id": sess["channel_id"],
                "details": f"Page views: {sess['page_views']}, Landing: {sess['landing_page']} (Evidence: {sess.get('identity_evidence_type', 'VERIFIED')})"
            })

        # 2. Add Touchpoints
        for _, touch in cnt_touches.iterrows():
            t_dict = touch.to_dict()
            t_time = touch["timestamp_dt"]

            # Anomaly rule: touchpoint occurred AFTER deal closed
            if pd.notna(close_dt) and t_time > close_dt:
                t_dict["exclusion_reason"] = "TOUCHPOINT_AFTER_CONVERSION"
                excluded_touches.append(t_dict)
                timeline_events.append({
                    "event_type": "TOUCHPOINT_EXCLUDED_POST_CLOSE",
                    "event_id": touch["touchpoint_id"],
                    "timestamp": touch["timestamp"],
                    "channel_id": touch["channel_id"],
                    "details": f"{touch['interaction_type']} ({touch['medium']}) - Excluded: After Deal Close"
                })
            else:
                valid_touches.append(t_dict)
                timeline_events.append({
                    "event_type": "TOUCHPOINT_VALID",
                    "event_id": touch["touchpoint_id"],
                    "timestamp": touch["timestamp"],
                    "channel_id": touch["channel_id"],
                    "details": f"{touch['interaction_type']} ({touch['medium']}) - Cost: ${touch['touchpoint_cost']:.2f}"
                })

        # 3. Add Opportunity Creation & Close
        timeline_events.append({
            "event_type": "OPPORTUNITY_CREATED",
            "event_id": opp["opportunity_id"],
            "timestamp": opp["created_at"],
            "channel_id": "N/A",
            "details": f"Stage: {opp['stage']}, Deal Size: ${opp['amount']:,.2f}"
        })

        if pd.notna(close_dt):
            timeline_events.append({
                "event_type": f"OPPORTUNITY_{opp['stage'].upper().replace(' ', '_')}",
                "event_id": opp["opportunity_id"],
                "timestamp": opp["closed_at"],
                "channel_id": "N/A",
                "details": f"Closed at: {opp['closed_at']}"
            })

        # Sort timeline chronologically
        timeline_events.sort(key=lambda x: str(x["timestamp"]))

        return {
            "opportunity": opp,
            "contact_id": contact_id,
            "closed_at": close_dt,
            "valid_touches": valid_touches,
            "excluded_touches": excluded_touches,
            "timeline": timeline_events
        }
