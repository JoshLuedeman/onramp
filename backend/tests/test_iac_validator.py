"""Tests for IaC syntax validation service and API routes.

Covers Bicep, Terraform, ARM, Pulumi TypeScript, and Pulumi Python
validators plus the /api/iac/* HTTP endpoints.
"""

import json
import textwrap

import pytest
from fastapi.testclient import TestClient

from app.schemas.iac_validation import (
    IaCFormat,
    IaCValidateBundleRequest,
    IaCValidateRequest,
)
from app.services.iac_validator import IaCValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def validator():
    """Return a fresh IaCValidator instance."""
    return IaCValidator()


def _make_client():
    """Create a test client with the full FastAPI application."""
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Sample code snippets
# ---------------------------------------------------------------------------

VALID_BICEP = textwrap.dedent("""\
    param location string = resourceGroup().location
    param storageAccountName string

    resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
      name: storageAccountName
      location: location
      kind: 'StorageV2'
      sku: {
        name: 'Standard_LRS'
      }
    }

    output storageId string = storageAccount.id
""")

VALID_TERRAFORM = textwrap.dedent("""\
    terraform {
      required_providers {
        azurerm = {
          source  = "hashicorp/azurerm"
          version = "~> 3.0"
        }
      }
    }

    provider "azurerm" {
      features {}
    }

    resource "azurerm_resource_group" "example" {
      name     = "example-rg"
      location = "eastus"
    }

    output "rg_id" {
      value = azurerm_resource_group.example.id
    }
""")

VALID_ARM = json.dumps(
    {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {},
        "variables": {},
        "resources": [
            {
                "type": "Microsoft.Storage/storageAccounts",
                "apiVersion": "2023-01-01",
                "name": "mystorageaccount",
                "location": "[resourceGroup().location]",
                "kind": "StorageV2",
                "sku": {"name": "Standard_LRS"},
            }
        ],
        "outputs": {},
    },
    indent=2,
)

VALID_PULUMI_TS = textwrap.dedent("""\
    import * as pulumi from "@pulumi/pulumi";
    import * as azure from "@pulumi/azure-native";

    const resourceGroup = new azure.resources.ResourceGroup("myRg", {
      location: "eastus",
    });

    export const rgName = resourceGroup.name;
""")

VALID_PULUMI_PY = textwrap.dedent("""\
    import pulumi
    import pulumi_azure_native as azure

    resource_group = azure.resources.ResourceGroup("myRg",
        location="eastus",
    )

    pulumi.export("rg_name", resource_group.name)
""")


# =========================================================================
# 1. Common / dispatch
# =========================================================================


class TestCommonValidation:
    """Tests for common pre-checks applied to all formats."""

    def test_empty_file_returns_error(self, validator):
        result = validator.validate("", IaCFormat.bicep)
        assert result.is_valid is False
        assert any("empty" in e.message.lower() for e in result.errors)

    def test_whitespace_only_is_empty(self, validator):
        result = validator.validate("   \n  \n  ", IaCFormat.terraform)
        assert result.is_valid is False
        assert any("empty" in e.message.lower() for e in result.errors)

    def test_large_file_produces_warning(self, validator):
        # 600 KB file
        code = "param x string\n" * 40_000
        result = validator.validate(code, IaCFormat.bicep)
        assert any("512 KB" in w.message for w in result.warnings)

    def test_format_stored_in_result(self, validator):
        result = validator.validate(VALID_BICEP, IaCFormat.bicep)
        assert result.format == IaCFormat.bicep

    def test_file_name_stored_in_result(self, validator):
        result = validator.validate(VALID_BICEP, IaCFormat.bicep, file_name="main.bicep")
        assert result.file_name == "main.bicep"

    def test_file_name_defaults_to_none(self, validator):
        result = validator.validate(VALID_BICEP, IaCFormat.bicep)
        assert result.file_name is None


# =========================================================================
# 2. Bicep validation
# =========================================================================


