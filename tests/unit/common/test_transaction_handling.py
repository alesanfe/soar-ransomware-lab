#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Transaction Handling Tests
Unit tests for transaction handling
"""

from unittest.mock import patch

import pytest

from soar_lab.db.transaction import TransactionManager


class TestTransactionHandling:
    """Test transaction handling."""

    @pytest.fixture
    def transaction_manager(self):
        """Create transaction manager for testing."""
        return TransactionManager()

    def test_commit_transaction(self, transaction_manager):
        """Test successful transaction commit."""
        with patch("soar_lab.db.transaction.Transaction.commit") as mock_commit:
            transaction = transaction_manager.begin()

            # Perform operations
            transaction.execute("INSERT INTO test VALUES (1, 'test')")

            # Commit
            transaction.commit()

            assert mock_commit.called, "Commit should be called"

    def test_rollback_transaction(self, transaction_manager):
        """Test transaction rollback on error."""
        with patch("soar_lab.db.transaction.Transaction.rollback") as mock_rollback:
            transaction = transaction_manager.begin()

            # Perform operations
            transaction.execute("INSERT INTO test VALUES (1, 'test')")

            # Rollback
            transaction.rollback()

            assert mock_rollback.called, "Rollback should be called"

    def test_atomic_operations(self, transaction_manager):
        """Test atomic transaction operations."""
        with patch("soar_lab.db.transaction.Transaction.commit") as mock_commit:
            with patch("soar_lab.db.transaction.Transaction.rollback") as mock_rollback:
                with transaction_manager.atomic() as transaction:
                    transaction.execute("INSERT INTO test VALUES (1, 'test')")
                    transaction.execute("UPDATE test SET value = 'updated' WHERE id = 1")

                # Should commit on success
                assert mock_commit.called, "Should commit on success"
                assert not mock_rollback.called, "Should not rollback on success"

    def test_nested_transactions(self, transaction_manager):
        """Test nested transaction handling."""
        with patch("soar_lab.db.transaction.Transaction.commit") as mock_commit:
            with transaction_manager.atomic() as outer_tx:
                outer_tx.execute("INSERT INTO test VALUES (1, 'outer')")

                with transaction_manager.atomic() as inner_tx:
                    inner_tx.execute("INSERT INTO test VALUES (2, 'inner')")

                outer_tx.execute("UPDATE test SET value = 'updated'")

            # Both should commit
            assert mock_commit.called, "Nested transactions should commit"

    def test_transaction_rollback_on_exception(self, transaction_manager):
        """Test automatic rollback on exception."""
        with patch("soar_lab.db.transaction.Transaction.rollback") as mock_rollback:
            with pytest.raises(Exception):
                with transaction_manager.atomic() as transaction:
                    transaction.execute("INSERT INTO test VALUES (1, 'test')")
                    raise Exception("Test error")

            # Should rollback on exception
            assert mock_rollback.called, "Should rollback on exception"

    def test_transaction_isolation(self, transaction_manager):
        """Test transaction isolation."""
        with patch("soar_lab.db.transaction.Transaction.set_isolation_level") as mock_isolation:
            transaction_manager.begin(isolation_level="SERIALIZABLE")

            assert mock_isolation.called, "Isolation level should be set"

    def test_transaction_savepoint(self, transaction_manager):
        """Test transaction savepoints."""
        with patch("soar_lab.db.transaction.Transaction.create_savepoint") as mock_savepoint:
            with transaction_manager.atomic() as transaction:
                transaction.execute("INSERT INTO test VALUES (1, 'test')")
                transaction.create_savepoint("sp1")
                transaction.execute("INSERT INTO test VALUES (2, 'test')")
                transaction.rollback_to_savepoint("sp1")

            assert mock_savepoint.called, "Savepoint should be created"

    def test_transaction_timeout(self, transaction_manager):
        """Test transaction timeout."""
        with patch("soar_lab.db.transaction.Transaction.commit") as mock_commit:

            def slow_commit():
                import time

                time.sleep(10)

            mock_commit.side_effect = slow_commit

            with pytest.raises(Exception):
                with transaction_manager.atomic(timeout=1) as transaction:
                    transaction.execute("INSERT INTO test VALUES (1, 'test')")

    def test_transaction_retry_on_deadlock(self, transaction_manager):
        """Test transaction retry on deadlock."""
        call_count = [0]

        def execute_with_deadlock():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Deadlock detected")
            return "success"

        result = transaction_manager.execute_with_retry(
            execute_with_deadlock, max_retries=3, retry_on=[Exception("Deadlock detected")]
        )

        assert result == "success", "Should succeed after retries"
        assert call_count[0] == 3, "Should have retried twice"

    def test_transaction_context_manager(self, transaction_manager):
        """Test transaction as context manager."""
        with patch("soar_lab.db.transaction.Transaction.commit") as mock_commit:
            with transaction_manager.atomic() as transaction:
                transaction.execute("INSERT INTO test VALUES (1, 'test')")

            # Should auto-commit on exit
            assert mock_commit.called, "Should auto-commit on context exit"

    def test_multiple_concurrent_transactions(self, transaction_manager):
        """Test multiple concurrent transactions."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []

        def execute_transaction(i):
            with patch("soar_lab.db.transaction.Transaction.commit"):
                with transaction_manager.atomic() as transaction:
                    transaction.execute(f"INSERT INTO test VALUES ({i}, 'test')")
                return i

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_transaction, i) for i in range(10)]
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == 10, "All transactions should complete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
