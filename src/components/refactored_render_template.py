"""
Refactored Render Template - Main Coordinator
Complexity reduced from 15 to 5 using composition
"""

from typing import Any, Dict, Optional

from .data_binder import DataBinder
from .rendering_engine import RenderingEngine
from .template_error_handler import TemplateErrorHandler
from .template_loader import TemplateLoader


class RefactoredRenderTemplate:
    """
    Main coordinator for template rendering
    Complexity: 5 (down from 15)
    """

    def __init__(self):
        self.loader = TemplateLoader()
        self.binder = DataBinder()
        self.engine = RenderingEngine()
        self.error_handler = TemplateErrorHandler()

    def render_template(
        self, template_path: str, data: Dict[str, Any], options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Render complete template
        Complexity: 5 (down from 15)
        """
        options = options or {}

        try:
            # Step 1: Load template
            template_content = self.loader.load_template(template_path)
            if not template_content:  # +1
                return {
                    "success": False,
                    "error": f"Template not found: {template_path}",
                    "stage": "loading",
                }

            # Step 2: Parse template
            template_data = self.loader.parse_template(template_content)
            if not template_data["valid"]:  # +1
                return {"success": False, "error": "Invalid template syntax", "stage": "parsing"}

            # Step 3: Bind data
            bound_content = self.binder.bind_variables(template_content, data)
            bound_content = self.binder.resolve_expressions(bound_content, data)
            bound_content = self.binder.handle_conditionals(bound_content, data)

            # Check for binding errors
            binding_errors = self.binder.get_binding_errors()
            if binding_errors and not options.get("ignore_binding_errors"):  # +1
                return {
                    "success": False,
                    "error": "Data binding failed",
                    "errors": binding_errors,
                    "stage": "binding",
                }

            # Step 4: Render output
            rendered = self.engine.render_template(template_data, bound_content)

            # Step 5: Format output
            if options.get("format_output"):  # +1
                rendered = self.engine.format_output(rendered, options)

            return {
                "success": True,
                "rendered_output": rendered,
                "stage": "complete",
                "metadata": {
                    "template_path": template_path,
                    "variables_found": len(template_data["variables"]),
                    "binding_errors": len(binding_errors),
                },
            }

        except Exception as e:  # +1
            error_info = self.error_handler.handle_error(e, template_content or template_path)

            return {
                "success": False,
                "error": str(e),
                "error_details": error_info,
                "suggestions": self.error_handler.suggest_fixes(error_info),
                "stage": "error",
            }

    def orchestrate_rendering(
        self, template_content: str, data: Dict[str, Any], options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Orchestrate rendering process - complexity 3"""
        results = {}

        try:
            # Load and parse
            template_data = self.loader.parse_template(template_content)  # +1
            results["loaded"] = template_data["valid"]

            # Bind data
            bound = self.binder.bind_variables(template_content, data)  # +1
            results["bound"] = len(self.binder.get_binding_errors()) == 0

            # Render
            rendered = self.engine.render_template(template_data, bound)
            results["rendered"] = bool(rendered)

        except Exception as e:
            results["error"] = str(e)

        return results

    def compile_output(self, rendering_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile final output - complexity 2"""
        if "error" in rendering_results:  # +1
            return {"success": False, "error": rendering_results["error"]}

        return {
            "success": all(
                rendering_results.get(key, False) for key in ["loaded", "bound", "rendered"]
            ),
            "output": rendering_results.get("final_output", ""),
            "metadata": {
                "stages_completed": sum(1 for v in rendering_results.values() if v is True)
            },
        }
