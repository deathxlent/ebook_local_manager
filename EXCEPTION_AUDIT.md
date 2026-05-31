# 异常捕获问题记录

审查所有源码，记录正常操作流程中可能发生但未被正确捕获或处理的异常。

---

## 1. [高] 详情窗口 `save_changes` — 元数据更新失败未提示用户

**文件**：`detail_window.py:559-571`

**场景**：用户编辑书籍信息后点击保存，保存到数据库成功，但后续 `ebook_parser.update_metadata_to_file()` 写入文件失败时（如文件被占用、权限不足），仅静默失败，用户看不到任何错误提示。

**当前代码**：
```python
if self.db.update_book(self.book_data['id'], update_data):
    ...
    ebook_parser = EbookParser()
    file_metadata = {...}
    ebook_parser.update_metadata_to_file(self.book_data['physical_path'], file_metadata)
    
    self.set_edit_mode(False)
    self.book_changed.emit()
    QMessageBox.information(self, "成功", "修改已保存！")
```

**问题**：`update_metadata_to_file` 的返回值被忽略，文件写入失败时仍显示「修改已保存」。

**建议**：检查返回值，若文件写入失败应提示用户「数据库已保存，但元数据写入文件失败」。

---

## 2. [高] 详情窗口 `save_changes` — `physical_path` 为空时元数据更新崩溃

**文件**：`detail_window.py:571`

**场景**：如果书籍的 `physical_path` 为空（理论上不太可能但数据库无此约束），调用 `ebook_parser.update_metadata_to_file(None, metadata)` 会在 `EbookParser` 内部尝试 `os.path.splitext(filepath)` 导致 `TypeError`。

**当前代码**：
```python
ebook_parser.update_metadata_to_file(self.book_data['physical_path'], file_metadata)
```

**建议**：保存前检查 `physical_path` 是否有效，或在外层加 try-except。

---

## 3. [高] 详情窗口 `restore_cover` — 封面还原时旧封面未清理

**文件**：`detail_window.py:816-836`

**场景**：用户点击「还原封面」时，从源文件重新解析封面，但旧封面文件没有被删除。由于封面文件名使用 `hash(physical_path + id)` 生成，重新解析会生成相同文件名，所以旧文件会被覆盖。但如果 `EbookParser` 使用了不同的 hash 算法或路径变化，可能导致旧封面残留。

**当前代码**：仅声明 `old_cover_path = self.book_data.get('cover_path')` 但未使用。

**建议**：还原成功后删除旧封面文件（如果存在且与新的不同）。

---

## 4. [中] 豆瓣解析 — 解析超时阻塞 UI

**文件**：`detail_window.py:598`

**场景**：详情页的豆瓣解析是同步调用（`self.douban_parser.search_book()`），虽然调用了 `QApplication.processEvents()`，但如果网络请求超时（15 秒），UI 仍然会卡住。

**当前代码**：
```python
result = self.douban_parser.search_book(title, author)
```

**建议**：改为异步调用（类似主窗口的 `add_to_queue` 机制），或使用 QThread 避免阻塞 UI。

---

## 5. [中] 数据库 `update_book` — 异常未捕获

**文件**：`database.py:138-168`

**场景**：`update_book` 方法中如果 `book_data` 的 key 包含 SQL 保留字或特殊字符，`f'{k} = ?'` 拼接可能导致 SQL 语法错误。此外 `get_connection()` 可能抛出 `sqlite3.OperationalError`（如数据库文件被锁），但方法内没有 try-except。

**当前代码**：
```python
def update_book(self, book_id: int, book_data: Dict[str, Any]) -> bool:
    conn = self.get_connection()
    cursor = conn.cursor()
    ...
```

**建议**：添加 try-except-finally 确保 `conn.close()` 总被调用，捕获数据库异常并返回 False。

---

## 6. [中] 数据库 `add_book` — 异常时连接未关闭

**文件**：`database.py:110-136`

**场景**：`add_book` 方法在 `IntegrityError` 时返回 -1 并关闭连接，但如果在 `cursor.execute` 之前发生其他异常（如 `get_connection()` 失败），连接不会被关闭。其他 `get_connection()` 后的操作也有类似风险。

**当前代码**：
```python
try:
    cursor.execute(...)
    book_id = cursor.lastrowid
    conn.commit()
    return book_id
except sqlite3.IntegrityError:
    return -1
finally:
    conn.close()
```

