# 09 · UI / UX specification

Read in: **Phase 6**, one sub-phase at a time (each sub-phase lists the sections it needs).

The UI is graded. The audience is an AP manager and an interviewer watching a live run. It must feel like a calm, precise financial tool: paper, ink, and colour used only to carry meaning. Not a SaaS landing page.

## 9.0 Design skills to load first (Phase 6a)
1. Read `skills/frontend-design/SKILL.md` (in this repo).
2. Install the taste skill for your agent and read it:
   `npx skills add https://github.com/Leonxlnx/taste-skill --skill design-taste-frontend`
   (Codex users may additionally read the `gpt-taste` variant, but **ignore its GSAP / scroll-animation / high layout-variance directions**; they are for marketing sites.)
   If installation fails, fetch `https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/taste-skill/SKILL.md` and read it. If both fail, continue with this document alone and note it in PROGRESS.md.
3. Dials to apply from taste-skill: **DESIGN_VARIANCE 3, MOTION_INTENSITY 3, VISUAL_DENSITY 6**.
4. **Precedence:** this document > taste-skill > frontend-design skill. Where they conflict, this document wins.

## 9.1 Anti-slop rules (hard bans)
- No gradients (backgrounds, text, buttons, borders). No glassmorphism, blur panels, glows, neon, floating blobs, noise textures.
- No purple, violet, indigo, teal-to-blue anything. No emoji anywhere in the UI.
- No em dashes (—) in UI copy. Use periods, colons, or middots (·).
- No centered hero sections, no marketing taglines, no "AI-powered" badges, no sparkle icons.
- No cards inside cards inside cards: max one level of card nesting.
- No more than one primary (filled black) button visible per view region.
- No all-caps except the 11px eyebrow labels defined below.
- No placeholder lorem ipsum, no fake data in the UI. Everything comes from the API.
- No layout shift when data loads: use skeletons with the final dimensions.
- No default browser focus outline removal without replacement.

## 9.2 Stack (Phase 6a)
Vite + React 18 + TypeScript (strict) · React Router v6 · TanStack Query v5 · Tailwind CSS v4 (`@tailwindcss/vite`), tokens declared in CSS (`@theme`) · `lucide-react` icons (stroke width 1.5, size 16 or 18 only) · `@fontsource/raleway` (600, 700), `@fontsource/source-sans-3` (400, 600), `@fontsource/ibm-plex-mono` (400, 500), self-hosted (no Google Fonts request, no FOUT). No component library (no MUI, Chakra, shadcn). Build small components yourself.

## 9.3 Typography
Headings: **Raleway**. Body: **Source Sans 3**. Data (IDs, invoice numbers, GSTINs, PO numbers, amounts in tables, event log): **IBM Plex Mono**.
(Gill Sans MT is not licensed for web embedding; Raleway gives the same geometric-humanist feel. Economica was considered and rejected: condensed faces hurt legibility at UI sizes.)

**Raleway ships old-style figures by default; numbers in headings look broken without this.** Apply globally:
```css
h1,h2,h3,h4,.font-heading { font-feature-settings: "lnum" 1, "tnum" 1; }
.tabular { font-variant-numeric: tabular-nums lining-nums; }
```

| Token | Font | Size / line-height | Weight | Tracking | Use |
|---|---|---|---|---|---|
| `display` | Raleway | 32 / 40 | 700 | -0.015em | Decision label on run page only |
| `h1` | Raleway | 26 / 32 | 700 | -0.01em | Page title (one per page) |
| `h2` | Raleway | 18 / 26 | 600 | -0.005em | Section/card titles |
| `h3` | Raleway | 15 / 22 | 600 | 0 | Sub-sections, stage names |
| `eyebrow` | Raleway | 11 / 16 | 600 | 0.08em, UPPERCASE | Labels above values, table headers |
| `body` | Source Sans 3 | 15 / 24 | 400 | 0 | Default text |
| `body-strong` | Source Sans 3 | 15 / 24 | 600 | 0 | Emphasis |
| `small` | Source Sans 3 | 13 / 20 | 400 | 0 | Secondary text, captions |
| `mono` | IBM Plex Mono | 13 / 20 | 400 | 0 | IDs, amounts in tables |
| `mono-lg` | IBM Plex Mono | 20 / 28 | 500 | 0 | KPI numbers, decision amount |

