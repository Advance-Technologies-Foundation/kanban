"""
Regression tests for Kanban filter behaviour in OpportunitySectionV2.

Bug history:
  v1.7.0 – CaseDataStorage.createDcmFilters serialised the section filter
            with serializeFilterManagerInfo=true, which corrupted dynamic
            period filters (e.g. "Previous month") when combined with a
            lookup filter (e.g. owner).  Fixed in v1.7.1 by removing the
            serialize/deserialize and using filters.addItem(this.filters)
            directly (same pattern as ActivityDataStorage).

Test environment assumptions (185574-crm-bundle.creatio.com / clio user):
  - Total opportunities: ~101
  - April 2026 (previous month as of 2026-05-08): 11 records
  - Mary King owns 16 opportunities, 4 of which fall in April 2026
"""

import pytest
import pytest_asyncio

from conftest import (
    read_column_counts,
    count_total,
    apply_prev_month,
    set_owner,
    _clear_all_filters,
    _idle,
)


@pytest.mark.asyncio
async def test_baseline_has_records(kanban_page):
    """Sanity: unfiltered board shows a non-zero record count."""
    cols = await read_column_counts(kanban_page)
    assert count_total(cols) > 0, f"Expected records with no filter, got: {cols}"


@pytest.mark.asyncio
async def test_previous_month_filter_returns_records(kanban_page):
    """
    Regression: applying 'Previous month' date filter must not zero out all columns.

    Buggy build (v1.7.0 without the c1beddc partial fix): returned 0 for
    certain combinations.  This test catches the date-only case.
    """
    await apply_prev_month(kanban_page)
    cols = await read_column_counts(kanban_page)
    total = count_total(cols)
    assert total > 0, (
        f"'Previous month' filter returned 0 records — possible filter serialization bug.\n"
        f"Columns: {cols}"
    )
    await _clear_all_filters(kanban_page)


@pytest.mark.asyncio
async def test_owner_filter_returns_records(kanban_page):
    """Sanity: owner filter alone must not zero out all columns for an owner with records."""
    selected = await set_owner(kanban_page, "Mary King")
    assert selected, "Could not select owner in lookup"

    cols = await read_column_counts(kanban_page)
    total = count_total(cols)
    assert total > 0, (
        f"Owner filter for '{selected}' returned 0 records — owner may have changed.\n"
        f"Columns: {cols}"
    )
    await _clear_all_filters(kanban_page)


@pytest.mark.asyncio
async def test_owner_plus_previous_month_returns_records(kanban_page):
    """
    Regression for bug fixed in v1.7.1:

    Combining an owner filter with 'Previous month' must not zero out all
    columns when that owner has records in the previous month.

    Root cause: CaseDataStorage.createDcmFilters was calling
      this.filters.serialize({serializeFilterManagerInfo: true})
    which embedded FilterManager context into the filter, breaking
    dynamic period evaluation when the filter was used in a column ESQ.

    Fix: pass this.filters directly via filters.addItem(this.filters).
    """
    selected = await set_owner(kanban_page, "Mary King")
    assert selected, "Could not select owner in lookup"

    # Verify owner alone has records (precondition)
    cols_owner = await read_column_counts(kanban_page)
    owner_total = count_total(cols_owner)
    assert owner_total > 0, f"Precondition failed: '{selected}' has 0 records total"

    # Now add the period filter
    await apply_prev_month(kanban_page)
    cols = await read_column_counts(kanban_page)
    total = count_total(cols)

    assert total > 0, (
        f"Owner '{selected}' + 'Previous month' returned 0 records.\n"
        f"Owner alone had {owner_total} records.\n"
        f"This is the v1.7.0 filter serialization bug.\n"
        f"Columns: {cols}"
    )

    await _clear_all_filters(kanban_page)
