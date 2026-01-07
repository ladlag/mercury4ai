import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, date
from pathlib import Path
import json
import httpx
from urllib.parse import urlparse
import uuid

logger = logging.getLogger(__name__)


def extract_markdown_string(markdown_result):
    """
    Extract markdown string from crawl4ai result.
    
    In crawl4ai 0.7.8+, result.markdown can be either:
    - A string (simple markdown text)
    - A MarkdownGenerationResult object with raw_markdown and fit_markdown properties
    
    Args:
        markdown_result: The markdown field from crawl4ai result
    
    Returns:
        String containing the markdown content, or None if not available
    """
    if markdown_result is None:
        return None
    
    # If it's already a string, return it
    if isinstance(markdown_result, str):
        return markdown_result
    
    # If it's a MarkdownGenerationResult object, extract the markdown
    # Prefer raw_markdown for full content, fall back to fit_markdown
    if hasattr(markdown_result, 'raw_markdown'):
        return markdown_result.raw_markdown
    elif hasattr(markdown_result, 'fit_markdown'):
        return markdown_result.fit_markdown
    elif hasattr(markdown_result, 'markdown_with_citations'):
        return markdown_result.markdown_with_citations
    
    # Last resort: try to convert to string
    try:
        return str(markdown_result)
    except Exception:
        logger.warning(f"Unable to extract markdown from result type: {type(markdown_result)}")
        return None


# Provider configurations for Chinese LLM providers
CHINESE_LLM_PROVIDERS = {
    'qwen': {
        'model_prefix': 'openai/',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    },
    'ernie': {
        'model_prefix': 'openai/',
        'base_url': 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat',
    },
    'deepseek': {
        'model_prefix': 'deepseek/',
        'base_url': None,  # Uses default Deepseek endpoint
    },
}


