// API base URL for fetch. Uses (in order): window.API_BASE, <meta name="api-base" content="...">, or same origin.
// When deploying on another machine: if frontend and backend are on different ports, set API_BASE so Policy Violation and API calls work.
function getApiBase() {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    const fromWindow = window.API_BASE;
    const fromMeta = document.querySelector && document.querySelector('meta[name="api-base"]')?.getAttribute('content');
    const base = (fromWindow || fromMeta || window.location?.origin || 'http://localhost:8000').trim();
    return base.replace(/\/$/, '');
}
const API_BASE = getApiBase();

/** Format alert created_at in user's local timezone (browser). Returns 'N/A' if invalid. */
function formatAlertTimeLocal(createdAt, fallback) {
    if (createdAt == null || createdAt === '') return (fallback || 'N/A');
    const d = new Date(createdAt);
    if (isNaN(d.getTime())) return (fallback || 'N/A');
    return d.toLocaleString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Sound effect for alerts (Simple beep/alert sound encoded in base64)
const ALERT_SOUND = new Audio("data:audio/wav;base64,UklGRl9vT1BXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU"); // Shortened placeholder, will use a real beep

// Better beep sound (Base64)
const BEEP_SOUND = "data:audio/wav;base64,UklGRl9vT1BXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU";

// ============================================================================
// Safe localStorage wrapper - with sessionStorage fallback to preserve session on refresh
// When localStorage is blocked (e.g. "Access is denied"), use sessionStorage so refresh keeps the user logged in.
// ============================================================================
let _authStorage = null; // Will be localStorage or sessionStorage

function getAuthStorage() {
    if (_authStorage !== null) return _authStorage;
    try {
        localStorage.setItem('__auth_test__', '1');
        localStorage.removeItem('__auth_test__');
        _authStorage = localStorage;
        return _authStorage;
    } catch (e) {
        console.warn('localStorage not available, using sessionStorage for auth (session will persist on refresh in this tab):', e.message);
    }
    try {
        sessionStorage.setItem('__auth_test__', '1');
        sessionStorage.removeItem('__auth_test__');
        _authStorage = sessionStorage;
        return _authStorage;
    } catch (e2) {
        console.warn('sessionStorage also not available:', e2.message);
        return null;
    }
}

const safeStorage = {
    isAvailable: function() {
        return getAuthStorage() !== null;
    },

    getItem: function(key) {
        try {
            const storage = getAuthStorage();
            return storage ? storage.getItem(key) : null;
        } catch (e) {
            console.warn(`Failed to get "${key}":`, e.message);
            return null;
        }
    },

    setItem: function(key, value) {
        try {
            const storage = getAuthStorage();
            if (storage) {
                storage.setItem(key, value);
                return true;
            }
            return false;
        } catch (e) {
            console.warn(`Failed to set "${key}":`, e.message);
            return false;
        }
    },

    removeItem: function(key) {
        try {
            const storage = getAuthStorage();
            if (storage) storage.removeItem(key);
            if (_authStorage === localStorage && sessionStorage) {
                try { sessionStorage.removeItem(key); } catch (_) {}
            } else if (_authStorage === sessionStorage && localStorage) {
                try { localStorage.removeItem(key); } catch (_) {}
            }
            return true;
        } catch (e) {
            console.warn(`Failed to remove "${key}":`, e.message);
            return false;
        }
    },

    clear: function() {
        try {
            const storage = getAuthStorage();
            if (storage) storage.clear();
            return true;
        } catch (e) {
            console.warn('Failed to clear storage:', e.message);
            return false;
        }
    }
};

// ============================================================================
// CRITICAL: Define approve/reject functions IMMEDIATELY at top level
// These must be available before any HTML is rendered
// ============================================================================
window.approveUser = async function approveUser(userId) {
    console.log('approveUser called with userId:', userId, typeof userId);
    
    if (!userId) {
        console.error('No userId provided to approveUser');
        if (typeof showNotification === 'function') {
            showNotification('Error: User ID is missing', 'error');
        }
        return;
    }
    
    if (!confirm('Are you sure you want to approve this user?')) {
        console.log('User cancelled approval');
        return;
    }

    try {
        console.log('Approving user:', userId);
        const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
        console.log('Request headers:', { hasAuth: !!headers['Authorization'] });
        
        const response = await fetch(`/api/users/${userId}/approve`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({})
        });

        console.log('Approve response status:', response.status);

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized - logging out user');
                if (typeof showNotification === 'function') {
                    showNotification('Session expired. Please login again.', 'warning');
                }
                if (typeof logout === 'function') {
                    logout();
                }
                return;
            }
            
            let errorMessage = 'Failed to approve user';
            try {
                const error = await response.json();
                errorMessage = error.detail || error.message || errorMessage;
                console.error('Approve error:', error);
            } catch (e) {
                const errorText = await response.text();
                console.error('Approve error (text):', errorText);
                errorMessage = errorText || errorMessage;
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log('User approved successfully:', data);
        if (typeof showNotification === 'function') {
            showNotification('User approved successfully!', 'success');
        }
        
        // Reload pending users and all users
        if (typeof loadPendingUsers === 'function') {
            loadPendingUsers();
        }
        if (typeof loadUsers === 'function') {
            loadUsers();
        }

    } catch (error) {
        console.error('Error approving user:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error approving user: ' + error.message, 'error');
        }
    }
};

window.rejectUser = async function rejectUser(userId) {
    const reason = prompt('Enter rejection reason (optional):');
    if (reason === null) return; // User cancelled

    try {
        console.log('Rejecting user:', userId, 'reason:', reason);
        const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json' };
        console.log('Request headers:', { hasAuth: !!headers['Authorization'] });
        
        const response = await fetch(`/api/users/${userId}/reject`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ reason: reason || null })
        });

        console.log('Reject response status:', response.status);

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized - logging out user');
                if (typeof showNotification === 'function') {
                    showNotification('Session expired. Please login again.', 'warning');
                }
                if (typeof logout === 'function') {
                    logout();
                }
                return;
            }
            
            let errorMessage = 'Failed to reject user';
            try {
                const error = await response.json();
                errorMessage = error.detail || error.message || errorMessage;
                console.error('Reject error:', error);
            } catch (e) {
                const errorText = await response.text();
                console.error('Reject error (text):', errorText);
                errorMessage = errorText || errorMessage;
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log('User rejected successfully:', data);
        if (typeof showNotification === 'function') {
            showNotification('User rejected', 'warning');
        }
        
        // Reload pending users and all users
        if (typeof loadPendingUsers === 'function') {
            loadPendingUsers();
        }
        if (typeof loadUsers === 'function') {
            loadUsers();
        }

    } catch (error) {
        console.error('Error rejecting user:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error rejecting user: ' + error.message, 'error');
        }
    }
}; 

// ============================================================================
// CRITICAL: Modal functions MUST be defined at top level for immediate availability
// These functions are called from HTML onclick handlers and event listeners
// ============================================================================
window.showLoginModal = function() {
    console.log('showLoginModal called (global)');
    try {
        const modal = document.getElementById('loginModal');
        if (!modal) {
            console.error('Login modal not found');
            return;
        }
        
        // Hide the login overlay first
        const overlay = document.getElementById('loginRequiredOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
        
        // CRITICAL: Remove the inline style attribute completely
        modal.removeAttribute('style');
        
        // Set all properties with !important to override CSS
        modal.style.setProperty('display', 'flex', 'important');
        modal.style.setProperty('position', 'fixed', 'important');
        modal.style.setProperty('top', '0', 'important');
        modal.style.setProperty('left', '0', 'important');
        modal.style.setProperty('width', '100vw', 'important');
        modal.style.setProperty('height', '100vh', 'important');
        modal.style.setProperty('z-index', '100001', 'important');
        modal.style.setProperty('opacity', '1', 'important');
        modal.style.setProperty('visibility', 'visible', 'important');
        modal.style.setProperty('pointer-events', 'auto', 'important');
        modal.style.setProperty('align-items', 'center', 'important');
        modal.style.setProperty('justify-content', 'center', 'important');
        
        // Add show class
        modal.classList.add('show');
        
        // Focus on username input
        setTimeout(() => {
            const usernameInput = document.getElementById('loginUsername');
            if (usernameInput) {
                usernameInput.focus();
            }
        }, 100);
    } catch (error) {
        console.error('Error in showLoginModal:', error);
    }
};

window.showRegisterModal = function() {
    console.log('showRegisterModal called (global)');
    try {
        const modal = document.getElementById('registerModal');
        if (!modal) {
            console.error('Register modal not found');
            return;
        }
        
        // Hide the login overlay first
        const overlay = document.getElementById('loginRequiredOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
        
        // CRITICAL: Remove the inline style attribute completely
        modal.removeAttribute('style');
        
        // Set all properties with !important to override CSS
        modal.style.setProperty('display', 'flex', 'important');
        modal.style.setProperty('position', 'fixed', 'important');
        modal.style.setProperty('top', '0', 'important');
        modal.style.setProperty('left', '0', 'important');
        modal.style.setProperty('width', '100vw', 'important');
        modal.style.setProperty('height', '100vh', 'important');
        modal.style.setProperty('z-index', '100001', 'important');
        modal.style.setProperty('opacity', '1', 'important');
        modal.style.setProperty('visibility', 'visible', 'important');
        modal.style.setProperty('pointer-events', 'auto', 'important');
        modal.style.setProperty('align-items', 'center', 'important');
        modal.style.setProperty('justify-content', 'center', 'important');
        
        // Add show class
        modal.classList.add('show');
        
        // Load departments for the dropdown (no auth required)
        fetch('/api/departments/list')
            .then(r => r.ok ? r.json() : [])
            .then(list => {
                const sel = document.getElementById('registerDepartment');
                if (!sel) return;
                sel.innerHTML = '<option value="">Select department...</option>';
                (list || []).forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.name || d.id;
                    sel.appendChild(opt);
                });
            })
            .catch(() => {});
        
        // Focus on username input
        setTimeout(() => {
            const usernameInput = document.getElementById('registerUsername');
            if (usernameInput) {
                usernameInput.focus();
            }
        }, 100);
    } catch (error) {
        console.error('Error in showRegisterModal:', error);
    }
};

console.log('Modal functions defined at top level:', {
    showLoginModal: typeof window.showLoginModal,
    showRegisterModal: typeof window.showRegisterModal
});

function playAlertSound() {
    try {
        // Create oscillator for a more reliable "beep" without external files
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = 'triangle'; // Alert-like sound
            osc.frequency.setValueAtTime(880, ctx.currentTime); // High pitch (A5)
            osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.5); // Drop pitch
            
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start();
            osc.stop(ctx.currentTime + 0.5);
        }
    } catch (e) {
        console.error("Audio play failed", e);
    }
}

// Notification system (must be defined early)
function showNotification(message, type = 'info') {
    if (message != null && typeof message !== 'string') {
        if (typeof message === 'object' && message.message) {
            message = message.message;
        } else if (Array.isArray(message)) {
            message = message.map(function (m) {
                return typeof m === 'string' ? m : (m && m.msg) || JSON.stringify(m);
            }).join('. ');
        } else {
            message = JSON.stringify(message);
        }
    }
    const text = String(message || '');
    // Play sound for warnings and errors
    if (type === 'error' || type === 'warning' || type === 'danger') {
        playAlertSound();
    }

    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = text;
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
    console.log('showTab called:', tabName, element);
    
    // Check if user has permission to access this tab
    if (currentUser && currentUser.role !== 'admin') {
        const allowedTabs = currentUser.role === 'manager'
            ? ['analysis', 'testEmail', 'users']
            : ['analysis', 'testEmail'];
        if (!allowedTabs.includes(tabName)) {
            console.warn('Access denied: This tab is not available for your role');
            showNotification('Access denied. This feature is not available for your role.', 'error');
            return;
        }
    }
    
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
        tab.style.display = 'none';
        tab.style.visibility = 'hidden';
        tab.removeAttribute('style'); // Remove inline styles that might have !important
        tab.style.display = 'none'; // Set display to none without !important
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const tabContent = document.getElementById(tabName);
    if (tabContent) {
        tabContent.classList.add('active');
        // Remove any inline styles first
        tabContent.removeAttribute('style');
        // Then set display
        tabContent.style.display = 'block';
        tabContent.style.visibility = 'visible';
        tabContent.style.opacity = '1';
        tabContent.style.pointerEvents = 'auto';
        console.log('Tab content shown:', tabName);
    } else {
        console.error('Tab content not found:', tabName);
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
    
    // Load data when specific tabs are opened
    if (tabName === 'users' && currentUser && (currentUser.role === 'admin' || currentUser.role === 'manager')) {
        // Load all users by default when opening users tab
        setTimeout(() => {
            if (typeof loadUsers === 'function') {
                loadUsers(null, 1);
            }
        }, 100);
    } else if (tabName === 'policies' && currentUser && currentUser.role === 'admin') {
        // Load policies when opening policies tab
        setTimeout(() => {
            if (typeof loadPolicies === 'function') {
                loadPolicies(1);
            }
        }, 100);
    } else if (tabName === 'alerts' && currentUser && currentUser.role === 'admin') {
        // Load alerts when opening alerts tab
        setTimeout(() => {
            if (typeof loadAlerts === 'function') {
                loadAlerts(1);
            }
        }, 100);
    } else if (tabName === 'monitoring' && currentUser && currentUser.role === 'admin') {
        // Load monitoring data when opening monitoring tab
        setTimeout(() => {
            if (typeof loadMonitoringData === 'function') {
                loadMonitoringData(1);
            }
        }, 100);
    } else if (tabName === 'testEmail' && currentUser) {
        // Test Email tab — inbox loads when user switches to "Emails sent to you" sub-tab
    }
}

// Email tab sub-tab switching (Test Email | Emails sent to you)
function switchEmailMode(mode, buttonElement) {
    const emailTab = document.getElementById('testEmail');
    if (!emailTab) return;
    emailTab.querySelectorAll('.sub-tab-btn').forEach(btn => btn.classList.remove('active'));
    if (buttonElement) buttonElement.classList.add('active');
    emailTab.querySelectorAll('.email-mode-section').forEach(section => section.classList.remove('active'));
    if (mode === 'test') {
        const section = document.getElementById('testEmailSection');
        if (section) section.classList.add('active');
    } else if (mode === 'inbox') {
        const section = document.getElementById('emailInboxSection');
        if (section) section.classList.add('active');
        if (currentUser && typeof loadEmailList === 'function') loadEmailList(1);
    }
}

// Analysis Mode Switching
function switchAnalysisMode(mode, buttonElement) {
    // Remove active class from all sub-tabs
    document.querySelectorAll('.sub-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Add active class to clicked button
    if (buttonElement) {
        buttonElement.classList.add('active');
    }

    // Hide all sections
    document.querySelectorAll('.analysis-mode-section').forEach(section => {
        section.classList.remove('active');
    });

    // Show selected section
    if (mode === 'file') {
        document.getElementById('fileAnalysisSection').classList.add('active');
    } else if (mode === 'text') {
        document.getElementById('textAnalysisSection').classList.add('active');
    } else if (mode === 'decrypt') {
        const el = document.getElementById('decryptAnalysisSection');
        if (el) el.classList.add('active');
    }
}

async function decryptPastedContent() {
    const input = document.getElementById('decryptTextInput');
    const resultDiv = document.getElementById('decryptResult');
    const resultContent = document.getElementById('decryptResultContent');
    const btn = document.getElementById('decryptContentBtn');
    if (!input || !resultDiv || !resultContent) return;
    const content = (input.value || '').trim();
    if (!content) {
        showNotification('Paste encrypted text first', 'warning');
        return;
    }
    if (btn) { btn.disabled = true; btn.textContent = 'Decrypting...'; }
    try {
        const response = await fetch('/api/analyze/decrypt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify({ content: content })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || response.statusText || 'Decrypt failed');
        }
        if (data.decrypted != null) {
            resultContent.textContent = data.decrypted;
            resultDiv.style.display = 'block';
            showNotification('Decrypted successfully.', 'success');
        }
    } catch (e) {
        showNotification(e.message || 'Decryption failed.', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Decrypt'; }
    }
}

// File Upload functions
function initFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const fileUploadArea = document.getElementById('fileUploadArea');
    const analyzeFileBtn = document.getElementById('analyzeFileBtn');
    const selectedFileName = document.getElementById('selectedFileName');
    const fileUploadText = document.getElementById('fileUploadText');

    if (!fileInput || !fileUploadArea || !analyzeFileBtn) return;

    // Click to browse
    fileUploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // File selected
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileSelect(file);
        }
    });

    // Drag and drop
    fileUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUploadArea.classList.add('dragover');
    });

    fileUploadArea.addEventListener('dragleave', () => {
        fileUploadArea.classList.remove('dragover');
    });

    fileUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUploadArea.classList.remove('dragover');

        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect(file);
        }
    });

    function handleFileSelect(file) {
        // Check file type
        const allowedTypes = ['.pdf', '.docx', '.txt', '.xlsx'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();

        if (!allowedTypes.includes(fileExt)) {
            showNotification(`Unsupported file type. Supported: ${allowedTypes.join(', ')}`, 'error');
            fileInput.value = '';
            return;
        }

        // Update UI
        selectedFileName.textContent = `Selected: ${file.name}`;
        selectedFileName.style.display = 'block';
        fileUploadText.textContent = file.name;
        fileUploadArea.classList.add('has-file');
        analyzeFileBtn.disabled = false;
    }

    // Analyze file button
    analyzeFileBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) {
            showNotification('Please select a file first', 'warning');
            return;
        }

        await analyzeFile(file);
    });
}

