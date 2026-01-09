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

logger = logging.getLogger(__name__)

# Try to import markdown generation strategy (may not be available in all versions)
try:
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    from crawl4ai.content_filter_strategy import PruningContentFilter
    MARKDOWN_GENERATOR_AVAILABLE = True
except ImportError:
    MARKDOWN_GENERATOR_AVAILABLE = False

# Try to import LLMConfig for crawl4ai 0.7.8+ compatibility
try:
    from crawl4ai.async_configs import LLMConfig
    LLMCONFIG_AVAILABLE = True
except ImportError:
    LLMCONFIG_AVAILABLE = False
    logger.warning("LLMConfig not available - crawl4ai 0.7.8+ is required for LLM extraction")


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
    
    # Only use fallback if both raw and fit are unavailable (edge case)
    # This helps identify when the content filter is not working properly
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


def build_llm_config(
    provider: str,
    model: str,
    params: Dict[str, Any]
) -> Optional[Any]:
    """
    Build LLMConfig for crawl4ai 0.7.8+ compatibility.
    
    Args:
        provider: LLM provider name (e.g., 'openai', 'qwen', 'deepseek')
        model: Model name (e.g., 'gpt-4', 'deepseek-chat', 'qwen-turbo')
        params: Additional parameters including api_key, base_url, temperature, etc.
    
    Returns:
        LLMConfig instance or None if construction fails
    """
    if not LLMCONFIG_AVAILABLE:
        logger.error("LLMConfig not available - cannot create LLM extraction strategy. "
                    "Please ensure crawl4ai>=0.7.8 is installed.")
        return None
    
    try:
        # Extract API key from params (it's stored in task.llm_params)
        # Support both 'api_key' and 'api_token' for backward compatibility
        api_key = params.get('api_key') or params.get('api_token')
        
        if not api_key:
            logger.warning("No API key provided for LLM extraction. LLM extraction will be skipped.")
            return None
        
        # Handle Chinese LLM providers
        provider_lower = provider.lower()
        full_model = model
        base_url = params.get('base_url')
        
        if provider_lower in CHINESE_LLM_PROVIDERS:
            provider_config = CHINESE_LLM_PROVIDERS[provider_lower]
            
            # Set model with proper prefix for LiteLLM compatibility
            if provider_config['model_prefix']:
                full_model = f"{provider_config['model_prefix']}{model}"
            
            # Set base_url if configured for this provider and not already set
            if provider_config['base_url'] and not base_url:
                base_url = provider_config['base_url']
            
            logger.debug(f"Using Chinese LLM provider: {provider_lower}, full_model: {full_model}")
        else:
            # For standard providers (openai, anthropic, etc.), use provider/model format
            full_model = f"{provider}/{model}" if '/' not in model else model
            logger.debug(f"Using standard LLM provider: {provider}, full_model: {full_model}")
        
        # Build LLMConfig with all supported parameters
        llm_config_params = {
            'provider': full_model,
            'api_token': api_key,
        }
        
        # Add optional parameters if present
        if base_url:
            llm_config_params['base_url'] = base_url
        if 'temperature' in params:
            llm_config_params['temperature'] = params['temperature']
        if 'max_tokens' in params:
            llm_config_params['max_tokens'] = params['max_tokens']
        if 'top_p' in params:
            llm_config_params['top_p'] = params['top_p']
        if 'frequency_penalty' in params:
            llm_config_params['frequency_penalty'] = params['frequency_penalty']
        if 'presence_penalty' in params:
            llm_config_params['presence_penalty'] = params['presence_penalty']
        if 'stop' in params:
            llm_config_params['stop'] = params['stop']
        if 'n' in params:
            llm_config_params['n'] = params['n']
        
        # Create LLMConfig instance
        llm_config = LLMConfig(**llm_config_params)
        
        logger.debug(f"LLMConfig created successfully: provider={full_model}, base_url={base_url}")
        return llm_config
        
    except Exception as e:
        logger.error(f"Failed to create LLMConfig: {e}", exc_info=True)
        return None


