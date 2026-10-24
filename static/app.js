// Taskspace UI: communicates only with our FastAPI server, never with Notion directly.
const $ = (id) => document.getElementById(id);
let allTasks = [];
let filter = 'All';

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  let data;
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`);
  return data;
}
function message(text = '') { $('message').textContent = text; }
function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function render() {
  $('total').textContent = allTasks.length;
  $('progress').textContent = allTasks.filter(t => t.status === 'In Progress').length;
  $('done').textContent = allTasks.filter(t => t.status === 'Done').length;
  const list = $('tasks'); list.replaceChildren();
  const visible = allTasks.filter(t => filter === 'All' || t.status === filter);
  if (!visible.length) { list.append(node('div', 'empty', 'No tasks here yet. Add one above!')); return; }
  for (const task of visible) {
    const row = node('div', 'task');
    const title = node('div', 'task-title' + (task.status === 'Done' ? ' complete' : ''), task.title);
    const priority = node('span', 'pill ' + task.priority, task.priority);
    const status = node('select'); status.setAttribute('aria-label', `Status for ${task.title}`);
    for (const s of ['To Do', 'In Progress', 'Done']) { const option = node('option', '', s); option.value = s; option.selected = task.status === s; status.append(option); }
    status.addEventListener('change', async () => { status.disabled = true; try { await api(`/api/tasks/${task.id}`, {method: 'PATCH', body: JSON.stringify({status: status.value})}); await load(); } catch (err) { message(err.message); status.value = task.status; } finally { status.disabled = false; } });
    const remove = node('button', 'delete', 'Archive'); remove.setAttribute('aria-label', `Archive ${task.title}`);
    remove.addEventListener('click', async () => { remove.disabled = true; try { await api(`/api/tasks/${task.id}`, {method: 'DELETE'}); await load(); } catch (err) { message(err.message); remove.disabled = false; } });
    row.append(title, priority, status, remove); list.append(row);
  }
}
async function load() { try { message(); allTasks = await api('/api/tasks'); render(); } catch (err) { message(err.message); $('tasks').replaceChildren(node('div', 'empty', 'Could not load tasks. Check your Notion configuration.')); } }
$('task-form').addEventListener('submit', async (event) => { event.preventDefault(); const title = $('title').value.trim(); if (!title) return; const button = event.currentTarget.querySelector('button'); button.disabled = true; try { await api('/api/tasks', {method: 'POST', body: JSON.stringify({title, priority: $('priority').value})}); $('title').value = ''; await load(); } catch (err) { message(err.message); } finally { button.disabled = false; } });
$('refresh').addEventListener('click', load);
document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; document.querySelectorAll('.filter').forEach(b => b.classList.toggle('active', b === button)); render(); }));
load();
