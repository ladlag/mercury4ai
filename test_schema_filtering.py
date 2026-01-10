#!/usr/bin/env python3
"""
Unit tests for schema filtering functionality.

Tests:
1. Schema filtering removes extra fields
2. Schema filtering keeps only defined properties
3. Missing required fields are detected
4. Schema filtering works with no schema
5. Schema filtering works with empty data
"""

import sys
from typing import Dict, Any, List, Optional, Tuple


def filter_by_schema(
    data: Dict[str, Any],
    output_schema: Optional[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Filter extracted data to match output schema strictly.
    
    This ensures that:
    1. Only properties defined in schema are kept
    2. Extra fields (like 'error') are removed
    3. Returns list of missing required fields for validation
    
    Args:
        data: Raw extracted data from LLM
        output_schema: JSON Schema with 'properties' and optional 'required' fields
    
    Returns:
        Tuple of (filtered_data, missing_required_fields)
        - filtered_data: Dictionary with only schema-defined properties
        - missing_required_fields: List of required field names that are missing
    """
    if not output_schema or not isinstance(data, dict):
        return data, []
    
    # Get schema properties and required fields
    schema_properties = output_schema.get('properties', {})
    required_fields = output_schema.get('required', [])
    
    if not schema_properties:
        # No properties defined in schema, return as-is
        return data, []
    
    # Filter data to only include schema-defined properties
    filtered_data = {}
    for key in schema_properties.keys():
        if key in data:
            filtered_data[key] = data[key]
    
    # Check for missing required fields
    missing_required = [field for field in required_fields if field not in filtered_data]
    
    return filtered_data, missing_required


def test_schema_filtering_removes_extra_fields():
    """Test: Extra fields like 'error' are removed"""
    print("\n" + "="*80)
    print("TEST 1: Schema filtering removes extra fields")
    print("="*80)
    
    try:
        # LLM returned data with extra 'error' field
        llm_data = {
            'title': 'Test Article',
            'error': False  # This should be removed
        }
        
        # Schema only defines 'title'
        schema = {
            'properties': {
                'title': {'type': 'string'}
            },
            'required': ['title']
        }
        
        filtered_data, missing_required = filter_by_schema(llm_data, schema)
        
        # Assertions
        assert 'title' in filtered_data, "title should be in filtered data"
        assert 'error' not in filtered_data, "error field should be removed"
        assert filtered_data['title'] == 'Test Article', "title value should be preserved"
        assert len(missing_required) == 0, "No required fields should be missing"
        
        print(f"✅ PASS: Extra 'error' field correctly removed")
        print(f"   Input keys: {list(llm_data.keys())}")
        print(f"   Output keys: {list(filtered_data.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_filtering_keeps_defined_properties():
    """Test: All schema-defined properties are kept"""
    print("\n" + "="*80)
    print("TEST 2: Schema filtering keeps all defined properties")
    print("="*80)
    
    try:
        llm_data = {
            'title': 'Test Article',
            'content': 'Article content here',
            'author': 'John Doe',
            'published_date': '2024-01-01',
            'error': False,  # Extra field
            'metadata': {'foo': 'bar'}  # Extra field
        }
        
        schema = {
            'properties': {
                'title': {'type': 'string'},
                'content': {'type': 'string'},
                'author': {'type': 'string'},
                'published_date': {'type': 'string'}
            },
            'required': ['title', 'content']
        }
        
        filtered_data, missing_required = filter_by_schema(llm_data, schema)
        
        # Assertions
        assert 'title' in filtered_data, "title should be in filtered data"
        assert 'content' in filtered_data, "content should be in filtered data"
        assert 'author' in filtered_data, "author should be in filtered data"
        assert 'published_date' in filtered_data, "published_date should be in filtered data"
        assert 'error' not in filtered_data, "error field should be removed"
        assert 'metadata' not in filtered_data, "metadata field should be removed"
        assert len(missing_required) == 0, "No required fields should be missing"
        
        print(f"✅ PASS: All defined properties kept, extra fields removed")
        print(f"   Input keys: {list(llm_data.keys())}")
        print(f"   Output keys: {list(filtered_data.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missing_required_fields_detected():
    """Test: Missing required fields are detected"""
    print("\n" + "="*80)
    print("TEST 3: Missing required fields are detected")
    print("="*80)
    
    try:
        # LLM only returned title, missing required 'content'
        llm_data = {
            'title': 'Test Article',
            'author': 'John Doe',  # Optional field
            'error': False
        }
        
        schema = {
            'properties': {
                'title': {'type': 'string'},
                'content': {'type': 'string'},
                'author': {'type': 'string'}
            },
            'required': ['title', 'content']  # content is required
        }
        
        filtered_data, missing_required = filter_by_schema(llm_data, schema)
        
        # Assertions
        assert 'title' in filtered_data, "title should be in filtered data"
        assert 'author' in filtered_data, "author should be in filtered data"
        assert 'content' not in filtered_data, "content should not be in filtered data (missing)"
        assert 'error' not in filtered_data, "error field should be removed"
        assert len(missing_required) == 1, "Should detect 1 missing required field"
        assert 'content' in missing_required, "content should be in missing_required list"
        
        print(f"✅ PASS: Missing required field 'content' correctly detected")
        print(f"   Missing required: {missing_required}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_filtering_no_schema():
    """Test: No filtering when schema is not provided"""
    print("\n" + "="*80)
    print("TEST 4: Schema filtering with no schema (passthrough)")
    print("="*80)
    
    try:
        llm_data = {
            'title': 'Test Article',
            'error': False,
            'anything': 'goes'
        }
        
        # No schema provided
        filtered_data, missing_required = filter_by_schema(llm_data, None)
        
        # Assertions
        assert filtered_data == llm_data, "Data should be unchanged when no schema"
        assert len(missing_required) == 0, "No required fields when no schema"
        
        print(f"✅ PASS: Data passes through unchanged when no schema")
        print(f"   Keys: {list(filtered_data.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_filtering_empty_properties():
    """Test: Schema with no properties defined"""
    print("\n" + "="*80)
    print("TEST 5: Schema filtering with empty properties")
    print("="*80)
    
    try:
        llm_data = {
            'title': 'Test Article',
            'content': 'Content here'
        }
        
        # Schema with no properties
        schema = {
            'properties': {},
            'required': []
        }
        
        filtered_data, missing_required = filter_by_schema(llm_data, schema)
        
        # Assertions
        assert filtered_data == llm_data, "Data should be unchanged when no properties in schema"
        assert len(missing_required) == 0, "No required fields"
        
        print(f"✅ PASS: Data passes through when schema has no properties")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_filtering_all_fields_missing():
    """Test: All required fields missing"""
    print("\n" + "="*80)
    print("TEST 6: All required fields missing")
    print("="*80)
    
    try:
        llm_data = {
            'error': False,
            'status': 'success'
        }
        
        schema = {
            'properties': {
                'title': {'type': 'string'},
                'content': {'type': 'string'}
            },
            'required': ['title', 'content']
        }
        
        filtered_data, missing_required = filter_by_schema(llm_data, schema)
        
        # Assertions
        assert len(filtered_data) == 0, "Filtered data should be empty"
        assert len(missing_required) == 2, "Should detect 2 missing required fields"
        assert 'title' in missing_required, "title should be in missing_required"
        assert 'content' in missing_required, "content should be in missing_required"
        
        print(f"✅ PASS: All missing required fields correctly detected")
        print(f"   Missing required: {missing_required}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_filtering_optional_fields():
    """Test: Optional fields can be missing"""
    print("\n" + "="*80)
    print("TEST 7: Optional fields can be missing")
    print("="*80)
    
    try:
        llm_data = {
            'title': 'Test Article',
            'content': 'Content here'
            # author is optional and missing
        }
        
        schema = {
            'properties': {
                'title': {'type': 'string'},
                'content': {'type': 'string'},
                'author': {'type': 'string'}  # Optional
            },
            'required': ['title', 'content']
        }
        
        filtered_data, missing_required = filter_by_schema(llm_data, schema)
        
        # Assertions
        assert 'title' in filtered_data, "title should be in filtered data"
        assert 'content' in filtered_data, "content should be in filtered data"
        assert 'author' not in filtered_data, "author should not be in filtered data (was missing)"
        assert len(missing_required) == 0, "No required fields missing"
        
        print(f"✅ PASS: Optional fields can be missing without error")
        print(f"   Output keys: {list(filtered_data.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*80)
    print("Schema Filtering Unit Tests")
    print("="*80)
    
    results = []
    
    # Run all tests
    results.append(test_schema_filtering_removes_extra_fields())
    results.append(test_schema_filtering_keeps_defined_properties())
    results.append(test_missing_required_fields_detected())
    results.append(test_schema_filtering_no_schema())
    results.append(test_schema_filtering_empty_properties())
    results.append(test_schema_filtering_all_fields_missing())
    results.append(test_schema_filtering_optional_fields())
    
    print("\n" + "="*80)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("="*80)
    
    if all(results):
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {len(results) - sum(results)} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
