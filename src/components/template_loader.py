"""
Template Loader Component - Single Responsibility: Template Loading & Parsing
Extracted from _render_template (complexity 15 → 3 per method)
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set


class TemplateLoader:
    """
    Single Responsibility: Load and parse template files
    All methods ≤ 3 complexity
    """

    def __init__(self):
        self.template_cache = {}
        self.template_dirs = ["./templates", "./views"]
        self.supported_extensions = {".html", ".txt", ".md", ".xml"}
        self.logger = logging.getLogger(__name__)

    def load_template(self, template_path: str) -> Optional[str]:
        """
        Load template from file or cache
        Complexity: 3
        """
        if not template_path:  # +1
            return None

        # Check cache first
        if template_path in self.template_cache:  # +1
            return self.template_cache[template_path]

        # Load from file
        full_path = self._resolve_template_path(template_path)
        if full_path and os.path.exists(full_path):  # +1
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.template_cache[template_path] = content
                    return content
            except Exception as e:
                self.logger.error(f"Failed to load template {template_path}: {e}")

        # Fallback: treat as inline template
        return template_path if self._looks_like_template(template_path) else None

    def parse_template(self, template_content: str) -> Dict[str, Any]:
        """
        Parse template and extract metadata
        Complexity: 3
        """
        if not template_content:  # +1
            return {"variables": [], "blocks": [], "valid": False}

        # Extract variables ({{variable}})
        variables = self._extract_variables(template_content)

        # Extract control blocks ({% if %}, {% for %}, etc.)
        blocks = self._extract_control_blocks(template_content)

        # Validate template syntax
        is_valid = self.validate_syntax(template_content)  # +1

        return {
            "variables": variables,
            "blocks": blocks,
            "valid": is_valid,
            "content": template_content,
            "metadata": {
                "variable_count": len(variables),
                "block_count": len(blocks),
                "complexity_score": len(variables) + len(blocks) * 2,
            },
        }

    def validate_syntax(self, template_content: str) -> bool:
        """
        Validate template syntax
        Complexity: 3
        """
        if not template_content:  # +1
            return False

        # Check for balanced braces
        if not self._check_balanced_braces(template_content):  # +1
            return False

        # Check for valid control block syntax
        if not self._check_control_blocks(template_content):  # +1
            return False

        return True

    def set_template_directories(self, directories: List[str]) -> None:
        """Set template search directories - complexity 1"""
        self.template_dirs = directories.copy() if directories else []

    def clear_cache(self) -> int:
        """Clear template cache - complexity 1"""
        count = len(self.template_cache)
        self.template_cache.clear()
        return count

    def get_cached_templates(self) -> List[str]:
        """Get list of cached templates - complexity 1"""
        return list(self.template_cache.keys())

    def _resolve_template_path(self, template_path: str) -> Optional[str]:
        """Resolve full template path - complexity 2"""
        for template_dir in self.template_dirs:  # +1
            full_path = os.path.join(template_dir, template_path)
            if os.path.exists(full_path):
                return full_path
        return None

    def _looks_like_template(self, content: str) -> bool:
        """Check if content looks like a template - complexity 2"""
        if not content:
            return False
        # Simple heuristic: contains template syntax
        return "{{" in content or "{%" in content  # +1

    def _extract_variables(self, content: str) -> List[str]:
        """Extract template variables - complexity 2"""
        # Find all {{variable}} patterns
        variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*?)\s*\}\}"
        matches = re.findall(variable_pattern, content)
        return list(set(matches))  # Remove duplicates  # +1

    def _extract_control_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract control blocks - complexity 2"""
        # Find control blocks like {% if %}, {% for %}, etc.
        block_pattern = r"\{%\s*(\w+)\s*([^%]*)%\}"
        matches = re.findall(block_pattern, content)

        blocks = []
        for block_type, block_content in matches:  # +1
            blocks.append({"type": block_type, "content": block_content.strip()})

        return blocks

    def _check_balanced_braces(self, content: str) -> bool:
        """Check for balanced braces - complexity 3"""
        open_vars = content.count("{{")
        close_vars = content.count("}}")
        open_blocks = content.count("{%")
        close_blocks = content.count("%}")

        return open_vars == close_vars and open_blocks == close_blocks  # +1 (complex condition)

    def _check_control_blocks(self, content: str) -> bool:
        """Check control block syntax - complexity 2"""
        # Basic validation for common control structures
        blocks = self._extract_control_blocks(content)

        for block in blocks:  # +1
            if block["type"] in ["if", "for", "while"] and not block["content"]:
                return False

        return True
