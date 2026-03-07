# Visual Documentation — Methodology

Automated evidence extraction from video recordings for documentation creation, update, and review. The `visual` command processes video files using computer vision to extract significant frames as documentation evidence — no external services, no cloud APIs, standard libraries only.

## When to Use

| Scenario | Example |
|----------|---------|
| **Post-session documentation** | Extract key moments from a recorded development session |
| **Evidence collection** | Capture UI states, UART output, error screens from video |
| **Automated review** | Scan recordings for content changes relevant to a project |
| **Time-based extraction** | Pull frames at specific timestamps from meeting recordings |
| **Comparative analysis** | Extract before/after frames from test recordings |

## Architecture

### Technology Stack

| Library | Role | Version |
|---------|------|---------|
| **OpenCV** (cv2) | Video decoding, frame extraction, image processing | 4.x (headless) |
| **Pillow** (PIL) | Image annotation, format conversion, contact sheets | 12.x |
| **NumPy** | Array operations (OpenCV dependency) | 2.x |
| **Python stdlib** | pathlib, datetime, json, urllib, tempfile, hashlib | 3.11+ |

**Design constraint**: No external tools (no ffmpeg CLI, no cloud vision APIs, no OCR services). All processing is done through Python library calls. This ensures portability across all environments where the Knowledge System operates.

### Module Structure

```
scripts/
├── visual_engine.py    # Core processing engine
│   ├── VideoInfo              — Video metadata extraction
│   ├── EvidenceSession        — Organized evidence directory management
│   ├── extract_frames_at_timestamps()  — Seconds-based extraction
│   ├── extract_frames_at_times()       — HH:MM:SS extraction
│   ├── extract_frames_at_dates()       — DateTime extraction
│   ├── detect_evidence_frames()        — Automatic detection
│   ├── search_video()                  — Multi-criteria, multi-pass search
│   ├── reconstruct_clip()              — Video segment extraction
│   ├── analyze_image()                 — Single image evidence analysis
│   ├── generate_contact_sheet()        — Thumbnail grid
│   ├── generate_evidence_report()      — Markdown report
│   ├── fetch_video_from_github()       — Remote video fetching
│   └── deduplicate_frames()            — Perceptual hash dedup
│
└── visual_cli.py       # CLI entry point (argparse dispatcher)
    ├── build_parser()           — Argument definitions
    ├── resolve_video_source()   — Local/GitHub resolution
    ├── run()                    — Main execution pipeline
    ├── print_summary()          — Human-readable output
    └── print_search_summary()   — Search results output
```

## Operating Modes

### 1. Timestamp Mode

Extract frames at known points in the video. Three input formats:

| Format | Flag | Example |
|--------|------|---------|
| **Seconds** | `--timestamps` | `--timestamps 10.5 30.0 60.0` |
| **Clock time** | `--times` | `--times 00:01:30 00:05:00` |
| **Date-time** | `--dates` | `--dates "2026-03-01 14:30:00"` |

For clock times and date-times, provide `--video-start` or `--video-start-datetime` to calculate offsets from the recording start.