def select_content_selector(crawl_config: Dict[str, Any], html: Optional[str] = None) -> tuple[Optional[str], str]:
    """
    Select the best CSS selector for main content extraction.
    
    This implements a strategy to find the main content area:
    1. If user provided content_selector, use it
    2. If css_selector is provided, use it (for backward compatibility)
    3. Otherwise, use heuristic with default candidate selectors
    
    Args:
        crawl_config: Crawl configuration dictionary
        html: Optional HTML content for heuristic analysis (not implemented yet)
    
    Returns:
        Tuple of (selected_selector, selection_reason)
    """
    # Priority 1: User-provided content_selector (new field for Stage 1 cleaning)
    if crawl_config.get('content_selector'):
        selector = crawl_config['content_selector']
        logger.info(f"Using user-provided content_selector: '{selector}'")
        return selector, "user-provided content_selector"
    
    # Priority 2: Existing css_selector (for backward compatibility)
    if crawl_config.get('css_selector'):
        selector = crawl_config['css_selector']
        logger.info(f"Using css_selector for content extraction: '{selector}'")
        return selector, "css_selector (backward compatibility)"
    
    # Priority 3: Heuristic with default candidates
    # These are common selectors for main content in web pages
    # Ordered by likelihood of containing main content
    default_candidates = [
        'article',
        'main',
        '.content',
        '#content',
        '.main-content',
        '#main-content',
        '.post-content',
        '.article-content',
        '.detail-content',
        '#main',
        '.main',
        '.post',
        '.entry-content',
        '[role="main"]',
    ]
    
    # For now, return the first candidate as a comma-separated list
    # This allows crawl4ai to try multiple selectors
    # Future enhancement: parse HTML and select best based on text density
    selector = ', '.join(default_candidates)
    logger.info(f"Using heuristic content selector with {len(default_candidates)} candidates")
    logger.debug(f"Candidate selectors: {selector}")
    return selector, "heuristic with default candidates"