Hierarchy rule: every screen reads in this order: page title → the one thing that matters (KPI strip / decision) → detail. Never two `h1`s. Body text max width 68ch.

## 9.4 Colour tokens
```css
--paper: #F6F5F1;        /* app background, warm off-white */
--surface: #FFFFFF;      /* cards, tables, nav */
--surface-sunken: #FAF9F6; /* table header, code blocks, input bg */
--ink: #111111;          /* primary text, primary button bg */
--ink-2: #3D3D3A;        /* secondary text */
--ink-3: #6E6D68;        /* tertiary, captions, placeholders (AA on white: 5.1:1) */
--line: #E5E3DC;         /* hairlines, card borders */
--line-strong: #CCC9BF;  /* input borders, dividers that must be seen */
--focus: #111111;

/* semantic: text / tint background / border */
--approve: #1B6B43;  --approve-tint: #EAF4EE; --approve-line: #B9DCC8;
--review:  #8A5A00;  --review-tint:  #FBF3E1; --review-line:  #EAD2A0;
--hold:    #A13D0F;  --hold-tint:    #FCEEE6; --hold-line:    #F0C3A8;
--reject:  #A3182A;  --reject-tint:  #FBEBED; --reject-line:  #EFBCC3;
--info:    #3D3D3A;  --info-tint:    #F1F0EC;
--running: #111111;
```
Colour appears only on: decision badges, check outcome icons, stage status markers, consumption bars, the decision panel's left rule. Everything else is ink on paper. Status is **never** conveyed by colour alone: always icon + text.

Dark mode: not required. Do not add a toggle.

## 9.5 Space, shape, depth
- Spacing scale (px): 4, 8, 12, 16, 24, 32, 48, 64. Use nothing else. Card padding 24. Gap between cards 24. Section gap 32. Table row height 48 (dense list 40). Page top padding 32.
- Layout: max content width 1240 px, centred; side gutters 32 px (≥1024), 24 px (≥640), 16 px below.
- Radius: 10 px cards/panels, 8 px buttons/inputs, 6 px badges, 999 px only for status dots.
- Borders: 1 px `--line` on every card. 
- Shadows (two only): `--shadow-1: 0 1px 2px rgba(17,17,17,0.04)` on cards; `--shadow-2: 0 1px 2px rgba(17,17,17,0.05), 0 12px 32px -16px rgba(17,17,17,0.18)` on popovers, dialogs, the decision panel.
- Depth comes from paper vs white surface + hairline + shadow-1, not from colour blocks.

## 9.6 Motion
- Durations 120 ms (hover, press), 200 ms (panel/tab change), 300 ms (decision panel reveal). Easing `cubic-bezier(0.2, 0, 0, 1)`.
- Allowed: opacity/translateY(4px) fades for appearing content; running stage marker = 1.2 s linear spinning ring; completed marker icon scales 0.9 → 1.0 once; consumption bar width transitions 300 ms.
- Not allowed: bounces, springs, parallax, staggered list entrances longer than 200 ms total, confetti.
- `prefers-reduced-motion: reduce` → disable all transforms and the spinner (show a static half ring).

