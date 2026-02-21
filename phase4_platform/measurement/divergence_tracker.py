"""
Divergence Tracker — Infrastructure for Phase 3 Faith Variable Research.

This module measures the gap between the digital twin's logical decisions
and the real human's actual choices. Every divergence — especially those
where the twin's confidence was below 45% — is a potential data point
for faith as a measurable variable.

From the original research:
"I started to wonder about this 'Blind Belief,' which created a miracle
 in me! This 'Blind belief' is Faith. I wondered why it had the magical
 power to manifest anything into reality."

We don't add faith to the twin — we measure its absence.
"""

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from loguru import logger


class DivergenceTracker:
    """
    Tracks and analyzes divergences between twin and human decisions.
    
    The faith variable = the systematic pattern in where and when
    humans override their logical twin's recommendations.
    """
    
    def __init__(self, db_path: str = "./data/decisions/decisions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
    
    def get_full_analysis(self) -> dict:
        """
        Complete divergence analysis for the devudaaaa dashboard.
        
        Returns a comprehensive view of:
        - Overall divergence statistics
        - Faith threshold analysis
        - Category breakdown
        - Temporal patterns
        - Signal strength assessment
        """
        return {
            "summary": self._get_summary(),
            "faith_analysis": self._get_faith_analysis(),
            "category_breakdown": self._get_category_breakdown(),
            "temporal_patterns": self._get_temporal_patterns(),
            "recent_divergences": self._get_recent_divergences(limit=20),
            "signal_assessment": self._assess_signal(),
            "generated_at": datetime.now().isoformat(),
        }
    
    def _get_summary(self) -> dict:
        """Overall statistics."""
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN real_human_choice IS NOT NULL THEN 1 ELSE 0 END) as with_human_data,
                SUM(CASE WHEN diverged = 1 THEN 1 ELSE 0 END) as divergences,
                SUM(CASE WHEN below_faith_threshold = 1 THEN 1 ELSE 0 END) as below_threshold,
                SUM(CASE WHEN diverged = 1 AND below_faith_threshold = 1 THEN 1 ELSE 0 END) as faith_divergences,
                AVG(confidence) as avg_confidence
            FROM decisions
        """)
        row = cursor.fetchone()
        
        if not row or row["total"] == 0:
            return {"total_decisions": 0, "status": "no_data"}
        
        total_with_data = row["with_human_data"] or 0
        divergences = row["divergences"] or 0
        faith_divs = row["faith_divergences"] or 0
        
        return {
            "total_decisions": row["total"],
            "decisions_with_human_data": total_with_data,
            "total_divergences": divergences,
            "divergence_rate": divergences / total_with_data if total_with_data else 0,
            "below_threshold_decisions": row["below_threshold"] or 0,
            "faith_divergences": faith_divs,
            "avg_confidence": row["avg_confidence"],
        }
    
    def _get_faith_analysis(self) -> dict:
        """Detailed analysis of sub-threshold decisions (the faith zone)."""
        cursor = self.db.execute("""
            SELECT 
                confidence,
                chosen as twin_choice,
                real_human_choice,
                diverged,
                question,
                reasoning,
                timestamp
            FROM decisions
            WHERE below_faith_threshold = 1 AND real_human_choice IS NOT NULL
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            return {"status": "no_faith_zone_data", "decisions": []}
        
        # Analyze patterns in faith-zone divergences
        proceeded_despite_logic = sum(
            1 for r in rows 
            if r["twin_choice"] in ("decline", "defer") and r["real_human_choice"] == "proceed"
        )
        
        return {
            "total_faith_zone_decisions": len(rows),
            "human_overrode_logic": proceeded_despite_logic,
            "override_rate": proceeded_despite_logic / len(rows) if rows else 0,
            "interpretation": (
                f"In {proceeded_despite_logic}/{len(rows)} cases where logic said no "
                f"(confidence < 45%), the human proceeded anyway. "
                f"This {proceeded_despite_logic/len(rows):.0%} override rate suggests "
                f"{'a strong' if proceeded_despite_logic/len(rows) > 0.5 else 'a moderate' if proceeded_despite_logic/len(rows) > 0.2 else 'a weak'} "
                f"faith signal."
            ),
            "decisions": [
                {
                    "question": r["question"][:100],
                    "twin_said": r["twin_choice"],
                    "human_did": r["real_human_choice"],
                    "diverged": bool(r["diverged"]),
                    "confidence": r["confidence"],
                    "timestamp": r["timestamp"],
                }
                for r in rows[:10]  # Last 10
            ],
        }
    
    def _get_category_breakdown(self) -> dict:
        """Breakdown by decision category."""
        cursor = self.db.execute("""
            SELECT 
                faith_category,
                COUNT(*) as total,
                SUM(CASE WHEN diverged = 1 THEN 1 ELSE 0 END) as divergences,
                AVG(confidence) as avg_confidence
            FROM decisions
            WHERE real_human_choice IS NOT NULL
            GROUP BY faith_category
        """)
        
        categories = {}
        for row in cursor.fetchall():
            cat = row["faith_category"] or "uncategorized"
            total = row["total"]
            divs = row["divergences"] or 0
            categories[cat] = {
                "total": total,
                "divergences": divs,
                "divergence_rate": divs / total if total else 0,
                "avg_confidence": row["avg_confidence"],
            }
        
        return categories
    
    def _get_temporal_patterns(self) -> dict:
        """Analyze divergence patterns over time."""
        cursor = self.db.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as decisions,
                SUM(CASE WHEN diverged = 1 THEN 1 ELSE 0 END) as divergences,
                AVG(confidence) as avg_confidence
            FROM decisions
            WHERE real_human_choice IS NOT NULL
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
        """)
        
        return {
            "daily": [
                {
                    "date": row["date"],
                    "decisions": row["decisions"],
                    "divergences": row["divergences"] or 0,
                    "avg_confidence": row["avg_confidence"],
                }
                for row in cursor.fetchall()
            ]
        }
    
    def _get_recent_divergences(self, limit: int = 20) -> list[dict]:
        """Get the most recent divergences."""
        cursor = self.db.execute("""
            SELECT *
            FROM decisions
            WHERE diverged = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        return [
            {
                "decision_id": row["decision_id"],
                "question": row["question"],
                "twin_choice": row["chosen"],
                "human_choice": row["real_human_choice"],
                "confidence": row["confidence"],
                "below_threshold": bool(row["below_faith_threshold"]),
                "reasoning": row["reasoning"],
                "notes": row["divergence_notes"],
                "timestamp": row["timestamp"],
            }
            for row in cursor.fetchall()
        ]
    
    def _assess_signal(self) -> dict:
        """Assess the overall faith-variable signal strength."""
        summary = self._get_summary()
        faith = self._get_faith_analysis()
        
        if summary.get("status") == "no_data":
            return {
                "strength": "NO_DATA",
                "message": "No decisions recorded yet. Start using the twin to generate data.",
                "recommendations": [
                    "Use the /decide endpoint to log structured decisions",
                    "Record human choices with /decide/record",
                    "Aim for 50+ decisions for statistical significance",
                ],
            }
        
        override_rate = faith.get("override_rate", 0)
        total = summary.get("decisions_with_human_data", 0)
        
        if total < 10:
            strength = "INSUFFICIENT"
            message = f"Only {total} decisions with human data. Need 50+ for meaningful analysis."
        elif override_rate > 0.6:
            strength = "STRONG"
            message = (
                f"Strong faith signal detected. Humans override logic {override_rate:.0%} of the time "
                f"when confidence is below the threshold. This is a statistically significant pattern."
            )
        elif override_rate > 0.3:
            strength = "MODERATE"
            message = (
                f"Moderate faith signal. {override_rate:.0%} override rate in faith-zone decisions. "
                f"More data will strengthen the analysis."
            )
        elif override_rate > 0.1:
            strength = "WEAK"
            message = (
                f"Weak but present faith signal ({override_rate:.0%} override rate). "
                f"The human occasionally overrides logic, but it's not the dominant pattern."
            )
        else:
            strength = "MINIMAL"
            message = (
                "Very low divergence in the faith zone. The human tends to agree with "
                "the logical twin even under uncertainty."
            )
        
        return {
            "strength": strength,
            "override_rate": override_rate,
            "sample_size": total,
            "message": message,
            "publishable": total >= 50 and strength in ("STRONG", "MODERATE"),
        }
    
    def export_for_research(self, output_path: str = "./data/exports/divergence_report.json"):
        """Export full analysis as a research-ready JSON report."""
        analysis = self.get_full_analysis()
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Research report exported to {output}")
        return analysis
