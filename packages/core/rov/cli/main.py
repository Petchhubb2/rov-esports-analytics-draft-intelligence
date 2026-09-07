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


def _load_series(tournament: str, live: bool = False):
    from rov.draft.importer.crawl import crawl_tournament
    from rov.draft.importer.liquipedia import LiquipediaClient

    c = LiquipediaClient()
    res = crawl_tournament(c, tournament, dry_run=not live)
    if not res.series:
        typer.secho(
            f"ไม่มีข้อมูลของ {tournament} ใน cache — รัน "
            f'rov draft import "{tournament}" --live ก่อน',
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    return c, res


@draft_app.command("stats")
def draft_stats(
    tournament: str = typer.Argument("RoV Pro League/2026/Summer"),
    top: int = typer.Option(20),
) -> None:
    """สถิติฮีโร่จากข้อมูล draft จริง — pick, ban, win rate พร้อม shrinkage"""
    from rov.draft.stats import compute_stats, report

    _, res = _load_series(tournament)
    typer.echo(report(compute_stats(res.series), top=top))


@draft_app.command("heroes-init")
def draft_heroes_init(
    tournament: str = typer.Argument("RoV Pro League/2026/Summer"),
    out: str = typer.Option("configs/draft/heroes.yaml"),
    live: bool = typer.Option(False, "--live", help="ยิง request จริงเพื่อดึง class"),
    patch: str = typer.Option("1.63"),
) -> None:
    """สร้างหรืออัปเดตไฟล์ฮีโร่จากข้อมูลจริง

    เติมเฉพาะ id, name_en, hero_class ซึ่งตรวจสอบได้
    ค่าเชิงคุณภาพต้องให้คนกรอก ระบบไม่เดาให้
    รันซ้ำได้โดยไม่ทับค่าที่กรอกไว้แล้ว
    """
    from pathlib import Path as _P

    from rov.draft.heroes import HeroDB
    from rov.draft.importer.heroinfo import fetch_hero_classes, parse_hero_classes
    from rov.draft.seed import seed_hero_db
    from rov.draft.stats import compute_stats

    c, res = _load_series(tournament, live=live)
    stats = compute_stats(res.series)

    try:
        if live:
            info, _ = fetch_hero_classes(c)
        else:
            cached = c.cache.get(
                "https://liquipedia.net/honorofkings/api.php",
                {
                    "action": "query", "prop": "revisions", "rvprop": "content",
                    "rvslots": "main", "titles": "Portal:Heroes/Arena of Valor",
                    "format": "json", "formatversion": "2",
                },
            )
            if cached is None:
                typer.secho(
                    "ยังไม่มีข้อมูล class ใน cache — ใส่ --live เพื่อดึง (1 request)",
                    fg=typer.colors.YELLOW,
                )
                info = {}
            else:
                import json as _json

                pages = _json.loads(cached.body)["query"]["pages"]
                text = pages[0]["revisions"][0]["slots"]["main"]["content"]
                info, _ = parse_hero_classes(text)
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"ดึงข้อมูล class ไม่สำเร็จ: {exc}", fg=typer.colors.YELLOW)
        info = {}

    existing = HeroDB.load(out) if _P(out).exists() else None
    db, result = seed_hero_db(stats, info, existing=existing, patch=patch)
    db.save(out)

    typer.echo(result.report())
    cs = db.completeness()
    typer.echo("")
    typer.secho(
        f"กรอกครบแล้ว {cs['complete']}/{cs['total']} ({cs['fraction']:.0%})",
        fg=typer.colors.GREEN if cs["fraction"] > 0.5 else typer.colors.YELLOW,
    )
    typer.echo(f"เขียนไฟล์ {out}")
    typer.echo("ดูว่าต้องกรอกอะไรต่อด้วย rov draft todo")


