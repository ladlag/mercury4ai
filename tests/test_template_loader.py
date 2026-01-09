"""
Unit tests for template_loader service.

These tests verify the functionality of template and schema loading,
including file references, inline values, and error handling.

To run tests:
    pip install pytest
    pytest tests/test_template_loader.py -v
"""

import json
import tempfile
from pathlib import Path
import pytest

from app.services.template_loader import (
    resolve_prompt_template,
    resolve_output_schema,
    get_default_prompt_from_env,
    PROMPT_TEMPLATES_DIR,
    SCHEMAS_DIR
)


class MockSettings:
    """Mock settings object for testing default prompt logic"""
    def __init__(self):
        self.DEFAULT_PROMPT_TEMPLATE = None
        self.DEFAULT_PROMPT_TEMPLATE_REF = None


def test_resolve_prompt_template_inline():
    """Test resolving inline prompt template"""
    inline_prompt = "Extract title and content from the page"
    prompt, source = resolve_prompt_template(inline_prompt)
    
    assert prompt == inline_prompt
    assert source == "inline"


def test_resolve_prompt_template_none():
    """Test resolving None prompt template"""
    prompt, source = resolve_prompt_template(None)
    
    assert prompt is None
    assert source is None


def test_resolve_prompt_template_file_success():
    """Test resolving prompt from existing file"""
    # This tests with actual files in the repository
    # Assuming news_article_zh.txt exists
    ref = "@prompt_templates/news_article_zh.txt"
    prompt, source = resolve_prompt_template(ref)
    
    if (PROMPT_TEMPLATES_DIR / "news_article_zh.txt").exists():
        assert prompt is not None
        assert len(prompt) > 0
        assert source == ref
    else:
        # File doesn't exist, should return None
        assert prompt is None
        assert source is None


def test_resolve_prompt_template_file_not_found():
    """Test resolving prompt from non-existent file"""
    ref = "@prompt_templates/nonexistent_file.txt"
    prompt, source = resolve_prompt_template(ref)
    
    assert prompt is None
    assert source is None


def test_resolve_output_schema_inline():
    """Test resolving inline output schema"""
    inline_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"}
        }
    }
    schema, source = resolve_output_schema(inline_schema)
    
    assert schema == inline_schema
    assert source == "inline"


def test_resolve_output_schema_none():
    """Test resolving None output schema"""
    schema, source = resolve_output_schema(None)
    
    assert schema is None
    assert source is None


def test_resolve_output_schema_file_success():
    """Test resolving schema from existing file"""
    # This tests with actual files in the repository
    # Assuming news_article_zh.json exists
    ref = "@schemas/news_article_zh.json"
    schema, source = resolve_output_schema(ref)
    
    if (SCHEMAS_DIR / "news_article_zh.json").exists():
        assert schema is not None
        assert isinstance(schema, dict)
        assert source == ref
    else:
        # File doesn't exist, should return None
        assert schema is None
        assert source is None


def test_resolve_output_schema_file_not_found():
    """Test resolving schema from non-existent file"""
    ref = "@schemas/nonexistent_file.json"
    schema, source = resolve_output_schema(ref)
    
    assert schema is None
    assert source is None


def test_resolve_output_schema_invalid_json():
    """Test resolving schema from file with invalid JSON"""
    # Create a temporary invalid JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir=SCHEMAS_DIR) as f:
        f.write("{invalid json content")
        temp_file = Path(f.name)
    
    try:
        ref = f"@schemas/{temp_file.name}"
        schema, source = resolve_output_schema(ref)
        
        # Should return None for invalid JSON
        assert schema is None
        assert source is None
    finally:
        # Clean up
        if temp_file.exists():
            temp_file.unlink()


def test_resolve_output_schema_invalid_type():
    """Test resolving schema with invalid type (string that doesn't start with @schemas/)"""
    schema, source = resolve_output_schema("not a valid reference")
    
    # String that doesn't start with @schemas/ is invalid
    assert schema is None
    assert source is None


def test_get_default_prompt_inline_priority():
    """Test default prompt with inline template having priority"""
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE = "Inline prompt template"
    settings.DEFAULT_PROMPT_TEMPLATE_REF = "@prompt_templates/news_article_zh.txt"
    
    prompt, source = get_default_prompt_from_env(settings)
    
    # Inline should have priority
    assert prompt == "Inline prompt template"
    assert source == "DEFAULT_PROMPT_TEMPLATE"


def test_get_default_prompt_ref_fallback():
    """Test default prompt falling back to ref when inline is not set"""
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE = None
    settings.DEFAULT_PROMPT_TEMPLATE_REF = "@prompt_templates/news_article_zh.txt"
    
    prompt, source = get_default_prompt_from_env(settings)
    
    if (PROMPT_TEMPLATES_DIR / "news_article_zh.txt").exists():
        # Should load from file reference
        assert prompt is not None
        assert "DEFAULT_PROMPT_TEMPLATE_REF" in source
    else:
        # File doesn't exist
        assert prompt is None


def test_get_default_prompt_none():
    """Test default prompt when neither is set"""
    settings = MockSettings()
    
    prompt, source = get_default_prompt_from_env(settings)
    
    assert prompt is None
    assert source is None


def test_security_path_traversal_prompt():
    """Test security: prevent path traversal in prompt template"""
    ref = "@prompt_templates/../../../etc/passwd"
    prompt, source = resolve_prompt_template(ref)
    
    # Should be blocked by security check
    assert prompt is None
    assert source is None


def test_security_path_traversal_schema():
    """Test security: prevent path traversal in schema"""
    ref = "@schemas/../../../etc/passwd"
    schema, source = resolve_output_schema(ref)
    
    # Should be blocked by security check
    assert schema is None
    assert source is None


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
