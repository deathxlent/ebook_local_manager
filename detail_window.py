import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QTextEdit, QPushButton, QFormLayout, QMessageBox,
                             QDoubleSpinBox, QScrollArea, QWidget, QFrame, QApplication,
                             QFileDialog, QComboBox)
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl, pyqtSignal

from utils import safe_str, sanitize_filename
from ebook_parser import EbookParser


class DetailWindow(QDialog):
    book_changed = pyqtSignal()

    def __init__(self, db, book, douban_parser, category_manager, parent=None, books_data=None, current_index=0):
        super().__init__(parent)
        self.db = db
        self.book_data = book.copy() if book else {}
        self.original_book = book.copy() if book else {}
        self.douban_parser = douban_parser
        self.category_manager = category_manager
        self.books_data = books_data or []
        self.current_index = current_index
        self.is_edit_mode = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"书籍详情 - {self.book_data.get('title', '')}")
        self.setMinimumSize(950, 800)
        self.setModal(True)

        main_layout = QVBoxLayout(self)

        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        cover_layout = QVBoxLayout()
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(250, 350)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 2px dashed #ccc;
                border-radius: 8px;
            }
        """)

        cover_path = self.book_data.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            self.cover_label.setPixmap(pixmap.scaled(
                230, 330,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.cover_label.setText("无封面")

        cover_layout.addWidget(self.cover_label)

        self.change_cover_btn = QPushButton("更换封面")
        self.change_cover_btn.setMaximumWidth(250)
        self.change_cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        self.change_cover_btn.clicked.connect(self.change_cover)
        cover_layout.addWidget(self.change_cover_btn)

        self.restore_cover_btn = QPushButton("还原封面")
        self.restore_cover_btn.setMaximumWidth(250)
        self.restore_cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.restore_cover_btn.clicked.connect(self.restore_cover)
        cover_layout.addWidget(self.restore_cover_btn)

        cover_layout.addStretch()
        content_layout.addLayout(cover_layout)

        form_container = QScrollArea()
        form_container.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(10, 10, 20, 10)
        form_layout.setSpacing(15)

        self.title_edit = QLineEdit()
        self.title_edit.setText(self.book_data.get('title', ''))
        self.title_edit.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        form_layout.addRow("标题:", self.title_edit)

        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setText(self.book_data.get('subtitle', ''))
        self.subtitle_edit.setPlaceholderText("副标题")
        form_layout.addRow("副标题:", self.subtitle_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setText(safe_str(self.book_data.get('authors', '')))
        self.author_edit.setPlaceholderText("多个作者用逗号分隔")
        form_layout.addRow("作者:", self.author_edit)

        self.publisher_edit = QLineEdit()
        self.publisher_edit.setText(self.book_data.get('publisher', ''))
        form_layout.addRow("出版社:", self.publisher_edit)

        self.pubdate_edit = QLineEdit()
        self.pubdate_edit.setText(self.book_data.get('pubdate', ''))
        self.pubdate_edit.setPlaceholderText("出版日期 (YYYY-MM-DD)")
        form_layout.addRow("出版日期:", self.pubdate_edit)

        self.isbn_edit = QLineEdit()
        self.isbn_edit.setText(self.book_data.get('isbn', ''))
        form_layout.addRow("ISBN:", self.isbn_edit)

        category_layout = QHBoxLayout()
        self.dir_root_combo = QComboBox()
        self.dir_root_combo.setEditable(True)
        self.dir_root_combo.addItem("")
        for root in self.category_manager.get_root_categories():
            self.dir_root_combo.addItem(root)
        current_root = self.book_data.get('dir_root', '')
        if current_root:
            index = self.dir_root_combo.findText(current_root)
            if index >= 0:
                self.dir_root_combo.setCurrentIndex(index)
            else:
                self.dir_root_combo.setCurrentText(current_root)
        self.dir_root_combo.currentTextChanged.connect(self.on_dir_root_changed)
        category_layout.addWidget(self.dir_root_combo, 1)

        self.dir_sub_combo = QComboBox()
        self.dir_sub_combo.setEditable(True)
        self.dir_sub_combo.addItem("")
        current_sub = self.book_data.get('dir_sub', '')
        if current_root:
            for sub in self.category_manager.get_sub_categories(current_root):
                self.dir_sub_combo.addItem(sub)
        if current_sub:
            index = self.dir_sub_combo.findText(current_sub)
            if index >= 0:
                self.dir_sub_combo.setCurrentIndex(index)
            else:
                self.dir_sub_combo.setCurrentText(current_sub)
        category_layout.addWidget(self.dir_sub_combo, 1)

        form_layout.addRow("分类:", category_layout)

        self.adjust_combo_sizes()

        self.tags_edit = QLineEdit()
        self.tags_edit.setText(safe_str(self.book_data.get('tags', '')))
        self.tags_edit.setPlaceholderText("多个标签用逗号分隔")
        form_layout.addRow("标签:", self.tags_edit)

        rating_layout = QHBoxLayout()
        self.rating_spin = QDoubleSpinBox()
        self.rating_spin.setRange(0, 10)
        self.rating_spin.setSingleStep(0.5)
        self.rating_spin.setValue(float(self.book_data.get('rating', 0) or 0))
        self.rating_spin.setDecimals(1)
        rating_layout.addWidget(self.rating_spin)
        rating_layout.addStretch()
        form_layout.addRow("评分:", rating_layout)

        self.douban_edit = QLineEdit()
        self.douban_edit.setText(self.book_data.get('douban_url', ''))
        self.douban_edit.setPlaceholderText("https://book.douban.com/subject/...")
        form_layout.addRow("豆瓣链接:", self.douban_edit)

        self.douban_id_edit = QLineEdit()
        self.douban_id_edit.setText(self.book_data.get('douban_id', ''))
        self.douban_id_edit.setReadOnly(True)
        form_layout.addRow("豆瓣ID:", self.douban_id_edit)

        self.page_count_edit = QLineEdit()
        self.page_count_edit.setText(safe_str(self.book_data.get('page_count', '')))
        form_layout.addRow("页数:", self.page_count_edit)

        info_label = QLabel("--- 文件信息 ---")
        info_label.setStyleSheet("font-weight: bold; color: #666; margin-top: 10px;")
        form_layout.addRow("", info_label)

        ext_display = QLineEdit()
        ext_display.setText(self.book_data.get('extension', ''))
        ext_display.setReadOnly(True)
        form_layout.addRow("格式:", ext_display)

        size_display = QLineEdit()
        file_size = self.book_data.get('file_size', 0)
        if file_size:
            from ebook_parser import EbookParser
            parser = EbookParser()
            size_display.setText(parser.format_file_size(file_size))
        size_display.setReadOnly(True)
        form_layout.addRow("大小:", size_display)

        path_display = QLineEdit()
        path_display.setText(self.book_data.get('physical_path', ''))
        path_display.setReadOnly(True)
        path_display.setMinimumWidth(400)
        form_layout.addRow("路径:", path_display)

        notes_label = QLabel("--- 备注/简介 ---")
        notes_label.setStyleSheet("font-weight: bold; color: #666; margin-top: 10px;")
        form_layout.addRow("", notes_label)

        self.summary_edit = QTextEdit()
        self.summary_edit.setText(self.book_data.get('summary', ''))
        self.summary_edit.setPlaceholderText("书籍内容简介...")
        self.summary_edit.setMaximumHeight(150)
        form_layout.addRow("简介:", self.summary_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setText(self.book_data.get('notes', ''))
        self.notes_edit.setPlaceholderText("个人备注、阅读笔记...")
        self.notes_edit.setMaximumHeight(100)
        form_layout.addRow("备注:", self.notes_edit)

        form_container.setWidget(form_widget)
        content_layout.addWidget(form_container, 1)

        nav_btn_layout = QHBoxLayout()

        self.prev_btn = QPushButton("⬅️ 上一本")
        self.prev_btn.setMinimumHeight(40)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.prev_btn.clicked.connect(self.go_prev)
        self.prev_btn.setEnabled(self.current_index > 0)
        nav_btn_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一本 ➡️")
        self.next_btn.setMinimumHeight(40)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.next_btn.clicked.connect(self.go_next)
        self.next_btn.setEnabled(self.current_index < len(self.books_data) - 1)
        nav_btn_layout.addWidget(self.next_btn)

        main_layout.addLayout(nav_btn_layout)

        btn_layout = QHBoxLayout()

        self.parse_btn = QPushButton("🔍 从豆瓣解析")
        self.parse_btn.setMinimumHeight(40)
        self.parse_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.parse_btn.clicked.connect(self.parse_from_douban)
        btn_layout.addWidget(self.parse_btn)

        self.open_btn = QPushButton("📖 打开书籍")
        self.open_btn.setMinimumHeight(40)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.open_btn.clicked.connect(self.open_book)
        btn_layout.addWidget(self.open_btn)

        self.update_cover_btn = QPushButton("🖼️ 更新封面到文件")
        self.update_cover_btn.setMinimumHeight(40)
        self.update_cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.update_cover_btn.clicked.connect(self.update_cover_to_file)
        btn_layout.addWidget(self.update_cover_btn)

        self.update_meta_btn = QPushButton("📝 更新元数据到文件")
        self.update_meta_btn.setMinimumHeight(40)
        self.update_meta_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BCD4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0097A7;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.update_meta_btn.clicked.connect(self.update_metadata_to_file)
        btn_layout.addWidget(self.update_meta_btn)

        self.rename_btn = QPushButton("🔤 重命名")
        self.rename_btn.setMinimumHeight(40)
        self.rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #512DA8;
            }
        """)
        self.rename_btn.clicked.connect(self.rename_file)
        btn_layout.addWidget(self.rename_btn)

        btn_layout.addStretch()

        self.edit_btn = QPushButton("✏️ 修改")
        self.edit_btn.setMinimumHeight(40)
        self.edit_btn.setMinimumWidth(100)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.edit_btn.clicked.connect(self.toggle_edit)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setMinimumHeight(40)
        self.delete_btn.setMinimumWidth(100)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_book)
        btn_layout.addWidget(self.delete_btn)

        main_layout.addLayout(btn_layout)

        self.set_edit_mode(False)

    def on_dir_root_changed(self, text):
        self.dir_sub_combo.clear()
        self.dir_sub_combo.addItem("")
        for sub in self.category_manager.get_sub_categories(text):
            self.dir_sub_combo.addItem(sub)
        self.adjust_combo_sizes()
        if self.dir_sub_combo.count() > 1 and self.is_edit_mode:
            self.dir_sub_combo.showPopup()

    def adjust_combo_sizes(self):
        max_visible_items = 15
        
        root_count = self.dir_root_combo.count()
        if root_count <= max_visible_items:
            self.dir_root_combo.setMaxVisibleItems(root_count)
        else:
            self.dir_root_combo.setMaxVisibleItems(max_visible_items)
        
        sub_count = self.dir_sub_combo.count()
        if sub_count <= max_visible_items:
            self.dir_sub_combo.setMaxVisibleItems(sub_count)
        else:
            self.dir_sub_combo.setMaxVisibleItems(max_visible_items)

    def set_edit_mode(self, edit_mode):
        self.is_edit_mode = edit_mode

        edits = [
            self.title_edit, self.subtitle_edit, self.author_edit,
            self.publisher_edit, self.pubdate_edit, self.isbn_edit,
            self.tags_edit, self.rating_spin, self.douban_edit, 
            self.page_count_edit, self.summary_edit, self.notes_edit
        ]

        for edit in edits:
            edit.setReadOnly(not edit_mode)
            if hasattr(edit, 'setButtonSymbols'):
                continue

        self.dir_root_combo.setEnabled(edit_mode)
        self.dir_sub_combo.setEnabled(edit_mode)

        if edit_mode:
            self.edit_btn.setText("💾 保存")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 25px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.edit_btn.setText("✏️ 修改")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 10px 25px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)

    def toggle_edit(self):
        if self.is_edit_mode:
            self.save_changes()
        else:
            self.set_edit_mode(True)

    def save_changes(self):
        dir_root = self.dir_root_combo.currentText().strip() or None
        dir_sub = self.dir_sub_combo.currentText().strip() or None
        
        update_data = {
            'title': self.title_edit.text(),
            'subtitle': self.subtitle_edit.text(),
            'authors': self.author_edit.text(),
            'publisher': self.publisher_edit.text(),
            'pubdate': self.pubdate_edit.text(),
            'isbn': self.isbn_edit.text(),
            'tags': self.tags_edit.text(),
            'rating': self.rating_spin.value(),
            'douban_url': self.douban_edit.text(),
            'douban_id': self.douban_id_edit.text(),
            'summary': self.summary_edit.toPlainText(),
            'notes': self.notes_edit.toPlainText(),
            'dir_root': dir_root,
            'dir_sub': dir_sub
        }

        try:
            page_count = int(self.page_count_edit.text())
            update_data['page_count'] = page_count
        except:
            pass

        if self.db.update_book(self.book_data['id'], update_data):
            self.book_data.update(update_data)
            
            file_update_success = True
            file_update_msg = ""
            
            physical_path = self.book_data.get('physical_path')
            if physical_path and os.path.exists(physical_path):
                ebook_parser = EbookParser()
                file_metadata = {
                    'title': update_data['title'],
                    'authors': update_data['authors'],
                    'publisher': update_data['publisher'],
                    'pubdate': update_data['pubdate'],
                    'isbn': update_data['isbn'],
                    'summary': update_data['summary'],
                    'tags': update_data['tags'],
                    'rating': update_data['rating'],
                    'page_count': update_data.get('page_count')
                }
                file_update_success = ebook_parser.update_metadata_to_file(physical_path, file_metadata)
                if not file_update_success:
                    file_update_msg = "\n\n⚠️ 提示：数据库已保存，但元数据写入文件失败（文件可能被占用或权限不足）"
            else:
                file_update_success = False
                file_update_msg = "\n\n⚠️ 提示：数据库已保存，但源文件不存在，无法更新元数据到文件"
            
            self.set_edit_mode(False)
            self.book_changed.emit()
            QMessageBox.information(self, "成功", f"修改已保存！{file_update_msg}")
        else:
            QMessageBox.warning(self, "错误", "保存失败！")

    def parse_from_douban(self):
        if not self.douban_parser.has_cookie():
            QMessageBox.warning(self, "提示", "请先在设置中配置豆瓣 Cookie！")
            if self.parent():
                self.parent().open_douban_settings()
            return

        title = self.title_edit.text()
        author = self.author_edit.text()

        if not title:
            QMessageBox.warning(self, "提示", "请先填写书名！")
            return

        self.set_edit_mode(True)
        self.parse_btn.setEnabled(False)
        self.parse_btn.setText("⏳ 解析中...")
        QApplication.processEvents()

        result = self.douban_parser.search_book(title, author)

        if result and 'error' not in result:
            if result.get('title'):
                self.title_edit.setText(result['title'])
            if result.get('subtitle'):
                self.subtitle_edit.setText(result['subtitle'])
            if result.get('authors'):
                authors_str = ', '.join(result['authors']) if isinstance(result['authors'], list) else str(result['authors'])
                self.author_edit.setText(authors_str)
            if result.get('publisher'):
                self.publisher_edit.setText(result['publisher'])
            if result.get('pubdate'):
                self.pubdate_edit.setText(result['pubdate'])
            if result.get('isbn'):
                self.isbn_edit.setText(result['isbn'])
            if result.get('rating'):
                self.rating_spin.setValue(float(result['rating']))
            if result.get('douban_url'):
                self.douban_edit.setText(result['douban_url'])
            if result.get('douban_id'):
                self.douban_id_edit.setText(result['douban_id'])
            if result.get('summary'):
                self.summary_edit.setPlainText(result['summary'])
            if result.get('tags'):
                tags_str = ', '.join(result['tags']) if isinstance(result['tags'], list) else str(result['tags'])
                self.tags_edit.setText(tags_str)
            if result.get('page_count'):
                self.page_count_edit.setText(str(result['page_count']))

            if result.get('cover_url'):
                self.book_data['cover_url'] = result['cover_url']
                file_hash = abs(hash(self.book_data.get('physical_path', '') + str(self.book_data.get('id', 0))))
                cover_filename = f"cover_{file_hash}.jpg"
                covers_dir = os.path.join(os.path.dirname(__file__), 'covers')
                cover_path = os.path.join(covers_dir, cover_filename)

                if self.douban_parser.download_cover(result['cover_url'], cover_path):
                    self.book_data['cover_path'] = cover_path
                    if os.path.exists(cover_path):
                        pixmap = QPixmap(cover_path)
                        self.cover_label.setPixmap(pixmap.scaled(
                            230, 330,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        ))

            self.db.update_book(self.book_data['id'], {
                'parse_status': 'success',
                'last_parsed_at': 'CURRENT_TIMESTAMP'
            })

            self.set_edit_mode(True)
            self.adjust_combo_sizes()
            self.dir_root_combo.setFocus()
            self.dir_root_combo.showPopup()
        else:
            error_msg = result.get('error', '解析失败，请检查网络或Cookie') if result else '解析失败'
            QMessageBox.warning(self, "提示", f"豆瓣抓取失败: {error_msg}")

        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("🔍 从豆瓣解析")

    def open_book(self):
        filepath = self.book_data.get('physical_path')
        if filepath and os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(self, "错误", "文件不存在！")

    def change_cover(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择封面图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.gif *.webp *.bmp)"
        )
        if not file_path:
            return

        try:
            from PIL import Image

            img = Image.open(file_path)
            if img.mode in ('RGBA', 'P', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((400, 600))

            file_hash = abs(hash(self.book_data.get('physical_path', '') + str(self.book_data.get('id', 0))))
            cover_filename = f"cover_{file_hash}.jpg"
            covers_dir = os.path.join(os.path.dirname(__file__), 'covers')
            cover_path = os.path.join(covers_dir, cover_filename)

            os.makedirs(covers_dir, exist_ok=True)
            img.save(cover_path, 'JPEG', quality=85)

            self.book_data['cover_path'] = cover_path
            pixmap = QPixmap(cover_path)
            self.cover_label.setPixmap(pixmap.scaled(
                230, 330,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

            if not self.is_edit_mode:
                self.db.update_book(self.book_data['id'], {'cover_path': cover_path})
                self.book_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"更换封面失败: {str(e)}")

    def delete_book(self):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这本书吗？\n（只会删除记录，不会删除文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_book(self.book_data['id']):
                QMessageBox.information(self, "成功", "书籍已删除！")
                self.book_changed.emit()
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "删除失败！")

    def go_prev(self):
        if self.current_index > 0:
            if self.is_edit_mode:
                reply = QMessageBox.question(
                    self, "未保存的修改",
                    "当前处于编辑模式，可能有未保存的修改。\n\n确定要翻页吗？未保存的修改将会丢失。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.current_index -= 1
            self.load_book(self.books_data[self.current_index])

    def go_next(self):
        if self.current_index < len(self.books_data) - 1:
            if self.is_edit_mode:
                reply = QMessageBox.question(
                    self, "未保存的修改",
                    "当前处于编辑模式，可能有未保存的修改。\n\n确定要翻页吗？未保存的修改将会丢失。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.current_index += 1
            self.load_book(self.books_data[self.current_index])

    def load_book(self, book):
        self.book_data = book.copy() if book else {}
        self.original_book = book.copy() if book else {}
        self.setWindowTitle(f"书籍详情 - {self.book_data.get('title', '')}")

        cover_path = self.book_data.get('cover_path')
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            self.cover_label.setPixmap(pixmap.scaled(
                230, 330,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.cover_label.setText("无封面")

        self.title_edit.setText(self.book_data.get('title', ''))
        self.subtitle_edit.setText(self.book_data.get('subtitle', ''))
        self.author_edit.setText(safe_str(self.book_data.get('authors', '')))
        self.publisher_edit.setText(self.book_data.get('publisher', ''))
        self.pubdate_edit.setText(self.book_data.get('pubdate', ''))
        self.isbn_edit.setText(self.book_data.get('isbn', ''))
        
        self.dir_root_combo.clear()
        self.dir_root_combo.addItem("")
        for root in self.category_manager.get_root_categories():
            self.dir_root_combo.addItem(root)
        current_root = self.book_data.get('dir_root', '')
        if current_root:
            index = self.dir_root_combo.findText(current_root)
            if index >= 0:
                self.dir_root_combo.setCurrentIndex(index)
            else:
                self.dir_root_combo.setCurrentText(current_root)
        
        self.dir_sub_combo.clear()
        self.dir_sub_combo.addItem("")
        if current_root:
            for sub in self.category_manager.get_sub_categories(current_root):
                self.dir_sub_combo.addItem(sub)
        current_sub = self.book_data.get('dir_sub', '')
        if current_sub:
            index = self.dir_sub_combo.findText(current_sub)
            if index >= 0:
                self.dir_sub_combo.setCurrentIndex(index)
            else:
                self.dir_sub_combo.setCurrentText(current_sub)
        
        self.adjust_combo_sizes()
        
        self.tags_edit.setText(safe_str(self.book_data.get('tags', '')))
        self.rating_spin.setValue(float(self.book_data.get('rating', 0) or 0))
        self.douban_edit.setText(self.book_data.get('douban_url', ''))
        self.douban_id_edit.setText(self.book_data.get('douban_id', ''))
        self.page_count_edit.setText(safe_str(self.book_data.get('page_count', '')))
        self.summary_edit.setText(self.book_data.get('summary', ''))
        self.notes_edit.setText(self.book_data.get('notes', ''))

        self.set_edit_mode(False)
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.books_data) - 1)

        self.book_changed.emit()

    def restore_cover(self):
        filepath = self.book_data.get('physical_path')
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, "提示", "书籍文件不存在！")
            return

        reply = QMessageBox.question(
            self, "确认还原", 
            "确定要从源文件重新解析封面吗？\n\n这将删除当前封面并从电子书文件中重新提取。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            old_cover_path = self.book_data.get('cover_path')
            
            ebook_parser = EbookParser()
            parsed_data = ebook_parser.parse_book(filepath)
            new_cover_path = parsed_data.get('cover_path')
            
            if new_cover_path and os.path.exists(new_cover_path):
                self.book_data['cover_path'] = new_cover_path
                self.db.update_book(self.book_data['id'], {'cover_path': new_cover_path})
                
                if old_cover_path and old_cover_path != new_cover_path and os.path.exists(old_cover_path):
                    try:
                        os.remove(old_cover_path)
                    except:
                        pass
                
                pixmap = QPixmap(new_cover_path)
                self.cover_label.setPixmap(pixmap.scaled(
                    230, 330,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                
                QMessageBox.information(self, "成功", "封面已从源文件重新解析！")
            else:
                self.cover_label.setText("无封面")
                QMessageBox.information(self, "提示", "源文件中未找到封面图片。")

    def update_cover_to_file(self):
        cover_path = self.book_data.get('cover_path')
        if not cover_path or not os.path.exists(cover_path):
            QMessageBox.warning(self, "提示", "没有可用的封面图片！")
            return

        filepath = self.book_data.get('physical_path')
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, "提示", "书籍文件不存在！")
            return

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in ['.epub', '.pdf']:
            QMessageBox.warning(self, "提示", "仅支持 EPUB 和 PDF 格式！")
            return

        reply = QMessageBox.question(
            self, "确认更新",
            f"确定要将封面更新到原文件吗？\n\n这将修改原始电子书文件，建议先备份！\n\n文件: {os.path.basename(filepath)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            parser = EbookParser()
            if parser.update_cover_to_file(filepath, cover_path):
                QMessageBox.information(self, "成功", "封面已更新到文件！")
            else:
                QMessageBox.warning(self, "错误", "更新封面失败，请查看控制台输出！")

    def update_metadata_to_file(self):
        filepath = self.book_data.get('physical_path')
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, "提示", "书籍文件不存在！")
            return

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in ['.epub', '.pdf']:
            QMessageBox.warning(self, "提示", "仅支持 EPUB 和 PDF 格式！")
            return

        metadata = {}

        title = self.title_edit.text().strip()
        if title:
            metadata['title'] = title

        authors = self.author_edit.text().strip()
        if authors:
            if ',' in authors:
                metadata['authors'] = [a.strip() for a in authors.split(',') if a.strip()]
            else:
                metadata['authors'] = authors

        isbn = self.isbn_edit.text().strip()
        if isbn:
            metadata['isbn'] = isbn

        publisher = self.publisher_edit.text().strip()
        if publisher:
            metadata['publisher'] = publisher

        pubdate = self.pubdate_edit.text().strip()
        if pubdate:
            metadata['pubdate'] = pubdate

        summary = self.summary_edit.toPlainText().strip()
        if summary:
            metadata['summary'] = summary

        tags = self.tags_edit.text().strip()
        if tags:
            if ',' in tags:
                metadata['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
            else:
                metadata['tags'] = tags

        rating = self.rating_spin.value()
        if rating > 0:
            metadata['rating'] = rating

        if metadata:
            meta_list = '\n'.join([f"{k}: {v}" for k, v in metadata.items()])
            reply = QMessageBox.question(
                self, "确认更新",
                f"确定要将以下元数据更新到原文件吗？\n\n这将修改原始电子书文件，建议先备份！\n\n文件: {os.path.basename(filepath)}\n\n将更新的字段:\n{meta_list}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                parser = EbookParser()
                if parser.update_metadata_to_file(filepath, metadata):
                    QMessageBox.information(self, "成功", "元数据已更新到文件！")
                else:
                    QMessageBox.warning(self, "错误", "更新元数据失败，请查看控制台输出！")
        else:
            QMessageBox.information(self, "提示", "没有可更新的元数据字段！")

    def rename_file(self):
        old_path = self.book_data.get('physical_path')
        if not old_path or not os.path.exists(old_path):
            QMessageBox.warning(self, "错误", "文件不存在，无法重命名！")
            return

        title = safe_str(self.book_data.get('title')).strip()
        authors = safe_str(self.book_data.get('authors')).strip()
        ext = safe_str(self.book_data.get('extension')).strip()

        if not ext:
            ext = os.path.splitext(old_path)[1].lstrip('.')

        if not title:
            QMessageBox.warning(self, "错误", "标题为空，无法重命名！")
            return

        new_filename = f"{title}"
        if authors:
            new_filename += f" - {authors}"
        if ext:
            new_filename += f".{ext}"

        new_filename = sanitize_filename(new_filename)
        old_dir = os.path.dirname(old_path)
        new_path = os.path.join(old_dir, new_filename)

        if old_path == new_path:
            QMessageBox.information(self, "提示", "文件名已经是规范格式，无需重命名！")
            return

        reply = QMessageBox.question(
            self, "确认重命名",
            f"将文件重命名为：\n\n{new_filename}\n\n确定吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(new_path):
                    QMessageBox.warning(self, "错误", f"文件已存在：\n{new_path}")
                    return

                os.rename(old_path, new_path)
                self.db.update_book(self.book_data['id'], {'physical_path': new_path})
                self.book_data['physical_path'] = new_path
                QMessageBox.information(self, "成功", "文件重命名成功！")
                self.book_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败：{str(e)}")
