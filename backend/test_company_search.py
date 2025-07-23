import asyncio
import json
from .enhanced_research_system import (
    WebSearchRetrieverAgent, QualityEvaluationAgent, 
    ResourceManager, SubQuestion, Settings
)
from .utils import CacheManager, SecurityManager
import structlog

async def test_company_search():
    """Test company search functionality in detail"""
    
    # Setup
    settings = Settings()
    cache_manager = CacheManager(settings)
    security_manager = SecurityManager(settings.encryption_key)
    
    quality_agent = QualityEvaluationAgent(settings, cache_manager, security_manager)
    retriever = WebSearchRetrieverAgent(settings, cache_manager, security_manager, quality_agent)
    
    query = "Apple Inc company information"
    
    print(f"🔍 Testing company search for: {query}")
    
    async with ResourceManager(settings) as resource_manager:
        
        # Test 1: AI company detection
        print(f"\n1️⃣ Testing AI company detection...")
        company_info = await retriever._detect_company_query(query, resource_manager)
        print(f"Company detected: {company_info}")
        
        # Test 2: Domain guessing for detected companies
        if company_info.get('detected_companies'):
            company_name = company_info['detected_companies'][0]
            print(f"\n2️⃣ Testing AI domain guessing for: {company_name}")
            domains = await retriever._guess_company_domains(company_name, resource_manager)
            print(f"Predicted domains: {domains}")
        
        # Test 3: Enhanced search query generation
        print(f"\n3️⃣ Testing enhanced search query generation...")
        enhanced_queries = await retriever._create_enhanced_search_queries_from_query(query, company_info, resource_manager)
        print(f"Enhanced queries ({len(enhanced_queries)}):")
        for i, q in enumerate(enhanced_queries, 1):
            print(f"  {i}. {q}")
        
        # Test 4: Individual search queries
        print(f"\n4️⃣ Testing individual search queries...")
        
        for i, search_query in enumerate(enhanced_queries[:6], 1):
            print(f"\n--- Query {i}: {search_query} ---")
            
            # Get raw search results
            raw_results = await retriever._brave_search(search_query, 5, resource_manager)
            print(f"Results found: {len(raw_results)}")
            
            # Score results with company priority
            scored_results = retriever._score_relevance_with_company_priority(raw_results, query, company_info)
            
            # Check for apple.com results
            apple_results = [r for r in scored_results if 'apple.com' in r.url.lower()]
            if apple_results:
                print(f"✅ Found {len(apple_results)} apple.com result(s):")
                for apple_result in apple_results:
                    print(f"  • {apple_result.title} ({apple_result.url}) - Relevance: {apple_result.relevance_score:.3f}")
            else:
                print(f"❌ No apple.com results found")
            
            # Show top 3 results with scoring breakdown
            print("Top 3 results:")
            for j, result in enumerate(scored_results[:3], 1):
                # Calculate detailed scoring breakdown
                search_terms = query.lower().split()
                base_score = retriever._calculate_url_relevance_score(result.url, result.title, query, search_terms)
                company_boost = retriever._calculate_company_domain_boost(result.url, result.title, company_info)
                final_score = min(1.0, base_score + company_boost)
                
                print(f"  {j}. {result.title} ({result.url})")
                print(f"     Base: {base_score:.3f} + Company: {company_boost:.3f} = Final: {final_score:.3f}")
        
        # Test 5: Direct site:apple.com search
        print(f"\n5️⃣ Testing direct site:apple.com search...")
        direct_results = await retriever._brave_search("site:apple.com company information", 5, resource_manager)
        scored_direct = retriever._score_relevance_with_company_priority(direct_results, query, company_info)
        
        print(f"Direct site search results: {len(scored_direct)}")
        for result in scored_direct:
            # Calculate detailed scoring breakdown
            search_terms = query.lower().split()
            base_score = retriever._calculate_url_relevance_score(result.url, result.title, query, search_terms)
            company_boost = retriever._calculate_company_domain_boost(result.url, result.title, company_info)
            final_score = min(1.0, base_score + company_boost)
            
            print(f"  • {result.title} ({result.url})")
            print(f"    Base: {base_score:.3f} + Company: {company_boost:.3f} = Final: {final_score:.3f}")

if __name__ == "__main__":
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    asyncio.run(test_company_search()) 