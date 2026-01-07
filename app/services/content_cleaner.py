"""
Content cleaning service for processing crawled markdown and generating cleaned outputs.

This module provides functionality to:
1. Clean markdown content by removing navigation, headers, footers, and other non-content elements
2. Generate cleaned JSON with essential content only
3. Extract main content from noisy web pages
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ContentCleaner:
    """Service for cleaning and processing crawled content"""
    
    # Common patterns to remove from markdown
    NAVIGATION_PATTERNS = [
        r'\[.*?\]\(javascript:;\)',  # JavaScript links
        r'##\s*\[.*?\]\(.*?\".*?\"\)\s*\n(?:\s*\*\s*\[.*?\]\(.*?\).*?\n)*',  # Navigation sections
        r'热门搜索[:：].*?(?=\n##|\n\n|$)',  # Hot searches
        r'当前位置[:：].*?(?=\n#|\n\n|$)',  # Breadcrumbs
    ]
    
    FOOTER_PATTERNS = [
        r'主办[:：].*?(?=\n|$)',  # Footer hosting info
        r'京ICP备.*?(?=\n|$)',  # ICP registration
        r'京公网安备.*?(?=\n|$)',  # Public security registration
        r'\[!\[.*?\]\(.*?icon.*?\).*?(?=\n|$)',  # Footer icons
    ]
    
    SIDEBAR_PATTERNS = [
        r'##\s*热点排行.*?(?=\n##|\n\n|$)',  # Hot rankings
        r'##\s*相关链接.*?(?=\n##|\n\n|$)',  # Related links
        r'##\s*热点专题.*?(?=\n##|\n\n|$)',  # Hot topics
    ]
    
    # Patterns for duplicate/repetitive content
    DUPLICATE_PATTERNS = [
        r'(.*?\n)\1+',  # Repeated lines
    ]
    
    def __init__(self):
        """Initialize content cleaner"""
        pass
    
    def clean_markdown(self, markdown: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Clean markdown content by removing navigation, headers, footers, and other noise.
        
        Args:
            markdown: Raw markdown content from crawl
            metadata: Optional metadata from crawl (title, description, etc.)
        
        Returns:
            Dictionary containing:
            - cleaned_markdown: Cleaned markdown content
            - removed_sections: List of removed section types
            - statistics: Cleaning statistics
        """
        if not markdown:
            logger.warning("Empty markdown provided for cleaning")
            return {
                'cleaned_markdown': '',
                'removed_sections': [],
                'statistics': {'original_length': 0, 'cleaned_length': 0, 'reduction_percent': 0}
            }
        
        original_length = len(markdown)
        cleaned = markdown
        removed_sections = []
        
        logger.info(f"Starting markdown cleaning. Original length: {original_length} characters")
        
        # Remove navigation patterns
        for pattern in self.NAVIGATION_PATTERNS:
            matches_before = len(re.findall(pattern, cleaned, re.MULTILINE | re.DOTALL))
            if matches_before > 0:
                cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
                removed_sections.append('navigation')
                logger.debug(f"Removed {matches_before} navigation section(s)")
        
        # Remove footer patterns
        for pattern in self.FOOTER_PATTERNS:
            matches_before = len(re.findall(pattern, cleaned, re.MULTILINE))
            if matches_before > 0:
                cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
                removed_sections.append('footer')
                logger.debug(f"Removed {matches_before} footer element(s)")
        
        # Remove sidebar patterns
        for pattern in self.SIDEBAR_PATTERNS:
            matches_before = len(re.findall(pattern, cleaned, re.MULTILINE | re.DOTALL))
            if matches_before > 0:
                cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
                removed_sections.append('sidebar')
                logger.debug(f"Removed {matches_before} sidebar section(s)")
        
        # Remove images that are logos or icons
        cleaned = re.sub(r'!\[\]\(.*?(?:logo|icon|banner).*?\)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Max 2 consecutive newlines
        cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)  # Trailing spaces
        cleaned = re.sub(r'\n[ \t]+', '\n', cleaned)  # Leading spaces
        
        # Remove empty list items
        cleaned = re.sub(r'\n\s*[\*\-]\s*\n', '\n', cleaned)
        
        # Remove links with no text (just empty brackets)
        cleaned = re.sub(r'\[\]\(.*?\)', '', cleaned)
        
        # Clean up duplicate content (be conservative)
        # Only remove if 3+ identical consecutive lines
        cleaned = re.sub(r'(^.*$\n)((?:\1){2,})', r'\1', cleaned, flags=re.MULTILINE)
        
        # Final cleanup: normalize whitespace
        cleaned = cleaned.strip()
        
        cleaned_length = len(cleaned)
        reduction_percent = ((original_length - cleaned_length) / original_length * 100) if original_length > 0 else 0
        
        statistics = {
            'original_length': original_length,
            'cleaned_length': cleaned_length,
            'reduction_percent': round(reduction_percent, 2),
            'removed_sections': list(set(removed_sections))
        }
        
        logger.info(f"Markdown cleaning completed. Cleaned length: {cleaned_length} characters "
                   f"(reduced by {reduction_percent:.2f}%)")
        
        return {
            'cleaned_markdown': cleaned,
            'removed_sections': list(set(removed_sections)),
            'statistics': statistics
        }
    
    def extract_main_content(self, markdown: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Extract main content from cleaned markdown.
        
        This focuses on extracting the primary article/document content,
        typically following headers like # Title.
        
        Args:
            markdown: Markdown content (ideally pre-cleaned)
            metadata: Optional metadata with title info
        
        Returns:
            Extracted main content or None if not found
        """
        if not markdown:
            return None
        
        # Find the first H1 heading (main title)
        h1_match = re.search(r'^# (.+)$', markdown, re.MULTILINE)
        if not h1_match:
            # No clear title found, return content after first meaningful paragraph
            logger.debug("No H1 heading found, using heuristic content extraction")
            # Skip lines until we find substantial text (not just links or short lines)
            lines = markdown.split('\n')
            content_start = 0
            for i, line in enumerate(lines):
                # Look for paragraph text (not links, not empty, not just short lines)
                if len(line.strip()) > 50 and not line.startswith('#') and not line.startswith('['):
                    content_start = i
                    break
            
            if content_start > 0:
                return '\n'.join(lines[content_start:]).strip()
            return markdown.strip()
        
        # Get content after the H1 title
        title_pos = h1_match.end()
        main_content = markdown[title_pos:].strip()
        
        # Look for common content boundaries and stop there
        # E.g., "## 热点排行", "## 相关链接", etc.
        boundary_patterns = [
            r'\n##\s*热点排行',
            r'\n##\s*相关链接',
            r'\n##\s*热点专题',
            r'\n主办[:：]',
        ]
        
        earliest_boundary = len(main_content)
        for pattern in boundary_patterns:
            match = re.search(pattern, main_content)
            if match and match.start() < earliest_boundary:
                earliest_boundary = match.start()
        
        if earliest_boundary < len(main_content):
            main_content = main_content[:earliest_boundary].strip()
            logger.debug(f"Truncated content at boundary, length: {len(main_content)}")
        
        return main_content
    
    def generate_cleaned_json(
        self,
        cleaned_markdown: str,
        metadata: Optional[Dict[str, Any]] = None,
        structured_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a cleaned JSON representation of the content.
        
        Args:
            cleaned_markdown: Cleaned markdown content
            metadata: Crawl metadata (title, description, etc.)
            structured_data: LLM-extracted structured data (if available)
        
        Returns:
            Dictionary with cleaned content in JSON format
        """
        main_content = self.extract_main_content(cleaned_markdown, metadata)
        
        cleaned_json = {
            'metadata': {
                'title': metadata.get('title') if metadata else None,
                'description': metadata.get('description') if metadata else None,
                'language': metadata.get('language') if metadata else None,
                'keywords': metadata.get('keywords', []) if metadata else [],
            },
            'content': {
                'main_text': main_content,
                'length': len(main_content) if main_content else 0,
            }
        }
        
        # Include structured data if available and different from basic extraction
        if structured_data:
            cleaned_json['structured_data'] = structured_data
        
        # Extract simple statistics
        if main_content:
            # Count paragraphs (separated by blank lines)
            paragraphs = [p.strip() for p in main_content.split('\n\n') if p.strip()]
            cleaned_json['statistics'] = {
                'paragraph_count': len(paragraphs),
                'character_count': len(main_content),
                'line_count': len(main_content.split('\n')),
            }
        
        logger.info(f"Generated cleaned JSON with {len(main_content) if main_content else 0} characters of main content")
        
        return cleaned_json


# Global instance
content_cleaner = ContentCleaner()
