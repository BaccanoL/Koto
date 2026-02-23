// ================= State =================
// 🔥 VERSION: 2026-02-14-03 - 多文件累加上传修复版
let currentSession = null;
let selectedFiles = [];
let setupComplete = false;
let lockedTaskType = null;  // 用户手动选择的任务类型
let selectedModel = 'auto'; // 用户选择的模型 (auto = 自动选择)
const MAX_UPLOAD_FILES = 10;

console.log('🔥 Koto App.js 已加载 - VERSION: 2026-02-14-03');

// ================= 窗口控制 =================
async function minimizeWindow() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.minimize) {
        await window.pywebview.api.minimize();
    }
}

async function maximizeWindow() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.maximize) {
        await window.pywebview.api.maximize();
    }
}

async function closeWindow() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.close) {
        await window.pywebview.api.close();
    } else {
        window.close();
    }
}

// ⭐ 改进：每个 session 有自己的生成状态，而不是全局的 isGenerating
// 这样可以支持多个对话并行，也能正确处理话题切换
const sessionStates = new Map();  // sessionName -> { isGenerating, abortController }

function getSessionState(sessionName) {
    if (!sessionStates.has(sessionName)) {
        sessionStates.set(sessionName, {
            isGenerating: false,
            abortController: null
        });
    }
    return sessionStates.get(sessionName);
}

function setSessionGenerating(sessionName, isGenerating) {
    const state = getSessionState(sessionName);
    state.isGenerating = isGenerating;
    console.log(`[STATE] Session ${sessionName}: isGenerating=${isGenerating}`);
}

function isSessionGenerating(sessionName) {
    const state = getSessionState(sessionName);
    return state.isGenerating;
}

function setSessionAbortController(sessionName, controller) {
    const state = getSessionState(sessionName);
    state.abortController = controller;
}

function getSessionAbortController(sessionName) {
    const state = getSessionState(sessionName);
    return state.abortController;
}

function setSessionTaskId(sessionName, taskId) {
    const state = getSessionState(sessionName);
    state.taskId = taskId || null;
}

function getSessionTaskId(sessionName) {
    const state = getSessionState(sessionName);
    return state.taskId || null;
}

// 任务类型到模型的映射
const TASK_MODELS = {
    'CHAT': 'gemini-3-flash-preview',
    'CODER': 'gemini-3-pro-preview', 
    'VISION': 'gemini-3-flash-preview',
    'PAINTER': 'nano-banana-pro-preview',
    'VOICE': 'gemini-3-flash-preview',  // 语音模式使用快速模型
    'RESEARCH': 'deep-research-pro-preview-12-2025',
    'FILE_GEN': 'gemini-3-pro-preview'
};

// ================= Notification =================
function showNotification(message, type = 'info', duration = 3000) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `<span>${message}</span>`;
    
    // 根据类型设置颜色
    let bgColor;
    switch (type) {
        case 'success':
            bgColor = '#22c55e';
            break;
        case 'error':
            bgColor = '#ef4444';
            break;
        case 'warning':
            bgColor = '#f59e0b';
            break;
        default:
            bgColor = '#3b82f6';
    }
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        background: ${bgColor};
        color: white;
        font-size: 14px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // 指定时间后自动消失
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// ================= Initialization =================
document.addEventListener('DOMContentLoaded', async () => {
    hideStartupSplash();

    // 1. 优先加载设置并应用主题（避免闪烁）
    await loadSettings();
    const theme = currentSettings?.appearance?.theme || 'light';
    applyTheme(theme);
    updateThemeSelector(theme);
    
    // 2. 检查是否需要设置向导
    await checkSetupStatus();
    
    // 3. 加载会话和状态
    loadSessions();
    checkStatus();
    initCapabilityButtons();
    
    // 4. 加载模型设置（从已加载的 currentSettings 中提取，无需重复请求）
    if (currentSettings?.ai) {
        selectedModel = currentSettings.ai.default_model || 'auto';
        const modelSelect = document.getElementById('settingModel');
        if (modelSelect) {
            modelSelect.value = selectedModel;
        }
    }
    
    // 5. Handle Enter key in modal
    document.getElementById('newSessionName').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            confirmNewSession();
        }
    });
    
    // 6. 监听系统主题变化（auto 模式下）
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if ((currentSettings?.appearance?.theme || 'light') === 'auto') {
            applyTheme('auto');
        }
    });
    
    // 7. 延迟初始化语音，等待 pywebview 就绪
    setTimeout(initVoice, 500);
    initVoicePanel();
    initProactiveUI();
});

function hideStartupSplash() {
    const splash = document.getElementById('startupSplash');
    if (!splash) return;
    splash.classList.add('hidden');
    setTimeout(() => splash.remove(), 300);
    document.body.classList.remove('loading');
}

// ================= Setup Wizard =================
async function checkSetupStatus() {
    try {
        const response = await fetch('/api/setup/status');
        const data = await response.json();
        
        if (!data.initialized || !data.has_api_key) {
            showSetupWizard();
        } else {
            setupComplete = true;
        }
    } catch (error) {
        console.error('Setup check failed:', error);
    }
}

function showSetupWizard() {
    document.getElementById('setupWizard').classList.add('active');
    document.getElementById('setupStep1').classList.add('active');
}

function hideSetupWizard() {
    document.getElementById('setupWizard').classList.remove('active');
}

async function saveApiKey() {
    const apiKey = document.getElementById('setupApiKey').value.trim();
    const status = document.getElementById('step1Status');
    
    if (!apiKey || apiKey.length < 10) {
        status.textContent = '❌ 请输入有效的 API Key';
        status.className = 'step-status error';
        return;
    }
    
    status.textContent = '⏳ 正在验证...';
    status.className = 'step-status loading';
    
    try {
        const response = await fetch('/api/setup/apikey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });
        const data = await response.json();
        
        if (data.success) {
            status.textContent = '✅ API Key 已保存';
            status.className = 'step-status success';
            document.getElementById('setupStep1').classList.remove('active');
            document.getElementById('setupStep1').classList.add('completed');
            document.getElementById('setupStep2').classList.add('active');
        } else {
            status.textContent = '❌ ' + (data.error || '保存失败');
            status.className = 'step-status error';
        }
    } catch (error) {
        status.textContent = '❌ 网络错误';
        status.className = 'step-status error';
    }
}

async function saveWorkspace() {
    const workspacePath = document.getElementById('setupWorkspacePath').value.trim();
    const status = document.getElementById('step2Status');
    
    status.textContent = '⏳ 正在创建工作区...';
    status.className = 'step-status loading';
    
    try {
        const response = await fetch('/api/setup/workspace', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: workspacePath })
        });
        const data = await response.json();
        
        if (data.success) {
            status.textContent = '✅ 工作区已创建: ' + data.path;
            status.className = 'step-status success';
            document.getElementById('setupStep2').classList.remove('active');
            document.getElementById('setupStep2').classList.add('completed');
            document.getElementById('setupStep3').classList.add('active');
        } else {
            status.textContent = '❌ ' + (data.error || '创建失败');
            status.className = 'step-status error';
        }
    } catch (error) {
        status.textContent = '❌ 网络错误';
        status.className = 'step-status error';
    }
}

async function testConnection() {
    const status = document.getElementById('step3Status');
    
    status.textContent = '⏳ 正在测试连接...';
    status.className = 'step-status loading';
    
    try {
        const response = await fetch('/api/setup/test');
        const data = await response.json();
        
        if (data.success) {
            status.textContent = `✅ 连接成功! (${data.latency}s) - ${data.message}`;
            status.className = 'step-status success';
            document.getElementById('setupStep3').classList.remove('active');
            document.getElementById('setupStep3').classList.add('completed');
            document.getElementById('startKotoBtn').disabled = false;
        } else {
            status.textContent = '❌ ' + (data.error || '连接失败');
            status.className = 'step-status error';
        }
    } catch (error) {
        status.textContent = '❌ 网络错误: ' + error.message;
        status.className = 'step-status error';
    }
}

function skipSetup() {
    if (confirm('跳过设置可能导致部分功能无法使用，确定要跳过吗？')) {
        hideSetupWizard();
    }
}

function finishSetup() {
    setupComplete = true;
    hideSetupWizard();
    loadSessions();
    checkStatus();
}

function browseSetupFolder() {
    // 使用现有的文件夹浏览功能
    currentBrowseTarget = 'setup_workspace';
    currentBrowsePath = 'C:\\';
    document.getElementById('manualPathInput').value = currentBrowsePath;
    loadFolderList(currentBrowsePath);
    document.getElementById('folderModal').classList.add('active');
}

// ================= Sessions =================
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        renderSessions(data.sessions);
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

function renderSessions(sessions) {
    const container = document.getElementById('sessionsList');
    
    if (sessions.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; color: var(--text-muted);">
                <p>No chats yet</p>
                <p style="font-size: 12px; margin-top: 8px;">Click "New Chat" to start</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = sessions.map(session => `
        <div class="session-item ${currentSession === session ? 'active' : ''}" 
             onclick="selectSession('${session}')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span class="session-name">${escapeHtml(session)}</span>
        </div>
    `).join('');
}

// ================= 返回欢迎页 =================
function goToWelcome() {
    // ⭐ 改进：如果之前的会话还在生成，先中止它
    if (currentSession && isSessionGenerating(currentSession)) {
        const controller = getSessionAbortController(currentSession);
        if (controller) {
            console.log(`[CLEANUP] Aborting previous session ${currentSession}`);
            controller.abort();
        }
        setSessionGenerating(currentSession, false);
    }
    
    currentSession = null;
    document.getElementById('chatTitle').textContent = '选择或创建对话';
    
    // 取消所有会话的选中状态
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 显示欢迎页面
    const container = document.getElementById('chatMessages');
    document.getElementById('welcomeScreen').style.display = 'block';
    
    // 清除聊天消息，只保留欢迎页
    const messages = container.querySelectorAll('.message');
    messages.forEach(msg => msg.remove());
    
    // 取消任务锁定
    lockedTaskType = null;
    document.querySelectorAll('.capability').forEach(c => c.classList.remove('selected'));
    updateTaskIndicator(null);
}

async function selectSession(sessionName) {
    // ⭐ 改进：允许多个会话并行运行，不中止前一个会话的任务
    // 只切换 currentSession 用于 UI 显示和新消息输入，但不中止前一个会话的生成
    console.log(`[SWITCH] 从 ${currentSession} 切换到 ${sessionName}（保持后台任务运行）`);
    
    currentSession = sessionName;
    document.getElementById('chatTitle').textContent = sessionName;
    
    // Update active state
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.remove('active');
        if (item.querySelector('.session-name').textContent === sessionName) {
            item.classList.add('active');
        }
    });
    
    // Load chat history
    try {
        const response = await fetch(`/api/sessions/${encodeURIComponent(sessionName)}`);
        const data = await response.json();
        renderChatHistory(data.history);
    } catch (error) {
        console.error('Failed to load session:', error);
    }
}

// ================= 图片容器DOM渲染 =================
function renderImagesInContainer(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const imagesJson = container.getAttribute('data-images');
    if (!imagesJson) return;
    
    try {
        const images = JSON.parse(imagesJson);
        if (!Array.isArray(images) || images.length === 0) return;
        
        // 清空容器
        container.innerHTML = '';
        container.style.display = 'flex';
        container.style.gap = '10px';
        container.style.flexWrap = 'wrap';
        container.style.marginTop = '12px';
        
        for (let i = 0; i < images.length; i++) {
            const img = images[i];
            const url = `/api/workspace/${img.replace(/\\\\/g, '/')}`;
            
            const link = document.createElement('a');
            link.href = url;
            link.target = '_blank';
            link.style.display = 'inline-block';
            
            const imgEl = document.createElement('img');
            imgEl.src = url;
            imgEl.alt = `Generated image ${i + 1}`;
            imgEl.className = 'generated-image';
            imgEl.style.maxWidth = '400px';
            imgEl.style.maxHeight = '400px';
            imgEl.style.borderRadius = '14px';
            imgEl.style.border = '1px solid var(--border-color)';
            imgEl.style.cursor = 'pointer';
            
            imgEl.onload = () => console.log(`✓ History image ${i + 1} loaded: ${url}`);
            imgEl.onerror = () => console.error(`✗ History image ${i + 1} failed: ${url}`);
            
            link.appendChild(imgEl);
            container.appendChild(link);
        }
    } catch (e) {
        console.error(`Failed to parse images for container ${containerId}:`, e);
    }
}

// ================= 智能会话名称生成 =================
function generateSessionName(message) {
    // 从消息中提取关键词作为会话名称
    let name = message.trim();
    
    // 移除常见的前缀词
    const prefixes = ['请', '帮我', '帮忙', '能不能', '可以', '我想', '我要', '给我', 'please', 'help me', 'can you'];
    for (const prefix of prefixes) {
        if (name.toLowerCase().startsWith(prefix)) {
            name = name.slice(prefix.length).trim();
        }
    }
    
    // 截取前20个字符作为名称
    if (name.length > 20) {
        name = name.slice(0, 20) + '...';
    }
    
    // 如果太短或为空，使用时间戳
    if (name.length < 2) {
        const now = new Date();
        name = `对话 ${now.getMonth() + 1}/${now.getDate()} ${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
    
    return name;
}

async function createNewSession(name = null) {
    // 如果没有提供名称，显示弹窗让用户输入
    if (!name) {
        showNewSessionModal();
        return;
    }
    
    // 自动创建会话
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
        
        if (response.ok) {
            currentSession = name;
            document.getElementById('chatTitle').textContent = name;
            loadSessions();
            
            // 清空聊天区域
            const container = document.getElementById('chatMessages');
            container.innerHTML = '';
        }
    } catch (error) {
        console.error('Failed to create session:', error);
    }
}

function showNewSessionModal() {
    document.getElementById('newSessionModal').classList.add('active');
    document.getElementById('newSessionName').value = '';
    document.getElementById('newSessionName').focus();
}

function closeModal() {
    document.getElementById('newSessionModal').classList.remove('active');
}

async function confirmNewSession() {
    const name = document.getElementById('newSessionName').value.trim();
    if (!name) return;
    
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        if (data.success) {
            closeModal();
            await loadSessions();
            selectSession(data.session);
        }
    } catch (error) {
        console.error('Failed to create session:', error);
    }
}

async function deleteCurrentSession() {
    if (!currentSession) return;
    
    if (!confirm(`Delete chat "${currentSession}"?`)) return;
    
    const deletingSession = currentSession;
    
    // ⭐ 改进：在删除前，如果有生成，先中止它
    if (isSessionGenerating(deletingSession)) {
        const controller = getSessionAbortController(deletingSession);
        if (controller) {
            console.log(`[CLEANUP] Deleting session ${deletingSession}, aborting its generation`);
            controller.abort();
        }
        setSessionGenerating(deletingSession, false);
    }
    
    try {
        const response = await fetch(`/api/sessions/${encodeURIComponent(deletingSession)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            // ⭐ 改进：实时移除该话题的 DOM 元素
            document.querySelectorAll('.session-item').forEach(item => {
                if (item.querySelector('.session-name').textContent === deletingSession) {
                    item.remove();
                }
            });
            
            currentSession = null;
            document.getElementById('chatTitle').textContent = '选择或创建对话';
            
            // 清除聊天消息
            const container = document.getElementById('chatMessages');
            container.innerHTML = document.getElementById('welcomeScreen').outerHTML;
            
            // ⭐ 不重新加载列表，而是使用上面的 DOM 移除方式
            console.log(`[DELETE] 已删除话题 ${deletingSession}，UI 实时更新`);
        }
    } catch (error) {
        console.error('Failed to delete session:', error);
    }
}

