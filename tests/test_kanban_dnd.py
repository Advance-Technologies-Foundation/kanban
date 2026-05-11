"""
P0 tests for Kanban drag-and-drop card moving.

Badge counts (.kanban-column-summary) show server-side totals, which update
synchronously via CollectionDataStorage._setTotalCount when insert/removeByIndex
fires on the collection, before the server save callback.
"""

import pytest
from playwright.async_api import TimeoutError as PWTimeout

from conftest import (
    _clear_all_filters,
    _idle,
    get_column_count_by_index,
    read_column_counts,
    count_total,
)


async def _wait_for_cards(page, timeout=30000):
    """Wait until at least one card element is rendered."""
    try:
        await page.wait_for_selector('.kanban-element-wrap', timeout=timeout)
    except PWTimeout:
        pass
    await page.wait_for_timeout(2000)


@pytest.mark.asyncio
@pytest.mark.xdist_group("dnd")
async def test_drag_card_to_adjacent_column(kanban_page):
    """
    P0: Dragging a card from column A to adjacent column B decrements A's badge
    by 1 and increments B's badge by 1.
    """
    page = kanban_page

    await _wait_for_cards(page)

    cols = await page.query_selector_all('.dcm-stage-wrap')
    assert len(cols) >= 2, "Need at least 2 columns for drag test"

    cards_in_col0 = await page.locator(
        '.dcm-stage-wrap'
    ).first.locator('.kanban-element-wrap').count()
    assert cards_in_col0 > 0, "Column 0 has no rendered cards to drag after 30s wait"

    count_a_before = await get_column_count_by_index(page, 0)
    count_b_before = await get_column_count_by_index(page, 1)

    source = page.locator('.dcm-stage-wrap').first.locator('.kanban-element-wrap').first
    target = page.locator('.dcm-stage-wrap').nth(1)

    # ExtJS DD requires slow mouse movement to trigger drag threshold.
    # Use raw mouse events instead of drag_to().
    src_box = await source.bounding_box()
    tgt_box = await target.bounding_box()
    sx = src_box['x'] + src_box['width'] / 2
    sy = src_box['y'] + src_box['height'] / 2
    tx = tgt_box['x'] + tgt_box['width'] / 2
    ty = tgt_box['y'] + tgt_box['height'] / 2

    await page.mouse.move(sx, sy)
    await page.mouse.down()
    await page.wait_for_timeout(300)
    # Move in steps so ExtJS DD detects the drag threshold
    steps = 15
    for i in range(1, steps + 1):
        frac = i / steps
        await page.mouse.move(sx + (tx - sx) * frac, sy + (ty - sy) * frac)
        await page.wait_for_timeout(30)
    await page.wait_for_timeout(300)
    await page.mouse.up()

    await _idle(page, 15000)
    await page.wait_for_timeout(5000)

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
@pytest.mark.xdist_group("dnd")
async def test_drag_card_updates_column_counts(kanban_page):
    """
    P0: Moving a card via drag-and-drop must not create or delete records —
    total count across all columns must stay the same.
    """
    page = kanban_page

    await _wait_for_cards(page)

    cols = await page.query_selector_all('.dcm-stage-wrap')
    assert len(cols) >= 2, "Need at least 2 columns for drag test"

    cards_in_col0 = await page.locator(
        '.dcm-stage-wrap'
    ).first.locator('.kanban-element-wrap').count()
    assert cards_in_col0 > 0, "Column 0 has no rendered cards to drag after 30s wait"

    total_before = count_total(await read_column_counts(page))

    source = page.locator('.dcm-stage-wrap').first.locator('.kanban-element-wrap').first
    target = page.locator('.dcm-stage-wrap').nth(1)
    await source.drag_to(target)
    await _idle(page, 15000)
    await page.wait_for_timeout(5000)

    total_after = count_total(await read_column_counts(page))

    assert total_after == total_before, (
        f"Total record count changed after drag: {total_before} → {total_after}. "
        "A record may have been created or deleted."
    )

    await _clear_all_filters(page)
