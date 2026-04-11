           SPRINT 8 — COMMAND PALETTE
        ═══════════════════════════════════════════════ */
        const _commandRegistry = [
            { icon: '📊', label: 'Go to Dashboard', action: () => switchTab('dashboard'), shortcut: '' },
            { icon: '🔍', label: 'Go to Model Explorer', action: () => switchTab('explorer'), shortcut: '' },
            { icon: '🗄️', label: 'Go to Global Vault', action: () => switchTab('vault'), shortcut: '' },
            { icon: '🎨', label: 'Go to My Creations', action: () => switchTab('creations'), shortcut: '' },
            { icon: '🎛️', label: 'Go to Inference Studio', action: () => switchTab('inference'), shortcut: '' },
            { icon: '🏪', label: 'Go to App Store', action: () => switchTab('appstore'), shortcut: '' },
            { icon: '📦', label: 'Go to Installed Packages', action: () => switchTab('packages'), shortcut: '' },
            { icon: '⚙️', label: 'Go to Settings', action: () => switchTab('settings'), shortcut: '' },
            { icon: '📥', label: 'Scan Vault for New Models', action: () => { triggerUnmanagedImport(); }, shortcut: '' },
            { icon: '🔄', label: 'Check for Model Updates', action: () => { triggerUpdatesCheck(); }, shortcut: '' },
            { icon: '🩺', label: 'Run Vault Health Check', action: () => { triggerHealthCheck(); }, shortcut: '' },
            { icon: '📚', label: 'Open Prompt Library', action: () => { switchTab('inference'); setTimeout(togglePromptLibrary, 300); }, shortcut: '' },
            // Sprint 10: New commands
            { icon: '🔎', label: 'Search Models in Vault', action: () => { switchTab('vault'); setTimeout(() => document.getElementById('vault-search')?.focus(), 300); }, shortcut: '' },
            { icon: '🖼️', label: 'View Recent Generations', action: () => { switchTab('creations'); }, shortcut: '' },
            { icon: '🎨', label: 'Toggle Theme (Dark/Light/Glass)', action: () => {
                const themes = ['dark', 'light', 'glass'];
                const current = document.body.getAttribute('data-theme') || 'dark';
                const next = themes[(themes.indexOf(current) + 1) % themes.length];
                document.body.setAttribute('data-theme', next);
                const themeEl = document.getElementById('set-theme');
                if(themeEl) themeEl.value = next;
                showSettingsToast(`Theme switched to ${next}`);
            }, shortcut: '' },
            { icon: '🔀', label: 'A/B Compare Generations', action: () => { switchTab('creations'); showSettingsToast('Open a generation, then click Compare A/B'); }, shortcut: '' },
            // Sprint 12: New commands
            { icon: '📊', label: 'Open X/Y/Z Parameter Plot', action: () => { switchTab('inference'); setTimeout(toggleXYZPanel, 300); }, shortcut: '' },
            { icon: '🌱', label: 'Run Seed Explorer (9 Variations)', action: () => { switchTab('inference'); setTimeout(() => { toggleXYZPanel(); runSeedExplorer(9); }, 300); }, shortcut: '' },
            { icon: '🖌️', label: 'Toggle Inpaint Mode', action: () => { switchTab('inference'); setTimeout(toggleInpaintMode, 300); }, shortcut: '' },
            { icon: '📐', label: 'Toggle Regional Prompting', action: () => { switchTab('inference'); setTimeout(toggleRegionMode, 300); }, shortcut: '' },
        ];
        let _cmdActiveIndex = 0;
        let _cmdFiltered = [..._commandRegistry];

        function openCommandPalette() {
            const overlay = document.getElementById('command-palette');
            overlay.classList.add('open');
            const input = document.getElementById('cmd-search');
            input.value = '';
            input.focus();
            _cmdActiveIndex = 0;
            _cmdFiltered = [..._commandRegistry];
            renderCommandList();
        }

        function closeCommandPalette() {
            document.getElementById('command-palette').classList.remove('open');
        }

        function filterCommands(query) {
            const q = query.toLowerCase();
            _cmdFiltered = _commandRegistry.filter(c => c.label.toLowerCase().includes(q));
            _cmdActiveIndex = 0;
            renderCommandList();
        }

        function renderCommandList() {
            const list = document.getElementById('cmd-list');
            if(_cmdFiltered.length === 0) {
                list.innerHTML = '<div style="padding:20px 22px; color:var(--text-muted); text-align:center;">No matching commands</div>';
                return;
            }
            list.innerHTML = _cmdFiltered.map((c, i) => `
                <div class="cmd-item${i === _cmdActiveIndex ? ' active' : ''}"
                     onclick="executeCommand(${i})"
                     onmouseenter="_cmdActiveIndex=${i}; renderCommandList();">
                    <span class="cmd-icon">${c.icon}</span>
                    <span class="cmd-label">${c.label}</span>
                    ${c.shortcut ? `<span class="cmd-shortcut">${c.shortcut}</span>` : ''}
                </div>
            `).join('');
        }

        function executeCommand(index) {
            const cmd = _cmdFiltered[index];
            if(cmd) {
                closeCommandPalette();
                cmd.action();
            }
        }

        function handleCmdKeydown(e) {
            if(e.key === 'ArrowDown') {
                e.preventDefault();
                _cmdActiveIndex = Math.min(_cmdActiveIndex + 1, _cmdFiltered.length - 1);
                renderCommandList();
            } else if(e.key === 'ArrowUp') {
                e.preventDefault();
                _cmdActiveIndex = Math.max(_cmdActiveIndex - 1, 0);
                renderCommandList();
            } else if(e.key === 'Enter') {
                e.preventDefault();
                executeCommand(_cmdActiveIndex);
            } else if(e.key === 'Escape') {
                closeCommandPalette();
            }
        }

        // Global keyboard shortcut: Ctrl+K / Cmd+K
        document.addEventListener('keydown', (e) => {
            if((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const overlay = document.getElementById('command-palette');
                if(overlay.classList.contains('open')) {
                    closeCommandPalette();
                } else {
                    openCommandPalette();
                }
            }
        });

        /* ═══════════════════════════════════════════════
