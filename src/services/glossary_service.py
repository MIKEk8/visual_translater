"""
Glossary Service for game-specific translation terminology management.

This service manages context-aware glossaries that provide consistent
translations for game-specific terms and phrases.
"""

import json
import asyncio
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from src.services.circuit_breaker import get_circuit_breaker_manager
from src.utils.logger import logger


class TermReplacementError(Exception):
    """Exception raised when term replacement fails."""
    pass


@dataclass
class GlossaryTerm:
    """Represents a single glossary term with translations and metadata."""

    source_term: str
    target_term: str
    context: Optional[str] = None
    priority: int = 1  # 1-10, higher = more important
    case_sensitive: bool = False
    whole_word_only: bool = True
    category: Optional[str] = None
    notes: Optional[str] = None
    usage_count: int = 0
    created_at: datetime = None
    last_used: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def matches(self, text: str) -> bool:
        """Check if this term matches the given text."""
        if self.whole_word_only:
            pattern = r'\b' + re.escape(self.source_term) + r'\b'
        else:
            pattern = re.escape(self.source_term)

        flags = 0 if self.case_sensitive else re.IGNORECASE
        return bool(re.search(pattern, text, flags))

    def replace_in_text(self, text: str) -> Tuple[str, int]:
        """Replace occurrences of this term in text.

        Returns:
            Tuple of (modified_text, replacement_count)
        """
        if self.whole_word_only:
            pattern = r'\b' + re.escape(self.source_term) + r'\b'
        else:
            pattern = re.escape(self.source_term)

        flags = 0 if self.case_sensitive else re.IGNORECASE

        def replacement_func(match):
            # Preserve original case if not case sensitive
            original = match.group(0)
            if not self.case_sensitive and original.isupper():
                return self.target_term.upper()
            elif not self.case_sensitive and original.istitle():
                return self.target_term.title()
            return self.target_term

        new_text, count = re.subn(pattern, replacement_func, text, flags=flags)
        return new_text, count

    def to_dict(self) -> Dict:
        """Convert term to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["last_used"] = self.last_used.isoformat() if self.last_used else None
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "GlossaryTerm":
        """Create term from dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_used") and isinstance(data["last_used"], str):
            data["last_used"] = datetime.fromisoformat(data["last_used"])
        return cls(**data)


