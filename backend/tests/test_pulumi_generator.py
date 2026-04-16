"""Comprehensive tests for the Pulumi code generator and API routes."""

import json
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.archetypes import get_archetype
from app.services.pulumi_generator import PulumiGenerator, pulumi_generator

client = TestClient(app)

# ---------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------

MINIMAL_ARCH: dict = {
    "management_groups": [{"name": "root", "children": []}],
    "subscriptions": [],
}

ARCH_WITH_SPOKES: dict = {
    "organization_size": "large",
    "network_topology": {
        "primary_region": "westus2",
        "hub": {"vnet_cidr": "10.0.0.0/16"},
        "spokes": [
            {"name": "prod", "vnet_cidr": "10.1.0.0/16"},
            {"name": "dev", "vnet_cidr": "10.2.0.0/16"},
        ],
    },
    "security": {"azure_firewall": True},
}

ARCH_NO_FIREWALL: dict = {
    "organization_size": "small",
    "network_topology": {
        "primary_region": "northeurope",
        "hub": {"vnet_cidr": "172.16.0.0/16"},
        "spokes": [],
    },
    "security": {"azure_firewall": False},
}


# ===============================================================
#  Unit tests — PulumiGenerator class
# ===============================================================


class TestPulumiGeneratorVersion:
    """Generator version metadata."""

    def test_version_string(self):
        assert pulumi_generator.get_version() == "1.0.0"

    def test_version_is_semver(self):
        parts = pulumi_generator.get_version().split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestPulumiGeneratorTemplates:
    """Template listing."""

    def test_list_templates_returns_list(self):
        templates = pulumi_generator.list_templates()
        assert isinstance(templates, list)

    def test_list_templates_not_empty(self):
        assert len(pulumi_generator.list_templates()) > 0

    def test_template_has_required_keys(self):
        for t in pulumi_generator.list_templates():
            assert "name" in t
            assert "description" in t
            assert "languages" in t

    def test_template_languages_contain_ts(self):
        for t in pulumi_generator.list_templates():
            assert "typescript" in t["languages"]

    def test_template_languages_contain_python(self):
        for t in pulumi_generator.list_templates():
            assert "python" in t["languages"]

    def test_landing_zone_template_exists(self):
        names = [t["name"] for t in pulumi_generator.list_templates()]
        assert "azure-landing-zone" in names


