"""
Shared fixtures for Kanban Playwright tests.

Environment variables (override defaults for non-standard envs):
  KANBAN_BASE_URL   base URL of the Creatio instance
  KANBAN_USER       login username   (default: clio)
  KANBAN_PASSWORD   login password
"""
import os
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_URL  = os.getenv("KANBAN_BASE_URL", "https://185574-crm-bundle.creatio.com")
USERNAME  = os.getenv("KANBAN_USER",     "clio")
PASSWORD  = os.getenv("KANBAN_PASSWORD", "Supervisor2!")

SECTION_URL = BASE_URL + "/0/Shell/#SectionModuleV2/OpportunitySectionV2"


@pytest_asyncio.fixture(scope="session")
async def browser():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        yield b
        await b.close()


@pytest_asyncio.fixture
async def kanban_page(browser):
    """Authenticated page opened to the Opportunity Kanban view, all filters cleared."""
    ctx = await browser.new_context(
        viewport={"width": 1600, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        ),
    )
    page = await ctx.new_page()

    # Login
    await page.goto(BASE_URL + "/Login/NuiLogin.aspx")
    await _idle(page, 20000)
    await page.fill("#loginEdit-el", USERNAME)
    await page.fill("#passwordEdit-el", PASSWORD)
    await page.click(".t-btn-style-green")
    await _idle(page, 30000)
    await page.wait_for_timeout(3000)

    # Open Kanban
    await page.goto(SECTION_URL)
    await page.wait_for_selector(".dcm-stage-wrap", timeout=90000)
    await page.wait_for_timeout(3000)

    # Clear any stale filters from a previous session
    await _clear_all_filters(page)

    yield page

    await ctx.close()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _idle(page, ms=20000):
    try:
        await page.wait_for_load_state("networkidle", timeout=ms)
    except PWTimeout:
        pass


async def _clear_all_filters(page):
    clear = await page.query_selector('[data-item-marker="clearPeriodFilter"]')
    if clear:
        await clear.click()
        await page.wait_for_timeout(2000)

    ob = await page.query_selector('[data-item-marker="OwnerFixedFilterBtn"]')
    if not ob:
        return
    await ob.click()
    await page.wait_for_timeout(800)
    clr = await page.query_selector('li:has-text("Clear")')
    if clr and await clr.is_visible():
        await clr.click()
        await page.wait_for_timeout(2000)
    else:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
    await _idle(page, 10000)
    await page.wait_for_timeout(2000)


async def read_column_counts(page) -> list[str]:
    """Return ['Stage [N]', ...] for every visible Kanban column."""
    await page.wait_for_timeout(4000)
    return await page.evaluate("""() =>
        Array.from(document.querySelectorAll('.dcm-stage-wrap')).map(w => {
            const cap = w.querySelector('.stage-tools .t-label');
            const cnt = w.querySelector('.kanban-column-summary');
            return (cap ? cap.innerText.trim() : '?')
                 + ' [' + (cnt ? cnt.innerText.trim() : '?') + ']';
        })
    """)


def count_total(cols: list[str]) -> int:
    import re
    return sum(int(m.group(1)) for c in cols for m in [re.search(r'\[(\d+)\]', c)] if m)


async def apply_prev_month(page):
    menu = await page.query_selector('[data-item-marker="month"] .t-btn-menuWrap')
    await menu.click()
    await page.wait_for_timeout(1000)
    item = await page.query_selector('li:has-text("Previous month")')
    await item.click()
    await _idle(page, 20000)
    await page.wait_for_timeout(5000)


async def set_owner(page, search_name: str) -> str:
    """Open the owner lookup, search by name, double-click the first match. Returns selected name."""
    ob = await page.query_selector('[data-item-marker="OwnerFixedFilterBtn"]')
    await ob.click()
    await page.wait_for_timeout(1000)
    add = await page.query_selector('li:has-text("Add owner")')
    if not add:
        await page.keyboard.press("Escape")
        return ""
    await add.click()
    try:
        await page.wait_for_selector('.containerLookupPage .grid-primary-column', timeout=15000)
    except PWTimeout:
        pass

    search = await page.query_selector('#searchEdit-el')
    if search:
        await search.click()
        await search.fill("")
        await page.keyboard.type(search_name, delay=80)
        await page.wait_for_timeout(1000)
        srch = await page.query_selector('[data-item-marker="searchButton"]')
        if srch:
            await srch.click()
        await page.wait_for_timeout(3000)

    rows = await page.query_selector_all('.containerLookupPage .grid-primary-column')
    if not rows:
        await page.keyboard.press("Escape")
        return ""

    selected = (await rows[0].inner_text()).strip()
    await rows[0].dblclick()
    await page.wait_for_timeout(2000)

    lp = await page.query_selector('.containerLookupPage')
    if lp:
        sel = await page.query_selector('[data-item-marker="selectButton"]')
        if sel:
            await sel.click(force=True)
            await page.wait_for_timeout(1500)
    lp2 = await page.query_selector('.containerLookupPage')
    if lp2:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)

    await _idle(page, 10000)
    await page.wait_for_timeout(3000)
    return selected
