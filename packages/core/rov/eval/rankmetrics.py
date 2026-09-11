"""วัดคุณภาพการจัดอันดับ และเทียบ ranker หลายตัวบนตาเดียวกัน — PHASE M0.5

**ต่างจาก `benchmark.py` เดิมอย่างไร**

`benchmark.py` วัดจาก top-5 จึงคำนวณ MRR กับ mean rank ไม่ได้ —
ตัวที่ทีมอาชีพเลือกอาจอยู่อันดับ 40 ซึ่ง top-5 มองไม่เห็นเลย
โมดูลนี้ขอ ranking เต็มจาก ranker แล้ววัดอันดับจริงของตัวนั้น

**ความเป็นธรรมของการเทียบ**

ทุก ranker เห็น `TurnContext` เดียวกัน เลือกจาก `candidates()` ชุดเดียวกัน
และถูกวัดบนตาชุดเดียวกัน — ตาที่ ranker ตัวใดตัวหนึ่งจัดอันดับไม่ได้
จะถูกตัดออกจากการนับของ **ทุกตัว** ไม่ใช่แค่ตัวนั้น
มิฉะนั้นตัวที่ยอมแพ้บ่อยจะได้เปรียบเพราะเหลือแต่ตาที่ง่าย
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RankStats:
    """ผลของ ranker หนึ่งตัวบนตาชุดหนึ่ง"""

    name: str
    n_turns: int = 0            # ตาที่ถูกนับทั้งหมด
    n_ranked: int = 0           # ตาที่ตัวจริงอยู่ในอันดับ (coverage)
    top1: int = 0
    top3: int = 0
    top5: int = 0
    rr_sum: float = 0.0         # Σ 1/rank
    rank_sum: int = 0
    ranks: list[int] = field(default_factory=list)

    def add(self, rank: int | None) -> None:
        """rank เริ่มที่ 1 · None = ตัวจริงไม่อยู่ในอันดับเลย"""
        self.n_turns += 1
        if rank is None:
            return
        self.n_ranked += 1
        self.rr_sum += 1.0 / rank
        self.rank_sum += rank
        self.ranks.append(rank)
        self.top1 += rank <= 1
        self.top3 += rank <= 3
        self.top5 += rank <= 5

    # ---- ตัวชี้วัด · ทุกตัวหารด้วย n_ranked ไม่ใช่ n_turns -------------
    #
    # ตาที่จัดอันดับไม่ได้ถูกแยกไปอยู่ใน coverage แล้ว
    # ถ้าเอามาหารซ้ำจะเป็นการลงโทษสองครั้งและทำให้เทียบข้าม ranker ไม่ได้

    def _r(self, n: int) -> float | None:
        return n / self.n_ranked if self.n_ranked else None

    @property
    def top1_acc(self) -> float | None:
        return self._r(self.top1)

    @property
    def top3_acc(self) -> float | None:
        return self._r(self.top3)

    @property
    def top5_acc(self) -> float | None:
        return self._r(self.top5)

    @property
    def mrr(self) -> float | None:
        return self._r(self.rr_sum) if self.n_ranked else None

    @property
    def mean_rank(self) -> float | None:
        return self.rank_sum / self.n_ranked if self.n_ranked else None

    @property
    def median_rank(self) -> float | None:
        if not self.ranks:
            return None
        s = sorted(self.ranks)
        n = len(s)
        return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    @property
    def coverage(self) -> float | None:
        return self.n_ranked / self.n_turns if self.n_turns else None

    def row(self) -> str:
        def f(v: float | None, w: int = 6, p: int = 3) -> str:
            return f"{v:>{w}.{p}f}" if v is not None else f"{'—':>{w}}"

        return (
            f"  {self.name:<22}{f(self.top1_acc)}{f(self.top3_acc)}"
            f"{f(self.top5_acc)}{f(self.mrr)}{f(self.mean_rank, 8, 1)}"
            f"{f(self.median_rank, 8, 1)}{f(self.coverage)}{self.n_ranked:>7}"
        )


HEADER = (
    f"  {'ranker':<22}{'top1':>6}{'top3':>6}{'top5':>6}{'MRR':>6}"
    f"{'mean':>8}{'median':>8}{'cover':>6}{'n':>7}"
)


def wilson_interval(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """ช่วงความเชื่อมั่นของสัดส่วน — Wilson score

    ใช้ Wilson ไม่ใช่ normal approximation เพราะ top-1 accuracy ต่ำมาก (~5%)
    และ n ไม่ใหญ่ ซึ่งเป็นกรณีที่ normal approximation ให้ช่วงที่ผิด
    (ติดลบได้ และแคบเกินจริง)
    """
    if n == 0:
        return (0.0, 0.0)
    p = hits / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def significant_difference(a: RankStats, b: RankStats, metric: str = "top1") -> str:
    """ต่างกันอย่างมีนัยไหม — บอกตรง ๆ เมื่อยังบอกไม่ได้

    ใช้การทับกันของช่วงความเชื่อมั่น ซึ่งเป็นเกณฑ์ที่ **เข้มกว่า**
    การทดสอบสองสัดส่วนตามปกติ จึงอนุรักษ์นิยม (ไม่ประกาศว่าต่างง่าย ๆ)
    เหมาะกับสถานการณ์ที่ยังไม่อยากด่วนสรุป
    """
    ha, hb = getattr(a, metric), getattr(b, metric)
    if ha is None or hb is None:
        return "ข้อมูลไม่พอ"
    na, nb = a.n_ranked, b.n_ranked
    lo_a, hi_a = wilson_interval(int(round(ha * na)), na)
    lo_b, hi_b = wilson_interval(int(round(hb * nb)), nb)
    if hi_a < lo_b or hi_b < lo_a:
        return "ต่างอย่างมีนัย"
    return "ยังแยกไม่ออก (ช่วงความเชื่อมั่นทับกัน)"


# ---------------------------------------------------------------- breakdown


@dataclass
class Sliced:
    """ผลที่แยกตามมิติหนึ่ง เช่น ฝั่ง หรือเฟส"""

    dimension: str
    rows: dict[str, dict[str, RankStats]] = field(default_factory=dict)

    def add(self, slice_key: str, ranker: str, rank: int | None) -> None:
        bucket = self.rows.setdefault(str(slice_key), {})
        st = bucket.get(ranker)
        if st is None:
            st = bucket[ranker] = RankStats(name=ranker)
        st.add(rank)

    def report(self, metric: str = "top1_acc", min_n: int = 20) -> str:
        """ตารางหนึ่งมิติ · ซ่อนกลุ่มที่ n น้อยเกินกว่าจะอ่านได้"""
        names: list[str] = []
        for bucket in self.rows.values():
            for n in bucket:
                if n not in names:
                    names.append(n)
        lines = [f"  ── แยกตาม {self.dimension} ──", ""]
        lines.append(f"  {'':<20}" + "".join(f"{n[:16]:>18}" for n in names))
        for key in sorted(self.rows):
            bucket = self.rows[key]
            any_n = max((s.n_ranked for s in bucket.values()), default=0)
            if any_n < min_n:
                continue
            cells = []
            for n in names:
                s = bucket.get(n)
                v = getattr(s, metric) if s else None
                cells.append(f"{v:>16.3f}  " if v is not None else f"{'—':>16}  ")
            lines.append(f"  {key:<20}" + "".join(cells) + f"  n={any_n}")
        skipped = [k for k, b in self.rows.items()
                   if max((s.n_ranked for s in b.values()), default=0) < min_n]
        if skipped:
            names_ = ", ".join(sorted(skipped)[:6])
            lines.append(f"  (ซ่อน {len(skipped)} กลุ่มที่ n < {min_n}: {names_})")
        return "\n".join(lines)


# ------------------------------------------------------------- calibration


@dataclass
class Calibration:
    """คะแนนที่ระบบให้ สอดคล้องกับความแม่นจริงไหม

    ถ้าคะแนนมีความหมาย ตาที่อันดับ 1 ทิ้งห่างอันดับ 2 มาก ควรแม่นกว่า
    ตาที่คะแนนสูสี — ถ้าไม่เป็นแบบนั้น แปลว่าคะแนนบอกความมั่นใจไม่ได้
    """

    buckets: dict[str, tuple[int, int]] = field(default_factory=lambda: defaultdict(lambda: (0, 0)))

    def add(self, gap: float, hit: bool) -> None:
        key = self._bucket(gap)
        h, n = self.buckets.get(key, (0, 0))
        self.buckets[key] = (h + int(hit), n + 1)

    @staticmethod
    def _bucket(gap: float) -> str:
        for edge, label in ((1.0, "0-1"), (3.0, "1-3"), (6.0, "3-6"), (12.0, "6-12")):
            if gap < edge:
                return label
        return "12+"

    def report(self) -> str:
        order = ["0-1", "1-3", "3-6", "6-12", "12+"]
        lines = [
            "  ── calibration · ช่องว่างคะแนนอันดับ 1 กับ 2 เทียบกับความแม่นจริง ──",
            "",
            f"  {'ช่องว่าง':<12}{'top-1 แม่น':>12}{'n':>8}",
        ]
        seen = []
        for key in order:
            if key not in self.buckets:
                continue
            h, n = self.buckets[key]
            seen.append((key, h / n if n else 0.0, n))
            lines.append(f"  {key:<12}{h / n if n else 0:>12.3f}{n:>8}")
        if len(seen) >= 2:
            first, last = seen[0], seen[-1]
            better = last[1] > first[1]
            lines += [
                "",
                f"  ช่องว่างมาก ({last[0]}) แม่นกว่าช่องว่างน้อย ({first[0]}) หรือไม่: "
                + ("ใช่ — คะแนนบอกความมั่นใจได้" if better
                   else "ไม่ — คะแนนยังบอกความมั่นใจไม่ได้"),
            ]
        return "\n".join(lines)
