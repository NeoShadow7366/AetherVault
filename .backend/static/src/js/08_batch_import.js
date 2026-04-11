           SPRINT 9 — Batch Generation Queue
        ═════════════════════════════════════════════ */

        let _batchPollInterval = null;

        function getInferencePayload() {
            // Gather current inference parameters into a payload object
            const payload = {
                prompt: resolveWildcards(document.getElementById('inf-prompt')?.value || ''),
                negative: resolveWildcards(document.getElementById('inf-negative')?.value || ''),
                steps: parseInt(document.getElementById('inf-steps')?.value || '20'),
                cfg: parseFloat(document.getElementById('inf-cfg')?.value || '7'),
                width: parseInt(document.getElementById('inf-width')?.value || '512'),
                height: parseInt(document.getElementById('inf-height')?.value || '512'),
                seed: parseInt(document.getElementById('inf-seed')?.value || '-1'),
                sampler: document.getElementById('inf-sampler')?.value || 'euler',
                scheduler: document.getElementById('inf-scheduler')?.value || 'normal',
                backend: 'comfyui'
            };
            // Model
            const modelSel = document.getElementById('inf-model');
            if(modelSel) payload.model = modelSel.value;
            // Sprint 12: Include inpainting mask if active
            if (hasInpaintMask()) {
                payload.mask_b64 = getInpaintMaskBase64();
                // Also include the current canvas image as init_image for inpainting
                const canvasImg = document.getElementById('inf-canvas-img');
                if (canvasImg && canvasImg.src && canvasImg.style.display !== 'none') {
                    // Convert displayed image to base64
                    const tmpCanvas = document.createElement('canvas');
                    tmpCanvas.width = canvasImg.naturalWidth;
                    tmpCanvas.height = canvasImg.naturalHeight;
                    tmpCanvas.getContext('2d').drawImage(canvasImg, 0, 0);
                    payload.init_image_b64 = tmpCanvas.toDataURL('image/png').split(',')[1];
                }
            }
            // Sprint 12: Include regional prompting data if active
            const regionData = getRegionData();
            if (regionData) {
                payload.regions = regionData;
            }
            return payload;
        }

        async function addToBatchQueue() {
            const payload = getInferencePayload();
            if(!payload.prompt.trim()) {
                showToast('Enter a prompt before adding to queue.'); return;
            }
            try {
                const res = await fetch('/api/generate/batch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ payload })
                });
                const data = await res.json();
                if(data.status === 'success') {
                    showToast(`Added to queue (${data.queue_length} total)`);
                    refreshBatchPanel();
                    if(!_batchPollInterval) {
                        _batchPollInterval = setInterval(refreshBatchPanel, 2000);
                    }
                } else {
                    showToast('Queue error: ' + (data.message || 'Unknown'));
                }
            } catch(e) {
                showToast('Failed to add to queue: ' + e.message);
            }
        }

        async function refreshBatchPanel() {
            try {
                const res = await fetch('/api/generate/queue');
                const data = await res.json();
                const queue = data.queue || [];

                const countEl = document.getElementById('inf-batch-count');
                if(countEl) countEl.innerText = queue.length;

                const listEl = document.getElementById('batch-list');
                if(!listEl) return;

                if(queue.length === 0) {
                    listEl.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding:20px; font-size:0.85rem;">Queue is empty</div>';
                    if(_batchPollInterval) { clearInterval(_batchPollInterval); _batchPollInterval = null; }
                    return;
                }

                listEl.innerHTML = queue.map(j => `
                    <div class="batch-item">
                        <div class="batch-status ${j.status}"></div>
                        <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#e2e8f0;">${j.prompt || '(no prompt)'}</div>
                        <span style="color:var(--text-muted); font-size:0.75rem; flex-shrink:0;">${j.status}</span>
                    </div>
                `).join('');

                // Stop polling if all done/failed
                const allFinished = queue.every(j => j.status === 'done' || j.status === 'failed');
                if(allFinished && _batchPollInterval) {
                    clearInterval(_batchPollInterval); _batchPollInterval = null;
                }
            } catch(e) {}
        }

        function toggleBatchPanel() {
            const panel = document.getElementById('batch-panel');
            if(!panel) return;
            panel.classList.toggle('open');
            if(panel.classList.contains('open')) refreshBatchPanel();
        }

        // ── SSE Consumer: Batch Updates ──────────────────────────
        window._onSSEBatchUpdate = function(data) {
            // Server pushed a batch job status change — refresh the panel UI
            refreshBatchPanel();
            // Show toast notification for completion
            if (data.status === 'done') {
                showToast('🎨 Batch job completed');
            } else if (data.status === 'failed') {
                showToast('❌ Batch job failed: ' + (data.error || 'Unknown error'));
            }
        };

        /* ═════════════════════════════════════════════
           SPRINT 9 — Vault Import from Backup
        ═════════════════════════════════════════════ */

        async function handleVaultImportBackup(file) {
            if(!file) return;
            try {
                const text = await file.text();
                let parsed = JSON.parse(text);
                // Support both direct array manifests and {manifest: [...]} wrappers
                let manifest = Array.isArray(parsed) ? parsed : (parsed.manifest || []);

                if(!manifest.length) {
                    showToast('Invalid manifest: no model entries found.');
                    return;
                }

                const res = await fetch('/api/vault/import', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ manifest })
                });
                const data = await res.json();
                if(data.status === 'success') {
                    showToast(`Import complete: ${data.imported} imported, ${data.skipped} skipped.`);
                    loadModels();  // Refresh vault grid
                } else {
                    showToast('Import failed: ' + (data.message || 'Unknown error'));
                }
            } catch(e) {
                showToast('Import error: ' + e.message);
            }
            // Reset file input
            document.getElementById('vault-import-file').value = '';
        }
        
        /* ═══════════════════════════════════════════════
