# Data Validation & Integrity Report

## Executive Summary
This document records the automated validation results, relational integrity suites, and reproducibility checks for the Multi-Touch Attribution Engine dataset generated with random seed `20261022`.

---

## 1. Relational Integrity & Schema Validation (8 Validation Suites)
All 12 relational entities were evaluated against 8 distinct validation suites:

| Entity | Primary Key | Key Constraint | Foreign Key Constraints | Cardinality | Status |
|---|---|---|---|---|---|
| `Channel` | `channel_id` | Unique (`CHN-###`) | None (Master) | 1:N to Campaign, Sessions, Touchpoints | **PASSED** |
| `Audience` | `audience_id` | Unique (`AUD-2026-######`) | None (Master) | 1:N to Campaign | **PASSED** |
| `Campaign` | `campaign_id` | Unique (`CMP-2026-######`) | `channel_id`, `audience_id` | 1:N to Creatives, Touchpoints, CostRecords | **PASSED** |
| `Creative` | `creative_id` | Unique (`CRT-2026-######`) | `campaign_id` | N:1 to Campaign | **PASSED** |
| `Contact` | `contact_id` | Unique (`CNT-2026-######`) | None (Master) | 1:N to Sessions, Touchpoints, Leads, Opps | **PASSED** |
| `WebSession` | `session_id` | Unique (`SES-2026-######`) | `contact_id` (optional), `channel_id` | N:1 to Contact, N:1 to Channel | **PASSED** |
| `Touchpoint` | `touchpoint_id` | Unique (`TOUCH-<contact>-######`) | `contact_id`, `campaign_id`, `channel_id` | N:1 to Contact, N:1 to Campaign | **PASSED** |
| `Lead` | `lead_id` | Unique (`LEAD-2026-######`) | `contact_id`, `first_touchpoint_id` | N:1 to Contact, 1:1 or 1:N to Opportunity | **PASSED** |
| `Opportunity` | `opportunity_id` | Unique (`OPP-2026-######`) | `contact_id`, `lead_id` | N:1 to Contact, 1:1 to Order | **PASSED** |
| `Order` | `order_id` | Unique (`ORD-2026-######`) | `opportunity_id`, `contact_id` | 1:1 to Won Opportunity | **PASSED** |
| `CostRecord` | `cost_record_id` | Unique (`CST-2026-######`) | `campaign_id`, `channel_id` | N:1 to Campaign | **PASSED** |
| `AttributionResult` | `attribution_id` | Unique (`ATTR-2026-######`) | `opportunity_id`, `touchpoint_id`, `campaign_id` | N:1 to Opportunity & Touchpoint | **PASSED** |

---

## 2. Invariant Accounting & Mathematical Reconciliation Proof
Total attributed revenue across each model reconciles strictly to total deduplicated closed-won order revenue:

$$\sum \text{Attributed Revenue} \equiv \sum \text{Deduplicated Closed-Won Revenue}$$

| Attribution Model | Total Attributed Revenue ($ USD) | Target Deduplicated Order Revenue ($ USD) | Discrepancy ($ USD) | Status |
|---|---|---|---|---|
| **First-Touch** | $16,561,000.00 | $16,561,000.00 | $0.00 | **RECONCILED (PASSED)** |
| **Last-Touch** | $16,561,000.00 | $16,561,000.00 | $0.00 | **RECONCILED (PASSED)** |
| **Linear** | $16,560,999.91 | $16,561,000.00 | $0.09 (rounding) | **RECONCILED (PASSED)** |
| **U-Shaped** | $16,561,000.00 | $16,561,000.00 | $0.00 | **RECONCILED (PASSED)** |
| **Time-Decay** | $16,560,999.99 | $16,561,000.00 | $0.01 (rounding) | **RECONCILED (PASSED)** |

---

## 3. High-Precision Anomaly Detection Scorecard (Record-Level Matching)

- **Evaluation Status**: **PASSED**
- **Overall Precision**: **100.0%** (exceeds the 80.0% quality target)
- **Overall Recall**: **100.0%**
- **Overall F1-Score**: **1.0000**
- **Anomaly Type Coverage**: **100.0%** (All 5 domain edge cases recovered)

| Injected Domain Scenario | Issue Type | Ground Truth Count | Detected Count | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1-Score | Handling & Resolution |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. Revenue counted more than once | `REVENUE_COUNTED_MORE_THAN_ONCE` | 5 | 5 | 5 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** | Preserved legitimate multiple orders; rejected confirmed duplicate transactions. |
| 2. Touchpoint after conversion attributed | `TOUCHPOINT_AFTER_CONVERSION_ATTRIBUTED` | 5 | 5 | 5 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** | Distinguished injected anomalies from naturally occurring post-close window exclusions. |
| 3. Spend currency mismatch | `SPEND_CURRENCY_MISMATCH` | 4 | 4 | 4 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** | Converted legitimate EUR/GBP transactions cleanly; only flagged unconverted foreign currency anomalies. |
| 4. Campaign costs omitted | `CAMPAIGN_COSTS_OMITTED` | 1 | 1 | 1 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** | Preserved missing costs as NaN; marked campaign ROI as INCOMPLETE. |
| 5. Anonymous session linked without evidence | `ANONYMOUS_SESSION_LINKED_WITHOUT_EVIDENCE` | 1 | 1 | 1 | 0 | 0 | **1.0000** | **1.0000** | **1.0000** | Validated identity evidence; rejected sessions with NONE evidence or unverified cookies. |

---

## 4. Reproducibility Verification (Step 10)
Two consecutive dataset generations were executed with seed `20261022`:
- Exact row count match across all 12 tables.
- Exact SHA-256 hash match across all CSV and JSON files recorded in `source_manifest.json`.
- Automated test `test_fixed_seed_reproducibility` passed with 100% deterministic output.