class TestBicepValidation:
    """Tests for Bicep syntax validation."""

    def test_valid_bicep(self, validator):
        result = validator.validate(VALID_BICEP, IaCFormat.bicep)
        assert result.is_valid is True
        assert result.errors == []

    def test_unbalanced_opening_brace(self, validator):
        code = "resource myRes 'type@version' = {\n  name: 'foo'\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is False
        assert any("Unclosed brace" in e.message for e in result.errors)

    def test_unbalanced_closing_brace(self, validator):
        code = "param x string\n}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is False
        assert any("Unexpected closing brace" in e.message for e in result.errors)

    def test_no_structural_keywords_warns(self, validator):
        code = "// just a comment\nvar x = 42\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert any("structural keywords" in w.message.lower() for w in result.warnings)

    def test_unmatched_single_quote(self, validator):
        code = "param x string\nvar y = 'hello\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is False
        assert any("single quote" in e.message.lower() for e in result.errors)

    def test_double_quote_warning(self, validator):
        code = 'param x string\nvar y = "hello"\n'
        result = validator.validate(code, IaCFormat.bicep)
        assert any("double quotes" in w.message.lower() for w in result.warnings)

    def test_comment_lines_are_skipped_for_quotes(self, validator):
        code = "param x string\n// This isn't a problem\nresource r 'type@v' = {\n  name: 'ok'\n}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_targetScope_is_recognized(self, validator):
        code = "targetScope = 'subscription'\nparam x string\n"
        result = validator.validate(code, IaCFormat.bicep)
        # Should not warn about missing keywords because param is present
        assert not any("structural keywords" in w.message.lower() for w in result.warnings)

    def test_module_keyword_is_structural(self, validator):
        code = textwrap.dedent("""\
            module storage 'br:myregistry.azurecr.io/bicep/storage:v1' = {
              name: 'storageDeploy'
              params: {
                location: 'eastus'
              }
            }
        """)
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_output_keyword_is_structural(self, validator):
        code = "output myOutput string = 'hello'\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert not any("structural keywords" in w.message.lower() for w in result.warnings)

    def test_matched_single_quotes_are_valid(self, validator):
        code = "param x string\nvar y = 'hello world'\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert not any("single quote" in e.message.lower() for e in result.errors)

    def test_block_comment_does_not_affect_braces(self, validator):
        code = "param x string\n/* { this is a comment } */\nresource r 'type@v' = {\n  name: 'ok'\n}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_string_braces_do_not_affect_balance(self, validator):
        code = "param x string\nvar y = '{not a real brace}'\nresource r 'type@v' = {\n  name: 'ok'\n}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True


# =========================================================================
# 3. Terraform validation
# =========================================================================


