// Use relative URL to avoid CORS issues
const API_BASE = window.location.origin || 'http://localhost:8000';

// Notification system (must be defined early)
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Tab management
function showTab(tabName, element) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const tabContent = document.getElementById(tabName);
    if (tabContent) {
        tabContent.classList.add('active');
    }
    
    // Activate button
    if (element) {
        element.classList.add('active');
    } else {
        // Find button by text content
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.textContent.includes(tabName === 'analysis' ? 'تحليل' : 
                                         tabName === 'policies' ? 'السياسات' :
                                         tabName === 'alerts' ? 'التنبيهات' : 'المراقبة')) {
                btn.classList.add('active');
            }
        });
    }
}

// Analysis functions
async function analyzeText() {
    console.log('analyzeText function called');
    
    try {
        const textInput = document.getElementById('textInput');
        const applyPoliciesCheck = document.getElementById('applyPolicies');
        const analyzeBtn = document.querySelector('#analysis .btn-primary');
        const resultBox = document.getElementById('analysisResult');
        
        if (!textInput) {
            throw new Error('عنصر textInput غير موجود');
        }
        if (!applyPoliciesCheck) {
            throw new Error('عنصر applyPolicies غير موجود');
        }
        if (!analyzeBtn) {
            throw new Error('زر التحليل غير موجود');
        }
        
        const text = textInput.value.trim();
        const applyPolicies = applyPoliciesCheck.checked;
        
        if (!text) {
            showNotification('Please enter text to analyze', 'warning');
            return;
        }
        
        // Show loading state
        const originalText = analyzeBtn.textContent;
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analyzing...';
        analyzeBtn.style.opacity = '0.7';
        if (resultBox) {
            resultBox.style.display = 'none';
        }
        
        console.log('Sending request to API...');
        const response = await fetch('/api/analyze/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                apply_policies: applyPolicies
            })
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (resultBox) {
            displayAnalysisResult(data);
        }
        showNotification('Analysis completed successfully', 'success');
    } catch (error) {
        console.error('Error in analyzeText:', error);
        const errorMessage = error.message || 'Unknown error occurred';
        showNotification('Error: ' + errorMessage, 'error');
        alert('Error: ' + errorMessage + '\n\nOpen Console (F12) for more details.');
    } finally {
        // Restore button
        const analyzeBtn = document.querySelector('#analysis .btn-primary');
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analyze';
            analyzeBtn.style.opacity = '1';
        }
    }
}

function displayAnalysisResult(result) {
    const resultBox = document.getElementById('analysisResult');
    const resultContent = document.getElementById('resultContent');
    
    if (!resultBox || !resultContent) return;
    
    let html = '';
    
    if (result.sensitive_data_detected) {
        html += `<div class="alert-banner alert-danger">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <span>Sensitive Data Detected!</span>
        </div>`;
        
        if (result.blocked) {
            html += `<div class="alert-banner alert-warning">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"></path>
                </svg>
                <span>Data Transfer Blocked</span>
            </div>`;
        }
        
        if (result.alert_created) {
            html += `<div class="badge badge-warning">Alert Created</div>`;
        }
        
        html += `<h4 style="margin-top: 24px; margin-bottom: 16px; color: var(--dark);">Detected Entities (${result.detected_entities.length})</h4>`;
        result.detected_entities.forEach(entity => {
            html += `
                <div class="entity-item">
                    <div class="entity-type">${entity.entity_type}</div>
                    <div class="entity-value">${entity.value}</div>
                    <div class="entity-score">Confidence: ${(entity.score * 100).toFixed(1)}%</div>
                </div>
            `;
        });
        
        if (result.actions_taken && result.actions_taken.length > 0) {
            html += `<div class="actions-taken"><strong>Actions Taken:</strong> `;
            result.actions_taken.forEach(action => {
                html += `<span class="action-tag">${action}</span>`;
            });
            html += `</div>`;
        }
    } else {
        html += `<div class="alert-banner alert-success">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>No sensitive data detected in the text</span>
        </div>`;
    }
    
    resultContent.innerHTML = html;
    resultBox.style.display = 'block';
}

