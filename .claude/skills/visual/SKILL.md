---
name: visual
description: Visual documentation engine — extract evidence frames from video, detection mode, deep analysis, contact sheets. OpenCV + Pillow + NumPy.
user_invocable: true
---

# /visual — Visual Documentation Engine

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `visual <path>` — extract frames (timestamp, detection, or search mode)
- `visual --detect` — automatic significant frame extraction
- `visual --search` — multi-criteria search on video (multi-pass, no bulk extraction)
- `visual --clip <sec>` — reconstruct video clip around a timestamp
- `visual --image <path>` — analyze single image for evidence matching
- `visual --repo` — fetch and process from GitHub repo
- `deep <description>` — frame-by-frame anomaly analysis
- `analyze <path>` — static video analysis with state progression

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/visual-documentation.md`, Publication #22

### Three Operating Paradigms

**Timestamp mode** — extract at known points:
```bash
visual recording.mp4 --timestamps 10.5 30.0 60.0
visual recording.mp4 --times HH:MM:SS --video-start HH:MM:SS
visual recording.mp4 --dates "YYYY-MM-DD HH:MM:SS"
```

**Detection mode** — automatic extraction:
```bash
visual recording.mp4 --detect
visual recording.mp4 --detect --subjects "UART" "error"
```

**Search mode** — multi-criteria, multi-pass scan (no bulk extraction):
```bash
visual recording.mp4 --search --scene-change --min-text 0.15
visual recording.mp4 --search --time-range 30 60 --structured
visual recording.mp4 --search --evidence --session-name demo-2026
```

### Additional Capabilities

**Clip reconstruction** — extract video segment around evidence:
```bash
visual recording.mp4 --clip 45.0 --context 10
```

**Image analysis** — single image evidence matching:
```bash
visual --image screenshot.png
```

**Evidence structure** — organized output with `discoveries/` and `clips/`:
```bash
visual recording.mp4 --search --evidence --session-name demo
```

### Detection Heuristics

| Detector | Method |
|----------|--------|
| Scene change | Histogram correlation |
| Text density | Adaptive threshold + morphology |
| Edge density | Canny edge detection |
| Structured content | Horizontal + vertical line detection |

### Output Pipeline

```bash
visual recording.mp4 --detect --dedup --report --sheet
```

### Deep Analysis

`deep <description>`: Extract ALL frames from newest clip, frame-by-frame analysis focused on described anomaly. Reports: before → anomaly → after → root cause.

### Static Analysis

`analyze <path>`: Key frames at regular intervals, state progression timeline, anomaly detection.

### Inline Evidence Display

After extraction, present discovered frames directly in the conversation. Two methods depending on client capability:

| Method | How | When |
|--------|-----|------|
| **Direct** (Read tool) | `Read` on the PNG file — client renders inline | Desktop/web clients that support `<output_image>` |
| **Via GitHub** (push + raw URL) | Commit evidence to branch → push → display as markdown `![](https://raw.githubusercontent.com/...)` | Mobile app, clients where Read images don't render |

**Protocol**:
1. After extraction, ask the user: "Tu veux voir les résultats maintenant?" (AskUserQuestion — "Show inline" / "Just save" / "Push to GitHub for viewing")
2. If the user already asked to see results (e.g. "montre-moi les extraits"), skip the question and display immediately
3. Try Read tool first (direct). If user reports they can't see → fall back to GitHub push method
4. For GitHub method: commit evidence to current branch → push → display frames as markdown image links using `raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>`
5. Limit inline display to 5 key frames max — link to evidence directory for the rest

**Raw URL pattern**:
```
![Frame description](https://raw.githubusercontent.com/<owner>/<repo>/<branch>/evidence/<session>/discoveries/<filename>.png)
```

## Notes

- Technology: OpenCV (headless) + Pillow + NumPy — no external tools, no cloud APIs
- Engine: `scripts/visual_engine.py` (core) + `scripts/visual_cli.py` (CLI)
- Frame annotation: timestamp bar, source info, detection badge, corner marks
- Search mode works directly on video (seek per frame) — no gigabytes of temp frames
- Evidence structure: `evidence/<session>/discoveries/` + `clips/` + `metadata.json` + `index.md`
