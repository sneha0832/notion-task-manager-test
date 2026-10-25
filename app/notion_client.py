"""Notion REST API adapter using data-source endpoints.

This project pins Notion-Version: 2022-06-28 and uses the legacy
POST /v1/databases/{database_id}/query route. The 2025-09-03 API
introduces data-source IDs and different query routes.
"""
import httpx
from fastapi import HTTPException
from app.config import NOTION_API_BASE, NOTION_DATA_SOURCE_ID, NOTION_VERSION, notion_settings


class NotionClient:
    def __init__(self, transport=None):
        token, self.database_id = notion_settings()
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': NOTION_VERSION,
            'Content-Type': 'application/json',
        }
        self.transport = transport
        self.data_source_id = NOTION_DATA_SOURCE_ID or None

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

    async def resolve_data_source_id(self):
        """Resolve and cache the data source used by this task database."""
        if self.data_source_id:
            return self.data_source_id
        database = await self.request('GET', f'/databases/{self.database_id}')
        data_sources = database.get('data_sources') or []
        if len(data_sources) != 1:
            raise HTTPException(
                status_code=503,
                detail=(
                    'Set NOTION_DATA_SOURCE_ID to the data source that stores tasks '
                    'when the database has multiple data sources.'
                ),
            )
        self.data_source_id = data_sources[0].get('id')
        if not self.data_source_id:
            raise HTTPException(
                status_code=502,
                detail='Notion returned a database without a usable data source ID.',
            )
        return self.data_source_id

    async def query_database(self, start_cursor=None):
        """Query the configured Notion data source."""
        data_source_id = await self.resolve_data_source_id()
        body = {'page_size': 100, 'sorts': [{'timestamp': 'created_time', 'direction': 'descending'}]}
        if start_cursor:
            body['start_cursor'] = start_cursor
        return await self.request('POST', f'/data_sources/{data_source_id}/query', json=body)

    async def create_page(self, properties):
        data_source_id = await self.resolve_data_source_id()
        return await self.request('POST', '/pages', json={
            'parent': {'type': 'data_source_id', 'data_source_id': data_source_id},
            'properties': properties,
        })

    async def update_page(self, page_id, properties):
        return await self.request('PATCH', f'/pages/{page_id}', json={'properties': properties})

    async def archive_page(self, page_id):
        return await self.request('PATCH', f'/pages/{page_id}', json={'archived': True})
