#!/usr/bin/env python3
"""
Demo script showing how Stage 2 (LLM extraction) configuration works.

This script demonstrates:
1. How @prompt_templates/... and @schemas/... references work
2. How default prompts from environment variables work
3. What logs appear when Stage 2 is enabled/disabled
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.template_loader import (
    resolve_prompt_template,
    resolve_output_schema,
    get_default_prompt_from_env
)


class MockSettings:
    """Mock settings for demonstration"""
    def __init__(self):
        self.DEFAULT_PROMPT_TEMPLATE = None
        self.DEFAULT_PROMPT_TEMPLATE_REF = None


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def demo_1_task_with_template_references():
    """Demo: Task with @prompt_templates/... and @schemas/... references"""
    print_header("DEMO 1: Task with Template File References")
    
    print("Task Configuration:")
    print("""
    {
      "name": "Extract News Articles",
      "urls": ["https://news.example.com/article1"],
      "prompt_template": "@prompt_templates/news_article_zh.txt",
      "output_schema": "@schemas/news_article_zh.json"
    }
    """)
    
    print("\nWhat happens:")
    print("1. System reads prompt from prompt_templates/news_article_zh.txt")
    print("2. System reads schema from schemas/news_article_zh.json")
    print("3. Both are resolved before sending to crawler")
    
    # Demonstrate the resolution
    prompt, prompt_source = resolve_prompt_template("@prompt_templates/news_article_zh.txt")
    schema, schema_source = resolve_output_schema("@schemas/news_article_zh.json")
    
    print("\n✓ Resolution Result:")
    if prompt:
        print(f"  - Prompt loaded: {len(prompt)} characters from {prompt_source}")
        print(f"  - Preview: {prompt[:80]}...")
    if schema:
        print(f"  - Schema loaded from {schema_source}")
        print(f"  - Schema properties: {list(schema.get('properties', {}).keys())}")
    
    print("\nExpected Log Output:")
    print("""
    Data Cleaning Configuration:
      • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
      • Stage 2 (LLM extraction): ENABLED - Extracts structured data
        - Provider: openai
        - Model: deepseek-chat
        - Prompt: @prompt_templates/news_article_zh.txt (178 chars)
        - Schema: @schemas/news_article_zh.json
    """)


def demo_2_task_with_inline_prompt():
    """Demo: Task with inline prompt (no file reference)"""
    print_header("DEMO 2: Task with Inline Prompt")
    
    print("Task Configuration:")
    print("""
    {
      "name": "Simple Extraction",
      "urls": ["https://example.com/page"],
      "prompt_template": "Extract title and content in JSON format",
      "output_schema": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "content": {"type": "string"}
        }
      }
    }
    """)
    
    print("\nWhat happens:")
    print("1. System uses inline prompt directly (no file loading)")
    print("2. System uses inline schema directly (no file loading)")
    
    # Demonstrate the resolution
    prompt, prompt_source = resolve_prompt_template("Extract title and content in JSON format")
    schema, schema_source = resolve_output_schema({
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"}
        }
    })
    
    print("\n✓ Resolution Result:")
    print(f"  - Prompt source: {prompt_source}")
    print(f"  - Schema source: {schema_source}")
    
    print("\nExpected Log Output:")
    print("""
    Data Cleaning Configuration:
      • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
      • Stage 2 (LLM extraction): ENABLED - Extracts structured data
        - Provider: openai
        - Model: deepseek-chat
        - Prompt: inline (48 chars)
        - Schema: inline
    """)


def demo_3_default_prompt_from_env():
    """Demo: Using default prompt from environment variables"""
    print_header("DEMO 3: Using Default Prompt from Environment")
    
    print("Scenario: Task has NO prompt_template")
    print("\nTask Configuration:")
    print("""
    {
      "name": "Task Without Prompt",
      "urls": ["https://example.com/page"]
      // Note: No prompt_template specified
    }
    """)
    
    print("\nEnvironment Variables (.env):")
    print("""
    DEFAULT_LLM_PROVIDER=openai
    DEFAULT_LLM_MODEL=deepseek-chat
    DEFAULT_LLM_API_KEY=sk-xxx...
    DEFAULT_PROMPT_TEMPLATE=Extract main content and title from the page.
    """)
    
    print("\nWhat happens:")
    print("1. Task has no prompt_template")
    print("2. System checks DEFAULT_PROMPT_TEMPLATE in environment")
    print("3. Finds it and uses it as fallback")
    
    # Demonstrate the fallback
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE = "Extract main content and title from the page."
    
    prompt, source = get_default_prompt_from_env(settings)
    
    print("\n✓ Resolution Result:")
    print(f"  - Prompt: {prompt}")
    print(f"  - Source: {source}")
    
    print("\nExpected Log Output:")
    print("""
    Task has no prompt_template - checking for defaults in environment
    Using DEFAULT_PROMPT_TEMPLATE from environment (48 chars)
    
    Data Cleaning Configuration:
      • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
      • Stage 2 (LLM extraction): ENABLED - Extracts structured data
        - Provider: openai
        - Model: deepseek-chat
        - Prompt: DEFAULT_PROMPT_TEMPLATE (48 chars)
        - Schema: not configured (will use free-form)
    """)


def demo_4_default_prompt_ref_from_env():
    """Demo: Using default prompt file reference from environment"""
    print_header("DEMO 4: Using Default Prompt File Reference from Environment")
    
    print("Scenario: Task has NO prompt_template")
    print("\nTask Configuration:")
    print("""
    {
      "name": "Task Without Prompt",
      "urls": ["https://example.com/page"]
      // Note: No prompt_template specified
    }
    """)
    
    print("\nEnvironment Variables (.env):")
    print("""
    DEFAULT_LLM_PROVIDER=openai
    DEFAULT_LLM_MODEL=deepseek-chat
    DEFAULT_LLM_API_KEY=sk-xxx...
    DEFAULT_PROMPT_TEMPLATE_REF=@prompt_templates/news_article_zh.txt
    """)
    
    print("\nWhat happens:")
    print("1. Task has no prompt_template")
    print("2. System checks DEFAULT_PROMPT_TEMPLATE (empty)")
    print("3. System checks DEFAULT_PROMPT_TEMPLATE_REF (has value)")
    print("4. Loads prompt from the referenced file")
    
    # Demonstrate the fallback
    settings = MockSettings()
    settings.DEFAULT_PROMPT_TEMPLATE_REF = "@prompt_templates/news_article_zh.txt"
    
    prompt, source = get_default_prompt_from_env(settings)
    
    print("\n✓ Resolution Result:")
    if prompt:
        print(f"  - Prompt loaded: {len(prompt)} characters")
        print(f"  - Source: {source}")
    
    print("\nExpected Log Output:")
    print("""
    Task has no prompt_template - checking for defaults in environment
    Using DEFAULT_PROMPT_TEMPLATE_REF from environment: @prompt_templates/news_article_zh.txt
    Loaded prompt template from file: @prompt_templates/news_article_zh.txt (178 chars)
    
    Data Cleaning Configuration:
      • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
      • Stage 2 (LLM extraction): ENABLED - Extracts structured data
        - Provider: openai
        - Model: deepseek-chat
        - Prompt: DEFAULT_PROMPT_TEMPLATE_REF (@prompt_templates/news_article_zh.txt) (178 chars)
        - Schema: not configured (will use free-form)
    """)


def demo_5_stage2_disabled():
    """Demo: Stage 2 disabled - various scenarios"""
    print_header("DEMO 5: Stage 2 DISABLED Scenarios")
    
    print("Scenario A: No LLM Config")
    print("-" * 80)
    print("Task Configuration:")
    print("""
    {
      "name": "Task",
      "urls": ["https://example.com"],
      "prompt_template": "Extract data"
      // Note: No llm_provider, llm_model, or DEFAULT_LLM_* in env
    }
    """)
    print("\nExpected Log:")
    print("""
      • Stage 2 (LLM extraction): DISABLED - No LLM config (missing provider/model or API key)
    """)
    
    print("\n" + "-" * 80)
    print("Scenario B: Has LLM Config but No Prompt")
    print("-" * 80)
    print("Task Configuration:")
    print("""
    {
      "name": "Task",
      "urls": ["https://example.com"]
      // Note: No prompt_template
    }
    
    Environment (.env):
    DEFAULT_LLM_PROVIDER=openai
    DEFAULT_LLM_MODEL=deepseek-chat
    DEFAULT_LLM_API_KEY=sk-xxx
    // Note: No DEFAULT_PROMPT_TEMPLATE or DEFAULT_PROMPT_TEMPLATE_REF
    """)
    print("\nExpected Log:")
    print("""
    Task has no prompt_template - checking for defaults in environment
    No default prompt configured in environment (DEFAULT_PROMPT_TEMPLATE or DEFAULT_PROMPT_TEMPLATE_REF)
    
      • Stage 2 (LLM extraction): DISABLED - No prompt_template in task and no default prompt configured
        To enable Stage 2, either:
          1. Add 'prompt_template' to task config (inline or @prompt_templates/...)
          2. Set DEFAULT_PROMPT_TEMPLATE in .env (inline prompt text)
          3. Set DEFAULT_PROMPT_TEMPLATE_REF in .env (@prompt_templates/... reference)
    """)
    
    print("\n" + "-" * 80)
    print("Scenario C: File Reference Not Found")
    print("-" * 80)
    print("Task Configuration:")
    print("""
    {
      "name": "Task",
      "urls": ["https://example.com"],
      "prompt_template": "@prompt_templates/missing_file.txt"
    }
    """)
    print("\nExpected Log:")
    print("""
    Prompt template file not found: /path/to/prompt_templates/missing_file.txt
    Reference: @prompt_templates/missing_file.txt
    To fix: Create the file or use an inline prompt
    Failed to resolve task prompt_template: @prompt_templates/missing_file.txt
    
      • Stage 2 (LLM extraction): DISABLED - Failed to load prompt template: @prompt_templates/missing_file.txt
    """)


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("  Mercury4AI Stage 2 (LLM Extraction) Configuration Demo")
    print("=" * 80)
    print("\nThis demo shows how the new template loading and default prompt")
    print("functionality works in different scenarios.")
    
    demo_1_task_with_template_references()
    demo_2_task_with_inline_prompt()
    demo_3_default_prompt_from_env()
    demo_4_default_prompt_ref_from_env()
    demo_5_stage2_disabled()
    
    print("\n" + "=" * 80)
    print("  Demo Complete!")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("1. Use @prompt_templates/... and @schemas/... for reusable templates")
    print("2. Set DEFAULT_PROMPT_TEMPLATE or DEFAULT_PROMPT_TEMPLATE_REF for fallback")
    print("3. Stage 2 requires BOTH LLM config AND a prompt (task or default)")
    print("4. Logs clearly show why Stage 2 is enabled or disabled")
    print("\n")


if __name__ == "__main__":
    main()