## 9.7 Components (build in `frontend/src/components/`)
| Component | Spec |
|---|---|
| `AppShell` | Top nav bar 56 px, white, bottom hairline. Left: wordmark `Kestrel AP` (Raleway 700, 16 px) + small `·` + `Invoice desk` in `--ink-3`. Center-left nav links: Invoices, Process invoice, Purchase orders, Rules. Active link: ink text + 2 px ink underline offset 18 px. Right: server status dot (green "Live" / amber "Waking server" while health > 2 s / red "Offline") + model name in mono small. |
| `PageHeader` | `h1` + optional one-line `small` description in `--ink-2` + right-aligned actions. Bottom margin 24. |
| `Button` | Variants: `primary` (ink bg, white text), `secondary` (white bg, `--line-strong` border, ink text), `ghost` (text only), `danger` (reject colour text, reject-line border). Height 36 (sm 32). Padding x 14. Icon 16 left with 8 gap. Hover: primary → #2A2A2A; secondary → `--surface-sunken`. Pressed: translateY(0.5px). Disabled: 40% opacity, not-allowed cursor. Loading: spinner replaces icon, label stays. |
| `DecisionBadge` | Inline-flex, height 24, radius 6, padding x 8, tint bg + text colour + 1 px line border, 14 px icon + label (small, 600). Icons: APPROVE `CheckCircle2`, REVIEW `Eye`, HOLD `ShieldAlert`, REJECT `XCircle`. Running state: ink outline badge with spinning ring + "Running · {stage label}". Queued: `Clock` + "Queued". |
| `OutcomeIcon` | PASS `Check` approve colour; INFO `Info` ink-3; FLAG: icon by severity (REVIEW `AlertTriangle` review colour, HOLD `ShieldAlert` hold, REJECT `XOctagon` reject); SKIP `MinusCircle` ink-3. |
| `StageMarker` | 24 px circle. PENDING: 1.5 px `--line-strong` ring, number inside (mono 11). RUNNING: ink spinning ring. PASSED: approve-tint fill + check. FLAGGED: tint of highest severity among its checks + matching icon. FAILED: reject-tint + `X`. SKIPPED: dashed ring + `–`. |
| `KeyValue` | eyebrow label above, value below (body or mono). Grid of 2-4 per row. |
| `Money` | Formats rupees with `Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',minimumFractionDigits:2})` → `₹1,29,682.00`. Compact variant for KPIs: ≥1 crore `₹1.25 Cr`, ≥1 lakh `₹12.4 L`, else full. Always mono, tabular. |
| `DataTable` | White card, header row `--surface-sunken` with eyebrow labels, rows separated by hairlines, hover row `--surface-sunken`, whole row clickable (cursor pointer, `Enter` key works). Numeric columns right-aligned. Sticky header. |
| `ConsumptionBar` | 6 px tall track `--line`, filled segment ink for billed ≤100%, overflow segment in reject colour beyond 100% (bar scales to max(100, billed_pct)). Label right: `{billed_pct}% billed` mono small. |
| `Tabs` | Text tabs with 2 px ink underline on active, 40 px tall, hairline below. |
| `Disclosure` | "Show evidence" toggles a `<pre>`-like mono block (sunken bg, 12 px padding, radius 8, max-height 280 scroll). Render evidence dict as indented key: value lines, not raw JSON braces. |
| `Dialog` | Centered, 480 px, shadow-2, radius 12, padding 24, ESC closes, focus trapped, backdrop rgba(17,17,17,0.32). |
| `Toast` | Bottom-right, ink bg white text, 4 s, one at a time. |
| `Skeleton` | `--line` blocks with 1.4 s opacity pulse (0.5 ↔ 1). |
| `EmptyState` | Left-aligned inside the card (not centered page art): `h3` + one sentence + one button. |
| `Dropzone` | Dashed 1.5 px `--line-strong` border, radius 10, height 220, `Upload` icon 18, text "Drop an invoice PDF or image" + small "or browse · PDF, PNG, JPG up to 10 MB". Drag-over: ink border, sunken bg. Error inline in reject colour. |

## 9.8 Pages

