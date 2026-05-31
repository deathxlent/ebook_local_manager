import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                             QGridLayout, QLabel, QFrame, QToolTip)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer

from utils import safe_str


class BookCard(QFrame):
    clicked = pyqtSignal(dict)
    double_clicked = pyqtSignal(dict)

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book
        self.is_selected = False
        self._click_timer = QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(300)
        self._click_timer.timeout.connect(self._emit_single_click)
        self._pending_book = None
        self.init_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        cover_label = QLabel()
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_label.setFixedSize(120, 160)
        cover_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)

        cover_path = self.book.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            cover_label.setPixmap(pixmap.scaled(
                120, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            parse_status = self.book.get('parse_status', '')
            status_text = ''
            if parse_status == 'parsing':
                status_text = '⏳ 解析中'
            elif parse_status == 'success':
                status_text = '✓'
            elif parse_status == 'failed':
                status_text = '✗'
            cover_label.setText(status_text)
            cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(cover_label, alignment=Qt.AlignmentFlag.AlignCenter)

        title = safe_str(self.book.get('title')) or '未知标题'
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setFixedWidth(120)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        authors = safe_str(self.book.get('authors')) or '未知作者'
        if isinstance(authors, list):
            authors = ', '.join(authors)
        author_label = QLabel(authors)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setWordWrap(True)
        author_label.setFixedWidth(120)
        author_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(author_label)

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                BookCard {
                    background-color: #E3F2FD;
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                    padding: 10px;
                }
                BookCard:hover {
                    background-color: #BBDEFB;
                    border: 2px solid #1976D2;
                }
            """)
        else:
            self.setStyleSheet("""
                BookCard {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 10px;
                }
                BookCard:hover {
                    background-color: #f5f5f5;
                    border: 1px solid #bdbdbd;
                }
            """)

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def _emit_single_click(self):
        if self._pending_book is not None:
            self.clicked.emit(self._pending_book)
            self._pending_book = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pending_book = self.book
            self._click_timer.start()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self._pending_book = None
            self.double_clicked.emit(self.book)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        tooltip_text = self.format_tooltip()
        QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        super().enterEvent(event)

    def format_tooltip(self):
        lines = []
        title = safe_str(self.book.get('title'))
        if title:
            lines.append(f"标题: {title}")
        
        subtitle = safe_str(self.book.get('subtitle'))
        if subtitle:
            lines.append(f"副标题: {subtitle}")
        
        authors = safe_str(self.book.get('authors'))
        if isinstance(authors, list):
            authors = ', '.join(authors)
        if authors:
            lines.append(f"作者: {authors}")
        
        publisher = safe_str(self.book.get('publisher'))
        if publisher:
            lines.append(f"出版社: {publisher}")
        
        pubdate = safe_str(self.book.get('pubdate'))
        if pubdate:
            lines.append(f"出版日期: {pubdate}")
        
        isbn = safe_str(self.book.get('isbn'))
        if isbn:
            lines.append(f"ISBN: {isbn}")
        
        category = safe_str(self.book.get('category'))
        if category:
            lines.append(f"豆瓣分类: {category}")
        
        dir_root = safe_str(self.book.get('dir_root')) or '-'
        dir_sub = safe_str(self.book.get('dir_sub')) or '-'
        if dir_root != '-':
            lines.append(f"分类: {dir_root}")
        if dir_sub != '-':
            lines.append(f"子分类: {dir_sub}")
        
        tags = safe_str(self.book.get('tags'))
        if isinstance(tags, list):
            tags = ', '.join(tags)
        if tags:
            lines.append(f"标签: {tags}")
        
        rating = self.book.get('rating')
        if rating:
            lines.append(f"评分: {rating:.1f}")
        
        series = safe_str(self.book.get('series'))
        if series:
            lines.append(f"丛书: {series}")
        
        extension = safe_str(self.book.get('extension'))
        if extension:
            lines.append(f"格式: {extension.upper()}")
        
        return '\n'.join(lines)


class BookshelfView(QWidget):
    book_clicked = pyqtSignal(dict)
    book_double_clicked = pyqtSignal(dict)
    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books_data = []
        self.selected_ids = set()
        self.cards = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

    def set_books(self, books_data):
        self.books_data = books_data
        self.update_view()

    def set_selected_ids(self, selected_ids):
        self.selected_ids = set(selected_ids) if selected_ids else set()
        for card in self.cards:
            book_id = card.book.get('id')
            card.set_selected(book_id in self.selected_ids)

    def update_view(self):
        self.cards = []
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        columns = max(1, (self.scroll_area.width() - 30) // 160)
        
        for idx, book in enumerate(self.books_data):
            row = idx // columns
            col = idx % columns
            
            card = BookCard(book)
            card.clicked.connect(self.on_book_clicked)
            card.double_clicked.connect(self.on_book_double_clicked)
            book_id = book.get('id')
            card.set_selected(book_id in self.selected_ids)
            self.cards.append(card)
            self.grid_layout.addWidget(card, row, col)

    def on_book_clicked(self, book):
        book_id = book.get('id')
        if book_id in self.selected_ids:
            self.selected_ids.discard(book_id)
        else:
            self.selected_ids.add(book_id)
        
        for card in self.cards:
            if card.book.get('id') == book_id:
                card.set_selected(book_id in self.selected_ids)
                break
        
        self.book_clicked.emit(book)
        self.selection_changed.emit(list(self.selected_ids))

    def on_book_double_clicked(self, book):
        book_id = book.get('id')
        self.selected_ids.add(book_id)
        for card in self.cards:
            if card.book.get('id') == book_id:
                card.set_selected(True)
                break
        
        self.selection_changed.emit(list(self.selected_ids))
        self.book_double_clicked.emit(book)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_view()
