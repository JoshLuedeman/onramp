"""IoT landing zone accelerator API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.iot import (
    IoTArchitectureRequest,
    IoTArchitectureResponse,
    IoTBestPracticesListResponse,
    IoTBicepRequest,
    IoTBicepResponse,
    IoTQuestionsListResponse,
    IoTReferenceArchitecturesListResponse,
    IoTSizingRequest,
    IoTSizingResponse,
    IoTSkuRecommendationRequest,
    IoTSkuRecommendationResponse,
    IoTValidationRequest,
    IoTValidationResponse,
)
from app.services.iot_accelerator import iot_accelerator
from app.services.iot_bicep import iot_bicep_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/accelerators/iot", tags=["iot-accelerator"]
)


# ── Information Endpoints ────────────────────────────────────────────────────


@router.get(
    "/questions",
    response_model=IoTQuestionsListResponse,
)
async def list_questions(
    user: dict = Depends(get_current_user),
):
    """List IoT-specific questionnaire questions."""
    questions = iot_accelerator.get_questions()
    return {"questions": questions, "total": len(questions)}


@router.get(
    "/best-practices",
    response_model=IoTBestPracticesListResponse,
)
async def list_best_practices(
    user: dict = Depends(get_current_user),
):
    """List IoT best practices and recommendations."""
    practices = iot_accelerator.get_best_practices()
    return {
        "best_practices": practices,
        "total": len(practices),
    }


@router.get(
    "/reference-architectures",
    response_model=IoTReferenceArchitecturesListResponse,
)
async def list_reference_architectures(
    user: dict = Depends(get_current_user),
):
    """List IoT reference architectures."""
    archs = iot_accelerator.get_reference_architectures()
    return {"architectures": archs, "total": len(archs)}


# ── Recommendation & Architecture ────────────────────────────────────────────


@router.post(
    "/sku-recommendations",
    response_model=IoTSkuRecommendationResponse,
)
async def get_sku_recommendations(
    request: IoTSkuRecommendationRequest,
    user: dict = Depends(get_current_user),
):
    """Get IoT Hub SKU recommendations based on answers."""
    result = iot_accelerator.get_sku_recommendations(
        request.answers
    )
    return result


@router.post(
    "/architecture",
    response_model=IoTArchitectureResponse,
)
async def generate_architecture(
    request: IoTArchitectureRequest,
    user: dict = Depends(get_current_user),
):
    """Generate an IoT architecture from questionnaire answers."""
    result = iot_accelerator.generate_architecture(
        request.answers
    )
    return result


@router.post(
    "/sizing",
    response_model=IoTSizingResponse,
)
async def estimate_sizing(
    request: IoTSizingRequest,
    user: dict = Depends(get_current_user),
):
    """Estimate IoT infrastructure sizing."""
    result = iot_accelerator.estimate_sizing(
        request.requirements
    )
    return result


@router.post(
    "/validate",
    response_model=IoTValidationResponse,
)
async def validate_architecture(
    request: IoTValidationRequest,
    user: dict = Depends(get_current_user),
):
    """Validate an IoT architecture for completeness."""
    result = iot_accelerator.validate_architecture(
        request.architecture
    )
    return result


# ── Bicep Generation ─────────────────────────────────────────────────────────


@router.post(
    "/bicep",
    response_model=IoTBicepResponse,
)
async def generate_bicep(
    request: IoTBicepRequest,
    user: dict = Depends(get_current_user),
):
    """Generate Bicep template for IoT resources."""
    generators = {
        "iot_hub": iot_bicep_service.generate_iot_hub,
        "dps": iot_bicep_service.generate_dps,
        "event_hub": iot_bicep_service.generate_event_hub,
        "stream_analytics": (
            iot_bicep_service.generate_stream_analytics
        ),
        "storage": iot_bicep_service.generate_storage,
        "adx": iot_bicep_service.generate_adx,
        "full_stack": (
            iot_bicep_service.generate_full_iot_stack
        ),
    }
    generator = generators.get(request.template_type)
    if generator is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown template_type"
                f" '{request.template_type}'."
                f" Valid types:"
                f" {', '.join(generators.keys())}"
            ),
        )
    bicep_template = generator(request.config)
    descriptions = {
        "iot_hub": (
            "Azure IoT Hub for device connectivity"
        ),
        "dps": (
            "Device Provisioning Service for enrollment"
        ),
        "event_hub": (
            "Event Hubs for high-throughput ingestion"
        ),
        "stream_analytics": (
            "Stream Analytics for real-time processing"
        ),
        "storage": "Storage account for telemetry data",
        "adx": (
            "Azure Data Explorer for time series analytics"
        ),
        "full_stack": "Complete IoT landing zone stack",
    }
    return {
        "template_type": request.template_type,
        "bicep_template": bicep_template,
        "description": descriptions.get(
            request.template_type, ""
        ),
    }
