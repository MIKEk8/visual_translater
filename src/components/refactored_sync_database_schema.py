"""Refactored Sync Database Schema - Main Coordinator"""

from typing import Any, Dict, Optional

from .database_connection import DatabaseConnection
from .migration_generator import MigrationGenerator
from .schema_diff_analyzer import SchemaDiffAnalyzer
from .schema_validator import SchemaValidator


class RefactoredSyncDatabaseSchema:
    """Main coordinator for database schema sync - complexity ≤ 5"""

    def __init__(self):
        self.validator = SchemaValidator()
        self.diff_analyzer = SchemaDiffAnalyzer()
        self.migration_generator = MigrationGenerator()
        self.db_connection = DatabaseConnection()

    def sync_database_schema(
        self,
        target_schema: Dict[str, Any],
        connection_params: Dict[str, Any],
        options: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Synchronize database schema - complexity 5"""
        options = options or {}

        try:
            # Step 1: Validate target schema
            is_valid, validation_errors = self.validator.validate_schema(target_schema)
            if not is_valid:  # +1
                return {"success": False, "stage": "validation", "errors": validation_errors}

            # Step 2: Connect to database
            if not self.db_connection.establish_connection(connection_params):  # +1
                return {
                    "success": False,
                    "stage": "connection",
                    "error": "Failed to connect to database",
                }

            # Step 3: Get current schema (simulated)
            current_schema = options.get("current_schema", {"tables": {}})

            # Step 4: Analyze differences
            diff_analysis = self.diff_analyzer.analyze_differences(current_schema, target_schema)

            if diff_analysis.get("total_changes", 0) == 0:  # +1
                return {
                    "success": True,
                    "message": "Schema already up to date",
                    "stage": "analysis",
                }

            # Step 5: Generate and execute migration
            changes = diff_analysis["changes"]
            migration = self.migration_generator.generate_migration(changes)

            if not migration["success"]:  # +1
                return {
                    "success": False,
                    "stage": "migration_generation",
                    "error": migration.get("error", "Migration generation failed"),
                }

            # Execute migration
            if not options.get("dry_run", False):  # +1
                result = self.db_connection.execute_transaction(migration["forward_sql"])

                if not result["success"]:
                    return {
                        "success": False,
                        "stage": "execution",
                        "error": result["error"],
                        "migration": migration,
                    }

            return {
                "success": True,
                "stage": "completed",
                "changes_applied": diff_analysis["total_changes"],
                "migration_id": migration["migration_id"],
                "executed_statements": len(migration["forward_sql"]),
                "dry_run": options.get("dry_run", False),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "stage": "error"}
        finally:
            self.db_connection.close_connection()

    def validate_sync_readiness(
        self, target_schema: Dict[str, Any], connection_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate readiness for sync - complexity 3"""
        readiness_checks = {
            "schema_valid": False,
            "connection_available": False,
            "migration_safe": False,
        }

        # Check schema validity
        is_valid, _ = self.validator.validate_schema(target_schema)  # +1
        readiness_checks["schema_valid"] = is_valid

        # Check connection
        connection_ok = self.db_connection.establish_connection(connection_params)  # +1
        readiness_checks["connection_available"] = connection_ok

        if connection_ok:
            self.db_connection.close_connection()

        # Check migration safety (simplified)
        naming_issues = self.validator.check_naming_conventions(target_schema)
        readiness_checks["migration_safe"] = len(naming_issues) == 0  # +1

        all_ready = all(readiness_checks.values())

        return {
            "ready": all_ready,
            "checks": readiness_checks,
            "blockers": [k for k, v in readiness_checks.items() if not v],
        }

    def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status - complexity 2"""
        return {
            "connection_status": self.db_connection.get_connection_status(),
            "last_validation_errors": len(self.validator.validation_errors),  # +1
            "pending_changes": len(self.diff_analyzer.changes),
        }
