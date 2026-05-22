from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QTextEdit)


class SettingsWindow(QDialog):
    def __init__(self, parent=None, current_cookie: str = ""):
        super().__init__(parent)
        self.cookie = current_cookie
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("豆瓣配置")
        self.setMinimumSize(600, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)

        desc_label = QLabel(
            "请配置豆瓣 Cookie 以使用豆瓣信息解析功能。\n\n"
            "获取 Cookie 方法:\n"
            "1. 在浏览器中登录豆瓣: https://www.douban.com\n"
            "2. 按 F12 打开开发者工具\n"
            "3. 切换到 Network（网络）标签\n"
            "4. 刷新页面，点击任意请求\n"
            "5. 在请求头中复制完整的 Cookie 值\n"
        )
        desc_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 8px;
                color: #666;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(15)

        cookie_label = QLabel("豆瓣 Cookie:")
        cookie_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(cookie_label)

        self.cookie_edit = QTextEdit()
        self.cookie_edit.setPlaceholderText("在这里粘贴完整的 Cookie 值...")
        self.cookie_edit.setText(self.cookie)
        self.cookie_edit.setMaximumHeight(150)
        self.cookie_edit.setStyleSheet("""
            QTextEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.cookie_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()

        save_btn = QPushButton("💾 保存")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(120)
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #999;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def save_settings(self):
        cookie = self.cookie_edit.toPlainText().strip()

        if not cookie:
            reply = QMessageBox.question(
                self, "确认",
                "Cookie 为空，确定要保存吗？\n（空 Cookie 可能导致豆瓣解析功能不可用）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.cookie = cookie
        self.accept()

    def get_cookie(self) -> str:
        return self.cookie
