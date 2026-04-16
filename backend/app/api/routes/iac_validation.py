"""IaC syntax validation API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.iac_validation import (
    IaCBundleValidationResult,
    IaCValidateBundleRequest,
    IaCValidateRequest,
    IaCValidationResult,
)
from app.services.iac_validator import iac_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iac", tags=["iac-validation"])


@router.post("/validate", response_model=IaCValidationResult)
async def validate_iac(request: IaCValidateRequest) -> IaCValidationResult:
    """Validate a single IaC file for syntax correctness."""
    try:
        result = iac_validator.validate(
            code=request.code,
            fmt=request.format,
            file_name=request.file_name,
        )
        return result
    except Exception as exc:
        logger.exception("IaC validation failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/validate-bundle", response_model=IaCBundleValidationResult)
async def validate_iac_bundle(
    request: IaCValidateBundleRequest,
) -> IaCBundleValidationResult:
    """Validate a bundle of IaC files for syntax correctness."""
    try:
        file_results: list[IaCValidationResult] = []
        all_valid = True

        for bundle_file in request.files:
            result = iac_validator.validate(
                code=bundle_file.code,
                fmt=request.format,
                file_name=bundle_file.file_name,
            )
            file_results.append(result)
            if not result.is_valid:
                all_valid = False

        return IaCBundleValidationResult(
            is_valid=all_valid,
            format=request.format,
            file_results=file_results,
        )
    except Exception as exc:
        logger.exception("IaC bundle validation failed")
        raise HTTPException(status_code=500, detail=str(exc))
