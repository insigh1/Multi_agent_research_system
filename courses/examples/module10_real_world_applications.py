#!/usr/bin/env python3
"""
🌍 Module 10: Real-World Applications & Case Studies
==================================================

This module demonstrates practical applications of multi-agent research systems
in real-world scenarios including academic research, market analysis, and 
competitive intelligence.

Key Learning Objectives:
1. Academic research automation
2. Market research and trend analysis  
3. Competitive intelligence gathering
4. Multi-layered content analysis
5. Database integration and persistence
6. Report generation and export
7. Production-ready system design
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import csv
import sqlite3
from pathlib import Path

# External dependencies
import aiohttp
import structlog
from asyncio_throttle import Throttler

# Configure logging
logger = structlog.get_logger()

class ResearchType(Enum):
    ACADEMIC = "academic"
    MARKET = "market"
    COMPETITIVE = "competitive"
    TREND = "trend"
    TECHNICAL = "technical"

class ContentType(Enum):
    ARTICLE = "article"
    RESEARCH_PAPER = "research_paper"
    NEWS = "news"
    BLOG_POST = "blog_post"
    SOCIAL_MEDIA = "social_media"

@dataclass
class ResearchQuery:
    topic: str
    research_type: ResearchType
    depth_level: str  # "shallow", "medium", "deep"
    max_sources: int = 10
    time_range: str = "1y"  # 1d, 1w, 1m, 1y
    filters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContentItem:
    title: str
    content: str
    source: str
    url: str
    content_type: ContentType
    timestamp: datetime
    relevance_score: float = 0.0
    sentiment_score: float = 0.0
    key_topics: List[str] = field(default_factory=list)

@dataclass
class ResearchReport:
    query: ResearchQuery
    content_items: List[ContentItem]
    summary: str
    key_insights: List[str]
    trends: List[str]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

class ResearchAutomationAgent:
    """Agent specialized for automated research tasks"""
    
    def __init__(self, api_key: str, model: str = "accounts/fireworks/models/llama-v3p3-70b-instruct"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.session = None
        self.throttler = Throttler(rate_limit=10, period=1.0)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def generate_research_plan(self, query: ResearchQuery) -> Dict[str, Any]:
        """Generate a comprehensive research plan"""
        prompt = f"""
        Create a detailed research plan for the following query:
        
        Topic: {query.topic}
        Research Type: {query.research_type.value}
        Depth Level: {query.depth_level}
        Max Sources: {query.max_sources}
        Time Range: {query.time_range}
        
        Generate a research plan with:
        1. Key research questions to answer
        2. Primary sources to investigate
        3. Secondary sources for validation
        4. Specific search strategies
        5. Expected deliverables
        6. Timeline estimates
        
        Format as structured JSON.
        """
        
        return await self._make_api_call(prompt, "research_planning")
        
    async def analyze_content_relevance(self, content: str, topic: str) -> float:
        """Analyze how relevant content is to the research topic"""
        prompt = f"""
        Analyze the relevance of the following content to the topic "{topic}".
        
        Content: {content[:2000]}...
        
        Rate the relevance on a scale of 0.0 to 1.0 where:
        - 1.0 = Highly relevant, directly addresses the topic
        - 0.8 = Very relevant, addresses most aspects of the topic
        - 0.6 = Moderately relevant, addresses some aspects
        - 0.4 = Somewhat relevant, tangentially related
        - 0.2 = Minimally relevant, barely related
        - 0.0 = Not relevant, unrelated to the topic
        
        Respond with just the numerical score (e.g., 0.8).
        """
        
        result = await self._make_api_call(prompt, "relevance_analysis")
        
        try:
            # Extract numerical score from response
            score_text = result.get("content", "0.0").strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))  # Clamp between 0 and 1
        except ValueError:
            logger.warning("Failed to parse relevance score", response=result.get("content"))
            return 0.5  # Default to medium relevance
            
    async def extract_key_insights(self, content_items: List[ContentItem], topic: str) -> List[str]:
        """Extract key insights from multiple content items"""
        # Combine content for analysis
        combined_content = "\n\n".join([
            f"Source {i+1}: {item.title}\n{item.content[:1000]}..."
            for i, item in enumerate(content_items[:5])  # Limit to first 5 items
        ])
        
        prompt = f"""
        Analyze the following research content about "{topic}" and extract 5-7 key insights.
        
        Content:
        {combined_content}
        
        Extract insights that are:
        1. Factual and well-supported
        2. Actionable or decision-relevant
        3. Non-obvious or surprising
        4. Trend-indicating
        5. Strategically important
        
        Format as a numbered list of insights.
        """
        
        result = await self._make_api_call(prompt, "insight_extraction")
        
        # Parse insights from response
        content = result.get("content", "")
        insights = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up the insight text
                insight = line.split('.', 1)[-1].strip() if '.' in line else line
                insight = insight.lstrip('•-').strip()
                if insight:
                    insights.append(insight)
                    
        return insights[:7]  # Limit to 7 insights
        
    async def generate_summary(self, content_items: List[ContentItem], query: ResearchQuery) -> str:
        """Generate a comprehensive summary of research findings"""
        # Select top relevant content
        top_content = sorted(content_items, key=lambda x: x.relevance_score, reverse=True)[:10]
        
        content_summaries = []
        for item in top_content:
            content_summaries.append(f"- {item.title} (Score: {item.relevance_score:.2f})\n  {item.content[:300]}...")
            
        combined_summaries = "\n\n".join(content_summaries)
        
        prompt = f"""
        Create a comprehensive research summary based on the following information:
        
        Research Topic: {query.topic}
        Research Type: {query.research_type.value}
        Depth Level: {query.depth_level}
        
        Content Summaries:
        {combined_summaries}
        
        Generate a well-structured summary that includes:
        1. Executive overview
        2. Key findings
        3. Current state of the topic
        4. Emerging trends
        5. Gaps or limitations in current knowledge
        
        Keep it concise but comprehensive (500-800 words).
        """
        
        result = await self._make_api_call(prompt, "summary_generation")
        return result.get("content", "Summary generation failed")
        
    async def _make_api_call(self, prompt: str, operation: str) -> Dict[str, Any]:
        """Make API call with error handling"""
        async with self.throttler:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.3
            }
            
            try:
                async with self.session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        return {
                            "content": content,
                            "tokens_used": data["usage"]["total_tokens"],
                            "success": True,
                            "operation": operation
                        }
                    else:
                        error_text = await response.text()
                        logger.error("API call failed", operation=operation, status=response.status, error=error_text)
                        return {
                            "error": error_text,
                            "success": False,
                            "operation": operation
                        }
                        
            except Exception as e:
                logger.error("API call exception", operation=operation, error=str(e))
                return {
                    "error": str(e),
                    "success": False,
                    "operation": operation
                }

class ContentAnalysisAgent:
    """Agent specialized for content analysis and sentiment analysis"""
    
    def __init__(self, api_key: str, model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.session = None
        self.throttler = Throttler(rate_limit=15, period=1.0)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text content"""
        prompt = f"""
        Analyze the sentiment of the following text on a scale from -1.0 to 1.0:
        - 1.0 = Very positive sentiment
        - 0.5 = Somewhat positive
        - 0.0 = Neutral sentiment
        - -0.5 = Somewhat negative
        - -1.0 = Very negative sentiment
        
        Text: {text[:1500]}
        
        Respond with just the numerical score (e.g., 0.3).
        """
        
        result = await self._make_api_call(prompt, "sentiment_analysis")
        
        try:
            score_text = result.get("content", "0.0").strip()
            score = float(score_text)
            return max(-1.0, min(1.0, score))  # Clamp between -1 and 1
        except ValueError:
            return 0.0  # Default to neutral
            
    async def extract_key_topics(self, text: str, max_topics: int = 5) -> List[str]:
        """Extract key topics from text content"""
        prompt = f"""
        Extract the {max_topics} most important topics/themes from the following text.
        
        Text: {text[:2000]}
        
        Return only the topics as a comma-separated list (e.g., "artificial intelligence, machine learning, automation").
        """
        
        result = await self._make_api_call(prompt, "topic_extraction")
        
        content = result.get("content", "")
        topics = [topic.strip() for topic in content.split(",") if topic.strip()]
        return topics[:max_topics]
        
    async def categorize_content(self, title: str, content: str) -> ContentType:
        """Categorize content into predefined types"""
        prompt = f"""
        Categorize the following content into one of these types:
        - article: General news or magazine articles
        - research_paper: Academic or scientific papers
        - news: Breaking news or news reports
        - blog_post: Blog posts or opinion pieces
        - social_media: Social media posts or comments
        
        Title: {title}
        Content: {content[:500]}...
        
        Respond with just the category name.
        """
        
        result = await self._make_api_call(prompt, "content_categorization")
        
        category = result.get("content", "article").strip().lower()
        
        # Map response to enum
        category_mapping = {
            "article": ContentType.ARTICLE,
            "research_paper": ContentType.RESEARCH_PAPER,
            "news": ContentType.NEWS,
            "blog_post": ContentType.BLOG_POST,
            "social_media": ContentType.SOCIAL_MEDIA
        }
        
        return category_mapping.get(category, ContentType.ARTICLE)
        
    async def _make_api_call(self, prompt: str, operation: str) -> Dict[str, Any]:
        """Make API call with error handling"""
        async with self.throttler:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.1
            }
            
            try:
                async with self.session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        return {
                            "content": content,
                            "tokens_used": data["usage"]["total_tokens"],
                            "success": True,
                            "operation": operation
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "error": error_text,
                            "success": False,
                            "operation": operation
                        }
                        
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False,
                    "operation": operation
                }

