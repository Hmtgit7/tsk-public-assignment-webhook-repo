// app/static/js/main.js

// Global variables
let isLoading = false;
let lastEventCount = 0;
let pollInterval;
let lastEventId = null;

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
    
    // Start polling every 10 seconds
    startPolling();
    
    // Add refresh button click handler
    refreshBtn.addEventListener('click', fetchEvents);
    
    // Update relative timestamps every 30 seconds
    setInterval(updateAllTimestamps, 30000);
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
    
    // Start new polling interval (10 seconds)
    pollInterval = setInterval(fetchEvents, 10000);
    console.log('Started polling every 10 seconds');
}

async function fetchEvents() {
    if (isLoading) {
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
            
            // Check for new events
            if (data.events.length > 0 && data.events[0].id !== lastEventId) {
                lastEventId = data.events[0].id;
                if (lastEventCount > 0) {
                    showSuccessMessage('New activity detected!');
                }
            }
            
        } else {
            throw new Error(data.error || 'Failed to fetch events');
        }
        
    } catch (error) {
        console.error('Error fetching events:', error);
        updateStatus('offline', 'Connection Error');
        showErrorMessage('Failed to fetch events. Retrying...');
    } finally {
        isLoading = false;
        updateLoadingState(false);
        updateLastUpdateTime();
    }
}

function updateLoadingState(loading) {
    if (loading && !eventsListEl.querySelector('.event-item')) {
        // Only show loading if there are no events displayed
        loadingEl.style.display = 'block';
        eventsListEl.style.display = 'none';
        noEventsEl.style.display = 'none';
    } else {
        loadingEl.style.display = 'none';
    }
    
    refreshBtn.disabled = loading;
    refreshBtn.innerHTML = loading ? 
        '<i class="fas fa-spinner fa-spin"></i> Refreshing' : 
        '<i class="fas fa-sync-alt"></i> Refresh';
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
        const isNew = hasNewEvents && index === 0;
        const eventElement = createEventElement(event, isNew);
        eventsListEl.appendChild(eventElement);
    });
    
    lastEventCount = events.length;
}

function createEventElement(event, isNew = false) {
    const eventItem = document.createElement('div');
    eventItem.className = `event-item ${isNew ? 'new' : ''}`;
    eventItem.setAttribute('data-event-id', event.id);
    eventItem.setAttribute('data-timestamp', event.timestamp);
    
    const actionType = event.action.toLowerCase().replace('_', '-');
    const iconClass = getIconClass(event.action);
    const badgeClass = actionType;
    
    // Parse additional details from the message
    const eventDetails = parseEventMessage(event.message);
    
    eventItem.innerHTML = `
        <div class="event-icon ${actionType}">
            <i class="${iconClass}"></i>
        </div>
        <div class="event-content">
            <div class="event-message">${escapeHtml(event.message)}</div>
            <div class="event-meta">
                <span class="event-time" data-timestamp="${event.timestamp}">
                    <i class="fas fa-clock"></i>
                    <span class="time-text">${formatTimestamp(event.timestamp)}</span>
                </span>
                ${eventDetails.repository ? `
                    <span class="event-repo">
                        <i class="fab fa-github"></i>
                        ${escapeHtml(eventDetails.repository)}
                    </span>
                ` : ''}
                ${eventDetails.branches ? `
                    <span class="event-branches">
                        <i class="fas fa-code-branch"></i>
                        ${escapeHtml(eventDetails.branches)}
                    </span>
                ` : ''}
            </div>
        </div>
        <div class="event-badge ${badgeClass}">${event.action.replace('_', ' ')}</div>
    `;
    
    return eventItem;
}

function updateAllTimestamps() {
    // Update all timestamp elements to show current relative time
    const timeElements = document.querySelectorAll('.event-time[data-timestamp]');
    timeElements.forEach(timeEl => {
        const timestamp = timeEl.getAttribute('data-timestamp');
        const timeTextEl = timeEl.querySelector('.time-text');
        if (timeTextEl) {
            timeTextEl.textContent = formatTimestamp(timestamp);
        }
    });
}

