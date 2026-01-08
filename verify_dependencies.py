#!/usr/bin/env python3
"""
Verification script to check that RQ and Click versions are compatible
and that crawl4ai is properly configured.
"""

import sys

def check_versions():
    """Check that required packages are installed with correct versions"""
    errors = []
    warnings = []
    
    # Check RQ version
    try:
        import rq
        rq_version = rq.__version__
        print(f"✓ RQ version: {rq_version}")
        
        # Parse version
        major, minor, patch = map(int, rq_version.split('.')[:3])
        if (major, minor) < (2, 6):
            warnings.append(f"RQ version {rq_version} is older than recommended 2.6.1")
    except ImportError:
        errors.append("RQ is not installed")
    except Exception as e:
        warnings.append(f"Could not verify RQ version: {e}")
    
    # Check Click version
    try:
        import click
        click_version = click.__version__
        print(f"✓ Click version: {click_version}")
        
        # Parse version
        major, minor = map(int, click_version.split('.')[:2])
        if (major, minor) >= (8, 2):
            warnings.append(
                f"Click version {click_version} may cause duplicate parameter warnings with RQ. "
                "Recommended: <8.2.0"
            )
    except ImportError:
        errors.append("Click is not installed")
    except Exception as e:
        warnings.append(f"Could not verify Click version: {e}")
    
    # Check crawl4ai
    try:
        import crawl4ai
        print(f"✓ crawl4ai is installed")
        
        # Check if AsyncWebCrawler is available
        from crawl4ai import AsyncWebCrawler, BrowserConfig
        print(f"✓ AsyncWebCrawler is available")
        
        # Check if new config classes are available
        try:
            from crawl4ai import CacheMode
            print(f"✓ CacheMode is available (0.7.8+ API)")
        except ImportError:
            warnings.append("CacheMode not available - may be using older crawl4ai version")
    except ImportError:
        errors.append("crawl4ai is not installed")
    except Exception as e:
        warnings.append(f"Could not fully verify crawl4ai: {e}")
    
    # Check redis
    try:
        import redis
        redis_version = redis.__version__
        print(f"✓ Redis client version: {redis_version}")
    except ImportError:
        errors.append("Redis client is not installed")
    except Exception as e:
        warnings.append(f"Could not verify Redis client version: {e}")
    
    return errors, warnings


def main():
    print("=" * 60)
    print("Mercury4AI Dependency Verification")
    print("=" * 60)
    print()
    
    errors, warnings = check_versions()
    
    print()
    if warnings:
        print("⚠ Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    if errors:
        print("✗ Errors:")
        for error in errors:
            print(f"  - {error}")
        print()
        print("Dependencies check FAILED")
        return 1
    else:
        print("✓ All required dependencies are properly installed")
        if warnings:
            print("  (with some warnings - see above)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