// ================= Chat =================
function renderChatHistory(history) {
    const container = document.getElementById('chatMessages');
    
    if (history.length === 0) {
        container.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-logo">言</div>
                <h2>Start chatting</h2>
                <p>Send a message to begin the conversation</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    for (let i = 0; i < history.length; i += 2) {
        const userMsg = history[i];
        const assistantMsg = history[i + 1];
        
        if (userMsg) {
            container.innerHTML += renderMessage('user', userMsg.parts[0], {
                timestamp: userMsg.timestamp
            });
        }
        if (assistantMsg) {
            // 跳过未完成的占位符回复
            const msgText = assistantMsg.parts ? assistantMsg.parts[0] : '';
            if (msgText === '⏳ 处理中...') {
                // 显示为中断/未完成状态
                const meta = {
                    task: assistantMsg.task,
                    model: assistantMsg.model_name,
                    timestamp: assistantMsg.timestamp
                };
                container.innerHTML += renderMessage('assistant', '⚠️ *此任务未完成（可能因断连或崩溃中断）*', meta);
            } else {
                // 提取 meta 信息（包括图片、任务类型等）
                const meta = {
                    task: assistantMsg.task,
                    model: assistantMsg.model_name,
                    images: assistantMsg.images || [],
                    saved_files: assistantMsg.saved_files || [],
                    time: assistantMsg.time,
                    timestamp: assistantMsg.timestamp
                };
                const msgHtml = renderMessage('assistant', assistantMsg.parts[0], meta);
                container.innerHTML += msgHtml;
                
                // 渲染图片容器
                if (meta.images && meta.images.length > 0) {
                    // 延迟以确保DOM已更新
                    setTimeout(() => {
                        const containers = container.querySelectorAll('[id^="images-"]');
                        containers.forEach(c => renderImagesInContainer(c.id));
                    }, 0);
                }
            }
        }
    }
    
    scrollToBottom();
    highlightCode();
    // 渲染 Mermaid 图表（历史消息中可能包含）
    setTimeout(() => renderMermaidBlocks(), 100);
}

// 🎯 PPT 相关函数（P0 新增）
function downloadPPT(sessionId) {
    console.log(`[PPT] 下载 PPT 会话: ${sessionId}`);
    
    // 调用后端生成下载链接
    fetch('/api/ppt/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
    })
    .then(response => {
        if (response.ok) return response.blob();
        throw new Error('下载失败');
    })
    .then(blob => {
        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `presentation_${sessionId.substr(0, 8)}.pptx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification('✅ PPT 下载成功', 'success');
    })
    .catch(err => {
        console.error('[PPT] 下载失败:', err);
        showNotification('❌ PPT 下载失败: ' + err.message, 'error');
    });
}

function formatMessageTimestamp(ts) {
    if (!ts) return '';
    const dt = new Date(ts);
    if (Number.isNaN(dt.getTime())) return '';

    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

function renderMessage(role, content, meta = {}) {
    const avatar = role === 'user' ? 'U' : '言';
    const sender = role === 'user' ? 'You' : 'Koto';
    
    // 模型名称简化显示 (2026-01)
    const modelDisplayName = {
        // Gemini 3 系列 (最新)
        'gemini-3-flash-preview': 'Gemini 3 Flash ⚡',
        'gemini-3-pro-preview': 'Gemini 3 Pro 🚀',
        'gemini-3-pro-image-preview': 'Gemini 3 Vision 👁️',
        // Gemini 2.5 系列
        'gemini-2.5-flash': 'Gemini 2.5 Flash ⚡',
        'gemini-2.5-pro': 'Gemini 2.5 Pro 🚀',
        // 图像生成
        'nano-banana-pro-preview': 'Nano Banana Pro 🎨',
        'imagen-4.0-generate-001': 'Imagen 4 🖼️',
        // 特殊
        'deep-research-pro-preview-12-2025': 'Deep Research 🔬',
        // 本地执行
        'local-executor': 'Local Executor 🖥️',
    };
    
    let metaHtml = '';
    const timestampText = formatMessageTimestamp(meta.timestamp);

    if (meta.task) {
        const friendlyModel = modelDisplayName[meta.model] || meta.model || 'Auto';
        const routeMethod = meta.route_method || '';
        metaHtml = `
            <span class="task-badge ${meta.task.toLowerCase()}">${meta.task}</span>
            <span class="model-info" title="${meta.model}\n路由: ${routeMethod}">📦 ${friendlyModel}</span>
            <span class="time-info">⏱️ ${meta.time || ''}</span>
        `;
    }

    if (timestampText) {
        metaHtml += `<span class="time-info" title="${meta.timestamp}">🕒 ${timestampText}</span>`;
    }
    
    let imagesHtml = '';
    const containerId = `images-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    if (meta.images && meta.images.length > 0) {
        imagesHtml = `<div class="generated-images" id="${containerId}" data-images='${JSON.stringify(meta.images)}'></div>`;
    }
    
    let filesHtml = '';
    if (meta.saved_files && meta.saved_files.length > 0) {
        filesHtml = `
            <div class="saved-files">
                <div class="saved-files-title">✓ Files saved to workspace:</div>
                ${meta.saved_files.map(file => `
                    <a href="javascript:void(0)" class="saved-file-link" title="点击打开 ${file}" onclick="fetch('/api/open-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filepath:'${file.replace(/'/g, "\\'")}'})}).then(r=>r.json()).then(d=>{if(!d.success)console.error(d.error)}).catch(e=>console.error(e));return false;">
                        <div class="saved-file">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <span>${file}</span>
                        </div>
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    // Parse markdown for assistant messages
    const parsedContent = role === 'assistant' ? parseMarkdown(content) : escapeHtml(content);
    
    // 用户上传的文件附件显示
    let attachmentHtml = '';
    if (meta.attachments && meta.attachments.length > 0) {
        const items = meta.attachments.map(att => {
            const isImage = att.type && att.type.startsWith('image');
            const icon = isImage ? '🖼️' : '📄';
            const sizeStr = att.size ? `(${formatFileSize(att.size)})` : '';
            return `
                <div class="message-attachment file-attachment">
                    <div class="attachment-icon">${icon}</div>
                    <div class="attachment-info">
                        <span class="attachment-name">${att.name}</span>
                        <span class="attachment-size">${sizeStr}</span>
                    </div>
                </div>
            `;
        }).join('');
        attachmentHtml = `<div class="message-attachment-list">${items}</div>`;
    } else if (meta.attachment) {
        const att = meta.attachment;
        const isImage = att.type && att.type.startsWith('image');
        const icon = isImage ? '🖼️' : '📄';
        const sizeStr = att.size ? `(${formatFileSize(att.size)})` : '';
        
        if (isImage && att.preview) {
            attachmentHtml = `
                <div class="message-attachment image-attachment">
                    <img src="${att.preview}" alt="${att.name}" class="attachment-preview">
                    <div class="attachment-info">
                        <span class="attachment-name">${icon} ${att.name}</span>
                        <span class="attachment-size">${sizeStr}</span>
                    </div>
                </div>
            `;
        } else {
            attachmentHtml = `
                <div class="message-attachment file-attachment">
                    <div class="attachment-icon">${icon}</div>
                    <div class="attachment-info">
                        <span class="attachment-name">${att.name}</span>
                        <span class="attachment-size">${sizeStr}</span>
                    </div>
                </div>
            `;
        }
    }
    
    // 🎯 PPT 编辑/下载按钮（P0 新增）
    let pptHtml = '';
    if (meta.ppt_session_id && role === 'assistant' && meta.task === 'FILE_GEN') {
        const sessionId = meta.ppt_session_id;
        pptHtml = `
            <div class="ppt-actions">
                <div class="ppt-actions-title">📊 PPT 已生成</div>
                <div class="ppt-buttons">
                    <a href="/edit-ppt/${sessionId}" class="ppt-btn ppt-edit-btn" title="打开编辑器">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"></path>
                        </svg>
                        📝 编辑
                    </a>
                    <button class="ppt-btn ppt-download-btn" onclick="downloadPPT('${sessionId}')" title="下载 PPTX">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        ⬇️ 下载
                    </button>
                </div>
            </div>
        `;
    }
    
    return `
        <div class="message ${role}">
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${sender}</span>
                    <div class="message-meta">${metaHtml}</div>
                </div>
                ${attachmentHtml}
                <div class="message-body">${parsedContent}</div>
                ${pptHtml}
                ${imagesHtml}
                ${filesHtml}
            </div>
        </div>
    `;
}