function parseEventMessage(message) {
    const details = {};
    
    // Extract repository name
    const repoMatch = message.match(/in "([^"]+)"/);
    if (repoMatch) {
        details.repository = repoMatch[1];
    }
    
    // Extract branch information
    const pushMatch = message.match(/pushed to "([^"]+)"/);
    const prMatch = message.match(/from "([^"]+)" to "([^"]+)"/);
    const mergeMatch = message.match(/branch "([^"]+)" to "([^"]+)"/);
    
    if (pushMatch) {
        details.branches = pushMatch[1];
    } else if (prMatch) {
        details.branches = `${prMatch[1]} → ${prMatch[2]}`;
    } else if (mergeMatch) {
        details.branches = `${mergeMatch[1]} → ${mergeMatch[2]}`;
    }
    
    return details;
}

function getIconClass(action) {
    switch (action) {
        case 'PUSH':
            return 'fas fa-upload';
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
            return 'just now';
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        } else {
            // For older events, show full date
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
        totalEventsEl.style.color = '#10b981';
        setTimeout(() => {
            totalEventsEl.style.transform = 'scale(1)';
            totalEventsEl.style.color = '';
        }, 300);
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
    showNotification(message, 'error');
}

function showSuccessMessage(message) {
    showNotification(message, 'success');
}

function showNotification(message, type) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}-notification`;
    
    const colors = {
        success: { bg: '#d1fae5', border: '#a7f3d0', text: '#065f46', icon: 'fas fa-check-circle' },
        error: { bg: '#fee2e2', border: '#fecaca', text: '#991b1b', icon: 'fas fa-exclamation-triangle' }
    };
    
    const color = colors[type];
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="${color.icon}"></i>
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Add notification styles if not already present
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                border-radius: 8px;
                padding: 16px;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                animation: slideInRight 0.3s ease-out;
            }
            .success-notification {
                background: #d1fae5;
                border: 1px solid #a7f3d0;
            }
            .error-notification {
                background: #fee2e2;
                border: 1px solid #fecaca;
            }
            .notification-content {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .success-notification .notification-content {
                color: #065f46;
            }
            .error-notification .notification-content {
                color: #991b1b;
            }
            .notification-close {
                background: none;
                border: none;
                cursor: pointer;
                padding: 4px;
                margin-left: auto;
                opacity: 0.7;
                transition: opacity 0.2s ease;
            }
            .notification-close:hover {
                opacity: 1;
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    notification.style.background = color.bg;
    notification.style.borderColor = color.border;
    notification.style.color = color.text;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 4000);
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

// Handle page visibility change to optimize polling
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, reduce polling frequency
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = setInterval(fetchEvents, 60000); // 1 minute when hidden
        }
    } else {
        // Page is visible, resume normal polling
        fetchEvents(); // Immediate fetch
        startPolling(); // Resume normal polling
    }
});

// Handle online/offline events
window.addEventListener('online', function() {
    updateStatus('online', 'Connected');
    showSuccessMessage('Connection restored!');
    fetchEvents();
    startPolling();
});

window.addEventListener('offline', function() {
    updateStatus('offline', 'Offline');
    showErrorMessage('Connection lost. Will retry when back online.');
    if (pollInterval) {
        clearInterval(pollInterval);
    }
});

// Add enhanced event styles
const eventStyles = document.createElement('style');
eventStyles.textContent = `
    .event-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-top: 8px;
        font-size: 0.8rem;
        opacity: 0.8;
    }
    
    .event-meta span {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .event-meta i {
        opacity: 0.7;
    }
    
    .event-repo {
        color: #6366f1;
        font-weight: 500;
    }
    
    .event-branches {
        color: #059669;
        font-weight: 500;
    }
    
    .event-time {
        color: #6b7280;
    }
    
    .event-item.new {
        border-left-color: #10b981 !important;
        background: linear-gradient(90deg, #ecfdf5 0%, #f8fafc 100%) !important;
        animation: newEventGlow 2s ease-out;
    }
    
    @keyframes newEventGlow {
        0% {
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
            transform: translateX(-5px);
        }
        50% {
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.2);
        }
        100% {
            box-shadow: none;
            transform: translateX(0);
        }
    }
    
    @media (max-width: 768px) {
        .event-meta {
            flex-direction: column;
            gap: 8px;
        }
    }
`;
document.head.appendChild(eventStyles);

console.log('✅ GitHub Webhook Monitor loaded successfully!');