// Policy functions
async function loadPolicies() {
    try {
        const response = await fetch('/api/policies/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const policies = await response.json();
        displayPolicies(policies);
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error loading policies', 'error');
        document.getElementById('policiesList').innerHTML = '<p style="color: var(--danger);">Error loading policies</p>';
    }
}

function displayPolicies(policies) {
    const list = document.getElementById('policiesList');
    
    if (policies.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>No policies found. Create your first policy to get started.</p></div>';
        return;
    }
    
    let html = '';
    policies.forEach(policy => {
        const statusBadge = policy.enabled 
            ? '<span class="badge badge-success">Enabled</span>'
            : '<span class="badge badge-danger">Disabled</span>';
        
        html += `
            <div class="policy-card">
                <h3>${policy.name} ${statusBadge}</h3>
                <p>${policy.description || 'No description provided'}</p>
                <div class="policy-details">
                    <div class="detail-item">
                        <strong>Action:</strong> <span class="badge badge-info">${policy.action}</span>
                    </div>
                    <div class="detail-item">
                        <strong>Severity:</strong> <span class="badge badge-${policy.severity === 'high' || policy.severity === 'critical' ? 'danger' : policy.severity === 'medium' ? 'warning' : 'info'}">${policy.severity}</span>
                    </div>
                    <div class="detail-item">
                        <strong>Entity Types:</strong> ${policy.entity_types.map(e => `<span class="badge badge-secondary">${e}</span>`).join(' ')}
                    </div>
                </div>
            </div>
        `;
    });
    
    list.innerHTML = html;
}

function showCreatePolicyForm() {
    const modal = document.getElementById('createPolicyForm');
    modal.style.display = 'flex';
    modal.classList.add('show');
    setTimeout(() => {
        document.getElementById('policyName').focus();
    }, 100);
}

function closeModal() {
    const modal = document.getElementById('createPolicyForm');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

async function createPolicy(event) {
    event.preventDefault();
    
    const policyName = document.getElementById('policyName').value.trim();
    const policyDescription = document.getElementById('policyDescription').value.trim();
    const selectedEntities = Array.from(document.getElementById('policyEntities').selectedOptions)
        .map(option => option.value);
    const policyAction = document.getElementById('policyAction').value;
    const policySeverity = document.getElementById('policySeverity').value;
    
    // Validation
    if (!policyName) {
        showNotification('Please enter a policy name', 'warning');
        return;
    }
    
    if (selectedEntities.length === 0) {
        showNotification('Please select at least one entity type', 'warning');
        return;
    }
    
    const formData = {
        name: policyName,
        description: policyDescription || null,
        entity_types: selectedEntities,
        action: policyAction,
        severity: policySeverity,
        enabled: true,
        apply_to_network: true,
        apply_to_devices: true,
        apply_to_storage: true,
        gdpr_compliant: false,
        hipaa_compliant: false
    };
    
    try {
        const response = await fetch('/api/policies/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification('Policy created successfully', 'success');
            closeModal();
            document.getElementById('policyForm').reset();
            loadPolicies();
        } else {
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to create policy';
            console.error('Policy creation error:', error);
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error creating policy: ' + error.message, 'error');
    }
}

// Alert functions
async function loadAlerts() {
    try {
        const response = await fetch('/api/alerts/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const alerts = await response.json();
        displayAlerts(alerts);
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error loading alerts', 'error');
        document.getElementById('alertsList').innerHTML = '<p style="color: var(--danger);">Error loading alerts</p>';
    }
}

function displayAlerts(alerts) {
    const list = document.getElementById('alertsList');
    
    if (alerts.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>No alerts found. All clear!</p></div>';
        return;
    }
    
    let html = '';
    alerts.forEach(alert => {
        const severityBadge = {
            'low': 'badge-info',
            'medium': 'badge-warning',
            'high': 'badge-danger',
            'critical': 'badge-danger'
        }[alert.severity] || 'badge-info';
        
        const statusBadge = {
            'pending': 'badge-warning',
            'acknowledged': 'badge-info',
            'resolved': 'badge-success',
            'false_positive': 'badge-secondary'
        }[alert.status] || 'badge-info';
        
        html += `
            <div class="alert-card">
                <h3>${alert.title} 
                    <span class="badge ${severityBadge}">${alert.severity}</span>
                    <span class="badge ${statusBadge}">${alert.status}</span>
                </h3>
                <p>${alert.description || ''}</p>
                ${alert.blocked ? '<div class="alert-banner alert-danger">Data Transfer Blocked</div>' : ''}
                <div class="alert-meta">
                    <span><strong>Source:</strong> ${alert.source_ip || 'Unknown'}</span>
                    <span><strong>User:</strong> ${alert.source_user || 'Unknown'}</span>
                    <span><strong>Time:</strong> ${new Date(alert.created_at).toLocaleString('en-US')}</span>
                </div>
            </div>
        `;
    });
    
    list.innerHTML = html;
}

// Monitoring functions
async function loadMonitoringData() {
    try {
        const [statusResponse, summaryResponse, emailStatsResponse] = await Promise.all([
            fetch('/api/monitoring/status'),
            fetch('/api/monitoring/reports/summary?days=7'),
            fetch('/api/monitoring/email/statistics?days=7')
        ]);
        
        const status = await statusResponse.json();
        const summary = await summaryResponse.json();
        const emailStats = emailStatsResponse.ok ? await emailStatsResponse.json() : null;
        
        displayMonitoringData(status, summary, emailStats);
        if (emailStats) {
            await loadEmailLogs();
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error loading monitoring data', 'error');
        document.getElementById('monitoringData').innerHTML = '<p style="color: var(--danger);">Error loading data</p>';
    }
}

function displayMonitoringData(status, summary, emailStats) {
    const container = document.getElementById('monitoringData');
    
    let html = '<div class="stats-grid">';
    html += `
        <div class="stat-card">
            <p>Total Logs</p>
            <h3>${summary.summary.total_logs}</h3>
        </div>
        <div class="stat-card">
            <p>Detected Entities</p>
            <h3>${summary.summary.total_detected_entities}</h3>
        </div>
        <div class="stat-card">
            <p>Total Alerts</p>
            <h3>${summary.summary.total_alerts}</h3>
        </div>
        <div class="stat-card">
            <p>Blocked Attempts</p>
            <h3>${summary.summary.blocked_attempts}</h3>
        </div>
    `;
    html += '</div>';
    
    html += '<h3 style="margin-top: 32px; margin-bottom: 16px; color: var(--dark);">Entity Type Distribution</h3>';
    html += '<div class="stats-grid">';
    for (const [entityType, count] of Object.entries(summary.entity_type_breakdown || {})) {
        html += `
            <div class="stat-card">
                <p>${entityType}</p>
                <h3>${count}</h3>
            </div>
        `;
    }
    html += '</div>';
    
    html += `<h3 style="margin-top: 32px; margin-bottom: 16px; color: var(--dark);">System Status</h3>`;
    html += `<div class="status-grid">`;
    html += `<div class="status-item"><strong>Presidio:</strong> <span class="badge badge-success">${status.presidio.status}</span></div>`;
    const mydlpStatus = status.mydlp.enabled 
        ? `${status.mydlp.status} (${status.mydlp.is_localhost ? 'Localhost Mode' : 'Network Mode'})`
        : 'Disabled';
    html += `<div class="status-item"><strong>MyDLP:</strong> <span class="badge ${status.mydlp.enabled ? 'badge-success' : 'badge-secondary'}">${mydlpStatus}</span></div>`;
    html += `</div>`;
    
    container.innerHTML = html;
    
    // Display email statistics if available
    if (emailStats) {
        displayEmailStats(emailStats);
    }
}

function displayEmailStats(stats) {
    const container = document.getElementById('emailStats');
    if (!container) return;
    
    let html = `
        <div class="stat-card stat-card-primary">
            <p>Emails Analyzed</p>
            <h3>${stats.total_emails_analyzed || 0}</h3>
        </div>
        <div class="stat-card stat-card-success">
            <p>Allowed Emails</p>
            <h3>${stats.allowed_emails || 0}</h3>
        </div>
        <div class="stat-card stat-card-danger">
            <p>Blocked Emails</p>
            <h3>${stats.blocked_emails || 0}</h3>
        </div>
        <div class="stat-card stat-card-warning">
            <p>Detected Entities</p>
            <h3>${stats.detected_entities || 0}</h3>
        </div>
    `;
    
    container.innerHTML = html;
}

async function loadEmailLogs() {
    try {
        const response = await fetch('/api/monitoring/email/logs?limit=10');
        if (!response.ok) return;
        
        const data = await response.json();
        displayEmailLogs(data.logs || []);
    } catch (error) {
        console.error('Error loading email logs:', error);
    }
}

function displayEmailLogs(logs) {
    const container = document.getElementById('emailLogs');
    if (!container) return;
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No email logs yet. Test email monitoring to see results.</p></div>';
        return;
    }
    
    let html = '<h4 style="margin-top: 24px; margin-bottom: 16px; color: var(--dark);">Recent Email Activity</h4>';
    html += '<div class="email-logs-list">';
    
    logs.forEach(log => {
        const emailData = log.email_data || {};
        const fromEmail = emailData.from || 'Unknown';
        const toEmails = Array.isArray(emailData.to) ? emailData.to.join(', ') : emailData.to || 'Unknown';
        const subject = emailData.subject || 'No subject';
        
        html += `
            <div class="email-log-item">
                <div class="email-log-header">
                    <div class="email-log-from">
                        <strong>From:</strong> ${fromEmail}
                    </div>
                    <div class="email-log-time">
                        ${new Date(log.created_at).toLocaleString('en-US')}
                    </div>
                </div>
                <div class="email-log-details">
                    <div><strong>To:</strong> ${toEmails}</div>
                    <div><strong>Subject:</strong> ${subject}</div>
                    ${emailData.has_attachments ? `<div><strong>Attachments:</strong> ${emailData.attachment_count || 0} file(s)</div>` : ''}
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function showEmailTestForm() {
    const modal = document.getElementById('emailTestModal');
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
        document.getElementById('emailFrom').focus();
    }, 10);
}

function closeEmailModal() {
    const modal = document.getElementById('emailTestModal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

async function testEmail(event) {
    event.preventDefault();
    
    const fromEmail = document.getElementById('emailFrom').value;
    const toEmails = document.getElementById('emailTo').value.split(',').map(e => e.trim()).filter(e => e);
    const subject = document.getElementById('emailSubject').value;
    const body = document.getElementById('emailBody').value;
    
    const emailData = {
        from: fromEmail,
        to: toEmails,
        subject: subject,
        body: body,
        source_ip: '127.0.0.1',
        source_user: fromEmail
    };
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analyzing...';
    
    try {
        const response = await fetch('/api/monitoring/email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(emailData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Display result
        let resultHtml = '<div class="email-result">';
        resultHtml += `<h4>Email Analysis Result</h4>`;
        
        if (result.sensitive_data_detected) {
            resultHtml += `<div class="alert-banner alert-danger">`;
            resultHtml += `<strong>⚠️ Sensitive Data Detected!</strong>`;
            resultHtml += `<p>${result.message}</p>`;
            resultHtml += `</div>`;
            
            if (result.blocked) {
                resultHtml += `<div class="alert-banner alert-danger">`;
                resultHtml += `<strong>🚫 Email Blocked</strong>`;
                resultHtml += `<p>The email was blocked due to policy violation.</p>`;
                resultHtml += `</div>`;
            }
            
            resultHtml += `<h5>Detected Entities (${result.detected_entities.length}):</h5>`;
            resultHtml += '<div class="entities-list">';
            result.detected_entities.forEach(entity => {
                resultHtml += `
                    <div class="entity-item">
                        <span class="entity-type">${entity.entity_type}</span>
                        <span class="entity-value">${entity.value}</span>
                        <span class="entity-score">${(entity.score * 100).toFixed(1)}% confidence</span>
                    </div>
                `;
            });
            resultHtml += '</div>';
        } else {
            resultHtml += `<div class="alert-banner alert-success">`;
            resultHtml += `<strong>✅ No Sensitive Data Detected</strong>`;
            resultHtml += `<p>The email is safe to send.</p>`;
            resultHtml += `</div>`;
        }
        
        resultHtml += '</div>';
        
        // Insert result into modal
        const form = document.getElementById('emailTestForm');
        let resultDiv = document.getElementById('emailTestResult');
        if (!resultDiv) {
            resultDiv = document.createElement('div');
            resultDiv.id = 'emailTestResult';
            form.appendChild(resultDiv);
        }
        resultDiv.innerHTML = resultHtml;
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        showNotification(result.blocked ? 'Email blocked - Sensitive data detected!' : 'Email analysis completed', result.blocked ? 'error' : 'success');
        
        // Reload email stats and logs
        setTimeout(() => {
            loadMonitoringData();
        }, 1000);
        
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error analyzing email: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// Make functions globally available
window.analyzeText = analyzeText;
window.showTab = showTab;
window.loadPolicies = loadPolicies;
window.loadAlerts = loadAlerts;
window.loadMonitoringData = loadMonitoringData;
window.showCreatePolicyForm = showCreatePolicyForm;
window.closeModal = closeModal;
window.createPolicy = createPolicy;
window.showNotification = showNotification;
window.showEmailTestForm = showEmailTestForm;
window.closeEmailModal = closeEmailModal;
window.testEmail = testEmail;

// Load data on page load
window.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');
    
    // Verify elements exist
    const textInput = document.getElementById('textInput');
    const analyzeBtn = document.querySelector('#analysis .btn-primary');
    
    if (!textInput) {
        console.error('textInput element not found!');
    }
    if (!analyzeBtn) {
        console.error('analyze button not found!');
    } else {
        // Add click listener as backup
        analyzeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('Button clicked via event listener');
            analyzeText();
        });
    }
    
    // Show loading indicators
    try {
        showNotification('Loading data...', 'info');
    } catch (e) {
        console.error('Error showing notification:', e);
    }
    
    // Load data with error handling
    Promise.allSettled([
        loadPolicies().catch((e) => console.error('Error loading policies:', e)),
        loadAlerts().catch((e) => console.error('Error loading alerts:', e)),
        loadMonitoringData().catch((e) => console.error('Error loading monitoring:', e))
    ]).then(() => {
        try {
            showNotification('Data loaded successfully', 'success');
        } catch (e) {
            console.error('Error showing success notification:', e);
        }
    });
});