// 文件大小格式化
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function sendMessage(event) {
    event.preventDefault();
    
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const message = input.value.trim();
    
    // ⭐ 改进：使用 session 特定的状态，而不是全局 isGenerating
    const isCurrentSessionGenerating = isSessionGenerating(currentSession);
    
    // 如果正在生成，点击按钮表示停止
    if (isCurrentSessionGenerating) {
        sendBtn.disabled = true;
        
        // ⭐ 使用 AbortController 立即停止 fetch
        const controller = getSessionAbortController(currentSession);
        if (controller) {
            console.log(`[INTERRUPT] Aborting fetch for session ${currentSession}`);
            controller.abort();
        }
        
        // 同时通知后端
        try {
            const activeTaskId = getSessionTaskId(currentSession);
            await fetch('/api/chat/interrupt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session: currentSession, task_id: activeTaskId })
            });
            console.log('[INTERRUPT] Backend interrupt signal sent');
        } catch (e) {
            console.error('Interrupt signal failed:', e);
        }
        return;
    }
    
    if (!message && selectedFiles.length === 0) return;
    
    // === 如果没有选择对话，自动创建一个 ===
    if (!currentSession) {
        // 根据消息内容生成会话名称
        const sessionName = generateSessionName(message);
        await createNewSession(sessionName);
    }
    
    // Clear input
    input.value = '';
    input.style.height = 'auto';
    
    // Add user message to UI
    const container = document.getElementById('chatMessages');
    
    // Remove welcome screen if present
    const welcome = container.querySelector('.welcome-screen');
    if (welcome) welcome.remove();
    
    // 准备附件信息（如果有文件）
    let attachmentInfo = null;
    let attachmentList = null;
    if (selectedFiles.length === 1) {
        const file = selectedFiles[0];
        attachmentInfo = {
            name: file.name,
            type: file.type,
            size: file.size,
            preview: null
        };
        if (file.type && file.type.startsWith('image')) {
            attachmentInfo.preview = URL.createObjectURL(file);
        }
    } else if (selectedFiles.length > 1) {
        attachmentList = selectedFiles.map(file => ({
            name: file.name,
            type: file.type,
            size: file.size
        }));
    }
    
    container.innerHTML += renderMessage('user', message || '(附件)', { attachment: attachmentInfo, attachments: attachmentList });
    scrollToBottom();
    
    // === 确定任务类型和模型 ===
    let taskType = lockedTaskType;  // 用户锁定的任务类型
    let modelToUse = selectedModel; // 用户选择的模型
    
    // === 第一步：预分析任务（如果没有锁定） ===
    showLoading('🔍 分析任务类型...', '');
    
    let taskInfo = null;
    try {
        const analyzeResp = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                locked_task: taskType,     // 传递锁定的任务
                locked_model: modelToUse,  // 传递选择的模型
                has_file: selectedFiles.length > 0,  // 是否有文件
                file_type: selectedFiles.length === 1 ? selectedFiles[0].type : 'multiple'  // 文件类型
            })
        });
        taskInfo = await analyzeResp.json();
        
        // 显示选择的模型和任务类型 (包含速度标签)
        const displayTask = taskType || taskInfo.task;
        const modelDisplay = taskInfo.model_speed 
            ? `${taskInfo.model_name} ${taskInfo.model_speed}`
            : taskInfo.model_name;
        showLoading(`✨ ${displayTask} 任务处理中...`, modelDisplay);
    } catch (e) {
        showLoading('Koto 正在思考...', '');
    }
    
    // === 第二步：发送请求获取流式响应 ===
    try {
        setSessionGenerating(currentSession, true);
        
        // 切换发送按钮为停止状态
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.classList.add('generating');
        sendBtn.disabled = false;
        sendBtn.title = '停止生成';
        
        // 创建一个占位符消息
        const msgId = 'msg-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant';
        msgDiv.id = msgId;
        msgDiv.innerHTML = `
            <div class="message-avatar">言</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">Koto</span>
                    <div class="message-meta">
                        <span class="task-badge ${(taskType || taskInfo?.task || 'chat').toLowerCase()}">${taskType || taskInfo?.task || 'CHAT'}</span>
                        <span class="model-info">📦 ${taskInfo?.model_name || 'Loading...'}</span>
                        <span class="time-info" id="${msgId}-time">⏱️ ...</span>
                    </div>
                </div>
                <div class="message-body" id="${msgId}-body">
                    <span class="typing-cursor">▊</span>
                </div>
            </div>
        `;
        const container2 = document.getElementById('chatMessages');
        container2.appendChild(msgDiv);
        
        scrollToBottom();
        
        // 发送流式请求
        const startTime = Date.now();
        let response;
        
        if (selectedFiles.length > 0) {
            // Send with file
            const formData = new FormData();
            formData.append('session', currentSession);
            formData.append('message', message);
            selectedFiles.forEach(file => formData.append('file', file));
            formData.append('file_count', String(selectedFiles.length));
            formData.append('locked_task', taskType || '');
            formData.append('locked_model', modelToUse || 'auto');

            const abortController = new AbortController();
            setSessionAbortController(currentSession, abortController);
            
            response = await fetch('/api/chat/file', {
                method: 'POST',
                body: formData,
                signal: abortController.signal,
                keepalive: true
            });
            
            // 检查响应类型：SSE流式 or JSON
            const contentType = response.headers.get('Content-Type') || '';
            
            if (contentType.includes('text/event-stream')) {
                // === SSE 流式响应（DOC_ANNOTATE等长任务）===
                console.log('[FILE UPLOAD] 检测到SSE流式响应，切换到流式读取');
                removeFile();
                
                const bodyEl = document.getElementById(`${msgId}-body`);
                const timeEl = document.getElementById(`${msgId}-time`);
                let fullText = '';
                let lastUpdateTime = Date.now();
                let streamComplete = false;
                
                // 累积进度步骤追踪
                let completedSteps = [];  // [{message, detail}]
                let currentStage = null;
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let streamBuffer = '';
                
                while (!streamComplete) {
                    try {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value, { stream: true });
                        streamBuffer += chunk;
                        const lines = streamBuffer.split('\n');
                        streamBuffer = lines.pop() || '';
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    
                                    if (data.type === 'token') {
                                        fullText += data.content;
                                        if (Date.now() - lastUpdateTime > 50) {
                                            try {
                                                bodyEl.innerHTML = parseMarkdown(fullText) + '<span class="typing-cursor">▊</span>';
                                            } catch (e) {
                                                bodyEl.innerHTML = `<div style="white-space:pre-wrap;">${escapeHtml(fullText)}</div><span class="typing-cursor">▊</span>`;
                                            }
                                            scrollToBottom();
                                            lastUpdateTime = Date.now();
                                        }
                                    } else if (data.type === 'progress') {
                                        // 显示进度（累积已完成步骤）
                                        const progressPct = data.progress || 0;
                                        const progressMsg = data.message || '';
                                        const progressDetail = data.detail || '';
                                        const stage = data.stage || '';
                                        
                                        // 检测阶段完成：当 stage 以 _complete 结尾或为 complete 时记录为已完成步骤
                                        if (stage && (stage.endsWith('_complete') || stage === 'complete')) {
                                            completedSteps.push({ message: progressMsg, detail: progressDetail });
                                            currentStage = null;
                                        } else if (stage && stage !== currentStage) {
                                            // 阶段切换（非完成），更新当前阶段
                                            currentStage = stage;
                                        }
                                        
                                        // 构建累积进度显示
                                        let progressHtml = `<div class="doc-progress" style="padding:16px;">`;
                                        
                                        // 1. 已完成的步骤（带 ✓）
                                        for (const step of completedSteps) {
                                            progressHtml += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;opacity:0.85;">`;
                                            progressHtml += `<span style="color:#22c55e;font-size:16px;">✓</span>`;
                                            progressHtml += `<span style="color:#666;">${step.message}</span>`;
                                            if (step.detail) {
                                                progressHtml += `<span style="color:#999;font-size:12px;margin-left:4px;">${step.detail}</span>`;
                                            }
                                            progressHtml += `</div>`;
                                        }
                                        
                                        // 2. 当前活跃步骤（仅在非 complete 阶段显示）
                                        if (stage !== 'complete') {
                                            progressHtml += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;margin-top:${completedSteps.length > 0 ? '8' : '0'}px;">`;
                                            progressHtml += `<span class="typing-cursor" style="animation:blink 1s infinite;">▊</span>`;
                                            progressHtml += `<strong>${progressMsg}</strong>`;
                                            progressHtml += `</div>`;
                                            if (progressDetail) {
                                                progressHtml += `<div style="color:#888;font-size:13px;margin-bottom:8px;">${progressDetail}</div>`;
                                            }
                                        }
                                        
                                        // 3. 进度条
                                        progressHtml += `<div style="background:rgba(0,0,0,0.06);border-radius:8px;height:6px;overflow:hidden;margin-top:8px;">`;
                                        progressHtml += `<div style="background:linear-gradient(90deg,#4361ee,#3a86ff);height:100%;width:${progressPct}%;transition:width 0.5s ease;border-radius:8px;"></div>`;
                                        progressHtml += `</div>`;
                                        progressHtml += `<div style="text-align:right;font-size:12px;color:#666;margin-top:4px;">${progressPct}%</div>`;
                                        progressHtml += `</div>`;
                                        
                                        bodyEl.innerHTML = progressHtml;
                                        scrollToBottom();
                                    } else if (data.type === 'classification') {
                                        console.log('[FILE STREAM] 任务分类:', data.task_type);
                                        if (data.task_id) {
                                            setSessionTaskId(currentSession, data.task_id);
                                        }
                                    } else if (data.type === 'info') {
                                        fullText += `*${data.message}*\n\n`;
                                        bodyEl.innerHTML = parseMarkdown(fullText);
                                        scrollToBottom();
                                    } else if (data.type === 'error') {
                                        fullText += `\n\n❌ ${data.message}\n`;
                                        bodyEl.innerHTML = parseMarkdown(fullText);
                                        scrollToBottom();
                                    } else if (data.type === 'done') {
                                        streamComplete = true;
                                        const elapsedTime = data.total_time ? data.total_time.toFixed(2) : ((Date.now() - startTime) / 1000).toFixed(2);
                                        
                                        bodyEl.innerHTML = parseMarkdown(fullText);
                                        renderMermaidBlocks();
                                        timeEl.textContent = `⏱️ ${elapsedTime}s`;
                                        
                                        // 添加文件链接
                                        if (data.saved_files && data.saved_files.length > 0) {
                                            const filesDiv = document.createElement('div');
                                            filesDiv.className = 'saved-files';
                                            const titleDiv = document.createElement('div');
                                            titleDiv.className = 'saved-files-title';
                                            titleDiv.textContent = '✓ 生成的文件:';
                                            filesDiv.appendChild(titleDiv);
                                            
                                            for (let file of data.saved_files) {
                                                const fileLink = document.createElement('a');
                                                fileLink.href = 'javascript:void(0)';
                                                fileLink.className = 'saved-file-link';
                                                fileLink.style.textDecoration = 'none';
                                                fileLink.style.display = 'block';
                                                fileLink.style.cursor = 'pointer';
                                                fileLink.title = `点击打开 ${file}`;
                                                fileLink.addEventListener('click', (e) => {
                                                    e.preventDefault();
                                                    fetch('/api/open-file', {
                                                        method: 'POST',
                                                        headers: {'Content-Type': 'application/json'},
                                                        body: JSON.stringify({filepath: file})
                                                    });
                                                });
                                                const fileDiv = document.createElement('div');
                                                fileDiv.className = 'saved-file';
                                                fileDiv.textContent = `📄 ${file}`;
                                                fileLink.appendChild(fileDiv);
                                                filesDiv.appendChild(fileLink);
                                            }
                                            bodyEl.appendChild(filesDiv);
                                        }
                                        
                                        // 完成标记
                                        const completeDiv = document.createElement('div');
                                        completeDiv.className = 'task-complete';
                                        completeDiv.style.cssText = 'margin-top:12px;padding:10px;border-radius:6px;background:rgba(42,212,137,0.1);font-size:13px;color:#2ad489;';
                                        completeDiv.textContent = `✅ 任务完成  耗时 ${elapsedTime}s`;
                                        bodyEl.appendChild(completeDiv);
                                    }
                                } catch (parseErr) {
                                    console.warn('[FILE STREAM] Parse error:', parseErr);
                                }
                            }
                        }
                    } catch (readErr) {
                        console.error('[FILE STREAM] Read error:', readErr);
                        break;
                    }
                }
                
            } else {
                // === 普通 JSON 响应（非流式）===
                const data = await response.json();
                const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(2);
                
                const bodyEl = document.getElementById(`${msgId}-body`);
                const timeEl = document.getElementById(`${msgId}-time`);
                bodyEl.innerHTML = parseMarkdown(data.response);
                timeEl.textContent = `⏱️ ${elapsedTime}s`;
                
                if (data.open_suggestion_panel && data.file_path) {
                    console.log('[FILE UPLOAD] 打开建议面板:', data.file_path);
                    openSuggestionPanel(data.file_path, data.requirement || '');
                }
                
                if (data.images && data.images.length > 0) {
                    const imagesDiv = document.createElement('div');
                    imagesDiv.className = 'generated-images';
                    imagesDiv.style.display = 'flex';
                    imagesDiv.style.gap = '10px';
                    imagesDiv.style.flexWrap = 'wrap';
                    imagesDiv.style.marginTop = '12px';
                    
                    for (const img of data.images) {
                        const link = document.createElement('a');
                        link.href = `/api/workspace/${img}`;
                        link.target = '_blank';
                        link.style.display = 'inline-block';
                        
                        const imgEl = document.createElement('img');
                        imgEl.src = `/api/workspace/${img}`;
                        imgEl.alt = 'Generated image';
                        imgEl.className = 'generated-image';
                        imgEl.style.maxWidth = '400px';
                        imgEl.style.borderRadius = '14px';
                        
                        link.appendChild(imgEl);
                        imagesDiv.appendChild(link);
                    }
                    bodyEl.appendChild(imagesDiv);
                }
                
                removeFile();
            }
        } else {
            // === 流式输出 ===
            // ⭐ 创建 AbortController 来支持取消请求
            const abortController = new AbortController();
            setSessionAbortController(currentSession, abortController);

            const effectiveTaskType = String(taskType || '').toUpperCase();
            const useUnifiedAgentStream = (effectiveTaskType === 'AGENT');
            const streamEndpoint = useUnifiedAgentStream ? '/api/agent/process-stream' : '/api/chat/stream';
            const streamPayload = useUnifiedAgentStream
                ? {
                    request: message,
                    context: { history: [] },
                    session_id: currentSession,
                    model: modelToUse || 'gemini-3-flash-preview'
                }
                : {
                    session: currentSession,
                    message: message,
                    locked_task: taskType,
                    locked_model: modelToUse
                };
            
            console.log('[FETCH] Initiating stream request...');
            response = await fetch(streamEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(streamPayload),
                signal: abortController.signal,  // ⭐ 传递 abort signal
                keepalive: true  // 保持连接
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            console.log('[FETCH] Stream response received, starting to read...');
            
            const bodyEl = document.getElementById(`${msgId}-body`);
            const timeEl = document.getElementById(`${msgId}-time`);
            let fullText = '';
            let agentThoughtText = ''; // 记录Agent思考文本，用于去重
            let lastUpdateTime = Date.now();
            let streamComplete = false;
            let hasReceivedData = false; // 追踪是否收到过数据
            let agentStepCounter = 0;

            const tryParseObservationJson = (raw) => {
                if (!raw || typeof raw !== 'string') return null;
                const trimmed = raw.trim();
                if (!trimmed || (trimmed[0] !== '{' && trimmed[0] !== '[')) return null;
                try {
                    return JSON.parse(trimmed);
                } catch {
                    return null;
                }
            };

            const renderObservationHtml = (obj, rawText) => {
                if (!obj || typeof obj !== 'object') {
                    return `<div class="agent-observation-text">${escapeHtml(rawText || '')}</div>`;
                }

                if (Array.isArray(obj.warnings)) {
                    const warningItems = obj.warnings.length
                        ? obj.warnings.map(w => `<li>${escapeHtml(String(w))}</li>`).join('')
                        : '<li>无异常告警</li>';
                    return `<div class="agent-observation-card"><strong>系统告警</strong><ul>${warningItems}</ul></div>`;
                }

                if (obj.usage_percent !== undefined && obj.logical_cores !== undefined) {
                    return `
                        <div class="agent-observation-card">
                            <strong>CPU 状态</strong>
                            <div>使用率: ${escapeHtml(String(obj.usage_percent))}%</div>
                            <div>核心: ${escapeHtml(String(obj.physical_cores ?? '-'))}/${escapeHtml(String(obj.logical_cores ?? '-'))}</div>
                            <div>频率: ${escapeHtml(String(obj.frequency_mhz ?? '-'))} MHz</div>
                        </div>`;
                }

                if (obj.total_gb !== undefined && obj.percent !== undefined && obj.swap_total_gb !== undefined) {
                    return `
                        <div class="agent-observation-card">
                            <strong>内存状态</strong>
                            <div>总内存: ${escapeHtml(String(obj.total_gb))} GB</div>
                            <div>已用: ${escapeHtml(String(obj.used_gb ?? '-'))} GB (${escapeHtml(String(obj.percent))}%)</div>
                            <div>可用: ${escapeHtml(String(obj.available_gb ?? '-'))} GB</div>
                        </div>`;
                }

                if (obj.drives && typeof obj.drives === 'object') {
                    const driveRows = Object.entries(obj.drives).slice(0, 6).map(([drive, info]) => {
                        const used = info?.used_gb ?? '-';
                        const total = info?.total_gb ?? '-';
                        const percent = info?.percent ?? '-';
                        return `<li>${escapeHtml(String(drive))}: ${escapeHtml(String(used))}/${escapeHtml(String(total))} GB (${escapeHtml(String(percent))}%)</li>`;
                    }).join('');
                    return `
                        <div class="agent-observation-card">
                            <strong>磁盘状态</strong>
                            <div>总容量: ${escapeHtml(String(obj.total_gb ?? '-'))} GB，剩余: ${escapeHtml(String(obj.free_gb ?? '-'))} GB</div>
                            <ul>${driveRows || '<li>无驱动器信息</li>'}</ul>
                        </div>`;
                }

                if (obj.hostname && obj.interfaces) {
                    const interfaceCount = Object.keys(obj.interfaces || {}).length;
                    return `
                        <div class="agent-observation-card">
                            <strong>网络状态</strong>
                            <div>主机名: ${escapeHtml(String(obj.hostname))}</div>
                            <div>网卡数量: ${escapeHtml(String(interfaceCount))}</div>
                        </div>`;
                }

                if (obj.version && obj.executable) {
                    return `
                        <div class="agent-observation-card">
                            <strong>Python 环境</strong>
                            <div>版本: ${escapeHtml(String(obj.version))}</div>
                            <div>解释器: ${escapeHtml(String(obj.executable))}</div>
                            <div>虚拟环境: ${obj.is_virtual_env ? '是' : '否'}</div>
                        </div>`;
                }

                if (obj.top_processes && Array.isArray(obj.top_processes)) {
                    const procRows = obj.top_processes.slice(0, 5).map(p => {
                        const name = p?.name ?? 'unknown';
                        const mem = p?.memory_percent ?? '-';
                        const cpu = p?.cpu_percent ?? '-';
                        return `<li>${escapeHtml(String(name))} (内存 ${escapeHtml(String(mem))}% / CPU ${escapeHtml(String(cpu))}%)</li>`;
                    }).join('');
                    return `
                        <div class="agent-observation-card">
                            <strong>运行进程</strong>
                            <div>总进程数: ${escapeHtml(String(obj.total_processes ?? '-'))}</div>
                            <ul>${procRows || '<li>无进程信息</li>'}</ul>
                        </div>`;
                }

                return `<div class="agent-observation-card"><pre>${escapeHtml(JSON.stringify(obj, null, 2))}</pre></div>`;
            };

            const normalizeEvent = (evt) => {
                if (!evt || typeof evt !== 'object') return evt;

                if (evt.type === 'error' && evt.data && !evt.message) {
                    return { type: 'error', message: evt.data.error || '未知错误' };
                }

                if (evt.type === 'task_final' && evt.data) {
                    return {
                        type: 'done',
                        content: evt.data.result || '',
                        steps: Array.isArray(evt.data.steps) ? evt.data.steps.length : undefined,
                        elapsed_time: evt.data.elapsed_time
                    };
                }

                if (evt.type === 'agent_step' && evt.data && evt.data.step_type) {
                    const step = evt.data;
                    const stepType = String(step.step_type).toUpperCase();

                    if (stepType === 'THOUGHT') {
                        return { type: 'agent_thought', thought: step.content || '' };
                    }

                    if (stepType === 'ACTION') {
                        agentStepCounter += 1;
                        return {
                            type: 'agent_step',
                            step_number: agentStepCounter,
                            total_steps: '?',
                            tool_name: step.action?.tool_name || 'tool',
                            tool_args: step.action?.tool_args || {}
                        };
                    }

                    if (stepType === 'OBSERVATION') {
                        return {
                            type: 'observation',
                            message: step.content || '',
                            observation: step.observation || step.content || ''
                        };
                    }

                    if (stepType === 'ANSWER') {
                        return { type: 'token', content: step.content || '' };
                    }

                    if (stepType === 'ERROR') {
                        return { type: 'error', message: step.content || 'Agent 执行失败' };
                    }
                }

                return evt;
            };
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let streamBuffer = '';
            
            console.log('[STREAM] Starting to read response stream...');
            
            while (!streamComplete) {
                try {
                    const { done, value } = await reader.read();
                    if (done) {
                        console.log('[STREAM] Stream ended naturally');
                        break;
                    }
                    
                    hasReceivedData = true; // 标记已收到数据
                    const chunk = decoder.decode(value, { stream: true });
                    streamBuffer += chunk;
                    const lines = streamBuffer.split('\n');
                    streamBuffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = normalizeEvent(JSON.parse(line.slice(6)));
                                
                                if (data.type === 'token') {
                                    // ⭐ 去重: 如果token内容与之前的agent_thought高度重叠，
                                    // 先移除thought部分，只保留token(最终回复)
                                    if (agentThoughtText && data.content.length > 50) {
                                        const thoughtCore = agentThoughtText.replace(/\s/g, '').slice(0, 100);
                                        const tokenCore = data.content.replace(/\s/g, '').slice(0, 100);
                                        if (thoughtCore && tokenCore && thoughtCore.slice(0, 60) === tokenCore.slice(0, 60)) {
                                            console.log('[AGENT] Dedup: removing thought text, keeping final token');
                                            fullText = fullText.replace(`*💭 ${agentThoughtText}*\n\n`, '');
                                            agentThoughtText = '';
                                        }
                                    }
                                    fullText += data.content;
                                    // 每50ms更新一次UI
                                    if (Date.now() - lastUpdateTime > 50) {
                                        try {
                                            bodyEl.innerHTML = parseMarkdown(fullText) + '<span class="typing-cursor">▊</span>';
                                        } catch (mdError) {
                                            console.warn('[Markdown] Parsing failed (temp):', mdError);
                                            // 降级渲染，防止UI卡死
                                            bodyEl.innerHTML = `<div class="markdown-fallback" style="white-space: pre-wrap;">${escapeHtml(fullText)}</div><span class="typing-cursor">▊</span>`;
                                        }
                                        scrollToBottom();
                                        lastUpdateTime = Date.now();
                                    }
                                } else if (data.type === 'progress') {
                                    // 显示进度信息
                                    showLoading(data.message, data.detail || '');
                                } else if (data.type === 'classification') {
                                    // 显示任务分类信息（兼容后端未返回 message 的情况）
                                    console.log('[STREAM] 任务分类:', data.task_type, data.pattern);
                                    const classificationText = data.message
                                        || `🎯 任务分类: ${data.task_display || data.task_type || '未知任务'}`
                                        || '';
                                    if (classificationText) {
                                        fullText += `**${classificationText}**\n\n`;
                                        bodyEl.innerHTML = parseMarkdown(fullText);
                                        scrollToBottom();
                                    }
                                } else if (data.type === 'status') {
                                    // 显示状态信息（多步任务进度）
                                    console.log('[STREAM] 状态更新:', data.message);
                                    fullText += (data.message || '') + '\n';
                                    bodyEl.innerHTML = parseMarkdown(fullText) + '<span class="typing-cursor">▊</span>';
                                    scrollToBottom();
                                } else if (data.type === 'info') {
                                    // 显示额外信息
                                    if (data.message) {
                                        fullText += `*${data.message}*\n\n`;
                                        bodyEl.innerHTML = parseMarkdown(fullText);
                                        scrollToBottom();
                                    }
                                } else if (data.type === 'thinking') {
                                    // 思考过程事件 — 仅在用户开启时显示
                                    const showThinking = currentSettings?.ai?.show_thinking === true;
                                    if (showThinking) {
                                        // 创建或获取思考面板
                                        let thinkingPanel = bodyEl.querySelector('.thinking-panel');
                                        if (!thinkingPanel) {
                                            thinkingPanel = document.createElement('details');
                                            thinkingPanel.className = 'thinking-panel';
                                            thinkingPanel.open = true;
                                            thinkingPanel.innerHTML = '<summary class="thinking-summary">💭 思考过程</summary><div class="thinking-steps"></div>';
                                            bodyEl.insertBefore(thinkingPanel, bodyEl.firstChild);
                                        }
                                        const stepsList = thinkingPanel.querySelector('.thinking-steps');
                                        const stepEl = document.createElement('div');
                                        stepEl.className = 'thinking-step';
                                        // 支持阶段标签
                                        const phase = data.phase || '';
                                        const phaseIcons = {
                                            'routing': '🎯', 'planning': '📋', 'searching': '🔍',
                                            'analyzing': '🔬', 'generating': '✍️', 'validating': '✅',
                                            'model': '🤖', 'context': '🔗', 'thinking': '💭'
                                        };
                                        const icon = phaseIcons[phase] || '💭';
                                        const elapsed = data.elapsed ? ` <span class="thinking-time">${data.elapsed}s</span>` : '';
                                        stepEl.innerHTML = `<span class="thinking-icon">${icon}</span><span class="thinking-text">${escapeHtml(data.message)}</span>${elapsed}`;
                                        stepsList.appendChild(stepEl);
                                        scrollToBottom();
                                    }
                                } else if (data.type === 'agent_step') {
                                    // Agent步骤信息 - 在步骤面板中显示
                                    console.log('[AGENT] Step:', data.step_number, '/', data.total_steps, '-', data.tool_name);
                                    
                                    // 初始化 agent 状态栏和步骤面板（首次）
                                    if (!bodyEl.querySelector('.agent-status-bar')) {
                                        const statusBar = document.createElement('div');
                                        statusBar.className = 'agent-status-bar';
                                        statusBar.innerHTML = '<div class="agent-spinner"></div><span class="agent-status-text">🤖 Agent 执行中…</span>';
                                        bodyEl.insertBefore(statusBar, bodyEl.firstChild);
                                    }
                                    let stepsPanel = bodyEl.querySelector('.agent-steps-panel');
                                    if (!stepsPanel) {
                                        stepsPanel = document.createElement('details');
                                        stepsPanel.className = 'agent-steps-panel';
                                        stepsPanel.open = true;
                                        stepsPanel.innerHTML = '<summary>📋 执行步骤</summary><div class="agent-steps-list"></div>';
                                        // 在状态栏之后、正文之前插入
                                        const statusBar = bodyEl.querySelector('.agent-status-bar');
                                        if (statusBar && statusBar.nextSibling) {
                                            bodyEl.insertBefore(stepsPanel, statusBar.nextSibling);
                                        } else {
                                            bodyEl.appendChild(stepsPanel);
                                        }
                                    }
                                    
                                    // 更新状态栏
                                    const statusText = bodyEl.querySelector('.agent-status-text');
                                    if (statusText) statusText.textContent = `🤖 步骤 ${data.step_number}/${data.total_steps} — ${data.tool_name}`;
                                    
                                    // 添加步骤卡片
                                    const stepsList = stepsPanel.querySelector('.agent-steps-list');
                                    const stepCard = document.createElement('div');
                                    stepCard.className = 'agent-step-card step-pending';
                                    stepCard.id = `agent-step-${data.step_number}`;
                                    const argsStr = data.tool_args ? Object.entries(data.tool_args).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(', ') : '';
                                    stepCard.innerHTML = `
                                        <div class="agent-step-number">${data.step_number}</div>
                                        <div class="agent-step-info">
                                            <div class="agent-step-tool">${escapeHtml(data.tool_name)}</div>
                                            <div class="agent-step-status">⏳ 执行中...${argsStr ? ' (' + escapeHtml(argsStr).substring(0, 60) + ')' : ''}</div>
                                        </div>`;
                                    stepsList.appendChild(stepCard);
                                    scrollToBottom();

                                } else if (data.type === 'observation' && bodyEl.querySelector('.agent-steps-panel')) {
                                    // Agent OBSERVATION: 结构化展示工具结果
                                    const cards = bodyEl.querySelectorAll('.agent-step-card');
                                    const lastCard = cards.length > 0 ? cards[cards.length - 1] : null;
                                    if (lastCard) {
                                        lastCard.className = 'agent-step-card step-success';
                                        const statusEl = lastCard.querySelector('.agent-step-status');
                                        if (statusEl) {
                                            statusEl.textContent = '✅ 已完成';
                                        }

                                        const rawObs = data.observation || data.message || '';
                                        const obsObj = tryParseObservationJson(rawObs);
                                        let obsEl = lastCard.querySelector('.agent-step-observation');
                                        if (!obsEl) {
                                            obsEl = document.createElement('div');
                                            obsEl.className = 'agent-step-observation';
                                            lastCard.appendChild(obsEl);
                                        }
                                        obsEl.innerHTML = renderObservationHtml(obsObj, rawObs);
                                    }
                                    scrollToBottom();
                                    
                                } else if (data.type === 'progress' && bodyEl.querySelector('.agent-steps-panel')) {
                                    // Agent 模式下的 progress: 更新最后一个步骤卡片的状态
                                    const cards = bodyEl.querySelectorAll('.agent-step-card');
                                    const lastCard = cards.length > 0 ? cards[cards.length - 1] : null;
                                    if (lastCard) {
                                        const statusEl = lastCard.querySelector('.agent-step-status');
                                        const msg = data.message || '';
                                        if (msg.startsWith('✅')) {
                                            lastCard.className = 'agent-step-card step-success';
                                            if (statusEl) statusEl.textContent = msg;
                                        } else if (msg.startsWith('⚠️') || msg.startsWith('❌')) {
                                            lastCard.className = 'agent-step-card step-fail';
                                            if (statusEl) statusEl.textContent = msg;
                                        } else {
                                            if (statusEl) statusEl.textContent = msg;
                                        }
                                    }
                                    scrollToBottom();
                                    
                                } else if (data.type === 'agent_thought') {
                                    // Agent思考过程 - 仅在工具调用中间步骤显示
                                    // 最终回复(token)会替代思考内容，避免重复
                                    console.log('[AGENT] Thinking:', data.thought);
                                    agentThoughtText = data.thought; // 记录思考文本，用于去重
                                    fullText += `*💭 ${data.thought}*\n\n`;
                                    // 更新正文区（跳过面板部分）
                                    const textContainer = bodyEl.querySelector('.agent-answer') || bodyEl;
                                    if (!bodyEl.querySelector('.agent-answer')) {
                                        const answerDiv = document.createElement('div');
                                        answerDiv.className = 'agent-answer';
                                        bodyEl.appendChild(answerDiv);
                                    }
                                    bodyEl.querySelector('.agent-answer').innerHTML = parseMarkdown(fullText) + '<span class="typing-cursor">▊</span>';
                                    scrollToBottom();
                                    
                                } else if (data.type === 'user_confirm') {
                                    // 需要用户确认 - 显示带倒计时的确认对话框
                                    console.log('[AGENT] Requesting confirmation for tool:', data.tool_name);
                                    const confirmResult = await showAgentConfirmDialog(data.tool_name, data.tool_args, data.reason);
                                    if (confirmResult) {
                                        // 发送确认结果回后端
                                        try {
                                            await fetch('/api/agent/confirm', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({ session: currentSession, confirmed: confirmResult.confirmed })
                                            });
                                        } catch(e) { console.error('[AGENT] Confirm callback failed:', e); }
                                    }
                                } else if (data.type === 'user_choice') {
                                    // 需要用户选择 - 显示多选对话框
                                    console.log('[AGENT] Requesting choice:', data.question, 'Options:', data.options);
                                    const choiceResult = await showAgentChoiceDialog(data.question, data.options);
                                    if (choiceResult && choiceResult.displayText) {
                                        fullText += choiceResult.displayText + '\n\n';
                                        if (bodyEl.querySelector('.agent-answer')) {
                                            bodyEl.querySelector('.agent-answer').innerHTML = parseMarkdown(fullText);
                                        }
                                    }
                                    // 发送选择结果回后端
                                    if (choiceResult && choiceResult.selected != null) {
                                        try {
                                            await fetch('/api/agent/choice', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({ session: currentSession, selected: choiceResult.selected })
                                            });
                                        } catch(e) { console.error('[AGENT] Choice callback failed:', e); }
                                    }
                                } else if (data.type === 'open_suggestion_panel') {
                                    // 打开文档建议面板
                                    console.log('[STREAM] 打开建议面板:', data.file_path);
                                    fullText += `📝 正在分析文档并生成修改建议...\n\n`;
                                    bodyEl.innerHTML = parseMarkdown(fullText);
                                    openSuggestionPanel(data.file_path, data.requirement || '');
                                } else if (data.type === 'done') {
                                    // 完成事件处理 - 使用真实DOM元素而不是HTML字符串
                                    console.log('[STREAM] ========== DONE EVENT ==========');
                                    console.log('[STREAM] Images:', data.images);
                                    console.log('[STREAM] Files:', data.saved_files);

                                    if ((!fullText || fullText.trim() === '') && data.content) {
                                        fullText = data.content;
                                    }
                                    
                                    streamComplete = true;
                                    const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(2);
                                    
                                    // Agent 模式：保留步骤面板，只更新回复区
                                    const agentStepsPanel = bodyEl.querySelector('.agent-steps-panel');
                                    const agentStatusBar = bodyEl.querySelector('.agent-status-bar');
                                    if (agentStepsPanel) {
                                        // 移除状态栏 spinner
                                        if (agentStatusBar) agentStatusBar.remove();
                                        
                                        // 折叠步骤面板
                                        agentStepsPanel.open = false;
                                        const summary = agentStepsPanel.querySelector('summary');
                                        const stepCount = data.steps || agentStepsPanel.querySelectorAll('.agent-step-card').length;
                                        const backendTime = data.elapsed_time || elapsedTime;
                                        if (summary) summary.textContent = `📋 执行步骤 (${stepCount} 步, ${backendTime}s)`;
                                        
                                        // 更新或创建回复区
                                        let answerDiv = bodyEl.querySelector('.agent-answer');
                                        if (!answerDiv) {
                                            answerDiv = document.createElement('div');
                                            answerDiv.className = 'agent-answer';
                                            bodyEl.appendChild(answerDiv);
                                        }
                                        answerDiv.innerHTML = parseMarkdown(fullText);
                                        renderMermaidBlocks();
                                        timeEl.textContent = `⏱️ ${backendTime}s`;
                                    } else {
                                        // 非 Agent 模式：原逻辑
                                        bodyEl.innerHTML = parseMarkdown(fullText);
                                        renderMermaidBlocks();
                                        timeEl.textContent = `⏱️ ${elapsedTime}s`;
                                    }
                                    
                                    // 折叠思考过程面板（如有）
                                    const thinkingPanel = bodyEl.querySelector('.thinking-panel');
                                    if (thinkingPanel) {
                                        thinkingPanel.open = false;
                                        const summary = thinkingPanel.querySelector('.thinking-summary');
                                        const stepCount = thinkingPanel.querySelectorAll('.thinking-step').length;
                                        if (summary) summary.textContent = `💭 思考过程 (${stepCount} 步, ${elapsedTime}s)`;
                                        // 重新插到最前面（parseMarkdown 会重写 innerHTML）
                                        bodyEl.insertBefore(thinkingPanel, bodyEl.firstChild);
                                    }
                                    
                                    // 2. 添加图片 - 使用真实DOM元素
                                    if (data.images && Array.isArray(data.images) && data.images.length > 0) {
                                        console.log('[STREAM] Creating image container...');
                                        
                                        const imagesDiv = document.createElement('div');
                                        imagesDiv.className = 'generated-images';
                                        imagesDiv.style.display = 'flex';
                                        imagesDiv.style.gap = '10px';
                                        imagesDiv.style.flexWrap = 'wrap';
                                        imagesDiv.style.marginTop = '12px';
                                        
                                        for (let i = 0; i < data.images.length; i++) {
                                            const img = data.images[i];
                                            const cleanPath = img.replace(/\\/g, '/');
                                            const url = `/api/workspace/${cleanPath}`;
                                            
                                            console.log(`[STREAM] Image ${i + 1}: ${url}`);
                                            
                                            // 创建链接
                                            const link = document.createElement('a');
                                            link.href = url;
                                            link.target = '_blank';
                                            link.style.display = 'inline-block';
                                            
                                            // 创建图片
                                            const imgEl = document.createElement('img');
                                            imgEl.src = url;
                                            imgEl.alt = `Generated image ${i + 1}`;
                                            imgEl.className = 'generated-image';
                                            imgEl.style.maxWidth = '400px';
                                            imgEl.style.maxHeight = '400px';
                                            imgEl.style.borderRadius = '14px';
                                            imgEl.style.border = '1px solid var(--border-color)';
                                            imgEl.style.cursor = 'pointer';
                                            
                                            imgEl.onload = () => console.log(`✓ Image ${i + 1} loaded successfully`);
                                            imgEl.onerror = () => console.error(`✗ Image ${i + 1} failed to load: ${url}`);
                                            
                                            link.appendChild(imgEl);
                                            imagesDiv.appendChild(link);
                                        }
                                        
                                        bodyEl.appendChild(imagesDiv);
                                        console.log('[STREAM] Image container added to DOM');
                                    }
                                    
                                    // 3. 添加文件 - 使用真实DOM元素
                                    if (data.saved_files && Array.isArray(data.saved_files) && data.saved_files.length > 0) {
                                        console.log('[STREAM] Creating files container...');
                                        
                                        const filesDiv = document.createElement('div');
                                        filesDiv.className = 'saved-files';
                                        
                                        const titleDiv = document.createElement('div');
                                        titleDiv.className = 'saved-files-title';
                                        titleDiv.textContent = '✓ Files saved to workspace:';
                                        filesDiv.appendChild(titleDiv);
                                        
                                        for (let file of data.saved_files) {
                                            const fileLink = document.createElement('a');
                                            fileLink.href = 'javascript:void(0)';
                                            fileLink.className = 'saved-file-link';
                                            fileLink.style.textDecoration = 'none';
                                            fileLink.style.display = 'block';
                                            fileLink.style.cursor = 'pointer';
                                            fileLink.title = `点击打开 ${file}`;
                                            fileLink.addEventListener('click', (e) => {
                                                e.preventDefault();
                                                fetch('/api/open-file', {
                                                    method: 'POST',
                                                    headers: {'Content-Type': 'application/json'},
                                                    body: JSON.stringify({filepath: file})
                                                }).then(r => r.json()).then(d => {
                                                    if (!d.success) console.error('Open file failed:', d.error);
                                                }).catch(err => console.error('Open file error:', err));
                                            });
                                            
                                            const fileDiv = document.createElement('div');
                                            fileDiv.className = 'saved-file';
                                            fileDiv.textContent = `📄 ${file}`;
                                            
                                            fileLink.appendChild(fileDiv);
                                            filesDiv.appendChild(fileLink);
                                        }
                                        
                                        bodyEl.appendChild(filesDiv);
                                        console.log('[STREAM] Files container added to DOM');
                                    }
                                    
                                    // 4. 添加完成标记 - 使用真实DOM元素
                                    const completeDiv = document.createElement('div');
                                    completeDiv.className = 'task-complete';
                                    completeDiv.style.marginTop = '12px';
                                    completeDiv.style.padding = '10px';
                                    completeDiv.style.borderRadius = '6px';
                                    completeDiv.style.background = 'rgba(42, 212, 137, 0.1)';
                                    
                                    const completeSpan = document.createElement('span');
                                    completeSpan.textContent = '✅ 任务完成';
                                    completeDiv.appendChild(completeSpan);
                                    
                                    const timeSpan = document.createElement('span');
                                    timeSpan.className = 'task-time';
                                    timeSpan.textContent = `耗时 ${elapsedTime}s`;
                                    timeSpan.style.marginLeft = '10px';
                                    timeSpan.style.fontSize = '12px';
                                    timeSpan.style.color = 'var(--text-muted)';
                                    completeDiv.appendChild(timeSpan);
                                    
                                    bodyEl.appendChild(completeDiv);
                                    
                                    console.log('[STREAM] ========== ALL ELEMENTS ADDED ==========');
                                    scrollToBottom();
                                    hideLoading();
                                    break;  // 立即退出 for 循环
                                } else if (data.type === 'error') {
                                    bodyEl.innerHTML = `<span class="error-text">❌ ${data.message}</span>`;
                                    streamComplete = true;
                                    break;
                                }
                            } catch (e) {
                                // 忽略解析错误
                            }
                        }
                    }
                } catch (e) {
                    // ⭐ 捕获 abort 错误 - 用户点击了中断
                    if (e.name === 'AbortError') {
                        console.log('[INTERRUPT] Stream aborted by user');
                        bodyEl.innerHTML = '<span class="interrupt-msg">⏹️ 已中断</span>';
                    } else {
                        console.error('[STREAM] Error reading stream:', e);
                        // 如果已经收到了一些数据，保留已有内容
                        if (hasReceivedData && fullText) {
                            console.log('[STREAM] Partial content received, keeping it');
                            bodyEl.innerHTML = parseMarkdown(fullText) + '<div class="stream-interrupted">⚠️ 连接中断，但部分内容已接收</div>';
                        } else {
                            // 真正的错误才显示
                            bodyEl.innerHTML = `<span class="error-text">❌ 流错误: ${e.message}</span>`;
                        }
                    }
                    streamComplete = true;
                    break;
                }
            }
            
            // 如果流结束但没有收到 done 事件，完成最终渲染
            if (hasReceivedData && fullText && !streamComplete) {
                console.log('[STREAM] Stream ended without done event, finalizing...');
                const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(2);
                bodyEl.innerHTML = parseMarkdown(fullText);
                renderMermaidBlocks();
                timeEl.textContent = `⏱️ ${elapsedTime}s`;
                bodyEl.innerHTML += `
                    <div class="task-complete">
                        <span>✅ 任务完成</span>
                        <span class="task-time">耗时 ${elapsedTime}s</span>
                    </div>
                `;
            }
        }
        
        scrollToBottom();
        highlightCode();
        
    } catch (error) {
        console.error('[ERROR] Chat error:', error.name, error.message);
        // ⭐ 捕获 abort 错误
        if (error.name === 'AbortError') {
            console.log('[INTERRUPT] Request aborted by user');
            const bodyEl = document.getElementById(`${msgId}-body`);
            if (bodyEl) {
                bodyEl.innerHTML = '<span class="interrupt-msg">⏹️ 已中断</span>';
            }
        } else {
            const bodyEl = document.getElementById(`${msgId}-body`);
            if (bodyEl) {
                let errorMsg = '抱歉，发生错误';
                
                // 提供更具体的错误信息
                if (error.message.includes('Failed to fetch')) {
                    errorMsg = '❌ 网络连接失败，请检查网络或代理设置';
                } else if (error.message.includes('HTTP 503')) {
                    errorMsg = '❌ 服务器繁忙，请稍后重试';
                } else if (error.message.includes('HTTP 500')) {
                    errorMsg = '❌ 服务器内部错误，请重试或联系管理员';
                } else if (error.message) {
                    errorMsg = `❌ ${error.message}`;
                }
                
                bodyEl.innerHTML = `<span class="error-text">${errorMsg}</span>`;
            }
        }
        scrollToBottom();
    } finally {
        setSessionGenerating(currentSession, false);
        hideLoading();
        
        // 恢复发送按钮状态
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.classList.remove('generating');
        sendBtn.disabled = false;
        sendBtn.title = '发送';
        
        // 清理 AbortController
        setSessionAbortController(currentSession, null);
        setSessionTaskId(currentSession, null);
        
        // 重置中断标志
        await fetch('/api/chat/reset-interrupt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session: currentSession })
        }).catch(e => console.error('Reset interrupt failed:', e));
    }
}

