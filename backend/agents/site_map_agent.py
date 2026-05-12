"""
Site Map Agent - Creates interactive site maps with population overlays
Integrates with Dynamic Reasoning Engine for clinical trial site selection
"""

import asyncio
import json
import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from agents.llm_agent import llm_agent
from agents.trialtrove_agent import trialtrove_agent
from agents.site_trove_agent import site_trove_agent
from agents.claims_data_agent import claims_data_agent
from models.schemas import BaseModel, Field
from utils.logger import logger, log_error
from utils.cache import cache_manager


@dataclass
class Coordinates:
    """Geographic coordinates"""
    lat: float
    lng: float


@dataclass
class TrialExperience:
    """Trial experience for a site"""
    trial_id: str
    phase: str
    therapeutic_area: str
    enrollment_success: float
    enrollment_target: int
    enrollment_actual: int
    completion_rate: float


@dataclass
class TrialReference:
    """Reference trial for site identification"""
    trial_id: str
    title: str
    therapeutic_area: str
    phase: str
    sites_used: List[Dict[str, Any]]
    enrollment_success: float
    geographic_distribution: Dict[str, Any]


class SiteMapRequest(BaseModel):
    """Request model for site map generation"""
    query: str = Field(..., description="User query for site mapping")
    therapeutic_area: Optional[str] = Field(None, description="Therapeutic area")
    inclusion_criteria: List[str] = Field(default_factory=list, description="Inclusion criteria")
    exclusion_criteria: List[str] = Field(default_factory=list, description="Exclusion criteria")
    geographic_scope: Optional[Dict[str, Any]] = Field(None, description="Geographic scope")
    site_filters: Optional[Dict[str, Any]] = Field(None, description="Site filters")
    population_filters: Optional[Dict[str, Any]] = Field(None, description="Population filters")
    conversation_history: List[Dict] = Field(default_factory=list, description="Conversation history")