@dataclass
class Glossary:
    """Represents a complete glossary with metadata."""

    name: str
    description: str
    language_pair: Tuple[str, str]  # (source_language, target_language)
    terms: Dict[str, GlossaryTerm]
    version: str = "1.0"
    author: Optional[str] = None
    created_at: datetime = None
    last_updated: datetime = None
    category: str = "general"
    tags: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.tags is None:
            self.tags = []

    def add_term(self, term: GlossaryTerm) -> None:
        """Add a term to the glossary."""
        key = term.source_term.lower()
        self.terms[key] = term
        self.last_updated = datetime.now()

    def remove_term(self, source_term: str) -> bool:
        """Remove a term from the glossary."""
        key = source_term.lower()
        if key in self.terms:
            del self.terms[key]
            self.last_updated = datetime.now()
            return True
        return False

    def get_term(self, source_term: str) -> Optional[GlossaryTerm]:
        """Get a term by source text."""
        key = source_term.lower()
        return self.terms.get(key)

    def get_terms_by_category(self, category: str) -> List[GlossaryTerm]:
        """Get all terms in a specific category."""
        return [term for term in self.terms.values() if term.category == category]

    def get_popular_terms(self, limit: int = 10) -> List[GlossaryTerm]:
        """Get most frequently used terms."""
        sorted_terms = sorted(
            self.terms.values(),
            key=lambda t: (t.usage_count, t.priority),
            reverse=True
        )
        return sorted_terms[:limit]

    def to_dict(self) -> Dict:
        """Convert glossary to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "language_pair": self.language_pair,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "category": self.category,
            "tags": self.tags,
            "terms": {key: term.to_dict() for key, term in self.terms.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Glossary":
        """Create glossary from dictionary."""
        # Convert datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("last_updated"), str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])

        # Convert terms
        terms_data = data.pop("terms", {})
        terms = {key: GlossaryTerm.from_dict(term_data)
                for key, term_data in terms_data.items()}
        data["terms"] = terms

        return cls(**data)


class GlossaryService:
    """Service for managing translation glossaries."""

    def __init__(self, glossaries_dir: str = "data/glossaries", glossaries_path: str = None, load_builtins: bool = None):
        """Initialize the glossary service.

        Args:
            glossaries_dir: Directory containing glossary files
            glossaries_path: Alternative parameter name for glossaries_dir (for tests)
            load_builtins: Whether to load built-in glossaries (defaults to True for default path, False for custom path)
        """
        # Accept either parameter name for compatibility
        path = glossaries_path if glossaries_path is not None else glossaries_dir
        self.glossaries_dir = Path(path)
        self.glossaries_path = path  # Add this attribute for test compatibility
        self.glossaries_dir.mkdir(parents=True, exist_ok=True)

        # Only load built-ins for default path unless explicitly specified
        if load_builtins is None:
            load_builtins = (glossaries_path is None and glossaries_dir == "data/glossaries")
        self.load_builtins = load_builtins

        self.loaded_glossaries: Dict[str, Glossary] = {}
        self.active_glossary: Optional[Glossary] = None
        self.circuit_breaker = get_circuit_breaker_manager().create_circuit_breaker("glossary")

        # Performance optimization
        self._compiled_patterns: Dict[str, List[Tuple[re.Pattern, GlossaryTerm]]] = {}
        self._last_compilation: Dict[str, datetime] = {}

        self._load_all_glossaries()
        if self.load_builtins:
            self._load_builtin_glossaries()

        logger.info(f"GlossaryService initialized with {len(self.loaded_glossaries)} glossaries")

    @property
    def available_glossaries(self) -> List[str]:
        """Get list of available glossary names."""
        return list(self.loaded_glossaries.keys())

    def _load_all_glossaries(self) -> None:
        """Load all glossary files from the directory."""
        for glossary_file in self.glossaries_dir.glob("*.json"):
            try:
                with open(glossary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                glossary = Glossary.from_dict(data)
                self.loaded_glossaries[glossary.name.lower()] = glossary

                logger.debug(f"Loaded glossary: {glossary.name} ({len(glossary.terms)} terms)")

            except Exception as e:
                logger.error(f"Failed to load glossary {glossary_file.name}: {e}")

    def _load_builtin_glossaries(self) -> None:
        """Load built-in glossaries for popular games."""
        builtin_glossaries = [
            self._create_genshin_impact_glossary(),
            self._create_final_fantasy_glossary(),
            self._create_wow_glossary(),
        ]

        for glossary in builtin_glossaries:
            glossary_file = self.glossaries_dir / f"{glossary.name.lower().replace(' ', '_')}.json"

            # Only create if doesn't exist
            if not glossary_file.exists():
                self._save_glossary_sync(glossary)

            self.loaded_glossaries[glossary.name.lower()] = glossary

    def _create_genshin_impact_glossary(self) -> Glossary:
        """Create built-in Genshin Impact glossary."""
        terms = {
            "traveler": GlossaryTerm("Traveler", "Путешественник", priority=9, category="character"),
            "primogem": GlossaryTerm("Primogem", "Примогем", priority=8, category="currency"),
            "resin": GlossaryTerm("Resin", "Смола", priority=7, category="resource"),
            "domain": GlossaryTerm("Domain", "Подземелье", priority=6, category="location"),
            "artifact": GlossaryTerm("Artifact", "Артефакт", priority=8, category="equipment"),
            "constellation": GlossaryTerm("Constellation", "Созвездие", priority=7, category="character"),
            "ascension": GlossaryTerm("Ascension", "Возвышение", priority=6, category="system"),
        }

        glossary = Glossary(
            name="Genshin Impact",
            description="Russian terminology for Genshin Impact",
            language_pair=("en", "ru"),
            terms=terms,
            category="game",
            tags=["genshin", "mihoyo", "rpg", "anime"]
        )

        return glossary

    def _create_final_fantasy_glossary(self) -> Glossary:
        """Create built-in Final Fantasy XIV glossary."""
        terms = {
            "warrior of light": GlossaryTerm("Warrior of Light", "Воин Света", priority=9, category="title"),
            "gil": GlossaryTerm("Gil", "Гил", priority=8, category="currency"),
            "duty": GlossaryTerm("Duty", "Задание", priority=7, category="activity"),
            "dungeon": GlossaryTerm("Dungeon", "Подземелье", priority=7, category="location"),
            "raid": GlossaryTerm("Raid", "Рейд", priority=8, category="activity"),
            "free company": GlossaryTerm("Free Company", "Вольная Компания", priority=6, category="social"),
        }

        glossary = Glossary(
            name="Final Fantasy XIV",
            description="Russian terminology for Final Fantasy XIV",
            language_pair=("en", "ru"),
            terms=terms,
            category="game",
            tags=["ffxiv", "square-enix", "mmo", "final-fantasy"]
        )

        return glossary

    def _create_wow_glossary(self) -> Glossary:
        """Create built-in World of Warcraft glossary."""
        terms = {
            "dungeon": GlossaryTerm("Dungeon", "Подземелье", priority=8, category="location"),
            "raid": GlossaryTerm("Raid", "Рейд", priority=9, category="activity"),
            "guild": GlossaryTerm("Guild", "Гильдия", priority=7, category="social"),
            "battleground": GlossaryTerm("Battleground", "Поле боя", priority=6, category="pvp"),
            "horde": GlossaryTerm("Horde", "Орда", priority=8, category="faction"),
            "alliance": GlossaryTerm("Alliance", "Альянс", priority=8, category="faction"),
        }

        glossary = Glossary(
            name="World of Warcraft",
            description="Russian terminology for World of Warcraft",
            language_pair=("en", "ru"),
            terms=terms,
            category="game",
            tags=["wow", "blizzard", "mmo", "warcraft"]
        )

        return glossary

    async def apply_glossary(self, text: str, translation: str) -> str:
        """Apply active glossary to translated text.

        Args:
            text: Original text
            translation: Translated text to enhance

        Returns:
            Enhanced translation with glossary terms applied
        """
        if not self.active_glossary or not translation:
            return translation

        try:
            enhanced_translation = await self.circuit_breaker.call(
                self._apply_glossary_internal,
                text,
                translation
            )
            return enhanced_translation

        except Exception as e:
            logger.error(f"Glossary application failed: {e}")
            return translation

    async def _apply_glossary_internal(self, text: str, translation: str) -> str:
        """Internal method to apply glossary terms."""
        glossary = self.active_glossary
        enhanced_translation = translation

        # Get compiled patterns for performance
        patterns = self._get_compiled_patterns(glossary.name)

        # Track replacements
        replacements_made = 0
        terms_used = []

        # Apply terms in priority order
        for pattern, term in patterns:
            if pattern.search(enhanced_translation):
                new_translation, count = term.replace_in_text(enhanced_translation)
                if count > 0:
                    enhanced_translation = new_translation
                    replacements_made += count
                    terms_used.append(term)

                    # Update usage statistics
                    term.usage_count += count
                    term.last_used = datetime.now()

        if replacements_made > 0:
            logger.debug(f"Applied {replacements_made} glossary replacements using {len(terms_used)} terms")

        return enhanced_translation

    def _get_compiled_patterns(self, glossary_name: str) -> List[Tuple[re.Pattern, GlossaryTerm]]:
        """Get compiled regex patterns for a glossary with caching."""
        cache_key = glossary_name.lower()

        # Check if we need to recompile
        glossary = self.loaded_glossaries.get(cache_key)
        if not glossary:
            return []

        last_compilation = self._last_compilation.get(cache_key)
        if (cache_key not in self._compiled_patterns or
            not last_compilation or
            glossary.last_updated > last_compilation):

            # Compile patterns
            patterns = []
            for term in glossary.terms.values():
                if term.whole_word_only:
                    pattern_str = r'\b' + re.escape(term.source_term) + r'\b'
                else:
                    pattern_str = re.escape(term.source_term)

                flags = 0 if term.case_sensitive else re.IGNORECASE
                pattern = re.compile(pattern_str, flags)
                patterns.append((pattern, term))

            # Sort by priority (higher first)
            patterns.sort(key=lambda x: x[1].priority, reverse=True)

            self._compiled_patterns[cache_key] = patterns
            self._last_compilation[cache_key] = datetime.now()

            logger.debug(f"Compiled {len(patterns)} patterns for glossary: {glossary_name}")

        return self._compiled_patterns[cache_key]

    async def set_active_glossary(self, glossary_name: str) -> bool:
        """Set the active glossary by name.

        Args:
            glossary_name: Name of the glossary to activate

        Returns:
            True if glossary was set successfully
        """
        glossary_key = glossary_name.lower()

        if glossary_key in self.loaded_glossaries:
            self.active_glossary = self.loaded_glossaries[glossary_key]
            logger.info(f"Active glossary set to: {self.active_glossary.name}")
            return True
        else:
            logger.warning(f"Glossary not found: {glossary_name}")
            return False

    def get_active_glossary(self) -> Optional[Glossary]:
        """Get the currently active glossary."""
        return self.active_glossary

    async def create_glossary(
        self,
        name: str,
        description: str,
        language_pair: Tuple[str, str],
        terms: Optional[Dict[str, GlossaryTerm]] = None,
        **kwargs
    ) -> Glossary:
        """Create a new glossary.

        Args:
            name: Glossary name
            description: Glossary description
            language_pair: Source and target language codes
            terms: Optional initial terms
            **kwargs: Additional glossary options

        Returns:
            Created Glossary object
        """
        glossary = Glossary(
            name=name,
            description=description,
            language_pair=language_pair,
            terms=terms or {},
            **kwargs
        )

        self.loaded_glossaries[name.lower()] = glossary
        await self._save_glossary(glossary)

        logger.info(f"Created new glossary: {name}")
        return glossary

    async def add_term_to_glossary(
        self,
        glossary_name: str,
        source_term: str,
        target_term: str,
        **term_options
    ) -> bool:
        """Add a term to an existing glossary.

        Args:
            glossary_name: Name of the glossary
            source_term: Source language term
            target_term: Target language term
            **term_options: Additional term options

        Returns:
            True if term was added successfully
        """
        glossary_key = glossary_name.lower()

        if glossary_key not in self.loaded_glossaries:
            logger.error(f"Glossary not found: {glossary_name}")
            return False

        glossary = self.loaded_glossaries[glossary_key]
        term = GlossaryTerm(
            source_term=source_term,
            target_term=target_term,
            **term_options
        )

        glossary.add_term(term)
        await self._save_glossary(glossary)

        # Invalidate compiled patterns cache
        if glossary_key in self._compiled_patterns:
            del self._compiled_patterns[glossary_key]

        logger.info(f"Added term '{source_term}' -> '{target_term}' to glossary: {glossary_name}")
        return True

    async def remove_term_from_glossary(
        self,
        glossary_name: str,
        source_term: str
    ) -> bool:
        """Remove a term from a glossary.

        Args:
            glossary_name: Name of the glossary
            source_term: Source term to remove

        Returns:
            True if term was removed successfully
        """
        glossary_key = glossary_name.lower()

        if glossary_key not in self.loaded_glossaries:
            logger.error(f"Glossary not found: {glossary_name}")
            return False

        glossary = self.loaded_glossaries[glossary_key]
        success = glossary.remove_term(source_term)

        if success:
            await self._save_glossary(glossary)

            # Invalidate compiled patterns cache
            if glossary_key in self._compiled_patterns:
                del self._compiled_patterns[glossary_key]

            logger.info(f"Removed term '{source_term}' from glossary: {glossary_name}")

        return success

    async def search_terms(
        self,
        query: str,
        glossary_name: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[GlossaryTerm]:
        """Search for terms across glossaries.

        Args:
            query: Search query
            glossary_name: Optional specific glossary to search
            category: Optional category filter

        Returns:
            List of matching terms
        """
        query = query.lower()
        matches = []

        # Determine which glossaries to search
        if glossary_name:
            glossary_key = glossary_name.lower()
            glossaries = [self.loaded_glossaries[glossary_key]] if glossary_key in self.loaded_glossaries else []
        else:
            glossaries = list(self.loaded_glossaries.values())

        for glossary in glossaries:
            for term in glossary.terms.values():
                # Apply category filter
                if category and term.category != category:
                    continue

                # Check if query matches
                if (query in term.source_term.lower() or
                    query in term.target_term.lower() or
                    (term.notes and query in term.notes.lower())):

                    matches.append(term)

        # Sort by priority and usage
        matches.sort(key=lambda t: (t.priority, t.usage_count), reverse=True)

        return matches

    def list_glossaries(self) -> List[Dict[str, Any]]:
        """List all available glossaries with metadata.

        Returns:
            List of glossary information dictionaries
        """
        glossary_list = []

        for glossary in self.loaded_glossaries.values():
            info = {
                "name": glossary.name,
                "description": glossary.description,
                "language_pair": glossary.language_pair,
                "term_count": len(glossary.terms),
                "category": glossary.category,
                "tags": glossary.tags,
                "version": glossary.version,
                "last_updated": glossary.last_updated.isoformat(),
                "is_active": glossary == self.active_glossary
            }
            glossary_list.append(info)

        # Sort by name
        glossary_list.sort(key=lambda g: g["name"])

        return glossary_list

    def _save_glossary_sync(self, glossary: Glossary) -> None:
        """Save a glossary synchronously (for initialization)."""
        try:
            glossary_file = self.glossaries_dir / f"{glossary.name.lower().replace(' ', '_')}.json"

            data = {
                "name": glossary.name,
                "description": glossary.description,
                "source_language": glossary.language_pair[0],
                "target_language": glossary.language_pair[1],
                "terms": [self._term_to_dict(term) for term in glossary.terms.values()],
                "created_at": glossary.created_at.isoformat(),
                "last_modified": glossary.last_updated.isoformat() if glossary.last_updated else glossary.created_at.isoformat(),
                "version": glossary.version
            }

            with open(glossary_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Glossary saved: {glossary.name}")

        except Exception as e:
            logger.error(f"Failed to save glossary {glossary.name}: {e}")

    def _term_to_dict(self, term: GlossaryTerm) -> Dict:
        """Convert GlossaryTerm to dictionary with proper datetime handling."""
        data = asdict(term)
        if data.get('created_at'):
            data['created_at'] = term.created_at.isoformat() if term.created_at else None
        if data.get('last_used'):
            data['last_used'] = term.last_used.isoformat() if term.last_used else None
        return data

    async def _save_glossary(self, glossary: Glossary) -> None:
        """Save a glossary to file."""
        filename = glossary.name.lower().replace(' ', '_').replace('/', '_') + '.json'
        filepath = self.glossaries_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(glossary.to_dict(), f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved glossary to: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save glossary {glossary.name}: {e}")
            raise

    async def export_glossary(self, glossary_name: str, export_path: str) -> bool:
        """Export a glossary to a file.

        Args:
            glossary_name: Name of glossary to export
            export_path: Path to export file

        Returns:
            True if exported successfully
        """
        glossary_key = glossary_name.lower()

        if glossary_key not in self.loaded_glossaries:
            logger.error(f"Glossary not found: {glossary_name}")
            return False

        try:
            glossary = self.loaded_glossaries[glossary_key]

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(glossary.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Exported glossary '{glossary_name}' to: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export glossary: {e}")
            return False

    async def import_glossary(self, import_path: str) -> Optional[str]:
        """Import a glossary from a file.

        Args:
            import_path: Path to glossary file

        Returns:
            Name of imported glossary or None if failed
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            glossary = Glossary.from_dict(data)
            self.loaded_glossaries[glossary.name.lower()] = glossary

            await self._save_glossary(glossary)

            logger.info(f"Imported glossary: {glossary.name}")
            return glossary.name

        except Exception as e:
            logger.error(f"Failed to import glossary from {import_path}: {e}")
            return None

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for all glossaries.

        Returns:
            Dictionary with usage statistics
        """
        stats = {
            "total_glossaries": len(self.loaded_glossaries),
            "active_glossary": self.active_glossary.name if self.active_glossary else None,
            "glossaries": {}
        }

        for name, glossary in self.loaded_glossaries.items():
            total_usage = sum(term.usage_count for term in glossary.terms.values())
            popular_terms = glossary.get_popular_terms(5)

            stats["glossaries"][name] = {
                "term_count": len(glossary.terms),
                "total_usage": total_usage,
                "category": glossary.category,
                "language_pair": glossary.language_pair,
                "popular_terms": [
                    {"term": term.source_term, "translation": term.target_term, "usage": term.usage_count}
                    for term in popular_terms
                ]
            }

        return stats