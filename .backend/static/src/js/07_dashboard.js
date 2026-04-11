                // Sprint 7: LAN Banner
                const lanBanner = document.getElementById('lan-banner');
                if(data.lan_sharing && lanBanner) {
                    const port = location.port || '8080';
                    const ip = data.lan_ip || '0.0.0.0';
                    document.getElementById('lan-ip-display').innerText = `http://${ip}:${port}`;
                    lanBanner.style.display = 'block';
                } else if(lanBanner) {
                    lanBanner.style.display = 'none';
                }
                // Sprint 8: Dashboard Analytics
                updateDashboardCards(data);
            } catch(e) {}
        }

        function formatBytes(bytes) {
            if(!bytes || bytes === 0) return '0 B';
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return (bytes / Math.pow(1024, i)).toFixed(i > 1 ? 1 : 0) + ' ' + sizes[i];
        }

        function updateDashboardCards(data) {
            const el = (id) => document.getElementById(id);
            if(el('dash-models')) el('dash-models').innerText = data.total_models ?? '—';
            if(el('dash-generations')) el('dash-generations').innerText = data.total_generations ?? '—';
            if(el('dash-vault-size')) el('dash-vault-size').innerText = formatBytes(data.vault_size_bytes);
            if(el('dash-packages')) el('dash-packages').innerText = data.installed_packages ?? '—';
            if(el('dash-prompts')) el('dash-prompts').innerText = data.prompts_saved ?? '—';
            if(el('dash-running')) el('dash-running').innerText = data.running_packages ?? '—';

            // Sprint 9: Activity Feed
            if(data.recent_generations || data.recent_downloads) {
                renderActivityFeed(data.recent_generations || [], data.recent_downloads || []);
            }
            // Sprint 9: Donut Chart
            if(data.category_distribution) {
                renderDonutChart(data.category_distribution);
            }

            // Sprint 10: Disk Space Warning
            const diskWarn = document.getElementById('dash-disk-warning');
            if(diskWarn && data.vault_size_bytes && data.vault_size_warning_gb) {
                const vaultGB = data.vault_size_bytes / (1024 * 1024 * 1024);
                if(vaultGB >= data.vault_size_warning_gb) {
                    const detail = document.getElementById('dash-disk-detail');
                    detail.innerText = `Vault is using ${vaultGB.toFixed(1)} GB (threshold: ${data.vault_size_warning_gb} GB). Consider removing unused models.`;
                    diskWarn.style.display = 'flex';
                } else {
                    diskWarn.style.display = 'none';
                }
            }
        }

        async function refreshDashboard() {
            try {
                const res = await fetch('/api/server_status');
                const data = await res.json();
                updateDashboardCards(data);
            } catch(e) {}
        }
        setInterval(checkSystemStatus, 3000);
        setInterval(pollDownloads, 1000); // 1-second background poll

        /* ═════════════════════════════════════════════
           SPRINT 9 — Dashboard Intelligence
        ═════════════════════════════════════════════ */

        function timeAgo(dateStr) {
            if(!dateStr) return '';
            const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
            if(diff < 60) return 'just now';
            if(diff < 3600) return Math.floor(diff/60) + 'm ago';
            if(diff < 86400) return Math.floor(diff/3600) + 'h ago';
            return Math.floor(diff/86400) + 'd ago';
        }

        function renderActivityFeed(generations, downloads) {
            const container = document.getElementById('dash-activity-list');
            if(!container) return;

            let items = [];
            for(const g of generations) {
                items.push({
                    icon: '🎨', type: 'generation',
                    primary: (g.prompt || 'No prompt').substring(0, 60) + (g.prompt && g.prompt.length > 60 ? '...' : ''),
                    secondary: g.model || 'Unknown model',
                    time: timeAgo(g.created_at),
                    sortKey: new Date(g.created_at || 0).getTime()
                });
            }
            for(const d of downloads) {
                items.push({
                    icon: '📥', type: 'download',
                    primary: d.model_name || d.filename || 'Download',
                    secondary: 'Completed',
                    time: timeAgo(d.completed_at),
                    sortKey: new Date(d.completed_at || 0).getTime()
                });
            }

            items.sort((a, b) => b.sortKey - a.sortKey);
            items = items.slice(0, 8);

            if(items.length === 0) {
                container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 20px;">No recent activity.</div>';
                return;
            }

            container.innerHTML = items.map(it => `
                <div class="activity-item" onclick="switchTab('${it.type === 'generation' ? 'creations' : 'vault'}')">
                    <div class="activity-icon">${it.icon}</div>
                    <div class="activity-text">
                        <div class="primary">${it.primary}</div>
                        <div class="secondary">${it.secondary}</div>
                    </div>
                    <div class="activity-time">${it.time}</div>
                </div>
            `).join('');
        }

        async function clearDashboardActivity() {
            if(!confirm("Clear Dashboard Activity Feed?\n\nThis will clear the downloads log. Your Gallery generations and actual files will NOT be affected, as requested.")) return;
            try {
                const res = await fetch('/api/dashboard/clear_history', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({}) });
                const data = await res.json();
                if(data.status === 'success') {
                    showSettingsToast('🧹 Feed cleared.');
                    refreshDashboard();
                } else alert("Failed: " + data.message);
            } catch(e) { alert("Failed to clear feed."); }
        }

        const DONUT_COLORS = ['#6366f1','#f59e0b','#10b981','#3b82f6','#ec4899','#8b5cf6','#06b6d4','#f43f5e','#84cc16','#a855f7'];

        function renderDonutChart(distribution) {
            const svg = document.getElementById('dash-donut');
            const legend = document.getElementById('dash-donut-legend');
            if(!svg || !legend) return;

            // Rest of donut chart code omitted here


            const entries = Object.entries(distribution).filter(([k,v]) => v > 0);
            const total = entries.reduce((s, [,v]) => s + v, 0);
            if(total === 0) {
                svg.innerHTML = '<text x="100" y="105" text-anchor="middle" fill="#64748b" font-size="14">No models</text>';
                legend.innerHTML = '';
                return;
            }

            const cx = 100, cy = 100, r = 75, inner = 45;
            let startAngle = -Math.PI / 2;
            let paths = '';

            entries.forEach(([cat, count], i) => {
                const fraction = count / total;
                const endAngle = startAngle + fraction * 2 * Math.PI;
                const largeArc = fraction > 0.5 ? 1 : 0;

                const x1 = cx + r * Math.cos(startAngle);
                const y1 = cy + r * Math.sin(startAngle);
                const x2 = cx + r * Math.cos(endAngle);
                const y2 = cy + r * Math.sin(endAngle);
                const ix1 = cx + inner * Math.cos(endAngle);
                const iy1 = cy + inner * Math.sin(endAngle);
                const ix2 = cx + inner * Math.cos(startAngle);
                const iy2 = cy + inner * Math.sin(startAngle);

                const color = DONUT_COLORS[i % DONUT_COLORS.length];
                paths += `<path d="M${x1},${y1} A${r},${r} 0 ${largeArc} 1 ${x2},${y2} L${ix1},${iy1} A${inner},${inner} 0 ${largeArc} 0 ${ix2},${iy2} Z" fill="${color}" opacity="0.85"><title>${cat}: ${count} (${(fraction*100).toFixed(1)}%)</title></path>`;
                startAngle = endAngle;
            });

            // Center text
            paths += `<text x="${cx}" y="${cy-4}" text-anchor="middle" fill="#f1f5f9" font-size="22" font-weight="700">${total}</text>`;
            paths += `<text x="${cx}" y="${cy+14}" text-anchor="middle" fill="#94a3b8" font-size="10">models</text>`;
            svg.innerHTML = paths;

            legend.innerHTML = entries.map(([cat, count], i) => {
                const color = DONUT_COLORS[i % DONUT_COLORS.length];
                return `<div class="donut-legend-item"><div class="donut-legend-dot" style="background:${color}"></div>${cat} (${count})</div>`;
            }).join('');
        }

        /* ═════════════════════════════════════════════
           SPRINT 9 — Token Counter
        ═════════════════════════════════════════════ */

        function getTokenLimit() {
            const modelType = document.getElementById('inf-model-type');
            if(!modelType) return 77;
            const val = modelType.value;
            if(val === 'flux-dev' || val === 'flux-schnell') return 512;
            if(val === 'sdxl') return 154; // 77 * 2 (dual encoder)
            return 77; // SD 1.5 default
        }

        function countTokens(text) {
            if(!text || !text.trim()) return 0;
            // CLIP-style approximation: split on whitespace and commas, each segment is ~1 token
            return text.split(/[\s,]+/).filter(t => t.length > 0).length;
        }

        function updateTokenCounter() {
            const prompt = document.getElementById('inf-prompt');
            const countEl = document.getElementById('inf-token-count');
            const limitEl = document.getElementById('inf-token-limit');
            const container = document.getElementById('inf-token-counter');
            if(!prompt || !countEl || !container) return;

            const count = countTokens(prompt.value);
            const limit = getTokenLimit();
            countEl.innerText = count;
            if(limitEl) limitEl.innerText = limit;

            const ratio = count / limit;
            container.className = 'token-counter ' + (ratio > 0.75 ? 'red' : ratio > 0.5 ? 'yellow' : 'green');
        }

        /* ═════════════════════════════════════════════
