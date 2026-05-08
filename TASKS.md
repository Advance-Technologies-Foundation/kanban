# Test Implementation Tasks

Each task below is one pytest function to add to the `tests/` directory.
The [filter bug v1.7.1] is resolved — all tasks here are new test coverage.

**Priority legend:**
- **P0** — blocks release; suite must be green before shipping
- **P1** — covers a named feature; should be green for confident release
- **P2** — edge cases and UX details; add opportunistically

**Workflow:** pick a task → write the failing test stub → implement → mark `[x]`.
Follow the bug-fix workflow in CLAUDE.md (test first, then code, then verify full suite).

---

## File layout

| File | Test group |
|---|---|
| `tests/test_kanban_filters.py` | Filter behaviour (existing + extensions) |
| `tests/test_kanban_board.py` | View switching, board structure |
| `tests/test_kanban_pagination.py` | Load More |
| `tests/test_kanban_dnd.py` | Drag-and-drop / card move |
| `tests/test_kanban_settings.py` | Last-stage filter, column settings |

---

## P0 — Release blockers

### [x] test_switch_to_kanban_view
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Open Opportunity section (already in list view via `kanban_page` fixture).
2. Click the Kanban view icon: `[data-item-marker="Kanban"]` (verify selector in browser; may be `[data-item-marker="KanbanDataView"]`).
3. Wait for `.dcm-stage-wrap`.  

**Assert:** at least one `.dcm-stage-wrap` element is visible.  
**Notes:** `kanban_page` fixture already opens in Kanban; for this test use a dedicated context that starts in Grid mode. Alternatively, switch to Grid first with `_switch_to_grid(page)` helper, then switch back.

---

### [x] test_switch_back_to_grid_view
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Start in Kanban view (use `kanban_page`).
2. Click Grid view icon: `[data-item-marker="GridDataView"]`.
3. Wait for the grid to appear (`.grid-listed-view` or `.grid-dataview-wrap`).  

**Assert:** `.dcm-stage-wrap` is not visible; grid container is visible.

---

### [x] test_drag_card_to_adjacent_column
**File:** `tests/test_kanban_dnd.py`  
**Steps:**
1. Open Kanban, note column counts for columns A and B (adjacent).
2. Find a card in column A: first `.dcm-stage-element-view-wrap` inside the first `.dcm-stage-wrap`.
3. Playwright drag: `page.drag_and_drop(source_selector, target_selector)`.
4. Wait for network idle.  

**Assert:** `count(A) == old_count(A) - 1`, `count(B) == old_count(B) + 1`, sum unchanged.  
**Notes:** Drag target is the `.dcm-stage-wrap` of column B, not a card inside it.
Counts come from `.kanban-column-summary` text. After drop, wait for `afterKanbanElementSaved` — approximate with `_idle(page, 10000)`.

---

### [x] test_drag_card_updates_column_counts
**File:** `tests/test_kanban_dnd.py`  
**Steps:** Same setup as above.  
**Assert:** total `count_total(cols_before) == count_total(cols_after)` — no record created or deleted on move.

---

### [x] test_load_more_button_visible_when_has_more
**File:** `tests/test_kanban_pagination.py`  
**Steps:**
1. Open Kanban with no filters (use `kanban_page`, ~101 total records across columns).
2. Find the Load More button: `[data-item-marker="LoadMore"]`.  

**Assert:** button is visible.  
**Notes:** The button renders only when `LoadMoreButtonVisible == true`, which is set by `checkAllDataLoaded` when any column has `totalCount > currentCount`. With 101 records and 7-per-page, at least one column will exceed the page size.

---

### [x] test_load_more_increases_visible_card_count
**File:** `tests/test_kanban_pagination.py`  
**Steps:**
1. Count total visible cards: `document.querySelectorAll('.dcm-stage-element-view-wrap').length`.
2. Click `[data-item-marker="LoadMore"]`.
3. Wait for `_idle(page, 15000)`.
4. Count again.  

**Assert:** new count > old count.

---

### [x] test_double_click_card_opens_edit
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Double-click the first card: `.dcm-stage-element-view-wrap >> nth=0`.
2. Wait for edit page or mini-page to appear (`.minipage-container` or a new URL hash containing `edit`).  

**Assert:** an edit panel or full edit page is visible.  
**Notes:** `onElementDblClick` calls `openEditMiniPage` or `editRecord`. A mini-page will appear as `.minipage-container`; a full page will change the URL hash. Check both.

---

### [x] test_clear_period_filter_restores_baseline
**File:** `tests/test_kanban_filters.py`  
**Steps:**
1. Note baseline total (no filters).
2. Apply "Previous month" (`apply_prev_month`).
3. Clear: `_clear_all_filters`.
4. Note restored total.  

**Assert:** restored total == baseline total (within ±1 to allow for records created during test run).

---

### [x] test_clear_owner_filter_restores_baseline
**File:** `tests/test_kanban_filters.py`  
**Steps:**
1. Note baseline total.
2. `set_owner(page, "Mary King")`.
3. `_clear_all_filters`.
4. Note restored total.  

**Assert:** restored total == baseline total.

---

