import asyncio
import time
from crawl4ai import AsyncWebCrawler, CacheMode, BrowserConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, date
from pathlib import Path
import json
import httpx
import re
from html.parser import HTMLParser
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
    fit_html is the cleaned HTML corresponding to fit_markdown.
    
    Args:
        markdown_result: The markdown field from crawl4ai result
    
    Returns:
        Dictionary with 'raw', 'fit', and 'fit_html' keys containing respective versions
    """
    result = {'raw': None, 'fit': None, 'fit_html': None}
    
    if markdown_result is None:
        return result
    
    # If it's already a string, use it for both (backward compatibility)
    if isinstance(markdown_result, str):
        result['raw'] = markdown_result
        result['fit'] = markdown_result
        return result
    
    # If it's a MarkdownGenerationResult object, extract all versions
    # This is the expected format in crawl4ai 0.7.8+
    if hasattr(markdown_result, 'raw_markdown'):
        result['raw'] = markdown_result.raw_markdown
    if hasattr(markdown_result, 'fit_markdown'):
        result['fit'] = markdown_result.fit_markdown
    if hasattr(markdown_result, 'fit_html'):
        result['fit_html'] = markdown_result.fit_html
    
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


class _BasicHTMLTextExtractor(HTMLParser):
    """
    Lightweight HTML to text extractor used as a fallback when crawl4ai cleaning
    is ineffective. It removes navigation-like sections and strips scripts/styles
    without introducing new dependencies.
    """
    SKIP_TAGS = {"nav", "header", "footer", "aside", "script", "style"}
    BLOCK_TAGS = {
        "p", "div", "section", "article", "br", "hr", "li", "ul", "ol",
        "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td"
    }

    def __init__(self):
        super().__init__()
        self.skip_depth = 0
        self.parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth > 0:
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            if self.skip_depth > 0:
                self.skip_depth -= 1
            return
        if self.skip_depth > 0:
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        text = " ".join(self.parts)
        # Use two small regex passes so we collapse long space runs but keep intentional newlines.
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()


def fallback_clean_markdown(html_content: Optional[str]) -> Optional[str]:
    """
    Apply a lightweight HTML-to-text cleaning pass to remove navigation,
    headers/footers, and scripts/styles when built-in cleaning is ineffective.
    """
    if not html_content:
        return None

    extractor = _BasicHTMLTextExtractor()
    extractor.feed(html_content)
    cleaned_text = extractor.get_text()
    return cleaned_text if cleaned_text else None


def should_apply_stage1_fallback(raw_len: int, fit_len: Optional[int]) -> bool:
    """
    Decide whether to run the HTML-based Stage 1 fallback cleaning.
    """
    if raw_len <= 0:
        return False
    if fit_len is None:
        return True
    reduction_ratio = (raw_len - fit_len) / raw_len
    return reduction_ratio < CLEANING_REDUCTION_THRESHOLD


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

CLEANING_REDUCTION_THRESHOLD = 0.05  # 5% minimum reduction to consider Stage 1 cleaning effective


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


def select_content_selector(crawl_config: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """
    Select the best CSS selector for main content extraction.
    
    This implements a strategy to find the main content area:
    1. If css_selector is provided, use it (backward compatibility / explicit override)
    2. If user provided content_selector, use it
    3. Otherwise, use heuristic with prioritized default candidate selectors
    
    Args:
        crawl_config: Crawl configuration dictionary
    
    Returns:
        Tuple of (selected_selector, selection_reason)
    """
    # Priority 1: Existing css_selector (for backward compatibility and explicit override)
    if crawl_config.get('css_selector'):
        selector = crawl_config['css_selector']
        logger.info(f"Using css_selector for content extraction: '{selector}'")
        return selector, "css_selector (backward compatibility/override)"
    
    # Priority 2: User-provided content_selector (new field for Stage 1 cleaning)
    if crawl_config.get('content_selector'):
        selector = crawl_config['content_selector']
        logger.info(f"Using user-provided content_selector: '{selector}'")
        return selector, "user-provided content_selector"
    
    # Priority 3: Heuristic with default candidates
    # These are common selectors for main content in web pages
    # Ordered by likelihood of containing main content and specificity
    # Using comma-separated list allows crawl4ai to try each selector in order
    # and use the first match found
    default_candidates = [
        '#content',          # Generic content ID (common on Chinese educational sites)
        'div#content',
        'article',           # HTML5 article element (high priority)
        'main',              # HTML5 main element
        '[role="main"]',     # ARIA main role
        '.article-content',  # Common article content class
        '.post-content',     # Common blog post class
        '.detail-content',   # Common detail page class
        '.content',          # Generic content class
        '.main-content',     # Common main content class
        '#main-content',     # Common main content ID
        '.entry-content',    # WordPress default
        '#main',             # Generic main ID
        '.main',             # Generic main class
        '.post',             # Generic post class
    ]
    
    # Return as comma-separated list for crawl4ai to try in order
    selector = ', '.join(default_candidates)
    logger.info(f"Using heuristic content selector strategy with {len(default_candidates)} candidates")
    logger.info(f"  Top candidates: {', '.join(default_candidates[:5])}")
    logger.debug(f"  Full selector list: {selector}")
    return selector, "heuristic with prioritized default candidates"


def normalize_extracted_json(
    data: Any,
    schema: Optional[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Normalize LLM output to comply with the provided JSON schema.
    
    - Filters out keys not defined in schema.properties
    - Validates required fields presence
    
    Returns:
        (filtered_data, error_message)
    """
    if not schema or not isinstance(schema, dict):
        return data, None
    
    if not isinstance(data, dict):
        return None, "Extracted data is not an object; cannot satisfy schema"
    
    properties = schema.get('properties') or {}
    allowed_keys = set(properties.keys())
    filtered = {k: v for k, v in data.items() if k in allowed_keys}
    
    missing_required = [
        key for key in schema.get('required', []) if key not in filtered
    ]
    
    logger.info("Stage 2 normalization summary:")
    logger.info(f"  - schema keys: {sorted(list(allowed_keys)) if allowed_keys else '[]'}")
    logger.info(f"  - raw keys: {sorted(list(data.keys())) if isinstance(data, dict) else 'N/A'}")
    logger.info(f"  - kept keys: {sorted(list(filtered.keys())) if filtered else '[]'}")
    logger.info(f"  - missing required: {missing_required if missing_required else 'none'}")
    
    if missing_required:
        return None, f"Missing required fields: {', '.join(missing_required)}"
    
    return filtered, None


