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
    
    // Start polling every 10 seconds for more responsiveness
    startPolling();
    
    // Add refresh button click handler
    refreshBtn.addEventListener('click', fetchEvents);
    
    // Add test event buttons
    addTestEventButtons();
});

function setWebhookUrl() {
    const protocol = window.location.protocol;
    const host = window.location.host;
    const webhookUrl = `${protocol}//${host}/webhook/receiver`;
    webhookUrlEl.textContent = webhookUrl;
}

function addTestEventButtons() {
    // Add test buttons to the header for easy testing
    const headerContent = document.querySelector('.header-content');
    const testButtonsContainer = document.createElement('div');
    testButtonsContainer.className = 'test-buttons';
    testButtonsContainer.innerHTML = `
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button onclick="createTestEvent('push')" class="test-btn">Test Push</button>
            <button onclick="createTestEvent('pull_request')" class="test-btn">Test PR</button>
            <button onclick="createTestEvent('merge')" class="test-btn">Test Merge</button>
        </div>
    `;
    
    // Add styles for test buttons
    if (!document.querySelector('#test-button-styles')) {
        const style = document.createElement('style');
        style.id = 'test-button-styles';
        style.textContent = `
            .test-btn {
                padding: 8px 16px;
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            .test-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
            }
            @media (max-width: 768px) {
                .test-buttons {
                    width: 100%;
                    justify-content: center;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    headerContent.appendChild(testButtonsContainer);
}

async function createTestEvent(type) {
    try {
        const response = await fetch('/webhook/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: type })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccessMessage(`Test ${type} event created successfully!`);
            // Fetch events immediately to show the new test event
            setTimeout(fetchEvents, 500);
        } else {
            showErrorMessage(`Failed to create test event: ${data.error}`);
        }
    } catch (error) {
        console.error('Error creating test event:', error);
        showErrorMessage('Failed to create test event');
    }
}

function startPolling() {
    // Clear any existing interval
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    // Start new polling interval (10 seconds for better responsiveness)
    pollInterval = setInterval(fetchEvents, 10000);
    console.log('Started polling every 10 seconds');
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
            
            // Check for new events
            if (data.events.length > 0 && data.events[0].id !== lastEventId) {
                lastEventId = data.events[0].id;
                if (lastEventCount > 0) { // Don't show notification on first load
                    showSuccessMessage('New event received!');
                }
            }
            
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
    
    // Display events with enhanced information
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
                <span class="event-time">
                    <i class="fas fa-clock"></i>
                    ${formatTimestamp(event.timestamp)}
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
    
    // Auto-remove after 5 seconds for errors, 3 seconds for success
    const autoRemoveTime = type === 'error' ? 5000 : 3000;
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, autoRemoveTime);
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

// Enhanced debug function to check webhook connectivity
async function debugWebhook() {
    try {
        console.log('Testing webhook connectivity...');
        const response = await fetch('/webhook/debug');
        const data = await response.json();
        
        console.log('Recent webhook events:', data);
        
        if (data.success && data.events.length > 0) {
            console.log('✅ Webhook is receiving events');
            showSuccessMessage('Webhook is working correctly!');
        } else {
            console.log('⚠️ No recent webhook events found');
            showErrorMessage('No recent webhook events found. Check your GitHub webhook configuration.');
        }
        
    } catch (error) {
        console.error('Debug webhook failed:', error);
        showErrorMessage('Failed to debug webhook connectivity');
    }
}

// Add debug webhook button to console
console.log('🔧 Debug commands available:');
console.log('- debugWebhook(): Test webhook connectivity');
console.log('- createTestEvent("push"): Create test push event');
console.log('- createTestEvent("pull_request"): Create test PR event');
console.log('- createTestEvent("merge"): Create test merge event');
console.log('- fetchEvents(): Manually fetch latest events');

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

// Add enhanced event meta styles
const eventMetaStyles = document.createElement('style');
eventMetaStyles.textContent = `
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
    
    @media (max-width: 768px) {
        .event-meta {
            flex-direction: column;
            gap: 8px;
        }
    }
`;
document.head.appendChild(eventMetaStyles);