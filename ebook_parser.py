import os
import io
import re
import tempfile
import shutil
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

            creators = self._get_all_metadata(book, 'creator')
            if creators:
                data['authors'] = creators

            description = self._get_metadata(book, 'description')
            if description:
                clean_desc = re.sub(r'<[^>]+>', '', description)
                clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                data['summary'] = clean_desc[:2000]

            isbn = self._get_isbn_from_epub(book)
            if isbn:
                data['isbn'] = isbn

            subjects = self._get_all_metadata(book, 'subject')
            if subjects:
                data['category'] = subjects[0]
                data['tags'] = subjects

            publisher = self._get_metadata(book, 'publisher')
            if publisher:
                data['publisher'] = publisher

            date = self._get_metadata(book, 'date')
            if date:
                data['pubdate'] = date

            try:
                page_count = len(book.spine)
                if page_count > 0:
                    data['page_count'] = page_count
            except:
                pass

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

                def get_meta(*keys):
                    for key in keys:
                        try:
                            if key.startswith('/'):
                                if key in metadata:
                                    value = metadata[key]
                                    if value:
                                        return value
                            else:
                                if hasattr(metadata, key):
                                    value = getattr(metadata, key)
                                    if value:
                                        return value
                                pdf_key = '/' + key.capitalize()
                                if pdf_key in metadata:
                                    value = metadata[pdf_key]
                                    if value:
                                        return value
                        except:
                            pass
                    return None

                title = get_meta('title')
                if title:
                    data['title'] = title

                author = get_meta('author')
                if author:
                    data['authors'] = [author]

                subject = get_meta('subject')
                if subject:
                    data['summary'] = subject[:2000] if len(subject) > 2000 else subject

                publisher = get_meta('publisher', 'Publisher')
                if publisher:
                    data['publisher'] = publisher

                isbn = get_meta('/ISBN', 'isbn', 'ISBN', 'Isbn')
                if isbn:
                    isbn_clean = str(isbn).replace('-', '').replace(' ', '')
                    if isbn_clean.isdigit() and len(isbn_clean) in [10, 13]:
                        data['isbn'] = str(isbn)

                keywords = get_meta('keywords')
                if keywords:
                    kw_list = [k.strip() for k in str(keywords).split(',') if k.strip()]
                    if kw_list:
                        data['tags'] = kw_list
                    if 'isbn' not in data:
                        for kw in kw_list:
                            kw_clean = kw.replace('-', '').replace(' ', '')
                            if kw_clean.isdigit() and len(kw_clean) in [10, 13]:
                                data['isbn'] = kw_clean
                                break

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

    def _get_all_metadata(self, book, name: str) -> list:
        try:
            meta = book.get_metadata('DC', name)
            if meta:
                values = []
                for item in meta:
                    value = item[0]
                    if value and isinstance(value, str):
                        value = value.strip()
                        if value and value.lower() not in ['none', 'null', 'nan']:
                            values.append(value)
                return values
        except:
            pass
        return []

    def _get_isbn_from_epub(self, book) -> Optional[str]:
        try:
            identifiers = book.get_metadata('DC', 'identifier')
            for value, attrs in identifiers:
                if attrs and isinstance(attrs, dict) and attrs.get('id') == 'isbn':
                    if value and isinstance(value, str):
                        value_clean = value.replace('-', '').replace(' ', '')
                        if value_clean.isdigit() and len(value_clean) in [10, 13]:
                            return value
                elif value and isinstance(value, str):
                    value_clean = value.replace('-', '').replace(' ', '')
                    if value_clean.isdigit() and len(value_clean) in [10, 13]:
                        return value
        except:
            pass
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

    def _write_epub_safe(self, epub_path: str, book) -> bool:
        try:
            tmp_dir = os.path.dirname(epub_path)
            base_name = os.path.basename(epub_path)
            tmp_path = os.path.join(tmp_dir, f".tmp_{base_name}")

            def fix_toc_uid(items, counter=0):
                for item in items:
                    if isinstance(item, tuple):
                        counter = fix_toc_uid(item[1], counter)
                    elif hasattr(item, 'uid') and item.uid is None:
                        item.uid = f'navpoint_{counter}'
                        counter += 1
                return counter

            fix_toc_uid(book.toc)

            epub.write_epub(tmp_path, book)

            if os.path.exists(epub_path):
                backup_path = epub_path + '.bak'
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(epub_path, backup_path)

            os.rename(tmp_path, epub_path)

            backup_path = epub_path + '.bak'
            if os.path.exists(backup_path):
                os.remove(backup_path)

            print(f"EPUB 写入成功: {epub_path}")
            return True
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            print(f"EPUB 写入失败: {e}")
            import traceback
            traceback.print_exc()
            return False

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

    def update_cover_to_file(self, filepath: str, cover_image_path: str) -> bool:
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            return False
        if not os.path.exists(cover_image_path):
            print(f"封面图片不存在: {cover_image_path}")
            return False

        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == '.epub':
                return self._update_epub_cover(filepath, cover_image_path)
            elif ext == '.pdf':
                return self._update_pdf_cover(filepath, cover_image_path)
            else:
                print(f"不支持的文件格式: {ext}")
                return False
        except Exception as e:
            print(f"更新封面失败: {e}")
            return False

    def _update_epub_cover(self, epub_path: str, cover_image_path: str) -> bool:
        try:
            book = epub.read_epub(epub_path, options={'ignore_ncx': True})

            with open(cover_image_path, 'rb') as f:
                cover_data = f.read()

            img = Image.open(cover_image_path)
            ext = img.format.lower() if img.format else 'jpeg'
            if ext not in ['jpeg', 'jpg', 'png']:
                ext = 'jpeg'

            cover_filename = f"cover.{ext}"
            media_type = f"image/{'jpeg' if ext in ['jpeg', 'jpg'] else ext}"

            cover_item = None
            for item in book.get_items():
                try:
                    item_type = item.get_type() if hasattr(item, 'get_type') else None
                    if item_type == 10:
                        cover_item = item
                        break
                except:
                    pass

            if cover_item:
                old_id = cover_item.get_id() or 'cover-image'
                old_filename = cover_item.get_name() or cover_filename
                cover_item.set_content(cover_data)
                cover_item.file_name = cover_filename
                cover_item.media_type = media_type
            else:
                new_cover = epub.EpubImage(
                    uid='cover-image',
                    file_name=cover_filename,
                    media_type=media_type,
                    content=cover_data
                )
                book.add_item(new_cover)
                book.add_metadata('OPF', 'cover', '', {'content': 'cover-image'})

            return self._write_epub_safe(epub_path, book)
        except Exception as e:
            print(f"更新 EPUB 封面失败: {e}")
            return False

    def _update_pdf_cover(self, pdf_path: str, cover_image_path: str) -> bool:
        try:
            from pypdf import PdfWriter, PdfReader

            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            img = Image.open(cover_image_path)
            if img.mode in ('RGBA', 'P', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img_pdf_bytes = io.BytesIO()
            img.save(img_pdf_bytes, format='PDF', resolution=150.0)
            img_pdf_bytes.seek(0)

            cover_reader = PdfReader(img_pdf_bytes)
            cover_page = cover_reader.pages[0]
            writer.add_page(cover_page)

            for page in reader.pages:
                writer.add_page(page)

            if reader.metadata:
                writer.add_metadata(reader.metadata)

            tmp_dir = os.path.dirname(pdf_path)
            base_name = os.path.basename(pdf_path)
            tmp_path = os.path.join(tmp_dir, f".tmp_{base_name}")

            with open(tmp_path, 'wb') as f:
                writer.write(f)

            if os.path.exists(pdf_path):
                backup_path = pdf_path + '.bak'
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(pdf_path, backup_path)

            os.rename(tmp_path, pdf_path)

            backup_path = pdf_path + '.bak'
            if os.path.exists(backup_path):
                os.remove(backup_path)

            print(f"PDF 封面更新成功: {pdf_path}")
            return True
        except ImportError as e:
            print(f"缺少依赖库: {e}")
            return False
        except Exception as e:
            print(f"更新 PDF 封面失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_metadata_to_file(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            return False

        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == '.epub':
                return self._update_epub_metadata(filepath, metadata)
            elif ext == '.pdf':
                return self._update_pdf_metadata(filepath, metadata)
            else:
                print(f"不支持的文件格式: {ext}")
                return False
        except Exception as e:
            print(f"更新元数据失败: {e}")
            return False

    def _update_epub_metadata(self, epub_path: str, metadata: Dict[str, Any]) -> bool:
        try:
            book = epub.read_epub(epub_path, options={'ignore_ncx': True})

            DC_NS = 'http://purl.org/dc/elements/1.1/'

            def clear_field(name):
                try:
                    if hasattr(book, 'metadata') and DC_NS in book.metadata:
                        if name in book.metadata[DC_NS]:
                            del book.metadata[DC_NS][name]
                except:
                    pass

            title = metadata.get('title')
            if title:
                clear_field('title')
                book.add_metadata('DC', 'title', str(title))

            authors = metadata.get('authors')
            if authors:
                clear_field('creator')
                if isinstance(authors, list):
                    for author in authors:
                        book.add_metadata('DC', 'creator', str(author))
                else:
                    book.add_metadata('DC', 'creator', str(authors))

            isbn = metadata.get('isbn')
            if isbn:
                try:
                    if DC_NS in book.metadata and 'identifier' in book.metadata[DC_NS]:
                        book.metadata[DC_NS]['identifier'] = [
                            item for item in book.metadata[DC_NS]['identifier']
                            if not (isinstance(item, tuple) and len(item) > 1 and 
                                    isinstance(item[1], dict) and item[1].get('id') == 'isbn')
                        ]
                except:
                    pass
                book.add_metadata('DC', 'identifier', str(isbn), {'id': 'isbn'})

            publisher = metadata.get('publisher')
            if publisher:
                clear_field('publisher')
                book.add_metadata('DC', 'publisher', str(publisher))

            pubdate = metadata.get('pubdate')
            if pubdate:
                clear_field('date')
                book.add_metadata('DC', 'date', str(pubdate))

            description = metadata.get('summary') or metadata.get('description')
            if description:
                clear_field('description')
                book.add_metadata('DC', 'description', str(description))

            subject = metadata.get('tags') or metadata.get('category')
            if subject:
                clear_field('subject')
                if isinstance(subject, list):
                    for s in subject:
                        book.add_metadata('DC', 'subject', str(s))
                else:
                    book.add_metadata('DC', 'subject', str(subject))

            rating = metadata.get('rating')
            if rating:
                clear_field('rating')
                book.add_metadata('DC', 'rating', str(rating))

            page_count = metadata.get('page_count')
            if page_count:
                try:
                    book.spine.insert(0, None)
                    book.spine.pop(0)
                except:
                    pass

            return self._write_epub_safe(epub_path, book)
        except Exception as e:
            print(f"更新 EPUB 元数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _update_pdf_metadata(self, pdf_path: str, metadata: Dict[str, Any]) -> bool:
        try:
            from pypdf import PdfWriter, PdfReader

            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            new_metadata = {}
            if reader.metadata:
                new_metadata.update(reader.metadata)

            title = metadata.get('title')
            if title:
                new_metadata['/Title'] = str(title)

            authors = metadata.get('authors')
            if authors:
                if isinstance(authors, list):
                    new_metadata['/Author'] = ', '.join(map(str, authors))
                else:
                    new_metadata['/Author'] = str(authors)

            isbn = metadata.get('isbn')
            if isbn:
                new_metadata['/ISBN'] = str(isbn)

            publisher = metadata.get('publisher')
            if publisher:
                new_metadata['/Publisher'] = str(publisher)

            description = metadata.get('summary') or metadata.get('description')
            if description:
                new_metadata['/Subject'] = str(description)

            tags = metadata.get('tags')
            if tags:
                if isinstance(tags, list):
                    new_metadata['/Keywords'] = ', '.join(map(str, tags))
                else:
                    new_metadata['/Keywords'] = str(tags)

            rating = metadata.get('rating')
            if rating:
                new_metadata['/Rating'] = str(rating)

            page_count = metadata.get('page_count')
            if page_count:
                new_metadata['/PageCount'] = str(page_count)

            writer.add_metadata(new_metadata)

            tmp_dir = os.path.dirname(pdf_path)
            base_name = os.path.basename(pdf_path)
            tmp_path = os.path.join(tmp_dir, f".tmp_{base_name}")

            with open(tmp_path, 'wb') as f:
                writer.write(f)

            if os.path.exists(pdf_path):
                backup_path = pdf_path + '.bak'
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(pdf_path, backup_path)

            os.rename(tmp_path, pdf_path)

            backup_path = pdf_path + '.bak'
            if os.path.exists(backup_path):
                os.remove(backup_path)

            print(f"PDF 元数据更新成功: {pdf_path}")
            return True
        except Exception as e:
            print(f"更新 PDF 元数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
