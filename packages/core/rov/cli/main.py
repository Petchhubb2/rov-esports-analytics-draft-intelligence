"""rov — command line ของระบบ

CLI คือหน้าตาหลักของระบบตลอด Phase 0-4 ไม่ใช่หน้าเว็บ
ดู docs/02-architecture.md §3
"""

from __future__ import annotations

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


# --------------------------------------------------------------- System 01


ingest_app = typer.Typer(help="System 01 — Video Ingestion", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")


@ingest_app.command("init-db")
def ingest_init_db() -> None:
    """สร้างตารางในฐานข้อมูล (ใช้ตอน dev — production ใช้ alembic)"""
    from rov.store.db import create_all, database_url, ping

    if not ping():
        typer.secho(f"ต่อฐานข้อมูลไม่ได้: {database_url()}", fg=typer.colors.RED)
        typer.echo("ตรวจว่า PostgreSQL รันอยู่ และตั้ง ROV_DATABASE_URL ถูกต้อง")
        raise typer.Exit(1)
    create_all()
    typer.secho(f"สร้างตารางแล้วที่ {database_url()}", fg=typer.colors.GREEN)


@ingest_app.command("add")
def ingest_add(
    path: str,
    title: str = typer.Option(None, help="ชื่อแมตช์"),
    match_id: str = typer.Option(None, help="เพิ่มวิดีโอเข้าแมตช์ที่มีอยู่แล้ว"),
) -> None:
    """รับไฟล์วิดีโอเข้าระบบ แล้วสร้าง Match, Video, ProcessingJob"""
    from rov.ingest.service import IngestError, ingest_video
    from rov.store.db import session_scope

    try:
        with session_scope() as s:
            r = ingest_video(s, path, title=title, match_id=match_id)
    except IngestError as exc:
        typer.secho(f"รับไฟล์ไม่ได้: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc

    typer.echo(r.meta.summary())
    typer.echo("")
    typer.echo(f"  match_id  {r.match_id}")
    typer.echo(f"  video_id  {r.video_id}")
    typer.echo(f"  job_id    {r.job_id}")
    for w in r.warnings:
        typer.secho(f"  ⚠ {w}", fg=typer.colors.YELLOW)


@ingest_app.command("job")
def ingest_job(job_id: str) -> None:
    """ดูสถานะของ processing job"""
    from rov.ingest.service import IngestError, job_state
    from rov.store.db import session_scope

    try:
        with session_scope() as s:
            st = job_state(s, job_id)
    except IngestError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    for k, v in st.items():
        typer.echo(f"  {k:<12} {v}")


@ingest_app.command("list")
def ingest_list(limit: int = 20) -> None:
    """รายการแมตช์ล่าสุด"""
    from rov.store.db import session_scope
    from rov.store.repo import MatchRepo, VideoRepo

    with session_scope() as s:
        matches = MatchRepo(s).list(limit=limit)
        if not matches:
            typer.echo("ยังไม่มีแมตช์ในระบบ")
            return
        for m in matches:
            vids = VideoRepo(s).by_match(m.id)
            res = vids[0].resolution if vids else "-"
            typer.echo(f"  {m.id[:8]}  {res:<10} {m.title or '(ไม่มีชื่อ)'}")


# --------------------------------------------------------------- Draft import


draft_app = typer.Typer(help="Draft Intelligence", no_args_is_help=True)
app.add_typer(draft_app, name="draft")


@draft_app.command("plan")
def draft_plan(tournaments: int = 10, pages_each: int = 3) -> None:
    """ประมาณเวลาที่ต้องใช้ดึงข้อมูลก่อนเริ่มจริง

    ต้องรันก่อนงานดึงยาวเสมอ เพราะ Liquipedia จำกัด 60 requests ต่อชั่วโมง
    """
    from rov.draft.importer.liquipedia import LiquipediaClient

    c = LiquipediaClient()
    n = tournaments * (1 + pages_each)
    p = c.plan(n)
    typer.echo(f"  รายการแข่ง        {tournaments}")
    typer.echo(f"  หน้าต่อรายการ      {1 + pages_each}")
    typer.echo(f"  request รวม       {p['requests']}")
    typer.echo(f"  เวลาโดยประมาณ     {p['estimated_hours']} ชั่วโมง")
    typer.echo(f"  โควตาเหลือชั่วโมงนี้ {p['remaining_this_hour']}")
    typer.echo("")
    typer.echo("หนึ่งหน้า Group Stage ให้ข้อมูลราว 270 เกม จึงไม่ต้องดึงทีละแมตช์")


@draft_app.command("import")
def draft_import(
    tournament: str = typer.Argument(
        ..., help='เช่น "RoV Pro League/2026/Summer"'
    ),
    live: bool = typer.Option(
        False, "--live", help="ยิง request จริง (ค่าเริ่มต้นใช้เฉพาะ cache)"
    ),
    max_pages: int = typer.Option(8),
) -> None:
    """ดึงข้อมูล draft ของรายการแข่งหนึ่งรายการ"""
    from rov.draft.importer.crawl import crawl_tournament
    from rov.draft.importer.liquipedia import LiquipediaClient
    from rov.draft.importer.parser import summarize

    c = LiquipediaClient()
    if not live:
        typer.secho(
            "โหมด cache เท่านั้น — ใส่ --live เพื่อยิง request จริง",
            fg=typer.colors.YELLOW,
        )

    res = crawl_tournament(c, tournament, max_pages=max_pages, dry_run=not live)

    typer.echo(f"\nหน้าที่ดึงมา   {len(res.pages_fetched)}")
    for p in res.pages_fetched:
        typer.echo(f"    ✓ {p}")
    for p in res.pages_skipped:
        typer.echo(f"    · ข้าม (ไม่มีใน cache) {p}")
    for p, err in res.pages_failed:
        typer.secho(f"    ✗ {p}: {err}", fg=typer.colors.RED)

    if res.series:
        typer.echo("")
        typer.echo(summarize(res.series).report())
    typer.echo(f"\nสถิติ client: {c.stats.as_dict()}")
    typer.echo(f"โควตาเหลือชั่วโมงนี้: {c.limiter.remaining_this_hour}")


@draft_app.command("cache")
def draft_cache() -> None:
    """ดูขนาดของ cache"""
    from rov.draft.importer.cache import ResponseCache

    st = ResponseCache().stats()
    typer.echo(f"  ไฟล์   {st['entries']}")
    typer.echo(f"  ขนาด   {st['bytes'] / 1024:.0f} KB")
    typer.echo(f"  ที่อยู่  {st['root']}")


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
    layout_dir = Path("configs/layouts")
    layouts = sorted(layout_dir.glob("*.yaml")) if layout_dir.exists() else []
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
    from rov.store.db import ping

    db_ok = ping()
    layouts = Path("configs/layouts")
    has_layout = layouts.exists() and any(layouts.glob("*.yaml"))
    cache = Path("data/cache/liquipedia")
    has_draft_data = cache.exists() and any(cache.rglob("*.json.gz"))

    items = [
        ("01 Video Ingestion", db_ok, "probe/sampler + DB + API + queue" if db_ok
         else "โค้ดพร้อม แต่ต่อฐานข้อมูลไม่ได้"),
        ("02 Broadcast Parser", False, "มีแค่สคีมา ROI ยังไม่มีตัวอ่าน HUD/นาฬิกา"),
        ("03 Minimap Vision", True, "ผ่านเกณฑ์บนชุดสังเคราะห์ ยังไม่ทดสอบคลิปจริง"),
        ("04 Hero Identification", False, "ยังไม่เริ่ม"),
        ("05 Player Identity", False, "มีแค่ชนิดข้อมูล"),
        ("06 Player Tracking", False, "ยังไม่เริ่ม"),
        ("07 Map Calibration", has_layout, "ต้องมีคลิปจริงก่อน" if not has_layout else ""),
        ("08 Map / Zone Engine", True, "raster lookup O(1) พร้อม"),
        ("09 Ground Truth", False, "มีตัวกำเนิด GT แต่ยังไม่มีเครื่องมือ label"),
        ("10 Event Detection", False, "ยังไม่เริ่ม"),
        ("11-14 Macro/Player/Team Analytics", False, "ยังไม่เริ่ม"),
        ("15-26 Draft Engines", False, "ยังไม่เริ่ม"),
        ("— Draft Data Import", has_draft_data,
         "ดึงจาก Liquipedia ได้แล้ว" if has_draft_data else "ยังไม่ได้ดึงข้อมูล"),
        ("27-32 Macro Planner", False, "ออกแบบไว้ใน docs/11 ยังไม่เขียนโค้ด"),
        ("33 Scouting", False, "ยังไม่เริ่ม"),
        ("34 Prediction / ML", False, "ห้ามเริ่มก่อนมี ground truth"),
        ("39 Processing Queue", db_ok, "jobs table + SKIP LOCKED"),
        ("40-41 API / Database", db_ok, "ครอบคลุมเฉพาะ System 01"),
        ("42-43 Dashboard / Replay", False, "ยังไม่เริ่ม"),
        ("44 Testing / Evaluation", True, "87 เทสต์"),
    ]
    for name, done, note in items:
        mark = "✓" if done else "·"
        col = typer.colors.GREEN if done else None
        typer.secho(f"  {mark} {name:<28} {note}", fg=col)


if __name__ == "__main__":
    app()
