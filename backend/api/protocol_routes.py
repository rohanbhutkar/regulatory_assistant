"""
API routes for protocol generation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from agents.protocol_authoring_agent import protocol_authoring_agent

router = APIRouter()

# Request/Response Models
class ProtocolGenerationRequest(BaseModel):
    section_type: Optional[str] = None
    trials: List[Dict[str, Any]] = []
    reference_info: Optional[str] = ""
    study_context: Optional[Dict[str, Any]] = {}
    criteria_type: Optional[str] = None

class ProtocolGenerationResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    section_type: Optional[str] = None
    message: Optional[str] = None
    trials_used: Optional[int] = None

# Generic section generation
@router.post("/generate-section", response_model=ProtocolGenerationResponse)
async def generate_protocol_section(request: ProtocolGenerationRequest):
    """Generate a specific protocol section using reference trials"""
    try:
        if not request.section_type:
            raise HTTPException(status_code=400, detail="section_type is required")
        
        print(f"📝 Generating section: {request.section_type}")
        print(f"   Trials: {len(request.trials)}")
        print(f"   Reference info: {len(request.reference_info or '')} chars")
        
        content = await protocol_authoring_agent.generate_section(
            section_type=request.section_type,
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type=request.section_type,
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating section: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Protocol Title Generation
@router.post("/generate-title", response_model=ProtocolGenerationResponse)
async def generate_protocol_title(request: ProtocolGenerationRequest):
    """Generate protocol title with full and short versions"""
    try:
        print("📝 Generating protocol title")
        print(f"   Trials: {len(request.trials)}")
        
        content = await protocol_authoring_agent.generate_section(
            section_type='title',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='title',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating title: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Objectives Generation
@router.post("/generate-objectives", response_model=ProtocolGenerationResponse)
async def generate_objectives(request: ProtocolGenerationRequest):
    """Generate study objectives"""
    try:
        print("📝 Generating objectives")
        print(f"   Trials: {len(request.trials)}")
        
        content = await protocol_authoring_agent.generate_section(
            section_type='objectives',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='objectives',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating objectives: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints Generation
@router.post("/generate-endpoints", response_model=ProtocolGenerationResponse)
async def generate_endpoints(request: ProtocolGenerationRequest):
    """Generate study endpoints (primary and secondary)"""
    try:
        print("📝 Generating endpoints")
        print(f"   Trials: {len(request.trials)}")
        
        # Generate secondary_endpoints section which includes both primary and secondary
        content = await protocol_authoring_agent.generate_section(
            section_type='secondary_endpoints',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='secondary_endpoints',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating endpoints: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Eligibility Criteria Generation
@router.post("/generate-criteria", response_model=ProtocolGenerationResponse)
async def generate_criteria(request: ProtocolGenerationRequest):
    """Generate eligibility criteria (inclusion and exclusion)"""
    try:
        print("📝 Generating eligibility criteria")
        print(f"   Trials: {len(request.trials)}")
        
        # Generate both inclusion and exclusion criteria
        inclusion_content = await protocol_authoring_agent.generate_section(
            section_type='inclusion_criteria',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        exclusion_content = await protocol_authoring_agent.generate_section(
            section_type='exclusion_criteria',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        # Combine both sections
        combined_content = f"""## Inclusion Criteria

{inclusion_content}

## Exclusion Criteria

