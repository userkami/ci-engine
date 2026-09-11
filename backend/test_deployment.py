"""Offline API regression tests: python -m unittest test_deployment -v.

The queue entrypoint is stubbed; no AI calls, database, or Redis are used.
"""
import importlib
import json
import os
import sys
import types
import unittest
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx


@contextmanager
def api_module():
    queue = types.ModuleType("app.worker.tasks")
    queue.execute_research_job = SimpleNamespace(delay=lambda *args: None)
    with patch.dict(sys.modules, {"app.worker.tasks": queue}):
        yield importlib.import_module("app.main")


class DeploymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with api_module() as api:
            self.api = api
        self.db = AsyncMock()

        async def database():
            yield self.db

        self.api.app.dependency_overrides[self.api.get_db] = database
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.api.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        self.api.app.dependency_overrides.clear()

    async def test_provision_rejects_missing_and_wrong_internal_secret(self):
        with patch.dict(os.environ, {"INTERNAL_API_SECRET": "a" * 64}):
            for headers in ({}, {"X-Internal-Api-Secret": "wrong"}):
                response = await self.client.post(
                    "/api/auth/provision", json={"email": "owner@example.com"}, headers=headers
                )
                self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_provision_fails_closed_when_unconfigured(self):
        with patch.dict(os.environ, {"INTERNAL_API_SECRET": ""}):
            response = await self.client.post(
                "/api/auth/provision", json={"email": "owner@example.com"}
            )
        self.assertEqual(response.status_code, 503)

    async def test_trusted_provision_returns_identity_and_real_balance(self):
        owner = SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")
        self.db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: owner)
        self.db.get.return_value = SimpleNamespace(balance=0)
        with patch.dict(os.environ, {"INTERNAL_API_SECRET": "a" * 64, "JWT_SECRET": "b" * 64}):
            response = await self.client.post(
                "/api/auth/provision", json={"email": owner.email},
                headers={"X-Internal-Api-Secret": "a" * 64},
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["user_id"], str(owner.id))
        self.assertEqual(response.json()["balance"], 0)

    async def test_stream_requires_login(self):
        response = await self.client.get(f"/api/jobs/{uuid.uuid4()}/stream")
        self.assertEqual(response.status_code, 401)

    async def test_stream_rejects_other_users_job(self):
        self.api.app.dependency_overrides[self.api.get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4())
        self.db.get.return_value = SimpleNamespace(user_id=uuid.uuid4())
        response = await self.client.get(f"/api/jobs/{uuid.uuid4()}/stream")
        self.assertEqual(response.status_code, 404)

    async def test_late_subscriber_gets_saved_report_id(self):
        owner = uuid.uuid4()
        card = str(uuid.uuid4())
        self.api.app.dependency_overrides[self.api.get_current_user] = lambda: SimpleNamespace(id=owner)
        self.db.get.return_value = SimpleNamespace(user_id=owner)
        with patch.object(self.api, "_job_state", AsyncMock(return_value=("completed", ""))), patch.object(
            self.api, "_completed_data", AsyncMock(return_value={"battlecard_id": card})
        ):
            response = await self.client.get(f"/api/jobs/{uuid.uuid4()}/stream")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.text.removeprefix("data: ").strip())
        self.assertEqual(payload["data"]["battlecard_id"], card)


if __name__ == "__main__":
    unittest.main()
