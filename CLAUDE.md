# Kanban — Creatio Package Dev Guide

## What this project is

A **Creatio (Terrasoft) platform package** that adds a Kanban board view to any section.
It extends `BaseSectionV2` so every entity section can switch to Kanban view via a toolbar icon.

The package lives in `Kanban/` (the Creatio-deployable artifact).
Source lives in `src/` and is compiled to `Kanban/Files/src/kanban-min.js` by `build.js`.

---

## Repository layout

```
kanban/
├── src/                          ← EDIT THESE
│   ├── KanbanSection.js          ← outer AMD define wrapper + mixin object (attributes/methods)
│   ├── CaseDataStorage.js        ← Terrasoft.CaseDataStorage + ActivityDataStorage
│   ├── CollectionDataStorage.js  ← Terrasoft.Kanban.DataStorage (paginated ESQ)
│   ├── KanbanBoard.js            ← Terrasoft.controls.KanbanBoard (Ext control)
│   ├── KanbanBoardViewGenerator.js ← KanbanBoardViewGenerator AMD module
│   ├── KanbanColumn.js           ← Terrasoft.controls.KanbanColumn (Ext control)
│   ├── KanbanColumnViewConfigBuilder.js ← view config factory
│   ├── KanbanColumnViewModel.js  ← Terrasoft.controls.KanbanColumnViewModel
│   ├── KanbanElement.js          ← Terrasoft.controls.KanbanElement (card Ext control)
│   ├── KanbanElementViewModel.js ← Terrasoft.controls.KanbanElementViewModel
│   ├── css/
│   │   ├── KanbanBoard.css
│   │   ├── KanbanColumn.css
│   │   └── KanbanElement.css
│   ├── Enable_kanban_for_Activity.sql  ← one-time Postgres script to enable Activity Kanban
│   └── require.config.txt              ← local dev RequireJS config (not used in build)
│
├── Kanban/                       ← Creatio package (deploy this)
│   ├── descriptor.json           ← package metadata (v1.7.0, depends on ProductCore 7.8+)
│   ├── Files/src/
│   │   ├── kanban-min.js         ← BUILD OUTPUT — do not edit directly
│   │   ├── kanban-min.css        ← BUILD OUTPUT — do not edit directly
│   │   └── bootstrap.js          ← RequireJS bundle config loaded by Creatio
│   ├── Schemas/
│   │   ├── BaseSectionV2/        ← re-exports KanbanSection mixin into the platform's BaseSectionV2
│   │   ├── MainHeaderSchema/     ← small fix: respects `visible` on icon buttons
│   │   └── KanbanEmptyModule/    ← placeholder (empty)
│   ├── Data/SysSettings_KanbanCDNUrl/  ← optional CDN URL system setting
│   └── Resources/                ← localisation strings
│
├── build.js                      ← build script (Node.js, no dependencies)
└── package.json
```

---

## Build

```bash
npm run build          # one-shot build → writes Kanban/Files/src/kanban-min.js + kanban-min.css
npm run watch          # same, but rebuilds on every src/ save
```

No npm packages required — `build.js` uses only Node.js built-ins.

### How the build works

`KanbanSection.js` is an AMD `define("KanbanSection", [...deps...], function() { return { ... }; })` wrapper.
All other `src/*.js` files are injected **inside** that function, just before its `return {` statement.
`KanbanBoardViewGenerator.js` keeps its own nested `define()` call — that is intentional (RequireJS bundle pattern).

The `MainHeaderSchema` dependency is added to the define deps list by the build script
(it is not in the source `KanbanSection.js` to keep the source clean).

CSS files are concatenated: `KanbanElement.css` → `KanbanColumn.css` → `KanbanBoard.css`.

---

## Architecture

### Data layer

| Class | File | Role |
|---|---|---|
| `Terrasoft.CaseDataStorage` | CaseDataStorage.js | Column collection for DCM-based sections (cases/stages) |
| `Terrasoft.ActivityDataStorage` | CaseDataStorage.js | Column collection for Activity section (uses `ActivityStatus` ESQ) |
| `Terrasoft.Kanban.DataStorage` | CollectionDataStorage.js | Per-column paginated card collection |

`CaseDataStorage` / `ActivityDataStorage` extend `BaseViewModelCollection`.
Each item is a `KanbanColumnViewModel`.
Each column holds a `Terrasoft.Kanban.DataStorage` instance in its `ViewModelItems` attribute.

### View layer (Ext controls)

| Control | File | Extends |
|---|---|---|
| `Terrasoft.KanbanBoard` | KanbanBoard.js | `Terrasoft.DcmStageContainer` |
| `Terrasoft.KanbanColumn` | KanbanColumn.js | `Terrasoft.DcmStage` |
| `Terrasoft.KanbanElement` | KanbanElement.js | `Terrasoft.DcmStageElement` |

