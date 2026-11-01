# PAI OS

Skeleton. Implements PRD section 5.1 (OS-1 … OS-9).

- `ansible/` — playbook that provisions a dev box to the image's state (OS-9). Start here while the image build is chosen.
- Image build (bootc/Fedora CoreOS-style vs Ubuntu Core) — decide by prototyping; tracked in PRD §11.

Hard rules: services bind to localhost or the overlay interface only (OS-5); telemetry off (OS-7); signed A/B updates (OS-1, OS-2).