// ================= File Handling =================
function updateFilePreview() {
    console.log(`[UPDATE PREVIEW] 更新文件预览，当前 selectedFiles:`, selectedFiles);
    console.log(`[UPDATE PREVIEW] selectedFiles.length = ${selectedFiles.length}`);
    
    const preview = document.getElementById('filePreview');
    const listEl = document.getElementById('fileList');
    
    if (!preview || !listEl) {
        console.error('[UPDATE PREVIEW] ❌ 找不到预览元素！', { preview: !!preview, listEl: !!listEl });
        return;
    }
    
    if (selectedFiles.length === 0) {
        console.log('[UPDATE PREVIEW] 清空预览（无文件）');
        preview.style.display = 'none';
        listEl.innerHTML = '';
        return;
    }
    
    preview.style.display = 'flex';
    
    // 生成每个文件的列表项
    const html = selectedFiles.map((file, index) => `
        <div class="file-item">
            <span class="file-name">${file.name}</span>
            <span class="file-size">(${formatFileSize(file.size)})</span>
            <button class="remove-file-btn" onclick="removeSingleFile(${index})" title="移除">×</button>
        </div>
    `).join('');
    
    listEl.innerHTML = html;
    console.log(`[UPDATE PREVIEW] ✅ 已渲染 ${selectedFiles.length} 个文件到UI`);
    console.log('[UPDATE PREVIEW] HTML content:', html);
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function removeSingleFile(index) {
    selectedFiles.splice(index, 1);
    updateFilePreview();
    if (selectedFiles.length === 0) {
        document.getElementById('fileInput').value = '';
    }
}

function setSelectedFiles(files, appendMode = false) {
    console.log(`[FILE SELECT] 开始处理文件...`);
    console.log(`[FILE SELECT] 收到 ${files.length} 个文件, 追加模式: ${appendMode}, 当前已有: ${selectedFiles.length} 个`);
    console.log('[FILE SELECT] 新文件列表:', files.map(f => ({ name: f.name, size: f.size })));
    
    let newFiles = appendMode ? [...selectedFiles, ...files] : files;
    console.log(`[FILE SELECT] 合并后共 ${newFiles.length} 个文件`);
    
    // 去重：基于文件名和大小
    const uniqueFiles = [];
    const seen = new Set();
    for (const file of newFiles) {
        const key = `${file.name}_${file.size}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueFiles.push(file);
        }
    }
    console.log(`[FILE SELECT] 去重后 ${uniqueFiles.length} 个文件`);
    
    const trimmed = uniqueFiles.slice(0, MAX_UPLOAD_FILES);
    let tooLargeCount = 0;
    selectedFiles = trimmed.filter(file => {
        if (file.size > 100 * 1024 * 1024) {
            tooLargeCount += 1;
            return false;
        }
        return true;
    });
    
    console.log(`[FILE SELECT] ✅ 最终选择 ${selectedFiles.length} 个文件:`, selectedFiles.map(f => f.name));
    console.log('[FILE SELECT] selectedFiles 变量更新完毕:', selectedFiles);
    
    if (newFiles.length > MAX_UPLOAD_FILES) {
        showNotification(`⚠️ 最多一次上传 ${MAX_UPLOAD_FILES} 个文件，已截取前 ${MAX_UPLOAD_FILES} 个`, 'warning');
    }
    if (tooLargeCount > 0) {
        showNotification(`❌ ${tooLargeCount} 个文件超过 100MB 已跳过`, 'error');
    }
    if (selectedFiles.length > 0) {
        showNotification(`✅ 已选择 ${selectedFiles.length} 个文件`, 'success');
    }
    
    console.log('[FILE SELECT] 调用 updateFilePreview()...');
    updateFilePreview();
    console.log('[FILE SELECT] updateFilePreview() 完成');
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files || []);
    console.log(`[FILE INPUT] ========== 文件选择事件触发 ==========`);
    console.log(`[FILE INPUT] event.target.files.length = ${event.target.files ? event.target.files.length : 0}`);
    console.log(`[FILE INPUT] 文件选择器返回 ${files.length} 个文件:`, files.map(f => f.name));
    console.log(`[FILE INPUT] 当前 selectedFiles 包含 ${selectedFiles.length} 个文件`);
    
    if (files.length > 0) {
        console.log('[FILE INPUT] ✅ 进入累加模式，调用 setSelectedFiles(files, true)');
        // 累加模式：追加新文件到现有列表
        setSelectedFiles(files, true);
        
        // 重置input value以允许再次选择相同文件
        event.target.value = '';
        console.log('[FILE INPUT] ✅ input value 已重置');
    } else {
        console.log('[FILE INPUT] ⚠️ 未选择任何文件');
    }
}

function removeFile() {
    selectedFiles = [];
    updateFilePreview();
    document.getElementById('fileInput').value = '';
}

// ================= Drag & Drop Upload =================
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    const overlay = document.getElementById('dragOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // 只有当离开 chatMessages 本身时才隐藏
    if (event.target.id === 'chatMessages') {
        const overlay = document.getElementById('dragOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const overlay = document.getElementById('dragOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
    
    const files = Array.from(event.dataTransfer.files || []);
    console.log(`[DRAG DROP] 拖拽了 ${files.length} 个文件:`, files.map(f => f.name));
    
    if (files.length > 0) {
        // 拖拽也使用累加模式
        setSelectedFiles(files, true);
        
        const inputEl = document.getElementById('messageInput');
        inputEl.focus();
        if (selectedFiles.length === 1) {
            inputEl.placeholder = `输入对 ${selectedFiles[0].name} 的处理指令...`;
        } else {
            inputEl.placeholder = `输入对 ${selectedFiles.length} 个文件的处理指令...`;
        }
    }
}

// ================= Workspace =================
function openWorkspaceFolder() {
    fetch('/api/open-workspace', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification('📂 已打开工作区文件夹', 'success');
            }
        })
        .catch(err => console.error('Failed to open workspace:', err));
}

function toggleWorkspace() {
    const panel = document.getElementById('workspacePanel');
    panel.classList.toggle('active');
    
    if (panel.classList.contains('active')) {
        loadWorkspaceFiles();
    }
}

async function loadWorkspaceFiles() {
    try {
        const response = await fetch('/api/workspace');
        const data = await response.json();
        
        const container = document.getElementById('workspaceFiles');
        
        if (data.files.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px; color: var(--text-muted);">
                    <p>No files yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.files.map(file => `
            <a href="/api/workspace/${file}" target="_blank" class="workspace-file">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span>${escapeHtml(file)}</span>
            </a>
        `).join('');
    } catch (error) {
        console.error('Failed to load workspace files:', error);
    }
}

// ================= Batch Jobs Panel =================
let batchJobsState = {
    timer: null
};

function openBatchJobsPanel() {
    const modal = document.getElementById('batchPanelModal');
    modal.style.display = 'flex';
    refreshBatchJobs();
    if (batchJobsState.timer) {
        clearInterval(batchJobsState.timer);
    }
    batchJobsState.timer = setInterval(refreshBatchJobs, 2000);
}

function closeBatchJobsPanel() {
    const modal = document.getElementById('batchPanelModal');
    modal.style.display = 'none';
    if (batchJobsState.timer) {
        clearInterval(batchJobsState.timer);
        batchJobsState.timer = null;
    }
}

async function refreshBatchJobs() {
    try {
        const response = await fetch('/api/batch/jobs');
        const data = await response.json();
        if (!data.success) return;

        const listEl = document.getElementById('batchJobsList');
        const jobs = data.jobs || [];
        if (jobs.length === 0) {
            listEl.innerHTML = '<div class="batch-empty">暂无任务</div>';
            return;
        }

        listEl.innerHTML = jobs.map(job => {
            const total = job.total_items || 0;
            const processed = job.processed_items || 0;
            const percent = total > 0 ? Math.round((processed / total) * 100) : 0;
            const outputDir = job.output_dir || '';
            const encodedOutput = encodeURIComponent(outputDir);
            const status = job.status || 'unknown';

            return `
                <div class="batch-job-card">
                    <div class="batch-job-title">${escapeHtml(job.name || job.job_id)}</div>
                    <div class="batch-job-meta">
                        <span>状态: ${escapeHtml(status)}</span>
                        <span>${processed}/${total}</span>
                    </div>
                    <div class="batch-job-progress">
                        <div class="batch-job-progress-fill" style="width:${percent}%"></div>
                    </div>
                    <div class="batch-job-meta" style="margin-top:6px;">
                        <span>${escapeHtml(outputDir)}</span>
                        <button class="ghost-btn" style="padding:2px 8px;font-size:12px;" onclick="openPath('${encodedOutput}')">打开</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load batch jobs:', error);
    }
}

function openPath(path) {
    if (!path) return;
    const decodedPath = decodeURIComponent(path);
    fetch('/api/open-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: decodedPath })
    });
}