### ViewModel layer

| Class | File | Extends |
|---|---|---|
| `Terrasoft.KanbanColumnViewModel` | KanbanColumnViewModel.js | `Terrasoft.DcmStageViewModel` |
| `Terrasoft.KanbanElementViewModel` | KanbanElementViewModel.js | `Terrasoft.DcmStageElementViewModel` |

### Section mixin (`KanbanSection.js`)

Mixed into `BaseSectionV2` via the Creatio schema override in `Schemas/BaseSectionV2/`.
Key methods:

- `init` — loads kanban profile (column settings, last-stage filter), then initialises storage
- `_isKanban()` — `true` when `ActiveViewName === "Kanban"`
- `_loadKanbanStorage()` — dispatches to `_loadCaseKanbanStorage` or `_loadActivityKanbanStorage`
- `_setKanbanFilter(filters, lastStageFilters)` — pushes section filters into `CaseDataStorage`
- `loadMore` — loads the next page of cards when user scrolls to bottom
- `moveKanbanElement(elementId, unsuccessfulColumnId)` — handles drag-to-unsuccessful-column

---

## Key concepts

### Kanban view activation
A "Kanban" entry is added to `DataViews` dynamically in `getDefaultDataViews` (lazy, only when DCM cases exist or `EnableKanbanForActivitySection` feature flag is on).

### DCM vs Activity mode
- **DCM mode** (default): columns come from DCM case stages via `DcmSchemaManager`. Enabled when `DcmCase` lookup resolves.
- **Activity mode**: columns come from `ActivityStatus` lookup. Enabled by feature flag `EnableKanbanForActivitySection`. SQL to enable: `src/Enable_kanban_for_Activity.sql`.

### Drag-and-drop
Cards are `Terrasoft.DcmStageElement` (drag source).
Columns are `Terrasoft.DcmReorderableContainer` (drop zone) with `groupName` = array of connected column IDs.
Unsuccessful/terminal columns appear as a fixed bottom bar when dragging; registered as `DDTarget`.

### Last-stage filter
Users can configure a folder-based filter applied only to the terminal stage's cards.
Stored in the kanban profile (`lastStageFilterId`).

### Pagination
`Terrasoft.Kanban.DataStorage` loads 7 cards per column by default (`rowCount: 7`).
The board fires `loadMore` on window scroll-to-bottom; the section calls `storage.loadData()` to append the next page.

---

## Release build (packaging for installation)

All intermediate files go into `builds/` — never into the project root.

```bash
mkdir -p builds
npm run build
clio generate-pkg-zip Kanban -d builds/Kanban.gz
cd builds && zip Kanban.zip Kanban.gz && cd ..
```

Result: `builds/Kanban.zip` — ready to upload via Creatio UI Package Installer.

### Why this structure
- `builds/Kanban.gz` — clio binary format (proprietary, not tar.gz); required by `generate-pkg-zip`
- `builds/Kanban.zip` — zip wrapping the `.gz`; what the Creatio UI `UploadPackage` endpoint accepts
- Uploading `.gz` directly → HTTP 400
- Uploading a zip with raw package files (not wrapping `.gz`) → "name does not match descriptor.json"
- The zip filename and the `.gz` filename inside **must** match `"Name"` in `Kanban/descriptor.json` exactly (i.e. `Kanban`)

### Install via CLI (no zip needed)
```bash
clio push-pkg Kanban -e <env-name>
```

## Deploying to Creatio

1. `npm run build`
2. Build the install package: see **Release build** section above.
3. Upload `builds/Kanban.zip` via **Configuration → Packages → Install package from file**.
4. The `bootstrap.js` is loaded automatically when the section page opens; it registers `KanbanSection` as an AMD bundle.

---

## Common tasks

### Add a new method to the section mixin
Edit `src/KanbanSection.js` inside the `methods: { ... }` object, then `npm run build`.

### Change card rendering (columns, layout)
Edit `src/KanbanElementViewModel.js` (`getViewConfig`, `generateAdditionalColumnViewConfig`).
Card CSS is in `src/css/KanbanElement.css`.

### Change column header / layout
Edit `src/KanbanColumnViewConfigBuilder.js` (view config) or `src/KanbanColumn.js` (Ext control / template).
Column CSS is in `src/css/KanbanColumn.css`.

### Add a drag-and-drop behaviour
The entry point is `KanbanColumnViewModel.move()` (called when a card is dropped into a column).
`KanbanBoard.onElementDragDrop()` handles drops on unsuccessful columns.

### Change pagination page size
Set `pageRowCount` on `CaseDataStorage` / `ActivityDataStorage` or `rowCount` on the `Terrasoft.Kanban.DataStorage` created inside `createColumn()`.

---

## Bug-fix workflow (mandatory)

