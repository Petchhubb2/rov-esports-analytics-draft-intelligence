"""rov — command line ของระบบ

CLI คือหน้าตาหลักของระบบตลอด Phase 0-4 ไม่ใช่หน้าเว็บ
ดู docs/02-architecture.md §3
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from rov.cli.console import setup_console

app = typer.Typer(
    add_completion=False,
    help="RoV Esports Analytics & Draft Intelligence",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    setup_console()


# --------------------------------------------------------------- Phase 0


@app.command()
def probe(path: str) -> None:
    """อ่าน metadata ของไฟล์วิดีโอ"""
    from rov.ingest.probe import probe as do_probe

    meta = do_probe(path)
    typer.echo(meta.summary())
    typer.echo("")
    for k, v in meta.to_dict().items():
        typer.echo(f"  {k:<16} {v}")
    if meta.variable_fps:
        typer.echo("")
        typer.echo(
            "⚠  คลิปนี้เป็น variable frame rate — ห้ามคำนวณเวลาจาก frame_index/fps"
        )


@app.command("layout-check")
def layout_check(
    layout: str = typer.Argument(..., help="ไฟล์ configs/layouts/<id>.yaml"),
    video: str = typer.Option(None, help="วาดกรอบ ROI ทับเฟรมจากคลิปนี้"),
    out: str = typer.Option("data/exports/layout_check", help="โฟลเดอร์ปลายทาง"),
    n: int = typer.Option(10, help="จำนวนเฟรมที่จะตรวจ"),
) -> None:
    """ตรวจ layout config และวาดกรอบ ROI ทับเฟรมจริงเพื่อยืนยันด้วยตา

    เกณฑ์ผ่าน Phase 0 คือกรอบต้องอยู่ตรงตำแหน่งครบทุกเฟรมที่สุ่มมา
    """
    from rov.config.layout import Layout

    lay = Layout.load(layout)
    typer.echo(f"layout      {lay.id}")
    typer.echo(f"ความละเอียด  {lay.source_resolution[0]}x{lay.source_resolution[1]}")
    typer.echo(f"minimap ROI {lay.minimap.roi.model_dump()}")

    missing = lay.unanswered_phase0
    if missing:
        typer.echo("")
        typer.secho("คำถาม Phase 0 ที่ยังไม่มีคำตอบ:", fg=typer.colors.YELLOW)
        for m in missing:
            typer.echo(f"  · {m}")
        typer.echo("")
        typer.echo("ห้ามรัน pipeline จนกว่าจะตอบครบ การเดาคำตอบทำให้ผลผิดแบบเงียบ ๆ")
    else:
        typer.secho("ตอบคำถาม Phase 0 ครบแล้ว", fg=typer.colors.GREEN)

    if not video:
        return

    import cv2

    from rov.ingest.probe import probe as do_probe
    from rov.ingest.sampler import read_frames_at, spread_times

    meta = do_probe(video)
    lay = lay.scaled_to(meta.width, meta.height)
    times = spread_times(meta.duration, n)
    frames = read_frames_at(video, times)

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    boxes = [("minimap", lay.minimap.roi, (0, 255, 0))]
    if lay.clock:
        boxes.append(("clock", lay.clock.roi, (0, 200, 255)))
    if lay.scoreboard:
        boxes.append(("score", lay.scoreboard, (255, 200, 0)))
    if lay.hud:
        for side in ("left", "right"):
            hs = getattr(lay.hud, side)
            for i in range(hs.slots):
                r = hs.slot_rect(i)
                boxes.append((f"{side[0]}{i}", type(lay.minimap.roi)(
                    x=r.x, y=r.y, w=r.w, h=r.h), (200, 120, 255)))

    for f in frames:
        img = f.image.copy()
        for name, r, col in boxes:
            cv2.rectangle(img, (r.x, r.y), (r.x + r.w, r.y + r.h), col, 2)
            cv2.putText(img, name, (r.x, max(12, r.y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
        cv2.imwrite(str(out_dir / f"t{f.video_time:07.1f}.png"), img)
    typer.echo(f"\nเขียนภาพ {len(frames)} ไฟล์ลง {out_dir}")
    typer.echo("เปิดดูด้วยตา ทุกกรอบต้องตรงตำแหน่งครบทุกภาพจึงจะผ่าน Phase 0")


# --------------------------------------------------------------- zones


@app.command()
def zones(
    path: str = typer.Argument("configs/zones/rov_map_v1.yaml"),
    out: str = typer.Option(None, help="เขียนภาพ zone map ลงไฟล์นี้"),
) -> None:
    """ตรวจไฟล์ zone และรายงานความครอบคลุม"""
    import numpy as np

    from rov.config.zones import RASTER_SIZE, ZoneMap

    zm = ZoneMap.load(path)
    typer.echo(f"zone ทั้งหมด   {len(zm.zones)}")
    typer.echo(f"ครอบคลุมแมพ   {zm.coverage_fraction():.1%}")
    typer.echo("")
    for z in zm.zones:
        typer.echo(f"  {z.id:<24} {z.kind:<10} region={z.region or z.id}")

    slayer_r = zm.region_of("SLAYER_PIT")
    sentinel_r = zm.region_of("SPIRIT_SENTINEL")
    dragon_r = zm.region_of("DRAGON_PIT")
    typer.echo("")
    if slayer_r and sentinel_r and slayer_r == sentinel_r and dragon_r != slayer_r:
        typer.secho(
            "✓ Slayer กับ Sentinel อยู่ครึ่งแม่น้ำเดียวกัน และ Dragon อยู่อีกครึ่ง",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            "✗ ผังไม่ตรงกับเกมจริง — Slayer กับ Spirit Sentinel ต้องอยู่ครึ่งแม่น้ำเดียวกัน",
            fg=typer.colors.RED,
        )

    if out:
        import cv2

        zm.build()
        raster = zm._raster
        rng = np.random.default_rng(1)
        palette = rng.integers(40, 255, (len(zm.zones) + 1, 3), dtype=np.uint8)
        palette[0] = (25, 25, 25)
        img = palette[raster]
        cv2.imwrite(out, img)
        typer.echo(f"\nเขียนภาพ zone ขนาด {RASTER_SIZE}x{RASTER_SIZE} ลง {out}")


# --------------------------------------------------------------- eval


@app.command("eval-synthetic")
def eval_synthetic(
    duration: float = typer.Option(240.0),
    seed: int = typer.Option(0),
    seeds: int = typer.Option(1, help="รันหลาย seed แล้วสรุปรวม"),
) -> None:
    """วัด detector บน minimap สังเคราะห์

    ใช้ระหว่างยังไม่มีคลิปจริง ตรวจว่าอัลกอริทึมถูก
    ไม่ได้ตรวจว่าค่าพารามิเตอร์เหมาะกับคลิปจริง
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
    from eval_synthetic import run_eval  # type: ignore[import-not-found]

    rows = []
    for s in range(seed, seed + seeds):
        m = run_eval(duration=duration, seed=s, quiet=seeds > 1)
        rows.append((s, m))
        if seeds == 1:
            typer.echo(m.report())

    if seeds > 1:
        typer.echo(f"{'seed':<6}{'precision':>11}{'rec_clear':>11}{'rec_occ':>10}{'err':>9}  ผล")
        for s, m in rows:
            mark = "ผ่าน" if m.passed else "ไม่ผ่าน"
            typer.echo(
                f"{s:<6}{m.precision:>11.4f}{m.recall_clear:>11.4f}"
                f"{m.recall_occluded:>10.4f}{m.mean_error:>9.5f}  {mark}"
            )
        n_ok = sum(1 for _, m in rows if m.passed)
        typer.echo(f"\nผ่าน {n_ok} จาก {len(rows)} seed")


