"""
Glossary domain entity for representing translation glossaries.

This module defines the domain model for glossaries and their terms.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class GlossaryTerm:
    """Domain entity representing a glossary term."""

    source_term: str
    target_term: str
    context: Optional[str] = None
    priority: int = 1
    case_sensitive: bool = False
    whole_word_only: bool = True
    category: Optional[str] = None
    notes: Optional[str] = None
    usage_count: int = 0
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Glossary:
    """Domain entity representing a complete glossary."""

    name: str
    description: str
    language_pair: Tuple[str, str]
    terms: Dict[str, GlossaryTerm]
    version: str = "1.0"
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    category: str = "general"
    tags: Optional[List[str]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.tags is None:
            self.tags = []