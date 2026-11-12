
"""
Deterministic Synthetic Data Generator for Multi-Touch Attribution Engine.

Supports parameterized scale (starter, medium, full) with deterministic seeds.

ID naming conventions:
- CMP-2026-000001
- TOUCH-<contact-id>-000001
- SES-2026-000001
- LEAD-2026-000001
- OPP-2026-000001
- ORD-2026-000001
- CST-2026-000001
- CNT-2026-000001
"""

import random
import hashlib
import numpy as np
import pandas as pd

from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.config import DEFAULT_SEED, SCALE_CONFIGS
from src.generator.anomalies import AnomalyInjector


class SyntheticDataGenerator:

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        scale: str = "starter"
    ):
        self.seed = seed
        self.scale_cfg = SCALE_CONFIGS.get(
            scale,
            SCALE_CONFIGS["starter"]
        )

        self.random = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        self.base_start_date = datetime(2026, 1, 1, 8, 0, 0)
        self.base_end_date = datetime(2026, 12, 31, 20, 0, 0)

    # =====================================================
    # MAIN DATA GENERATION PIPELINE
    # =====================================================

    def generate(
        self,
        inject_anomalies: bool = True
    ) -> Dict[str, pd.DataFrame]:

        """
        Generates the complete relational dataset.
        """

        # Step 1: Master data
        channels_df = self._generate_channels()
        audiences_df = self._generate_audiences()

        campaigns_df = self._generate_campaigns(
            channels_df,
            audiences_df
        )

        creatives_df = self._generate_creatives(
            campaigns_df
        )

        contacts_df = self._generate_contacts()

        # Step 2: Events
        sessions_df = self._generate_web_sessions(
            contacts_df,
            channels_df
        )

        touchpoints_df = self._generate_touchpoints(
            contacts_df,
            campaigns_df,
            channels_df,
            creatives_df,
            sessions_df
        )

        # Step 3: Leads and conversions
        leads_df = self._generate_leads(
            contacts_df,
            touchpoints_df,
            sessions_df
        )

        opportunities_df = self._generate_opportunities(
            contacts_df,
            leads_df
        )

        orders_df = self._generate_orders(
            opportunities_df
        )

        costs_df = self._generate_cost_records(
            campaigns_df
        )

        # Step 4: Inject labelled anomalies
        ground_truth: List[Dict[str, Any]] = []

        if inject_anomalies:

            injector = AnomalyInjector(self.random)

            (
                campaigns_df,
                contacts_df,
                touchpoints_df,
                sessions_df,
                opportunities_df,
                orders_df,
                costs_df,
                ground_truth
            ) = injector.inject_all(
                campaigns_df,
                contacts_df,
                touchpoints_df,
                sessions_df,
                opportunities_df,
                orders_df,
                costs_df
            )

        return {
            "channels": channels_df,
            "audiences": audiences_df,
            "campaigns": campaigns_df,
            "creatives": creatives_df,
            "contacts": contacts_df,
            "web_sessions": sessions_df,
            "touchpoints": touchpoints_df,
            "leads": leads_df,
            "opportunities": opportunities_df,
            "orders": orders_df,
            "cost_records": costs_df,
            "ground_truth": ground_truth
        }

    # =====================================================
    # CHANNEL GENERATION
    # =====================================================

    def _generate_channels(self) -> pd.DataFrame:

        channels_data = [
            {
                "channel_id": "CHN-001",
                "channel_name": "Paid Search",
                "channel_type": "Paid",
                "is_paid": True,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-002",
                "channel_name": "Paid Social",
                "channel_type": "Paid",
                "is_paid": True,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-003",
                "channel_name": "Organic Search",
                "channel_type": "Organic",
                "is_paid": False,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-004",
                "channel_name": "Email",
                "channel_type": "Outbound",
                "is_paid": False,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-005",
                "channel_name": "Display",
                "channel_type": "Paid",
                "is_paid": True,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-006",
                "channel_name": "Events/Conferences",
                "channel_type": "Outbound",
                "is_paid": True,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-007",
                "channel_name": "Direct",
                "channel_type": "Inbound",
                "is_paid": False,
                "created_at": "2026-01-01 00:00:00"
            },
            {
                "channel_id": "CHN-008",
                "channel_name": "Referral",
                "channel_type": "Inbound",
                "is_paid": False,
                "created_at": "2026-01-01 00:00:00"
            }
        ]

        return pd.DataFrame(channels_data)

    # =====================================================
    # AUDIENCE GENERATION
    # =====================================================

    def _generate_audiences(self) -> pd.DataFrame:

        audiences = []

        industries = [
            "Technology",
            "Healthcare",
            "Financial Services",
            "Manufacturing",
            "Retail",
            "Education"
        ]

        tiers = [
            "Enterprise",
            "Mid-Market",
            "SMB"
        ]

        personas = [
            "CTO/VP Eng",
            "CMO/VP Mktg",
            "CFO/Finance",
            "Operations Lead",
            "Security Lead"
        ]

        num_audiences = max(
            6,
            self.scale_cfg.num_campaigns // 5
        )

        for i in range(1, num_audiences + 1):

            aud_id = f"AUD-2026-{i:06d}"

            industry = industries[
                (i - 1) % len(industries)
            ]

            tier = tiers[
                (i - 1) % len(tiers)
            ]

            persona = personas[
                (i - 1) % len(personas)
            ]

            audiences.append({
                "audience_id": aud_id,
                "audience_name": f"{industry} {tier} {persona}",
                "industry": industry,
                "tier": tier,
                "target_persona": persona,
                "created_at": "2026-01-01 00:00:00"
            })

        return pd.DataFrame(audiences)

    # =====================================================
    # CAMPAIGN GENERATION
    # =====================================================

    def _generate_campaigns(
        self,
        channels_df: pd.DataFrame,
        audiences_df: pd.DataFrame
    ) -> pd.DataFrame:

        campaigns = []

        c_ids = channels_df["channel_id"].tolist()
        a_ids = audiences_df["audience_id"].tolist()

        currencies = [
            "USD",
            "USD",
            "USD",
            "EUR",
            "GBP"
        ]

        for i in range(
            1,
            self.scale_cfg.num_campaigns + 1
        ):

            camp_id = f"CMP-2026-{i:06d}"

            channel_id = self.random.choice(c_ids)
            aud_id = self.random.choice(a_ids)

            start_offset = self.random.randint(0, 90)

            camp_start = (
                self.base_start_date
                + timedelta(days=start_offset)
            )

            camp_duration = self.random.randint(60, 240)

            camp_end = (
                camp_start
                + timedelta(days=camp_duration)
            )

            budget = round(
                float(
                    self.random.choice([
                        5000,
                        10000,
                        25000,
                        50000,
                        100000,
                        200000
                    ])
                ),
                2
            )

            campaigns.append({
                "campaign_id": camp_id,
                "campaign_name": (
                    f"Campaign_{channel_id}_{aud_id[-4:]}_{i}"
                ),
                "channel_id": channel_id,
                "audience_id": aud_id,
                "budget": budget,
                "currency": self.random.choice(currencies),
                "status": (
                    "Active"
                    if camp_end > datetime(2026, 9, 1)
                    else "Completed"
                ),
                "start_date": camp_start.strftime("%Y-%m-%d"),
                "end_date": camp_end.strftime("%Y-%m-%d")
            })

        return pd.DataFrame(campaigns)

    # =====================================================
    # CREATIVE GENERATION
    # =====================================================

    def _generate_creatives(
        self,
        campaigns_df: pd.DataFrame
    ) -> pd.DataFrame:

        creatives = []

        types = [
            "Video",
            "Static Banner",
            "Whitepaper",
            "Webinar",
            "Text Ad",
            "Case Study"
        ]

        ctas = [
            "Book Demo",
            "Download Now",
            "Start Free Trial",
            "Contact Sales",
            "Learn More"
        ]

        crt_counter = 1

        for _, camp in campaigns_df.iterrows():

            n_creatives = self.random.randint(2, 4)

            for _ in range(n_creatives):

                crt_id = f"CRT-2026-{crt_counter:06d}"

                asset = self.random.choice(types)

                creatives.append({
                    "creative_id": crt_id,
                    "campaign_id": camp["campaign_id"],
                    "asset_type": asset,
                    "headline": (
                        f"{asset} for {camp['campaign_name']}"
                    ),
                    "call_to_action": self.random.choice(ctas),
                    "created_at": (
                        f"{camp['start_date']} 09:00:00"
                    )
                })

                crt_counter += 1

        return pd.DataFrame(creatives)

    # =====================================================
    # CONTACT GENERATION
    # =====================================================

    def _generate_contacts(self) -> pd.DataFrame:

        contacts = []

        first_names = [
            "Alex", "Jordan", "Taylor", "Morgan",
            "Sam", "Chris", "Pat", "Riley",
            "Casey", "Avery", "Jamie", "Logan",
            "Elena", "Marcus", "Priya", "Carlos"
        ]

        last_names = [
            "Smith", "Johnson", "Williams", "Brown",
            "Jones", "Miller", "Davis", "Garcia",
            "Rodriguez", "Wilson", "Chen", "Patel",
            "Kumar", "Kim"
        ]

        companies = [
            "AcmeCorp", "ApexTech", "OmniGlobal",
            "VertexSystems", "QuantumDynamics",
            "StarlightMedia", "NimbusData",
            "Synthetix", "BlueFin", "SolarisCorp"
        ]

        roles = [
            "VP Marketing",
            "Head of Growth",
            "Director of IT",
            "Demand Gen Lead",
            "Chief Architect",
            "Procurement Manager",
            "CRO"
        ]

        stages = [
            "Visitor",
            "Lead",
            "MQL",
            "SQL",
            "Opportunity",
            "Customer"
        ]

        for i in range(
            1,
            self.scale_cfg.num_contacts + 1
        ):

            cnt_id = f"CNT-2026-{i:06d}"

            fn = self.random.choice(first_names)
            ln = self.random.choice(last_names)
            comp = self.random.choice(companies)

            created_offset = self.random.randint(0, 180)

            created_at = (
                self.base_start_date
                + timedelta(
                    days=created_offset,
                    hours=self.random.randint(0, 23)
                )
            )

            contacts.append({
                "contact_id": cnt_id,
                "email": (
                    f"{fn.lower()}.{ln.lower()}_{i}"
                    f"@{comp.lower()}.com"
                ),
                "first_name": fn,
                "last_name": ln,
                "company_name": comp,
                "job_role": self.random.choice(roles),
                "lifecycle_stage": self.random.choice(stages),
                "created_at": created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            })

        return pd.DataFrame(contacts)

    # =====================================================
    # WEB SESSION GENERATION
    # =====================================================

    def _generate_web_sessions(
        self,
        contacts_df: pd.DataFrame,
        channels_df: pd.DataFrame
    ) -> pd.DataFrame:

        sessions = []

        c_ids = channels_df["channel_id"].tolist()
        contact_ids = contacts_df["contact_id"].tolist()

        num_sessions = max(
            len(contacts_df) * 3,
            self.scale_cfg.num_touchpoints
        )

        evidence_types = [
            "AUTHENTICATED_LOGIN",
            "VERIFIED_COOKIE_BINDING",
            "FORM_SUBMISSION"
        ]

        for i in range(1, num_sessions + 1):

            ses_id = f"SES-2026-{i:06d}"

            # 70% identified and 30% anonymous
            is_identified = (
                self.random.random() < 0.70
            )

            contact_id = (
                self.random.choice(contact_ids)
                if is_identified
                else None
            )

            # Generate deterministic cookie ID
            cookie_source = (
                contact_id
                if contact_id
                else f"anon_{i}"
            )

            cookie_hash = hashlib.sha256(
                cookie_source.encode("utf-8")
            ).hexdigest()[:8]

            cookie_id = f"ck_{cookie_hash}"

            # Add identity evidence
            if is_identified:

                identity_evidence_type = (
                    self.random.choice(evidence_types)
                )

                identity_verified = True

            else:

                identity_evidence_type = "NONE"
                identity_verified = False

            ch_id = self.random.choice(c_ids)

            sess_offset = self.random.randint(0, 300)

            s_start = (
                self.base_start_date
                + timedelta(
                    days=sess_offset,
                    minutes=self.random.randint(0, 1440)
                )
            )

            duration = self.random.randint(30, 1800)

            s_end = s_start + timedelta(
                seconds=duration
            )

            sessions.append({
                "session_id": ses_id,
                "cookie_id": cookie_id,
                "contact_id": contact_id,
                "channel_id": ch_id,
                "landing_page": (
                    f"/solutions/{self.random.choice([
                        'enterprise',
                        'pricing',
                        'product',
                        'whitepaper',
                        'roi-calculator'
                    ])}"
                ),
                "page_views": self.random.randint(1, 15),
                "duration_seconds": duration,
                "device_type": self.random.choice([
                    "Desktop",
                    "Mobile",
                    "Tablet"
                ]),
                "started_at": s_start.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "ended_at": s_end.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "identity_evidence_type": identity_evidence_type,
                "identity_verified": identity_verified
            })

        return pd.DataFrame(sessions)

    # =====================================================
    # TOUCHPOINT GENERATION
    # =====================================================

    def _generate_touchpoints(
        self,
        contacts_df: pd.DataFrame,
        campaigns_df: pd.DataFrame,
        channels_df: pd.DataFrame,
        creatives_df: pd.DataFrame,
        sessions_df: pd.DataFrame
    ) -> pd.DataFrame:

        touchpoints = []

        interaction_types = [
            "Ad Click",
            "Email Open",
            "Email Click",
            "Content Download",
            "Webinar Attended",
            "Conference Meeting",
            "Product Demo",
            "Direct Visit"
        ]

        contacts = contacts_df.to_dict("records")
        campaign_records = campaigns_df.to_dict("records")

        creatives_by_camp = (
            creatives_df.groupby("campaign_id")[
                "creative_id"
            ].apply(list).to_dict()
        )

        sessions_by_contact = (
            sessions_df.dropna(subset=["contact_id"])
            .groupby("contact_id")["session_id"]
            .apply(list)
            .to_dict()
        )

        target_total = self.scale_cfg.num_touchpoints

        avg_touches_per_contact = max(
            2,
            target_total // len(contacts)
        )

        for cnt in contacts:

            cnt_id = cnt["contact_id"]

            cnt_created = datetime.strptime(
                cnt["created_at"],
                "%Y-%m-%d %H:%M:%S"
            )

            # Generate 2 to 8 touches per contact journey
            n_touches = self.random.randint(
                max(1, avg_touches_per_contact - 2),
                avg_touches_per_contact + 3
            )

            cur_time = cnt_created

            for seq in range(1, n_touches + 1):

                touch_id = (
                    f"TOUCH-{cnt_id}-{seq:06d}"
                )

                camp = self.random.choice(
                    campaign_records
                )

                c_id = camp["campaign_id"]
                ch_id = camp["channel_id"]

                # Link creative
                camp_crts = creatives_by_camp.get(
                    c_id,
                    []
                )

                crt_id = (
                    self.random.choice(camp_crts)
                    if camp_crts
                    else None
                )

                # Link session
                cnt_sessions = sessions_by_contact.get(
                    cnt_id,
                    []
                )

                ses_id = (
                    self.random.choice(cnt_sessions)
                    if cnt_sessions
                    and self.random.random() < 0.6
                    else None
                )

                itype = self.random.choice(
                    interaction_types
                )

                is_offline = itype in [
                    "Conference Meeting",
                    "Product Demo"
                ]

                cost = round(
                    float(
                        self.random.uniform(
                            80.0,
                            450.0
                        )
                        if is_offline
                        else self.random.uniform(
                            1.5,
                            45.0
                        )
                    ),
                    2
                )

                # Advance time between touchpoints
                cur_time += timedelta(
                    days=self.random.randint(1, 25),
                    hours=self.random.randint(1, 12)
                )

                touchpoints.append({
                    "touchpoint_id": touch_id,
                    "contact_id": cnt_id,
                    "campaign_id": c_id,
                    "channel_id": ch_id,
                    "creative_id": crt_id,
                    "session_id": ses_id,
                    "interaction_type": itype,
                    "medium": (
                        "Offline"
                        if is_offline
                        else "Online"
                    ),
                    "touchpoint_cost": cost,
                    "timestamp": cur_time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                })

                if len(touchpoints) >= target_total:
                    break

            if len(touchpoints) >= target_total:
                break

        return pd.DataFrame(touchpoints)

    # =====================================================
    # LEAD GENERATION
    # =====================================================

    def _generate_leads(
        self,
        contacts_df: pd.DataFrame,
        touchpoints_df: pd.DataFrame,
        sessions_df: pd.DataFrame
    ) -> pd.DataFrame:

        leads = []

        if touchpoints_df.empty:
            return pd.DataFrame(columns=[
                "lead_id",
                "contact_id",
                "first_touchpoint_id",
                "session_id",
                "lead_score",
                "status",
                "created_at"
            ])

        touches_by_contact = (
            touchpoints_df.groupby("contact_id")
        )

        # Only sessions with valid identity evidence
        valid_sessions = sessions_df[
            sessions_df["identity_verified"].eq(True)
            & sessions_df["identity_evidence_type"].isin([
                "AUTHENTICATED_LOGIN",
                "VERIFIED_COOKIE_BINDING",
                "FORM_SUBMISSION"
            ])
            & sessions_df["contact_id"].notna()
        ]

        session_lookup = (
            valid_sessions
            .set_index("session_id")["contact_id"]
            .to_dict()
        )

        lead_counter = 1

        for _, cnt in contacts_df.iterrows():

            cnt_id = cnt["contact_id"]

            if cnt_id not in touches_by_contact.groups:
                continue

            contact_touches = (
                touches_by_contact
                .get_group(cnt_id)
                .sort_values("timestamp")
            )

            first_touch = contact_touches.iloc[0]

            session_id = first_touch["session_id"]

            # Validate session-contact relationship
            if pd.notna(session_id):

                verified_contact = session_lookup.get(
                    session_id
                )

                if verified_contact != cnt_id:
                    session_id = None

            else:
                session_id = None

            lead_id = (
                f"LEAD-2026-{lead_counter:06d}"
            )

            lead_created = (
                datetime.strptime(
                    first_touch["timestamp"],
                    "%Y-%m-%d %H:%M:%S"
                )
                + timedelta(
                    hours=self.random.randint(1, 48)
                )
            )

            leads.append({
                "lead_id": lead_id,
                "contact_id": cnt_id,
                "first_touchpoint_id": first_touch[
                    "touchpoint_id"
                ],
                "session_id": session_id,
                "lead_score": self.random.randint(20, 99),
                "status": self.random.choice([
                    "Open",
                    "Contacted",
                    "Qualified",
                    "Converted"
                ]),
                "created_at": lead_created.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            })

            lead_counter += 1

        return pd.DataFrame(leads)

    # =====================================================
    # OPPORTUNITY GENERATION
    # =====================================================

    def _generate_opportunities(
        self,
        contacts_df: pd.DataFrame,
        leads_df: pd.DataFrame
    ) -> pd.DataFrame:

        opportunities = []

        if leads_df.empty:
            return pd.DataFrame(columns=[
                "opportunity_id",
                "contact_id",
                "lead_id",
                "opportunity_name",
                "stage",
                "amount",
                "currency",
                "created_at",
                "closed_at"
            ])

        num_opps = min(
            self.scale_cfg.num_opportunities,
            len(leads_df)
        )

        sampled_leads = leads_df.sample(
            n=num_opps,
            random_state=self.seed
        ).to_dict("records")

        stages = [
            "Discovery",
            "Validation",
            "Proposal",
            "Negotiation",
            "Closed Won",
            "Closed Lost"
        ]

        stage_weights = [
            0.15,
            0.15,
            0.15,
            0.15,
            0.25,
            0.15
        ]

        currencies = [
            "USD",
            "USD",
            "USD",
            "EUR",
            "GBP"
        ]

        for i, lead in enumerate(
            sampled_leads,
            start=1
        ):

            opp_id = f"OPP-2026-{i:06d}"

            lead_created = datetime.strptime(
                lead["created_at"],
                "%Y-%m-%d %H:%M:%S"
            )

            opp_created = (
                lead_created
                + timedelta(
                    days=self.random.randint(2, 20)
                )
            )

            stage = self.random.choices(
                stages,
                weights=stage_weights,
                k=1
            )[0]

            amount = round(
                float(
                    self.random.choice([
                        12000,
                        25000,
                        48000,
                        85000,
                        150000,
                        320000
                    ])
                ),
                2
            )

            currency = self.random.choice(
                currencies
            )

            closed_at = None

            if stage in [
                "Closed Won",
                "Closed Lost"
            ]:

                close_dt = (
                    opp_created
                    + timedelta(
                        days=self.random.randint(15, 90)
                    )
                )

                closed_at = close_dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            opportunities.append({
                "opportunity_id": opp_id,
                "contact_id": lead["contact_id"],
                "lead_id": lead["lead_id"],
                "opportunity_name": (
                    f"Deal_{opp_id[-6:]}_{stage}"
                ),
                "stage": stage,
                "amount": amount,
                "currency": currency,
                "created_at": opp_created.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "closed_at": closed_at
            })

        return pd.DataFrame(opportunities)

    # =====================================================
    # ORDER GENERATION
    # =====================================================

    def _generate_orders(
        self,
        opportunities_df: pd.DataFrame
    ) -> pd.DataFrame:

        orders = []

        if opportunities_df.empty:
            return pd.DataFrame(columns=[
                "order_id",
                "opportunity_id",
                "contact_id",
                "order_date",
                "gross_revenue",
                "currency",
                "status"
            ])

        won_opps = opportunities_df[
            opportunities_df["stage"] == "Closed Won"
        ]

        for i, (_, opp) in enumerate(
            won_opps.iterrows(),
            start=1
        ):

            order_id = f"ORD-2026-{i:06d}"

            order_date = (
                datetime.strptime(
                    opp["closed_at"],
                    "%Y-%m-%d %H:%M:%S"
                )
                + timedelta(
                    hours=self.random.randint(1, 24)
                )
            )

            orders.append({
                "order_id": order_id,
                "opportunity_id": opp["opportunity_id"],
                "contact_id": opp["contact_id"],
                "order_date": order_date.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "gross_revenue": opp["amount"],
                "currency": opp["currency"],
                "status": "Completed"
            })

        return pd.DataFrame(orders)

    # =====================================================
    # COST RECORD GENERATION
    # =====================================================

    def _generate_cost_records(
        self,
        campaigns_df: pd.DataFrame
    ) -> pd.DataFrame:

        cost_records = []

        categories = [
            "Media Spend",
            "Agency Fee",
            "Software Tool",
            "Sponsorship",
            "Production"
        ]

        cst_counter = 1

        for _, camp in campaigns_df.iterrows():

            c_id = camp["campaign_id"]
            ch_id = camp["channel_id"]

            budget = float(camp["budget"])
            curr = camp["currency"]

            start_dt = datetime.strptime(
                camp["start_date"],
                "%Y-%m-%d"
            )

            # Divide budget into 3 to 6 cost records
            n_entries = self.random.randint(3, 6)

            per_entry_spend = round(
                budget / n_entries,
                2
            )

            remaining_budget = budget

            for j in range(n_entries):

                cst_id = (
                    f"CST-2026-{cst_counter:06d}"
                )

                sp_date = (
                    start_dt
                    + timedelta(days=j * 30)
                )

                # Adjust final record for rounding
                if j == n_entries - 1:

                    spend_amount = round(
                        remaining_budget,
                        2
                    )

                else:

                    spend_amount = per_entry_spend

                remaining_budget -= spend_amount

                cost_records.append({
                    "cost_record_id": cst_id,
                    "campaign_id": c_id,
                    "channel_id": ch_id,
                    "spend_date": sp_date.strftime(
                        "%Y-%m-%d"
                    ),
                    "spend_amount": spend_amount,
                    "currency": curr,
                    "cost_category": self.random.choice(
                        categories
                    )
                })

                cst_counter += 1

        return pd.DataFrame(cost_records)
