"""
WebSearchRetrieverAgent - Complete extraction with ALL functionality preserved
"""

import asyncio
import time
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import aiohttp
import re

from .base_agent import LLMAgent
from ..enhanced_research_system import (
    SearchResult, SubQuestion, RetrievalFindings, ResourceManager, 
    ProgressTracker, with_search_timeout_and_retries, AdaptiveSourceFilter,
    metrics_collector, FIRECRAWL_AVAILABLE
)
from ..config import Settings
from ..utils import CacheManager, SecurityManager
from ..enhanced_research_system import ModelManager

class WebSearchRetrieverAgent(LLMAgent):
    """Enhanced web search agent with Brave API integration"""
    
    def __init__(self, settings: Settings, cache_manager: CacheManager, 
                 security_manager: SecurityManager, quality_agent: 'QualityEvaluationAgent' = None,
                 model_manager: ModelManager = None):
        super().__init__("WebSearchRetrieverAgent", "Information Retrieval", settings, cache_manager, security_manager,
                        model_manager, "web_search")
        self.quality_agent = quality_agent
        self.source_filter = AdaptiveSourceFilter(settings, self.logger) if settings.enable_source_filtering else None
        
        # Initialize unified quality assessor
        from ..core.quality_assessor import UnifiedQualityAssessor
        self.quality_assessor = UnifiedQualityAssessor(settings)
        
        # Initialize search metrics
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_results': 0,
            'rate_limited_searches': 0
        }
    
    async def _detect_company_query(self, query: str, resource_manager: ResourceManager = None) -> Dict[str, Any]:
        """Enhanced company detection using our clean company_detection.py module"""
        # Import the clean company detector we created
        from company_detection import CompanyDetector
        
        detector = CompanyDetector()
        company_info = detector.detect_companies(query)
        
        # Convert to the format expected by this class
        return {
            'is_company_query': company_info.is_company_query,
            'detected_companies': company_info.companies,
            'company_context': company_info.query_type,
            'confidence': company_info.confidence,
            'reasoning': f"Detected via {len(company_info.indicators)} indicators: {', '.join(company_info.indicators[:3])}",
            'ai_powered': False  # Using our pattern-based detection
        }
    
    @with_search_timeout_and_retries()
    async def _brave_search(self, query: str, count: int = 10, 
                          resource_manager: ResourceManager = None) -> List[SearchResult]:
        """Enhanced Brave search with company website prioritization and URL relevance scoring"""
        try:
            # Check if this is a company query and enhance search accordingly
            company_info = await self._detect_company_query(query, resource_manager)
            
            # Create enhanced search queries for company research
            search_queries = await self._create_enhanced_search_queries_from_query(query, company_info, resource_manager)
            
            all_results = []
            
            # Execute multiple search queries for comprehensive coverage
            for search_query in search_queries[:3]:  # Limit to top 3 queries to avoid rate limits
                try:
                    response = await resource_manager.throttled_request(
                        "GET", 
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": self.settings.brave_api_key},
                        params={
                            "q": search_query,
                            "count": count,
                            "text_decorations": "false",
                            "search_lang": "en",
                            "country": "US",
                            "safesearch": "moderate",
                            "freshness": "py"  # Past year for recent information
                        }
                    )
                    
                    if response.status == 200:
                        data = await response.json()
                        web_results = data.get("web", {}).get("results", [])
                        
                        for result in web_results:
                            description = result.get("description", "")
                            # Use unified quality assessor for realistic quality scores
                            from ..core.quality_assessor import AssessmentRequest, AssessmentMode
                            
                            # Create a temporary SearchResult for quality assessment
                            temp_result = SearchResult(
                                url=result.get("url", ""),
                                title=result.get("title", ""),
                                snippet=description,
                                content=description,
                                relevance_score=0.0,
                                source_type="web"
                            )
                            
                            # Quick algorithmic assessment for individual results
                            quality_request = AssessmentRequest(
                                results=[temp_result],
                                sub_question=None,  # Will be handled gracefully by assessor
                                mode=AssessmentMode.ALGORITHMIC_FAST
                            )
                            
                            # Get quality metrics synchronously (since this is not an async context)
                            try:
                                if hasattr(self, 'quality_assessor'):
                                    # Use a simple approach for sync context
                                    quality_metrics = self.quality_assessor._algorithmic_fast_assessment(quality_request)
                                    content_quality = quality_metrics.content_quality
                                    authority_score = quality_metrics.authority_score
                                else:
                                    # Fallback to basic scoring
                                    content_quality = 0.5
                                    authority_score = 0.5
                            except Exception:
                                content_quality = 0.5
                                authority_score = 0.5
                            
                            search_result = SearchResult(
                                url=result.get("url", ""),
                                title=result.get("title", ""),
                                snippet=description,
                                content=description,  # For now, use same as snippet
                                relevance_score=0.0,  # Will be calculated later
                                source_type="web",
                                date_published=result.get("age", None),
                                authority_score=authority_score,
                                content_quality=content_quality,
                                language="en"
                            )
                            all_results.append(search_result)
                    
                    # Small delay between searches to respect rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Search query failed: {search_query}", error=str(e))
                    continue
            
            if not all_results:
                return []
            

            unique_results = []
            seen_urls = set()
            for result in all_results:
                if result.url not in seen_urls:
                    unique_results.append(result)
                    seen_urls.add(result.url)
            
            # Score results with enhanced company domain prioritization
            scored_results = self._score_relevance_with_company_priority(unique_results, query, company_info)
            
            # 🎯 ENHANCED: Prioritize company domain results for company queries
            if company_info.get('is_company_query', False):
                final_results = self._prioritize_company_domains(scored_results, company_info, count)
            else:
                # Sort by relevance score and return top results
                scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
                final_results = scored_results[:count]
            
            return final_results
            
        except Exception as e:
            self.logger.error("Brave search failed", error=str(e))
            return []
    
    async def _firecrawl_search(self, query: str, count: int = 10, 
                               resource_manager: ResourceManager = None) -> List[SearchResult]:
        """Enhanced Firecrawl search with parallel scraping"""
        self.logger.info("Starting Firecrawl search", query=query, count=count)
        
        try:
            # Check if Firecrawl is available and configured
            if not FIRECRAWL_AVAILABLE or not self.settings.firecrawl_api_key:
                if not FIRECRAWL_AVAILABLE:
                    self.logger.warning("Requests library not available, falling back to Brave search")
                else:
                    self.logger.warning("Firecrawl API key not configured, falling back to Brave search")
                return await self._brave_search(query, count, resource_manager)
            

            
            # Step 1: Search using Firecrawl
            search_url = "https://api.firecrawl.dev/v1/search"
            search_headers = {
                "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
                "Content-Type": "application/json"
            }
            
            search_data = {
                "query": query,
                "limit": min(count, getattr(self.settings, 'firecrawl_max_results', 10)),
                "lang": "en",
                "country": "us"
            }
            
            # Use asyncio to run the synchronous requests call
            loop = asyncio.get_event_loop()
            
            # Search for URLs
            search_response = await loop.run_in_executor(
                None, 
                lambda: requests.post(
                    search_url, 
                    headers=search_headers, 
                    json=search_data, 
                    timeout=get_search_timeout().total
                )
            )
            
            if search_response.status_code != 200:
                self.logger.error(f"Firecrawl search failed with status {search_response.status_code}: {search_response.text}")
                return await self._brave_search(query, count, resource_manager)
            
            search_results = search_response.json()
            
            if not search_results.get('data'):
                self.logger.warning("No search results from Firecrawl, falling back to Brave search")
                return await self._brave_search(query, count, resource_manager)
            
            # Step 2: Scrape content - parallel vs sequential based on configuration
            scrape_url = "https://api.firecrawl.dev/v1/scrape"
            seen_urls = set()
            
            # Filter unique URLs first
            unique_results = []
            for result in search_results['data'][:count]:
                url = result.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            # Check if parallel scraping is enabled
            if getattr(self.settings, 'firecrawl_parallel_scraping', True):
                results = await self._scrape_urls_parallel(unique_results, scrape_url, search_headers, loop)
            else:
                results = await self._scrape_urls_sequential(unique_results, scrape_url, search_headers, loop)
            
            self.logger.info("Firecrawl search completed", 
                           query=query, 
                           total_results=len(results),
                           valid_results=len([r for r in results if r.content]))
            
            return results
            
        except Exception as e:
            self.logger.error("Firecrawl search failed", query=query, error=str(e))
            return await self._brave_search(query, count, resource_manager)

    async def _scrape_urls_parallel(self, url_results, scrape_url, headers, loop):
        """Scrape URLs in parallel with controlled concurrency"""
        unique_results = []
        seen_urls = set()
        
        for result in url_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                unique_results.append(result)
                seen_urls.add(url)
        
        self.logger.info("Starting parallel scraping", url_count=len(unique_results))
        
        # Create scraping tasks for all URLs simultaneously
        tasks = []
        for i, result in enumerate(unique_results):
            task = self._scrape_single_url(result, scrape_url, headers, loop, i+1, len(unique_results))
            tasks.append(task)
        
        # Execute all scraping tasks in parallel
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = []
        for result in results:
            if isinstance(result, SearchResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                self.logger.warning(f"Parallel scraping error: {str(result)}")
        
        elapsed = time.time() - start_time
        self.logger.info("Parallel scraping completed", 
                       valid_results=len(valid_results),
                       total_attempts=len(unique_results),
                       elapsed_time=f"{elapsed:.1f}s")
        return valid_results
    
    async def _scrape_single_url(self, result_data, scrape_url, headers, loop, index, total):
        """Scrape a single URL with enhanced error handling"""
        url = result_data.get("url", "")
        title = result_data.get("title", "Untitled")
        
        self.logger.debug("Scraping URL", url=url, index=index, total=total)
        
        try:
            if not url:
                return None
            
            # Optimized scrape configuration using unified timeout manager
            from ..core.timeout_manager import get_scrape_timeout_seconds, get_scrape_timeout_ms
            timeout_seconds = get_scrape_timeout_seconds()
            scrape_data = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": getattr(self.settings, 'firecrawl_only_main_content', True),
                "timeout": get_scrape_timeout_ms(),
                "waitFor": 2000
            }
            
            # Single retry with unified timeout
            http_timeout = timeout_seconds
            description = result_data.get("description", "")
            
            try:
                scrape_response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(scrape_url, headers=headers, json=scrape_data, timeout=http_timeout)
                )
                
                # Process successful response
                full_content = description  # fallback
                if scrape_response.status_code == 200:
                    try:
                        scrape_result = scrape_response.json()
                        if scrape_result.get('data', {}).get('markdown'):
                            full_content = scrape_result['data']['markdown']
                            
                            # Apply content limit
                            content_limit = getattr(self.settings, 'firecrawl_content_limit', 2500)
                            original_length = len(full_content)
                            if len(full_content) > content_limit:
                                full_content = full_content[:content_limit] + f"...\n\n[Content limited to first {content_limit:,} characters for efficiency. Original: {original_length:,} chars]"
                        
                        self.logger.debug("URL scraped successfully", 
                                       url=url, 
                                       content_length=len(full_content),
                                       index=index)
                    except Exception as json_error:
                        self.logger.warning("JSON parsing error during scraping", 
                                          url=url, 
                                          error=str(json_error),
                                          index=index)
                else:
                    self.logger.warning("Scraping failed", 
                                      url=url, 
                                      status_code=scrape_response.status_code,
                                      index=index)
                
            except Exception as e:
                self.logger.error("Scraping exception", 
                                url=url, 
                                error=str(e),
                                index=index)
                full_content = description  # fallback to snippet
            
            # Use unified quality assessor for content quality
            from ..core.quality_assessor import AssessmentRequest, AssessmentMode
            
            temp_result = SearchResult(
                url=url,
                title=title,
                snippet=description,
                content=full_content,
                relevance_score=0.0,
                source_type="firecrawl"
            )
            
            quality_request = AssessmentRequest(
                results=[temp_result],
                sub_question=None,
                mode=AssessmentMode.ALGORITHMIC_FAST
            )
            
            try:
                if hasattr(self, 'quality_assessor'):
                    quality_metrics = self.quality_assessor._algorithmic_fast_assessment(quality_request)
                    content_quality = quality_metrics.content_quality
                else:
                    content_quality = 0.7  # Default for firecrawl
            except Exception:
                content_quality = 0.7
            
            # Create SearchResult
            return SearchResult(
                title=title,
                url=url,
                snippet=description,
                content=full_content,
                relevance_score=0.8,
                authority_score=0.7,
                content_quality=content_quality,
                source_type="firecrawl"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to scrape URL {url}: {str(e)}")
            return None

    async def _scrape_urls_sequential(self, url_results, scrape_url, headers, loop):
        """Scrape URLs sequentially with rate limiting"""
        self.logger.info("Starting sequential scraping", url_count=len(url_results))
        
        results = []
        start_time = time.time()
        
        for i, result_data in enumerate(url_results):
            scraped_result = await self._scrape_single_url(result_data, scrape_url, headers, loop, i+1, len(url_results))
            if scraped_result:
                results.append(scraped_result)
            
            # Rate limiting between requests
            if i < len(url_results) - 1:
                await asyncio.sleep(0.5)
        
        elapsed = time.time() - start_time
        self.logger.info("Sequential scraping completed", 
                       results_count=len(results),
                       total_attempts=len(url_results),
                       elapsed_time=f"{elapsed:.1f}s")
        
        return results
    
    async def _unified_search(self, query: str, count: int = 10, 
                             resource_manager: ResourceManager = None) -> List[SearchResult]:
        """Unified search using preferred method with fallback"""
        self.logger.info("Starting unified search", query=query, preferred_method="Firecrawl")
        
        # Determine which search engine to use based on configuration
        preferred_engine = self.settings.preferred_search_engine.lower()
        
        if preferred_engine == "firecrawl":
            if self.settings.firecrawl_api_key:
                self.logger.info("Using Firecrawl search (preferred)")
        
                return await self._firecrawl_search(query, count, resource_manager)
            else:
                self.logger.warning("Firecrawl preferred but API key not configured, falling back to Brave")
                return await self._brave_search(query, count, resource_manager)
        
        elif preferred_engine == "brave":
            if self.settings.brave_api_key:
                self.logger.info("Using Brave search (preferred)")
                return await self._brave_search(query, count, resource_manager)
            else:
                self.logger.warning("Brave preferred but API key not configured, trying Firecrawl")
                return await self._firecrawl_search(query, count, resource_manager)
        
        elif preferred_engine == "auto":
            # Auto mode: try Firecrawl first, then fallback to Brave
            if self.settings.firecrawl_api_key:
                self.logger.info("Auto mode: trying Firecrawl first")
                try:
                    results = await self._firecrawl_search(query, count, resource_manager)
                    if results:
                        return results
                    else:
                        self.logger.info("Firecrawl returned no results, trying Brave")
                        return await self._brave_search(query, count, resource_manager)
                except Exception as e:
                    self.logger.warning(f"Firecrawl failed in auto mode, falling back to Brave: {e}")
                    return await self._brave_search(query, count, resource_manager)
            else:
                self.logger.info("Auto mode: Firecrawl not available, using Brave")
                return await self._brave_search(query, count, resource_manager)
        
        else:
            # Default to Brave if invalid configuration
            self.logger.warning(f"Invalid preferred_search_engine: {preferred_engine}, defaulting to Brave")
            return await self._brave_search(query, count, resource_manager)
    
    def _prioritize_company_domains(self, results: List[SearchResult], company_info: Dict[str, Any], count: int) -> List[SearchResult]:
        """Ensure company domain results are prioritized in final results"""
        detected_companies = company_info.get('detected_companies', [])
        
        # Separate company domain results from other results
        company_results = []
        other_results = []
        
        for result in results:
            is_company_domain = False
            url_lower = result.url.lower()
            
            for company in detected_companies:
                company_clean = company.lower().replace(' inc', '').replace(' corp', '').replace(' llc', '').replace(' ltd', '').replace(' company', '').replace(' ', '')
                
                # Check if this is an official company domain (check both clean and full name)
                if any(domain in url_lower for domain in [
                    f"{company_clean}.com",
                    f"{company_clean}.org", 
                    f"{company_clean}.net",
                    f"{company.lower().replace(' ', '')}.com",  # Also check full name
                    f"{company.lower().replace(' ', '')}.org",
                    f"{company.lower().replace(' ', '')}.net"
                ]):
                    is_company_domain = True
                    break
            
            if is_company_domain:
                company_results.append(result)
            else:
                other_results.append(result)
        
        # Sort both lists by relevance
        company_results.sort(key=lambda x: x.relevance_score, reverse=True)
        other_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Ensure we get at least some company results if they exist
        final_results = []
        
        if company_results:
            # Guarantee at least 2 company domain results if available
            guaranteed_company_count = min(2, len(company_results), count // 2)
            final_results.extend(company_results[:guaranteed_company_count])
            
            # Fill remaining slots with mix of company and other results
            remaining_slots = count - len(final_results)
            remaining_company = company_results[guaranteed_company_count:]
            
            # Interleave remaining company results with other results
            all_remaining = remaining_company + other_results
            all_remaining.sort(key=lambda x: x.relevance_score, reverse=True)
            final_results.extend(all_remaining[:remaining_slots])
        else:
            # No company results found, just return top other results
            final_results = other_results[:count]
        
        self.logger.info("Company domain prioritization applied", 
                        company_results=len(company_results),
                        other_results=len(other_results),
                        final_count=len(final_results))
        
        return final_results
    
    async def _create_enhanced_search_queries_from_query(self, query: str, company_info: Dict[str, Any], resource_manager: ResourceManager = None) -> List[str]:
        """🤖 Create AI-enhanced search queries targeting company websites"""
        queries = [query]  # Start with original query
        
        if company_info.get('is_company_query', False):
            detected_companies = company_info.get('detected_companies', [])
            
            for company in detected_companies[:2]:  # Limit to avoid too many queries
                # Add company-specific search queries
                queries.extend([
                    f"{company} official website",
                    f"{company} company information",
                    f"{company} about company profile"
                ])
                
                # Add AI-powered domain-specific searches
                if resource_manager:
                    try:
                        domains = await self._guess_company_domains(company, resource_manager)
                        for domain in domains[:2]:  # Use top 2 domains
                            queries.append(f"site:{domain} {query}")
                    except Exception as e:
                        self.logger.warning(f"Failed to get AI domains for {company}", error=str(e))
                        # Fallback to simple domain
                        fallback_domains = self._fallback_domain_guess(company)
                        queries.append(f"site:{fallback_domains[0]} {query}")
                else:
                    # Fallback when no resource manager
                    fallback_domains = self._fallback_domain_guess(company)
                    queries.append(f"site:{fallback_domains[0]} {query}")
        
        return queries
    
    async def _guess_company_domains(self, company_name: str, resource_manager: ResourceManager = None) -> List[str]:
        """🤖 AI-powered intelligent domain guessing for any company"""
        try:
            if resource_manager is None:
                return self._fallback_domain_guess(company_name)
            
            # Use AI to intelligently guess likely domains
            ai_prompt = f"""Given a company name, predict the most likely official website domains. Consider:
1. Common domain patterns and conventions
2. Company name variations and abbreviations
3. Different TLDs (.com, .org, .net, country-specific)
4. Industry-specific patterns

Company: "{company_name}"

Provide a JSON response with:
1. primary_domain: Most likely official domain
2. alternative_domains: Array of other possible domains (max 3)
3. reasoning: Brief explanation of domain choices

Examples:
- "Apple Inc" → {{"primary_domain": "apple.com", "alternative_domains": ["apple.org"], "reasoning": "Simple brand name, tech company typically uses .com"}}
- "Tesla Motors" → {{"primary_domain": "tesla.com", "alternative_domains": ["teslamotors.com"], "reasoning": "Brand Tesla is primary, Tesla Motors is full name"}}
- "Berkshire Hathaway" → {{"primary_domain": "berkshirehathaway.com", "alternative_domains": ["brk.com", "berkshire.com"], "reasoning": "Full name likely, financial companies often use abbreviations"}}

Respond with only valid JSON, no other text."""

            response = await self._call_fireworks_api(
                ai_prompt, 
                max_tokens=200, 
                resource_manager=resource_manager,
                operation="domain_guessing"
            )
            
            # Parse AI response using unified parser
            try:
                from ..core.response_parser import ResponseParser
                json_response = ResponseParser.extract_json_from_response(response)
                ai_result = ResponseParser.parse_json_response(json_response)
                
                domains = [ai_result.get('primary_domain', f"{company_name.lower().replace(' ', '')}.com")]
                domains.extend(ai_result.get('alternative_domains', []))
                
    
                return [d for d in domains if d and d not in domains[:domains.index(d)]][:4]  # Max 4 domains
                
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse AI domain guessing response", response=response)
                return self._fallback_domain_guess(company_name)
                
        except Exception as e:
            self.logger.warning("AI domain guessing failed, using fallback", error=str(e))
            return self._fallback_domain_guess(company_name)
    
    def _fallback_domain_guess(self, company_name: str) -> List[str]:
        """Fallback domain guessing when AI is unavailable"""
        # Clean up company name
        clean_name = company_name.lower().replace(' inc', '').replace(' corp', '').replace(' llc', '').replace(' ltd', '').replace(' company', '').replace(' ', '')
        
        # Generate multiple possible domains
        domains = [
            f"{clean_name}.com",
            f"{company_name.lower().replace(' ', '')}.com",  # Full name
        ]
        
        # Add common variations
        if len(clean_name) > 8:  # For longer names, try abbreviations
            words = company_name.split()
            if len(words) > 1:
                abbreviation = ''.join(word[0].lower() for word in words if word.lower() not in ['inc', 'corp', 'llc', 'ltd', 'company'])
                if len(abbreviation) >= 2:
                    domains.append(f"{abbreviation}.com")
        
        return domains[:3]  # Return max 3 domains
    
    def _score_relevance_with_company_priority(self, results: List[SearchResult], query: str, company_info: Dict[str, Any]) -> List[SearchResult]:
        """Enhanced relevance scoring with company domain prioritization"""
        search_terms = query.lower().split()
        
        for result in results:
            # Calculate base URL relevance score
            url_score = self._calculate_url_relevance_score(result.url, result.title, query, search_terms)
            
            # Apply company domain boost if this is a company query
            if company_info.get('is_company_query', False):
                company_boost = self._calculate_company_domain_boost(result.url, result.title, company_info)
                url_score = min(1.0, url_score + company_boost)
            
            result.relevance_score = url_score
            
            # Update authority score using unified quality assessor
            from ..core.quality_assessor import AssessmentRequest, AssessmentMode
            
            quality_request = AssessmentRequest(
                results=[result],
                sub_question=None,
                mode=AssessmentMode.ALGORITHMIC_FAST
            )
            
            try:
                if hasattr(self, 'quality_assessor'):
                    quality_metrics = self.quality_assessor._algorithmic_fast_assessment(quality_request)
                    result.authority_score = quality_metrics.authority_score
            except Exception:
                result.authority_score = 0.5  # Fallback
        
        return results
    
    def _calculate_company_domain_boost(self, url: str, title: str, company_info: Dict[str, Any]) -> float:
        """Calculate moderate boost for official company domains while preserving content quality assessment"""
        boost = 0.0
        detected_companies = company_info.get('detected_companies', [])
        
        for company in detected_companies:
            company_lower = company.lower()
            url_lower = url.lower()
            title_lower = title.lower()
            
            # Clean company name - remove common suffixes
            company_clean = company_lower.replace(' inc', '').replace(' corp', '').replace(' llc', '').replace(' ltd', '').replace(' company', '').replace(' ', '')
            
            # Strong boost for official company domains to prioritize over general sources
            if any(domain in url_lower for domain in [
                f"{company_clean}.com",
                f"{company_clean}.org",
                f"{company_clean}.net",
                f"{company_lower.replace(' ', '')}.com",  # Also check full name
                f"{company_lower.replace(' ', '')}.org",
                f"{company_lower.replace(' ', '')}.net"
            ]):
                boost += 0.5  # Increased to ensure company websites outrank Wikipedia
            
            # Moderate boost for company name in domain (check both clean and full name)
            elif company_clean in url_lower or company_lower.replace(' ', '') in url_lower:
                boost += 0.3  # Increased from 0.15
            
            # Small boost for company name in title
            elif company_lower in title_lower or company_clean in title_lower:
                boost += 0.15  # Increased from 0.05
        
        return boost
    
    
    
    def _calculate_url_relevance_score(self, url: str, title: str, question: str, search_terms: List[str]) -> float:
        """Calculate relevance score with balanced general content focus"""
        total_score = 0.0
        
        # 1. Title relevance (most important for general content)
        title_score = self._analyze_title_relevance(title, question, search_terms)
        total_score += title_score * 0.40  # Increased - title is strongest signal
        
        # 2. URL path analysis 
        path_score = self._analyze_url_path(url, search_terms)
        total_score += path_score * 0.25  
        
        # 3. Domain relevance analysis
        domain_score = self._analyze_domain_relevance(url, question, search_terms)
        total_score += domain_score * 0.20  
        
        # 4. Company domain boost (only when relevant)
        company_score = self._analyze_company_domain_relevance(url, title, question, search_terms)
        total_score += company_score * 0.10  # Reduced - only boost when company-specific
        
        # 5. Question-specific patterns
        pattern_score = self._analyze_question_specific_patterns(url, question)
        total_score += pattern_score * 0.05  
        
        # Add baseline relevance for reasonable sources to avoid systematic under-scoring
        if total_score < 0.3 and title and any(term.lower() in title.lower() for term in search_terms):
            total_score = max(total_score, 0.3)  # Minimum relevance for term-matching titles
        
        return min(1.0, total_score)
    
    def _analyze_title_relevance(self, title: str, question: str, search_terms: List[str]) -> float:
        """Analyze how well the title matches the search intent"""
        if not title:
            return 0.0
            
        title_lower = title.lower()
        question_lower = question.lower()
        score = 0.0
        
        # Direct search term matches in title (strongest signal)
        matched_terms = 0
        for term in search_terms:
            if term.lower() in title_lower:
                matched_terms += 1
                score += 0.4
        
        # Bonus for multiple term matches
        if matched_terms > 1:
            score += 0.3
            
        # Question word matches
        question_words = question_lower.split()
        title_words = title_lower.split()
        overlap = len(set(question_words) & set(title_words))
        if overlap > 0:
            score += min(0.4, overlap * 0.1)
        
        return min(1.0, score)
    
    def _analyze_company_domain_relevance(self, url: str, title: str, question: str, search_terms: List[str]) -> float:
        """Analyze company domain relevance for company queries with balanced scoring"""
        score = 0.0
        url_lower = url.lower()
        title_lower = title.lower()
        question_lower = question.lower()
        
        # Detect company indicators in question
        company_indicators = ['company', 'corporation', 'corp', 'inc', 'ltd', 'llc']
        has_company_indicator = any(indicator in question_lower for indicator in company_indicators)
        
        if has_company_indicator:
            # Extract potential company names from search terms
            for term in search_terms:
                term_clean = term.strip().lower()
                if len(term_clean) > 2:  # Avoid short words
                    # Check if company name appears in domain (strong boost for official sites)
                    if term_clean.replace(' ', '') in url_lower:
                        score += 0.8  # Increased to prioritize official company domains
                    # Check if company name appears in title
                    elif term_clean in title_lower:
                        score += 0.4  # Increased from 0.3
        
        # Boost for official company pages
        if any(pattern in url_lower for pattern in ['/about', '/company', '/investor', '/careers']):
            score += 0.3  # Increased back to prioritize official company pages
        
        return min(1.0, score)  # Allow full score for official company domains
    
    def _analyze_domain_relevance(self, url: str, question: str, search_terms: List[str]) -> float:
        """Analyze domain relevance to question topic"""
        domain = url.split('/')[2] if len(url.split('/')) > 2 else url
        domain_lower = domain.lower()
        
        score = 0.0
        
        # High-authority domains get a boost
        if any(auth_domain in domain_lower for auth_domain in [
            'gov', 'edu', 'org', 'wikipedia', 'reuters', 'bloomberg'
        ]):
            score += 0.8
        
        # Check for topic-specific domains
        for term in search_terms:
            if term.lower() in domain_lower:
                score += 0.3
                break
        
        return min(1.0, score)
    
    def _analyze_url_path(self, url: str, search_terms: List[str]) -> float:
        """Analyze URL path for content indicators"""
        path = url.split('/', 3)[-1] if '/' in url else ''
        path_lower = path.lower()
        
        score = 0.0
        
        # Content type indicators
        content_indicators = {
            'about': 0.8, 'company': 0.8, 'profile': 0.7,
            'info': 0.6, 'overview': 0.6, 'details': 0.5,
            'news': 0.4, 'press': 0.4, 'blog': 0.3
        }
        
        for indicator, weight in content_indicators.items():
            if indicator in path_lower:
                score += weight
                break
        
        # Search term matches in path
        for term in search_terms:
            if term.lower() in path_lower:
                score += 0.3
        
        return min(1.0, score)
    
    
    
    def _analyze_question_specific_patterns(self, url: str, question: str) -> float:
        """Analyze URL patterns specific to question type"""
        url_lower = url.lower()
        question_lower = question.lower()
        
        score = 0.0
        
        # Question type patterns
        if any(word in question_lower for word in ['what is', 'about', 'overview']):
            if any(pattern in url_lower for pattern in ['/about', '/overview', '/company']):
                score += 0.8
        
        if any(word in question_lower for word in ['history', 'founded', 'background']):
            if any(pattern in url_lower for pattern in ['/history', '/about', '/company']):
                score += 0.8
        
        if any(word in question_lower for word in ['products', 'services']):
            if any(pattern in url_lower for pattern in ['/products', '/services']):
                score += 0.8
        
        return min(1.0, score)
    
    
    
    def _prepare_content_for_ai(self, results: List[SearchResult], sub_question: SubQuestion) -> str:
        """Prepare search results content for AI analysis"""
        content_parts = []
        
        content_parts.append(f"RESEARCH QUESTION: {sub_question.question}")
        content_parts.append(f"SEARCH TERMS: {', '.join(sub_question.search_terms)}")
        content_parts.append("")
        
        content_parts.append("SEARCH RESULTS:")
        for i, result in enumerate(results[:10], 1):  # Limit to top 10 for processing
            content_parts.append(f"""
{i}. Title: {result.title}
   URL: {result.url}
   Source: {result.source_type}
   Authority: {result.authority_score:.2f}
   Relevance: {result.relevance_score:.2f}
   Content: {result.snippet}
   Published: {result.date_published or 'Unknown'}
""")
        
        return "\n".join(content_parts)
    
    
    
    async def gather_information(self, sub_question: SubQuestion, 
                               resource_manager: ResourceManager,
                               progress: ProgressTracker) -> RetrievalFindings:
        """Enhanced information gathering with quality assessment and company-specific search"""
        self.logger.info("Gathering information", question=sub_question.question)
        progress.update_stage(f"searching_for_question_{sub_question.id}")
        
        start_time = time.time()
        
        try:
            # Check if this is a company-related query and create enhanced search queries
            company_info = await self._detect_company_query(sub_question.question, resource_manager)
            search_queries = await self._create_enhanced_search_queries(sub_question, resource_manager)
            
            # Perform web search with more results for company queries
            all_results = []
            is_company_query = company_info.get('is_company_query', False)
            
            if is_company_query:
                # For company queries, use more search queries and higher result counts
                for query in search_queries[:6]:  # Use more queries for companies
                    count = 8 if 'site:' in query else 6  # Reduced from 15/12 to save Firecrawl credits
                    results = await self._unified_search(query, count=count, resource_manager=resource_manager)
                    all_results.extend(results)
                    
                    # Add a small delay between searches to avoid rate limiting
                    await asyncio.sleep(0.3)
            else:
                # For non-company queries, use standard approach
                for query in search_queries[:3]:
                    results = await self._unified_search(query, count=5, resource_manager=resource_manager)  # Reduced from 10 to 5
                    all_results.extend(results)
            
            if not all_results:
                # Fallback to basic search if enhanced search fails
                fallback_count = 10 if is_company_query else 8  # Reduced from 20/15 to save Firecrawl credits
                all_results = await self._unified_search(sub_question.question, count=fallback_count, resource_manager=resource_manager)
            

            unique_results = []
            seen_urls = set()
            for result in all_results:
                if result.url not in seen_urls and len(unique_results) < 25:  # Increased limit for company queries
                    unique_results.append(result)
                    seen_urls.add(result.url)
            
            # CRITICAL: Apply company domain relevance scoring BEFORE filtering
            if is_company_query and unique_results:
                self.logger.info("🏢 Applying company domain prioritization", 
                               company_query=True, 
                               results_count=len(unique_results))
                unique_results = self._score_relevance_with_company_priority(
                    unique_results, sub_question.question, company_info
                )
            else:
                # Apply standard relevance scoring for non-company queries
                company_info = {"is_company_query": False, "detected_companies": []}
                unique_results = self._score_relevance_with_company_priority(unique_results, sub_question.question, company_info)
            
            # Apply source filtering if enabled
            if self.source_filter:
                filtering_decision = self.source_filter.filter_sources(unique_results, sub_question)
                filtered_results = filtering_decision.filtered_results
                
                # Update metrics collector with filtering information for web UI
                metrics_collector.update_source_filtering(filtering_decision, unique_results)
            else:
                filtered_results = unique_results[:12]  # Increased limit for better company coverage
            
            # Update metrics collector with current sources for web UI
            metrics_collector.update_sources(filtered_results)
            
                    # Sources updated in metrics collector
            self.logger.debug(f"Updated metrics with {len(filtered_results)} filtered sources")
            
            # Extract insights and facts using AI
            key_insights, extracted_facts = await self._extract_insights_with_ai(
                filtered_results, sub_question, resource_manager
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(filtered_results, key_insights, extracted_facts)
            
            processing_time = time.time() - start_time
            
            return RetrievalFindings(
                sub_question_id=sub_question.id,
                query_used=sub_question.question,
                results=filtered_results,
                key_insights=key_insights,
                extracted_facts=extracted_facts,
                confidence_score=confidence_score,
                processing_time=processing_time,
                sources_count=len(filtered_results)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Use unified error handler with structured fallback
            from ..core.error_handler import StandardErrorHandler, ErrorContext, ErrorSeverity, RecoveryStrategy
            context = ErrorContext(
                operation="gather_information",
                component=self.name,
                metadata={"sub_question_id": sub_question.id, "processing_time": processing_time}
            )
            handler = StandardErrorHandler()
            
            # Return empty findings on failure
            fallback_findings = RetrievalFindings(
                sub_question_id=sub_question.id,
                query_used=sub_question.question,
                results=[],
                key_insights=["Failed to gather information due to technical issues"],
                extracted_facts=["No facts could be extracted"],
                confidence_score=0.0,
                processing_time=processing_time,
                sources_count=0
            )
            return handler.handle_error(e, context, ErrorSeverity.MEDIUM, RecoveryStrategy.RETURN_FALLBACK, fallback_findings)
    
    async def _create_enhanced_search_queries(self, sub_question: SubQuestion, resource_manager: ResourceManager = None) -> List[str]:
        """🤖 Create AI-enhanced search queries including dynamic company-specific ones"""
        queries = [sub_question.question]  # Start with original question
        
        # Detect if this is a company query using AI
        company_info = await self._detect_company_query(sub_question.question, resource_manager)
        
        if company_info.get('is_company_query', False):
            detected_companies = company_info.get('detected_companies', [])
            
            for company in detected_companies[:1]:  # Focus on primary company
                # Add high-priority company website searches
                queries.extend([
                    f"{company} official website",
                    f"{company} company about us",
                    f"{company} corporate information",
                    f"{company} investor relations",
                    f"{company} company profile overview"
                ])
                
                # Add AI-powered domain-specific searches
                if resource_manager:
                    try:
                        domains = await self._guess_company_domains(company, resource_manager)
                        for domain in domains[:3]:  # Use top 3 domains
                            queries.extend([
                                f"site:{domain} about",
                                f"site:{domain} company",
                                f"site:{domain} {sub_question.question}"
                            ])
                    except Exception as e:
                        self.logger.warning(f"Failed to get AI domains for {company}", error=str(e))
                        # Fallback to simple domain guessing
                        fallback_domains = self._fallback_domain_guess(company)
                        for domain in fallback_domains[:2]:
                            queries.extend([
                                f"site:{domain} about",
                                f"site:{domain} company"
                            ])
                else:
                    # Fallback when no resource manager
                    fallback_domains = self._fallback_domain_guess(company)
                    for domain in fallback_domains[:2]:
                        queries.extend([
                            f"site:{domain} about",
                            f"site:{domain} company"
                        ])
        
        # Add search term variations (only if not already covered)
        for term in sub_question.search_terms[:1]:  # Reduce to avoid query explosion
            if term.lower() not in sub_question.question.lower() and len(term) > 3:
                queries.append(f"{sub_question.question} {term}")
        
        return queries
    
    async def _extract_insights_with_ai(self, results: List[SearchResult], 
                                      sub_question: SubQuestion,
                                      resource_manager: ResourceManager) -> tuple:
        """Extract insights and facts using AI analysis"""
        try:
            # Prepare content for AI analysis
            content_summary = self._prepare_content_for_ai(results, sub_question)
            
            prompt = f"""Analyze the search results below and extract key insights and facts relevant to: "{sub_question.question}"

{content_summary}

Extract the most important insights and facts. Focus on accuracy and relevance.

Respond with ONLY valid JSON in this format:
{{
    "key_insights": [
        "insight 1",
        "insight 2", 
        "insight 3",
        "insight 4",
        "insight 5"
    ],
    "extracted_facts": [
        "fact 1",
        "fact 2",
        "fact 3", 
        "fact 4",
        "fact 5"
    ]
}}"""
        
            api_response = await self._call_fireworks_api(prompt, 800, resource_manager, "insight_extraction")
            
            # Enhanced JSON parsing with fallback handling
            try:
                from ..core.response_parser import ResponseParser
                json_response = ResponseParser.extract_json_from_response(api_response)
                data = ResponseParser.parse_json_response(json_response)
            except Exception as parse_error:
                # If JSON parsing fails, try to extract partial data
                self.logger.warning("JSON parsing failed, using simple extraction", 
                                  error=str(parse_error), response_preview=api_response[:500])
                
                # Try simple regex extraction as fallback
                import re
                try:
                    insight_match = re.search(r'"key_insights":\s*\[(.*?)\]', api_response, re.DOTALL)
                    facts_match = re.search(r'"extracted_facts":\s*\[(.*?)\]', api_response, re.DOTALL)
                    
                    insights = []
                    facts = []
                    
                    if insight_match:
                        insight_text = insight_match.group(1)
                        insights = [s.strip('"') for s in re.findall(r'"([^"]*)"', insight_text)]
                    
                    if facts_match:
                        facts_text = facts_match.group(1)
                        facts = [s.strip('"') for s in re.findall(r'"([^"]*)"', facts_text)]
                    
                    data = {
                        "key_insights": insights if insights else ["Partial insight extraction from malformed response"],
                        "extracted_facts": facts if facts else ["Partial fact extraction from malformed response"]
                    }
                except Exception:
                    # Complete fallback
                    data = {
                        "key_insights": ["Response parsing failed - manual analysis required"],
                        "extracted_facts": ["Response parsing failed - manual analysis required"]
                    }
            
            return (
                data.get("key_insights", [
                    "AI-generated insight 1", "AI-generated insight 2", 
                    "AI-generated insight 3", "AI-generated insight 4", 
                    "AI-generated insight 5"
                ]),
                data.get("extracted_facts", [
                    "AI-generated fact 1", "AI-generated fact 2",
                    "AI-generated fact 3", "AI-generated fact 4",
                    "AI-generated fact 5"
                ])
            )
            
        except Exception as e:
            self.logger.warning("AI insight extraction failed, using fallback", 
                              error=str(e), sub_question_id=sub_question.id)
            
            # Return robust fallback data
            return (
                ["AI insight extraction failed - using manual fallback"],
                ["AI fact extraction failed - using manual fallback"]
            )
    
    def _calculate_confidence_score(self, results: List[SearchResult], 
                                  insights: List[str], facts: List[str]) -> float:
        """Calculate confidence score based on result quality and quantity"""
        base_confidence = 0.3
        
        # Factor in result quantity and quality (safely handle empty lists)
        if results:
            result_factor = min(len(results) / 10, 1.0) * 0.3
            
            # Factor in quality metrics (safely handle None values)
            authority_scores = [r.authority_score or 0.5 for r in results]
            relevance_scores = [r.relevance_score or 0.5 for r in results]
            
            quality_factor = sum(authority_scores) / len(results) * 0.2
            relevance_factor = sum(relevance_scores) / len(results) * 0.1
        else:
            result_factor = quality_factor = relevance_factor = 0.0
        
        # Factor in content richness (safely handle None lists)
        insights = insights or []
        facts = facts or []
        insight_factor = min(len(insights) / 5, 1.0) * 0.1
        fact_factor = min(len(facts) / 5, 1.0) * 0.1
        
        confidence = base_confidence + result_factor + quality_factor + relevance_factor + insight_factor + fact_factor
        return min(1.0, max(0.1, confidence))

    # NEW BATCHED PARALLEL SCRAPING METHODS
    async def gather_search_urls_only(self, sub_question: SubQuestion, 
                                    resource_manager: ResourceManager) -> tuple:
        """Enhanced information gathering that only collects URLs without scraping"""
        self.logger.info("Gathering search URLs only", question=sub_question.question)
        
        try:
            # Check if this is a company-related query and create enhanced search queries
            company_info = await self._detect_company_query(sub_question.question, resource_manager)
            search_queries = await self._create_enhanced_search_queries(sub_question, resource_manager)
            
            # Perform web search with more results for company queries
            all_url_results = []
            is_company_query = company_info.get('is_company_query', False)
            
            if is_company_query:
                # For company queries, use more search queries and higher result counts
                for query in search_queries[:6]:  # Use more queries for companies
                    count = 8 if 'site:' in query else 6
                    url_results = await self._unified_search_urls_only(query, count=count, resource_manager=resource_manager)
                    all_url_results.extend(url_results)
                    
                    # Add a small delay between searches to avoid rate limiting
                    await asyncio.sleep(0.3)
            else:
                # For non-company queries, use standard approach
                for query in search_queries[:3]:
                    url_results = await self._unified_search_urls_only(query, count=5, resource_manager=resource_manager)
                    all_url_results.extend(url_results)
            
            if not all_url_results:
                # Fallback to basic search if enhanced search fails
                fallback_count = 10 if is_company_query else 8
                all_url_results = await self._unified_search_urls_only(sub_question.question, count=fallback_count, resource_manager=resource_manager)
            
            # Remove duplicates but keep order with reasonable limits
            unique_url_results = []
            seen_urls = set()
            max_urls = 8 if is_company_query else 5  # Reasonable limits: 8 for company, 5 for regular
            
            for result in all_url_results:
                url = result.get("url", "")
                if url and url not in seen_urls and len(unique_url_results) < max_urls:
                    # Add sub_question_id to track which question this URL belongs to
                    result["sub_question_id"] = sub_question.id
                    result["sub_question"] = sub_question.question
                    result["company_info"] = company_info
                    unique_url_results.append(result)
                    seen_urls.add(url)
            
            self.logger.info("URLs collected for sub-question", 
                           sub_question_id=sub_question.id, 
                           url_count=len(unique_url_results))
            
            return unique_url_results, company_info
            
        except Exception as e:
            self.logger.error("Failed to gather URLs for sub-question", 
                            sub_question_id=sub_question.id, error=str(e))
            return [], {}

    async def _unified_search_urls_only(self, query: str, count: int = 10, 
                                       resource_manager: ResourceManager = None) -> List[dict]:
        """Unified search that returns only URL data without scraping content"""
        self.logger.debug("Starting unified search (URLs only)", query=query)
        
        # Determine which search engine to use based on configuration
        preferred_engine = self.settings.preferred_search_engine.lower()
        
        if preferred_engine == "firecrawl":
            if self.settings.firecrawl_api_key:
                self.logger.debug("Using Firecrawl search (URLs only)")
                return await self._firecrawl_search_urls_only(query, count, resource_manager)
            else:
                self.logger.warning("Firecrawl preferred but API key not configured, falling back to Brave")
                return await self._brave_search_urls_only(query, count, resource_manager)
        
        elif preferred_engine == "brave":
            if self.settings.brave_api_key:
                self.logger.debug("Using Brave search (URLs only)")
                return await self._brave_search_urls_only(query, count, resource_manager)
            else:
                self.logger.warning("Brave preferred but API key not configured, trying Firecrawl")
                return await self._firecrawl_search_urls_only(query, count, resource_manager)
        
        elif preferred_engine == "auto":
            # Auto mode: try Firecrawl first, then fallback to Brave
            try:
                if self.settings.firecrawl_api_key:
                    return await self._firecrawl_search_urls_only(query, count, resource_manager)
                elif self.settings.brave_api_key:
                    return await self._brave_search_urls_only(query, count, resource_manager)
                else:
                    self.logger.error("No search engine API keys configured")
                    return []
            except Exception as e:
                self.logger.warning("Firecrawl search failed, trying Brave", error=str(e))
                try:
                    return await self._brave_search_urls_only(query, count, resource_manager)
                except Exception as brave_error:
                    self.logger.error("All search engines failed", 
                                    firecrawl_error=str(e), 
                                    brave_error=str(brave_error))
                    return []
        
        return []

    async def _firecrawl_search_urls_only(self, query: str, count: int = 10, 
                                        resource_manager: ResourceManager = None) -> List[dict]:
        """Firecrawl search that returns only URL data without content scraping"""
        try:
            search_url = "https://api.firecrawl.dev/v1/search"
            headers = {
                "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
                "Content-Type": "application/json"
            }
            
            search_data = {
                "query": query,
                "limit": count,
                "lang": "en"
            }
            
            # Use unified timeout manager
            from ..core.timeout_manager import get_search_timeout_seconds
            timeout = get_search_timeout_seconds()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(search_url, headers=headers, json=search_data, timeout=timeout)
            )
            
            if response.status_code == 200:
                search_result = response.json()
                url_results = []
                
                for item in search_result.get("data", []):
                    url_data = {
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "description": item.get("description", "")
                    }
                    url_results.append(url_data)
                
                self.logger.debug("Firecrawl search completed (URLs only)", 
                                url_count=len(url_results), query=query)
                return url_results
            else:
                self.logger.warning("Firecrawl search failed", 
                                  status_code=response.status_code, 
                                  query=query)
                return []
                
        except Exception as e:
            self.logger.error("Firecrawl search error", error=str(e), query=query)
            return []

    async def _brave_search_urls_only(self, query: str, count: int = 10, 
                                    resource_manager: ResourceManager = None) -> List[dict]:
        """Brave search that returns only URL data without content"""
        try:
            # Use Brave API for search results (URLs only)
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.settings.brave_api_key
            }
            params = {
                "q": query,
                "count": count,
                "search_lang": "en",
                "country": "us",
                "text_decorations": "false",
                "result_filter": "web"
            }
            
            from ..core.timeout_manager import get_search_timeout_seconds
            timeout = get_search_timeout_seconds()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=params, timeout=timeout)
            )
            
            if response.status_code == 200:
                data = response.json()
                url_results = []
                
                for result in data.get("web", {}).get("results", []):
                    url_data = {
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "description": result.get("description", "")
                    }
                    url_results.append(url_data)
                
                self.logger.debug("Brave search completed (URLs only)", 
                                url_count=len(url_results), query=query)
                return url_results
            else:
                self.logger.warning("Brave search failed", 
                                  status_code=response.status_code, 
                                  query=query)
                return []
                
        except Exception as e:
            self.logger.error("Brave search error", error=str(e), query=query)
            return []

    async def batch_scrape_all_urls(self, all_url_results: List[dict], 
                                  resource_manager: ResourceManager) -> dict:
        """
        Scrape all URLs from all sub-questions in optimized batches
        Takes advantage of Firecrawl's 50 concurrent browser sessions capability
        """
        if not all_url_results:
            return {}
        
        self.logger.info("🚀 Starting TRUE batched parallel URL scraping", 
                       total_urls=len(all_url_results),
                       max_concurrent=50)
        
        # Determine scraping method based on configuration
        preferred_engine = self.settings.preferred_search_engine.lower()
        
        if preferred_engine == "firecrawl" and self.settings.firecrawl_api_key:
            return await self._batch_scrape_firecrawl(all_url_results, resource_manager)
        else:
            # Fallback to individual scraping if not using Firecrawl
            return await self._batch_scrape_fallback(all_url_results, resource_manager)

    async def _batch_scrape_firecrawl(self, all_url_results: List[dict], 
                                    resource_manager: ResourceManager) -> dict:
        """Batch scrape using Firecrawl's parallel capabilities"""
        scrape_url = "https://api.firecrawl.dev/v1/scrape"
        headers = {
            "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
            "Content-Type": "application/json"
        }
        
        # Process in batches of 50 (Firecrawl's concurrent limit)
        batch_size = 50
        all_scraped_results = {}
        
        for batch_start in range(0, len(all_url_results), batch_size):
            batch_end = min(batch_start + batch_size, len(all_url_results))
            batch = all_url_results[batch_start:batch_end]
            
            self.logger.info(f"🔄 Processing batch {(batch_start//batch_size)+1} of {((len(all_url_results)-1)//batch_size)+1}", 
                           batch_size=len(batch),
                           urls_range=f"{batch_start+1}-{batch_end}")
            
            # Create scraping tasks for this batch
            loop = asyncio.get_event_loop()
            tasks = []
            
            for i, url_data in enumerate(batch):
                task = self._scrape_single_url_enhanced(url_data, scrape_url, headers, loop, 
                                                      batch_start + i + 1, len(all_url_results))
                tasks.append(task)
            
            # Execute batch in parallel
            batch_start_time = time.time()
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_elapsed = time.time() - batch_start_time
            
            # Process batch results
            successful_count = 0
            for i, result in enumerate(batch_results):
                url_data = batch[i]
                sub_question_id = url_data.get("sub_question_id")
                
                if sub_question_id not in all_scraped_results:
                    all_scraped_results[sub_question_id] = []
                
                if isinstance(result, SearchResult):
                    all_scraped_results[sub_question_id].append(result)
                    successful_count += 1
                elif isinstance(result, Exception):
                    self.logger.warning("Batch scraping error", 
                                      url=url_data.get("url", ""), 
                                      error=str(result))
                    # Create fallback result with snippet content
                    fallback_result = SearchResult(
                        title=url_data.get("title", "Untitled"),
                        url=url_data.get("url", ""),
                        snippet=url_data.get("description", ""),
                        content=url_data.get("description", ""),
                        relevance_score=0.5,
                        authority_score=0.5,
                        content_quality=0.3,
                        source_type="firecrawl_fallback"
                    )
                    all_scraped_results[sub_question_id].append(fallback_result)
            
            self.logger.info(f"✅ Batch {(batch_start//batch_size)+1} completed", 
                           successful=successful_count,
                           total_attempted=len(batch),
                           batch_time=f"{batch_elapsed:.1f}s",
                           avg_per_url=f"{batch_elapsed/len(batch):.2f}s")
            
            # Small delay between batches to respect rate limits
            if batch_end < len(all_url_results):
                await asyncio.sleep(1.0)
        
        self.logger.info("🎉 ALL batched scraping completed", 
                       total_sub_questions=len(all_scraped_results),
                       total_results=sum(len(results) for results in all_scraped_results.values()))
        
        return all_scraped_results

    async def _scrape_single_url_enhanced(self, url_data: dict, scrape_url: str, headers: dict, 
                                        loop, index: int, total: int) -> SearchResult:
        """Enhanced single URL scraping with better error handling and metadata preservation"""
        url = url_data.get("url", "")
        title = url_data.get("title", "Untitled")
        description = url_data.get("description", "")
        
        self.logger.debug("Scraping URL (batched)", url=url, index=index, total=total)
        
        try:
            if not url:
                return None
            
            # Optimized scrape configuration
            from ..core.timeout_manager import get_scrape_timeout_seconds, get_scrape_timeout_ms
            timeout_seconds = get_scrape_timeout_seconds()
            
            scrape_data = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": getattr(self.settings, 'firecrawl_only_main_content', True),
                "timeout": get_scrape_timeout_ms(),
                "waitFor": 2000
            }
            
            # Single retry with timeout
            try:
                scrape_response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(scrape_url, headers=headers, json=scrape_data, timeout=timeout_seconds)
                )
                
                # Process successful response
                full_content = description  # fallback
                if scrape_response.status_code == 200:
                    try:
                        scrape_result = scrape_response.json()
                        if scrape_result.get('data', {}).get('markdown'):
                            full_content = scrape_result['data']['markdown']
                            
                            # Apply content limit
                            content_limit = getattr(self.settings, 'firecrawl_content_limit', 2500)
                            original_length = len(full_content)
                            if len(full_content) > content_limit:
                                full_content = full_content[:content_limit] + f"...\n\n[Content limited to first {content_limit:,} characters for efficiency. Original: {original_length:,} chars]"
                        
                        self.logger.debug("URL scraped successfully (batched)", 
                                       url=url, 
                                       content_length=len(full_content),
                                       index=index)
                    except Exception as json_error:
                        self.logger.warning("JSON parsing error during batched scraping", 
                                          url=url, 
                                          error=str(json_error),
                                          index=index)
                else:
                    self.logger.warning("Batched scraping failed", 
                                      url=url, 
                                      status_code=scrape_response.status_code,
                                      index=index)
                
            except Exception as e:
                self.logger.error("Batched scraping exception", 
                                url=url, 
                                error=str(e),
                                index=index)
                full_content = description  # fallback to snippet
            
            # Use quality assessor for content quality
            from ..core.quality_assessor import AssessmentRequest, AssessmentMode
            
            temp_result = SearchResult(
                url=url,
                title=title,
                snippet=description,
                content=full_content,
                relevance_score=0.0,
                source_type="firecrawl_batched"
            )
            
            quality_request = AssessmentRequest(
                results=[temp_result],
                sub_question=None,
                mode=AssessmentMode.ALGORITHMIC_FAST
            )
            
            try:
                if hasattr(self, 'quality_assessor'):
                    quality_metrics = self.quality_assessor._algorithmic_fast_assessment(quality_request)
                    content_quality = quality_metrics.content_quality
                else:
                    content_quality = 0.7  # Default for firecrawl
            except Exception:
                content_quality = 0.7
            
            # Create SearchResult with enhanced metadata
            return SearchResult(
                title=title,
                url=url,
                snippet=description,
                content=full_content,
                relevance_score=0.8,
                authority_score=0.7,
                content_quality=content_quality,
                source_type="firecrawl_batched"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to scrape URL in batch {url}: {str(e)}")
            return None

    async def _batch_scrape_fallback(self, all_url_results: List[dict], 
                                   resource_manager: ResourceManager) -> dict:
        """Fallback batch scraping for non-Firecrawl engines"""
        self.logger.info("Using fallback batch scraping (no Firecrawl)")
        
        all_scraped_results = {}
        
        # Group URLs by sub-question
        urls_by_question = {}
        for url_data in all_url_results:
            sub_question_id = url_data.get("sub_question_id")
            if sub_question_id not in urls_by_question:
                urls_by_question[sub_question_id] = []
            urls_by_question[sub_question_id].append(url_data)
        
        # Process each sub-question's URLs (since we don't have Firecrawl batching)
        for sub_question_id, url_list in urls_by_question.items():
            self.logger.info(f"Processing URLs for sub-question {sub_question_id}", url_count=len(url_list))
            
            # Create SearchResults with snippet content only (no scraping)
            results = []
            for url_data in url_list:
                result = SearchResult(
                    title=url_data.get("title", "Untitled"),
                    url=url_data.get("url", ""),
                    snippet=url_data.get("description", ""),
                    content=url_data.get("description", ""),  # Use description as content
                    relevance_score=0.6,
                    authority_score=0.5,
                    content_quality=0.4,
                    source_type="brave_snippet"
                )
                results.append(result)
            
            all_scraped_results[sub_question_id] = results
        
        return all_scraped_results