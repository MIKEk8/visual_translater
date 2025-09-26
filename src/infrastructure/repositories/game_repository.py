"""
Game Repository for managing game profile persistence and community databases.

This repository handles storage and retrieval of game profiles,
including community-maintained game databases.
"""

import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime

from src.services.game_detector_service import GameProfile, GamePlatform
from src.utils.logger import logger


class GameRepository:
    """Repository for game profile data management."""

    def __init__(self, data_dir: str = "data/games"):
        """Initialize the game repository.

        Args:
            data_dir: Directory for storing game data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.local_db_file = self.data_dir / "local_games.json"
        self.community_db_file = self.data_dir / "community_games.json"
        self.user_db_file = self.data_dir / "user_games.json"

        # Community database URL (placeholder)
        self.community_db_url = "https://raw.githubusercontent.com/visual-translator/game-database/main/games.json"

        logger.debug(f"GameRepository initialized with data directory: {data_dir}")

    async def save_game_profile(self, profile: GameProfile, profile_type: str = "user") -> bool:
        """Save a game profile to the appropriate database.

        Args:
            profile: GameProfile to save
            profile_type: Type of database ("user", "local", "community")

        Returns:
            True if saved successfully
        """
        try:
            if profile_type == "user":
                db_file = self.user_db_file
            elif profile_type == "local":
                db_file = self.local_db_file
            elif profile_type == "community":
                db_file = self.community_db_file
            else:
                raise ValueError(f"Invalid profile type: {profile_type}")

            # Load existing data
            existing_data = await self._load_database(db_file)
            games = existing_data.get("games", {})

            # Add/update the game profile
            games[profile.process_name.lower()] = profile.to_dict()

            # Save back to file
            save_data = {
                "games": games,
                "last_updated": datetime.now().isoformat(),
                "version": existing_data.get("version", "1.0")
            }

            await self._save_database(db_file, save_data)

            logger.debug(f"Saved game profile: {profile.name} to {profile_type} database")
            return True

        except Exception as e:
            logger.error(f"Failed to save game profile {profile.name}: {e}")
            return False

    async def load_game_profile(self, process_name: str, search_all: bool = True) -> Optional[GameProfile]:
        """Load a game profile by process name.

        Args:
            process_name: Process name to search for
            search_all: Whether to search all databases or just user database

        Returns:
            GameProfile if found, None otherwise
        """
        process_name = process_name.lower()

        # Search order: user -> local -> community
        databases = [self.user_db_file]
        if search_all:
            databases.extend([self.local_db_file, self.community_db_file])

        for db_file in databases:
            try:
                data = await self._load_database(db_file)
                games = data.get("games", {})

                if process_name in games:
                    profile = GameProfile.from_dict(games[process_name])
                    logger.debug(f"Loaded game profile: {profile.name} from {db_file.name}")
                    return profile

            except Exception as e:
                logger.debug(f"Error loading from {db_file.name}: {e}")
                continue

        return None

    async def delete_game_profile(self, process_name: str, profile_type: str = "user") -> bool:
        """Delete a game profile.

        Args:
            process_name: Process name of game to delete
            profile_type: Type of database to delete from

        Returns:
            True if deleted, False if not found
        """
        try:
            if profile_type == "user":
                db_file = self.user_db_file
            elif profile_type == "local":
                db_file = self.local_db_file
            else:
                raise ValueError("Cannot delete from community database")

            process_name = process_name.lower()

            # Load existing data
            data = await self._load_database(db_file)
            games = data.get("games", {})

            if process_name not in games:
                return False

            # Remove the game
            del games[process_name]

            # Save updated data
            save_data = {
                "games": games,
                "last_updated": datetime.now().isoformat(),
                "version": data.get("version", "1.0")
            }

            await self._save_database(db_file, save_data)

            logger.debug(f"Deleted game profile: {process_name} from {profile_type} database")
            return True

        except Exception as e:
            logger.error(f"Failed to delete game profile {process_name}: {e}")
            return False

    def load_game_profiles(self, include_community: bool = True) -> List[GameProfile]:
        """Load game profiles synchronously (for test compatibility).

        Args:
            include_community: Whether to include community database

        Returns:
            List of game profiles
        """
        # Synchronous wrapper for async list_game_profiles
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.list_game_profiles(include_community=include_community))

    async def list_game_profiles(
        self,
        platform: Optional[GamePlatform] = None,
        include_community: bool = True
    ) -> List[GameProfile]:
        """List all game profiles.

        Args:
            platform: Optional platform filter
            include_community: Whether to include community database

        Returns:
            List of game profiles
        """
        profiles = []
        seen_processes = set()

        # Load from all databases (user takes precedence)
        databases = [self.user_db_file, self.local_db_file]
        if include_community:
            databases.append(self.community_db_file)

        for db_file in databases:
            try:
                data = await self._load_database(db_file)
                games = data.get("games", {})

                for process_name, game_data in games.items():
                    if process_name in seen_processes:
                        continue  # Skip duplicates, user database takes precedence

                    try:
                        profile = GameProfile.from_dict(game_data)

                        # Apply platform filter
                        if platform and profile.platform != platform:
                            continue

                        profiles.append(profile)
                        seen_processes.add(process_name)

                    except Exception as e:
                        logger.debug(f"Failed to parse game profile {process_name}: {e}")
                        continue

            except Exception as e:
                logger.debug(f"Error loading from {db_file.name}: {e}")
                continue

        # Sort by name
        profiles.sort(key=lambda p: p.name.lower())

        return profiles

    async def update_community_database(self, force_update: bool = False) -> bool:
        """Update the community game database from remote source.

        Args:
            force_update: Force update even if recently updated

        Returns:
            True if updated successfully
        """
        try:
            # Check if we need to update
            if not force_update and self.community_db_file.exists():
                data = await self._load_database(self.community_db_file)
                last_updated = data.get("last_updated")

                if last_updated:
                    updated_time = datetime.fromisoformat(last_updated)
                    age_hours = (datetime.now() - updated_time).total_seconds() / 3600

                    if age_hours < 24:  # Don't update more than once per day
                        logger.debug("Community database is up to date")
                        return True

            # Download community database
            logger.info("Updating community game database...")

            async with aiohttp.ClientSession() as session:
                async with session.get(self.community_db_url, timeout=30) as response:
                    if response.status == 200:
                        community_data = await response.json()

                        # Validate the data structure
                        if "games" in community_data:
                            # Add metadata
                            community_data["last_updated"] = datetime.now().isoformat()
                            community_data["source"] = "community"

                            await self._save_database(self.community_db_file, community_data)

                            logger.info(f"Updated community database with {len(community_data['games'])} games")
                            return True
                        else:
                            logger.error("Invalid community database format")
                            return False
                    else:
                        logger.error(f"Failed to download community database: HTTP {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error("Timeout updating community database")
            return False
        except Exception as e:
            logger.error(f"Failed to update community database: {e}")
            return False

    async def search_games(
        self,
        query: str,
        platform: Optional[GamePlatform] = None,
        include_community: bool = True
    ) -> List[GameProfile]:
        """Search for games by name or process.

        Args:
            query: Search query
            platform: Optional platform filter
            include_community: Whether to search community database

        Returns:
            List of matching game profiles
        """
        query = query.lower().strip()
        if not query:
            return []

        all_profiles = await self.list_game_profiles(platform, include_community)
        matches = []

        for profile in all_profiles:
            # Search in name, executable, and process name
            search_text = f"{profile.name} {profile.executable} {profile.process_name}".lower()

            if query in search_text:
                matches.append(profile)

        # Sort by relevance (exact matches first)
        def relevance_score(profile):
            name_exact = 1 if query == profile.name.lower() else 0
            name_starts = 1 if profile.name.lower().startswith(query) else 0
            name_contains = 1 if query in profile.name.lower() else 0
            return name_exact * 100 + name_starts * 10 + name_contains

        matches.sort(key=relevance_score, reverse=True)

        return matches

    async def get_popular_games(self, limit: int = 20) -> List[GameProfile]:
        """Get popular games based on play count and detection frequency.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of popular game profiles
        """
        all_profiles = await self.list_game_profiles()

        # Sort by play count and last detected time
        def popularity_score(profile):
            play_count = profile.play_count or 0
            recency = 0

            if profile.last_detected:
                days_ago = (datetime.now() - profile.last_detected).days
                recency = max(0, 30 - days_ago)  # More recent = higher score

            return play_count * 10 + recency

        popular = sorted(all_profiles, key=popularity_score, reverse=True)

        return popular[:limit]

    async def export_user_games(self, file_path: str) -> bool:
        """Export user games to a file.

        Args:
            file_path: Path to export file

        Returns:
            True if exported successfully
        """
        try:
            user_data = await self._load_database(self.user_db_file)

            export_data = {
                "export_date": datetime.now().isoformat(),
                "export_version": "1.0",
                "games": user_data.get("games", {}),
                "total_games": len(user_data.get("games", {}))
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {export_data['total_games']} user games to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export user games: {e}")
            return False

    async def import_user_games(self, file_path: str, merge: bool = True) -> int:
        """Import user games from a file.

        Args:
            file_path: Path to import file
            merge: Whether to merge with existing games or replace

        Returns:
            Number of games imported
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            imported_games = import_data.get("games", {})

            if merge:
                # Load existing user data
                existing_data = await self._load_database(self.user_db_file)
                existing_games = existing_data.get("games", {})

                # Merge games
                existing_games.update(imported_games)
                games_to_save = existing_games
            else:
                games_to_save = imported_games

            # Save merged data
            save_data = {
                "games": games_to_save,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }

            await self._save_database(self.user_db_file, save_data)

            logger.info(f"Imported {len(imported_games)} games from {file_path}")
            return len(imported_games)

        except Exception as e:
            logger.error(f"Failed to import user games: {e}")
            return 0

    async def _load_database(self, db_file: Path) -> Dict:
        """Load database from file."""
        if not db_file.exists():
            return {"games": {}, "version": "1.0"}

        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load database {db_file.name}: {e}")
            return {"games": {}, "version": "1.0"}

    async def _save_database(self, db_file: Path, data: Dict) -> None:
        """Save database to file."""
        # Create backup of existing file
        if db_file.exists():
            backup_file = db_file.with_suffix('.backup')
            db_file.rename(backup_file)

        try:
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Remove backup on success
            backup_file = db_file.with_suffix('.backup')
            if backup_file.exists():
                backup_file.unlink()

        except Exception as e:
            # Restore backup on failure
            backup_file = db_file.with_suffix('.backup')
            if backup_file.exists():
                backup_file.rename(db_file)
            raise e

    def get_statistics(self) -> Dict[str, any]:
        """Get repository statistics."""
        stats = {
            "databases": {
                "user": self.user_db_file.exists(),
                "local": self.local_db_file.exists(),
                "community": self.community_db_file.exists()
            },
            "data_directory": str(self.data_dir),
            "community_url": self.community_db_url
        }

        return stats