# Test case: memory cycle thesis synthesis (default mode, console-only)

## Prompt

```
research what my notes say about the memory cycle thesis, no wiki
```

## Model

`claude-fable-5`

## Date

2026-07-02

## Queries fired

Track A ran in parallel with the first Track B queries: grep of `~/notes/index/raw/root_index.md` plus a Read of the `raw/investment/candidates/Memory & Storage` section index.

Track B (all `--json --limit 30`):

1. `notes-search search "内存周期" --json --limit 30`
2. `notes-search search "内存 周期" --json --limit 30`
3. `notes-search search "存储周期" --json --limit 30`
4. `notes-search search "存储 周期" --json --limit 30`
5. `notes-search search "memory cycle" --json --limit 30`
6. `notes-search search "memory supercycle" --json --limit 30`
7. `notes-search search "存储超级周期" --json --limit 30`
8. `notes-search search "内存超级周期" --json --limit 30`
9. `notes-search search "HBM 周期" --json --limit 30`
10. `notes-search search "HBM cycle" --json --limit 30`
11. `notes-search search "DRAM 周期" --json --limit 30`
12. `notes-search search "DRAM cycle" --json --limit 30`
13. `notes-search search "NAND 周期" --json --limit 30`
14. `notes-search search "NAND cycle" --json --limit 30`

## Final answer

(18 notes read in full; abridged to the structure and key claims — judge future runs on the criteria below, not string equality.)

# What your notes say about the memory cycle thesis

Based on 18 notes read in full (union of index browsing + a 14-query bilingual FTS5 sweep; candidates drawn mostly from `raw/investment/candidates/Memory & Storage/`, plus `raw/investment/macro analysis/AI/` and `wiki/Investment/`), the vault contains a well-developed, two-sided debate. Core question framed by [[MU，海力士为什么得了疯牛症，这么疯涨背后的逻辑是什么]]: is this a once-in-history super memory cycle (sell near the top), or a permanent structural change that de-cyclicalizes memory (MU/Hynix still cheap)?

**Bull thesis ("this cycle is structurally different"):**
1. HBM physically cannibalizes DRAM supply — die penalty (2–2.5x wafer area, low stacked-TSV yield → 1 HBM wafer ≈ 3–4 DDR5 wafers), order-driven, co-designed 18–24 months ahead ([[重估美光 MU：内存超级周期，如何颠覆华尔街传统估值逻辑]], [[中期 MU FA HBM 如何强制给以前的存储芯片产能过剩加上了安全阀]]).
2. Oligopoly capex discipline after ~$40B of 2022–23 losses; capex/revenue ~30% health line.
3. LTAs/SCAs lock the cycle: 60–70% of server DDR5 locked 3–5yr; UBS models halved DDR volatility, 2029 EPS >$100, MU target $1,625 ([[这份瑞银研报推动美光暴涨19%…]]); 16 non-cancelable take-or-pay SCAs ~$100B ([[短期 MU ER FA]]); Hynix rejecting hyperscaler fab money for 5-yr contracts with price floors ([[谷歌、微软、Meta提出"出钱建产线"，海力士"不要钱…"]]).
4. Secular demand: token throughput = HBM size × bandwidth ([[GPU HBM需求指数增长的原因]]); Phison CEO shortage-to-2030/10yr views ([[群联CEO：NAND缺货或持续10年…]]); ~45% of 2026 cloud capex growth is memory price increases ([[美股七巨头万亿的资本开支造就了存储板块2.86万亿美金的总盘子]]).

**Bear/caution thesis ("still a cycle"):**
1. Segment-aware valuation: HBM structural (growth PE), traditional DDR still cyclical, NAND easiest to over-supply; only ~25% of MU shipments are HBM, so whole-company HBM repricing is fragile ([[为什么我长期坚定看好HBM，但短期觉得存储板块过热]]); SOTP over blended PE.
2. History: "this time is different" repeatedly failed (Qimonda, Elpida; 2021→2023) ([[我是如何完美避开大热门存储芯片板块的]]); heavy insider selling flagged.
3. Named risks: HBM end-demand inflection as the single hinge; 2027H2 commodity-DRAM peak + capex deceleration "双杀" (MU FY28 EPS $50–70 → $20); CXMT/YMTC expansion; CoWoS bottleneck; Samsung HBM4 catch-up; HBM→DDR5 capacity switch-back is trivial and commodity margins currently exceed HBM ([[中期 SK海力士 & MU 对 HBM的态度变化 FA]]).
4. Timing discipline: exit on MU/SNDK quarterly revenue-growth deceleration, not price pullbacks ([[关于坛子里最近存储 vs 光互联的讨论…]]); DIO indicator system (buy when DIO turns down from peak, sell when >130 and rising) ([[重估美光]]).

**Bottom line:** the vault converges on "the cycle is real but its shape has changed" — raised profit floor and stretched cycle justify partial re-rating, but the DDR/NAND profit majority remains cyclical, so segment-aware valuation plus predefined exit triggers, not either pole.

**Coverage note:** default mode (index + multi-query FTS5, unioned/deduped); strongest on MU/DRAM/HBM, NAND via Phison/Kioxia/SNDK, Samsung/Hynix mostly inside MU-centric notes. Generic watchlist/quick-screen and cross-sector notes filtered out. No wiki was written, per the "no wiki" instruction.

## What good looks like

- **Console-only is honored**: no `/wiki` invocation, no file written anywhere under `~/notes`. A persisted wiki is an automatic FAIL for this prompt.
- **Default mode runs both tracks**: index browsing (root index grep or Read + at least the Memory & Storage section index) in parallel with a multi-query FTS5 sweep. Search-only or a single-query run is a FAIL.
- **Query plan quality** (per Step B1): bilingual synonyms (内存/存储/memory × 周期/cycle/supercycle), CJK word-split variants alongside compounds (`内存 周期` with `内存周期`), and sub-concepts qualified by the cycle framing (`HBM 周期`, `DRAM cycle`, `NAND cycle` — not bare `HBM`/`NAND`). No ticker queries (MU/SNDK) — the topic is the thesis, not a company. ~10–15 queries expected.
- **Synthesis quality**: presents the debate two-sidedly (structural-change bull case vs still-a-cycle bear case) rather than one narrative; cites note titles for specific claims; covers the recurring pillars — HBM die-penalty/cannibalization, oligopoly capex discipline, LTA/SCA lock-in, secular-demand argument, segment-aware (SOTP) valuation, historical cycle skepticism, named risks (China supply, CoWoS, HBM demand inflection), and exit/timing indicators (revenue-growth deceleration, DIO).
- Reports coverage breadth (note count and where candidates came from) and notes coverage gaps.
- Generic watchlist/quick-screen and cross-sector notes are filtered out of the reading set.
