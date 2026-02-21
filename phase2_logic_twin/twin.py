"""
Digital Twin — Main Orchestrator

This is the central brain that coordinates:
- Personality (how to sound like the owner)
- Memory (what to remember and reference)
- Reasoning (how to make decisions)
- Authorization (what to reveal)

The twin receives a message, retrieves relevant memories,
generates a personality-appropriate response, and logs any
decisions for Phase 3 analysis.

Usage:
    from phase2_logic_twin.twin import DigitalTwin
    
    twin = DigitalTwin()
    response = twin.respond("Hey, what do you think about AI regulation?")
    print(response)
"""

import json
from typing import Optional
from loguru import logger

from config_loader import settings, yaml_config
from phase2_logic_twin.twin_core.personality import PersonalityEngine
from phase2_logic_twin.twin_core.reasoning import ReasoningEngine
from phase2_logic_twin.twin_core.memory import MemorySystem
from temporal_engine import (
    GTRBACEngine, RoleState, OperationMode, Operation,
    create_default_twin_engine,
)


class DigitalTwin:
    """
    The complete digital twin agent.
    
    This is what the original 2020 system described as "my digital twin" —
    a system that can respond as you would, reason as you would,
    and remember what you would. Everything except faith.
    """
    
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        access_tier: str = "friends",
    ):
        self.provider = provider or settings.primary_llm_provider
        self.model = model or settings.primary_model
        self.access_tier = access_tier
        
        # Core systems
        twin_config = yaml_config.get("twin", {})
        self.personality = PersonalityEngine(
            persona_config=self._build_persona_from_config(twin_config)
        )
        self.reasoning = ReasoningEngine(
            faith_threshold=settings.faith_threshold
        )
        self.memory = MemorySystem()
        
        # Temporal Engine — GTRBAC clock (from AIT research)
        # Governs WHEN each mode/tier is active via periodic expressions
        self.temporal_engine = create_default_twin_engine(tick_seconds=60)
        self.temporal_engine.on_state_change(self._on_temporal_change)
        
        # Do an initial tick to set current state
        self.temporal_engine.tick()
        
        # Conversation history (for context)
        self.conversation_history: list[dict] = []
        
        # LLM client (lazy loaded)
        self._llm_client = None
        
        logger.info(
            f"Digital Twin initialized: provider={self.provider}, "
            f"model={self.model}, tier={self.access_tier}"
        )
    
    def _build_persona_from_config(self, config: dict) -> dict | None:
        """Build persona dict from YAML config if available."""
        if not config:
            return None
        
        personality = config.get("personality", {})
        reasoning = config.get("reasoning", {})
        
        return {
            "name": config.get("name", "Ade"),
            "background": (
                f"Communication style: {personality.get('communication_style', 'analytical-yet-warm')}. "
                f"Cultural context: {personality.get('cultural_context', 'Telugu heritage, scientific mindset')}. "
                f"Languages: {', '.join(personality.get('languages', ['english']))}."
            ),
            "core_traits": [
                f"Humor level: {personality.get('humor_level', 0.7)}/1.0 — self-aware, not dry",
                f"Decision framework: {reasoning.get('decision_framework', 'game_theory')}",
                f"Argumentation style: {reasoning.get('argumentation_style', 'evidence_based')}",
            ],
            "communication_patterns": [],
            "values": [],
            "quirks": [],
        }
    
    @property
    def llm_client(self):
        """Lazy-load the LLM client via unified provider with automatic fallback."""
        if self._llm_client is None:
            from llm_provider import get_llm
            self._llm_client = get_llm(preferred=self.provider)
            self.provider = self._llm_client.name  # Record which provider was actually resolved
        return self._llm_client
    
    def _on_temporal_change(self, changes: list[dict], t):
        """
        Callback when the GTRBAC engine changes role states.
        
        This is the bridge between temporal constraints and twin behavior.
        When the engine transitions a mode (e.g., professional → casual),
        the twin's personality and access tier adapt automatically.
        """
        for change in changes:
            logger.info(
                f"⏰ Temporal shift: {change['role']} "
                f"{change['old_state']} → {change['new_state']}"
            )
        
        # Update access tier based on temporal engine
        new_tier = self.temporal_engine.get_current_access_tier()
        if new_tier != self.access_tier:
            logger.info(f"Access tier auto-adjusted: {self.access_tier} → {new_tier}")
            self.access_tier = new_tier
    
    def respond(
        self,
        message: str,
        sender: str = "user",
        context: str = "",
    ) -> str:
        """
        Generate a response as the digital twin.
        
        This is the main entry point. Given a message, the twin:
        1. Retrieves relevant memories
        2. Generates a personality-appropriate system prompt
        3. Calls the LLM with memories + personality + message
        4. Returns the response
        
        Args:
            message: The incoming message to respond to
            sender: Who sent the message (affects authorization)
            context: Additional context (e.g., "slack channel #general")
        """
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message,
        })
        
        # ── Step 1: Check temporal state ──────────────
        # The GTRBAC engine determines current mode/tier based on periodic expressions
        current_mode = self.temporal_engine.get_current_personality_mode()
        temporal_tier = self.temporal_engine.get_current_access_tier()
        effective_tier = max(
            [self.access_tier, temporal_tier],
            key=lambda t: ["public", "friends", "close", "private"].index(t)
            if t in ["public", "friends", "close", "private"] else 0
        )
        
        # ── Step 2: Retrieve relevant memories ─────────
        memories = self.memory.recall_for_context(
            messages=self.conversation_history,
            n_results=8,
            access_tier=effective_tier,
        )
        memory_context = self.memory.format_memories_for_prompt(memories)
        
        # ── Step 3: Generate system prompt with temporal context ──
        temporal_context = (
            f"Current temporal state: mode={current_mode}, tier={effective_tier}. "
            f"Adapt your formality and depth accordingly."
        )
        full_context = f"{context}\n{temporal_context}\n\n{memory_context}" if memory_context else f"{context}\n{temporal_context}"
        
        system_prompt = self.personality.generate_system_prompt(
            access_tier=effective_tier,
            context=full_context,
            recipient=sender,
        )
        
        # ── Step 4: Call LLM ───────────────────────────
        response = self._call_llm(system_prompt, self.conversation_history)
        
        # ── Step 5: Store response ─────────────────────
        self.conversation_history.append({
            "role": "assistant",
            "content": response,
        })
        
        return response
    
    def decide(
        self,
        question: str,
        context: str = "",
        options: list[str] | None = None,
    ) -> dict:
        """
        Make a structured decision as the digital twin.
        
        This activates the reasoning engine and logs the decision
        for Phase 3 divergence analysis.
        
        Args:
            question: The decision to be made
            context: Additional context
            options: Available options (if applicable)
        
        Returns:
            Decision dict with choice, confidence, reasoning, etc.
        """
        # Retrieve relevant memories for the decision
        memories = self.memory.recall(
            query=question,
            n_results=5,
            access_tier="private",  # Use full access for decisions
        )
        memory_info = [m["content"] for m in memories]
        
        if options:
            memory_info.append(f"Available options: {', '.join(options)}")
        
        # Build reasoning prompt
        reasoning_prompt = self.reasoning.build_reasoning_prompt(
            question=question,
            context=context,
            available_info=memory_info,
        )
        
        # Get LLM's reasoning
        system_prompt = (
            "You are an analytical decision-making system. "
            "Apply game theory and argumentation principles. "
            "Respond ONLY with the requested JSON format."
        )
        
        response = self._call_llm(
            system_prompt,
            [{"role": "user", "content": reasoning_prompt}],
        )
        
        # Parse into structured decision
        decision = self.reasoning.parse_reasoning_response(
            response=response,
            question=question,
            context=context,
        )
        
        return decision.to_dict()
    
    def _call_llm(self, system_prompt: str, messages: list[dict]) -> str:
        """Call the LLM through the unified provider (supports Ollama, Anthropic, OpenAI with automatic fallback)."""
        try:
            return self.llm_client.chat(messages=messages, system=system_prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"[Twin error: {e}]"
    
    def set_access_tier(self, tier: str):
        """Change the authorization tier."""
        valid = ["public", "friends", "close", "private"]
        if tier not in valid:
            raise ValueError(f"Invalid tier '{tier}'. Must be one of: {valid}")
        self.access_tier = tier
        logger.info(f"Access tier changed to: {tier}")
    
    def clear_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_status(self) -> dict:
        """Get the twin's current status."""
        memory_stats = self.memory.get_stats()
        divergence_stats = self.reasoning.get_divergence_stats()
        temporal_status = self.temporal_engine.get_status()
        
        return {
            "twin_name": settings.twin_name,
            "provider": self.provider,
            "model": self.model,
            "access_tier": self.access_tier,
            "conversation_length": len(self.conversation_history),
            "memory": memory_stats,
            "divergence": divergence_stats,
            "temporal": temporal_status,
        }


# ── CLI Interactive Mode ──────────────────────────────────

def interactive_mode():
    """Run the twin in interactive chat mode."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    
    console = Console()
    
    console.print(Panel(
        f"[bold cyan]🧠 Digital Twin — Interactive Mode[/bold cyan]\n\n"
        f"Provider: {settings.primary_llm_provider}\n"
        f"Model: {settings.primary_model}\n\n"
        f"Commands:\n"
        f"  /tier <public|friends|close|private> — Change access tier\n"
        f"  /decide <question> — Make a structured decision\n"
        f"  /temporal — Show GTRBAC temporal engine state\n"
        f"  /tick — Force a temporal engine tick\n"
        f"  /status — Show twin status\n"
        f"  /clear — Clear conversation\n"
        f"  /quit — Exit",
        title="devudaaaa Digital Twin",
        border_style="cyan",
    ))
    
    twin = DigitalTwin()
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if not user_input.strip():
                continue
            
            if user_input.startswith("/quit"):
                console.print("[dim]Goodbye![/dim]")
                break
            
            if user_input.startswith("/tier "):
                tier = user_input.split(" ", 1)[1].strip()
                twin.set_access_tier(tier)
                console.print(f"[yellow]Access tier set to: {tier}[/yellow]")
                continue
            
            if user_input.startswith("/decide "):
                question = user_input.split(" ", 1)[1].strip()
                console.print("[dim]Analyzing decision...[/dim]")
                result = twin.decide(question)
                console.print(Panel(
                    json.dumps(result, indent=2),
                    title="Decision Analysis",
                    border_style="yellow",
                ))
                continue
            
            if user_input == "/status":
                status = twin.get_status()
                console.print(Panel(
                    json.dumps(status, indent=2, default=str),
                    title="Twin Status",
                    border_style="blue",
                ))
                continue
            
            if user_input == "/temporal":
                temporal = twin.temporal_engine.get_status()
                console.print(Panel(
                    json.dumps(temporal, indent=2, default=str),
                    title="⏰ GTRBAC Temporal Engine (Bertino et al. 1998)",
                    border_style="magenta",
                ))
                continue
            
            if user_input == "/tick":
                changes = twin.temporal_engine.tick()
                mode = twin.temporal_engine.get_current_personality_mode()
                tier = twin.temporal_engine.get_current_access_tier()
                console.print(f"[magenta]⏰ Tick executed. Mode: {mode}, Tier: {tier}[/magenta]")
                if changes:
                    for c in changes:
                        console.print(f"  [yellow]→ {c['role']}: {c['old_state']} → {c['new_state']}[/yellow]")
                else:
                    console.print(f"  [dim]No state changes[/dim]")
                continue
            
            if user_input == "/clear":
                twin.clear_conversation()
                console.print("[yellow]Conversation cleared[/yellow]")
                continue
            
            # Normal message
            console.print("[dim]Thinking...[/dim]")
            response = twin.respond(user_input)
            console.print(f"\n[bold cyan]{settings.twin_name}[/bold cyan]: {response}")
            
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    interactive_mode()
