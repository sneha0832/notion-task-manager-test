"""Offline tests: no real Notion token, no network calls, no GitHub writes."""
import asyncio
import json
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.notion_client import NotionClient
from app.task_service import list_tasks, create_task, update_task

PAGE_ID = '11111111-1111-4111-8111-111111111111'

def page(title='Test task', status='To Do', priority='Medium'):
    return {'id': PAGE_ID, 'url': 'https://notion.so/example', 'properties': {
        'Name': {'title': [{'plain_text': title}]},
        'Status': {'select': {'name': status}},
        'Priority': {'select': {'name': priority}},
    }}

def test_health_without_credentials():
    response = TestClient(app).get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_legacy_notion_api_operations(monkeypatch):
    monkeypatch.setenv('NOTION_TOKEN', 'test-token-not-real')
    monkeypatch.setenv('NOTION_DATABASE_ID', '22222222-2222-4222-8222-222222222222')
    calls = []
    def handler(request):
        calls.append((request.method, request.url.path, json.loads(request.content or b'{}')))
        assert request.headers['Notion-Version'] == '2022-06-28'
        if request.url.path.endswith('/query'):
            return httpx.Response(200, json={'results': [page()], 'has_more': False, 'next_cursor': None})
        if request.method == 'POST':
            return httpx.Response(200, json=page('Created task', priority='High'))
        return httpx.Response(200, json=page('Test task', status='Done'))
    async def exercise():
        client = NotionClient(transport=httpx.MockTransport(handler))
        tasks = await list_tasks(client)
        assert len(tasks) == 1 and tasks[0]['title'] == 'Test task'
        created = await create_task(client, 'Created task', 'High')
        assert created['priority'] == 'High'
        updated = await update_task(client, PAGE_ID, status='Done')
        assert updated['status'] == 'Done'
        await client.archive_page(PAGE_ID)
    asyncio.run(exercise())
    assert calls[0][1] == '/v1/databases/22222222-2222-4222-8222-222222222222/query'
    assert calls[1][1] == '/v1/pages'
    assert calls[2][1] == f'/v1/pages/{PAGE_ID}'
    assert calls[3][2] == {'archived': True}


def test_request_validation():
    client = TestClient(app)
    assert client.post('/api/tasks', json={'title': ''}).status_code == 422
    assert client.patch(f'/api/tasks/{PAGE_ID}', json={}).status_code == 422
    assert client.delete('/api/tasks/not-a-uuid').status_code == 422