### 9.8.1 Invoices (dashboard) `/` (Phase 6b)
1. PageHeader: `Invoices` / "Every invoice processed, with the decision and the reason." / primary button `Process invoice` (icon `Plus`) → `/new`.
2. KPI strip: one white card, 5 equal columns separated by vertical hairlines (not 5 separate cards). Each: eyebrow + `mono-lg` value + `small` caption.
   - PROCESSED · `{completed_runs}` · "{total_runs - completed} running" or "all complete"
   - AUTO-APPROVED · `{rate}%` · "{n} of {completed}"
   - AWAITING ACTION · `{awaiting_action}` · "needs review or on hold" (value in review colour if > 0)
   - VALUE PROCESSED · compact money · "across all invoices"
   - MEDIAN TIME · `{x.x} s` · "upload to decision"
3. Filter row (gap 12): segmented control `All · Approved · Needs review · On hold · Rejected` with counts in mono; search input (240 px, `Search` icon, placeholder "Vendor, invoice or PO") right-aligned. Filters sync to URL query (`?decision=REVIEW&q=...`).
4. Runs table columns: `RECEIVED` (relative "4 min ago", title attr absolute IST) · `INVOICE` (mono; under it small ink-3 filename) · `VENDOR` · `PO` (mono; inferred → small "inferred" outline tag) · `AMOUNT` (right, Money) · `DECISION` (DecisionBadge) · `REASON` (headline minus the label prefix, 1 line, ellipsis, max 320 px) · `TIME` (right, mono `3.4 s`) · `REVIEW` (Pending in review colour / "Approved by AP" / "Rejected by AP" / `·` for not required).
5. Live behaviour: refetch list + stats every 2 s while any run is QUEUED/RUNNING, else every 15 s. New rows fade in.
6. Empty: card with "No invoices processed yet" / "Run one of the sample invoices to see the pipeline work end to end." / button `Process invoice`.
7. Loading: skeleton KPI + 6 skeleton rows.

### 9.8.2 Process invoice `/new` (Phase 6c)
Two-column grid (7/5) on ≥1024, stacked below.
- Left card `Upload an invoice`: Dropzone; below it a checkbox `Use cached extraction when the same file was read before` (default checked) with small helper "Turn off to watch the model read the document live." Upload starts immediately on drop → navigate to `/runs/{id}`.
- Right card `Sample invoices`: grouped list (eyebrow per group). Each row: title (body-strong), filename (mono small ink-3), `Expected:` + DecisionBadge (small), and actions: ghost `Preview` (opens Dialog-sized PDF viewer, 720 px wide, `<iframe>` of `/api/samples/{id}/file`) and secondary `Run` (icon `Play`). Row description shown as small ink-2 text under the title (2 lines max).
- Above both cards: a slim info line (small, ink-2, `Info` icon): "Runs execute one at a time. Each run reads the invoice, checks it against the vendor master, the PO ledger and prior invoices, then decides."

### 9.8.3 Run detail / live run `/runs/:id` (Phase 6d) — the most important screen
Structure top to bottom:
1. **Breadcrumb + title row.** `Invoices / {invoice_number or filename}` (small ink-3, link). Title `h1`: invoice number in mono if known else filename. Right side: DecisionBadge (or running badge), elapsed timer (mono, live ticking while running, final duration after), secondary button `View document` (opens right drawer, §4).
2. **Decision panel** (white card, shadow-2, 4 px left rule in decision colour, padding 24, appears with 300 ms fade/translate when `run.completed` arrives). While running: same card at final height showing skeleton lines and the text "Decision appears when all eight stages finish." (ink-3).
   Content when done, in a 12-col grid:
   - Left (8 cols): eyebrow `DECISION` → `display` label in decision colour (e.g. "Needs review") → headline (body, ink-2) → `Reasons` list: each row OutcomeIcon + check name (body-strong) + message (body); → `Next steps` ordered list (body).
   - Right (4 cols): KeyValue stack: VENDOR, INVOICE / DATE, PO (with "inferred" tag), AMOUNT (mono-lg), PAY BY (approve) or PAYMENT ("Blocked" in hold/reject colour).
   - Footer row (top hairline, padding-top 16) only when `review_status == PENDING`: primary `Approve` + danger `Reject` buttons. Each opens Dialog: note textarea (required, ≥5 chars), reviewer name input (default "AP reviewer"), and for HOLD a required checkbox "I confirmed the bank change by calling the number on the vendor master." Submit → POST review → toast "Marked as approved" → panel shows a line `AP decision: Approved by {reviewer} · {time} · "{note}"`.
   - If `vendor_email` present: secondary button `Vendor email draft` → Dialog showing subject + body in a sunken mono-free (body font) block with `Copy` button. For HOLD show instead an inline callout (hold-tint bg, hold-line border, radius 8, padding 12): `ShieldAlert` + "Do not reply to the email this invoice came from. Call {vendor} on the number in the vendor master."
