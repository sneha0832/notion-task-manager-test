"""Translate Notion page properties into simple task objects."""
from app.notion_client import NotionClient


def title_property(text):
    return {'title': [{'text': {'content': text}}]}


def select_property(value):
    return {'select': {'name': value}}


def parse_task(page):
    props = page.get('properties', {})
    title_parts = props.get('Name', {}).get('title', [])
    return {
        'id': page['id'],
        'title': ''.join(part.get('plain_text', part.get('text', {}).get('content', '')) for part in title_parts),
        'status': (props.get('Status', {}).get('select') or {}).get('name', 'To Do'),
        'priority': (props.get('Priority', {}).get('select') or {}).get('name', 'Medium'),
        'url': page.get('url', ''),
        'created_time': page.get('created_time', ''),
    }


async def list_tasks(client: NotionClient):
    results, cursor = [], None
    while True:
        page = await client.query_database(cursor)
        results.extend(parse_task(item) for item in page.get('results', []) if not item.get('archived', False))
        if not page.get('has_more') or not page.get('next_cursor'):
            return results
        cursor = page['next_cursor']


async def create_task(client: NotionClient, title, priority):
    page = await client.create_page({'Name': title_property(title),
                                     'Status': select_property('To Do'),
                                     'Priority': select_property(priority)})
    return parse_task(page)


async def update_task(client: NotionClient, page_id, status=None, priority=None):
    properties = {}
    if status is not None:
        properties['Status'] = select_property(status)
    if priority is not None:
        properties['Priority'] = select_property(priority)
    return parse_task(await client.update_page(page_id, properties))
