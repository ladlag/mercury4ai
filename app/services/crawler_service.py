import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode, BrowserConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, date
from pathlib import Path
import json
import httpx
from urllib.parse import urlparse
import uuid

# Try to import markdown generation strategy (may not be available in all versions)
try:
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    from crawl4ai.content_filter_strategy import PruningContentFilter
    MARKDOWN_GENERATOR_AVAILABLE = True
except ImportError:
    MARKDOWN_GENERATOR_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract_markdown_string(markdown_result: Any) -> Optional[str]:
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
    except (TypeError, AttributeError, ValueError) as e:
        logger.warning(f"Unable to extract markdown from result type {type(markdown_result)}: {e}")
        return None


def extract_markdown_versions(markdown_result: Any) -> Dict[str, Optional[str]]:
    """
    Extract both raw and fit (cleaned) markdown from crawl4ai result.
    
    In crawl4ai 0.7.8+:
    - result.markdown is a MarkdownGenerationResult object
    - It has properties: raw_markdown (full), fit_markdown (cleaned), fit_html
    
    fit_markdown is the cleaned version with headers, footers, and navigation removed by crawl4ai.
    raw_markdown is the original full markdown.
    
    Args:
        markdown_result: The markdown field from crawl4ai result
    
    Returns:
        Dictionary with 'raw' and 'fit' keys containing respective markdown versions
    """
    result = {'raw': None, 'fit': None}
    
    if markdown_result is None:
        return result
    
    # If it's already a string, use it for both (backward compatibility)
    if isinstance(markdown_result, str):
        result['raw'] = markdown_result
        result['fit'] = markdown_result
        return result
    
    # If it's a MarkdownGenerationResult object, extract both versions
    # This is the expected format in crawl4ai 0.7.8+
    if hasattr(markdown_result, 'raw_markdown'):
        result['raw'] = markdown_result.raw_markdown
    if hasattr(markdown_result, 'fit_markdown'):
        result['fit'] = markdown_result.fit_markdown
    
    # If we only got raw markdown but no fit markdown, don't use raw as fallback
    # This helps identify when the content filter is not working
    # Only use raw as fallback if neither is available
    if not result['raw'] and not result['fit']:
        # Last resort: try to convert to string
        try:
            fallback_str = str(markdown_result)
            result['raw'] = fallback_str
            result['fit'] = fallback_str
        except (TypeError, AttributeError, ValueError):
            pass
    
    return result


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
    def __init__(self, verbose: bool = True, browser_type: str = "chromium", headless: bool = True):
        """
        Initialize CrawlerService
        
        Args:
            verbose: Legacy parameter, kept for compatibility but no longer used in crawl4ai 0.7.8+.
                     Logging verbosity is now controlled by Python logging configuration.
            browser_type: Browser type to use (default: "chromium", options: "chromium", "firefox", "webkit")
            headless: Run browser in headless mode (default: True)
        """
        self.crawler = None
        self.verbose = verbose  # Kept for backward compatibility
        self.browser_type = browser_type
        self.headless = headless
    
    async def __aenter__(self):
        """Context manager entry"""
        # Configure browser
        # Note: verbose parameter removed for crawl4ai 0.7.8 compatibility
        browser_config = BrowserConfig(
            browser_type=self.browser_type,
            headless=self.headless
        )
        self.crawler = await AsyncWebCrawler(config=browser_config).__aenter__()
        logger.info(f"AsyncWebCrawler initialized with browser_type={self.browser_type}, headless={self.headless}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
            logger.info("AsyncWebCrawler closed")
    
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
            crawl_config: General crawl4ai configuration (may include verbose flag)
            llm_config: LLM provider configuration
            prompt_template: Prompt for LLM extraction
            output_schema: JSON schema for structured output
        
        Returns:
            Dictionary with crawl results
        """
        try:
            logger.info(f"Starting crawl for URL: {url}")
            
            # Prepare crawl parameters
            crawl_params = {
                'url': url,
                'cache_mode': CacheMode.BYPASS,
            }
            
            # Configure markdown generator to get both raw and fit (cleaned) versions
            # This enables crawl4ai's built-in cleaning (Stage 1 cleaning)
            if MARKDOWN_GENERATOR_AVAILABLE:
                try:
                    # Use PruningContentFilter to remove headers, footers, navigation, ads, etc.
                    # threshold=0.48 means keep blocks with text density >= 48% (recommended default)
                    # threshold_type="dynamic" adjusts based on content characteristics
                    # min_word_threshold=0 includes even short blocks if they meet density requirements
                    content_filter = PruningContentFilter(
                        threshold=0.48,
                        threshold_type="dynamic",
                        min_word_threshold=0
                    )
                    markdown_generator = DefaultMarkdownGenerator(
                        content_filter=content_filter
                    )
                    crawl_params['markdown_generator'] = markdown_generator
                    logger.debug("Markdown generator configured with PruningContentFilter for content cleaning")
                except Exception as e:
                    logger.warning(f"Could not configure markdown generator: {e}. Will use default markdown generation.")
            else:
                logger.debug("DefaultMarkdownGenerator not available - using default markdown generation")
            
            # Add optional parameters
            # Note: verbose parameter no longer supported in crawl4ai 0.7.8+
            if crawl_config.get('js_code'):
                crawl_params['js_code'] = crawl_config['js_code']
                logger.debug(f"Added js_code to crawl params")
            if crawl_config.get('wait_for'):
                crawl_params['wait_for'] = crawl_config['wait_for']
                logger.debug(f"Added wait_for selector: {crawl_config['wait_for']}")
            if crawl_config.get('css_selector'):
                crawl_params['css_selector'] = crawl_config['css_selector']
                logger.debug(f"Added css_selector: {crawl_config['css_selector']}")
            if crawl_config.get('screenshot'):
                crawl_params['screenshot'] = True
                logger.debug("Screenshot enabled")
            if crawl_config.get('pdf'):
                crawl_params['pdf'] = True
                logger.debug("PDF generation enabled")
            
            # Configure LLM extraction if provided (Stage 2 cleaning)
            if llm_config and prompt_template:
                provider = llm_config.get('provider', 'openai')
                model = llm_config.get('model', 'gpt-4')
                params = llm_config.get('params', {})
                
                logger.info(f"Configuring LLM extraction with provider={provider}, model={model}")
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Prompt template length: {len(prompt_template)} chars")
                    logger.debug(f"Output schema provided: {output_schema is not None}")
                
                # Extract API key from params (it's stored in task.llm_params)
                api_key = params.get('api_key')
                
                if not api_key:
                    logger.warning("No API key provided for LLM extraction. LLM extraction will be skipped.")
                else:
                    logger.debug("API key is present")
                
                # Handle Chinese LLM providers
                provider_lower = provider.lower()
                if provider_lower in CHINESE_LLM_PROVIDERS:
                    provider_config = CHINESE_LLM_PROVIDERS[provider_lower]
                    
                    # Set model with proper prefix
                    if provider_config['model_prefix']:
                        full_model = f"{provider_config['model_prefix']}{model}"
                    else:
                        full_model = model
                    
                    logger.debug(f"Using Chinese LLM provider: {provider_lower}, full_model: {full_model}")
                    
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
                    logger.debug(f"Using standard LLM provider: {provider}")
                    extraction_strategy = LLMExtractionStrategy(
                        provider=provider,
                        api_token=api_key,
                        instruction=prompt_template,
                        schema=output_schema,
                        **params
                    )
                
                crawl_params['extraction_strategy'] = extraction_strategy
                logger.info("LLM extraction strategy configured successfully")
            else:
                # Log why LLM extraction is not being used
                if not llm_config:
                    logger.info("No LLM config provided - skipping structured extraction")
                elif not prompt_template:
                    logger.warning("LLM config present but no prompt_template provided - skipping structured extraction")
            
            # Execute crawl
            logger.info(f"Executing crawl for: {url}")
            result = await self.crawler.arun(**crawl_params)
            
            if not result.success:
                logger.error(f"Crawl failed for {url}: {result.error_message}")
                return {
                    'success': False,
                    'url': url,
                    'error': result.error_message,
                }
            
            logger.info(f"Crawl completed successfully for: {url}")
            
            # Extract both raw and fit (cleaned) markdown versions
            # In crawl4ai 0.7.8+, result.markdown is a MarkdownGenerationResult object
            # with properties: raw_markdown (full), fit_markdown (cleaned), fit_html
            markdown_versions = extract_markdown_versions(result.markdown)
            
            # Log what we extracted
            if markdown_versions['raw']:
                logger.debug(f"Extracted raw markdown: {len(markdown_versions['raw'])} characters")
            if markdown_versions['fit']:
                logger.debug(f"Extracted fit markdown (cleaned by crawl4ai): {len(markdown_versions['fit'])} characters")
            else:
                # If no fit markdown extracted, log more details for debugging
                logger.warning("No fit_markdown extracted - content filter may not be working")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"result.markdown type: {type(result.markdown)}")
                    if hasattr(result.markdown, '__dict__'):
                        logger.debug(f"result.markdown properties: {list(vars(result.markdown).keys())}")

            
            crawl_result = {
                'success': True,
                'url': url,
                'html': result.html,
                'markdown': markdown_versions['raw'],  # Original markdown
                'markdown_fit': markdown_versions['fit'],  # Cleaned markdown (first pass by crawl4ai)
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
            
            # Log media extraction results if any media was found
            images_count = len(crawl_result['media']['images'])
            videos_count = len(crawl_result['media']['videos'])
            audios_count = len(crawl_result['media']['audios'])
            if images_count > 0 or videos_count > 0 or audios_count > 0:
                logger.info(f"Extracted {images_count} images, {videos_count} videos, {audios_count} audios from {url}")
            
            # Parse structured data if LLM extraction was used
            if result.extracted_content:
                try:
                    crawl_result['structured_data'] = json.loads(result.extracted_content)
                    logger.info(f"Successfully parsed structured data for {url}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse extracted_content as JSON for {url}: {str(e)}")
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
