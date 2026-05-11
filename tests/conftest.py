"""
Shared fixtures for Kanban Playwright tests.

Environment variables (override defaults for non-standard envs):
  KANBAN_BASE_URL   base URL of the Creatio instance
  KANBAN_USER       login username   (default: clio)
  KANBAN_PASSWORD   login password

Performance strategy
  Auth is performed ONCE per test run and saved to /tmp/kanban_auth.json
  (Playwright storage_state — cookies + localStorage). All tests load
  that state so no re-login is needed per test. The file is protected by
  a lock file so xdist workers don't race each other on creation.

  Each test still creates its own browser/context/page (fully isolated),
  so pytest-xdist -n N works without any event-loop sharing concerns.
"""
import asyncio
import fcntl
import os
import time

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_URL  = os.getenv("KANBAN_BASE_URL", "https://185574-crm-bundle.creatio.com")
USERNAME  = os.getenv("KANBAN_USER",     "clio")
PASSWORD  = os.getenv("KANBAN_PASSWORD", "Supervisor2!")

SECTION_URL = BASE_URL + "/0/Shell/#SectionModuleV2/OpportunitySectionV2"

AUTH_FILE = "/tmp/kanban_auth.json"
AUTH_LOCK = "/tmp/kanban_auth.lock"


# ── auth-state bootstrap ─────────────────────────────────────────────────────

async def _create_auth_file():
    """Login once and persist cookies/localStorage to AUTH_FILE."""
    pw = await async_playwright().start()
    b = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    ctx = await b.new_context(
        viewport={"width": 1600, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        ),
    )
    page = await ctx.new_page()

    await page.goto(BASE_URL + "/Login/NuiLogin.aspx")
    await _idle(page, 20000)
    await page.fill("#loginEdit-el", USERNAME)
    await page.fill("#passwordEdit-el", PASSWORD)
    await page.click(".t-btn-style-green")
    await _idle(page, 30000)
    await page.wait_for_timeout(2000)

    await ctx.storage_state(path=AUTH_FILE)
    await b.close()
    await pw.stop()


def _ensure_auth_file():
    """Create AUTH_FILE if absent; safe to call from multiple xdist workers."""
    if os.path.exists(AUTH_FILE):
        return

    lock = open(AUTH_LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)       # one worker at a time
        if not os.path.exists(AUTH_FILE):       # re-check after acquiring
            asyncio.run(_create_auth_file())
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


@pytest.fixture(scope="session", autouse=True)
def auth_state():
    """Session fixture: guarantees AUTH_FILE exists before any test runs."""
    _ensure_auth_file()
    yield


# ── main page fixture ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def kanban_page(auth_state):
    """Authenticated page at the Opportunity Kanban view, all filters cleared.

    Loads cookies from AUTH_FILE — no login round-trip per test.
    """
    async with async_playwright() as pw:
        b = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await b.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=AUTH_FILE,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            ),
        )
        page = await ctx.new_page()

        await page.goto(SECTION_URL)
        await _idle(page, 30000)
        await page.wait_for_timeout(2000)

        # Activate Kanban view if the saved profile left Grid active
        dcm = await page.query_selector('.dcm-stage-wrap')
        if not dcm or not await dcm.is_visible():
            for sel in ['[data-item-marker="Kanban"]', '[data-item-marker="KanbanDataView"]']:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await _idle(page, 15000)
                    break

        await page.wait_for_selector(".dcm-stage-wrap", timeout=90000)
        await page.wait_for_timeout(2000)

        try:
            await page.wait_for_selector(".kanban-element-wrap", timeout=25000)
        except PWTimeout:
            pass
        await page.wait_for_timeout(2000)

        await _clear_all_filters(page)

        try:
            await page.wait_for_selector(".kanban-element-wrap", timeout=20000)
        except PWTimeout:
            pass
        await page.wait_for_timeout(1000)

        yield page

        await ctx.close()
        await b.close()


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


async def switch_to_grid(page):
    """Click Grid view icon and wait for grid to render."""
    btn = await page.query_selector('[data-item-marker="GridDataView"]')
    if btn:
        await btn.click()
    await _idle(page, 15000)
    await page.wait_for_timeout(2000)


async def switch_to_kanban(page):
    """Click Kanban view icon and wait for .dcm-stage-wrap."""
    for sel in ['[data-item-marker="Kanban"]', '[data-item-marker="KanbanDataView"]']:
        btn = await page.query_selector(sel)
        if btn:
            await btn.click()
            break
    await page.wait_for_selector(".dcm-stage-wrap", timeout=60000)
    await _idle(page, 15000)
    await page.wait_for_timeout(2000)


async def apply_period(page, label: str):
    """Open period dropdown and click a named period item (e.g. 'Current month')."""
    menu = await page.query_selector('[data-item-marker="month"] .t-btn-menuWrap')
    await menu.click()
    await page.wait_for_timeout(1000)
    item = await page.query_selector(f'li:has-text("{label}")')
    await item.click()
    await _idle(page, 20000)
    await page.wait_for_timeout(5000)


async def count_visible_cards(page) -> int:
    """Count rendered .kanban-element-wrap elements across all columns."""
    return await page.evaluate(
        "() => document.querySelectorAll('.kanban-element-wrap').length"
    )


async def get_column_count_by_index(page, index: int) -> int:
    """Return the numeric count badge of the nth column."""
    import re
    raw = await page.evaluate(f"""() => {{
        const cols = document.querySelectorAll('.dcm-stage-wrap');
        if ({index} >= cols.length) return '0';
        const badge = cols[{index}].querySelector('.kanban-column-summary');
        return badge ? badge.innerText.trim() : '0';
    }}""")
    m = re.search(r'\d+', str(raw))
    return int(m.group()) if m else 0


async def get_terminal_column_count(page) -> int:
    """Return the count badge of the last (terminal) column."""
    import re
    raw = await page.evaluate("""() => {
        const cols = document.querySelectorAll('.dcm-stage-wrap');
        if (!cols.length) return '0';
        const last = cols[cols.length - 1];
        const badge = last.querySelector('.kanban-column-summary');
        return badge ? badge.innerText.trim() : '0';
    }""")
    m = re.search(r'\d+', str(raw))
    return int(m.group()) if m else 0


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
        first_word = search_name.split()[0].lower()
        for _ in range(4):
            await page.wait_for_timeout(2000)
            rows = await page.query_selector_all('.containerLookupPage .grid-primary-column')
            matched = False
            for r in rows:
                if first_word in (await r.inner_text()).lower():
                    matched = True
                    break
            if matched:
                break

    rows = await page.query_selector_all('.containerLookupPage .grid-primary-column')
    if not rows:
        await page.keyboard.press("Escape")
        return ""

    first_word = search_name.split()[0].lower()
    target_row = rows[0]
    for r in rows:
        if first_word in (await r.inner_text()).lower():
            target_row = r
            break

    selected = (await target_row.inner_text()).strip()
    await target_row.dblclick()
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