class CrawlerService:
    def __init__(self):
        self.crawler = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self.crawler = await AsyncWebCrawler().__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    async def crawl_url(
        self,
        url: str,
        crawl_config: Dict[str, Any],
        llm_config: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crawl a single URL with crawl4ai
        
        Args:
            url: URL to crawl
            crawl_config: General crawl4ai configuration
            llm_config: LLM provider configuration
            prompt_template: Prompt for LLM extraction
            output_schema: JSON schema for structured output
        
        Returns:
            Dictionary with crawl results
        """
        try:
            # Prepare crawl parameters
            crawl_params = {
                'url': url,
                'cache_mode': CacheMode.BYPASS,
            }
            
            # Add optional parameters
            # Note: verbose parameter removed to avoid conflict with crawl4ai 0.7.8
            if crawl_config.get('js_code'):
                crawl_params['js_code'] = crawl_config['js_code']
            if crawl_config.get('wait_for'):
                crawl_params['wait_for'] = crawl_config['wait_for']
            if crawl_config.get('css_selector'):
                crawl_params['css_selector'] = crawl_config['css_selector']
            if crawl_config.get('screenshot'):
                crawl_params['screenshot'] = True
            if crawl_config.get('pdf'):
                crawl_params['pdf'] = True
            
            # Configure LLM extraction if provided
            if llm_config and prompt_template:
                provider = llm_config.get('provider', 'openai')
                model = llm_config.get('model', 'gpt-4')
                params = llm_config.get('params', {})
                
                # Extract API key from params (it's stored in task.llm_params)
                api_key = params.get('api_key')
                
                # Handle Chinese LLM providers
                provider_lower = provider.lower()
                if provider_lower in CHINESE_LLM_PROVIDERS:
                    provider_config = CHINESE_LLM_PROVIDERS[provider_lower]
                    
                    # Set model with proper prefix
                    if provider_config['model_prefix']:
                        full_model = f"{provider_config['model_prefix']}{model}"
                    else:
                        full_model = model
                    
                    # Set base_url if configured
                    if provider_config['base_url']:
                        params['base_url'] = provider_config['base_url']
                    
                    # Use the full model name as provider for LiteLLM
                    extraction_strategy = LLMExtractionStrategy(
                        provider=full_model,
                        api_token=api_key,
                        instruction=prompt_template,
                        schema=output_schema,
                        **params
                    )
                else:
                    # Standard provider (openai, anthropic, etc.)
                    extraction_strategy = LLMExtractionStrategy(
                        provider=provider,
                        api_token=api_key,
                        instruction=prompt_template,
                        schema=output_schema,
                        **params
                    )
                
                crawl_params['extraction_strategy'] = extraction_strategy
            
            # Execute crawl
            result = await self.crawler.arun(**crawl_params)
            
            if not result.success:
                logger.error(f"Crawl failed for {url}: {result.error_message}")
                return {
                    'success': False,
                    'url': url,
                    'error': result.error_message,
                }
            
            # Extract data
            # Handle markdown properly - it can be a string or MarkdownGenerationResult object
            markdown_content = extract_markdown_string(result.markdown)
            
            crawl_result = {
                'success': True,
                'url': url,
                'html': result.html,
                'markdown': markdown_content,
                'cleaned_html': result.cleaned_html,
                'metadata': {
                    'title': getattr(result, 'title', None),
                    'description': getattr(result, 'description', None),
                    'language': getattr(result, 'language', None),
                    'keywords': getattr(result, 'keywords', []),
                },
                'links': {
                    'internal': getattr(result, 'links', {}).get('internal', []),
                    'external': getattr(result, 'links', {}).get('external', []),
                },
                'media': {
                    'images': getattr(result, 'media', {}).get('images', []),
                    'videos': getattr(result, 'media', {}).get('videos', []),
                    'audios': getattr(result, 'media', {}).get('audios', []),
                },
                'extracted_content': result.extracted_content if hasattr(result, 'extracted_content') else None,
                'screenshot': result.screenshot if crawl_config.get('screenshot') else None,
                'pdf': result.pdf if crawl_config.get('pdf') else None,
            }
            
            # Parse structured data if LLM extraction was used
            if result.extracted_content:
                try:
                    crawl_result['structured_data'] = json.loads(result.extracted_content)
                except json.JSONDecodeError:
                    crawl_result['structured_data'] = {'raw': result.extracted_content}
            
            logger.info(f"Successfully crawled: {url}")
            return crawl_result
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'url': url,
                'error': str(e),
            }


async def download_resource(
    url: str,
    max_size_mb: int = 10,
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Download a resource (image, attachment) with size limit
    
    Returns:
        Dictionary with download info or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # First, do a HEAD request to check size
            try:
                head_response = await client.head(url, follow_redirects=True)
                content_length = head_response.headers.get('content-length')
                
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        logger.warning(f"Resource too large ({size_mb:.2f}MB): {url}")
                        return None
            except Exception as e:
                logger.debug(f"HEAD request failed for {url}: {e}")
            
            # Download the resource
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            content = response.content
            size_bytes = len(content)
            size_mb = size_bytes / (1024 * 1024)
            
            if size_mb > max_size_mb:
                logger.warning(f"Downloaded resource too large ({size_mb:.2f}MB): {url}")
                return None
            
            # Get content type
            content_type = response.headers.get('content-type', 'application/octet-stream')
            
            # Extract filename from URL
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name or f"resource_{uuid.uuid4().hex[:8]}"
            
            return {
                'success': True,
                'content': content,
                'size_bytes': size_bytes,
                'mime_type': content_type,
                'filename': filename,
            }
            
    except Exception as e:
        logger.error(f"Error downloading resource {url}: {str(e)}")
        return None


def generate_minio_path(run_id: str, resource_type: str, filename: str) -> str:
    """
    Generate MinIO path for resource
    
    Args:
        run_id: Run ID
        resource_type: Type of resource (json, markdown, images, attachments, logs)
        filename: Filename
    
    Returns:
        MinIO object path
    """
    today = date.today().strftime('%Y-%m-%d')
    return f"{today}/{run_id}/{resource_type}/{filename}"
