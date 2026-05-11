"""
PubMed Central API Agent
"""
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from utils.logger import log_api_call, log_error
from utils.cache import cache_manager
from utils.rate_limiter import rate_limiter
from models.schemas import PublicationResult
from datetime import datetime, timedelta

class PubMedAgent:
    def __init__(self):
        self.rest_url = settings.PUBMED_BASE_URL
        self.timeout = httpx.Timeout(15.0)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_rest_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make REST request with retry logic"""
        await rate_limiter.acquire("pubmed")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            start_time = asyncio.get_event_loop().time()
            
            try:
                response = await client.get(f"{self.rest_url}{endpoint}", params=params)
                response.raise_for_status()
                
                end_time = asyncio.get_event_loop().time()
                log_api_call("pubmed_rest", endpoint, response.status_code, end_time - start_time)
                
                # Handle different response types
                if endpoint == "/efetch.fcgi" and params.get("retmode") == "xml":
                    # Return XML as text for efetch
                    return response.text
                else:
                    # Return JSON for other endpoints
                    return response.json()
                
            except httpx.HTTPStatusError as e:
                log_error(e, f"PubMed REST error: {e.response.status_code}")
                raise
            except Exception as e:
                log_error(e, "PubMed REST request")
                raise
    
    async def search_publications(self, query: str, max_results: int = 50) -> List[PublicationResult]:
        """Search PubMed for publications"""
        print(f"🔍 PubMedAgent.search_publications called with query: '{query}', max_results: {max_results}")
        
        try:
            # Extract key terms from complex queries for better PubMed search
            search_terms = self._extract_search_terms(query)
    
            
            # Search PubMed with transformed terms
            results = await self._search_pubmed(search_terms, max_results)
            
            if not results:
                print("⚠️ Primary search returned no results, trying alternative search terms")
                # Try alternative search strategy
                alt_terms = self._get_alternative_search_terms(query)
                if alt_terms != search_terms:
                    print(f"🔄 Trying alternative terms: '{alt_terms}'")
                    results = await self._search_pubmed(alt_terms, max_results)
            
            if not results:
                print("❌ PubMed search returned no results after trying alternatives")
                return []
            
            print(f"✅ PubMed search successful: {len(results)} results found")
            return results
            
        except Exception as e:
            print(f"❌ PubMed search error: {e}")
            log_error(e, "PubMed search")
            return []
    
    def _extract_search_terms(self, query: str) -> str:
        """Transform complex queries into PubMed-compatible search terms"""
        query_lower = query.lower()
        
        # Handle drug comparison queries
        if "difference between" in query_lower or "compare" in query_lower:
            if "nivolumab" in query_lower and "pembrolizumab" in query_lower:
                return "nivolumab AND pembrolizumab"
            elif "nivolumab" in query_lower:
                return "nivolumab"
            elif "pembrolizumab" in query_lower:
                return "pembrolizumab"
        
        # Handle specific drug queries
        if "nivolumab" in query_lower:
            return "nivolumab"
        if "pembrolizumab" in query_lower:
            return "pembrolizumab"
        
        # Handle disease-specific queries
        if "diabetes" in query_lower:
            if "treatment" in query_lower or "therapy" in query_lower:
                return "diabetes AND treatment"
            return "diabetes"
        
        if "cancer" in query_lower or "tumor" in query_lower:
            if "treatment" in query_lower or "therapy" in query_lower:
                return "cancer AND treatment"
            return "cancer"
        
        if "melanoma" in query_lower:
            return "melanoma"
        
        if "lung cancer" in query_lower:
            return "lung cancer"
        
        if "breast cancer" in query_lower:
            return "breast cancer"
        
        # Handle immunotherapy queries
        if "immunotherapy" in query_lower:
            return "immunotherapy"
        
        if "pd-1" in query_lower or "pd1" in query_lower:
            return "PD-1"
        
        if "checkpoint inhibitor" in query_lower:
            return "checkpoint inhibitor"
        
        # Handle clinical trial queries
        if "clinical trial" in query_lower:
            return "clinical trial"
        
        # Extract key medical terms
        medical_terms = [
            "diabetes", "cancer", "melanoma", "lung cancer", "breast cancer", 
            "treatment", "therapy", "clinical trial", "drug", "medication",
            "nivolumab", "pembrolizumab", "immunotherapy", "PD-1", "checkpoint inhibitor"
        ]
        
        found_terms = []
        for term in medical_terms:
            if term in query_lower:
                found_terms.append(term)
        
        if found_terms:
            # Limit to 2-3 terms to avoid overly complex queries
            return " AND ".join(found_terms[:2])
        
        # Fallback: extract meaningful words
        words = query.split()
        meaningful_words = [word for word in words if len(word) > 3 and word.lower() not in ['what', 'when', 'where', 'which', 'about', 'between', 'latest', 'recent']]
        
        if meaningful_words:
            return " ".join(meaningful_words[:3])
        
        # Last resort: use first few words
        return " ".join(words[:3])
    
    def _get_alternative_search_terms(self, query: str) -> str:
        """Get alternative search terms if primary search fails"""
        query_lower = query.lower()
        
        # For drug comparisons, try broader immunotherapy terms
        if "nivolumab" in query_lower and "pembrolizumab" in query_lower:
            return "PD-1 inhibitor"
        
        if "nivolumab" in query_lower or "pembrolizumab" in query_lower:
            return "immunotherapy"
        
        # For disease queries, try broader terms
        if "diabetes" in query_lower:
            return "diabetes mellitus"
        
        if "cancer" in query_lower:
            return "neoplasms"
        
        if "melanoma" in query_lower:
            return "skin cancer"
        
        # For treatment queries, try clinical trial
        if "treatment" in query_lower or "therapy" in query_lower:
            return "clinical trial"
        
        # Default fallback
        return "clinical research"
    
    async def _search_pubmed(self, query: str, max_results: int) -> List[PublicationResult]:
        """Search using PubMed E-utilities API"""
        # Clean and validate the query
        query = query.strip()
        if not query:
            print("❌ Empty query provided")
            return []
        
        print(f"🔍 Searching PubMed with term: '{query}'")
        
        # Step 1: Search for PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        
        try:
            search_response = await self._make_rest_request("/esearch.fcgi", search_params)
            print(f"📊 Search response keys: {list(search_response.keys())}")
            
            # Check for errors in the response
            if "esearchresult" in search_response:
                esearch_result = search_response["esearchresult"]
                
                # Check for API errors
                if "ERROR" in esearch_result:
                    error_msg = esearch_result["ERROR"]
                    print(f"❌ PubMed search error: {error_msg}")
                    return []
                
                # Check for warning messages
                if "WARNING" in esearch_result:
                    warning_msg = esearch_result["WARNING"]
                    print(f"⚠️ PubMed search warning: {warning_msg}")
                
                # Get the count of results
                count = esearch_result.get("count", "0")
                print(f"📊 PubMed found {count} total results")
                
                if "idlist" in esearch_result:
                    pmids = esearch_result["idlist"]
                    print(f"📋 Retrieved {len(pmids)} PMIDs: {pmids[:5]}...")
                    
                    if pmids:
                        # Step 2: Get details for the found PMIDs
                        fetch_params = {
                            "db": "pubmed",
                            "id": ",".join(pmids[:max_results]),
                            "retmode": "xml",
                            "rettype": "abstract"
                        }
                        
                        print(f"🔍 Fetching details for {len(pmids[:max_results])} PMIDs...")
                        fetch_response = await self._make_rest_request("/efetch.fcgi", fetch_params)
                        
                        # Parse XML response to extract abstracts
                        results = []
                        try:
                            import xml.etree.ElementTree as ET
                            
                            # Handle both string and dict responses
                            if isinstance(fetch_response, str):
                                xml_content = fetch_response
                            else:
                                # If it's a dict, try to extract XML content
                                xml_content = str(fetch_response)
                            
                            # Parse XML
                            root = ET.fromstring(xml_content)
                            
                            # Find all PubmedArticle elements
                            for article in root.findall('.//PubmedArticle'):
                                try:
                                    # Extract PMID
                                    pmid_elem = article.find('.//PMID')
                                    pmid = pmid_elem.text if pmid_elem is not None else ""
                                    
                                    # Extract title
                                    title_elem = article.find('.//ArticleTitle')
                                    title = title_elem.text if title_elem is not None else ""
                                    
                                    # Extract abstract
                                    abstract_elem = article.find('.//AbstractText')
                                    abstract = abstract_elem.text if abstract_elem is not None and abstract_elem.text is not None else ""
                                    # Ensure abstract is never None
                                    if abstract is None:
                                        abstract = ""
                                    
                                    # Extract authors
                                    authors = []
                                    author_list = article.find('.//AuthorList')
                                    if author_list is not None:
                                        for author in author_list.findall('.//Author'):
                                            last_name_elem = author.find('.//LastName')
                                            first_name_elem = author.find('.//ForeName')
                                            if last_name_elem is not None and first_name_elem is not None:
                                                authors.append(f"{first_name_elem.text} {last_name_elem.text}")
                                            elif last_name_elem is not None:
                                                authors.append(last_name_elem.text)
                                    
                                    # Extract journal
                                    journal_elem = article.find('.//Journal/Title')
                                    journal = journal_elem.text if journal_elem is not None else ""
                                    
                                    # Extract publication date
                                    pub_date_elem = article.find('.//PubDate')
                                    pub_date = ""
                                    if pub_date_elem is not None:
                                        year_elem = pub_date_elem.find('.//Year')
                                        month_elem = pub_date_elem.find('.//Month')
                                        if year_elem is not None:
                                            pub_date = year_elem.text
                                            if month_elem is not None:
                                                pub_date = f"{month_elem.text} {pub_date}"
                                    
                                    # Extract DOI
                                    doi_elem = article.find('.//ELocationID[@EIdType="doi"]')
                                    doi = doi_elem.text if doi_elem is not None else ""
                                    
                                    result = PublicationResult(
                                        pmid=pmid,
                                        pmcid="",  # PMC ID not available in this format
                                        title=title,
                                        authors=authors,
                                        journal=journal,
                                        publication_date=pub_date,
                                        abstract=abstract,
                                        keywords=[],  # Keywords not available in this format
                                        doi=doi,
                                        full_text=None,
                                        relevance_score=0.8
                                    )
                                    results.append(result)
                                    abstract_len = len(abstract) if abstract else 0
                                    print(f"📄 Processed PMID {pmid}: {title[:50] if title else 'No title'}... (Abstract: {abstract_len} chars)")
                                    
                                except Exception as e:
                                    print(f"⚠️ Error processing article: {e}")
                                    continue
                            
                            print(f"✅ Successfully processed {len(results)} articles with abstracts")
                            return results
                            
                        except Exception as e:
                            print(f"❌ Error parsing XML response: {e}")
                            # Fallback to summary endpoint
                            print("🔄 Falling back to summary endpoint...")
                            return await self._get_summary_results(pmids[:max_results])
                    else:
                        print("❌ No PMIDs found in search response")
                else:
                    print("❌ No idlist found in search response")
            else:
                print(f"❌ Unexpected search response structure: {search_response}")
            
            return []
            
        except Exception as e:
            print(f"❌ PubMed E-utilities search error: {e}")
            log_error(e, "PubMed E-utilities search")
            return []
    
    async def _get_summary_results(self, pmids: List[str]) -> List[PublicationResult]:
        """Fallback method to get summary results when XML parsing fails"""
        try:
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json"
            }
            
            fetch_response = await self._make_rest_request("/esummary.fcgi", fetch_params)
            
            results = []
            if "esummaryresult" in fetch_response:
                summary_data = fetch_response["esummaryresult"]
                
                for pmid, article in summary_data.items():
                    if pmid != "uids":
                        try:
                            title = article.get("title", "")
                            
                            # Create authors list
                            authors = []
                            if "authors" in article:
                                for author in article["authors"]:
                                    if isinstance(author, dict) and "name" in author:
                                        authors.append(author["name"])
                                    elif isinstance(author, str):
                                        authors.append(author)
                            
                            result = PublicationResult(
                                pmid=pmid,
                                pmcid=article.get("pmcid", ""),
                                title=title,
                                authors=authors,
                                journal=article.get("fulljournalname", ""),
                                publication_date=article.get("pubdate", ""),
                                abstract=article.get("abstract", ""),  # May be empty in summary
                                keywords=[],
                                doi=article.get("elocationid", ""),
                                full_text=None,
                                relevance_score=0.8
                            )
                            results.append(result)
                        except Exception as e:
                            print(f"⚠️ Error processing summary for PMID {pmid}: {e}")
                            continue
            
            return results
            
        except Exception as e:
            print(f"❌ Error getting summary results: {e}")
            return []
    
    def _get_mock_results(self, query: str, max_results: int) -> List[PublicationResult]:
        """Generate mock results for demonstration"""
        mock_results = []
        for i in range(min(max_results, 5)):
            result = PublicationResult(
                pmid=f"PMID{i+1:06d}",
                pmcid=f"PMC{i+1:06d}",
                title=f"Research Publication {i+1} on {query}",
                authors=[f"Author {i+1}", f"Researcher {i+1}"],
                journal="Journal of Clinical Research",
                publication_date="2024-01-01",
                abstract=f"This is a research publication investigating {query}",
                keywords=["clinical research", "medical study"],
                doi=f"10.1000/example.{i+1}",
                full_text=None,
                relevance_score=0.8 - (i * 0.1)
            )
            mock_results.append(result)
        return mock_results
    
    async def search_by_keywords(self, keywords: List[str], max_results: int = 50) -> List[PublicationResult]:
        """Search publications by keywords"""
        query = " AND ".join(keywords)
        return await self.search_publications(query, max_results)
    
    async def get_recent_publications(self, days: int = 30, max_results: int = 50) -> List[PublicationResult]:
        """Get recent publications from the last N days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[dp]"
        return await self.search_publications(query, max_results)

# Global instance
pubmed_agent = PubMedAgent() 