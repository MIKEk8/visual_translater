"""
Rendering Engine Component - Single Responsibility: Template Rendering & Output
"""

import json
from typing import Any, Dict, List, Optional


class RenderingEngine:
    """Generate final rendered output from processed templates"""

    def __init__(self):
        self.output_formatters = {
            "html": self._format_html,
            "json": self._format_json,
            "xml": self._format_xml,
            "plain": self._format_plain,
        }

    def render_template(self, template_data: Dict[str, Any], bound_data: str) -> str:
        """Render final template output - complexity 3"""
        if not bound_data:  # +1
            return ""

        # Apply any post-processing
        result = bound_data

        if template_data.get("metadata", {}).get("post_process"):  # +1
            result = self._post_process(result)

        return result

    def apply_filters(self, text: str, filters: List[str]) -> str:
        """Apply rendering filters - complexity 3"""
        result = text

        for filter_name in filters:  # +1
            if filter_name == "upper":
                result = result.upper()
            elif filter_name == "lower":
                result = result.lower()
            elif filter_name == "reverse":  # +1
                result = result[::-1]
            elif filter_name == "trim":
                result = result.strip()

        return result

    def format_output(self, output: str, options: Dict[str, Any] = None) -> str:
        """Format final output - complexity 2"""
        options = options or {}
        format_type = options.get("format", "plain")

        if format_type in self.output_formatters:  # +1
            return self.output_formatters[format_type](output, options)

        return output

    def _format_html(self, content: str, options: Dict[str, Any]) -> str:
        """Format as HTML - complexity 1"""
        return content  # HTML is already formatted

    def _format_json(self, content: str, options: Dict[str, Any]) -> str:
        """Format as JSON - complexity 1"""
        return json.dumps({"content": content}, indent=2)

    def _format_xml(self, content: str, options: Dict[str, Any]) -> str:
        """Format as XML - complexity 1"""
        return f"<content>{content}</content>"

    def _format_plain(self, content: str, options: Dict[str, Any]) -> str:
        """Format as plain text - complexity 1"""
        return content

    def _post_process(self, content: str) -> str:
        """Post-process content - complexity 1"""
        return content.strip()