class TestTerraformValidation:
    """Tests for Terraform HCL syntax validation."""

    def test_valid_terraform(self, validator):
        result = validator.validate(VALID_TERRAFORM, IaCFormat.terraform)
        assert result.is_valid is True
        assert result.errors == []

    def test_unbalanced_brace(self, validator):
        code = 'resource "azurerm_resource_group" "rg" {\n  name = "rg"\n'
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is False
        assert any("Unclosed brace" in e.message for e in result.errors)

    def test_no_top_level_blocks_warns(self, validator):
        code = "# just a comment\nfoo = bar\n"
        result = validator.validate(code, IaCFormat.terraform)
        assert any("top-level blocks" in w.message.lower() for w in result.warnings)

    def test_no_resource_blocks_warns(self, validator):
        code = textwrap.dedent("""\
            terraform {
              required_version = ">= 1.0"
            }

            provider "azurerm" {
              features {}
            }
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert any("No resource" in w.message for w in result.warnings)

    def test_unmatched_double_quote(self, validator):
        code = 'resource "azurerm_resource_group" "rg" {\n  name = "rg\n}\n'
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is False
        assert any("double quote" in e.message.lower() for e in result.errors)

    def test_comment_lines_skipped(self, validator):
        code = textwrap.dedent("""\
            # This is a comment with "quotes" and {braces}
            terraform {
              required_version = ">= 1.0"
            }
            resource "null_resource" "example" {}
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is True

    def test_data_block_counts_as_resource(self, validator):
        code = textwrap.dedent("""\
            terraform {
              required_version = ">= 1.0"
            }
            data "azurerm_subscription" "current" {}
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert not any("No resource" in w.message for w in result.warnings)

    def test_module_block_counts_as_resource(self, validator):
        code = textwrap.dedent("""\
            terraform {
              required_version = ">= 1.0"
            }
            module "network" {
              source = "./modules/network"
            }
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert not any("No resource" in w.message for w in result.warnings)

    def test_variable_and_output_blocks(self, validator):
        code = textwrap.dedent("""\
            variable "name" {
              type = string
            }
            output "value" {
              value = var.name
            }
            resource "null_resource" "x" {}
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is True

    def test_locals_block(self, validator):
        code = textwrap.dedent("""\
            locals {
              env = "dev"
            }
            resource "null_resource" "x" {}
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is True
        assert "locals" in {
            w.message for w in result.warnings
        } or result.is_valid  # Just ensure no errors

    def test_multiple_extra_closing_braces(self, validator):
        code = textwrap.dedent("""\
            resource "null_resource" "x" {
            }
            }
            }
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is False

    def test_hcl_comment_hash(self, validator):
        code = textwrap.dedent("""\
            # { not a brace
            resource "null_resource" "x" {}
        """)
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is True


# =========================================================================
# 4. ARM template validation
# =========================================================================


class TestARMValidation:
    """Tests for ARM template JSON validation."""

    def test_valid_arm(self, validator):
        result = validator.validate(VALID_ARM, IaCFormat.arm)
        assert result.is_valid is True
        assert result.errors == []

    def test_invalid_json(self, validator):
        result = validator.validate("{not valid json", IaCFormat.arm)
        assert result.is_valid is False
        assert any("Invalid JSON" in e.message for e in result.errors)

    def test_non_object_json(self, validator):
        result = validator.validate("[1, 2, 3]", IaCFormat.arm)
        assert result.is_valid is False
        assert any("JSON object" in e.message for e in result.errors)

    def test_missing_schema(self, validator):
        template = {"contentVersion": "1.0.0.0", "resources": []}
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("$schema" in e.message for e in result.errors)

    def test_missing_content_version(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "resources": [],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("contentVersion" in e.message for e in result.errors)

    def test_missing_resources(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("resources" in e.message for e in result.errors)

    def test_resources_not_array(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": "not-an-array",
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("array" in e.message.lower() for e in result.errors)

    def test_resource_missing_type(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [{"apiVersion": "2023-01-01", "name": "test"}],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("type" in e.message for e in result.errors)

    def test_resource_missing_api_version(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [{"type": "Microsoft.Storage/storageAccounts", "name": "test"}],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("apiVersion" in e.message for e in result.errors)

    def test_resource_missing_name_warns(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [
                {"type": "Microsoft.Storage/storageAccounts", "apiVersion": "2023-01-01"}
            ],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert any("name" in w.message for w in result.warnings)

    def test_unknown_top_level_field_warns(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
            "customField": "value",
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert any("Unknown top-level" in w.message for w in result.warnings)

    def test_non_standard_schema_warns(self, validator):
        template = {
            "$schema": "https://example.com/some-other-schema.json",
            "contentVersion": "1.0.0.0",
            "resources": [],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert any("known ARM" in w.message for w in result.warnings)

    def test_subscription_deployment_schema_is_valid(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is True
        assert not any("known ARM" in w.message for w in result.warnings)

    def test_schema_not_string(self, validator):
        template = {
            "$schema": 123,
            "contentVersion": "1.0.0.0",
            "resources": [],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("$schema must be a string" in e.message for e in result.errors)

    def test_content_version_not_string(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": 1,
            "resources": [],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("contentVersion must be a string" in e.message for e in result.errors)

    def test_resource_not_object(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": ["not-an-object"],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("must be an object" in e.message for e in result.errors)

    def test_empty_resources_is_valid(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is True

    def test_multiple_resources_validated(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [
                {"type": "Microsoft.Storage/storageAccounts", "apiVersion": "2023-01-01", "name": "a"},
                {"name": "b"},  # missing type and apiVersion
            ],
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is False
        assert any("resources[1]" in e.message and "type" in e.message for e in result.errors)
        assert any("resources[1]" in e.message and "apiVersion" in e.message for e in result.errors)


# =========================================================================
# 5. Pulumi TypeScript validation
# =========================================================================


class TestPulumiTSValidation:
    """Tests for Pulumi TypeScript syntax validation."""

    def test_valid_pulumi_ts(self, validator):
        result = validator.validate(VALID_PULUMI_TS, IaCFormat.pulumi_ts)
        assert result.is_valid is True
        assert result.errors == []

    def test_unbalanced_braces(self, validator):
        code = textwrap.dedent("""\
            import * as pulumi from "@pulumi/pulumi";
            const rg = new azure.resources.ResourceGroup("rg", {
              location: "eastus",
            // missing closing brace
            export const name = rg.name;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert result.is_valid is False
        assert any("brace" in e.message.lower() for e in result.errors)

    def test_unbalanced_parens(self, validator):
        code = textwrap.dedent("""\
            import * as pulumi from "@pulumi/pulumi";
            const rg = new azure.resources.ResourceGroup("rg", {
              location: "eastus",
            };
            export const name = rg.name;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert result.is_valid is False
        assert any("parenthesis" in e.message.lower() for e in result.errors)

    def test_no_imports_warns(self, validator):
        code = textwrap.dedent("""\
            const x = 42;
            export const value = x;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert any("No import" in w.message for w in result.warnings)

    def test_no_pulumi_import_warns(self, validator):
        code = textwrap.dedent("""\
            import * as fs from "fs";
            export const x = 42;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert any("@pulumi" in w.message for w in result.warnings)

    def test_no_export_warns(self, validator):
        code = textwrap.dedent("""\
            import * as pulumi from "@pulumi/pulumi";
            const rg = new pulumi.StackReference("ref");
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert any("export" in w.message.lower() for w in result.warnings)

    def test_unmatched_backtick(self, validator):
        code = textwrap.dedent("""\
            import * as pulumi from "@pulumi/pulumi";
            const name = `hello
            export const x = name;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert result.is_valid is False
        assert any("backtick" in e.message.lower() for e in result.errors)

    def test_comment_lines_skipped_for_backtick(self, validator):
        code = textwrap.dedent("""\
            import * as pulumi from "@pulumi/pulumi";
            // this ` backtick is fine
            export const x = 42;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert not any("backtick" in e.message.lower() for e in result.errors)

    def test_balanced_template_literal(self, validator):
        code = textwrap.dedent("""\
            import * as pulumi from "@pulumi/pulumi";
            const name = `hello-${world}`;
            export const x = name;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert result.is_valid is True

    def test_import_with_no_space(self, validator):
        code = textwrap.dedent("""\
            import{something} from "@pulumi/pulumi";
            export const x = 42;
        """)
        result = validator.validate(code, IaCFormat.pulumi_ts)
        assert not any("No import" in w.message for w in result.warnings)


# =========================================================================
# 6. Pulumi Python validation
# =========================================================================


class TestPulumiPyValidation:
    """Tests for Pulumi Python syntax validation."""

    def test_valid_pulumi_py(self, validator):
        result = validator.validate(VALID_PULUMI_PY, IaCFormat.pulumi_py)
        assert result.is_valid is True
        assert result.errors == []

    def test_syntax_error(self, validator):
        code = textwrap.dedent("""\
            import pulumi
            def broken(
                pulumi.export("x", 1)
        """)
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert result.is_valid is False
        assert any("syntax error" in e.message.lower() for e in result.errors)

    def test_no_imports_warns(self, validator):
        code = "x = 42\npulumi.export('x', x)\n"
        # Note: this will also fail ast.parse since pulumi isn't defined,
        # but ast.parse doesn't check name resolution. Let's test with valid syntax.
        code = "x = 42\n"
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert any("No import" in w.message for w in result.warnings)

    def test_no_pulumi_import_warns(self, validator):
        code = textwrap.dedent("""\
            import os
            x = os.getcwd()
        """)
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert any("pulumi" in w.message.lower() for w in result.warnings)

    def test_mixed_indentation_warns(self, validator):
        # Mix tabs and spaces across different functions (both are valid Python
        # individually, but mixing them in one file is a bad practice).
        code = "import pulumi\ndef foo():\n\tx = 1\n\treturn x\ndef bar():\n    y = 2\n    return y\npulumi.export('x', 1)\n"
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert any("Mixed tabs" in w.message for w in result.warnings)

    def test_no_export_warns(self, validator):
        code = textwrap.dedent("""\
            import pulumi
            rg = "hello"
        """)
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert any("export" in w.message.lower() for w in result.warnings)

    def test_from_import_detected(self, validator):
        code = textwrap.dedent("""\
            from pulumi_azure_native import resources
            rg = resources.ResourceGroup("rg", location="eastus")
            import pulumi
            pulumi.export("rg", rg.name)
        """)
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert result.is_valid is True
        assert not any("No import" in w.message for w in result.warnings)
        assert not any("No pulumi" in w.message for w in result.warnings)

    def test_syntax_error_line_number(self, validator):
        code = "import pulumi\nx = (\n"
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert result.is_valid is False
        assert result.errors[0].line is not None

    def test_consistent_space_indentation(self, validator):
        code = textwrap.dedent("""\
            import pulumi

            def create():
                x = 1
                y = 2
                return x + y

            pulumi.export("val", create())
        """)
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert not any("Mixed tabs" in w.message for w in result.warnings)

    def test_consistent_tab_indentation(self, validator):
        code = "import pulumi\ndef create():\n\tx = 1\n\ty = 2\n\treturn x + y\npulumi.export('v', create())\n"
        result = validator.validate(code, IaCFormat.pulumi_py)
        assert not any("Mixed tabs" in w.message for w in result.warnings)


# =========================================================================
# 7. Edge cases
# =========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_only_comments_bicep(self, validator):
        code = "// just a comment\n// another comment\n"
        result = validator.validate(code, IaCFormat.bicep)
        # Valid syntax but warns about missing keywords
        assert result.is_valid is True
        assert any("structural keywords" in w.message.lower() for w in result.warnings)

    def test_only_comments_terraform(self, validator):
        code = "# just a comment\n# another comment\n"
        result = validator.validate(code, IaCFormat.terraform)
        assert result.is_valid is True
        assert any("top-level blocks" in w.message.lower() for w in result.warnings)

    def test_single_line_file(self, validator):
        code = "param x string"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_deeply_nested_braces(self, validator):
        code = "resource r 'type@v' = {\n" + "  a: {\n" * 20 + "  b: 1\n" + "  }\n" * 20 + "}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_arm_deeply_nested_json(self, validator):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
            "variables": {"a": {"b": {"c": {"d": {"e": "deep"}}}}},
        }
        result = validator.validate(json.dumps(template), IaCFormat.arm)
        assert result.is_valid is True

    def test_unicode_content(self, validator):
        code = "param name string // 名前パラメータ\nresource r 'type@v' = {\n  name: 'café'\n}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_crlf_line_endings(self, validator):
        code = "param x string\r\nresource r 'type@v' = {\r\n  name: 'ok'\r\n}\r\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_trailing_newlines(self, validator):
        code = VALID_BICEP + "\n\n\n\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_no_trailing_newline(self, validator):
        code = "param x string"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True

    def test_arm_empty_json_object(self, validator):
        result = validator.validate("{}", IaCFormat.arm)
        assert result.is_valid is False

    def test_arm_json_array_of_objects(self, validator):
        result = validator.validate("[{}]", IaCFormat.arm)
        assert result.is_valid is False

    def test_bicep_string_with_braces_inside(self, validator):
        code = "param x string\nvar y = 'hello {world} bye'\nresource r 'type@v' = {\n  name: y\n}\n"
        result = validator.validate(code, IaCFormat.bicep)
        assert result.is_valid is True


# =========================================================================
# 8. Bundle validation
# =========================================================================


class TestBundleValidation:
    """Tests for multi-file bundle validation via the service."""

    def test_all_valid_bundle(self, validator):
        files = [
            ("main.tf", VALID_TERRAFORM),
            ("variables.tf", 'variable "name" {\n  type = string\n}\n'),
        ]
        results = []
        for name, code in files:
            results.append(validator.validate(code, IaCFormat.terraform, file_name=name))
        assert all(r.is_valid for r in results)

    def test_one_invalid_in_bundle(self, validator):
        files = [
            ("main.tf", VALID_TERRAFORM),
            ("broken.tf", 'resource "x" "y" {\n'),  # unclosed brace
        ]
        results = []
        for name, code in files:
            results.append(validator.validate(code, IaCFormat.terraform, file_name=name))
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[1].file_name == "broken.tf"

    def test_empty_bundle(self, validator):
        results = []
        assert len(results) == 0  # No files to validate

    def test_bundle_preserves_file_names(self, validator):
        files = [
            ("main.bicep", VALID_BICEP),
            ("modules/storage.bicep", "param x string\nresource r 'type@v' = {\n  name: 'ok'\n}\n"),
        ]
        results = []
        for name, code in files:
            results.append(validator.validate(code, IaCFormat.bicep, file_name=name))
        assert results[0].file_name == "main.bicep"
        assert results[1].file_name == "modules/storage.bicep"


# =========================================================================
# 9. API route tests
# =========================================================================


class TestIaCValidationRoutes:
    """Tests for the /api/iac/* HTTP endpoints."""

    def test_validate_valid_bicep(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": VALID_BICEP, "format": "bicep"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["format"] == "bicep"
        assert data["errors"] == []

    def test_validate_invalid_bicep(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": "resource r 'type@v' = {\n", "format": "bicep"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_with_file_name(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": VALID_BICEP, "format": "bicep", "file_name": "main.bicep"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_name"] == "main.bicep"

    def test_validate_empty_code(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": "", "format": "terraform"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False

    def test_validate_arm_template(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": VALID_ARM, "format": "arm"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True

    def test_validate_pulumi_ts(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": VALID_PULUMI_TS, "format": "pulumi_ts"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True

    def test_validate_pulumi_py(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": VALID_PULUMI_PY, "format": "pulumi_py"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True

    def test_validate_invalid_format_rejected(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate",
            json={"code": "hello", "format": "yaml"},
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_validate_bundle_all_valid(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate-bundle",
            json={
                "files": [
                    {"code": VALID_TERRAFORM, "file_name": "main.tf"},
                    {"code": 'variable "x" {\n  type = string\n}\nresource "null_resource" "y" {}\n', "file_name": "vars.tf"},
                ],
                "format": "terraform",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert len(data["file_results"]) == 2
        assert all(fr["is_valid"] for fr in data["file_results"])

    def test_validate_bundle_with_invalid_file(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate-bundle",
            json={
                "files": [
                    {"code": VALID_TERRAFORM, "file_name": "main.tf"},
                    {"code": 'resource "x" "y" {\n', "file_name": "broken.tf"},
                ],
                "format": "terraform",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert data["file_results"][0]["is_valid"] is True
        assert data["file_results"][1]["is_valid"] is False
        assert data["file_results"][1]["file_name"] == "broken.tf"

    def test_validate_bundle_empty_files(self):
        client = _make_client()
        resp = client.post(
            "/api/iac/validate-bundle",
            json={"files": [], "format": "bicep"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["file_results"] == []


# =========================================================================
# 10. Singleton pattern
# =========================================================================


class TestSingleton:
    """Verify the module-level singleton is accessible."""

    def test_singleton_import(self):
        from app.services.iac_validator import iac_validator

        assert isinstance(iac_validator, IaCValidator)

    def test_singleton_validates(self):
        from app.services.iac_validator import iac_validator

        result = iac_validator.validate(VALID_BICEP, IaCFormat.bicep)
        assert result.is_valid is True


# =========================================================================
# 11. Schema model tests
# =========================================================================


class TestSchemaModels:
    """Tests for the Pydantic schema models themselves."""

    def test_iac_format_enum_values(self):
        assert IaCFormat.bicep.value == "bicep"
        assert IaCFormat.terraform.value == "terraform"
        assert IaCFormat.arm.value == "arm"
        assert IaCFormat.pulumi_ts.value == "pulumi_ts"
        assert IaCFormat.pulumi_py.value == "pulumi_py"

    def test_validate_request_model(self):
        req = IaCValidateRequest(code="param x string", format=IaCFormat.bicep)
        assert req.code == "param x string"
        assert req.format == IaCFormat.bicep
        assert req.file_name is None

    def test_validate_request_with_file_name(self):
        req = IaCValidateRequest(
            code="param x string", format=IaCFormat.bicep, file_name="main.bicep"
        )
        assert req.file_name == "main.bicep"

    def test_bundle_request_model(self):
        req = IaCValidateBundleRequest(
            files=[{"code": "param x string", "file_name": "main.bicep"}],
            format=IaCFormat.bicep,
        )
        assert len(req.files) == 1
        assert req.format == IaCFormat.bicep
