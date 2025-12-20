// Global State
const state = {
    ws: null,
    currentAlert: null,
    chart: null,
    dashboardData: null,
    isInitialized: false
};

async function initializeSystem() {
    if (state.isInitialized) {
        return;
    }
    
    showToast('Initializing Financial Alarm System...', 'info');
    
    try {
        const response = await fetch('/api/initialize', {
            method: 'POST'
        });
        
        if (response.ok) {
            state.isInitialized = true;
            showToast('System initialized successfully!', 'success');
            await loadDashboard();
            connectWebSocket();
            initParticles();
        }
    } catch (error) {
        console.error('Initialization error:', error);
        showToast('Failed to initialize system', 'error');
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('lastSync').textContent = formatTime(new Date());
    };
    
    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
    
    state.ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWebSocket, 5000);
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function handleWebSocketMessage(message) {
    if (message.type === 'new_alert') {
        playAlertSound();
        showAlertNotification(message.alert);
        loadDashboard(); // Refresh dashboard
    }
}

async function loadDashboard() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        state.dashboardData = data;
        
        updateBalance(data);
        updateAlerts(data.alerts);
        updateTransactions(data.recent_transactions);
        updateChart(data.category_spending);
        updateStats(data);
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showToast('Failed to load dashboard data', 'error');
    }
}

async function syncData() {
    const syncBtn = event.target.closest('.btn-primary');
    syncBtn.disabled = true;
    syncBtn.innerHTML = '<span>⚡</span> SYNCING...';
    
    try {
        const response = await fetch('/api/sync', { method: 'POST' });
        const data = await response.json();
        
        showToast(`Synced ${data.transactions_synced} transactions, ${data.new_alerts} new alerts`, 'success');
        
        document.getElementById('lastSync').textContent = formatTime(new Date());
        
        await loadDashboard();
        
    } catch (error) {
        console.error('Sync failed:', error);
        showToast('Sync failed', 'error');
    } finally {
        syncBtn.disabled = false;
        syncBtn.innerHTML = '<span>⚡</span> SYNC NOW';
    }
}

async function loadAllAlerts() {
    try {
        const response = await fetch('/api/alerts');
        return await response.json();
    } catch (error) {
        console.error('Failed to load alerts:', error);
        return [];
    }
}

async function updateAlertStatus(alertId, status) {
    try {
        await fetch(`/api/alerts/${alertId}/status?status=${status}`, {
            method: 'PUT'
        });
        return true;
    } catch (error) {
        console.error('Failed to update alert:', error);
        return false;
    }
}

async function loadRules() {
    try {
        const response = await fetch('/api/rules');
        const rules = await response.json();
        updateRules(rules);
    } catch (error) {
        console.error('Failed to load rules:', error);
    }
}

