// Global variables
let isLoading = false;
let lastEventCount = 0;
let pollInterval;

// DOM elements
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const totalEventsEl = document.getElementById('totalEvents');
const lastUpdateEl = document.getElementById('lastUpdate');
const refreshBtn = document.getElementById('refreshBtn');
const loadingEl = document.getElementById('loading');
const noEventsEl = document.getElementById('noEvents');
const eventsListEl = document.getElementById('eventsList');
const webhookUrlEl = document.getElementById('webhookUrl');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('GitHub Webhook Monitor initialized');
    
    // Set webhook URL based on current location
    setWebhookUrl();
    
    // Initial fetch
    fetchEvents();
    
    // Start polling every 15 seconds
    startPolling();
    
    // Add refresh button click handler
    refreshBtn.addEventListener('click', fetchEvents);
});

function setWebhookUrl() {
    const protocol = window.location.protocol;
    const host = window.location.host;
    const webhookUrl = `${protocol}//${host}/webhook/receiver`;
    webhookUrlEl.textContent = webhookUrl;
}

function startPolling() {
    // Clear any existing interval
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    // Start new polling interval (15 seconds)
    pollInterval = setInterval(fetchEvents, 15000);
    console.log('Started polling every 15 seconds');
}

async function fetchEvents() {
    if (isLoading) {
        console.log('Already fetching events, skipping...');
        return;
    }
    
    isLoading = true;
    updateLoadingState(true);
    
    try {
        const response = await fetch('/api/events');
        const data = await response.json();
        
        if (data.success) {
            displayEvents(data.events);
            updateStats(data.count);
            updateStatus('online', 'Connected');
            console.log(`Fetched ${data.events.length} events`);
        } else {
            throw new Error(data.error || 'Failed to fetch events');
        }
        
    } catch (error) {
        console.error('Error fetching events:', error);
        updateStatus('offline', 'Connection Error');
        showErrorMessage('Failed to fetch events. Please check your connection.');
    } finally {
        isLoading = false;
        updateLoadingState(false);
        updateLastUpdateTime();
    }
}

function updateLoadingState(loading) {
    if (loading) {
        loadingEl.style.display = 'block';
        eventsListEl.style.display = 'none';
        noEventsEl.style.display = 'none';
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing';
    } else {
        loadingEl.style.display = 'none';
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
    }
}

function displayEvents(events) {
    if (!events || events.length === 0) {
        eventsListEl.style.display = 'none';
        noEventsEl.style.display = 'block';
        return;
    }
    
    noEventsEl.style.display = 'none';
    eventsListEl.style.display = 'block';
    
    // Check for new events
    const hasNewEvents = events.length > lastEventCount;
    
    // Clear existing events
    eventsListEl.innerHTML = '';
    
    // Display events
    events.forEach((event, index) => {
        const eventElement = createEventElement(event, hasNewEvents && index === 0);
        eventsListEl.appendChild(eventElement);
    });
    
    lastEventCount = events.length;
}

function createEventElement(event, isNew = false) {
    const eventItem = document.createElement('div');
    eventItem.className = `event-item ${isNew ? 'new' : ''}`;
    eventItem.setAttribute('data-event-id', event.id);
    
    const actionType = event.action.toLowerCase().replace('_', '-');
    const iconClass = getIconClass(event.action);
    const badgeClass = actionType;
    
    eventItem.innerHTML = `
        <div class="event-icon ${actionType}">
            <i class="${iconClass}"></i>
        </div>
        <div class="event-content">
            <div class="event-message">${escapeHtml(event.message)}</div>
            <div class="event-time">${formatTimestamp(event.timestamp)}</div>
        </div>
        <div class="event-badge ${badgeClass}">${event.action.replace('_', ' ')}</div>
    `;
    
    return eventItem;
}

function getIconClass(action) {
    switch (action) {
        case 'PUSH':
            return 'fas fa-arrow-up';
        case 'PULL_REQUEST':
            return 'fas fa-code-branch';
        case 'MERGE':
            return 'fas fa-code-merge';
        default:
            return 'fas fa-code';
    }
}

function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) {
            return 'Just now';
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    } catch (error) {
        console.error('Error formatting timestamp:', error);
        return 'Unknown time';
    }
}

function updateStats(count) {
    totalEventsEl.textContent = count;
    
    // Animate the counter if it's increased
    if (count > lastEventCount) {
        totalEventsEl.style.transform = 'scale(1.1)';
        setTimeout(() => {
            totalEventsEl.style.transform = 'scale(1)';
        }, 200);
    }
}

function updateStatus(status, message) {
    statusDot.className = `status-dot ${status === 'offline' ? 'offline' : ''}`;
    statusText.textContent = message;
}

function updateLastUpdateTime() {
    const now = new Date();
    lastUpdateEl.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function showErrorMessage(message) {
    // Create error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-notification';
    errorDiv.innerHTML = `
        <div class="error-content">
            <i class="fas fa-exclamation-triangle"></i>
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="error-close">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Add error styles if not already present
    if (!document.querySelector('#error-styles')) {
        const style = document.createElement('style');
        style.id = 'error-styles';
        style.textContent = `
            .error-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #fee2e2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 16px;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                animation: slideInRight 0.3s ease-out;
            }
            .error-content {
                display: flex;
                align-items: center;
                gap: 12px;
                color: #991b1b;
            }
            .error-close {
                background: none;
                border: none;
                color: #991b1b;
                cursor: pointer;
                padding: 4px;
                margin-left: auto;
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(errorDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentElement) {
            errorDiv.remove();
        }
    }, 5000);
}

function copyWebhookUrl() {
    const url = webhookUrlEl.textContent;
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
            showSuccessMessage('Webhook URL copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy URL:', err);
            fallbackCopyTextToClipboard(url);
        });
    } else {
        fallbackCopyTextToClipboard(url);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showSuccessMessage('Webhook URL copied to clipboard!');
    } catch (err) {
        console.error('Fallback: Unable to copy', err);
        showErrorMessage('Failed to copy URL to clipboard');
    }
    
    document.body.removeChild(textArea);
}

function showSuccessMessage(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-notification';
    successDiv.innerHTML = `
        <div class="success-content">
            <i class="fas fa-check-circle"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
    
    // Add success styles if not already present
    if (!document.querySelector('#success-styles')) {
        const style = document.createElement('style');
        style.id = 'success-styles';
        style.textContent = `
            .success-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #d1fae5;
                border: 1px solid #a7f3d0;
                border-radius: 8px;
                padding: 16px;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                animation: slideInRight 0.3s ease-out;
            }
            .success-content {
                display: flex;
                align-items: center;
                gap: 12px;
                color: #065f46;
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(successDiv);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (successDiv.parentElement) {
            successDiv.remove();
        }
    }, 3000);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Handle page visibility change to pause/resume polling
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, stop polling to save resources
        if (pollInterval) {
            clearInterval(pollInterval);
            console.log('Page hidden, stopped polling');
        }
    } else {
        // Page is visible, resume polling
        console.log('Page visible, resuming polling');
        fetchEvents(); // Immediate fetch
        startPolling(); // Resume regular polling
    }
});

// Handle online/offline events
window.addEventListener('online', function() {
    console.log('Connection restored');
    updateStatus('online', 'Connected');
    fetchEvents();
    startPolling();
});

window.addEventListener('offline', function() {
    console.log('Connection lost');
    updateStatus('offline', 'Offline');
    if (pollInterval) {
        clearInterval(pollInterval);
    }
});