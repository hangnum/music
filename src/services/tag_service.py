"""
Tag Service Module

Provides tag creation, management, and track-tag association operations.
"""

from typing import List, Optional
from datetime import datetime
import uuid
import logging

from core.database import DatabaseManager
from models.tag import Tag

logger = logging.getLogger(__name__)


class TagService:
    """
    Tag Service
    
    Provides CRUD operations for tags and track-tag association management.
    
    Usage example:
        tag_service = TagService(db)
        
        # Create tag
        tag = tag_service.create_tag("Favorite", "#FF5733")
        
        # Add tag to track
        tag_service.add_tag_to_track(track_id, tag.id)
        
        # Get all tags for track
        tags = tag_service.get_track_tags(track_id)
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Initialize the Tag Service.
        
        Args:
            db: Database manager instance; if None, use the default instance.
        """
        self._db = db or DatabaseManager()
    
    # ========== Tag CRUD ==========
    
    def create_tag(self, name: str, color: str = "#808080", 
                   source: str = "user") -> Optional[Tag]:
        """
        Create a new tag.
        
        Args:
            name: Tag name
            color: Tag color (hex format)
            source: Tag source ("user" for user-created, "llm" for LLM-tagged)
            
        Returns:
            Created Tag object, or None if a tag with the same name already exists.
        """
        # Check if tag with same name exists (case-insensitive)
        existing = self.get_tag_by_name(name)
        if existing:
            return None
        
        tag = Tag(
            id=str(uuid.uuid4()),
            name=name.strip(),
            color=color,
            source=source,
            created_at=datetime.now()
        )
        
        self._db.insert("tags", {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "source": tag.source,
            "created_at": tag.created_at.isoformat()
        })
        
        return tag
    
    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """
        Get a tag by ID.
        
        Args:
            tag_id: Tag ID
            
        Returns:
            Tag object, or None if it does not exist.
        """
        row = self._db.fetch_one(
            "SELECT * FROM tags WHERE id = ?",
            (tag_id,)
        )
        
        if not row:
            return None
        
        return Tag.from_dict(dict(row))
    
    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """
        Get a tag by name (case-insensitive).
        
        Args:
            name: Tag name
            
        Returns:
            Tag object, or None if it does not exist.
        """
        row = self._db.fetch_one(
            "SELECT * FROM tags WHERE name = ? COLLATE NOCASE",
            (name.strip(),)
        )
        
        if not row:
            return None
        
        return Tag.from_dict(dict(row))
    
    def get_all_tags(self) -> List[Tag]:
        """
        Get all tags.
        
        Returns:
            List of Tag objects, sorted by name.
        """
        rows = self._db.fetch_all(
            "SELECT * FROM tags ORDER BY name COLLATE NOCASE"
        )
        
        return [Tag.from_dict(dict(row)) for row in rows]
    
    def update_tag(self, tag_id: str, name: Optional[str] = None, 
                   color: Optional[str] = None) -> bool:
        """
        Update a tag.
        
        Args:
            tag_id: Tag ID
            name: New name (optional)
            color: New color (optional)
            
        Returns:
            True if the update was successful.
        """
        data = {}
        if name is not None:
            # Check if the new name conflicts with another tag
            existing = self.get_tag_by_name(name)
            if existing and existing.id != tag_id:
                return False
            data["name"] = name.strip()
        
        if color is not None:
            data["color"] = color
        
        if not data:
            return False
        
        affected = self._db.update("tags", data, "id = ?", (tag_id,))
        return affected > 0
    
    def delete_tag(self, tag_id: str) -> bool:
        """
        Delete a tag.
        
        This also removes all track associations with this tag.
        
        Args:
            tag_id: Tag ID
            
        Returns:
            True if deletion was successful.
        """
        affected = self._db.delete("tags", "id = ?", (tag_id,))
        return affected > 0
    
    # ========== Track-tag association ==========
    
    def add_tag_to_track(self, track_id: str, tag_id: str) -> bool:
        """
        Add a tag to a track.
        
        Args:
            track_id: Track ID
            tag_id: Tag ID
            
        Returns:
            True if successfully added.
        """
        try:
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO track_tags (track_id, tag_id, created_at) VALUES (?, ?, ?)",
                (track_id, tag_id, datetime.now().isoformat()),
            )
            return cursor.rowcount > 0
        except Exception:
            # Could be duplicate insertion or foreign key constraint failure
            logger.warning("Failed to add tag: track_id=%s, tag_id=%s", track_id, tag_id, exc_info=True)
            return False
    
    def remove_tag_from_track(self, track_id: str, tag_id: str) -> bool:
        """
        Remove a tag from a track.
        
        Args:
            track_id: Track ID
            tag_id: Tag ID
            
        Returns:
            True if successfully removed.
        """
        affected = self._db.delete(
            "track_tags",
            "track_id = ? AND tag_id = ?",
            (track_id, tag_id)
        )
        return affected > 0
    
    def get_track_tags(self, track_id: str) -> List[Tag]:
        """
        Get all tags for a specific track.
        
        Args:
            track_id: Track ID
            
        Returns:
            List of Tag objects.
        """
        rows = self._db.fetch_all(
            """
            SELECT t.* FROM tags t
            INNER JOIN track_tags tt ON t.id = tt.tag_id
            WHERE tt.track_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (track_id,)
        )
        
        return [Tag.from_dict(dict(row)) for row in rows]
    
    def get_track_tag_names(self, track_id: str) -> List[str]:
        """
        Get all tag names for a specific track (useful for display).
        
        Args:
            track_id: Track ID
            
        Returns:
            List of tag names.
        """
        rows = self._db.fetch_all(
            """
            SELECT t.name FROM tags t
            INNER JOIN track_tags tt ON t.id = tt.tag_id
            WHERE tt.track_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (track_id,)
        )
        
        return [row['name'] for row in rows]
    
    def get_tracks_by_tag(self, tag_id: str) -> List[str]:
        """
        Get all track IDs associated with a specific tag.
        
        Args:
            tag_id: Tag ID
            
        Returns:
            List of track IDs.
        """
        rows = self._db.fetch_all(
            "SELECT track_id FROM track_tags WHERE tag_id = ?",
            (tag_id,)
        )
        
        return [row['track_id'] for row in rows]
    
    def set_track_tags(self, track_id: str, tag_ids: List[str]) -> bool:
        """
        Set tags for a track (replaces all existing tags).
        
        Uses a transaction to ensure atomicity: if any step fails, all changes are rolled back.
        
        Args:
            track_id: Track ID
            tag_ids: New list of tag IDs
            
        Returns:
            True if successful.
        """
        try:
            with self._db.transaction():
                # First delete existing associations
                self._db.delete("track_tags", "track_id = ?", (track_id,))
                
                # Add new associations
                for tag_id in tag_ids:
                    self._db.insert("track_tags", {
                        "track_id": track_id,
                        "tag_id": tag_id,
                        "created_at": datetime.now().isoformat()
                    })
            
            return True
        except Exception:
            logger.warning("Failed to set track tags: track_id=%s, tag_ids=%s", track_id, tag_ids, exc_info=True)
            return False
    
    # ========== Search ==========
    
    def search_tags(self, query: str, limit: int = 20) -> List[Tag]:
        """
        Search for tags.
        
        Args:
            query: Search keyword
            limit: Result count limit
            
        Returns:
            List of matching Tag objects.
        """
        rows = self._db.fetch_all(
            """
            SELECT * FROM tags
            WHERE name LIKE ? COLLATE NOCASE
            ORDER BY name COLLATE NOCASE
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )
        
        return [Tag.from_dict(dict(row)) for row in rows]
    
    def get_tag_count(self) -> int:
        """
        Get the total number of tags.
        
        Returns:
            Tag count.
        """
        result = self._db.fetch_one("SELECT COUNT(*) as count FROM tags")
        return result['count'] if result else 0
    
    def get_track_count_by_tag(self, tag_id: str) -> int:
        """
        Get the number of tracks associated with a specific tag.
        
        Args:
            tag_id: Tag ID
            
        Returns:
            Track count.
        """
        result = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM track_tags WHERE tag_id = ?",
            (tag_id,)
        )
        return result['count'] if result else 0
    
    # ========== LLM Batch Tagging Support ==========
    
    def create_tag_if_not_exists(self, name: str, color: str = "#808080",
                                  source: str = "user") -> Tag:
        """
        Create a tag if it doesn't already exist.
        
        Args:
            name: Tag name
            color: Tag color
            source: Tag source
            
        Returns:
            Tag object (newly created or existing).
        """
        existing = self.get_tag_by_name(name)
        if existing:
            return existing
        
        tag = self.create_tag(name, color, source)
        if tag is None:
            # Might have been created recently in a concurrent scenario
            return self.get_tag_by_name(name)  # type: ignore
        return tag
    
    def batch_add_tags_to_track(self, track_id: str, tag_names: List[str],
                                 source: str = "llm") -> int:
        """
        Add multiple tags to a track (creating non-existent tags automatically).
        
        Args:
            track_id: Track ID
            tag_names: List of tag names
            source: Tag source
            
        Returns:
            Number of successfully added tags.
        """
        added = 0
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            
            tag = self.create_tag_if_not_exists(name, source=source)
            if self.add_tag_to_track(track_id, tag.id):
                added += 1
        
        return added
    
    def get_tracks_by_tags(self, tag_names: List[str], 
                           match_mode: str = "any",
                           limit: int = 200) -> List[str]:
        """
        Search for track IDs by tag names.
        
        Args:
            tag_names: List of tag names
            match_mode: Matching mode
                - "any": Match any tag (OR)
                - "all": Match all tags (AND)
            limit: Result count limit
            
        Returns:
            List of track IDs.
        """
        if not tag_names:
            return []
        
        tag_names = [n.strip() for n in tag_names if n.strip()]
        if not tag_names:
            return []
        
        if match_mode == "all":
            # Must match all tags
            placeholders = ",".join(["?" for _ in tag_names])
            query = f"""
                SELECT tt.track_id
                FROM track_tags tt
                INNER JOIN tags t ON tt.tag_id = t.id
                WHERE t.name IN ({placeholders}) COLLATE NOCASE
                GROUP BY tt.track_id
                HAVING COUNT(DISTINCT t.id) = ?
                LIMIT ?
            """
            params = tuple(tag_names) + (len(tag_names), limit)
        else:
            # Match any tag
            placeholders = ",".join(["?" for _ in tag_names])
            query = f"""
                SELECT DISTINCT tt.track_id
                FROM track_tags tt
                INNER JOIN tags t ON tt.tag_id = t.id
                WHERE t.name IN ({placeholders}) COLLATE NOCASE
                LIMIT ?
            """
            params = tuple(tag_names) + (limit,)
        
        rows = self._db.fetch_all(query, params)
        return [row['track_id'] for row in rows]
    
    def get_untagged_tracks(self, source: str = "llm", 
                            limit: int = 500) -> List[str]:
        """
        Get IDs of tracks not tagged by a specific source.
        
        Args:
            source: Tag source ("llm" = get tracks not tagged by LLM)
            limit: Result count limit
            
        Returns:
            List of track IDs.
        """
        if source == "llm":
            # Find tracks not in the llm_tagged_tracks table
            query = """
                SELECT t.id
                FROM tracks t
                LEFT JOIN llm_tagged_tracks ltt ON t.id = ltt.track_id
                WHERE ltt.track_id IS NULL
                LIMIT ?
            """
        else:
            # Find tracks without tags from the specified source
            query = """
                SELECT t.id
                FROM tracks t
                WHERE t.id NOT IN (
                    SELECT DISTINCT tt.track_id
                    FROM track_tags tt
                    INNER JOIN tags tg ON tt.tag_id = tg.id
                    WHERE tg.source = ?
                )
                LIMIT ?
            """
            rows = self._db.fetch_all(query, (source, limit))
            return [row['id'] for row in rows]
        
        rows = self._db.fetch_all(query, (limit,))
        return [row['id'] for row in rows]
    
    def get_all_tag_names(self, source: Optional[str] = None) -> List[str]:
        """
        Get all tag names.
        
        Args:
            source: Filter tags by a specific source (None = all sources)
            
        Returns:
            List of tag names.
        """
        if source:
            rows = self._db.fetch_all(
                "SELECT name FROM tags WHERE source = ? ORDER BY name COLLATE NOCASE",
                (source,)
            )
        else:
            rows = self._db.fetch_all(
                "SELECT name FROM tags ORDER BY name COLLATE NOCASE"
            )
        
        return [row['name'] for row in rows]
    
    def mark_track_as_tagged(self, track_id: str, job_id: Optional[str] = None) -> bool:
        """
        Mark a track as having been tagged by LLM.
        
        Args:
            track_id: Track ID
            job_id: Tagging job ID (optional)
            
        Returns:
            True if marking was successful.
        """
        try:
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO llm_tagged_tracks (track_id, job_id, tagged_at) VALUES (?, ?, ?)",
                (track_id, job_id, datetime.now().isoformat()),
            )
            return cursor.rowcount > 0
        except Exception:
            logger.warning("Failed to mark track LLM tagging status: track_id=%s, job_id=%s", track_id, job_id, exc_info=True)
            return False

