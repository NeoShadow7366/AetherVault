           SETTINGS PANEL — Load / Save / OTA
        ═══════════════════════════════════════════════ */
        async function loadSettings() {
            try {
                const res = await fetch('/api/settings');
                const data = await res.json();
                document.getElementById('set-api-key').value = data.civitai_api_key || '';
                document.getElementById('set-hf-api-key').value = data.hf_api_key || '';
                const themeEl = document.getElementById('set-theme');
                if(themeEl && data.theme) { themeEl.value = data.theme; document.body.setAttribute('data-theme', data.theme); }
                const accentEl = document.getElementById('set-accent');
                if(accentEl && data.accent) {
                    accentEl.value = data.accent;
                    // S-1 fix: Validate CSS color before applying
                    const testEl = document.createElement('span');
                    testEl.style.color = data.accent;
                    if (testEl.style.color) {
                        document.body.style.setProperty('--primary', data.accent);
                    }
                }
                const updEl = document.getElementById('set-updates');
                if(updEl && data.auto_updates !== undefined) updEl.value = String(data.auto_updates);
                // Sprint 7: LAN toggle
                const lanEl = document.getElementById('set-lan-sharing');
                if(lanEl) lanEl.checked = !!data.lan_sharing;
                if(data.civitai_api_key) localStorage.setItem('civitai_api_key', data.civitai_api_key);
                if(data.hf_api_key) localStorage.setItem('hf_api_key', data.hf_api_key);
                
                // Phase 6: Load favorites from SQLite (migrated from settings.json)
                try {
                    const favRes = await fetch('/api/favorites');
                    window.appFavorites = await favRes.json() || {};
                } catch(e) { window.appFavorites = {}; }
            } catch(e) {
                console.warn('Failed to load settings from server:', e);
            }
        }

        async function saveSettings() {
            const payload = {
                civitai_api_key: document.getElementById('set-api-key').value,
                hf_api_key: document.getElementById('set-hf-api-key').value,
                theme: document.getElementById('set-theme').value,
                accent: document.getElementById('set-accent').value,
                auto_updates: document.getElementById('set-updates').value === 'true',
                lan_sharing: document.getElementById('set-lan-sharing').checked
            };
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if(data.status === 'success') {
                    localStorage.setItem('civitai_api_key', payload.civitai_api_key);
                    localStorage.setItem('hf_api_key', payload.hf_api_key);
                    // Apply theme to DOM immediately
                    if(payload.theme) document.body.setAttribute('data-theme', payload.theme);
                    if(payload.accent) document.body.style.setProperty('--primary', payload.accent);
                    showSettingsToast('✅ Settings saved successfully.' + (payload.lan_sharing ? ' LAN changes apply on restart.' : ''));
                } else {
                    showSettingsToast('❌ Failed to save: ' + (data.message || 'Unknown error'));
                }
            } catch(e) {
                showSettingsToast('❌ Network error: ' + e.message);
            }
        }

        function showSettingsToast(msg) {
            const toast = document.getElementById('global-sync-toast');
            toast.innerText = msg;
            toast.style.display = 'flex';
            setTimeout(() => { toast.style.display = 'none'; }, 3000);
        }

        async function triggerSystemUpdate() {
            if(!confirm('Apply System Update?\n\nThis will pull the latest code from the repository and restart the server. Your Global Vault, settings, and database are safe.')) return;
            try {
                const modal = document.getElementById('ext-modal');
                if(modal) {
                    modal.style.display = 'flex';
                    document.getElementById('ext-title').innerText = "System OTA Update";
                    document.getElementById('ext-progress-text').innerText = "Initiating Update...";
                    document.getElementById('ext-progress-bar').style.width = '10%';
                    document.getElementById('ext-log-output').innerText = "[Client] Requesting System Update from server...\n";
                }

                const res = await fetch('/api/system/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                });
                const data = await res.json();
                
                if(modal) {
                    const logEl = document.getElementById('ext-log-output');
                    if(data.status === 'success') {
                        logEl.innerText += "[Server] Updater spawned.\n[Server] Detaching and shutting down current instance...\n[Client] Waiting for reboot...";
                        document.getElementById('ext-progress-text').innerText = "Restarting Server...";
                        document.getElementById('ext-progress-bar').style.width = '50%';
                    } else {
                        logEl.innerText += `\n[Error] ${data.message || 'Unknown'}`;
                        document.getElementById('ext-progress-text').innerText = "Update Failed";
                    }
                } else if(data.status === 'success') {
                    showSettingsToast('🔄 Update started. Server restarting...');
                } else alert('Update failed: ' + data.message);

                if(data.status === 'success') waitForReboot();
            } catch(e) {
                if(document.getElementById('ext-log-output')) {
                    document.getElementById('ext-log-output').innerText += `\n[Exception] ${e.message}`;
                } else alert('Failed to trigger update: ' + e.message);
            }
        }

        function waitForReboot() {
            // Gray out the UI and poll /api/server_status until the server comes back
            document.body.style.opacity = '0.4';
            document.body.style.pointerEvents = 'none';
            const overlay = document.createElement('div');
            overlay.id = 'reboot-overlay';
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;color:white;font-family:inherit;';
            overlay.innerHTML = `
                <div style="font-size:3rem;margin-bottom:20px;animation:spin 2s linear infinite;">⚙️</div>
                <div style="font-size:1.3rem;font-weight:700;margin-bottom:10px;">Applying System Update</div>
                <div id="reboot-status" style="color:#94a3b8;font-size:0.95rem;">Waiting for server to restart...</div>
                <style>@keyframes spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}</style>
            `;
            document.body.appendChild(overlay);
            document.body.style.opacity = '1';
            document.body.style.pointerEvents = 'auto';

            let attempts = 0;
            const maxAttempts = 60; // 2 minutes max wait
            const pollInterval = setInterval(async () => {
                attempts++;
                const statusEl = document.getElementById('reboot-status');
                if(statusEl) statusEl.innerText = `Polling server... (attempt ${attempts}/${maxAttempts})`;
                try {
                    const res = await fetch('/api/server_status', { signal: AbortSignal.timeout(3000) });
                    if(res.ok) {
                        clearInterval(pollInterval);
                        if(statusEl) statusEl.innerText = '✅ Server is back online! Reloading...';
                        setTimeout(() => location.reload(), 1000);
                    }
                } catch(e) {
                    // Server still down — continue polling
                }
                if(attempts >= maxAttempts) {
                    clearInterval(pollInterval);
                    const el = document.getElementById('reboot-overlay');
                    if(el) el.innerHTML = `
                        <div style="font-size:2rem;margin-bottom:20px;">⚠️</div>
                        <div style="font-size:1.2rem;font-weight:700;margin-bottom:10px;">Server did not restart in time</div>
                        <div style="color:#94a3b8;font-size:0.9rem;margin-bottom:20px;">Please restart the server manually and reload this page.</div>
                        <button onclick="location.reload()" style="background:var(--primary);color:#fff;border:none;padding:12px 24px;border-radius:8px;font-weight:600;cursor:pointer;">Reload Page</button>
                    `;
                }
            }, 2000);
        }

        /* ═══════════════════════════════════════════════
           SPRINT 7 — RECIPE LIVE PREVIEW
        ═══════════════════════════════════════════════ */
        function updateRecipePreview() {
            const obj = {
                app_id: document.getElementById('recipe-id').value || '',
                name: document.getElementById('recipe-name').value || '',
                repository: document.getElementById('recipe-repo').value || '',
                launch: document.getElementById('recipe-launch').value || '',
                pip_packages: (document.getElementById('recipe-pip').value || '').split(',').map(s=>s.trim()).filter(Boolean),
                symlink_targets: Array.from(document.querySelectorAll('.recipe-symlink-cb:checked')).map(cb => cb.value),
                platform_flags: (document.getElementById('recipe-platform-flags') || {}).value || '',
                requirements_file: 'requirements.txt'
            };
            const el = document.getElementById('recipe-json-preview');
            if(el) el.textContent = JSON.stringify(obj, null, 2);
        }
        function exportRecipeJSON() {
            const el = document.getElementById('recipe-json-preview');
            if(el) {
                navigator.clipboard.writeText(el.textContent).then(() => showSettingsToast('📋 Recipe JSON copied to clipboard!'));
            }
        }

        /* ═══════════════════════════════════════════════
           SPRINT 7 — VAULT BULK SELECTION
        ═══════════════════════════════════════════════ */
        let _vaultSelectMode = false;
        function toggleVaultSelectMode() {
            _vaultSelectMode = !_vaultSelectMode;
            const grid = document.getElementById('models-grid');
            const btn = document.getElementById('vault-select-toggle');
            if(_vaultSelectMode) {
                grid.classList.add('vault-select-mode');
                btn.style.background = 'var(--primary)';
                btn.style.color = '#fff';
            } else {
                grid.classList.remove('vault-select-mode');
                btn.style.background = 'var(--surface-hover)';
                btn.style.color = 'var(--text-muted)';
                cancelVaultSelection();
            }
        }
        function updateVaultSelection() {
            const checked = document.querySelectorAll('.vault-select-checkbox:checked');
            const bar = document.getElementById('vault-action-bar');
            const countEl = document.getElementById('vault-select-count');
            if(checked.length > 0) {
                bar.style.display = 'flex';
                countEl.innerText = `${checked.length} model${checked.length > 1 ? 's' : ''} selected`;
            } else {
                bar.style.display = 'none';
            }
        }
        function cancelVaultSelection() {
            document.querySelectorAll('.vault-select-checkbox:checked').forEach(cb => cb.checked = false);
            document.getElementById('vault-action-bar').style.display = 'none';
        }
        async function executeBulkDelete() {
            const checked = document.querySelectorAll('.vault-select-checkbox:checked');
            if(checked.length === 0) return;
            const models = Array.from(checked).map(cb => ({
                filename: cb.dataset.filename,
                category: cb.dataset.category
            }));
            const names = models.map(m => m.filename).join('\n');
            if(!confirm(`Delete ${models.length} model${models.length > 1 ? 's' : ''}?\n\n${names}\n\nThis cannot be undone!`)) return;
            try {
                const res = await fetch('/api/vault/bulk_delete', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ models })
                });
                const data = await res.json();
                showSettingsToast(`🗑️ Deleted ${data.deleted} model${data.deleted !== 1 ? 's' : ''}` + (data.failed?.length ? `, ${data.failed.length} failed` : ''));
                cancelVaultSelection();
                loadModels(false);
            } catch(e) { alert('Bulk delete failed: ' + e.message); }
        }
        /* ═══════════════════════════════════════════════
           SPRINT 8 — VAULT EXPORT
        ═══════════════════════════════════════════════ */
        function executeVaultExport() {
            const checked = document.querySelectorAll('.vault-select-checkbox:checked');
            if(checked.length === 0) return alert('No models selected.');
            document.getElementById('export-dialog').style.display = 'flex';
            document.getElementById('export-include-files').checked = false;
        }

        async function executeVaultExportConfirm() {
            const checked = document.querySelectorAll('.vault-select-checkbox:checked');
            const filenames = Array.from(checked).map(cb => cb.dataset.filename);
            const includeFiles = document.getElementById('export-include-files').checked;

            document.getElementById('export-dialog').style.display = 'none';

            if(includeFiles) {
                // Download as zip via form submission
                try {
                    showSettingsToast('📦 Building export archive... please wait.');
                    const res = await fetch('/api/vault/export', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ filenames, include_files: true })
                    });
                    if(!res.ok) throw new Error('Export failed');
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `vault_export_${Date.now()}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showSettingsToast('✅ Export downloaded!');
                } catch(e) {
                    alert('Export failed: ' + e.message);
                }
            } else {
                // Metadata-only JSON export
                try {
                    const res = await fetch('/api/vault/export', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ filenames, include_files: false })
                    });
                    const data = await res.json();
                    if(data.status === 'success') {
                        const jsonStr = JSON.stringify(data.manifest, null, 2);
                        const blob = new Blob([jsonStr], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `vault_metadata_${Date.now()}.json`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        showSettingsToast('✅ Metadata exported!');
                    } else alert(data.message);
                } catch(e) {
                    alert('Export failed: ' + e.message);
                }
            }
            cancelVaultSelection();
        }

        /* ═══════════════════════════════════════════════
