// app.js

// Configuration
const CONFIG = {
    API_BASE: window.location.origin, // Assumes frontend and backend are on the same domain
    MAX_MESSAGE_LENGTH: 500,
    HISTORY_LIMIT: 10 // Max history pairs (user + bot) to send
};

// State
const state = {
    history: [],
    isLoading: false
};

// DOM Elements
const elements = {
    messages: document.getElementById('messages'),
    messageInput: document.getElementById('messageInput'),
    chatForm: document.getElementById('chatForm'),
    sendButton: document.getElementById('sendButton'),
    typing: document.getElementById('typing'),
    sourcesContainer: document.getElementById('sourcesContainer'),
    sourcesList: document.getElementById('sourcesList'),
    stats: document.getElementById('stats'),
    sourcesToggle: document.getElementById('sourcesToggle')
};

// Utilities
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || ''; // Ensure text is not null/undefined
    return div.innerHTML;
}

function formatMessage(content) {
    // Basic markdown-like formatting
    return escapeHtml(content)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/\*(.*?)\*/g, '<em>$1</em>')         // Italic
        .replace(/`([^`]+)`/g, '<code>$1</code>')        // Code
        .replace(/\n/g, '<br>');                      // Newlines
}

function scrollToBottom() {
    setTimeout(() => {
        elements.messages.scrollTo({
            top: elements.messages.scrollHeight,
            behavior: 'smooth'
        });
    }, 100);
}

// API Functions
async function sendMessageToAPI(message, history) {
    const response = await fetch(`${CONFIG.API_BASE}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // Cleaned up body to match backend Pydantic model
        body: JSON.stringify({
            message,
            history: history.slice(-CONFIG.HISTORY_LIMIT),
            k: 5
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
    }

    return response.json();
}

async function getStats() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/stats`);
        if (!response.ok) return;
        const data = await response.json();
        if (data.total_pedidos) {
            elements.stats.textContent = `📊 ${data.total_pedidos.toLocaleString('pt-BR')} pedidos disponíveis`;
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
        elements.stats.textContent = '📊 Estatísticas indisponíveis';
    }
}

// UI Functions
function addMessage(content, isUser = false, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'} ${isError ? 'error' : ''}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMessage(content);

    messageDiv.appendChild(contentDiv);
    elements.messages.appendChild(messageDiv);
    scrollToBottom();
}

function showTyping() {
    elements.typing.style.display = 'flex';
    scrollToBottom();
}

function hideTyping() {
    elements.typing.style.display = 'none';
}

function setControlsState(enabled) {
    elements.sendButton.disabled = !enabled;
    elements.messageInput.disabled = !enabled;
}

function renderSources(sources) {
    if (!sources || sources.length === 0) {
        elements.sourcesContainer.classList.remove('active');
        return;
    }

    elements.sourcesList.innerHTML = '';

    // Função auxiliar para criar uma linha de informação apenas se o texto for válido
    const createInfoLine = (icon, text) => {
        if (!text || text.toLowerCase() === 'n/a' || text.includes('N/A')) {
            return ''; // Retorna string vazia se não houver dado, para não renderizar a linha
        }
        return `<div class="source-info">${icon} ${escapeHtml(text)}</div>`;
    };

    sources.forEach(source => {
        const card = document.createElement('div');
        card.className = 'source-card';

        // Usa a função auxiliar para construir o HTML dinamicamente
        card.innerHTML = `
            <div class="source-protocol">📋 ${escapeHtml(source.protocolo || 'Protocolo não encontrado')}</div>
            ${createInfoLine('🏢', source.orgao)}
            ${createInfoLine('📅', source.data)}
            ${createInfoLine('📊', source.situacao)}
            <div class="source-summary">${escapeHtml(source.resumo || 'Sem resumo.')}</div>
            <span class="source-score">Relevância: ${((source.score || 0) * 100).toFixed(0)}%</span>
        `;
        elements.sourcesList.appendChild(card);
    });

    elements.sourcesContainer.classList.add('active');
}

function showError(message) {
    addMessage(message, false, true);
}

// History Functions
function addToHistory(role, content) {
    state.history.push({ role, content });
    // Keep history from growing indefinitely
    if (state.history.length > CONFIG.HISTORY_LIMIT * 2) {
        state.history = state.history.slice(-CONFIG.HISTORY_LIMIT * 2);
    }
    saveHistory();
}

function saveHistory() {
    try {
        localStorage.setItem('chatcgu_history', JSON.stringify(state.history));
    } catch (error) {
        console.error('Failed to save history:', error);
    }
}

function loadHistory() {
    try {
        const data = localStorage.getItem('chatcgu_history');
        if (data) {
            state.history = JSON.parse(data);
            // Don't render old messages on load to start fresh
        }
    } catch (error) {
        console.error('Failed to load history:', error);
        state.history = [];
    }
}

// Error Handling
function getErrorMessage(error) {
    if (error.message.includes('timeout')) {
        return 'A requisição demorou muito para responder. Tente novamente.';
    }
    if (error.message.includes('HTTP error')) {
        return `Erro de comunicação com o servidor. (${error.message})`;
    }
    return 'Ocorreu um erro inesperado. Tente novamente mais tarde.';
}

// Main Chat Function
async function handleFormSubmit() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isLoading) {
        return;
    }

    state.isLoading = true;
    setControlsState(false);
    addMessage(message, true);
    addToHistory('user', message);
    elements.messageInput.value = '';

    // Show typing indicator after a short delay
    const typingTimeout = setTimeout(() => showTyping(), 500);

    try {
        const response = await sendMessageToAPI(message, state.history);

        if (response.answer) {
            addMessage(response.answer, false);
            addToHistory('assistant', response.answer);
        } else {
            showError('Desculpe, não consegui gerar uma resposta.');
        }

        renderSources(response.sources);

    } catch (error) {
        const errorMessage = getErrorMessage(error);
        showError(errorMessage);
        console.error('Chat error:', error);
    } finally {
        clearTimeout(typingTimeout);
        hideTyping();
        state.isLoading = false;
        setControlsState(true);
        elements.messageInput.focus();
    }
}

// Event Listeners
function setupEventListeners() {
    elements.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFormSubmit();
    });

    elements.sourcesToggle.addEventListener('click', () => {
        elements.sourcesContainer.classList.remove('active');
    });

    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const question = e.currentTarget.dataset.question;
            elements.messageInput.value = question;
            elements.messageInput.focus();
            handleFormSubmit(); // Automatically send the example question
        });
    });

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            handleFormSubmit();
        }
        if (e.key === 'Escape') {
            elements.sourcesContainer.classList.remove('active');
        }
    });
}

// Initialization
async function init() {
    loadHistory();
    await getStats();
    setupEventListeners();
    elements.messageInput.focus();
    console.log('Chat CGU initialized.');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);