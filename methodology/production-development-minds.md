# Production/Development Mind Deployment Model

## Overview

Knowledge's distributed network operates as a **multi-tier deployment model** where each node (mind) has a dual role:

- **System-level**: relative to the core, satellites are **development/pre-production** environments — testing new capabilities before harvest brings intelligence back to core for promotion.
- **Repo-level**: each satellite is simultaneously a **production** environment at its own level — publishing its own GitHub Pages, managing its own project boards, serving its own web presence.

This multi-tier architecture means every node in the network is both **consumer** (development relative to core) and **producer** (production at its own repo level).

## The Multi-Tier Model

```
Core (packetqc/knowledge)
│   Role: PRODUCTION — system-wide canonical brain
│   Web:  packetqc.github.io/knowledge/
│   Scope: methodology, core publications, compliance, evolution
│
├── Satellite: knowledge-live (P3)
│   Role: DEV/PRE-PROD relative to core
│         PRODUCTION at repo level
│   Web:  packetqc.github.io/knowledge-live/
│   Scope: test new capabilities, own publications, own project boards
│
├── Satellite: MPLIB (P1)
│   Role: DEV/PRE-PROD relative to core
│         PRODUCTION at repo level
│   Web:  packetqc.github.io/MPLIB/
│   Scope: embedded library development, own documentation
│
├── Satellite: STM32 PoC (P2)
│   Role: DEV/PRE-PROD relative to core
│         PRODUCTION at repo level
│   Scope: hardware proof-of-concept, own methodology
│
└── Satellite: MPLIB Dev Staging (P4)
    Role: DEV/PRE-PROD relative to P1 (child of child)
          PRODUCTION at repo level
    Scope: staging environment for MPLIB changes
```

## Dual Role of Satellites

Every satellite in the network operates at two levels simultaneously:

| Perspective | Role | What it means |
|-------------|------|---------------|
| **Relative to core** | Development / Pre-production | Testing ground for new capabilities. Insights, patterns, and methodology discovered here are harvested back to core for review and promotion. The satellite is an experiment. |
| **At its own repo level** | Production | Published GitHub Pages, own project boards, own publications, own web presence. The satellite serves real content to real users through its own `packetqc.github.io/<repo>/` URL. |

This is not a contradiction — it's the same principle as a microservice being both a consumer of a shared platform AND a producer of its own API. The satellite consumes core methodology (development role) while producing its own documentation (production role).

## Web Presence at Every Node

GitHub Pages per repo is the enabler of this model. Each node publishes independently:

| Node | GitHub Pages URL | Content |
|------|-----------------|---------|
| Core (knowledge) | `packetqc.github.io/knowledge/` | Canonical publications, profile, compliance reports |
| knowledge-live | `packetqc.github.io/knowledge-live/` | Live session tooling, export documentation |
| MPLIB | `packetqc.github.io/MPLIB/` | Embedded library documentation |

The network is a **constellation of production web presences**, not a single central site with satellites feeding into it. Each node is independently useful and independently published.

### Dual-Origin Links

Publications and documentation exist across repos with independent GitHub Pages:

- **Core links** (`packetqc.github.io/knowledge/`) — system-production, canonical, reviewed
- **Satellite links** (`packetqc.github.io/<repo>/`) — repo-production, independently published

Both are valid production. The difference is scope, not quality. The origin badge (**core** vs *satellite*) in project hub pages indicates provenance, not authority level.

See `methodology/project-management.md` (Dual-Origin Link System) for the full specification.

## Lifecycle Flow

The production/development tiers create a natural lifecycle for capabilities and intelligence:

```
1. IDEA
   └── Discovered during satellite work (development role)

2. SATELLITE TESTING
   └── Implemented and tested in satellite (development role)
   └── Published on satellite's own GitHub Pages (production role at repo level)

3. HARVEST
   └── Core session runs harvest <satellite>
   └── Insights extracted into minds/<satellite>.md (incubator)

4. PROMOTION
   └── harvest --review → harvest --stage → harvest --promote
   └── Insight graduates to core patterns/, lessons/, or methodology/

5. CORE PRODUCTION
   └── Published on core's GitHub Pages (system-production)
   └── Available to all satellites on next wakeup (push)

6. NETWORK INHERITANCE
   └── All satellites inherit the promoted capability on next wakeup
   └── The cycle can repeat — satellites may evolve the capability further
```

### Live Example: P6 Export Documentation

P6 (Export Documentation) demonstrates this lifecycle:
1. **Created in knowledge-live** (satellite) as a managed project — tested PDF/DOCX export
2. **Published on knowledge-live's GitHub Pages** — repo-level production
3. **Harvested to core** via `harvest knowledge-live` — insights into `minds/knowledge-live.md`
4. **Promoted to core** — export capability documented in core publications
5. **All satellites inherited** — export toolbar available in all project web pages

## Project Management at Satellite Level

Satellites have the same project management capabilities as core:

| Capability | Core | Satellite |
|-----------|------|-----------|
| `project create` | Creates managed projects in core | Creates managed projects in satellite host repo |
| `project list` | Lists all P# projects | Lists satellite-scoped projects |
| GitHub Project boards | Linked to core repo | Linked to satellite repo |
| Publications (`pub new`) | Published on core Pages | Published on satellite Pages |
| Webcards (`webcard`) | Generated for core pages | Generated for satellite pages |

The `project create` command works identically at both levels — the difference is which repo hosts the result and which GitHub Pages URL serves it.

## When to Use Each Tier

| Scenario | Tier | Why |
|----------|------|-----|
| Testing new knowledge system capability | Satellite (development) | Doesn't risk core stability |
| Publishing project-specific documentation | Satellite (repo-production) | The satellite IS the authoritative source |
| Promoting validated patterns to all projects | Core (system-production) | All satellites inherit on next wakeup |
| Creating a new managed project for testing | Satellite (development) | Can be promoted to core later |
| Publishing compliance reports, methodology | Core (system-production) | System-wide canonical content |

## Relationship to Other Concepts

| Concept | Document | Connection |
|---------|----------|------------|
| Dual-origin links | `methodology/project-management.md` | Core vs satellite link origins |
| Knowledge layers | `CLAUDE.md` (Distributed Minds) | Core → Proven → Harvested → Session |
| minds/ incubator | `minds/README.md` | Where satellite insights mature before core promotion |
| Satellite bootstrap | `methodology/satellite-bootstrap.md` | How nodes join the network |
| Harvest protocol | `CLAUDE.md` (Harvest section) | How intelligence flows back to core |

---

*Discovery: v47 — Production/Development Mind Deployment Model*
*Authors: Martin Paquet & Claude (Anthropic, Opus 4.6)*
