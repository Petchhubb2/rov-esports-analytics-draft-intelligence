"""ประเมิน detector เทียบ ground truth

หลัก P5 — วัดก่อนปรับ ห้ามแก้ threshold โดยไม่มีตัวเลขก่อน/หลัง

รายงานแยกกรณี occluded เสมอ ถ้ารวมกัน ตัวเลขจะดูดีเกินจริง
เพราะกรณียากมีสัดส่วนน้อยแต่สำคัญที่สุด (แผนเดิม §77)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from rov.domain.enums import Team
from rov.domain.geometry import Point


@dataclass(slots=True)
class GTIcon:
    point: Point
    team: Team = Team.UNKNOWN
    occluded: bool = False
    slot: int | None = None


@dataclass(slots=True)
class DetPoint:
    point: Point
    team: Team = Team.UNKNOWN
    conf: float = 0.0


@dataclass
class DetectionMetrics:
    n_gt: int = 0
    n_pred: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    # แยกตามความยาก
    gt_clear: int = 0
    tp_clear: int = 0
    gt_occluded: int = 0
    tp_occluded: int = 0
    # ความแม่นของตำแหน่ง
    errors: list[float] = field(default_factory=list)
    # ความถูกต้องของการระบุทีม
    team_correct: int = 0
    team_total: int = 0
    n_frames: int = 0

    # ------------------------------------------------------------------

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def recall_clear(self) -> float:
        return self.tp_clear / self.gt_clear if self.gt_clear else 0.0

    @property
    def recall_occluded(self) -> float:
        return self.tp_occluded / self.gt_occluded if self.gt_occluded else 0.0

    @property
    def mean_error(self) -> float:
        return float(np.mean(self.errors)) if self.errors else float("nan")

    @property
    def p95_error(self) -> float:
        return float(np.percentile(self.errors, 95)) if self.errors else float("nan")

    @property
    def team_accuracy(self) -> float:
        return self.team_correct / self.team_total if self.team_total else 0.0

    @property
    def occluded_fraction(self) -> float:
        return self.gt_occluded / self.n_gt if self.n_gt else 0.0

    def gates(self) -> dict[str, tuple[float, float, bool]]:
        """เกณฑ์ผ่าน Milestone 1 (docs/04-vision-pipeline.md §7)

        คืน {ชื่อ: (ค่าที่วัดได้, เกณฑ์, ผ่านหรือไม่)}
        """
        return {
            "precision": (self.precision, 0.95, self.precision >= 0.95),
            "recall_clear": (self.recall_clear, 0.95, self.recall_clear >= 0.95),
            "recall_occluded": (self.recall_occluded, 0.70, self.recall_occluded >= 0.70),
            "mean_error": (self.mean_error, 0.008, self.mean_error <= 0.008),
        }

    @property
    def passed(self) -> bool:
        return all(ok for _, _, ok in self.gates().values())

    def report(self) -> str:
        lines = [
            "═══ Detection Metrics ═══",
            f"เฟรมที่ประเมิน       {self.n_frames}",
            f"ground truth        {self.n_gt}   (occluded {self.gt_occluded}"
            f" = {self.occluded_fraction:.0%})",
            f"detection ที่ได้     {self.n_pred}",
            "",
            f"precision           {self.precision:.4f}",
            f"recall (รวม)        {self.recall:.4f}",
            f"recall (ไม่ทับ)      {self.recall_clear:.4f}   [{self.tp_clear}/{self.gt_clear}]",
            f"recall (ทับกัน)      {self.recall_occluded:.4f}   "
            f"[{self.tp_occluded}/{self.gt_occluded}]",
            f"F1                  {self.f1:.4f}",
            "",
            f"mean position error {self.mean_error:.5f}  (normalized)",
            f"p95  position error {self.p95_error:.5f}",
            f"team accuracy       {self.team_accuracy:.4f}",
            "",
            "─── เกณฑ์ผ่าน Milestone 1 ───",
        ]
        for name, (val, thr, ok) in self.gates().items():
            mark = "✓ ผ่าน" if ok else "✗ ไม่ผ่าน"
            cmp = "≤" if "error" in name else "≥"
            lines.append(f"  {mark}  {name:<18} {val:.5f}  ({cmp} {thr})")
        lines.append("")
        lines.append("ผลรวม: " + ("ผ่านทุกเกณฑ์" if self.passed else "ยังไม่ผ่าน"))
        return "\n".join(lines)


def match_frame(
    gt: list[GTIcon],
    pred: list[DetPoint],
    max_dist: float,
    metrics: DetectionMetrics,
) -> None:
    """จับคู่แบบ optimal (Hungarian) ไม่ใช่ greedy

    greedy ให้ผลที่ขึ้นกับลำดับของ input ทำให้ตัวเลขเทียบข้ามครั้งไม่ได้
    """
    metrics.n_frames += 1
    metrics.n_gt += len(gt)
    metrics.n_pred += len(pred)
    for g in gt:
        if g.occluded:
            metrics.gt_occluded += 1
        else:
            metrics.gt_clear += 1

    if not gt or not pred:
        metrics.fn += len(gt)
        metrics.fp += len(pred)
        return

    cost = np.full((len(gt), len(pred)), 1e6, dtype=np.float64)
    for i, g in enumerate(gt):
        for j, p in enumerate(pred):
            d = g.point.dist(p.point)
            if d <= max_dist:
                cost[i, j] = d

    rows, cols = linear_sum_assignment(cost)
    matched_gt: set[int] = set()
    matched_pred: set[int] = set()

    for i, j in zip(rows, cols, strict=True):
        if cost[i, j] >= 1e6:
            continue
        matched_gt.add(i)
        matched_pred.add(j)
        metrics.tp += 1
        metrics.errors.append(float(cost[i, j]))
        if gt[i].occluded:
            metrics.tp_occluded += 1
        else:
            metrics.tp_clear += 1
        if gt[i].team is not Team.UNKNOWN and pred[j].team is not Team.UNKNOWN:
            metrics.team_total += 1
            if gt[i].team is pred[j].team:
                metrics.team_correct += 1

    metrics.fn += len(gt) - len(matched_gt)
    metrics.fp += len(pred) - len(matched_pred)


def evaluate(
    frames: list[tuple[list[GTIcon], list[DetPoint]]],
    max_dist: float = 0.02,
) -> DetectionMetrics:
    m = DetectionMetrics()
    for gt, pred in frames:
        match_frame(gt, pred, max_dist, m)
    return m
