"""
REST API for Multi-Touch Attribution Engine.
Provides programmatic access to attribution models, campaign ROI,
customer journey timelines, identity verification, period splits, and anomaly evaluations.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import pandas as pd
from pathlib import Path

from src.config import DATA_DIR, EXCHANGE_RATES_TO_USD

def create_app():
    app = Flask(__name__)
    CORS(app)
    db_path = DATA_DIR / "attribution.db"

    def get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "service": "Attribution-Engine-API"})

    @app.route("/api/overview", methods=["GET"])
    def get_overview():
        conn = get_db()
        cur = conn.cursor()
        
        camps_count = cur.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        contacts_count = cur.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        touches_count = cur.execute("SELECT COUNT(*) FROM touchpoints").fetchone()[0]
        opps_count = cur.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        won_opps = cur.execute("SELECT COUNT(*), SUM(amount) FROM opportunities WHERE stage = 'Closed Won'").fetchone()
        
        conn.close()
        return jsonify({
            "campaigns": camps_count,
            "contacts": contacts_count,
            "touchpoints": touches_count,
            "opportunities": opps_count,
            "won_opportunities": won_opps[0],
            "total_won_pipeline_usd": round(won_opps[1] or 0.0, 2)
        })

    @app.route("/api/models/comparison", methods=["GET"])
    def get_model_comparison():
        conn = get_db()
        query = """
            SELECT 
                model_name,
                COUNT(DISTINCT opportunity_id) as opportunities_attributed,
                COUNT(DISTINCT campaign_id) as campaigns_credited,
                ROUND(SUM(attributed_revenue_usd), 2) as total_attributed_revenue_usd
            FROM attribution_results
            GROUP BY model_name
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return jsonify(df.to_dict(orient="records"))

    @app.route("/api/campaigns", methods=["GET"])
    def get_campaigns_roi():
        model = request.args.get("model", "U-Shaped")
        conn = get_db()
        query = f"""
            SELECT 
                a.campaign_id,
                c.campaign_name,
                ch.channel_name,
                c.budget,
                ROUND(SUM(a.attributed_revenue_usd), 2) as attributed_revenue,
                COUNT(a.touchpoint_id) as touchpoints_count
            FROM attribution_results a
            JOIN campaigns c ON a.campaign_id = c.campaign_id
            JOIN channels ch ON a.channel_id = ch.channel_id
            WHERE a.model_name = ?
            GROUP BY a.campaign_id, c.campaign_name, ch.channel_name, c.budget
            ORDER BY attributed_revenue DESC
        """
        df = pd.read_sql_query(query, conn, params=[model])
        conn.close()
        return jsonify(df.to_dict(orient="records"))

    @app.route("/api/journey/<opportunity_id>", methods=["GET"])
    def get_opportunity_journey(opportunity_id):
        conn = get_db()
        opp_query = "SELECT * FROM opportunities WHERE opportunity_id = ?"
        opp = pd.read_sql_query(opp_query, conn, params=[opportunity_id]).to_dict(orient="records")
        if not opp:
            conn.close()
            return jsonify({"error": "Opportunity not found"}), 404

        touches_query = """
            SELECT 
                t.*,
                c.campaign_name,
                ch.channel_name
            FROM touchpoints t
            JOIN campaigns c ON t.campaign_id = c.campaign_id
            JOIN channels ch ON t.channel_id = ch.channel_id
            WHERE t.contact_id = ?
            ORDER BY t.timestamp ASC
        """
        touches = pd.read_sql_query(touches_query, conn, params=[opp[0]["contact_id"]]).to_dict(orient="records")

        attr_query = """
            SELECT model_name, touchpoint_id, attribution_weight, attributed_revenue_usd
            FROM attribution_results
            WHERE opportunity_id = ?
        """
        attr = pd.read_sql_query(attr_query, conn, params=[opportunity_id]).to_dict(orient="records")
        conn.close()

        return jsonify({
            "opportunity": opp[0],
            "touchpoints": touches,
            "attributions": attr
        })

    @app.route("/api/identity/verification", methods=["GET"])
    def get_identity_verification():
        conn = get_db()
        sessions = pd.read_sql_query("SELECT * FROM web_sessions", conn)
        conn.close()
        
        total = len(sessions)
        identified = int(sessions["contact_id"].notna().sum())
        anon = total - identified
        missing_high_intent = int(sessions[sessions["contact_id"].isna() & sessions["landing_page"].str.contains("pricing|enterprise|roi", case=False, na=False)].shape[0])

        return jsonify({
            "total_web_sessions": total,
            "identified_sessions": identified,
            "anonymous_sessions": anon,
            "missing_identity_links": missing_high_intent
        })

    @app.route("/api/reconciliation", methods=["GET"])
    def get_reconciliation():
        conn = get_db()
        orders = pd.read_sql_query("SELECT * FROM orders", conn).drop_duplicates(subset=["opportunity_id"])
        attr = pd.read_sql_query("SELECT model_name, SUM(attributed_revenue_usd) as total_attr FROM attribution_results GROUP BY model_name", conn)
        conn.close()

        orders["fx_rate"] = orders["currency"].map(EXCHANGE_RATES_TO_USD).fillna(1.0)
        target_rev = round(float((orders["gross_revenue"] * orders["fx_rate"]).sum()), 2)
        
        models_proof = {}
        for _, row in attr.iterrows():
            m_rev = round(float(row["total_attr"]), 2)
            models_proof[row["model_name"]] = {
                "attributed_revenue_usd": m_rev,
                "target_revenue_usd": target_rev,
                "difference": round(abs(m_rev - target_rev), 2),
                "is_reconciled": abs(m_rev - target_rev) < 1.0
            }

        return jsonify({
            "status": "PASSED" if all(v["is_reconciled"] for v in models_proof.values()) else "FAILED",
            "target_revenue_usd": target_rev,
            "models": models_proof
        })

    @app.route("/api/anomalies", methods=["GET"])
    def get_anomalies():
        conn = get_db()
        gt = pd.read_sql_query("SELECT * FROM ground_truth", conn).to_dict(orient="records")
        conn.close()
        return jsonify(gt)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(port=5000, debug=True)
