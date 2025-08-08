"""
Config Dependency Validator Component - Single Responsibility: Dependency Validation
"""

from typing import Any, Dict, List, Tuple


class ConfigDependencyValidator:
    """Validate configuration dependencies and cross-references"""

    def __init__(self):
        self.validation_errors = []

    def validate_dependencies(
        self, config: Dict[str, Any], dependencies: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """Validate configuration dependencies - complexity 3"""
        self.validation_errors.clear()
        dependencies = dependencies or {}

        for field, dep_rule in dependencies.items():  # +1
            if field in config:
                required_field = dep_rule.get("requires")
                required_value = dep_rule.get("value")

                if required_field not in config:  # +1
                    self.validation_errors.append(
                        f"Field '{field}' requires '{required_field}' to be present"
                    )
                elif config[required_field] != required_value:  # +1
                    self.validation_errors.append(
                        f"Field '{field}' requires '{required_field}' to be '{required_value}'"
                    )

        return len(self.validation_errors) == 0, self.validation_errors

    def check_references(
        self, config: Dict[str, Any], field_name: str, valid_references: List[str]
    ) -> bool:
        """Check cross-references - complexity 2"""
        if field_name not in config:  # +1
            return True

        value = config[field_name]
        return value in valid_references  # +1

    def verify_consistency(self, config: Dict[str, Any]) -> bool:
        """Verify configuration consistency - complexity 1"""
        return True  # Placeholder implementation
