def safe_str(value):
    if value is None:
        return ''
    if isinstance(value, list):
        filtered = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return ', '.join(filtered)
    if isinstance(value, (int, float)):
        if value == 0:
            return ''
        return str(value)
    s = str(value).strip()
    if s.lower() in ['none', 'null', 'nan', '', '[]', '{}']:
        return ''
    return s


def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()