3. **Pipeline area**: 12-col grid, gap 24.
   - **Left (4 cols) `Pipeline` card**: list of 8 stages. Each row (min-height 56, padding 12, radius 8, clickable): StageMarker, then stage label (h3) and summary (small ink-2, 2 lines max) and right-aligned duration (mono small ink-3, e.g. `1.84 s`, blank while pending). A 1.5 px vertical connector line between markers (`--line`, turns ink once the upper stage completes). Selected row: sunken bg + 2 px ink left inset. Running row: summary shows "Running…" (one ellipsis char). Under the list: small ink-3 line "Stage timings are real. The UI holds each step on screen for at least 300 ms so you can follow it."
   - **Right (8 cols) detail card** with Tabs: `Stage` · `Extracted data` · `Event log`.
     - `Stage` tab: h2 stage label + description sentence (ink-2). Then the stage's checks list: rows with OutcomeIcon, check name (body-strong) + id (mono small ink-3), message, and `Show evidence` Disclosure. Then stage-specific output view (§9.9). Auto-follows the running stage; once the user clicks any stage, auto-follow stops and a ghost button `Follow live` appears in the card header (only while running).
     - `Extracted data` tab: available after extract. Table: FIELD (eyebrow-like label) · VALUE (mono where ID/number) · CONFIDENCE (40 px bar + %; bar colour ink, < 80% review colour). Then line items table (description, HSN, qty, UOM, rate, GST %, amount). Then a row `Method: Text layer · gemini-x · 2.1 s · cached` in small.
     - `Event log` tab: mono 12 px list, each line `14:02:11.348  stage.completed  extract  PASSED  2104 ms`. Auto-scroll to bottom while running unless the user scrolled up.
4. **Document drawer**: right side sheet 560 px (full width on mobile), shadow-2, header with filename + page count + close. Body: page images from `/pages/{n}.png` stacked with 16 gap, each in a white card. Footer: `Open original` link to `/document`.

**Client-side pacing (honest):** events are applied from a queue; each stage stays in RUNNING on screen for at least 300 ms before its `stage.completed` is applied. Displayed durations are always the real server values. Total added delay is bounded (≤ 2.4 s) and documented in the footnote above.

**Live data flow:** on mount `GET /api/runs/{id}`; if status not COMPLETED/FAILED, open `EventSource(`${API}/api/runs/${id}/events?after_seq=${lastSeqFromDetail}`)`; apply events to a local reducer (stages, checks, decision); on `run.completed` refetch detail once, close stream. If EventSource errors twice, fall back to polling detail every 1 s. Use an `aria-live="polite"` visually hidden region announcing "Extract complete", "Decision: Needs review".

### 9.8.4 Purchase orders `/purchase-orders` (Phase 6e)
PageHeader `Purchase orders` / "Open commitments and how much of each has been invoiced."
Table: PO (mono) · VENDOR · DATE · STATUS (Open / Closed text + dot) · VALUE (Money, net) · BILLED (ConsumptionBar 160 px + pct). Row expands inline (chevron) to show: line table (LINE, DESCRIPTION, ORDERED, BILLED, REMAINING (reject colour if negative), UNIT PRICE, GST) and `Invoices against this PO` list (invoice number mono, date, amount, ledger status as text badge, source "seeded history" or link "run {short_id}"). Below the table, a `Vendors` card: compact table VENDOR · GSTIN (mono) · STATUS · BANK (`HDFC Bank ••••5321`) · TERMS.

