           MY CREATIONS GALLERY (Sprint 10 Enhanced)
        ═══════════════════════════════════════════════ */
        let _galleryData = [];
        let _galleryActiveTag = '';

        async function loadGallery() {
            const sort = document.getElementById('gallery-sort')?.value || 'newest';
            try {
                const res = await fetch(`/api/gallery?sort=${sort}`);
                if(!res.ok) throw new Error('No gallery data');
                const data = await res.json();
                _galleryData = data.generations || [];
                renderGallery(_galleryData);
                loadGalleryTags();
            } catch(e) {
                document.getElementById('gallery-grid').innerHTML = '<div class="empty-state">No generations yet. Create something in the Inference Studio!</div>';
            }
        }

        async function loadGalleryTags() {
            try {
                const res = await fetch('/api/gallery/tags');
                const data = await res.json();
                const tags = data.tags || [];
                // Populate dropdown
                const sel = document.getElementById('gallery-tag-filter');
                if(sel) {
                    sel.innerHTML = '<option value="">All Tags</option>' +
                        tags.map(t => `<option value="${t}">${t}</option>`).join('');
                }
                // Populate pill bar
                const bar = document.getElementById('gallery-tag-bar');
                if(bar && tags.length > 0) {
                    bar.style.display = 'flex';
                    bar.innerHTML = `<span class="tag-pill${_galleryActiveTag===''?' active':''}" onclick="loadGalleryByTag('')">All</span>` +
                        tags.map(t => `<span class="tag-pill${_galleryActiveTag===t?' active':''}" onclick="loadGalleryByTag('${t}')">${t}</span>`).join('');
                } else if(bar) {
                    bar.style.display = 'none';
                }
            } catch(e) {
                // Tags endpoint may not be available yet
            }
        }

        async function loadGalleryByTag(tag) {
            _galleryActiveTag = tag;
            if(!tag) {
                loadGallery();
                return;
            }
            try {
                const res = await fetch(`/api/gallery?tag=${encodeURIComponent(tag)}`);
                const data = await res.json();
                _galleryData = data.generations || [];
                renderGallery(_galleryData);
                // Update active pill
                document.querySelectorAll('#gallery-tag-bar .tag-pill').forEach(p => {
                    p.classList.toggle('active', p.innerText === tag);
                });
                const sel = document.getElementById('gallery-tag-filter');
                if(sel) sel.value = tag;
            } catch(e) {
                document.getElementById('gallery-grid').innerHTML = '<div class="empty-state">Failed to filter by tag.</div>';
            }
        }

        function filterGallery(query) {
            const q = query.toLowerCase();
            const filtered = _galleryData.filter(g =>
                (g.prompt || '').toLowerCase().includes(q) ||
                (g.model || '').toLowerCase().includes(q)
            );
            renderGallery(filtered);
        }

        function renderStars(rating) {
            let html = '';
            for(let i = 1; i <= 5; i++) {
                html += `<span class="star${i <= rating ? ' filled' : ''}">★</span>`;
            }
            return html;
        }

        function renderGallery(items) {
            const grid = document.getElementById('gallery-grid');
            if(!items.length) {
                grid.innerHTML = '<div class="empty-state">No creations found.</div>';
                return;
            }
            grid.innerHTML = items.map(g => `
                <div class="card" onclick="openGalleryItem(${g.id})">
                    <div class="card-img-container" style="padding-top:100%;">
                        <img class="card-img" src="${g.image_path}" loading="lazy">
                    </div>
                    <div class="card-banner" style="background:var(--surface);">
                        <h3 style="font-size:0.85rem; height:1.2rem; overflow:hidden;">${g.prompt || 'Untitled'}</h3>
                        <div class="card-meta-row">
                            <span>${g.model || ''}</span>
                            <span>${new Date(g.created_at).toLocaleDateString()}</span>
                        </div>
                        <div class="gallery-star-bar" style="pointer-events:none;">
                            ${renderStars(g.rating || 0)}
                        </div>
                    </div>
                </div>
            `).join('');
        }

        // Sprint 10: Gallery Lightbox with star rating support
        let _glCurrentItem = null;

        function openGalleryItem(id) {
            const g = _galleryData.find(x => x.id === id);
            if(!g) return;
            
            if(window._abSelectMode) {
                if(window._abSelectMode === 'a') {
                    _abSlotA = g;
                    renderABPane('a', g);
                } else if(window._abSelectMode === 'b') {
                    _abSlotB = g;
                    renderABPane('b', g);
                }
                window._abSelectMode = null;
                return;
            }

            _glCurrentItem = g;            document.getElementById('gl-img').src = g.image_path;
            document.getElementById('gl-prompt').innerText = g.prompt || 'N/A';
            document.getElementById('gl-negative').innerText = g.negative || 'N/A';
            document.getElementById('gl-model').innerText = g.model || '—';
            document.getElementById('gl-sampler').innerText = g.sampler || '—';
            document.getElementById('gl-steps').innerText = g.steps || '—';
            document.getElementById('gl-cfg').innerText = g.cfg || '—';
            document.getElementById('gl-size').innerText = `${g.width || '?'}×${g.height || '?'}`;
            document.getElementById('gl-seed').innerText = g.seed || '—';
            document.getElementById('gl-date').innerText = g.created_at ? new Date(g.created_at).toLocaleString() : '';

            // Star rating display
            const bar = document.getElementById('gl-star-bar');
            if(bar) {
                bar.dataset.id = g.id;
                bar.dataset.rating = g.rating || 0;
                updateStarDisplay(g.rating || 0);
            }

            document.getElementById('gallery-lightbox').style.display = 'flex';
        }

        // Sprint 10: Star Rating UI
        function updateStarDisplay(rating) {
            const bar = document.getElementById('gl-star-bar');
            if(!bar) return;
            const stars = bar.querySelectorAll('.star');
            stars.forEach((s, i) => {
                s.classList.toggle('filled', i < rating);
            });
        }

        function hoverStars(n) {
            const bar = document.getElementById('gl-star-bar');
            if(!bar) return;
            const stars = bar.querySelectorAll('.star');
            stars.forEach((s, i) => {
                s.classList.toggle('hover-active', i < n);
            });
        }

        function unhoverStars() {
            const bar = document.getElementById('gl-star-bar');
            if(!bar) return;
            bar.querySelectorAll('.star').forEach(s => s.classList.remove('hover-active'));
        }

        async function rateGeneration(rating) {
            const bar = document.getElementById('gl-star-bar');
            if(!bar) return;
            const id = parseInt(bar.dataset.id);
            bar.dataset.rating = rating;
            updateStarDisplay(rating);

            // Update local data
            const g = _galleryData.find(x => x.id === id);
            if(g) g.rating = rating;

            // Persist to backend
            try {
                await fetch('/api/gallery/rate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id, rating })
                });
            } catch(e) {
                console.warn('Failed to persist rating:', e);
            }
        }

        async function restoreToStudioFromGallery() {
            const bar = document.getElementById('gl-star-bar');
            if(!bar) return;
            const id = parseInt(bar.dataset.id);
            const g = _galleryData.find(x => x.id === id);
            if(!g) return;
            
            // Rehydrate studio
            if(g.prompt) {
                const promptEl = document.getElementById('inf-prompt');
                if(promptEl) promptEl.value = g.prompt;
            }
            if(g.negative_prompt) {
                const negEl = document.getElementById('inf-negative');
                if(negEl) negEl.value = g.negative_prompt;
            }
            if(g.model_name) {
                const modEl = document.getElementById('inf-model');
                if(modEl) modEl.value = g.model_name;
            }
            if(g.loras) {
                const lorasEl = document.getElementById('inf-loras');
                if(lorasEl) lorasEl.value = g.loras;
            }
            
            try {
                const params = JSON.parse(g.parameters || '{}');
                if(params.width) document.getElementById('inf-width').value = params.width;
                if(params.height) document.getElementById('inf-height').value = params.height;
                if(params.steps) document.getElementById('inf-steps').value = params.steps;
                if(params.cfg) document.getElementById('inf-cfg').value = params.cfg;
                if(params.sampler_name) document.getElementById('inf-sampler').value = params.sampler_name;
                if(params.seed !== undefined) document.getElementById('inf-seed').value = params.seed;
            } catch(e) {}
            
            document.getElementById('gallery-lightbox').style.display = 'none';
            switchTab('inference', document.querySelector('.nav-item[onclick*="inference"]'));
            showSettingsToast('⚡ Sent to Studio!');
        }

        async function deleteGenerationFromGallery() {
            const bar = document.getElementById('gl-star-bar');
            if(!bar) return;
            const id = parseInt(bar.dataset.id);
            if(!confirm("Are you sure you want to delete this generation?")) return;
            
            try {
                const res = await fetch('/api/gallery/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: id })
                });
                const data = await res.json();
                if(data.status === 'success') {
                    document.getElementById('gallery-lightbox').style.display = 'none';
                    _galleryData = _galleryData.filter(x => x.id !== id);
                    renderGallery(_galleryData);
                    showSettingsToast('🗑 Generation deleted');
                } else alert(data.message);
            } catch(e) {
                alert('Delete failed: ' + e.message);
            }
        }

        /* ═══════════════════════════════════════════════
           SPRINT 10 — A/B Comparison
        ═══════════════════════════════════════════════ */
        let _abSlotA = null, _abSlotB = null;
        let _abSelectMode = null; // 'a' or 'b'

        function startABComparison() {
            if(!_glCurrentItem) return;
            // Load current item into slot A
            _abSlotA = { ..._glCurrentItem };
            _abSlotB = null;
            _abSelectMode = 'b'; // Next gallery click goes to B

            // Close gallery lightbox, open A/B
            document.getElementById('gallery-lightbox').style.display = 'none';
            const overlay = document.getElementById('ab-comparison');
            overlay.classList.add('open');
            window._abSelectMode = 'b';

            // Render pane A
            renderABPane('a', _abSlotA);
            // Clear pane B
            document.getElementById('ab-img-b').style.display = 'none';
            document.getElementById('ab-empty-b').style.display = 'block';
            document.getElementById('ab-empty-b').innerText = 'Click any gallery card to set Image B';
            document.getElementById('ab-meta-b').innerHTML = '';

            showSettingsToast('Click a gallery card to select Image B');
        }

        function renderABPane(side, item) {
            const img = document.getElementById('ab-img-' + side);
            const empty = document.getElementById('ab-empty-' + side);
            const meta = document.getElementById('ab-meta-' + side);
            if(!item) return;
            img.src = item.image_path;
            img.style.display = 'block';
            empty.style.display = 'none';
            meta.innerHTML = `<b>Model:</b> ${item.model || '—'} · <b>Steps:</b> ${item.steps || '—'} · <b>CFG:</b> ${item.cfg || '—'} · <b>Seed:</b> ${item.seed || '—'}<br><b>Prompt:</b> ${(item.prompt || '').substring(0, 120)}${(item.prompt || '').length > 120 ? '...' : ''}`;
        }

        function closeABComparison() {
            document.getElementById('ab-comparison').classList.remove('open');
            window._abSelectMode = null;
        }

        function openComparePicker(side) {
            window._abSelectMode = side;
            showSettingsToast(`Click a gallery card to select Image ${side.toUpperCase()}`);
        }

        function swapABPanes() {
            const tmp = _abSlotA;
            _abSlotA = _abSlotB;
            _abSlotB = tmp;
            if(_abSlotA) renderABPane('a', _abSlotA);
            else {
                document.getElementById('ab-img-a').style.display = 'none';
                document.getElementById('ab-empty-a').style.display = 'block';
            }
            if(_abSlotB) renderABPane('b', _abSlotB);
            else {
                document.getElementById('ab-img-b').style.display = 'none';
                document.getElementById('ab-empty-b').style.display = 'block';
            }
        }

        // A/B divider drag
        document.addEventListener('DOMContentLoaded', () => {
            const divider = document.getElementById('ab-divider');
            if(!divider) return;
            divider.addEventListener('mousedown', (e) => {
                e.preventDefault();
                divider.classList.add('dragging');
                const body = document.querySelector('.ab-body');
                const paneA = document.getElementById('ab-pane-a');
                const paneB = document.getElementById('ab-pane-b');
                const startX = e.clientX;
                const startWidthA = paneA.offsetWidth;
                const totalWidth = body.offsetWidth - 4; // minus divider
                function onMove(ev) {
                    const dx = ev.clientX - startX;
                    const newA = Math.max(100, Math.min(totalWidth - 100, startWidthA + dx));
                    paneA.style.flex = 'none';
                    paneA.style.width = newA + 'px';
                    paneB.style.flex = '1';
                }
                function onUp() {
                    divider.classList.remove('dragging');
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onUp);
                }
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
            });
        });

        /* --- CivitAI Explorer Integration --- */
        let installedHashes = new Set(); // To cross-check installed models
        window.cardState = {}; // Carousel indexes
        window.onlyNsfw = false;
        let vaultOffset = 0;
        const vaultLimit = 40;

        // Helper: detect if a version is in early access
        function isVersionEarlyAccess(v) {
            // CivitAI current API: availability field
            if(v.availability && v.availability === 'EarlyAccess') return true;
            // Legacy fallback fields
            if(v.earlyAccessEndsAt) {
                return new Date(v.earlyAccessEndsAt) > new Date();
            }
            if(v.earlyAccessTimeFrame && v.earlyAccessTimeFrame > 0) return true;
            return false;
        }

        // Helper: format download count with K/M suffix
        function formatDownloadCount(count) {
            if(!count || count < 1000) return String(count || 0);
            if(count >= 1000000) return (count / 1000000).toFixed(1) + 'M';
            return (count / 1000).toFixed(1) + 'k';
        }
        
        function handleNsfwClick(e) {
            e.preventDefault();
            const cb = document.getElementById('ex-nsfw');
            cb.checked = !cb.checked;
            window.onlyNsfw = cb.checked ? e.altKey : false;
            loadExplorer();
        }

        // Phase 5: Dynamic type filter based on source
        const _civitaiTypes = '<option value="">All Types</option><option value="Checkpoint">Checkpoint</option><option value="TextualInversion">Embedding / TextualInversion</option><option value="Hypernetwork">Hypernetwork</option><option value="AestheticGradient">Aesthetic Gradient</option><option value="LORA">LoRA</option><option value="LoCon">LoCon / LyCORIS</option><option value="DoRA">DoRA</option><option value="Controlnet">Controlnet</option><option value="Upscaler">Upscaler</option><option value="MotionModule">Motion</option><option value="VAE">VAE</option><option value="Poses">Poses</option><option value="Wildcards">Wildcards</option><option value="Workflows">Workflows</option><option value="Detection">Detection</option><option value="Other">Other</option><option value="Text Encoder">Text Encoder (CLIP/T5)</option>';
        const _hfTypes = '<option value="">All Tasks</option><option value="text-to-image">Text-to-Image</option><option value="image-to-image">Image-to-Image</option><option value="LORA">LoRA</option><option value="Controlnet">ControlNet</option><option value="Text Encoder">Text Encoder (CLIP/T5)</option>';

        function onExplorerSourceChange() {
            const source = document.getElementById('ex-source').value;
            const typeSelect = document.getElementById('ex-type');
            typeSelect.innerHTML = (source === 'huggingface') ? _hfTypes : _civitaiTypes;
            loadExplorer();
        }