class SiteCandidate(BaseModel):
    """Candidate site for clinical trials"""
    site_id: str = Field(..., description="Unique site identifier")
    name: str = Field(..., description="Site name")
    address: str = Field(..., description="Site address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    zip_code: str = Field(..., description="ZIP code")
    coordinates: Dict[str, float] = Field(..., description="Latitude and longitude")
    trial_experience: List[Dict[str, Any]] = Field(default_factory=list, description="Trial experience")
    population_density: float = Field(0.0, description="Population density")
    patient_pool_size: int = Field(0, description="Estimated patient pool size")
    inclusion_rate: float = Field(0.0, description="Inclusion rate")
    exclusion_rate: float = Field(0.0, description="Exclusion rate")
    site_score: float = Field(0.0, description="Overall site score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ZipCodePopulation(BaseModel):
    """Population data for ZIP code"""
    zip_code: str = Field(..., description="ZIP code")
    population: int = Field(..., description="Total population")
    patient_count: int = Field(..., description="Patient count for therapeutic area")
    density: float = Field(..., description="Population density")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Latitude and longitude coordinates")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Demographic breakdown")


class StatePopulation(BaseModel):
    """Population data for state"""
    state: str = Field(..., description="State name")
    population: int = Field(..., description="Total population")
    patient_count: int = Field(..., description="Patient count for therapeutic area")
    site_count: int = Field(..., description="Number of sites")
    avg_density: float = Field(..., description="Average population density")


class CountyPopulation(BaseModel):
    """Population data for county"""
    county: str = Field(..., description="County name")
    state: str = Field(..., description="State name")
    population: int = Field(..., description="Total population")
    patient_count: int = Field(..., description="Patient count for therapeutic area")
    facility_count: int = Field(0, description="Number of healthcare facilities")
    avg_density: float = Field(..., description="Average population density")


class PopulationOverlay(BaseModel):
    """Population overlay data for map"""
    zip_code_data: List[ZipCodePopulation] = Field(default_factory=list, description="ZIP code population data")
    state_data: List[StatePopulation] = Field(default_factory=list, description="State population data")
    county_data: List[CountyPopulation] = Field(default_factory=list, description="County population data")
    demographic_breakdown: Dict[str, Any] = Field(default_factory=dict, description="Overall demographic breakdown")


class SiteMapResponse(BaseModel):
    """Response model for site map generation"""
    map_id: str = Field(..., description="Unique map identifier")
    sites: List[SiteCandidate] = Field(..., description="Candidate sites")
    population_overlay: PopulationOverlay = Field(..., description="Population overlay data")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    generated_at: str = Field(..., description="Generation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SiteMapAgent:
    """Agent for creating interactive site maps with population overlays"""
    
    def __init__(self):
        # Use module singletons — constructing new SiteTroveAgent/ClaimsDataAgent duplicates
        # multi-GB in-memory loads (see dynamic_reasoning_engine agent wiring).
        self.trial_trove_agent = trialtrove_agent
        self.site_trove_agent = site_trove_agent
        self.claims_data_agent = claims_data_agent
        self.llm_agent = llm_agent
        self.cache_manager = cache_manager
    
    async def generate_site_map(self, request: SiteMapRequest) -> SiteMapResponse:
        """Main method called by DRE - orchestrates the entire site mapping process"""
        try:
            logger.info(f"Starting site map generation for query: {request.query}")
            
            # Step 1: Analyze query and extract parameters
            analysis = await self._analyze_site_map_query(request)
            logger.info(f"Query analysis completed: {len(analysis)} parameters extracted")
            
            # Step 2: Get reference trials
            reference_trials = await self._get_reference_trials(analysis)
            logger.info(f"Found {len(reference_trials)} reference trials")
            
            # Step 3: Identify candidate sites
            candidate_sites = await self._identify_sites(reference_trials, analysis)
            logger.info(f"Identified {len(candidate_sites)} candidate sites")
            
            # If no real sites found, return empty result
            if not candidate_sites:
                logger.warning("No real sites found - returning empty site map")
                return SiteMapResponse(
                    map_id=f"empty_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    sites=[],
                    population_overlay=PopulationOverlay(),
                    filters_applied={},
                    generated_at=datetime.now().isoformat(),
                    metadata={
                        "status": "no_sites_found",
                        "message": "No real clinical trial sites found for the specified criteria",
                        "reference_trials_count": len(reference_trials),
                        "therapeutic_area": analysis.get('therapeutic_area', 'unknown')
                    }
                )
            
            # Step 4: Analyze population distribution
            population_overlay = await self._analyze_population_distribution(candidate_sites, analysis)
            logger.info(f"Population analysis completed: {len(population_overlay.zip_code_data)} ZIP codes")
            
            # Step 5: Filter claims data by criteria
            filtered_claims = await self._filter_claims_by_criteria(analysis)
            logger.info(f"Claims filtering completed: {len(filtered_claims)} filter types applied")
            
            # Step 6: Calculate site scores and metrics
            scored_sites = await self._calculate_site_scores(candidate_sites, population_overlay, analysis)
            logger.info(f"Site scoring completed for {len(scored_sites)} sites")
            
            # Step 7: Apply initial filters
            filtered_sites = await self._apply_filters(scored_sites, request.site_filters)
            logger.info(f"Applied filters: {len(filtered_sites)} sites remaining")
            
            # Step 8: Generate response
            response = SiteMapResponse(
                map_id=f"site_map_{uuid.uuid4().hex[:8]}",
                sites=filtered_sites,
                population_overlay=population_overlay,
                filters_applied=request.site_filters or {},
                generated_at=datetime.now().isoformat(),
                metadata={
                    "therapeutic_area": analysis.get('therapeutic_area', 'general'),
                    "total_sites_found": len(candidate_sites),
                    "sites_after_filtering": len(filtered_sites),
                    "analysis_parameters": analysis,
                    "reference_trials_count": len(reference_trials),
                    "filtered_claims_data": filtered_claims
                }
            )
            
            logger.info(f"Site map generation completed: {response.map_id}")
            return response
            
        except Exception as e:
            logger.error(f"Site map generation failed: {e}")
            log_error(e, "Site map generation")
            raise
    
    async def _analyze_site_map_query(self, request: SiteMapRequest) -> Dict[str, Any]:
        """Use LLM to analyze the site mapping request and extract parameters"""
        try:
            prompt = f"""
            Analyze this site mapping request and extract comprehensive parameters:
            
            Query: {request.query}
            Therapeutic Area: {request.therapeutic_area or 'Not specified'}
            Inclusion Criteria: {request.inclusion_criteria}
            Exclusion Criteria: {request.exclusion_criteria}
            Geographic Scope: {request.geographic_scope}
            
            Extract the following information:
            1. Target patient population characteristics
            2. Geographic preferences and constraints
            3. Site experience requirements
            4. Population density preferences
            5. Site performance criteria
            6. ICD diagnosis codes mentioned (if any)
            7. Patient demographics (age ranges, gender preferences)
            8. Insurance/payer preferences
            9. Additional constraints or requirements
            
            IMPORTANT: You MUST return ONLY valid JSON format. Do not include any explanatory text, markdown formatting, or code blocks. Return ONLY the JSON object.
            
            Return as JSON with all extracted parameters. Base your estimates on:
            - The specific therapeutic area mentioned
            - The trial phase and complexity
            - Industry standards for similar trials
            - Any specific requirements mentioned in the query
            - Geographic scope and regulatory environment
            
            Example structure:
            {{
                "therapeutic_area": "Oncology",
                "phase": "Phase III",
                "target_sample_size": 500,
                "geographic_preference": "Northeast",
                "site_experience_required": "Phase III oncology",
                "population_density_preference": "high",
                "site_performance_criteria": "high enrollment success",
                "icd_codes": ["C78.00", "C78.01", "C78.02"],
                "patient_demographics": {{
                    "age_range": "18-75",
                    "gender_preference": "both"
                }},
                "insurance_preferences": ["Commercial", "Medicare"],
                "additional_requirements": "Academic medical centers preferred"
            }}
            """
            
            response = await self.llm_agent.generate_response(prompt)
            return self._parse_llm_response(response)
            
        except Exception as e:
            logger.warning(f"LLM analysis failed, using defaults: {e}")
            return self._get_default_analysis(request)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response with robust JSON extraction"""
        try:
            # First try direct JSON parsing
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.info(f"Raw LLM response: {response}")
            
            # Try to extract JSON from markdown code blocks
            cleaned_response = re.sub(r'```json\s*', '', response)
            cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
            cleaned_response = re.sub(r'```\s*', '', cleaned_response)
            
            # Try to parse the cleaned response
            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError as e2:
                logger.warning(f"Still failed to parse after cleaning: {e2}")
            
            # Try to extract JSON using regex - look for the largest JSON object
            json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_matches:
                # Try the longest match first
                json_matches.sort(key=len, reverse=True)
                for match in json_matches:
                    try:
                        return json.loads(match)
                    except:
                        continue
            
            # Try to extract just the content between the first { and last }
            try:
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_content = response[start:end+1]
                    return json.loads(json_content)
            except:
                pass
            
            # Fallback to default analysis
            logger.warning("All JSON parsing attempts failed, using default analysis")
            return self._get_default_analysis(None)
    
    def _get_default_analysis(self, request: Optional[SiteMapRequest]) -> Dict[str, Any]:
        """Get default analysis when LLM parsing fails"""
        return {
            "therapeutic_area": getattr(request, 'therapeutic_area', None) or "General",
            "phase": "Phase III",
            "target_sample_size": 300,
            "geographic_preference": "United States",
            "site_experience_required": "Clinical trial experience",
            "population_density_preference": "medium",
            "site_performance_criteria": "successful enrollment",
            "icd_codes": [],
            "patient_demographics": {
                "age_range": "18-80",
                "gender_preference": "both"
            },
            "insurance_preferences": ["Commercial", "Medicare", "Medicaid"],
            "additional_requirements": "Qualified clinical sites"
        }
    
    async def _get_reference_trials(self, analysis: Dict[str, Any]) -> List[TrialReference]:
        """Get reference trials using TrialTroveAgent"""
        try:
            # Create a query for the trial trove agent
            therapeutic_area = analysis.get('therapeutic_area', 'general')
            phase = analysis.get('phase', 'Phase III')
            
            trial_query = f"""
            Find clinical trials in {therapeutic_area} 
            {phase} studies with successful enrollment and site performance data.
            Focus on trials with good site recruitment and geographic distribution.
            """
            
            # Call the trial trove agent
            trial_results = await self.trial_trove_agent.search_studies(trial_query, max_results=30)
            
            logger.info(f"TrialTroveAgent returned {len(trial_results)} trials")
            if trial_results:
                logger.info(f"Sample trial result: {type(trial_results[0])}")
                logger.info(f"Sample trial attributes: {dir(trial_results[0])}")
            
            # Convert to TrialReference objects
            reference_trials = []
            for result in trial_results:
                # Handle both ClinicalTrialResult objects and dictionaries
                if hasattr(result, 'nct_id'):
                    # ClinicalTrialResult object
                    trial_id = result.nct_id.replace("TrialTrove-", "") if result.nct_id.startswith("TrialTrove-") else result.nct_id
                    title = result.title
                    metadata = result.metadata
                else:
                    # Dictionary format
                    trial_id = result.get('nct_id', '').replace("TrialTrove-", "") if result.get('nct_id', '').startswith("TrialTrove-") else result.get('nct_id', '')
                    title = result.get('title', 'Unknown Trial')
                    metadata = result.get('metadata', {})
                
                # Convert trial_id to integer for matching with SiteTrove
                try:
                    trial_id_int = int(float(trial_id)) if trial_id else None
                except (ValueError, TypeError):
                    trial_id_int = None
                
                # Get site count from metadata
                site_count = 0
                if metadata and "trialtrove" in metadata:
                    trialtrove_data = metadata["trialtrove"]
                    site_count = trialtrove_data.get("reported_sites", 0)
                
                logger.info(f"Processing trial {trial_id} (int: {trial_id_int}): {title}")
                logger.info(f"Trial has {site_count} reported sites")
                
                # Create TrialReference with empty sites_used - we'll populate from SiteTroveAgent
                reference_trials.append(TrialReference(
                    trial_id=str(trial_id_int) if trial_id_int else trial_id,  # Use integer ID for SiteTrove matching
                    title=title,
                    therapeutic_area=therapeutic_area,
                    phase=phase,
                    sites_used=[],  # Will be populated by SiteTroveAgent
                    enrollment_success=0.8,  # Default success rate
                    geographic_distribution={'states': []}  # Will be populated from sites
                ))
            
            return reference_trials
            
        except Exception as e:
            logger.warning(f"Failed to get reference trials: {e}")
            return []
    
    async def _identify_sites(self, reference_trials: List[TrialReference], analysis: Dict[str, Any]) -> List[SiteCandidate]:
        """Identify candidate sites from reference trials using SiteTroveAgent"""
        try:
            if not reference_trials:
                logger.warning("No reference trials provided for site identification")
                return []
            
            # Extract trial IDs from reference trials
            trial_ids = []
            for trial in reference_trials:
                try:
                    # Convert trial_id to integer for matching
                    trial_id_int = int(float(trial.trial_id)) if trial.trial_id else None
                    if trial_id_int:
                        trial_ids.append(trial_id_int)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid trial ID format: {trial.trial_id}")
                    continue
            
            if not trial_ids:
                logger.warning("No valid trial IDs found in reference trials")
                return []
            
            logger.info(f"Looking for sites associated with {len(trial_ids)} trials: {trial_ids[:10]}...")  # Show first 10
            
            # Use SiteTroveAgent to find sites for these trials
            sites_found = []
            for trial_id in trial_ids:
                try:
                    # Get sites by trial ID using the correct method
                    site_results = await self.site_trove_agent.get_sites_by_trial_id(trial_id)
                    logger.info(f"Found {len(site_results)} sites for trial {trial_id}")
                    sites_found.extend(site_results)
                except Exception as e:
                    logger.warning(f"Error getting sites for trial {trial_id}: {e}")
                    continue
            
            if not sites_found:
                logger.warning("No sites found in SiteTroveAgent for any of the reference trials")
                return []
            
            # Deduplicate sites by site_id to avoid duplicates
            unique_sites = {}
            for site in sites_found:
                site_id = site.get('site_id', 'unknown')
                if site_id not in unique_sites:
                    unique_sites[site_id] = site
                else:
                    # If site already exists, merge trial information
                    existing_site = unique_sites[site_id]
                    existing_trial_id = existing_site.get('metadata', {}).get('trial_id')
                    current_trial_id = site.get('metadata', {}).get('trial_id')
                    if existing_trial_id != current_trial_id:
                        # Add additional trial info to metadata
                        if 'additional_trials' not in existing_site['metadata']:
                            existing_site['metadata']['additional_trials'] = []
                        existing_site['metadata']['additional_trials'].append(current_trial_id)
            
            sites_found = list(unique_sites.values())
            logger.info(f"After deduplication: {len(sites_found)} unique sites")
            
            # Convert site dictionaries to SiteCandidate objects
            candidates = []
            for site_result in sites_found:
                # Extract coordinates - handle both 'latitude'/'longitude' and 'lat'/'lng' formats
                lat = site_result.get('latitude', site_result.get('lat', 0.0))
                lng = site_result.get('longitude', site_result.get('lng', 0.0))
                
                # Convert to float and handle None/NaN values
                try:
                    lat = float(lat) if lat is not None and str(lat).lower() != 'nan' else 0.0
                    lng = float(lng) if lng is not None and str(lng).lower() != 'nan' else 0.0
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0
                
                # Skip sites without valid coordinates
                if lat == 0.0 and lng == 0.0:
                    logger.warning(f"Skipping site {site_result.get('site_name', 'Unknown')} - no coordinates")
                    continue
                
                # Handle NaN values in string fields
                def safe_str(value):
                    if value is None or (isinstance(value, float) and str(value).lower() == 'nan'):
                        return ''
                    return str(value)
                
                # Find which trials this site is associated with
                associated_trials = []
                trial_id_from_site = site_result.get('metadata', {}).get('trial_id')
                additional_trials = site_result.get('metadata', {}).get('additional_trials', [])
                
                # Add primary trial
                for trial in reference_trials:
                    if str(trial.trial_id) == str(trial_id_from_site):
                        associated_trials.append({
                            'trial_id': trial.trial_id,
                            'phase': trial.phase,
                            'therapeutic_area': trial.therapeutic_area,
                            'enrollment_success': trial.enrollment_success
                        })
                        break
                
                # Add additional trials
                for additional_trial_id in additional_trials:
                    for trial in reference_trials:
                        if str(trial.trial_id) == str(additional_trial_id):
                            associated_trials.append({
                                'trial_id': trial.trial_id,
                                'phase': trial.phase,
                                'therapeutic_area': trial.therapeutic_area,
                                'enrollment_success': trial.enrollment_success
                            })
                            break
                
                candidates.append(SiteCandidate(
                    site_id=safe_str(site_result.get('site_id', 'unknown')),
                    name=safe_str(site_result.get('site_name', 'Unknown Site')),
                    address=f"{safe_str(site_result.get('address', ''))}, {safe_str(site_result.get('city', ''))}, {safe_str(site_result.get('state', ''))}",
                    city=safe_str(site_result.get('city', '')),
                    state=safe_str(site_result.get('state', '')),
                    zip_code=safe_str(site_result.get('postal_code', '')),
                    coordinates={
                        'lat': lat,
                        'lng': lng
                    },
                    trial_experience=associated_trials,
                    population_density=0.0,  # Will be calculated
                    patient_pool_size=0,     # Will be calculated
                    inclusion_rate=0.0,       # Will be calculated
                    exclusion_rate=0.0,       # Will be calculated
                    site_score=0.0,           # Will be calculated
                    metadata={
                        'source': 'site_trove',
                        'trial_count': len(associated_trials),
                        'therapeutic_area': analysis.get('therapeutic_area', 'general'),
                        'organization_type': safe_str(site_result.get('site_type', '')),
                        'total_trials': site_result.get('total_trials', 0),
                        'ongoing_trials': site_result.get('ongoing_trials', 0)
                    }
                ))
            
            logger.info(f"Successfully identified {len(candidates)} candidate sites with valid coordinates")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to identify sites: {e}")
            return []
    
    async def _analyze_population_distribution(self, sites: List[SiteCandidate], analysis: Dict[str, Any]) -> PopulationOverlay:
        """Analyze population distribution using ClaimsDataAgent"""
        try:
            # Get ZIP codes for all sites
            zip_codes = [site.zip_code for site in sites if site.zip_code and site.zip_code != '00000']
            
            # Query claims data for population distribution (regardless of site ZIP codes)
            therapeutic_area = analysis.get('therapeutic_area', 'general')
            
            # Use real claims data for general population analysis
            logger.info(f"Analyzing population distribution for therapeutic area: {therapeutic_area}")
            geographic_data = await self.claims_data_agent.analyze_geographic_distribution(
                therapeutic_area=therapeutic_area, 
                max_results=100
            )
            
            zip_code_data = geographic_data.get('zip_code_data', [])
            state_data = geographic_data.get('state_data', [])
            county_data = geographic_data.get('county_data', [])
            
            logger.info(f"Retrieved real claims data: {len(zip_code_data)} ZIP codes, {len(state_data)} states")
            
            # If claims data doesn't have ZIP codes but we have site ZIP codes, create population data
            if not zip_code_data and zip_codes:
                logger.info("Claims data has no ZIP codes, creating population data based on site locations")
                zip_code_data = []
                
                # Create population data for each site's ZIP code
                for zip_code in zip_codes[:50]:  # Limit to 50 for performance
                    # Mock population data based on ZIP code
                    population = 50000 + (hash(zip_code) % 100000)
                    patient_count = int(population * 0.1)  # Assume 10% have the condition
                    
                    zip_code_data.append({
                        'zip_code': zip_code,
                        'population': population,
                        'patient_count': patient_count,
                        'density': population / 1000,  # Mock density
                        'demographics': {
                            'age_18_65': 0.6,
                            'age_65_plus': 0.3,
                            'male': 0.48,
                            'female': 0.52,
                            'therapeutic_area': therapeutic_area
                        }
                    })
            
            # If still no data, create minimal fallback based on states
            if not zip_code_data and not state_data:
                logger.warning("No population data available, creating minimal fallback based on site states")
                state_data = []
                county_data = []
                
                # Group sites by state and create state-level data
                state_counts = {}
                for site in sites:
                    state = site.state
                    if state not in state_counts:
                        state_counts[state] = 0
                    state_counts[state] += 1
                
                for state, site_count in state_counts.items():
                    # Mock state population data
                    population = site_count * 1000000  # Assume 1M people per site
                    patient_count = int(population * 0.1)  # Assume 10% have the condition
                    
                    state_data.append({
                        'state': state,
                        'population': population,
                        'patient_count': patient_count,
                        'site_count': site_count,
                        'avg_density': population / 1000
                    })
            
            # Convert real claims data to Pydantic objects
            zip_code_objects = []
            for zip_data in zip_code_data:
                zip_code_objects.append(ZipCodePopulation(
                    zip_code=zip_data['zip_code'],
                    population=zip_data['population'],
                    patient_count=zip_data['patient_count'],
                    density=zip_data['density'],
                    coordinates=zip_data.get('coordinates'),
                    demographics=zip_data['demographics']
                ))
            
            # Convert state data to Pydantic objects
            state_objects = []
            for state_data_item in state_data:
                state_objects.append(StatePopulation(
                    state=state_data_item['state'],
                    population=state_data_item['population'],
                    patient_count=state_data_item['patient_count'],
                    site_count=state_data_item['site_count'],
                    avg_density=state_data_item['avg_density']
                ))
            
            # Convert county data to Pydantic objects
            county_objects = []
            for county_data_item in county_data:
                county_objects.append(CountyPopulation(
                    county=county_data_item['county'],
                    state=county_data_item['state'],
                    population=county_data_item['population'],
                    patient_count=county_data_item['patient_count'],
                    facility_count=county_data_item['facility_count'],
                    avg_density=county_data_item['avg_density']
                ))
            
            return PopulationOverlay(
                zip_code_data=zip_code_objects,
                state_data=state_objects,
                county_data=county_objects,
                demographic_breakdown={
                    'total_population': sum(zp.population for zp in zip_code_objects),
                    'total_patients': sum(zp.patient_count for zp in zip_code_objects),
                    'therapeutic_area': therapeutic_area
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze population distribution: {e}")
            return PopulationOverlay()
    
    async def _filter_claims_by_criteria(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Filter claims data based on ICD codes and other criteria from analysis"""
        try:
            icd_codes = analysis.get('icd_codes', [])
            patient_demographics = analysis.get('patient_demographics', {})
            insurance_preferences = analysis.get('insurance_preferences', [])
            
            if not icd_codes and not patient_demographics and not insurance_preferences:
                logger.info("No specific filtering criteria found, using all claims data")
                return {}
            
            # Get filtered claims data from ClaimsDataAgent
            filtered_data = {}
            
            # Filter by ICD codes if specified
            if icd_codes:
                logger.info(f"Filtering claims by ICD codes: {icd_codes}")
                icd_results = await self.claims_data_agent.search_diagnoses(
                    query=f"ICD codes: {', '.join(icd_codes)}", 
                    max_results=1000
                )
                filtered_data['icd_filtered_claims'] = icd_results
                logger.info(f"Found {len(icd_results)} claims matching ICD codes")
            
            # Filter by patient demographics if specified
            if patient_demographics:
                logger.info(f"Filtering claims by demographics: {patient_demographics}")
                demo_results = await self.claims_data_agent.analyze_patient_population(
                    query=f"Demographics: {patient_demographics}", 
                    max_results=1000
                )
                filtered_data['demographics_filtered_claims'] = demo_results
                logger.info(f"Found {len(demo_results)} claims matching demographics")
            
            # Filter by insurance preferences if specified
            if insurance_preferences:
                logger.info(f"Filtering claims by insurance: {insurance_preferences}")
                insurance_results = await self.claims_data_agent.get_enrollment_analysis(
                    query=f"Insurance types: {', '.join(insurance_preferences)}", 
                    max_results=1000
                )
                filtered_data['insurance_filtered_claims'] = insurance_results
                logger.info(f"Found {len(insurance_results)} claims matching insurance preferences")
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Failed to filter claims by criteria: {e}")
            return {}
    
    async def _calculate_site_scores(self, sites: List[SiteCandidate], population_overlay: PopulationOverlay, analysis: Dict[str, Any]) -> List[SiteCandidate]:
        """Calculate site scores and metrics"""
        try:
            # Create ZIP code lookup for population data
            zip_lookup = {zp.zip_code: zp for zp in population_overlay.zip_code_data}
            
            for site in sites:
                # Get population data for this site
                zip_data = zip_lookup.get(site.zip_code)
                if zip_data:
                    site.population_density = zip_data.density
                    site.patient_pool_size = zip_data.patient_count
                
                # Calculate inclusion/exclusion rates (mock for now)
                site.inclusion_rate = 0.7 + (hash(site.site_id) % 30) / 100  # 70-100%
                site.exclusion_rate = 0.1 + (hash(site.site_id) % 20) / 100  # 10-30%
                
                # Calculate site score based on multiple factors
                score = 0.0
                
                # Trial experience factor (30%)
                experience_score = min(len(site.trial_experience) / 5.0, 1.0) * 0.3
                score += experience_score
                
                # Population density factor (25%)
                density_score = min(site.population_density / 100.0, 1.0) * 0.25
                score += density_score
                
                # Patient pool size factor (25%)
                pool_score = min(site.patient_pool_size / 10000.0, 1.0) * 0.25
                score += pool_score
                
                # Inclusion rate factor (20%)
                inclusion_score = site.inclusion_rate * 0.2
                score += inclusion_score
                
                site.site_score = min(score, 1.0)  # Cap at 1.0
            
            # Sort sites by score
            sites.sort(key=lambda x: x.site_score, reverse=True)
            
            return sites
            
        except Exception as e:
            logger.error(f"Failed to calculate site scores: {e}")
            return sites
    
    async def _apply_filters(self, sites: List[SiteCandidate], filters: Optional[Dict[str, Any]]) -> List[SiteCandidate]:
        """Apply filters to candidate sites"""
        if not filters:
            return sites
        
        try:
            filtered_sites = sites.copy()
            
            # Apply geographic filters
            if 'geographic_scope' in filters:
                scope = filters['geographic_scope']
                if 'states' in scope:
                    filtered_sites = [s for s in filtered_sites if s.state in scope['states']]
                if 'radius' in scope and 'center' in scope:
                    # Apply radius filter (simplified)
                    center_lat = scope['center']['lat']
                    center_lng = scope['center']['lng']
                    radius_km = scope['radius']
                    
                    filtered_sites = [s for s in filtered_sites if self._calculate_distance(
                        center_lat, center_lng, s.coordinates['lat'], s.coordinates['lng']
                    ) <= radius_km]
            
            # Apply site score filter
            if 'min_site_score' in filters:
                min_score = filters['min_site_score']
                filtered_sites = [s for s in filtered_sites if s.site_score >= min_score]
            
            # Apply population density filter
            if 'min_population_density' in filters:
                min_density = filters['min_population_density']
                filtered_sites = [s for s in filtered_sites if s.population_density >= min_density]
            
            return filtered_sites
            
        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            return sites
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates in kilometers"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r


# Create agent instance
site_map_agent = SiteMapAgent()
