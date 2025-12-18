"""
集成测试 - 使用真实音乐库测试
"""

import os
import pytest


@pytest.mark.skipif(
    not os.environ.get("TEST_MUSIC_DIR"),
    reason="需要设置环境变量 TEST_MUSIC_DIR 指向真实音乐目录"
)
def test_library_scan():
    """测试媒体库扫描（使用真实音乐库）"""
    from core.database import DatabaseManager
    from services.library_service import LibraryService
    
    # 使用临时数据库
    DatabaseManager.reset_instance()
    db = DatabaseManager("test_integration.db")
    
    try:
        service = LibraryService(db)
        
        # 从环境变量获取扫描目录
        music_dir = os.environ.get("TEST_MUSIC_DIR", "")
        
        if os.path.exists(music_dir):
            print(f"\n扫描目录: {music_dir}")
            
            def progress(current, total, path):
                if current % 10 == 0:
                    print(f"  进度: {current}/{total}")
            
            added = service.scan([music_dir], progress_callback=progress)
            
            print(f"\n扫描完成!")
            print(f"  添加曲目: {added}")
            print(f"  库中总数: {service.get_track_count()}")
            
            # 获取一些曲目信息
            tracks = service.get_all_tracks()[:5]
            print(f"\n前5首曲目:")
            for t in tracks:
                print(f"  - {t.display_name} ({t.duration_str})")
            
            # 获取艺术家
            artists = service.get_artists()
            print(f"\n艺术家数量: {len(artists)}")
            if artists:
                for a in artists[:5]:
                    print(f"  - {a.name} ({a.track_count}首)")
            
            # 获取专辑
            albums = service.get_albums()
            print(f"\n专辑数量: {len(albums)}")
            if albums:
                for al in albums[:5]:
                    print(f"  - {al.title}")
            
            assert added > 0 or service.get_track_count() > 0
        else:
            print(f"音乐目录不存在: {music_dir}")
            print("跳过真实库扫描测试")
    
    finally:
        DatabaseManager.reset_instance()
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")


if __name__ == "__main__":
    test_library_scan()
