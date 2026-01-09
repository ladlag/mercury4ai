"""
Template and schema loader service.

This module provides utilities to load prompt templates and output schemas
from files in the repository, supporting the @prompt_templates/... and @schemas/... syntax.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Repository root directory
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
PROMPT_TEMPLATES_DIR = REPO_ROOT / "prompt_templates"
SCHEMAS_DIR = REPO_ROOT / "schemas"


def resolve_prompt_template(prompt_template: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve prompt template from string or file reference.
    
    Args:
        prompt_template: Either inline prompt text or @prompt_templates/... reference
    
    Returns:
        Tuple of (resolved_prompt, source):
        - resolved_prompt: The actual prompt text, or None if resolution failed
        - source: Description of where the prompt came from (for logging)
    
    Examples:
        >>> resolve_prompt_template("Extract title and content")
        ("Extract title and content", "inline")
        
        >>> resolve_prompt_template("@prompt_templates/news_article_zh.txt")
        ("Extract the following...", "@prompt_templates/news_article_zh.txt")
        
        >>> resolve_prompt_template(None)
        (None, None)
    """
    if not prompt_template:
        return None, None
    
    # Check if it's a file reference
    if prompt_template.startswith("@prompt_templates/"):
        # Extract the file path
        relative_path = prompt_template[len("@prompt_templates/"):]
        file_path = PROMPT_TEMPLATES_DIR / relative_path
        
        # Validate and load the file
        try:
            if not file_path.exists():
                logger.error(f"Prompt template file not found: {file_path}")
                logger.error(f"Reference: {prompt_template}")
                logger.error(f"To fix: Create the file or use an inline prompt")
                return None, None
            
            if not file_path.is_file():
                logger.error(f"Prompt template path is not a file: {file_path}")
                return None, None
            
            # Security check: ensure the file is within the prompt_templates directory
            try:
                file_path.resolve().relative_to(PROMPT_TEMPLATES_DIR)
            except ValueError:
                logger.error(f"Security: Prompt template path is outside prompt_templates directory: {file_path}")
                return None, None
            
            # Read the file
            prompt_content = file_path.read_text(encoding='utf-8')
            logger.info(f"Loaded prompt template from file: {prompt_template} ({len(prompt_content)} chars)")
            return prompt_content, prompt_template
            
        except Exception as e:
            logger.error(f"Error loading prompt template from {file_path}: {str(e)}", exc_info=True)
            return None, None
    
    # It's an inline prompt
    logger.debug(f"Using inline prompt template ({len(prompt_template)} chars)")
    return prompt_template, "inline"


def resolve_output_schema(output_schema: Optional[Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Resolve output schema from dict or file reference.
    
    Args:
        output_schema: Either inline dict schema or @schemas/... string reference
    
    Returns:
        Tuple of (resolved_schema, source):
        - resolved_schema: The actual schema dict, or None if resolution failed
        - source: Description of where the schema came from (for logging)
    
    Examples:
        >>> resolve_output_schema({"type": "object", "properties": {...}})
        ({"type": "object", ...}, "inline")
        
        >>> resolve_output_schema("@schemas/news_article_zh.json")
        ({"type": "object", ...}, "@schemas/news_article_zh.json")
        
        >>> resolve_output_schema(None)
        (None, None)
    """
    if not output_schema:
        return None, None
    
    # Check if it's a file reference (string starting with @schemas/)
    if isinstance(output_schema, str) and output_schema.startswith("@schemas/"):
        # Extract the file path
        relative_path = output_schema[len("@schemas/"):]
        file_path = SCHEMAS_DIR / relative_path
        
        # Validate and load the file
        try:
            if not file_path.exists():
                logger.error(f"Output schema file not found: {file_path}")
                logger.error(f"Reference: {output_schema}")
                logger.error(f"To fix: Create the file or use an inline schema")
                return None, None
            
            if not file_path.is_file():
                logger.error(f"Output schema path is not a file: {file_path}")
                return None, None
            
            # Security check: ensure the file is within the schemas directory
            try:
                file_path.resolve().relative_to(SCHEMAS_DIR)
            except ValueError:
                logger.error(f"Security: Output schema path is outside schemas directory: {file_path}")
                return None, None
            
            # Read and parse the JSON file
            schema_content = file_path.read_text(encoding='utf-8')
            schema_dict = json.loads(schema_content)
            
            logger.info(f"Loaded output schema from file: {output_schema}")
            return schema_dict, output_schema
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in output schema file {file_path}: {str(e)}")
            logger.error(f"To fix: Validate the JSON syntax in the schema file")
            return None, None
        except Exception as e:
            logger.error(f"Error loading output schema from {file_path}: {str(e)}", exc_info=True)
            return None, None
    
    # It's an inline schema (already a dict)
    if isinstance(output_schema, dict):
        logger.debug(f"Using inline output schema")
        return output_schema, "inline"
    
    # Invalid type
    logger.error(f"Invalid output_schema type: {type(output_schema)}. Expected dict or @schemas/... string reference")
    return None, None


def get_default_prompt_from_env(env_settings) -> Tuple[Optional[str], Optional[str]]:
    """
    Get default prompt from environment variables.
    
    Checks in priority order:
    1. DEFAULT_PROMPT_TEMPLATE (inline prompt text)
    2. DEFAULT_PROMPT_TEMPLATE_REF (@prompt_templates/... reference)
    
    Args:
        env_settings: Settings object with environment variables
    
    Returns:
        Tuple of (prompt_text, source_description)
    """
    # Check for inline default prompt
    if hasattr(env_settings, 'DEFAULT_PROMPT_TEMPLATE') and env_settings.DEFAULT_PROMPT_TEMPLATE:
        prompt = env_settings.DEFAULT_PROMPT_TEMPLATE
        logger.info(f"Using DEFAULT_PROMPT_TEMPLATE from environment ({len(prompt)} chars)")
        return prompt, "DEFAULT_PROMPT_TEMPLATE"
    
    # Check for file reference default prompt
    if hasattr(env_settings, 'DEFAULT_PROMPT_TEMPLATE_REF') and env_settings.DEFAULT_PROMPT_TEMPLATE_REF:
        ref = env_settings.DEFAULT_PROMPT_TEMPLATE_REF
        logger.info(f"Using DEFAULT_PROMPT_TEMPLATE_REF from environment: {ref}")
        prompt, _ = resolve_prompt_template(ref)
        if prompt:
            return prompt, f"DEFAULT_PROMPT_TEMPLATE_REF ({ref})"
        else:
            logger.error(f"Failed to load prompt from DEFAULT_PROMPT_TEMPLATE_REF: {ref}")
            return None, None
    
    return None, None
