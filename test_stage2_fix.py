#!/usr/bin/env python3
"""
Test script to validate Stage 2 (LLM extraction) fixes.

Tests:
1. Stage 2 with valid config - should generate JSON
2. Stage 2 with missing prompt - should log error
3. Stage 2 with missing API key - should log error and disable
4. Verify stage2_status is properly returned
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app.services.crawler_service import CrawlerService


async def test_stage2_no_config():
    """Test: Stage 2 disabled when no LLM config provided"""
    print("\n" + "="*80)
    print("TEST 1: Stage 2 disabled (no LLM config)")
    print("="*80)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={},
                llm_config=None,
                prompt_template=None,
                output_schema=None
            )
            
            stage2_status = result.get('stage2_status', {})
            
            assert result['success'], "Crawl should succeed"
            assert not stage2_status['enabled'], "Stage 2 should be disabled"
            assert stage2_status['error'] == "No LLM config provided", "Should have correct error message"
            assert result.get('structured_data') is None, "Should have no structured data"
            
            print("✅ PASS: Stage 2 correctly disabled when no LLM config")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stage2_no_prompt():
    """Test: Stage 2 disabled when LLM config present but no prompt"""
    print("\n" + "="*80)
    print("TEST 2: Stage 2 disabled (LLM config but no prompt)")
    print("="*80)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={},
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4",
                    "params": {"api_key": "fake-key"}
                },
                prompt_template=None,  # Missing prompt!
                output_schema=None
            )
            
            stage2_status = result.get('stage2_status', {})
            
            assert result['success'], "Crawl should succeed"
            assert not stage2_status['enabled'], "Stage 2 should be disabled"
            assert stage2_status['error'] == "No prompt_template provided", "Should have correct error message"
            assert result.get('structured_data') is None, "Should have no structured data"
            
            print("✅ PASS: Stage 2 correctly disabled when no prompt template")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stage2_no_api_key():
    """Test: Stage 2 disabled when no API key"""
    print("\n" + "="*80)
    print("TEST 3: Stage 2 disabled (no API key)")
    print("="*80)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={},
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4",
                    "params": {}  # No API key!
                },
                prompt_template="Extract the title and content",
                output_schema=None
            )
            
            stage2_status = result.get('stage2_status', {})
            
            assert result['success'], "Crawl should succeed"
            assert not stage2_status['enabled'], "Stage 2 should be disabled"
            assert "API key" in stage2_status['error'] or "LLMConfig" in stage2_status['error'], "Should mention API key issue"
            assert result.get('structured_data') is None, "Should have no structured data"
            
            print("✅ PASS: Stage 2 correctly disabled when no API key")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stage2_status_structure():
    """Test: Verify stage2_status structure is correct"""
    print("\n" + "="*80)
    print("TEST 4: Verify stage2_status structure")
    print("="*80)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={},
                llm_config=None,
                prompt_template=None,
                output_schema=None
            )
            
            stage2_status = result.get('stage2_status', {})
            
            # Check required fields
            assert 'enabled' in stage2_status, "stage2_status should have 'enabled' field"
            assert 'success' in stage2_status, "stage2_status should have 'success' field"
            assert 'error' in stage2_status, "stage2_status should have 'error' field"
            assert 'output_size_bytes' in stage2_status, "stage2_status should have 'output_size_bytes' field"
            
            # Check types
            assert isinstance(stage2_status['enabled'], bool), "'enabled' should be boolean"
            assert isinstance(stage2_status['success'], bool), "'success' should be boolean"
            assert isinstance(stage2_status['error'], (str, type(None))), "'error' should be string or None"
            assert isinstance(stage2_status['output_size_bytes'], (int, type(None))), "'output_size_bytes' should be int or None"
            
            print("✅ PASS: stage2_status structure is correct")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("="*80)
    print("Stage 2 Fix Validation Tests")
    print("="*80)
    
    results = []
    
    # Run tests
    results.append(await test_stage2_no_config())
    results.append(await test_stage2_no_prompt())
    results.append(await test_stage2_no_api_key())
    results.append(await test_stage2_status_structure())
    
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
    import sys
    sys.exit(asyncio.run(main()))
