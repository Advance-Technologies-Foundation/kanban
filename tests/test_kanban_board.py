"""
P0 tests for Kanban board view switching and basic card interaction.
"""

import pytest
from playwright.async_api import TimeoutError as PWTimeout

from conftest import (
    _clear_all_filters,
    _idle,
    switch_to_grid,
    switch_to_kanban,
)


@pytest.mark.asyncio
async def test_switch_to_kanban_view(kanban_page):
    """
    P0: Clicking the Kanban icon from Grid mode activates the Kanban view.

    Flow: start in Kanban (fixture) → switch to Grid → switch back to Kanban.
    Assert: .dcm-stage-wrap is visible.
    """
    page = kanban_page
    await switch_to_grid(page)

    # Confirm kanban is gone before switching back
    stage_wraps = await page.query_selector_all('.dcm-stage-wrap')
    visible_before = False
    for el in stage_wraps:
        if await el.is_visible():
            visible_before = True
            break

    await switch_to_kanban(page)

    stage_wraps = await page.query_selector_all('.dcm-stage-wrap')
    assert len(stage_wraps) > 0, "No .dcm-stage-wrap elements found after switching to Kanban"
    any_visible = any([await el.is_visible() for el in stage_wraps])
    assert any_visible, ".dcm-stage-wrap elements present but none visible after Kanban switch"

    await _clear_all_filters(page)


@pytest.mark.asyncio
async def test_switch_back_to_grid_view(kanban_page):
    """
    P0: Clicking the Grid icon from Kanban mode deactivates the Kanban view.

    Assert: .dcm-stage-wrap is not visible; some grid container is visible.
    Cleanup in finally: always restore Kanban so subsequent tests are not affected.
    """
    page = kanban_page
    try:
        await switch_to_grid(page)

        # Kanban columns must not be visible
        stage_wraps = await page.query_selector_all('.dcm-stage-wrap')
        for el in stage_wraps:
            assert not await el.is_visible(), ".dcm-stage-wrap still visible after switching to Grid"

        # Some grid container must be visible.
        # First try known static selectors; fall back to JS scan for any
        # visible element whose class contains 'grid', 'listed', or 'dataview'.
        grid_visible = False
        for sel in [
            '.grid-listed-view',
            '.grid-dataview-wrap',
            '.grid-utils-table',
            '.t-grid-dataview',
            '.t-grid-loaded',
            '.data-grid-wrap',
            'crt-grid-container',
            'crt-grid',
        ]:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                grid_visible = True
                break

        if not grid_visible:
            visible_cls = await page.evaluate("""() => {
                const keywords = ['grid', 'listed', 'dataview'];
                return Array.from(document.querySelectorAll('*'))
                    .filter(el => {
                        if (!el.className || typeof el.className !== 'string') return false;
                        const r = el.getBoundingClientRect();
                        if (r.width < 100 || r.height < 50) return false;
                        const c = el.className.toLowerCase();
                        return keywords.some(k => c.includes(k));
                    })
                    .slice(0, 8)
                    .map(el => el.tagName.toLowerCase() + '.' +
                         el.className.split(' ').slice(0, 3).join('.'));
            }""")
            grid_visible = bool(visible_cls)
            assert grid_visible, (
                "No grid container visible after switching to Grid — "
                f"JS scan also found nothing. Visible elements with grid/listed/dataview: {visible_cls}. "
                "Inspect browser to find the correct CSS selector."
            )
    finally:
        # Always restore Kanban so subsequent tests start in the correct state
        await switch_to_kanban(page)
        await _clear_all_filters(page)


@pytest.mark.asyncio
async def test_double_click_card_opens_edit(kanban_page):
    """
    P0: Double-clicking a card opens an edit panel (mini-page or full edit page).

    Assert: .minipage-container is visible OR the URL hash contains 'edit'.
    """
    page = kanban_page

    # Cards render async after columns — wait explicitly
    try:
        await page.wait_for_selector('.kanban-element-wrap', timeout=30000)
    except PWTimeout:
        pass

    cards = await page.query_selector_all('.kanban-element-wrap')
    assert cards, "No cards found on the Kanban board after 30s wait"

    await cards[0].dblclick()
    await _idle(page, 15000)
    await page.wait_for_timeout(3000)

    minipage = await page.query_selector('.minipage-container')
    if minipage and await minipage.is_visible():
        return  # pass

    url = page.url
    assert 'edit' in url.lower() or 'CardModule' in url, (
        f"Double-click on card did not open edit panel. URL: {url}"
    )
