# PAI extendable starter box — research notes (2026-10-31)

Evidence grade: [V] vendor/primary page read, [S] secondary/news, [F] forum/community, [E] my arithmetic estimate, [U] unverified/conflicting.
Many search hits were SEO-style aggregators with odd dates; anything marked [U] needs a live check before it goes in a campaign.
Live DRAM (from STATUS.md, Newegg 10/31): 2x32 GB SO-DIMM $775-1,130; 2x16 GB $550-620 -> one 16 GB ~$275-310, one 32 GB ~$390 [E]. Newegg listing for Crucial 32 GB single stick showed ~$350 but undated [U].

## 1. NVIDIA extensibility
- DGX Spark/GB10: onboard ConnectX-7 (200GbE). NVIDIA playbook says 2-4 Sparks, direct QSFP cables, no switch required [V: build.nvidia.com/playbooks/connect-multiple-sparks]. 64 GB Spark $4,999 from Oct 23 2026 via Acer/ASUS/Dell/Gigabyte/HP/MSI; two 64 GB pool to 128 GB; NVIDIA claims up to 1.7x vs one 128 GB unit [S: storagereview.com, 2026-10-02]. Floor for "extend later" = $10k. Not a starter-box model.
- Real 2-Spark number: Qwen3-235B-A22B UD-Q4_K_XL via llama.cpp RPC over 200GbE: 12.5 t/s gen, 37.7 t/s prompt; single node 1.8 t/s. vLLM+Ray and TensorRT-LLM NVFP4 failed in that report; author needed `-fit off` to avoid segfault [F: forums.developer.nvidia.com/t/.../355126, 2025-12-18]. Commenters say vLLM/SGLang dual-Spark recipes do work (community repo). NVIDIA native multi-node stack on GB10 was immature as of Dec 2025 [F].
- RTX Spark / N1X (Windows on Arm): launching fall 2026; analyst estimates $1,799 (N1) / $2,899+ (N1X laptops), up to 128 GB LPDDR5X; ASUS/MSI/HP mini PCs shown, no confirmed prices [S/U: tomsguide, tomshardware, letsdatascience]. Memory is on-package/unified; no upgrade path found.
- Jetson: NVIDIA raised prices July 2026: AGX Thor kit $3,499 -> $5,499; Orin Nano Super $249 -> $399; Orin Nano 2 announced 2026-08-25 (price not found) [S: cnx-software 2026-07-22, jetsonhacks 2026-08-26]. The "$249 front door" idea is dead.
- NVLink Fusion / consumer "add a GPU later": nothing found. Treat as nonexistent for PAI [U].
- Software: Dynamo supports TRT-LLM, vLLM, SGLang (disaggregated prefill/decode, KV-aware routing) [S]. For a cheap box, llama.cpp RPC is the realistic path.
- eGPU: no NVIDIA-specific consumer path; use generic OCuLink/USB4 (section 2/3).

## 2. AMD / x86 extensibility
- Strix Halo memory is soldered LPDDR5x-8000, confirmed [V: Framework blog/iFixit; Framework says soldered for full bandwidth]. Framework Desktop mainboard (Mini-ITX, PCIe x4 slot) was $799 for Max 385/32 GB at 2025 launch [S: community.frame.work, hothardware]; current price not rechecked and DRAM crisis likely moved it [U]. Not a <$1k extendable design.
- Strix Halo clustering: AMD guide (2026-02-25) runs Kimi K2.5 UD_Q2_K_XL (375 GB) on 4x Ryzen AI Max+ 395 128 GB via llama.cpp RPC over Ethernet (5 Gbps in guide); TTM kernel param lifts VRAM to 120 GB/node [S: amd.com developer article; page fetch timed out so tok/s not read]. kyuz0 toolboxes use 2 Framework Desktops over 50 Gbps Ethernet; says latency, not bandwidth, limits [F/S]. Community estimate 10-15 t/s sparse MoE on 2 nodes [U, estimate].
- SO-DIMM APU mini PCs: GMKtec K11 (Ryzen 9 8945HS, OCuLink, USB4, dual 2.5GbE, up to 96 GB) barebone ~$430-510 on sales, $599.99 list; 32GB/1TB bundles $470-650 over 2025-26 [S: notebookcheck, slickdeals, gmktec.com; none dated Oct 2026 -> U]. Minisforum MS-A2: slot is x16 physical, PCIe 4.0 x8, half-height low-profile cards up to 75 W only [S: notebookcheck]. Gigabyte BRIX with Ryzen AI 400 "Gorgon Point" (announced Mar 2026) up to 96 GB DDR5-5600, SO-DIMM not confirmed [S/U]. Beelink SER9 uses soldered LPDDR5 (no upgrade, no OCuLink) [S]. Beelink EX Pro dock $179, works only with GTi12/13/14 [S/U]. Not checked: MS-S1 MAX, GTi15 OCuLink details.
- LPCAMM2: exists (Micron/Crucial, up to 64 GB, 8533 MT/s) but only in laptops/workstations; no mini PC found [S].
- Add-in VRAM prices: Intel Arc Pro B60 24 GB MSRP $599, one tracker $650 low on 2026-10-02, listings $650-1,700 [S/U]; llama.cpp on Arc uses SYCL (less mature) [S]. Radeon AI PRO R9700 32 GB MSRP $1,299, US stock poor, EU/UK above MSRP [S]. RTX 5060 Ti 16 GB MSRP $429, ~$485-550 street as of May 2026, since reported up [S/U]. Used RTX 3090 $1,300+ (Sep 2026) [S/U]. GPU prices >= MSRP: a 24 GB card alone (~$650) eats the whole upgrade budget.

