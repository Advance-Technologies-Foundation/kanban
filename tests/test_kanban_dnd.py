"""
P0 tests for Kanban drag-and-drop card moving.

Badge counts (.kanban-column-summary) show server-side totals, which update
synchronously via CollectionDataStorage._setTotalCount when insert/removeByIndex
fires on the collection, before the server save callback.
"""

import pytest

from conftest import (
    _clear_all_filters,
    _idle,
    get_column_count_by_index,
    read_column_counts,
    count_total,
)


async def _drag_first_card_to_next_column(page):
    """Drag the first card in column 0 onto column 1. Returns (count_A_before, count_B_before)."""
    count_a = await get_column_count_by_index(page, 0)
    count_b = await get_column_count_by_index(page, 1)

    source = page.locator('.dcm-stage-wrap').first.locator('.dcm-stage-element-view-wrap').first
    target = page.locator('.dcm-stage-wrap').nth(1)

    await source.drag_to(target)
    # Wait for afterKanbanElementSaved + DOM + badge update
    await _idle(page, 15000)
    await page.wait_for_timeout(5000)

    return count_a, count_b


@pytest.mark.asyncio
async def test_drag_card_to_adjacent_column(kanban_page):
    """
    P0: Dragging a card from column A to adjacent column B decrements A's badge
    by 1 and increments B's badge by 1.
    """
    page = kanban_page

    cols_before = await page.query_selector_all('.dcm-stage-wrap')
    assert len(cols_before) >= 2, "Need at least 2 columns for drag test"

    cards_in_col0 = await page.locator(
        '.dcm-stage-wrap'
    ).first.locator('.dcm-stage-element-view-wrap').count()
    assert cards_in_col0 > 0, "Column 0 has no rendered cards to drag"

    count_a_before, count_b_before = await _drag_first_card_to_next_column(page)

    count_a_after = await get_column_count_by_index(page, 0)
    count_b_after = await get_column_count_by_index(page, 1)

    assert count_a_after == count_a_before - 1, (
        f"Column A count should decrease by 1: {count_a_before} → {count_a_after}"
    )
    assert count_b_after == count_b_before + 1, (
        f"Column B count should increase by 1: {count_b_before} → {count_b_after}"
    )

    await _clear_all_filters(page)


@pytest.mark.asyncio
async def test_drag_card_updates_column_counts(kanban_page):
    """
    P0: Moving a card via drag-and-drop must not create or delete records —
    total count across all columns must stay the same.
    """
    page = kanban_page

    cols_before = await page.query_selector_all('.dcm-stage-wrap')
    assert len(cols_before) >= 2, "Need at least 2 columns for drag test"

    cards_in_col0 = await page.locator(
        '.dcm-stage-wrap'
    ).first.locator('.dcm-stage-element-view-wrap').count()
    assert cards_in_col0 > 0, "Column 0 has no rendered cards to drag"

    total_before = count_total(await read_column_counts(page))
    await _drag_first_card_to_next_column(page)
    total_after = count_total(await read_column_counts(page))

    assert total_after == total_before, (
        f"Total record count changed after drag: {total_before} → {total_after}. "
        "A record may have been created or deleted."
    )

    await _clear_all_filters(page)