async function analyzeFile(file) {
    const analyzeFileBtn = document.getElementById('analyzeFileBtn');
    const applyPoliciesFile = document.getElementById('applyPoliciesFile');
    const resultBox = document.getElementById('analysisResult');
    const resultContent = document.getElementById('resultContent');

    if (!file) {
        showNotification('Please select a file', 'warning');
        return;
    }

    // Show loading
    const originalText = analyzeFileBtn.innerHTML;
    analyzeFileBtn.disabled = true;
    analyzeFileBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg><span>Analyzing...</span>';

    if (resultBox) {
        resultBox.style.display = 'none';
    }

    try {
        // Create FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('apply_policies', applyPoliciesFile ? applyPoliciesFile.checked : true);

        const response = await fetch('/api/analyze/file', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `Server error: ${response.status}`);
        }

        const data = await response.json();

        // Display results
        if (resultBox && resultContent) {
            displayAnalysisResult(data, file.name);
            resultBox.style.display = 'block';
        }

        showNotification('File analysis completed successfully', 'success');
    } catch (error) {
        console.error('Error analyzing file:', error);
        showNotification('Error: ' + error.message, 'error');
    } finally {
        analyzeFileBtn.disabled = false;
        analyzeFileBtn.innerHTML = originalText;
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
        const headers = getAuthHeaders();
        headers['Content-Type'] = 'application/json';
        const response = await fetch('/api/analyze/', {
            method: 'POST',
            headers: headers,
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
        
        // Display results - determine which result box to use
        const isFileMode = document.getElementById('fileAnalysisSection').classList.contains('active');
        const targetResultBox = isFileMode
            ? document.getElementById('analysisResult')
            : document.getElementById('analysisResultText');

        if (targetResultBox) {
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

function displayAnalysisResult(result, fileName = null) {
    // Determine which result box to use based on active mode
    const isFileMode = document.getElementById('fileAnalysisSection').classList.contains('active');
    const resultBox = isFileMode
        ? document.getElementById('analysisResult')
        : document.getElementById('analysisResultText');
    const resultContent = isFileMode
        ? document.getElementById('resultContent')
        : document.getElementById('resultContentText');
    
    if (!resultBox || !resultContent) return;

    const esc = (s) => {
        if (s == null) return '';
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    };
    const confidencePct = (entity) => {
        const v = entity.score != null ? entity.score : entity.confidence;
        if (v == null) return '—';
        return (v <= 1 ? v * 100 : v).toFixed(1) + '%';
    };
    
    let html = '';

    // Show file name if provided
    if (fileName) {
        html += `<div style="margin-bottom: 16px; padding: 12px; background: var(--light); border-radius: 8px; border-left: 4px solid var(--primary);">
            <strong>File:</strong> ${esc(fileName)}
        </div>`;
    }
    
    // Check if policies were applied
    const policiesMatched = result.policies_matched || false;
    const appliedPolicies = result.applied_policies || [];
    
    if (result.sensitive_data_detected) {
        // Show message based on whether policies matched
        if (policiesMatched && appliedPolicies.length > 0) {
            html += `<div class="alert-banner alert-danger">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
                <span>Sensitive Data Detected - Policies Applied!</span>
            </div>`;
        } else {
            html += `<div class="alert-banner alert-info">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                <span>Sensitive Data Detected - No Matching Policies (No Action Taken)</span>
            </div>`;
        }
        
        // Show applied policies
        if (appliedPolicies.length > 0) {
            html += `<h4 style="margin-top: 24px; margin-bottom: 16px; color: var(--dark);">Applied Policies (${appliedPolicies.length})</h4>`;
            html += `<div style="margin-bottom: 24px;">`;
            appliedPolicies.forEach(policy => {
                const actionBadge = policy.action === 'block' ? 'badge-danger' : policy.action === 'alert' ? 'badge-warning' : 'badge-info';
                const severityBadge = policy.severity === 'critical' || policy.severity === 'high' ? 'badge-danger' : policy.severity === 'medium' ? 'badge-warning' : 'badge-info';
                const matchedStr = (policy.matched_entities || []).map(e => esc(e)).join(', ');
                const typesStr = (policy.entity_types || []).map(t => esc(t)).join(', ');
                html += `
                    <div style="padding: 16px; margin-bottom: 12px; background: var(--light); border-radius: 8px; border-left: 4px solid var(--primary);">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <strong style="font-size: 1.1rem; color: var(--dark);">${esc(policy.name)}</strong>
                            <div>
                                <span class="badge ${actionBadge}" style="margin-right: 8px;">${esc(policy.action)}</span>
                                <span class="badge ${severityBadge}">${esc(policy.severity)}</span>
                            </div>
                        </div>
                        <div style="margin-top: 8px; font-size: 0.9rem; color: var(--text-muted);">
                            <div><strong>Matched Entities:</strong> ${matchedStr} (${policy.matched_count} found)</div>
                            <div style="margin-top: 4px;"><strong>Policy Entity Types:</strong> ${typesStr}</div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }
        
        if (result.blocked) {
            html += `<div class="alert-banner alert-warning">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"></path>
                </svg>
                <span>Data Transfer Blocked by Policy</span>
            </div>`;
        }
        
        if (result.alert_created) {
            html += `<div class="badge badge-warning" style="margin-bottom: 16px;">Alert Created</div>`;
        }
        
        html += `<h4 style="margin-top: 24px; margin-bottom: 16px; color: var(--dark);">Detected Entities (${result.detected_entities.length})</h4>`;
        (result.detected_entities || []).forEach(entity => {
            html += `
                <div class="entity-item">
                    <div class="entity-type">${esc(entity.entity_type || '')}</div>
                    <div class="entity-value">${esc(entity.value || '')}</div>
                    <div class="entity-score">Confidence: ${confidencePct(entity)}</div>
                </div>
            `;
        });
        
        if (result.actions_taken && result.actions_taken.length > 0) {
            html += `<div class="actions-taken" style="margin-top: 16px;"><strong>Actions Taken:</strong> `;
            result.actions_taken.forEach(action => {
                html += `<span class="action-tag">${esc(action)}</span>`;
            });
            html += `</div>`;
        }
        
        // Show encrypted text if encryption was applied
        if (result.encrypted_text) {
            // Escape HTML and prepare text for display
            const escapedText = result.encrypted_text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
            
            // Prepare text for copy function (escape quotes)
            const textForCopy = result.encrypted_text
                .replace(/\\/g, '\\\\')
                .replace(/'/g, "\\'")
                .replace(/"/g, '\\"')
                .replace(/\n/g, '\\n')
                .replace(/\r/g, '\\r');
            
            html += `<div style="margin-top: 24px; padding: 16px; background: var(--light); border-radius: 8px; border-left: 4px solid var(--success);">
                <h4 style="margin-top: 0; margin-bottom: 12px; color: var(--dark);">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 8px;">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                    Encrypted Text
                </h4>
                <div id="encryptedTextDisplay" style="background: white; padding: 12px; border-radius: 4px; border: 1px solid var(--border); font-family: monospace; word-break: break-all; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">
                    ${escapedText}
                </div>
                <button onclick="copyEncryptedText('${textForCopy}')" 
                        style="margin-top: 8px; padding: 6px 12px; background: var(--primary); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem;">
                    Copy Encrypted Text
                </button>
            </div>`;
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

// Copy to clipboard helper function
function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
    try {
        // Create a temporary textarea element
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showNotification(successMessage, 'success');
    } catch (err) {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy to clipboard', 'error');
    }
}

// Copy encrypted text function (handles escaped text)
function copyEncryptedText(escapedText) {
    try {
        // Unescape the text
        const unescapedText = escapedText
            .replace(/\\n/g, '\n')
            .replace(/\\r/g, '\r')
            .replace(/\\'/g, "'")
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, '\\');
        copyToClipboard(unescapedText, 'Encrypted text copied to clipboard!');
    } catch (err) {
        console.error('Failed to copy encrypted text:', err);
        showNotification('Failed to copy encrypted text', 'error');
    }
}

// Policy functions
function switchPoliciesView(view, btn) {
    // Update active tab
    document.querySelectorAll('.sub-tabs-container .sub-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    if (view === 'active') {
        document.getElementById('policiesList').style.display = 'block';
        document.getElementById('deletedPoliciesList').style.display = 'none';
        loadPolicies();
    } else if (view === 'deleted') {
        document.getElementById('policiesList').style.display = 'none';
        document.getElementById('deletedPoliciesList').style.display = 'block';
        loadDeletedPolicies();
    }
}

async function loadPolicies(page = 1) {
    try {
        // Only load if user is logged in and is admin
        if (!authToken || !currentUser || currentUser.role !== 'admin') {
            console.log('Skipping policies load - user not admin', { authToken: !!authToken, currentUser, role: currentUser?.role });
            return;
        }
        
        currentPoliciesPage = page;
        console.log('Loading policies with auth token:', authToken ? 'present' : 'missing', 'page:', page);
        const headers = getAuthHeaders();
        console.log('Request headers:', headers);
        
        const response = await fetch(`/api/policies/?page=${page}&limit=${policiesPagination.limit}`, {
            headers: headers
        });
        
        console.log('Policies response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Policies API error:', response.status, errorText);
            
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized to load policies - logging out');
                logout();
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText.substring(0, 100)}`);
        }
        
        const data = await response.json();
        console.log('Policies API response:', data);
        
        // Handle both paginated and non-paginated responses
        const policies = Array.isArray(data) ? data : (data.items || []);
        
        if (!Array.isArray(policies)) {
            console.error('Policies is not an array:', typeof policies, policies);
            throw new Error('Invalid policies data format');
        }
        
        policiesPagination = {
            total: data.total || policies.length,
            total_pages: data.total_pages || 1,
            limit: data.limit || policiesPagination.limit,
            has_next: data.has_next !== undefined ? data.has_next : (currentPoliciesPage < (data.total_pages || 1)),
            has_prev: data.has_prev !== undefined ? data.has_prev : (currentPoliciesPage > 1)
        };
        
        console.log('Policies loaded successfully:', policies.length, 'policies');
        console.log('Policies pagination:', policiesPagination);
        displayPolicies(policies);
        renderPagination('policies', currentPoliciesPage, policiesPagination, loadPolicies);
    } catch (error) {
        console.error('Error loading policies:', error);
        const policiesList = document.getElementById('policiesList');
        if (policiesList) {
            policiesList.innerHTML = `<p style="color: var(--danger);">Error loading policies: ${error.message}</p>`;
        }
        // Only show notification if user is admin
        if (currentUser && currentUser.role === 'admin') {
            showNotification(`Error loading policies: ${error.message}`, 'error');
        }
    }
}

function displayPolicies(policies) {
    console.log('displayPolicies called with:', policies);
    const list = document.getElementById('policiesList');
    
    if (!list) {
        console.error('policiesList element not found!');
        return;
    }
    
    if (!policies || policies.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>No policies found. Create your first policy to get started.</p></div>';
        return;
    }
    
    console.log('Rendering table for', policies.length, 'policies');
    console.log('Current user:', currentUser);
    let html = `
        <div class="table-container">
            <table class="policies-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Entity Types</th>
                        <th>Action</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Ensure policies is an array before iterating
    if (!Array.isArray(policies)) {
        console.error('Policies is not an array in forEach:', typeof policies, policies);
        list.innerHTML = '<div class="empty-state"><p>Error: Invalid policies data format</p></div>';
        return;
    }
    
    policies.forEach(policy => {
        const statusBadge = policy.enabled 
            ? '<span class="badge badge-success">Enabled</span>'
            : '<span class="badge badge-danger">Disabled</span>';
        
        const severityBadge = `<span class="badge badge-${policy.severity === 'high' || policy.severity === 'critical' ? 'danger' : policy.severity === 'medium' ? 'warning' : 'info'}">${policy.severity}</span>`;
        const actionBadge = `<span class="badge badge-info">${policy.action}</span>`;
        const entityTypes = policy.entity_types && policy.entity_types.length > 0 
            ? policy.entity_types.map(e => `<span class="badge badge-secondary badge-small">${e}</span>`).join(' ')
            : '<span class="text-muted">None</span>';
        
        // Handle description - strip HTML if present and truncate
        let descriptionText = policy.description || '';
        // Remove any HTML tags for truncation
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = descriptionText;
        descriptionText = tempDiv.textContent || tempDiv.innerText || '';
        
        const truncatedDescription = descriptionText.length > 50 
            ? descriptionText.substring(0, 50) + '...' 
            : descriptionText || '<span class="text-muted">No description</span>';
        
        // Store policy data in data attribute (safer than inline onclick)
        const policyDataAttr = encodeURIComponent(JSON.stringify(policy));
        
        // Toggle button - Enable/Disable
        const toggleButton = policy.enabled
            ? `<button class="btn-icon btn-warning" onclick="event.stopPropagation(); togglePolicy('${policy.id}', false)" title="Disable Policy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="6" y="4" width="4" height="16" rx="1"></rect>
                    <rect x="14" y="4" width="4" height="16" rx="1"></rect>
                </svg>
            </button>`
            : `<button class="btn-icon btn-success" onclick="event.stopPropagation(); togglePolicy('${policy.id}', true)" title="Enable Policy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
            </button>`;
        
        html += `
            <tr data-policy-id="${policy.id}" class="table-row-clickable" data-policy-data="${policyDataAttr}" data-policy-name="${policy.name.replace(/"/g, '&quot;')}">
                <td><strong>${policy.name}</strong></td>
                <td><span title="${descriptionText || 'No description'}">${truncatedDescription}</span></td>
                <td><div class="entity-types-cell">${entityTypes}</div></td>
                <td>${actionBadge}</td>
                <td>${severityBadge}</td>
                <td>${statusBadge}</td>
                <td>
                    <div class="action-buttons" style="display: flex; gap: 4px; justify-content: flex-end;">
                        ${toggleButton}
                        <button class="btn-icon btn-update" onclick="event.stopPropagation(); editPolicy('${policy.id}')" title="Edit Policy">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button class="btn-icon btn-delete" onclick="event.stopPropagation(); deletePolicy('${policy.id}')" title="Delete Policy">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    list.innerHTML = html;
    
    // Force reflow to ensure buttons are rendered
    const buttons = list.querySelectorAll('.btn-icon');
    console.log('Policies table rendered with action buttons');
    console.log('Action buttons count:', buttons.length);
    console.log('Action buttons HTML:', buttons.length > 0 ? buttons[0].outerHTML : 'No buttons found');
    
    // Ensure buttons are visible
    buttons.forEach(btn => {
        btn.style.display = 'flex';
        btn.style.visibility = 'visible';
    });
    
    // Add event delegation for policy row clicks
    const table = list.querySelector('.policies-table');
    if (table && !table.dataset.policyClickBound) {
        table.dataset.policyClickBound = 'true';
        table.addEventListener('click', (e) => {
            const row = e.target.closest('tr[data-policy-id]');
            if (!row) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const policyId = row.getAttribute('data-policy-id');
            const policyName = row.getAttribute('data-policy-name');
            const policyDataStr = row.getAttribute('data-policy-data');
            
            if (policyId && policyDataStr) {
                try {
                    const policyData = JSON.parse(decodeURIComponent(policyDataStr));
                    console.log('Policy row clicked, showing details:', policyId);
                    if (typeof window.showPolicyDetails === 'function') {
                        window.showPolicyDetails(policyId, policyName || policyData.name || 'Policy', policyData);
                    } else {
                        console.error('showPolicyDetails function not found');
                    }
                } catch (error) {
                    console.error('Error parsing policy data:', error);
                }
            }
        });
    }
}

function showCreatePolicyForm(resetForm = true) {
    const modal = document.getElementById('createPolicyForm');
    if (resetForm) {
        resetPolicyForm(); // Reset form to create mode
    }
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
        resetPolicyForm(); // Reset form when closing
    }, 300);
}

async function createPolicy(event) {
    event.preventDefault();
    
    const policyName = document.getElementById('policyName').value.trim();
    const policyDescription = document.getElementById('policyDescription').value.trim();
    // Get selected entities from checkboxes
    const selectedEntities = Array.from(document.querySelectorAll('input[name="policyEntities"]:checked'))
        .map(checkbox => checkbox.value);
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
        const headers = getAuthHeaders();
        console.log('Creating policy with headers:', { 
            hasAuth: !!headers['Authorization'],
            authLength: headers['Authorization']?.length || 0
        });
        
        const response = await fetch('/api/policies/', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(formData)
        });
        
        console.log('Policy creation response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            showNotification('Policy created successfully', 'success');
            closeModal();
            document.getElementById('policyForm').reset();
            loadPolicies();
        } else {
            if (response.status === 401 || response.status === 403) {
                // Unauthorized - logout user
                console.log('Unauthorized - logging out user');
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
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

async function deletePolicy(policyId) {
    if (!confirm('Are you sure you want to delete this policy? This action can be undone by restoring the policy.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/policies/${policyId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            showNotification('Policy deleted successfully. You can restore it from deleted policies.', 'success');
            loadPolicies();
        } else {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized - logging out user');
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to delete policy';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error deleting policy:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

async function restorePolicy(policyId) {
    if (!confirm('Are you sure you want to restore this policy?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/policies/${policyId}/restore`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            showNotification('Policy restored successfully', 'success');
            loadPolicies();
            loadDeletedPolicies();
        } else {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized - logging out user');
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to restore policy';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error restoring policy:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

async function loadDeletedPolicies() {
    try {
        const response = await fetch('/api/policies/deleted', {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized - logging out user');
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            throw new Error('Failed to load deleted policies');
        }
        
        const deletedPolicies = await response.json();
        displayDeletedPolicies(deletedPolicies);
    } catch (error) {
        console.error('Error loading deleted policies:', error);
    }
}

function displayDeletedPolicies(policies) {
    const container = document.getElementById('deletedPoliciesList');
    if (!container) return;
    
    if (policies.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No deleted policies found</p></div>';
        return;
    }
    
    let html = '<div class="table-container"><table class="policies-table"><thead><tr><th>Name</th><th>Description</th><th>Action</th><th>Severity</th><th>Deleted At</th><th>Actions</th></tr></thead><tbody>';
    
    policies.forEach(policy => {
        const descriptionText = policy.description || 'No description';
        const truncatedDescription = descriptionText.length > 50 
            ? descriptionText.substring(0, 50) + '...' 
            : descriptionText;
        
        html += `
            <tr>
                <td><strong>${policy.name}</strong></td>
                <td><span title="${descriptionText}">${truncatedDescription}</span></td>
                <td><span class="badge badge-info">${policy.action}</span></td>
                <td><span class="badge badge-${policy.severity === 'high' || policy.severity === 'critical' ? 'danger' : policy.severity === 'medium' ? 'warning' : 'info'}">${policy.severity}</span></td>
                <td>${policy.updated_at ? new Date(policy.updated_at).toLocaleString() : 'N/A'}</td>
                <td>
                    <button class="btn btn-success btn-small" onclick="restorePolicy('${policy.id}')" title="Restore Policy">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
                            <path d="M21 3v5h-5"></path>
                            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
                            <path d="M3 21v-5h5"></path>
                        </svg>
                        Restore
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

async function togglePolicy(policyId, enabled) {
    try {
        // First, get the current policy
        const getResponse = await fetch(`/api/policies/${policyId}`, {
            headers: getAuthHeaders()
        });
        
        if (!getResponse.ok) {
            throw new Error('Failed to fetch policy');
        }
        
        const policy = await getResponse.json();
        
        // Update the enabled status
        const updateResponse = await fetch(`/api/policies/${policyId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                ...policy,
                enabled: enabled
            })
        });
        
        if (updateResponse.ok) {
            showNotification(`Policy ${enabled ? 'enabled' : 'disabled'} successfully`, 'success');
            loadPolicies();
        } else {
            const error = await updateResponse.json();
            const errorMsg = error.detail || error.message || 'Failed to update policy';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error toggling policy:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

async function editPolicy(policyId) {
    try {
        // Fetch the policy data
        const response = await fetch(`/api/policies/${policyId}`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch policy');
        }
        
        const policy = await response.json();
        
        // Populate the form with policy data
        document.getElementById('policyName').value = policy.name || '';
        document.getElementById('policyDescription').value = policy.description || '';
        document.getElementById('policyAction').value = policy.action || 'block';
        document.getElementById('policySeverity').value = policy.severity || 'medium';
        
        // Set entity types (multiple select)
        // Set checkboxes based on policy entity types
        const entityCheckboxes = document.querySelectorAll('input[name="policyEntities"]');
        entityCheckboxes.forEach(checkbox => {
            checkbox.checked = policy.entity_types && policy.entity_types.includes(checkbox.value);
        });
        updateSelectedEntitiesTags();
        
        // Change form to edit mode
        const form = document.getElementById('policyForm');
        const modal = document.getElementById('createPolicyForm');
        const modalTitle = modal.querySelector('.modal-header h3');
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Store policy ID for update
        form.dataset.editPolicyId = policyId;
        if (modalTitle) modalTitle.textContent = 'Edit Policy';
        if (submitBtn) submitBtn.textContent = 'Update Policy';
        
        // Change form submit handler
        form.setAttribute('onsubmit', 'updatePolicy(event); return false;');
        
        // Show modal without resetting form (we already populated it)
        modal.style.display = 'flex';
        modal.classList.add('show');
        setTimeout(() => {
            const nameInput = document.getElementById('policyName');
            if (nameInput) nameInput.focus();
        }, 100);
    } catch (error) {
        console.error('Error loading policy for edit:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

async function updatePolicy(event) {
    event.preventDefault();
    
    const form = document.getElementById('policyForm');
    const policyId = form.dataset.editPolicyId;
    
    if (!policyId) {
        showNotification('Error: Policy ID not found', 'error');
        return;
    }
    
    const policyName = document.getElementById('policyName').value.trim();
    const policyDescription = document.getElementById('policyDescription').value.trim();
    // Get selected entities from checkboxes
    const selectedEntities = Array.from(document.querySelectorAll('input[name="policyEntities"]:checked'))
        .map(checkbox => checkbox.value);
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
    
    // First, get the current policy to preserve other fields
    try {
        const getResponse = await fetch(`/api/policies/${policyId}`, {
            headers: getAuthHeaders()
        });
        
        if (!getResponse.ok) {
            throw new Error('Failed to fetch current policy');
        }
        
        const currentPolicy = await getResponse.json();
        
        const formData = {
            ...currentPolicy,
            name: policyName,
            description: policyDescription || null,
            entity_types: selectedEntities,
            action: policyAction,
            severity: policySeverity
        };
        
        const response = await fetch(`/api/policies/${policyId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showNotification('Policy updated successfully', 'success');
            closeModal();
            resetPolicyForm();
            loadPolicies();
        } else {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized - logging out user');
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to update policy';
            console.error('Policy update error:', error);
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error updating policy:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

function resetPolicyForm() {
    const form = document.getElementById('policyForm');
    if (!form) return;
    
    form.reset();
    // Clear checkboxes
    document.querySelectorAll('input[name="policyEntities"]').forEach(checkbox => {
        checkbox.checked = false;
    });
    updateSelectedEntitiesTags();
    // Restore original onsubmit from HTML
    form.setAttribute('onsubmit', 'createPolicy(event)');
    delete form.dataset.editPolicyId;
    
    const modal = document.getElementById('createPolicyForm');
    if (modal) {
        const modalTitle = modal.querySelector('.modal-header h3');
        const submitBtn = form.querySelector('button[type="submit"]');
        if (modalTitle) modalTitle.textContent = 'Create New Policy';
        if (submitBtn) submitBtn.textContent = 'Create Policy';
    }
}

// Department functions (Admin only)
async function loadDepartments() {
    try {
        if (!authToken || !currentUser || currentUser.role !== 'admin') return;
        const response = await fetch('/api/departments/', { headers: getAuthHeaders() });
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) { logout(); return; }
            throw new Error(await response.text().catch(() => 'Unknown error'));
        }
        const items = await response.json();
        displayDepartments(Array.isArray(items) ? items : []);
    } catch (e) {
        console.error('Error loading departments:', e);
        const el = document.getElementById('departmentsList');
        if (el) el.innerHTML = '<p class="error">Failed to load departments</p>';
        showNotification('Error loading departments', 'error');
    }
}

function displayDepartments(items) {
    const list = document.getElementById('departmentsList');
    if (!list) return;
    const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    if (!items || items.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>No departments. Click "Add Department" to create one.</p></div>';
        return;
    }
    let html = '<div class="table-container"><table class="policies-table"><thead><tr><th>الاسم</th><th>الوصف</th><th>إجراءات</th></tr></thead><tbody>';
    items.forEach(d => {
        const desc = (d.description || '').replace(/</g, '&lt;').substring(0, 60);
        const nameForJs = String(d.name || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        html += `<tr>
            <td>${esc(d.name)}</td>
            <td>${desc}${(d.description || '').length > 60 ? '...' : ''}</td>
            <td>
                <button type="button" class="btn btn-ghost btn-sm" onclick="editDepartment('${d.id}')">Edit</button>
                <button type="button" class="btn btn-ghost btn-sm" onclick="deleteDepartment('${d.id}', '${nameForJs}')">Delete</button>
            </td>
        </tr>`;
    });
    html += '</tbody></table></div>';
    list.innerHTML = html;
}

function showCreateDepartmentForm() {
    document.getElementById('departmentFormTitle').textContent = 'Add Department';
    document.getElementById('departmentId').value = '';
    document.getElementById('departmentName').value = '';
    document.getElementById('departmentDescription').value = '';
    const modal = document.getElementById('departmentFormModal');
    if (modal) {
        modal.classList.add('show');
        modal.style.setProperty('display', 'flex', 'important');
        modal.setAttribute('aria-hidden', 'false');
    }
}

function closeDepartmentModal() {
    const modal = document.getElementById('departmentFormModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}

function editDepartment(id) {
    fetch(`/api/departments/${id}`, { headers: getAuthHeaders() })
        .then(r => r.ok ? r.json() : Promise.reject(new Error('Failed to load')))
        .then(d => {
            document.getElementById('departmentFormTitle').textContent = 'Edit Department';
            document.getElementById('departmentId').value = d.id;
            document.getElementById('departmentName').value = d.name || '';
            document.getElementById('departmentDescription').value = d.description || '';
            const modal = document.getElementById('departmentFormModal');
            if (modal) {
                modal.classList.add('show');
                modal.style.setProperty('display', 'flex', 'important');
                modal.setAttribute('aria-hidden', 'false');
            }
        })
        .catch(e => { showNotification('Error loading department', 'error'); });
}

async function saveDepartment(event) {
    event.preventDefault();
    const id = document.getElementById('departmentId').value;
    const name = document.getElementById('departmentName').value.trim();
    const description = document.getElementById('departmentDescription').value.trim() || null;
    const url = id ? `/api/departments/${id}` : '/api/departments/';
    const method = id ? 'PUT' : 'POST';
    const body = id ? { name, description } : { name, description };
    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || res.statusText);
        }
        closeDepartmentModal();
        loadDepartments();
        showNotification(id ? 'Department updated' : 'Department created', 'success');
    } catch (e) {
        showNotification(e.message || 'Error', 'error');
    }
}

async function deleteDepartment(id, name) {
    if (!confirm(`Delete department "${name}"? Cannot delete if it has users.`)) return;
    try {
        const res = await fetch(`/api/departments/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
        if (res.status === 400) {
            const data = await res.json().catch(() => ({}));
            showNotification(data.detail || 'Cannot delete: department has users', 'error');
            return;
        }
        if (!res.ok) throw new Error(res.statusText);
        loadDepartments();
        showNotification('Department deleted', 'success');
    } catch (e) {
        showNotification(e.message || 'Error', 'error');
    }
}

// Alert functions
async function loadAlerts(page = 1) {
    try {
        // Only load if user is logged in and is admin
        if (!authToken || !currentUser || currentUser.role !== 'admin') {
            console.log('Skipping alerts load - user not admin');
            return;
        }
        
        currentAlertsPage = page;
        const limit = alertsPagination.limit || 10;
        const response = await fetch(`/api/alerts/?page=${page}&limit=${limit}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.log('Unauthorized to load alerts - logging out');
                logout();
                return;
            }
            const errorText = await response.text().catch(() => 'Unknown error');
            console.error('Alerts API error:', response.status, errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText.substring(0, 100)}`);
        }
        const data = await response.json();
        console.log('Alerts data received:', data);
        
        // Handle both paginated and non-paginated responses
        const alerts = Array.isArray(data) ? data : (data.items || []);
        alertsPagination = {
            total: data.total || alerts.length,
            total_pages: data.total_pages || 1,
            limit: data.limit || limit,
            has_next: data.has_next !== undefined ? data.has_next : (page < (data.total_pages || 1)),
            has_prev: data.has_prev !== undefined ? data.has_prev : (page > 1)
        };
        
        console.log('Alerts pagination:', alertsPagination);
        displayAlerts(alerts);
        renderPagination('alerts', currentAlertsPage, alertsPagination, loadAlerts);
    } catch (error) {
        console.error('Error loading alerts:', error);
        const alertsList = document.getElementById('alertsList');
        if (alertsList) {
            alertsList.innerHTML = `<p style="color: var(--danger);">Error loading alerts: ${error.message || 'Unknown error'}</p>`;
        }
        // Only show notification if user is admin
        if (currentUser && currentUser.role === 'admin') {
            showNotification(`Error loading alerts: ${error.message || 'Unknown error'}`, 'error');
        }
    }
}

function displayAlerts(alerts) {
    const list = document.getElementById('alertsList');
    
    if (!list) {
        console.error('alertsList element not found!');
        return;
    }
    
    // Ensure alerts is an array
    if (!alerts) {
        console.warn('Alerts data is null or undefined');
        list.innerHTML = '<div class="empty-state"><p>No alerts found. All clear!</p></div>';
        return;
    }
    
    if (!Array.isArray(alerts)) {
        console.error('Alerts is not an array:', typeof alerts, alerts);
        list.innerHTML = '<div class="empty-state"><p>Error: Invalid alerts data format</p></div>';
        return;
    }
    
    if (alerts.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <p><strong>No alerts found. All clear!</strong></p>
                <p class="empty-state-hint">Alerts appear when a policy is violated (e.g. sensitive data in analyzed text or test email). On a new installation, run Analysis or send a test email with sensitive content, then click Refresh.</p>
            </div>`;
        return;
    }
    
    console.log('Displaying alerts:', alerts.length, 'alerts');
    
    let html = `
        <div class="table-container">
            <table class="alerts-table">
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Description</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Source</th>
                        <th>To</th>
                        <th>Action</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
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
        
        // Handle description - strip HTML and truncate
        let descriptionText = alert.description || '';
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = descriptionText;
        descriptionText = tempDiv.textContent || tempDiv.innerText || '';
        
        const truncatedDescription = descriptionText.length > 50 
            ? descriptionText.substring(0, 50) + '...' 
            : descriptionText || '<span class="text-muted">No description</span>';
        
        const sourceInfo = alert.source_user 
            ? `${alert.source_user}${alert.source_ip ? ' @ ' + alert.source_ip : ''}`
            : alert.source_ip || 'Unknown';
        
        const actionTaken = alert.action_taken || (alert.blocked ? 'Blocked' : 'Alert');
        const actionBadge = alert.blocked 
            ? '<span class="badge badge-danger">Blocked</span>'
            : '<span class="badge badge-info">' + actionTaken + '</span>';
        
        const formattedDate = formatAlertTimeLocal(alert.created_at, alert.created_at_server);
        
        const toRecipients = (alert.extra_data && alert.extra_data.to) 
            ? (Array.isArray(alert.extra_data.to) ? alert.extra_data.to.join(', ') : String(alert.extra_data.to)) 
            : '—';
        
        const fullDescription = descriptionText || 'No description available';
        const alertData = {
            id: alert.id,
            title: alert.title,
            description: fullDescription,
            severity: alert.severity,
            status: alert.status,
            source_ip: alert.source_ip,
            source_user: alert.source_user,
            source_device: alert.source_device,
            action_taken: alert.action_taken,
            blocked: alert.blocked,
            created_at: alert.created_at,
            created_at_server: alert.created_at_server,
            detected_entities: alert.detected_entities || []
        };
        
        html += `
            <tr data-alert-id="${alert.id}" class="table-row-clickable" data-alert-data="${encodeURIComponent(JSON.stringify(alertData))}">
                <td><strong>${alert.title}</strong></td>
                <td><span title="${descriptionText || 'No description'}">${truncatedDescription}</span></td>
                <td><span class="badge ${severityBadge}">${alert.severity}</span></td>
                <td><span class="badge ${statusBadge}">${alert.status}</span></td>
                <td><span class="text-muted">${sourceInfo}</span></td>
                <td><span class="text-muted">${toRecipients}</span></td>
                <td>${actionBadge}</td>
                <td><span class="text-muted">${formattedDate}</span></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    list.innerHTML = html;
    
    // Add event delegation for alert row clicks
    const table = list.querySelector('table');
    if (table && !table.dataset.alertClickBound) {
        table.dataset.alertClickBound = 'true';
        table.addEventListener('click', (e) => {
            const row = e.target.closest('tr[data-alert-id]');
            if (!row) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const alertId = row.getAttribute('data-alert-id');
            const alertDataStr = row.getAttribute('data-alert-data');
            
            if (alertId && alertDataStr) {
                try {
                    const alertData = JSON.parse(decodeURIComponent(alertDataStr));
                    console.log('Alert row clicked, showing details:', alertId);
                    if (typeof window.showAlertDetails === 'function') {
                        window.showAlertDetails(alertId, alertData);
                    } else {
                        console.error('showAlertDetails function not found');
                    }
                } catch (error) {
                    console.error('Error parsing alert data:', error);
                }
            }
        });
    }
}

function showPolicyDetails(policyId, policyName, policyData) {
    // Parse the policy data if it's a string
    let policy;
    if (typeof policyData === 'string') {
        try {
            policy = JSON.parse(policyData.replace(/&quot;/g, '"'));
        } catch (e) {
            policy = { description: policyData };
        }
    } else {
        policy = policyData;
    }
    
    const description = policy.description || 'No description provided';
    const entityTypes = policy.entity_types && policy.entity_types.length > 0 
        ? policy.entity_types.join(', ')
        : 'None';
    
    const modalHtml = `
        <div class="modal-overlay show" id="policyDetailsModal" onclick="closeDetailsModal(event)">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>Policy Details: ${policyName}</h3>
                    <button class="close-btn" onclick="closeDetailsModal()">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="detail-section">
                        <h4>Description</h4>
                        <p>${description}</p>
                    </div>
                    <div class="detail-section">
                        <h4>Entity Types</h4>
                        <p>${entityTypes}</p>
                    </div>
                    <div class="detail-section">
                        <h4>Action</h4>
                        <p><span class="badge badge-info">${policy.action || 'N/A'}</span></p>
                    </div>
                    <div class="detail-section">
                        <h4>Severity</h4>
                        <p><span class="badge badge-${policy.severity === 'high' || policy.severity === 'critical' ? 'danger' : policy.severity === 'medium' ? 'warning' : 'info'}">${policy.severity || 'N/A'}</span></p>
                    </div>
                    <div class="detail-section">
                        <h4>Status</h4>
                        <p><span class="badge ${policy.enabled ? 'badge-success' : 'badge-danger'}">${policy.enabled ? 'Enabled' : 'Disabled'}</span></p>
                    </div>
                </div>
                <div class="modal-actions">
                    <button onclick="closeDetailsModal()" class="btn btn-secondary">Close</button>
                </div>
                </div>
            </div>
        `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('policyDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * Build HTML for a draggable card showing attachment/file names.
 * title defaults to 'Attachments'. attachmentContents optional: [{filename, content}] for email modal.
 */
function buildAttachmentsCardHtml(fileNames, title, attachmentContents) {
    if (!fileNames || !fileNames.length) return '';
    const cardTitle = title != null ? title : 'Attachments';
    const esc = (s) => {
        const d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    };
    const contentByFile = Array.isArray(attachmentContents)
        ? Object.fromEntries(attachmentContents.map(a => [a.filename, a.content]))
        : {};
    const listHtml = fileNames.map(name => {
        const content = contentByFile[name];
        const contentBlock = content != null && String(content).trim()
            ? `<pre class="attachment-card-content">${esc(content)}</pre>`
            : '';
        return `<div class="attachment-card-item"><span class="attachment-card-filename">${esc(name)}</span>${contentBlock}</div>`;
    }).join('');
    return `<div class="attachment-card-draggable" data-draggable-card>
        <div class="attachment-card-header" data-drag-handle><span class="attachment-card-title">${esc(cardTitle)}</span><span class="attachment-card-drag-hint" aria-hidden="true">&#8942;&#8942;</span></div>
        <div class="attachment-card-body">${listHtml}</div>
    </div>`;
}

/** Initialize drag-to-move for attachment cards inside the given container */
function initDraggableCards(container) {
    if (!container) return;
    const cards = container.querySelectorAll('.attachment-card-draggable[data-draggable-card]');
    cards.forEach(card => {
        const header = card.querySelector('[data-drag-handle]');
        if (!header) return;
        let dragging = false, startX, startY, startLeft, startTop;
        const onMouseDown = (e) => {
            if (e.button !== 0) return;
            dragging = true;
            const rect = card.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            startX = e.clientX;
            startY = e.clientY;
            card.classList.add('is-dragging');
            card.style.position = 'fixed';
            card.style.left = startLeft + 'px';
            card.style.top = startTop + 'px';
            card.style.width = rect.width + 'px';
            e.preventDefault();
        };
        const onMouseMove = (e) => {
            if (!dragging) return;
            const dx = e.clientX - startX, dy = e.clientY - startY;
            card.style.left = (startLeft + dx) + 'px';
            card.style.top = (startTop + dy) + 'px';
        };
        const onMouseUp = () => {
            if (!dragging) return;
            dragging = false;
            card.classList.remove('is-dragging');
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        header.addEventListener('mousedown', (e) => {
            onMouseDown(e);
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    });
}

function showAlertDetails(alertId, alertData) {
    // Parse the alert data if it's a string
    let alert;
    if (typeof alertData === 'string') {
        try {
            alert = JSON.parse(alertData.replace(/&quot;/g, '"'));
        } catch (e) {
            alert = { description: alertData };
        }
    } else {
        alert = alertData;
    }
    const escapeHtml = (s) => {
        const d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    };
    const description = alert.description || 'No description available';
    const sourceInfo = alert.source_user 
        ? `${alert.source_user}${alert.source_ip ? ' @ ' + alert.source_ip : ''}${alert.source_device ? ' (' + alert.source_device + ')' : ''}`
        : alert.source_ip || 'Unknown';
    
    const detectedEntities = alert.detected_entities && alert.detected_entities.length > 0
        ? alert.detected_entities.map(e => `${e.entity_type || e.type || 'Unknown'}: ${e.value || 'N/A'}`).join('<br>')
        : 'None';
    
    const formattedDate = formatAlertTimeLocal(alert.created_at, alert.created_at_server);
    
    // Use policy_name from API response if available, otherwise extract from title
    // Title is now the policy name directly
    const fullTitle = alert.title || 'Security Alert';
    let primaryTitle = fullTitle;
    let policyName = alert.policy_name || fullTitle;  // Use policy_name from API, fallback to title
    
    // If policy_name is not provided, use title as policy name (since title is now policy name)
    if (!alert.policy_name) {
        policyName = fullTitle;
    }
    
    // Primary title is the policy name
    primaryTitle = policyName || 'Security Alert';
    
    // Only show policy name if it exists and policy_id is valid
    if (!alert.policy_id) {
        // Policy was deleted, show generic message
        primaryTitle = 'Security Alert';
        policyName = null;
    }
    
    const severityClass = alert.severity === 'high' || alert.severity === 'critical' ? 'danger' : alert.severity === 'medium' ? 'warning' : 'info';
    const statusClass = alert.status === 'resolved' ? 'success' : alert.status === 'pending' ? 'warning' : alert.status === 'acknowledged' ? 'info' : 'secondary';
    const actionTaken = alert.action_taken || (alert.blocked ? 'Blocked' : 'Alert');
    const actionClass = alert.blocked ? 'danger' : 'info';
    const hasEntities = alert.detected_entities && alert.detected_entities.length > 0;
    
    // Format detected entities with better structure
    let entitiesHtml = '';
    if (hasEntities) {
        entitiesHtml = alert.detected_entities.map(e => {
            const entityType = e.entity_type || e.type || 'Unknown';
            const entityValue = e.value || 'N/A';
            return `<div class="entity-item"><span class="entity-type-badge">${entityType}</span><span class="entity-value">${entityValue}</span></div>`;
        }).join('');
    } else {
        entitiesHtml = '<span class="text-muted">No entities detected</span>';
    }
    
    // Check if description is redundant (just entity count)
    const isDescriptionRedundant = description.toLowerCase().includes('detected') && 
                                   description.toLowerCase().includes('sensitive entities');
    
    const modalHtml = `
        <div class="modal-overlay show" id="alertDetailsModal" onclick="closeDetailsModal(event)">
            <div class="modal-content alert-details-modal" onclick="event.stopPropagation()">
                <div class="alert-modal-header">
                    <div class="alert-header-content">
                        <h2 class="alert-incident-title">${primaryTitle}</h2>
                        ${policyName ? `<p class="alert-policy-name">${policyName}</p>` : ''}
                    </div>
                    <button class="close-btn alert-close-btn" onclick="closeDetailsModal()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="alert-summary-section">
                    <div class="summary-row">
                        <div class="summary-item">
                            <span class="summary-label">Severity</span>
                            <span class="badge badge-${severityClass}">${alert.severity || 'N/A'}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Status</span>
                            <span class="badge badge-${statusClass}">${alert.status || 'N/A'}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Action</span>
                            <span class="badge badge-${actionClass}">${actionTaken}</span>
                        </div>
                    </div>
                </div>
                <div class="alert-details-section">
                    ${!isDescriptionRedundant ? `<div class="detail-section">
                        <h4>Description</h4>
                        <p class="detail-value">${description}</p>
                    </div>` : ''}
                    <div class="detail-section">
                        <h4>Source</h4>
                        <p class="detail-value">${sourceInfo}</p>
                    </div>
                    ${(alert.attachment_names && alert.attachment_names.length) ? buildAttachmentsCardHtml(alert.attachment_names, 'Attachments', (alert.extra_data && alert.extra_data.attachment_contents) || []) : ''}
                    ${(alert.extra_data && (alert.extra_data.body_preview || alert.extra_data.body)) ? `<div class="detail-section"><h4>Body</h4><pre class="attachment-card-content" style="margin:0;">${escapeHtml(alert.extra_data.body_preview || alert.extra_data.body)}</pre></div>` : ''}
                    <div class="detail-section">
                        <h4>Detected Entities</h4>
                        <div class="entities-container ${!hasEntities ? 'entities-empty' : ''}">${entitiesHtml}</div>
                    </div>
                    <div class="detail-section">
                        <h4>Created At</h4>
                        <p class="detail-value">${formattedDate}</p>
                    </div>
                </div>
                <div class="alert-modal-actions">
                    <button onclick="closeDetailsModal()" class="btn btn-secondary">Close</button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('alertDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modalEl = document.getElementById('alertDetailsModal');
    if (modalEl && typeof initDraggableCards === 'function') initDraggableCards(modalEl);
}

function closeDetailsModal(event) {
    if (event && event.target !== event.currentTarget) {
        return;
    }
    const modals = document.querySelectorAll('#policyDetailsModal, #alertDetailsModal, #userActivityModal, #operationDetailsModal, #emailDetailModal');
    modals.forEach(modal => {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    });
}

async function updateAlertStatus(alertId) {
    try {
        // Get current alert
        const response = await fetch(`/api/alerts/${alertId}`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch alert');
        }
        
        const alert = await response.json();
        
        // Show status selection dialog
        const newStatus = prompt(
            `Update alert status:\n\nCurrent: ${alert.status}\n\nOptions:\n- pending\n- acknowledged\n- resolved\n- false_positive\n\nEnter new status:`,
            alert.status
        );
        
        if (!newStatus || newStatus === alert.status) {
            return;
        }
        
        const validStatuses = ['pending', 'acknowledged', 'resolved', 'false_positive'];
        if (!validStatuses.includes(newStatus.toLowerCase())) {
            showNotification('Invalid status. Must be one of: pending, acknowledged, resolved, false_positive', 'error');
            return;
        }
        
        // Update alert
        const updateResponse = await fetch(`/api/alerts/${alertId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                status: newStatus.toLowerCase(),
                resolved_by: currentUser ? currentUser.username : null
            })
        });
        
        if (updateResponse.ok) {
            showNotification('Alert status updated successfully', 'success');
            loadAlerts();
        } else {
            const error = await updateResponse.json();
            const errorMsg = error.detail || error.message || 'Failed to update alert';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error updating alert status:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

// Monitoring functions
async function loadMonitoringData(page = 1) {
    try {
        // Only load if user is logged in and is admin
        if (!authToken || !currentUser || currentUser.role !== 'admin') {
            console.log('Skipping monitoring data load - user not admin');
            return;
        }
        
        currentMonitoringPage = page;
        const headers = getAuthHeaders();
        const [statusResponse, summaryResponse, emailStatsResponse, logsResponse] = await Promise.all([
            fetch('/api/monitoring/status', { headers }),
            fetch('/api/monitoring/reports/summary?days=7', { headers }),
            fetch('/api/monitoring/email/statistics?days=7', { headers }),
            fetch(`/api/monitoring/reports/logs?page=${page}&limit=${monitoringPagination.limit}`, { headers })
        ]);
        
        // Check if main responses are ok
        if (!statusResponse.ok) {
            if (statusResponse.status === 401 || statusResponse.status === 403) {
                console.log('Unauthorized to load monitoring data');
                return;
            }
            const errorText = await statusResponse.text().catch(() => 'Unknown error');
            throw new Error(`Status API error (${statusResponse.status}): ${errorText.substring(0, 100)}`);
        }
        
        if (!summaryResponse.ok) {
            if (summaryResponse.status === 401 || summaryResponse.status === 403) {
                console.log('Unauthorized to load summary data');
                return;
            }
            const errorText = await summaryResponse.text().catch(() => 'Unknown error');
            throw new Error(`Summary API error (${summaryResponse.status}): ${errorText.substring(0, 100)}`);
        }
        
        // Parse responses
        const status = await statusResponse.json();
        const summary = await summaryResponse.json();
        const emailStats = emailStatsResponse.ok ? await emailStatsResponse.json().catch(() => null) : null;
        const logsData = logsResponse.ok ? await logsResponse.json().catch(() => null) : null;
        
        // Handle logs pagination
        if (logsData) {
            const logs = logsData.items || logsData.logs || [];
            monitoringPagination = {
                total: logsData.total || logs.length,
                total_pages: logsData.total_pages || 1,
                limit: logsData.limit || monitoringPagination.limit,
                has_next: logsData.has_next || false,
                has_prev: logsData.has_prev || false
            };
        }
        
        // Debug: Log MyDLP status from API
        console.log('MyDLP status from API:', {
            enabled: status.mydlp?.enabled,
            status: status.mydlp?.status,
            is_localhost: status.mydlp?.is_localhost,
            full_mydlp: status.mydlp
        });
        
        // Display data
        displayMonitoringData(status, summary, emailStats, logsData);
    } catch (error) {
        console.error('Error loading monitoring data:', error);
        const monitoringData = document.getElementById('monitoringData');
        if (monitoringData) {
            // Show a more user-friendly error message
            const errorMessage = error.message || 'Unknown error';
            try {
                monitoringData.innerHTML = `<p style="color: var(--danger);">Error loading data: ${errorMessage.substring(0, 100)}</p>`;
            } catch (e) {
                console.error('Error setting monitoringData innerHTML:', e);
            }
        } else {
            console.error('monitoringData element not found');
        }
        // Only show notification if it's a critical error (not 401/403)
        if (currentUser && currentUser.role === 'admin') {
            // Don't show notification for authorization errors (user already knows)
            if (!error.message || (!error.message.includes('401') && !error.message.includes('403'))) {
                showNotification(`Error loading monitoring data: ${error.message || 'Unknown error'}`, 'error');
            }
        }
    }
}

function displayMonitoringData(status, summary, emailStats, logsData = null) {
    const container = document.getElementById('monitoringData');
    
    if (!container) {
        console.error('monitoringData container not found');
        return;
    }
    
    // Validate data structure
    if (!container) {
        console.error('monitoringData container not found in displayMonitoringData');
        return;
    }
    
    if (!summary || !summary.summary) {
        console.error('Invalid summary data structure:', summary);
        try {
            container.innerHTML = '<p style="color: var(--danger);">Error: Invalid data structure</p>';
        } catch (e) {
            console.error('Error setting container innerHTML:', e);
        }
        return;
    }
    
    if (!status) {
        console.error('Invalid status data structure:', status);
        try {
            container.innerHTML = '<p style="color: var(--danger);">Error: Invalid status data</p>';
        } catch (e) {
            console.error('Error setting container innerHTML:', e);
        }
        return;
    }
    
    let html = '<div class="stats-grid">';
    html += `
        <div class="stat-card">
            <p>Total Logs</p>
            <h3>${summary.summary.total_logs || 0}</h3>
        </div>
        <div class="stat-card">
            <p>Detected Entities</p>
            <h3>${summary.summary.total_detected_entities || 0}</h3>
        </div>
        <div class="stat-card">
            <p>Total Alerts</p>
            <h3>${summary.summary.total_alerts || 0}</h3>
        </div>
        <div class="stat-card">
            <p>Blocked Attempts</p>
            <h3>${summary.summary.blocked_attempts || 0}</h3>
        </div>
    `;
    html += '</div>';
    
    // Entity Type Distribution
    if (summary.entity_type_breakdown && Object.keys(summary.entity_type_breakdown).length > 0) {
    html += '<h3 style="margin-top: 32px; margin-bottom: 16px; color: var(--dark);">Entity Type Distribution</h3>';
    html += '<div class="stats-grid">';
        for (const [entityType, count] of Object.entries(summary.entity_type_breakdown)) {
        html += `
            <div class="stat-card">
                <p>${entityType}</p>
                    <h3>${count || 0}</h3>
            </div>
        `;
    }
    html += '</div>';
    }
    
    // System Status
    html += `<h3 style="margin-top: 32px; margin-bottom: 16px; color: var(--dark);">System Status</h3>`;
    html += `<div class="status-grid">`;
    
    // Presidio status
    const presidioStatus = (status.presidio && status.presidio.status) ? status.presidio.status : 'unknown';
    html += `<div class="status-item"><strong>Presidio:</strong> <span class="badge badge-success">${presidioStatus}</span></div>`;
    
    // MyDLP status
    if (status.mydlp) {
        // Debug: Log what we're checking
        console.log('Displaying MyDLP status:', {
            enabled: status.mydlp.enabled,
            enabled_type: typeof status.mydlp.enabled,
            enabled_strict: status.mydlp.enabled === true,
            status: status.mydlp.status,
            is_localhost: status.mydlp.is_localhost
        });
        
        // Check enabled status - handle both boolean true and string "true"
        // Also handle case where enabled might be a string "True" or number 1
        const mydlpEnabled = status.mydlp.enabled === true || 
                            status.mydlp.enabled === "true" || 
                            status.mydlp.enabled === "True" ||
                            status.mydlp.enabled === 1;
        const mydlpStatus = mydlpEnabled 
            ? `${status.mydlp.status || 'operational'}${status.mydlp.is_localhost ? ' (Localhost Mode)' : ' (Network Mode)'}`
        : 'Disabled';
        const mydlpBadgeClass = mydlpEnabled ? 'badge-success' : 'badge-secondary';
        html += `<div class="status-item"><strong>MyDLP:</strong> <span class="badge ${mydlpBadgeClass}">${mydlpStatus}</span></div>`;
    } else {
        console.warn('MyDLP status not found in API response:', status);
        html += `<div class="status-item"><strong>MyDLP:</strong> <span class="badge badge-secondary">Unknown</span></div>`;
    }
    
    html += `</div>`;
    
    container.innerHTML = html;
    
    // Display logs if available
    if (logsData) {
        const logs = Array.isArray(logsData) ? logsData : (logsData.items || logsData.logs || []);
        if (Array.isArray(logs)) {
            displayMonitoringLogs(logs);
            renderPagination('monitoring', currentMonitoringPage, monitoringPagination, loadMonitoringData);
        } else {
            console.warn('Logs data is not an array:', typeof logs, logs);
        }
    }
    
    // Display email statistics if available
    if (emailStats) {
        displayEmailStats(emailStats);
    }
}

function displayMonitoringLogs(logs) {
    let container = document.getElementById('monitoringLogs');
    if (!container) {
        // Create logs container if it doesn't exist
        const monitoringData = document.getElementById('monitoringData');
        if (!monitoringData) {
            console.error('monitoringData container not found');
            return;
        }
        container = document.createElement('div');
        container.id = 'monitoringLogs';
        container.className = 'monitoring-logs-section';
        monitoringData.appendChild(container);
    }
    
    // Ensure logs is an array
    if (!logs || !Array.isArray(logs)) {
        console.warn('Logs is not an array:', typeof logs, logs);
        container.innerHTML = '<div class="empty-state"><p>No logs found</p></div>';
        return;
    }
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No logs found</p></div>';
        return;
    }
    
    let html = '<h3 style="margin-top: 24px; margin-bottom: 16px;">Recent Logs</h3><div class="table-container"><table class="logs-table"><thead><tr><th>Time</th><th>Event Type</th><th>Level</th><th>Message</th><th>Source</th><th>To</th></tr></thead><tbody>';
    
    logs.forEach(log => {
        const time = log.created_at_server || (log.created_at ? new Date(log.created_at).toLocaleString() : 'N/A');
        const toRecipients = (log.metadata && log.metadata.to) ? (Array.isArray(log.metadata.to) ? log.metadata.to.join(', ') : String(log.metadata.to)) : '—';
        html += `
            <tr>
                <td>${time}</td>
                <td><span class="badge badge-info">${log.event_type || 'N/A'}</span></td>
                <td><span class="badge badge-${log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : 'info'}">${log.level || 'info'}</span></td>
                <td>${log.message || 'N/A'}</td>
                <td>${log.source_user || log.source_ip || 'N/A'}</td>
                <td><span class="text-muted">${toRecipients}</span></td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

let currentMonitoringUsersPage = 1;
let monitoringUsersPagination = { total: 0, total_pages: 0, limit: 10 };
let lastMonitoringUserSearch = '';

async function searchMonitoringUsers(page = 1) {
    const input = document.getElementById('monitoringUserSearchInput');
    const query = input ? input.value.trim() : '';
    if (!query) {
        const container = document.getElementById('monitoringUsersList');
        if (container) {
            container.innerHTML = '<div class="empty-state"><p>Type an email or username to search.</p></div>';
        }
        return;
    }
    await loadMonitoringUsers(query, page);
}

async function loadMonitoringUsers(searchQuery, page = 1) {
    if (!authToken || !currentUser || currentUser.role !== 'admin') {
        showNotification('Admin access required', 'error');
        return;
    }
    const query = (searchQuery || '').trim();
    if (!query) return;

    try {
        lastMonitoringUserSearch = query;
        currentMonitoringUsersPage = page;
        const params = new URLSearchParams();
        params.append('search', query);
        params.append('page', String(page));
        params.append('limit', String(monitoringUsersPagination.limit));

        const response = await fetch(`/api/users/?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            if (response.status === 401) {
                logout();
                throw new Error('Session expired. Please login again.');
            }
            throw new Error('Failed to search users');
        }

        const data = await response.json();
        const users = Array.isArray(data) ? data : (data.items || []);
        monitoringUsersPagination = {
            total: data.total || users.length,
            total_pages: data.total_pages || 1,
            limit: data.limit || monitoringUsersPagination.limit,
            has_next: data.has_next || false,
            has_prev: data.has_prev || false
        };

        displayMonitoringUsers(users);
        renderPagination('monitoringUsers', currentMonitoringUsersPage, monitoringUsersPagination, loadMonitoringUsersPage);
    } catch (error) {
        showNotification('Error searching users: ' + error.message, 'error');
    }
}

function loadMonitoringUsersPage(page) {
    return loadMonitoringUsers(lastMonitoringUserSearch, page);
}

function displayMonitoringUsers(users) {
    const container = document.getElementById('monitoringUsersList');
    if (!container) return;

    if (!Array.isArray(users) || users.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No matching users found.</p></div>';
        return;
    }

    let html = `
        <div class="table-container">
            <table class="users-table">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Activity</th>
                    </tr>
                </thead>
                <tbody>
    `;

    users.forEach(user => {
        const status = user.status || 'unknown';
        const statusBadge = status === 'active' || status === 'approved'
            ? '<span class="badge badge-success">' + status + '</span>'
            : status === 'pending'
            ? '<span class="badge badge-warning">' + status + '</span>'
            : '<span class="badge badge-secondary">' + status + '</span>';
        const roleBadge = user.role === 'admin'
            ? '<span class="badge badge-danger">admin</span>'
            : '<span class="badge badge-info">regular</span>';

        html += `
            <tr class="table-row-clickable" data-user-id="${user.id}" onclick="showUserActivityModal('${user.id}')">
                <td><strong>${user.username || 'N/A'}</strong></td>
                <td>${user.email || 'N/A'}</td>
                <td>${roleBadge}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-secondary btn-small" onclick="event.stopPropagation(); showUserActivityModal('${user.id}')">
                        View Activity
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

const USER_ACTIVITY_PAGE_SIZE = 20;

function buildUserActivityTableRows(operations, escapeHtml) {
    if (!operations.length) {
        return '<tr><td colspan="7" class="text-muted">No operations found for this period.</td></tr>';
    }
    return operations.map((op, idx) => {
        const metadata = op.metadata ? JSON.stringify(op.metadata, null, 2) : '';
        const time = op.timestamp_server || (op.timestamp ? new Date(op.timestamp).toLocaleString() : 'N/A');
        const fileDisplay = op.file_name || (op.metadata && op.metadata.attachment_names && op.metadata.attachment_names.length ? op.metadata.attachment_names.join(', ') : 'N/A');
        const toRecipients = (op.metadata && op.metadata.to) ? (Array.isArray(op.metadata.to) ? op.metadata.to.join(', ') : String(op.metadata.to)) : '—';
        return `
            <tr class="table-row-clickable" data-op-index="${idx}" title="Click to view operation details">
                <td>${escapeHtml(op.event_type || 'N/A')}</td>
                <td>${escapeHtml(op.message || 'N/A')}</td>
                <td>${escapeHtml(time)}</td>
                <td>${escapeHtml(op.source_ip || 'N/A')}</td>
                <td><span class="text-muted">${escapeHtml(toRecipients)}</span></td>
                <td>${escapeHtml(fileDisplay)}</td>
                <td><pre class="activity-metadata">${escapeHtml(metadata || '—')}</pre></td>
            </tr>
        `;
    }).join('');
}

function buildUserActivityPagination(pagination, userId) {
    if (!pagination || pagination.total_pages <= 1) return '';
    const { page, total_pages, total } = pagination;
    let html = '<div class="pagination" style="margin-top:12px;flex-wrap:wrap;gap:6px;">';
    if (pagination.has_prev) {
        html += `<button type="button" class="btn btn-secondary btn-small" onclick="loadUserActivityPage('${userId}', ${page - 1})">Prev</button> `;
    }
    html += `<span class="text-muted" style="align-self:center;">Page ${page} of ${total_pages} (${total} total)</span>`;
    if (pagination.has_next) {
        html += ` <button type="button" class="btn btn-secondary btn-small" onclick="loadUserActivityPage('${userId}', ${page + 1})">Next</button>`;
    }
    html += '</div>';
    return html;
}

async function loadUserActivityPage(userId, page) {
    const modal = document.getElementById('userActivityModal');
    if (!modal) return;
    const tbody = modal.querySelector('.logs-table tbody');
    const paginationContainer = modal.querySelector('#userActivityPagination') || modal.querySelector('.user-activity-pagination');
    if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="text-muted">Loading…</td></tr>';
    try {
        const limit = USER_ACTIVITY_PAGE_SIZE;
        const response = await fetch(`/api/monitoring/user-activities/${encodeURIComponent(userId)}?days=30&page=${page}&limit=${limit}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error('Failed to load page');
        const data = await response.json();
        const operations = (data.operations && Array.isArray(data.operations.all)) ? data.operations.all : [];
        const escapeHtml = (value) => {
            const div = document.createElement('div');
            div.textContent = value == null ? '' : String(value);
            return div.innerHTML;
        };
        window._lastUserActivityOperations = operations;
        if (tbody) tbody.innerHTML = buildUserActivityTableRows(operations, escapeHtml);
        if (data.pagination && paginationContainer) {
            paginationContainer.innerHTML = buildUserActivityPagination(data.pagination, userId);
        }
        modal.querySelectorAll('tr.table-row-clickable').forEach(tr => {
            tr.onclick = function () {
                const idx = parseInt(this.getAttribute('data-op-index'), 10);
                if (!isNaN(idx) && window._lastUserActivityOperations && window._lastUserActivityOperations[idx]) {
                    showOperationDetailsModal(window._lastUserActivityOperations[idx], window._lastUserActivityUser);
                }
            };
        });
    } catch (e) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="text-danger">Error loading page.</td></tr>';
        showNotification('Error loading user activity page', 'error');
    }
}

async function showUserActivityModal(userId) {
    if (!userId) return;
    try {
        const limit = USER_ACTIVITY_PAGE_SIZE;
        const response = await fetch(`/api/monitoring/user-activities/${encodeURIComponent(userId)}?days=30&page=1&limit=${limit}`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error('Failed to load user activity');
        }
        const data = await response.json();
        const operations = (data.operations && Array.isArray(data.operations.all)) ? data.operations.all : [];
        const summary = data.summary || {};
        const pagination = data.pagination || {};

        const escapeHtml = (value) => {
            const div = document.createElement('div');
            div.textContent = value == null ? '' : String(value);
            return div.innerHTML;
        };

        const operationsRows = buildUserActivityTableRows(operations, escapeHtml);
        window._lastUserActivityOperations = operations;
        window._lastUserActivityUser = { username: data.username || '', email: data.email || '' };

        const paginationHtml = buildUserActivityPagination(pagination, userId);

        const modalHtml = `
            <div class="modal-overlay show" id="userActivityModal" data-user-id="${escapeHtml(userId)}" onclick="closeDetailsModal(event)">
                <div class="modal-content" style="max-width: 1100px;" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>User Activity Log</h3>
                        <button class="close-btn" onclick="closeDetailsModal()">&times;</button>
                    </div>
                    <div style="padding: 20px; overflow:auto;">
                        <div class="stats-grid" style="margin-bottom: 16px;">
                            <div class="stat-card"><p>User</p><h3>${escapeHtml(data.username || 'N/A')}</h3></div>
                            <div class="stat-card"><p>Email</p><h3>${escapeHtml(data.email || 'N/A')}</h3></div>
                            <div class="stat-card"><p>Total Operations</p><h3>${summary.total_operations ?? 0}</h3></div>
                            <div class="stat-card"><p>Analysis Operations</p><h3>${summary.analysis_operations ?? 0}</h3></div>
                        </div>
                        <p class="text-muted" style="margin-bottom: 8px; font-size: 0.9rem;">Click a row to view operation details, policy violated, and related data.</p>
                        <div class="table-container">
                            <table class="logs-table">
                                <thead>
                                    <tr>
                                        <th>Event Type</th>
                                        <th>Message</th>
                                        <th>Timestamp</th>
                                        <th>Source IP</th>
                                        <th>To</th>
                                        <th>File</th>
                                        <th>Metadata</th>
                                    </tr>
                                </thead>
                                <tbody>${operationsRows}</tbody>
                            </table>
                        </div>
                        <div class="user-activity-pagination" id="userActivityPagination">${paginationHtml}</div>
                    </div>
                    <div class="modal-actions" style="padding: 16px 20px; border-top: 1px solid #e5e7eb;">
                        <button class="btn btn-secondary" onclick="closeDetailsModal()">Close</button>
                    </div>
                </div>
            </div>
        `;

        const existing = document.getElementById('userActivityModal');
        if (existing) existing.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        document.querySelectorAll('#userActivityModal tr.table-row-clickable').forEach(tr => {
            tr.addEventListener('click', function () {
                const idx = parseInt(this.getAttribute('data-op-index'), 10);
                if (!isNaN(idx) && window._lastUserActivityOperations && window._lastUserActivityOperations[idx]) {
                    showOperationDetailsModal(window._lastUserActivityOperations[idx], window._lastUserActivityUser);
                }
            });
        });
    } catch (error) {
        showNotification('Error loading user activity: ' + error.message, 'error');
    }
}

function showOperationDetailsModal(operation, userInfo) {
    if (!operation) return;
    const escapeHtml = (value) => {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    };
    const meta = operation.metadata || {};
    const policyNames = operation.policy_names || [];
    const hasPolicyViolation = policyNames.length > 0;
    const blocked = meta.blocked === true;
    const entityCount = meta.detected_entities_count != null ? meta.detected_entities_count : 0;
    const entityTypes = meta.detected_entity_types || [];
    const sourceUser = operation.source_user || userInfo.username || userInfo.email || 'N/A';
    const sourceInfo = sourceUser + (operation.source_ip ? ' @ ' + operation.source_ip : '');
    const formattedDate = operation.timestamp_server || (operation.timestamp
        ? new Date(operation.timestamp).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : 'N/A');
    const title = (operation.event_type || 'Operation').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const actionTaken = blocked ? 'Blocked' : (hasPolicyViolation ? 'Policy applied' : 'Logged');
    const actionClass = blocked ? 'danger' : hasPolicyViolation ? 'warning' : 'info';
    let entitiesHtml = '';
    if (entityCount > 0 || entityTypes.length > 0) {
        const types = entityTypes.length ? entityTypes : (entityCount > 0 ? ['See metadata'] : []);
        entitiesHtml = types.map(t => `<div class="entity-item"><span class="entity-type-badge">${escapeHtml(t)}</span></div>`).join('');
        if (entityCount > 0 && !entityTypes.length) {
            entitiesHtml = `<div class="entity-item"><span class="entity-type-badge">Count</span><span class="entity-value">${entityCount} detected</span></div>` + entitiesHtml;
        }
    } else {
        entitiesHtml = '<span class="text-muted">No entity details in this log</span>';
    }
    const policySection = hasPolicyViolation
        ? `<div class="detail-section">
            <h4>Policy / Policies Violated</h4>
            <p class="detail-value">${policyNames.map(p => escapeHtml(p)).join(', ')}</p>
          </div>`
        : (meta.policies_applied === 0 ? '<div class="detail-section"><h4>Policy</h4><p class="text-muted">No matching policy (entities detected but no policy matched)</p></div>' : '');
    const fileSection = operation.file_name
        ? buildAttachmentsCardHtml([operation.file_name + (operation.file_size ? ' (' + operation.file_size + ' bytes)' : '')], 'File')
        : '';
    const attachmentNames = meta.attachment_names || [];
    const attachmentContents = meta.attachment_contents || [];
    const attachmentSection = attachmentNames.length
        ? buildAttachmentsCardHtml(attachmentNames, 'Attachments', attachmentContents)
        : '';
    const networkSection = operation.network_destination
        ? `<div class="detail-section"><h4>Network</h4><p class="detail-value">${escapeHtml(operation.network_destination)}${operation.network_protocol ? ' (' + operation.network_protocol + ')' : ''}</p></div>`
        : '';
    const modalHtml = `
        <div class="modal-overlay show" id="operationDetailsModal" onclick="closeDetailsModal(event)">
            <div class="modal-content alert-details-modal" onclick="event.stopPropagation()">
                <div class="alert-modal-header">
                    <div class="alert-header-content">
                        <h2 class="alert-incident-title">${escapeHtml(title)}</h2>
                        <p class="alert-policy-name">Operation details</p>
                    </div>
                    <button class="close-btn alert-close-btn" onclick="closeDetailsModal()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="alert-summary-section">
                    <div class="summary-row">
                        <div class="summary-item">
                            <span class="summary-label">Action</span>
                            <span class="badge badge-${actionClass}">${actionTaken}</span>
                        </div>
                        ${blocked ? '<div class="summary-item"><span class="summary-label">Blocked</span><span class="badge badge-danger">Yes</span></div>' : ''}
                    </div>
                </div>
                <div class="alert-details-section">
                    <div class="detail-section">
                        <h4>Description</h4>
                        <p class="detail-value">${escapeHtml(operation.message || 'N/A')}</p>
                    </div>
                    <div class="detail-section">
                        <h4>Source</h4>
                        <p class="detail-value">${escapeHtml(sourceInfo)}</p>
                    </div>
                    ${policySection}
                    <div class="detail-section">
                        <h4>Detected Entities</h4>
                        <div class="entities-container">${entitiesHtml}</div>
                    </div>
                    ${fileSection}
                    ${attachmentSection}
                    ${networkSection}
                    <div class="detail-section">
                        <h4>Created At</h4>
                        <p class="detail-value">${formattedDate}</p>
                    </div>
                </div>
                <div class="alert-modal-actions">
                    <button onclick="closeDetailsModal()" class="btn btn-secondary">Close</button>
                </div>
            </div>
        </div>
    `;
    const existingModal = document.getElementById('operationDetailsModal');
    if (existingModal) existingModal.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const opModal = document.getElementById('operationDetailsModal');
    if (opModal && typeof initDraggableCards === 'function') initDraggableCards(opModal);
}

// Pagination rendering function
function renderPagination(section, currentPage, pagination, loadFunction) {
    const containerId = `${section}Pagination`;
    let container = document.getElementById(containerId);
    
    if (!container) {
        // Create pagination container
        const parentContainer = document.getElementById(`${section}List`) || 
                               document.getElementById(`${section}Data`) ||
                               document.getElementById('policiesList') ||
                               document.getElementById('usersList') ||
                               document.getElementById('alertsList') ||
                               document.getElementById('monitoringData') ||
                               document.getElementById('monitoringLogs');
        
        if (!parentContainer) {
            console.warn(`Parent container not found for pagination: ${section}`);
            return;
        }
        
        container = document.createElement('div');
        container.id = containerId;
        container.className = 'pagination';
        parentContainer.appendChild(container);
    }
    
    if (pagination.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    const total = pagination.total;
    const totalPages = pagination.total_pages;
    const start = (currentPage - 1) * pagination.limit + 1;
    const end = Math.min(currentPage * pagination.limit, total);
    
    let html = `
        <div class="pagination-info">
            Showing ${start}-${end} of ${total}
        </div>
        <div class="pagination-controls">
    `;
    
    // Previous button
    html += `
        <button class="pagination-btn" onclick="${loadFunction.name}(${currentPage - 1})" ${!pagination.has_prev ? 'disabled' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
        </button>
    `;
    
    // Page numbers
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    if (startPage > 1) {
        html += `<button class="pagination-btn" onclick="${loadFunction.name}(1)">1</button>`;
        if (startPage > 2) {
            html += `<span class="pagination-ellipsis">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="${loadFunction.name}(${i})">
                ${i}
            </button>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `<span class="pagination-ellipsis">...</span>`;
        }
        html += `<button class="pagination-btn" onclick="${loadFunction.name}(${totalPages})">${totalPages}</button>`;
    }
    
    // Next button
    html += `
        <button class="pagination-btn" onclick="${loadFunction.name}(${currentPage + 1})" ${!pagination.has_next ? 'disabled' : ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
        </button>
    `;
    
    html += '</div>';
    container.innerHTML = html;
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


function showEmailTestForm() {
    // Switch to Test Email tab
    const testEmailTabBtn = document.getElementById('testEmailTabBtn');
    if (testEmailTabBtn) {
        showTab('testEmail', testEmailTabBtn);
    }
}

function closeEmailModal() {
    // No longer needed - using tab instead of modal
}

/** Read a File as base64 string (for email attachments) */
function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const dataUrl = reader.result;
            const base64 = dataUrl.indexOf(',') >= 0 ? dataUrl.split(',')[1] : dataUrl;
            resolve(base64 || null);
        };
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
    });
}

function resetEmailForm() {
    const emailTo = document.getElementById('emailTo');
    const emailSubject = document.getElementById('emailSubject');
    const emailBody = document.getElementById('emailBody');
    const emailTestResult = document.getElementById('emailTestResult');
    const emailFrom = document.getElementById('emailFrom');
    const emailAttachments = document.getElementById('emailAttachments');
    
    // Reset all fields except emailFrom (which is disabled and auto-filled)
    if (emailTo) emailTo.value = 'external@example.com';
    if (emailSubject) emailSubject.value = 'Customer Data Request';
    if (emailBody) emailBody.value = `Dear Customer,

Please find your information below:
Phone: 123-456-7890
Email: customer@example.com
Address: 123 Main St, City, State 12345

Best regards,
Employee`;
    if (emailAttachments) emailAttachments.value = '';
    // Keep emailFrom as current user's email (don't reset it)
    if (emailFrom && currentUser && currentUser.email) {
        emailFrom.value = currentUser.email;
    }
    if (emailTestResult) {
        emailTestResult.style.display = 'none';
        emailTestResult.innerHTML = '';
    }
}

async function loadEmailList(page) {
    const container = document.getElementById('emailListContainer');
    if (!container) return;
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    try {
        const headers = getAuthHeaders();
        const response = await fetch(`/api/monitoring/email/list?page=${page || 1}&limit=20`, { headers });
        if (!response.ok) {
            if (response.status === 401) {
                container.innerHTML = '<p class="text-muted">Sign in to see emails sent to you.</p>';
                return;
            }
            throw new Error(response.statusText || 'Failed to load');
        }
        const data = await response.json();
        const logs = data.logs || [];
        if (logs.length === 0) {
            container.innerHTML = '<p class="text-muted">No emails sent to you yet.</p>';
            return;
        }
        const escapeHtml = (v) => {
            const d = document.createElement('div');
            d.textContent = v == null ? '' : String(v);
            return d.innerHTML;
        };
        let html = '<div class="table-container"><table class="logs-table"><thead><tr><th>From</th><th>To</th><th>Subject</th><th>Date</th><th>Attachments</th></tr></thead><tbody>';
        logs.forEach(log => {
            const ed = log.email_data || {};
            const from = ed.from || '—';
            const to = Array.isArray(ed.to) ? ed.to.join(', ') : (ed.to || '—');
            const subject = ed.subject || '—';
            const date = log.created_at_server || (log.created_at ? new Date(log.created_at).toLocaleString() : '—');
            const attCount = ed.attachment_count > 0 ? ed.attachment_count : (ed.attachment_names && ed.attachment_names.length ? ed.attachment_names.length : 0);
            const attLabel = attCount > 0 ? attCount + ' file(s)' : '—';
            html += `<tr class="table-row-clickable" data-log-id="${escapeHtml(log.id)}" title="Click to view email">`;
            html += `<td>${escapeHtml(from)}</td><td>${escapeHtml(to)}</td><td>${escapeHtml(subject)}</td><td>${escapeHtml(date)}</td><td>${escapeHtml(attLabel)}</td></tr>`;
        });
        html += '</tbody></table></div>';
        if (data.total > 20) {
            const totalPages = Math.ceil(data.total / 20) || 1;
            html += '<div class="pagination" style="margin-top:12px;">';
            for (let p = 1; p <= Math.min(totalPages, 10); p++) {
                html += `<button type="button" class="btn btn-secondary btn-small" ${p === page ? 'disabled' : ''} onclick="loadEmailList(${p})">${p}</button> `;
            }
            html += '</div>';
        }
        container.innerHTML = html;
        container.querySelectorAll('tr.table-row-clickable').forEach(tr => {
            tr.addEventListener('click', function () {
                const logId = this.getAttribute('data-log-id');
                const log = logs.find(l => String(l.id) === logId);
                if (log) showEmailDetailModal(log);
            });
        });
    } catch (e) {
        container.innerHTML = `<p class="text-danger">Error: ${(e.message || String(e)).replace(/</g, '&lt;')}</p>`;
    }
}

function showEmailDetailModal(log) {
    if (!log || !log.email_data) return;
    const ed = log.email_data;
    const escapeHtml = (v) => {
        const d = document.createElement('div');
        d.textContent = v == null ? '' : String(v);
        return d.innerHTML;
    };
    const from = ed.from || '—';
    const to = Array.isArray(ed.to) ? ed.to.join(', ') : (ed.to || '—');
    const subject = ed.subject || '—';
    const date = log.created_at_server || (log.created_at ? new Date(log.created_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');
    const attachmentNames = ed.attachment_names || [];
    const attachmentContents = ed.attachment_contents || [];
    const attachmentsHtml = attachmentNames.length
        ? buildAttachmentsCardHtml(attachmentNames, 'Attachments', attachmentContents)
        : '<p class="text-muted">None</p>';
    const bodyPreview = ed.encrypted_body != null ? ed.encrypted_body : ed.body_preview;
    const bodyLabel = ed.encrypted_body != null ? 'Body (encrypted)' : 'Body';
    const bodyHtml = bodyPreview
        ? '<pre class="activity-metadata" style="max-height:200px;overflow:auto;white-space:pre-wrap;">' + escapeHtml(bodyPreview) + '</pre>'
        : '<p class="text-muted">Body was not stored.</p>';
    const modalHtml = `
        <div class="modal-overlay show" id="emailDetailModal" onclick="closeDetailsModal(event)">
            <div class="modal-content alert-details-modal" style="max-width:560px;" onclick="event.stopPropagation()">
                <div class="alert-modal-header">
                    <div class="alert-header-content">
                        <h2 class="alert-incident-title">Email</h2>
                    </div>
                    <button class="close-btn alert-close-btn" onclick="closeDetailsModal()">&times;</button>
                </div>
                <div class="alert-details-section">
                    <div class="detail-section"><h4>From</h4><p class="detail-value">${escapeHtml(from)}</p></div>
                    <div class="detail-section"><h4>To</h4><p class="detail-value">${escapeHtml(to)}</p></div>
                    <div class="detail-section"><h4>Subject</h4><p class="detail-value">${escapeHtml(subject)}</p></div>
                    <div class="detail-section"><h4>Date</h4><p class="detail-value">${escapeHtml(date)}</p></div>
                    <div class="detail-section"><h4>Attachments</h4>${attachmentsHtml}</div>
                    <div class="detail-section"><h4>${bodyLabel}</h4>${bodyHtml}</div>
                </div>
                <div class="alert-modal-actions">
                    <button onclick="closeDetailsModal()" class="btn btn-secondary">Close</button>
                </div>
            </div>
        </div>
    `;
    const existing = document.getElementById('emailDetailModal');
    if (existing) existing.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const emailModal = document.getElementById('emailDetailModal');
    if (emailModal && typeof initDraggableCards === 'function') initDraggableCards(emailModal);
}

async function decryptEmailContent(buttonElement) {
    const modal = document.getElementById('emailDetailModal');
    if (!modal) return;
    const contentEl = modal.querySelector('[data-log-id]');
    const logId = contentEl ? contentEl.getAttribute('data-log-id') : null;
    if (!logId) {
        showNotification('Cannot get email id.', 'error');
        return;
    }
    const btn = buttonElement;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Decrypting...';
    const decryptedDiv = document.getElementById('emailDecryptedContent');
    try {
        const response = await fetch(`/api/monitoring/email/decrypt?log_id=${encodeURIComponent(logId)}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || response.statusText || 'Decrypt failed');
        }
        if (data.decrypted === false && data.message) {
            if (decryptedDiv) {
                decryptedDiv.innerHTML = '<p class="text-warning" style="margin:0;">' + (data.message || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>';
                decryptedDiv.style.display = 'block';
            }
            btn.disabled = false;
            btn.textContent = originalText;
            return;
        }
        const escapeHtml = (v) => {
            const d = document.createElement('div');
            d.textContent = v == null ? '' : String(v);
            return d.innerHTML;
        };
        let html = '';
        if (data.subject != null) {
html += `<p><strong>Subject (original):</strong> ${escapeHtml(data.subject)}</p>`;
        }
        if (data.body != null) {
            html += `<pre class="activity-metadata" style="max-height:200px;overflow:auto;white-space:pre-wrap;">${escapeHtml(data.body)}</pre>`;
        }
        if (!html) html = '<p class="text-muted">No content to display.</p>';
        if (decryptedDiv) {
decryptedDiv.innerHTML = '<p class="text-success" style="margin-bottom:8px;"><strong>Decrypted content:</strong></p>' + html;
            decryptedDiv.style.display = 'block';
        }
        btn.style.display = 'none';
showNotification('Decrypted successfully.', 'success');
    } catch (e) {
        showNotification(e.message || 'Decryption failed.', 'error');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function testEmail(event) {
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
        
        // Display result in the tab
        const resultDiv = document.getElementById('emailTestResult');
        if (!resultDiv) {
            console.error('Result div not found');
            return;
        }
        
        let resultHtml = '<div class="email-result">';
        resultHtml += `<h4>Email Analysis Result</h4>`;
        if (emailData.attachments && emailData.attachments.length > 0) {
resultHtml += `<p class="text-muted" style="margin-top:4px;">${emailData.attachments.length} attachment(s) analyzed with the email.</p>`;
        }
        
        // Get analysis result (may be nested in analysis field)
        const analysis = result.analysis || result;
        const policiesMatched = analysis.policies_matched || false;
        const appliedPolicies = analysis.applied_policies || [];
        const actionsTaken = analysis.actions_taken || [];
        
        if (analysis.sensitive_data_detected) {
            // Show message based on whether policies matched
            if (policiesMatched && appliedPolicies.length > 0) {
                resultHtml += `<div class="alert-banner alert-danger">`;
                resultHtml += `<strong>⚠️ Sensitive Data Detected - Policies Applied!</strong>`;
                resultHtml += `<p>${analysis.message || result.message || 'Sensitive data detected and policies applied'}</p>`;
                resultHtml += `</div>`;
            } else {
                resultHtml += `<div class="alert-banner alert-info">`;
                resultHtml += `<strong>⚠️ Sensitive Data Detected</strong>`;
                resultHtml += `<p>${analysis.message || result.message || 'Sensitive data detected but no matching policies'}</p>`;
                resultHtml += `</div>`;
            }
            
            // Show applied policies
            if (appliedPolicies.length > 0) {
                resultHtml += `<h5 style="margin-top: 20px;">Applied Policies (${appliedPolicies.length}):</h5>`;
                resultHtml += '<div style="margin-bottom: 20px;">';
                appliedPolicies.forEach(policy => {
                    const actionBadge = policy.action === 'block' ? 'badge-danger' : policy.action === 'encrypt' ? 'badge-success' : policy.action === 'alert' ? 'badge-warning' : 'badge-info';
                    const severityBadge = policy.severity === 'critical' || policy.severity === 'high' ? 'badge-danger' : policy.severity === 'medium' ? 'badge-warning' : 'badge-info';
                    const escE = (s) => { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; };
                    const matchedStrE = (policy.matched_entities || []).map(e => escE(e)).join(', ');
                    resultHtml += `
                        <div style="padding: 12px; margin-bottom: 8px; background: var(--light); border-radius: 8px; border-left: 4px solid var(--primary);">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;">
                                <strong>${escE(policy.name)}</strong>
                                <div>
                                    <span class="badge ${actionBadge}" style="margin-right: 8px;">${escE(policy.action)}</span>
                                    <span class="badge ${severityBadge}">${escE(policy.severity)}</span>
                                </div>
                            </div>
                            <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 4px;">
                                Matched: ${matchedStrE} (${policy.matched_count} found)
                            </div>
                        </div>
                    `;
                });
                resultHtml += '</div>';
            }
            
            // Show action status: block | alert | encrypt
            const actionType = analysis.action || (analysis.blocked ? 'block' : (analysis.encrypted_text ? 'encrypt' : 'alert'));
            if (actionType === 'block') {
                resultHtml += `<div class="alert-banner alert-danger" style="margin-bottom: 16px;">`;
                resultHtml += `<strong>🚫 Email Blocked (منع الإرسال)</strong>`;
                resultHtml += `<p class="text-muted" style="margin-top: 8px; margin-bottom: 0;">Email blocked. Manager notified.</p>`;
                resultHtml += `</div>`;
            } else if (actionType === 'encrypt') {
                resultHtml += `<div class="alert-banner alert-success" style="margin-bottom: 16px;">`;
                resultHtml += `<strong>🔒 Email Allowed with Encryption (السماح مع التشفير)</strong>`;
                resultHtml += `<p class="text-muted" style="margin-top: 8px; margin-bottom: 0;">Manager notified. You can send the email with the encrypted content below.</p>`;
                resultHtml += `</div>`;
            } else if (actionType === 'alert') {
                resultHtml += `<div class="alert-banner alert-warning" style="margin-bottom: 16px;">`;
                resultHtml += `<strong>📧 Email Allowed (السماح بالإرسال)</strong>`;
                resultHtml += `<p class="text-muted" style="margin-top: 8px; margin-bottom: 0;">Email sent. Manager notified.</p>`;
                resultHtml += `</div>`;
            }
            
            if (actionsTaken.length > 0) {
                const escA = (s) => { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; };
                resultHtml += `<div style="margin-bottom: 16px;"><strong>Actions Taken:</strong> `;
                actionsTaken.forEach(action => {
                    resultHtml += `<span class="badge badge-info" style="margin-right: 4px;">${escA(action)}</span>`;
                });
                resultHtml += `</div>`;
            }
            
            if (analysis.detected_entities && analysis.detected_entities.length > 0) {
                const escE = (s) => { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; };
                const confPct = (e) => { const v = e.score != null ? e.score : e.confidence; return v == null ? '—' : (v <= 1 ? v * 100 : v).toFixed(1) + '%'; };
                resultHtml += `<h5>Detected Entities (${analysis.detected_entities.length}):</h5>`;
                resultHtml += '<div class="entities-list">';
                analysis.detected_entities.forEach(entity => {
                    resultHtml += `
                        <div class="entity-item">
                            <span class="entity-type">${escE(entity.entity_type)}</span>
                            <span class="entity-value">${escE(entity.value)}</span>
                            <span class="entity-score">${confPct(entity)} confidence</span>
                        </div>
                    `;
                });
                resultHtml += '</div>';
            }
            
            // Show encrypted text if available
            // Show encrypted content (prefer encrypted_body = what recipient sees)
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
                
                resultHtml += `<div style="margin-top: 24px; padding: 16px; background: var(--light); border-radius: 8px; border-left: 4px solid var(--success);">
                    <h5 style="margin-top: 0; margin-bottom: 12px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 8px;">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                        Content the recipient will receive
                    </h5>
                    ${analysis.encrypted_subject ? `<p style="margin-bottom: 8px;"><strong>Subject:</strong> <code>${String(analysis.encrypted_subject).replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></p>` : ''}
                    <div style="background: white; padding: 12px; border-radius: 4px; border: 1px solid var(--border); font-family: monospace; word-break: break-all; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">
                        ${escapedText}
                    </div>
                    <button onclick="copyEncryptedText('${textForCopy}')" 
                            style="margin-top: 8px; padding: 6px 12px; background: var(--primary); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem;">
                        Copy encrypted content
                    </button>
                </div>`;
            }
        } else {
            resultHtml += `<div class="alert-banner alert-success">`;
            resultHtml += `<strong>✅ No Sensitive Data Detected</strong>`;
            resultHtml += `<p>The email is safe to send.</p>`;
            resultHtml += `</div>`;
        }
        
        resultHtml += '</div>';
        
        // Display result in the tab (reuse existing resultDiv from above)
        if (!resultDiv) {
            console.error('Result div not found');
            return;
        }
        resultDiv.innerHTML = resultHtml;
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
        
        // Refresh inbox list so the new email appears
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

// Authentication functions
let currentUser = null;
let authToken = null;

// Load user from localStorage on page load
function loadStoredAuth() {
    console.log('Loading stored auth from localStorage...');
    const storedToken = safeStorage.getItem('authToken');
    const storedUser = safeStorage.getItem('currentUser');

    if (storedToken && storedUser) {
        try {
            authToken = storedToken;
            currentUser = JSON.parse(storedUser);
            console.log('Auth loaded successfully:', { 
                hasToken: !!authToken, 
                username: currentUser?.username,
                role: currentUser?.role 
            });
            updateAuthUI();
        } catch (e) {
            console.error('Error loading stored auth:', e);
            // Clear invalid stored data
            safeStorage.removeItem('authToken');
            safeStorage.removeItem('currentUser');
            authToken = null;
            currentUser = null;
            updateAuthUI();
        }
    } else {
        console.log('No stored auth found in localStorage');
        // No stored auth - show login overlay
        authToken = null;
        currentUser = null;
        updateAuthUI();
    }
}

// Update authentication UI
function updateAuthUI() {
    console.log('updateAuthUI called', { currentUser, authToken });

    const authButtons = document.getElementById('authButtons');
    const userInfo = document.getElementById('userInfo');
    const userName = document.getElementById('userName');
    const userRole = document.getElementById('userRole');
    const usersTabBtn = document.getElementById('usersTabBtn');
    const loginOverlay = document.getElementById('loginRequiredOverlay');
    const mainTabs = document.getElementById('mainTabs');
    const mainContent = document.querySelectorAll('.tab-content');

    if (currentUser && authToken) {
        console.log('User is logged in, hiding overlay');
        // User is logged in - hide overlay, show content
        if (loginOverlay) {
            loginOverlay.style.display = 'none';
            loginOverlay.style.visibility = 'hidden';
        }
        if (mainTabs) {
            // Force show tabs container
            mainTabs.removeAttribute('style');
            mainTabs.style.display = 'flex';
            mainTabs.style.visibility = 'visible';
        }
        mainContent.forEach(content => {
            // Remove any inline styles that might interfere
            if (content.hasAttribute('style') && content.getAttribute('style').includes('!important')) {
                content.removeAttribute('style');
            }
            
            if (content.classList.contains('active')) {
                content.style.display = 'block';
                content.style.visibility = 'visible';
                content.style.opacity = '1';
                content.style.pointerEvents = 'auto';
            } else {
                content.style.display = 'none';
                content.style.visibility = 'hidden';
            }
        });
        
        // Ensure the first tab (analysis) is shown by default if no active tab
        const activeTab = document.querySelector('.tab-content.active');
        if (!activeTab && mainContent.length > 0) {
            // Open analysis tab by default using showTab function
            const analysisTab = document.getElementById('analysis');
            const analysisTabBtn = document.querySelector('.tab-btn[onclick*="analysis"]');
            if (analysisTab && analysisTabBtn) {
                showTab('analysis', analysisTabBtn);
            } else {
                // Fallback to manual activation
                const firstTab = document.getElementById('analysis');
                if (firstTab) {
                    // Remove any inline styles
                    if (firstTab.hasAttribute('style')) {
                        firstTab.removeAttribute('style');
                    }
                    firstTab.classList.add('active');
                    firstTab.style.display = 'block';
                    firstTab.style.visibility = 'visible';
                    firstTab.style.opacity = '1';
                    firstTab.style.pointerEvents = 'auto';
                }
            }
        }

        if (authButtons) authButtons.style.display = 'none';
        if (userInfo) {
            userInfo.style.display = 'flex';
            if (userName) userName.textContent = currentUser.username;
            if (userRole) {
                const roleLabel = currentUser.role === 'admin' ? 'Admin' : (currentUser.role === 'manager' ? 'Manager' : 'User');
                userRole.textContent = roleLabel;
                userRole.className = `role-badge ${currentUser.role === 'admin' ? 'badge-danger' : (currentUser.role === 'manager' ? 'badge-warning' : 'badge-info')}`;
            }
        }

        // Show/hide tabs based on user role
        const policiesTabBtn = document.getElementById('policiesTabBtn');
        const alertsTabBtn = document.getElementById('alertsTabBtn');
        const monitoringTabBtn = document.getElementById('monitoringTabBtn');
        const testEmailTabBtn = document.getElementById('testEmailTabBtn');
        const analysisTabBtn = document.querySelector('.tab-btn[onclick*="analysis"]');
        
        // Function to show a tab button
        const showTabButton = (btn) => {
            if (btn) {
                btn.removeAttribute('style');
                btn.style.display = 'flex';
                btn.style.visibility = 'visible';
            }
        };
        
        // Function to hide a tab button
        const hideTabButton = (btn) => {
            if (btn) {
                btn.style.display = 'none';
                btn.style.visibility = 'hidden';
            }
        };
        
        if (currentUser.role === 'admin') {
            // Admin: Show all tabs (no separate Departments tab; it's a sub-tab under Users)
            showTabButton(policiesTabBtn);
            showTabButton(alertsTabBtn);
            showTabButton(monitoringTabBtn);
            showTabButton(testEmailTabBtn);
            showTabButton(usersTabBtn);
            showTabButton(analysisTabBtn);
            const deptSubtab = document.getElementById('usersDepartmentsSubtabBtn');
            if (deptSubtab) { deptSubtab.style.display = 'flex'; deptSubtab.style.visibility = 'visible'; }
            
            // Load admin data
            setTimeout(() => {
                console.log('Loading admin data from updateAuthUI');
                if (typeof loadPolicies === 'function') loadPolicies();
                if (typeof loadAlerts === 'function') loadAlerts();
                if (typeof loadMonitoringData === 'function') loadMonitoringData();
            }, 300);
            // Start real-time notification polling for admin
            if (typeof startAdminNotificationPolling === 'function') startAdminNotificationPolling();
        } else if (currentUser.role === 'manager') {
            // Manager: Show Users, Analysis, Email only (no Policies, Alerts, Monitoring, Departments sub-tab)
            if (typeof stopAdminNotificationPolling === 'function') stopAdminNotificationPolling();
            hideTabButton(policiesTabBtn);
            hideTabButton(alertsTabBtn);
            hideTabButton(monitoringTabBtn);
            showTabButton(usersTabBtn);
            showTabButton(testEmailTabBtn);
            showTabButton(analysisTabBtn);
            const deptSubtab = document.getElementById('usersDepartmentsSubtabBtn');
            if (deptSubtab) { deptSubtab.style.display = 'none'; }
            setTimeout(() => {
                if (typeof loadUsers === 'function') loadUsers(null, 1);
            }, 300);
        } else {
            // Regular user: Hide admin-only tabs (Policies, Alerts, Monitoring, Users, Departments)
            if (typeof stopAdminNotificationPolling === 'function') stopAdminNotificationPolling();
            // Regular users can only access: Analysis (File + Text) and Test Email
            hideTabButton(policiesTabBtn);
            hideTabButton(alertsTabBtn);
            hideTabButton(monitoringTabBtn);
            hideTabButton(usersTabBtn);
            showTabButton(testEmailTabBtn); // Show Email tab (includes Test Email + Emails sent to you sub-tabs)
            showTabButton(analysisTabBtn); // Show Analysis tab
            const deptSubtab = document.getElementById('usersDepartmentsSubtabBtn');
            if (deptSubtab) { deptSubtab.style.display = 'none'; }
        }
        
        // Set user email in Test Email form (disabled field)
        const emailFromInput = document.getElementById('emailFrom');
        if (emailFromInput) {
            if (currentUser && currentUser.email) {
                emailFromInput.value = currentUser.email;
            } else {
                emailFromInput.value = '';
            }
            // Always keep the field disabled and readonly
            emailFromInput.setAttribute('disabled', 'disabled');
            emailFromInput.setAttribute('readonly', 'readonly');
        }
        
        // Hide admin-only content in tabs for regular users
        if (currentUser.role !== 'admin') {
            // Hide admin-only sections in monitoring tab
            const monitoringData = document.getElementById('monitoringData');
            if (monitoringData) {
                monitoringData.style.display = 'none';
            }
            
            // Hide admin-only sections in other tabs if any
            const adminOnlySections = document.querySelectorAll('.admin-only');
            adminOnlySections.forEach(section => {
                section.style.display = 'none';
            });
            const decryptSubtab = document.getElementById('analysisDecryptSubtabBtn');
            if (decryptSubtab) decryptSubtab.style.display = 'none';
        } else {
            // Show all content for admins
            const monitoringData = document.getElementById('monitoringData');
            if (monitoringData) {
                monitoringData.style.display = 'block';
            }
            
            const adminOnlySections = document.querySelectorAll('.admin-only');
            adminOnlySections.forEach(section => {
                section.style.display = '';
            });
            const decryptSubtabBtn = document.getElementById('analysisDecryptSubtabBtn');
            if (decryptSubtabBtn) decryptSubtabBtn.style.display = 'flex';
        }
    } else {
        console.log('User is NOT logged in, showing overlay');
        // User is not logged in - show overlay, hide ALL content

        // Show overlay first
        if (loginOverlay) {
            loginOverlay.style.display = 'flex';
            loginOverlay.style.zIndex = '99999';
            loginOverlay.style.position = 'fixed';
            loginOverlay.style.top = '0';
            loginOverlay.style.left = '0';
            loginOverlay.style.width = '100vw';
            loginOverlay.style.height = '100vh';
            console.log('Login overlay display set to flex');
        }

        // Hide navigation tabs completely
        if (mainTabs) {
            mainTabs.style.display = 'none !important';
            mainTabs.style.visibility = 'hidden';
            mainTabs.style.opacity = '0';
            mainTabs.style.pointerEvents = 'none';
        }

        // Hide all tab content completely
        mainContent.forEach(content => {
            content.style.display = 'none !important';
            content.style.visibility = 'hidden';
            content.style.opacity = '0';
            content.style.pointerEvents = 'none';
        });

        // Hide ALL content sections
        const allTabs = document.querySelectorAll('nav.tabs, .tab-content, .tab-btn');
        allTabs.forEach(el => {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
        });

        // Show login/register buttons in header
        if (authButtons) {
            authButtons.style.display = 'flex';
            authButtons.style.gap = '8px';
        }
        if (userInfo) userInfo.style.display = 'none';
        if (usersTabBtn) usersTabBtn.style.display = 'none';
    }
}

// Get auth headers
function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
        console.log('Auth token included in headers');
    } else {
        console.warn('No auth token available! User may need to login again.');
        // Try to reload from localStorage
        const storedToken = safeStorage.getItem('authToken');
        if (storedToken) {
            authToken = storedToken;
            headers['Authorization'] = `Bearer ${authToken}`;
            console.log('Auth token loaded from localStorage');
        }
    }
    return headers;
}

// Login
async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalBtnContent = submitBtn.innerHTML;

    // Show loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Signing In...';

    try {
        console.log('Attempting login with:', { username, password: '***' });
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            const data = await response.json();
            console.log('Response data:', data);
            if (!response.ok) {
                console.error('Login failed:', data);
                throw new Error(data.detail || 'Login failed');
            }

            authToken = data.access_token;
            currentUser = {
                id: data.user.id,
                username: data.user.username,
                email: data.user.email,
                role: data.user.role
            };

            // Store in localStorage
            safeStorage.setItem('authToken', authToken);
            safeStorage.setItem('currentUser', JSON.stringify(currentUser));

            updateAuthUI();
            closeLoginModal();
            showNotification(`Welcome back, ${currentUser.username}!`, 'success');

            // Force update tabs visibility after a short delay to ensure DOM is ready
            setTimeout(() => {
                updateAuthUI(); // Call again to ensure tabs are visible
                
                // Open default tab after login
                const defaultTab = document.getElementById('analysis');
                const defaultTabBtn = document.querySelector('.tab-btn[onclick*="analysis"]');
                if (defaultTab && defaultTabBtn) {
                    showTab('analysis', defaultTabBtn);
                }
            }, 150);

            // Reload data (only if admin)
            if (currentUser.role === 'admin') {
                setTimeout(() => {
                    if (typeof loadPolicies === 'function') loadPolicies();
                    if (typeof loadAlerts === 'function') loadAlerts();
                    if (typeof loadMonitoringData === 'function') loadMonitoringData();
                }, 500);
            }

            // Show main content
            const loginOverlay = document.getElementById('loginRequiredOverlay');
            if (loginOverlay) {
                loginOverlay.style.display = 'none';
            }
        } else {
            // Handle non-JSON response (likely 500 error)
            const text = await response.text();
            throw new Error(`Server Error (${response.status}): ${text.substring(0, 100)}...`);
        }

    } catch (error) {
        console.error("Login error:", error);
        showNotification(error.message, 'error');
        // Shake animation
        const modalContent = document.querySelector('#loginModal .modal-content');
        if (modalContent) {
            modalContent.classList.remove('shake');
            void modalContent.offsetWidth; // Trigger reflow
            modalContent.classList.add('shake');
        }
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnContent;
    }
}

// Register
async function handleRegister(event) {
    event.preventDefault();

    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const passwordConfirm = document.getElementById('registerPasswordConfirm').value;
    const departmentIdEl = document.getElementById('registerDepartment');
    const department_id = departmentIdEl ? departmentIdEl.value : '';

    if (password !== passwordConfirm) {
        showNotification('Passwords do not match', 'warning');
        const modalContent = document.querySelector('#registerModal .modal-content');
        if (modalContent) {
            modalContent.classList.remove('shake');
            void modalContent.offsetWidth;
            modalContent.classList.add('shake');
        }
        return;
    }

    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalBtnContent = submitBtn.innerHTML;

    // Show loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Creating Account...';

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password, department_id })
        });

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            const data = await response.json();
            if (!response.ok) {
                let msg = 'Registration failed';
                if (data.detail) {
                    if (Array.isArray(data.detail)) {
                        msg = data.detail.map(function (e) {
                            const loc = (e.loc && e.loc.filter(function (x) { return x !== 'body'; }).join('.')) || '';
                            return (loc ? loc + ': ' : '') + (e.msg || String(e));
                        }).join('. ');
                    } else if (typeof data.detail === 'string') {
                        msg = data.detail;
                    } else {
                        msg = JSON.stringify(data.detail);
                    }
                }
                throw new Error(msg);
            }

            closeRegisterModal();
            showNotification('Account created successfully! Please wait for admin approval.', 'success');

            // Show login modal after registration
            setTimeout(() => {
                showLoginModal();
            }, 2000);
        } else {
            // Handle non-JSON response
            const text = await response.text();
            throw new Error(`Server Error (${response.status}): ${text.substring(0, 100)}...`);
        }

    } catch (error) {
        console.error("Registration error:", error);
        showNotification(error.message, 'error');
        // Shake animation
        const modalContent = document.querySelector('#registerModal .modal-content');
        if (modalContent) {
            modalContent.classList.remove('shake');
            void modalContent.offsetWidth; // Trigger reflow
            modalContent.classList.add('shake');
        }
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnContent;
    }
}

// Logout
async function logout() {
    if (typeof stopAdminNotificationPolling === 'function') stopAdminNotificationPolling();
    authToken = null;
    currentUser = null;
    safeStorage.removeItem('authToken');
    safeStorage.removeItem('currentUser');

    updateAuthUI();
    showNotification('Logged out successfully', 'success');

    // Hide admin-only tabs
    const usersTabBtn = document.getElementById('usersTabBtn');
    if (usersTabBtn) usersTabBtn.style.display = 'none';

    // Switch to analysis tab
    const analysisTab = document.querySelector('.tab-btn');
    if (analysisTab) analysisTab.click();
}

// Modal functions
function showLoginModal() {
    console.log('showLoginModal called');
    const modal = document.getElementById('loginModal');
    if (modal) {
        // Hide the login overlay first
        const overlay = document.getElementById('loginRequiredOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
        // Force show modal - remove inline display:none and set display:flex
        if (modal.hasAttribute('style')) {
            const currentStyle = modal.getAttribute('style');
            // Remove display:none if present
            const newStyle = currentStyle.replace(/display\s*:\s*none\s*;?/gi, '');
            modal.setAttribute('style', newStyle);
        }
        // Set display and other properties
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100vw';
        modal.style.height = '100vh';
        modal.style.zIndex = '100001';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
        modal.style.pointerEvents = 'auto';
        modal.classList.add('show');
        
        // Focus on username input
        setTimeout(() => {
            const usernameInput = document.getElementById('loginUsername');
            if (usernameInput) {
                usernameInput.focus();
            }
        }, 100);
    } else {
        console.error('Login modal not found');
    }
}

function closeLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            const form = document.getElementById('loginForm');
            if (form) form.reset();
            // Show login overlay again if user is not logged in
            if (!currentUser) {
                const overlay = document.getElementById('loginRequiredOverlay');
                if (overlay) {
                    overlay.style.display = 'flex';
                }
            }
        }, 300);
    }
}

function showRegisterModal() {
    console.log('showRegisterModal called');
    try {
        const modal = document.getElementById('registerModal');
        if (!modal) {
            console.error('Register modal not found');
            alert('Registration form not found. Please refresh the page.');
            return;
        }
        
        // Hide the login overlay first
        const overlay = document.getElementById('loginRequiredOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
        
        // Force show modal - remove inline display:none and set display:flex
        if (modal.hasAttribute('style')) {
            const currentStyle = modal.getAttribute('style');
            // Remove display:none if present
            const newStyle = currentStyle.replace(/display\s*:\s*none\s*;?/gi, '');
            modal.setAttribute('style', newStyle);
        }
        // Set display and other properties
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100vw';
        modal.style.height = '100vh';
        modal.style.zIndex = '100001';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
        modal.style.pointerEvents = 'auto';
        modal.classList.add('show');
        
        // Load departments for the dropdown (no auth required)
        fetch('/api/departments/list')
            .then(r => r.ok ? r.json() : [])
            .then(list => {
                const sel = document.getElementById('registerDepartment');
                if (!sel) return;
                sel.innerHTML = '<option value="">Select department...</option>';
                (list || []).forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.name || d.id;
                    sel.appendChild(opt);
                });
            })
            .catch(() => {});
        
        // Focus on username input
        setTimeout(() => {
            const usernameInput = document.getElementById('registerUsername');
            if (usernameInput) {
                usernameInput.focus();
            }
        }, 100);
    } catch (error) {
        console.error('Error in showRegisterModal:', error);
        alert('Error opening registration form: ' + error.message);
    }
}

function closeRegisterModal() {
    const modal = document.getElementById('registerModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            const form = document.getElementById('registerForm');
            if (form) form.reset();
            // Show login overlay again if user is not logged in
            if (!currentUser) {
                const overlay = document.getElementById('loginRequiredOverlay');
                if (overlay) {
                    overlay.style.display = 'flex';
                }
            }
        }, 300);
    }
}

// Users Management (Admin only)
let currentUsersView = 'all';
let currentUsersPage = 1;
let usersPagination = { total: 0, total_pages: 0, limit: 10 };

// Pagination state for other sections
let currentPoliciesPage = 1;
let policiesPagination = { total: 0, total_pages: 0, limit: 50 };

let currentAlertsPage = 1;
let alertsPagination = { total: 0, total_pages: 0, limit: 10, has_next: false, has_prev: false };

// Admin real-time notification polling
let lastNotificationCheck = null;
let notificationPollingIntervalId = null;
const NOTIFICATION_POLL_INTERVAL_MS = 5000;
/** Set of alert IDs we've already shown in this session to avoid duplicate dialogs */
let shownAlertIds = new Set();
/** Prevent overlapping fetch calls */
let recentAlertsFetchInFlight = false;

function startAdminNotificationPolling() {
    if (!currentUser || String(currentUser.role).toLowerCase() !== 'admin' || !authToken) {
        if (currentUser && String(currentUser.role).toLowerCase() !== 'admin') return;
        return;
    }
    stopAdminNotificationPolling();
    lastNotificationCheck = new Date().toISOString();
    shownAlertIds.clear();
    const base = getApiBase();
    console.log('[Policy Violation] Admin notification polling started; API base:', base);
    notificationPollingIntervalId = setInterval(fetchRecentAlertsAndShowDialogs, NOTIFICATION_POLL_INTERVAL_MS);
    fetchRecentAlertsAndShowDialogs();
}

function stopAdminNotificationPolling() {
    if (notificationPollingIntervalId) {
        clearInterval(notificationPollingIntervalId);
        notificationPollingIntervalId = null;
    }
}

async function fetchRecentAlertsAndShowDialogs() {
    const isAdmin = currentUser && String(currentUser.role).toLowerCase() === 'admin';
    if (!currentUser || !isAdmin || !authToken || !lastNotificationCheck || recentAlertsFetchInFlight) return;
    recentAlertsFetchInFlight = true;
    const sinceAtStart = lastNotificationCheck;
    const url = `${getApiBase()}/api/alerts/recent?since=${encodeURIComponent(sinceAtStart)}&limit=50`;
    try {
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            if (response.status === 401) {
                stopAdminNotificationPolling();
                authToken = null;
                currentUser = null;
                safeStorage.removeItem('authToken');
                safeStorage.removeItem('currentUser');
                updateAuthUI();
                showNotification('Session expired or invalid. Please log in again.', 'warning');
            } else {
                console.warn('[Policy Violation] Fetch alerts failed:', response.status, response.statusText, url);
            }
            return;
        }
        const data = await response.json();
        const items = data.items || (Array.isArray(data) ? data : []);
        if (!Array.isArray(items) || items.length === 0) {
            lastNotificationCheck = new Date().toISOString();
            return;
        }
        const newAlerts = items.filter(a => a && a.id && !shownAlertIds.has(String(a.id)));
        newAlerts.forEach(alert => {
            shownAlertIds.add(String(alert.id));
            showAlertDialog(alert);
        });
        lastNotificationCheck = new Date().toISOString();
        if (newAlerts.length > 0) {
            if (typeof loadAlerts === 'function') loadAlerts(1);
            if (typeof loadMonitoringData === 'function') loadMonitoringData(1);
        }
    } catch (e) {
        console.warn('[Policy Violation] Failed to fetch recent alerts:', e.message || e, 'URL:', url);
    } finally {
        recentAlertsFetchInFlight = false;
    }
}

function showAlertDialog(alert) {
    function escapeHtml(str) {
        if (str == null) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    const overlay = document.createElement('div');
    overlay.className = 'alert-notification-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Policy violation alert');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.75);padding:24px;backdrop-filter:blur(8px);';

    const policyName = (alert && (alert.policy_name || alert.title)) || '—';
    const clientName = (alert && alert.source_user) || 'Unknown';
    const desc = (alert && alert.description) || '';
    const timeStr = formatAlertTimeLocal(alert && alert.created_at, null);
    const severity = (alert && alert.severity) ? String(alert.severity) : 'medium';
    const status = (alert && alert.status) ? String(alert.status) : 'pending';
    const actionTaken = (alert && alert.blocked) ? 'Blocked' : (alert && alert.action_taken) || 'Alert';
    const severityClass = severity === 'high' || severity === 'critical' ? 'danger' : severity === 'medium' ? 'warning' : 'info';
    const statusClass = status === 'resolved' ? 'success' : status === 'pending' ? 'warning' : status === 'acknowledged' ? 'info' : 'secondary';
    const actionClass = (alert && alert.blocked) ? 'danger' : 'info';

    const hasEntities = alert && alert.detected_entities && alert.detected_entities.length > 0;
    const entitiesHtml = hasEntities
        ? alert.detected_entities.map(e => {
            const t = e.entity_type || e.type || 'Unknown';
            const v = e.value || 'N/A';
            return `<div class="entity-item"><span class="entity-type-badge">${escapeHtml(t)}</span><span class="entity-value">${escapeHtml(v)}</span></div>`;
        }).join('')
        : '<span class="text-muted">No entities detected</span>';

    overlay.innerHTML = `
        <div class="modal-content alert-details-modal alert-notification-dialog-content" style="max-width:520px;" onclick="event.stopPropagation()">
            <div class="alert-modal-header">
                <div class="alert-header-content">
                    <h2 class="alert-incident-title">Policy Violation</h2>
                    <p class="alert-policy-name">${escapeHtml(policyName)}</p>
                </div>
                <button type="button" class="close-btn alert-close-btn alert-notification-close" aria-label="Close">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="alert-summary-section">
                <div class="summary-row">
                    <div class="summary-item">
                        <span class="summary-label">Severity</span>
                        <span class="badge badge-${severityClass}">${escapeHtml(severity)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Status</span>
                        <span class="badge badge-${statusClass}">${escapeHtml(status)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Action</span>
                        <span class="badge badge-${actionClass}">${escapeHtml(actionTaken)}</span>
                    </div>
                </div>
            </div>
            <div class="alert-details-section">
                <div class="detail-section">
                    <h4>Source</h4>
                    <p class="detail-value">${escapeHtml(clientName)}</p>
                </div>
                ${(alert.attachment_names && alert.attachment_names.length) ? buildAttachmentsCardHtml(alert.attachment_names, 'Attachments', (alert.extra_data && alert.extra_data.attachment_contents) || []) : ''}
                ${(alert.extra_data && (alert.extra_data.body_preview || alert.extra_data.body)) ? `<div class="detail-section"><h4>Body</h4><pre class="attachment-card-content" style="margin:0;">${escapeHtml(alert.extra_data.body_preview || alert.extra_data.body)}</pre></div>` : ''}
                ${desc ? `<div class="detail-section"><h4>Description</h4><p class="detail-value">${escapeHtml(desc)}</p></div>` : ''}
                <div class="detail-section">
                    <h4>Detected Entities</h4>
                    <div class="entities-container ${!hasEntities ? 'entities-empty' : ''}">${entitiesHtml}</div>
                </div>
                <div class="detail-section"><h4>Created At</h4><p class="detail-value">${escapeHtml(timeStr)}</p></div>
            </div>
            <div class="alert-modal-actions">
                <button type="button" class="btn btn-primary alert-notification-btn-view">View Alerts</button>
                <button type="button" class="btn btn-secondary alert-notification-btn-ok">OK</button>
            </div>
        </div>
    `;
    function close() {
        overlay.remove();
    }
    const closeBtn = overlay.querySelector('.alert-notification-close');
    const okBtn = overlay.querySelector('.alert-notification-btn-ok');
    const viewBtn = overlay.querySelector('.alert-notification-btn-view');
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (okBtn) okBtn.addEventListener('click', close);
    if (viewBtn) {
        viewBtn.addEventListener('click', () => {
            close();
            const alertsTabBtn = document.getElementById('alertsTabBtn');
            if (alertsTabBtn) {
                showTab('alerts', alertsTabBtn);
                if (typeof loadAlerts === 'function') loadAlerts(1);
            }
        });
    }
    const shownAt = Date.now();
    overlay.addEventListener('click', function(e) {
        if (e.target !== overlay) return;
        if (Date.now() - shownAt < 400) return;
        close();
    });
    document.body.appendChild(overlay);
    if (typeof initDraggableCards === 'function') initDraggableCards(overlay);
}

let currentMonitoringPage = 1;
let monitoringPagination = { total: 0, total_pages: 0, limit: 10 };

function switchUsersView(view, buttonElement) {
    currentUsersView = view;

    // Update active tab
    document.querySelectorAll('#users .sub-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    if (buttonElement) {
        buttonElement.classList.add('active');
    }

    const usersListEl = document.getElementById('usersList');
    const departmentsSectionEl = document.getElementById('usersDepartmentsSection');

    if (view === 'departments') {
        if (usersListEl) usersListEl.style.display = 'none';
        if (departmentsSectionEl) departmentsSectionEl.style.display = 'block';
        if (typeof loadDepartments === 'function') loadDepartments();
    } else {
        if (usersListEl) usersListEl.style.display = '';
        if (departmentsSectionEl) departmentsSectionEl.style.display = 'none';
        if (view === 'pending') {
            loadPendingUsers();
        } else if (view === 'active') {
            loadUsers('active', 1);
        } else {
            loadUsers(null, 1);
        }
    }
}

async function loadUsers(statusFilter = null, page = 1) {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'manager')) {
        showNotification('Admin or manager access required', 'error');
        return;
    }

    try {
        currentUsersPage = page;
        let url = '/api/users/';
        const params = new URLSearchParams();
        if (statusFilter === 'active') {
            // For active users, we need to filter by both status (approved or active) and is_active=true
            // Since API doesn't support is_active filter directly, we'll get all approved/active users
            // and filter on frontend, or we can use status=active if it exists
            params.append('status', 'active');
        }
        params.append('page', page);
        params.append('limit', usersPagination.limit);
        if (params.toString()) {
            url += '?' + params.toString();
        }

        const response = await fetch(url, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                throw new Error('Session expired. Please login again.');
            }
            throw new Error('Failed to load users');
        }

        const data = await response.json();
        console.log('Users API response:', data);
        
        // Handle both paginated and non-paginated responses
        const users = Array.isArray(data) ? data : (data.items || []);
        
        if (!Array.isArray(users)) {
            console.error('Users is not an array:', typeof users, users);
            throw new Error('Invalid users data format');
        }
        
        usersPagination = {
            total: data.total || users.length,
            total_pages: data.total_pages || 1,
            limit: data.limit || usersPagination.limit,
            has_next: data.has_next !== undefined ? data.has_next : (currentUsersPage < (data.total_pages || 1)),
            has_prev: data.has_prev !== undefined ? data.has_prev : (currentUsersPage > 1)
        };
        
        console.log('Users loaded successfully:', users.length, 'users');
        console.log('Users pagination:', usersPagination);
        displayUsers(users);
        renderPagination('users', currentUsersPage, usersPagination, (p) => loadUsers(statusFilter, p));

    } catch (error) {
        showNotification('Error loading users: ' + error.message, 'error');
    }
}

async function loadPendingUsers() {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'manager')) {
        showNotification('Admin or manager access required', 'error');
        return;
    }

    try {
        const response = await fetch('/api/users/pending', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                throw new Error('Session expired. Please login again.');
            }
            throw new Error('Failed to load pending users');
        }

        const users = await response.json();
        displayUsers(users);

        // Update pending count
        const pendingCount = document.getElementById('pendingCount');
        const pendingTabCount = document.getElementById('pendingTabCount');
        if (pendingCount) {
            pendingCount.textContent = users.length;
            pendingCount.style.display = users.length > 0 ? 'inline-block' : 'none';
        }
        if (pendingTabCount) {
            pendingTabCount.textContent = users.length;
            pendingTabCount.style.display = users.length > 0 ? 'inline-block' : 'none';
        }

    } catch (error) {
        showNotification('Error loading pending users: ' + error.message, 'error');
    }
}

function displayUsers(users) {
    const container = document.getElementById('usersList');
    if (!container) return;
    
    // Ensure users is an array
    if (!users) {
        console.warn('Users data is null or undefined');
        container.innerHTML = '<div class="empty-state"><p>No users found</p></div>';
        return;
    }
    
    if (!Array.isArray(users)) {
        console.error('Users is not an array:', typeof users, users);
        container.innerHTML = '<div class="empty-state"><p>Error: Invalid users data format</p></div>';
        return;
    }

    // Bind delegated handlers once (survives re-renders via innerHTML)
    if (!container.dataset.userActionsBound) {
        container.dataset.userActionsBound = 'true';
        container.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-testid="approve-user-btn"], [data-testid="reject-user-btn"]');
            if (!btn) return;

            e.preventDefault();
            e.stopPropagation();

            const userId = btn.getAttribute('data-user-id');
            if (!userId) {
                console.error('User action clicked but data-user-id is missing');
                showNotification('Error: User ID is missing', 'error');
                return;
            }

            if (btn.dataset.testid === 'approve-user-btn' || btn.getAttribute('data-testid') === 'approve-user-btn') {
                console.log('Approve clicked (delegated), userId:', userId);
                if (typeof window.approveUser === 'function') {
                    window.approveUser(userId);
                } else {
                    console.error('window.approveUser is not a function');
                    showNotification('Error: Approve function not available. Please refresh the page.', 'error');
                }
                return;
            }

            console.log('Reject clicked (delegated), userId:', userId);
            if (typeof window.rejectUser === 'function') {
                window.rejectUser(userId);
            } else {
                console.error('window.rejectUser is not a function');
                showNotification('Error: Reject function not available. Please refresh the page.', 'error');
            }
        });
    }

    if (users.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No users found</p></div>';
        return;
    }

    // Create table layout
    let html = `
        <div class="table-container">
            <table class="users-table">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Department</th>
                        <th>Status</th>
                        <th>Account Status</th>
                        <th>Created</th>
                        <th>Last Login</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;

    users.forEach(user => {
        const statusBadge = {
            'pending': '<span class="badge badge-warning">Pending</span>',
            'approved': '<span class="badge badge-success">Approved</span>',
            'rejected': '<span class="badge badge-danger">Rejected</span>',
            'active': '<span class="badge badge-success">Active</span>'
        }[user.status] || '<span class="badge badge-secondary">Unknown</span>';

        const roleBadge = user.role === 'admin'
            ? '<span class="badge badge-danger">Admin</span>'
            : user.role === 'manager'
            ? '<span class="badge badge-warning">Department Manager</span>'
            : '<span class="badge badge-info">User</span>';

        const accountStatusBadge = user.is_active === false
            ? '<span class="badge badge-warning">Suspended</span>'
            : user.status === 'approved' || user.status === 'active'
            ? '<span class="badge badge-success">Active</span>'
            : statusBadge;

        const createdDate = user.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        }) : 'N/A';

        const lastLogin = user.last_login ? new Date(user.last_login).toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }) : '<span class="text-muted">Never</span>';

        html += `
            <tr data-user-id="${user.id}" class="user-row ${user.status === 'pending' ? 'row-pending' : ''}">
                <td>
                    <div class="user-info-cell">
                        <div class="user-avatar">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                                <circle cx="12" cy="7" r="4"></circle>
                            </svg>
                        </div>
                        <div class="user-name-info">
                            <strong>${user.username}</strong>
                            ${user.rejection_reason ? `<div class="rejection-reason-tooltip" title="${user.rejection_reason}">⚠️ Rejected</div>` : ''}
                        </div>
                    </div>
                </td>
                <td>
                    <div class="email-cell">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px; opacity: 0.6;">
                            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                            <polyline points="22,6 12,13 2,6"></polyline>
                        </svg>
                        ${user.email}
                    </div>
                </td>
                <td>${roleBadge}</td>
                <td><span class="department-cell">${(user.department_name || '—')}</span></td>
                <td>${statusBadge}</td>
                <td>${accountStatusBadge}</td>
                <td><span class="date-cell">${createdDate}</span></td>
                <td><span class="date-cell">${lastLogin}</span></td>
                <td>
                    <div class="action-buttons">
                        ${user.status === 'pending' ? `
                            <button class="btn-icon btn-success" onclick="event.stopPropagation(); approveUser('${user.id}')" title="Approve User" data-testid="approve-user-btn" data-user-id="${user.id}">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            </button>
                            <button class="btn-icon btn-danger" onclick="event.stopPropagation(); rejectUser('${user.id}')" title="Reject User" data-testid="reject-user-btn" data-user-id="${user.id}">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                            </button>
                        ` : ''}
                        ${user.status === 'approved' || user.status === 'active' ? `
                            ${user.is_active ? `
                                <button class="btn-icon btn-warning" onclick="event.stopPropagation(); suspendUser('${user.id}')" title="Suspend User">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                        <rect x="6" y="4" width="4" height="16" rx="1"></rect>
                                        <rect x="14" y="4" width="4" height="16" rx="1"></rect>
                                    </svg>
                                </button>
                                ` : `
                                <button class="btn-icon btn-success" onclick="event.stopPropagation(); activateUser('${user.id}')" title="Activate User">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                    </svg>
                                </button>
                            `}
                        ` : ''}
                        <button class="btn-icon btn-ghost" onclick="event.stopPropagation(); openEditUserModal('${user.id}')" title="Edit User">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button class="btn-icon btn-delete" onclick="event.stopPropagation(); deleteUser('${user.id}')" title="Delete User">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
    
    console.log('Users displayed in table format');
    console.log('User rows count:', container.querySelectorAll('.user-row').length);
}

// User management functions
async function suspendUser(userId) {
    if (!confirm('Are you sure you want to suspend this user? They will not be able to login.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${userId}/suspend`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            showNotification('User suspended successfully', 'success');
            loadUsers();
        } else {
            if (response.status === 401 || response.status === 403) {
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to suspend user';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error suspending user:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

async function activateUser(userId) {
    if (!confirm('Are you sure you want to activate this user? They will be able to login again.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${userId}/activate`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            showNotification('User activated successfully', 'success');
            loadUsers();
        } else {
            if (response.status === 401 || response.status === 403) {
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to activate user';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error activating user:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to permanently delete this user? This action cannot be undone!')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/users/${userId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (response.ok || response.status === 204) {
            showNotification('User deleted successfully', 'success');
            loadUsers();
        } else {
            if (response.status === 401 || response.status === 403) {
                showNotification('Session expired. Please login again.', 'warning');
                logout();
                return;
            }
            const error = await response.json();
            const errorMsg = error.detail || error.message || 'Failed to delete user';
            showNotification('Error: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

function closeEditUserModal() {
    const modal = document.getElementById('editUserModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}

async function openEditUserModal(userId) {
    try {
        const [userRes, deptRes] = await Promise.all([
            fetch(`/api/users/${userId}`, { headers: getAuthHeaders() }),
            fetch('/api/departments/', { headers: getAuthHeaders() })
        ]);
        if (!userRes.ok) {
            if (userRes.status === 401 || userRes.status === 403) { logout(); return; }
            showNotification('Failed to load user', 'error');
            return;
        }
        const user = await userRes.json();
        const departments = deptRes.ok ? await deptRes.json() : [];
        document.getElementById('editUserId').value = user.id;
        document.getElementById('editUserUsername').value = user.username || '';
        document.getElementById('editUserEmail').value = user.email || '';
        document.getElementById('editUserPassword').value = '';
        const deptSel = document.getElementById('editUserDepartment');
        deptSel.innerHTML = '<option value="">— None —</option>';
        (departments || []).forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.name || d.id;
            if (user.department_id && String(d.id) === String(user.department_id)) opt.selected = true;
            deptSel.appendChild(opt);
        });
        const roleSel = document.getElementById('editUserRole');
        roleSel.value = user.role || 'regular';
        if (currentUser && currentUser.role === 'manager') {
            const adminOpt = roleSel.querySelector('option[value="admin"]');
            if (adminOpt) adminOpt.remove();
        }
        const modal = document.getElementById('editUserModal');
        if (modal) {
            modal.classList.add('show');
            modal.style.setProperty('display', 'flex', 'important');
            modal.setAttribute('aria-hidden', 'false');
        }
    } catch (e) {
        showNotification('Error loading user: ' + (e.message || 'Unknown'), 'error');
    }
}

async function saveEditUser(event) {
    event.preventDefault();
    const userId = document.getElementById('editUserId').value;
    const username = document.getElementById('editUserUsername').value.trim();
    const email = document.getElementById('editUserEmail').value.trim();
    const password = document.getElementById('editUserPassword').value;
    const department_id = document.getElementById('editUserDepartment').value || null;
    const role = document.getElementById('editUserRole').value;
    const body = { username, email, role, department_id };
    if (password) body.password = password;
    try {
        const res = await fetch(`/api/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || res.statusText);
        }
        closeEditUserModal();
        loadUsers();
        showNotification('User updated', 'success');
    } catch (e) {
        showNotification(e.message || 'Error', 'error');
    }
}

// Make functions globally available IMMEDIATELY
// This must be done before DOMContentLoaded to ensure functions are available
// CRITICAL: This IIFE must execute immediately when script loads
(function() {
    'use strict';
    // Define functions in global scope immediately
    window.showLoginModal = function() {
        console.log('showLoginModal called (global)');
        try {
            const modal = document.getElementById('loginModal');
            if (!modal) {
                console.error('Login modal not found');
                alert('Login form not found. Please refresh the page.');
                return;
            }
            
            console.log('Modal found, showing...');
            
            // Hide the login overlay first
            const overlay = document.getElementById('loginRequiredOverlay');
            if (overlay) {
                overlay.style.display = 'none';
                console.log('Overlay hidden');
            }
            
            // CRITICAL: Remove the inline style attribute completely to override display:none
            modal.removeAttribute('style');
            console.log('Inline style removed');
            
            // Set all properties directly on style object (this overrides CSS)
            modal.style.setProperty('display', 'flex', 'important');
            modal.style.setProperty('position', 'fixed', 'important');
            modal.style.setProperty('top', '0', 'important');
            modal.style.setProperty('left', '0', 'important');
            modal.style.setProperty('width', '100vw', 'important');
            modal.style.setProperty('height', '100vh', 'important');
            modal.style.setProperty('z-index', '100001', 'important');
            modal.style.setProperty('opacity', '1', 'important');
            modal.style.setProperty('visibility', 'visible', 'important');
            modal.style.setProperty('pointer-events', 'auto', 'important');
            modal.style.setProperty('align-items', 'center', 'important');
            modal.style.setProperty('justify-content', 'center', 'important');
            
            // Add show class
            modal.classList.add('show');
            
            console.log('Modal styles set, checking visibility...');
            console.log('Computed display:', window.getComputedStyle(modal).display);
            console.log('Computed opacity:', window.getComputedStyle(modal).opacity);
            console.log('Computed visibility:', window.getComputedStyle(modal).visibility);
            
            // Focus on username input
            setTimeout(() => {
                const usernameInput = document.getElementById('loginUsername');
                if (usernameInput) {
                    usernameInput.focus();
                    console.log('Username input focused');
                }
            }, 100);
        } catch (error) {
            console.error('Error in showLoginModal:', error);
            alert('Error opening login form: ' + error.message);
        }
    };
    
    window.showRegisterModal = function() {
        console.log('showRegisterModal called (global)');
        try {
            const modal = document.getElementById('registerModal');
            if (!modal) {
                console.error('Register modal not found');
                alert('Registration form not found. Please refresh the page.');
                return;
            }
            
            // Hide the login overlay first
            const overlay = document.getElementById('loginRequiredOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
            
            // Force show modal - remove inline display:none and set display:flex
            if (modal.hasAttribute('style')) {
                const currentStyle = modal.getAttribute('style');
                // Remove display:none if present
                const newStyle = currentStyle.replace(/display\s*:\s*none\s*;?/gi, '');
                if (newStyle.trim() !== currentStyle.trim()) {
                    modal.setAttribute('style', newStyle);
                }
            }
            // Set display and other properties
            modal.style.display = 'flex';
            modal.style.position = 'fixed';
            modal.style.top = '0';
            modal.style.left = '0';
            modal.style.width = '100vw';
            modal.style.height = '100vh';
            modal.style.zIndex = '100001';
            modal.style.opacity = '1';
            modal.style.visibility = 'visible';
            modal.style.pointerEvents = 'auto';
            modal.classList.add('show');
            
            // Load departments for the dropdown (no auth required)
            fetch('/api/departments/list')
                .then(r => r.ok ? r.json() : [])
                .then(list => {
                    const sel = document.getElementById('registerDepartment');
                    if (!sel) return;
                    sel.innerHTML = '<option value="">Select department...</option>';
                    (list || []).forEach(d => {
                        const opt = document.createElement('option');
                        opt.value = d.id;
                        opt.textContent = d.name || d.id;
                        sel.appendChild(opt);
                    });
                })
                .catch(() => {});
            
            // Focus on username input
            setTimeout(() => {
                const usernameInput = document.getElementById('registerUsername');
                if (usernameInput) {
                    usernameInput.focus();
                }
            }, 100);
        } catch (error) {
            console.error('Error in showRegisterModal:', error);
            alert('Error opening registration form: ' + error.message);
        }
    };
})();

// Make other functions globally available
window.analyzeText = analyzeText;
window.showTab = showTab;
window.switchAnalysisMode = switchAnalysisMode;
window.decryptPastedContent = decryptPastedContent;
window.switchEmailMode = switchEmailMode;
window.closeLoginModal = closeLoginModal;
window.closeRegisterModal = closeRegisterModal;
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.logout = logout;
window.loadUsers = loadUsers;
window.suspendUser = suspendUser;
window.activateUser = activateUser;
window.deleteUser = deleteUser;
window.restorePolicy = restorePolicy;
window.editPolicy = editPolicy;
window.loadDeletedPolicies = loadDeletedPolicies;
window.switchPoliciesView = switchPoliciesView;
window.loadPendingUsers = loadPendingUsers;
window.switchUsersView = switchUsersView;
// approveUser and rejectUser are already defined in window scope above
window.loadPolicies = loadPolicies;
window.loadAlerts = loadAlerts;
window.updateAlertStatus = updateAlertStatus;
window.showPolicyDetails = showPolicyDetails;
window.showAlertDetails = showAlertDetails;
window.closeDetailsModal = closeDetailsModal;
window.loadMonitoringData = loadMonitoringData;
window.loadEmailList = loadEmailList;
window.decryptEmailContent = decryptEmailContent;
window.searchMonitoringUsers = searchMonitoringUsers;
window.showUserActivityModal = showUserActivityModal;
window.loadUserActivityPage = loadUserActivityPage;
window.showOperationDetailsModal = showOperationDetailsModal;
window.showCreatePolicyForm = showCreatePolicyForm;
window.closeModal = closeModal;
window.createPolicy = createPolicy;
window.deletePolicy = deletePolicy;
window.togglePolicy = togglePolicy;
window.updatePolicy = updatePolicy;
window.resetPolicyForm = resetPolicyForm;
window.showNotification = showNotification;

// Function to update selected entities tags display
function updateSelectedEntitiesTags() {
    const selectedCheckboxes = document.querySelectorAll('input[name="policyEntities"]:checked');
    const tagsContainer = document.getElementById('selectedEntitiesTags');
    if (!tagsContainer) return;
    
    const entityLabels = {
        'PERSON': 'Person',
        'PHONE_NUMBER': 'Phone Number',
        'EMAIL_ADDRESS': 'Email Address',
        'CREDIT_CARD': 'Credit Card',
        'ADDRESS': 'Address',
        'ORGANIZATION': 'Organization',
        'DATE_TIME': 'Date/Time',
        'LOCATION': 'Location',
        'IBAN_CODE': 'IBAN Code',
        'IP_ADDRESS': 'IP Address',
        'US_SSN': 'US SSN',
        'MALICIOUS_SCRIPT': 'Malicious Script'
    };
    
    if (selectedCheckboxes.length === 0) {
        tagsContainer.style.display = 'none';
        return;
    }
    
    tagsContainer.style.display = 'flex';
    let html = '<span class="tag-label">Selected:</span>';
    
    selectedCheckboxes.forEach(checkbox => {
        const label = entityLabels[checkbox.value] || checkbox.value;
        html += `
            <span class="entity-tag">
                ${label}
                <span class="remove-tag" onclick="document.querySelector('input[value=\\'${checkbox.value}\\']').click(); updateSelectedEntitiesTags();" title="Remove">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </span>
            </span>
        `;
    });
    
    tagsContainer.innerHTML = html;
}

window.updateSelectedEntitiesTags = updateSelectedEntitiesTags;
window.showEmailTestForm = showEmailTestForm;
window.closeEmailModal = closeEmailModal;
window.testEmail = testEmail;
window.resetEmailForm = resetEmailForm;

// Load data on page load
window.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');
    
    // Add change listeners to entity type checkboxes
    const entityCheckboxes = document.querySelectorAll('input[name="policyEntities"]');
    entityCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedEntitiesTags);
    });
    
    // Immediately disable emailFrom field
    const emailFromInput = document.getElementById('emailFrom');
    if (emailFromInput) {
        emailFromInput.disabled = true;
        emailFromInput.readOnly = true;
        emailFromInput.setAttribute('disabled', 'disabled');
        emailFromInput.setAttribute('readonly', 'readonly');
    }

    // Clear any old/invalid tokens first (for testing)
    // Uncomment the next line to force login screen on every page load
    // safeStorage.clear();

    // Add event listeners to overlay buttons using IDs
    // Use event delegation for better reliability
    const loginOverlay = document.getElementById('loginRequiredOverlay');
    if (loginOverlay) {
        loginOverlay.addEventListener('click', function(e) {
            const target = e.target;
            const btn = target.closest('button');
            
            if (btn && btn.id === 'overlayLoginBtn') {
                e.preventDefault();
                e.stopPropagation();
                console.log('Overlay Login button clicked via delegation');
                if (typeof window.showLoginModal === 'function') {
                    window.showLoginModal();
                } else {
                    console.error('showLoginModal is not a function');
                }
                return false;
            }
            
            if (btn && btn.id === 'overlayRegisterBtn') {
                e.preventDefault();
                e.stopPropagation();
                console.log('Overlay Register button clicked via delegation');
                if (typeof window.showRegisterModal === 'function') {
                    window.showRegisterModal();
                } else {
                    console.error('showRegisterModal is not a function');
                }
                return false;
            }
        });
    }
    
    // Also add direct listeners as backup
    const overlayLoginBtn = document.getElementById('overlayLoginBtn');
    const overlayRegisterBtn = document.getElementById('overlayRegisterBtn');
    
    if (overlayLoginBtn) {
        console.log('Overlay Login button found, adding direct event listener');
        overlayLoginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Overlay Login button clicked (direct)');
            if (typeof window.showLoginModal === 'function') {
                window.showLoginModal();
            } else {
                console.error('showLoginModal is not a function', typeof window.showLoginModal);
            }
            return false;
        });
    } else {
        console.error('Overlay Login button not found');
    }
    
    if (overlayRegisterBtn) {
        console.log('Overlay Register button found, adding direct event listener');
        overlayRegisterBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Overlay Register button clicked (direct)');
            if (typeof window.showRegisterModal === 'function') {
                window.showRegisterModal();
            } else {
                console.error('showRegisterModal is not a function', typeof window.showRegisterModal);
            }
            return false;
        });
    } else {
        console.error('Overlay Register button not found');
    }

    // Load stored authentication
    loadStoredAuth();

    // Initialize file upload
    initFileUpload();
    
    // Ensure tabs are visible if user is logged in
    if (currentUser && authToken) {
        // Show the first tab by default
        const firstTab = document.getElementById('analysis');
        if (firstTab) {
            firstTab.classList.add('active');
            firstTab.style.display = 'block';
            firstTab.style.visibility = 'visible';
        }
        
        // Activate the first tab button
        const firstTabBtn = document.querySelector('.tab-btn[onclick*="analysis"]');
        if (firstTabBtn) {
            firstTabBtn.classList.add('active');
        }
        
        // Ensure emailFrom field is filled with user's email
        const emailFromInput = document.getElementById('emailFrom');
        if (emailFromInput && currentUser.email) {
            emailFromInput.value = currentUser.email;
            emailFromInput.setAttribute('disabled', 'disabled');
            emailFromInput.setAttribute('readonly', 'readonly');
        }
    }

    // Set default mode to file analysis
    const fileTabBtn = document.querySelector('.sub-tab-btn');
    if (fileTabBtn) {
        switchAnalysisMode('file', fileTabBtn);
    }
    
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
    
    // Data loading is now handled in updateAuthUI() when user logs in
    // This ensures data is loaded after authentication is confirmed
    console.log('DOM loaded, authentication will trigger data loading if user is logged in');
});

