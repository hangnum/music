"""
Strict concurrency and robustness tests for Core components.
"""

import threading
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from core.event_bus import EventBus, EventType
from core.database import DatabaseManager

class TestEventBusStrict:
    """Strict tests for EventBus concurrency."""

    def setup_method(self):
        EventBus.reset_instance()

    def teardown_method(self):
        EventBus.reset_instance()

    def test_concurrent_publishing(self):
        """Test that publishing from multiple threads doesn't lose events."""
        bus = EventBus()
        received_events = []
        lock = threading.Lock()

        def handler(data):
            with lock:
                received_events.append(data)

        # Subscribe
        bus.subscribe(EventType.TRACK_STARTED, handler)

        # Number of threads and events per thread
        num_threads = 10
        events_per_thread = 100
        total_expected = num_threads * events_per_thread

        def publisher(thread_id):
            for i in range(events_per_thread):
                bus.publish(EventType.TRACK_STARTED, {"id": f"{thread_id}-{i}"})
                # Small sleep to induce context switches
                if i % 10 == 0:
                    time.sleep(0.001)

        # Run concurrent publishers
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(publisher, i) for i in range(num_threads)]
            for f in futures:
                f.result()

        # Wait a bit for processing (since publish might be async depending on implementation, 
        # but here we assume the bus handles it reasonably fast or we wait for queue drain if applicable)
        # In this implementation, if publish is async (using Qt), we can't easily test it without a Qt loop.
        # However, the current EventBus implementation likely uses direct calls or a simple queue.
        # If it relies on Qt signals, this test might need a Qt loop.
        # Let's check if publish is synchronous or if we need to wait.
        
        # Based on previous readings, publish_sync is synchronous. publish might be async.
        # Let's assume eventual consistency and wait up to 2 seconds.
        start_time = time.time()
        while len(received_events) < total_expected and time.time() - start_time < 2:
            time.sleep(0.1)

        assert len(received_events) == total_expected, f"Expected {total_expected} events, got {len(received_events)}"
        
        # Verify all IDs are present
        received_ids = {e["id"] for e in received_events}
        assert len(received_ids) == total_expected

class TestDatabaseManagerStrict:
    """Strict tests for DatabaseManager concurrency."""
    
    def setup_method(self):
        DatabaseManager.reset_instance()
        
    def teardown_method(self):
        DatabaseManager.reset_instance()
        if hasattr(self, 'db_path') and self.db_path:
            import os
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_concurrent_writes(self, tmp_path):
        """Test concurrent writes to the database."""
        self.db_path = str(tmp_path / "strict_test.db")
        db = DatabaseManager(self.db_path)
        
        # Setup schema
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER,
                msg TEXT
            )
        """)
        
        num_threads = 5
        writes_per_thread = 50
        
        def writer(thread_id):
            # Each thread needs its own connection if the manager is thread-local aware
            # or the manager should handle it.
            # We use the same manager instance.
            local_db = DatabaseManager(self.db_path)
            for i in range(writes_per_thread):
                try:
                    local_db.execute(
                        "INSERT INTO test_log (thread_id, msg) VALUES (?, ?)", 
                        (thread_id, f"msg-{i}")
                    )
                except Exception as e:
                    # Retry on lock is a common SQLite pattern, but we want to see if our Manager handles it 
                    # or if it crashes.
                    print(f"Write error in thread {thread_id}: {e}")
                    raise e
                    
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(writer, i) for i in range(num_threads)]
            for f in futures:
                f.result() # Will raise if any thread failed
                
        # Verify count
        row = db.fetch_one("SELECT COUNT(*) as cnt FROM test_log")
        assert row['cnt'] == num_threads * writes_per_thread

    def test_transaction_isolation(self, tmp_path):
        """Test that transactions are isolated between threads/connections."""
        self.db_path = str(tmp_path / "isolation_test.db")
        db_main = DatabaseManager(self.db_path)
        
        db_main.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
        db_main.execute("INSERT INTO accounts (id, balance) VALUES (1, 100)")
        
        def transaction_worker():
            db_thread = DatabaseManager(self.db_path)
            with db_thread.transaction():
                db_thread.execute("UPDATE accounts SET balance = 200 WHERE id = 1")
                # Simulate long work
                time.sleep(0.5)
                # Verify inside transaction
                row = db_thread.fetch_one("SELECT balance FROM accounts WHERE id = 1")
                assert row['balance'] == 200
                
        # Start transaction thread
        t = threading.Thread(target=transaction_worker)
        t.start()
        
        # Give it a moment to start and lock
        time.sleep(0.1)
        
        # Main thread should still see 100 (if WAL mode or isolation level permits reading old snapshot)
        # Or it might block. SQLite default isolation is SERIALIZABLE usually.
        # If it blocks, we can't easily test "seeing 100", but we can test that it DOESN'T see 200 yet.
        
        row = db_main.fetch_one("SELECT balance FROM accounts WHERE id = 1")
        # In default SQLite mode, this read might wait for the writer to finish or return the old data depending on journaling.
        # If we are in WAL mode, we might see 100. If rollback journal, read might block.
        # For this test, let's just ensure we assume standard behavior:
        # If we can read, it MUST be 100. It MUST NOT be 200 until commit.
        
        if row:
            assert row['balance'] == 100
            
        t.join()
        
        # Now it should be 200
        row = db_main.fetch_one("SELECT balance FROM accounts WHERE id = 1")
        assert row['balance'] == 200
