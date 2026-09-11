"""Composition Engine — วิเคราะห์ทีม 5 ตัวจาก attribute ล้วน

Blueprint §30 · docs/06-draft-engine.md §3

ทำงานได้โดยไม่ต้องมีข้อมูลแมตช์แม้แต่เกมเดียว ขอเพียง hero attribute ครบ
จึงเป็นส่วนแรกของ Draft System ที่ส่งมอบคุณค่าได้

**หลักสำคัญ: ห้ามใช้ค่าเฉลี่ยกับทุกมิติ**

การเลือกฟังก์ชันรวมผิดคือสาเหตุหลักที่ระบบให้คะแนน draft ผิด

    มีหนึ่งคนก็พอ    engage, frontline    -> ใช้ค่าสูงสุดถ่วงน้ำหนัก
    สะสมกันได้       cc, damage           -> ใช้ผลรวมที่อิ่มตัว
    จุดอ่อนกำหนด     waveclear ตอนตั้งรับ -> ใช้ค่าต่ำสุด
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from rov.domain.enums import DamageType, LaneRole
from rov.draft.heroes import Hero

TEAM_SIZE = 5


class IncompleteDataError(ValueError):
    """attribute ไม่ครบ — ระบบปฏิเสธการให้คะแนนแทนที่จะเดา"""


@dataclass(slots=True)
class Dimension:
    key: str
    label: str
    value: float
    detail: str

    def __post_init__(self) -> None:
        self.value = max(0.0, min(100.0, self.value))


@dataclass
class CompositionReport:
    heroes: list[str]
    dimensions: dict[str, Dimension] = field(default_factory=dict)
    power_curve: dict[str, float] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    # ตัวที่ค่ามาจากผู้ช่วย AI ไม่ใช่คนที่รู้เกม — ต้องขึ้นคำเตือนทุกครั้ง
    assistant_filled: list[str] = field(default_factory=list)

    def value(self, key: str) -> float:
        return self.dimensions[key].value

    def report(self) -> str:
        lines = [f"═══ Composition: {', '.join(self.heroes)} ═══", ""]
        for d in self.dimensions.values():
            bar = "█" * int(d.value / 5)
            lines.append(f"  {d.label:<18} {d.value:>5.1f}  {bar}")
            if d.detail:
                lines.append(f"  {'':<18}        {d.detail}")
        lines += ["", "  Power curve"]
        for k in ("early", "mid", "late"):
            v = self.power_curve.get(k, 0.0)
            lines.append(f"    {k:<6} {v:>5.1f}  {'█' * int(v / 5)}")
        if self.strengths:
            lines += ["", "  จุดแข็ง: " + ", ".join(self.strengths)]
        if self.gaps:
            lines.append("  จุดอ่อน: " + ", ".join(self.gaps))
        lines += self.provenance_lines()
        return "\n".join(lines)

    def provenance_lines(self) -> list[str]:
        """บอกว่าคะแนนที่เห็นยืนอยู่บนอะไร

        ต่างจากมิติอื่นในระบบ ตรงนี้ไม่มี n ให้ดู เพราะไม่ได้มาจากการนับ
        สิ่งเดียวที่บอกความน่าเชื่อถือได้คือ "ใครเป็นคนให้ค่า" จึงต้องแสดงเสมอ
        """
        if not self.assistant_filled:
            return []
        return [
            "",
            f"  ⚠ ค่า attribute ของ {', '.join(self.assistant_filled)} "
            "ประเมินโดยผู้ช่วย AI ไม่ใช่โค้ชหรือผู้เล่น",
            "    คะแนนข้างบนจึงเป็นจุดตั้งต้น ไม่ใช่ข้อสรุป "
            "ดูเหตุผลที่ configs/draft/hero_assessment.yaml",
        ]


# --------------------------------------------------------------- ฟังก์ชันรวม


def _top_weighted(vals: list[int], weights: tuple[float, ...] = (0.7, 0.3)) -> float:
    """มีคนเก่งหนึ่งคนมีค่ากว่ามีคนกลาง ๆ ห้าคน

    ใช้กับมิติที่ "มีหนึ่งคนก็พอ" เช่น engage และ frontline
    """
    s = sorted(vals, reverse=True)
    return sum(w * (s[i] if i < len(s) else 0) for i, w in enumerate(weights))


def _saturating_sum(vals: list[int], scale: float) -> float:
    """ผลรวมที่อิ่มตัว — คนที่ห้าเพิ่มค่าน้อยกว่าคนที่สอง

    ใช้กับมิติที่สะสมกันได้แต่มีผลตอบแทนลดลง เช่น CC
    """
    return 100.0 * (1.0 - math.exp(-sum(vals) / scale))


def _weakest(vals: list[int]) -> float:
    """จุดอ่อนที่สุดเป็นตัวกำหนด — ใช้กับมิติที่ทีมพังเพราะคนเดียว"""
    return float(min(vals)) if vals else 0.0


def _mean(vals: list[int]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


# --------------------------------------------------------- ทีมที่ยังไม่ครบ


# ชื่อมิติที่คิดจาก utility ตรง ๆ คู่กับฟังก์ชันรวมของมัน
# **ต้องตรงกับที่ analyze() ใช้เป๊ะ ๆ** — ถ้าวันหนึ่งไม่ตรง คะแนนระหว่างดราฟต์
# จะคนละมาตรกับคะแนนตอนดราฟต์จบ ซึ่งผู้ใช้จะงงว่าทำไมตัวเลขกระโดด
# tests/unit/test_composition_partial.py คอยจับให้
_PARTIAL_DIMS: dict[str, tuple[str, str]] = {
    "frontline": ("frontline", "top"),
    "engage": ("engage", "top"),
    "disengage": ("disengage", "top"),
    "peel": ("peel", "top"),
    "objective": ("objective", "top"),
    "crowd_control": ("cc_hard", "sat"),
    "waveclear": ("waveclear", "weak_mean"),
    "split_push": ("splitpush", "top80"),
}


def partial_dimensions(heroes: list[Hero]) -> dict[str, float] | None:
    """คะแนนแต่ละมิติของทีมที่ยังเลือกไม่ครบ 5 ตัว

    ใช้ระหว่างดราฟต์ ตอนที่ยังมี 0-4 ตัว ซึ่ง `analyze()` รับไม่ได้
    เพราะมันบังคับ 5 ตัวพอดีและโยน IncompleteDataError

    **ใช้ฟังก์ชันรวมชุดเดียวกับ analyze() ทุกตัว ไม่ได้เขียนสูตรใหม่**
    ต่างกันแค่รับจำนวนตัวไม่ครบได้ และคืน None แทนการโยน exception

    คืน `None` เมื่อมีตัวใดตัวหนึ่ง attribute ไม่ครบ — ไม่เดาค่าให้
    เป็นหลักเดียวกับ `Hero.u()` ที่ยอมโยน exception ดีกว่าคืนค่ากลาง

    ทีมว่าง (ยังไม่เลือกใคร) คืน dict ที่ทุกมิติเป็น 0.0 ซึ่งถูกต้อง —
    ทีมที่ยังไม่มีใครเลย ไม่มี frontline จริง ๆ ไม่ใช่ "ไม่รู้"
    """
    if any(not h.complete for h in heroes):
        return None

    out: dict[str, float] = {}
    for name, (key, how) in _PARTIAL_DIMS.items():
        vals = [h.u(key) for h in heroes]
        if not vals:
            out[name] = 0.0
        elif how == "top":
            out[name] = _top_weighted(vals)
        elif how == "top80":
            out[name] = _top_weighted(vals, (0.8, 0.2))
        elif how == "sat":
            out[name] = _saturating_sum(vals, 180.0)
        else:  # weak_mean
            out[name] = 0.45 * _weakest(vals) + 0.55 * _mean(vals)

    out["role_balance"] = _role_balance(heroes).value if heroes else 0.0
    out["damage_mix"] = _damage_mix(heroes).value if heroes else 0.0
    return {k: max(0.0, min(100.0, v)) for k, v in out.items()}


# ------------------------------------------------------------------- หลัก


def analyze(heroes: list[Hero]) -> CompositionReport:
    """วิเคราะห์ทีม — โยน IncompleteDataError ถ้า attribute ไม่ครบ"""
    if len(heroes) != TEAM_SIZE:
        raise ValueError(f"ทีมต้องมี {TEAM_SIZE} ตัว แต่ได้ {len(heroes)}")

    missing = {h.id: h.missing_fields() for h in heroes if not h.complete}
    if missing:
        detail = "; ".join(f"{k}: {', '.join(v[:4])}" for k, v in missing.items())
        raise IncompleteDataError(
            f"ให้คะแนนไม่ได้เพราะ attribute ยังไม่ครบ — {detail}. "
            "ระบบไม่เดาค่าให้ ใช้ rov draft todo เพื่อดูว่าต้องกรอกอะไรบ้าง"
        )

    rep = CompositionReport(
        heroes=[h.id for h in heroes],
        assistant_filled=[h.id for h in heroes if h.filled_kind == "assistant"],
    )
    d = rep.dimensions

    # 1 Role balance — เลนครบไหม
    d["role_balance"] = _role_balance(heroes)

    # 2 Damage mix — เอียงไปทางเดียวหรือไม่
    d["damage_mix"] = _damage_mix(heroes)

    # 3 Frontline — มีคนรับดาเมจไหม (มีหนึ่งคนก็พอ)
    d["frontline"] = Dimension(
        "frontline", "Frontline",
        _top_weighted([h.u("frontline") for h in heroes]),
        _who_leads(heroes, "frontline"),
    )

    # 4 Engage — เปิดฟightได้ไหม (มีหนึ่งคนก็พอ)
    d["engage"] = Dimension(
        "engage", "Engage",
        _top_weighted([h.u("engage") for h in heroes]),
        _who_leads(heroes, "engage"),
    )

    # 5 Disengage — ถอยได้ไหม
    d["disengage"] = Dimension(
        "disengage", "Disengage",
        _top_weighted([h.u("disengage") for h in heroes]), "",
    )

    # 6 Crowd control — สะสมกันได้ แต่อิ่มตัว
    cc = [h.u("cc_hard") for h in heroes]
    d["crowd_control"] = Dimension(
        "crowd_control", "Hard CC", _saturating_sum(cc, 180.0),
        f"รวม {sum(cc)} จาก {sum(1 for c in cc if c >= 50)} ตัวที่มี CC เด่น",
    )

    # 7 Peel — ปกป้อง carry
    d["peel"] = Dimension(
        "peel", "Peel", _top_weighted([h.u("peel") for h in heroes]),
        _who_leads(heroes, "peel"),
    )

    # 8 Objective — ตี objective ได้เร็วไหม
    d["objective"] = Dimension(
        "objective", "Objective", _top_weighted([h.u("objective") for h in heroes]),
        _who_leads(heroes, "objective"),
    )

    # 9 Waveclear — ตั้งรับได้ไหม จุดอ่อนที่สุดเป็นตัวกำหนด
    wc = [h.u("waveclear") for h in heroes]
    d["waveclear"] = Dimension(
        "waveclear", "Waveclear", 0.45 * _weakest(wc) + 0.55 * _mean(wc),
        f"ต่ำสุด {min(wc)} เฉลี่ย {_mean(wc):.0f}",
    )

    # 10 Split push
    d["split_push"] = Dimension(
        "split_push", "Split Push",
        _top_weighted([h.u("splitpush") for h in heroes], (0.8, 0.2)),
        _who_leads(heroes, "splitpush"),
    )

    rep.power_curve = {
        "early": _mean([h.scaling.early for h in heroes]),  # type: ignore[misc]
        "mid": _mean([h.scaling.mid for h in heroes]),  # type: ignore[misc]
        "late": _mean([h.scaling.late for h in heroes]),  # type: ignore[misc]
    }

    for dim in d.values():
        if dim.value < 35:
            rep.gaps.append(dim.label)
        elif dim.value >= 75:
            rep.strengths.append(dim.label)
    return rep


# ------------------------------------------------------------------- มิติย่อย


def _max_lane_matching(heroes: list[Hero]) -> dict[LaneRole, int]:
    """จับคู่ฮีโร่กับเลนให้ครอบคลุมมากที่สุด ด้วยอัลกอริทึม Kuhn

    ต้องเป็น maximum matching จริง ไม่ใช่การไล่จัดตามลำดับ
    เพราะฮีโร่ที่เล่นได้หลายเลนต้องยอมสละเลนให้ตัวที่เล่นได้เลนเดียว

    ตัวอย่างที่การไล่จัดแบบง่ายพลาด
        demo_1 เล่นได้ DS, JUNGLE
        demo_5 เล่นได้ DS อย่างเดียว
    ถ้าให้ demo_1 ลง DS ก่อน จะไม่มีใครลง JUNGLE ได้เลย
    ที่ถูกคือ demo_5 ลง DS แล้ว demo_1 ไปลง JUNGLE
    """
    match_lane: dict[LaneRole, int] = {}

    def augment(hero_idx: int, visited: set[LaneRole]) -> bool:
        for lane in heroes[hero_idx].lane_roles:
            if lane in visited:
                continue
            visited.add(lane)
            holder = match_lane.get(lane)
            if holder is None or augment(holder, visited):
                match_lane[lane] = hero_idx
                return True
        return False

    for i in range(len(heroes)):
        augment(i, set())
    return match_lane


def _role_balance(heroes: list[Hero]) -> Dimension:
    """ครอบคลุมห้าเลนหรือไม่"""
    lanes = list(LaneRole)
    matched = _max_lane_matching(heroes)
    covered = len(matched)
    uncovered = [ln.value for ln in lanes if ln not in matched]
    return Dimension(
        "role_balance", "Role Balance",
        100.0 * covered / len(lanes),
        f"ครบ {covered}/{len(lanes)}" + (f" ขาด {', '.join(uncovered)}" if uncovered else ""),
    )


def _damage_mix(heroes: list[Hero]) -> Dimension:
    """ลงโทษทีมที่ดาเมจเอียงไปทางเดียว เพราะศัตรูขึ้นของต้านทางเดียวก็พอ"""
    phys = sum(1 for h in heroes if h.damage.type is DamageType.PHYSICAL)
    mag = sum(1 for h in heroes if h.damage.type is DamageType.MAGICAL)
    hybrid = sum(1 for h in heroes if h.damage.type is DamageType.HYBRID)
    phys += hybrid * 0.5
    mag += hybrid * 0.5
    if max(phys, mag) == 0:
        return Dimension("damage_mix", "Damage Mix", 0.0, "ไม่มีข้อมูลชนิดดาเมจ")
    ratio = min(phys, mag) / max(phys, mag)
    return Dimension(
        "damage_mix", "Damage Mix",
        100.0 * ratio**0.6,
        f"กายภาพ {phys:g} : เวท {mag:g}",
    )


def _who_leads(heroes: list[Hero], key: str) -> str:
    best = max(heroes, key=lambda h: h.u(key))
    return f"นำโดย {best.id} ({best.u(key)})"


# ------------------------------------------------------------------- เทียบทีม


def compare(ours: CompositionReport, theirs: CompositionReport) -> str:
    lines = ["═══ เทียบสองทีม ═══", "",
             f"  {'มิติ':<18}{'เรา':>7}{'เขา':>7}{'ต่าง':>8}"]
    for key, dim in ours.dimensions.items():
        a, b = dim.value, theirs.value(key)
        lines.append(f"  {dim.label:<18}{a:>7.1f}{b:>7.1f}{a - b:>+8.1f}")
    lines += ["", "  Power curve"]
    for k in ("early", "mid", "late"):
        a, b = ours.power_curve[k], theirs.power_curve[k]
        lines.append(f"    {k:<6}{a:>9.1f}{b:>7.1f}{a - b:>+8.1f}")

    diffs = {k: ours.power_curve[k] - theirs.power_curve[k] for k in ("early", "mid", "late")}
    best = max(diffs, key=lambda k: diffs[k])
    lines += ["", f"  ได้เปรียบที่สุดช่วง {best} ({diffs[best]:+.1f})"]
    if best == "early":
        lines.append("  แปลว่าควรจบเกมให้เร็ว อย่าปล่อยให้ยืดไปช่วงท้าย")
    elif best == "late":
        lines.append("  แปลว่าควรยื้อเวลา หลีกเลี่ยงการปะทะช่วงต้น")
    return "\n".join(lines)
