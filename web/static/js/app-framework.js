// ================= 应用框架系统 =================
// 支持多个独立应用窗口

class AppFramework {
    constructor() {
        this.apps = new Map();
        this.windows = new Map();
        this.activeWindow = null;
        this.initContainer();
        this.setupEventListeners();
    }

    initContainer() {
        const container = document.getElementById('appsContainer');
        if (!container) {
            console.error('Apps container not found');
            return;
        }
    }

    setupEventListeners() {
        // 监听底部任务栏点击
        document.addEventListener('click', (e) => {
            if (e.target.closest('.app-icon-btn')) {
                const btn = e.target.closest('.app-icon-btn');
                const appId = btn.dataset.appId;
                this.toggleApp(appId);
            }
        });

        // 阻止默认右键菜单
        document.addEventListener('contextmenu', (e) => {
            if (e.target.closest('.app-window')) {
                e.preventDefault();
            }
        });
    }

    /**
     * 注册应用
     * @param {string} id - 应用 ID
     * @param {object} config - 应用配置
     *   - name: 应用名称
     *   - icon: 应用图标 (emoji)
     *   - createContent: 创建内容的函数
     *   - width: 默认宽度
     *   - height: 默认高度
     */
    registerApp(id, config) {
        this.apps.set(id, config);
        if (!config.hidden) {
            this.createTaskbarIcon(id, config);
        }
        console.log(`[App Framework] Registered app: ${config.name}`);
    }

    /**
     * 创建任务栏图标
     */
    createTaskbarIcon(appId, config) {
        const taskbarApps = document.getElementById('taskbarApps');
        
        // 如果taskbar不存在，则忽略（不显示任务栏图标）
        if (!taskbarApps) {
            return;
        }
        
        const btn = document.createElement('button');
        btn.className = 'app-icon-btn';
        btn.dataset.appId = appId;
        btn.title = config.name;
        btn.innerHTML = config.icon;
        
        taskbarApps.appendChild(btn);
    }

    /**
     * 切换应用窗口显示/隐藏
     */
    toggleApp(appId) {
        if (this.windows.has(appId)) {
            const window = this.windows.get(appId);
            window.toggle();
        } else {
            this.openApp(appId);
        }
    }

    /**
     * 打开应用
     */
    openApp(appId) {
        const config = this.apps.get(appId);
        if (!config) {
            console.error(`App not found: ${appId}`);
            return;
        }

        // 如果窗口已经存在，显示它
        if (this.windows.has(appId)) {
            this.windows.get(appId).show();
            return;
        }

        // 创建新窗口
        const appWindow = new AppWindow(appId, config);
        this.windows.set(appId, appWindow);
        this.activeWindow = appId;

        // 更新任务栏图标状态
        this.updateTaskbarState(appId);
    }

    /**
     * 关闭应用
     */
    closeApp(appId) {
        if (this.windows.has(appId)) {
            const window = this.windows.get(appId);
            window.close();
            this.windows.delete(appId);
        }

        if (this.activeWindow === appId) {
            this.activeWindow = null;
        }

        this.updateTaskbarState(appId);
    }

    /**
     * 更新任务栏状态
     */
    updateTaskbarState(appId) {
        const btn = document.querySelector(`[data-app-id="${appId}"]`);
        if (!btn) return;

        if (this.windows.has(appId) && !this.windows.get(appId).isMinimized) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    }
}

/**
 * 应用窗口类
 */
class AppWindow {
    constructor(appId, config) {
        this.appId = appId;
        this.config = config;
        this.isDragging = false;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;
        this.isMinimized = false;

        this.create();
        this.setupPosition();
        this.setupDragAndDrop();
        this.setupContent();
    }

    create() {
        const container = document.getElementById('appsContainer');
        
        this.element = document.createElement('div');
        this.element.className = 'app-window';
        this.element.id = `app-${this.appId}`;

        // 标题栏
        const titlebar = document.createElement('div');
        titlebar.className = 'app-titlebar';
        
        const title = document.createElement('div');
        title.className = 'app-title';
        title.innerHTML = `<span class="app-icon">${this.config.icon}</span><span>${this.config.name}</span>`;

        const controls = document.createElement('div');
        controls.className = 'app-controls';

        // 最小化按钮
        const minBtn = document.createElement('button');
        minBtn.className = 'app-btn';
        minBtn.innerHTML = '−';
        minBtn.onclick = (e) => {
            e.stopPropagation();
            this.minimize();
        };

        // 关闭按钮
        const closeBtn = document.createElement('button');
        closeBtn.className = 'app-btn close';
        closeBtn.innerHTML = '✕';
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            this.close();
        };

