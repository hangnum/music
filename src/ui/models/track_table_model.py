"""
曲目表格模型

使用 QAbstractTableModel 实现虚拟化渲染，优化大列表性能。
"""

from typing import List, Optional, Any

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt6.QtGui import QColor

from models.track import Track


class TrackTableModel(QAbstractTableModel):
    """
    曲目表格模型
    
    通过 Model-View 架构实现虚拟化渲染，
    仅渲染可见区域，大幅提升大列表性能。
    
    Attributes:
        COLUMNS: 列定义 (标题, 艺术家, 专辑, 时长, 格式)
    """
    
    COLUMNS = ["标题", "艺术家", "专辑", "时长", "格式"]
    
    def __init__(self, parent=None):
        """初始化模型"""
        super().__init__(parent)
        self._tracks: List[Track] = []
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回行数"""
        if parent.isValid():
            return 0
        return len(self._tracks)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回列数"""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        返回指定索引的数据
        
        Args:
            index: 模型索引
            role: 数据角色
            
        Returns:
            对应角色的数据
        """
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._tracks):
            return None
        
        track = self._tracks[row]
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return track.title
            elif col == 1:
                return track.artist_name or "-"
            elif col == 2:
                return track.album_name or "-"
            elif col == 3:
                return track.duration_str
            elif col == 4:
                return track.format
        
        elif role == Qt.ItemDataRole.UserRole:
            # 返回完整 Track 对象
            return track
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (3, 4):  # 时长和格式居中
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """返回表头数据"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None
    
    def setTracks(self, tracks: List[Track]) -> None:
        """
        设置曲目列表
        
        使用 beginResetModel/endResetModel 通知视图更新。
        
        Args:
            tracks: 曲目列表
        """
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()
    
    def getTracks(self) -> List[Track]:
        """获取所有曲目"""
        return self._tracks
    
    def getTrack(self, row: int) -> Optional[Track]:
        """
        获取指定行的曲目
        
        Args:
            row: 行索引
            
        Returns:
            Track 对象，无效行返回 None
        """
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """
        按列排序
        
        Args:
            column: 列索引
            order: 排序顺序
        """
        self.beginResetModel()
        
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        key_funcs = {
            0: lambda t: t.title.lower(),
            1: lambda t: (t.artist_name or "").lower(),
            2: lambda t: (t.album_name or "").lower(),
            3: lambda t: t.duration_ms,
            4: lambda t: t.format.lower(),
        }
        
        key_func = key_funcs.get(column, lambda t: t.title.lower())
        self._tracks.sort(key=key_func, reverse=reverse)
        
        self.endResetModel()


class TrackFilterProxyModel(QSortFilterProxyModel):
    """
    曲目过滤代理模型
    
    支持按标题、艺术家、专辑进行模糊搜索过滤。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_text = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    
    def setFilterText(self, text: str) -> None:
        """设置过滤文本"""
        self._filter_text = text.lower()
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """判断行是否接受过滤"""
        if not self._filter_text:
            return True
        
        source_model = self.sourceModel()
        if not source_model:
            return True
        
        track = source_model.getTrack(source_row)
        if not track:
            return True
        
        # 搜索标题、艺术家、专辑
        return (self._filter_text in track.title.lower() or
                self._filter_text in (track.artist_name or "").lower() or
                self._filter_text in (track.album_name or "").lower())
