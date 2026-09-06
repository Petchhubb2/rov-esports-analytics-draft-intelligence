"""ตัวแยก template ของ MediaWiki wikitext

จำเป็นต้องเขียนเองเพราะ template ซ้อนกันหลายชั้น เช่น

    {{Match
      |opponent1={{TeamOpponent|fs|substitutes={{PlayerSubstitutions|...}}}}
      |map1={{Map|t1h1=skud|...}}
    }}

การใช้ regex แยก `|` ตรง ๆ จะพังทันทีที่เจอ template ซ้อน
จึงต้องนับวงเล็บให้สมดุลก่อนตัด
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Template:
    name: str
    params: dict[str, str] = field(default_factory=dict)
    positional: list[str] = field(default_factory=list)
    raw: str = ""

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.params.get(key, default)

    def sub(self, key: str) -> Template | None:
        """แปลงค่าพารามิเตอร์ที่เป็น template ซ้อนอยู่"""
        val = self.params.get(key)
        if not val:
            return None
        found = find_templates(val)
        return found[0] if found else None


def strip_comments(text: str) -> str:
    """ตัด <!-- ... --> ออก เพราะไฟล์จริงใช้ comment คั่นกลุ่ม pick กับ ban"""
    out: list[str] = []
    i = 0
    while i < len(text):
        start = text.find("<!--", i)
        if start == -1:
            out.append(text[i:])
            break
        out.append(text[i:start])
        end = text.find("-->", start)
        if end == -1:
            break
        i = end + 3
    return "".join(out)


def _split_top_level(body: str) -> list[str]:
    """ตัดด้วย | เฉพาะระดับบนสุด ไม่ตัดข้างใน {{ }} หรือ [[ ]]"""
    parts: list[str] = []
    depth_brace = 0
    depth_bracket = 0
    cur: list[str] = []
    i = 0
    while i < len(body):
        two = body[i : i + 2]
        if two == "{{":
            depth_brace += 1
            cur.append(two)
            i += 2
            continue
        if two == "}}":
            depth_brace -= 1
            cur.append(two)
            i += 2
            continue
        if two == "[[":
            depth_bracket += 1
            cur.append(two)
            i += 2
            continue
        if two == "]]":
            depth_bracket -= 1
            cur.append(two)
            i += 2
            continue
        ch = body[i]
        if ch == "|" and depth_brace == 0 and depth_bracket == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def parse_template(raw: str) -> Template:
    """แปลงข้อความ {{Name|a=1|b=2}} หนึ่งอันเป็นอ็อบเจกต์"""
    inner = raw.strip()
    if inner.startswith("{{"):
        inner = inner[2:]
    if inner.endswith("}}"):
        inner = inner[:-2]

    parts = _split_top_level(inner)
    name = parts[0].strip()
    tpl = Template(name=name, raw=raw)
    for part in parts[1:]:
        if "=" in part:
            key, _, val = part.partition("=")
            key = key.strip()
            # key ที่มี {{ }} แปลว่า = อยู่ใน template ซ้อน ไม่ใช่ตัวคั่นจริง
            if "{{" in key or "\n" in key:
                tpl.positional.append(part.strip())
            else:
                tpl.params[key] = val.strip()
        else:
            stripped = part.strip()
            if stripped:
                tpl.positional.append(stripped)
    return tpl


def find_templates(text: str, name: str | None = None) -> list[Template]:
    """หา template ทั้งหมดในระดับบนสุดของข้อความ

    name  กรองเฉพาะชื่อที่ต้องการ (เทียบแบบไม่สนตัวพิมพ์)
    """
    text = strip_comments(text)
    out: list[Template] = []
    i = 0
    n = len(text)
    while i < n:
        start = text.find("{{", i)
        if start == -1:
            break
        depth = 0
        j = start
        while j < n:
            if text[j : j + 2] == "{{":
                depth += 1
                j += 2
                continue
            if text[j : j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
                continue
            j += 1
        if depth != 0:
            break  # วงเล็บไม่สมดุล หยุดดีกว่าเดา
        raw = text[start:j]
        tpl = parse_template(raw)
        if name is None or tpl.name.lower() == name.lower():
            out.append(tpl)
        i = j
    return out


def iter_nested(text: str, name: str) -> list[Template]:
    """หา template ชื่อที่ระบุ ทุกระดับความลึก ไม่ใช่เฉพาะระดับบนสุด"""
    text = strip_comments(text)
    out: list[Template] = []
    i = 0
    n = len(text)
    target = "{{" + name.lower()
    while i < n:
        start = text.lower().find(target, i)
        if start == -1:
            break
        after = start + len(target)
        # ต้องตามด้วยตัวคั่น ไม่ใช่ตัวอักษรอื่น กัน Match ไปชน MatchList
        if after < n and (text[after].isalnum() or text[after] == "/"):
            i = start + 2
            continue
        depth = 0
        j = start
        while j < n:
            if text[j : j + 2] == "{{":
                depth += 1
                j += 2
                continue
            if text[j : j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
                continue
            j += 1
        if depth != 0:
            break
        out.append(parse_template(text[start:j]))
        i = j
    return out