@draft_app.command("todo")
def draft_todo(
    tournament: str = typer.Argument("RoV Pro League/2026/Summer"),
    heroes: str = typer.Option("configs/draft/heroes.yaml"),
    limit: int = typer.Option(15),
) -> None:
    """ฮีโร่ที่ยังต้องกรอก attribute เรียงตามความสำคัญในเมตาจริง"""
    from rov.draft.heroes import HeroDB
    from rov.draft.stats import compute_stats, hero_priority_order

    db = HeroDB.load(heroes)
    _, res = _load_series(tournament)
    stats = compute_stats(res.series)
    order = [hid for hid, _, _ in hero_priority_order(stats)]

    cs = db.completeness()
    typer.echo(f"กรอกครบแล้ว {cs['complete']}/{cs['total']} ({cs['fraction']:.0%})")
    pending = db.todo(priority=order, limit=limit)
    if not pending:
        typer.secho("\nกรอกครบทุกตัวแล้ว", fg=typer.colors.GREEN)
        return

    typer.echo(f"\n{limit} ตัวถัดไปที่ควรกรอก (เรียงตาม pick + ban จริง)\n")
    for i, h in enumerate(pending, 1):
        pres = stats.presence_rate(h.id)
        miss = h.missing_fields()
        cls = ",".join(c.value for c in h.hero_class) or "ไม่รู้ class"
        typer.echo(f"  {i:>2}. {h.id:<16} presence {pres:>4.0%}  [{cls}]")
        typer.echo(f"      ขาด {len(miss)} ช่อง: {', '.join(miss[:6])}"
                   + (" ..." if len(miss) > 6 else ""))


@draft_app.command("comp")
def draft_comp(
    team: str = typer.Argument(..., help="ฮีโร่ 5 ตัว คั่นด้วยจุลภาค"),
    enemy: str = typer.Option(None, help="ทีมตรงข้าม 5 ตัว"),
    heroes: str = typer.Option("configs/draft/heroes.yaml"),
) -> None:
    """วิเคราะห์ composition ของทีม"""
    from rov.draft.composition import IncompleteDataError, analyze, compare
    from rov.draft.heroes import HeroDB

    db = HeroDB.load(heroes)

    def build(spec: str):
        ids = [x.strip() for x in spec.split(",") if x.strip()]
        try:
            return [db.require(i) for i in ids]
        except KeyError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(1) from exc

    try:
        ours = analyze(build(team))
        typer.echo(ours.report())
        if enemy:
            theirs = analyze(build(enemy))
            typer.echo("")
            typer.echo(theirs.report())
            typer.echo("")
            typer.echo(compare(ours, theirs))
    except IncompleteDataError as exc:
        typer.secho(f"\n{exc}", fg=typer.colors.YELLOW)
        raise typer.Exit(1) from exc


# รายการแข่งที่ดึงข้อมูลไว้แล้ว — เพิ่มได้เมื่อ import รายการใหม่
KNOWN_TOURNAMENTS: list[tuple[str, str, str]] = [
    ("TH", "RoV Pro League/2026/Summer", "RPL 2026 Summer (ไทย)"),
    ("TH", "RoV Pro League/2026/Winter", "RPL 2026 Winter (ไทย)"),
    ("TH", "RoV Pro League/2025/Winter", "RPL 2025 Winter (ไทย)"),
    ("TW", "Garena Challenger Series/2026/Spring", "GCS 2026 Spring (ไต้หวัน)"),
    ("TW", "Garena Challenger Series/2026/Summer", "GCS 2026 Summer (ไต้หวัน)"),
]


def _regions(only: str | None = None):
    """โหลดทุกรายการที่อยู่ใน cache แล้วจัดเป็น Region"""
    from rov.draft.importer.crawl import crawl_tournament
    from rov.draft.importer.liquipedia import LiquipediaClient
    from rov.draft.meta import Region

    c = LiquipediaClient()
    out = []
    for key, page, label in KNOWN_TOURNAMENTS:
        if only and only.upper() != key:
            continue
        res = crawl_tournament(c, page, dry_run=True)
        if res.series:
            out.append(Region(key=key, label=label, series=res.series))
    return out