async function toggleRule(ruleId, enabled) {
    try {
        const rule = state.dashboardData?.rules?.find(r => r.id === ruleId);
        if (!rule) return;
        
        await fetch(`/api/rules/${ruleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rule_type: rule.rule_type,
                enabled: enabled,
                params: rule.params
            })
        });
        
        showToast(`Rule ${enabled ? 'enabled' : 'disabled'}`, 'info');
        await loadRules();
        
    } catch (error) {
        console.error('Failed to toggle rule:', error);
        showToast('Failed to update rule', 'error');
    }
}

function updateBalance(data) {
    const balanceEl = document.getElementById('balance');
    const statusEl = document.getElementById('balanceStatus');
    const barEl = document.getElementById('balanceBar');
    
    // Animate balance
    animateValue(balanceEl, 0, data.balance, 1500, (val) => val.toLocaleString('en-ZA', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }));
    
    // Update status
    if (data.balance < 500) {
        statusEl.textContent = '⚠️ Balance critically low';
        statusEl.className = 'balance-status text-danger';
    } else if (data.balance < 2000) {
        statusEl.textContent = '⚡ Monitor spending carefully';
        statusEl.className = 'balance-status text-warning';
    } else {
        statusEl.textContent = '✓ Balance healthy';
        statusEl.className = 'balance-status text-success';
    }
    
    // Update progress bar
    const maxBalance = 20000;
    const percentage = Math.min((data.balance / maxBalance) * 100, 100);
    barEl.style.width = `${percentage}%`;
}

function updateAlerts(alerts) {
    const container = document.getElementById('alertsList');
    const badge = document.getElementById('alertBadge');
    
    badge.textContent = alerts.length;
    
    if (alerts.length === 0) {
        container.innerHTML = `
            <div class="loading-state">
                <div style="font-size: 48px; margin-bottom: 10px;">✓</div>
                <p>No active alerts - All systems normal</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item severity-${alert.severity}" 
             onclick="showAlertDetail(${alert.id})"
             data-alert-id="${alert.id}">
            <div class="alert-header">
                <div class="alert-title">${alert.title}</div>
                <span class="severity-badge ${alert.severity}">${alert.severity}</span>
            </div>
            <div class="alert-body">${alert.body}</div>
            <div class="alert-footer">
                <span class="alert-time">${formatTimeAgo(new Date(alert.created_at))}</span>
                <div class="alert-actions">
                    <button class="alert-action-btn" onclick="markAsRead(${alert.id}, event)">
                        Mark Read
                    </button>
                    <button class="alert-action-btn" onclick="dismissAlert(${alert.id}, event)">
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function updateTransactions(transactions) {
    const container = document.getElementById('transactionList');
    
    if (transactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💳</div>
                <div class="empty-state-text">No transactions yet</div>
            </div>
        `;
        return;
    }
    
    // Category icon mapping
    const categoryIcons = {
        'groceries': '🛒',
        'food': '🍔',
        'restaurants': '🍽️',
        'entertainment': '🎬',
        'transport': '🚗',
        'utilities': '💡',
        'shopping': '🛍️',
        'health': '⚕️',
        'education': '📚',
        'travel': '✈️',
        'telecommunications': '📱',
        'fast food': '🍕',
        'salary': '💰',
        'income': '💵',
        'default': '💳'
    };
    
    container.innerHTML = transactions.map(txn => {
        const isDebit = txn.amount < 0;
        const amountClass = isDebit ? 'debit' : 'credit';
        const sign = isDebit ? '-' : '+';
        
        // Get icon for category
        const categoryLower = (txn.category || 'default').toLowerCase();
        const icon = categoryIcons[categoryLower] || categoryIcons['default'];
        
        // Truncate long merchant names
        const maxLength = 25;
        const displayMerchant = txn.merchant.length > maxLength 
            ? txn.merchant.substring(0, maxLength) + '...'
            : txn.merchant;
        
        return `
            <div class="transaction-item" title="${txn.merchant}">
                <div class="transaction-icon">${icon}</div>
                <div class="transaction-info">
                    <div class="transaction-merchant">${displayMerchant}</div>
                    <div class="transaction-meta">
                        <span class="transaction-category">${txn.category}</span>
                        <span class="transaction-date">${formatDate(new Date(txn.date))}</span>
                    </div>
                </div>
                <div class="transaction-amount ${amountClass}">
                    ${sign}R ${Math.abs(txn.amount).toFixed(2)}
                </div>
            </div>
        `;
    }).join('');
}

function updateChart(categorySpending) {
    const ctx = document.getElementById('spendingChart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (state.chart) {
        state.chart.destroy();
    }
    
    // Prepare data
    const sortedCategories = Object.entries(categorySpending)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8); // Top 8 categories
    
    const labels = sortedCategories.map(([cat]) => cat);
    const data = sortedCategories.map(([, amount]) => amount);
    
    // Generate colors
    const colors = generateNeonColors(labels.length);
    
    // Create chart
    state.chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.backgrounds,
                borderColor: colors.borders,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(19, 24, 58, 0.95)',
                    titleColor: '#00f3ff',
                    bodyColor: '#ffffff',
                    borderColor: '#00f3ff',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `R ${value.toFixed(2)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    // Update legend
    updateChartLegend(labels, data, colors.backgrounds);
}

function updateChartLegend(labels, data, colors) {
    const legend = document.getElementById('chartLegend');
    const total = data.reduce((a, b) => a + b, 0);
    
    legend.innerHTML = labels.map((label, i) => {
        const percentage = ((data[i] / total) * 100).toFixed(1);
        return `
            <div class="legend-item">
                <div class="legend-color" style="background: ${colors[i]}"></div>
                <span class="legend-label">${label}:</span>
                <span class="legend-value">R ${data[i].toFixed(2)} (${percentage}%)</span>
            </div>
        `;
    }).join('');
}

function updateStats(data) {
    // Month spend
    const monthSpend = Object.values(data.category_spending || {})
        .reduce((sum, val) => sum + val, 0);
    document.getElementById('monthSpend').textContent = `R ${monthSpend.toFixed(0)}`;
    
    // Active rules (we'll load this separately)
    loadRules();
    
    // Critical alerts
    const criticalCount = data.alerts.filter(a => a.severity === 'CRITICAL').length;
    document.getElementById('criticalAlerts').textContent = criticalCount;
}

function updateRules(rules) {
    const container = document.getElementById('rulesList');
    document.getElementById('activeRules').textContent = rules.filter(r => r.enabled).length;
    
    if (rules.length === 0) {
        container.innerHTML = `
            <div class="loading-state">
                <p>No rules configured</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = rules.map(rule => {
        const params = formatRuleParams(rule.rule_type, rule.params);
        return `
            <div class="rule-item">
                <div class="rule-header">
                    <span class="rule-name">${formatRuleName(rule.rule_type)}</span>
                    <label class="rule-toggle">
                        <input type="checkbox" 
                               ${rule.enabled ? 'checked' : ''}
                               onchange="toggleRule(${rule.id}, this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="rule-params">${params}</div>
            </div>
        `;
    }).join('');
}

function showAlertDetail(alertId) {
    const alert = state.dashboardData.alerts.find(a => a.id === alertId);
    if (!alert) return;
    
    state.currentAlert = alertId;
    
    const modal = document.getElementById('alertModal');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalBody');
    
    title.textContent = alert.title;
    body.innerHTML = `
        <div style="margin-bottom: 20px;">
            <span class="severity-badge ${alert.severity}">${alert.severity}</span>
        </div>
        <div style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 20px;">
            ${alert.body}
        </div>
        <div style="background: var(--bg-tertiary); padding: 15px; border-radius: 8px;">
            <div style="color: var(--text-dim); font-size: 12px; margin-bottom: 8px;">ALERT DATA:</div>
            <pre style="color: var(--text-secondary); font-size: 12px; overflow-x: auto;">${JSON.stringify(alert.data, null, 2)}</pre>
        </div>
        <div style="margin-top: 15px; font-size: 12px; color: var(--text-dim);">
            Triggered: ${formatDate(new Date(alert.created_at))}
        </div>
    `;
    
    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('alertModal');
    modal.classList.remove('active');
    state.currentAlert = null;
}

async function markAsRead(alertId, event) {
    event.stopPropagation();
    
    const success = await updateAlertStatus(alertId, 'READ');
    if (success) {
        showToast('Alert marked as read', 'info');
        await loadDashboard();
    }
}

async function dismissAlert(alertId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    const id = alertId || state.currentAlert;
    if (!id) return;
    
    const success = await updateAlertStatus(id, 'DISMISSED');
    if (success) {
        showToast('Alert dismissed', 'info');
        closeModal();
        await loadDashboard();
    }
}

async function showAllAlerts() {
    const alerts = await loadAllAlerts();
    // Could open a modal or navigate to alerts page
    showToast(`Total alerts: ${alerts.length}`, 'info');
}

function showAlerts() {
    // Scroll to alerts panel
    document.getElementById('alertsPanel').scrollIntoView({ behavior: 'smooth' });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.4s ease-out';
        setTimeout(() => {
            container.removeChild(toast);
        }, 400);
    }, 3000);
}

function showAlertNotification(alert) {
    showToast(`${alert.title}`, alert.severity.toLowerCase());
}

function playAlertSound() {
    const audio = document.getElementById('alertSound');
    audio.play().catch(e => console.log('Audio play failed:', e));
}

function initParticles() {
    const canvas = document.getElementById('particles');
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    const particleCount = 50;
    
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.radius = Math.random() * 2;
            this.opacity = Math.random() * 0.5;
        }
        
        update() {
            this.x += this.vx;
            this.y += this.vy;
            
            if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
            if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
        }
        
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 243, 255, ${this.opacity})`;
            ctx.fill();
        }
    }
    
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        
        // Draw connections
        particles.forEach((p1, i) => {
            particles.slice(i + 1).forEach(p2 => {
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 150) {
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(0, 243, 255, ${0.2 * (1 - distance / 150)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            });
        });
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

function animateValue(element, start, end, duration, formatter) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = start + (end - start) * easeOutQuart;
        
        element.textContent = formatter ? formatter(current) : current.toFixed(2);
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function formatTime(date) {
    return date.toLocaleTimeString('en-ZA', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDate(date) {
    return date.toLocaleString('en-ZA', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function formatRuleName(ruleType) {
    const names = {
        'LOW_BALANCE': '💰 Low Balance Alert',
        'CATEGORY_LIMIT': '📊 Category Spending Limit',
        'SPENDING_SPIKE': '📈 Spending Spike Detection',
        'NEW_SUBSCRIPTION': '🔄 New Subscription Detection',
        'LARGE_TRANSACTION': '🚨 Large Transaction Alert',
        'PAYDAY_COUNTDOWN': '⏰ Payday Countdown'
    };
    return names[ruleType] || ruleType;
}

function formatRuleParams(ruleType, params) {
    switch (ruleType) {
        case 'LOW_BALANCE':
            return `Trigger when balance falls below R ${params.threshold || 500}`;
        case 'CATEGORY_LIMIT':
            return `Limit: R ${params.limit || 1500} for ${params.category || 'category'}`;
        case 'LARGE_TRANSACTION':
            return `Alert on transactions over R ${params.threshold || 2000}`;
        default:
            return JSON.stringify(params);
    }
}

function generateNeonColors(count) {
    const baseColors = [
        { bg: 'rgba(0, 243, 255, 0.7)', border: '#00f3ff' },
        { bg: 'rgba(255, 0, 110, 0.7)', border: '#ff006e' },
        { bg: 'rgba(57, 255, 20, 0.7)', border: '#39ff14' },
        { bg: 'rgba(191, 0, 255, 0.7)', border: '#bf00ff' },
        { bg: 'rgba(0, 102, 255, 0.7)', border: '#0066ff' },
        { bg: 'rgba(255, 170, 0, 0.7)', border: '#ffaa00' },
        { bg: 'rgba(255, 20, 147, 0.7)', border: '#ff1493' },
        { bg: 'rgba(0, 255, 255, 0.7)', border: '#00ffff' }
    ];
    
    const backgrounds = [];
    const borders = [];
    
    for (let i = 0; i < count; i++) {
        const color = baseColors[i % baseColors.length];
        backgrounds.push(color.bg);
        borders.push(color.border);
    }
    
    return { backgrounds, borders };
}

document.addEventListener('DOMContentLoaded', () => {
    initializeSystem();
    
    // Close modal on outside click
    document.getElementById('alertModal').addEventListener('click', (e) => {
        if (e.target.id === 'alertModal') {
            closeModal();
        }
    });
    
    // Auto-sync every 5 minutes
    setInterval(() => {
        if (state.isInitialized) {
            console.log('Auto-syncing...');
            // We can add a silent sync here if needed
        }
    }, 300000); // 5 minutes
});

window.loadDashboard = loadDashboard;
window.syncData = syncData;
window.showAlerts = showAlerts;
window.showAllAlerts = showAllAlerts;
window.showAlertDetail = showAlertDetail;
window.closeModal = closeModal;
window.dismissAlert = dismissAlert;
window.markAsRead = markAsRead;

window.toggleRule = toggleRule;
