"""
API routes for map-based site selection with population overlay
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import pgeocode

router = APIRouter()

# Initialize ZIP code geocoder (lazy load to avoid startup delay)
_zip_geocoder = None

def get_zip_geocoder():
    """Get or initialize the ZIP code geocoder"""
    global _zip_geocoder
    if _zip_geocoder is None:
        print("📍 Initializing US ZIP code geocoder...")
        _zip_geocoder = pgeocode.Nominatim('US')
    return _zip_geocoder

class SiteMapRequest(BaseModel):
    reference_trial_ids: List[str] = []
    indication: Optional[str] = None
    phase: Optional[str] = None
    therapeutic_area: Optional[str] = None
    icd_codes: List[str] = []
    inclusion_criteria: List[str] = []
    exclusion_criteria: List[str] = []

class SiteLocation(BaseModel):
    site_id: str
    site_name: str
    organization: str
    city: Optional[str] = "Unknown"
    state: Optional[str] = "Unknown"
    country: Optional[str] = "Unknown"
    latitude: float
    longitude: float
    historical_trials: int = 0
    avg_enrollment: float = 0.0
    therapeutic_areas: List[str] = []
    recent_trials: List[Dict[str, Any]] = []
    selected: bool = False
    # Organization details
    organization_type: Optional[str] = None
    organization_address: Optional[str] = None
    postal_code: Optional[str] = None
    phones: Optional[str] = None
    faxes: Optional[str] = None
    region: Optional[str] = None
    npi_number: Optional[str] = None
    # Trial metrics
    total_trials: int = 0
    ongoing_trials: int = 0
    planned_trials: int = 0
    total_matching_trials: int = 0
    ongoing_matching_trials: int = 0
    planned_matching_trials: int = 0
    total_investigators: int = 0
    last_trial_start_date: Optional[str] = None
    # Specialization
    disease_areas: List[str] = []
    sponsors: List[str] = []  # Companies they've worked with
    # Parent organization
    parent_organization_name: Optional[str] = None
    parent_organization_type: Optional[str] = None
    parent_total_trials: int = 0
    # URLs
    record_url: Optional[str] = None
    supporting_urls: Optional[str] = None

class PopulationHeatmapPoint(BaseModel):
    latitude: float
    longitude: float
    state: str
    city: Optional[str]
    patient_count: int
    percentage: float
    icd_codes: List[str]

class SiteMapResponse(BaseModel):
    success: bool
    sites: List[SiteLocation]
    population_heatmap: List[PopulationHeatmapPoint]
    total_sites: int
    total_population: int
    coverage_analysis: Dict[str, Any]

class NearestSitesRequest(BaseModel):
    latitude: float
    longitude: float
    max_results: int = 5
    therapeutic_area: Optional[str] = None

class NearestSitesResponse(BaseModel):
    success: bool
    sites: List[SiteLocation]
    distances_miles: List[float]

@router.post("/sites-with-population", response_model=SiteMapResponse)
async def get_sites_with_population_map(request: SiteMapRequest):
    """
    Get sites from reference trials mapped with population data for visualization
    """
    try:
        print("\n" + "="*80)
        print("📍 Site Map Request Received")
        print(f"   Reference Trial IDs: {len(request.reference_trial_ids)} trials")
        print(f"   Indication: {request.indication}")
        print(f"   Phase: {request.phase}")
        print(f"   Therapeutic Area: {request.therapeutic_area}")
        print(f"   ICD Codes: {len(request.icd_codes)} codes")
        print("="*80 + "\n")
        
        import main_complete
        data_loader = main_complete.data_loader
        
        # Get data from cache
        site_trove_df = data_loader.get_data('sitetrove')
        claims_df = data_loader.get_data('claims')
        
        if site_trove_df.empty:
            raise HTTPException(status_code=500, detail="SiteTrove data not available")
        
        if claims_df.empty:
            raise HTTPException(status_code=500, detail="Claims data not available")
        
        # Get sites from SiteTrove data
        sites_data = []
        
        # PRIORITY 1: Use reference trial IDs to get actual sites that participated
        if request.reference_trial_ids:
            print(f"\n🔍 Looking up sites for {len(request.reference_trial_ids)} reference trials:")
            print(f"   Trial IDs: {request.reference_trial_ids}")
            for trial_id in request.reference_trial_ids:
                trial_sites = _get_sites_for_trial(site_trove_df, trial_id)
                sites_data.extend(trial_sites)
                print(f"   ✅ Trial {trial_id}: Found {len(trial_sites)} sites")
            print(f"✅ Total: {len(sites_data)} sites from {len(request.reference_trial_ids)} reference trials\n")
        
        # FALLBACK: If no trials or no sites found, use therapeutic area
        if not sites_data and (request.indication or request.therapeutic_area):
            print("⚠️  No sites from reference trials, falling back to therapeutic area")
            sites_data = _get_sites_by_therapeutic_area(
                site_trove_df, 
                request.indication or request.therapeutic_area
            )
            print(f"✅ Retrieved {len(sites_data)} sites for indication/TA")
        
        # Deduplicate sites by site_id
        unique_sites = {}
        for site in sites_data:
            site_id = site.get('site_id') or site.get('Organization Name', '')
            if site_id and site_id not in unique_sites:
                unique_sites[site_id] = site
        
        # Format sites with location data
        formatted_sites = []
        for site_id, site in unique_sites.items():
            lat = site.get('Latitude') or site.get('latitude')
            lon = site.get('Longitude') or site.get('longitude')
            
            if lat and lon and not pd.isna(lat) and not pd.isna(lon):
                try:
                    # Handle None values from data
                    city = site.get('City') or site.get('city')
                    state = site.get('State') or site.get('state')
                    country = site.get('Country') or site.get('country')
                    
                    # Parse disease areas (pipe-separated)
                    disease_areas_raw = site.get('Organization Disease Areas', '')
                    disease_areas = []
                    if disease_areas_raw and pd.notna(disease_areas_raw):
                        disease_areas = [da.strip() for da in str(disease_areas_raw).split('|') if da.strip()]
                    
                    # Parse sponsors (semicolon-separated, extract company name before parentheses)
                    sponsors_raw = site.get('Organization Sponsor/Collaborator Involvement', '')
                    sponsors = []
                    if sponsors_raw and pd.notna(sponsors_raw):
                        for sponsor in str(sponsors_raw).split(';'):
                            # Extract company name (before trial count in parentheses)
                            company = sponsor.split('(')[0].strip()
                            if company:
                                sponsors.append(company)
                    
                    # Safely get integer values
                    def safe_int(val, default=0):
                        try:
                            if val and pd.notna(val):
                                return int(val)
                        except (ValueError, TypeError):
                            pass
                        return default
                    
                    # Safely get string values
                    def safe_str(val, default=None):
                        if val and pd.notna(val):
                            return str(val)
                        return default
                    
                    # Extract contact info
                    phones_val = safe_str(site.get('Organization Phones'))
                    faxes_val = safe_str(site.get('Organization Faxes'))
                    npi_val = safe_str(site.get('Organization NPI Number'))
                    
                    # Debug first few sites
                    if len(formatted_sites) < 3:
                        print(f"   DEBUG Site {len(formatted_sites) + 1}: {site.get('Organization Name', 'Unknown')}")
                        print(f"     Phone: {phones_val}")
                        print(f"     Fax: {faxes_val}")
                        print(f"     NPI: {npi_val}")
                    
                    formatted_sites.append(SiteLocation(
                        site_id=str(site_id),
                        site_name=site.get('Organization Name', site.get('site_name', 'Unknown')),
                        organization=site.get('Organization Name', 'Unknown'),
                        city=city if city and pd.notna(city) else 'Unknown',
                        state=state if state and pd.notna(state) else 'Unknown',
                        country=country if country and pd.notna(country) else 'USA',
                        latitude=float(lat),
                        longitude=float(lon),
                        historical_trials=safe_int(site.get('trial_count', site.get('Total Trials', site.get('Organization Total Trials', 0)))),
                        avg_enrollment=float(site.get('avg_enrollment', site.get('Avg Enrollment', 0))),
                        therapeutic_areas=site.get('therapeutic_areas', [request.therapeutic_area]) if request.therapeutic_area else [],
                        recent_trials=[],
                        selected=False,
                        # Organization details
                        organization_type=safe_str(site.get('Organization Type')),
                        organization_address=safe_str(site.get('Organization Address')),
                        postal_code=safe_str(site.get('Organization Postal Code')),
                        phones=phones_val,
                        faxes=faxes_val,
                        region=safe_str(site.get('Organization Region')),
                        npi_number=npi_val,
                        # Trial metrics
                        total_trials=safe_int(site.get('Total Trials', site.get('Organization Total Trials', 0))),
                        ongoing_trials=safe_int(site.get('Organization Ongoing Trials', 0)),
                        planned_trials=safe_int(site.get('Organization Planned Trials', 0)),
                        total_matching_trials=safe_int(site.get('Organization Total Matching Trials', 0)),
                        ongoing_matching_trials=safe_int(site.get('Organization Ongoing Matching Trials', 0)),
                        planned_matching_trials=safe_int(site.get('Organization Planned Matching Trials', 0)),
                        total_investigators=safe_int(site.get('Organization Total Matching Investigators', 0)),
                        last_trial_start_date=safe_str(site.get('Organization Last Trial Start Date')),
                        # Specialization
                        disease_areas=disease_areas[:20],  # Limit to top 20 for performance
                        sponsors=sponsors[:30],  # Limit to top 30 sponsors
                        # Parent organization
                        parent_organization_name=safe_str(site.get('Parent Organization Name')),
                        parent_organization_type=safe_str(site.get('Parent Organization Type')),
                        parent_total_trials=safe_int(site.get('Parent Organization Total Trials', 0)),
                        # URLs
                        record_url=safe_str(site.get('Organization Record URL')),
                        supporting_urls=safe_str(site.get('Organization Supporting URLs'))
                    ))
                except (ValueError, TypeError) as e:
                    print(f"Error formatting site {site_id}: {e}")
                    continue
        
        # Get population heatmap from claims data
        population_heatmap = _get_population_heatmap(
            claims_df,
            request.icd_codes,
            request.indication
        )
        
        # Calculate coverage analysis
        coverage_analysis = _calculate_coverage(formatted_sites, population_heatmap)
        
        return SiteMapResponse(
            success=True,
            sites=formatted_sites,  # Return all sites (frontend can handle clustering)
            population_heatmap=population_heatmap,
            total_sites=len(formatted_sites),
            total_population=sum(p.patient_count for p in population_heatmap),
            coverage_analysis=coverage_analysis
        )
        
    except Exception as e:
        import traceback
        print(f"Error in site map generation: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/find-nearest-sites", response_model=NearestSitesResponse)
async def find_nearest_sites(request: NearestSitesRequest):
    """
    Find the nearest real sites from SiteTrove to a clicked location
    """
    try:
        import main_complete
        data_loader = main_complete.data_loader
        
        # Get SiteTrove data
        site_trove_df = data_loader.get_data('sitetrove')
        
        if site_trove_df.empty:
            raise HTTPException(status_code=500, detail="SiteTrove data not available")
        
        print(f"🔍 Finding nearest sites to ({request.latitude:.4f}, {request.longitude:.4f})")
        
        # Filter sites with valid coordinates
        valid_sites = site_trove_df[
            (site_trove_df['Organization Latitude'].notna()) & 
            (site_trove_df['Organization Longitude'].notna())
        ].copy()
        
        # Calculate distance to all sites using Haversine formula
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Calculate distance between two points in miles"""
            R = 3959  # Earth's radius in miles
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            
            return R * c
        
        # Calculate distance for each site
        valid_sites['distance_miles'] = valid_sites.apply(
            lambda row: haversine_distance(
                request.latitude,
                request.longitude,
                row['Organization Latitude'],
                row['Organization Longitude']
            ),
            axis=1
        )
        
        # Sort by distance and get top N
        nearest_sites = valid_sites.nsmallest(request.max_results, 'distance_miles')
        
        # Format response
        sites = []
        distances = []
        
        for _, row in nearest_sites.iterrows():
            org_name = row.get('Organization Name', 'Unknown')
            
            # Handle None values from pandas DataFrame
            city = row.get('Organization City')
            state = row.get('Organization State')
            country = row.get('Organization Country')
            
            # Parse disease areas (pipe-separated)
            disease_areas_raw = row.get('Organization Disease Areas', '')
            disease_areas = []
            if disease_areas_raw and pd.notna(disease_areas_raw):
                disease_areas = [da.strip() for da in str(disease_areas_raw).split('|') if da.strip()]
            
            # Parse sponsors (semicolon-separated, extract company name before parentheses)
            sponsors_raw = row.get('Organization Sponsor/Collaborator Involvement', '')
            sponsors = []
            if sponsors_raw and pd.notna(sponsors_raw):
                for sponsor in str(sponsors_raw).split(';'):
                    # Extract company name (before trial count in parentheses)
                    company = sponsor.split('(')[0].strip()
                    if company:
                        sponsors.append(company)
            
            site = SiteLocation(
                site_id=str(org_name),
                site_name=org_name,
                organization=org_name,
                city=city if pd.notna(city) else 'Unknown',
                state=state if pd.notna(state) else 'Unknown',
                country=country if pd.notna(country) else 'USA',
                latitude=float(row['Organization Latitude']),
                longitude=float(row['Organization Longitude']),
                historical_trials=int(row.get('Organization Total Trials', 0)),
                avg_enrollment=0.0,  # Not directly available
                therapeutic_areas=[request.therapeutic_area] if request.therapeutic_area else [],
                recent_trials=[],
                selected=False,
                # NEW: Expanded filtering fields
                organization_type=row.get('Organization Type'),
                disease_areas=disease_areas[:20],  # Limit to top 20 for performance
                sponsors=sponsors[:30],  # Limit to top 30 sponsors
                region=row.get('Organization Region'),
                total_trials=int(row.get('Organization Total Trials', 0)),
                ongoing_trials=int(row.get('Organization Ongoing Trials', 0))
            )
            sites.append(site)
            distances.append(round(float(row['distance_miles']), 1))
        
        print(f"✅ Found {len(sites)} nearest sites:")
        for i, (site, dist) in enumerate(zip(sites, distances), 1):
            print(f"   {i}. {site.site_name} ({site.city}, {site.state}) - {dist} miles")
        
        return NearestSitesResponse(
            success=True,
            sites=sites,
            distances_miles=distances
        )
        
    except Exception as e:
        import traceback
        print(f"Error finding nearest sites: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def _get_sites_for_trial(site_trove_df: pd.DataFrame, trial_id: str) -> List[Dict]:
    """
    Get all sites that participated in a specific trial.
    
    Uses TrialTrove Trial ID to directly match against Organization Trialtrove Trial IDs.
    The Trial ID should be the numeric ID from the TrialTrove 'Trial ID' column.
    """
    try:
        # The trial_id is already the TrialTrove numeric ID from the frontend
        trialtrove_id = str(trial_id).strip()
        
        print(f"   🔍 Looking up sites for TrialTrove ID: {trialtrove_id}")
        
        # Find sites with this TrialTrove ID
        # The 'Organization Trialtrove Trial IDs' column contains semicolon-separated numeric IDs
        # Example: "3921; 4077; 4106; 513168; 7454"
        trial_sites = site_trove_df[
            site_trove_df['Organization Trialtrove Trial IDs'].astype(str).str.contains(
                f'(^|;\\s*){trialtrove_id}(\\s*;|$)', 
                case=False, 
                na=False,
                regex=True
            )
        ]
        
        if trial_sites.empty:
            print(f"   ⚠️  No sites found for TrialTrove ID {trialtrove_id}")
            return []
        
        # Extract site information
        sites = []
        for _, row in trial_sites.iterrows():
            org_name = row.get('Organization Name', 'Unknown')
            lat = row.get('Organization Latitude')
            lon = row.get('Organization Longitude')
            
            # Skip sites without valid coordinates
            if pd.isna(lat) or pd.isna(lon):
                continue
            
            site_data = {
                'Organization Name': org_name,
                'site_id': str(row.get('Organization ID', org_name)),
                'Latitude': lat,
                'Longitude': lon,
                'City': row.get('Organization City', 'Unknown'),
                'State': row.get('Organization State', 'Unknown'),
                'Country': row.get('Organization Country', 'USA'),
                'Total Trials': row.get('Organization Total Trials', 0),
                'trial_count': row.get('Organization Total Trials', 0),
                'Avg Enrollment': 0,  # Not directly available
                'trialtrove_id': trialtrove_id,
                # Organization details
                'Organization Type': row.get('Organization Type'),
                'Organization Address': row.get('Organization Address'),
                'Organization Postal Code': row.get('Organization Postal Code'),
                'Organization Phones': row.get('Organization Phones'),
                'Organization Faxes': row.get('Organization Faxes'),
                'Organization Region': row.get('Organization Region'),
                'Organization NPI Number': row.get('Organization NPI Number'),
                # Trial metrics
                'Organization Total Matching Trials': row.get('Organization Total Matching Trials', 0),
                'Organization Ongoing Matching Trials': row.get('Organization Ongoing Matching Trials', 0),
                'Organization Planned Matching Trials': row.get('Organization Planned Matching Trials', 0),
                'Organization Total Matching Investigators': row.get('Organization Total Matching Investigators', 0),
                'Organization Ongoing Trials': row.get('Organization Ongoing Trials', 0),
                'Organization Planned Trials': row.get('Organization Planned Trials', 0),
                'Organization Last Trial Start Date': row.get('Organization Last Trial Start Date'),
                # Specialization
                'Organization Disease Areas': row.get('Organization Disease Areas'),
                'Organization Sponsor/Collaborator Involvement': row.get('Organization Sponsor/Collaborator Involvement'),
                # Parent organization
                'Parent Organization Name': row.get('Parent Organization Name'),
                'Parent Organization Type': row.get('Parent Organization Type'),
                'Parent Organization Total Trials': row.get('Parent Organization Total Trials', 0),
                # URLs
                'Organization Record URL': row.get('Organization Record URL'),
                'Organization Supporting URLs': row.get('Organization Supporting URLs'),
            }
            sites.append(site_data)
        
        print(f"   ✅ Found {len(sites)} sites for TrialTrove ID {trialtrove_id}")
        return sites
        
    except Exception as e:
        print(f"Error getting sites for trial {trial_id}: {e}")
        import traceback
        print(traceback.format_exc())
        return []

def _get_sites_by_therapeutic_area(site_trove_df: pd.DataFrame, therapeutic_area: str) -> List[Dict]:
    """Get sites by therapeutic area or indication"""
    try:
        # Use actual column names from SiteTrove data
        lat_col = 'Organization Latitude'
        lon_col = 'Organization Longitude'
        
        # Filter sites with valid coordinates
        valid_sites = site_trove_df[
            (site_trove_df[lat_col].notna()) & 
            (site_trove_df[lon_col].notna())
        ].head(200)
        
        sites = []
        seen_orgs = set()
        for _, row in valid_sites.iterrows():
            org_name = row.get('Organization Name', 'Unknown')
            
            # Skip duplicates
            if org_name in seen_orgs:
                continue
            seen_orgs.add(org_name)
            
            # Get coordinates
            lat = row.get(lat_col)
            lon = row.get(lon_col)
            city = row.get('Organization City', 'Unknown')
            state = row.get('Organization State', 'Unknown')
            country = row.get('Organization Country', 'USA')
            total_trials = row.get('Organization Total Trials', 0)
            
            site_data = {
                'Organization Name': org_name,
                'site_id': org_name,
                'Latitude': lat,
                'Longitude': lon,
                'City': city,
                'State': state,
                'Country': country,
                'Total Trials': total_trials,
                'trial_count': total_trials if pd.notna(total_trials) else 0,
                'Avg Enrollment': 0  # Not available in this dataset
            }
            sites.append(site_data)
        
        print(f"✅ Found {len(sites)} sites for therapeutic area: {therapeutic_area}")
        return sites
        
    except Exception as e:
        print(f"Error getting sites by therapeutic area: {e}")
        import traceback
        print(traceback.format_exc())
        return []

def _get_population_heatmap(claims_df: pd.DataFrame, icd_codes: List[str], indication: Optional[str]) -> List[PopulationHeatmapPoint]:
    """Get geographic population distribution from claims data at ZIP code level"""
    try:
        print(f"🗺️ Generating ZIP-level population heatmap for {len(icd_codes)} ICD codes")
        
        # Filter by ICD codes if provided
        if icd_codes:
            diagnosis_cols = [col for col in claims_df.columns if col.startswith('D') and col != 'DIAGNOSIS_CODE']
            if not diagnosis_cols:
                diagnosis_cols = ['DIAGNOSIS_CODE'] if 'DIAGNOSIS_CODE' in claims_df.columns else []
            
            print(f"   Diagnosis columns found: {diagnosis_cols[:5]}...")
            
            if diagnosis_cols:
                mask = pd.Series([False] * len(claims_df))
                for icd_code in icd_codes:
                    for col in diagnosis_cols:
                        mask |= claims_df[col].astype(str).str.contains(icd_code, case=False, na=False)
                
                filtered_claims = claims_df[mask]
                print(f"   Filtered to {len(filtered_claims)} claims matching ICD codes")
            else:
                filtered_claims = claims_df
                print(f"   No diagnosis columns, using all {len(claims_df)} claims")
        else:
            # Sample claims data
            filtered_claims = claims_df.sample(min(10000, len(claims_df)))
            print(f"   No ICD codes provided, sampled {len(filtered_claims)} claims")
        
        # Use BILLING_ADR_ZIP as it has the best coverage (54.7%)
        if 'BILLING_ADR_ZIP' not in filtered_claims.columns:
            print("⚠️ BILLING_ADR_ZIP column not found")
            return []
        
        # Extract ZIP5 from the 9-digit USPS ZIP+4 format
        # Format: XXXXX-XXXX stored as integer XXXXXXXXX
        valid_zips = filtered_claims[filtered_claims['BILLING_ADR_ZIP'].notna()].copy()
        valid_zips['zip5'] = valid_zips['BILLING_ADR_ZIP'].apply(
            lambda x: str(int(x)).zfill(9)[:5] if pd.notna(x) else None
        )
        
        # Filter out invalid ZIPs (00000-00999 are placeholders/test data)
        valid_zips = valid_zips[valid_zips['zip5'].notna()]
        valid_zips['zip5_int'] = valid_zips['zip5'].astype(int)
        valid_zips = valid_zips[valid_zips['zip5_int'] >= 1000]
        
        print(f"   Extracted {len(valid_zips)} claims with valid ZIP codes")
        
        # Group by ZIP5
        zip_counts = valid_zips.groupby('zip5').size().reset_index(name='count')
        print(f"   Found {len(zip_counts)} unique ZIP codes")
        
        # Extrapolate to US population (claims data is 15% sample)
        sample_rate = 0.15
        
        # Get ZIP geocoder
        geocoder = get_zip_geocoder()
        
        heatmap_points = []
        total_count = zip_counts['count'].sum()
        
        # Batch geocode ZIPs
        print(f"   Geocoding {len(zip_counts)} ZIP codes...")
        for idx, row in zip_counts.iterrows():
            zip5 = row['zip5']
            count = row['count']
            
            try:
                # Get lat/lon for this ZIP
                result = geocoder.query_postal_code(zip5)
                
                if pd.notna(result.latitude) and pd.notna(result.longitude):
                    estimated_population = int(count / sample_rate)
                    
                    heatmap_points.append(PopulationHeatmapPoint(
                        latitude=float(result.latitude),
                        longitude=float(result.longitude),
                        state=str(result.state_code) if pd.notna(result.state_code) else None,
                        city=str(result.place_name) if pd.notna(result.place_name) else None,
                        patient_count=estimated_population,
                        percentage=float(count / total_count * 100),
                        icd_codes=icd_codes if icd_codes else []
                    ))
                    
                    # Progress indicator for large datasets
                    if (idx + 1) % 100 == 0:
                        print(f"   Geocoded {idx + 1}/{len(zip_counts)} ZIPs...")
                        
            except Exception:
                # Skip ZIPs that fail to geocode
                continue
        
        print(f"✅ Generated {len(heatmap_points)} ZIP-level population heatmap points")
        print(f"   Coverage: {len(set(p.state for p in heatmap_points if p.state))} states, {len(heatmap_points)} ZIP codes")
        return heatmap_points
        
    except Exception as e:
        import traceback
        print(f"Error getting population heatmap: {e}")
        print(traceback.format_exc())
        return []

def _get_state_coordinates() -> Dict[str, Dict[str, float]]:
    """Get approximate center coordinates for US states"""
    return {
        'AL': {'lat': 32.806671, 'lon': -86.791130},
        'AK': {'lat': 61.370716, 'lon': -152.404419},
        'AZ': {'lat': 33.729759, 'lon': -111.431221},
        'AR': {'lat': 34.969704, 'lon': -92.373123},
        'CA': {'lat': 36.116203, 'lon': -119.681564},
        'CO': {'lat': 39.059811, 'lon': -105.311104},
        'CT': {'lat': 41.597782, 'lon': -72.755371},
        'DE': {'lat': 39.318523, 'lon': -75.507141},
        'FL': {'lat': 27.766279, 'lon': -81.686783},
        'GA': {'lat': 33.040619, 'lon': -83.643074},
        'HI': {'lat': 21.094318, 'lon': -157.498337},
        'ID': {'lat': 44.240459, 'lon': -114.478828},
        'IL': {'lat': 40.349457, 'lon': -88.986137},
        'IN': {'lat': 39.849426, 'lon': -86.258278},
        'IA': {'lat': 42.011539, 'lon': -93.210526},
        'KS': {'lat': 38.526600, 'lon': -96.726486},
        'KY': {'lat': 37.668140, 'lon': -84.670067},
        'LA': {'lat': 31.169546, 'lon': -91.867805},
        'ME': {'lat': 44.693947, 'lon': -69.381927},
        'MD': {'lat': 39.063946, 'lon': -76.802101},
        'MA': {'lat': 42.230171, 'lon': -71.530106},
        'MI': {'lat': 43.326618, 'lon': -84.536095},
        'MN': {'lat': 45.694454, 'lon': -93.900192},
        'MS': {'lat': 32.741646, 'lon': -89.678696},
        'MO': {'lat': 38.456085, 'lon': -92.288368},
        'MT': {'lat': 46.921925, 'lon': -110.454353},
        'NE': {'lat': 41.125370, 'lon': -98.268082},
        'NV': {'lat': 38.313515, 'lon': -117.055374},
        'NH': {'lat': 43.452492, 'lon': -71.563896},
        'NJ': {'lat': 40.298904, 'lon': -74.521011},
        'NM': {'lat': 34.840515, 'lon': -106.248482},
        'NY': {'lat': 42.165726, 'lon': -74.948051},
        'NC': {'lat': 35.630066, 'lon': -79.806419},
        'ND': {'lat': 47.528912, 'lon': -99.784012},
        'OH': {'lat': 40.388783, 'lon': -82.764915},
        'OK': {'lat': 35.565342, 'lon': -96.928917},
        'OR': {'lat': 44.572021, 'lon': -122.070938},
        'PA': {'lat': 40.590752, 'lon': -77.209755},
        'RI': {'lat': 41.680893, 'lon': -71.511780},
        'SC': {'lat': 33.856892, 'lon': -80.945007},
        'SD': {'lat': 44.299782, 'lon': -99.438828},
        'TN': {'lat': 35.747845, 'lon': -86.692345},
        'TX': {'lat': 31.054487, 'lon': -97.563461},
        'UT': {'lat': 40.150032, 'lon': -111.862434},
        'VT': {'lat': 44.045876, 'lon': -72.710686},
        'VA': {'lat': 37.769337, 'lon': -78.169968},
        'WA': {'lat': 47.400902, 'lon': -121.490494},
        'WV': {'lat': 38.491226, 'lon': -80.954453},
        'WI': {'lat': 44.268543, 'lon': -89.616508},
        'WY': {'lat': 42.755966, 'lon': -107.302490},
    }

def _calculate_coverage(sites: List[SiteLocation], population: List[PopulationHeatmapPoint]) -> Dict[str, Any]:
    """Calculate ZIP-level coverage based on proximity to sites"""
    if not sites or not population:
        return {
            'total_zip_codes': 0,
            'covered_zip_codes': 0,
            'coverage_percentage': 0,
            'total_patients': 0,
            'covered_patients': 0,
            'patient_coverage_percentage': 0,
            'underserved_areas': []
        }
    
    # Haversine distance calculation (in miles)
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 3959  # Earth's radius in miles
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    # Define coverage radius (50 miles = reasonable driving distance)
    COVERAGE_RADIUS_MILES = 50
    
    print("📊 ZIP-Level Coverage Analysis:")
    print(f"   Total sites: {len(sites)}")
    print(f"   Total ZIP codes: {len(population)}")
    print(f"   Coverage radius: {COVERAGE_RADIUS_MILES} miles")
    
    # Check each population ZIP against all sites
    covered_zips = 0
    covered_patients = 0
    total_patients = sum(p.patient_count for p in population)
    underserved = []
    
    for pop_point in population:
        is_covered = False
        min_distance = float('inf')
        
        # Check distance to each site
        for site in sites:
            distance = haversine_distance(
                pop_point.latitude, pop_point.longitude,
                site.latitude, site.longitude
            )
            min_distance = min(min_distance, distance)
            
            if distance <= COVERAGE_RADIUS_MILES:
                is_covered = True
                break
        
        if is_covered:
            covered_zips += 1
            covered_patients += pop_point.patient_count
        else:
            # Track underserved areas
            location = f"{pop_point.city}, {pop_point.state}" if pop_point.city else pop_point.state
            underserved.append({
                'location': location,
                'patients': pop_point.patient_count,
                'nearest_site_miles': round(min_distance, 1)
            })
    
    # Sort underserved by patient count (descending)
    underserved.sort(key=lambda x: x['patients'], reverse=True)
    
    zip_coverage_pct = round(covered_zips / len(population) * 100, 1) if population else 0
    patient_coverage_pct = round(covered_patients / total_patients * 100, 1) if total_patients else 0
    
    print(f"   ✅ Covered ZIPs: {covered_zips}/{len(population)} ({zip_coverage_pct}%)")
    print(f"   ✅ Covered patients: {covered_patients:,}/{total_patients:,} ({patient_coverage_pct}%)")
    print(f"   ⚠️  Underserved areas: {len(underserved)}")
    
    return {
        'total_zip_codes': len(population),
        'covered_zip_codes': covered_zips,
        'coverage_percentage': zip_coverage_pct,
        'total_patients': total_patients,
        'covered_patients': covered_patients,
        'patient_coverage_percentage': patient_coverage_pct,
        'underserved_areas': [f"{u['location']} ({u['patients']:,} patients, {u['nearest_site_miles']}mi away)" for u in underserved[:10]]
    }

