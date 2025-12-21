"""
Integration Tests - Testing with a Real Music Library
"""

import os
import pytest


@pytest.mark.skipif(
    not os.environ.get("TEST_MUSIC_DIR"),
    reason="Environment variable TEST_MUSIC_DIR must be set to point to a real music directory."
)
def test_library_scan():
    """Test media library scanning using a real music library."""
    from core.database import DatabaseManager
    from services.library_service import LibraryService
    
    # Use a temporary database
    DatabaseManager.reset_instance()
    db = DatabaseManager("test_integration.db")
    
    try:
        service = LibraryService(db)
        
        # Get scan directory from environment variable
        music_dir = os.environ.get("TEST_MUSIC_DIR", "")
        
        if os.path.exists(music_dir):
            print(f"\nScanning directory: {music_dir}")
            
            def progress(current, total, path):
                if current % 10 == 0:
                    print(f"  Progress: {current}/{total}")
            
            added = service.scan([music_dir], progress_callback=progress)
            
            print(f"\nScan completed!")
            print(f"  Tracks added: {added}")
            print(f"  Total tracks in library: {service.get_track_count()}")
            
            # Retrieve some track information
            tracks = service.get_all_tracks()[:5]
            print(f"\nFirst 5 tracks:")
            for t in tracks:
                print(f"  - {t.display_name} ({t.duration_str})")
            
            # Retrieve artists
            artists = service.get_artists()
            print(f"\nArtist count: {len(artists)}")
            if artists:
                for a in artists[:5]:
                    print(f"  - {a.name} ({a.track_count} tracks)")
            
            # Retrieve albums
            albums = service.get_albums()
            print(f"\nAlbum count: {len(albums)}")
            if albums:
                for al in albums[:5]:
                    print(f"  - {al.title}")
            
            assert added > 0 or service.get_track_count() > 0
        else:
            print(f"Music directory does not exist: {music_dir}")
            print("Skipping real library scan test.")
    
    finally:
        DatabaseManager.reset_instance()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")


if __name__ == "__main__":
    test_library_scan()
