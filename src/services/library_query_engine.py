"""
Library Query Engine Module

Responsible for various query and search functions for the media library.
"""

from typing import Iterator, List, Optional, Dict, Any
import logging

from core.database import DatabaseManager
from models.track import Track
from models.album import Album
from models.artist import Artist

logger = logging.getLogger(__name__)


class LibraryQueryEngine:
    """
    Library Query Engine
    
    Provides various query and search functions for the media library.
    """


    """


    Library Query Engine


    


    Provides various query and search functions for the media library.


    """


    


    def __init__(self, db: DatabaseManager):


        self._db = db


    


    def get_all_tracks(self) -> List[Track]:


        """Get all tracks."""


        rows = self._db.fetch_all(


            "SELECT * FROM tracks ORDER BY artist_name, album_name, track_number"


        )


        return [Track.from_dict(row) for row in rows]


    


    def get_track(self, track_id: str) -> Optional[Track]:


        """Get a single track."""


        row = self._db.fetch_one(


            "SELECT * FROM tracks WHERE id = ?",


            (track_id,)


        )


        return Track.from_dict(row) if row else None


    


    def get_track_by_path(self, file_path: str) -> Optional[Track]:


        """Get a track by file path."""


        row = self._db.fetch_one(


            "SELECT * FROM tracks WHERE file_path = ?",


            (file_path,)


        )


        return Track.from_dict(row) if row else None


    


    def get_albums(self) -> List[Album]:


        """Get all albums."""


        rows = self._db.fetch_all(


            """SELECT a.*, 


                      ar.name as artist_name,


                      COUNT(t.id) as track_count,


                      COALESCE(SUM(t.duration_ms), 0) as total_duration_ms


               FROM albums a


               LEFT JOIN artists ar ON a.artist_id = ar.id


               LEFT JOIN tracks t ON t.album_id = a.id


               GROUP BY a.id


               ORDER BY a.title"""


        )


        


        return [Album(


            id=row["id"],


            title=row["title"],


            artist_id=row.get("artist_id"),


            artist_name=row.get("artist_name", ""),


            year=row.get("year"),


            cover_path=row.get("cover_path"),


            track_count=row["track_count"],


            total_duration_ms=row["total_duration_ms"],


        ) for row in rows]


    


    def get_album_tracks(self, album_id: str) -> List[Track]:


        """Get all tracks in an album."""


        rows = self._db.fetch_all(


            "SELECT * FROM tracks WHERE album_id = ? ORDER BY track_number",


            (album_id,)


        )


        return [Track.from_dict(row) for row in rows]


    


    def get_artists(self) -> List[Artist]:


        """Get all artists."""


        rows = self._db.fetch_all(


            """SELECT a.*,


                      COUNT(DISTINCT al.id) as album_count,


                      COUNT(DISTINCT t.id) as track_count


               FROM artists a


               LEFT JOIN albums al ON al.artist_id = a.id


               LEFT JOIN tracks t ON t.artist_id = a.id


               GROUP BY a.id


               ORDER BY a.name"""


        )


        


        return [Artist(


            id=row["id"],


            name=row["name"],


            image_path=row.get("image_path"),


            album_count=row["album_count"],


            track_count=row["track_count"],


        ) for row in rows]


    


    def get_artist_tracks(self, artist_id: str) -> List[Track]:


        """Get all tracks by an artist."""


        rows = self._db.fetch_all(


            "SELECT * FROM tracks WHERE artist_id = ? ORDER BY album_name, track_number",


            (artist_id,)


        )


        return [Track.from_dict(row) for row in rows]


    


    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:


        """


        Search the library.


        


        Args:


            query: Search keyword


            limit: Result count limit


            


        Returns:


            dict: Search results containing tracks, albums, and artists


        """


        search_term = f"%{query}%"


        


        # Search tracks


        track_rows = self._db.fetch_all(


            """SELECT * FROM tracks 


               WHERE title LIKE ? OR artist_name LIKE ? OR album_name LIKE ?


               LIMIT ?""",


            (search_term, search_term, search_term, limit)


        )


        


        # Search albums


        album_rows = self._db.fetch_all(


            """SELECT a.*, ar.name as artist_name,


                      COUNT(t.id) as track_count,


                      COALESCE(SUM(t.duration_ms), 0) as total_duration_ms


               FROM albums a


               LEFT JOIN artists ar ON a.artist_id = ar.id


               LEFT JOIN tracks t ON t.album_id = a.id


               WHERE a.title LIKE ?


               GROUP BY a.id


               LIMIT ?""",


            (search_term, limit)


        )


        


        # Search artists


        artist_rows = self._db.fetch_all(


            """SELECT a.*,


                      COUNT(DISTINCT al.id) as album_count,


                      COUNT(DISTINCT t.id) as track_count


               FROM artists a


               LEFT JOIN albums al ON al.artist_id = a.id


               LEFT JOIN tracks t ON t.artist_id = a.id


               WHERE a.name LIKE ?


               GROUP BY a.id


               LIMIT ?""",


            (search_term, limit)


        )


        


        return {


            "tracks": [Track.from_dict(row) for row in track_rows],


            "albums": [Album(


                id=row["id"],


                title=row["title"],


                artist_id=row.get("artist_id"),


                artist_name=row.get("artist_name", ""),


                year=row.get("year"),


                track_count=row["track_count"],


                total_duration_ms=row["total_duration_ms"],


            ) for row in album_rows],


            "artists": [Artist(


                id=row["id"],


                name=row["name"],


                album_count=row["album_count"],


                track_count=row["track_count"],


            ) for row in artist_rows],


        }


    


    def get_top_genres(self, limit: int = 30) -> List[str]:


        """Get a list of the most frequent genres (for hints/LLM context)."""


        try:


            limit = int(limit)


        except Exception:


            limit = 30


        limit = max(1, min(200, limit))





        rows = self._db.fetch_all(


            """SELECT genre, COUNT(*) as c


               FROM tracks


               WHERE genre IS NOT NULL AND TRIM(genre) <> ''


               GROUP BY genre


               ORDER BY c DESC


               LIMIT ?""",


            (limit,),


        )


        return [str(r.get("genre", "")).strip() for r in rows if str(r.get("genre", "")).strip()]


    


    def query_tracks(


        self,


        query: str = "",


        genre: str = "",


        artist: str = "",


        album: str = "",


        limit: int = 50,


        shuffle: bool = True,


    ) -> List[Track]:


        """


        Select tracks from the library based on conditions (genre/artist/album/keyword).





        'query' matches: title/artist_name/album_name/genre


        """


        try:


            limit = int(limit)


        except Exception:


            limit = 50


        limit = max(1, min(200, limit))





        where_parts: List[str] = []


        params: List[object] = []





        q = (query or "").strip()


        if q:


            term = f"%{q}%"


            where_parts.append("(title LIKE ? OR artist_name LIKE ? OR album_name LIKE ? OR genre LIKE ?)")


            params.extend([term, term, term, term])





        g = (genre or "").strip()


        if g:


            where_parts.append("genre LIKE ?")


            params.append(f"%{g}%")





        a = (artist or "").strip()


        if a:


            where_parts.append("artist_name LIKE ?")


            params.append(f"%{a}%")





        al = (album or "").strip()


        if al:


            where_parts.append("album_name LIKE ?")


            params.append(f"%{al}%")





        sql = "SELECT * FROM tracks"


        if where_parts:


            sql += " WHERE " + " AND ".join(where_parts)


        sql += " ORDER BY RANDOM()" if shuffle else " ORDER BY artist_name, album_name, track_number"


        sql += " LIMIT ?"


        params.append(limit)





        rows = self._db.fetch_all(sql, tuple(params))


        return [Track.from_dict(row) for row in rows]


    


    def iter_tracks_brief(self, batch_size: int = 250, limit: Optional[int] = None) -> Iterator[List[Dict[str, Any]]]:


        """


        Iterate through brief track info in pages (used for LLM semantic selection to avoid loading too much data).





        Returned dict fields include: id/title/artist_name/album_name


        """


        try:


            batch_size = int(batch_size)


        except Exception:


            batch_size = 250


        batch_size = max(50, min(800, batch_size))





        remaining = None


        if limit is not None:


            try:


                remaining = int(limit)


            except Exception:


                remaining = None


            if remaining is not None:


                remaining = max(1, remaining)





        offset = 0


        while True:


            if remaining is None:


                size = batch_size


            else:


                if remaining <= 0:


                    break


                size = min(batch_size, remaining)





            rows = self._db.fetch_all(


                """SELECT id, title, artist_name, album_name


                   FROM tracks


                   ORDER BY artist_name, album_name, title


                   LIMIT ? OFFSET ?""",


                (size, offset),


            )


            if not rows:


                break





            yield rows


            offset += len(rows)


            if remaining is not None:


                remaining -= len(rows)





    def get_tracks_by_ids(self, track_ids: List[str]) -> List[Track]:


        """Fetch tracks in bulk by a given list of IDs (order not guaranteed; caller may reorder)."""


        ids = [t for t in track_ids if isinstance(t, str) and t]


        if not ids:


            return []





        out: List[Track] = []


        # SQLite parameter limit might be low, so query in chunks


        chunk_size = 400


        for i in range(0, len(ids), chunk_size):


            chunk = ids[i : i + chunk_size]


            placeholders = ",".join(["?"] * len(chunk))


            rows = self._db.fetch_all(f"SELECT * FROM tracks WHERE id IN ({placeholders})", tuple(chunk))


            out.extend([Track.from_dict(r) for r in rows])


        return out