async def fallback_llm_extraction(
    html_content: str,
    url: str,
    llm_config_obj: Any,
    prompt_template: str,
    output_schema: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Perform fallback LLM extraction when crawl4ai's extraction fails.
    
    This function calls LLMExtractionStrategy.aextract() directly with cleaned HTML.
    Compatible with crawl4ai 0.7.8+ signature: aextract(url: str, ix: int, html: str)
    
    Args:
        html_content: Cleaned HTML content to extract from (fit_html or cleaned_html)
        url: Source URL for the content
        llm_config_obj: LLMConfig instance for the LLM provider
        prompt_template: Prompt template for extraction
        output_schema: Optional JSON schema for structured output
    
    Returns:
        Extracted structured data as dictionary, or None if failed
    """
    try:
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("Stage 2 FALLBACK extraction START")
        logger.info(f"  - URL: {url}")
        logger.info(f"  - Input type: HTML")
        logger.info(f"  - Input size: {len(html_content)} characters")
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
        # crawl4ai 0.7.8+ signature: aextract(url: str, ix: int, html: str) -> List[Dict[str, Any]]
        extracted_list = await extraction_strategy.aextract(
            url=url,
            ix=0,  # Index for batch processing (0 for single extraction)
            html=html_content
        )
        
        elapsed = time.time() - start_time
        
        if extracted_list:
            # aextract returns List[Dict[str, Any]]
            # Convert to unified structured_data format
            if isinstance(extracted_list, list) and len(extracted_list) > 0:
                # Single result: return the dict directly
                # Multiple results: wrap in {'items': [...]} for consistency
                structured_data = extracted_list[0] if len(extracted_list) == 1 else {'items': extracted_list}
                
                # Calculate output size
                output_size = len(json.dumps(structured_data, ensure_ascii=False))
                
                # Log keys for observability
                if isinstance(structured_data, dict):
                    keys = list(structured_data.keys())
                    keys_str = f"{keys[:10]}..." if len(keys) > 10 else str(keys)
                else:
                    keys_str = f"<{type(structured_data).__name__}>"
                
                logger.info("=" * 60)
                logger.info("Stage 2 FALLBACK extraction END - SUCCESS")
                logger.info(f"  - Elapsed time: {elapsed:.2f}s")
                logger.info(f"  - Output size: {output_size} bytes")
                logger.info(f"  - Output keys: {keys_str}")
                logger.info(f"  - Items returned: {len(extracted_list)}")
                logger.info("=" * 60)
                
                return structured_data
            else:
                logger.warning("=" * 60)
                logger.warning("Stage 2 FALLBACK extraction END - FAILED")
                logger.warning(f"  - Elapsed time: {elapsed:.2f}s")
                logger.warning("  - Reason: LLM returned empty list")
                logger.warning("=" * 60)
                return None
        else:
            logger.warning("=" * 60)
            logger.warning("Stage 2 FALLBACK extraction END - FAILED")
            logger.warning(f"  - Elapsed time: {elapsed:.2f}s")
            logger.warning("  - Reason: LLM returned empty/None")
            logger.warning("=" * 60)
            return None
            
    except Exception as e:
        logger.error(f"Fallback LLM extraction failed: {e}", exc_info=True)
        logger.error("=" * 60)
        logger.error("Stage 2 FALLBACK extraction END - ERROR")
        logger.error(f"  - Error type: {type(e).__name__}")
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
            effective_selector = None
            selected_selector, selection_reason = select_content_selector(crawl_config)
            effective_selector = selected_selector
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

            # If Stage 1 cleaning is missing or ineffective, apply a lightweight HTML-based fallback
            stage1_fallback_used = False
            html_source_for_cleaning = result.cleaned_html or result.html
            raw_md = markdown_versions.get('raw')
            fit_md = markdown_versions.get('fit')
            raw_len_for_fallback = len(raw_md) if raw_md else 0
            fit_len_for_fallback = len(fit_md) if fit_md else None

            if html_source_for_cleaning and should_apply_stage1_fallback(raw_len_for_fallback, fit_len_for_fallback):
                fallback_cleaned_md = fallback_clean_markdown(html_source_for_cleaning)
                if fallback_cleaned_md:
                    markdown_versions['fit'] = fallback_cleaned_md
                    stage1_fallback_used = True
                    logger.info("Applied fallback HTML cleaning to improve cleaned markdown")
                    logger.info(f"  - Fallback cleaned length: {len(fallback_cleaned_md)} chars")
            
            # Determine which content to use for Stage 2 and fallback
            # For fallback, we need HTML (not markdown) to match aextract() signature
            stage2_input_source = None
            stage2_input_content = None
            stage2_html_content = None  # HTML for fallback
            
            if stage2_enabled:
                # Determine input source for Stage 2
                cleaned_md = markdown_versions.get('fit')
                raw_md = markdown_versions.get('raw')
                fit_html = markdown_versions.get('fit_html')
                
                if cleaned_md and len(cleaned_md.strip()) > 0:
                    # Use cleaned markdown if available and not empty
                    stage2_input_source = "cleaned"
                    stage2_input_content = cleaned_md
                    # Prefer fit_html for fallback (cleaned HTML)
                    stage2_html_content = fit_html if fit_html else result.cleaned_html
                    
                    if not stage2_html_content:
                        logger.warning("No HTML content available for fallback (fit_html and cleaned_html are both None)")
                    
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
                    # Use raw HTML for fallback (should always be available)
                    stage2_html_content = result.html if result.html else result.cleaned_html
                    
                    if not stage2_html_content:
                        logger.error("Critical: No HTML content available despite having markdown")
                    
                    logger.warning("Cleaned markdown is empty, falling back to raw markdown for Stage 2")
                else:
                    stage2_input_source = "none"
                    stage2_input_content = None
                    stage2_html_content = None
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
                selector_label = effective_selector if effective_selector else 'none'
                logger.info(f"Content selector diagnostic: selector='{selector_label}' (reason: {selection_reason}), raw_len={raw_len}, cleaned_len={fit_len}")
                
                if raw_len > 0:
                    reduction = ((raw_len - fit_len) / raw_len * 100)
                    logger.info(f"Stage 1 cleaning completed: {raw_len} -> {fit_len} chars (reduced {reduction:.1f}%)")

                    if stage1_fallback_used:
                        logger.info("Stage 1 fallback cleaning applied using HTML parser (removed nav/header/footer/script/style)")
                    
                    # Provide diagnostics if cleaning ratio is very low (< 5%)
                    if reduction < CLEANING_REDUCTION_THRESHOLD * 100:
                        logger.warning("⚠ Stage 1 cleaning reduced very little content (< 5%)")
                        logger.warning("Possible reasons:")
                        logger.warning("  1. Page content is already clean (no headers/footers/navigation)")
                        logger.warning("  2. Page structure prevents PruningContentFilter from working effectively")
                        logger.warning("  3. No effective selector configured - crawl4ai processed entire page")
                        logger.warning("")
                        logger.warning("Recommendations to improve Stage 1 cleaning:")
                        logger.warning("  • Add 'content_selector' (or legacy 'css_selector') to target main content area:")
                        logger.warning("    Example selectors: '#content, div#content, article, .article, .content,")
                        logger.warning("                       .main, .main-content, .detail, .detail-content, #main'")
                        logger.warning("  • Inspect the page HTML to find the main content container CSS selector")
                        logger.warning("  • Use browser DevTools to identify the right selector")
                        
                        # Check which selector was used
                        if effective_selector:
                            logger.info(f"  Note: Effective selector used: '{effective_selector}' (reason: {selection_reason})")
                            logger.info("  The selector might be too broad or not matching main content.")
                        else:
                            logger.info("  Note: No content selector configured - processing entire page")
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
            normalized_data = None
            
            if result.extracted_content:
                try:
                    parsed_structured = json.loads(result.extracted_content)
                    normalized_data, normalize_error = normalize_extracted_json(parsed_structured, output_schema)
                    
                    if normalize_error:
                        stage2_error = normalize_error
                        logger.warning(f"Stage 2 normalization failed: {normalize_error}")
                    else:
                        crawl_result['structured_data'] = normalized_data
                        stage2_success = True
                        stage2_output_size = len(json.dumps(crawl_result['structured_data']))
                    
                    # Log Stage 2 END with success details
                    # Show sample of keys for large JSON objects to avoid expensive logging
                    if stage2_success:
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

            # Attempt Stage 2 fallback whenever the primary path failed
            # (extraction errors, JSON parsing errors, or normalization/schema failures).
            if stage2_enabled and not stage2_success:
                fallback_enabled = crawl_config.get('stage2_fallback_enabled', True)
                if fallback_enabled and stage2_html_content and llm_config_obj:
                    logger.info("Attempting Stage 2 FALLBACK extraction...")
                    logger.info(f"  - HTML content available: {len(stage2_html_content)} characters")
                    logger.info(f"  - Source: {stage2_input_source}")
                    
                    try:
                        fallback_result = await fallback_llm_extraction(
                            html_content=stage2_html_content,
                            url=url,
                            llm_config_obj=llm_config_obj,
                            prompt_template=prompt_template,
                            output_schema=output_schema
                        )
                        
                        if fallback_result:
                            normalized_fallback, normalize_error = normalize_extracted_json(fallback_result, output_schema)
                            if normalize_error:
                                logger.warning(f"Stage 2 FALLBACK normalization failed: {normalize_error}")
                                stage2_error = normalize_error
                            else:
                                # Fallback succeeded
                                crawl_result['structured_data'] = normalized_fallback
                                stage2_success = True
                                stage2_fallback_used = True
                                stage2_output_size = len(json.dumps(normalized_fallback))
                                stage2_error = None  # Clear the error since fallback succeeded
                                
                                logger.info(f"✓ Stage 2 FALLBACK succeeded: {stage2_output_size} bytes extracted")
                        else:
                            logger.warning("✗ Stage 2 FALLBACK failed: No output generated")
                            stage2_error = "Both primary and fallback extraction failed"
                    except Exception as e:
                        logger.error(f"Stage 2 FALLBACK exception: {e}", exc_info=True)
                        stage2_error = f"Primary extraction failed, fallback error: {str(e)}"
                elif fallback_enabled and not stage2_html_content:
                    logger.warning("Stage 2 FALLBACK skipped: No HTML content available")
                    stage2_error = stage2_error or "LLM extraction failed and no HTML content for fallback"
                elif fallback_enabled and not llm_config_obj:
                    logger.warning("Stage 2 FALLBACK skipped: No LLM config available")
                    stage2_error = stage2_error or "LLM extraction failed and no config for fallback"
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
