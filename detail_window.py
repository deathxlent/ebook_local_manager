import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QTextEdit, QPushButton, QFormLayout, QMessageBox,
                             QDoubleSpinBox, QScrollArea, QWidget, QFrame, QApplication)
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl

from utils import safe_str


class DetailWindow(QDialog):
    def __init__(self, db, book, douban_parser, parent=None):
        super().__init__(parent)
        self.db = db
        self.book_data = book.copy() if book else {}
        self.original_book = book.copy() if book else {}
        self.douban_parser = douban_parser
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

        self.category_edit = QLineEdit()
        self.category_edit.setText(self.book_data.get('category', ''))
        form_layout.addRow("分类:", self.category_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setText(safe_str(self.book_data.get('tags', '')))
        self.tags_edit.setPlaceholderText("多个标签用逗号分隔")
        form_layout.addRow("标签:", self.tags_edit)

        self.series_edit = QLineEdit()
        self.series_edit.setText(self.book_data.get('series', ''))
        form_layout.addRow("丛书:", self.series_edit)

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

    def set_edit_mode(self, edit_mode):
        self.is_edit_mode = edit_mode

        edits = [
            self.title_edit, self.subtitle_edit, self.author_edit,
            self.publisher_edit, self.pubdate_edit, self.isbn_edit,
            self.category_edit, self.tags_edit, self.series_edit,
            self.rating_spin, self.douban_edit, self.page_count_edit,
            self.summary_edit, self.notes_edit
        ]

        for edit in edits:
            edit.setReadOnly(not edit_mode)
            if hasattr(edit, 'setButtonSymbols'):
                continue

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
        update_data = {
            'title': self.title_edit.text(),
            'subtitle': self.subtitle_edit.text(),
            'authors': self.author_edit.text(),
            'publisher': self.publisher_edit.text(),
            'pubdate': self.pubdate_edit.text(),
            'isbn': self.isbn_edit.text(),
            'category': self.category_edit.text(),
            'tags': self.tags_edit.text(),
            'series': self.series_edit.text(),
            'rating': self.rating_spin.value(),
            'douban_url': self.douban_edit.text(),
            'summary': self.summary_edit.toPlainText(),
            'notes': self.notes_edit.toPlainText()
        }

        try:
            page_count = int(self.page_count_edit.text())
            update_data['page_count'] = page_count
        except:
            pass

        if self.db.update_book(self.book_data['id'], update_data):
            self.book_data.update(update_data)
            self.set_edit_mode(False)
            QMessageBox.information(self, "成功", "修改已保存！")
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "保存失败！")

    def parse_from_douban(self):
        if not self.douban_parser.has_cookie():
            QMessageBox.warning(self, "提示", "请先在设置中配置豆瓣 Cookie！")
            if self.parent():
                self.parent().open_settings_window()
            return

        title = self.title_edit.text()
        author = self.author_edit.text()

        if not title:
            QMessageBox.warning(self, "提示", "请先填写书名！")
            return

        reply = QMessageBox.question(
            self, "确认解析",
            f"确定要从豆瓣解析以下书籍信息吗？\n\n书名: {title}\n作者: {author}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
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
                if result.get('series'):
                    self.series_edit.setText(result['series'])

                if result.get('cover_url'):
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

                QMessageBox.information(self, "成功", "豆瓣信息解析完成！\n请检查并保存修改。")
            else:
                error_msg = result.get('error', '解析失败，请检查网络或Cookie') if result else '解析失败'
                QMessageBox.warning(self, "错误", f"解析失败: {error_msg}")

            self.parse_btn.setEnabled(True)
            self.parse_btn.setText("🔍 从豆瓣解析")

    def open_book(self):
        filepath = self.book_data.get('physical_path')
        if filepath and os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(self, "错误", "文件不存在！")

    def delete_book(self):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这本书吗？\n（只会删除记录，不会删除文件）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_book(self.book_data['id']):
                QMessageBox.information(self, "成功", "书籍已删除！")
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "删除失败！")