        controls.appendChild(minBtn);
        controls.appendChild(closeBtn);

        titlebar.appendChild(title);
        titlebar.appendChild(controls);

        // 内容区
        this.contentDiv = document.createElement('div');
        this.contentDiv.className = 'app-content';

        this.element.appendChild(titlebar);
        this.element.appendChild(this.contentDiv);

        container.appendChild(this.element);

        // 保存标题栏以便拖拽
        this.titlebar = titlebar;
    }

    setupPosition() {
        // 随机位置，避免重叠
        const offsetX = Math.random() * 100 - 50;
        const offsetY = Math.random() * 100 - 50;
        
        const x = window.innerWidth - 450 + offsetX;
        const y = 80 + offsetY;

        this.element.style.left = Math.max(0, x) + 'px';
        this.element.style.top = Math.max(0, y) + 'px';
        this.element.style.width = (this.config.width || 450) + 'px';
        this.element.style.height = (this.config.height || 400) + 'px';
    }

    setupDragAndDrop() {
        this.titlebar.addEventListener('mousedown', (e) => {
            if (e.target.closest('.app-controls')) return;

            this.isDragging = true;
            this.titlebar.classList.add('dragging');

            const rect = this.element.getBoundingClientRect();
            this.dragOffsetX = e.clientX - rect.left;
            this.dragOffsetY = e.clientY - rect.top;

            const onMouseMove = (moveEvent) => {
                if (this.isDragging) {
                    this.element.style.left = (moveEvent.clientX - this.dragOffsetX) + 'px';
                    this.element.style.top = (moveEvent.clientY - this.dragOffsetY) + 'px';
                }
            };

            const onMouseUp = () => {
                this.isDragging = false;
                this.titlebar.classList.remove('dragging');
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    setupContent() {
        // 使用注册的内容创建函数
        if (this.config.createContent) {
            this.config.createContent(this.contentDiv);
        }
    }

    minimize() {
        this.isMinimized = !this.isMinimized;
        this.element.classList.toggle('minimized');

        const framework = window.appFramework;
        if (framework) {
            framework.updateTaskbarState(this.appId);
        }
    }

    show() {
        this.element.style.display = 'flex';
        this.isMinimized = false;
        this.element.classList.remove('minimized');
    }

    toggle() {
        if (this.isMinimized) {
            this.minimize();
        } else {
            this.minimize();
        }
    }

    close() {
        this.element.remove();
        const framework = window.appFramework;
        if (framework) {
            framework.closeApp(this.appId);
        }
    }
}

// ================= 笔记应用 =================

class NotesApp {
    constructor(contentDiv) {
        this.contentDiv = contentDiv;
        this.notes = [];
        this.selectedNoteId = null;
        this.isAddingNote = false;

        this.render();
        this.loadNotes();
    }

    render() {
        this.contentDiv.innerHTML = `
            <div class="notes-app">
                <div class="notes-header">
                    <input type="text" class="notes-search" id="notesSearch" placeholder="搜索笔记...">
                    <button class="notes-add-btn" id="notesAddBtn">+ 新笔记</button>
                </div>
                <div class="notes-list" id="notesList"></div>
                <div id="notesEditor" style="display: none;"></div>
            </div>
        `;

        // 事件监听
        document.getElementById('notesAddBtn').addEventListener('click', () => this.showAddForm());
        document.getElementById('notesSearch').addEventListener('input', (e) => this.searchNotes(e.target.value));
    }

    async loadNotes() {
        try {
            const response = await fetch('/api/notes/list?limit=100');
            const data = await response.json();
            this.notes = data.notes || [];
            this.renderNotesList();
        } catch (error) {
            console.error('Failed to load notes:', error);
        }
    }

    renderNotesList() {
        const notesList = document.getElementById('notesList');
        
        if (this.notes.length === 0) {
            notesList.innerHTML = `
                <div class="notes-empty">
                    <div>
                        <div class="notes-empty-icon">📝</div>
                        <p>还没有笔记</p>
                        <p style="font-size: 12px; margin-top: 8px;">点击"新笔记"开始记录</p>
                    </div>
                </div>
            `;
            return;
        }

        notesList.innerHTML = '';

        this.notes.forEach(note => {
            const noteItem = document.createElement('div');
            noteItem.className = 'note-item';
            if (note.id === this.selectedNoteId) {
                noteItem.classList.add('selected');
            }

            const tagsHtml = (note.tags || [])
                .map(tag => `<span class="note-tag">#${tag}</span>`)
                .join('');

            noteItem.innerHTML = `
                <div style="display: flex; align-items: start; gap: 8px;">
                    <div style="flex: 1;">
                        <div class="note-item-title">${this.escapeHtml(note.title)}</div>
                        <div class="note-item-preview">${this.escapeHtml(note.content.substring(0, 50))}</div>
                        <div class="note-item-meta">
                            ${note.category ? `<span>📁 ${note.category}</span>` : ''}
                            ${tagsHtml}
                        </div>
                    </div>
                    <button class="note-delete-btn" data-note-id="${note.id}">🗑️</button>
                </div>
            `;

            noteItem.addEventListener('click', () => this.editNote(note));
            noteItem.querySelector('.note-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteNote(note.id);
            });

            notesList.appendChild(noteItem);
        });
    }

    showAddForm() {
        const editor = document.getElementById('notesEditor');
        editor.style.display = 'block';
        editor.innerHTML = `
            <div class="note-form">
                <div class="note-form-group">
                    <label>标题</label>
                    <input type="text" id="noteTitle" placeholder="输入笔记标题">
                </div>
                <div class="note-form-group">
                    <label>内容</label>
                    <textarea id="noteContent" placeholder="输入笔记内容"></textarea>
                </div>
                <div class="note-form-group">
                    <label>分类</label>
                    <input type="text" id="noteCategory" placeholder="输入分类(可选)">
                </div>
                <div class="note-form-group">
                    <label>标签</label>
                    <input type="text" id="noteTags" placeholder="输入标签，用逗号分隔(可选)">
                </div>
                <div class="note-form-actions">
                    <button class="note-save-btn" id="noteSaveBtn">保存笔记</button>
                    <button class="note-cancel-btn" id="noteCancelBtn">取消</button>
                </div>
            </div>
        `;

        document.getElementById('noteSaveBtn').addEventListener('click', () => this.saveNote());
        document.getElementById('noteCancelBtn').addEventListener('click', () => this.cancelEdit());

        // 自动聚焦
        setTimeout(() => document.getElementById('noteTitle').focus(), 100);
    }

    editNote(note) {
        this.selectedNoteId = note.id;
        this.renderNotesList();

        const editor = document.getElementById('notesEditor');
        editor.style.display = 'block';
        editor.innerHTML = `
            <div class="note-form">
                <div class="note-form-group">
                    <label>标题</label>
                    <input type="text" id="noteTitle" value="${this.escapeHtml(note.title)}">
                </div>
                <div class="note-form-group">
                    <label>内容</label>
                    <textarea id="noteContent">${this.escapeHtml(note.content)}</textarea>
                </div>
                <div class="note-form-group">
                    <label>分类</label>
                    <input type="text" id="noteCategory" value="${this.escapeHtml(note.category || '')}">
                </div>
                <div class="note-form-group">
                    <label>标签</label>
                    <input type="text" id="noteTags" value="${(note.tags || []).join(', ')}">
                </div>
                <div class="note-form-actions">
                    <button class="note-save-btn" id="noteSaveBtn">保存更改</button>
                    <button class="note-cancel-btn" id="noteCancelBtn">取消</button>
                </div>
            </div>
        `;

        document.getElementById('noteSaveBtn').addEventListener('click', () => this.saveNote(note.id));
        document.getElementById('noteCancelBtn').addEventListener('click', () => this.cancelEdit());
    }

    async saveNote(noteId = null) {
        const title = document.getElementById('noteTitle').value.trim();
        const content = document.getElementById('noteContent').value.trim();
        const category = document.getElementById('noteCategory').value.trim() || 'default';
        const tags = document.getElementById('noteTags').value
            .split(',')
            .map(t => t.trim())
            .filter(t => t);

        if (!title || !content) {
            alert('标题和内容不能为空');
            return;
        }

        try {
            const response = await fetch('/api/notes/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content, category, tags })
            });

            if (response.ok) {
                await this.loadNotes();
                this.cancelEdit();
                this.showNotification('✅ 笔记已保存');
            } else {
                this.showNotification('❌ 保存失败', true);
            }
        } catch (error) {
            console.error('Failed to save note:', error);
            this.showNotification('❌ 保存失败', true);
        }
    }

    async deleteNote(noteId) {
        if (!confirm('确认删除这条笔记吗？')) return;

        try {
            const response = await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
            if (response.ok) {
                await this.loadNotes();
                this.selectedNoteId = null;
                document.getElementById('notesEditor').style.display = 'none';
                this.showNotification('✅ 笔记已删除');
            }
        } catch (error) {
            console.error('Failed to delete note:', error);
        }
    }

    searchNotes(query) {
        if (!query) {
            this.renderNotesList();
            return;
        }

        const filtered = this.notes.filter(note => 
            note.title.toLowerCase().includes(query.toLowerCase()) ||
            note.content.toLowerCase().includes(query.toLowerCase()) ||
            (note.tags || []).some(tag => tag.toLowerCase().includes(query.toLowerCase()))
        );

        const notesList = document.getElementById('notesList');
        notesList.innerHTML = '';

        filtered.forEach(note => {
            const noteItem = document.createElement('div');
            noteItem.className = 'note-item';
            noteItem.innerHTML = `
                <div class="note-item-title">${this.escapeHtml(note.title)}</div>
                <div class="note-item-preview">${this.escapeHtml(note.content.substring(0, 50))}</div>
            `;
            noteItem.addEventListener('click', () => this.editNote(note));
            notesList.appendChild(noteItem);
        });
    }

    cancelEdit() {
        document.getElementById('notesEditor').style.display = 'none';
        this.selectedNoteId = null;
        this.renderNotesList();
    }

    showNotification(message, isError = false) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 16px;
            background: ${isError ? '#ef4444' : '#22c55e'};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}


// ================= 日程应用 =================
class ScheduleApp {
    constructor(container) {
        this.container = container;
        this.events = [];
        this.render();
        this.loadEvents();
    }

    render() {
        this.container.innerHTML = `
            <div class="schedule-app">
                <div class="schedule-header">
                    <input type="text" class="schedule-search" id="scheduleSearch" placeholder="搜索日程...">
                    <button class="schedule-add-btn" id="scheduleAddBtn">+ 新日程</button>
                </div>
                <div class="schedule-list" id="scheduleList"></div>
                <div id="scheduleEditor" style="display:none;"></div>
            </div>
        `;

        document.getElementById('scheduleAddBtn').addEventListener('click', () => this.showAddForm());
        document.getElementById('scheduleSearch').addEventListener('input', (e) => this.searchEvents(e.target.value));
    }

    async loadEvents() {
        try {
            const response = await fetch('/api/calendar/list?limit=200');
            const data = await response.json();
            this.events = data.events || [];
            this.renderEvents();
        } catch (error) {
            console.error('Failed to load events:', error);
            this.showNotification('加载日程失败', true);
        }
    }

    renderEvents(filtered) {
        const list = document.getElementById('scheduleList');
        const items = filtered || this.events;

        if (!items || items.length === 0) {
            list.innerHTML = `
                <div class="schedule-empty">
                    <div class="schedule-empty-icon">📅</div>
                    <div>还没有日程，点击右上角新增</div>
                </div>
            `;
            return;
        }

        list.innerHTML = '';
        items.forEach(ev => {
            const start = this.formatDate(ev.start);
            const end = ev.end ? this.formatDate(ev.end) : '';
            const item = document.createElement('div');
            item.className = 'schedule-item';
            item.innerHTML = `
                <div class="schedule-item-title">${this.escapeHtml(ev.title)}</div>
                <div class="schedule-item-time">${start}${end ? ' - ' + end : ''}</div>
                <div class="schedule-item-desc">${this.escapeHtml((ev.description || '').slice(0, 120))}</div>
                <button class="schedule-delete-btn">删除</button>
            `;
            item.querySelector('.schedule-delete-btn').addEventListener('click', () => this.deleteEvent(ev.id));
            list.appendChild(item);
        });
    }

    showAddForm() {
        const editor = document.getElementById('scheduleEditor');
        editor.innerHTML = `
            <div class="schedule-form">
                <input type="text" id="eventTitle" placeholder="标题" required>
                <textarea id="eventDesc" placeholder="描述" rows="3"></textarea>
                <label>开始时间</label>
                <input type="datetime-local" id="eventStart" required>
                <label>结束时间 (可选)</label>
                <input type="datetime-local" id="eventEnd">
                <label>提前提醒 (分钟，可选)</label>
                <input type="number" id="eventRemind" min="0" placeholder="0">
                <div class="schedule-form-actions">
                    <button class="schedule-cancel-btn" id="eventCancel">取消</button>
                    <button class="schedule-save-btn" id="eventSave">保存日程</button>
                </div>
            </div>
        `;
        editor.style.display = 'block';

        document.getElementById('eventCancel').addEventListener('click', () => {
            editor.style.display = 'none';
        });
        document.getElementById('eventSave').addEventListener('click', () => this.saveEvent());
    }

    async saveEvent() {
        const title = document.getElementById('eventTitle').value.trim();
        const description = document.getElementById('eventDesc').value.trim();
        const start = document.getElementById('eventStart').value;
        const end = document.getElementById('eventEnd').value;
        const remind = document.getElementById('eventRemind').value;

        if (!title || !start) {
            this.showNotification('标题和开始时间不能为空', true);
            return;
        }

        try {
            const payload = {
                title,
                description,
                start: this.toIso(start),
            };
            if (end) payload.end = this.toIso(end);
            if (remind) payload.remind_before_minutes = parseInt(remind, 10);

            const response = await fetch('/api/calendar/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.success) {
                await this.loadEvents();
                document.getElementById('scheduleEditor').style.display = 'none';
                this.showNotification('日程已保存');
            } else {
                this.showNotification(data.error || '保存失败', true);
            }
        } catch (error) {
            console.error('Failed to save event:', error);
            this.showNotification('保存失败', true);
        }
    }

    async deleteEvent(id) {
        if (!id) return;
        try {
            const res = await fetch(`/api/calendar/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                this.events = this.events.filter(ev => ev.id !== id);
                this.renderEvents();
                this.showNotification('已删除');
            } else {
                this.showNotification('删除失败', true);
            }
        } catch (error) {
            console.error('Delete event failed:', error);
            this.showNotification('删除失败', true);
        }
    }

    searchEvents(keyword) {
        const query = keyword.trim().toLowerCase();
        if (!query) {
            this.renderEvents();
            return;
        }
        const filtered = this.events.filter(ev =>
            (ev.title || '').toLowerCase().includes(query) ||
            (ev.description || '').toLowerCase().includes(query)
        );
        this.renderEvents(filtered);
    }

    formatDate(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const hh = String(d.getHours()).padStart(2, '0');
            const mm = String(d.getMinutes()).padStart(2, '0');
            return `${y}-${m}-${day} ${hh}:${mm}`;
        } catch (e) {
            return iso;
        }
    }

    toIso(localStr) {
        // local datetime-local string -> ISO
        try {
            const d = new Date(localStr);
            return d.toISOString();
        } catch (e) {
            return localStr;
        }
    }

    showNotification(message, isError = false) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 16px;
            background: ${isError ? '#ef4444' : '#22c55e'};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ================= 初始化应用框架 =================

document.addEventListener('DOMContentLoaded', () => {
    // 创建应用框架
    window.appFramework = new AppFramework();

    // 注册笔记应用（隐藏，仅后台调用）
    window.appFramework.registerApp('notes', {
        name: '笔记',
        icon: '📝',
        width: 480,
        height: 540,
        hidden: true, // 不在任务栏显示，后台自动调用
        createContent: (contentDiv) => {
            new NotesApp(contentDiv);
        }
    });

    // 注册日程应用（隐藏，仅任务触发）
    window.appFramework.registerApp('schedule', {
        name: '我的日程',
        icon: '🗓️',
        width: 520,
        height: 540,
        hidden: true, // 不在任务栏显示，仅任务调用时打开
        createContent: (contentDiv) => {
            new ScheduleApp(contentDiv);
        }
    });

    // 提供全局方法用于任务触发打开日程
    window.openScheduleApp = function() {
        window.appFramework.openApp('schedule');
    };

    console.log('[App Framework] 应用框架已初始化');
});
