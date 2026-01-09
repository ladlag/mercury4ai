"""
Template and schema file reference resolver.

This module handles resolving file references like:
- @prompt_templates/news_article.txt
- @schemas/news_article.json

to their actual file contents.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

# Base directories for templates and schemas
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROMPT_TEMPLATES_DIR = PROJECT_ROOT / "prompt_templates"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def resolve_file_reference(value: str) -> str:
    """
    Resolve a file reference to its content.
    
    Args:
        value: Either a file reference (starting with @) or inline content
        
    Returns:
        The file content if it's a reference, otherwise the original value
        
    Raises:
        FileNotFoundError: If the referenced file doesn't exist
        ValueError: If the reference format is invalid
    """
    if not value or not isinstance(value, str):
        return value
    
    # Check if this is a file reference
    if not value.startswith('@'):
        return value
    
    # Parse the reference
    try:
        # Format: @prompt_templates/file.txt or @schemas/file.json
        parts = value[1:].split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid file reference format: {value}. Expected format: @directory/filename")
        
        directory_name, filename = parts
        
        # Determine base directory
        if directory_name == "prompt_templates":
            base_dir = PROMPT_TEMPLATES_DIR
        elif directory_name == "schemas":
            base_dir = SCHEMAS_DIR
        else:
            raise ValueError(f"Invalid directory in reference: {value}. Must be @prompt_templates or @schemas")
        
        # Construct file path
        file_path = base_dir / filename
        
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Referenced file not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Referenced path is not a file: {file_path}")
        
        # Read and return content
        logger.info(f"Resolving file reference: {value} -> {file_path}")
        content = file_path.read_text(encoding='utf-8')
        
        return content
        
    except Exception as e:
        logger.error(f"Error resolving file reference '{value}': {str(e)}")
        raise


def resolve_schema_reference(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Resolve a schema reference to its content.
    
    Args:
        value: Either a dict with schema, a string reference, or None
        
    Returns:
        The schema dict if resolved, otherwise the original value
        
    Raises:
        FileNotFoundError: If the referenced file doesn't exist
        ValueError: If the reference format is invalid or JSON is invalid
    """
    if value is None:
        return None
    
    # If it's already a dict, return as-is
    if isinstance(value, dict):
        return value
    
    # If it's a string reference, resolve it
    if isinstance(value, str) and value.startswith('@'):
        content = resolve_file_reference(value)
        try:
            schema = json.loads(content)
            logger.info(f"Successfully loaded schema from reference: {value}")
            return schema
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file {value}: {str(e)}")
    
    # If it's just a string but not a reference, it's invalid
    if isinstance(value, str):
        raise ValueError(f"Invalid schema format: expected dict or @schemas/ reference, got string: {value[:50]}...")
    
    return value


def resolve_template_in_task_data(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve all template and schema references in task data.
    
    This function modifies the task_data dict in-place to resolve:
    - prompt_template: @prompt_templates/file.txt
    - output_schema: @schemas/file.json
    
    Args:
        task_data: Task configuration dict
        
    Returns:
        Modified task_data with resolved references
        
    Raises:
        FileNotFoundError: If a referenced file doesn't exist
        ValueError: If a reference format is invalid
    """
    # Resolve prompt_template reference
    if 'prompt_template' in task_data and task_data['prompt_template']:
        try:
            original_value = task_data['prompt_template']
            resolved = resolve_file_reference(original_value)
            if resolved != original_value:
                logger.info(f"Resolved prompt_template reference: {len(resolved)} characters")
            task_data['prompt_template'] = resolved
        except Exception as e:
            logger.error(f"Failed to resolve prompt_template reference: {str(e)}")
            raise
    
    # Resolve output_schema reference
    if 'output_schema' in task_data and task_data['output_schema']:
        try:
            original_value = task_data['output_schema']
            resolved = resolve_schema_reference(original_value)
            if resolved != original_value:
                logger.info(f"Resolved output_schema reference")
            task_data['output_schema'] = resolved
        except Exception as e:
            logger.error(f"Failed to resolve output_schema reference: {str(e)}")
            raise
    
    return task_data
