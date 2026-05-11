"""
USDM Converter
Converts Study Designer data to CDISC USDM v4.0 format
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .usdm.id_generator import IDGenerator
from .usdm.cdisc_codes import CDISCCodeResolver


class USDMConverter:
    """
    Converts Study Designer data to USDM v4.0 format.
    
    This converter takes study data from the Study Designer context
    and transforms it into a fully compliant CDISC USDM JSON structure.
    """
    
    def __init__(self):
        self.id_gen = IDGenerator()
        self.codes = CDISCCodeResolver()
    
    def convert(self, study_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main conversion function.
        
        Args:
            study_data: Complete study data from Study Designer context
        
        Returns:
            USDM JSON structure
        """
        try:
            # Reset ID generator for fresh conversion
            self.id_gen.reset()
            
            context = study_data.get('studyContext', {})
            
            # Build Study root object
            study = {
                'id': None,  # Always null per USDM spec
                'name': context.get('studyTitle', 'Untitled Study'),
                'instanceType': 'Study',
                'versions': [self._build_version(study_data)]
            }
            
            # Wrap in standard structure
            usdm_output = {
                'study': study,
                'usdmVersion': '4.0',
                'systemName': 'StudyDesigner',
                'systemVersion': '1.0',
                'generatedDate': datetime.utcnow().isoformat() + 'Z'
            }
            
            return usdm_output
            
        except Exception as e:
            print(f"❌ Error in USDM conversion: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _build_version(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build StudyVersion with all child entities"""
        
        context = data.get('studyContext') or {}
        design = data.get('studyDesign') or {}
        
        # Build core version object
        version = {
            'id': self.id_gen.generate('StudyVersion'),
            'versionIdentifier': '1.0',
            'versionDate': datetime.utcnow().strftime('%Y-%m-%d'),
            'instanceType': 'StudyVersion',
            
            # Study metadata
            'studyPhase': self.codes.resolve_phase(context.get('phase')),
            'studyType': self.codes.resolve_study_type(design.get('studyType')),
            
            # Identifiers
            'studyIdentifiers': self._build_identifiers(context),
            
            # Titles
            'titles': self._build_titles(context),
            
            # Study designs
            'studyDesigns': [self._build_design(data)]
        }
        
        return version
    
    def _build_identifiers(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build StudyIdentifier objects"""
        identifiers = []
        
        # Generate a protocol ID if not provided
        title = context.get('studyTitle', 'STUDY')
        safe_title = ''.join(c if c.isalnum() else '-' for c in title)[:30]
        protocol_id = f"{safe_title}-{datetime.now().strftime('%Y%m%d')}"
        
        identifiers.append({
            'id': self.id_gen.generate('StudyIdentifier'),
            'studyIdentifier': protocol_id,
            'studyIdentifierScope': {
                'organisationIdentifier': 'ORG-001',
                'organisationIdentifierScheme': 'Internal',
                'organisationName': 'Study Sponsor',
                'organisationType': self.codes.build_code('C93453', 'Sponsor')
            },
            'instanceType': 'StudyIdentifier'
        })
        
        return identifiers
    
    def _build_titles(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build StudyTitle objects"""
        titles = []
        
        study_title = context.get('studyTitle', 'Untitled Study')
        
        titles.append({
            'id': self.id_gen.generate('StudyTitle'),
            'text': study_title,
            'type': self.codes.build_code('C99894', 'Official Study Title'),
            'instanceType': 'StudyTitle'
        })
        
        return titles
    
    def _build_design(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build InterventionalStudyDesign with all child entities"""
        
        design_data = data.get('studyDesign') or {}
        context = data.get('studyContext') or {}
        
        design = {
            'id': self.id_gen.generate('StudyDesign'),
            'instanceType': 'InterventionalStudyDesign',
        }
        
        # Add objectives if available
        objectives_data = data.get('objectives') or []
        if objectives_data and len(objectives_data) > 0:
            design['objectives'] = self._build_objectives(objectives_data, data.get('endpoints') or [])
        
        # Add indications if available
        indication = context.get('indication')
        if indication:
            design['indications'] = self._build_indications(indication)
        
        # Add therapeutic area if available
        therapeutic_area = context.get('therapeuticArea')
        if therapeutic_area:
            design['therapeuticAreas'] = self._build_therapeutic_areas(therapeutic_area)
        
        # Add eligibility criteria if available
        inclusion = data.get('inclusionCriteria') or []
        exclusion = data.get('exclusionCriteria') or []
        if inclusion or exclusion:
            design['eligibilityCriteria'] = self._build_eligibility_criteria(inclusion, exclusion)
        
        # Add arms if available
        arms = design_data.get('arms') or []
        if arms and len(arms) > 0:
            design['arms'] = self._build_arms(arms)
        
        # Add epochs (default or parsed from duration)
        design['epochs'] = self._build_epochs(design_data)
        
        # Add population if available
        total_participants = design_data.get('totalParticipants')
        if total_participants:
            design['studyPopulations'] = self._build_populations(total_participants)
        
        return design
    
    def _build_objectives(self, objectives: List[Dict[str, Any]], endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build Objective objects with endpoints"""
        result = []
        
        for obj in objectives:
            obj_type = obj.get('type', 'primary')
            
            objective = {
                'id': self.id_gen.generate('Objective'),
                'description': obj.get('description', ''),
                'level': self.codes.resolve_objective_level(obj_type),
                'instanceType': 'Objective'
            }
            
            # Find matching endpoints for this objective type
            matching_endpoints = [ep for ep in endpoints if ep.get('type') == obj_type]
            if matching_endpoints:
                objective['endpoints'] = self._build_endpoints(matching_endpoints, obj_type)
            
            result.append(objective)
        
        return result
    
    def _build_endpoints(self, endpoints: List[Dict[str, Any]], level: str) -> List[Dict[str, Any]]:
        """Build Endpoint objects"""
        result = []
        
        for ep in endpoints:
            endpoint = {
                'id': self.id_gen.generate('Endpoint'),
                'name': ep.get('name', ''),
                'description': ep.get('description', ''),
                'level': self.codes.resolve_objective_level(level),
                'purpose': ep.get('timepoint', ''),
                'instanceType': 'Endpoint'
            }
            result.append(endpoint)
        
        return result
    
    def _build_indications(self, indication: str) -> List[Dict[str, Any]]:
        """Build Indication objects"""
        return [{
            'id': self.id_gen.generate('Indication'),
            'description': indication,
            'instanceType': 'Indication'
        }]
    
    def _build_therapeutic_areas(self, therapeutic_area: str) -> List[Dict[str, Any]]:
        """Build TherapeuticArea objects"""
        return [{
            'id': self.id_gen.generate('TherapeuticArea'),
            'description': therapeutic_area,
            'instanceType': 'TherapeuticArea'
        }]
    
    def _build_eligibility_criteria(
        self, 
        inclusion: List[Dict[str, Any]], 
        exclusion: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build EligibilityCriterion objects"""
        criteria = []
        
        # Build inclusion criteria
        for criterion in inclusion:
            text = criterion.get('text') or criterion.get('criterion', '')
            if text:
                criteria.append({
                    'id': self.id_gen.generate('EligibilityCriterion'),
                    'description': text,
                    'category': self.codes.resolve_criterion_category('inclusion'),
                    'instanceType': 'EligibilityCriterion'
                })
        
        # Build exclusion criteria
        for criterion in exclusion:
            text = criterion.get('text') or criterion.get('criterion', '')
            if text:
                criteria.append({
                    'id': self.id_gen.generate('EligibilityCriterion'),
                    'description': text,
                    'category': self.codes.resolve_criterion_category('exclusion'),
                    'instanceType': 'EligibilityCriterion'
                })
        
        return criteria
    
    def _build_arms(self, arms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build StudyArm objects"""
        result = []
        
        for arm in arms:
            arm_name = arm.get('name', 'Arm')
            arm_obj = {
                'id': self.id_gen.generate('StudyArm'),
                'name': arm_name,
                'description': arm.get('intervention', ''),
                'type': self.codes.resolve_arm_type(arm_name),
                'instanceType': 'StudyArm'
            }
            result.append(arm_obj)
        
        return result
    
    def _build_epochs(self, design_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build StudyEpoch objects"""
        epochs = []
        
        # Default epochs for most interventional studies
        epoch_names = ['Screening', 'Treatment', 'Follow-up']
        
        for idx, name in enumerate(epoch_names):
            epochs.append({
                'id': self.id_gen.generate('StudyEpoch'),
                'name': name,
                'description': f'{name} period',
                'sequenceInStudy': idx + 1,
                'type': self.codes.resolve_epoch_type(name),
                'instanceType': 'StudyEpoch'
            })
        
        return epochs
    
    def _build_populations(self, total_participants: int) -> List[Dict[str, Any]]:
        """Build StudyDesignPopulation objects"""
        return [{
            'id': self.id_gen.generate('StudyDesignPopulation'),
            'description': 'Planned study population',
            'plannedEnrollmentNumber': {
                'type': self.codes.build_code('C25463', 'Count'),
                'value': int(total_participants)
            },
            'instanceType': 'StudyDesignPopulation'
        }]
    
    def validate(self, usdm_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate USDM output and return report.
        
        Args:
            usdm_output: Generated USDM JSON
        
        Returns:
            Validation report with errors, warnings, and info
        """
        issues = []
        errors = 0
        warnings = 0
        info_count = 0
        
        # Basic validation checks
        try:
            # Check required top-level fields
            if 'study' not in usdm_output:
                issues.append({
                    'level': 'error',
                    'category': 'STRUCTURE',
                    'path': 'study',
                    'message': 'Missing required field: study',
                    'suggestion': 'Ensure study object is present'
                })
                errors += 1
            else:
                study = usdm_output['study']
                
                # Check Study.id is null
                if study.get('id') is not None:
                    issues.append({
                        'level': 'error',
                        'category': 'STRUCTURE',
                        'path': 'study.id',
                        'message': 'Study.id must be null per USDM specification',
                        'suggestion': 'Set study.id to null'
                    })
                    errors += 1
                
                # Check versions exist
                versions = study.get('versions', [])
                if not versions:
                    issues.append({
                        'level': 'error',
                        'category': 'REQUIRED_FIELD',
                        'path': 'study.versions',
                        'message': 'Study must have at least one version',
                        'suggestion': 'Add a StudyVersion object'
                    })
                    errors += 1
                else:
                    # Validate first version
                    version = versions[0]
                    
                    # Check required version fields
                    required_version_fields = ['studyPhase', 'studyType', 'studyIdentifiers', 'titles', 'studyDesigns']
                    for field in required_version_fields:
                        if field not in version or not version[field]:
                            issues.append({
                                'level': 'warning',
                                'category': 'REQUIRED_FIELD',
                                'path': f'study.versions[0].{field}',
                                'message': f'Missing or empty required field: {field}',
                                'suggestion': f'Add {field} to StudyVersion'
                            })
                            warnings += 1
                    
                    # Check study designs
                    designs = version.get('studyDesigns', [])
                    if designs:
                        design = designs[0]
                        
                        # Info: Optional but recommended fields
                        optional_fields = ['objectives', 'indications', 'eligibilityCriteria', 'studyPopulations']
                        for field in optional_fields:
                            if field not in design or not design.get(field):
                                issues.append({
                                    'level': 'info',
                                    'category': 'OPTIONAL_FIELD',
                                    'path': f'study.versions[0].studyDesigns[0].{field}',
                                    'message': f'Optional field not provided: {field}',
                                    'suggestion': f'Consider adding {field} for completeness'
                                })
                                info_count += 1
            
            # Check USDM version
            if usdm_output.get('usdmVersion') != '4.0':
                issues.append({
                    'level': 'warning',
                    'category': 'VERSION',
                    'path': 'usdmVersion',
                    'message': f'USDM version is {usdm_output.get("usdmVersion")}, expected 4.0',
                    'suggestion': 'Update to USDM version 4.0'
                })
                warnings += 1
            
        except Exception as e:
            issues.append({
                'level': 'error',
                'category': 'VALIDATION_ERROR',
                'message': f'Validation error: {str(e)}',
                'suggestion': 'Check USDM structure'
            })
            errors += 1
        
        # Return validation report
        return {
            'valid': errors == 0,
            'errors': errors,
            'warnings': warnings,
            'info': info_count,
            'issues': issues
        }