// ================= Status =================
async function checkStatus() {
    try {
        const response = await fetch('/api/ping');
        const data = await response.json();
        
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        
        if (data.status === 'ok') {
            dot.classList.add('online');
            dot.classList.remove('offline');
            text.textContent = `${data.latency.toFixed(0)}ms`;
            
            if (data.ollama) {
                text.textContent += ' | 🦙';
            }
        } else {
            dot.classList.add('offline');
            dot.classList.remove('online');
            text.textContent = 'Offline';
        }
    } catch (error) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        dot.classList.add('offline');
        dot.classList.remove('online');
        text.textContent = 'Error';
    }
}

// ================= Utilities =================
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage(event);
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}

function showLoading(text, model) {
    const think = document.getElementById('inputThinking');
    document.getElementById('thinkingText').textContent = text || 'Koto 正在思考...';
    if (model) {
        document.getElementById('currentModel').textContent = '📦 ' + model;
    } else {
        document.getElementById('currentModel').textContent = '';
    }
    think.style.display = '';
}

function hideLoading() {
    const think = document.getElementById('inputThinking');
    think.style.display = 'none';
    // 停止spinner动画，防止后台继续旋转
    const spinner = think.querySelector('.spinner');
    if (spinner) {
        spinner.style.animationPlayState = 'paused';
        spinner.style.animation = 'none';
    }
    // 清除文本内容
    document.getElementById('thinkingText').textContent = 'Koto 正在思考...';
    document.getElementById('currentModel').textContent = '';
}

// ============== Agent Confirmation & Choice Dialogs ==============
/**
 * 显示Agent工具确认对话框
 * @param {string} toolName - 工具名称
 * @param {object} toolArgs - 工具参数
 * @param {string} reason - 需要确认的原因
 * @returns {Promise<string|null>} - 返回显示的消息文本，null表示取消
 */
async function showAgentConfirmDialog(toolName, toolArgs, reason) {
    return new Promise((resolve) => {
        const TIMEOUT = 60;
        let remaining = TIMEOUT;
        
        // 创建蒙层
        const overlay = document.createElement('div');
        overlay.className = 'agent-dialog-overlay';
        
        // 创建对话框
        const dialog = document.createElement('div');
        dialog.className = 'agent-confirm-dialog';
        
        // 格式化工具参数
        const argsHtml = Object.entries(toolArgs)
            .map(([key, value]) => `<div><strong>${key}:</strong> ${escapeHtml(String(value))}</div>`)
            .join('');
        
        dialog.innerHTML = `
            <h3 style="margin-top:0;">🤖 Agent需要确认</h3>
            <p>${escapeHtml(reason || '即将执行以下操作：')}</p>
            <div class="agent-args">
                <div class="tool-label" style="margin-bottom:8px;">🔧 工具: ${escapeHtml(toolName)}</div>
                <div>${argsHtml}</div>
            </div>
            <div class="agent-confirm-countdown" id="confirm-countdown">${remaining}s 后自动跳过</div>
            <div style="display:flex; gap:12px; justify-content:flex-end; margin-top:16px;">
                <button id="agent-confirm-no" style="padding:8px 20px; border-radius:6px; border:1px solid var(--border-color);
                    background:transparent; color:var(--text-secondary); cursor:pointer;">取消</button>
                <button id="agent-confirm-yes" style="padding:8px 20px; border-radius:6px; border:none;
                    background:#4CAF50; color:white; font-weight:bold; cursor:pointer;">确认执行</button>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // 倒计时
        const countdownEl = document.getElementById('confirm-countdown');
        const timer = setInterval(() => {
            remaining--;
            if (countdownEl) countdownEl.textContent = `${remaining}s 后自动跳过`;
            if (remaining <= 0) {
                clearInterval(timer);
                cleanup();
                resolve({ confirmed: false, message: `⏰ 确认超时，已跳过 \`${toolName}\`` });
            }
        }, 1000);
        
        function cleanup() {
            clearInterval(timer);
            if (document.body.contains(overlay)) document.body.removeChild(overlay);
        }
        
        // 绑定按钮事件
        document.getElementById('agent-confirm-yes').onclick = () => {
            cleanup();
            resolve({ confirmed: true, message: `✅ 已确认执行 \`${toolName}\`` });
        };
        document.getElementById('agent-confirm-no').onclick = () => {
            cleanup();
            resolve({ confirmed: false, message: `❌ 已取消 \`${toolName}\`` });
        };
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                cleanup();
                resolve({ confirmed: false, message: `❌ 已取消 \`${toolName}\`` });
            }
        };
    });
}

/**
 * 显示Agent多选对话框
 * @param {string} question - 问题文本
 * @param {array} options - 选项数组 [{label: "选项1", value: "val1"}, ...]
 * @returns {Promise<{displayText: string, selected: string|null}|null>} - 返回显示文本和选中值
 */
async function showAgentChoiceDialog(question, options) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'agent-dialog-overlay';
        
        const dialog = document.createElement('div');
        dialog.className = 'agent-choice-dialog';
        
        const optionsHtml = options.map((opt, idx) => `
            <button class="agent-choice-option" data-value="${escapeHtml(opt.value)}" 
                style="display:block; width:100%; padding:12px; margin:8px 0; 
                border:1px solid var(--border-color); border-radius:6px; background:var(--bg-tertiary); 
                color:var(--text-secondary); cursor:pointer; text-align:left; transition:all 0.2s;">
                <span style="font-weight:bold; color:#4CAF50;">${idx + 1}.</span> ${escapeHtml(opt.label)}
            </button>
        `).join('');
        
        dialog.innerHTML = `
            <h3 style="margin-top:0;">🤖 Agent需要您的选择</h3>
            <p style="margin:12px 0 20px 0;">${escapeHtml(question)}</p>
            <div id="agent-choice-options">${optionsHtml}</div>
            <div style="text-align:center; margin-top:16px;">
                <button id="agent-choice-cancel" style="padding:8px 20px; border-radius:6px; 
                    border:1px solid var(--border-color); background:transparent; color:var(--text-muted); cursor:pointer;">取消</button>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // 绑定选项点击事件
        const optionBtns = dialog.querySelectorAll('.agent-choice-option');
        optionBtns.forEach((btn, idx) => {
            btn.onclick = () => {
                const selected = options[idx];
                document.body.removeChild(overlay);
                resolve({ displayText: `✅ 您选择了: **${selected.label}**`, selected: selected.value });
            };
        });
        
        // 取消按钮
        const cancelBtn = document.getElementById('agent-choice-cancel');
        cancelBtn.onclick = () => {
            document.body.removeChild(overlay);
            resolve({ displayText: `❌ 已取消选择`, selected: '__cancelled__' });
        };
        
        // 点击蒙层外部取消
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                resolve(null);
            }
        };
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function parseMarkdown(text) {
    if (!text) return '';
    try {
        const preprocessed = preprocessMarkdown(text);

        if (typeof marked === 'undefined') {
            return `<div class="markdown-fallback" style="white-space: pre-wrap;">${escapeHtml(preprocessed)}</div>`;
        }

        // Create custom renderer for code blocks and tables
        const renderer = new marked.Renderer();
        
        // Custom table rendering with copy button
        renderer.table = function(header, body) {
            const tableId = 'table-' + Math.random().toString(36).slice(2, 10);
            return `<div class="table-wrapper" id="${tableId}">
                <div class="table-header">
                    <span class="table-label">📊 表格</span>
                    <button class="copy-table-btn" onclick="copyTable('${tableId}')" title="复制表格">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <span>复制</span>
                    </button>
                </div>
                <div class="table-scroll">
                    <table>
                        <thead>${header}</thead>
                        <tbody>${body}</tbody>
                    </table>
                </div>
            </div>`;
        };
        
        // Custom code block rendering with language tag, copy button, and Artifact button
        renderer.code = function(code, language) {
            try {
                // Mermaid 图表：输出占位 div，后续 renderMermaidBlocks() 处理
                if (language === 'mermaid') {
                    const mermaidId = 'mermaid-' + Math.random().toString(36).slice(2, 10);
                    return `<div class="mermaid-wrapper"><div class="mermaid" id="${mermaidId}">${escapeHtml(code)}</div></div>`;
                }

                // 防御性处理：检查 hljs 是否可用
                if (typeof hljs === 'undefined') {
                    return `<pre><code>${escapeHtml(code)}</code></pre>`;
                }

                const validLang = language && hljs.getLanguage(language) ? language : '';
                const highlighted = validLang 
                    ? hljs.highlight(code, { language: validLang }).value
                    : hljs.highlightAuto(code).value;
                
                const langAttr = validLang ? ` data-lang="${validLang}"` : '';
                const encodedCode = btoa(unescape(encodeURIComponent(code)));
                
                // 对于较长代码块（>5行），显示 Artifact 按钮
                const lineCount = (code.match(/\n/g) || []).length + 1;
                const artifactBtn = lineCount > 5
                    ? `<button class="open-artifact-btn" data-code="${encodedCode}" data-lang="${validLang || 'plaintext'}" onclick="openInArtifact(this)" title="在侧面板中打开">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
                        <span>Artifact</span>
                       </button>`
                    : '';

                return `<div class="code-block-wrapper">
                    <div class="code-header">
                        <span class="code-lang">${validLang || 'code'}</span>
                        <div style="display:flex;align-items:center;gap:4px;">
                            ${artifactBtn}
                            <button class="copy-btn" data-code="${encodedCode}" onclick="copyCode(this)" title="复制代码">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                                <span>复制</span>
                            </button>
                        </div>
                    </div>
                    <pre${langAttr}><code class="hljs language-${validLang || 'plaintext'}">${highlighted}</code></pre>
                </div>`;
            } catch (highlightErr) {
                console.warn('Highlight error:', highlightErr);
                return `<pre><code>${code}</code></pre>`; 
            }
        };
        
        // Configure marked
        marked.setOptions({
            renderer: renderer,
            breaks: true,
            gfm: true
        });
        
        let html = marked.parse(preprocessed);

        // 后处理：渲染 KaTeX 数学公式
        html = renderKaTeX(html);

        return html;
    } catch (e) {
        console.error('Markdown parse error:', e);
        return text; // Fallback to raw text
    }
}

/**
 * KaTeX 数学公式渲染
 * 处理 $$...$$ (块级) 和 $...$ (行内) 语法
 */
function renderKaTeX(html) {
    if (typeof katex === 'undefined') return html;
    try {
        // 块级公式: $$...$$
        html = html.replace(/\$\$([\s\S]+?)\$\$/g, (match, tex) => {
            try {
                return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false });
            } catch (e) { return match; }
        });
        // 行内公式: $...$ (不匹配 $$ 或 代码中的 $)
        html = html.replace(/(?<!\$)\$(?!\$)([^\n$]+?)\$(?!\$)/g, (match, tex) => {
            try {
                return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false });
            } catch (e) { return match; }
        });
    } catch (e) { console.warn('KaTeX render error:', e); }
    return html;
}

/**
 * 在 parseMarkdown 后调用：初始化 Mermaid 图表
 */
function renderMermaidBlocks() {
    if (typeof mermaid === 'undefined') return;
    try {
        const theme = document.documentElement.getAttribute('data-theme') === 'light' ? 'default' : 'dark';
        mermaid.initialize({ startOnLoad: false, theme: theme, securityLevel: 'loose' });
        document.querySelectorAll('.mermaid:not([data-processed])').forEach(async (el) => {
            try {
                el.setAttribute('data-processed', 'true');
                const id = el.id || ('m-' + Math.random().toString(36).slice(2, 8));
                const { svg } = await mermaid.render(id + '-svg', el.textContent.trim());
                el.innerHTML = svg;
            } catch (e) {
                console.warn('Mermaid render error:', e);
                el.innerHTML = `<pre style="color:var(--accent-warning);font-size:13px;">⚠️ 图表渲染失败: ${escapeHtml(e.message || '')}</pre>`;
            }
        });
    } catch (e) { console.warn('Mermaid init error:', e); }
}

function preprocessMarkdown(text) {
    const fileBlockRegex = /---BEGIN_FILE:\s*([^\n-]+?)\s*---\s*([\s\S]*?)---END_FILE---/gi;
    return text.replace(fileBlockRegex, (match, filename, code) => {
        const lang = getLanguageFromFilename(filename);
        const trimmed = (code || '').trim();
        return `\n\n\`\`\`${lang}\n${trimmed}\n\`\`\`\n`;
    });
}

function getLanguageFromFilename(filename) {
    const lower = String(filename || '').toLowerCase();
    if (lower.endsWith('.py')) return 'python';
    if (lower.endsWith('.js')) return 'javascript';
    if (lower.endsWith('.ts')) return 'typescript';
    if (lower.endsWith('.tsx')) return 'tsx';
    if (lower.endsWith('.jsx')) return 'jsx';
    if (lower.endsWith('.html')) return 'html';
    if (lower.endsWith('.css')) return 'css';
    if (lower.endsWith('.json')) return 'json';
    if (lower.endsWith('.md')) return 'markdown';
    if (lower.endsWith('.yml') || lower.endsWith('.yaml')) return 'yaml';
    if (lower.endsWith('.sh')) return 'bash';
    if (lower.endsWith('.ps1')) return 'powershell';
    if (lower.endsWith('.java')) return 'java';
    if (lower.endsWith('.c')) return 'c';
    if (lower.endsWith('.cpp')) return 'cpp';
    if (lower.endsWith('.cs')) return 'csharp';
    if (lower.endsWith('.go')) return 'go';
    if (lower.endsWith('.rs')) return 'rust';
    if (lower.endsWith('.rb')) return 'ruby';
    if (lower.endsWith('.php')) return 'php';
    if (lower.endsWith('.sql')) return 'sql';
    return '';
}

// 复制代码到剪贴板
async function copyCode(btn, code) {
    try {
        let decodedCode = '';
        if (code) {
            // Decode HTML entities
            const textarea = document.createElement('textarea');
            textarea.innerHTML = code;
            decodedCode = textarea.value;
        } else if (btn && btn.dataset && btn.dataset.code) {
            decodedCode = decodeURIComponent(escape(atob(btn.dataset.code)));
        }
        if (!decodedCode) return;
        
        await navigator.clipboard.writeText(decodedCode);
        
        // 显示成功状态
        const originalHTML = btn.innerHTML;
        btn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>已复制!</span>
        `;
        btn.classList.add('copied');
        
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

// 复制表格到剪贴板
async function copyTable(tableId) {
    try {
        const wrapper = document.getElementById(tableId);
        if (!wrapper) return;
        
        const table = wrapper.querySelector('table');
        if (!table) return;
        
        // 提取表格数据为制表符分隔的文本（适合粘贴到Excel）
        let text = '';
        const rows = table.querySelectorAll('tr');
        
        rows.forEach((row, rowIndex) => {
            const cells = row.querySelectorAll('th, td');
            const cellTexts = Array.from(cells).map(cell => cell.textContent.trim());
            text += cellTexts.join('\t') + '\n';
        });
        
        await navigator.clipboard.writeText(text);
        
        // 显示成功状态
        const btn = wrapper.querySelector('.copy-table-btn');
        if (!btn) return;
        
        const originalHTML = btn.innerHTML;
        btn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>已复制!</span>
        `;
        btn.classList.add('copied');
        
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy table:', err);
    }
}

function highlightCode() {
    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}
// ================= Settings =================
let currentSettings = null;
let currentBrowseTarget = null;
let currentBrowsePath = '';

async function loadSettings() {
    // 最多重试 2 次，防止启动时 Flask 还未就绪
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                currentSettings = await response.json();
                applySettingsToUI();
                return;
            }
        } catch (error) {
            console.warn(`Settings load attempt ${attempt + 1} failed:`, error);
        }
        // 等待后重试
        if (attempt < 2) await new Promise(r => setTimeout(r, 500));
    }
    console.error('Failed to load settings after all retries');
}

function applySettingsToUI() {
    if (!currentSettings) return;
    
    // Storage settings
    document.getElementById('settingWorkspaceDir').value = currentSettings.storage?.workspace_dir || '';
    document.getElementById('settingDocumentsDir').value = currentSettings.storage?.documents_dir || '';
    document.getElementById('settingImagesDir').value = currentSettings.storage?.images_dir || '';
    document.getElementById('settingChatsDir').value = currentSettings.storage?.chats_dir || '';
    
    // Appearance settings - update theme selector
    const currentTheme = currentSettings.appearance?.theme || 'light';
    updateThemeSelector(currentTheme);
    applyTheme(currentTheme);  // 确保设置面板打开时也同步主题
    document.getElementById('settingLanguage').value = currentSettings.appearance?.language || 'zh-CN';
    
    // AI settings
    document.getElementById('settingModel').value = currentSettings.ai?.default_model || 'gemini-3-flash-preview';
    
    // 思考过程开关
    const showThinkingCheckbox = document.getElementById('settingShowThinking');
    if (showThinkingCheckbox) {
        showThinkingCheckbox.checked = currentSettings.ai?.show_thinking === true;
    }
    
    // 语音自动模式设置
    const voiceAutoModeCheckbox = document.getElementById('settingVoiceAutoMode');
    if (voiceAutoModeCheckbox) {
        const isAutoMode = currentSettings.ai?.voice_auto_mode !== false; // 默认开启
        voiceAutoModeCheckbox.checked = isAutoMode;
        voiceAutoMode = isAutoMode; // 更新全局变量
    }
    
    // Proxy settings
    document.getElementById('settingProxyEnabled').checked = currentSettings.proxy?.enabled !== false;
    document.getElementById('settingManualProxy').value = currentSettings.proxy?.manual_proxy || '';
}

// Theme selector functions
function updateThemeSelector(theme) {
    document.querySelectorAll('.theme-option').forEach(opt => {
        opt.classList.remove('active');
        if (opt.dataset.theme === theme) {
            opt.classList.add('active');
        }
    });
}

function selectTheme(theme) {
    updateThemeSelector(theme);
    applyTheme(theme);
    updateSetting('appearance', 'theme', theme);
}

function openSettings() {
    loadSettings();
    loadMemories(); // Load memories when opening settings
    document.getElementById('settingsPanel').classList.add('active');
}

function closeSettings() {
    document.getElementById('settingsPanel').classList.remove('active');
}

// ================= Memory Management =================
async function loadMemories() {
    const listEl = document.getElementById('memoryList');
    if (!listEl) return;
    listEl.innerHTML = '<div class="memory-empty">正在加载记忆...</div>';
    
    try {
        const response = await fetch('/api/memories');
        if (!response.ok) {
            let detail = `HTTP ${response.status}`;
            try {
                const text = await response.text();
                if (text) detail = `${detail} - ${text.slice(0, 120)}`;
            } catch (_) {}

            if (response.status === 404) {
                throw new Error('后端接口未就绪（404）。请重启 Koto 启动器后重试。');
            }
            throw new Error(`加载失败: ${detail}`);
        }
        const memories = await response.json();
        renderMemories(memories);
    } catch (e) {
        listEl.innerHTML = `<div class="memory-empty" style="color:var(--accent-danger)">加载失败: ${e.message}</div>`;
    }
}

