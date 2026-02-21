"""
Reasoning Engine — Replaces the million lines of PROLOG.

The original 2020 system used PROLOG to encode decision-making logic:
"if probability of success is less than 45%, my intellect won't agree"

Modern approach: Use structured prompting with the LLM to replicate
this reasoning, while also LOGGING every decision and its confidence
level for Phase 3's faith-variable analysis.

This is where game theory meets AI — the twin uses argumentation
theory (from the textbook!) to structure its reasoning.
"""

import json
import time
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from loguru import logger


class DecisionOutcome(str, Enum):
    PROCEED = "proceed"
    DECLINE = "decline"
    DEFER = "defer"
    UNCERTAIN = "uncertain"  # Below faith threshold — key for Phase 3


@dataclass
class Decision:
    """
    A structured decision made by the twin.
    
    Every decision is logged for Phase 3 analysis.
    The 'confidence' field is critical — decisions where confidence < 0.45
    (the faith threshold from the original research) are flagged for divergence analysis.
    """
    
    # The decision
    question: str                           # What was being decided
    options: list[str] = field(default_factory=list)  # Available options
    chosen: str = ""                        # What was chosen
    outcome: DecisionOutcome = DecisionOutcome.UNCERTAIN
    
    # Analysis
    confidence: float = 0.5                 # 0-1, how confident the twin is
    reasoning: str = ""                     # Why this was chosen
    arguments_for: list[str] = field(default_factory=list)
    arguments_against: list[str] = field(default_factory=list)
    
    # Phase 3 markers
    below_faith_threshold: bool = False     # Was confidence < 0.45?
    faith_category: str = ""                # What type of faith decision
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    context: str = ""                       # Conversational context
    decision_id: str = ""                   # Unique ID
    
    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "question": self.question,
            "options": self.options,
            "chosen": self.chosen,
            "outcome": self.outcome.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "arguments_for": self.arguments_for,
            "arguments_against": self.arguments_against,
            "below_faith_threshold": self.below_faith_threshold,
            "faith_category": self.faith_category,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class ReasoningEngine:
    """
    Structured reasoning system that replaces PROLOG.
    
    Uses argumentation theory from the textbook to structure decisions:
    1. Identify the claim/question
    2. Generate arguments for and against
    3. Evaluate argument strength
    4. Make a decision with confidence level
    5. Log everything for Phase 3
    
    The critical innovation: When confidence drops below 0.45,
    the logical twin is SUPPOSED to decline. But the real person
    might proceed anyway — that gap is faith.
    """
    
    def __init__(
        self,
        faith_threshold: float = 0.45,
        decision_log_dir: str = "./data/decisions",
    ):
        self.faith_threshold = faith_threshold
        self.decision_log_dir = Path(decision_log_dir)
        self.decision_log_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for decision logging."""
        db_path = self.decision_log_dir / "decisions.db"
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT,
                chosen TEXT,
                outcome TEXT,
                confidence REAL,
                reasoning TEXT,
                arguments_for TEXT,
                arguments_against TEXT,
                below_faith_threshold BOOLEAN,
                faith_category TEXT,
                context TEXT,
                -- Phase 3 columns
                real_human_choice TEXT,
                diverged BOOLEAN DEFAULT NULL,
                divergence_notes TEXT
            )
        """)
        self.db.commit()
    
    def build_reasoning_prompt(
        self,
        question: str,
        context: str = "",
        available_info: list[str] | None = None,
    ) -> str:
        """
        Build a structured reasoning prompt using argumentation theory.
        
        This prompt instructs the LLM to reason the way the original
        PROLOG system was designed to reason — but better.
        """
        prompt = f"""Analyze this decision using structured argumentation:

## Question
{question}

## Context
{context if context else "No additional context provided."}

## Available Information
{chr(10).join(f"- {info}" for info in (available_info or []))}

## Instructions
Using game theory and argumentation principles, analyze this decision:

1. **Identify Arguments FOR** (list each argument supporting proceeding)
2. **Identify Arguments AGAINST** (list each argument against proceeding)  
3. **Evaluate Strength** (rate each argument 0-1)
4. **Calculate Overall Confidence** (weighted average, 0-1)
5. **Make Decision** with one of: proceed, decline, defer, uncertain

CRITICAL RULE: If your overall confidence is below {self.faith_threshold} (45%), 
your logical assessment is that you should DECLINE or DEFER. 
This is the rationality threshold — below this, logic says no.
(Note: This is exactly where faith would override logic for the real person.)

Respond in this exact JSON format:
{{
    "arguments_for": [
        {{"argument": "...", "strength": 0.0}}
    ],
    "arguments_against": [
        {{"argument": "...", "strength": 0.0}}
    ],
    "confidence": 0.0,
    "chosen": "proceed|decline|defer",
    "reasoning": "Brief explanation of the decision logic"
}}"""
        
        return prompt
    
    def parse_reasoning_response(self, response: str, question: str, context: str = "") -> Decision:
        """Parse the LLM's structured reasoning into a Decision object."""
        import hashlib
        
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            confidence = float(data.get("confidence", 0.5))
            below_threshold = confidence < self.faith_threshold
            
            # Map choice to outcome
            choice_map = {
                "proceed": DecisionOutcome.PROCEED,
                "decline": DecisionOutcome.DECLINE,
                "defer": DecisionOutcome.DEFER,
            }
            outcome = choice_map.get(
                data.get("chosen", "uncertain"),
                DecisionOutcome.UNCERTAIN
            )
            
            # If confidence is below threshold but twin chose to proceed,
            # that's a logic inconsistency we should flag
            if below_threshold and outcome == DecisionOutcome.PROCEED:
                logger.warning(
                    f"Twin chose to PROCEED despite confidence {confidence:.2f} < "
                    f"threshold {self.faith_threshold}. This shouldn't happen for a pure logic twin."
                )
                outcome = DecisionOutcome.DECLINE
            
            decision = Decision(
                question=question,
                chosen=data.get("chosen", "uncertain"),
                outcome=outcome,
                confidence=confidence,
                reasoning=data.get("reasoning", ""),
                arguments_for=[a["argument"] for a in data.get("arguments_for", [])],
                arguments_against=[a["argument"] for a in data.get("arguments_against", [])],
                below_faith_threshold=below_threshold,
                faith_category="sub_threshold" if below_threshold else "above_threshold",
                context=context,
                decision_id=hashlib.sha256(
                    f"{question}:{time.time()}".encode()
                ).hexdigest()[:16],
            )
            
            # Log the decision
            self.log_decision(decision)
            
            return decision
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse reasoning response: {e}")
            return Decision(
                question=question,
                outcome=DecisionOutcome.UNCERTAIN,
                confidence=0.5,
                reasoning=f"Parse error: {e}",
                context=context,
            )
    
    def log_decision(self, decision: Decision):
        """Log a decision to the SQLite database for Phase 3 analysis."""
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO decisions 
                   (decision_id, timestamp, question, options, chosen, outcome, 
                    confidence, reasoning, arguments_for, arguments_against,
                    below_faith_threshold, faith_category, context)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision.decision_id,
                    decision.timestamp.isoformat(),
                    decision.question,
                    json.dumps(decision.options),
                    decision.chosen,
                    decision.outcome.value,
                    decision.confidence,
                    decision.reasoning,
                    json.dumps(decision.arguments_for),
                    json.dumps(decision.arguments_against),
                    decision.below_faith_threshold,
                    decision.faith_category,
                    decision.context,
                )
            )
            self.db.commit()
            
            if decision.below_faith_threshold:
                logger.info(
                    f"⚡ FAITH THRESHOLD DECISION logged: confidence={decision.confidence:.2f} "
                    f"| outcome={decision.outcome.value} | question='{decision.question[:50]}...'"
                )
            else:
                logger.debug(f"Decision logged: {decision.decision_id}")
                
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
    
    def record_human_choice(
        self,
        decision_id: str,
        human_choice: str,
        notes: str = "",
    ):
        """
        Record what the REAL human chose for a given decision.
        
        This is the Phase 3 data collection method. After the twin makes
        a decision, the real human logs what they actually did. The
        divergence between twin_choice and human_choice IS the faith variable.
        """
        try:
            # Get the twin's decision
            cursor = self.db.execute(
                "SELECT chosen, confidence, below_faith_threshold FROM decisions WHERE decision_id = ?",
                (decision_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Decision {decision_id} not found")
                return
            
            twin_choice, confidence, below_threshold = row
            diverged = (human_choice.lower() != twin_choice.lower())
            
            self.db.execute(
                """UPDATE decisions 
                   SET real_human_choice = ?, diverged = ?, divergence_notes = ?
                   WHERE decision_id = ?""",
                (human_choice, diverged, notes, decision_id)
            )
            self.db.commit()
            
            if diverged and below_threshold:
                logger.info(
                    f"🔮 FAITH DIVERGENCE DETECTED: Twin said '{twin_choice}' "
                    f"(confidence {confidence:.2f}), human chose '{human_choice}'. "
                    f"This is a faith data point!"
                )
            elif diverged:
                logger.info(
                    f"↔️ Divergence: Twin='{twin_choice}', Human='{human_choice}' "
                    f"(confidence {confidence:.2f})"
                )
                
        except Exception as e:
            logger.error(f"Failed to record human choice: {e}")
    
    def get_divergence_stats(self) -> dict:
        """Get statistics on twin-human divergence for Phase 3 analysis."""
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as total_decisions,
                SUM(CASE WHEN below_faith_threshold THEN 1 ELSE 0 END) as below_threshold,
                SUM(CASE WHEN diverged THEN 1 ELSE 0 END) as total_divergences,
                SUM(CASE WHEN diverged AND below_faith_threshold THEN 1 ELSE 0 END) as faith_divergences,
                AVG(confidence) as avg_confidence,
                AVG(CASE WHEN diverged THEN confidence ELSE NULL END) as avg_divergence_confidence
            FROM decisions
            WHERE real_human_choice IS NOT NULL
        """)
        
        row = cursor.fetchone()
        if not row or row[0] == 0:
            return {"total_decisions": 0, "message": "No human choices recorded yet"}
        
        total, below_threshold, divergences, faith_divs, avg_conf, avg_div_conf = row
        
        return {
            "total_decisions_with_human_data": total,
            "below_faith_threshold": below_threshold,
            "total_divergences": divergences or 0,
            "faith_divergences": faith_divs or 0,
            "divergence_rate": (divergences or 0) / total if total else 0,
            "faith_divergence_rate": (faith_divs or 0) / (below_threshold or 1),
            "avg_confidence": avg_conf,
            "avg_confidence_at_divergence": avg_div_conf,
            "faith_variable_signal": (
                "STRONG" if (faith_divs or 0) / max(below_threshold or 1, 1) > 0.5
                else "MODERATE" if (faith_divs or 0) / max(below_threshold or 1, 1) > 0.2
                else "WEAK" if faith_divs
                else "NO DATA"
            ),
        }
