"""
Complete Data Exporter for CSV, JSON, SQLite and Full SQL Seed DDL dumps.
Exports all 12 entities and ground truth cleanly into production formats.
"""
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime

from src.generator.data_dictionary import DATA_DICTIONARY, export_data_dictionary_markdown
from src.generator.validator import compute_dataset_checksums

class DataExporter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.raw_dir = output_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        datasets: Dict[str, pd.DataFrame],
        ground_truth: List[Dict[str, Any]],
        seed: int,
        scale: str,
        validation_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exports data to CSVs, JSONs, SQLite database, full SQL script, and Manifest."""
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "seed": seed,
            "scale": scale,
            "tables": {}
        }

        # 1. Export CSVs & Entity JSONs
        consolidated_json = {}
        for name, df in datasets.items():
            if isinstance(df, pd.DataFrame):
                # CSV
                csv_path = self.raw_dir / f"{name}.csv"
                df.to_csv(csv_path, index=False)

                # Individual JSON
                json_path = self.raw_dir / f"{name}.json"
                df.to_json(json_path, orient="records", indent=2, date_format="iso")

                consolidated_json[name] = df.to_dict(orient="records")

                manifest["tables"][name] = {
                    "row_count": len(df),
                    "csv_file": f"raw/{name}.csv",
                    "json_file": f"raw/{name}.json"
                }

        # Full consolidated JSON seed
        with open(self.output_dir / "seed_data.json", "w", encoding="utf-8") as f:
            json.dump(consolidated_json, f, indent=2, default=str)

        # 2. Export Ground Truth (JSON and CSV)
        gt_df = pd.DataFrame(ground_truth)
        gt_csv_path = self.output_dir / "ground_truth.csv"
        gt_json_path = self.output_dir / "ground_truth.json"
        gt_df.to_csv(gt_csv_path, index=False)
        with open(gt_json_path, "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2)

        # 3. Export Data Dictionary
        dd_json_path = self.output_dir / "data_dictionary.json"
        with open(dd_json_path, "w", encoding="utf-8") as f:
            json.dump(DATA_DICTIONARY, f, indent=2)

        # 4. Export SQLite DB with Indexes
        db_path = self.output_dir / "attribution.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for name, df in datasets.items():
            if isinstance(df, pd.DataFrame):
                df.to_sql(name, conn, if_exists="replace", index=False)
        gt_df.to_sql("ground_truth", conn, if_exists="replace", index=False)
        
        # Create helpful analytical indexes
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_touches_contact ON touchpoints (contact_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_touches_camp ON touchpoints (campaign_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_opps_contact ON opportunities (contact_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_attr_opp ON attribution_results (opportunity_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_attr_camp ON attribution_results (campaign_id);")
            conn.commit()
        except Exception:
            pass
        conn.close()

        # 5. Export Full SQL DDL / Seed dump
        sql_path = self.output_dir / "seed_data.sql"
        with open(sql_path, "w", encoding="utf-8") as sql_file:
            sql_file.write(f"-- ==========================================================\n")
            sql_file.write(f"-- Multi-Touch Attribution Engine Seed Data & DDL\n")
            sql_file.write(f"-- Seed: {seed} | Scale: {scale} | Timestamp: {manifest['generated_at']}\n")
            sql_file.write(f"-- ==========================================================\n\n")

            for name, df in datasets.items():
                if isinstance(df, pd.DataFrame):
                    cols = ", ".join([f"`{c}` TEXT" for c in df.columns])
                    sql_file.write(f"CREATE TABLE IF NOT EXISTS `{name}` ({cols});\n")
                    
                    for _, row in df.iterrows():
                        vals = ", ".join(f"'{str(v).replace('\'', '\'\'')}'" if pd.notna(v) else "NULL" for v in row.values)
                        sql_file.write(f"INSERT INTO `{name}` VALUES ({vals});\n")
                    sql_file.write("\n")

        # 6. Checksums
        checksums = compute_dataset_checksums(datasets)
        for name, chk in checksums.items():
            if name in manifest["tables"]:
                manifest["tables"][name]["sha256"] = chk

        # 7. Write Manifest and Validation Summary
        manifest["validation"] = validation_summary
        manifest_path = self.output_dir / "source_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest
