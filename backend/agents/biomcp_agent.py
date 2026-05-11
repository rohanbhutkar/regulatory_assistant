"""
BioOntology Agent - NCBO BioPortal API Integration
"""
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from utils.logger import log_api_call, log_error
from utils.cache import cache_manager
from utils.rate_limiter import rate_limiter
from models.schemas import BioMCPResult

class BioOntologyAgent:
    def __init__(self):
        self.base_url = "https://data.bioontology.org"
        self.api_key = "99912f5a-b6e0-4436-9b36-45f0d3ad9a2f"
        self.timeout = httpx.Timeout(15.0)
        self.headers = {
            "Authorization": f"apikey token={self.api_key}",
            "Accept": "application/json"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request with retry logic"""
        await rate_limiter.acquire("bioontology")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            start_time = asyncio.get_event_loop().time()
            
            try:
                url = f"{self.base_url}{endpoint}"
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                
                end_time = asyncio.get_event_loop().time()
                log_api_call("bioontology", endpoint, response.status_code, end_time - start_time)
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                log_error(e, f"BioOntology API error: {e.response.status_code}")
                raise
            except Exception as e:
                log_error(e, "BioOntology API request")
                raise
    
    async def search_terms(self, query: str, max_results: int = 50) -> List[BioMCPResult]:
        """Search for terms across all ontologies"""
        print(f"🔍 BioMCPAgent.search_terms called with query: '{query}', max_results: {max_results}")
        
        cache_key = cache_manager.get_api_cache_key("bioontology", "search", {"query": query, "max_results": max_results})
        
        # Check cache first
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            print(f"📊 Using cached BioOntology result for query: {query}")
            return cached_result
        
        params = {
            "q": query,
            "pagesize": min(max_results, 100),
            "include": "prefLabel,synonym,definition,notation,cui,semanticType",
            "format": "json"
        }
        
        print(f"📊 Making BioOntology API request with params: {params}")
        
        try:
            data = await self._make_request("/search", params)
            print(f"📊 BioOntology API response received, collection size: {len(data.get('collection', []))}")
            
            results = []
            for item in data.get("collection", [])[:max_results]:
                try:
                    # Extract ontology info
                    links = item.get("links", {})
                    ontology_link = links.get("ontology", "")
                    ontology_acronym = ontology_link.split("/")[-1] if ontology_link else "Unknown"
                    
                    # Extract semantic types
                    semantic_types = item.get("semanticType", [])
                    semantic_type_text = ", ".join(semantic_types) if semantic_types else ""
                    
                    # Extract synonyms
                    synonyms = item.get("synonym", [])
                    synonym_text = "; ".join(synonyms) if synonyms else ""
                    
                    # Extract CUIs
                    cuis = item.get("cui", [])
                    cui_text = ", ".join(cuis) if cuis else ""
                    
                    result = BioMCPResult(
                        id=item.get("@id", ""),
                        title=item.get("prefLabel", ""),
                        description=item.get("definition", [""])[0] if item.get("definition") else "",
                        type=f"Ontology Class ({ontology_acronym})",
                        url=item.get("@id", ""),
                        metadata={
                            "ontology": ontology_acronym,
                            "synonyms": synonym_text,
                            "semantic_types": semantic_type_text,
                            "cuis": cui_text,
                            "notation": item.get("notation", ""),
                            "obsolete": item.get("obsolete", False)
                        },
                        relevance_score=0.8
                    )
                    results.append(result)
                except Exception as e:
                    log_error(e, f"Processing BioOntology result {item.get('@id', 'unknown')}")
                    continue
            
            print(f"📊 Successfully processed {len(results)} BioOntology results")
            
            # Cache results
            cache_manager.set(cache_key, results)
            return results
            
        except Exception as e:
            log_error(e, "BioOntology search")
            print(f"❌ BioOntology search failed: {e}")
            return self._get_mock_results(query, max_results)
    
    async def search_by_ontology(self, query: str, ontology: str, max_results: int = 50) -> List[BioMCPResult]:
        """Search for terms in a specific ontology"""
        cache_key = cache_manager.get_api_cache_key("bioontology", "ontology_search", {
            "query": query, "ontology": ontology, "max_results": max_results
        })
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "q": query,
            "ontologies": ontology,
            "pagesize": min(max_results, 100),
            "include": "prefLabel,synonym,definition,notation,cui,semanticType",
            "format": "json"
        }
        
        try:
            data = await self._make_request("/search", params)
            results = await self._parse_search_results(data, max_results)
            cache_manager.set(cache_key, results)
            return results
        except Exception as e:
            log_error(e, f"BioOntology ontology search for {ontology}")
            return []
    
    async def annotate_text(self, text: str, ontologies: List[str] = None) -> List[BioMCPResult]:
        """Annotate text to find relevant ontology classes"""
        cache_key = cache_manager.get_api_cache_key("bioontology", "annotate", {"text": text[:100], "ontologies": ontologies})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "text": text,
            "include": "prefLabel,synonym,definition,notation,cui,semanticType",
            "format": "json"
        }
        
        if ontologies:
            params["ontologies"] = ",".join(ontologies)
        
        try:
            data = await self._make_request("/annotator", params)
            
            results = []
            for annotation in data.get("annotations", []):
                try:
                    # Extract annotation details
                    annotation_details = annotation.get("annotations", [])
                    if annotation_details:
                        detail = annotation_details[0]
                        class_info = detail.get("class", {})
                        
                        # Extract ontology info
                        links = class_info.get("links", {})
                        ontology_link = links.get("ontology", "")
                        ontology_acronym = ontology_link.split("/")[-1] if ontology_link else "Unknown"
                        
                        # Extract semantic types
                        semantic_types = class_info.get("semanticType", [])
                        semantic_type_text = ", ".join(semantic_types) if semantic_types else ""
                        
                        # Extract synonyms
                        synonyms = class_info.get("synonym", [])
                        synonym_text = "; ".join(synonyms) if synonyms else ""
                        
                        # Extract CUIs
                        cuis = class_info.get("cui", [])
                        cui_text = ", ".join(cuis) if cuis else ""
                        
                        result = BioMCPResult(
                            id=class_info.get("@id", ""),
                            title=class_info.get("prefLabel", ""),
                            description=class_info.get("definition", [""])[0] if class_info.get("definition") else "",
                            type=f"Annotated Class ({ontology_acronym})",
                            url=class_info.get("@id", ""),
                            metadata={
                                "ontology": ontology_acronym,
                                "synonyms": synonym_text,
                                "semantic_types": semantic_type_text,
                                "cuis": cui_text,
                                "notation": class_info.get("notation", ""),
                                "obsolete": class_info.get("obsolete", False),
                                "annotation_score": detail.get("score", 0),
                                "annotated_text": detail.get("text", "")
                            },
                            relevance_score=detail.get("score", 0.5)
                        )
                        results.append(result)
                except Exception as e:
                    log_error(e, f"Processing annotation {annotation.get('@id', 'unknown')}")
                    continue
            
            # Cache results
            cache_manager.set(cache_key, results)
            return results
            
        except Exception as e:
            log_error(e, "BioOntology annotation")
            return []
    
    async def get_ontology_info(self, ontology_acronym: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific ontology"""
        cache_key = cache_manager.get_api_cache_key("bioontology", "ontology_info", {"acronym": ontology_acronym})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            data = await self._make_request(f"/ontologies/{ontology_acronym}")
            
            # Cache result
            cache_manager.set(cache_key, data)
            return data
            
        except Exception as e:
            log_error(e, f"Get ontology info for {ontology_acronym}")
            return None
    
    async def get_class_details(self, ontology_acronym: str, class_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific class"""
        cache_key = cache_manager.get_api_cache_key("bioontology", "class_details", {
            "ontology": ontology_acronym, "class_id": class_id
        })
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # URL encode the class ID
            import urllib.parse
            encoded_class_id = urllib.parse.quote(class_id, safe='')
            
            data = await self._make_request(f"/ontologies/{ontology_acronym}/classes/{encoded_class_id}")
            
            # Cache result
            cache_manager.set(cache_key, data)
            return data
            
        except Exception as e:
            log_error(e, f"Get class details for {ontology_acronym}:{class_id}")
            return None
    
    async def recommend_ontologies(self, text: str) -> List[Dict[str, Any]]:
        """Get ontology recommendations for given text"""
        cache_key = cache_manager.get_api_cache_key("bioontology", "recommend", {"text": text[:100]})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "input": text,
            "input_type": "1",  # Text input
            "output_type": "1",  # Individual ontologies
            "format": "json"
        }
        
        try:
            data = await self._make_request("/recommender", params)
            
            recommendations = []
            for rec in data.get("recommendations", []):
                try:
                    ontology_info = rec.get("ontologies", [{}])[0]
                    recommendation = {
                        "ontology_acronym": ontology_info.get("acronym", ""),
                        "ontology_name": ontology_info.get("name", ""),
                        "score": rec.get("score", 0),
                        "coverage": rec.get("coverage", 0),
                        "acceptance": rec.get("acceptance", 0),
                        "detail": rec.get("detail", 0),
                        "specialization": rec.get("specialization", 0)
                    }
                    recommendations.append(recommendation)
                except Exception as e:
                    log_error(e, "Processing ontology recommendation")
                    continue
            
            # Cache results
            cache_manager.set(cache_key, recommendations)
            return recommendations
            
        except Exception as e:
            log_error(e, "BioOntology recommendation")
            return []
    
    async def _parse_search_results(self, data: Dict[str, Any], max_results: int) -> List[BioMCPResult]:
        """Parse search results from BioOntology API"""
        results = []
        for item in data.get("collection", [])[:max_results]:
            try:
                # Extract ontology info
                links = item.get("links", {})
                ontology_link = links.get("ontology", "")
                ontology_acronym = ontology_link.split("/")[-1] if ontology_link else "Unknown"
                
                # Extract semantic types
                semantic_types = item.get("semanticType", [])
                semantic_type_text = ", ".join(semantic_types) if semantic_types else ""
                
                # Extract synonyms
                synonyms = item.get("synonym", [])
                synonym_text = "; ".join(synonyms) if synonyms else ""
                
                # Extract CUIs
                cuis = item.get("cui", [])
                cui_text = ", ".join(cuis) if cuis else ""
                
                result = BioMCPResult(
                    id=item.get("@id", ""),
                    title=item.get("prefLabel", ""),
                    description=item.get("definition", [""])[0] if item.get("definition") else "",
                    type=f"Ontology Class ({ontology_acronym})",
                    url=item.get("@id", ""),
                    metadata={
                        "ontology": ontology_acronym,
                        "synonyms": synonym_text,
                        "semantic_types": semantic_type_text,
                        "cuis": cui_text,
                        "notation": item.get("notation", ""),
                        "obsolete": item.get("obsolete", False)
                    },
                    relevance_score=0.8
                )
                results.append(result)
            except Exception as e:
                log_error(e, f"Processing BioOntology result {item.get('@id', 'unknown')}")
                continue
        
        return results
    
    def _get_mock_results(self, query: str, max_results: int) -> List[BioMCPResult]:
        """Generate mock results for demonstration"""
        mock_results = []
        for i in range(min(max_results, 5)):
            result = BioMCPResult(
                id=f"http://example.org/ontology/class_{i+1}",
                title=f"Mock Ontology Class {i+1} for {query}",
                description=f"This is a mock ontology class representing {query}",
                type="Mock Ontology Class",
                url=f"http://example.org/ontology/class_{i+1}",
                metadata={
                    "ontology": "MOCK",
                    "synonyms": f"Mock synonym {i+1}",
                    "semantic_types": "Mock semantic type",
                    "cuis": f"C{i+1:06d}",
                    "notation": f"MOCK{i+1:03d}",
                    "obsolete": False
                },
                relevance_score=0.7 - (i * 0.1)
            )
            mock_results.append(result)
        return mock_results
    
    async def search_data(self, query: str, max_results: int = 50) -> List[BioMCPResult]:
        """Main search method that delegates to appropriate search function"""
        print(f"🔍 BioMCPAgent.search_data called with query: '{query}', max_results: {max_results}")
        
        try:
            # Use the general search method
            results = await self.search_terms(query, max_results)
    
            return results
        except Exception as e:
            print(f"❌ BioMCP search failed: {e}")
            return self._get_mock_results(query, max_results)

# Global BioOntology agent instance
biomcp_agent = BioOntologyAgent() 