### 9.8.5 Rules `/rules` (Phase 6f)
Two cards. `How decisions are made`: the 4 decisions with badge + one-sentence meaning (from doc 07 §7.2 table) and the precedence line "Reject outranks Hold, Hold outranks Review." Then the full check catalogue table: ID (mono) · CHECK · STAGE · CAN ROUTE TO (badges). `Thresholds`: KeyValue grid from `/api/config` (e.g. PRICE TOLERANCE "1% or ₹1,000 per line, whichever is lower"). `Demo data` (only if demo_mode): text "Resets vendors, POs and the invoice ledger to their starting state. Cached extractions are kept." + danger button `Reset demo data` → Dialog requiring typing `RESET`.

## 9.9 Stage-specific output views (inside Stage tab)
- ingest: KeyValue grid: FILE, SIZE, PAGES, TEXT LAYER (Yes / No, scanned), SHA-256 (mono, first 16 chars + copy).
- extract: METHOD, MODEL, CACHED, LATENCY; link "See all extracted fields" switches tab.
- normalize: small table of normalisations performed: field · as printed · normalised (e.g. invoice number `BIS/INV/26/89` → `BIS-INV-26-89`, date, tax-inclusive conversions).
- vendor: matched vendor card-row: name, GSTIN, status, method; bank comparison two-column mini table "On invoice / On vendor master" with mismatching cells in hold colour.
- duplicates: candidates checked count; if hit, side-by-side compare table (field · this invoice · ledger invoice), matching cells highlighted with approve-tint.
- po_match: PO + method; if inferred, candidate table (PO · coverage · amount fit · date bonus · score) with the winner row bold; line pairing table (invoice line → PO line, score).
- reconcile: per line table: LINE · ORDERED · ALREADY BILLED · THIS INVOICE · REMAINING AFTER · PRICE VAR. Over-billed cells reject-coloured. Plus a ConsumptionBar showing before → after.
- decide: decision summary text (same as panel) and "Precedence applied: {list of severities found} → {decision}".

## 9.10 Responsiveness & accessibility (Phase 6g)
- Breakpoints: 640, 1024, 1280. Below 1024 the pipeline grid stacks (stage list first, collapsible). Tables become horizontally scrollable inside their card (never the page).
- All interactive elements reachable by keyboard; visible focus ring `outline: 2px solid var(--focus); outline-offset: 2px`.
- Text contrast ≥ 4.5:1. Touch targets ≥ 36 px.
- Every icon-only button has `aria-label`.

## 9.11 Copy rules
Sentence case everywhere except eyebrows. Numbers: Indian grouping. Dates: `12 Nov 2026`; times `14:02` IST; relative times under 24 h. Plain verbs: "Approve", "Reject", "Run", not "Submit". Error messages say what happened and what to do: "Upload failed: only PDF, PNG or JPG up to 10 MB."

## 9.12 Phase 6 acceptance checklist (tick in PROGRESS.md)
- [ ] Fonts load self-hosted; headings show lining numerals.
- [ ] Only colours from §9.4 appear (grep the CSS for hex values outside the token file → zero).
- [ ] Running F01 shows each of 8 stages go pending → running → passed in order with real durations, decision panel reveals APPROVE.
- [ ] F05 shows HOLD, bank comparison highlighted, no vendor email, callout present, approve requires the checkbox.
- [ ] F02 reconcile view shows over-billing in red, ConsumptionBar overflow on PO page after AP approves it.
- [ ] Dashboard updates live while a run is in progress.
- [ ] Reload the run page mid-run: it resumes from the right stage with no duplicated checks.
- [ ] Lighthouse accessibility ≥ 95 on `/` and `/runs/:id`.
- [ ] 1280 px and 390 px screenshots of every page reviewed for spacing consistency (only scale values).
- [ ] Taste-skill final checklist run; violations fixed or justified in PROGRESS.md.
