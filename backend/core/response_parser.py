"""
Core response parsing utilities for the research system.
Consolidates all the different JSON parsing patterns found throughout the codebase.
"""

import json
import re
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class ResponseParseError(Exception):
    """Raised when response parsing fails"""
    pass


class ResponseParser:
    """Unified response parser that handles all JSON parsing patterns"""
    
    @staticmethod
    def extract_json_from_response(response: str) -> str:
        """
        Extract JSON content from various response formats.
        Consolidates all parsing patterns found in the codebase.
        
        Handles:
        - Plain JSON
        - Markdown code blocks (```json...```)
        - Mixed text with JSON
        - Malformed JSON with common issues
        
        Returns: Clean JSON string ready for json.loads()
        Raises: ResponseParseError if JSON cannot be extracted
        """
        if not response or not response.strip():
            raise ResponseParseError("Empty response")
        
        response = response.strip()
        
        # Pattern 1: Check if response starts with { (plain JSON)
        if response.startswith('{') and response.endswith('}'):
            return response
            
        # Pattern 2: Extract from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
            
        # Pattern 3: Find JSON object in mixed content
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            potential_json = json_match.group(0)
            # Validate it's actually JSON
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                pass
        
        # Pattern 4: Clean up common JSON formatting issues
        cleaned = ResponseParser._clean_malformed_json(response)
        if cleaned:
            return cleaned
            
        raise ResponseParseError(f"No valid JSON found in response: {response[:200]}...")
    
    @staticmethod
    def parse_json_response(response: str) -> Dict[str, Any]:
        """
        Parse JSON response with unified error handling.
        
        Returns: Parsed dictionary
        Raises: ResponseParseError with detailed error info
        """
        try:
            json_content = ResponseParser.extract_json_from_response(response)
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.warning("JSON decode error", error=str(e), response_preview=response[:200])
            raise ResponseParseError(f"JSON decode failed: {str(e)}")
        except Exception as e:
            logger.error("Unexpected parsing error", error=str(e), response_preview=response[:200])
            raise ResponseParseError(f"Parsing failed: {str(e)}")
    
    @staticmethod
    def parse_with_fallback(response: str, fallback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON response with guaranteed fallback.
        
        Returns: Parsed dict on success, fallback_data on failure
        """
        try:
            return ResponseParser.parse_json_response(response)
        except ResponseParseError as e:
            logger.warning("Using fallback data due to parse error", error=str(e))
            return fallback_data
    
    @staticmethod
    def _clean_malformed_json(response: str) -> Optional[str]:
        """Clean up common JSON formatting issues"""
        # Remove common prefixes/suffixes
        response = re.sub(r'^.*?(?=\{)', '', response, flags=re.DOTALL)
        response = re.sub(r'\}.*?$', '}', response, flags=re.DOTALL)
        
        # Fix common escape issues
        response = response.replace('\\"', '"')
        response = response.replace('\\n', '\n')
        
        # Try to validate cleaned JSON
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError:
            return None


# Backward compatibility function
def extract_json_from_response(response: str) -> str:
    """
    Legacy function for backward compatibility.
    Use ResponseParser.extract_json_from_response() for new code.
    """
    return ResponseParser.extract_json_from_response(response) 