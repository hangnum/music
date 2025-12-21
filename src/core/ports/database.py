# -*- coding: utf-8 -*-
"""
Database Port Interface

Defines an abstract interface for database operations, ensuring the service layer 
does not depend on specific database implementations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class IDatabase(Protocol):
    """Database Operations Interface
    
    Provides basic SQL execution and CRUD operations.
    Current implementation: DatabaseManager (SQLite)
    """
    
    def execute(self, sql: str, params: tuple = ()) -> Any:
        """Execute a SQL statement
        
        Args:
            sql: SQL statement
            params: Parameter tuple
            
        Returns:
            Execution result (e.g., lastrowid)
        """
        ...
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single record
        
        Args:
            sql: SELECT statement
            params: Parameter tuple
            
        Returns:
            Record dictionary or None
        """
        ...
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all records
        
        Args:
            sql: SELECT statement
            params: Parameter tuple
            
        Returns:
            List of record dictionaries
        """
        ...
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a record
        
        Args:
            table: Table name
            data: Field dictionary
            
        Returns:
            The ID of the new record
        """
        ...
    
    def update(
        self, 
        table: str, 
        data: Dict[str, Any], 
        where: str, 
        where_params: tuple
    ) -> int:
        """Update a record
        
        Args:
            table: Table name
            data: Fields to update
            where: WHERE clause
            where_params: Condition parameters
            
        Returns:
            Number of affected rows
        """
        ...
    
    def delete(self, table: str, where: str, where_params: tuple) -> int:
        """Delete a record
        
        Args:
            table: Table name
            where: WHERE clause
            where_params: Condition parameters
            
        Returns:
            Number of affected rows
        """
        ...
    
    def commit(self) -> None:
        """Commit the transaction"""
        ...
    
    def close(self) -> None:
        """Close the connection"""
        ...


@runtime_checkable
class ITrackRepository(Protocol):
    """Track Repository Interface
    
    Provides track-level CRUD operations, hiding underlying SQL details.
    """
    
    def get_by_id(self, track_id: str) -> Optional[Any]:
        """Fetch a track by ID"""
        ...
    
    def get_all(self) -> List[Any]:
        """Fetch all tracks"""
        ...
    
    def save(self, track: Any) -> str:
        """Save a track and return its ID"""
        ...
    
    def delete(self, track_id: str) -> bool:
        """Delete a track"""
        ...
    
    def search(self, query: str, limit: int = 50) -> List[Any]:
        """Search for tracks"""
        ...