{exclusion_content}"""
        
        return ProtocolGenerationResponse(
            success=True,
            content=combined_content,
            section_type='eligibility_criteria',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating criteria: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Schedule of Activities Generation
@router.post("/generate-soa", response_model=ProtocolGenerationResponse)
async def generate_soa(request: ProtocolGenerationRequest):
    """Generate Schedule of Activities"""
    try:
        print("📝 Generating Schedule of Activities")
        print(f"   Trials: {len(request.trials)}")
        
        content = await protocol_authoring_agent.generate_section(
            section_type='schedule_of_activities',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='schedule_of_activities',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating SoA: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Study Design Generation
@router.post("/generate-study-design", response_model=ProtocolGenerationResponse)
async def generate_study_design(request: ProtocolGenerationRequest):
    """Generate overall study design with arms and participant distribution"""
    try:
        print("📝 Generating study design")
        print(f"   Trials: {len(request.trials)}")
        print(f"   Study context: {request.study_context}")
        
        # Build enhanced reference info with study context
        context_str = ""
        if request.study_context:
            context_parts = []
            if 'indication' in request.study_context:
                context_parts.append(f"Indication: {request.study_context['indication']}")
            if 'phase' in request.study_context:
                context_parts.append(f"Phase: {request.study_context['phase']}")
            if 'drugName' in request.study_context:
                context_parts.append(f"Drug Name: {request.study_context['drugName']}")
            elif 'compound' in request.study_context:
                context_parts.append(f"Drug Name: {request.study_context['compound']}")
            if 'totalParticipants' in request.study_context:
                context_parts.append(f"Target Enrollment: {request.study_context['totalParticipants']}")
            
            if context_parts:
                context_str = "\n\n**STUDY CONTEXT:**\n" + "\n".join(context_parts)
        
        enhanced_reference_info = (request.reference_info or "") + context_str
        
        content = await protocol_authoring_agent.generate_section(
            section_type='study_design',
            trials=request.trials,
            reference_info=enhanced_reference_info
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='study_design',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating study design: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Study Schema Generation
@router.post("/generate-schema", response_model=ProtocolGenerationResponse)
async def generate_schema(request: ProtocolGenerationRequest):
    """Generate study schema"""
    try:
        print("📝 Generating study schema")
        print(f"   Trials: {len(request.trials)}")
        
        content = await protocol_authoring_agent.generate_section(
            section_type='schema',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='schema',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating schema: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Rationale Generation
@router.post("/generate-rationale", response_model=ProtocolGenerationResponse)
async def generate_rationale(request: ProtocolGenerationRequest):
    """Generate study rationale"""
    try:
        print("📝 Generating rationale")
        print(f"   Trials: {len(request.trials)}")
        
        content = await protocol_authoring_agent.generate_section(
            section_type='rationale',
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        
        return ProtocolGenerationResponse(
            success=True,
            content=content,
            section_type='rationale',
            trials_used=len(request.trials)
        )
        
    except Exception as e:
        import traceback
        print(f"Error generating rationale: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Full Protocol Generation
@router.post("/generate-full", response_model=Dict[str, Any])
async def generate_full_protocol(request: ProtocolGenerationRequest):
    """Generate complete protocol with all sections"""
    try:
        print("📝 Generating full protocol")
        print(f"   Trials: {len(request.trials)}")
        
        sections = await protocol_authoring_agent.generate_full_protocol(
            trials=request.trials,
            reference_info=request.reference_info or ""
        )
        return {
            "success": True,
            "sections": sections,
            "trials_used": len(request.trials)
        }
        
    except Exception as e:
        import traceback
        print(f"Error generating full protocol: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USDM EXPORT
# ============================================================================

class USDMExportRequest(BaseModel):
    """Request model for USDM export"""
    studyContext: Dict[str, Any]
    studyDesign: Optional[Dict[str, Any]] = None
    objectives: Optional[List[Dict[str, Any]]] = []
    endpoints: Optional[List[Dict[str, Any]]] = []
    inclusionCriteria: Optional[List[Dict[str, Any]]] = []
    exclusionCriteria: Optional[List[Dict[str, Any]]] = []
    selectedSites: Optional[List[Dict[str, Any]]] = []
    selectedTrials: Optional[List[Dict[str, Any]]] = []
    protocolSections: Optional[Dict[str, str]] = {}


class USDMExportResponse(BaseModel):
    """Response model for USDM export"""
    success: bool
    usdm: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    message: str


@router.post("/export-usdm", response_model=USDMExportResponse)
async def export_to_usdm(request: USDMExportRequest):
    """
    Export study design to USDM v4.0 format.
    
    This endpoint converts the current study design to a fully compliant
    CDISC USDM JSON structure with validation.
    
    Returns:
        USDMExportResponse with USDM JSON and validation report
    """
    try:
        import sys
        from pathlib import Path
        
        # Add backend directory to path if not already there
        backend_dir = Path(__file__).parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        from utils.usdm_converter import USDMConverter
        
        print("📤 Exporting study to USDM format")
        print(f"   Study: {request.studyContext.get('studyTitle', 'Untitled')}")
        print(f"   Phase: {request.studyContext.get('phase')}")
        print(f"   Indication: {request.studyContext.get('indication')}")
        print(f"   Objectives: {len(request.objectives) if request.objectives else 0}")
        print(f"   Endpoints: {len(request.endpoints) if request.endpoints else 0}")
        print(f"   Inclusion criteria: {len(request.inclusionCriteria) if request.inclusionCriteria else 0}")
        print(f"   Exclusion criteria: {len(request.exclusionCriteria) if request.exclusionCriteria else 0}")
        
        # Convert request to dict
        study_data = {
            'studyContext': request.studyContext,
            'studyDesign': request.studyDesign,
            'objectives': request.objectives,
            'endpoints': request.endpoints,
            'inclusionCriteria': request.inclusionCriteria,
            'exclusionCriteria': request.exclusionCriteria,
            'selectedSites': request.selectedSites,
            'selectedTrials': request.selectedTrials,
            'protocolSections': request.protocolSections
        }
        
        # Initialize converter
        converter = USDMConverter()
        
        # Convert to USDM
        usdm_output = converter.convert(study_data)
        
        print(f"✅ USDM conversion successful")
        print(f"   Study name: {usdm_output.get('study', {}).get('name')}")
        versions = usdm_output.get('study', {}).get('versions', [])
        print(f"   Versions: {len(versions)}")
        if versions:
            designs = versions[0].get('studyDesigns', [])
            print(f"   Study designs: {len(designs)}")
            if designs:
                arms = designs[0].get('arms', [])
                epochs = designs[0].get('epochs', [])
                print(f"   Arms: {len(arms)}")
                print(f"   Epochs: {len(epochs)}")
        
        # Validate
        validation_report = converter.validate(usdm_output)
        
        print(f"📋 Validation complete")
        print(f"   Valid: {validation_report.get('valid')}")
        print(f"   Errors: {validation_report.get('errors', 0)}")
        print(f"   Warnings: {validation_report.get('warnings', 0)}")
        print(f"   Info: {validation_report.get('info', 0)}")
        
        return USDMExportResponse(
            success=True,
            usdm=usdm_output,
            validation=validation_report,
            message=f"USDM export successful. {validation_report.get('errors', 0)} errors, {validation_report.get('warnings', 0)} warnings."
        )
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"❌ Error exporting to USDM: {error_msg}")
        print(traceback.format_exc())
        
        return USDMExportResponse(
            success=False,
            message=f"USDM export failed: {error_msg}"
        )

