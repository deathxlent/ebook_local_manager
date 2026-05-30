import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                             QLabel, QToolTip, QHeaderView)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QEvent

from utils import safe_str


class TreeBookItem(QTreeWidgetItem):
    def __init__(self, book=None, parent=None):
        super().__init__(parent)
        self.book = book
        self.is_folder = book is None

    def get_tooltip_text(self):
        if self.is_folder:
            return self.text(0)
        
        book = self.book
        lines = []
        
        cover_path = book.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            lines.append("[封面]")
        
        title = safe_str(book.get('title'))
        if title:
            lines.append(f"标题: {title}")
        
        subtitle = safe_str(book.get('subtitle'))
        if subtitle:
            lines.append(f"副标题: {subtitle}")
        
        authors = safe_str(book.get('authors'))
        if isinstance(authors, list):
            authors = ', '.join(authors)
        if authors:
            lines.append(f"作者: {authors}")
        
        publisher = safe_str(book.get('publisher'))
        if publisher:
            lines.append(f"出版社: {publisher}")
        
        pubdate = safe_str(book.get('pubdate'))
        if pubdate:
            lines.append(f"出版日期: {pubdate}")
        
        isbn = safe_str(book.get('isbn'))
        if isbn:
            lines.append(f"ISBN: {isbn}")
        
        category = safe_str(book.get('category'))
        if category:
            lines.append(f"分类: {category}")
        
        tags = safe_str(book.get('tags'))
        if isinstance(tags, list):
            tags = ', '.join(tags)
        if tags:
            lines.append(f"标签: {tags}")
        
        rating = book.get('rating')
        if rating:
            lines.append(f"评分: {rating:.1f}")
        
        series = safe_str(book.get('series'))
        if series:
            lines.append(f"丛书: {series}")
        
        extension = safe_str(book.get('extension'))
        if extension:
            lines.append(f"格式: {extension.upper()}")
        
        return '\n'.join(lines)


class TreeView(QWidget):
    book_clicked = pyqtSignal(dict)
    book_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books_data = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["标题 / 目录", "作者"])
        self.tree.setColumnCount(2)
        
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 200)

        self.tree.setMouseTracking(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.itemEntered.connect(self.on_item_entered)
        self.tree.viewport().installEventFilter(self)

        layout.addWidget(self.tree)

    def set_books(self, books_data):
        self.books_data = books_data
        self.build_tree()

    def build_tree(self):
        self.tree.clear()
        
        folder_items = {}
        root_items = []

        for book in self.books_data:
            physical_path = book.get('physical_path', '')
            if not physical_path:
                item = TreeBookItem(book)
                item.setText(0, safe_str(book.get('title')) or '未知标题')
                authors = safe_str(book.get('authors')) or ''
                if isinstance(authors, list):
                    authors = ', '.join(authors)
                item.setText(1, authors)
                root_items.append(item)
                continue

            dir_path = os.path.dirname(physical_path)
            dir_name = os.path.basename(dir_path) or '根目录'
            
            if dir_path not in folder_items:
                folder_item = TreeBookItem()
                folder_item.setText(0, f"📁 {dir_name}")
                folder_item.setData(0, Qt.ItemDataRole.UserRole, dir_path)
                folder_items[dir_path] = folder_item
                root_items.append(folder_item)
            
            folder_item = folder_items[dir_path]
            book_item = TreeBookItem(book)
            book_item.setText(0, safe_str(book.get('title')) or '未知标题')
            authors = safe_str(book.get('authors')) or ''
            if isinstance(authors, list):
                authors = ', '.join(authors)
            book_item.setText(1, authors)
            folder_item.addChild(book_item)

        self.tree.addTopLevelItems(root_items)
        self.tree.expandAll()

        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            child_count = top_item.childCount()
            if child_count > 0:
                current_text = top_item.text(0)
                top_item.setText(0, f"{current_text} ({child_count})")

    def on_item_clicked(self, item, column):
        if not item.is_folder and item.book:
            self.book_clicked.emit(item.book)

    def on_item_double_clicked(self, item, column):
        if not item.is_folder and item.book:
            self.book_double_clicked.emit(item.book)

    def on_item_entered(self, item, column):
        pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ToolTip:
            index = self.tree.indexAt(event.pos())
            if index.isValid():
                item = self.tree.itemFromIndex(index)
                if isinstance(item, TreeBookItem):
                    QToolTip.showText(event.globalPos(), item.get_tooltip_text(), self.tree)
                    return True
        return super().eventFilter(obj, event)