class TestValidateLanguage:
    """Language validation."""

    def test_valid_typescript(self):
        assert pulumi_generator.validate_language("typescript") == "typescript"

    def test_valid_python(self):
        assert pulumi_generator.validate_language("python") == "python"

    def test_invalid_language_raises(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            pulumi_generator.validate_language("java")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            pulumi_generator.validate_language("")

    def test_case_sensitive(self):
        with pytest.raises(ValueError):
            pulumi_generator.validate_language("TypeScript")


class TestTypeScriptGeneration:
    """TypeScript output generation."""

    def test_generates_index_ts(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "index.ts" in files

    def test_generates_pulumi_yaml(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "Pulumi.yaml" in files

    def test_generates_package_json(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "package.json" in files

    def test_generates_tsconfig(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "tsconfig.json" in files

    def test_index_imports_pulumi(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert '@pulumi/pulumi' in files["index.ts"]

    def test_index_imports_azure_native(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert '@pulumi/azure-native' in files["index.ts"]

    def test_index_creates_resource_groups(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "rg-platform" in files["index.ts"]
        assert "rg-networking" in files["index.ts"]
        assert "rg-security" in files["index.ts"]

    def test_index_includes_hub_vnet(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "vnet-hub" in files["index.ts"]

    def test_index_has_stack_exports(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "export const" in files["index.ts"]

    def test_index_includes_version_header(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "OnRamp Generated" in files["index.ts"]

    def test_package_json_is_valid_json(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        pkg = json.loads(files["package.json"])
        assert "@pulumi/azure-native" in pkg["dependencies"]

    def test_pulumi_yaml_runtime_nodejs(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "runtime: nodejs" in files["Pulumi.yaml"]

    def test_spokes_in_typescript(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "typescript")
        assert "vnet-prod" in files["index.ts"]
        assert "vnet-dev" in files["index.ts"]

    def test_peering_in_typescript(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "typescript")
        assert "hub-to-prod" in files["index.ts"]
        assert "hub-to-dev" in files["index.ts"]

    def test_firewall_in_typescript(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "typescript")
        assert "AzureFirewall" in files["index.ts"]

    def test_no_firewall_when_disabled(self):
        files = pulumi_generator.generate_from_architecture(ARCH_NO_FIREWALL, "typescript")
        assert "AzureFirewall" not in files["index.ts"]

    def test_custom_region_in_typescript(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "typescript")
        assert "westus2" in files["index.ts"]

    def test_custom_hub_cidr(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "typescript")
        assert "10.0.0.0/16" in files["index.ts"]

    def test_tags_in_typescript(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "managedBy" in files["index.ts"]
        assert "OnRamp" in files["index.ts"]


class TestPythonGeneration:
    """Python output generation."""

    def test_generates_main_py(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "__main__.py" in files

    def test_generates_pulumi_yaml(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "Pulumi.yaml" in files

    def test_generates_requirements(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "requirements.txt" in files

    def test_no_tsconfig_for_python(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "tsconfig.json" not in files

    def test_no_package_json_for_python(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "package.json" not in files

    def test_main_imports_pulumi(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "import pulumi" in files["__main__.py"]

    def test_main_imports_azure_native(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "pulumi_azure_native" in files["__main__.py"]

    def test_main_creates_resource_groups(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "rg-platform" in files["__main__.py"]
        assert "rg-networking" in files["__main__.py"]

    def test_main_includes_hub_vnet(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "vnet-hub" in files["__main__.py"]

    def test_main_has_exports(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "pulumi.export" in files["__main__.py"]

    def test_main_includes_version_header(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "OnRamp Generated" in files["__main__.py"]

    def test_requirements_has_azure_native(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "pulumi-azure-native" in files["requirements.txt"]

    def test_pulumi_yaml_runtime_python(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "runtime: python" in files["Pulumi.yaml"]

    def test_spokes_in_python(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "python")
        assert "vnet-prod" in files["__main__.py"]
        assert "vnet-dev" in files["__main__.py"]

    def test_peering_in_python(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "python")
        assert "hub-to-prod" in files["__main__.py"]

    def test_firewall_in_python(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "python")
        assert "AzureFirewall" in files["__main__.py"]

    def test_no_firewall_when_disabled_py(self):
        files = pulumi_generator.generate_from_architecture(ARCH_NO_FIREWALL, "python")
        assert "AzureFirewall" not in files["__main__.py"]

    def test_custom_region_in_python(self):
        files = pulumi_generator.generate_from_architecture(ARCH_WITH_SPOKES, "python")
        assert "westus2" in files["__main__.py"]

    def test_tags_in_python(self):
        files = pulumi_generator.generate_from_architecture(MINIMAL_ARCH, "python")
        assert "managedBy" in files["__main__.py"]
        assert "OnRamp" in files["__main__.py"]


class TestArchetypeGeneration:
    """Generate from standard archetypes."""

    def test_small_archetype_typescript(self):
        arch = get_archetype("small")
        files = pulumi_generator.generate_from_architecture(arch, "typescript")
        assert "index.ts" in files
        assert len(files) >= 3

    def test_medium_archetype_typescript(self):
        arch = get_archetype("medium")
        files = pulumi_generator.generate_from_architecture(arch, "typescript")
        assert "index.ts" in files

    def test_small_archetype_python(self):
        arch = get_archetype("small")
        files = pulumi_generator.generate_from_architecture(arch, "python")
        assert "__main__.py" in files
        assert len(files) >= 3

    def test_medium_archetype_python(self):
        arch = get_archetype("medium")
        files = pulumi_generator.generate_from_architecture(arch, "python")
        assert "__main__.py" in files


class TestSingletonBehaviour:
    """Singleton module-level instance."""

    def test_singleton_is_instance(self):
        assert isinstance(pulumi_generator, PulumiGenerator)

    def test_new_instance_works(self):
        gen = PulumiGenerator()
        files = gen.generate_from_architecture(MINIMAL_ARCH, "typescript")
        assert "index.ts" in files


class TestHelpers:
    """Internal helper methods."""

    def test_project_name_from_arch(self):
        name = pulumi_generator._project_name({"organization_size": "enterprise"})
        assert "enterprise" in name

    def test_project_name_default(self):
        name = pulumi_generator._project_name({})
        assert "org" in name

    def test_primary_region_default(self):
        region = pulumi_generator._primary_region({})
        assert region == "eastus2"

    def test_primary_region_custom(self):
        region = pulumi_generator._primary_region(
            {"network_topology": {"primary_region": "uksouth"}}
        )
        assert region == "uksouth"


# ===============================================================
#  API Route tests
# ===============================================================


class TestTemplatesRoute:
    """GET /api/pulumi/templates."""

    def test_list_templates_200(self):
        r = client.get("/api/pulumi/templates")
        assert r.status_code == 200

    def test_list_templates_has_key(self):
        r = client.get("/api/pulumi/templates")
        assert "templates" in r.json()

    def test_list_templates_is_list(self):
        data = client.get("/api/pulumi/templates").json()
        assert isinstance(data["templates"], list)

    def test_list_templates_not_empty(self):
        data = client.get("/api/pulumi/templates").json()
        assert len(data["templates"]) > 0


class TestGenerateRoute:
    """POST /api/pulumi/generate."""

    def test_generate_typescript_200(self):
        r = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "language": "typescript",
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_generate_python_200(self):
        r = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "language": "python",
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_generate_returns_files(self):
        data = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        }).json()
        assert "files" in data
        assert data["total_files"] > 0

    def test_generate_returns_language(self):
        data = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "language": "python",
            "use_ai": False,
        }).json()
        assert data["language"] == "python"

    def test_generate_default_language_is_typescript(self):
        data = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        }).json()
        assert data["language"] == "typescript"

    def test_generate_invalid_language_400(self):
        r = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "language": "go",
            "use_ai": False,
        })
        assert r.status_code == 422 or r.status_code == 400

    def test_generate_ai_generated_flag(self):
        data = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        }).json()
        assert "ai_generated" in data

    def test_generate_file_has_content(self):
        data = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        }).json()
        for f in data["files"]:
            assert len(f["content"]) > 0

    def test_generate_file_has_size_bytes(self):
        data = client.post("/api/pulumi/generate", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        }).json()
        for f in data["files"]:
            assert f["size_bytes"] > 0
            assert f["size_bytes"] == len(f["content"])


class TestDownloadRoute:
    """POST /api/pulumi/download."""

    def test_download_typescript_200(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "language": "typescript",
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_download_python_200(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "language": "python",
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_download_is_zip(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        })
        assert r.headers["content-type"] == "application/zip"

    def test_download_has_content_disposition(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        })
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_download_zip_contains_files(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "language": "typescript",
            "use_ai": False,
        })
        zf = zipfile.ZipFile(BytesIO(r.content))
        names = zf.namelist()
        assert "index.ts" in names
        assert "Pulumi.yaml" in names
        assert "package.json" in names

    def test_download_python_zip_contents(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "language": "python",
            "use_ai": False,
        })
        zf = zipfile.ZipFile(BytesIO(r.content))
        names = zf.namelist()
        assert "__main__.py" in names
        assert "Pulumi.yaml" in names
        assert "requirements.txt" in names

    def test_download_zip_non_empty_files(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "use_ai": False,
        })
        zf = zipfile.ZipFile(BytesIO(r.content))
        for name in zf.namelist():
            assert len(zf.read(name)) > 0

    def test_download_filename_typescript(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "language": "typescript",
            "use_ai": False,
        })
        assert "ts.zip" in r.headers.get("content-disposition", "")

    def test_download_filename_python(self):
        r = client.post("/api/pulumi/download", json={
            "architecture": MINIMAL_ARCH,
            "language": "python",
            "use_ai": False,
        })
        assert "py.zip" in r.headers.get("content-disposition", "")
