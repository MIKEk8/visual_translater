"""Migration Generator - Database Migration Scripts"""

import datetime
from typing import Any, Dict, List


class MigrationGenerator:
    """Generate database migrations - complexity ≤ 4"""

    def __init__(self):
        self.migration_templates = {
            "add_table": "CREATE TABLE {table} ({columns});",
            "drop_table": "DROP TABLE {table};",
            "add_column": "ALTER TABLE {table} ADD COLUMN {column} {type};",
            "drop_column": "ALTER TABLE {table} DROP COLUMN {column};",
        }

    def generate_migration(
        self, changes: List[Dict[str, Any]], migration_name: str = None
    ) -> Dict[str, Any]:
        """Generate complete migration - complexity 4"""
        if not changes:  # +1
            return {"success": False, "error": "No changes to migrate"}

        migration_id = (
            migration_name or f"migration_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        # Generate SQL statements
        sql_statements = []
        rollback_statements = []

        for change in changes:  # +1
            forward_sql = self._generate_forward_sql(change)  # +1
            rollback_sql = self._generate_rollback_sql(change)  # +1

            if forward_sql:
                sql_statements.append(forward_sql)
            if rollback_sql:
                rollback_statements.append(rollback_sql)

        return {
            "success": True,
            "migration_id": migration_id,
            "forward_sql": sql_statements,
            "rollback_sql": list(reversed(rollback_statements)),
            "change_count": len(changes),
        }

    def generate_batch_migration(self, migrations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate batch migration - complexity 3"""
        if not migrations:  # +1
            return {"success": False, "error": "No migrations provided"}

        combined_sql = []
        combined_rollback = []

        for migration in migrations:  # +1
            if migration.get("success"):
                combined_sql.extend(migration.get("forward_sql", []))
                combined_rollback.extend(migration.get("rollback_sql", []))

        return {
            "success": True,
            "batch_id": f"batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "sql_statements": combined_sql,
            "rollback_statements": list(reversed(combined_rollback)),
            "migration_count": len(migrations),
        }

    def validate_migration_sql(self, sql_statements: List[str]) -> bool:
        """Validate generated SQL - complexity 2"""
        if not sql_statements:  # +1
            return False

        for sql in sql_statements:
            if not sql.strip() or not sql.strip().endswith(";"):
                return False

        return True

    def _generate_forward_sql(self, change: Dict[str, Any]) -> str:
        """Generate forward SQL - complexity 2"""
        action = change.get("action")
        template = self.migration_templates.get(action)

        if not template:  # +1
            return ""

        return template.format(**change)

    def _generate_rollback_sql(self, change: Dict[str, Any]) -> str:
        """Generate rollback SQL - complexity 2"""
        action = change.get("action")

        # Reverse operations for rollback
        if action == "add_table":
            return f"DROP TABLE {change.get('table')};"
        elif action == "drop_table":  # +1
            return ""  # Cannot easily reverse table drops

        return ""
