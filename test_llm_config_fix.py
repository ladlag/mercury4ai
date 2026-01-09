#!/usr/bin/env python3
"""
Test script to verify LLMConfig compatibility with crawl4ai 0.7.8+
Tests the build_llm_config function and LLMExtractionStrategy creation.
"""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the function we want to test
from app.services.crawler_service import build_llm_config, LLMCONFIG_AVAILABLE

def test_llm_config_availability():
    """Test that LLMConfig is available"""
    print("\n=== Test 1: LLMConfig Availability ===")
    if LLMCONFIG_AVAILABLE:
        print("✅ LLMConfig is available")
        return True
    else:
        print("❌ LLMConfig is not available - crawl4ai 0.7.8+ required")
        return False

def test_build_llm_config_standard():
    """Test building LLMConfig for standard providers"""
    print("\n=== Test 2: Build LLMConfig for Standard Provider ===")
    
    provider = "openai"
    model = "gpt-4"
    params = {
        "api_key": "test-key-123",
        "temperature": 0.1,
        "max_tokens": 4000
    }
    
    llm_config = build_llm_config(provider, model, params)
    
    if llm_config is None:
        print("❌ Failed to create LLMConfig")
        return False
    
    print(f"✅ LLMConfig created: provider={llm_config.provider}")
    print(f"   - api_token: {'***' + llm_config.api_token[-4:] if llm_config.api_token else 'None'}")
    print(f"   - temperature: {llm_config.temperature}")
    print(f"   - max_tokens: {llm_config.max_tokens}")
    return True

def test_build_llm_config_deepseek():
    """Test building LLMConfig for DeepSeek (Chinese provider)"""
    print("\n=== Test 3: Build LLMConfig for DeepSeek ===")
    
    provider = "openai"
    model = "deepseek-chat"
    params = {
        "api_key": "sk-deepseek-test-key",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.1,
        "max_tokens": 4000
    }
    
    llm_config = build_llm_config(provider, model, params)
    
    if llm_config is None:
        print("❌ Failed to create LLMConfig")
        return False
    
    print(f"✅ LLMConfig created: provider={llm_config.provider}")
    print(f"   - base_url: {llm_config.base_url}")
    print(f"   - api_token: {'***' + llm_config.api_token[-4:] if llm_config.api_token else 'None'}")
    return True

def test_build_llm_config_qwen():
    """Test building LLMConfig for Qwen (Chinese provider)"""
    print("\n=== Test 4: Build LLMConfig for Qwen ===")
    
    provider = "qwen"
    model = "qwen-turbo"
    params = {
        "api_key": "sk-qwen-test-key",
        "temperature": 0.1
    }
    
    llm_config = build_llm_config(provider, model, params)
    
    if llm_config is None:
        print("❌ Failed to create LLMConfig")
        return False
    
    print(f"✅ LLMConfig created: provider={llm_config.provider}")
    print(f"   - Expected provider format: openai/qwen-turbo")
    print(f"   - base_url: {llm_config.base_url}")
    return True

def test_build_llm_config_no_api_key():
    """Test that build_llm_config returns None when no API key is provided"""
    print("\n=== Test 5: Build LLMConfig Without API Key ===")
    
    provider = "openai"
    model = "gpt-4"
    params = {}  # No api_key
    
    llm_config = build_llm_config(provider, model, params)
    
    if llm_config is None:
        print("✅ Correctly returned None when no API key provided")
        return True
    else:
        print("❌ Should have returned None")
        return False

def test_llm_extraction_strategy():
    """Test creating LLMExtractionStrategy with LLMConfig"""
    print("\n=== Test 6: Create LLMExtractionStrategy ===")
    
    try:
        from crawl4ai.extraction_strategy import LLMExtractionStrategy
        
        provider = "openai"
        model = "gpt-4"
        params = {
            "api_key": "test-key-123",
            "temperature": 0.1
        }
        
        llm_config = build_llm_config(provider, model, params)
        
        if llm_config is None:
            print("❌ Failed to create LLMConfig")
            return False
        
        # Create extraction strategy
        strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction="Extract the title and content",
            schema={"type": "object", "properties": {"title": {"type": "string"}}}
        )
        
        print(f"✅ LLMExtractionStrategy created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create LLMExtractionStrategy: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_old_way_should_fail():
    """Test that the old way (provider= parameter) fails as expected"""
    print("\n=== Test 7: Old Way Should Fail ===")
    
    try:
        from crawl4ai.extraction_strategy import LLMExtractionStrategy
        
        # Try the old way (should fail)
        strategy = LLMExtractionStrategy(
            provider="openai/gpt-4",
            api_token="test-key",
            instruction="Extract the title"
        )
        
        print("❌ Old way did not fail - unexpected!")
        return False
        
    except AttributeError as e:
        if "deprecated" in str(e).lower():
            print(f"✅ Old way correctly fails with AttributeError: {e}")
            return True
        else:
            print(f"❌ Unexpected AttributeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing LLMConfig Fix for crawl4ai 0.7.8+")
    print("=" * 60)
    
    tests = [
        test_llm_config_availability,
        test_build_llm_config_standard,
        test_build_llm_config_deepseek,
        test_build_llm_config_qwen,
        test_build_llm_config_no_api_key,
        test_llm_extraction_strategy,
        test_old_way_should_fail,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {len(results) - sum(results)} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
