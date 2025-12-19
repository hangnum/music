# -*- coding: utf-8 -*-
"""
数据库端口接口

定义数据库操作的抽象接口，使服务层不依赖具体的数据库实现。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class IDatabase(Protocol):
    """数据库操作接口
    
    提供基础的 SQL 执行和 CRUD 操作。
    当前实现：DatabaseManager (SQLite)
    """
    
    def execute(self, sql: str, params: tuple = ()) -> Any:
        """执行 SQL 语句
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            执行结果（如 lastrowid）
        """
        ...
    
    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """获取单条记录
        
        Args:
            sql: SELECT 语句
            params: 参数元组
            
        Returns:
            记录字典或 None
        """
        ...
    
    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """获取所有记录
        
        Args:
            sql: SELECT 语句
            params: 参数元组
            
        Returns:
            记录字典列表
        """
        ...
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入记录
        
        Args:
            table: 表名
            data: 字段字典
            
        Returns:
            新记录 ID
        """
        ...
    
    def update(
        self, 
        table: str, 
        data: Dict[str, Any], 
        where: str, 
        where_params: tuple
    ) -> int:
        """更新记录
        
        Args:
            table: 表名
            data: 要更新的字段
            where: WHERE 条件
            where_params: 条件参数
            
        Returns:
            受影响行数
        """
        ...
    
    def delete(self, table: str, where: str, where_params: tuple) -> int:
        """删除记录
        
        Args:
            table: 表名
            where: WHERE 条件
            where_params: 条件参数
            
        Returns:
            受影响行数
        """
        ...
    
    def commit(self) -> None:
        """提交事务"""
        ...
    
    def close(self) -> None:
        """关闭连接"""
        ...


@runtime_checkable
class ITrackRepository(Protocol):
    """曲目仓储接口
    
    提供曲目级别的 CRUD 操作，隐藏底层 SQL 细节。
    """
    
    def get_by_id(self, track_id: str) -> Optional[Any]:
        """根据 ID 获取曲目"""
        ...
    
    def get_all(self) -> List[Any]:
        """获取所有曲目"""
        ...
    
    def save(self, track: Any) -> str:
        """保存曲目，返回 ID"""
        ...
    
    def delete(self, track_id: str) -> bool:
        """删除曲目"""
        ...
    
    def search(self, query: str, limit: int = 50) -> List[Any]:
        """搜索曲目"""
        ...
