"""Legacy Notion REST API adapter — intentional API Guardian migration target.

This project pins Notion-Version: 2022-06-28 and uses the legacy
POST /v1/databases/{database_id}/query route. The 2025-09-03 API
introduces data-source IDs and different query routes.
"""
import httpx
from fastapi import HTTPException
from app.config import NOTION_API_BASE, NOTION_VERSION, notion_settings


class NotionClient:
    def __init__(self, transport=None):
        token, self.database_id = notion_settings()
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': NOTION_VERSION,
            'Content-Type': 'application/json',
        }
        self.transport = transport

    async def request(self, method, path, *, json=None):
        try:
            async with httpx.AsyncClient(base_url=NOTION_API_BASE, headers=self.headers,
                                         transport=self.transport, timeout=20) as client:
                response = await client.request(method, path, json=json)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            # Never expose authorization headers or API tokens to clients.
            try:
                message = exc.response.json().get('message', 'Notion request failed')
            except ValueError:
                message = 'Notion request failed'
            raise HTTPException(status_code=502, detail=f'Notion API error ({exc.response.status_code}): {message}') from None
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail='Could not connect to Notion API') from None

    async def query_database(self, start_cursor=None):
        """Legacy endpoint intentionally preserved for migration testing."""
        body = {'page_size': 100, 'sorts': [{'timestamp': 'created_time', 'direction': 'descending'}]}
        if start_cursor:
            body['start_cursor'] = start_cursor
        return await self.request('POST', f'/databases/{self.database_id}/query', json=body)

    async def create_page(self, properties):
        return await self.request('POST', '/pages', json={
            'parent': {'database_id': self.database_id},
            'properties': properties,
        })

    async def update_page(self, page_id, properties):
        return await self.request('PATCH', f'/pages/{page_id}', json={'properties': properties})

    async def archive_page(self, page_id):
        return await self.request('PATCH', f'/pages/{page_id}', json={'archived': True})