## P1 — Important feature coverage

### [ ] test_kanban_icon_visible_in_toolbar
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Open Opportunity section URL directly in a fresh context (Grid mode, before Kanban ever activated).
2. Wait for grid to load.  

**Assert:** `[data-item-marker="Kanban"]` (or equivalent) is present in DOM and visible.  
**Notes:** If profile already has `ActiveView=Kanban`, this test is trivially true in the kanban fixture. Use a separate context starting from Grid.

---

### [ ] test_column_count_matches_dcm_stages
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Count `.dcm-stage-wrap` elements.  

**Assert:** count == expected number of Opportunity DCM stages (hardcode the known value for this env; note it in the test docstring).  
**Notes:** If DCM stages ever change, this test will catch unexpected schema changes.

---

### [ ] test_each_column_has_count_badge
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Get all `.dcm-stage-wrap` wrappers.
2. For each, find `.kanban-column-summary`.  

**Assert:** every column wrapper contains exactly one count badge.

---

### [ ] test_columns_have_stage_names
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Collect all `.stage-tools .t-label` texts.  

**Assert:** list is non-empty; each item is a non-empty string; list matches the known expected stage names (document them in the test docstring).

---

### [ ] test_current_month_filter_returns_records
**File:** `tests/test_kanban_filters.py`  
**Steps:**
1. Open period dropdown: `[data-item-marker="month"] .t-btn-menuWrap`.
2. Click "Current month".
3. Wait `_idle`.  

**Assert:** `count_total > 0`.  
**Notes:** Tests the "current month" code path separately from "previous month". Uses the same period dropdown as `apply_prev_month`; factor out a `apply_period(page, label)` helper.

---

### [ ] test_owner_filter_narrows_per_column
**File:** `tests/test_kanban_filters.py`  
**Steps:**
1. Note baseline total.
2. `set_owner(page, "Mary King")`.
3. Note filtered total.  

**Assert:** filtered total < baseline total.  
**Notes:** More precise than the existing `test_owner_filter_returns_records` which only checks `> 0`.

---

### [ ] test_period_then_owner_gives_same_result_as_owner_then_period
**File:** `tests/test_kanban_filters.py`  
**Steps:**
1. Apply period first, then owner → record `total_A`.
2. `_clear_all_filters`.
3. Apply owner first, then period → record `total_B`.  

**Assert:** `total_A == total_B`.  
**Notes:** Verifies that filter combination is commutative (order-independent).

---

### [ ] test_kanban_view_persists_after_reload
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Ensure Kanban is active (use `kanban_page`).
2. `page.reload()`.
3. Wait for `_idle(page, 30000)`.  

**Assert:** `.dcm-stage-wrap` is visible without re-clicking the Kanban icon.  
**Notes:** Tests that `getDefaultDataViews` reads `ActiveView=Kanban` from profile on re-init.

---

### [ ] test_sort_summary_buttons_hidden_in_kanban
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. In Kanban mode, look for Sort and Summary buttons (selectors TBD — inspect toolbar in browser; likely `[data-item-marker="SortMenu"]` and `[data-item-marker="SummarySettings"]`).  

**Assert:** both are either absent from DOM or have `display:none` / `visibility:hidden`.  
**Notes:** `KanbanSection.setActiveView` sets `IsSortMenuVisible = false` and `IsSummarySettingsVisible = false`.

---

### [ ] test_load_more_button_hides_after_full_load
**File:** `tests/test_kanban_pagination.py`  
**Steps:**
1. Click Load More repeatedly until button disappears (loop with a max iteration guard).
2. Detect via `page.query_selector('[data-item-marker="LoadMore"]')` returning `None` or button not visible.  

**Assert:** button eventually disappears, indicating `allDataLoaded = true` was fired.  
**Notes:** Only feasible if dataset is small enough to exhaust in a few pages. Apply a tight filter first to limit total records.

---

### [ ] test_setup_last_stage_filter_option_visible_in_kanban
**File:** `tests/test_kanban_settings.py`  
**Steps:**
1. In Kanban mode, open view options menu (button usually labelled with gear/settings icon; inspect DOM for `data-item-marker`).
2. Look for menu item with text "Setup last stage filter".  

**Assert:** item is present and visible.

---

### [ ] test_setup_last_stage_filter_option_hidden_in_grid
**File:** `tests/test_kanban_settings.py`  
**Steps:**
1. Switch to Grid mode.
2. Open view options menu.
3. Look for "Setup last stage filter".  

**Assert:** item is absent or has `visible: false`.  
**Notes:** `_showLastStageClear` and the `Visible: {bindTo: "_isKanban"}` binding control visibility.

---

### [ ] test_last_stage_filter_narrows_terminal_column
**File:** `tests/test_kanban_settings.py`  
**Steps:**
1. Note current card count in the last/terminal column (identify it by `IsLast` — visually it is rendered differently; find via `.dcm-stage-unsuccessful` or the last `.dcm-stage-wrap`).
2. Set a last-stage filter using a folder that covers a subset of records.
3. Wait for reload.  