function renderMemories(memories) {
    const listEl = document.getElementById('memoryList');
    if (!listEl) return;
    
    if (!memories || memories.length === 0) {
        listEl.innerHTML = '<div class="memory-empty">暂无长期记忆。Koto 会自动记住重要信息，或手动添加。</div>';
        return;
    }
    
    listEl.innerHTML = memories.map(m => `
        <div class="memory-item">
            <div class="memory-content">
                <div>${escapeHtml(m.content)}</div>
                <div class="memory-meta">${m.created_at} · ${m.category}</div>
            </div>
            <button class="memory-delete-btn" onclick="deleteMemory(${m.id})" title="忘记">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

async function addNewMemory() {
    const input = document.getElementById('newMemoryInput');
    const content = input.value.trim();
    if (!content) return;
    
    try {
        const response = await fetch('/api/memories', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                content: content,
                category: 'user_preference'
            })
        });
        
        if (response.ok) {
            input.value = '';
            loadMemories();
        } else {
            const text = await response.text();
            alert(`添加失败 (${response.status})\n${text || '请稍后重试'}`);
        }
    } catch (e) {
        console.error('Failed to add memory:', e);
        alert(`添加失败: ${e.message}`);
    }
}

async function deleteMemory(id) {
    if (!confirm('确定要忘记这条记忆吗？')) return;
    
    try {
        const response = await fetch(`/api/memories/${id}`, { method: 'DELETE' });
        if (response.ok) {
            loadMemories();
        } else {
            const text = await response.text();
            alert(`删除失败 (${response.status})\n${text || '请稍后重试'}`);
        }
    } catch (e) {
        console.error('Failed to delete memory:', e);
        alert(`删除失败: ${e.message}`);
    }
}

// 切换到迷你模式
async function switchToMiniMode() {
    try {
        // 如果是pywebview环境，直接调用窗口API切换
        if (window.pywebview && window.pywebview.api && window.pywebview.api.switch_to_mini) {
            await window.pywebview.api.switch_to_mini();
        } else {
            // 浏览器环境：优化的跳转流程
            // 1. 添加淡出效果
            document.body.style.transition = 'opacity 0.15s ease-out';
            document.body.style.opacity = '0';
            
            // 2. 预加载目标页面（可选，提升加载速度）
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = '/mini';
            document.head.appendChild(link);
            
            // 3. 短暂延迟后跳转（让动画完成）
            setTimeout(() => {
                window.location.href = '/mini';
            }, 150);
        }
    } catch (error) {
        console.error('切换到迷你模式失败:', error);
        // 备用：快速跳转
        document.body.style.opacity = '0';
        setTimeout(() => window.location.href = '/mini', 100);
    }
}

async function updateSetting(category, key, value) {
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, key, value })
        });
        
        const data = await response.json();
        if (data.success) {
            if (!currentSettings[category]) currentSettings[category] = {};
            currentSettings[category][key] = value;
            
            // Apply theme change immediately
            if (category === 'appearance' && key === 'theme') {
                applyTheme(value);
            }
            
            // 更新语音自动模式全局变量
            if (category === 'ai' && key === 'voice_auto_mode') {
                voiceAutoMode = value;
                console.log('[设置] 语音模式:', voiceAutoMode ? '自动' : '手动');
            }
        }
    } catch (error) {
        console.error('Failed to update setting:', error);
    }
}

async function resetSettings() {
    if (!confirm('确定要重置所有设置为默认值吗？')) return;
    
    try {
        const response = await fetch('/api/settings/reset', {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            await loadSettings();
        }
    } catch (error) {
        console.error('Failed to reset settings:', error);
    }
}

function applyTheme(theme) {
    // 支持多种主题: dark/light/ocean/forest/sunset/lavender/midnight/auto
    if (theme === 'auto') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }
    
    // Update highlight.js code block theme based on theme brightness
    updateCodeTheme(theme);
}

function updateCodeTheme(theme) {
    const lightThemes = ['light', 'lavender'];
    const isLight = lightThemes.includes(theme) || 
                   (theme === 'auto' && !window.matchMedia('(prefers-color-scheme: dark)').matches);
    
    // Dynamically switch code highlight theme
    const existingLink = document.querySelector('link[href*="highlight"]');
    if (existingLink) {
        const newHref = isLight 
            ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css'
            : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css';
        existingLink.href = newHref;
    }
}

// 主题已在主初始化流程中统一加载和应用，无需额外的 DOMContentLoaded 监听器

// ================= Folder Browser =================
async function browseFolder(target) {
    currentBrowseTarget = target;
    
    // Get current path for this setting
    let startPath = '';
    switch(target) {
        case 'workspace_dir':
            startPath = document.getElementById('settingWorkspaceDir').value;
            break;
        case 'documents_dir':
            startPath = document.getElementById('settingDocumentsDir').value;
            break;
        case 'images_dir':
            startPath = document.getElementById('settingImagesDir').value;
            break;
        case 'chats_dir':
            startPath = document.getElementById('settingChatsDir').value;
            break;
    }
    
    currentBrowsePath = startPath || 'C:\\';
    document.getElementById('manualPathInput').value = currentBrowsePath;
    
    await loadFolderList(currentBrowsePath);
    document.getElementById('folderModal').classList.add('active');
}

async function loadFolderList(path) {
    document.getElementById('currentBrowsePath').textContent = path;
    
    try {
        const response = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        const container = document.getElementById('folderList');
        
        if (data.error) {
            container.innerHTML = `<div style="padding: 20px; color: var(--accent-danger);">${data.error}</div>`;
            return;
        }
        
        let html = '';
        
        // Parent folder
        if (data.parent) {
            html += `
                <div class="folder-item" onclick="loadFolderList('${escapeAttr(data.parent)}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                    <span>..</span>
                </div>
            `;
        }
        
        // Folders
        for (const folder of data.folders) {
            html += `
                <div class="folder-item" onclick="selectFolder('${escapeAttr(folder.path)}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <span>${escapeHtml(folder.name)}</span>
                </div>
            `;
        }
        
        if (data.folders.length === 0 && !data.parent) {
            html += `<div style="padding: 20px; color: var(--text-muted);">没有子文件夹</div>`;
        }
        
        container.innerHTML = html;
        currentBrowsePath = path;
        document.getElementById('manualPathInput').value = path;
        
    } catch (error) {
        console.error('Failed to load folders:', error);
        document.getElementById('folderList').innerHTML = `
            <div style="padding: 20px; color: var(--accent-danger);">加载失败</div>
        `;
    }
}

function selectFolder(path) {
    // Double click to enter, single click to select
    document.querySelectorAll('.folder-item').forEach(el => el.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    document.getElementById('manualPathInput').value = path;
    
    // Double click handler
    if (event.detail === 2) {
        loadFolderList(path);
    }
}

function closeFolderModal() {
    document.getElementById('folderModal').classList.remove('active');
    currentBrowseTarget = null;
}

async function confirmFolderSelect() {
    const path = document.getElementById('manualPathInput').value.trim();
    if (!path || !currentBrowseTarget) return;
    
    // Check if this is for setup wizard
    if (currentBrowseTarget === 'setup_workspace') {
        document.getElementById('setupWorkspacePath').value = path;
        closeFolderModal();
        return;
    }
    
    // Update the setting
    await updateSetting('storage', currentBrowseTarget, path);
    
    // Update the input field
    switch(currentBrowseTarget) {
        case 'workspace_dir':
            document.getElementById('settingWorkspaceDir').value = path;
            break;
        case 'documents_dir':
            document.getElementById('settingDocumentsDir').value = path;
            break;
        case 'images_dir':
            document.getElementById('settingImagesDir').value = path;
            break;
        case 'chats_dir':
            document.getElementById('settingChatsDir').value = path;
            break;
    }
    
    closeFolderModal();
}

function escapeAttr(str) {
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

// ================= 任务类型选择 =================
function initCapabilityButtons() {
    // Support both old .capability and new .capability-chip selectors
    const capabilities = document.querySelectorAll('.capability, .capability-chip');
    capabilities.forEach(cap => {
        cap.style.cursor = 'pointer';
        cap.addEventListener('click', () => selectCapability(cap));
    });
}

function selectCapability(element) {
    // 优先使用 data-task 属性
    let taskType = element.dataset.task;
    
    // 如果没有 data-task，则使用图标映射
    if (!taskType) {
        const icon = element.querySelector('.cap-icon, .chip-icon')?.textContent;
        const iconToTask = {
            '💬': 'CHAT',
            '💻': 'CODER',
            '🖥️': 'SYSTEM',
            '👁️': 'VISION',
            '🎨': 'PAINTER',
            '🎤': 'VOICE'
        };
        taskType = iconToTask[icon];
    }
    
    if (!taskType) return;
    
    // 切换选中状态 - support both selectors
    const capabilities = document.querySelectorAll('.capability, .capability-chip');
    
    if (lockedTaskType === taskType) {
        // 再次点击取消锁定
        lockedTaskType = null;
        element.classList.remove('selected', 'active');
        updateTaskIndicator(null);
    } else {
        // 选中新任务
        capabilities.forEach(c => {
            c.classList.remove('selected', 'active');
        });
        element.classList.add('selected', 'active');
        lockedTaskType = taskType;
        updateTaskIndicator(taskType);
    }
}

function updateTaskIndicator(taskType) {
    // 更新输入框的提示
    const input = document.getElementById('messageInput');
    const taskNames = {
        'CHAT': '💬 对话模式',
        'CODER': '💻 编程模式',
        'SYSTEM': '🖥️ 系统模式',
        'VISION': '👁️ 视觉模式',
        'PAINTER': '🎨 创作模式',
        'VOICE': '🎤 语音模式'
    };
    
    if (taskType) {
        input.placeholder = `${taskNames[taskType] || taskType} - 输入消息...`;
        // 显示任务指示器
        showTaskModeIndicator(taskType, taskNames[taskType] || taskType);
    } else {
        input.placeholder = 'Message Koto...';
        hideTaskModeIndicator();
    }
}

function showTaskModeIndicator(taskType, taskName) {
    let indicator = document.getElementById('taskModeIndicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'taskModeIndicator';
        indicator.className = 'task-mode-indicator';
        const inputContainer = document.querySelector('.chat-input-container, .composer');
        inputContainer.insertBefore(indicator, inputContainer.firstChild);
    }
    indicator.innerHTML = `
        <span class="task-mode-text">${taskName}</span>
        <button class="task-mode-clear" onclick="clearTaskMode()">✕</button>
    `;
    indicator.style.display = 'flex';
}

function hideTaskModeIndicator() {
    const indicator = document.getElementById('taskModeIndicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

function clearTaskMode() {
    lockedTaskType = null;
    document.querySelectorAll('.capability, .capability-chip').forEach(c => {
        c.classList.remove('selected', 'active');
    });
    updateTaskIndicator(null);
}

// ================= 用户设置加载 =================
async function loadUserSettings() {
    // 模型设置现已在主初始化流程中从 currentSettings 加载
    // 此函数保留以备其他地方调用
    try {
        if (!currentSettings) {
            const response = await fetch('/api/settings');
            currentSettings = await response.json();
        }
        const modelSelect = document.getElementById('settingModel');
        if (modelSelect && currentSettings?.ai) {
            selectedModel = currentSettings.ai.default_model || 'auto';
            modelSelect.value = selectedModel;
        }
    } catch (error) {
        console.error('Failed to load user settings:', error);
    }
}

function onModelChange(value) {
    selectedModel = value;
    updateSetting('ai', 'default_model', value);
}

// ================= 语音输入功能（后端API方案） =================
let voiceState = 'idle';  // idle, listening, processing, error
let isVoiceSupported = true;  // 假设后端API总是可用
let browserRecognition = null;

// 检查浏览器原生语音识别（仅用于检测，优先使用后端）
function isBrowserVoiceSupported() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
}

// 初始化语音功能
async function initVoice() {
    const voiceBtn = document.getElementById('voiceBtn');
    if (!voiceBtn) return;
    
    // 总是显示语音按钮，因为后端API应该可用
    isVoiceSupported = true;
    voiceBtn.style.display = 'flex';
    voiceBtn.title = '语音输入（点击说话）';
    console.log('[语音] ✓ 语音输入已就绪（使用后端API）');
}

// 初始化浏览器语音识别（保留作为备用）
function initBrowserVoice() {
    // 不再初始化浏览器语音，改用后端API
}

// 显示语音预览（中间结果）
function updateVoicePreview(text) {
    let preview = document.getElementById('voicePreview');
    if (!preview) {
        preview = document.createElement('div');
        preview.id = 'voicePreview';
        preview.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 20px;
            font-size: 16px;
            z-index: 10000;
            max-width: 80%;
            text-align: center;
        `;
        document.body.appendChild(preview);
    }
    preview.textContent = '🎤 ' + text;
    preview.style.display = 'block';
}

function hideVoicePreview() {
    const preview = document.getElementById('voicePreview');
    if (preview) {
        preview.style.display = 'none';
    }
}

// 语音状态变化回调（供 Python 调用）
window.onVoiceStateChange = function(state) {
    setVoiceState(state);
};

// 设置语音状态
function setVoiceState(state) {
    voiceState = state;
    const voiceBtn = document.getElementById('voiceBtn');
    if (!voiceBtn) return;
    
    // 更新按钮样式
    voiceBtn.classList.remove('listening', 'processing', 'error');
    
    switch (state) {
        case 'listening':
            voiceBtn.classList.add('listening');
            voiceBtn.innerHTML = '<span class="voice-icon">🎤</span><span class="voice-pulse"></span>';
            voiceBtn.title = '正在听...';
            break;
        case 'processing':
            voiceBtn.classList.add('processing');
            voiceBtn.innerHTML = '<span class="voice-icon">🔄</span>';
            voiceBtn.title = '正在识别...';
            break;
        case 'error':
            voiceBtn.classList.add('error');
            voiceBtn.innerHTML = '<span class="voice-icon">❌</span>';
            voiceBtn.title = '识别失败';
            break;
        default:
            voiceBtn.innerHTML = '<span class="voice-icon">🎙️</span>';
            voiceBtn.title = '语音输入';
    }
}

// 处理识别结果
function handleVoiceResult(text) {
    if (!text || !text.trim()) return;
    
    const input = document.getElementById('messageInput');
    if (input) {
        // 追加到输入框
        const currentText = input.value.trim();
        input.value = currentText ? currentText + ' ' + text : text;
        autoResize(input);
        
        // 默认自动发送（除非明确关闭）
        const autoSend = !currentSettings || !currentSettings.ai || currentSettings.ai.voice_auto_send !== false;
        
        if (autoSend) {
            // 立即发送
            showNotification(`🎤 ${text}`, 'success');
            setTimeout(() => {
                const event = new Event('submit', { cancelable: true });
                document.querySelector('.chat-input-form').dispatchEvent(event);
            }, 100);
        } else {
            showNotification(`识别: ${text}`, 'success');
            input.focus();
        }
    }
}

// 语音流式识别的 EventSource
let voiceEventSource = null;
let voiceAutoMode = true; // 默认自动模式
let pendingVoiceText = ''; // 手动模式下暂存的文本

// 获取语音模式设置
function getVoiceAutoMode() {
    return voiceAutoMode;
}

// 点击语音按钮 - 使用流式后端API
async function toggleVoice() {
    // 如果正在监听
    if (voiceState === 'listening' || voiceState === 'processing') {
        // 手动模式：点击确认上传
        if (!voiceAutoMode && pendingVoiceText) {
            handleVoiceResult(pendingVoiceText);
            pendingVoiceText = '';
        }
        stopVoiceRecognition();
        return;
    }
    
    // 重置暂存文本
    pendingVoiceText = '';
    
    // 开始流式监听
    setVoiceState('listening');
    
    // 优化：立即显示反馈（不要等待响应）
    if (voiceAutoMode) {
        showNotification('🎤 自动模式（已开始）', 'info', 1500);
    } else {
        showNotification('🎤 手动模式（已开始，按麦克风确认）', 'info', 2000);
    }
    
    // 显示实时预览
    showVoicePreview('', voiceAutoMode);
    
    try {
        voiceEventSource = new EventSource('/api/voice/stream');
        
        voiceEventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'partial') {
                // 实时更新预览
                updateVoicePreview(data.text);
                // 只有真正的识别文字（不是状态消息）才存入 pending
                if (data.text && !data.text.includes('🎤') && !data.text.includes('🎧') && 
                    !data.text.includes('✨') && !data.text.includes('⏱️')) {
                    pendingVoiceText = data.text;
                }
            } else if (data.type === 'final') {
                // 最终结果
                if (voiceAutoMode) {
                    // 自动模式：直接发送
                    hideVoicePreview();
                    stopVoiceRecognition();
                    if (data.text) {
                        handleVoiceResult(data.text);
                    }
                } else {
                    // 手动模式：等待用户确认
                    pendingVoiceText = data.text;
                    updateVoicePreviewForConfirm(data.text);
                }
            } else if (data.type === 'error') {
                hideVoicePreview();
                stopVoiceRecognition();
                if (data.message && data.message !== '未检测到语音') {
                    showNotification(data.message, 'warning');
                }
            }
        };
        
        voiceEventSource.onerror = () => {
            hideVoicePreview();
            stopVoiceRecognition();
            // 降级到非流式 API
            toggleVoiceFallback();
        };
        
    } catch (error) {
        console.error('[语音] 流式API错误:', error);
        hideVoicePreview();
        setVoiceState('error');
        setTimeout(() => setVoiceState('idle'), 1500);
        showNotification('❌ 语音服务暂时不可用', 'error', 2000);
    }
}

// 停止语音识别
function stopVoiceRecognition() {
    if (voiceEventSource) {
        voiceEventSource.close();
        voiceEventSource = null;
    }
    setVoiceState('idle');
    hideVoicePreview();
    
    // 发送停止信号
    fetch('/api/voice/stop', { method: 'POST' }).catch(() => {});
}

