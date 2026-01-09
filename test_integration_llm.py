#!/usr/bin/env python3
"""
Integration test to verify the full crawler workflow with LLM extraction.
This simulates the actual usage pattern in the mercury4ai application.
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

async def test_crawl_without_llm():
    """Test crawling without LLM extraction (Stage 1 only)"""
    print("\n" + "="*60)
    print("Test 1: Crawl without LLM extraction (Stage 1 only)")
    print("="*60)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={
                    "verbose": True,
                },
                llm_config=None,
                prompt_template=None,
                output_schema=None
            )
            
            if result['success']:
                print(f"✅ Crawl succeeded without LLM")
                print(f"   - URL: {result['url']}")
                print(f"   - Title: {result['metadata'].get('title', 'N/A')}")
                print(f"   - Markdown length: {len(result.get('markdown', '')) if result.get('markdown') else 0}")
                print(f"   - Structured data: {result.get('structured_data', 'None')}")
                return True
            else:
                print(f"❌ Crawl failed: {result.get('error')}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_crawl_with_llm_no_api_key():
    """Test crawling with LLM config but no API key (should fall back to Stage 1)"""
    print("\n" + "="*60)
    print("Test 2: Crawl with LLM config but no API key")
    print("="*60)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={
                    "verbose": True,
                },
                llm_config={
                    "provider": "openai",
                    "model": "gpt-4",
                    "params": {}  # No API key
                },
                prompt_template="Extract the title and content",
                output_schema=None
            )
            
            if result['success']:
                print(f"✅ Crawl succeeded (fell back to Stage 1)")
                print(f"   - URL: {result['url']}")
                print(f"   - Markdown length: {len(result.get('markdown', '')) if result.get('markdown') else 0}")
                print(f"   - Structured data: {result.get('structured_data', 'None')}")
                
                # Should not have structured data since LLM was skipped
                if result.get('structured_data') is None:
                    print(f"✅ Correctly has no structured data (LLM was skipped)")
                    return True
                else:
                    print(f"❌ Unexpectedly has structured data")
                    return False
            else:
                print(f"❌ Crawl failed: {result.get('error')}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_crawl_with_invalid_llm_config():
    """Test crawling with invalid LLM config (should fall back to Stage 1)"""
    print("\n" + "="*60)
    print("Test 3: Crawl with invalid LLM config")
    print("="*60)
    
    try:
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={
                    "verbose": True,
                },
                llm_config={
                    "provider": "invalid_provider",
                    "model": "invalid_model",
                    "params": {"api_key": "fake-key"}
                },
                prompt_template="Extract the title and content",
                output_schema=None
            )
            
            if result['success']:
                print(f"✅ Crawl succeeded despite invalid LLM config")
                print(f"   - URL: {result['url']}")
                print(f"   - Markdown length: {len(result.get('markdown', '')) if result.get('markdown') else 0}")
                return True
            else:
                print(f"❌ Crawl failed: {result.get('error')}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_llm_config_construction():
    """Test that LLMConfig is constructed correctly for various providers"""
    print("\n" + "="*60)
    print("Test 4: LLMConfig Construction for Various Providers")
    print("="*60)
    
    from app.services.crawler_service import build_llm_config
    
    test_cases = [
        {
            "name": "OpenAI GPT-4",
            "provider": "openai",
            "model": "gpt-4",
            "params": {"api_key": "sk-test-key", "temperature": 0.1}
        },
        {
            "name": "DeepSeek",
            "provider": "openai",
            "model": "deepseek-chat",
            "params": {
                "api_key": "sk-deepseek-key",
                "base_url": "https://api.deepseek.com",
                "temperature": 0.1
            }
        },
        {
            "name": "Qwen",
            "provider": "qwen",
            "model": "qwen-turbo",
            "params": {
                "api_key": "sk-qwen-key",
                "temperature": 0.1
            }
        }
    ]
    
    all_passed = True
    for test_case in test_cases:
        llm_config = build_llm_config(
            test_case["provider"],
            test_case["model"],
            test_case["params"]
        )
        
        if llm_config is not None:
            print(f"✅ {test_case['name']}: LLMConfig created")
            print(f"   - Provider: {llm_config.provider}")
            if hasattr(llm_config, 'base_url') and llm_config.base_url:
                print(f"   - Base URL: {llm_config.base_url}")
        else:
            print(f"❌ {test_case['name']}: Failed to create LLMConfig")
            all_passed = False
    
    return all_passed

async def main():
    """Run all integration tests"""
    print("="*60)
    print("Integration Tests for LLM Extraction Fix")
    print("="*60)
    
    # Run tests
    results = []
    
    # Test 1: Crawl without LLM
    results.append(await test_crawl_without_llm())
    
    # Test 2: Crawl with LLM but no API key
    results.append(await test_crawl_with_llm_no_api_key())
    
    # Test 3: Crawl with invalid LLM config
    results.append(await test_crawl_with_invalid_llm_config())
    
    # Test 4: LLMConfig construction
    results.append(await test_llm_config_construction())
    
    print("\n" + "="*60)
    print(f"Integration Test Results: {sum(results)}/{len(results)} passed")
    print("="*60)
    
    if all(results):
        print("\n✅ All integration tests passed!")
        return 0
    else:
        print(f"\n❌ {len(results) - sum(results)} test(s) failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
