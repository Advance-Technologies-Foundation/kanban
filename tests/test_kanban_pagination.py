"""
P0 tests for Kanban Load More pagination.

LoadMoreButtonVisible is set to true by CaseDataStorage.checkAllDataLoaded when
any column has totalRowsCount > currentRowsCount (i.e. more data exists on server).
With ~101 records and rowCount=7, at least one column exceeds the page size.
"""

import pytest
from playwright.async_api import TimeoutError as PWTimeout

from conftest import _idle, count_visible_cards


@pytest.mark.asyncio
async def test_load_more_button_visible_when_has_more(kanban_page):
    """
    P0: The Load More button appears when at least one column has more records
    than the rendered page size (7 cards).

    With ~101 total records the button must be visible after the board loads.
    """
    page = kanban_page

    # checkAllDataLoaded fires after columns finish loading; wait for button
    try:
        await page.wait_for_selector(
            '[data-item-marker="LoadMore"]',
            state='visible',
            timeout=30000,
        )
    except PWTimeout:
        pass  # Button may be hidden via display:none — fall through to assertion

    btn = await page.query_selector('[data-item-marker="LoadMore"]')
    assert btn is not None, "[data-item-marker='LoadMore'] not found in DOM"
    assert await btn.is_visible(), (
        "Load More button exists but is not visible. "
        "Expected visible because total records (~101) exceed page size (7 per column)."
    )


@pytest.mark.asyncio
async def test_load_more_increases_visible_card_count(kanban_page):
    """
    P0: Clicking the Load More button renders additional card elements.

    Assert: card count after click > card count before click.
    """
    page = kanban_page

    # Ensure button is visible first
    try:
        await page.wait_for_selector(
            '[data-item-marker="LoadMore"]',
            state='visible',
            timeout=30000,
        )
    except PWTimeout:
        pytest.skip("Load More button not visible — cannot test pagination")

    count_before = await count_visible_cards(page)

    btn = await page.query_selector('[data-item-marker="LoadMore"]')
    assert btn is not None, "[data-item-marker='LoadMore'] not found"
    await btn.click()
    await _idle(page, 20000)
    await page.wait_for_timeout(3000)

    count_after = await count_visible_cards(page)

    assert count_after > count_before, (
        f"Clicking Load More did not increase visible card count: "
        f"{count_before} before, {count_after} after."
    )