async def fallback_llm_extraction(
    markdown_content: str,
    llm_config_obj: Any,
    prompt_template: str,
    output_schema: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Perform fallback LLM extraction when crawl4ai's extraction fails.
    
    This function makes a direct LLM call using the same configuration
    that crawl4ai would use, but with the cleaned markdown as input.
    
    Args:
        markdown_content: Cleaned markdown content to extract from
        llm_config_obj: LLMConfig instance for the LLM provider
        prompt_template: Prompt template for extraction
        output_schema: Optional JSON schema for structured output
    
    Returns:
        Extracted structured data as dictionary, or None if failed
    """
    try:
        import time
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("Stage 2 FALLBACK extraction START")
        logger.info(f"  - Input size: {len(markdown_content)} characters")
        logger.info(f"  - Prompt length: {len(prompt_template)} characters")
        logger.info(f"  - Schema provided: {'yes' if output_schema else 'no'}")
        logger.info("=" * 60)
        
        # Create a new extraction strategy with the cleaned content
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config_obj,
            instruction=prompt_template,
            schema=output_schema
        )
        
        # Extract using the strategy
        # Note: LLMExtractionStrategy.aextract() expects the markdown content
        extracted = await extraction_strategy.aextract(
            url="",  # Not used for fallback
            html="",  # Not used for fallback
            markdown=markdown_content
        )
        
        elapsed = time.time() - start_time
        
        if extracted:
            # Parse the extracted content
            try:
                structured_data = json.loads(extracted)
                output_size = len(json.dumps(structured_data))
                
                logger.info("=" * 60)
                logger.info("Stage 2 FALLBACK extraction END - SUCCESS")
                logger.info(f"  - Elapsed time: {elapsed:.2f}s")
                logger.info(f"  - Output size: {output_size} bytes")
                logger.info("=" * 60)
                
                return structured_data
            except json.JSONDecodeError as e:
                logger.error(f"Fallback extraction returned invalid JSON: {e}")
                logger.error(f"Raw output: {extracted[:200]}...")
                return None
        else:
            logger.warning("=" * 60)
            logger.warning("Stage 2 FALLBACK extraction END - FAILED")
            logger.warning(f"  - Elapsed time: {elapsed:.2f}s")
            logger.warning("  - Reason: LLM returned empty content")
            logger.warning("=" * 60)
            return None
            
    except Exception as e:
        logger.error(f"Fallback LLM extraction failed: {e}", exc_info=True)
        logger.error("=" * 60)
        logger.error("Stage 2 FALLBACK extraction END - ERROR")
        logger.error(f"  - Error: {str(e)}")
        logger.error("=" * 60)
        return None


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
                    # Based on crawl4ai documentation: https://docs.crawl4ai.com/core/fit-markdown/
                    # 
                    # Threshold configuration:
                    # - threshold=0.48 is default, keeps blocks with text density >= 48%
                    # - For Chinese educational websites, we use 0.40 to be more inclusive
                    #   (Chinese characters have higher information density)
                    # - threshold_type="dynamic" adjusts threshold based on content characteristics
                    # - min_word_threshold=0 includes short blocks if they meet density requirements
                    # 
                    # User can override by using css_selector in crawl_config
                    threshold = 0.40  # More inclusive for Chinese content
                    if crawl_config.get('content_filter_threshold'):
                        threshold = crawl_config['content_filter_threshold']
                    
                    content_filter = PruningContentFilter(
                        threshold=threshold,
                        threshold_type="dynamic",
                        min_word_threshold=0
                    )
                    markdown_generator = DefaultMarkdownGenerator(
                        content_filter=content_filter
                    )
                    crawl_params['markdown_generator'] = markdown_generator
                    logger.info(f"Stage 1 cleaning enabled: PruningContentFilter (threshold={threshold}) will remove headers, footers, and navigation")
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
            
            # Select content selector for Stage 1 cleaning
            # This helps crawl4ai focus on main content area
            selected_selector, selection_reason = select_content_selector(crawl_config)
            if selected_selector:
                crawl_params['css_selector'] = selected_selector
                logger.info(f"Content selector applied: '{selected_selector}' (reason: {selection_reason})")
            else:
                logger.info("No content selector applied - will process entire page")
            if crawl_config.get('screenshot'):
                crawl_params['screenshot'] = True
                logger.debug("Screenshot enabled")
            if crawl_config.get('pdf'):
                crawl_params['pdf'] = True
                logger.debug("PDF generation enabled")
            
            # Configure LLM extraction if provided (Stage 2 cleaning)
            # Track Stage 2 status for detailed logging
            stage2_enabled = False
            stage2_error = None
            llm_config_obj = None
            provider = None
            model = None
            params = {}
            
            if llm_config and prompt_template:
                provider = llm_config.get('provider', 'openai')
                model = llm_config.get('model', 'gpt-4')
                params = llm_config.get('params', {})
                
                logger.info(f"Configuring LLM extraction with provider={provider}, model={model}")
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Prompt template length: {len(prompt_template)} chars")
                    logger.debug(f"Output schema provided: {output_schema is not None}")
                
                # Build LLMConfig for crawl4ai 0.7.8+ compatibility
                try:
                    llm_config_obj = build_llm_config(provider, model, params)
                    
                    if llm_config_obj is None:
                        # build_llm_config already logged the reason for failure
                        stage2_error = "Failed to create LLMConfig (likely missing API key)"
                        logger.warning("Stage 2 extraction disabled: Failed to create LLMConfig. "
                                     "Continuing with Stage 1 only.")
                    else:
                        # Create LLMExtractionStrategy with LLMConfig
                        extraction_strategy = LLMExtractionStrategy(
                            llm_config=llm_config_obj,
                            instruction=prompt_template,
                            schema=output_schema
                        )
                        
                        crawl_params['extraction_strategy'] = extraction_strategy
                        stage2_enabled = True
                        logger.info("Stage 2 extraction enabled: LLM will extract structured data using custom schema")
                        
                except Exception as e:
                    # If LLMExtractionStrategy creation fails, log and continue without it
                    stage2_error = f"LLMExtractionStrategy creation failed: {str(e)}"
                    logger.error(f"Failed to create LLM extraction strategy: {e}", exc_info=True)
                    logger.warning("Stage 2 extraction disabled due to error. Continuing with Stage 1 only.")
            else:
                # Log why LLM extraction is not being used
                if not llm_config:
                    stage2_error = "No LLM config provided"
                    logger.info("Stage 2 extraction disabled: No LLM config provided")
                elif not prompt_template:
                    stage2_error = "No prompt_template provided"
                    logger.warning("Stage 2 extraction disabled: LLM config present but no prompt_template provided")
            
            # Execute crawl
            logger.info(f"Executing crawl for: {url}")
            
            result = await self.crawler.arun(**crawl_params)
            
            if not result.success:
                logger.error(f"Crawl failed for {url}: {result.error_message}")
                return {
                    'success': False,
                    'url': url,
                    'error': result.error_message,
                    'stage2_status': {
                        'enabled': stage2_enabled,
                        'success': False,
                        'error': f"Crawl failed: {result.error_message}",
                        'output_size_bytes': None,
                        'fallback_used': False
                    }
                }
            
            logger.info(f"Crawl completed successfully for: {url}")
            
            # Extract both raw and fit (cleaned) markdown versions
            # In crawl4ai 0.7.8+, result.markdown is a MarkdownGenerationResult object
            # with properties: raw_markdown (full), fit_markdown (cleaned), fit_html
            markdown_versions = extract_markdown_versions(result.markdown)
            
            # Determine which markdown to use for Stage 2
            # Prefer cleaned (fit) markdown, fall back to raw if cleaned is empty
            stage2_input_source = None
            stage2_input_content = None
            
            if stage2_enabled:
                # Determine input source for Stage 2
                cleaned_md = markdown_versions.get('fit')
                raw_md = markdown_versions.get('raw')
                
                if cleaned_md and len(cleaned_md.strip()) > 0:
                    # Use cleaned markdown if available and not empty
                    stage2_input_source = "cleaned"
                    stage2_input_content = cleaned_md
                    
                    # Check if cleaned is substantially the same as raw (cleaning ineffective)
                    if raw_md and len(raw_md) > 0:
                        reduction_ratio = (len(raw_md) - len(cleaned_md)) / len(raw_md)
                        if reduction_ratio < 0.05:  # Less than 5% reduction
                            logger.warning(f"Cleaned markdown is very similar to raw ({reduction_ratio*100:.1f}% reduction)")
                            logger.warning("Stage 1 cleaning may be ineffective - consider configuring content_selector")
                elif raw_md and len(raw_md.strip()) > 0:
                    # Fall back to raw markdown if cleaned is empty
                    stage2_input_source = "raw"
                    stage2_input_content = raw_md
                    logger.warning("Cleaned markdown is empty, falling back to raw markdown for Stage 2")
                else:
                    stage2_input_source = "none"
                    stage2_input_content = None
                    logger.error("No markdown content available for Stage 2 extraction")
                
                # Log detailed Stage 2 start information with input source
                api_key_present = "present" if params.get('api_key') else "absent"
                base_url = params.get('base_url', 'default')
                schema_configured = "yes" if output_schema else "no"
                prompt_source = "task config" if prompt_template else "default"
                
                logger.info("=" * 60)
                logger.info("Stage 2 (LLM extraction) START")
                logger.info(f"  - URL: {url}")
                logger.info(f"  - Provider: {provider}")
                logger.info(f"  - Model: {model}")
                logger.info(f"  - API key: {api_key_present}")
                logger.info(f"  - Base URL: {base_url}")
                logger.info(f"  - Input source: {stage2_input_source}")
                if stage2_input_content:
                    logger.info(f"  - Input size: {len(stage2_input_content)} characters")
                logger.info(f"  - Prompt length: {len(prompt_template)} chars")
                logger.info(f"  - Prompt source: {prompt_source}")
                logger.info(f"  - Schema configured: {schema_configured}")
                logger.info("=" * 60)
            
            # Log what we extracted and provide diagnostics for Stage 1 cleaning
            if markdown_versions['raw']:
                logger.info(f"Extracted raw markdown: {len(markdown_versions['raw'])} characters")
            
            if markdown_versions['fit']:
                # Calculate and log cleaning statistics
                raw_len = len(markdown_versions['raw']) if markdown_versions['raw'] else 0
                fit_len = len(markdown_versions['fit'])
                
                if raw_len > 0:
                    reduction = ((raw_len - fit_len) / raw_len * 100)
                    logger.info(f"Stage 1 cleaning completed: {raw_len} -> {fit_len} chars (reduced {reduction:.1f}%)")
                    
                    # Provide diagnostics if cleaning ratio is very low (< 5%)
                    if reduction < 5.0:
                        logger.warning("⚠ Stage 1 cleaning reduced very little content (< 5%)")
                        logger.warning("Possible reasons:")
                        logger.warning("  1. Page content is already clean (no headers/footers/navigation)")
                        logger.warning("  2. Page structure prevents PruningContentFilter from working effectively")
                        logger.warning("  3. css_selector not configured - crawl4ai processed entire page")
                        logger.warning("")
                        logger.warning("Recommendations to improve Stage 1 cleaning:")
                        logger.warning("  • Add 'css_selector' to crawl_config to target main content area:")
                        logger.warning("    Example selectors: 'article, .article, .content, .main, .main-content,")
                        logger.warning("                       .detail, .detail-content, #content, #main, .post-content'")
                        logger.warning("  • Inspect the page HTML to find the main content container CSS selector")
                        logger.warning("  • Use browser DevTools to identify the right selector")
                        
                        # Check if css_selector was used
                        css_selector = crawl_config.get('css_selector')
                        if css_selector:
                            logger.info(f"  Note: css_selector is configured: '{css_selector}'")
                            logger.info("  The selector might be too broad or not matching main content.")
                        else:
                            logger.info("  Note: No css_selector configured - processing entire page")
                else:
                    logger.info(f"Extracted cleaned markdown: {fit_len} characters")
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
            # Track Stage 2 execution status and results
            stage2_success = False
            stage2_output_size = 0
            stage2_fallback_used = False
            
            if result.extracted_content:
                try:
                    crawl_result['structured_data'] = json.loads(result.extracted_content)
                    stage2_success = True
                    stage2_output_size = len(json.dumps(crawl_result['structured_data']))
                    
                    # Log Stage 2 END with success details
                    # Show sample of keys for large JSON objects to avoid expensive logging
                    json_keys = list(crawl_result['structured_data'].keys()) if isinstance(crawl_result['structured_data'], dict) else 'N/A'
                    if isinstance(json_keys, list) and len(json_keys) > 10:
                        json_keys_str = f"{json_keys[:10]}... ({len(json_keys)} total)"
                    else:
                        json_keys_str = str(json_keys)
                    
                    logger.info("=" * 60)
                    logger.info("Stage 2 (LLM extraction) END - SUCCESS")
                    logger.info(f"  - URL: {url}")
                    logger.info(f"  - Output size: {stage2_output_size} bytes")
                    logger.info(f"  - JSON keys: {json_keys_str}")
                    logger.info("=" * 60)
                except json.JSONDecodeError as e:
                    stage2_error = f"JSON parse failed: {str(e)}"
                    logger.warning("=" * 60)
                    logger.warning("Stage 2 (LLM extraction) END - FAILED")
                    logger.warning(f"  - URL: {url}")
                    logger.warning(f"  - Error: {stage2_error}")
                    logger.warning(f"  - Raw content length: {len(result.extracted_content)} chars")
                    logger.warning("=" * 60)
                    crawl_result['structured_data'] = {'raw': result.extracted_content}
            elif stage2_enabled:
                # Stage 2 was enabled but produced no output
                stage2_error = "LLM returned empty/no extracted_content"
                logger.warning("=" * 60)
                logger.warning("Stage 2 (LLM extraction) END - FAILED")
                logger.warning(f"  - URL: {url}")
                logger.warning(f"  - Error: {stage2_error}")
                logger.warning("=" * 60)
                
                # Try fallback extraction if enabled and we have cleaned content
                fallback_enabled = crawl_config.get('stage2_fallback_enabled', True)
                if fallback_enabled and stage2_input_content and llm_config_obj:
                    logger.info("Attempting Stage 2 FALLBACK extraction...")
                    
                    try:
                        fallback_result = await fallback_llm_extraction(
                            markdown_content=stage2_input_content,
                            llm_config_obj=llm_config_obj,
                            prompt_template=prompt_template,
                            output_schema=output_schema
                        )
                        
                        if fallback_result:
                            # Fallback succeeded
                            crawl_result['structured_data'] = fallback_result
                            stage2_success = True
                            stage2_fallback_used = True
                            stage2_output_size = len(json.dumps(fallback_result))
                            stage2_error = None  # Clear the error since fallback succeeded
                            
                            logger.info(f"✓ Stage 2 FALLBACK succeeded: {stage2_output_size} bytes extracted")
                        else:
                            logger.warning("✗ Stage 2 FALLBACK failed: No output generated")
                            stage2_error = "Both primary and fallback extraction failed"
                    except Exception as e:
                        logger.error(f"Stage 2 FALLBACK exception: {e}", exc_info=True)
                        stage2_error = f"Primary extraction failed, fallback error: {str(e)}"
                elif fallback_enabled and not stage2_input_content:
                    logger.warning("Stage 2 FALLBACK skipped: No input content available")
                    stage2_error = "LLM extraction failed and no content for fallback"
                elif fallback_enabled and not llm_config_obj:
                    logger.warning("Stage 2 FALLBACK skipped: No LLM config available")
                    stage2_error = "LLM extraction failed and no config for fallback"
                else:
                    logger.info("Stage 2 FALLBACK disabled by configuration")
            
            # Add Stage 2 metadata to result for downstream processing
            crawl_result['stage2_status'] = {
                'enabled': stage2_enabled,
                'success': stage2_success,
                'error': stage2_error,
                'output_size_bytes': stage2_output_size if stage2_success else None,
                'fallback_used': stage2_fallback_used
            }
            
            logger.info(f"Successfully crawled: {url}")
            return crawl_result
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'stage2_status': {
                    'enabled': False,
                    'success': False,
                    'error': f"Crawl failed: {str(e)}",
                    'output_size_bytes': None,
                    'fallback_used': False
                }
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