@draft_app.command("meta")
def draft_meta(
    a: str = typer.Option("TH", help="ภูมิภาคฝั่งซ้าย"),
    b: str = typer.Option("TW", help="ภูมิภาคฝั่งขวา"),
    top: int = typer.Option(15),
) -> None:
    """เทียบเมต้าระหว่างภูมิภาค — ฮีโร่ตัวไหนนิยมต่างกัน"""
    from rov.draft.meta import Region, compare_report, region_summary

    regions = _regions()
    if not regions:
        typer.secho("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(region_summary(regions))
    typer.echo("")

    def merge(key: str) -> Region | None:
        parts = [r for r in regions if r.key == key.upper()]
        if not parts:
            return None
        merged = Region(key=key.upper(), label=f"{key.upper()} รวม {len(parts)} รายการ")
        for p in parts:
            merged.series.extend(p.series)
        return merged

    ra, rb = merge(a), merge(b)
    if ra is None or rb is None:
        typer.secho(f"ไม่มีข้อมูลของ {a if ra is None else b}", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.echo(compare_report(ra, rb, top=top))


@draft_app.command("counters")
def draft_counters(
    hero: str = typer.Argument(..., help="ชื่อฮีโร่ เช่น sinestrea"),
    min_games: int = typer.Option(10, help="จำนวนเกมขั้นต่ำของคู่ที่จะแสดง"),
    region: str = typer.Option(None, help="จำกัดเฉพาะภูมิภาค TH หรือ TW"),
) -> None:
    """ตัวแก้ของฮีโร่ — คู่ที่ได้เปรียบและเสียเปรียบ จากข้อมูลรวมทุกลีก"""
    from rov.draft.importer.parser import normalize_hero_id
    from rov.draft.meta import counter_report, pool

    regions = _regions(region)
    if not regions:
        typer.secho("ยังไม่มีข้อมูลใน cache", fg=typer.colors.RED)
        raise typer.Exit(1)

    pooled = pool(regions)
    hid = normalize_hero_id(hero)
    if hid not in pooled.stats.heroes:
        typer.secho(f"ไม่พบฮีโร่ {hid} ในข้อมูล", fg=typer.colors.RED)
        near = [h for h in pooled.stats.heroes if hid[:4] in h]
        if near:
            typer.echo("ใกล้เคียง: " + ", ".join(sorted(near)[:8]))
        raise typer.Exit(1)
    typer.echo(counter_report(pooled, hid, min_games=min_games))


@draft_app.command("pool")
def draft_pool(top: int = typer.Option(25)) -> None:
    """สถิติรวมทุกลีกทุกฤดูกาลที่ดึงมาแล้ว"""
    from rov.draft.meta import pool, region_summary
    from rov.draft.stats import report

    regions = _regions()
    if not regions:
        typer.secho("ยังไม่มีข้อมูลใน cache", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.echo(region_summary(regions))
    typer.echo("")
    pooled = pool(regions)
    typer.echo(report(pooled.stats, top=top))
    typer.echo(f"\nคู่ matchup ที่มีข้อมูล {len(pooled.matchups):,} คู่")
    enough = sum(1 for m in pooled.matchups.values() if m.games >= 10)
    typer.echo(f"คู่ที่มีอย่างน้อย 10 เกม {enough:,} คู่")


@draft_app.command("sim")
def draft_sim(
    blue: str = typer.Option("BLUE", help="ชื่อทีมฝั่งน้ำเงิน"),
    red: str = typer.Option("RED", help="ชื่อทีมฝั่งแดง"),
    fmt: str = typer.Option("configs/draft/format.yaml"),
    region: str = typer.Option(None, help="ใช้ข้อมูลเฉพาะ TH หรือ TW"),
    min_games: int = typer.Option(5, help="ฮีโร่ต้องมีอย่างน้อยกี่เกมจึงจะแนะนำ"),
    top: int = typer.Option(8),
) -> None:
    """Draft Simulator แบบโต้ตอบ พร้อมคำแนะนำจากข้อมูลจริง

    คำสั่งระหว่างเล่น
        <ชื่อฮีโร่>   เลือกหรือแบนตัวนั้น
        ?            ดูคำแนะนำอีกครั้ง
        /undo        ย้อนหนึ่งตา
        /reset       เริ่มใหม่
        /board       ดูกระดาน
        /history     ดูประวัติ
        /find <คำ>   ค้นหาชื่อฮีโร่
        /quit        ออก
    """
    from rov.draft.importer.parser import normalize_hero_id
    from rov.draft.meta import pool
    from rov.draft.recommend import recommend
    from rov.draft.recommend import report as rec_report
    from rov.draft.state import DraftFormat, DraftState, IllegalMove

    regions = _regions(region)
    if not regions:
        typer.secho("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน", fg=typer.colors.RED)
        raise typer.Exit(1)

    pooled = pool(regions)
    fo = DraftFormat.load(fmt)
    state = DraftState(
        fmt=fo, pool=set(pooled.stats.heroes), blue_name=blue, red_name=red
    )

    typer.echo(f"ข้อมูล {pooled.total_games} เกม จาก {len(pooled.sources)} รายการ")
    typer.echo(f"ฮีโร่ที่เลือกได้ {len(state.pool)} ตัว · format {fo.id}")
    if not fo.verified:
        typer.secho(
            "⚠ ลำดับ ban/pick ยังไม่ได้ยืนยันกับ rulebook จริง "
            "แก้ได้ที่ configs/draft/format.yaml",
            fg=typer.colors.YELLOW,
        )
    typer.echo("พิมพ์ ? เพื่อดูคำแนะนำ · /quit เพื่อออก\n")

    def show_recs() -> None:
        sugs = recommend(state, pooled, limit=top, min_games=min_games)
        if not sugs:
            typer.echo("  (ไม่มีตัวเลือกที่มีข้อมูลพอ)")
        else:
            typer.echo(rec_report(sugs, state, top=top))

    while not state.complete:
        typer.echo("")
        typer.secho(state.prompt(), fg=typer.colors.CYAN, bold=True)
        show_recs()
        try:
            raw = typer.prompt("\n> ", prompt_suffix="").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nออกแล้ว")
            return
        if not raw:
            continue

        low = raw.lower()
        if low in ("/quit", "/q", "/exit"):
            typer.echo("ออกแล้ว")
            return
        if low == "?":
            continue
        if low == "/undo":
            mv = state.undo()
            typer.echo(f"ย้อน {mv.hero_id}" if mv else "ไม่มีอะไรให้ย้อน")
            continue
        if low == "/reset":
            state.reset()
            typer.echo("เริ่มใหม่แล้ว")
            continue
        if low == "/board":
            typer.echo(state.board())
            continue
        if low == "/history":
            typer.echo(state.history())
            continue
        if low.startswith("/find"):
            q = normalize_hero_id(raw[5:])
            hits = sorted(h for h in state.legal_moves() if q in h)
            typer.echo("  " + (", ".join(hits[:30]) if hits else "ไม่พบ"))
            continue

        hid = normalize_hero_id(raw)
        try:
            mv = state.apply(hid)
        except IllegalMove as exc:
            typer.secho(f"  {exc}", fg=typer.colors.RED)
            near = sorted(h for h in state.legal_moves() if hid[:3] and hid[:3] in h)
            if near:
                typer.echo("  ใกล้เคียง: " + ", ".join(near[:10]))
            continue
        typer.secho(
            f"  {state.team_name(mv.turn.team_enum)} {mv.turn.action.value} {mv.hero_id}",
            fg=typer.colors.GREEN,
        )

    typer.echo("")
    typer.secho("═══ draft เสร็จสมบูรณ์ ═══", bold=True)
    typer.echo(state.board())
    typer.echo("")
    typer.echo(state.history())


@draft_app.command("cache")
def draft_cache() -> None:
    """ดูขนาดของ cache"""
    from rov.draft.importer.cache import ResponseCache

    st = ResponseCache().stats()
    typer.echo(f"  ไฟล์   {st['entries']}")
    typer.echo(f"  ขนาด   {st['bytes'] / 1024:.0f} KB")
    typer.echo(f"  ที่อยู่  {st['root']}")


# --------------------------------------------------------------- assets


assets_app = typer.Typer(help="ภาพประกอบ (hero icon, zone map)", no_args_is_help=True)
app.add_typer(assets_app, name="assets")


@assets_app.command("heroes")
def assets_heroes(
    out: str = typer.Option("data/assets/heroes"),
    meta_only: bool = typer.Option(
        False, "--meta-only", help="ดึงเฉพาะ URL ไม่ดาวน์โหลดไฟล์"
    ),
) -> None:
    """ดาวน์โหลดภาพฮีโร่จาก Liquipedia Commons

    เคารพกติกา 1 request ต่อ 2 วินาที ไฟล์ที่มีอยู่แล้วจะถูกข้าม
    อ่านเรื่องลิขสิทธิ์ที่ data/assets/heroes/ATTRIBUTION.md ก่อนนำไปเผยแพร่
    """
    from rov.draft.importer.assets import (
        download_hero_icons,
        hero_image_titles,
        resolve_urls,
    )
    from rov.draft.importer.liquipedia import LiquipediaClient

    c = LiquipediaClient()
    if meta_only:
        titles = hero_image_titles(c)
        urls = resolve_urls(c, sorted(set(titles.values())))
        typer.echo(f"ฮีโร่ {len(titles)} ตัว · หา URL ได้ {len(urls)}")
        return

    typer.echo("กำลังดาวน์โหลด — หน่วง 2 วินาทีต่อไฟล์ตามกติกาของ Liquipedia")
    res = download_hero_icons(c, out_dir=out)
    typer.echo(res.report())
    typer.secho(
        f"\nอ่าน {out}/ATTRIBUTION.md ก่อนนำภาพไปเผยแพร่สาธารณะ",
        fg=typer.colors.YELLOW,
    )


@assets_app.command("zone-map")
def assets_zone_map(
    zones_file: str = typer.Option("configs/zones/rov_map_v1.yaml"),
    out: str = typer.Option("data/exports/zone_map.png"),
) -> None:
    """วาดภาพ zone map จาก config — เป็นภาพของเราเอง ไม่ติดลิขสิทธิ์ใคร"""
    import json

    import cv2
    import numpy as np

    from rov.config.zones import RASTER_SIZE, ZoneMap

    kind_color = {
        "base": (86, 62, 40), "lane": (96, 122, 88), "jungle": (40, 66, 34),
        "river": (128, 92, 44), "approach": (58, 104, 128), "objective": (44, 140, 196),
    }
    zm = ZoneMap.load(zones_file)
    zm.build()
    raster = zm._raster
    img = np.full((RASTER_SIZE, RASTER_SIZE, 3), (26, 22, 18), np.uint8)
    meta = []
    for i, z in enumerate(zm.zones, start=1):
        img[raster == i] = kind_color.get(z.kind, (90, 90, 90))
        ys, xs = np.nonzero(raster == i)
        if len(xs):
            meta.append({
                "id": z.id, "kind": z.kind, "region": z.region,
                "cx": round(float(xs.mean()) / RASTER_SIZE, 4),
                "cy": round(float(ys.mean()) / RASTER_SIZE, 4),
            })
    img[cv2.Canny((raster % 251).astype(np.uint8), 1, 1) > 0] = (150, 165, 175)

    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), img)
    p.with_name("zone_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    typer.echo(f"เขียน {p} · {len(meta)} zone · ครอบคลุม {zm.coverage_fraction():.1%}")


@assets_app.command("status")
def assets_status(out: str = typer.Option("data/assets/heroes")) -> None:
    """ดูว่ามีภาพอะไรอยู่แล้วบ้าง"""
    d = Path(out)
    files = sorted(p for p in d.glob("*") if p.suffix.lower() in (".jpg", ".png"))
    total = sum(p.stat().st_size for p in files)
    typer.echo(f"ภาพฮีโร่   {len(files)} ไฟล์ · {total / 1024:.0f} KB · {d}")
    zm = Path("data/exports/zone_map.png")
    typer.echo(f"zone map  {'มี' if zm.exists() else 'ยังไม่มี'} · {zm}")
    if not (d / "ATTRIBUTION.md").exists() and files:
        typer.secho("ไม่พบ ATTRIBUTION.md", fg=typer.colors.YELLOW)


@app.command("web")
def web(
    port: int = typer.Option(8000),
    root: str = typer.Option("data/exports", help="โฟลเดอร์ที่จะเสิร์ฟ"),
) -> None:
    """เปิดหน้าเว็บ draft ในเครื่อง

    ต้องสร้างไฟล์ก่อนด้วย
        python scripts/export_draft_data.py
        python scripts/build_draft_page.py
    """
    import functools
    import http.server
    import socketserver

    d = Path(root)
    page = d / "draft_board.html"
    if not page.exists():
        typer.secho(f"ยังไม่มี {page}", fg=typer.colors.RED)
        typer.echo("รัน scripts/export_draft_data.py แล้ว scripts/build_draft_page.py ก่อน")
        raise typer.Exit(1)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(d))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as srv:
        url = f"http://127.0.0.1:{port}/draft_board.html"
        typer.secho(f"เปิดที่ {url}", fg=typer.colors.GREEN)
        typer.echo("กด Ctrl+C เพื่อหยุด")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            typer.echo("\nหยุดแล้ว")


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
