"""
Base repository implementation.
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseRepository(ABC):
    """Base repository with common functionality."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data")
        self.storage_path.mkdir(exist_ok=True)

    def _serialize_entity(self, entity: Any) -> Dict[str, Any]:
        """Serialize entity to dictionary."""
        if hasattr(entity, "to_dict"):
            return entity.to_dict()
        elif hasattr(entity, "__dict__"):
            return entity.__dict__
        else:
            raise ValueError(f"Cannot serialize entity: {type(entity)}")

    def _save_to_json(self, filename: str, data: Any) -> None:
        """Save data to JSON file."""
        file_path = self.storage_path / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _load_from_json(self, filename: str) -> Any:
        """Load data from JSON file."""
        file_path = self.storage_path / filename
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
