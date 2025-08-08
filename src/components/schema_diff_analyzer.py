"""Schema Diff Analyzer - Database Change Analysis"""

import logging
from typing import Any, Dict, List, Set


class SchemaDiffAnalyzer:
    """Analyze schema differences - complexity ≤ 4"""

    def __init__(self):
        self.changes = []
        self.logger = logging.getLogger(__name__)

    def analyze_differences(
        self, current_schema: Dict[str, Any], target_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze schema differences - complexity 4"""
        self.changes.clear()

        if not current_schema or not target_schema:  # +1
            return {"error": "Missing schema data"}

        current_tables = set(current_schema.get("tables", {}).keys())
        target_tables = set(target_schema.get("tables", {}).keys())

        # Table additions/deletions
        added_tables = target_tables - current_tables  # +1
        removed_tables = current_tables - target_tables
        common_tables = current_tables & target_tables

        for table in added_tables:
            self.changes.append({"action": "add_table", "table": table})

        for table in removed_tables:
            self.changes.append({"action": "drop_table", "table": table})

        # Column changes
        for table in common_tables:  # +1
            col_changes = self._analyze_column_changes(
                current_schema["tables"][table], target_schema["tables"][table], table
            )
            self.changes.extend(col_changes)  # +1

        return {
            "total_changes": len(self.changes),
            "changes": self.changes.copy(),
            "tables_added": len(added_tables),
            "tables_removed": len(removed_tables),
            "tables_modified": sum(1 for c in self.changes if c["action"].startswith("modify")),
        }

    def get_migration_complexity(self) -> str:
        """Estimate migration complexity - complexity 3"""
        if not self.changes:  # +1
            return "none"

        destructive_ops = sum(
            1 for c in self.changes if c["action"] in ["drop_table", "drop_column"]
        )

        if destructive_ops > 0:  # +1
            return "high"
        elif len(self.changes) > 10:  # +1
            return "medium"
        else:
            return "low"

    def prioritize_changes(self) -> List[Dict[str, Any]]:
        """Prioritize migration changes - complexity 3"""
        priority_order = {
            "add_table": 1,
            "add_column": 2,
            "modify_column": 3,
            "drop_column": 4,
            "drop_table": 5,
        }

        return sorted(self.changes, key=lambda x: priority_order.get(x["action"], 10))  # +1

    def _analyze_column_changes(
        self, current_table: Dict[str, Any], target_table: Dict[str, Any], table_name: str
    ) -> List[Dict[str, Any]]:
        """Analyze column changes - complexity 3"""
        changes = []

        current_cols = set(current_table.get("columns", {}).keys())
        target_cols = set(target_table.get("columns", {}).keys())

        # New columns
        for col in target_cols - current_cols:  # +1
            changes.append({"action": "add_column", "table": table_name, "column": col})

        # Removed columns
        for col in current_cols - target_cols:  # +1
            changes.append({"action": "drop_column", "table": table_name, "column": col})

        return changes