// 显示语音预览
function showVoicePreview(text, isAutoMode = true) {
    let preview = document.getElementById('voicePreview');
    if (!preview) {
        preview = document.createElement('div');
        preview.id = 'voicePreview';
        preview.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: 3px solid #3b82f6;
            border-radius: 16px;
            padding: 16px 24px;
            box-shadow: 0 8px 32px rgba(59,130,246,0.4), 0 0 0 1px rgba(255,255,255,0.1);
            z-index: 1000;
            min-width: 260px;
            max-width: 420px;
            text-align: center;
            animation: voicePulse 1.5s ease-in-out infinite;
        `;
        document.body.appendChild(preview);
        
        // 添加脉冲动画
        if (!document.getElementById('voicePulseStyle')) {
            const style = document.createElement('style');
            style.id = 'voicePulseStyle';
            style.textContent = `
                @keyframes voicePulse {
                    0%, 100% { box-shadow: 0 8px 32px rgba(59,130,246,0.4), 0 0 0 1px rgba(255,255,255,0.1); }
                    50% { box-shadow: 0 8px 40px rgba(59,130,246,0.6), 0 0 20px rgba(59,130,246,0.3), 0 0 0 1px rgba(255,255,255,0.2); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    const modeHint = isAutoMode 
        ? '<span style="color: #86efac;">✅ 自动模式</span> - 说完后自动发送'
        : '<span style="color: #fbbf24;">✋ 手动模式</span> - 点击麦克风确认';
    
    preview.innerHTML = `
        <div style="color: white; font-size: 13px; margin-bottom: 8px; font-weight: 600;" id="voiceModeLabel">🎤 正在聆听...</div>
        <div id="voicePreviewText" style="color: rgba(255,255,255,0.95); font-size: 16px; min-height: 28px; font-weight: 500; line-height: 1.4;">${text || ''}</div>
        <div style="color: rgba(255,255,255,0.7); font-size: 11px; margin-top: 10px;">${modeHint}</div>
        <div id="voiceElapsedTime" style="color: rgba(255,255,255,0.6); font-size: 10px; margin-top: 4px;"></div>
    `;
    preview.style.display = 'block';
}

// 更新语音预览为等待确认状态（手动模式）
function updateVoicePreviewForConfirm(text) {
    const preview = document.getElementById('voicePreview');
    if (preview) {
        const label = document.getElementById('voiceModeLabel');
        if (label) label.innerHTML = '✅ 识别完成';
        
        const previewText = document.getElementById('voicePreviewText');
        if (previewText) previewText.textContent = text;
        
        // 更新底部提示
        const hint = preview.querySelector('div:last-child');
        if (hint) hint.innerHTML = '<span style="color: #3b82f6; font-weight: 500;">👆 点击麦克风按钮发送</span>';
    }
}

// 更新语音预览
function updateVoicePreview(text) {
    const previewText = document.getElementById('voicePreviewText');
    const label = document.querySelector('#voicePreview > div:first-child');
    
    if (!text) return;
    
    // 判断是状态消息还是识别文字
    const isStatusMessage = text.includes('🎤') || text.includes('🎧') || 
                           text.includes('✨') || text.includes('⏱️') || 
                           text.includes('聆听') || text.includes('录音') || 
                           text.includes('请说话');
    
    if (isStatusMessage) {
        // 状态消息 - 显示在标签，清空文本区
        if (label) label.textContent = text;
        if (previewText) previewText.textContent = '';
    } else {
        // 真实识别文字 - 显示在文本区
        if (previewText) {
            previewText.textContent = text;
            // 添加淡入效果
            previewText.style.opacity = '0';
            setTimeout(() => {
                previewText.style.transition = 'opacity 0.3s ease-in';
                previewText.style.opacity = '1';
            }, 10);
        }
        if (label) label.textContent = '✨ 正在识别...';
    }
}

// 隐藏语音预览
function hideVoicePreview() {
    const preview = document.getElementById('voicePreview');
    if (preview) {
        preview.style.display = 'none';
    }
}

// 非流式 API 降级方案（优化版：立即开始，加快反馈）
async function toggleVoiceFallback() {
    if (voiceState === 'listening' || voiceState === 'processing') {
        return;
    }
    
    setVoiceState('listening');
    // 优化：立即显示反馈，而不是等待响应
    showNotification('🎤 正在聆听...（立即开始）', 'info', 1000);
    
    const startTime = Date.now();
    
    try {
        // 立即发送请求，不等待
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒硬超时
        
        const response = await fetch('/api/voice/listen', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ timeout: 8, language: 'zh-CN' }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        const elapsedMs = Date.now() - startTime;
        
        const data = await response.json();
        
        // 处理结果前设置为空闲状态
        setVoiceState('idle');
        
        if (data.success && data.text) {
            console.log('[语音] 识别结果:', data.text, `(耗时${elapsedMs}ms)`);
            // 自动发送
            handleVoiceResult(data.text);
        } else {
            const msg = data.message || '未能识别语音';
            console.log('[语音] 识别失败:', msg);
            showNotification(msg, 'warning', 2000);
        }
    } catch (error) {
        console.error('[语音] 后端API错误:', error);
        setVoiceState('error');
        setTimeout(() => setVoiceState('idle'), 1500);
        
        if (error.name === 'AbortError') {
            showNotification('❌ 识别超时（10秒）', 'error', 2000);
        } else {
            showNotification('❌ 语音服务暂时不可用', 'error', 2000);
        }
    }
}

// ==================== 语音功能面板函数 ====================

function initVoicePanel() {
    // 为语音选项卡添加点击事件
    const voiceChip = document.querySelector('[data-task="VOICE"]');
    if (voiceChip) {
        voiceChip.addEventListener('click', function() {
            // 防止默认的任务选择行为
            if (lockedTaskType === 'VOICE') {
                // 打开语音面板
                openVoicePanel();
            }
        });
    }
    
    // 加载语音命令
    loadVoiceCommands();
    
    // 为模态框背景点击关闭
    const modal = document.getElementById('voicePanelModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeVoicePanel();
            }
        });
    }
}

function openVoicePanel() {
    const modal = document.getElementById('voicePanelModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeVoicePanel() {
    const modal = document.getElementById('voicePanelModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadVoiceCommands() {
    try {
        const response = await fetch('/api/voice/commands');
        const data = await response.json();
        
        const commandsList = document.getElementById('voiceCommandsList');
        if (commandsList && data.commands) {
            commandsList.innerHTML = '';
            data.commands.forEach(cmd => {
                const div = document.createElement('div');
                div.className = 'command-item';
                div.innerHTML = `
                    <div class="command-name">${cmd.name}</div>
                    <div class="command-desc">${cmd.description}</div>
                `;
                commandsList.appendChild(div);
            });
        }
    } catch (error) {
        console.error('Failed to load voice commands:', error);
    }
}

async function startVoiceRecognition() {
    const btn = document.getElementById('voiceRecognizeBtn');
    const resultDiv = document.getElementById('voiceResult');
    const resultText = document.getElementById('voiceResultText');
    
    // 使用应用内独立语音识别（不依赖浏览器）
    if (false) {  // 禁用浏览器端识别
        try {
            btn.disabled = true;
            btn.textContent = '🎤 监听中...';
            resultDiv.style.display = 'none';
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            
            // 配置识别参数
            const language = document.getElementById('voiceLanguage')?.value || 'zh-CN';
            recognition.lang = language;
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
            
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                const confidence = event.results[0][0].confidence;
                
                resultText.textContent = transcript;
                resultDiv.style.display = 'block';
                
                console.log('语音识别结果:', transcript, '置信度:', confidence);
                
                // 如果启用自动发送
                if (document.getElementById('voiceAutoSend')?.checked) {
                    handleVoiceResult(transcript);
                    closeVoicePanel();
                }
            };
            
            recognition.onerror = (event) => {
                console.error('语音识别错误:', event.error);
                let errorMsg = '识别失败';
                switch(event.error) {
                    case 'no-speech':
                        errorMsg = '未检测到语音，请重试';
                        break;
                    case 'audio-capture':
                        errorMsg = '无法访问麦克风';
                        break;
                    case 'not-allowed':
                        errorMsg = '麦克风权限被拒绝';
                        break;
                    case 'network':
                        errorMsg = '网络错误';
                        break;
                    default:
                        errorMsg = '识别失败: ' + event.error;
                }
                resultText.textContent = errorMsg;
                resultDiv.style.display = 'block';
            };
            
            recognition.onend = () => {
                btn.disabled = false;
                btn.textContent = '🎤 开始识别';
            };
            
            // 开始识别
            recognition.start();
            
        } catch (error) {
            console.error('启动语音识别失败:', error);
            btn.disabled = false;
            btn.textContent = '🎤 开始识别';
            resultText.textContent = '启动失败: ' + error.message;
            resultDiv.style.display = 'block';
        }
    } else {
        // 降级到后端 API
        try {
            btn.disabled = true;
            btn.textContent = '🎤 录音中...';
            resultDiv.style.display = 'none';
            
            const response = await fetch('/api/voice/listen', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    timeout: 5,
                    language: document.getElementById('voiceLanguage')?.value || 'zh-CN'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                resultText.textContent = result.text;
                resultDiv.style.display = 'block';
                
                // 如果启用自动发送
                if (document.getElementById('voiceAutoSend')?.checked) {
                    handleVoiceResult(result.text);
                    closeVoicePanel();
                }
            } else {
                resultText.textContent = '识别失败: ' + (result.message || '未知错误');
                resultDiv.style.display = 'block';
            }
        } catch (error) {
            console.error('Voice recognition error:', error);
            resultText.textContent = '错误: ' + error.message;
            resultDiv.style.display = 'block';
        } finally {
            btn.disabled = false;
            btn.textContent = '🎤 开始识别';
        }
    }
}

// ==================== 文档建议系统 ====================

// 存储当前建议状态
let suggestionState = {
    suggestions: [],
    filePath: null,
    eventSource: null
};

/**
 * 打开文档建议面板并开始分析
 */
function openSuggestionPanel(filePath, userRequirement = "") {
    console.log('[SUGGESTION] Opening panel for:', filePath);
    
    // 重置状态
    suggestionState = {
        suggestions: [],
        filePath: filePath,
        eventSource: null
    };
    
    // 显示面板
    const modal = document.getElementById('suggestionPanelModal');
    modal.style.display = 'flex';
    
    // 重置UI
    document.getElementById('suggestionProgressFill').style.width = '0%';
    document.getElementById('suggestionProgressText').textContent = '准备分析...';
    document.getElementById('suggestionStats').style.display = 'none';
    document.getElementById('suggestionQuickActions').style.display = 'none';
    document.getElementById('suggestionFooter').style.display = 'none';
    document.getElementById('suggestionList').innerHTML = '<div class="suggestion-empty"><p>🔍 正在分析文档...</p></div>';
    
    // 开始SSE流式分析
    startSuggestionStream(filePath, userRequirement);
}

/**
 * 关闭建议面板
 */
function closeSuggestionPanel() {
    const modal = document.getElementById('suggestionPanelModal');
    modal.style.display = 'none';
    
    // 关闭SSE连接
    if (suggestionState.eventSource) {
        suggestionState.eventSource.close();
        suggestionState.eventSource = null;
    }
}

/**
 * 开始SSE流式获取建议
 */
function startSuggestionStream(filePath, userRequirement) {
    console.log('[SUGGESTION] Starting stream...');
    
    // 使用fetch + ReadableStream处理POST请求的SSE
    fetch('/api/document/suggest-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            file_path: filePath,
            user_requirement: userRequirement
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        function processStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    console.log('[SUGGESTION] Stream ended');
                    return;
                }
                
                buffer += decoder.decode(value, { stream: true });
                
                // 解析SSE事件 - 格式: "event: xxx\ndata: {...}\n\n"
                const events = buffer.split('\n\n');
                buffer = events.pop() || ''; // 保留最后不完整的部分
                
                for (const eventStr of events) {
                    if (!eventStr.trim()) continue;
                    
                    const lines = eventStr.split('\n');
                    let eventType = '';
                    let eventData = '';
                    
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7);
                        } else if (line.startsWith('data: ')) {
                            eventData = line.slice(6);
                        }
                    }
                    
                    if (eventType && eventData) {
                        try {
                            const data = JSON.parse(eventData);
                            handleSuggestionEvent(eventType, data);
                        } catch (e) {
                            console.error('[SUGGESTION] Parse error:', e, eventData);
                        }
                    }
                }
                
                processStream();
            }).catch(err => {
                console.error('[SUGGESTION] Stream error:', err);
            });
        }
        
        processStream();
    })
    .catch(err => {
        console.error('[SUGGESTION] Fetch error:', err);
        showNotification('分析失败: ' + err.message, 'error');
    });
}

/**
 * 处理单个SSE事件
 */
function handleSuggestionEvent(eventType, data) {
    console.log('[SUGGESTION] Event:', eventType, data);
    
    switch (eventType) {
        case 'progress':
            updateProgress(data.progress, data.message);
            break;
            
        case 'suggestion':
            addSuggestionToUI(data);
            break;
            
        case 'batch_complete':
            updateStats();
            break;
            
        case 'suggestions_complete':
            onSuggestionsComplete(data);
            break;
            
        case 'complete':
            onAnalysisComplete(data);
            break;
            
        case 'error':
            showNotification(data.message, 'error');
            break;
    }
}

/**
 * 更新进度条
 */
function updateProgress(percent, message) {
    document.getElementById('suggestionProgressFill').style.width = percent + '%';
    document.getElementById('suggestionProgressText').textContent = message;
}

/**
 * 添加单个建议到UI
 */
function addSuggestionToUI(suggestion) {
    const list = document.getElementById('suggestionList');
    
    // 移除"正在分析"提示
    const emptyDiv = list.querySelector('.suggestion-empty');
    if (emptyDiv) emptyDiv.remove();
    
    // 存储建议
    suggestion.accepted = null; // null=未决定, true=接受, false=拒绝
    suggestionState.suggestions.push(suggestion);
    
    // 创建建议卡片
    const card = document.createElement('div');
    card.className = 'suggestion-item';
    card.id = `suggestion-${suggestion.id}`;
    
    const confidence = Math.round((suggestion.置信度 || 0.8) * 100);
    
    card.innerHTML = `
        <div class="suggestion-header">
            <div class="suggestion-type">
                <span class="type-badge">${escapeHtml(suggestion.类型 || '修改')}</span>
                <span class="para-info">第 ${suggestion.段落号 + 1} 段</span>
            </div>
            <span class="confidence-badge">${confidence}% 置信度</span>
        </div>
        <div class="suggestion-diff">
            <div class="diff-original">
                <div class="diff-label">原文</div>
                ${escapeHtml(suggestion.原文)}
            </div>
            <div class="diff-modified">
                <div class="diff-label">建议修改为</div>
                ${escapeHtml(suggestion.修改)}
            </div>
        </div>
        <div class="suggestion-reason">
            💡 ${escapeHtml(suggestion.说明 || '优化表达')}
        </div>
        <div class="suggestion-actions">
            <button class="btn-accept" onclick="acceptSuggestion('${suggestion.id}')">✓ 接受</button>
            <button class="btn-reject" onclick="rejectSuggestion('${suggestion.id}')">✗ 忽略</button>
        </div>
    `;
    
    list.appendChild(card);
    
    // 滚动到最新
    list.scrollTop = list.scrollHeight;
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

/**
 * 更新统计信息
 */
function updateStats() {
    const total = suggestionState.suggestions.length;
    const accepted = suggestionState.suggestions.filter(s => s.accepted === true).length;
    const rejected = suggestionState.suggestions.filter(s => s.accepted === false).length;
    
    document.getElementById('totalSuggestions').textContent = total;
    document.getElementById('acceptedCount').textContent = accepted;
    document.getElementById('rejectedCount').textContent = rejected;
    
    if (total > 0) {
        document.getElementById('suggestionStats').style.display = 'flex';
    }
}

/**
 * 所有建议生成完成
 */
function onSuggestionsComplete(data) {
    console.log('[SUGGESTION] All suggestions received:', data.total_suggestions);
    
    if (data.total_suggestions > 0) {
        document.getElementById('suggestionQuickActions').style.display = 'flex';
        document.getElementById('suggestionFooter').style.display = 'flex';
    } else {
        document.getElementById('suggestionList').innerHTML = 
            '<div class="suggestion-empty"><p>✨ 文档已经很完美，没有需要修改的地方！</p></div>';
    }
    
    updateStats();
}

/**
 * 分析完成
 */
function onAnalysisComplete(data) {
    updateProgress(100, `✅ 分析完成！共 ${data.total_suggestions} 处建议`);
}

/**
 * 接受单个建议
 */
function acceptSuggestion(suggestionId) {
    const suggestion = suggestionState.suggestions.find(s => s.id === suggestionId);
    if (suggestion) {
        suggestion.accepted = true;
        
        const card = document.getElementById(`suggestion-${suggestionId}`);
        card.classList.remove('rejected');
        card.classList.add('accepted');
        
        const acceptBtn = card.querySelector('.btn-accept');
        const rejectBtn = card.querySelector('.btn-reject');
        acceptBtn.classList.add('active');
        rejectBtn.classList.remove('active');
        
        updateStats();
    }
}

/**
 * 拒绝单个建议
 */
function rejectSuggestion(suggestionId) {
    const suggestion = suggestionState.suggestions.find(s => s.id === suggestionId);
    if (suggestion) {
        suggestion.accepted = false;
        
        const card = document.getElementById(`suggestion-${suggestionId}`);
        card.classList.remove('accepted');
        card.classList.add('rejected');
        
        const acceptBtn = card.querySelector('.btn-accept');
        const rejectBtn = card.querySelector('.btn-reject');
        acceptBtn.classList.remove('active');
        rejectBtn.classList.add('active');
        
        updateStats();
    }
}

/**
 * 全部接受
 */
function acceptAllSuggestions() {
    for (const s of suggestionState.suggestions) {
        acceptSuggestion(s.id);
    }
}

/**
 * 全部拒绝
 */
function rejectAllSuggestions() {
    for (const s of suggestionState.suggestions) {
        rejectSuggestion(s.id);
    }
}

/**
 * 应用已接受的修改
 */
async function applySuggestions() {
    const acceptedSuggestions = suggestionState.suggestions.filter(s => s.accepted === true);
    
    if (acceptedSuggestions.length === 0) {
        showNotification('请先选择要接受的修改', 'warning');
        return;
    }
    
    updateProgress(90, '📥 正在应用修改...');
    
    try {
        const response = await fetch('/api/document/apply-suggestions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: suggestionState.filePath,
                suggestions: acceptedSuggestions
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateProgress(100, `✅ 已应用 ${result.applied_count} 处修改`);
            showNotification(`成功应用 ${result.applied_count} 处修改！文件已保存到: ${result.output_file}`, 'success', 5000);
            
            // 延迟关闭面板
            setTimeout(() => {
                closeSuggestionPanel();
            }, 2000);
        } else {
            showNotification('应用失败: ' + result.error, 'error');
        }
    } catch (err) {
        console.error('[SUGGESTION] Apply error:', err);
        showNotification('应用失败: ' + err.message, 'error');
    }
}

// ================= 文件生成进度显示 =================

/**
 * 显示文件生成进度
 * @param {HTMLElement} container 容器元素
 * @param {number} percentage 进度百分比 (0-100)
 * @param {string} stage 当前阶段 (validating/evaluating/improving/generating/completed/error)
 * @param {string} message 状态信息
 */
function displayGenerationProgress(container, percentage, stage, message) {
    if (!container) return;
    
    // 创建或获取进度容器
    let progressContainer = container.querySelector('.generation-progress');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.className = 'generation-progress';
        container.appendChild(progressContainer);
    }
    
    // 定义阶段信息
    const stageInfo = {
        'validating': { icon: '📋', text: '验证输入', color: '#3b82f6' },
        'evaluating': { icon: '📊', text: '评估质量', color: '#f59e0b' },
        'improving': { icon: '✨', text: '改进内容', color: '#8b5cf6' },
        'generating': { icon: '⚙️', text: '生成文件', color: '#06b6d4' },
        'completed': { icon: '✅', text: '已完成', color: '#22c55e' },
        'error': { icon: '❌', text: '出错', color: '#ef4444' }
    };
    
    const info = stageInfo[stage] || stageInfo['validating'];
    const isCompleted = stage === 'completed';
    const isError = stage === 'error';
    
    progressContainer.innerHTML = `
        <div class="progress-header">
            <span class="progress-stage-icon">${info.icon}</span>
            <span class="progress-stage-text">${info.text}</span>
            <span class="progress-percentage">${percentage}%</span>
        </div>
        <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${percentage}%; background-color: ${info.color};"></div>
        </div>
        <div class="progress-message">${message}</div>
    `;
    
    // 根据状态调整样式
    if (isCompleted) {
        progressContainer.classList.add('progress-completed');
    } else if (isError) {
        progressContainer.classList.add('progress-error');
    } else {
        progressContainer.classList.remove('progress-completed', 'progress-error');
    }
}