class MultiAgentResearchSystem:
    """Complete multi-agent system for real-world research applications"""
    
    def __init__(self, api_key: str):
        """Initialize multi-agent research system"""
        self.api_key = api_key
        self.db_path = Path("temp_research_system.db")  # Use safer temp database
        self.research_agent = None
        self.content_agent = None
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for storing research data"""
        conn = sqlite3.connect(str(self.db_path))  # Convert Path to string
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                research_type TEXT NOT NULL,
                depth_level TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT,
                content_type TEXT,
                relevance_score REAL,
                sentiment_score REAL,
                key_topics TEXT,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (query_id) REFERENCES research_queries (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER,
                summary TEXT NOT NULL,
                key_insights TEXT,
                trends TEXT,
                recommendations TEXT,
                generated_at DATETIME NOT NULL,
                FOREIGN KEY (query_id) REFERENCES research_queries (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
    async def initialize(self):
        """Initialize all agents"""
        self.research_agent = ResearchAutomationAgent(self.api_key)
        self.content_agent = ContentAnalysisAgent(self.api_key)
        
        await self.research_agent.__aenter__()
        await self.content_agent.__aenter__()
        
    async def cleanup(self):
        """Cleanup all agents"""
        if self.research_agent:
            await self.research_agent.__aexit__(None, None, None)
        if self.content_agent:
            await self.content_agent.__aexit__(None, None, None)
            
    async def conduct_research(self, query: ResearchQuery) -> ResearchReport:
        """Conduct comprehensive research using multiple agents"""
        logger.info("Starting research", topic=query.topic, type=query.research_type.value)
        
        # Store query in database
        query_id = self._store_query(query)
        
        # Generate research plan
        plan_result = await self.research_agent.generate_research_plan(query)
        logger.info("Research plan generated", success=plan_result.get("success", False))
        
        # Simulate content gathering (in real implementation, this would use web scraping or APIs)
        content_items = await self._simulate_content_gathering(query)
        
        # Analyze content with content agent
        analyzed_content = []
        for item in content_items:
            # Analyze relevance
            item.relevance_score = await self.research_agent.analyze_content_relevance(
                item.content, query.topic
            )
            
            # Analyze sentiment
            item.sentiment_score = await self.content_agent.analyze_sentiment(item.content)
            
            # Extract key topics
            item.key_topics = await self.content_agent.extract_key_topics(item.content)
            
            # Categorize content
            item.content_type = await self.content_agent.categorize_content(
                item.title, item.content
            )
            
            analyzed_content.append(item)
            
            # Store in database
            self._store_content_item(query_id, item)
            
        # Generate insights and summary
        key_insights = await self.research_agent.extract_key_insights(analyzed_content, query.topic)
        summary = await self.research_agent.generate_summary(analyzed_content, query)
        
        # Create research report
        report = ResearchReport(
            query=query,
            content_items=analyzed_content,
            summary=summary,
            key_insights=key_insights,
            trends=self._extract_trends(analyzed_content),
            recommendations=self._generate_recommendations(analyzed_content, key_insights)
        )
        
        # Store report in database
        self._store_report(query_id, report)
        
        logger.info("Research completed", 
                   content_items=len(analyzed_content),
                   insights=len(key_insights))
        
        return report
        
    async def _simulate_content_gathering(self, query: ResearchQuery) -> List[ContentItem]:
        """Simulate content gathering (in real implementation, use web scraping/APIs)"""
        # This is a simulation - in a real system, you would integrate with:
        # - Web scraping services
        # - News APIs
        # - Academic databases
        # - Social media APIs
        # - Company databases
        
        sample_content = [
            ContentItem(
                title=f"Understanding {query.topic}: A Comprehensive Overview",
                content=f"""This article provides a detailed analysis of {query.topic}. 
                The field has evolved significantly over recent years, with major developments 
                in technology and methodology. Current trends indicate growing interest and 
                investment in this area. Key players are focusing on innovation and 
                practical applications. The market shows strong growth potential with 
                increasing adoption across various industries. Recent studies highlight 
                both opportunities and challenges in implementation.""",
                source="Industry Weekly",
                url="https://example.com/article1",
                content_type=ContentType.ARTICLE,
                timestamp=datetime.now() - timedelta(days=5),
                relevance_score=0.0,
                sentiment_score=0.0,
                key_topics=[]  # Initialize empty list
            ),
            ContentItem(
                title=f"Recent Advances in {query.topic} Research",
                content=f"""Latest research findings reveal significant progress in {query.topic}. 
                Researchers have identified new methodologies and approaches that show promise 
                for future applications. The study involved comprehensive analysis and testing, 
                demonstrating improved efficiency and effectiveness. Preliminary results 
                suggest potential for widespread adoption. Further research is needed to 
                validate findings and explore additional applications. The research community 
                is optimistic about future developments.""",
                source="Research Journal",
                url="https://example.com/paper1",
                content_type=ContentType.RESEARCH_PAPER,
                timestamp=datetime.now() - timedelta(days=10),
                relevance_score=0.0,
                sentiment_score=0.0,
                key_topics=[]  # Initialize empty list
            ),
            ContentItem(
                title=f"Breaking: Major Development in {query.topic}",
                content=f"""A significant breakthrough in {query.topic} was announced today. 
                Industry leaders report successful implementation of new technologies that 
                could revolutionize the field. The development addresses long-standing 
                challenges and opens new possibilities for growth. Market analysts predict 
                substantial impact on industry dynamics. Companies are already expressing 
                interest in adopting these innovations. This development represents a 
                milestone in the evolution of {query.topic}.""",
                source="Tech News Daily",
                url="https://example.com/news1",
                content_type=ContentType.NEWS,
                timestamp=datetime.now() - timedelta(days=2),
                relevance_score=0.0,
                sentiment_score=0.0,
                key_topics=[]  # Initialize empty list
            )
        ]
        
        return sample_content
        
    def _extract_trends(self, content_items: List[ContentItem]) -> List[str]:
        """Extract trends from content analysis"""
        if not content_items:  # Handle empty content items
            return ["No content available for trend analysis"]
            
        # Analyze sentiment trends
        positive_content = [item for item in content_items if item.sentiment_score > 0.2]
        
        # Analyze topic frequency
        all_topics = []
        for item in content_items:
            all_topics.extend(item.key_topics)
            
        # Count topic frequency
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
        # Generate trend insights
        trends = []
        
        if len(positive_content) / len(content_items) > 0.6:
            trends.append("Overall positive sentiment trend in recent content")
            
        # Top trending topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        if sorted_topics:
            trends.append(f"Trending topics: {', '.join([topic for topic, count in sorted_topics[:3]])}")
            
        return trends if trends else ["No clear trends identified in current content"]
        
    def _generate_recommendations(self, content_items: List[ContentItem], insights: List[str]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Analyze content relevance distribution
        high_relevance = [item for item in content_items if item.relevance_score > 0.7]
        
        if len(high_relevance) < len(content_items) * 0.5:
            recommendations.append("Consider expanding search criteria to find more relevant content")
            
        # Analyze content diversity
        content_types = set(item.content_type for item in content_items)
        if len(content_types) < 3:
            recommendations.append("Diversify content sources to include more content types")
            
        # Based on insights
        if len(insights) > 5:
            recommendations.append("Focus on top 3-5 insights for immediate action planning")
            
        # Default recommendations
        recommendations.extend([
            "Monitor trends regularly for emerging developments",
            "Validate findings with additional primary sources",
            "Consider stakeholder perspectives in decision making"
        ])
        
        return recommendations
        
    def _store_query(self, query: ResearchQuery) -> int:
        """Store research query in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO research_queries (topic, research_type, depth_level, created_at)
            VALUES (?, ?, ?, ?)
        """, (query.topic, query.research_type.value, query.depth_level, datetime.now()))
        
        query_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return query_id
        
    def _store_content_item(self, query_id: int, item: ContentItem):
        """Store content item in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO content_items 
                (query_id, title, content, source, url, content_type, relevance_score, 
                 sentiment_score, key_topics, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_id, item.title, item.content, item.source, item.url,
                item.content_type.value, item.relevance_score, item.sentiment_score,
                ",".join(item.key_topics) if item.key_topics else "",  # Handle empty key_topics
                item.timestamp
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to store content item", error=str(e), title=item.title[:50])
        
    def _store_report(self, query_id: int, report: ResearchReport):
        """Store research report in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO research_reports 
            (query_id, summary, key_insights, trends, recommendations, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            query_id, report.summary,
            "\n".join(report.key_insights),
            "\n".join(report.trends),
            "\n".join(report.recommendations),
            report.generated_at
        ))
        
        conn.commit()
        conn.close()
        
    def export_report_to_csv(self, report: ResearchReport, filename: str):
        """Export research report to CSV format"""
        Path("reports").mkdir(exist_ok=True)
        filepath = Path("reports") / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header information
            writer.writerow(["Research Report"])
            writer.writerow(["Topic", report.query.topic])
            writer.writerow(["Research Type", report.query.research_type.value])
            writer.writerow(["Generated At", report.generated_at.strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow([])
            
            # Write summary
            writer.writerow(["Summary"])
            writer.writerow([report.summary])
            writer.writerow([])
            
            # Write insights
            writer.writerow(["Key Insights"])
            for insight in report.key_insights:
                writer.writerow([insight])
            writer.writerow([])
            
            # Write content items
            writer.writerow(["Content Analysis"])
            writer.writerow(["Title", "Source", "Content Type", "Relevance Score", "Sentiment Score", "Key Topics"])
            
            for item in report.content_items:
                writer.writerow([
                    item.title,
                    item.source,
                    item.content_type.value,
                    f"{item.relevance_score:.2f}",
                    f"{item.sentiment_score:.2f}",
                    "; ".join(item.key_topics)
                ])
                
        logger.info("Report exported to CSV", filepath=str(filepath))

async def demonstrate_use_cases():
    """Demonstrate various real-world use cases"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        return
        
    print("🌍 Real-World Applications & Case Studies Demo")
    print("=" * 60)
    print("Demonstrating practical multi-agent research applications...")
    print()
    
    # Initialize the multi-agent research system
    system = MultiAgentResearchSystem(api_key)
    await system.initialize()
    
    try:
        # Use Case 1: Academic Research
        print("📚 Use Case 1: Academic Research Automation")
        print("-" * 45)
        
        academic_query = ResearchQuery(
            topic="artificial intelligence in healthcare",
            research_type=ResearchType.ACADEMIC,
            depth_level="deep",
            max_sources=5,
            time_range="1y"
        )
        
        start_time = time.time()
        academic_report = await system.conduct_research(academic_query)
        duration = time.time() - start_time
        
        print(f"✅ Research completed in {duration:.1f} seconds")
        print(f"📄 Content items analyzed: {len(academic_report.content_items)}")
        print(f"💡 Key insights generated: {len(academic_report.key_insights)}")
        print(f"📈 Trends identified: {len(academic_report.trends)}")
        print()
        
        # Display sample insights
        print("🔍 Sample Key Insights:")
        for i, insight in enumerate(academic_report.key_insights[:3], 1):
            print(f"  {i}. {insight}")
        print()
        
        # Use Case 2: Market Research
        print("💼 Use Case 2: Market Research Analysis")
        print("-" * 40)
        
        market_query = ResearchQuery(
            topic="electric vehicle market trends",
            research_type=ResearchType.MARKET,
            depth_level="medium",
            max_sources=8,
            time_range="6m"
        )
        
        start_time = time.time()
        market_report = await system.conduct_research(market_query)
        duration = time.time() - start_time
        
        print(f"✅ Market analysis completed in {duration:.1f} seconds")
        print(f"📊 Market insights: {len(market_report.key_insights)}")
        print(f"🎯 Recommendations: {len(market_report.recommendations)}")
        print()
        
        # Display content analysis
        print("📈 Content Analysis Results:")
        for item in market_report.content_items[:3]:
            print(f"  • {item.title[:50]}... (Relevance: {item.relevance_score:.2f})")
        print()
        
        # Use Case 3: Competitive Intelligence
        print("🏢 Use Case 3: Competitive Intelligence")
        print("-" * 40)
        
        competitive_query = ResearchQuery(
            topic="cloud computing platforms comparison",
            research_type=ResearchType.COMPETITIVE,
            depth_level="deep",
            max_sources=10,
            time_range="3m"
        )
        
        start_time = time.time()
        competitive_report = await system.conduct_research(competitive_query)
        duration = time.time() - start_time
        
        print(f"✅ Competitive analysis completed in {duration:.1f} seconds")
        print(f"🔍 Competitive insights: {len(competitive_report.key_insights)}")
        print()
        
        # Display trends
        print("📊 Identified Trends:")
        for trend in competitive_report.trends:
            print(f"  • {trend}")
        print()
        
        # Export reports
        print("📁 Exporting Reports...")
        system.export_report_to_csv(academic_report, "academic_research_report.csv")
        system.export_report_to_csv(market_report, "market_research_report.csv")
        system.export_report_to_csv(competitive_report, "competitive_analysis_report.csv")
        print("✅ Reports exported to reports/ directory")
        print()
        
        # Performance Summary
        print("📊 Performance Summary")
        print("-" * 25)
        
        all_reports = [academic_report, market_report, competitive_report]
        total_content = sum(len(report.content_items) for report in all_reports)
        total_insights = sum(len(report.key_insights) for report in all_reports)
        
        # Calculate average sentiment and relevance
        all_items = []
        for report in all_reports:
            all_items.extend(report.content_items)
            
        avg_relevance = sum(item.relevance_score for item in all_items) / len(all_items)
        avg_sentiment = sum(item.sentiment_score for item in all_items) / len(all_items)
        
        print(f"Total Content Items Processed: {total_content}")
        print(f"Total Insights Generated: {total_insights}")
        print(f"Average Relevance Score: {avg_relevance:.2f}")
        print(f"Average Sentiment Score: {avg_sentiment:.2f}")
        print(f"Research Types Covered: {len(set(report.query.research_type for report in all_reports))}")
        
        # Content type distribution
        content_types = {}
        for item in all_items:
            content_types[item.content_type.value] = content_types.get(item.content_type.value, 0) + 1
            
        print("\n📋 Content Type Distribution:")
        for content_type, count in content_types.items():
            percentage = (count / len(all_items)) * 100
            print(f"  {content_type}: {count} ({percentage:.1f}%)")
            
    finally:
        await system.cleanup()
        
    print("\n🎉 Real-World Applications Demo Complete!")
    print("Key Features Demonstrated:")
    print("• Automated academic research with AI agents")
    print("• Market research and trend analysis")
    print("• Competitive intelligence gathering")
    print("• Multi-layered content analysis (relevance, sentiment, topics)")
    print("• Comprehensive report generation and export")
    print("• Database integration for research persistence")
    print("• Scalable multi-agent coordination")
    print("• Production-ready error handling and logging")

if __name__ == "__main__":
    asyncio.run(demonstrate_use_cases()) 