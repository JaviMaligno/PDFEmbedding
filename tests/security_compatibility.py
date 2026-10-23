"""Focused compatibility checks; external services/config replaced before imports."""
import asyncio
import io
from pathlib import Path
import socket
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def forbidden(*args, **kwargs):
    raise AssertionError("External network/provider access forbidden")

original_connect = socket.socket.connect
def guarded_connect(self, address):
    # Windows asyncio builds its internal wake-up pipe with stdlib socketpair.
    caller = sys._getframe(1).f_code
    if caller.co_name == "_fallback_socketpair" and Path(caller.co_filename).name == "socket.py" and address[0] in ("127.0.0.1", "::1"):
        return original_connect(self, address)
    return forbidden()
socket.socket.connect = guarded_connect
import httpx
httpx.HTTPTransport.handle_request = forbidden
httpx.AsyncHTTPTransport.handle_async_request = forbidden
from sqlalchemy.orm import declarative_base

database = types.ModuleType("app.database")
database.Base = declarative_base()
async def get_db():
    yield Mock(name="synthetic-db")
database.get_db = get_db
sys.modules[database.__name__] = database
config = types.ModuleType("app.config")
config.settings = types.SimpleNamespace(pdf_storage_path="unused-fixture-path", embedding_dimensions=1536)
sys.modules[config.__name__] = config
tasks = types.ModuleType("app.workers.tasks")
tasks.process_document = types.SimpleNamespace(delay=forbidden)
sys.modules[tasks.__name__] = tasks
services = types.ModuleType("app.services")
services.__path__ = [str(ROOT / "app/services")]
sys.modules[services.__name__] = services
search_service = types.ModuleType("app.services.search_service")
search_service.hybrid_search = AsyncMock(return_value=[])
sys.modules[search_service.__name__] = search_service

from fastapi.testclient import TestClient
from app.main import app
from app.services.pdf_processor import extract_text_from_pdf, pdf_page_to_image
import fitz
from PIL import Image

class Compatibility(unittest.TestCase):
    def test_health_and_metrics(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/health").json(), {"status": "healthy"})
            response = client.get("/metrics")
            self.assertEqual(response.status_code, 200)
            self.assertIn("http_requests_total", response.text)

    def test_search_validation_and_result(self):
        search_service.hybrid_search.return_value = [{
            "document_id": "12345678-1234-1234-1234-123456789abc",
            "chunk_id": "87654321-4321-4321-4321-cba987654321",
            "score": 0.89, "snippet": "synthetic text",
            "metadata": {"filename": "fixture.pdf", "page": 1},
        }]
        with TestClient(app) as client:
            self.assertEqual(client.post("/search", json={"query": ""}).status_code, 422)
            response = client.post("/search", json={"query": "synthetic"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["results"][0]["score"], 0.89)
        self.assertEqual(search_service.hybrid_search.await_args.kwargs["query"], "synthetic")

    def test_multipart_rejects_non_pdf_without_side_effects(self):
        with TestClient(app) as client:
            response = client.post("/upload", files={"files": ("fixture.txt", b"fixture", "text/plain")})
            self.assertEqual(response.status_code, 400)

    def test_pdf_raster_and_pillow_real_libraries(self):
        with tempfile.TemporaryDirectory(prefix="coverage-audit-pdf-", dir=ROOT.parent.parent) as folder:
            path = Path(folder) / "fixture.pdf"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((72, 72), "Synthetic compatibility fixture " * 3)
                document.save(path)
            pages = asyncio.run(extract_text_from_pdf(str(path)))
            self.assertEqual(len(pages), 1)
            self.assertIn("Synthetic compatibility fixture", pages[0]["text"])
            png = asyncio.run(pdf_page_to_image(str(path), 1))
            with Image.open(io.BytesIO(png)) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