**Assert:** terminal column count < previous count; other columns unchanged.  
**Notes:** Requires a pre-existing folder filter in the Opportunity Folders lookup. Document which folder to use for the test env.

---

### [ ] test_clear_last_stage_filter_restores_terminal_column
**File:** `tests/test_kanban_settings.py`  
**Steps:**
1. Set last stage filter (prerequisite from previous test or inline).
2. Open view options → click "Clear last stage filter (…)".
3. Wait for reload.  

**Assert:** terminal column count == original count.

---

### [ ] test_last_stage_filter_persists_after_reload
**File:** `tests/test_kanban_settings.py`  
**Steps:**
1. Set a last stage filter.
2. `page.reload()`.
3. Wait for Kanban to load.  

**Assert:** terminal column still shows narrowed count (filter reloaded from profile).  
**Notes:** Tests `_loadKanbanProfile` reading `lastStageFilterId`.

---

### [ ] test_dcm_case_button_visible_in_kanban
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. In Kanban mode, check for DCM case selector: `[data-item-marker="DcmCase"]` (inside `.case-filter` container).  

**Assert:** button is visible.

---

### [ ] test_dcm_case_button_hidden_in_grid
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Switch to Grid mode.
2. Check for `.case-filter` container or `[data-item-marker="DcmCase"]`.  

**Assert:** not visible (`.case-filter` has `hiddenControl: true`).  
**Notes:** `getKanbanDomAttributes` drives this binding.

---

## P2 — Edge cases and UX details

### [ ] test_no_records_for_far_future_period
**File:** `tests/test_kanban_filters.py`  
**Steps:**
1. Apply a custom date filter for a date far in the future (if the quick filter supports manual date input; otherwise skip or use a known empty period).
2. Wait for reload.  

**Assert:** `count_total == 0`.  
**Notes:** Validates that a zero-result filter does not break the board (no JS errors, columns still rendered).

---

### [ ] test_card_shows_primary_display_column
**File:** `tests/test_kanban_board.py`  
**Steps:**
1. Collect text from the first few card titles: `.dcm-stage-element-view-wrap .element-caption` (verify selector).  

**Assert:** each text is non-empty.  
**Notes:** `KanbanElementViewModel.getViewConfig` binds `caption` to `primaryDisplayColumnName`.

---

### [ ] test_kanban_settings_opens_column_configurator
**File:** `tests/test_kanban_settings.py`  
**Steps:**
1. In Kanban mode, click the Settings/Grid Settings button (typically `[data-item-marker="GridSettings"]`).
2. Wait for the grid settings module to open.  

**Assert:** a Kanban-specific column configurator appears (check for `isSingleTypeMode` tiled layout header or a panel title containing "Kanban").  
**Notes:** `openGridSettings` dispatches to `_openKanbanGridSettings` when in Kanban mode, which loads `GridSettingsV2` with `propertyName: "KanbanColumnSettings"`.

---

### [ ] test_column_badge_shows_total_not_just_loaded_page
**File:** `tests/test_kanban_pagination.py`  
**Steps:**
1. On initial load (7 cards per column), read the count badge of a column with >7 records.
2. Read the number of rendered card elements in that column.  

**Assert:** badge value > rendered card count (badge shows server total, not page size).  
**Notes:** `loadcount` event sets `RecordsCount` which drives the badge; `rowCount: 7` limits rendered cards.

---

## Shared helpers to add in `conftest.py`

These helpers are needed by multiple tests above — add them once to `conftest.py`:

```python
async def switch_to_grid(page):
    """Click Grid view icon and wait for grid to render."""

async def switch_to_kanban(page):
    """Click Kanban view icon and wait for .dcm-stage-wrap."""

async def apply_period(page, label: str):
    """Open period dropdown and click a named period item (e.g. 'Current month')."""

async def count_visible_cards(page) -> int:
    """Count rendered .dcm-stage-element-view-wrap elements across all columns."""

async def get_column_count_by_index(page, index: int) -> int:
    """Return the numeric count badge of the nth column."""

async def get_terminal_column_count(page) -> int:
    """Return the count badge of the last (terminal) column."""
```

---

## Known selectors (verify in browser before using)

| Element | Selector | Confidence |
|---|---|---|
| Kanban view icon | `[data-item-marker="Kanban"]` | Unverified — inspect toolbar |
| Grid view icon | `[data-item-marker="GridDataView"]` | Unverified |
| Sort menu button | `[data-item-marker="SortMenu"]` | Unverified |
| Summary settings | `[data-item-marker="SummarySettings"]` | Unverified |
| Load More button | `[data-item-marker="LoadMore"]` | Likely — matches diff `name: "LoadMore"` |
| Card element | `.dcm-stage-element-view-wrap` | Verify |
| Card title | `.dcm-stage-element-view-wrap .element-caption` | Verify |
| DCM case button | `[data-item-marker="DcmCase"]` | Likely — matches diff `name: "DcmCase"` |
| View options menu | `[data-item-marker="ViewOptions"]` | Unverified |
| Terminal column | last `.dcm-stage-wrap` or `.dcm-stage-unsuccessful` | Verify |
| Kanban column config | see GridSettingsV2 panel title | Inspect after opening |
