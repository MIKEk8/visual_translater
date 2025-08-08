"""
Data Binder Component - Single Responsibility: Data Binding & Variable Substitution
Extracted from _render_template (complexity 15 → 4 per method)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union


class DataBinder:
    """
    Single Responsibility: Bind data to template variables and expressions
    All methods ≤ 4 complexity
    """

    def __init__(self):
        self.binding_errors = []
        self.filters = {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "title": lambda x: str(x).title(),
            "length": lambda x: len(x) if hasattr(x, "__len__") else 0,
            "reverse": lambda x: str(x)[::-1] if isinstance(x, str) else x,
            "default": lambda x, default="": x if x is not None else default,
        }
        self.logger = logging.getLogger(__name__)

    def bind_variables(self, template: str, data: Dict[str, Any]) -> str:
        """
        Bind simple variables to template
        Complexity: 4
        """
        if not template or not isinstance(data, dict):  # +1
            return template or ""

        self.binding_errors.clear()
        result = template

        # Find and replace all {{variable}} patterns
        variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*?)\s*\}\}"

        def replace_variable(match):
            var_name = match.group(1)
            try:
                value = self._resolve_variable_path(var_name, data)  # +1
                return str(value) if value is not None else ""
            except KeyError:  # +1
                self.binding_errors.append(f"Variable '{var_name}' not found in data")
                return match.group(0)  # Keep original if not found
            except Exception as e:  # +1
                self.binding_errors.append(f"Error binding variable '{var_name}': {str(e)}")
                return match.group(0)

        result = re.sub(variable_pattern, replace_variable, result)
        return result

    def resolve_expressions(self, template: str, data: Dict[str, Any]) -> str:
        """
        Resolve complex expressions with filters
        Complexity: 4
        """
        if not template:  # +1
            return ""

        # Pattern for {{variable|filter1|filter2}}
        expression_pattern = r"\{\{\s*([^|\}]+)(?:\|([^\}]+))?\s*\}\}"

        def resolve_expression(match):
            var_part = match.group(1).strip()
            filter_part = match.group(2)

            try:
                # Get base value
                value = self._resolve_variable_path(var_part, data)  # +1

                # Apply filters if present
                if filter_part:  # +1
                    filters = [f.strip() for f in filter_part.split("|")]
                    value = self._apply_filters(value, filters)  # +1

                return str(value) if value is not None else ""
            except Exception as e:
                self.binding_errors.append(
                    f"Error resolving expression '{match.group(0)}': {str(e)}"
                )
                return match.group(0)

        return re.sub(expression_pattern, resolve_expression, template)

    def handle_conditionals(self, template: str, data: Dict[str, Any]) -> str:
        """
        Handle conditional blocks
        Complexity: 4
        """
        if not template:  # +1
            return ""

        # Pattern for {% if condition %}content{% endif %}
        conditional_pattern = r"\{%\s*if\s+([^%]+?)\s*%\}(.*?)\{%\s*endif\s*%\}"

        def process_conditional(match):
            condition = match.group(1).strip()
            content = match.group(2)

            try:
                # Evaluate condition
                if self._evaluate_condition(condition, data):  # +1
                    return content
                else:
                    return ""
            except Exception as e:  # +1
                self.binding_errors.append(f"Error in conditional '{condition}': {str(e)}")
                return match.group(0)  # +1

        # Process conditionals (may be nested, so repeat until no more matches)
        prev_result = None
        result = template
        while result != prev_result:
            prev_result = result
            result = re.sub(conditional_pattern, process_conditional, result, flags=re.DOTALL)

        return result

    def get_binding_errors(self) -> List[str]:
        """Get binding errors - complexity 1"""
        return self.binding_errors.copy()

    def clear_binding_errors(self) -> int:
        """Clear binding errors - complexity 1"""
        count = len(self.binding_errors)
        self.binding_errors.clear()
        return count

    def add_filter(self, name: str, filter_func) -> None:
        """Add custom filter - complexity 1"""
        self.filters[name] = filter_func

    def get_available_filters(self) -> List[str]:
        """Get available filters - complexity 1"""
        return list(self.filters.keys())

    def _resolve_variable_path(self, var_path: str, data: Dict[str, Any]) -> Any:
        """Resolve dot-notation variable paths - complexity 3"""
        if "." not in var_path:  # +1
            return data[var_path]

        parts = var_path.split(".")
        current = data

        for part in parts:  # +1
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):  # +1
                current = getattr(current, part)
            else:
                raise KeyError(f"Cannot resolve path '{var_path}'")

        return current

    def _apply_filters(self, value: Any, filters: List[str]) -> Any:
        """Apply filters to value - complexity 3"""
        result = value

        for filter_spec in filters:  # +1
            filter_parts = filter_spec.split(":")
            filter_name = filter_parts[0].strip()
            filter_args = filter_parts[1:] if len(filter_parts) > 1 else []

            if filter_name in self.filters:  # +1
                try:
                    filter_func = self.filters[filter_name]
                    if filter_args:
                        result = filter_func(result, *filter_args)
                    else:
                        result = filter_func(result)
                except Exception as e:  # +1
                    self.logger.warning(f"Filter '{filter_name}' failed: {e}")
                    # Continue with unfiltered value

        return result

    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate conditional expression - complexity 3"""
        condition = condition.strip()

        # Handle simple variable existence
        if condition in data:  # +1
            value = data[condition]
            return bool(value) if value is not None else False

        # Handle dot notation
        try:
            if "." in condition:  # +1
                value = self._resolve_variable_path(condition, data)
                return bool(value) if value is not None else False
        except:
            pass

        # Simple comparison operators
        for op in ["==", "!=", ">", "<", ">=", "<="]:  # +1
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._resolve_variable_path(left.strip(), data)
                right_val = right.strip().strip('"').strip("'")

                # Try to convert right side to number if possible
                try:
                    right_val = float(right_val)
                except:
                    pass

                if op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val
                elif op == ">":
                    return left_val > right_val
                elif op == "<":
                    return left_val < right_val
                elif op == ">=":
                    return left_val >= right_val
                elif op == "<=":
                    return left_val <= right_val

        return False
