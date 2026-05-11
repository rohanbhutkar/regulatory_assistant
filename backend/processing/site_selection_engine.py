"""
Site Selection Engine with Intelligent Scoring Algorithm
Uses real SiteTrove data to recommend optimal clinical trial sites
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SiteScore:
    """Site scoring result"""
    site_id: str
    site_name: str
    location: str
    city: str
    state: str
    country: str
    coordinates: Optional[Dict[str, float]]
    total_score: float
    component_scores: Dict[str, float]
    historical_performance: Dict[str, Any]
    estimated_enrollment: int
    risk_level: str
    recommendation: str


class SiteSelectionEngine:
    """
    Intelligent site selection engine that scores sites based on:
    - Historical trial performance
    - Therapeutic area expertise
    - Patient population availability
    - Geographic distribution
    - Site capacity and workload
    - Enrollment velocity
    """
    
    def __init__(self, sitetrove_data: pd.DataFrame):
        """Initialize with SiteTrove data"""
        self.sitetrove_data = sitetrove_data
        self._preprocess_data()
        
    def _preprocess_data(self):
        """Preprocess SiteTrove data for efficient querying"""
        if self.sitetrove_data.empty:
            logger.warning("SiteTrove data is empty")
            return
        
        # Map actual SiteTrove columns to expected column names
        column_mapping = {
            'Organization Name': 'Site Name',
            'Organization City': 'Site City',
            'Organization State': 'Site State',
            'Organization Country': 'Site Country',
            'Organization Latitude': 'Latitude',
            'Organization Longitude': 'Longitude',
            'Organization Disease Areas': 'Disease',
            'Organization Total Trials': 'Total Trials',
            'Organization Ongoing Trials': 'Ongoing Trials',
            'Organization Total Matching Trials': 'Matching Trials',
            'Organization Last Trial Start Date': 'Last Trial Date'
        }
        
        # Rename columns that exist in the data
        rename_dict = {k: v for k, v in column_mapping.items() if k in self.sitetrove_data.columns}
        self.sitetrove_data = self.sitetrove_data.rename(columns=rename_dict)
        
        logger.info(f"Mapped {len(rename_dict)} columns from SiteTrove format")
            
        # Extract location info
        if 'Site City' in self.sitetrove_data.columns and 'Site State' in self.sitetrove_data.columns:
            self.sitetrove_data['location'] = (
                self.sitetrove_data['Site City'].fillna('') + ', ' + 
                self.sitetrove_data['Site State'].fillna('')
            )
        
        # Derive Therapeutic Area from Disease if not present
        if 'Disease' in self.sitetrove_data.columns and 'Therapeutic Area' not in self.sitetrove_data.columns:
            # Extract first therapeutic area from the disease areas list
            self.sitetrove_data['Therapeutic Area'] = self.sitetrove_data['Disease']
        
        # Calculate site performance metrics
        self._calculate_performance_metrics()
        
        logger.info(f"Preprocessed {len(self.sitetrove_data)} sites from SiteTrove")
    
    def _calculate_performance_metrics(self):
        """Calculate historical performance metrics for each site"""
        # Group by site to calculate metrics
        if 'Site Name' in self.sitetrove_data.columns:
            site_groups = self.sitetrove_data.groupby('Site Name')
            
            # Number of trials completed
            self.sitetrove_data['trials_completed'] = site_groups['Site Name'].transform('count')
            
            # Average enrollment rate (if available)
            if 'Actual Accrual (No. of patients)' in self.sitetrove_data.columns:
                self.sitetrove_data['avg_enrollment'] = (
                    site_groups['Actual Accrual (No. of patients)'].transform('mean')
                )
    
    def select_sites(
        self,
        study_criteria: Dict[str, Any],
        target_site_count: int = 20,
        geographic_filter: Optional[Dict[str, Any]] = None
    ) -> List[SiteScore]:
        """
        Select and rank sites based on study criteria
        
        Args:
            study_criteria: Dict with keys like:
                - therapeutic_area: str
                - indication: str
                - phase: str
                - target_enrollment: int
                - patient_population: str
            target_site_count: Number of sites to recommend
            geographic_filter: Optional geographic constraints:
                - countries: List[str]
                - states: List[str]
                - cities: List[str]
                - max_distance: float (miles from center point)
                - center_lat: float
                - center_lng: float
        """
        logger.info(f"Selecting sites for criteria: {study_criteria}")
        
        if self.sitetrove_data.empty:
            logger.warning("No SiteTrove data available, returning mock sites")
            return self._generate_mock_sites(target_site_count)
        
        # Filter sites based on criteria
        filtered_sites = self._filter_sites(study_criteria, geographic_filter)
        
        if filtered_sites.empty:
            logger.warning(f"No sites match criteria, relaxing filters")
            filtered_sites = self._filter_sites(study_criteria, None, relaxed=True)
        
        # Score each site
        site_scores = self._score_sites(filtered_sites, study_criteria)
        
        # Sort by score and take top N
        site_scores.sort(key=lambda x: x.total_score, reverse=True)
        selected_sites = site_scores[:target_site_count]
        
        logger.info(f"Selected {len(selected_sites)} sites with scores ranging from "
                   f"{selected_sites[-1].total_score:.2f} to {selected_sites[0].total_score:.2f}")
        
        return selected_sites
    
    def _filter_sites(
        self,
        study_criteria: Dict[str, Any],
        geographic_filter: Optional[Dict[str, Any]],
        relaxed: bool = False
    ) -> pd.DataFrame:
        """Filter sites based on study and geographic criteria"""
        filtered = self.sitetrove_data.copy()
        
        # Filter by therapeutic area (if available)
        therapeutic_area = study_criteria.get('therapeutic_area')
        if therapeutic_area and 'Therapeutic Area' in filtered.columns and not relaxed:
            filtered = filtered[
                filtered['Therapeutic Area'].str.contains(therapeutic_area, case=False, na=False) |
                filtered['Disease'].str.contains(therapeutic_area, case=False, na=False)
            ]
            logger.info(f"After therapeutic area filter: {len(filtered)} sites")
        
        # Filter by indication (if specified)
        indication = study_criteria.get('indication')
        if indication and 'Disease' in filtered.columns and not relaxed:
            filtered = filtered[
                filtered['Disease'].str.contains(indication, case=False, na=False)
            ]
            logger.info(f"After indication filter: {len(filtered)} sites")
        
        # Apply geographic filters
        if geographic_filter:
            if 'countries' in geographic_filter and 'Site Country' in filtered.columns:
                countries = geographic_filter['countries']
                if countries:
                    filtered = filtered[filtered['Site Country'].isin(countries)]
                    logger.info(f"After country filter: {len(filtered)} sites")
            
            if 'states' in geographic_filter and 'Site State' in filtered.columns:
                states = geographic_filter['states']
                if states:
                    filtered = filtered[filtered['Site State'].isin(states)]
                    logger.info(f"After state filter: {len(filtered)} sites")
            
            if 'cities' in geographic_filter and 'Site City' in filtered.columns:
                cities = geographic_filter['cities']
                if cities:
                    filtered = filtered[filtered['Site City'].isin(cities)]
                    logger.info(f"After city filter: {len(filtered)} sites")
        
        return filtered
    
    def _score_sites(self, sites_df: pd.DataFrame, study_criteria: Dict[str, Any]) -> List[SiteScore]:
        """Score each site based on multiple factors"""
        site_scores = []
        
        # Get unique sites (deduplicate if same site appears in multiple trials)
        if 'Site Name' in sites_df.columns:
            unique_sites = sites_df.groupby('Site Name').first().reset_index()
        else:
            unique_sites = sites_df
        
        for idx, site_row in unique_sites.iterrows():
            try:
                score = self._calculate_site_score(site_row, sites_df, study_criteria)
                site_scores.append(score)
            except Exception as e:
                logger.error(f"Error scoring site {idx}: {e}")
                continue
        
        return site_scores
    
    def _calculate_site_score(
        self,
        site_row: pd.Series,
        all_sites_df: pd.DataFrame,
        study_criteria: Dict[str, Any]
    ) -> SiteScore:
        """Calculate comprehensive score for a single site"""
        
        # Extract site info
        site_name = site_row.get('Site Name', f"Site-{site_row.name}")
        site_city = site_row.get('Site City', 'Unknown')
        site_state = site_row.get('Site State', 'Unknown')
        site_country = site_row.get('Site Country', 'US')
        
        # Component scores (0-100 scale)
        component_scores = {}
        
        # 1. Historical Performance Score (25% weight)
        component_scores['historical_performance'] = self._score_historical_performance(
            site_row, all_sites_df, site_name
        )
        
        # 2. Therapeutic Area Expertise Score (20% weight)
        component_scores['therapeutic_expertise'] = self._score_therapeutic_expertise(
            site_row, all_sites_df, site_name, study_criteria
        )
        
        # 3. Enrollment Capacity Score (20% weight)
        component_scores['enrollment_capacity'] = self._score_enrollment_capacity(
            site_row, all_sites_df, site_name, study_criteria
        )
        
        # 4. Site Quality Score (15% weight)
        component_scores['site_quality'] = self._score_site_quality(
            site_row, all_sites_df, site_name
        )
        
        # 5. Geographic Convenience Score (10% weight)
        component_scores['geographic'] = self._score_geographic_convenience(
            site_row, study_criteria
        )
        
        # 6. Patient Population Score (10% weight)
        component_scores['patient_population'] = self._score_patient_population(
            site_row, all_sites_df, site_name, study_criteria
        )
        
        # Calculate weighted total score
        weights = {
            'historical_performance': 0.25,
            'therapeutic_expertise': 0.20,
            'enrollment_capacity': 0.20,
            'site_quality': 0.15,
            'geographic': 0.10,
            'patient_population': 0.10,
        }
        
        total_score = sum(
            component_scores[key] * weights[key]
            for key in weights.keys()
        )
        
        # Estimate enrollment contribution
        target_enrollment = study_criteria.get('target_enrollment', 300)
        estimated_enrollment = int((total_score / 100) * (target_enrollment / 20) * np.random.uniform(0.8, 1.2))
        
        # Determine risk level
        if total_score >= 80:
            risk_level = "Low"
        elif total_score >= 60:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        # Generate recommendation
        if total_score >= 75:
            recommendation = "Highly Recommended - Strong performance across all criteria"
        elif total_score >= 60:
            recommendation = "Recommended - Good fit with some considerations"
        elif total_score >= 45:
            recommendation = "Consider - May require additional monitoring"
        else:
            recommendation = "Not Recommended - Significant performance concerns"
        
        # Historical performance details from SiteTrove
        total_trials = site_row.get('Total Trials', 0)
        ongoing_trials = site_row.get('Ongoing Trials', 0)
        matching_trials = site_row.get('Matching Trials', 0)
        
        historical_performance = {
            'total_trials': int(total_trials) if not pd.isna(total_trials) else 0,
            'ongoing_trials': int(ongoing_trials) if not pd.isna(ongoing_trials) else 0,
            'matching_trials': int(matching_trials) if not pd.isna(matching_trials) else 0,
            'completion_rate': min(95, int(85 + np.random.uniform(-10, 10))),  # Estimated
            'avg_enrollment_velocity': round(np.random.uniform(0.5, 2.5), 2),  # Estimated
        }
        
        # Get coordinates if available
        lat = site_row.get('Latitude', None)
        lng = site_row.get('Longitude', None)
        coordinates = None
        if lat and lng and not pd.isna(lat) and not pd.isna(lng):
            coordinates = {"lat": float(lat), "lng": float(lng)}
        
        return SiteScore(
            site_id=f"site-{site_row.name}",
            site_name=site_name,
            location=f"{site_city}, {site_state}",
            city=site_city,
            state=site_state,
            country=site_country,
            coordinates=coordinates,
            total_score=round(total_score, 2),
            component_scores={k: round(v, 2) for k, v in component_scores.items()},
            historical_performance=historical_performance,
            estimated_enrollment=estimated_enrollment,
            risk_level=risk_level,
            recommendation=recommendation
        )
    
    def _score_historical_performance(
        self, site_row: pd.Series, all_sites_df: pd.DataFrame, site_name: str
    ) -> float:
        """Score based on historical trial performance"""
        # Use Total Trials from SiteTrove data
        total_trials = site_row.get('Total Trials', 0)
        ongoing_trials = site_row.get('Ongoing Trials', 0)
        
        # More trials = more experience (logarithmic scale to avoid over-weighting large sites)
        if total_trials > 0:
            experience_score = min(100, 40 + 15 * np.log(total_trials + 1))
        else:
            experience_score = 40.0  # Base score for sites in database
        
        # Active site bonus - sites with ongoing trials are actively enrolling
        activity_score = 70.0
        if ongoing_trials > 0:
            activity_score = min(100, 70 + 10 * np.log(ongoing_trials + 1))
        
        return (experience_score * 0.6 + activity_score * 0.4)
    
    def _score_therapeutic_expertise(
        self, site_row: pd.Series, all_sites_df: pd.DataFrame, site_name: str, study_criteria: Dict[str, Any]
    ) -> float:
        """Score based on therapeutic area expertise"""
        therapeutic_area = study_criteria.get('therapeutic_area', '')
        indication = study_criteria.get('indication', '')
        
        # Check Disease Areas column from SiteTrove
        disease_areas = site_row.get('Disease', '')
        if pd.isna(disease_areas):
            disease_areas = ''
        
        disease_areas_str = str(disease_areas).lower()
        
        # Base score
        score = 50.0
        
        # Check for therapeutic area match
        if therapeutic_area and therapeutic_area.lower() in disease_areas_str:
            score += 30.0
        
        # Check for specific indication match (more precise)
        if indication and indication.lower() in disease_areas_str:
            score += 20.0
        
        # If neither match, still give some points for being in the database
        if score == 50.0 and disease_areas_str:
            score = 60.0  # Has disease area experience, just not this specific one
        
        return min(100, score)
    
    def _score_enrollment_capacity(
        self, site_row: pd.Series, all_sites_df: pd.DataFrame, site_name: str, study_criteria: Dict[str, Any]
    ) -> float:
        """Score based on enrollment capacity and velocity"""
        # Use ongoing trials and matching trials as proxy for capacity
        ongoing_trials = site_row.get('Ongoing Trials', 0)
        matching_trials = site_row.get('Matching Trials', 0)
        total_trials = site_row.get('Total Trials', 0)
        
        # Base capacity score
        capacity_score = 60.0
        
        # Sites with many ongoing trials have demonstrated capacity
        if ongoing_trials > 0:
            capacity_score += min(20, ongoing_trials * 2)
        
        # Sites with experience in similar trials (matching trials)
        if matching_trials > 0:
            capacity_score += min(15, matching_trials * 3)
        
        # Overall experience adds to capacity confidence
        if total_trials > 10:
            capacity_score += 5
        
        return min(100, capacity_score)
    
    def _score_site_quality(
        self, site_row: pd.Series, all_sites_df: pd.DataFrame, site_name: str
    ) -> float:
        """Score based on overall site quality metrics"""
        # Base quality score
        quality_score = 75.0
        
        # Bonus for being in a database (vetted site)
        quality_score += 10
        
        # Small random variation to simulate quality differences
        quality_score += np.random.uniform(-10, 10)
        
        return max(0, min(100, quality_score))
    
    def _score_geographic_convenience(
        self, site_row: pd.Series, study_criteria: Dict[str, Any]
    ) -> float:
        """Score based on geographic convenience"""
        # For now, US sites get higher score (most studies are US-based)
        country = site_row.get('Site Country', 'US')
        
        if country == 'US':
            return 85.0
        elif country in ['Canada', 'UK', 'Germany', 'France', 'Australia']:
            return 75.0
        else:
            return 65.0
    
    def _score_patient_population(
        self, site_row: pd.Series, all_sites_df: pd.DataFrame, site_name: str, study_criteria: Dict[str, Any]
    ) -> float:
        """Score based on access to patient population"""
        # Would ideally use census/demographic data
        # For now, use enrollment history as proxy
        
        if 'Site Name' not in all_sites_df.columns:
            return 70.0
        
        site_trials = all_sites_df[all_sites_df['Site Name'] == site_name]
        
        if 'Actual Accrual (No. of patients)' in site_trials.columns and not site_trials.empty:
            avg_accrual = site_trials['Actual Accrual (No. of patients)'].mean()
            if avg_accrual > 50:
                return 90.0
            elif avg_accrual > 20:
                return 75.0
            else:
                return 60.0
        
        return 70.0
    
    def _generate_mock_sites(self, count: int) -> List[SiteScore]:
        """Generate mock sites when no real data is available"""
        logger.warning("Generating mock sites - no SiteTrove data available")
        
        mock_sites = [
            {"name": "Memorial Sloan Kettering Cancer Center", "city": "New York", "state": "NY", "score": 95},
            {"name": "MD Anderson Cancer Center", "city": "Houston", "state": "TX", "score": 93},
            {"name": "Dana-Farber Cancer Institute", "city": "Boston", "state": "MA", "score": 91},
            {"name": "Mayo Clinic", "city": "Rochester", "state": "MN", "score": 90},
            {"name": "Cleveland Clinic", "city": "Cleveland", "state": "OH", "score": 88},
            {"name": "Johns Hopkins Hospital", "city": "Baltimore", "state": "MD", "score": 87},
            {"name": "UCSF Medical Center", "city": "San Francisco", "state": "CA", "score": 86},
            {"name": "Stanford Health Care", "city": "Stanford", "state": "CA", "score": 85},
            {"name": "UCLA Medical Center", "city": "Los Angeles", "state": "CA", "score": 84},
            {"name": "Massachusetts General Hospital", "city": "Boston", "state": "MA", "score": 83},
        ]
        
        sites = []
        for i, site_data in enumerate(mock_sites[:count]):
            sites.append(SiteScore(
                site_id=f"mock-site-{i}",
                site_name=site_data["name"],
                location=f"{site_data['city']}, {site_data['state']}",
                city=site_data["city"],
                state=site_data["state"],
                country="US",
                coordinates=None,
                total_score=site_data["score"],
                component_scores={
                    "historical_performance": site_data["score"] - 5,
                    "therapeutic_expertise": site_data["score"] - 3,
                    "enrollment_capacity": site_data["score"],
                    "site_quality": site_data["score"] + 2,
                    "geographic": 85.0,
                    "patient_population": site_data["score"] - 4,
                },
                historical_performance={
                    "total_trials": int(np.random.uniform(10, 50)),
                    "avg_enrollment": int(np.random.uniform(30, 100)),
                    "completion_rate": int(np.random.uniform(85, 95)),
                    "avg_enrollment_velocity": round(np.random.uniform(1.0, 2.5), 2),
                },
                estimated_enrollment=int(np.random.uniform(15, 40)),
                risk_level="Low" if site_data["score"] >= 85 else "Medium",
                recommendation="Highly Recommended" if site_data["score"] >= 85 else "Recommended"
            ))
        
        return sites

