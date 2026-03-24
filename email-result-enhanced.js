// Enhanced email result display function
// This should replace the existing testEmail result display logic

async function testEmailEnhanced(event) {
    event.preventDefault();

    const fromEmail = document.getElementById('emailFrom').value;
    const toEmails = document.getElementById('emailTo').value.split(',').map(e => e.trim()).filter(e => e);
    const subject = document.getElementById('emailSubject').value;
    const body = document.getElementById('emailBody').value;
    const fileInput = document.getElementById('emailAttachments');

    const emailData = {
        from: fromEmail,
        to: toEmails,
        subject: subject,
        body: body,
        source_ip: '127.0.0.1',
        source_user: fromEmail
    };

    // Read attachments as base64 if any
    if (fileInput && fileInput.files && fileInput.files.length > 0) {
        const attachments = [];
        for (let i = 0; i < fileInput.files.length; i++) {
            const file = fileInput.files[i];
            const base64 = await readFileAsBase64(file);
            if (base64) attachments.push({ filename: file.name, content: base64 });
        }
        if (attachments.length) emailData.attachments = attachments;
    }

    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analyzing...';

    try {
        const response = await fetch('/api/monitoring/email', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(emailData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        // Display enhanced result
        const resultDiv = document.getElementById('emailTestResult');
        if (!resultDiv) {
            console.error('Result div not found');
            return;
        }

        const esc = (s) => {
            const d = document.createElement('div');
            d.textContent = s == null ? '' : String(s);
            return d.innerHTML;
        };

        let html = '<div class="email-result">';

        // Header with date
        html += `<div class="email-result-header">
            <h4>📧 Email Analysis Results</h4>
            <span class="email-result-date">${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
        </div>`;

        // Attachments info
        if (emailData.attachments && emailData.attachments.length > 0) {
            html += `<div class="email-attachments-info">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-4.24 4.24a2 2 0 0 1-2.83-2.83l2.83-2.83"></path>
                </svg>
                <span>${emailData.attachments.length} attachment(s) analyzed with this email</span>
            </div>`;
        }

        // Get analysis result
        const analysis = result.analysis || result;
        const policiesMatched = analysis.policies_matched || false;
        const appliedPolicies = analysis.applied_policies || [];
        const actionsTaken = analysis.actions_taken || [];

        // Status banner
        if (analysis.sensitive_data_detected) {
            if (policiesMatched && appliedPolicies.length > 0) {
                html += `<div class="email-alert-banner alert-banner alert-danger">
                    <div class="alert-banner-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                            <line x1="12" y1="9" x2="12" y2="13"></line>
                            <line x1="12" y1="17" x2="12.01" y2="17"></line>
                        </svg>
                    </div>
                    <div class="alert-banner-content">
                        <strong>⚠️ Policy Violation Detected!</strong>
                        <p>${esc(analysis.message || result.message || 'Sensitive data detected and policies were applied')}</p>
                    </div>
                </div>`;
            } else {
                html += `<div class="email-alert-banner alert-banner alert-info">
                    <div class="alert-banner-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <div class="alert-banner-content">
                        <strong>ℹ️ Sensitive Data Detected</strong>
                        <p>${esc(analysis.message || result.message || 'Sensitive data detected but no matching policies')}</p>
                    </div>
                </div>`;
            }
        } else {
            html += `<div class="email-alert-banner alert-banner alert-success">
                <div class="alert-banner-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
                <div class="alert-banner-content">
                    <strong>✅ No Sensitive Data Detected</strong>
                    <p>The email is safe to send.</p>
                </div>
            </div>`;
        }

        // Show violated policies if any
        if (appliedPolicies.length > 0) {
            html += `<div class="policies-section">`;
            html += `<h5 class="policies-section-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                Violated Policies (${appliedPolicies.length})
            </h5>`;
            html += `<div class="policies-list">`;

            appliedPolicies.forEach(policy => {
                const actionBadgeClass = policy.action === 'block' ? 'policy-badge-danger' : policy.action === 'encrypt' ? 'policy-badge-success' : policy.action === 'alert' ? 'policy-badge-warning' : 'policy-badge-info';
                const actionIcon = policy.action === 'block' ? '🚫' : policy.action === 'encrypt' ? '🔒' : policy.action === 'alert' ? '⚠️' : 'ℹ️';
                const severityBadgeClass = policy.severity === 'critical' || policy.severity === 'high' ? 'policy-badge-danger' : policy.severity === 'medium' ? 'policy-badge-warning' : 'policy-badge-info';
                const matchedStrE = (policy.matched_entities || []).map(e => esc(e)).join(', ');

                html += `
                    <div class="policy-card">
                        <div class="policy-card-header">
                            <div class="policy-name">${actionIcon} ${esc(policy.name)}</div>
                            <div class="policy-badges">
                                <span class="policy-badge ${actionBadgeClass}">${esc(policy.action)}</span>
                                <span class="policy-badge ${severityBadgeClass}">${esc(policy.severity)}</span>
                            </div>
                        </div>
                        <div class="policy-matched-entities">
                            <span class="policy-matched-label">Matched Entities:</span>
                            <span class="policy-matched-values">${matchedStrE}</span>
                            <span class="policy-matched-count">(${policy.matched_count} found)</span>
                        </div>
                    </div>
                `;
            });

            html += '</div></div>';
        }

        // Action status card
        const actionType = analysis.action || (analysis.blocked ? 'block' : (analysis.encrypted_text ? 'encrypt' : 'alert'));

        html += `<div class="action-status-card">`;
        html += `<h5 class="action-status-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            Action Taken by System
        </h5>`;

        if (actionType === 'block') {
            html += `<div class="action-status-item action-blocked">`;
            html += `<div class="action-status-icon">🚫</div>`;
            html += `<div class="action-status-content">`;
            html += `<strong>Email Blocked</strong>`;
            html += `<span class="action-status-arabic">(منع الإرسال)</span>`;
            html += `<p class="action-status-desc">Email prevented from being sent. Manager notified of policy violation.</p>`;
            html += `</div></div>`;
        } else if (actionType === 'encrypt') {
            html += `<div class="action-status-item action-encrypt">`;
            html += `<div class="action-status-icon">🔒</div>`;
            html += `<div class="action-status-content">`;
            html += `<strong>Email Allowed with Encryption</strong>`;
            html += `<span class="action-status-arabic">(السماح مع التشفير)</span>`;
            html += `<p class="action-status-desc">Email can be sent with encrypted content. Manager notified.</p>`;
            html += `</div></div>`;
        } else if (actionType === 'alert') {
            html += `<div class="action-status-item action-alert">`;
            html += `<div class="action-status-icon">📧</div>`;
            html += `<div class="action-status-content">`;
            html += `<strong>Email Allowed</strong>`;
            html += `<span class="action-status-arabic">(السماح بالإرسال)</span>`;
            html += `<p class="action-status-desc">Email sent successfully. Manager notified of sensitive data.</p>`;
            html += `</div></div>`;
        } else {
            html += `<div class="action-status-item action-allow">`;
            html += `<div class="action-status-icon">✅</div>`;
            html += `<div class="action-status-content">`;
            html += `<strong>Email Allowed</strong>`;
            html += `<p class="action-status-desc">No policy violation detected. Email can be sent.</p>`;
            html += `</div></div>`;
        }

        html += `</div>`; // Close action-status-card

        // Actions taken
        if (actionsTaken.length > 0) {
            html += `<div style="margin-top: 20px; padding: 12px; background: var(--light); border-radius: 8px;">
                <strong style="display: block; margin-bottom: 8px;">Actions Taken:</strong>
                ${actionsTaken.map(action => `<span class="badge badge-info" style="margin-right: 4px; display: inline-block; margin-bottom: 4px;">${esc(action)}</span>`).join('')}
            </div>`;
        }

        // Detected entities
        if (analysis.detected_entities && analysis.detected_entities.length > 0) {
            const confPct = (e) => {
                const v = e.score != null ? e.score : e.confidence;
                return v == null ? '—' : (v <= 1 ? v * 100 : v).toFixed(1) + '%';
            };

            html += `<div style="margin-top: 24px;">
                <h5 style="margin-bottom: 12px;">Detected Entities (${analysis.detected_entities.length}):</h5>
                <div class="entities-list">`;
            analysis.detected_entities.forEach(entity => {
                html += `
                    <div class="entity-item">
                        <span class="entity-type">${esc(entity.entity_type)}</span>
                        <span class="entity-value">${esc(entity.value)}</span>
                        <span class="entity-score">${confPct(entity)} confidence</span>
                    </div>
                `;
            });
            html += '</div></div>';
        }

        // Encrypted content
        if (analysis.encrypted_text || analysis.encrypted_body) {
            const contentToShow = analysis.encrypted_body != null ? analysis.encrypted_body : analysis.encrypted_text;
            const escapedText = (contentToShow || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');

            const textForCopy = (contentToShow || '')
                .replace(/\\/g, '\\\\')
                .replace(/'/g, "\\'")
                .replace(/"/g, '\\"')
                .replace(/\n/g, '\\n')
                .replace(/\r/g, '\\r');

            html += `<div style="margin-top: 24px; padding: 16px; background: var(--light); border-radius: 8px; border-left: 4px solid var(--success);">
                <h5 style="margin-top: 0; margin-bottom: 12px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 8px;">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                    Content Recipient Will Receive
                </h5>
                ${analysis.encrypted_subject ? `<p style="margin-bottom: 8px;"><strong>Subject:</strong> <code>${esc(analysis.encrypted_subject)}</code></p>` : ''}
                <div style="background: white; padding: 12px; border-radius: 4px; border: 1px solid var(--border); font-family: monospace; word-break: break-all; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">
                    ${escapedText}
                </div>
                <button onclick="copyEncryptedText('${textForCopy}')"
                        style="margin-top: 8px; padding: 8px 16px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; display: inline-flex; align-items: center; gap: 8px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    Copy encrypted content
                </button>
            </div>`;
        }

        html += '</div>'; // Close email-result

        resultDiv.innerHTML = html;
        resultDiv.style.display = 'block';
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        showNotification(
            result.blocked || (analysis && analysis.blocked)
                ? 'Email blocked. Manager notified.'
                : (analysis && analysis.action === 'encrypt')
                    ? 'Email allowed with encryption. Manager notified. You can send with encrypted content.'
                    : (analysis && analysis.action === 'alert')
                        ? 'Email allowed. Manager notified.'
                        : 'Email analysis completed',
            result.blocked || (analysis && analysis.blocked) ? 'error' : 'success'
        );

        // Refresh inbox list so new email appears
        if (typeof loadEmailList === 'function') loadEmailList(1);

        // Reload email stats and logs (only if admin)
        if (currentUser && currentUser.role === 'admin') {
            setTimeout(() => {
                loadMonitoringData();
            }, 1000);
        }

    } catch (error) {
        console.error('Error:', error);
        showNotification('Error analyzing email: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// Copy encrypted text function
function copyEncryptedText(text) {
    navigator.clipboard.writeText(text.replace(/\\n/g, '\n').replace(/\\r/g, '\r'))
        .then(() => {
            showNotification('Encrypted content copied to clipboard!', 'success');
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy content', 'error');
        });
}
