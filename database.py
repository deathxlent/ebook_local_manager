import sqlite3
import os
from typing import List, Dict, Optional, Any


class Database:
    def __init__(self, db_path: str = "ebook_manager.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                subtitle TEXT,
                authors TEXT,
                category TEXT,
                file_size INTEGER,
                physical_path TEXT UNIQUE,
                extension TEXT,
                isbn TEXT,
                rating REAL,
                douban_url TEXT,
                douban_id TEXT,
                publisher TEXT,
                pubdate TEXT,
                summary TEXT,
                notes TEXT,
                cover_path TEXT,
                cover_url TEXT,
                series TEXT,
                series_index REAL DEFAULT 0,
                languages TEXT,
                tags TEXT,
                page_count INTEGER,
                parse_status TEXT DEFAULT 'pending',
                last_parsed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self._migrate_database(conn)
        self._cleanup_duplicates(conn)

        conn.commit()
        conn.close()

    def _migrate_database(self, conn):
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(books)")
        columns = [col[1] for col in cursor.fetchall()]

        new_columns = {
            'subtitle': 'TEXT',
            'authors': 'TEXT',
            'douban_id': 'TEXT',
            'publisher': 'TEXT',
            'pubdate': 'TEXT',
            'summary': 'TEXT',
            'cover_url': 'TEXT',
            'series': 'TEXT',
            'series_index': 'REAL DEFAULT 0',
            'languages': 'TEXT',
            'tags': 'TEXT',
            'page_count': 'INTEGER',
            'parse_status': "TEXT DEFAULT 'pending'",
            'last_parsed_at': 'TIMESTAMP'
        }

        for col_name, col_def in new_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_def}")
                    print(f"添加字段: {col_name}")
                except Exception as e:
                    print(f"添加字段 {col_name} 失败: {e}")

    def _cleanup_duplicates(self, conn):
        cursor = conn.cursor()
        try:
            cursor.execute('''
                DELETE FROM books 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM books 
                    GROUP BY physical_path
                )
            ''')
            deleted = cursor.rowcount
            if deleted > 0:
                print(f"清理了 {deleted} 条重复的书籍记录")
        except Exception as e:
            print(f"清理重复数据失败: {e}")

    def add_book(self, book_data: Dict[str, Any]) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        if 'authors' in book_data and isinstance(book_data['authors'], list):
            book_data['authors'] = ', '.join(book_data['authors'])
        if 'tags' in book_data and isinstance(book_data['tags'], list):
            book_data['tags'] = ', '.join(book_data['tags'])
        if 'languages' in book_data and isinstance(book_data['languages'], list):
            book_data['languages'] = ', '.join(book_data['languages'])

        columns = ', '.join(book_data.keys())
        placeholders = ', '.join(['?' for _ in book_data])
        values = list(book_data.values())

        try:
            cursor.execute(
                f'INSERT INTO books ({columns}) VALUES ({placeholders})',
                values
            )
            book_id = cursor.lastrowid
            conn.commit()
            return book_id
        except sqlite3.IntegrityError:
            return -1
        finally:
            conn.close()

    def update_book(self, book_id: int, book_data: Dict[str, Any]) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        book_data['updated_at'] = 'CURRENT_TIMESTAMP'

        if 'authors' in book_data and isinstance(book_data['authors'], list):
            book_data['authors'] = ', '.join(book_data['authors'])
        if 'tags' in book_data and isinstance(book_data['tags'], list):
            book_data['tags'] = ', '.join(book_data['tags'])
        if 'languages' in book_data and isinstance(book_data['languages'], list):
            book_data['languages'] = ', '.join(book_data['languages'])

        set_clause = ', '.join([f'{k} = ?' for k in book_data.keys()])
        values = list(book_data.values())
        values.append(book_id)

        cursor.execute(
            f'UPDATE books SET {set_clause} WHERE id = ?',
            values
        )

        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_book(self, book_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            book = dict(row)
            if book.get('authors'):
                book['authors'] = [a.strip() for a in book['authors'].split(',')]
            if book.get('tags'):
                book['tags'] = [t.strip() for t in book['tags'].split(',')]
            if book.get('languages'):
                book['languages'] = [l.strip() for l in book['languages'].split(',')]
            return book
        return None

    def get_all_books(self, sort_by: str = "title", order: str = "ASC", search: str = "") -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM books'
        params = []

        if search:
            search_pattern = f'%{search}%'
            query += ''' WHERE title LIKE ? OR subtitle LIKE ? OR authors LIKE ? 
                          OR category LIKE ? OR physical_path LIKE ? OR extension LIKE ? OR isbn LIKE ? OR tags LIKE ?'''
            params = [search_pattern] * 8

        valid_columns = ["title", "subtitle", "authors", "category", "file_size", 
                        "physical_path", "extension", "isbn", "rating", "pubdate", "publisher", "id"]
        if sort_by in valid_columns:
            query += f' ORDER BY {sort_by} {order}'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        books = []
        for row in rows:
            book = dict(row)
            if book.get('authors'):
                book['authors'] = [a.strip() for a in book['authors'].split(',')]
            if book.get('tags'):
                book['tags'] = [t.strip() for t in book['tags'].split(',')]
            if book.get('languages'):
                book['languages'] = [l.strip() for l in book['languages'].split(',')]
            books.append(book)
        return books

    def book_exists(self, physical_path: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM books WHERE physical_path = ?', (physical_path,))
        exists = cursor.fetchone() is not None
        conn.close()

        return exists