**Use case**: You know when something happened (from logs, from memory, from another session's notes) and need the visual evidence.

### 2. Detection Mode

Scan the entire video for visually significant frames using computer vision heuristics:

| Detector | What it finds | Threshold |
|----------|--------------|-----------|
| **Scene change** | Major visual transitions (histogram correlation) | `< 1.0 - sensitivity` |
| **Text density** | Documentation-relevant frames (adaptive threshold + morphology) | `> 0.15` |
| **Edge density** | Diagrams, tables, code, UI elements (Canny edge detection) | `> 0.12` |
| **Structured content** | Tables, grids, forms (horizontal + vertical line detection) | `> 0.08` |

**Parameters**:
- `--sensitivity` (0-1): Lower = more frames detected. Default: 0.35
- `--interval` (seconds): Minimum gap between detections. Default: 1.0
- `--max-frames`: Cap on total extractions. Default: 50
- `--subjects`: Keyword hints for content-aware filtering

**Bookend frames**: Detection mode always captures first and last frames if not already selected.

**Use case**: You have a recording and want the system to find what's worth documenting.

### 3. Search Mode (Multi-Criteria, Multi-Pass)

Intelligent search directly on the video file — no bulk frame extraction. The engine performs multi-pass scanning:

- **Pass 1 (coarse)**: Scan every ~1 second, evaluate all criteria simultaneously
- **Pass 2 (fine)**: Frame-by-frame refinement around each hit (±0.5 seconds)

Search criteria can be combined freely:

| Criterion | Flag | Example |
|-----------|------|---------|
| **Scene changes** | `--scene-change` | Detect major visual transitions |
| **Text density** | `--min-text 0.15` | Find frames with text content |
| **Edge density** | `--min-edge 0.12` | Find diagrams, tables, UI |
| **Structured content** | `--structured` | Find tables, grids, forms |
| **Time ranges** | `--time-range 30 60` | Restrict search to specific ranges |
| **Timestamps** | `--timestamps 10 20` | Check specific known points |

```bash
# Multi-criteria search
visual recording.mp4 --search --scene-change --min-text 0.15

# Search within time ranges
visual recording.mp4 --search --time-range 30 60 --time-range 120 180

# Full evidence session with organized output
visual recording.mp4 --search --evidence --session-name demo-2026
```

**How it works**: Instead of extracting all frames to disk (which would consume gigabytes for a long video), the engine reads frames directly from the video using OpenCV's seek. Only frames that match the criteria are saved. This makes it practical to search hours-long recordings with minimal disk usage.

**Use case**: You have a multi-hour recording and specific things to find — combine criteria to narrow the search, get only what matches.

### 4. Clip Reconstruction

Extract a video segment centered around a timestamp. Produces a standalone `.mp4` clip with configurable context (default: ±10 seconds).

```bash
# Extract 20 seconds around the 45-second mark
visual recording.mp4 --clip 45.0 --context 10
```

**Automatic with search**: In search mode, clips are automatically reconstructed around each finding (unless `--no-clips` is specified).

**Use case**: You found an evidence frame — now extract the surrounding video for context or documentation.

### 5. Image Analysis

Analyze a single image for evidence characteristics using the same heuristics as video detection.

```bash
visual --image screenshot.png
visual --image capture.jpg --min-text 0.15
```

Returns scores for text density, edge density, and structured content, plus a boolean "is this evidence?" assessment. Optionally saves an annotated copy with scores overlay and evidence markers.

**Use case**: You have a screenshot and want to know if it matches the kind of evidence you're looking for.

### 6. Default Mode

When no explicit mode is specified, detection mode runs with default parameters. This is the zero-configuration path — provide a video, get evidence.

## Evidence Structure

When using `--evidence` (or automatically in search mode), results are organized in a structured directory:

```
evidence/<session-name>/
  metadata.json          — source info, criteria, timestamps, findings count
  discoveries/           — extracted evidence frames (only the hits)
  clips/                 — reconstructed video segments
  index.md               — markdown inventory of all findings
```

The evidence structure is designed to feed into documentation later — images and clips can be referenced directly from documentation pages.

## Video Sources

### Local Files

```bash
visual recording.mp4 --detect
visual /path/to/session_capture.mp4 --timestamps 10 20 30
```

### GitHub Repositories

```bash
visual --repo packetqc/stm32-poc --file live/dynamic/clip_0.mp4 --detect
visual --repo packetqc/knowledge --file live/static/demo.mp4 --ref feature-branch
```

Fetching uses `raw.githubusercontent.com` with automatic main/master fallback. Authenticated via `GH_TOKEN` when available (for private repos).

## Output Pipeline

### Extracted Frames

Each frame is saved as a PNG with optional annotation overlay:
- **Timestamp bar**: Semi-transparent bottom bar with HH:MM:SS.mmm
- **Source info**: Video filename and resolution
- **Detection badge**: Green badge with detection reason (detection mode only)
- **Corner marks**: Green evidence indicator marks at all four corners

### Inline Evidence Display

After extraction, present discovered frames directly in the conversation so the user sees results immediately without leaving the session.

**Two display methods** — client-dependent:

| Method | Mechanism | Best for |
|--------|-----------|----------|
| **Direct** | `Read` tool on PNG — client renders inline via `<output_image>` | Desktop/web clients with image rendering |
| **Via GitHub** | Commit + push evidence → display as `![](https://raw.githubusercontent.com/...)` markdown | Mobile app, CLI, clients where Read images don't render |

**Display protocol**:
1. If the user explicitly asked to see results → display immediately (no confirmation needed)
2. Otherwise → AskUserQuestion: "Show inline?" / "Just save" / "Push to GitHub for viewing"
3. Try direct method first. If user reports invisible → switch to GitHub method for the session
4. Limit inline display to ~5 key frames. Link to evidence directory for the full set
5. For clips (.mp4) → always push to GitHub (no inline video in any client)

**GitHub raw URL pattern**: `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/evidence/<session>/discoveries/<file>.png`

### Deduplication

The `--dedup` flag removes near-identical frames using perceptual hashing (DCT-based pHash):
1. Resize to 64x64 grayscale
2. Apply Discrete Cosine Transform
3. Extract 16x16 low-frequency components
4. Binary threshold at median
5. Compare Hamming distance between consecutive frames

Default threshold: 0.92 (92% similarity = duplicate).

### Contact Sheet

A grid of thumbnails with metadata labels. Generated with `--sheet`:

```
┌──────────────────────────────────────────┐
│  Evidence Contact Sheet                   │
│  12 frames · 2026-03-02 14:30            │
├──────┬──────┬──────┬──────┤
│ 0:05 │ 0:12 │ 0:24 │ 0:38 │
│      │      │      │      │
├──────┼──────┼──────┼──────┤
│ 0:45 │ 1:02 │ 1:15 │ 1:28 │
│      │      │      │      │
├──────┼──────┼──────┼──────┤
│ 1:40 │ 1:55 │ 2:10 │ 2:30 │
│      │      │      │      │
└──────┴──────┴──────┴──────┘
```

### Evidence Report

Markdown document with:
- Video metadata (resolution, fps, duration, codec)
- Summary table (timestamp, frame file, detection reason, hash)
- Per-frame detail sections with embedded image references
- Generated by `--report`

## Integration with Knowledge System

### As a Command Call

The `visual` command belongs to the **Visuals** category in the knowledge command system. It is invoked by Claude sessions when processing video evidence.

### Relationship to Live Session

| Aspect | Live Session (`I'm live`) | Visual (`visual`) |
|--------|--------------------------|-------------------|
| **Timing** | Real-time (during recording) | Post-hoc (after recording) |
| **Input** | Live RTSP stream clips | Video files (local or GitHub) |
| **Frame selection** | Latest frame only | Timestamps or auto-detection |
| **Output** | Immediate diagnostic report | Evidence frames + report + sheet |
| **Persistence** | Issue comments (ephemeral) | Files committed to repo |

### Workflow Example

```
1. Developer records a session (OBS → stream_capture.py → clip_N.mp4)
2. Session ends — clips are committed to the repo
3. Later: visual clip_0.mp4 --detect --dedup --report --sheet
4. Evidence frames extracted, contact sheet generated, report written
5. Frames and report committed as documentation evidence
```

## Safety Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max video duration | 7200s (2h) | Prevent runaway processing on detection mode |
| Max detection frames | 50 | Prevent output explosion |
| Min detection interval | configurable (default 1s) | Avoid frame flooding |
| Dedup threshold | configurable (default 0.92) | Balance uniqueness vs coverage |

## Related

- `scripts/visual_engine.py` — Core processing engine
- `scripts/visual_cli.py` — CLI entry point
- `methodology/interactive-diagnostic.md` — Diagnostic session methodology
- `methodology/commands.md` — Command reference (Visuals category)
- Publication #2 — Live Session Analysis (real-time counterpart)
- Publication #22 — Visual Documentation (this feature's publication)
