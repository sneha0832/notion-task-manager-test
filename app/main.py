"""FastAPI server for the Notion-backed task manager."""
from pathlib import Path
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from app.config import notion_settings
from app.notion_client import NotionClient
from app.task_service import list_tasks, create_task, update_task

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title='Notion Task Manager', version='1.0.0', description='A real Notion API integration used to test API Guardian.')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: Literal['Low', 'Medium', 'High'] = 'Medium'


class TaskUpdate(BaseModel):
    status: Literal['To Do', 'In Progress', 'Done'] | None = None
    priority: Literal['Low', 'Medium', 'High'] | None = None

    @model_validator(mode='after')
    def at_least_one_field(self):
        if self.status is None and self.priority is None:
            raise ValueError('Provide status or priority')
        return self


def get_client():
    try:
        notion_settings()
        return NotionClient()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.get('/', include_in_schema=False)
async def home():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/health')
async def health():
    try:
        notion_settings()
        configured = True
    except RuntimeError:
        configured = False
    return {'status': 'ok', 'notion_configured': configured, 'notion_version': '2022-06-28 (legacy demo)'}


@app.get('/api/tasks')
async def get_tasks():
    return await list_tasks(get_client())


@app.post('/api/tasks', status_code=201)
async def add_task(task: TaskCreate):
    return await create_task(get_client(), task.title.strip(), task.priority)


@app.patch('/api/tasks/{task_id}')
async def edit_task(task_id: UUID, task: TaskUpdate):
    return await update_task(get_client(), str(task_id), task.status, task.priority)


@app.delete('/api/tasks/{task_id}')
async def delete_task(task_id: UUID):
    await get_client().archive_page(str(task_id))
    return {'status': 'archived', 'id': str(task_id)}
