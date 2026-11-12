"""
Data Dictionary and Schema Definitions for Multi-Touch Attribution Engine.
Defines all 12 core entities:
1. Channel (Master)
2. Audience (Master)
3. Campaign (Master)
4. Creative (Master)
5. Contact (Master)
6. WebSession (Event)
7. Touchpoint (Event)
8. Lead (State/Transaction)
9. Opportunity (State/Transaction)
10. Order (State/Transaction/Revenue)
11. CostRecord (Cost/Financial)
12. AttributionResult (Analytical Output)
"""

DATA_DICTIONARY = {
    "Channel": {
        "description": "Marketing distribution channel definition",
        "primary_key": "channel_id",
        "cardinality": {
            "Campaign": "1:N (One channel hosts multiple campaigns)",
            "WebSession": "1:N (One channel refers multiple web sessions)",
            "Touchpoint": "1:N (One channel delivers multiple touchpoints)"
        },
        "lifecycle_states": ["Active", "Archived"],
        "fields": {
            "channel_id": {"type": "string", "required": True, "unique": True, "format": "CHN-###", "validation": r"^CHN-\d{3}$"},
            "channel_name": {"type": "string", "required": True, "allowed_values": ["Paid Search", "Paid Social", "Organic Search", "Email", "Display", "Events/Conferences", "Direct", "Referral"]},
            "channel_type": {"type": "string", "required": True, "allowed_values": ["Inbound", "Outbound", "Organic", "Paid"]},
            "is_paid": {"type": "boolean", "required": True},
            "created_at": {"type": "datetime", "required": True}
        }
    },
    "Audience": {
        "description": "Target audience segment definition",
        "primary_key": "audience_id",
        "cardinality": {
            "Campaign": "1:N (One audience segment targeted by multiple campaigns)"
        },
        "lifecycle_states": ["Active", "Inactive"],
        "fields": {
            "audience_id": {"type": "string", "required": True, "unique": True, "format": "AUD-2026-######", "validation": r"^AUD-2026-\d{6}$"},
            "audience_name": {"type": "string", "required": True},
            "industry": {"type": "string", "required": True, "allowed_values": ["Technology", "Healthcare", "Financial Services", "Manufacturing", "Retail", "Education"]},
            "tier": {"type": "string", "required": True, "allowed_values": ["Enterprise", "Mid-Market", "SMB"]},
            "target_persona": {"type": "string", "required": True, "allowed_values": ["CTO/VP Eng", "CMO/VP Mktg", "CFO/Finance", "Operations Lead", "Security Lead"]},
            "created_at": {"type": "datetime", "required": True}
        }
    },
    "Campaign": {
        "description": "Marketing campaign master record with budget, channel, and timeframe",
        "primary_key": "campaign_id",
        "foreign_keys": {
            "channel_id": "Channel.channel_id (Required)",
            "audience_id": "Audience.audience_id (Required)"
        },
        "cardinality": {
            "Channel": "N:1 (Belongs to one channel)",
            "Audience": "N:1 (Targets one audience)",
            "Creative": "1:N (Comprises multiple creatives)",
            "Touchpoint": "1:N (Drives multiple touchpoints)",
            "CostRecord": "1:N (Incurs multiple cost line items)"
        },
        "lifecycle_states": ["Active", "Completed", "Paused"],
        "effective_dates": "start_date to end_date (end_date >= start_date)",
        "fields": {
            "campaign_id": {"type": "string", "required": True, "unique": True, "format": "CMP-2026-######", "validation": r"^CMP-2026-\d{6}$"},
            "campaign_name": {"type": "string", "required": True},
            "channel_id": {"type": "string", "required": True},
            "audience_id": {"type": "string", "required": True},
            "budget": {"type": "float", "required": True, "unit": "currency", "min": 500.0},
            "currency": {"type": "string", "required": True, "allowed_values": ["USD", "EUR", "GBP"]},
            "status": {"type": "string", "required": True, "allowed_values": ["Active", "Completed", "Paused"]},
            "start_date": {"type": "date", "required": True},
            "end_date": {"type": "date", "required": True, "rule": "end_date >= start_date"}
        }
    },
    "Creative": {
        "description": "Advertising creative or content asset tied to a campaign",
        "primary_key": "creative_id",
        "foreign_keys": {
            "campaign_id": "Campaign.campaign_id (Required)"
        },
        "cardinality": {
            "Campaign": "N:1 (Belongs to one campaign)",
            "Touchpoint": "1:N (Associated with multiple touchpoints, optional)"
        },
        "lifecycle_states": ["Draft", "Live", "Retired"],
        "fields": {
            "creative_id": {"type": "string", "required": True, "unique": True, "format": "CRT-2026-######", "validation": r"^CRT-2026-\d{6}$"},
            "campaign_id": {"type": "string", "required": True},
            "asset_type": {"type": "string", "required": True, "allowed_values": ["Video", "Static Banner", "Whitepaper", "Webinar", "Text Ad", "Case Study"]},
            "headline": {"type": "string", "required": True},
            "call_to_action": {"type": "string", "required": True, "allowed_values": ["Book Demo", "Download Now", "Start Free Trial", "Contact Sales", "Learn More"]},
            "created_at": {"type": "datetime", "required": True}
        }
    },
    "Contact": {
        "description": "Prospective or existing customer master record",
        "primary_key": "contact_id",
        "cardinality": {
            "WebSession": "1:N (Executes multiple web sessions, optional)",
            "Touchpoint": "1:N (Participates in multiple touchpoints, mandatory)",
            "Lead": "1:N (Initiates leads)",
            "Opportunity": "1:N (Associated with multiple opportunities)",
            "Order": "1:N (Places multiple revenue orders)"
        },
        "lifecycle_states": ["Visitor", "Lead", "MQL", "SQL", "Opportunity", "Customer", "Churned"],
        "lifecycle_transitions": {
            "Visitor": ["Lead"],
            "Lead": ["MQL", "Churned"],
            "MQL": ["SQL", "Lead", "Churned"],
            "SQL": ["Opportunity", "MQL", "Churned"],
            "Opportunity": ["Customer", "Churned"],
            "Customer": ["Churned"],
            "Churned": ["Lead"]
        },
        "fields": {
            "contact_id": {"type": "string", "required": True, "unique": True, "format": "CNT-2026-######", "validation": r"^CNT-2026-\d{6}$"},
            "email": {"type": "string", "required": True, "unique": True},
            "first_name": {"type": "string", "required": True},
            "last_name": {"type": "string", "required": True},
            "company_name": {"type": "string", "required": True},
            "job_role": {"type": "string", "required": True},
            "lifecycle_stage": {"type": "string", "required": True, "allowed_values": ["Visitor", "Lead", "MQL", "SQL", "Opportunity", "Customer", "Churned"]},
            "created_at": {"type": "datetime", "required": True}
        }
    },
    "WebSession": {
        "description": "Web traffic session event, either anonymous or linked to contact",
        "primary_key": "session_id",
        "foreign_keys": {
            "contact_id": "Contact.contact_id (Optional/Nullable)",
            "channel_id": "Channel.channel_id (Required)"
        },
        "cardinality": {
            "Contact": "N:1 (Optionally resolved to one contact via cookie)",
            "Channel": "N:1 (Originated from one channel)",
            "Touchpoint": "1:1 (May generate a digital touchpoint)"
        },
        "fields": {
            "session_id": {"type": "string", "required": True, "unique": True, "format": "SES-2026-######", "validation": r"^SES-2026-\d{6}$"},
            "cookie_id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "required": False, "nullable": True},
            "channel_id": {"type": "string", "required": True},
            "landing_page": {"type": "string", "required": True},
            "page_views": {"type": "integer", "required": True, "min": 1},
            "duration_seconds": {"type": "integer", "required": True, "min": 0},
            "device_type": {"type": "string", "required": True, "allowed_values": ["Desktop", "Mobile", "Tablet"]},
            "started_at": {"type": "datetime", "required": True},
            "ended_at": {"type": "datetime", "required": True, "rule": "ended_at >= started_at"}
        }
    },
    "Touchpoint": {
        "description": "Marketing interaction event across digital or offline touchpoints",
        "primary_key": "touchpoint_id",
        "foreign_keys": {
            "contact_id": "Contact.contact_id (Required)",
            "campaign_id": "Campaign.campaign_id (Required)",
            "channel_id": "Channel.channel_id (Required)",
            "creative_id": "Creative.creative_id (Optional)",
            "session_id": "WebSession.session_id (Optional)"
        },
        "cardinality": {
            "Contact": "N:1 (Belongs to one contact)",
            "Campaign": "N:1 (Belongs to one campaign)",
            "Channel": "N:1 (Belongs to one channel)",
            "AttributionResult": "1:N (Attributed across 5 models)"
        },
        "fields": {
            "touchpoint_id": {"type": "string", "required": True, "unique": True, "format": "TOUCH-<contact-id>-######", "validation": r"^TOUCH-CNT-2026-\d{6}-\d{6}$"},
            "contact_id": {"type": "string", "required": True},
            "campaign_id": {"type": "string", "required": True},
            "channel_id": {"type": "string", "required": True},
            "creative_id": {"type": "string", "required": False, "nullable": True},
            "session_id": {"type": "string", "required": False, "nullable": True},
            "interaction_type": {"type": "string", "required": True, "allowed_values": ["Ad Click", "Email Open", "Email Click", "Content Download", "Webinar Attended", "Conference Meeting", "Product Demo", "Direct Visit"]},
            "medium": {"type": "string", "required": True, "allowed_values": ["Online", "Offline"]},
            "touchpoint_cost": {"type": "float", "required": True, "min": 0.0},
            "timestamp": {"type": "datetime", "required": True}
        }
    },
    "Lead": {
        "description": "Captured qualified marketing lead associated with a contact",
        "primary_key": "lead_id",
        "foreign_keys": {
            "contact_id": "Contact.contact_id (Required)",
            "first_touchpoint_id": "Touchpoint.touchpoint_id (Required)",
            "session_id": "WebSession.session_id (Optional)"
        },
        "cardinality": {
            "Contact": "N:1 (Belongs to one contact)",
            "Opportunity": "1:1 or 1:N (Converts to opportunities)"
        },
        "lifecycle_states": ["Open", "Contacted", "Qualified", "Unqualified", "Converted"],
        "lifecycle_transitions": {
            "Open": ["Contacted", "Unqualified"],
            "Contacted": ["Qualified", "Unqualified"],
            "Qualified": ["Converted", "Unqualified"],
            "Unqualified": ["Open"],
            "Converted": []
        },
        "fields": {
            "lead_id": {"type": "string", "required": True, "unique": True, "format": "LEAD-2026-######", "validation": r"^LEAD-2026-\d{6}$"},
            "contact_id": {"type": "string", "required": True},
            "first_touchpoint_id": {"type": "string", "required": True},
            "session_id": {"type": "string", "required": False, "nullable": True},
            "lead_score": {"type": "integer", "required": True, "min": 0, "max": 100},
            "status": {"type": "string", "required": True, "allowed_values": ["Open", "Contacted", "Qualified", "Unqualified", "Converted"]},
            "created_at": {"type": "datetime", "required": True}
        }
    },
    "Opportunity": {
        "description": "Sales pipeline deal progressing through stages to Won/Lost",
        "primary_key": "opportunity_id",
        "foreign_keys": {
            "contact_id": "Contact.contact_id (Required)",
            "lead_id": "Lead.lead_id (Required)"
        },
        "cardinality": {
            "Contact": "N:1 (Belongs to one contact)",
            "Lead": "N:1 (Converted from one lead)",
            "Order": "1:1 (Closed Won deal creates exactly one order)",
            "AttributionResult": "1:N (Attributed across 5 models)"
        },
        "lifecycle_states": ["Discovery", "Validation", "Proposal", "Negotiation", "Closed Won", "Closed Lost"],
        "lifecycle_transitions": {
            "Discovery": ["Validation", "Closed Lost"],
            "Validation": ["Proposal", "Closed Lost"],
            "Proposal": ["Negotiation", "Closed Lost"],
            "Negotiation": ["Closed Won", "Closed Lost"],
            "Closed Won": [],
            "Closed Lost": []
        },
        "fields": {
            "opportunity_id": {"type": "string", "required": True, "unique": True, "format": "OPP-2026-######", "validation": r"^OPP-2026-\d{6}$"},
            "contact_id": {"type": "string", "required": True},
            "lead_id": {"type": "string", "required": True},
            "opportunity_name": {"type": "string", "required": True},
            "stage": {"type": "string", "required": True, "allowed_values": ["Discovery", "Validation", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]},
            "amount": {"type": "float", "required": True, "min": 0.0},
            "currency": {"type": "string", "required": True, "allowed_values": ["USD", "EUR", "GBP"]},
            "created_at": {"type": "datetime", "required": True},
            "closed_at": {"type": "datetime", "required": False, "nullable": True, "rule": "closed_at >= created_at"}
        }
    },
    "Order": {
        "description": "Closed revenue transaction linked to closed-won opportunity",
        "primary_key": "order_id",
        "foreign_keys": {
            "opportunity_id": "Opportunity.opportunity_id (Required, 1:1)",
            "contact_id": "Contact.contact_id (Required)"
        },
        "cardinality": {
            "Opportunity": "1:1 (Unique order per closed-won opportunity)",
            "Contact": "N:1 (Belongs to one customer contact)"
        },
        "lifecycle_states": ["Completed", "Refunded", "Processing"],
        "fields": {
            "order_id": {"type": "string", "required": True, "unique": True, "format": "ORD-2026-######", "validation": r"^ORD-2026-\d{6}$"},
            "opportunity_id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "required": True},
            "order_date": {"type": "datetime", "required": True},
            "gross_revenue": {"type": "float", "required": True, "min": 0.0},
            "currency": {"type": "string", "required": True, "allowed_values": ["USD", "EUR", "GBP"]},
            "status": {"type": "string", "required": True, "allowed_values": ["Completed", "Refunded", "Processing"]}
        }
    },
    "CostRecord": {
        "description": "Direct financial spend record attributed to marketing campaigns",
        "primary_key": "cost_record_id",
        "foreign_keys": {
            "campaign_id": "Campaign.campaign_id (Required)",
            "channel_id": "Channel.channel_id (Required)"
        },
        "cardinality": {
            "Campaign": "N:1 (Belongs to one campaign)",
            "Channel": "N:1 (Belongs to one channel)"
        },
        "fields": {
            "cost_record_id": {"type": "string", "required": True, "unique": True, "format": "CST-2026-######", "validation": r"^CST-2026-\d{6}$"},
            "campaign_id": {"type": "string", "required": True},
            "channel_id": {"type": "string", "required": True},
            "spend_date": {"type": "date", "required": True},
            "spend_amount": {"type": "float", "required": True, "min": 0.0},
            "currency": {"type": "string", "required": True, "allowed_values": ["USD", "EUR", "GBP"]},
            "cost_category": {"type": "string", "required": True, "allowed_values": ["Media Spend", "Agency Fee", "Software Tool", "Sponsorship", "Production"]}
        }
    },
    "AttributionResult": {
        "description": "Calculated attribution weight, revenue, and ROI per touchpoint and model",
        "primary_key": "attribution_id",
        "foreign_keys": {
            "opportunity_id": "Opportunity.opportunity_id (Required)",
            "touchpoint_id": "Touchpoint.touchpoint_id (Required)",
            "campaign_id": "Campaign.campaign_id (Required)",
            "channel_id": "Channel.channel_id (Required)"
        },
        "cardinality": {
            "Opportunity": "N:1 (Belongs to one opportunity)",
            "Touchpoint": "N:1 (Attributed to one touchpoint)",
            "Campaign": "N:1 (Credited to one campaign)"
        },
        "fields": {
            "attribution_id": {"type": "string", "required": True, "unique": True, "format": "ATTR-2026-######", "validation": r"^ATTR-2026-\d{6}$"},
            "opportunity_id": {"type": "string", "required": True},
            "touchpoint_id": {"type": "string", "required": True},
            "campaign_id": {"type": "string", "required": True},
            "channel_id": {"type": "string", "required": True},
            "model_name": {"type": "string", "required": True, "allowed_values": ["First-Touch", "Last-Touch", "Linear", "U-Shaped", "Time-Decay"]},
            "attribution_weight": {"type": "float", "required": True, "min": 0.0, "max": 1.0},
            "attributed_revenue_usd": {"type": "float", "required": True, "min": 0.0},
            "attributed_cost_usd": {"type": "float", "required": True, "min": 0.0},
            "calculated_at": {"type": "datetime", "required": True}
        }
    }
}

