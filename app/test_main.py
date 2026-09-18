import asyncio
import time

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from .main import app

client = TestClient(app)

def test_default_file_name():
    response = client.post(
        "/pdfs",
        json={"html": "<h1>Hello World</h1>"},
    )

    assert response.status_code == 200
    assert response.headers['content-disposition'] == 'attachment; name="weasyprint"; filename="weasyprint.pdf"'
    assert response.headers['content-type'] == 'application/pdf'

def test_empty_file_name():
    response = client.post(
        "/pdfs",
        json={"filename": "           ", "html": "<h1>Hello World</h1>"},
    )

    assert response.status_code == 200
    assert response.headers['content-disposition'] == 'attachment; name="weasyprint"; filename="weasyprint.pdf"'
    assert response.headers['content-type'] == 'application/pdf'

def test_strip_specific_file_name():
    response = client.post(
        "/pdfs",
        json={"filename": "   shipping-label   ", "html": "<h1>Hello World</h1>"},
    )

    assert response.status_code == 200
    assert response.headers['content-disposition'] == 'attachment; name="shipping-label"; filename="shipping-label.pdf"'
    assert response.headers['content-type'] == 'application/pdf'

async def _render_heavy_doc(big_html: str):
    async def probe():
        # Created before the big request so its deadline lands inside the
        # render window: it only completes late if the loop is starved.
        start = time.monotonic()
        await asyncio.sleep(4)
        return time.monotonic() - start

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        probe_task = asyncio.create_task(probe())
        big_task = asyncio.create_task(client.post('/pdfs', json={'html': big_html}))

        elapsed = await probe_task
        assert elapsed < 5, (
            f'event loop was blocked for {elapsed:.1f}s during a heavy render; '
            'concurrent requests would stall until the render finishes'
        )

        big = await asyncio.wait_for(big_task, timeout=120)
        assert big.status_code == 200
        assert big.headers['content-type'] == 'application/pdf'

def test_heavy_render_does_not_block_the_event_loop():
    big_html = '<p>Hello World paragraph with some longer text content to make rendering work harder.</p>\n' * 12000

    asyncio.run(_render_heavy_doc(big_html))
