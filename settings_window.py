import os
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QTextEdit,
                             QWidget, QListWidget, QListWidgetItem, QInputDialog,
                             QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt


class CategoryManager:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'config.json')
        self.categories = {}
        self.load_categories()

    def load_categories(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.categories = config.get('categories', {})
        except Exception as e:
            print(f"加载分类配置失败: {e}")
            self.categories = {}

    def save_categories(self):
        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['categories'] = self.categories
            
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存分类配置失败: {e}")
            return False

    def add_category(self, root, sub=None):
        if root not in self.categories:
            self.categories[root] = []
        if sub and sub not in self.categories[root]:
            self.categories[root].append(sub)
        return self.save_categories()

    def remove_category(self, root, sub=None):
        if sub is None:
            if root in self.categories:
                del self.categories[root]
        else:
            if root in self.categories and sub in self.categories[root]:
                self.categories[root].remove(sub)
        return self.save_categories()

    def get_root_categories(self):
        return list(self.categories.keys())

    def get_sub_categories(self, root):
        return self.categories.get(root, [])

    def parse_quick_config(self, text):
        lines = text.strip().split('\n')
        new_categories = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if '/' in line:
                parts = line.split('/', 1)
                root = parts[0].strip()
                sub = parts[1].strip()
                if root not in new_categories:
                    new_categories[root] = []
                if sub and sub not in new_categories[root]:
                    new_categories[root].append(sub)
            else:
                root = line.strip()
                if root not in new_categories:
                    new_categories[root] = []
        
        self.categories = new_categories
        return self.save_categories()

    def export_text(self):
        lines = []
        for root, subs in self.categories.items():
            if not subs:
                lines.append(root)
            else:
                for sub in subs:
                    lines.append(f"{root}/{sub}")
        return '\n'.join(lines)


class DoubanSettingsWindow(QDialog):
    def __init__(self, parent=None, current_cookie: str = ""):
        super().__init__(parent)
        self.cookie = current_cookie
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("豆瓣配置")
        self.setMinimumSize(600, 400)
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
        btn_layout.addStretch()

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


class CategorySettingsWindow(QDialog):
    def __init__(self, parent=None, category_manager=None):
        super().__init__(parent)
        self.category_manager = category_manager or CategoryManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("分类配置")
        self.setMinimumSize(700, 550)
        self.setModal(True)

        layout = QVBoxLayout(self)

        desc_label = QLabel(
            "配置书籍的分类和子分类（最多支持两层级）。\n"
            "在修改书籍信息时可以级联选择这些分类。\n\n"
            "快速配置说明：每行一个分类，格式为「分类」或「分类/子分类」，例如：\n"
            "推理\n"
            "推理/东野圭吾\n"
            "科幻\n"
            "科幻/大刘\n"
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

        layout.addSpacing(10)

        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_label = QLabel("当前分类配置:")
        left_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(left_label)

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["分类 / 子分类"])
        self.category_tree.setColumnCount(1)
        self.category_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.refresh_category_tree()
        left_layout.addWidget(self.category_tree, 1)

        tree_btn_layout = QHBoxLayout()
        add_root_btn = QPushButton("+ 分类")
        add_root_btn.clicked.connect(self.add_root_category)
        tree_btn_layout.addWidget(add_root_btn)

        add_sub_btn = QPushButton("+ 子分类")
        add_sub_btn.clicked.connect(self.add_sub_category)
        tree_btn_layout.addWidget(add_sub_btn)

        remove_btn = QPushButton("- 删除")
        remove_btn.clicked.connect(self.remove_selected_category)
        tree_btn_layout.addWidget(remove_btn)

        left_layout.addLayout(tree_btn_layout)
        content_layout.addLayout(left_layout, 1)

        right_layout = QVBoxLayout()
        right_label = QLabel("快速配置（粘贴纯文本）:")
        right_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(right_label)

        self.quick_edit = QTextEdit()
        self.quick_edit.setPlaceholderText(
            "推理\n"
            "推理/东野圭吾\n"
            "科幻\n"
            "科幻/大刘\n"
            "科幻/斯卡尔奇"
        )
        self.quick_edit.setPlainText(self.category_manager.export_text())
        self.quick_edit.setStyleSheet("""
            QTextEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        right_layout.addWidget(self.quick_edit, 1)

        quick_btn_layout = QHBoxLayout()
        export_btn = QPushButton("📤 导出当前")
        export_btn.clicked.connect(self.export_categories)
        quick_btn_layout.addWidget(export_btn)

        import_btn = QPushButton("📥 导入配置")
        import_btn.clicked.connect(self.import_quick_config)
        quick_btn_layout.addWidget(import_btn)

        right_layout.addLayout(quick_btn_layout)
        content_layout.addLayout(right_layout, 1)

        layout.addLayout(content_layout, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

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
        save_btn.clicked.connect(self.save_and_close)
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

    def refresh_category_tree(self):
        self.category_tree.clear()
        for root, subs in self.category_manager.categories.items():
            root_item = QTreeWidgetItem([f"📂 {root}"])
            root_item.setData(0, Qt.ItemDataRole.UserRole, ('root', root))
            self.category_tree.addTopLevelItem(root_item)
            for sub in subs:
                sub_item = QTreeWidgetItem([f"📄 {sub}"])
                sub_item.setData(0, Qt.ItemDataRole.UserRole, ('sub', root, sub))
                root_item.addChild(sub_item)
        self.category_tree.expandAll()

    def add_root_category(self):
        text, ok = QInputDialog.getText(self, "添加分类", "请输入分类名称:")
        if ok and text.strip():
            self.category_manager.add_category(text.strip())
            self.refresh_category_tree()
            self.quick_edit.setPlainText(self.category_manager.export_text())

    def add_sub_category(self):
        current_item = self.category_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个分类！")
            return

        data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != 'root':
            QMessageBox.warning(self, "提示", "请选择一个分类（而非子分类）！")
            return

        root = data[1]
        text, ok = QInputDialog.getText(self, "添加子分类", f"请输入「{root}」的子分类名称:")
        if ok and text.strip():
            self.category_manager.add_category(root, text.strip())
            self.refresh_category_tree()
            self.quick_edit.setPlainText(self.category_manager.export_text())

    def remove_selected_category(self):
        current_item = self.category_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要删除的项目！")
            return

        data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data[0] == 'root':
            root = data[1]
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除分类「{root}」及其所有子分类吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.category_manager.remove_category(root)
                self.refresh_category_tree()
                self.quick_edit.setPlainText(self.category_manager.export_text())
        elif data[0] == 'sub':
            root, sub = data[1], data[2]
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除子分类「{root}/{sub}」吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.category_manager.remove_category(root, sub)
                self.refresh_category_tree()
                self.quick_edit.setPlainText(self.category_manager.export_text())

    def export_categories(self):
        text = self.category_manager.export_text()
        self.quick_edit.setPlainText(text)

    def import_quick_config(self):
        text = self.quick_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先粘贴配置文本！")
            return

        reply = QMessageBox.question(
            self, "确认导入",
            "导入将覆盖当前所有分类配置，确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.category_manager.parse_quick_config(text):
                self.refresh_category_tree()
                self.quick_edit.setPlainText(self.category_manager.export_text())
                QMessageBox.information(self, "成功", "分类配置导入成功！")
            else:
                QMessageBox.warning(self, "错误", "导入失败！")

    def save_and_close(self):
        quick_edit_text = self.quick_edit.toPlainText().strip()
        current_text = self.category_manager.export_text().strip()
        
        if quick_edit_text != current_text:
            reply = QMessageBox.question(
                self, "检测到未导入的修改",
                "快速配置区的内容已被修改但未导入。\n\n是否在保存前先导入快速配置？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.category_manager.parse_quick_config(quick_edit_text):
                    self.refresh_category_tree()
                    self.quick_edit.setPlainText(self.category_manager.export_text())
                    QMessageBox.information(self, "成功", "分类配置导入成功！")
                else:
                    QMessageBox.warning(self, "错误", "导入失败，请检查配置格式！")
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        self.accept()
