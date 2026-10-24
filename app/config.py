"""Load configuration without ever hard-coding Notion credentials."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

NOTION_API_BASE = 'https://api.notion.com/v1'
NOTION_VERSION = os.getenv('NOTION_VERSION', '2022-06-28')


def notion_settings():
    token = os.getenv('NOTION_TOKEN', '').strip()
    database_id = os.getenv('NOTION_DATABASE_ID', '').strip()
    if not token or token == 'secret_replace_me' or not database_id or database_id == 'replace_with_database_id':
        raise RuntimeError('Set NOTION_TOKEN and NOTION_DATABASE_ID in .env before using task endpoints.')
    return token, database_id