**建议**：确保所有数据库方法都使用 try-except-finally，且 `conn.close()` 始终执行。更优方案是使用上下文管理器（`with` 语句）。

---

## 7. [中] 导入窗口 — 导入过程中关闭窗口

**文件**：`import_window.py:196`

**场景**：导入线程运行时，如果用户点击「取消」按钮，窗口直接关闭（`self.close()`），但 `ImportThread` 仍在后台运行。虽然线程设置了 `daemon=True` 不会阻止程序退出，但线程完成时会发出信号尝试更新已关闭的控件，可能导致异常。

**当前代码**：
```python
self.cancel_btn.clicked.connect(self.close)
```

**建议**：导入进行中禁用取消按钮，或改为隐藏窗口、在线程结束后再关闭。

---

## 8. [中] 分类配置 — 保存按钮直接调用 `accept()`

**文件**：`settings_window.py:349`

**场景**：`CategorySettingsWindow` 的保存按钮直接调用 `self.accept()`，此时分类管理器中的 `categories` 已通过 `add_category`/`remove_category`/`parse_quick_config` 等方法实时写入了 `config.json`。但如果用户修改了右侧快速配置文本框内容后直接点保存，而未点「📥 导入配置」，文本框中的修改不会被应用。

**当前代码**：
```python
save_btn.clicked.connect(self.accept)
```

**建议**：保存时应检查右侧文本框内容是否与当前分类树一致，如不一致提示用户是否导入。

---

## 9. [低] 豆瓣解析 `_calc_url` — URL 解析异常

**文件**：`douban_parser.py:136-145`

**场景**：`_calc_url` 方法中，如果 `href` 的 query 参数格式异常（如 `key=value` 中 value 包含 `=`），`item.split('=')[1]` 只取到第一个 `=` 后的部分。更严重的是，如果 query 为空或格式异常，`query.split('&')` 和后续处理可能抛出 `IndexError`。

**当前代码**：
```python
params = {item.split('=')[0]: item.split('=')[1] for item in query.split('&')}
```

**建议**：使用 `urllib.parse.parse_qs` 解析 query string，更健壮。

---

## 10. [低] 批量删除 — 删除后选中状态未清理

**文件**：`main_window.py:716-737`

**场景**：批量删除后调用 `self.refresh_books()` 刷新列表，但 `self.selected_book_ids` 中仍保留已删除书籍的 ID。虽然刷新后这些 ID 不会再匹配到任何行，但 `selected_book_ids` 集合会持续增长（内存泄漏），且 `update_delete_button_state()` 中 `len(self.selected_book_ids)` 不为 0，导致批量操作按钮仍显示为可用。

**当前代码**：
```python
if reply == QMessageBox.StandardButton.Yes:
    deleted_count = 0
    for row in sorted(checked_rows, reverse=True):
        ...
    QMessageBox.information(self, "成功", f"已成功删除 {deleted_count} 本书！")
    self.refresh_books()
```

**建议**：删除成功后清空 `self.selected_book_ids`，或在 `refresh_books` 中过滤掉无效 ID。

---

## 11. [低] 详情页翻页 — 修改未保存时翻页数据丢失

**文件**：`detail_window.py:729-737`

**场景**：用户在编辑模式下修改了书籍信息，然后点击「上一本」或「下一本」翻页，当前修改会被丢弃且无任何提示。`load_book` 直接用新数据覆盖所有字段。

**当前代码**：
```python
def go_prev(self):
    if self.current_index > 0:
        self.current_index -= 1
        self.load_book(self.books_data[self.current_index])
```

**建议**：翻页前检查是否处于编辑模式且有未保存的修改，提示用户是否保存。

---

## 12. [低] 导出 CSV — 空列表导出

**文件**：`main_window.py:807-868`

**场景**：如果当前书籍列表为空（搜索无结果），点击「导出CSV」会导出一个只含表头的空 CSV 文件，无任何提示。虽然不是错误，但用户体验不佳。

**建议**：导出前检查列表是否为空，空时提示用户。

---

## 13. [低] 窗口标题版本号不一致

**文件**：`main_window.py:42`

**场景**：主窗口标题硬编码为「电子书管理器 v2.1」，但 README 曾标注为 v3.1，关于对话框显示 v2.0。版本号混乱。

**当前代码**：
```python
self.setWindowTitle("电子书管理器 v2.1")
```

**建议**：统一版本号，建议使用常量或配置文件管理。
