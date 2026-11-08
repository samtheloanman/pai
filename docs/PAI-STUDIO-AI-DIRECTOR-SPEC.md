# AutoResearch Specification: PAI Studio AI Director Pipeline

**Objective:** Implement an autonomous, self-hosted AI Director and studio-grade video production engine within the PAI fleet, integrating open-source multi-agent directing frameworks (`open-director`, `herk-edit-kit`, `OpenMontage`) with our local hardware (Dell Precision GPU, Mac Pro Docker, Mini PC).

---

## 1. Architectural Analysis: Gemini CLI vs. Gemini API

| Dimension | Gemini CLI (`gemini` / Code Assist) | Gemini API (`google-genai` / AI Studio) |
| :--- | :--- | :--- |
| **Authentication** | Google User OAuth2 (`gcloud auth` / OAuth web flow) | AI Studio API Key (`GEMINI_API_KEY`) or Vertex AI ADC (`vertexai=True`) |
| **Target Scope** | Developer assistant, interactive shell, code reasoning, workspace context | Raw REST / gRPC API programmatic access, model parameterization |
| **Model Access** | Text/multimodal reasoning (`gemini-2.5-pro`, `gemini-3.8-flash`) | Generative media APIs: `gemini-omni-1.1-flash` (video), Imagen 3, Live API |
| **Why API Key was needed** | CLI session OAuth tokens lack the `generativelanguage.googleapis.com` scope for headless Python background scripts. | The official `google-genai` SDK requires `GEMINI_API_KEY` to talk to the experimental `interactions` & `files` endpoints unless Vertex AI project/ADC is passed. |

---

## 2. Open-Source AI Director Ecosystem Research

### A. Top Open-Source AI Director Projects

1. **`seme-org/open-director` (Self-Hosted AI Studio)**:
   - *Architecture*: 9 specialized AI agents (Researcher, Screenwriter, Storyboarder, Character Designer, Voice/Audio Director, Camera Operator, Editor, Subtitler, Composer).
   - *Modes*: Creative Mode (1-prompt full film) & Batch Mode (automated short-form reels/shorts).
   - *Deployment*: Docker Compose with Redis, MinIO asset vault, and Celery render workers.
   - *Model Agnostic*: Pluggable with Gemini, OpenAI, DeepSeek, Qwen, and local Ollama instances.

2. **`nateherkai/herk-edit-kit` (The Motion & Editing Gold Standard)**:
   - *Architecture*: 15 Claude/Codex agent skills, 406 motion-graphics cards, transcript-aligned edit decision lists (EDL).
   - *Core Philosophy*: The 11 Motion Laws (black canvas, light as brand, camera never sleeps, anamorphic streak transitions, liquid-glass cards, audio sidechain ducking).
   - *Engine*: HyperFrames + GSAP (code-rendered motion design).

3. **`video-db/Director` & `calesthio/OpenMontage`**:
   - Programmatic Remotion/React video composition with automated cut detection, dynamic kinetic typography, and multi-track audio ducking.

---

## 3. PAI Fleet Capability Matrix (Current vs. Additions)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         PAI FLEET AI VIDEO PRODUCTION ENGINE                     │
└──────────────────────────────────────────────────────────────────────────────────┘
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
┌─────────────────────────────────┐                     ┌──────────────────────────────────┐
│       CURRENT LIVE ASSETS       │                     │       TARGET STUDIO ADDITIONS    │
├─────────────────────────────────┤                     ├──────────────────────────────────┤
│ • Hardware: Dell P3000 (CUDA)   │                     │ • Agent Swarm: Open-Director     │
│   & Mac Pro (Colima/Docker)     │                     │   9-role production orchestrator │
│ • Audio: edge-tts (Andrew/Ava)  │                     │ • Motion Engine: GSAP / Remotion │
│   + Python 44.1kHz synth master │                     │   code-driven 60fps renders      │
│ • Video: FFmpeg 9.0.2 hardware  │                     │ • Transitions: Anamorphic whip   │
│   H.264/AV1 + Pillow compositor │                     │   streaks + motion blur passes   │
│ • Skills: gemini-omni-flash-api │                     │ • SFX Library: Keyed whooshes,   │
│   + live-api-dev + generative_ui│                     │   sub-bass hits & UI snaps       │
└─────────────────────────────────┘                     └──────────────────────────────────┘
```

---

## 4. Testable Acceptance Criteria

1. **Autonomous Storyboard Generation**: A single prompt must trigger the Director Agent to output a validated multi-shot storyboard JSON with frame durations, camera angles, and cue timestamps.
2. **Audio Sidechain Ducking**: BGM track must automatically duck -4dB during speech and swell during pauses using FFmpeg `sidechaincompress`.
3. **Anamorphic Transition Whips**: Every scene cut must execute an eased light-streak transition masked with synchronized whoosh SFX.
4. **Zero-Cloud Isolation**: The complete pipeline must execute locally on the Mac Pro or Dell node without external video API costs.
