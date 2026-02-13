"""Extended tests for prompt builders."""
from app.services.prompts import (
    build_architecture_prompt,
    COMPLIANCE_EVALUATION_PROMPT,
    BICEP_GENERATION_PROMPT,
    ARCHITECTURE_REFINEMENT_PROMPT,
    COST_ESTIMATION_PROMPT,
)

def test_build_architecture_prompt_basic():
    answers = {"org_size": "medium", "industry": "technology"}
    prompt = build_architecture_prompt(answers)
    assert "medium" in prompt
    assert "technology" in prompt
    assert len(prompt) > 100

def test_build_architecture_prompt_with_unsure():
    answers = {"org_size": "_unsure", "network_topology": "hub_spoke"}
    prompt = build_architecture_prompt(answers)
    assert "_unsure" in prompt or "unsure" in prompt.lower()

def test_build_architecture_prompt_empty():
    prompt = build_architecture_prompt({})
    assert isinstance(prompt, str)
    assert len(prompt) > 0

def test_compliance_prompt_exists():
    assert len(COMPLIANCE_EVALUATION_PROMPT) > 100
    assert "compliance" in COMPLIANCE_EVALUATION_PROMPT.lower() or "framework" in COMPLIANCE_EVALUATION_PROMPT.lower()

def test_bicep_prompt_exists():
    assert len(BICEP_GENERATION_PROMPT) > 100
    assert "bicep" in BICEP_GENERATION_PROMPT.lower()

def test_refinement_prompt_exists():
    assert len(ARCHITECTURE_REFINEMENT_PROMPT) > 50

def test_cost_estimation_prompt_exists():
    assert len(COST_ESTIMATION_PROMPT) > 50
    assert "cost" in COST_ESTIMATION_PROMPT.lower()

def test_build_prompt_with_all_answers():
    answers = {
        "org_size": "enterprise",
        "industry": "healthcare",
        "compliance_frameworks": ["HIPAA", "SOC2"],
        "network_topology": "hub_spoke",
        "identity_provider": "entra_id",
        "security_level": "high",
    }
    prompt = build_architecture_prompt(answers)
    assert "enterprise" in prompt
    assert "healthcare" in prompt
