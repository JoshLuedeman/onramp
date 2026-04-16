"""Schemas for Infrastructure-as-Code syntax validation."""

from enum import Enum

from pydantic import BaseModel, Field


class IaCFormat(str, Enum):
    """Supported IaC output formats."""

    bicep = "bicep"
    terraform = "terraform"
    arm = "arm"
    pulumi_ts = "pulumi_ts"
    pulumi_py = "pulumi_py"


class IaCValidationError(BaseModel):
    """A single syntax error found during IaC validation."""

    line: int | None = None
    column: int | None = None
    message: str
    severity: str = "error"


class IaCValidationWarning(BaseModel):
    """A non-fatal issue found during IaC validation."""

    line: int | None = None
    message: str


class IaCValidationResult(BaseModel):
    """Result of validating a single IaC file."""

    is_valid: bool
    format: IaCFormat
    errors: list[IaCValidationError] = Field(default_factory=list)
    warnings: list[IaCValidationWarning] = Field(default_factory=list)
    file_name: str | None = None


class IaCValidateRequest(BaseModel):
    """Request body for single-file IaC validation."""

    code: str
    format: IaCFormat
    file_name: str | None = None


class IaCBundleFile(BaseModel):
    """A single file within a multi-file bundle."""

    code: str
    file_name: str


class IaCValidateBundleRequest(BaseModel):
    """Request body for multi-file bundle validation."""

    files: list[IaCBundleFile]
    format: IaCFormat


class IaCBundleValidationResult(BaseModel):
    """Result of validating a bundle of IaC files."""

    is_valid: bool
    format: IaCFormat
    file_results: list[IaCValidationResult] = Field(default_factory=list)
    bundle_errors: list[IaCValidationError] = Field(default_factory=list)
    bundle_warnings: list[IaCValidationWarning] = Field(default_factory=list)
