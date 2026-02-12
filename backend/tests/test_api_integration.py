"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# --- Health ---
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# --- Users ---
def test_user_me():
    r = client.get("/api/users/me")
    assert r.status_code == 200
    assert r.json()["name"] == "Development User"


def test_user_projects():
    r = client.get("/api/users/me/projects")
    assert r.status_code == 200
    assert "projects" in r.json()


# --- Questionnaire ---
def test_questionnaire_categories():
    r = client.get("/api/questionnaire/categories")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert len(cats) > 0


def test_questionnaire_all_questions():
    r = client.get("/api/questionnaire/questions")
    assert r.status_code == 200
    assert len(r.json()["questions"]) > 20


def test_questionnaire_next_empty():
    r = client.post("/api/questionnaire/next", json={"answers": {}})
    assert r.status_code == 200
    assert r.json()["complete"] is False
    assert r.json()["question"] is not None


def test_questionnaire_progress():
    r = client.post(
        "/api/questionnaire/progress",
        json={"answers": {"org_name": "Test", "org_size": "small"}},
    )
    assert r.status_code == 200
    assert r.json()["answered"] == 2


# --- Architecture ---
def test_architecture_archetypes():
    r = client.get("/api/architecture/archetypes")
    assert r.status_code == 200
    assert len(r.json()["archetypes"]) == 3


def test_architecture_generate():
    r = client.post(
        "/api/architecture/generate",
        json={
            "answers": {"org_size": "small", "primary_region": "westus2"},
            "use_ai": False,
        },
    )
    assert r.status_code == 200
    arch = r.json()["architecture"]
    assert arch["organization_size"] == "small"
    assert arch["network_topology"]["primary_region"] == "westus2"


# --- Compliance ---
def test_compliance_frameworks():
    r = client.get("/api/compliance/frameworks")
    assert r.status_code == 200
    assert len(r.json()["frameworks"]) == 6


def test_compliance_framework_detail():
    r = client.get("/api/compliance/frameworks/HIPAA")
    assert r.status_code == 200
    assert "controls" in r.json()


def test_compliance_controls():
    r = client.post("/api/compliance/controls", json=["SOC2", "HIPAA"])
    assert r.status_code == 200
    assert r.json()["total"] > 0


# --- Scoring ---
def test_scoring_evaluate():
    # First generate an architecture
    arch_r = client.post(
        "/api/architecture/generate",
        json={"answers": {"org_size": "medium"}, "use_ai": False},
    )
    arch = arch_r.json()["architecture"]

    # Score it
    r = client.post(
        "/api/scoring/evaluate",
        json={"architecture": arch, "frameworks": ["SOC2", "HIPAA"]},
    )
    assert r.status_code == 200
    result = r.json()
    assert "overall_score" in result
    assert len(result["frameworks"]) == 2


# --- Bicep ---
def test_bicep_templates():
    r = client.get("/api/bicep/templates")
    assert r.status_code == 200
    assert len(r.json()["templates"]) >= 4


def test_bicep_template_detail():
    r = client.get("/api/bicep/templates/hub-networking")
    assert r.status_code == 200
    assert "vnet-hub" in r.json()["content"]


def test_bicep_generate():
    arch_r = client.post(
        "/api/architecture/generate",
        json={"answers": {"org_size": "small"}, "use_ai": False},
    )
    arch = arch_r.json()["architecture"]

    r = client.post("/api/bicep/generate", json={"architecture": arch})
    assert r.status_code == 200
    files = r.json()["files"]
    assert len(files) >= 5
    file_names = [f["name"] for f in files]
    assert "main.bicep" in file_names


# --- Deployment ---
def test_deployment_validate():
    r = client.post(
        "/api/deployment/validate",
        json={"subscription_id": "test-sub-123", "region": "eastus2"},
    )
    assert r.status_code == 200
    # In dev mode, credentials won't be valid
    assert r.json()["subscription_id"] == "test-sub-123"


# --- Full Flow Integration ---
def test_full_flow_questionnaire_to_bicep():
    """Test the complete flow: questionnaire -> architecture -> scoring -> bicep."""
    # 1. Get first question
    r = client.post("/api/questionnaire/next", json={"answers": {}})
    assert r.status_code == 200
    first_question = r.json()["question"]
    assert first_question is not None

    # 2. Generate architecture with answers
    answers = {
        "org_name": "Contoso",
        "org_size": "medium",
        "primary_region": "eastus2",
        "network_topology": "hub_spoke",
        "compliance_frameworks": ["soc2"],
    }
    r = client.post(
        "/api/architecture/generate",
        json={"answers": answers, "use_ai": False},
    )
    assert r.status_code == 200
    arch = r.json()["architecture"]
    assert arch["organization_size"] == "medium"

    # 3. Score compliance
    r = client.post(
        "/api/scoring/evaluate",
        json={"architecture": arch, "frameworks": ["SOC2"]},
    )
    assert r.status_code == 200
    assert r.json()["overall_score"] >= 0

    # 4. Generate Bicep
    r = client.post("/api/bicep/generate", json={"architecture": arch})
    assert r.status_code == 200
    assert len(r.json()["files"]) >= 5
