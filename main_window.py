import os
import sys
import csv
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
                             QPushButton, QMenuBar, QMenu, QHeaderView, QMessageBox,
                             QAbstractItemView, QCheckBox, QFileDialog, QStackedWidget,
                             QButtonGroup)
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl

from database import Database
from ebook_parser import EbookParser
from import_window import ImportWindow
from detail_window import DetailWindow
from settings_window import SettingsWindow, CategoryManager
from douban_parser import DoubanParser
from utils import safe_str, sanitize_filename
from bookshelf_view import BookshelfView
from tree_view import TreeView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.parser = EbookParser()
        self.douban_parser = DoubanParser(parent=self)
        self.sort_column = 2
        self.sort_order = "ASC"
        self.current_search = ""
        self.books_data = []
        self.search_results = []
        self.selected_book_ids = set()
        self.current_view = "list"
        self.category_manager = CategoryManager()
        self.init_ui()
        self.refresh_books()
        self.setup_douban_callbacks()

    def init_ui(self):
        self.setWindowTitle("电子书管理器 v2.1")
        self.setMinimumSize(1600, 850)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.create_menu_bar()

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("标题、作者、分类、ISBN、标签...")
        self.search_input.textChanged.connect(self.on_search)
        top_layout.addWidget(self.search_input, 1)

        self.filter_label = QLabel("筛选:")
        self.filter_label.setVisible(False)
        top_layout.addWidget(self.filter_label)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("在搜索结果中筛选...")
        self.filter_input.setVisible(False)
        self.filter_input.textChanged.connect(self.on_filter)
        top_layout.addWidget(self.filter_input, 1)

        view_layout = QHBoxLayout()
        view_layout.setSpacing(0)
        
        self.list_view_btn = QPushButton("📋 列表")
        self.list_view_btn.setCheckable(True)
        self.list_view_btn.setChecked(True)
        self.list_view_btn.setMinimumHeight(35)
        self.list_view_btn.clicked.connect(lambda: self.switch_view("list"))
        
        self.bookshelf_view_btn = QPushButton("📚 书架")
        self.bookshelf_view_btn.setCheckable(True)
        self.bookshelf_view_btn.setMinimumHeight(35)
        self.bookshelf_view_btn.clicked.connect(lambda: self.switch_view("bookshelf"))
        
        self.tree_view_btn = QPushButton("🌳 目录树")
        self.tree_view_btn.setCheckable(True)
        self.tree_view_btn.setMinimumHeight(35)
        self.tree_view_btn.clicked.connect(lambda: self.switch_view("tree"))

        self.view_group = QButtonGroup()
        self.view_group.addButton(self.list_view_btn)
        self.view_group.addButton(self.bookshelf_view_btn)
        self.view_group.addButton(self.tree_view_btn)

        view_btn_style = """
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #bdbdbd;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover:!checked {
                background-color: #bdbdbd;
            }
        """
        self.list_view_btn.setStyleSheet(view_btn_style)
        self.bookshelf_view_btn.setStyleSheet(view_btn_style)
        self.tree_view_btn.setStyleSheet(view_btn_style)

        view_layout.addWidget(self.list_view_btn)
        view_layout.addWidget(self.bookshelf_view_btn)
        view_layout.addWidget(self.tree_view_btn)
        top_layout.addLayout(view_layout)

        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.setMinimumHeight(35)
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        top_layout.addWidget(self.select_all_btn)

        self.invert_select_btn = QPushButton("🔄 反选")
        self.invert_select_btn.setMinimumHeight(35)
        self.invert_select_btn.clicked.connect(self.invert_selection)
        top_layout.addWidget(self.invert_select_btn)

        self.batch_rename_btn = QPushButton("📝 批量重命名")
        self.batch_rename_btn.setMinimumHeight(35)
        self.batch_rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.batch_rename_btn.clicked.connect(self.batch_rename)
        self.batch_rename_btn.setEnabled(False)
        top_layout.addWidget(self.batch_rename_btn)

        self.export_csv_btn = QPushButton("📤 导出CSV")
        self.export_csv_btn.setMinimumHeight(35)
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BCD4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0097A7;
            }
        """)
        self.export_csv_btn.clicked.connect(self.export_csv)
        top_layout.addWidget(self.export_csv_btn)

        self.batch_delete_btn = QPushButton("🗑️ 批量删除选中")
        self.batch_delete_btn.setMinimumHeight(35)
        self.batch_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.batch_delete_btn.clicked.connect(self.batch_delete)
        self.batch_delete_btn.setEnabled(False)
        top_layout.addWidget(self.batch_delete_btn)

        self.cleanup_btn = QPushButton("🧹 一键清理")
        self.cleanup_btn.setMinimumHeight(35)
        self.cleanup_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.cleanup_btn.clicked.connect(self.cleanup_all)
        top_layout.addWidget(self.cleanup_btn)

        self.export_covers_btn = QPushButton("🖼️ 导出封面")
        self.export_covers_btn.setMinimumHeight(35)
        self.export_covers_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.export_covers_btn.clicked.connect(self.export_covers)
        self.export_covers_btn.setEnabled(False)
        top_layout.addWidget(self.export_covers_btn)

        main_layout.addLayout(top_layout)

        self.view_stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(16)
        self.table.setHorizontalHeaderLabels([
            "", "封面", "标题", "副标题", "作者", "出版社", "出版日期",
            "文件大小", "物理位置", "扩展名", "ISBN", "评分", "标签", 
            "分类", "子分类", "操作"
        ])

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 45)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 80)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(13, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(13, 100)
        header.setSectionResizeMode(14, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(14, 100)
        header.setSectionResizeMode(15, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(15, 150)

        self.table.verticalHeader().setDefaultSectionSize(100)

        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        self.view_stack.addWidget(self.table)

        self.bookshelf_view = BookshelfView()
        self.bookshelf_view.book_clicked.connect(self.on_bookshelf_book_clicked)
        self.bookshelf_view.book_double_clicked.connect(self.on_bookshelf_book_double_clicked)
        self.bookshelf_view.selection_changed.connect(self.on_view_selection_changed)
        self.view_stack.addWidget(self.bookshelf_view)

        self.tree_view = TreeView()
        self.tree_view.book_clicked.connect(self.on_tree_book_clicked)
        self.tree_view.book_double_clicked.connect(self.on_tree_book_double_clicked)
        self.tree_view.selection_changed.connect(self.on_view_selection_changed)
        self.view_stack.addWidget(self.tree_view)

        main_layout.addWidget(self.view_stack)

        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)

    def setup_douban_callbacks(self):
        self.douban_parser.status_signal.connect(self.on_parse_status)
        self.douban_parser.progress_signal.connect(self.on_parse_progress)
        self.douban_parser.parse_complete_signal.connect(self.on_parse_complete)

    def on_parse_status(self, message):
        self.status_label.setText(message)

    def on_parse_progress(self):
        queue_size = self.douban_parser.queue_size()
        if queue_size > 0:
            self.status_label.setText(f"解析队列剩余: {queue_size} 本书")
        else:
            self.refresh_books()

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")

        import_action = file_menu.addAction("导入电子书")
        import_action.triggered.connect(self.open_import_window)

        export_action = file_menu.addAction("导出CSV")
        export_action.triggered.connect(self.export_csv)

        file_menu.addSeparator()

        cleanup_action = file_menu.addAction("一键清理")
        cleanup_action.triggered.connect(self.cleanup_all)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)

        settings_menu = menubar.addMenu("设置")

        douban_settings_action = settings_menu.addAction("豆瓣配置")
        douban_settings_action.triggered.connect(self.open_settings_window)

        help_menu = menubar.addMenu("帮助")
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about)

    def open_settings_window(self):
        current_cookie = self.douban_parser.cookie
        dialog = SettingsWindow(self, current_cookie)
        if dialog.exec():
            new_cookie = dialog.get_cookie()
            self.douban_parser.save_config(new_cookie)
            QMessageBox.information(self, "成功", "配置已保存！")

    def refresh_books(self):
        self.search_results = self.db.get_all_books(
            sort_by=self.get_sort_column_name(self.sort_column),
            order=self.sort_order,
            search=self.current_search
        )

        filter_text = self.filter_input.text().strip().lower() if self.filter_input.isVisible() else ""
        if filter_text:
            self.books_data = [b for b in self.search_results if self._book_matches(b, filter_text)]
        else:
            self.books_data = list(self.search_results)

        self.table.setRowCount(len(self.books_data))

        for row, book in enumerate(self.books_data):
            self.set_book_row(row, book)

        self.bookshelf_view.set_books(self.books_data)
        self.tree_view.set_books(self.books_data)

        self.sync_selection_to_views()
        self.update_status()
        self.update_delete_button_state()

    def _book_matches(self, book, filter_text):
        fields = ['title', 'subtitle', 'authors', 'isbn', 'tags',
                  'publisher', 'pubdate', 'extension', 'physical_path',
                  'dir_root', 'dir_sub']
        for field in fields:
            val = safe_str(book.get(field, '')).lower()
            if filter_text in val:
                return True
        return False

    def switch_view(self, view_type):
        self.current_view = view_type
        if view_type == "list":
            self.view_stack.setCurrentWidget(self.table)
        elif view_type == "bookshelf":
            self.view_stack.setCurrentWidget(self.bookshelf_view)
        elif view_type == "tree":
            self.view_stack.setCurrentWidget(self.tree_view)

    def on_bookshelf_book_clicked(self, book):
        book_id = book.get('id')
        if book_id:
            if book_id in self.selected_book_ids:
                self.selected_book_ids.discard(book_id)
            else:
                self.selected_book_ids.add(book_id)
            self.sync_selection_to_views()
            self.update_delete_button_state()

    def on_bookshelf_book_double_clicked(self, book):
        self.open_detail_window(book)

    def on_tree_book_clicked(self, book):
        pass

    def on_tree_book_double_clicked(self, book):
        self.open_detail_window(book)

    def on_view_selection_changed(self, selected_ids):
        self.selected_book_ids = set(selected_ids)
        self.sync_selection_to_views()
        self.update_delete_button_state()

    def update_status(self):
        total = len(self.books_data)
        parsed = sum(1 for b in self.books_data if b.get('parse_status') == 'success')
        queue_size = self.douban_parser.queue_size()

        if queue_size > 0:
            self.status_label.setText(f"共 {total} 本书，已解析 {parsed} 本，队列中 {queue_size} 本")
        else:
            self.status_label.setText(f"共 {total} 本书，已解析 {parsed} 本")

    def set_book_row(self, row, book):
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(15, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        checkbox = QCheckBox()
        book_id = book.get('id')
        checkbox.setChecked(book_id in self.selected_book_ids)
        checkbox.stateChanged.connect(lambda state, b_id=book_id: self.on_checkbox_changed(b_id, state))
        checkbox_layout.addWidget(checkbox)

        self.table.setCellWidget(row, 0, checkbox_widget)

        cover_label = QLabel()
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_path = book.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            cover_label.setPixmap(pixmap.scaled(
                60, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            parse_status = book.get('parse_status', '')
            status_text = ''
            if parse_status == 'parsing':
                status_text = '⏳'
            elif parse_status == 'success':
                status_text = '✓'
            elif parse_status == 'failed':
                status_text = '✗'
            cover_label.setText(status_text)
        self.table.setCellWidget(row, 1, cover_label)

        self.table.setItem(row, 2, QTableWidgetItem(safe_str(book.get('title'))))
        self.table.setItem(row, 3, QTableWidgetItem(safe_str(book.get('subtitle'))))
        self.table.setItem(row, 4, QTableWidgetItem(safe_str(book.get('authors'))))
        self.table.setItem(row, 5, QTableWidgetItem(safe_str(book.get('publisher'))))
        self.table.setItem(row, 6, QTableWidgetItem(safe_str(book.get('pubdate'))))

        file_size = book.get('file_size', 0)
        size_str = self.parser.format_file_size(file_size) if file_size else ''
        self.table.setItem(row, 7, QTableWidgetItem(size_str))

        self.table.setItem(row, 8, QTableWidgetItem(safe_str(book.get('physical_path'))))
        self.table.setItem(row, 9, QTableWidgetItem(safe_str(book.get('extension'))))
        self.table.setItem(row, 10, QTableWidgetItem(safe_str(book.get('isbn'))))

        rating = book.get('rating', 0) or 0
        self.table.setItem(row, 11, QTableWidgetItem(f"{rating:.1f}" if rating > 0 else ''))

        self.table.setItem(row, 12, QTableWidgetItem(safe_str(book.get('tags'))))

        dir_root = safe_str(book.get('dir_root')) or '-'
        dir_sub = safe_str(book.get('dir_sub')) or '-'
        self.table.setItem(row, 13, QTableWidgetItem(dir_root))
        self.table.setItem(row, 14, QTableWidgetItem(dir_sub))

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(5, 0, 5, 0)
        btn_layout.setSpacing(8)

        open_btn = QPushButton("📖 打开")
        open_btn.setMinimumWidth(70)
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        open_btn.clicked.connect(lambda checked, b=book: self.open_book(b))
        btn_layout.addWidget(open_btn)

        detail_btn = QPushButton("✏️")
        detail_btn.setToolTip("查看/编辑详情")
        detail_btn.setMinimumWidth(40)
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        detail_btn.clicked.connect(lambda checked, b=book: self.open_detail_window(b))
        btn_layout.addWidget(detail_btn)

        self.table.setCellWidget(row, 15, btn_widget)

        if self.table.item(row, 7):
            self.table.item(row, 7).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if self.table.item(row, 11):
            self.table.item(row, 11).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table.item(row, 2).setData(Qt.ItemDataRole.UserRole, book)

    def get_sort_column_name(self, col):
        column_map = {
            2: 'title',
            3: 'subtitle',
            4: 'authors',
            5: 'publisher',
            6: 'pubdate',
            7: 'file_size',
            8: 'physical_path',
            9: 'extension',
            10: 'isbn',
            11: 'rating',
            13: 'dir_root',
            14: 'dir_sub'
        }
        return column_map.get(col, 'title')

    def on_header_clicked(self, col):
        if col in [0, 1, 15]:
            return

        if self.sort_column == col:
            self.sort_order = "DESC" if self.sort_order == "ASC" else "ASC"
        else:
            self.sort_column = col
            self.sort_order = "ASC"

        self.refresh_books()

    def on_search(self):
        self.current_search = self.search_input.text()
        has_search = bool(self.current_search.strip())
        self.filter_label.setVisible(has_search)
        self.filter_input.setVisible(has_search)
        if not has_search:
            self.filter_input.clear()
        self.refresh_books()

    def on_filter(self):
        self.refresh_books()

    def on_cell_double_clicked(self, row, col):
        if col == 0:
            return
        
        if row < 0 or row >= len(self.books_data):
            return
        
        book = self.books_data[row]
        if book and book.get('id'):
            self.open_detail_window(book)

    def on_checkbox_changed(self, book_id, state):
        if state == Qt.CheckState.Checked.value:
            self.selected_book_ids.add(book_id)
        else:
            self.selected_book_ids.discard(book_id)
        self.sync_selection_to_views()
        self.update_delete_button_state()

    def get_checked_rows(self):
        checked_rows = []
        for row, book in enumerate(self.books_data):
            if book.get('id') in self.selected_book_ids:
                checked_rows.append(row)
        return checked_rows

    def get_selected_books(self):
        return [b for b in self.books_data if b.get('id') in self.selected_book_ids]

    def sync_selection_to_views(self):
        self.bookshelf_view.set_selected_ids(self.selected_book_ids)
        self.tree_view.set_selected_ids(self.selected_book_ids)

        for row, book in enumerate(self.books_data):
            widget = self.table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    book_id = book.get('id')
                    if checkbox.isChecked() != (book_id in self.selected_book_ids):
                        checkbox.blockSignals(True)
                        checkbox.setChecked(book_id in self.selected_book_ids)
                        checkbox.blockSignals(False)

    def update_delete_button_state(self):
        checked_count = len(self.selected_book_ids)
        self.batch_delete_btn.setEnabled(checked_count > 0)
        self.batch_rename_btn.setEnabled(checked_count > 0)
        self.export_covers_btn.setEnabled(checked_count > 0)
        self.update_status()

    def toggle_select_all(self):
        all_checked = len(self.selected_book_ids) == len(self.books_data)
        for book in self.books_data:
            book_id = book.get('id')
            if book_id:
                if all_checked:
                    self.selected_book_ids.discard(book_id)
                else:
                    self.selected_book_ids.add(book_id)
        self.sync_selection_to_views()
        self.update_delete_button_state()

    def invert_selection(self):
        for book in self.books_data:
            book_id = book.get('id')
            if book_id:
                if book_id in self.selected_book_ids:
                    self.selected_book_ids.discard(book_id)
                else:
                    self.selected_book_ids.add(book_id)
        self.sync_selection_to_views()
        self.update_delete_button_state()

    def batch_parse_douban(self):
        if not self.douban_parser.has_cookie():
            QMessageBox.warning(self, "提示", "请先在设置中配置豆瓣 Cookie！")
            self.open_settings_window()
            return

        checked_rows = self.get_checked_rows()
        if not checked_rows:
            QMessageBox.warning(self, "提示", "请先选择要解析的书籍！")
            return

        count = len(checked_rows)
        reply = QMessageBox.question(
            self, "确认批量解析",
            f"确定要解析选中的 {count} 本书吗？\n（每次解析间隔约 5 秒，请耐心等待）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for row in checked_rows:
                if 0 <= row < len(self.books_data):
                    book = self.books_data[row]
                    if book and book.get('id'):
                        self.db.update_book(book['id'], {'parse_status': 'parsing'})
                        self.douban_parser.add_to_queue(
                            book['id'],
                            book
                        )

            self.refresh_books()

    def on_parse_complete(self, result, error):
        if result and 'book_id' in result:
            book_id = result['book_id']
            update_data = {
                'parse_status': 'success',
                'last_parsed_at': 'CURRENT_TIMESTAMP'
            }

            if 'title' in result:
                update_data['title'] = result['title']
            if 'subtitle' in result:
                update_data['subtitle'] = result['subtitle']
            if 'authors' in result:
                update_data['authors'] = result['authors']
            if 'isbn' in result:
                update_data['isbn'] = result['isbn']
            if 'rating' in result:
                update_data['rating'] = result['rating']
            if 'douban_url' in result:
                update_data['douban_url'] = result['douban_url']
            if 'douban_id' in result:
                update_data['douban_id'] = result['douban_id']
            if 'publisher' in result:
                update_data['publisher'] = result['publisher']
            if 'pubdate' in result:
                update_data['pubdate'] = result['pubdate']
            if 'summary' in result:
                update_data['summary'] = result['summary']
            if 'cover_url' in result:
                update_data['cover_url'] = result['cover_url']
            if 'cover_path' in result:
                update_data['cover_path'] = result['cover_path']
            if 'tags' in result:
                update_data['tags'] = result['tags']
            if 'series' in result:
                update_data['series'] = result['series']

            self.db.update_book(book_id, update_data)
            print(f"书籍解析完成: {result.get('title', '未知')}")
        elif error:
            print(f"解析失败: {error}")
            if result and 'book_id' in result:
                self.db.update_book(result['book_id'], {'parse_status': 'failed'})

    def batch_delete(self):
        checked_rows = self.get_checked_rows()
        if not checked_rows:
            return

        count = len(checked_rows)
        reply = QMessageBox.question(
            self, "确认批量删除",
            f"确定要删除选中的 {count} 本书吗？\n（只会删除记录，不会删除文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for row in sorted(checked_rows, reverse=True):
                if 0 <= row < len(self.books_data):
                    book = self.books_data[row]
                    if book and book.get('id') and self.db.delete_book(book['id']):
                        deleted_count += 1

            QMessageBox.information(self, "成功", f"已成功删除 {deleted_count} 本书！")
            self.refresh_books()

    def batch_rename(self):
        checked_rows = self.get_checked_rows()
        if not checked_rows:
            return

        count = len(checked_rows)
        reply = QMessageBox.question(
            self, "确认批量重命名",
            f"确定要重命名选中的 {count} 本书吗？\n\n命名格式: \"{{标题}} - {{作者}}.{{扩展名}}\"\n\n（文件不存在将自动跳过）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            skip_count = 0
            error_count = 0

            for row in sorted(checked_rows, reverse=True):
                if 0 <= row < len(self.books_data):
                    book = self.books_data[row]
                    if not book or not book.get('id'):
                        continue

                    old_path = book.get('physical_path')
                    if not old_path or not os.path.exists(old_path):
                        skip_count += 1
                        continue

                    title = safe_str(book.get('title')).strip()
                    authors = safe_str(book.get('authors')).strip()
                    ext = safe_str(book.get('extension')).strip()

                    if not ext:
                        ext = os.path.splitext(old_path)[1].lstrip('.')

                    if not title:
                        skip_count += 1
                        continue

                    new_filename = f"{title}"
                    if authors:
                        new_filename += f" - {authors}"
                    if ext:
                        new_filename += f".{ext}"

                    new_filename = sanitize_filename(new_filename)
                    old_dir = os.path.dirname(old_path)
                    new_path = os.path.join(old_dir, new_filename)

                    if old_path == new_path:
                        continue

                    try:
                        if os.path.exists(new_path):
                            skip_count += 1
                            continue

                        os.rename(old_path, new_path)
                        self.db.update_book(book['id'], {'physical_path': new_path})
                        success_count += 1
                    except Exception as e:
                        print(f"重命名失败: {e}")
                        error_count += 1

            result_msg = f"重命名完成！\n\n成功: {success_count} 本\n跳过: {skip_count} 本\n失败: {error_count} 本"
            QMessageBox.information(self, "完成", result_msg)
            self.refresh_books()

    def export_csv(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出CSV",
            "",
            "CSV文件 (*.csv)"
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = [
                    'file_name', 'file_type', 'dir_root', 'dir_sub', 'full_dir',
                    'douban_rank', 'summary', 'douban_title', 'douban_author',
                    'douban_isbn', 'douban_url', 'douban_tags'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='\t')
                writer.writeheader()

                for book in self.books_data:
                    physical_path = safe_str(book.get('physical_path'))
                    file_name = os.path.basename(physical_path) if physical_path else ''
                    file_type = safe_str(book.get('extension'))
                    
                    dir_root = safe_str(book.get('dir_root', ''))
                    dir_sub = safe_str(book.get('dir_sub', ''))
                    
                    if dir_root and dir_sub:
                        full_dir = f"{dir_root}/{dir_sub}"
                    elif dir_root:
                        full_dir = dir_root
                    else:
                        full_dir = ''

                    douban_rank = safe_str(book.get('rating'))
                    summary = safe_str(book.get('summary'))
                    douban_title = safe_str(book.get('title'))
                    douban_author = safe_str(book.get('authors'))
                    douban_isbn = safe_str(book.get('isbn'))
                    douban_url = safe_str(book.get('douban_url'))
                    douban_tags = safe_str(book.get('tags'))

                    writer.writerow({
                        'file_name': file_name,
                        'file_type': file_type,
                        'dir_root': dir_root,
                        'dir_sub': dir_sub,
                        'full_dir': full_dir,
                        'douban_rank': douban_rank,
                        'summary': summary,
                        'douban_title': douban_title,
                        'douban_author': douban_author,
                        'douban_isbn': douban_isbn,
                        'douban_url': douban_url,
                        'douban_tags': douban_tags
                    })

            QMessageBox.information(self, "成功", f"CSV文件已导出到：\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败：{str(e)}")

    def open_book(self, book):
        filepath = book.get('physical_path')
        if filepath and os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(self, "错误", "文件不存在！")

    def open_import_window(self):
        dialog = ImportWindow(self.db, self.parser, self)
        if dialog.exec():
            self.refresh_books()

    def open_detail_window(self, book, current_index=None):
        if current_index is None:
            for i, b in enumerate(self.books_data):
                if b.get('id') == book.get('id'):
                    current_index = i
                    break
        dialog = DetailWindow(self.db, book, self.douban_parser, self.category_manager, self, self.books_data, current_index)
        dialog.book_changed.connect(self.refresh_books)
        dialog.exec()

    def export_covers(self):
        checked_rows = self.get_checked_rows()
        if not checked_rows:
            return

        export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not export_dir:
            return

        success_count = 0
        skip_count = 0
        error_count = 0

        for row in checked_rows:
            if 0 <= row < len(self.books_data):
                book = self.books_data[row]
                cover_path = book.get('cover_path')

                if not cover_path or not os.path.exists(cover_path):
                    skip_count += 1
                    continue

                title = safe_str(book.get('title')).strip()
                authors = safe_str(book.get('authors')).strip()

                new_filename = f"{title}"
                if authors:
                    new_filename += f" - {authors}"
                new_filename = sanitize_filename(new_filename)

                ext = os.path.splitext(cover_path)[1]
                if not ext:
                    ext = '.jpg'
                new_filename += ext

                dest_path = os.path.join(export_dir, new_filename)

                if os.path.exists(dest_path):
                    base_name = sanitize_filename(title)
                    if authors:
                        base_name += f" - {sanitize_filename(authors)}"
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(export_dir, f"{base_name}_{counter}{ext}")
                        counter += 1

                try:
                    import shutil
                    shutil.copy2(cover_path, dest_path)
                    success_count += 1
                except Exception as e:
                    print(f"导出封面失败: {cover_path} -> {dest_path}, {e}")
                    error_count += 1

        result_msg = f"封面导出完成！\n\n成功: {success_count} 个\n跳过: {skip_count} 个\n失败: {error_count} 个"
        QMessageBox.information(self, "完成", result_msg)

    def cleanup_all(self):
        covers_dir = os.path.join(os.path.dirname(__file__), 'covers')
        all_books = self.db.get_all_books()

        cover_files_to_delete = []
        books_to_delete = []

        if os.path.exists(covers_dir):
            all_cover_paths = set()
            for book in all_books:
                cover_path = book.get('cover_path')
                if cover_path:
                    all_cover_paths.add(os.path.abspath(cover_path))

            for filename in os.listdir(covers_dir):
                filepath = os.path.join(covers_dir, filename)
                if os.path.isfile(filepath):
                    abs_path = os.path.abspath(filepath)
                    if abs_path not in all_cover_paths:
                        cover_files_to_delete.append(filepath)

        for book in all_books:
            physical_path = book.get('physical_path')
            if not physical_path or not os.path.exists(physical_path):
                books_to_delete.append(book)

        if not cover_files_to_delete and not books_to_delete:
            QMessageBox.information(self, "提示", "数据库和封面文件都是最新的，没有需要清理的内容。")
            return

        msg_parts = []
        if cover_files_to_delete:
            msg_parts.append(f"未关联的封面文件: {len(cover_files_to_delete)} 个")
        if books_to_delete:
            msg_parts.append(f"物理文件不存在的书籍记录: {len(books_to_delete)} 条")
            for book in books_to_delete[:5]:
                title = book.get('title') or '未知标题'
                path = book.get('physical_path') or '无路径'
                msg_parts.append(f"  - {title} ({path})")
            if len(books_to_delete) > 5:
                msg_parts.append(f"  ... 还有 {len(books_to_delete) - 5} 条")

        reply = QMessageBox.question(
            self, "确认清理",
            "检测到以下需要清理的内容：\n\n" + "\n".join(msg_parts) + "\n\n确定要清理吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_covers = 0
            deleted_books = 0

            for filepath in cover_files_to_delete:
                try:
                    os.remove(filepath)
                    deleted_covers += 1
                except Exception as e:
                    print(f"删除封面文件失败: {filepath}, {e}")

            for book in books_to_delete:
                try:
                    self.db.delete_book(book['id'])
                    deleted_books += 1
                except Exception as e:
                    print(f"删除书籍记录失败: {book.get('id')}, {e}")

            result_msg = f"清理完成！\n\n"
            if cover_files_to_delete:
                result_msg += f"删除封面文件: {deleted_covers} / {len(cover_files_to_delete)} 个\n"
            if books_to_delete:
                result_msg += f"删除书籍记录: {deleted_books} / {len(books_to_delete)} 条"

            QMessageBox.information(self, "完成", result_msg)
            self.refresh_books()

    def show_about(self):
        QMessageBox.about(
            self, "关于电子书管理器",
            "电子书管理器 v2.0\n\n"
            "支持 EPUB、PDF 格式\n"
            "集成豆瓣书籍信息解析\n"
            "使用 lxml + XPath 稳定解析\n"
            "跨平台支持 Windows、Linux、Mac"
        )


def main():
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
