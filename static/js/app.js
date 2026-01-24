/**
 * Web Backup Manager - Frontend JavaScript
 */

let T = {}; // Translations object

// Initial load
document.addEventListener('DOMContentLoaded', async () => {
    await loadTranslations();
});

async function loadTranslations() {
    try {
        const response = await fetch('/api/translations');
        T = await response.json();
    } catch (error) {
        console.error('Failed to load translations', error);
    }
}

// Get text
function t(key, replacements = {}) {
    let text = T[key] || key;
    for (const [k, v] of Object.entries(replacements)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}

// Toast notification system
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Format file size
function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('tr-TR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// API helper
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API error');
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Mobile menu toggle
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('open');
}

// Confirmation dialog helper
function showConfirmDialog(title, message, onConfirm) {
    const modal = document.getElementById('confirm-modal');
    if (!modal) return;

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    document.getElementById('modal-confirm-btn').onclick = () => {
        onConfirm();
        closeModal();
    };
    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Close modal on outside click
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});

// Close modal on ESC key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// Auto-refresh data every 30 seconds (if on dashboard)
let autoRefreshInterval = null;

function startAutoRefresh(callback, interval = 30000) {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(callback, interval);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', stopAutoRefresh);

// Debounce function for form inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Validate form field
function validateField(input, rules = {}) {
    const value = input.value.trim();
    let isValid = true;
    let message = '';

    if (rules.required && !value) {
        isValid = false;
        message = 'Bu alan zorunludur';
    } else if (rules.minLength && value.length < rules.minLength) {
        isValid = false;
        message = `En az ${rules.minLength} karakter olmalı`;
    } else if (rules.pattern && !rules.pattern.test(value)) {
        isValid = false;
        message = rules.patternMessage || 'Geçersiz format';
    }

    // Update UI
    if (isValid) {
        input.classList.remove('invalid');
        input.classList.add('valid');
    } else {
        input.classList.add('invalid');
        input.classList.remove('valid');
    }

    return { isValid, message };
}

// Copy to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Panoya kopyalandı', 'success');
    } catch (err) {
        showToast('Kopyalama başarısız', 'error');
    }
}

// Loading state helper
function setLoading(element, isLoading) {
    if (isLoading) {
        element.classList.add('loading');
        element.disabled = true;
    } else {
        element.classList.remove('loading');
        element.disabled = false;
    }
}

// Export functions for global use
window.showToast = showToast;
window.formatSize = formatSize;
window.formatDate = formatDate;
window.apiCall = apiCall;
window.toggleSidebar = toggleSidebar;
window.closeModal = closeModal;
window.showConfirmDialog = showConfirmDialog;
window.copyToClipboard = copyToClipboard;
window.setLoading = setLoading;