def export_data_dictionary_markdown(output_path: str):
    """Exports data dictionary as comprehensive markdown document with cardinality, lifecycle states, and Mermaid diagram."""
    lines = ["# Multi-Touch Attribution Engine: Comprehensive Data Dictionary & Relational Schema\n"]
    lines.append("## Entity Relationship Diagram (ERD) with Cardinality\n")
    lines.append("```mermaid")
    lines.append("erDiagram")
    lines.append("    Channel ||--o{ Campaign : \"hosts (1:N)\"")
    lines.append("    Channel ||--o{ WebSession : \"refers (1:N)\"")
    lines.append("    Channel ||--o{ Touchpoint : \"delivers (1:N)\"")
    lines.append("    Audience ||--o{ Campaign : \"targets (1:N)\"")
    lines.append("    Campaign ||--o{ Creative : \"comprises (1:N)\"")
    lines.append("    Campaign ||--o{ CostRecord : \"incurs (1:N)\"")
    lines.append("    Campaign ||--o{ Touchpoint : \"drives (1:N)\"")
    lines.append("    Contact ||--o{ WebSession : \"executes (1:N optional)\"")
    lines.append("    Contact ||--o{ Touchpoint : \"participates_in (1:N mandatory)\"")
    lines.append("    Contact ||--o{ Lead : \"initiates (1:N)\"")
    lines.append("    Contact ||--o{ Opportunity : \"associated_with (1:N)\"")
    lines.append("    Lead ||--o{ Opportunity : \"converts_to (1:N)\"")
    lines.append("    Opportunity ||--|| Order : \"fulfills (1:1)\"")
    lines.append("    Opportunity ||--o{ AttributionResult : \"evaluated_by (1:N)\"")
    lines.append("    Touchpoint ||--o{ AttributionResult : \"credited_in (1:N)\"")
    lines.append("```\n")

    lines.append("## Lifecycle States & Allowed Transitions\n")
    lines.append("- **Contact**: `Visitor` -> `Lead` -> `MQL` -> `SQL` -> `Opportunity` -> `Customer` (or `Churned`)")
    lines.append("- **Opportunity**: `Discovery` -> `Validation` -> `Proposal` -> `Negotiation` -> `Closed Won` / `Closed Lost`")
    lines.append("- **Lead**: `Open` -> `Contacted` -> `Qualified` -> `Converted` / `Unqualified`\n")

    for entity, details in DATA_DICTIONARY.items():
        lines.append(f"### Entity: `{entity}`")
        lines.append(f"*{details['description']}*")
        lines.append(f"- **Primary Key**: `{details['primary_key']}`")
        
        if "foreign_keys" in details:
            lines.append("- **Foreign Keys**:")
            for fk, target in details["foreign_keys"].items():
                lines.append(f"  - `{fk}` -> `{target}`")
                
        if "cardinality" in details:
            lines.append("- **Cardinality**:")
            for rel_entity, card in details["cardinality"].items():
                lines.append(f"  - `{rel_entity}`: {card}")

        if "lifecycle_states" in details:
            lines.append(f"- **Lifecycle States**: {', '.join(details['lifecycle_states'])}")

        if "effective_dates" in details:
            lines.append(f"- **Effective Dates**: {details['effective_dates']}")

        lines.append("\n| Field Name | Type | Required | Unique | Validation / Allowed Values / Units |")
        lines.append("|---|---|---|---|---|")
        for fname, finfo in details["fields"].items():
            req = "Yes" if finfo.get("required") else "No"
            uniq = "Yes" if finfo.get("unique") else "No"
            val = finfo.get("rule", "")
            if "allowed_values" in finfo:
                val = f"Enum: {', '.join(finfo['allowed_values'])}"
            elif "format" in finfo:
                val = f"Pattern: `{finfo['format']}`"
            elif finfo.get("min") is not None:
                val = f"Range: [{finfo.get('min')}, {finfo.get('max', 'inf')}]"
            if "unit" in finfo:
                val += f" (Unit: {finfo['unit']})"
            lines.append(f"| `{fname}` | {finfo['type']} | {req} | {uniq} | {val} |")
        lines.append("\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