Every bug fix **must** follow this sequence — no exceptions:

1. **Write a failing reproduction test first.**
   Add a test in `tests/test_kanban_filters.py` (or a new file) that fails on
   the current code and captures the exact symptom reported.
   Run it to confirm it fails: `pytest tests/ -k <test_name>`.

2. **Fix the code.**
   Edit the relevant `src/` file(s).

3. **Rebuild.**
   `npm run build`

4. **Deploy to the test environment.**
   `clio push-pkg Kanban -e kanban`

5. **Run the full test suite and confirm:**
   - The new reproduction test now **passes**.
   - All previously passing tests still **pass**.
   ```
   pytest tests/ -v
   ```

A fix is not done until step 5 is green.

---

## Tests

End-to-end Playwright tests live in `tests/`.
They run against the live Creatio environment defined by `KANBAN_BASE_URL`.

### Setup (one-time)

```bash
pip install -r tests/requirements.txt
playwright install chromium
```

### Run

```bash
# against default env (185574-crm-bundle.creatio.com, user clio)
pytest tests/ -v

# against a different env
KANBAN_BASE_URL=https://my-env.creatio.com \
KANBAN_USER=admin \
KANBAN_PASSWORD=secret \
pytest tests/ -v
```

### Selector reference (Opportunity Kanban, ExtJS shell)

| Element | Selector |
|---|---|
| Kanban loaded | `.dcm-stage-wrap` |
| Column caption | `.stage-tools .t-label` |
| Column record count | `.kanban-column-summary` |
| Month period dropdown | `[data-item-marker="month"] .t-btn-menuWrap` |
| Clear period filter | `[data-item-marker="clearPeriodFilter"]` |
| Owner filter button | `[data-item-marker="OwnerFixedFilterBtn"]` |
| Lookup search input | `#searchEdit-el` |
| Lookup search button | `[data-item-marker="searchButton"]` |
| Lookup result rows | `.containerLookupPage .grid-primary-column` |
| Lookup confirm button | `[data-item-marker="selectButton"]` |
| Login username | `#loginEdit-el` |
| Login password | `#passwordEdit-el` |
| Login submit | `.t-btn-style-green` |

**Notes:**
- The Kanban board lives inside a Freedom UI shell (`crt-` web components) that
  wraps the ExtJS section. Wait for `.dcm-stage-wrap`, not a fixed timeout.
- The owner filter label (`OwnerFixedFilterBtn` inner text) is unreliable —
  verify by checking record counts, not the label.
- Double-click a lookup row to select; then click `selectButton` if the dialog
  stays open.
- Always call `force_clear_owner` / `clearPeriodFilter` before each test to
  avoid filter state leaking across runs.

---

## Test task list

Planned tests to implement before each release are tracked in `TASKS.md`.

### Structure of TASKS.md

Each entry is one pytest function with this shape:

```
### [x/space] test_function_name — one-line description
**File:** tests/test_xxx.py
**Steps:** numbered implementation steps
**Assert:** what must be true
**Notes:** tricky details, selector caveats
```

Priorities:
- **P0** — suite must be fully green to ship
- **P1** — named features; needed for confident release
- **P2** — edge cases; add opportunistically

### Adding a new planned test

1. Add a `### [ ] test_name` entry to the appropriate priority block in `TASKS.md`.
2. Specify file, steps, assert, and any known selector hints.
3. When implemented, change `[ ]` → `[x]`.

### Picking up a task

1. Find an unchecked `[ ]` item in `TASKS.md`.
2. Follow the mandatory **Bug-fix workflow** above (write stub → confirm it fails → implement → full suite green).
3. Mark the checkbox `[x]` and commit together with the test file.

### Release gate

Before tagging a release, run:

```bash
pytest tests/ -v
```

All P0 tests must pass. P1 failures should be investigated and either fixed or explicitly deferred with a comment. P2 failures are acceptable to defer.

### Shared helpers

Common Playwright helpers live in `tests/conftest.py`.
When multiple tests need the same interaction, extract it into `conftest.py` rather than duplicating.
Planned helpers to add (see TASKS.md) include:
`switch_to_grid`, `switch_to_kanban`, `apply_period`, `count_visible_cards`,
`get_column_count_by_index`, `get_terminal_column_count`.

---

## Platform dependencies (do not vendor)

All of these are provided at runtime by the Creatio platform:
`Terrasoft`, `Ext`, `define` (AMD/RequireJS), `DcmStageContainer`, `DcmStage`, `DcmStageElement`,
`DcmStageViewModel`, `DcmStageElementViewModel`, `DcmSchemaManager`, `DcmElementSchemaManager`,
`BaseViewModelCollection`, `EntitySchemaQuery`, `PageUtilities`, `ConfigurationEnums`, `GridUtilities`.