## 3. Software that makes "extend later" real
- OCuLink eGPU: RTX 3090, Llama 3.1 8B Q4: 96.0 t/s internal vs 93.5 OCuLink (-2.6%); TB4/USB4 15-17% slower [S: localaimaster.com, vendor blog]. Penalty large only when layers spill to system RAM (prefill/load). Hardware-corner reports same for GEM10+3090 [S]. Dock + PSU cost not verified.
- Partial offload / MoE: `-ngl 99 --n-cpu-moe N` (or `--override-tensor`) keeps attention on GPU, experts in RAM. gpt-oss-120b on RTX 3090: ~0.9 -> ~1.6 t/s in one report, 5090 ~9.6 t/s (revision-inconsistent) [S/U: hardware-corner.net]. Expert-cache PR gave 14.95 -> 19.26 t/s on 4090 [S/U]. Lesson: big-model-on-small-GPU is RAM-bandwidth bound; needs dual-channel and 64 GB+.
- llama.cpp RPC: `rpc-server` on remote, `--rpc ip:50052` on host; only host needs the GGUF. Decode needs a network round-trip per token; ~0.17 ms per trip on 10GbE in one repo; TCP_NODELAY mattered (15 -> 43 t/s vs 48 local, 2024 PR) [F: github.com/ggerganov/llama.cpp/pull/6829; kjaiswal benchmarks]. Net: RPC buys capacity, not speed. Over 2.5GbE expect a decode penalty [E].
- exo: Apple/Mac-centric; RDMA over Thunderbolt 5 (macOS 26.2+), Mac+Spark prefill/decode split; MLX models only [S]. Not applicable to x86 PAI.
- distributed-llama, vLLM multi-node (Ray): not researched in this pass [U].

## 4. Starter-box designs (<$1k BOM, parts at cost, not retail)
Constraint: single SO-DIMM = single channel (~45 GB/s vs ~90 GB/s dual-channel theoretical, DDR5-5600) [E]. "Empty second slot" halves decode speed until user upgrades. That is the honest trade; say so on the page.

(a) RECOMMENDED: OCuLink SO-DIMM APU mini PC (K11 class)
| Item | Price | Source/grade |
|---|---|---|
| GMKtec K11-class barebone (8945HS, OCuLink, USB4, 2x2.5GbE) | ~$480 | S, 2025-26 sale prices, U for Oct 2026 |
| 1x32 GB DDR5-5600 SO-DIMM | ~$390 | E from live 2x32 price |
| 512 GB NVMe | ~$70 | U (NVMe price stale per STATUS.md) |
| Total | ~$940 | |
Cheaper variant: 1x16 GB ($290) -> ~$840.
Stages:
- Base (32 GB, single channel): 7-14B dense Q4, Qwen3-30B-A3B-class MoE Q4 (~18 GB) fits. Decode est. 8B Q4 ~8-12 t/s, 3B-active MoE ~15-25 t/s [E, bandwidth-bound arithmetic; must benchmark].
- +RAM (second 32 GB, $390, 64 GB dual channel): ~2x decode for CPU-resident models [E]; 70B Q4 (~40 GB) fits but ~2-3 t/s [E]; gpt-oss-120b (~63 GB) borderline, needs 96 GB.
- +GPU (OCuLink dock ~$60-180 [U] + 24 GB card ~$650 + PSU): fully-in-VRAM models within ~3% of native [S]. 24 GB runs 27-32B Q4 at tens of t/s. Total add ~$800-900.
- +second node: another box via llama.cpp RPC over 2.5GbE: pooled capacity (e.g. 2x64 GB), decode no faster [E].

(b) Mini-ITX with x16 slot: not priced this pass. DRAM cost is the same; board + case + PSU + CPU likely $500+ before RAM [E/U]. Larger than "Mac mini sized" unless SFF. Skip for v1.

(c) Pi / RK3588 / Orin front door: Pi 5 16 GB $205 (Feb 2026) vs $305 (Apr 2026), sources conflict [S/U]; Orin Nano Super now $399 [S]. No price advantage over (a) and 8 GB of RAM cannot host useful models. Drop. RK3588 not researched.

## 5. Pricing tactics (my judgment, unvalidated with customers)
- Ship 32 GB x1 with slot 2 empty; sell "Memory Upgrade Pack" at cost+10% with prepaid shipping label. DRAM is volatile; do not pre-sell fixed-price RAM credits longer than 30 days [E].
- "Upgrade credit" = voucher toward RAM only, expires 12 months, redeemable at then-current cost, not cash.
- Trade-in: take back the original 32 GB stick when customer buys 2x64 kit (resale of SO-DIMM holds value in this market) [E].
- GPU dock as separate SKU: do not stock GPUs; resell dock + PSU and publish a tested-GPU list (B60, 5060 Ti, 3090). GPU price swings make bundling risky.
- Marketing: "Starts at X, grows with you" must show the single-channel speed caveat; no t/s claims until measured on the prototype (STATUS.md contradiction already flagged).

## Gaps / next checks
Live-price K11 barebone and NVMe; confirm K11 OCuLink is a real x4 port and lists 2 SO-DIMM slots with 96 GB support on gmktec.com; benchmark prototype dual- vs single-channel; read AMD Kimi guide tok/s; FCC/warranty for resold docks.