/**
 * 显示评估详情
 * @param {HTMLElement} container 容器
 * @param {Object} assessment 评估对象 {overall_score, issues, suggestions, improvement_priority}
 */
function displayQualityAssessment(container, assessment) {
    if (!container || !assessment) return;
    
    let assessmentEl = container.querySelector('.quality-assessment');
    if (!assessmentEl) {
        assessmentEl = document.createElement('details');
        assessmentEl.className = 'quality-assessment';
        assessmentEl.innerHTML = '<summary>📈 质量评估</summary><div class="assessment-content"></div>';
        container.appendChild(assessmentEl);
    }
    
    const contentEl = assessmentEl.querySelector('.assessment-content');
    const score = assessment.overall_score || 0;
    const scoreColor = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444';
    
    let html = `
        <div class="assessment-score" style="color: ${scoreColor};">
            📊 综合评分: <strong>${score.toFixed(1)}/100</strong>
        </div>
    `;
    
    if (assessment.issues && assessment.issues.length > 0) {
        html += '<div class="assessment-section"><div class="section-title">⚠️ 发现的问题:</div>';
        html += '<ul class="assessment-list">';
        assessment.issues.forEach(issue => {
            html += `<li>${escapeHtml(issue)}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (assessment.suggestions && assessment.suggestions.length > 0) {
        html += '<div class="assessment-section"><div class="section-title">💡 改进建议:</div>';
        html += '<ul class="assessment-list">';
        assessment.suggestions.forEach(suggestion => {
            html += `<li>${escapeHtml(suggestion)}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (assessment.improvement_priority && assessment.improvement_priority.length > 0) {
        html += '<div class="assessment-section"><div class="section-title">🎯 改进优先级:</div>';
        html += '<ol class="assessment-list">';
        assessment.improvement_priority.forEach(priority => {
            html += `<li>${escapeHtml(priority)}</li>`;
        });
        html += '</ol></div>';
    }
    
    contentEl.innerHTML = html;
    assessmentEl.open = true;
}

/**
 * 处理文件生成进度 SSE 事件
 */
function setupGenerationProgressListener(sessionName) {
    // 该函数由 streamChat 调用来监听进度事件
    // 进度事件来自 /api/chat/stream 的 data.type === 'generation_progress'
}

// ================= Artifacts 面板 =================

let currentArtifact = { code: '', lang: '', title: '' };

/**
 * 打开代码块到 Artifacts 侧面板
 */
function openInArtifact(btn) {
    const encoded = btn.dataset.code;
    const lang = btn.dataset.lang || 'plaintext';
    if (!encoded) return;
    
    const code = decodeURIComponent(escape(atob(encoded)));
    currentArtifact = { code, lang, title: lang.toUpperCase() + ' Code' };
    
    // 更新标题和元数据
    document.getElementById('artifactsTitle').textContent = currentArtifact.title;
    document.getElementById('artifactLang').textContent = lang;
    document.getElementById('artifactSize').textContent = `${code.length} chars · ${(code.match(/\n/g)||[]).length + 1} lines`;
    
    // 默认显示预览
    switchArtifactTab('preview');
    
    // 打开面板
    document.getElementById('artifactsPanel').classList.add('active');
}

/**
 * 切换 Artifact 预览/代码 tab
 */
function switchArtifactTab(tab) {
    // Tab 按钮状态
    document.querySelectorAll('.artifact-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.artifact-tab-btn[data-tab="${tab}"]`)?.classList.add('active');
    
    const previewEl = document.getElementById('artifactPreview');
    const codeEl = document.getElementById('artifactCode');
    
    if (tab === 'preview') {
        previewEl.style.display = '';
        codeEl.style.display = 'none';
        renderArtifactPreview();
    } else {
        previewEl.style.display = 'none';
        codeEl.style.display = '';
        renderArtifactCode();
    }
}

/**
 * 渲染 Artifact 预览
 */
function renderArtifactPreview() {
    const el = document.getElementById('artifactPreview');
    const { code, lang } = currentArtifact;
    
    // HTML 文件：用 iframe sandbox 实时预览
    if (['html', 'htm'].includes(lang)) {
        el.innerHTML = '<iframe sandbox="allow-scripts allow-same-origin" style="width:100%;height:calc(100vh - 100px);border:none;border-radius:8px;background:#fff;"></iframe>';
        const iframe = el.querySelector('iframe');
        iframe.srcdoc = code;
        return;
    }
    
    // Markdown：渲染为 HTML
    if (['markdown', 'md'].includes(lang)) {
        el.innerHTML = `<div class="message-body">${parseMarkdown(code)}</div>`;
        renderMermaidBlocks();
        return;
    }
    
    // SVG：直接渲染
    if (lang === 'svg' || code.trim().startsWith('<svg')) {
        el.innerHTML = `<div style="text-align:center;padding:20px;">${code}</div>`;
        return;
    }
    
    // 其他代码：高亮显示
    if (typeof hljs !== 'undefined') {
        const validLang = hljs.getLanguage(lang) ? lang : '';
        const highlighted = validLang
            ? hljs.highlight(code, { language: validLang }).value
            : hljs.highlightAuto(code).value;
        el.innerHTML = `<pre style="margin:0;padding:0;background:transparent;"><code class="hljs language-${validLang || 'plaintext'}" style="font-size:13px;line-height:1.6;">${highlighted}</code></pre>`;
    } else {
        el.innerHTML = `<pre style="white-space:pre-wrap;">${escapeHtml(code)}</pre>`;
    }
}

/**
 * 渲染 Artifact 源代码
 */
function renderArtifactCode() {
    const el = document.getElementById('artifactCode');
    const { code, lang } = currentArtifact;
    
    // 可编辑的 textarea
    el.innerHTML = `
        <div class="code-actions">
            <button class="copy-btn" onclick="copyArtifactContent()" title="复制">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>复制</span>
            </button>
        </div>
        <textarea class="artifact-editor" spellcheck="false" 
            style="width:100%;height:calc(100vh - 140px);background:var(--code-bg);color:var(--code-text);border:none;padding:18px;font-family:'JetBrains Mono',monospace;font-size:13px;line-height:1.6;resize:none;outline:none;"
            oninput="currentArtifact.code = this.value">${escapeHtml(code)}</textarea>`;
}

/**
 * 复制 Artifact 内容
 */
async function copyArtifactContent() {
    try {
        await navigator.clipboard.writeText(currentArtifact.code);
        const btn = document.querySelector('.artifact-copy-all');
        if (btn) {
            const orig = btn.innerHTML;
            btn.innerHTML = '✓';
            setTimeout(() => btn.innerHTML = orig, 1500);
        }
    } catch (e) { console.error('Copy failed:', e); }
}

/**
 * 下载 Artifact 文件
 */
function downloadArtifact() {
    const { code, lang } = currentArtifact;
    const extMap = { python: 'py', javascript: 'js', typescript: 'ts', html: 'html', css: 'css', json: 'json', markdown: 'md', java: 'java', cpp: 'cpp', c: 'c', go: 'go', rust: 'rs', ruby: 'rb', php: 'php', sql: 'sql', bash: 'sh', powershell: 'ps1', yaml: 'yml', xml: 'xml', svg: 'svg' };
    const ext = extMap[lang] || 'txt';
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `artifact.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * 关闭 Artifacts 面板
 */
function closeArtifacts() {
    document.getElementById('artifactsPanel').classList.remove('active');
}

// ================= Proactive UI =================
const PROACTIVE_USER_ID = 'default';
let notificationSocket = null;
let notificationPollTimer = null;
let notificationCache = [];

function initProactiveUI() {
    connectNotificationSocket();
    refreshNotifications();
    initProactiveModalHandlers();
}

function initProactiveModalHandlers() {
    const notificationModal = document.getElementById('notificationPanelModal');
    if (notificationModal) {
        notificationModal.addEventListener('click', (e) => {
            if (e.target === notificationModal) {
                closeNotificationCenter();
            }
        });
    }
    const triggerModal = document.getElementById('triggerPanelModal');
    if (triggerModal) {
        triggerModal.addEventListener('click', (e) => {
            if (e.target === triggerModal) {
                closeTriggerPanel();
            }
        });
    }
}

function connectNotificationSocket() {
    if (!('WebSocket' in window)) {
        startNotificationPolling();
        return;
    }
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${location.host}/ws/notifications?user_id=${encodeURIComponent(PROACTIVE_USER_ID)}`;
    try {
        notificationSocket = new WebSocket(wsUrl);
        notificationSocket.onopen = () => console.log('[WS] 通知连接已建立');
        notificationSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.event === 'notification' && data.payload) {
                    showNotification(data.payload.title || '新通知', 'info', 2500);
                    refreshNotifications();
                }
            } catch (err) {
                console.warn('[WS] 解析通知失败', err);
            }
        };
        notificationSocket.onerror = () => startNotificationPolling();
        notificationSocket.onclose = () => startNotificationPolling();
    } catch (err) {
        console.warn('[WS] 连接失败，启用轮询', err);
        startNotificationPolling();
    }
}

function startNotificationPolling() {
    if (notificationPollTimer) return;
    notificationPollTimer = setInterval(refreshNotifications, 15000);
}

function openNotificationCenter() {
    const modal = document.getElementById('notificationPanelModal');
    if (modal) {
        modal.style.display = 'flex';
    }
    refreshNotifications();
}

function closeNotificationCenter() {
    const modal = document.getElementById('notificationPanelModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function refreshNotifications() {
    try {
        const response = await fetch(`/api/notifications/unread?user_id=${encodeURIComponent(PROACTIVE_USER_ID)}&limit=50`);
        const data = await response.json();
        if (!data.success) return;
        notificationCache = data.notifications || [];
        renderNotifications(notificationCache);
        updateNotificationBadge(notificationCache.length);
    } catch (error) {
        console.error('Failed to load notifications:', error);
    }
}

function renderNotifications(notifications) {
    const listEl = document.getElementById('notificationList');
    const emptyEl = document.getElementById('notificationEmpty');
    if (!listEl || !emptyEl) return;
    
    if (!notifications.length) {
        listEl.innerHTML = '';
        emptyEl.style.display = 'block';
        return;
    }
    emptyEl.style.display = 'none';
    listEl.innerHTML = notifications.map(n => {
        const created = n.created_at ? new Date(n.created_at).toLocaleString() : '';
        return `
            <div class="notification-card">
                <div class="meta">
                    <span>${escapeHtml(n.type || 'notice')}</span>
                    <span>${escapeHtml(created)}</span>
                </div>
                <div class="title">${escapeHtml(n.title || '通知')}</div>
                <div class="message">${escapeHtml(n.message || '')}</div>
                <div class="actions">
                    <button class="btn-sm" onclick="markNotificationRead(${n.id})">✓ 已读</button>
                    <button class="btn-sm" onclick="dismissNotification(${n.id})">✕ 忽略</button>
                </div>
            </div>
        `;
    }).join('');
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-flex';
    } else {
        badge.style.display = 'none';
    }
}

async function markNotificationRead(notificationId, silent = false) {
    try {
        await fetch('/api/notifications/mark-read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notification_id: notificationId, user_id: PROACTIVE_USER_ID })
        });
        if (!silent) showNotification('已标记为已读', 'success', 1500);
        refreshNotifications();
    } catch (error) {
        console.error('Failed to mark read:', error);
    }
}

async function dismissNotification(notificationId) {
    try {
        await fetch('/api/notifications/dismiss', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notification_id: notificationId, user_id: PROACTIVE_USER_ID })
        });
        showNotification('通知已忽略', 'warning', 1500);
        refreshNotifications();
    } catch (error) {
        console.error('Failed to dismiss:', error);
    }
}

async function markAllNotificationsRead() {
    if (!notificationCache.length) return;
    for (const item of notificationCache) {
        await markNotificationRead(item.id, true);
    }
    showNotification('已全部标记为已读', 'success', 1500);
}

function openTriggerPanel() {
    const modal = document.getElementById('triggerPanelModal');
    if (modal) {
        modal.style.display = 'flex';
    }
    refreshTriggerList();
}

function closeTriggerPanel() {
    const modal = document.getElementById('triggerPanelModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function refreshTriggerList() {
    try {
        const response = await fetch('/api/triggers/list');
        const data = await response.json();
        if (!data.success) return;
        renderTriggerList(data.triggers || []);
    } catch (error) {
        console.error('Failed to load triggers:', error);
    }
}

function renderTriggerList(triggers) {
    const listEl = document.getElementById('triggerList');
    if (!listEl) return;
    if (!triggers.length) {
        listEl.innerHTML = '<div class="notification-empty">暂无触发器</div>';
        return;
    }
    listEl.innerHTML = triggers.map(t => {
        const params = t.parameters || {};
        let parametersHTML = '';
        
        // 为每个参数生成编辑字段
        for (const [key, value] of Object.entries(params)) {
            const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
            parametersHTML += `
                <label class="trigger-param">
                    <span>${escapeHtml(key)}</span>
                    <input type="text" value="${escapeHtml(displayValue)}" 
                           onchange="updateTriggerParam('${escapeHtml(t.trigger_id)}', '${escapeHtml(key)}', this.value)"
                           placeholder="${escapeHtml(key)}">
                </label>
            `;
        }
        
        return `
            <div class="trigger-item" data-id="${escapeHtml(t.trigger_id)}">
                <div class="title">
                    <span>${escapeHtml(t.trigger_id)}</span>
                    <span class="meta">${escapeHtml(t.trigger_type)}</span>
                </div>
                <div class="meta">${escapeHtml(t.description || '')}</div>
                <div class="controls">
                    <label class="trigger-toggle">
                        <input type="checkbox" ${t.enabled ? 'checked' : ''} onchange="toggleTrigger('${escapeHtml(t.trigger_id)}', this.checked)">
                        启用
                    </label>
                    <label class="trigger-toggle">优先级
                        <input type="number" min="1" max="10" value="${t.priority}" onchange="updateTriggerValue('${escapeHtml(t.trigger_id)}', 'priority', this.value)">
                    </label>
                    <label class="trigger-toggle">冷却(分钟)
                        <input type="number" min="5" max="1440" value="${t.cooldown_minutes}" onchange="updateTriggerValue('${escapeHtml(t.trigger_id)}', 'cooldown_minutes', this.value)">
                    </label>
                    <button class="btn-sm" onclick="toggleTriggerParams('${escapeHtml(t.trigger_id)}')">⚙️ 参数</button>
                    <button class="btn-sm" onclick="saveTrigger('${escapeHtml(t.trigger_id)}')">保存</button>
                </div>
                ${parametersHTML ? `<div class="trigger-params-section" id="params-${escapeHtml(t.trigger_id)}" style="display: none;">${parametersHTML}</div>` : ''}
            </div>
        `;
    }).join('');
}

const triggerDrafts = {};
const triggerParamDrafts = {};

function toggleTriggerParams(triggerId) {
    const paramsSection = document.getElementById(`params-${triggerId}`);
    if (paramsSection) {
        if (paramsSection.style.display === 'none') {
            paramsSection.style.display = 'block';
        } else {
            paramsSection.style.display = 'none';
        }
    }
}

function toggleTrigger(triggerId, enabled) {
    if (!triggerDrafts[triggerId]) triggerDrafts[triggerId] = {};
    triggerDrafts[triggerId].enabled = enabled;
}

function updateTriggerValue(triggerId, field, value) {
    if (!triggerDrafts[triggerId]) triggerDrafts[triggerId] = {};
    const parsed = field === 'priority' || field === 'cooldown_minutes'
        ? parseInt(value, 10)
        : value;
    triggerDrafts[triggerId][field] = parsed;
}

function updateTriggerParam(triggerId, paramKey, paramValue) {
    if (!triggerParamDrafts[triggerId]) triggerParamDrafts[triggerId] = {};
    
    // 尝试解析为数字或布尔值
    let value = paramValue;
    if (paramValue === 'true') value = true;
    else if (paramValue === 'false') value = false;
    else if (!isNaN(paramValue) && paramValue !== '') value = parseFloat(paramValue);
    
    triggerParamDrafts[triggerId][paramKey] = value;
}

async function saveTrigger(triggerId) {
    const payload = Object.assign({ trigger_id: triggerId }, triggerDrafts[triggerId] || {});
    
    // 如果有参数修改，添加参数
    if (triggerParamDrafts[triggerId] && Object.keys(triggerParamDrafts[triggerId]).length > 0) {
        payload.parameters = triggerParamDrafts[triggerId];
    }
    
    try {
        const response = await fetch('/api/triggers/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.success) {
            showNotification('触发器已更新', 'success', 1500);
            triggerDrafts[triggerId] = {};
            triggerParamDrafts[triggerId] = {};
            refreshTriggerList();
        } else {
            showNotification(data.error || '更新失败', 'error', 2000);
        }
    } catch (error) {
        console.error('Failed to update trigger:', error);
        showNotification('更新失败', 'error', 2000);
    }
}

async function startTriggerMonitoring() {
    const intervalInput = document.getElementById('triggerIntervalInput');
    const interval = intervalInput ? parseInt(intervalInput.value, 10) : 300;
    try {
        await fetch('/api/triggers/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: PROACTIVE_USER_ID, interval })
        });
        showNotification('触发监控已启动', 'success', 1500);
    } catch (error) {
        console.error('Failed to start trigger monitoring:', error);
    }
}

async function stopTriggerMonitoring() {
    try {
        await fetch('/api/triggers/stop', { method: 'POST' });
        showNotification('触发监控已停止', 'warning', 1500);
    } catch (error) {
        console.error('Failed to stop trigger monitoring:', error);
    }
}

async function runTriggerEvaluation() {
    const decisionEl = document.getElementById('triggerDecision');
    if (decisionEl) decisionEl.textContent = '评估中...';
    try {
        const response = await fetch('/api/triggers/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: PROACTIVE_USER_ID, execute: false })
        });
        const data = await response.json();
        if (decisionEl) {
            if (data.decision) {
                const d = data.decision;
                decisionEl.innerHTML = `
                    <strong>${escapeHtml(d.reason || '评估结果')}</strong><br>
                    类型: ${escapeHtml(d.interaction_type || '')} · 优先级: ${escapeHtml(d.priority || '')}<br>
                    分数: ${d.scores?.final?.toFixed(2) || '0.00'}
                `;
            } else {
                decisionEl.textContent = '暂无触发结果';
            }
        }
    } catch (error) {
        if (decisionEl) decisionEl.textContent = '评估失败';
        console.error('Failed to evaluate triggers:', error);
    }
}

/**
 * 全局：每次 parseMarkdown 后渲染 Mermaid
 * 使用 MutationObserver 自动触发
 */
(function initMermaidObserver() {
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeType === 1 && (node.querySelector?.('.mermaid:not([data-processed])') || node.classList?.contains('mermaid'))) {
                    renderMermaidBlocks();
                    return;
                }
            }
        }
    });
    // 延迟初始化，等 DOM 就绪
    if (document.readyState !== 'loading') {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }
})();