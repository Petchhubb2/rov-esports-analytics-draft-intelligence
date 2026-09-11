# RoV Claude Code Knowledge Kit

ชุดนี้แปลงข้อมูลจาก NotebookLM จำนวน 5 หมวดให้พร้อมใช้เป็นฐานความรู้สำหรับ Claude Code:

- Draft
- Macro
- Hero
- Counter
- Synergy

## โครงสร้าง

```text
rov-claude-kit/
├── CLAUDE.md
├── README.md
├── KNOWLEDGE_BASE.md
├── PROMPT_CLAUDE_CODE.md
├── knowledge/
│   ├── draft.md
│   ├── macro.md
│   ├── hero.md
│   ├── counter.md
│   └── synergy.md
├── specs/
│   ├── DRAFT_ENGINE_SPEC.md
│   ├── COUNTER_ENGINE_SPEC.md
│   ├── SYNERGY_ENGINE_SPEC.md
│   ├── MACRO_ENGINE_SPEC.md
│   ├── HERO_DATA_SPEC.md
│   └── IMPLEMENTATION_PLAN.md
├── data/
└── originals/
    ├── Draft.md
    ├── Macro.md
    ├── Hero.md
    ├── Counter.md
    └── Synergy.md
```

## หมายเหตุสำคัญ

ไฟล์ใน `knowledge/` และ `originals/` เป็นข้อมูลจาก NotebookLM/Source เดิม ห้ามถือข้อเสนอเชิงสถาปัตยกรรมใน `specs/` เป็นข้อเท็จจริงของเกม เว้นแต่มีแหล่งข้อมูลรองรับ
