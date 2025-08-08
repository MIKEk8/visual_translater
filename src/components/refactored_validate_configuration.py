"""
Refactored Validate Configuration - Main Coordinator
Complexity reduced from 15 to 5 using composition
"""

from typing import Any, Dict, Optional

from .config_dependency_validator import ConfigDependencyValidator
from .config_error_collector import ConfigErrorCollector
from .config_schema_validator import ConfigSchemaValidator
from .config_value_validator import ConfigValueValidator


class RefactoredValidateConfiguration:
    """
    Main coordinator for configuration validation
    Complexity: 5 (down from 15)
    """

    def __init__(self):
        self.schema_validator = ConfigSchemaValidator()
        self.value_validator = ConfigValueValidator()
        self.dependency_validator = ConfigDependencyValidator()
        self.error_collector = ConfigErrorCollector()

    def validate_configuration(
        self, config: Dict[str, Any], rules: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate complete configuration
        Complexity: 5 (down from 15)
        """
        rules = rules or {}

        # Step 1: Schema validation
        schema_valid, schema_errors = self.schema_validator.validate_schema(config)
        if not schema_valid:  # +1
            self.error_collector.collect_errors("schema", schema_errors)
            return {"valid": False, "errors": schema_errors, "stage": "schema"}

        # Step 2: Value validation
        value_valid, value_errors = self.value_validator.validate_values(
            config, rules.get("constraints")
        )
        if not value_valid:  # +1
            self.error_collector.collect_errors("values", value_errors)

        # Step 3: Dependency validation
        dep_valid, dep_errors = self.dependency_validator.validate_dependencies(
            config, rules.get("dependencies")
        )
        if not dep_valid:  # +1
            self.error_collector.collect_errors("dependencies", dep_errors)

        # Step 4: Generate final result
        all_valid = schema_valid and value_valid and dep_valid
        if not all_valid:  # +1
            error_report = self.error_collector.generate_report()
            return {
                "valid": False,
                "errors": error_report["errors_by_category"],
                "total_errors": error_report["total_errors"],
                "stage": "complete",
            }

        return {"valid": True, "errors": {}, "stage": "complete"}  # +1

    def orchestrate_validation(
        self, config: Dict[str, Any], validation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrate validation process - complexity 3"""
        results = {}

        # Run all validations
        results["schema_validation"] = self.schema_validator.validate_schema(config)
        results["value_validation"] = self.value_validator.validate_values(
            config, validation_rules.get("constraints")
        )  # +1
        results["dependency_validation"] = self.dependency_validator.validate_dependencies(
            config, validation_rules.get("dependencies")
        )  # +1

        return results

    def compile_results(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile validation results - complexity 2"""
        all_errors = []
        all_valid = True

        for validation_type, (is_valid, errors) in validation_results.items():  # +1
            if not is_valid:
                all_valid = False
                all_errors.extend(errors)

        return {"valid": all_valid, "errors": all_errors}
