"""
Smoke test — Verifies Parallax can be assembled and all components connect.

Does NOT require an LLM API key. Tests the wiring, not the inference.

Usage:
    python tests/test_smoke.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_config_loads():
    """Config loader reads YAML + env without crashing."""
    from config_loader import settings, load_yaml_config
    config = load_yaml_config()
    assert settings.faith_threshold == 0.45
    assert config.get("twin", {}).get("name") == "Ade"
    print("  ✓ Config loads correctly")


def test_temporal_engine_creates():
    """Default twin engine creates with all roles and constraints."""
    from temporal_engine import create_default_twin_engine
    engine = create_default_twin_engine(tick_seconds=60)
    # tick() returns a list of changes; engine has roles internally
    engine.tick()
    assert len(engine._roles) > 0
    print(f"  ✓ Temporal engine: {len(engine._roles)} roles registered")


def test_reasoning_engine():
    """Reasoning engine initializes and can build prompts."""
    from phase2_logic_twin.twin_core.reasoning import ReasoningEngine
    re = ReasoningEngine(faith_threshold=0.45)
    prompt = re.build_reasoning_prompt("Should I accept this offer?", context="Job change")
    assert "arguments" in prompt.lower()
    assert "0.45" in prompt
    print("  ✓ Reasoning engine builds prompts")


def test_personality_engine():
    """Personality engine generates system prompts."""
    from phase2_logic_twin.twin_core.personality import PersonalityEngine
    pe = PersonalityEngine()
    prompt = pe.generate_system_prompt(access_tier="friends", context="evening chat")
    assert isinstance(prompt, str)
    assert len(prompt) > 50
    print("  ✓ Personality engine generates prompts")


def test_twin_assembles():
    """The full DigitalTwin object assembles without requiring an API key."""
    from phase2_logic_twin.twin import DigitalTwin
    # Don't call respond() — that needs an LLM + chromadb. Just verify core wiring.
    twin = DigitalTwin()
    assert twin.temporal_engine is not None
    assert twin.reasoning is not None
    assert twin.personality is not None
    status = twin.get_status()
    assert "twin_name" in status
    print(f"  ✓ Twin assembles: {status['twin_name']}, temporal engine connected")


def test_divergence_tracker():
    """Divergence tracker can initialize and report."""
    from phase4_platform.measurement.divergence_tracker import DivergenceTracker
    dt = DivergenceTracker()
    analysis = dt.get_full_analysis()
    assert isinstance(analysis, dict)
    print("  ✓ Divergence tracker operational")


def test_llm_provider_registry():
    """LLM provider registry lists all providers."""
    from llm_provider import PROVIDERS, check_available_providers
    assert "ollama" in PROVIDERS
    assert "anthropic" in PROVIDERS
    assert "openai" in PROVIDERS
    available = check_available_providers()
    print(f"  ✓ LLM providers: {available}")


def test_ingestors_import():
    """All data ingestors import cleanly."""
    from phase1_data_pipeline.ingestors.messages import SlackIngestor, WhatsAppIngestor, DiscordIngestor
    from phase1_data_pipeline.ingestors.documents import PDFIngestor, DocxIngestor, MarkdownIngestor, CodeIngestor
    from phase1_data_pipeline.ingestors.photos import PhotoIngestor
    print("  ✓ All ingestors import (Slack, WhatsApp, Discord, PDF, DOCX, Markdown, Code, Photo)")


if __name__ == "__main__":
    print("=" * 60)
    print("🔬 Parallax Smoke Tests")
    print("   Verifying system assembly (no API keys needed)")
    print("=" * 60)
    print()

    tests = [
        test_config_loads,
        test_temporal_engine_creates,
        test_reasoning_engine,
        test_personality_engine,
        test_twin_assembles,
        test_divergence_tracker,
        test_llm_provider_registry,
        test_ingestors_import,
    ]

    passed = 0
    failed = 0

    for test in tests:
        name = test.__name__.replace("test_", "").replace("_", " ").title()
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)
