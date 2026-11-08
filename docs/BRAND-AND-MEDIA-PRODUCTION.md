# PAI Brand Package, 3D Hardware Rendering & Video Explainer Guide

**Date:** 2026-11-01  
**Deliverables:** Vector Logo System, Brand Guidelines, Photorealistic 3D Renders & 60s Cinematic Explainer.

---

## 1. Logo Creation & Assets

The official vector logo asset represents the **"Sovereign Hearth"**—an unbroken architectural silhouette merging the letters `p` and `a` with a central glowing core.

### 1.1 Vector SVG Asset (`public/brand/logo.svg`)
```xml
<svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Outer Monolithic Chamfer Enclosure -->
  <rect x="4" y="4" width="40" height="40" rx="10" stroke="#10201F" stroke-width="3" />
  <!-- Sovereign Arch Counter -->
  <path d="M16 32V22C16 17.5817 19.5817 14 24 14C28.4183 14 32 17.5817 32 22V32" stroke="#10201F" stroke-width="3" stroke-linecap="round" />
  <!-- Private Inference Core (Teal Indicator) -->
  <circle cx="24" cy="24" r="3.5" fill="#0E7C76" />
</svg>
```

---

## 2. Complete Brand Package Guidelines

- **Primary Mark:** Sovereign Hearth glyph.
- **Wordmark:** **PAI** set in wide-tracked geometric uppercase (`letter-spacing: 0.12em`).
- **Typography:** `Geist` Display (Headlines, `-0.03em`), `Geist` Text (Body, 65ch max-width), `Geist Mono` (Technical benchmarks and specs).
- **Primary Color Swatches:**
  - **Nordic Mist Canvas:** `#F2F6F5`
  - **Deep Charcoal Ink:** `#10201F`
  - **Muted Slate:** `#566867`
  - **Whisper Line:** `#DCE4E3`
  - **PAI Botanical Teal (Accent):** `#0E7C76`
  - **Bioluminescent Indicator:** `#3DD6C6`

---

## 3. Computer Hardware 3D Image Rendering Protocol

To generate ultra-realistic product imagery that replaces placeholder illustrations across the website (`pai-store`) and press kits:

### 3.1 Blender / Cinema 4D / Octane Pipeline
1. **CAD Modeling:**
   - 135mm × 135mm × 42mm monolithic chassis with 3.5mm radius corners.
   - 45-degree micro-chamfer on top perimeter.
   - Precision CNC I/O cutouts on the rear (dual 2.5GbE, OCuLink, HDMI, USB-A).
   - Recessed front USB-C port and micro-drilled LED diffuser grille.
2. **Material Shader:**
   - Base Color: `#383C3D` (Space Gray) or `#D8DADB` (Satin Silver).
   - Metallic: `1.0`.
   - Roughness: `0.32` with micro-noise normal map simulating bead-blasted anodized aluminum.
3. **Studio Lighting Rig:**
   - Key Light: 80cm softbox positioned at 45 degrees overhead.
   - Rim Light: Narrow linear strip light accentuating the chamfered top edge.
   - Fill Light: Warm reflector panel bouncing 3200K ambient warmth into the dark aluminum shadows.

### 3.2 AI Render Generator Prompts (Midjourney v6 / Flux.1 Pro)
```text
Commercial studio product photography of the PAI Starter domestic AI server. Minimalist anodized bead-blasted dark aluminum mini PC chassis resting on a solid Danish white oak table next to a matte ceramic mug. Beveled chamfered metallic edges, diffused warm morning side-lighting, shallow depth of field (f/2.8, 85mm prime lens), single soft cyan-teal micro-LED indicator light on the front panel. Clean architectural composition, Dieter Rams industrial design aesthetic, Teenage Engineering craftsmanship, Hasselblad medium format camera detail, 8k resolution, raw photorealism. --ar 16:9 --style raw
```

---

## 4. Ultra-Realistic Explainer Video Production Plan

### 4.1 Production Tools
- **3D Motion Graphics:** Blender 4.2 / Cinema 4D (exploded internal view of Ryzen APU, SO-DIMM RAM slots, and OCuLink PCIe bus).
- **Live Video & Atmosphere:** Blackmagic Design 6K Pro / Sony FX3 with 35mm anamorphic prime lenses for domestic lifestyle shots.
- **Voiceover:** Native PAI Kokoro voice model (or high-end custom ElevenLabs voice design matching the calm Scandinavian tone).
- **Sound Design:** Tactile metal clicks, acoustic room tone, low warm electronic resonance.

### 4.2 Storyboard Breakdown (60s)
1. **[0:00 - 0:10] The Machine:** Extreme macro shot of CNC machining the aluminum chassis edge. Voiceover questions cloud privacy.
2. **[0:10 - 0:22] The Domestic Reality:** Placing the compact silent box onto a living room sideboard. Single Ethernet cable plugged in. Zero fan whine.
3. **[0:22 - 0:38] Conversational Intelligence:** User speaks naturally. PAI responds instantly (<800ms) with local speech synthesis. Voice wave pulses in soft teal.
4. **[0:38 - 0:50] The Hardware Inside:** Exploded view revealing the Ryzen 8000 APU, dual DDR5 slots, and SQLCipher encrypted local vault.
5. **[0:50 - 1:00] The Sovereign Statement:** Camera tracks back to show PAI running silently alongside phone and laptop. Tagline: **"Your AI. Your house."**
