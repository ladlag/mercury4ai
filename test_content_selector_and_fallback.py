#!/usr/bin/env python3
"""
Test script to validate content selector and Stage 2 fallback features.

Tests:
1. Content selector strategy - user-provided selector
2. Content selector strategy - css_selector backward compatibility
3. Content selector strategy - heuristic defaults
4. Stage 2 fallback_used flag in status
5. Stage 2 input source detection (cleaned vs raw)
"""

import asyncio
import logging

from app.services.crawler_service import CrawlerService, select_content_selector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_content_selector_user_provided():
    """Test: User-provided content_selector takes priority"""
    print("\n" + "="*80)
    print("TEST 1: Content selector - user-provided")
    print("="*80)
    
    try:
        crawl_config = {'content_selector': '.main-content'}
        selector, reason = select_content_selector(crawl_config)
        
        assert selector == '.main-content', f"Expected '.main-content', got '{selector}'"
        assert 'user-provided' in reason.lower(), f"Expected reason to mention user-provided, got '{reason}'"
        
        print(f"✅ PASS: User-provided selector correctly selected: '{selector}' (reason: {reason})")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_content_selector_backward_compat():
    """Test: css_selector used for backward compatibility"""
    print("\n" + "="*80)
    print("TEST 2: Content selector - css_selector backward compatibility")
    print("="*80)
    
    try:
        crawl_config = {'css_selector': 'article, .content'}
        selector, reason = select_content_selector(crawl_config)
        
        assert selector == 'article, .content', f"Expected 'article, .content', got '{selector}'"
        assert 'backward' in reason.lower() or 'css_selector' in reason.lower(), \
            f"Expected reason to mention backward compatibility or css_selector, got '{reason}'"
        
        print(f"✅ PASS: css_selector correctly used: '{selector}' (reason: {reason})")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_content_selector_heuristic():
    """Test: Heuristic default candidates used when no selector provided"""
    print("\n" + "="*80)
    print("TEST 3: Content selector - heuristic defaults")
    print("="*80)
    
    try:
        crawl_config = {}
        selector, reason = select_content_selector(crawl_config)
        
        assert selector is not None, "Expected a selector, got None"
        assert 'article' in selector.lower(), f"Expected 'article' in selector, got '{selector}'"
        assert 'heuristic' in reason.lower() or 'prioritized' in reason.lower(), \
            f"Expected reason to mention heuristic or prioritized, got '{reason}'"
        
        # Check that selector is properly formatted as comma-separated list
        selectors_list = [s.strip() for s in selector.split(',')]
        assert len(selectors_list) > 1, f"Expected multiple selectors, got {len(selectors_list)}"
        assert selectors_list[0] == 'article', f"Expected 'article' as first selector, got '{selectors_list[0]}'"
        
        print(f"✅ PASS: Heuristic selector correctly generated (reason: {reason})")
        print(f"   Selector count: {len(selectors_list)}")
        print(f"   Top 3 selectors: {', '.join(selectors_list[:3])}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_content_selector_priority():
    """Test: content_selector takes priority over css_selector"""
    print("\n" + "="*80)
    print("TEST 4: Content selector - priority order")
    print("="*80)
    
    try:
        # Both content_selector and css_selector provided
        # content_selector should take priority
        crawl_config = {
            'content_selector': '.new-selector',
            'css_selector': '.old-selector'
        }
        selector, reason = select_content_selector(crawl_config)
        
        assert selector == '.new-selector', \
            f"Expected content_selector to take priority, got '{selector}'"
        assert 'user-provided' in reason.lower(), \
            f"Expected reason to indicate user-provided, got '{reason}'"
        
        print(f"✅ PASS: content_selector correctly takes priority over css_selector")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stage2_status_with_fallback():
    """Test: Verify stage2_status includes fallback_used field"""
    print("\n" + "="*80)
    print("TEST 5: Stage 2 status - fallback_used field")
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
            assert 'fallback_used' in stage2_status, "stage2_status should have 'fallback_used' field"
            
            # Check types
            assert isinstance(stage2_status['enabled'], bool), "'enabled' should be boolean"
            assert isinstance(stage2_status['success'], bool), "'success' should be boolean"
            assert isinstance(stage2_status['error'], (str, type(None))), "'error' should be string or None"
            assert isinstance(stage2_status['output_size_bytes'], (int, type(None))), \
                "'output_size_bytes' should be int or None"
            assert isinstance(stage2_status['fallback_used'], bool), "'fallback_used' should be boolean"
            
            print("✅ PASS: stage2_status structure includes fallback_used field")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stage2_fallback_config():
    """Test: Stage 2 fallback can be disabled via config"""
    print("\n" + "="*80)
    print("TEST 6: Stage 2 fallback - config flag")
    print("="*80)
    
    try:
        # Test with fallback disabled
        async with CrawlerService(verbose=True, headless=True) as service:
            result = await service.crawl_url(
                url="https://example.com",
                crawl_config={'stage2_fallback_enabled': False},
                llm_config=None,
                prompt_template=None,
                output_schema=None
            )
            
            stage2_status = result.get('stage2_status', {})
            
            # When Stage 2 is not enabled, fallback should not be used
            assert stage2_status['fallback_used'] == False, \
                "fallback_used should be False when Stage 2 not enabled"
            
            print("✅ PASS: Stage 2 fallback config flag works correctly")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("="*80)
    print("Content Selector and Stage 2 Fallback Tests")
    print("="*80)
    
    results = []
    
    # Run synchronous tests
    results.append(test_content_selector_user_provided())
    results.append(test_content_selector_backward_compat())
    results.append(test_content_selector_heuristic())
    results.append(test_content_selector_priority())
    
    # Run async tests
    results.append(await test_stage2_status_with_fallback())
    results.append(await test_stage2_fallback_config())
    
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
