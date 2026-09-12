"""ล็อกเวอร์ชันของ engine — PHASE M1.5 · GOAL 1

**ทำไมต้องมี**

ผลการวัดจะเทียบกันได้ก็ต่อเมื่อรู้ว่าวัดจาก engine ตัวไหน ตอนนี้ระบบมีสามชั้น
ที่เปลี่ยนได้อิสระจากกัน และเปลี่ยนชั้นไหนก็ทำให้ตัวเลขขยับได้ทั้งนั้น

    โค้ด        recommend.py, counterknowledge.py, composition.py ...
    น้ำหนัก      weights_for, ban_weights_for, EXTRA_WEIGHTS
    ความรู้      heroes.yaml, knowledge/counter/, knowledge/macro/, format.yaml

ถ้าจดแค่ commit hash จะพลาดกรณีที่ไฟล์ความรู้ถูกแก้โดยไม่ commit
ถ้าจดแค่ไฟล์ความรู้จะพลาดกรณีที่โค้ดเปลี่ยนสูตร

โมดูลนี้จึง **คำนวณลายนิ้วมือสดจากไฟล์จริงทุกครั้ง** ไม่ใช่ค่าคงที่ที่ต้องมาไล่แก้เอง
ค่าคงที่ที่คนต้องจำไปอัปเดตเองคือค่าที่จะค้างอยู่กับอดีตแล้วหลอกคนอ่าน

**ไม่ใช่ระบบ migration** — มันไม่ได้ทำให้ผลเก่ากลับมาใช้ได้
มันแค่ตอบได้ว่า "ผลที่บันทึกไว้มาจาก engine เดียวกับตอนนี้หรือเปล่า"
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# ไฟล์ที่ถือว่าเป็น "engine" — แก้ไฟล์ไหนก็ตามในนี้ ผลการวัดเก่าใช้เทียบไม่ได้แล้ว
CODE_FILES: tuple[str, ...] = (
    "packages/core/rov/draft/recommend.py",
    "packages/core/rov/draft/stats.py",
    "packages/core/rov/draft/lanes.py",
    "packages/core/rov/draft/composition.py",
    "packages/core/rov/draft/counterknowledge.py",
    "packages/core/rov/draft/synergyknowledge.py",
    "packages/core/rov/draft/winconditions.py",
)

# ไฟล์ความรู้ — ไม่ใช่โค้ด แต่เปลี่ยนแล้วคำแนะนำเปลี่ยน
KNOWLEDGE_PATHS: tuple[str, ...] = (
    "configs/draft/heroes.yaml",
    "configs/draft/hero_assessment.yaml",
    "configs/draft/format.yaml",
    "knowledge/counter",
    "knowledge/synergy",
    "knowledge/macro",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _hash_path(path: Path) -> str | None:
    """แฮชไฟล์เดียวหรือทั้งไดเรกทอรี — คืน None เมื่อไม่มีไฟล์

    ไดเรกทอรีเรียงชื่อก่อนเสมอ ผลจึงซ้ำได้ไม่ว่าระบบไฟล์จะคืนลำดับอย่างไร
    """
    if not path.exists():
        return None
    if path.is_file():
        return _sha(path.read_bytes())
    h = hashlib.sha256()
    for f in sorted(path.rglob("*")):
        if f.is_file():
            h.update(f.relative_to(path).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:12]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


@dataclass
class EngineVersion:
    """ลายนิ้วมือของ engine ณ ขณะที่เรียก"""

    commit: str | None = None
    dirty: bool = False
    code: dict[str, str | None] = field(default_factory=dict)
    knowledge: dict[str, str | None] = field(default_factory=dict)
    weights: dict[str, object] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------

    @property
    def code_hash(self) -> str:
        return _sha("".join(f"{k}:{v}" for k, v in sorted(self.code.items())).encode())

    @property
    def knowledge_hash(self) -> str:
        return _sha(
            "".join(f"{k}:{v}" for k, v in sorted(self.knowledge.items())).encode()
        )

    @property
    def weights_hash(self) -> str:
        return _sha(repr(sorted(self.weights.items())).encode())

    @property
    def fingerprint(self) -> str:
        """ค่าเดียวที่สรุปทั้งสามชั้น — ใช้เทียบว่า 'engine เดียวกันไหม'"""
        return _sha(
            f"{self.code_hash}|{self.knowledge_hash}|{self.weights_hash}".encode()
        )

    @property
    def comparable(self) -> bool:
        """ผลที่วัดตอนนี้เอาไปเทียบกับผลอื่นได้ไหม

        working tree ที่ยังไม่ commit = เทียบไม่ได้ เพราะไม่มีใครย้อนกลับมาดูได้ว่า
        ตอนนั้นโค้ดหน้าตาอย่างไร
        """
        return self.commit is not None and not self.dirty


def current() -> EngineVersion:
    """อ่านสถานะจริงของ repo ตอนนี้"""
    from rov.draft.recommend import (
        BAN_META_SHARE,
        EXTRA_WEIGHTS,
        MIN_PAIR_GAMES,
        PICK_META_SHARE,
        ROLE_FLOOR,
        weights_for,
    )
    from rov.draft.stats import MIN_GAMES_RELIABLE, SHRINKAGE_K

    v = EngineVersion(
        commit=_git("rev-parse", "--short", "HEAD"),
        dirty=bool(_git("status", "--porcelain")),
        code={p: _hash_path(Path(p)) for p in CODE_FILES},
        knowledge={p: _hash_path(Path(p)) for p in KNOWLEDGE_PATHS},
        weights={
            # น้ำหนักฐานตอนที่ยังไม่มีใครเปิดตัว — จุดที่อ่านง่ายที่สุด
            "pick_opening": {k: round(x, 6) for k, x in weights_for(0, 0).items()},
            "pick_meta_share": PICK_META_SHARE,
            "ban_meta_share": BAN_META_SHARE,
            "extra": dict(sorted(EXTRA_WEIGHTS.items())),
            "role_floor": ROLE_FLOOR,
            "min_pair_games": MIN_PAIR_GAMES,
            "shrinkage_k": SHRINKAGE_K,
            "min_games_reliable": MIN_GAMES_RELIABLE,
        },
    )
    v.counts = _counts()
    return v


def _counts() -> dict[str, int]:
    """ขนาดของแต่ละคลังความรู้ — อ่านง่ายกว่าแฮชเวลาคนมาดู"""
    out: dict[str, int] = {}
    try:
        from rov.draft.heroes import HeroDB

        db = HeroDB.load("configs/draft/heroes.yaml")
        out["heroes"] = len(db.heroes)
        out["heroes_assessed"] = sum(1 for h in db.heroes if h.filled_kind)
    except Exception:  # noqa: BLE001 — ไฟล์หายไม่ควรทำให้เวอร์ชันอ่านไม่ได้
        pass
    try:
        from rov.draft.counterknowledge import CounterBook

        b = CounterBook.load()
        out["counter_evidence"] = len(b.evidence)
        out["counter_threats"] = len(b.threats)
        out["counter_capabilities"] = len(b.capabilities)
    except Exception:  # noqa: BLE001
        pass
    try:
        from rov.draft.synergyknowledge import SynergyBook

        sb = SynergyBook.load()
        out["synergy_evidence"] = len(sb.evidence)
        out["synergy_usable"] = len(sb.usable_evidence)
    except Exception:  # noqa: BLE001
        pass
    try:
        from rov.macro.plays import MacroBook

        out["macro_rules"] = len(MacroBook.load().rules)
    except Exception:  # noqa: BLE001
        pass
    return out


def report(v: EngineVersion | None = None) -> str:
    v = v or current()
    lines = [
        "── ENGINE VERSION ──",
        f"  fingerprint   {v.fingerprint}",
        f"  commit        {v.commit or 'ไม่ใช่ git repo'}"
        + ("  ⚠️ working tree มีของที่ยังไม่ commit" if v.dirty else ""),
        f"  เทียบผลได้ไหม  {'ได้' if v.comparable else 'ยังไม่ได้ — commit ก่อน'}",
        "",
        f"  code          {v.code_hash}",
    ]
    lines += [f"    {k.split('/')[-1]:<24} {h}" for k, h in sorted(v.code.items())]
    lines += ["", f"  knowledge     {v.knowledge_hash}"]
    lines += [f"    {k:<24} {h or 'ไม่มีไฟล์'}" for k, h in sorted(v.knowledge.items())]
    if v.counts:
        lines.append("")
        lines += [f"    {k:<24} {n}" for k, n in sorted(v.counts.items())]
    lines += ["", f"  weights       {v.weights_hash}"]
    opening = v.weights.get("pick_opening", {})
    if isinstance(opening, dict):
        lines.append(
            "    pick(0,0)              "
            + " ".join(f"{k} {x:.4f}" for k, x in sorted(opening.items()))
        )
    lines.append(f"    ban_meta_share         {v.weights.get('ban_meta_share')}")
    extra = v.weights.get("extra", {})
    if isinstance(extra, dict):
        on = [k for k, x in extra.items() if x]
        lines.append(
            f"    extra                  {len(extra)} ตัว · เปิดอยู่ "
            + (", ".join(on) if on else "ไม่มีเลย (ทุกตัวยัง 0)")
        )
    return "\n".join(lines)
