"""
Tools for interacting with Azure AI Search.

This module provides tools for:
1. PowerPoint Report Discovery: Finding up to 100 relevant PowerPoint reports based on a query
2. Specific PowerPoint Report Retrieval: Getting up to 750 chunks/slides of content from a specific PowerPoint report
"""

import os
import requests
from typing import List, Dict, Any, Optional
from agents import function_tool

class Config:
    """Configuration settings for Azure AI Search."""
    API_KEY = os.environ.get("AZURE_SEARCH_KEY")
    ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
    INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME")
    API_VERSION = "2024-07-01"
    VECTOR_FIELD = "embedding"
    SELECT_FIELDS = "embeddingContent, embeddingContext, fileName, webUrl, slideNumber, fileExtension"
    POWERPOINT_TYPE = ".pptx"

    @classmethod
    def get_base_url(cls) -> str:
        """Get the base URL for Azure AI Search API."""
        return f"https://{cls.ENDPOINT}/indexes/{cls.INDEX_NAME}/docs/search?api-version={cls.API_VERSION}"

def create_azure_search_tools() -> List[function_tool]:
    """Create the Azure AI Search tool functions for PowerPoint reports only."""
    
    @function_tool
    async def discover_powerpoint_reports(query: str) -> List[Dict[str, str]]:
        """Discover up to 750 relevant PowerPoint reports based on a query.
        
        Args:
            query: The search query
            
        Returns:
            List of dictionaries containing file_name and web_url for each discovered PowerPoint report (up to 750)
        """
        try:
            if not all([Config.ENDPOINT, Config.API_KEY, Config.INDEX_NAME]):
                raise ValueError("Azure AI Search configuration is incomplete. Please set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY, and AZURE_SEARCH_INDEX_NAME environment variables.")
            
            headers = {
                "Content-Type": "application/json",
                "api-key": Config.API_KEY
            }
            
            payload = {
                "search": query,
                "select": "fileName,webUrl",
                "searchFields": "fileName",
                "filter": f"fileExtension eq '{Config.POWERPOINT_TYPE}'",
                "top": 750
            }
            
            response = requests.post(
                Config.get_base_url(),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            results = response.json()
            
            # Deduplicate by file name
            unique_files = {}
            for result in results.get("value", []):
                file_name = result.get("fileName")
                web_url = result.get("webUrl", "")
                if file_name and file_name not in unique_files:
                    unique_files[file_name] = web_url
            
            # Sort alphabetically by file name
            formatted_results = [
                {"file_name": name, "web_url": url}
                for name, url in sorted(unique_files.items())
            ]
            return formatted_results
        except Exception as e:
            return [{"error": str(e)}]

    @function_tool
    async def retrieve_powerpoint_report(file_name: str, query: str) -> Dict[str, Any]:
        """Retrieve up to 1000 chunks/slides of content from a specific PowerPoint report.
        
        Args:
            file_name: The exact name of the PowerPoint report to retrieve
            query: The search query to find relevant content within the report
            
        Returns:
            Dictionary containing the report content and metadata (up to 1000 chunks/slides)
        """
        try:
            if not all([Config.ENDPOINT, Config.API_KEY, Config.INDEX_NAME]):
                raise ValueError("Azure AI Search configuration is incomplete. Please set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY, and AZURE_SEARCH_INDEX_NAME environment variables.")
            
            headers = {
                "Content-Type": "application/json",
                "api-key": Config.API_KEY
            }
            
            payload = {
                "search": query,
                "vectorQueries": [{
                    "text": query,
                    "kind": "text",
                    "fields": Config.VECTOR_FIELD,
                    "k": 1000
                }],
                "select": Config.SELECT_FIELDS,
                "filter": f"fileName eq '{file_name}' and fileExtension eq '{Config.POWERPOINT_TYPE}'",
                "top": 1000,
                "queryType": "semantic",
                "semanticConfiguration": "default-semantic-config"
            }
            
            response = requests.post(
                Config.get_base_url(),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            results = response.json()
            
            # Deduplicate by slide number, prefer embeddingContext, sort numerically with 'Unknown' last
            unique_slides = {}
            for result in results.get("value", []):
                slide_num_raw = result.get("slideNumber")
                slide_num = str(slide_num_raw) if slide_num_raw is not None and str(slide_num_raw).strip() else "Unknown"
                if slide_num not in unique_slides:
                    content = result.get("embeddingContext", result.get("embeddingContent", ""))
                    if content:
                        unique_slides[slide_num] = {
                            "slide_number": slide_num,
                            "content": content
                        }
            # Sort slides numerically, 'Unknown' last
            def sort_key(slide):
                sn = slide["slide_number"]
                try:
                    return (0, int(sn))
                except (ValueError, TypeError):
                    return (1, sn)
            slides = sorted(unique_slides.values(), key=sort_key)
            return {
                "file_name": file_name,
                "web_url": next((r.get("webUrl", "") for r in results.get("value", [])), ""),
                "slides": slides
            }
        except Exception as e:
            return {"error": str(e)}

    return [discover_powerpoint_reports, retrieve_powerpoint_report] 