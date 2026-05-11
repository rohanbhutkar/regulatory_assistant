"""
Site Trove Agent
Provides access to site location data and trial-site relationships
"""
import asyncio
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from config import settings
from utils.logger import log_error
from models.schemas import SiteResult, TrialSiteResult, GeographicResult
import logging

logger = logging.getLogger(__name__)

class SiteTroveAgent:
    def __init__(self):
        # Use absolute path to data directory
        backend_dir = Path(__file__).parent.parent
        self.data_path = backend_dir.parent / "data"
        self.cache = {}
        self._load_data()
    
    def _load_data(self):
        """Load site trove data into memory for fast access"""
        try:
            # Load the combined site trove data
            logger.info("Loading combined site trove data...")
            self.site_df = pd.read_csv(self.data_path / "combined_site_trove.csv")
            
            # Parse trial IDs from the Organization Trialtrove Trial IDs column
            self._parse_trial_ids()
            
            # Create indexes for fast searching
            self._create_indexes()
            
            logger.info(f"Loaded {len(self.site_df)} site locations")
            
        except Exception as e:
            log_error(e, f"Error loading site trove data: {e}")
            self.site_df = pd.DataFrame()
    
    def _parse_trial_ids(self):
        """Parse trial IDs from the Organization Trialtrove Trial IDs column"""
        try:
            if 'Organization Trialtrove Trial IDs' in self.site_df.columns:
                # Split the semicolon-separated trial IDs and convert to lists
                self.site_df['parsed_trial_ids'] = self.site_df['Organization Trialtrove Trial IDs'].apply(
                    lambda x: [int(tid.strip()) for tid in str(x).split(';') if tid.strip().isdigit()] 
                    if pd.notna(x) and str(x).strip() else []
                )
                
                # Create a flattened mapping of trial_id -> site_id for fast lookups
                trial_site_mapping = []
                for idx, row in self.site_df.iterrows():
                    for trial_id in row['parsed_trial_ids']:
                        trial_site_mapping.append({
                            'trial_id': trial_id,
                            'site_id': row['Organization ID'],
                            'site_name': row['Organization Name'],
                            'site_type': row['Organization Type'],
                            'city': row['Organization City'],
                            'state': row['Organization State'],
                            'country': row['Organization Country']
                        })
                
                self.trial_site_df = pd.DataFrame(trial_site_mapping)
                logger.info(f"Created trial-site mapping with {len(self.trial_site_df)} relationships")
            else:
                logger.warning("Organization Trialtrove Trial IDs column not found")
                self.trial_site_df = pd.DataFrame()
                
        except Exception as e:
            log_error(e, f"Error parsing trial IDs: {e}")
            self.trial_site_df = pd.DataFrame()
    
    def _create_indexes(self):
        """Create indexes for fast searching"""
        try:
            # Create indexes for common search patterns
            self.site_name_index = self.site_df.set_index('Organization Name').index if not self.site_df.empty else pd.Index([])
            self.site_type_index = self.site_df.set_index('Organization Type').index if not self.site_df.empty else pd.Index([])
            self.city_index = self.site_df.set_index('Organization City').index if not self.site_df.empty else pd.Index([])
            self.state_index = self.site_df.set_index('Organization State').index if not self.site_df.empty else pd.Index([])
            self.country_index = self.site_df.set_index('Organization Country').index if not self.site_df.empty else pd.Index([])
            
            # Create trial ID index if we have trial-site mapping
            if not self.trial_site_df.empty:
                self.trial_id_index = self.trial_site_df.set_index('trial_id').index
            else:
                self.trial_id_index = pd.Index([])
                
        except Exception as e:
            log_error(e, f"Error creating indexes: {e}")
    
    async def search_sites(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for sites by name, location, or type"""
        try:
            if self.site_df.empty:
                return []
            
            query_lower = query.lower()
            results = []
            
            # Search in multiple fields
            search_fields = [
                'Organization Name',
                'Organization Type', 
                'Organization City',
                'Organization State',
                'Organization Country',
                'Organization Disease Areas'
            ]
            
            # Create search mask
            search_mask = pd.Series([False] * len(self.site_df))
            
            for field in search_fields:
                if field in self.site_df.columns:
                    field_mask = self.site_df[field].astype(str).str.lower().str.contains(query_lower, na=False)
                    search_mask = search_mask | field_mask
            
            # Get matching sites
            matching_sites = self.site_df[search_mask]
            
            for _, site in matching_sites.head(max_results).iterrows():
                results.append({
                    'site_id': str(site['Organization ID']),
                    'site_name': site['Organization Name'],
                    'site_type': site['Organization Type'],
                    'address': site['Organization Address'],
                    'city': site['Organization City'],
                    'state': site['Organization State'],
                    'country': site['Organization Country'],
                    'postal_code': site['Organization Postal Code'],
                    'longitude': site['Organization Longitude'] if pd.notna(site['Organization Longitude']) else None,
                    'latitude': site['Organization Latitude'] if pd.notna(site['Organization Latitude']) else None,
                    'total_trials': site['Organization Total Matching Trials'],
                    'ongoing_trials': site['Organization Ongoing Matching Trials'],
                    'planned_trials': site['Organization Planned Matching Trials'],
                    'disease_areas': site['Organization Disease Areas'],
                    'trial_ids': site.get('parsed_trial_ids', []),
                    'metadata': {
                        'source': 'site_trove',
                        'analysis_type': 'site_search'
                    }
                })
            
            return results
            
        except Exception as e:
            log_error(e, f"Site search failed for query: {query}")
            return []
    
    async def get_sites_by_trial_id(self, trial_id: int) -> List[Dict[str, Any]]:
        """Get all sites associated with a specific trial ID"""
        try:
            if self.trial_site_df.empty:
                return []
            
            # Find sites for this trial
            trial_sites = self.trial_site_df[self.trial_site_df['trial_id'] == trial_id]
            
            if trial_sites.empty:
                return []
            
            # Get detailed site information
            site_ids = trial_sites['site_id'].tolist()
            detailed_sites = self.site_df[self.site_df['Organization ID'].isin(site_ids)]
            
            results = []
            for _, site in detailed_sites.iterrows():
                results.append({
                    'site_id': str(site['Organization ID']),
                    'site_name': site['Organization Name'],
                    'site_type': site['Organization Type'],
                    'address': site['Organization Address'],
                    'city': site['Organization City'],
                    'state': site['Organization State'],
                    'country': site['Organization Country'],
                    'longitude': site['Organization Longitude'] if pd.notna(site['Organization Longitude']) else None,
                    'latitude': site['Organization Latitude'] if pd.notna(site['Organization Latitude']) else None,
                    'total_trials': site['Organization Total Matching Trials'],
                    'ongoing_trials': site['Organization Ongoing Matching Trials'],
                    'metadata': {
                        'source': 'site_trove',
                        'analysis_type': 'trial_sites',
                        'trial_id': trial_id
                    }
                })
            
            return results
            
        except Exception as e:
            log_error(e, f"Failed to get sites for trial ID {trial_id}: {e}")
            return []
    
    async def analyze_geographic_distribution(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Analyze geographic distribution of sites"""
        try:
            if self.site_df.empty:
                return []
            
            query_lower = query.lower()
            results = []
            
            # Filter sites based on query
            search_mask = (
                self.site_df['Organization Name'].astype(str).str.lower().str.contains(query_lower, na=False) |
                self.site_df['Organization Type'].astype(str).str.lower().str.contains(query_lower, na=False) |
                self.site_df['Organization Disease Areas'].astype(str).str.lower().str.contains(query_lower, na=False)
            )
            
            filtered_sites = self.site_df[search_mask]
            
            # Group by geographic regions
            geographic_groups = filtered_sites.groupby(['Organization Country', 'Organization State']).agg({
                'Organization ID': 'count',
                'Organization Total Matching Trials': 'sum',
                'Organization Ongoing Matching Trials': 'sum',
                'Organization Planned Matching Trials': 'sum',
                'Organization Longitude': 'mean',
                'Organization Latitude': 'mean'
            }).reset_index()
            
            geographic_groups.columns = [
                'country', 'state', 'site_count', 'total_trials', 
                'ongoing_trials', 'planned_trials', 'avg_longitude', 'avg_latitude'
            ]
            
            for _, group in geographic_groups.head(max_results).iterrows():
                results.append({
                    'country': group['country'],
                    'state': group['state'],
                    'site_count': int(group['site_count']),
                    'total_trials': int(group['total_trials']),
                    'ongoing_trials': int(group['ongoing_trials']),
                    'planned_trials': int(group['planned_trials']),
                    'avg_longitude': round(group['avg_longitude'], 6) if pd.notna(group['avg_longitude']) else None,
                    'avg_latitude': round(group['avg_latitude'], 6) if pd.notna(group['avg_latitude']) else None,
                    'metadata': {
                        'source': 'site_trove',
                        'analysis_type': 'geographic_distribution'
                    }
                })
            
            return results
            
        except Exception as e:
            log_error(e, f"Geographic distribution analysis failed for query: {query}")
            return []
    
    async def analyze_site_capacity(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze site capacity and trial activity"""
        try:
            if self.site_df.empty:
                return []
            
            query_lower = query.lower()
            
            # Filter sites based on query
            search_mask = (
                self.site_df['Organization Name'].astype(str).str.lower().str.contains(query_lower, na=False) |
                self.site_df['Organization Type'].astype(str).str.lower().str.contains(query_lower, na=False) |
                self.site_df['Organization Disease Areas'].astype(str).str.lower().str.contains(query_lower, na=False)
            )
            
            filtered_sites = self.site_df[search_mask]
            
            # Calculate capacity metrics
            filtered_sites = filtered_sites.copy()
            filtered_sites['capacity_utilization'] = (
                filtered_sites['Organization Ongoing Matching Trials'] / 
                filtered_sites['Organization Total Matching Trials'].replace(0, 1)
            )
            filtered_sites['available_capacity'] = (
                filtered_sites['Organization Total Matching Trials'] - 
                filtered_sites['Organization Ongoing Matching Trials']
            )
            
            # Sort by capacity utilization (ascending) to show sites with available capacity first
            filtered_sites = filtered_sites.sort_values('capacity_utilization', ascending=True)
            
            results = []
            for _, site in filtered_sites.head(max_results).iterrows():
                results.append({
                    'site_id': str(site['Organization ID']),
                    'site_name': site['Organization Name'],
                    'site_type': site['Organization Type'],
                    'city': site['Organization City'],
                    'state': site['Organization State'],
                    'country': site['Organization Country'],
                    'total_trials': int(site['Organization Total Matching Trials']),
                    'ongoing_trials': int(site['Organization Ongoing Matching Trials']),
                    'planned_trials': int(site['Organization Planned Matching Trials']),
                    'capacity_utilization': round(site['capacity_utilization'], 3),
                    'available_capacity': int(site['available_capacity']),
                    'disease_areas': site['Organization Disease Areas'],
                    'metadata': {
                        'source': 'site_trove',
                        'analysis_type': 'site_capacity'
                    }
                })
            
            return results
            
        except Exception as e:
            log_error(e, f"Site capacity analysis failed for query: {query}")
            return []
    
    async def get_trial_site_relationships(self, trial_ids: List[int]) -> List[Dict[str, Any]]:
        """Get site relationships for multiple trial IDs"""
        try:
            if self.trial_site_df.empty or not trial_ids:
                return []
            
            # Find all sites for the given trial IDs
            trial_sites = self.trial_site_df[self.trial_site_df['trial_id'].isin(trial_ids)]
            
            if trial_sites.empty:
                return []
            
            # Group by trial ID and aggregate site information
            trial_site_groups = trial_sites.groupby('trial_id').agg({
                'site_id': 'count',
                'site_name': lambda x: list(x),
                'site_type': lambda x: list(x),
                'city': lambda x: list(x),
                'state': lambda x: list(x),
                'country': lambda x: list(x)
            }).reset_index()
            
            trial_site_groups.columns = [
                'trial_id', 'site_count', 'site_names', 'site_types', 
                'cities', 'states', 'countries'
            ]
            
            results = []
            for _, group in trial_site_groups.iterrows():
                results.append({
                    'trial_id': int(group['trial_id']),
                    'site_count': int(group['site_count']),
                    'site_names': group['site_names'],
                    'site_types': group['site_types'],
                    'cities': group['cities'],
                    'states': group['states'],
                    'countries': group['countries'],
                    'metadata': {
                        'source': 'site_trove',
                        'analysis_type': 'trial_site_relationships'
                    }
                })
            
            return results
            
        except Exception as e:
            log_error(e, f"Trial site relationships analysis failed: {e}")
            return []
    
    def get_site_trial_count(self, org_name: str) -> int:
        """Get the number of trials a site has participated in"""
        try:
            if not hasattr(self, 'trial_sites_df') or self.trial_sites_df.empty:
                return 0
            
            # Count unique trials for this organization
            site_trials = self.trial_sites_df[
                self.trial_sites_df['Organization Name'] == org_name
            ]
            return len(site_trials['NCT Number'].unique()) if not site_trials.empty else 0
        except Exception:
            return 0

    async def get_site_details(self, site_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific site"""
        try:
            if self.site_df.empty:
                return None
            
            # Search for exact or partial match
            site_mask = self.site_df['Organization Name'].str.contains(site_name, case=False, na=False)
            matching_sites = self.site_df[site_mask]
            
            if matching_sites.empty:
                return None
            
            # Get the first match (or best match)
            site = matching_sites.iloc[0]
            
            # Get all trials for this site
            site_trials = []
            if not self.trial_site_df.empty:
                site_trial_data = self.trial_site_df[self.trial_site_df['site_id'] == site['Organization ID']]
                site_trials = site_trial_data['trial_id'].tolist()
            
            # Calculate detailed metrics
            total_trials = site['Organization Total Matching Trials']
            ongoing_trials = site['Organization Ongoing Matching Trials']
            planned_trials = site['Organization Planned Matching Trials']
            
            capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
            available_capacity = total_trials - ongoing_trials
            
            return {
                'site_id': str(site['Organization ID']),
                'site_name': site['Organization Name'],
                'site_type': site['Organization Type'],
                'address': site['Organization Address'],
                'city': site['Organization City'],
                'state': site['Organization State'],
                'country': site['Organization Country'],
                'postal_code': site['Organization Postal Code'],
                'longitude': site['Organization Longitude'] if pd.notna(site['Organization Longitude']) else None,
                'latitude': site['Organization Latitude'] if pd.notna(site['Organization Latitude']) else None,
                'total_trials': int(total_trials),
                'ongoing_trials': int(ongoing_trials),
                'planned_trials': int(planned_trials),
                'capacity_utilization': round(capacity_utilization, 3),
                'available_capacity': int(available_capacity),
                'disease_areas': site['Organization Disease Areas'],
                'trial_ids': site_trials,
                'characteristics': {
                    'is_high_capacity': total_trials > 10,
                    'is_active': ongoing_trials > 0,
                    'has_planned_trials': planned_trials > 0,
                    'capacity_status': 'high' if capacity_utilization > 0.8 else 'medium' if capacity_utilization > 0.5 else 'low',
                    'geographic_region': f"{site['Organization City']}, {site['Organization State']}, {site['Organization Country']}"
                },
                'metadata': {
                    'source': 'site_trove',
                    'analysis_type': 'site_details',
                    'query': site_name
                }
            }
            
        except Exception as e:
            log_error(e, f"Failed to get site details for: {site_name}")
            return None
    
    async def search_sites_by_characteristics(self, characteristics: Dict[str, Any], max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for sites based on specific characteristics"""
        try:
            if self.site_df.empty:
                return []
            
            # Start with all sites
            filtered_sites = self.site_df.copy()
            
            # Apply filters based on characteristics
            if 'site_type' in characteristics:
                site_type = characteristics['site_type'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Type'].str.lower().str.contains(site_type, na=False)
                ]
            
            if 'country' in characteristics:
                country = characteristics['country'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Country'].str.lower().str.contains(country, na=False)
                ]
            
            if 'state' in characteristics:
                state = characteristics['state'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization State'].str.lower().str.contains(state, na=False)
                ]
            
            if 'city' in characteristics:
                city = characteristics['city'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization City'].str.lower().str.contains(city, na=False)
                ]
            
            if 'disease_area' in characteristics:
                disease_area = characteristics['disease_area'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Disease Areas'].str.lower().str.contains(disease_area, na=False)
                ]
            
            if 'min_trials' in characteristics:
                min_trials = characteristics['min_trials']
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Total Matching Trials'] >= min_trials
                ]
            
            if 'max_trials' in characteristics:
                max_trials = characteristics['max_trials']
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Total Matching Trials'] <= max_trials
                ]
            
            if 'has_ongoing_trials' in characteristics and characteristics['has_ongoing_trials']:
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Ongoing Matching Trials'] > 0
                ]
            
            if 'has_available_capacity' in characteristics and characteristics['has_available_capacity']:
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Total Matching Trials'] > 
                    filtered_sites['Organization Ongoing Matching Trials']
                ]
            
            # Sort by total trials (descending) to show most active sites first
            filtered_sites = filtered_sites.sort_values('Organization Total Matching Trials', ascending=False)
            
            results = []
            for _, site in filtered_sites.head(max_results).iterrows():
                total_trials = site['Organization Total Matching Trials']
                ongoing_trials = site['Organization Ongoing Matching Trials']
                capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
                available_capacity = total_trials - ongoing_trials
                
                results.append({
                    'site_id': str(site['Organization ID']),
                    'site_name': site['Organization Name'],
                    'site_type': site['Organization Type'],
                    'address': site['Organization Address'],
                    'city': site['Organization City'],
                    'state': site['Organization State'],
                    'country': site['Organization Country'],
                    'postal_code': site['Organization Postal Code'],
                    'longitude': site['Organization Longitude'] if pd.notna(site['Organization Longitude']) else None,
                    'latitude': site['Organization Latitude'] if pd.notna(site['Organization Latitude']) else None,
                    'total_trials': int(total_trials),
                    'ongoing_trials': int(ongoing_trials),
                    'planned_trials': int(site['Organization Planned Matching Trials']),
                    'capacity_utilization': round(capacity_utilization, 3),
                    'available_capacity': int(available_capacity),
                    'disease_areas': site['Organization Disease Areas'],
                    'characteristics': {
                        'is_high_capacity': total_trials > 10,
                        'is_active': ongoing_trials > 0,
                        'has_planned_trials': site['Organization Planned Matching Trials'] > 0,
                        'capacity_status': 'high' if capacity_utilization > 0.8 else 'medium' if capacity_utilization > 0.5 else 'low',
                        'geographic_region': f"{site['Organization City']}, {site['Organization State']}, {site['Organization Country']}"
                    },
                    'metadata': {
                        'source': 'site_trove',
                        'analysis_type': 'characteristics_search',
                        'filters_applied': characteristics
                    }
                })
            
            return results
            
        except Exception as e:
            log_error(e, f"Site characteristics search failed: {e}")
            return []
    
    async def compare_sites(self, site_names: List[str]) -> Dict[str, Any]:
        """Compare multiple sites side by side"""
        try:
            if not site_names or len(site_names) < 2:
                return {'error': 'At least 2 sites required for comparison'}
            
            site_details = []
            for site_name in site_names:
                details = await self.get_site_details(site_name)
                if details:
                    site_details.append(details)
            
            if len(site_details) < 2:
                return {'error': 'Could not find details for at least 2 sites'}
            
            # Create comparison metrics
            comparison = {
                'sites': site_details,
                'comparison_metrics': {
                    'total_trials': {
                        'highest': max(site['total_trials'] for site in site_details),
                        'lowest': min(site['total_trials'] for site in site_details),
                        'average': round(sum(site['total_trials'] for site in site_details) / len(site_details), 2)
                    },
                    'ongoing_trials': {
                        'highest': max(site['ongoing_trials'] for site in site_details),
                        'lowest': min(site['ongoing_trials'] for site in site_details),
                        'average': round(sum(site['ongoing_trials'] for site in site_details) / len(site_details), 2)
                    },
                    'capacity_utilization': {
                        'highest': max(site['capacity_utilization'] for site in site_details),
                        'lowest': min(site['capacity_utilization'] for site in site_details),
                        'average': round(sum(site['capacity_utilization'] for site in site_details) / len(site_details), 3)
                    },
                    'available_capacity': {
                        'highest': max(site['available_capacity'] for site in site_details),
                        'lowest': min(site['available_capacity'] for site in site_details),
                        'average': round(sum(site['available_capacity'] for site in site_details) / len(site_details), 2)
                    }
                },
                'geographic_distribution': {
                    'countries': list(set(site['country'] for site in site_details)),
                    'states': list(set(site['state'] for site in site_details)),
                    'cities': list(set(site['city'] for site in site_details))
                },
                'site_types': list(set(site['site_type'] for site in site_details)),
                'disease_areas': list(set(site['disease_areas'] for site in site_details if site['disease_areas'])),
                'metadata': {
                    'source': 'site_trove',
                    'analysis_type': 'site_comparison',
                    'sites_compared': len(site_details)
                }
            }
            
            return comparison
            
        except Exception as e:
            log_error(e, f"Site comparison failed: {e}")
            return {'error': f'Site comparison failed: {e}'}
    
    async def structure_site_list(self, criteria: Dict[str, Any], max_results: int = 100) -> Dict[str, Any]:
        """Structure a site list based on historical performance and criteria"""
        try:
            if self.site_df.empty:
                return {'error': 'No site data available'}
            
            # Start with all sites
            filtered_sites = self.site_df.copy()
            
            # Apply filtering criteria
            if 'therapeutic_area' in criteria:
                ta = criteria['therapeutic_area'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Disease Areas'].str.lower().str.contains(ta, na=False)
                ]
            
            if 'geographic_region' in criteria:
                region = criteria['geographic_region'].lower()
                if 'country' in region:
                    country = region.split('country:')[1].strip()
                    filtered_sites = filtered_sites[
                        filtered_sites['Organization Country'].str.lower().str.contains(country, na=False)
                    ]
                elif 'state' in region:
                    state = region.split('state:')[1].strip()
                    filtered_sites = filtered_sites[
                        filtered_sites['Organization State'].str.lower().str.contains(state, na=False)
                    ]
            
            if 'site_type' in criteria:
                site_type = criteria['site_type'].lower()
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Type'].str.lower().str.contains(site_type, na=False)
                ]
            
            if 'min_trial_experience' in criteria:
                min_trials = criteria['min_trial_experience']
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Total Matching Trials'] >= min_trials
                ]
            
            if 'max_trial_experience' in criteria:
                max_trials = criteria['max_trial_experience']
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Total Matching Trials'] <= max_trials
                ]
            
            if 'has_ongoing_capacity' in criteria and criteria['has_ongoing_capacity']:
                filtered_sites = filtered_sites[
                    filtered_sites['Organization Total Matching Trials'] > 
                    filtered_sites['Organization Ongoing Matching Trials']
                ]
            
            # Calculate site performance metrics
            filtered_sites = filtered_sites.copy()
            filtered_sites['capacity_utilization'] = (
                filtered_sites['Organization Ongoing Matching Trials'] / 
                filtered_sites['Organization Total Matching Trials'].replace(0, 1)
            )
            filtered_sites['available_capacity'] = (
                filtered_sites['Organization Total Matching Trials'] - 
                filtered_sites['Organization Ongoing Matching Trials']
            )
            filtered_sites['trial_velocity'] = (
                filtered_sites['Organization Ongoing Matching Trials'] + 
                filtered_sites['Organization Planned Matching Trials']
            )
            
            # Sort by performance metrics
            sort_by = criteria.get('sort_by', 'total_trials')
            ascending = criteria.get('ascending', False)
            
            if sort_by == 'total_trials':
                filtered_sites = filtered_sites.sort_values('Organization Total Matching Trials', ascending=ascending)
            elif sort_by == 'capacity_utilization':
                filtered_sites = filtered_sites.sort_values('capacity_utilization', ascending=ascending)
            elif sort_by == 'available_capacity':
                filtered_sites = filtered_sites.sort_values('available_capacity', ascending=ascending)
            elif sort_by == 'trial_velocity':
                filtered_sites = filtered_sites.sort_values('trial_velocity', ascending=ascending)
            
            # Structure the site list
            site_list = []
            for _, site in filtered_sites.head(max_results).iterrows():
                site_info = {
                    'site_id': str(site['Organization ID']),
                    'site_name': site['Organization Name'],
                    'site_type': site['Organization Type'],
                    'location': {
                        'address': site['Organization Address'],
                        'city': site['Organization City'],
                        'state': site['Organization State'],
                        'country': site['Organization Country'],
                        'postal_code': site['Organization Postal Code'],
                        'coordinates': {
                            'longitude': site['Organization Longitude'] if pd.notna(site['Organization Longitude']) else None,
                            'latitude': site['Organization Latitude'] if pd.notna(site['Organization Latitude']) else None
                        }
                    },
                    'trial_metrics': {
                        'total_trials': int(site['Organization Total Matching Trials']),
                        'ongoing_trials': int(site['Organization Ongoing Matching Trials']),
                        'planned_trials': int(site['Organization Planned Matching Trials']),
                        'capacity_utilization': round(site['capacity_utilization'], 3),
                        'available_capacity': int(site['available_capacity']),
                        'trial_velocity': int(site['trial_velocity'])
                    },
                    'specialization': {
                        'disease_areas': site['Organization Disease Areas'],
                        'therapeutic_focus': self._extract_therapeutic_focus(site['Organization Disease Areas'])
                    },
                    'performance_tier': self._calculate_performance_tier(site),
                    'recommendation_score': self._calculate_recommendation_score(site, criteria)
                }
                site_list.append(site_info)
            
            # Generate site list summary
            summary = {
                'total_sites': len(site_list),
                'criteria_applied': criteria,
                'performance_distribution': self._calculate_performance_distribution(site_list),
                'geographic_distribution': self._calculate_geographic_distribution(site_list),
                'specialization_breakdown': self._calculate_specialization_breakdown(site_list),
                'top_performers': site_list[:10] if len(site_list) >= 10 else site_list,
                'metadata': {
                    'source': 'site_trove',
                    'analysis_type': 'site_list_structure',
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            return {
                'site_list': site_list,
                'summary': summary
            }
            
        except Exception as e:
            log_error(e, f"Site list structuring failed: {e}")
            return {'error': f'Site list structuring failed: {e}'}
    
    async def compare_trial_site_selection(self, trial_ids: List[int]) -> Dict[str, Any]:
        """Compare site selection patterns between different trials"""
        try:
            if not trial_ids or len(trial_ids) < 2:
                return {'error': 'At least 2 trial IDs required for comparison'}
            
            if self.trial_site_df.empty:
                return {'error': 'No trial-site mapping data available'}
            
            # Get sites for each trial
            trial_site_data = {}
            for trial_id in trial_ids:
                trial_sites = self.trial_site_df[self.trial_site_df['trial_id'] == trial_id]
                if not trial_sites.empty:
                    trial_site_data[trial_id] = trial_sites
            
            if len(trial_site_data) < 2:
                return {'error': 'Insufficient trial-site data for comparison'}
            
            # Analyze site selection patterns
            comparison_analysis = {
                'trial_ids': trial_ids,
                'site_overlap_analysis': self._analyze_site_overlap(trial_site_data),
                'geographic_patterns': self._analyze_geographic_patterns(trial_site_data),
                'site_type_distribution': self._analyze_site_type_distribution(trial_site_data),
                'site_experience_comparison': self._analyze_site_experience(trial_site_data),
                'selection_strategy_insights': self._generate_selection_insights(trial_site_data),
                'recommendations': self._generate_site_selection_recommendations(trial_site_data)
            }
            
            return {
                'comparison_analysis': comparison_analysis,
                'metadata': {
                    'source': 'site_trove',
                    'analysis_type': 'trial_site_selection_comparison',
                    'trials_compared': len(trial_site_data),
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            log_error(e, f"Trial site selection comparison failed: {e}")
            return {'error': f'Trial site selection comparison failed: {e}'}
    
    async def analyze_site_dynamics(self, site_id: str, analysis_period: str = 'all') -> Dict[str, Any]:
        """Analyze site dynamics and performance over time at individual site level"""
        try:
            if self.site_df.empty:
                return {'error': 'No site data available'}
            
            # Find the site
            site_data = self.site_df[self.site_df['Organization ID'] == site_id]
            if site_data.empty:
                return {'error': f'Site {site_id} not found'}
            
            site = site_data.iloc[0]
            
            # Get trial history for this site
            site_trials = []
            if not self.trial_site_df.empty:
                site_trial_data = self.trial_site_df[self.trial_site_df['site_id'] == site_id]
                site_trials = site_trial_data['trial_id'].tolist()
            
            # Calculate site dynamics metrics
            dynamics_analysis = {
                'site_profile': {
                    'site_id': site_id,
                    'site_name': site['Organization Name'],
                    'site_type': site['Organization Type'],
                    'location': {
                        'city': site['Organization City'],
                        'state': site['Organization State'],
                        'country': site['Organization Country']
                    }
                },
                'trial_participation': {
                    'total_trials': int(site['Organization Total Matching Trials']),
                    'ongoing_trials': int(site['Organization Ongoing Matching Trials']),
                    'planned_trials': int(site['Organization Planned Matching Trials']),
                    'trial_ids': site_trials
                },
                'performance_metrics': {
                    'capacity_utilization': round(
                        site['Organization Ongoing Matching Trials'] / 
                        site['Organization Total Matching Trials'] if site['Organization Total Matching Trials'] > 0 else 0, 3
                    ),
                    'available_capacity': int(
                        site['Organization Total Matching Trials'] - 
                        site['Organization Ongoing Matching Trials']
                    ),
                    'trial_velocity': int(
                        site['Organization Ongoing Matching Trials'] + 
                        site['Organization Planned Matching Trials']
                    )
                },
                'specialization_analysis': {
                    'disease_areas': site['Organization Disease Areas'],
                    'therapeutic_focus': self._extract_therapeutic_focus(site['Organization Disease Areas']),
                    'specialization_depth': self._calculate_specialization_depth(site)
                },
                'competitive_positioning': {
                    'performance_tier': self._calculate_performance_tier(site),
                    'market_position': self._calculate_market_position(site),
                    'competitive_advantages': self._identify_competitive_advantages(site)
                },
                'growth_trajectory': {
                    'capacity_trend': self._analyze_capacity_trend(site),
                    'specialization_evolution': self._analyze_specialization_evolution(site),
                    'geographic_expansion_potential': self._assess_expansion_potential(site)
                },
                'recommendations': {
                    'optimization_opportunities': self._identify_optimization_opportunities(site),
                    'partnership_potential': self._assess_partnership_potential(site),
                    'risk_factors': self._identify_risk_factors(site)
                }
            }
            
            return {
                'site_dynamics': dynamics_analysis,
                'metadata': {
                    'source': 'site_trove',
                    'analysis_type': 'site_dynamics',
                    'site_id': site_id,
                    'analysis_period': analysis_period,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            log_error(e, f"Site dynamics analysis failed for site {site_id}: {e}")
            return {'error': f'Site dynamics analysis failed: {e}'}
    
    def _extract_therapeutic_focus(self, disease_areas: str) -> List[str]:
        """Extract therapeutic focus areas from disease areas string"""
        if pd.isna(disease_areas) or not disease_areas:
            return []
        
        # Common therapeutic areas
        therapeutic_areas = [
            'oncology', 'cancer', 'cardiovascular', 'diabetes', 'neurology',
            'immunology', 'infectious_disease', 'respiratory', 'gastroenterology',
            'dermatology', 'ophthalmology', 'urology', 'gynecology', 'pediatrics'
        ]
        
        focus_areas = []
        disease_lower = disease_areas.lower()
        for area in therapeutic_areas:
            if area in disease_lower:
                focus_areas.append(area)
        
        return focus_areas
    
    def _calculate_performance_tier(self, site) -> str:
        """Calculate performance tier based on site metrics"""
        total_trials = site['Organization Total Matching Trials']
        ongoing_trials = site['Organization Ongoing Matching Trials']
        capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
        
        if total_trials >= 20 and capacity_utilization >= 0.7:
            return 'premium'
        elif total_trials >= 10 and capacity_utilization >= 0.5:
            return 'high'
        elif total_trials >= 5:
            return 'medium'
        else:
            return 'emerging'
    
    def _calculate_recommendation_score(self, site, criteria: Dict[str, Any]) -> float:
        """Calculate recommendation score based on criteria"""
        score = 0.0
        
        # Trial experience score (0-0.4)
        total_trials = site['Organization Total Matching Trials']
        if total_trials >= 20:
            score += 0.4
        elif total_trials >= 10:
            score += 0.3
        elif total_trials >= 5:
            score += 0.2
        else:
            score += 0.1
        
        # Capacity utilization score (0-0.3)
        ongoing_trials = site['Organization Ongoing Matching Trials']
        capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
        if 0.3 <= capacity_utilization <= 0.8:  # Optimal range
            score += 0.3
        elif capacity_utilization < 0.3:  # Low utilization
            score += 0.2
        else:  # High utilization
            score += 0.1
        
        # Geographic score (0-0.2)
        if 'geographic_region' in criteria:
            region = criteria['geographic_region'].lower()
            if 'country' in region:
                country = region.split('country:')[1].strip()
                if country.lower() in site['Organization Country'].lower():
                    score += 0.2
        
        # Specialization score (0-0.1)
        if 'therapeutic_area' in criteria:
            ta = criteria['therapeutic_area'].lower()
            if ta in site['Organization Disease Areas'].lower():
                score += 0.1
        
        return round(score, 3)
    
    def _calculate_performance_distribution(self, site_list: List[Dict]) -> Dict[str, int]:
        """Calculate performance tier distribution"""
        distribution = {'premium': 0, 'high': 0, 'medium': 0, 'emerging': 0}
        for site in site_list:
            tier = site['performance_tier']
            distribution[tier] += 1
        return distribution
    
    def _calculate_geographic_distribution(self, site_list: List[Dict]) -> Dict[str, int]:
        """Calculate geographic distribution"""
        distribution = {}
        for site in site_list:
            country = site['location']['country']
            distribution[country] = distribution.get(country, 0) + 1
        return distribution
    
    def _calculate_specialization_breakdown(self, site_list: List[Dict]) -> Dict[str, int]:
        """Calculate specialization breakdown"""
        breakdown = {}
        for site in site_list:
            focus_areas = site['specialization']['therapeutic_focus']
            for area in focus_areas:
                breakdown[area] = breakdown.get(area, 0) + 1
        return breakdown
    
    def _analyze_site_overlap(self, trial_site_data: Dict[int, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze site overlap between trials"""
        trial_ids = list(trial_site_data.keys())
        overlap_analysis = {}
        
        for i, trial1 in enumerate(trial_ids):
            for j, trial2 in enumerate(trial_ids[i+1:], i+1):
                sites1 = set(trial_site_data[trial1]['site_id'].tolist())
                sites2 = set(trial_site_data[trial2]['site_id'].tolist())
                
                overlap_sites = sites1.intersection(sites2)
                overlap_percentage = len(overlap_sites) / len(sites1.union(sites2)) if sites1.union(sites2) else 0
                
                overlap_analysis[f'{trial1}_vs_{trial2}'] = {
                    'overlap_count': len(overlap_sites),
                    'overlap_percentage': round(overlap_percentage, 3),
                    'trial1_sites': len(sites1),
                    'trial2_sites': len(sites2),
                    'overlap_sites': list(overlap_sites)
                }
        
        return overlap_analysis
    
    def _analyze_geographic_patterns(self, trial_site_data: Dict[int, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze geographic patterns across trials"""
        patterns = {}
        
        for trial_id, sites_df in trial_site_data.items():
            country_dist = sites_df['country'].value_counts().to_dict()
            state_dist = sites_df['state'].value_counts().to_dict()
            
            patterns[trial_id] = {
                'country_distribution': country_dist,
                'state_distribution': state_dist,
                'geographic_diversity': len(country_dist),
                'primary_country': max(country_dist, key=country_dist.get) if country_dist else None
            }
        
        return patterns
    
    def _analyze_site_type_distribution(self, trial_site_data: Dict[int, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze site type distribution across trials"""
        distributions = {}
        
        for trial_id, sites_df in trial_site_data.items():
            type_dist = sites_df['site_type'].value_counts().to_dict()
            distributions[trial_id] = {
                'site_type_distribution': type_dist,
                'type_diversity': len(type_dist),
                'primary_type': max(type_dist, key=type_dist.get) if type_dist else None
            }
        
        return distributions
    
    def _analyze_site_experience(self, trial_site_data: Dict[int, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze site experience patterns across trials"""
        experience_analysis = {}
        
        for trial_id, sites_df in trial_site_data.items():
            # Get detailed site information for experience analysis
            site_ids = sites_df['site_id'].tolist()
            detailed_sites = self.site_df[self.site_df['Organization ID'].isin(site_ids)]
            
            if not detailed_sites.empty:
                avg_trials = detailed_sites['Organization Total Matching Trials'].mean()
                max_trials = detailed_sites['Organization Total Matching Trials'].max()
                min_trials = detailed_sites['Organization Total Matching Trials'].min()
                
                experience_analysis[trial_id] = {
                    'average_trial_experience': round(avg_trials, 2),
                    'max_trial_experience': int(max_trials),
                    'min_trial_experience': int(min_trials),
                    'experience_range': int(max_trials - min_trials),
                    'high_experience_sites': len(detailed_sites[detailed_sites['Organization Total Matching Trials'] >= 10])
                }
        
        return experience_analysis
    
    def _generate_selection_insights(self, trial_site_data: Dict[int, pd.DataFrame]) -> List[str]:
        """Generate insights about site selection strategies"""
        insights = []
        
        # Analyze common patterns
        all_sites = set()
        for sites_df in trial_site_data.values():
            all_sites.update(sites_df['site_id'].tolist())
        
        # Geographic concentration insight
        country_counts = {}
        for sites_df in trial_site_data.values():
            for country in sites_df['country']:
                country_counts[country] = country_counts.get(country, 0) + 1
        
        if country_counts:
            primary_country = max(country_counts, key=country_counts.get)
            insights.append(f"Geographic concentration: {primary_country} is the primary country across trials")
        
        # Site type preference insight
        type_counts = {}
        for sites_df in trial_site_data.values():
            for site_type in sites_df['site_type']:
                type_counts[site_type] = type_counts.get(site_type, 0) + 1
        
        if type_counts:
            preferred_type = max(type_counts, key=type_counts.get)
            insights.append(f"Site type preference: {preferred_type} sites are most commonly selected")
        
        return insights
    
    def _generate_site_selection_recommendations(self, trial_site_data: Dict[int, pd.DataFrame]) -> List[str]:
        """Generate recommendations for site selection"""
        recommendations = []
        
        # Analyze site overlap patterns
        overlap_counts = {}
        for sites_df in trial_site_data.values():
            for site_id in sites_df['site_id']:
                overlap_counts[site_id] = overlap_counts.get(site_id, 0) + 1
        
        # Identify high-performing sites
        high_performing_sites = [site_id for site_id, count in overlap_counts.items() if count > 1]
        
        if high_performing_sites:
            recommendations.append(f"Consider re-engaging {len(high_performing_sites)} sites that have been selected for multiple trials")
        
        # Geographic diversity recommendation
        all_countries = set()
        for sites_df in trial_site_data.values():
            all_countries.update(sites_df['country'].tolist())
        
        if len(all_countries) < 3:
            recommendations.append("Consider increasing geographic diversity in site selection")
        
        return recommendations
    
    def _calculate_specialization_depth(self, site) -> str:
        """Calculate specialization depth based on disease areas"""
        disease_areas = site['Organization Disease Areas']
        if pd.isna(disease_areas) or not disease_areas:
            return 'general'
        
        focus_areas = self._extract_therapeutic_focus(disease_areas)
        
        if len(focus_areas) == 0:
            return 'general'
        elif len(focus_areas) == 1:
            return 'highly_specialized'
        elif len(focus_areas) <= 3:
            return 'specialized'
        else:
            return 'multi_specialty'
    
    def _calculate_market_position(self, site) -> str:
        """Calculate market position based on site metrics"""
        total_trials = site['Organization Total Matching Trials']
        
        if total_trials >= 20:
            return 'market_leader'
        elif total_trials >= 10:
            return 'established_player'
        elif total_trials >= 5:
            return 'growing_presence'
        else:
            return 'emerging_player'
    
    def _identify_competitive_advantages(self, site) -> List[str]:
        """Identify competitive advantages of the site"""
        advantages = []
        
        total_trials = site['Organization Total Matching Trials']
        ongoing_trials = site['Organization Ongoing Matching Trials']
        capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
        
        if total_trials >= 15:
            advantages.append('high_trial_experience')
        
        if 0.3 <= capacity_utilization <= 0.7:
            advantages.append('optimal_capacity_utilization')
        
        if site['Organization Type'] and 'university' in site['Organization Type'].lower():
            advantages.append('academic_affiliation')
        
        if site['Organization Disease Areas'] and len(self._extract_therapeutic_focus(site['Organization Disease Areas'])) == 1:
            advantages.append('therapeutic_specialization')
        
        return advantages
    
    def _analyze_capacity_trend(self, site) -> str:
        """Analyze capacity trend for the site"""
        total_trials = site['Organization Total Matching Trials']
        ongoing_trials = site['Organization Ongoing Matching Trials']
        planned_trials = site['Organization Planned Matching Trials']
        
        capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
        
        if capacity_utilization > 0.8:
            return 'high_utilization'
        elif capacity_utilization > 0.5:
            return 'moderate_utilization'
        else:
            return 'low_utilization'
    
    def _analyze_specialization_evolution(self, site) -> str:
        """Analyze specialization evolution"""
        specialization_depth = self._calculate_specialization_depth(site)
        
        if specialization_depth == 'highly_specialized':
            return 'deepening_specialization'
        elif specialization_depth == 'multi_specialty':
            return 'broadening_scope'
        else:
            return 'stable_specialization'
    
    def _assess_expansion_potential(self, site) -> str:
        """Assess geographic expansion potential"""
        total_trials = site['Organization Total Matching Trials']
        
        if total_trials >= 15:
            return 'high_expansion_potential'
        elif total_trials >= 8:
            return 'moderate_expansion_potential'
        else:
            return 'limited_expansion_potential'
    
    def _identify_optimization_opportunities(self, site) -> List[str]:
        """Identify optimization opportunities"""
        opportunities = []
        
        total_trials = site['Organization Total Matching Trials']
        ongoing_trials = site['Organization Ongoing Matching Trials']
        capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
        
        if capacity_utilization < 0.3:
            opportunities.append('increase_trial_recruitment')
        
        if total_trials < 10:
            opportunities.append('build_trial_experience')
        
        if not site['Organization Disease Areas'] or pd.isna(site['Organization Disease Areas']):
            opportunities.append('define_therapeutic_specialization')
        
        return opportunities
    
    def _assess_partnership_potential(self, site) -> str:
        """Assess partnership potential"""
        total_trials = site['Organization Total Matching Trials']
        market_position = self._calculate_market_position(site)
        
        if market_position in ['market_leader', 'established_player']:
            return 'high_partnership_potential'
        elif market_position == 'growing_presence':
            return 'moderate_partnership_potential'
        else:
            return 'emerging_partnership_potential'
    
    def _identify_risk_factors(self, site) -> List[str]:
        """Identify risk factors"""
        risks = []
        
        total_trials = site['Organization Total Matching Trials']
        ongoing_trials = site['Organization Ongoing Matching Trials']
        capacity_utilization = ongoing_trials / total_trials if total_trials > 0 else 0
        
        if capacity_utilization > 0.9:
            risks.append('overcapacity_risk')
        
        if total_trials < 3:
            risks.append('limited_experience')
        
        if not site['Organization Disease Areas'] or pd.isna(site['Organization Disease Areas']):
            risks.append('undefined_specialization')
        
        return risks

# Create global instance
site_trove_agent = SiteTroveAgent()

site_trove_agent =  SiteTroveAgent()
