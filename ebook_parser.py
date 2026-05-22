import os
import io
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image


class EbookParser:
    SUPPORTED_EXTENSIONS = {'.epub', '.pdf'}

    def __init__(self, covers_dir: str = "covers"):
        self.covers_dir = covers_dir
        os.makedirs(covers_dir, exist_ok=True)

    def is_supported_file(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse_book(self, filepath: str) -> Dict[str, Any]:
        if not os.path.exists(filepath):
            return {}

        ext = os.path.splitext(filepath)[1].lower()

        book_data = {
            'physical_path': filepath,
            'extension': ext[1:],
            'file_size': os.path.getsize(filepath)
        }

        if ext == '.epub':
            parsed_data = self._parse_epub(filepath)
        elif ext == '.pdf':
            parsed_data = self._parse_pdf(filepath)
        else:
            parsed_data = {}

        book_data.update(parsed_data)

        if not book_data.get('title'):
            book_data['title'] = os.path.splitext(os.path.basename(filepath))[0]

        return book_data

    def _parse_epub(self, filepath: str) -> Dict[str, Any]:
        data = {}
        try:
            book = epub.read_epub(filepath, options={'ignore_ncx': True})

            title = self._get_metadata(book, 'title')
            if title:
                data['title'] = title

            creator = self._get_metadata(book, 'creator')
            if creator:
                data['authors'] = [creator]

            description = self._get_metadata(book, 'description')
            if description:
                data['subtitle'] = description[:200]

            isbn = self._get_metadata(book, 'identifier')
            if isbn and len(isbn) in [10, 13] and isbn.isdigit():
                data['isbn'] = isbn

            subject = self._get_metadata(book, 'subject')
            if subject:
                data['category'] = subject

            publisher = self._get_metadata(book, 'publisher')
            if publisher:
                data['publisher'] = publisher

            date = self._get_metadata(book, 'date')
            if date:
                data['pubdate'] = date

            cover_path = self._extract_epub_cover(filepath, book)
            if cover_path:
                data['cover_path'] = cover_path

        except Exception as e:
            print(f"Error parsing EPUB {filepath}: {e}")

        return data

    def _parse_pdf(self, filepath: str) -> Dict[str, Any]:
        data = {}
        try:
            from pypdf import PdfReader

            reader = PdfReader(filepath)

            if reader.metadata:
                metadata = reader.metadata

                def get_meta(key, default=None):
                    try:
                        if hasattr(metadata, key):
                            value = getattr(metadata, key)
                            if value:
                                return value
                        if key in metadata:
                            value = metadata[key]
                            if value:
                                return value
                    except:
                        pass
                    return default

                title = get_meta('title')
                if title:
                    data['title'] = title

                author = get_meta('author')
                if author:
                    data['authors'] = [author]

                subject = get_meta('subject')
                if subject:
                    data['subtitle'] = subject[:200] if len(subject) > 200 else subject

                publisher = get_meta('publisher')
                if publisher:
                    data['publisher'] = publisher

                data['page_count'] = len(reader.pages)

            cover_path = self._extract_pdf_cover(filepath)
            if cover_path:
                data['cover_path'] = cover_path

        except ImportError:
            print("pypdf 未安装，PDF 元数据解析不可用。安装命令: pip install pypdf")
        except Exception as e:
            print(f"Error parsing PDF {filepath}: {e}")

        return data

    def _extract_pdf_cover(self, filepath: str) -> Optional[str]:
        try:
            from pypdf import PdfReader
            from PIL import Image

            reader = PdfReader(filepath)
            if len(reader.pages) == 0:
                return None

            page = reader.pages[0]
            images = page.images

            if images:
                file_hash = abs(hash(filepath))
                cover_filename = f"cover_{file_hash}.jpg"
                cover_path = os.path.join(self.covers_dir, cover_filename)

                if not os.path.exists(cover_path):
                    image_data = images[0].data
                    img = Image.open(io.BytesIO(image_data))

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
                    img.save(cover_path, 'JPEG', quality=85)
                    print(f"PDF 封面已保存: {cover_path}")

                return cover_path
        except ImportError:
            pass
        except Exception as e:
            print(f"提取 PDF 封面失败: {e}")

        return None

    def _get_metadata(self, book, name: str) -> Optional[str]:
        try:
            meta = book.get_metadata('DC', name)
            if meta and len(meta) > 0:
                value = meta[0][0]
                if value and isinstance(value, str):
                    value = value.strip()
                    if value and value.lower() not in ['none', 'null', 'nan']:
                        return value
        except:
            pass
        return None

    def _extract_epub_cover(self, filepath: str, book: epub.EpubBook) -> Optional[str]:
        try:
            cover_item = None
            cover_id = None

            print(f"\n=== 开始提取封面: {os.path.basename(filepath)} ===")

            try:
                for item in book.get_metadata('OPF', 'cover'):
                    print(f"  OPF cover 元数据: {item}")
                    cover_id = None
                    if isinstance(item, tuple) and len(item) > 1:
                        for k, v in item[1].items():
                            if k.endswith('content'):
                                cover_id = v
                                print(f"  找到 cover_id: {cover_id}")
                                break
                    if cover_id:
                        break
            except Exception as e:
                print(f"  从OPF元数据获取cover_id失败: {e}")

            if cover_id:
                for item in book.get_items():
                    try:
                        if item.get_id() == cover_id:
                            cover_item = item
                            print(f"  ✅ 通过cover_id找到封面: {item.get_name()}")
                            break
                    except:
                        pass

            if not cover_item:
                for item in book.get_items():
                    try:
                        item_type = item.get_type() if hasattr(item, 'get_type') else None
                        if item_type == 10:
                            cover_item = item
                            print(f"  ✅ 通过ITEM_COVER(10)找到封面: {item.get_name()}")
                            break
                    except:
                        pass

            if not cover_item:
                for item in book.get_items():
                    try:
                        item_type = item.get_type() if hasattr(item, 'get_type') else None
                        if item_type == 8:
                            fname = item.get_name().lower()
                            if 'cover' in fname or 'jacket' in fname:
                                cover_item = item
                                print(f"  ✅ 通过ITEM_IMAGE(8)+文件名找到封面: {item.get_name()}")
                                break
                    except:
                        pass

            if not cover_item:
                for item in book.get_items():
                    try:
                        fname = item.get_name().lower()
                        if ('cover' in fname or 'jacket' in fname) and fname.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                            cover_item = item
                            print(f"  ✅ 通过文件名匹配找到封面: {item.get_name()}")
                            break
                    except:
                        pass

            if not cover_item:
                try:
                    image_items = []
                    for item in book.get_items():
                        try:
                            item_type = item.get_type() if hasattr(item, 'get_type') else None
                            if item_type == 8 or item.get_name().lower().endswith(('.jpg', '.jpeg', '.png')):
                                image_items.append(item)
                        except:
                            pass
                    if image_items:
                        print(f"  找到 {len(image_items)} 个图片文件，按大小排序...")
                        valid_images = []
                        for img_item in image_items:
                            try:
                                content = img_item.get_content()
                                if content:
                                    valid_images.append((len(content), img_item))
                            except:
                                pass
                        if valid_images:
                            valid_images.sort(reverse=True, key=lambda x: x[0])
                            cover_item = valid_images[0][1]
                            print(f"  ✅ 选择最大的图片作为封面: {cover_item.get_name()} ({valid_images[0][0]} bytes)")
                except Exception as e:
                    print(f"  按大小选择图片失败: {e}")

            if cover_item:
                file_hash = abs(hash(filepath))
                cover_filename = f"cover_{file_hash}.jpg"
                cover_path = os.path.join(self.covers_dir, cover_filename)

                if not os.path.exists(cover_path):
                    try:
                        img_data = cover_item.get_content()
                        if img_data and len(img_data) > 0:
                            try:
                                img = Image.open(io.BytesIO(img_data))
                                print(f"  图片模式: {img.mode}, 尺寸: {img.size}")
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
                                img.save(cover_path, 'JPEG', quality=85)
                                print(f"  ✅ 封面已保存: {cover_path}")
                            except Exception as img_error:
                                print(f"❌ 图片处理错误: {img_error}")
                                return None
                    except Exception as content_error:
                        print(f"❌ 获取图片内容错误: {content_error}")
                        return None
                else:
                    print(f"  封面已存在，跳过: {cover_path}")

                return cover_path
            else:
                print("❌ 未找到任何封面图片!")
        except Exception as e:
            print(f"❌ 提取封面异常: {e}")

        return None

    def scan_directory(self, dirpath: str) -> list:
        books = []
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                filepath = os.path.join(root, file)
                if self.is_supported_file(filepath):
                    books.append(filepath)
        return books

    def format_file_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return ''
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
