"""
曲目列表模型

使用 QAbstractListModel 实现虚拟化渲染，支持拖放排序。
"""

from typing import List, Optional, Any

from PyQt6.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QMimeData, QByteArray
)

from models.track import Track


class TrackListModel(QAbstractListModel):
    """
    曲目列表模型
    
    通过 Model-View 架构实现虚拟化渲染，支持拖放重排序。
    
    Features:
        - 虚拟化渲染，仅渲染可见项
        - 支持拖放排序 (drag & drop)
        - 高亮当前播放曲目
    """
    
    MIME_TYPE = "application/x-track-indices"
    
    def __init__(self, parent=None, enable_drag_drop: bool = True):
        """
        初始化模型
        
        Args:
            parent: 父对象
            enable_drag_drop: 是否启用拖放排序
        """
        super().__init__(parent)
        self._tracks: List[Track] = []
        self._highlighted_id: Optional[str] = None
        self._enable_drag_drop = enable_drag_drop
        self._show_index = True  # 是否显示序号
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回行数"""
        if parent.isValid():
            return 0
        return len(self._tracks)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """返回指定索引的数据"""
        if not index.isValid():
            return None
        
        row = index.row()
        if row < 0 or row >= len(self._tracks):
            return None
        
        track = self._tracks[row]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # 格式：序号. 标题 - 艺术家  [时长]
            if self._show_index:
                text = f"{row + 1}. {track.title}"
            else:
                text = track.title
            
            if track.artist_name:
                text += f" - {track.artist_name}"
            text += f"  [{track.duration_str}]"
            
            # 高亮当前播放
            if self._highlighted_id and track.id == self._highlighted_id:
                text = f"▶ {text}"
            
            return text
        
        elif role == Qt.ItemDataRole.UserRole:
            return track
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            if self._highlighted_id and track.id == self._highlighted_id:
                from PyQt6.QtGui import QColor
                return QColor(Qt.GlobalColor.green)
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """返回项的标志"""
        default_flags = super().flags(index)
        
        if not index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled
        
        if self._enable_drag_drop:
            return (default_flags | Qt.ItemFlag.ItemIsDragEnabled | 
                    Qt.ItemFlag.ItemIsDropEnabled)
        
        return default_flags
    
    def supportedDropActions(self) -> Qt.DropAction:
        """支持的拖放操作"""
        return Qt.DropAction.MoveAction
    
    def mimeTypes(self) -> List[str]:
        """支持的 MIME 类型"""
        return [self.MIME_TYPE]
    
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        """生成拖放数据"""
        mime_data = QMimeData()
        
        rows = sorted(set(index.row() for index in indexes if index.isValid()))
        data = ",".join(str(row) for row in rows)
        mime_data.setData(self.MIME_TYPE, QByteArray(data.encode()))
        
        return mime_data
    
    def dropMimeData(self, data: QMimeData, action: Qt.DropAction,
                     row: int, column: int, parent: QModelIndex) -> bool:
        """处理拖放数据"""
        if action == Qt.DropAction.IgnoreAction:
            return True
        
        if not data.hasFormat(self.MIME_TYPE):
            return False
        
        # 解析源行号
        raw_data = bytes(data.data(self.MIME_TYPE)).decode()
        source_rows = [int(r) for r in raw_data.split(",") if r]
        
        if not source_rows:
            return False
        
        # 确定目标位置
        if row < 0:
            if parent.isValid():
                row = parent.row()
            else:
                row = len(self._tracks)
        
        # 移动项目
        self._move_rows(source_rows, row)
        return True
    
    def _move_rows(self, source_rows: List[int], target_row: int) -> None:
        """移动行到目标位置"""
        # 提取要移动的曲目
        tracks_to_move = [self._tracks[r] for r in sorted(source_rows, reverse=True)]
        
        # 从原位置删除
        for row in sorted(source_rows, reverse=True):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._tracks[row]
            self.endRemoveRows()
        
        # 调整目标位置
        for row in sorted(source_rows):
            if row < target_row:
                target_row -= 1
        
        # 插入到新位置
        for i, track in enumerate(reversed(tracks_to_move)):
            insert_row = target_row
            self.beginInsertRows(QModelIndex(), insert_row, insert_row)
            self._tracks.insert(insert_row, track)
            self.endInsertRows()
    
    def setTracks(self, tracks: List[Track]) -> None:
        """设置曲目列表"""
        self.beginResetModel()
        self._tracks = list(tracks)  # 复制列表避免外部修改
        self.endResetModel()
    
    def getTracks(self) -> List[Track]:
        """获取所有曲目"""
        return list(self._tracks)
    
    def getTrack(self, row: int) -> Optional[Track]:
        """获取指定行的曲目"""
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None
    
    def highlightTrack(self, track_id: Optional[str]) -> None:
        """
        高亮指定曲目
        
        Args:
            track_id: 曲目 ID，None 表示取消高亮
        """
        self._highlighted_id = track_id
        # 通知视图刷新
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ForegroundRole]
        )
    
    def setShowIndex(self, show: bool) -> None:
        """设置是否显示序号"""
        self._show_index = show
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.DisplayRole]
        )
