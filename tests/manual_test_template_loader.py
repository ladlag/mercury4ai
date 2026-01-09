#!/usr/bin/env python3
"""
Manual test script for template loader functionality.

This script tests the core template loading functions without
requiring the full application stack.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.template_loader import (
    resolve_prompt_template,
    resolve_output_schema,
    get_default_prompt_from_env
)


class MockSettings:
    """Mock settings for testing"""
    def __init__(self):
        self.DEFAULT_PROMPT_TEMPLATE = None
        self.DEFAULT_PROMPT_TEMPLATE_REF = None


def test_section(name):
    """Print test section header"""
    print("\n" + "=" * 80)
    print(f"TEST: {name}")
    print("=" * 80)


def test_inline_prompt():
    """Test inline prompt resolution"""
    test_section("Inline Prompt")
    
    inline = "Extract title, content, and metadata from this page"
    prompt, source = resolve_prompt_template(inline)
    
    print(f"Input: {inline}")
    print(f"✓ Resolved prompt: {prompt[:50]}...")
    print(f"✓ Source: {source}")
    assert prompt == inline
    assert source == "inline"


def test_prompt_file_reference():
    """Test prompt file reference resolution"""
    test_section("Prompt File Reference")
    
    ref = "@prompt_templates/news_article_zh.txt"
    prompt, source = resolve_prompt_template(ref)
    
    print(f"Input: {ref}")
    if prompt:
        print(f"✓ Successfully loaded prompt ({len(prompt)} chars)")
        print(f"✓ Source: {source}")
        print(f"Preview: {prompt[:100]}...")
    else:
        print(f"✗ Failed to load prompt")
    
    assert prompt is not None


def test_prompt_file_not_found():
    """Test prompt file reference with non-existent file"""
    test_section("Prompt File Not Found (Expected Error)")
    
    ref = "@prompt_templates/nonexistent.txt"
    prompt, source = resolve_prompt_template(ref)
    
    print(f"Input: {ref}")
    print(f"✓ Correctly returned None for missing file")
    assert prompt is None
    assert source is None


def test_inline_schema():
    """Test inline schema resolution"""
    test_section("Inline Schema")
    
    inline = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"}
        }
    }
    schema, source = resolve_output_schema(inline)
    
    print(f"Input: {inline}")
    print(f"✓ Resolved schema: {schema}")
    print(f"✓ Source: {source}")
    assert schema == inline
    assert source == "inline"


def test_schema_file_reference():
    """Test schema file reference resolution"""
    test_section("Schema File Reference")
    
    ref = "@schemas/news_article_zh.json"
    schema, source = resolve_output_schema(ref)
    
    print(f"Input: {ref}")
    if schema:
        print(f"✓ Successfully loaded schema")
        print(f"✓ Source: {source}")
        print(f"✓ Schema type: {schema.get('type')}")
        print(f"✓ Properties: {list(schema.get('properties', {}).keys())}")
    else:
        print(f"✗ Failed to load schema")
    
    assert schema is not None
    assert isinstance(schema, dict)


def test_schema_file_not_found():
    """Test schema file reference with non-existent file"""
    test_section("Schema File Not Found (Expected Error)")
    
    ref = "@schemas/nonexistent.json"
    schema, source = resolve_output_schema(ref)
    
    print(f"Input: {ref}")
    print(f"✓ Correctly returned None for missing file")
    assert schema is None
    assert source is None


def test_default_prompt_inline():
    """Test default prompt with inline template"""
    test_section("Default Prompt - Inline")
    
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE = "This is the default inline prompt"
    
    prompt, source = get_default_prompt_from_env(settings)
    
    print(f"DEFAULT_PROMPT_TEMPLATE: {settings.DEFAULT_PROMPT_TEMPLATE}")
    print(f"✓ Resolved prompt: {prompt}")
    print(f"✓ Source: {source}")
    assert prompt == settings.DEFAULT_PROMPT_TEMPLATE
    assert source == "DEFAULT_PROMPT_TEMPLATE"


def test_default_prompt_ref():
    """Test default prompt with file reference"""
    test_section("Default Prompt - File Reference")
    
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE_REF = "@prompt_templates/news_article_zh.txt"
    
    prompt, source = get_default_prompt_from_env(settings)
    
    print(f"DEFAULT_PROMPT_TEMPLATE_REF: {settings.DEFAULT_PROMPT_TEMPLATE_REF}")
    if prompt:
        print(f"✓ Successfully loaded prompt ({len(prompt)} chars)")
        print(f"✓ Source: {source}")
    else:
        print(f"✗ Failed to load prompt")
    
    assert prompt is not None


def test_default_prompt_priority():
    """Test default prompt priority (inline > ref)"""
    test_section("Default Prompt - Priority Test")
    
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE = "Inline prompt"
    settings.DEFAULT_PROMPT_TEMPLATE_REF = "@prompt_templates/news_article_zh.txt"
    
    prompt, source = get_default_prompt_from_env(settings)
    
    print(f"DEFAULT_PROMPT_TEMPLATE: {settings.DEFAULT_PROMPT_TEMPLATE}")
    print(f"DEFAULT_PROMPT_TEMPLATE_REF: {settings.DEFAULT_PROMPT_TEMPLATE_REF}")
    print(f"✓ Inline has priority - resolved to: {source}")
    assert source == "DEFAULT_PROMPT_TEMPLATE"
    assert prompt == "Inline prompt"


def test_security_path_traversal():
    """Test security against path traversal attacks"""
    test_section("Security - Path Traversal Protection")
    
    # Test prompt template
    ref = "@prompt_templates/../../../etc/passwd"
    prompt, source = resolve_prompt_template(ref)
    print(f"Input: {ref}")
    print(f"✓ Path traversal blocked - returned None")
    assert prompt is None
    
    # Test schema
    ref = "@schemas/../../etc/passwd"
    schema, source = resolve_output_schema(ref)
    print(f"Input: {ref}")
    print(f"✓ Path traversal blocked - returned None")
    assert schema is None


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Template Loader Manual Test Suite")
    print("=" * 80)
    
    try:
        test_inline_prompt()
        test_prompt_file_reference()
        test_prompt_file_not_found()
        test_inline_schema()
        test_schema_file_reference()
        test_schema_file_not_found()
        test_default_prompt_inline()
        test_default_prompt_ref()
        test_default_prompt_priority()
        test_security_path_traversal()
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80 + "\n")
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