# --------------------------------------------------------------- misc


@app.command()
def doctor() -> None:
    """ตรวจว่าเครื่องพร้อมใช้งานหรือไม่"""
    import shutil

    setup_console()
    ok = True

    typer.echo("── ไลบรารี ──")
    for mod, label in [
        ("cv2", "OpenCV"), ("numpy", "NumPy"), ("scipy", "SciPy"),
        ("av", "PyAV"), ("polars", "Polars"), ("pyarrow", "PyArrow"),
        ("pydantic", "Pydantic"), ("yaml", "PyYAML"), ("httpx", "httpx"),
    ]:
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "?")
            typer.echo(f"  ✓ {label:<10} {ver}")
        except ImportError:
            typer.secho(f"  ✗ {label:<10} ไม่พบ", fg=typer.colors.RED)
            ok = False

    typer.echo("\n── โปรแกรมภายนอก ──")
    for exe, why in [("ffmpeg", "ตัดต่อและสร้างคลิปทดสอบ"), ("ffprobe", "ตรวจ metadata")]:
        p = shutil.which(exe)
        if p:
            typer.echo(f"  ✓ {exe:<10} {p}")
        else:
            typer.secho(
                f"  ~ {exe:<10} ไม่พบ ({why}) — PyAV ทำงานแทนได้ในท่อหลัก",
                fg=typer.colors.YELLOW,
            )

    typer.echo("\n── ไฟล์ config ──")
    for f in ["configs/zones/rov_map_v1.yaml"]:
        if Path(f).exists():
            typer.echo(f"  ✓ {f}")
        else:
            typer.secho(f"  ✗ {f} ไม่พบ", fg=typer.colors.RED)
            ok = False
    layouts = list(Path("configs/layouts").glob("*.yaml")) if Path("configs/layouts").exists() else []
    if layouts:
        for lf in layouts:
            typer.echo(f"  ✓ {lf}")
    else:
        typer.secho(
            "  ~ ยังไม่มี configs/layouts/*.yaml — ต้องทำ Phase 0 กับคลิปจริงก่อน",
            fg=typer.colors.YELLOW,
        )

    typer.echo("")
    if ok:
        typer.secho("พร้อมใช้งาน", fg=typer.colors.GREEN)
    else:
        typer.secho("ยังไม่พร้อม ดูรายการที่ขึ้น ✗ ด้านบน", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """สรุปว่าโครงการเดินมาถึงไหนแล้ว เทียบกับ roadmap"""
    setup_console()
    items = [
        ("Phase 0  layout config", Path("configs/layouts").exists()
         and any(Path("configs/layouts").glob("*.yaml")), "ต้องมีคลิปจริงก่อน"),
        ("Phase 0  zone map", Path("configs/zones/rov_map_v1.yaml").exists(),
         "แม่แบบพร้อม ยังไม่ยืนยันกับ minimap จริง"),
        ("Phase 1  detector + eval", True, "ผ่านเกณฑ์บนชุดสังเคราะห์ ยังไม่ทดสอบกับคลิปจริง"),
        ("Phase 2  HUD reader", False, "ยังไม่เริ่ม"),
        ("Phase 2  objective state", False, "ยังไม่เริ่ม"),
        ("Phase 3  tracking", False, "ยังไม่เริ่ม"),
        ("Phase 4  zone mapping", Path("packages/core/rov/config/zones.py").exists(),
         "lookup พร้อม ยังไม่ต่อกับ pipeline"),
        ("Phase 5  event detection", False, "ยังไม่เริ่ม"),
        ("Draft D0 importer", False, "ยังไม่เริ่ม — ควรเริ่มก่อนเพราะ rate limit"),
        ("Draft D1 hero attribute", False, "ยังไม่เริ่ม"),
    ]
    for name, done, note in items:
        mark = "✓" if done else "·"
        col = typer.colors.GREEN if done else None
        typer.secho(f"  {mark} {name:<28} {note}", fg=col)


if __name__ == "__main__":
    app()
