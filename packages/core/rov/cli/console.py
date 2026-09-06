"""บังคับ stdout เป็น UTF-8

Windows ภาษาไทยใช้ code page 874 เป็นค่าเริ่มต้น ซึ่งพิมพ์อักษรไทย
และสัญลักษณ์อย่าง ✓ ═ ไม่ได้ ทุก entry point ต้องเรียก setup_console() ก่อนพิมพ์
"""

from __future__ import annotations

import sys


def setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
