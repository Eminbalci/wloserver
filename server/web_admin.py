import asyncio
import logging
import os
import time
import json
import collections
from aiohttp import web

logger = logging.getLogger("WebAdmin")

# Deque to store the last 100 log messages
recent_logs = collections.deque(maxlen=100)

class WebLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            recent_logs.append(msg)
        except Exception:
            self.handleError(record)

# Attach handler to root logger to capture all log messages
log_handler = WebLogHandler()
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(log_handler)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WLO Private Server Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #080c14;
            --panel-bg: rgba(22, 28, 45, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-cyan: #00f2fe;
            --accent-purple: #9b51e0;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-gradient: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            overflow-x: hidden;
            background-image: 
                radial-gradient(at 10% 20%, rgba(0, 242, 254, 0.05) 0px, transparent 50%),
                radial-gradient(at 90% 80%, rgba(155, 81, 224, 0.05) 0px, transparent 50%);
            background-attachment: fixed;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }

        .logo-section h1 {
            font-size: 2rem;
            font-weight: 700;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }

        .logo-section p {
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }

        .server-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            color: var(--accent-green);
            font-weight: 600;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.6; }
            50% { transform: scale(1.1); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.6; }
        }

        /* Dashboard Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        /* Glass Cards */
        .card {
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: var(--glass-shadow);
            transition: transform 0.2s, border-color 0.2s;
        }

        .card:hover {
            border-color: rgba(0, 242, 254, 0.2);
        }

        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-value {
            font-size: 2.25rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.5rem;
        }

        .card-desc {
            font-size: 0.875rem;
            color: var(--text-muted);
        }

        /* Multiplier Section */
        .multiplier-inputs {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .form-group label {
            font-size: 0.875rem;
            color: var(--text-muted);
            font-weight: 600;
        }

        .form-row {
            display: flex;
            gap: 0.5rem;
        }

        input[type="number"], input[type="text"] {
            background: rgba(8, 12, 20, 0.6);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
            outline: none;
            width: 100%;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        input[type="number"]:focus, input[type="text"]:focus {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 10px rgba(0, 242, 254, 0.25);
        }

        button {
            background: var(--accent-gradient);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
        }

        button:hover {
            opacity: 0.9;
        }

        button:active {
            transform: scale(0.98);
        }

        button.btn-danger {
            background: var(--accent-red);
        }

        button.btn-success {
            background: var(--accent-green);
        }

        button.btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }

        /* Logs console */
        .logs-panel {
            grid-column: span 2;
        }

        @media (max-width: 1024px) {
            .logs-panel {
                grid-column: span 1;
            }
        }

        .console {
            background: #04060b;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            height: 300px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8125rem;
            line-height: 1.5;
            color: #38bdf8;
        }

        .console-line {
            margin-bottom: 0.25rem;
            white-space: pre-wrap;
        }

        .console-line.info { color: #38bdf8; }
        .console-line.warning { color: #f59e0b; }
        .console-line.error { color: #ef4444; }

        /* Tables */
        .players-table-wrapper {
            margin-top: 2rem;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.9375rem;
            color: var(--text-color);
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .player-actions {
            display: flex;
            gap: 0.5rem;
        }

        .badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-cyan {
            background: rgba(0, 242, 254, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 242, 254, 0.2);
        }

        /* Modal styling */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .modal-content {
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2rem;
            width: 90%;
            max-width: 500px;
            box-shadow: var(--glass-shadow);
        }

        .modal-header {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .modal-buttons {
            display: flex;
            justify-content: flex-end;
            gap: 0.5rem;
            margin-top: 1.5rem;
        }

        .btn-cancel {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
        }

        .btn-cancel:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-color);
        }

        /* ── Detail Modal ── */
        .modal-wide .modal-content {
            max-width: 860px;
            width: 95%;
        }
        .detail-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.25rem;
        }
        .detail-tab {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 0.5rem 1.25rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 600;
            transition: all 0.2s;
        }
        .detail-tab.active {
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            color: #fff;
            border-color: transparent;
        }
        .detail-section { display: none; }
        .detail-section.active { display: block; }
        .detail-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
        .detail-table th { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border-color); color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
        .detail-table td { padding: 0.6rem 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
        .detail-table tr:hover td { background: rgba(255,255,255,0.02); }
        .lvl-input { width: 64px; background: rgba(8,12,20,0.8); border: 1px solid var(--border-color); color: var(--text-color); padding: 0.3rem 0.5rem; border-radius: 6px; font-size: 0.875rem; text-align: center; }
        .btn-xs { padding: 0.3rem 0.7rem; font-size: 0.78rem; border-radius: 6px; }
        .btn-teal { background: linear-gradient(135deg,#00b09b,#96c93d); }
        .btn-sm-danger { background: var(--accent-red); }
        .empty-msg { color: var(--text-muted); text-align: center; padding: 1.5rem; font-style: italic; }

        /* Custom Searchable Dropdown */
        .searchable-dropdown {
            position: relative;
            width: 100%;
        }
        .dropdown-select-box {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(8, 12, 20, 0.6);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            user-select: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .dropdown-select-box:hover {
            border-color: rgba(0, 242, 254, 0.4);
        }
        .dropdown-select-box.active {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 8px rgba(0, 242, 254, 0.2);
        }
        .dropdown-select-box .arrow {
            border: solid var(--text-muted);
            border-width: 0 2px 2px 0;
            display: inline-block;
            padding: 3px;
            transform: rotate(45deg);
            transition: transform 0.2s;
        }
        .dropdown-select-box.active .arrow {
            transform: rotate(-135deg);
        }
        .dropdown-content-menu {
            display: none;
            position: absolute;
            top: calc(100% + 5px);
            left: 0;
            right: 0;
            background: #0f172a;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            z-index: 99999;
            flex-direction: column;
            overflow: hidden;
            max-height: 320px;
        }
        .dropdown-search-wrapper {
            padding: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(15, 23, 42, 0.95);
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .dropdown-search-input {
            width: 100%;
            background: rgba(8, 12, 20, 0.8);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            font-size: 0.875rem;
            outline: none;
            transition: border-color 0.2s;
        }
        .dropdown-search-input:focus {
            border-color: var(--accent-cyan);
        }
        .dropdown-list-container {
            overflow-y: auto;
            max-height: 250px;
            flex-grow: 1;
        }
        .dropdown-option-item {
            padding: 0.6rem 1rem;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.2s, color 0.2s;
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        }
        .dropdown-option-item:hover {
            background: rgba(0, 242, 254, 0.15);
            color: #fff;
        }
        .dropdown-option-item.selected {
            background: rgba(0, 242, 254, 0.25);
            color: #fff;
            font-weight: bold;
        }
        .dropdown-option-item .option-id {
            color: var(--text-muted);
            font-size: 0.75rem;
        }
        .dropdown-option-item:hover .option-id {
            color: var(--accent-cyan);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-section">
                <h1>Wonderland Online</h1>
                <p>Private Server Web Admin Control Center</p>
            </div>
            <div class="server-status">
                <span class="status-dot"></span>
                <span>SERVER RUNNING (PORT 6414)</span>
            </div>
        </header>

        <!-- Dashboard Grid -->
        <div class="grid">
            <!-- Server Status -->
            <div class="card">
                <div class="card-title">Server Metrics</div>
                <div class="card-value" id="uptime">0s</div>
                <div class="card-desc">Uptime since launch</div>
                <div class="card-desc" id="online-count" style="margin-top: 0.5rem; font-weight: 600; color: var(--accent-cyan);">Online: 0 Players</div>
            </div>

            <!-- Server Settings -->
            <div class="card">
                <div class="card-title">Multipliers Configuration</div>
                <div class="multiplier-inputs">
                    <div class="form-group">
                        <label>EXP Multiplier</label>
                        <div class="form-row">
                            <input type="number" id="exp-rate" step="0.5" min="1" value="1.0">
                            <button onclick="updateConfig()">Apply</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Gold Multiplier</label>
                        <div class="form-row">
                            <input type="number" id="gold-rate" step="0.5" min="1" value="1.0">
                            <button onclick="updateConfig()">Apply</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Global Broadcast -->
            <div class="card">
                <div class="card-title">Global System Broadcast</div>
                <div class="form-group" style="height: 100%; justify-content: space-between;">
                    <label>Send message to all online players</label>
                    <div class="form-row">
                        <input type="text" id="broadcast-msg" placeholder="Type announcement...">
                        <button onclick="sendBroadcast()">Broadcast</button>
                    </div>
                    <div class="card-desc" style="margin-top: 1rem;">Displays instantly in system chat box.</div>
                </div>
            </div>
        </div>

        <!-- Second Row: Logs -->
        <div class="grid" style="grid-template-columns: 1fr;">
            <div class="card logs-panel">
                <div class="card-title">Live Server Logs</div>
                <div class="console" id="console"></div>
            </div>
        </div>

        <!-- Third Row: Active Players -->
        <div class="card">
            <div class="card-title">Active Connected Players</div>
            <div class="players-table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Char Name</th>
                            <th>Level</th>
                            <th>Gold</th>
                            <th>Map ID</th>
                            <th>Coordinates (X,Y)</th>
                            <th>Client IP</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="players-list">
                        <!-- Filled dynamically -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Fourth Row: Registered Accounts -->
        <div class="card" style="margin-top: 2rem;">
            <div class="card-title">Registered Accounts / Kayıtlı Hesaplar</div>
            <div class="players-table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>User ID</th>
                            <th>Username / Kullanıcı Adı</th>
                            <th>Actions / İşlemler</th>
                        </tr>
                    </thead>
                    <tbody id="users-list">
                        <!-- Filled dynamically -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Fifth Row: Database Browser -->
        <div class="card" style="margin-top: 2rem;">
            <div class="card-title" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <span>Database Browser / Veri Tabanı Yöneticisi</span>
                <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                    <select id="db-table-select" onchange="changeTable()" style="background: rgba(8, 12, 20, 0.6); border: 1px solid var(--border-color); color: var(--text-color); padding: 0.4rem 1rem; border-radius: 8px; font-weight: 600; outline: none;"></select>
                    <input type="text" id="db-search-input" placeholder="Search table..." oninput="searchTable()" style="background: rgba(8, 12, 20, 0.6); border: 1px solid var(--border-color); color: var(--text-color); padding: 0.4rem 1rem; border-radius: 8px; outline: none; width: 200px;">
                    <button onclick="openAddRowModal()" class="btn-success" style="padding: 0.4rem 1rem; font-weight: 600; font-size: 0.875rem;">+ Add Row</button>
                </div>
            </div>
            <div class="players-table-wrapper" style="max-height: 500px; overflow-y: auto;">
                <table>
                    <thead id="db-table-header">
                        <!-- Filled dynamically -->
                    </thead>
                    <tbody id="db-table-body">
                        <!-- Filled dynamically -->
                    </tbody>
                </table>
            </div>
            <div id="db-pagination" style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; flex-wrap: wrap; gap: 1rem;">
                <span id="db-pagination-info" style="font-size: 0.875rem; color: var(--text-muted);">Showing 0 to 0 of 0 entries</span>
                <div style="display: flex; gap: 0.5rem;">
                    <button id="db-prev-btn" onclick="prevPage()" class="btn-secondary" style="padding: 0.4rem 1rem;">Previous</button>
                    <button id="db-next-btn" onclick="nextPage()" class="btn-secondary" style="padding: 0.4rem 1rem;">Next</button>
                </div>
            </div>
        </div>
    </div>

    <!-- ── Database Edit/Add Row Modal ── -->
    <div class="modal" id="db-edit-modal">
        <div class="modal-content" style="max-width: 600px; max-height: 85vh; display: flex; flex-direction: column;">
            <div class="modal-header" id="db-edit-modal-title">Edit Database Row</div>
            <div id="db-edit-form" style="display: flex; flex-direction: column; gap: 1rem; overflow-y: auto; padding-right: 0.5rem; flex-grow: 1; max-height: 60vh;">
                <!-- Form fields populated dynamically -->
            </div>
            <div class="modal-buttons" style="flex-shrink: 0; margin-top: 1rem;">
                <button class="btn-cancel" onclick="closeDbEditModal()">Cancel</button>
                <button onclick="saveDbRow()" class="btn-success">Save</button>
            </div>
        </div>
    </div>

    <!-- ── Player Detail Modal ── -->
    <div class="modal modal-wide" id="detail-modal">
        <div class="modal-content" style="max-width:860px;">
            <div class="modal-header" id="detail-modal-title">Player Details</div>
            <div class="detail-tabs">
                <button class="detail-tab active" onclick="switchDetailTab('items')">🎒 Items</button>
                <button class="detail-tab" onclick="switchDetailTab('pets')">🐾 Pets</button>
            </div>
            <!-- Items tab -->
            <div class="detail-section active" id="detail-items-section">
                <div style="max-height:420px;overflow-y:auto;">
                    <table class="detail-table">
                        <thead><tr><th>#</th><th>Item ID</th><th>Amount</th><th>Action</th></tr></thead>
                        <tbody id="detail-items-body"></tbody>
                    </table>
                </div>
            </div>
            <!-- Pets tab -->
            <div class="detail-section" id="detail-pets-section">
                <div style="max-height:420px;overflow-y:auto;">
                    <table class="detail-table">
                        <thead><tr><th>#</th><th>Pet ID</th><th>Level</th><th>EXP</th><th>Amity</th><th>STR/CON/AGI/INT/WIS</th><th>Actions</th></tr></thead>
                        <tbody id="detail-pets-body"></tbody>
                    </table>
                </div>
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeDetailModal()">Close</button>
            </div>
        </div>
    </div>

    <!-- Teleport Modal -->
    <div class="modal" id="warp-modal">
        <div class="modal-content">
            <div class="modal-header">Teleport Player</div>
            <input type="hidden" id="warp-player-name">
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Select Preset Map</label>
                <select id="warp-preset" onchange="onPresetMapChange()" style="background: rgba(8, 12, 20, 0.6); border: 1px solid var(--border-color); color: var(--text-color); padding: 0.75rem 1rem; border-radius: 8px; font-size: 1rem; outline: none; width: 100%;">
                                        <option value="">-- Harita Sec / Choose a Map --</option>
                    <optgroup label="Deniz / Sea (10xxx)">
                        <option value="10000,1000,1000">Sea Zone 0 [10000]</option>
                        <option value="10001,1000,1000">Sea Zone 1 [10001]</option>
                        <option value="10002,1000,1000">Sea Zone 2 [10002]</option>
                        <option value="10003,1000,1000">Sea Zone 3 [10003]</option>
                        <option value="10004,1000,1000">Sea Zone 4 [10004]</option>
                        <option value="10005,1000,1000">Sea Zone 5 [10005]</option>
                        <option value="10006,1000,1000">Sea Zone 6 [10006]</option>
                        <option value="10007,1000,1000">Sea Zone 7 [10007]</option>
                        <option value="10008,1000,1000">Sea Zone 8 [10008]</option>
                        <option value="10009,1000,1000">Sea Zone 9 [10009]</option>
                        <option value="10011,1000,1000">Open Sea 1 [10011]</option>
                        <option value="10012,1000,1000">Open Sea 2 [10012]</option>
                        <option value="10013,1000,1000">Open Sea 3 [10013]</option>
                        <option value="10014,1000,1000">Open Sea 4 [10014]</option>
                        <option value="10015,1000,1000">Open Sea 5 [10015]</option>
                        <option value="10016,1000,1000">Open Sea 6 [10016]</option>
                        <option value="10017,1042,1075">Starter Ship Cabin [10017]</option>
                        <option value="10018,1000,1000">Open Sea 8 [10018]</option>
                        <option value="10019,1000,1000">Open Sea 9 [10019]</option>
                        <option value="10020,1000,1000">Open Sea 10 [10020]</option>
                        <option value="10021,1000,1000">Open Sea 11 [10021]</option>
                        <option value="10022,1000,1000">Open Sea 12 [10022]</option>
                        <option value="10023,1000,1000">Open Sea 13 [10023]</option>
                        <option value="10024,1000,1000">Open Sea 14 [10024]</option>
                        <option value="10025,1000,1000">Open Sea 15 [10025]</option>
                        <option value="10026,1000,1000">Open Sea 16 [10026]</option>
                        <option value="10027,1000,1000">Open Sea 17 [10027]</option>
                        <option value="10028,1000,1000">Open Sea 18 [10028]</option>
                        <option value="10029,1000,1000">Open Sea 19 [10029]</option>
                        <option value="10030,1000,1000">Open Sea 20 [10030]</option>
                        <option value="10031,1000,1000">Open Sea 21 [10031]</option>
                        <option value="10032,1000,1000">Open Sea 22 [10032]</option>
                        <option value="10033,1000,1000">Open Sea 23 [10033]</option>
                        <option value="10034,1000,1000">Open Sea 24 [10034]</option>
                        <option value="10035,1000,1000">Open Sea 25 [10035]</option>
                        <option value="10036,1000,1000">Open Sea 26 [10036]</option>
                        <option value="10037,1000,1000">Open Sea 27 [10037]</option>
                        <option value="10038,1000,1000">Open Sea 28 [10038]</option>
                        <option value="10039,1000,1000">Open Sea 29 [10039]</option>
                        <option value="10040,1000,1000">Open Sea 30 [10040]</option>
                        <option value="10041,1000,1000">Open Sea 31 [10041]</option>
                        <option value="10042,1000,1000">Open Sea 32 [10042]</option>
                        <option value="10043,1000,1000">Open Sea 33 [10043]</option>
                        <option value="10044,1000,1000">Open Sea 34 [10044]</option>
                        <option value="10045,1000,1000">Open Sea 35 [10045]</option>
                        <option value="10046,1000,1000">Open Sea 36 [10046]</option>
                        <option value="10047,1000,1000">Open Sea 37 [10047]</option>
                        <option value="10048,1000,1000">Open Sea 38 [10048]</option>
                        <option value="10049,1000,1000">Open Sea 39 [10049]</option>
                        <option value="10050,1000,1000">Open Sea 40 [10050]</option>
                        <option value="10051,1000,1000">Open Sea 41 [10051]</option>
                        <option value="10052,1000,1000">Open Sea 42 [10052]</option>
                        <option value="10053,1000,1000">Open Sea 43 [10053]</option>
                        <option value="10054,1000,1000">Open Sea 44 [10054]</option>
                        <option value="10055,1000,1000">Open Sea 45 [10055]</option>
                        <option value="10056,1000,1000">Open Sea 46 [10056]</option>
                        <option value="10057,1000,1000">Open Sea 47 [10057]</option>
                        <option value="10058,1000,1000">Open Sea 48 [10058]</option>
                        <option value="10059,1000,1000">Open Sea 49 [10059]</option>
                        <option value="10060,1000,1000">Open Sea 50 [10060]</option>
                        <option value="10061,1000,1000">Open Sea 51 [10061]</option>
                        <option value="10062,1000,1000">Open Sea 52 [10062]</option>
                        <option value="10063,1000,1000">Open Sea 53 [10063]</option>
                        <option value="10064,1000,1000">Open Sea 54 [10064]</option>
                        <option value="10065,1000,1000">Open Sea 55 [10065]</option>
                        <option value="10066,1000,1000">Open Sea 56 [10066]</option>
                        <option value="10067,1000,1000">Open Sea 57 [10067]</option>
                        <option value="10068,1000,1000">Open Sea 58 [10068]</option>
                        <option value="10069,1000,1000">Open Sea 59 [10069]</option>
                        <option value="10070,1000,1000">Open Sea 60 [10070]</option>
                        <option value="10071,1000,1000">Open Sea 61 [10071]</option>
                        <option value="10072,1000,1000">Open Sea 62 [10072]</option>
                        <option value="10073,1000,1000">Open Sea 63 [10073]</option>
                        <option value="10074,1000,1000">Open Sea 64 [10074]</option>
                        <option value="10075,1000,1000">Open Sea 65 [10075]</option>
                        <option value="10076,1000,1000">Open Sea 66 [10076]</option>
                        <option value="10077,1000,1000">Open Sea 67 [10077]</option>
                        <option value="10078,1000,1000">Open Sea 68 [10078]</option>
                        <option value="10079,1000,1000">Open Sea 69 [10079]</option>
                        <option value="10080,1000,1000">Open Sea 70 [10080]</option>
                        <option value="10081,1000,1000">Open Sea 71 [10081]</option>
                        <option value="10082,1000,1000">Open Sea 72 [10082]</option>
                        <option value="10083,1000,1000">Open Sea 73 [10083]</option>
                        <option value="10084,1000,1000">Open Sea 74 [10084]</option>
                        <option value="10085,1000,1000">Open Sea 75 [10085]</option>
                        <option value="10086,1000,1000">Open Sea 76 [10086]</option>
                        <option value="10087,1000,1000">Open Sea 77 [10087]</option>
                        <option value="10088,1000,1000">Open Sea 78 [10088]</option>
                        <option value="10095,1000,1000">Open Sea 85 [10095]</option>
                        <option value="10096,1000,1000">Open Sea 86 [10096]</option>
                        <option value="10097,1000,1000">Open Sea 87 [10097]</option>
                        <option value="10098,1000,1000">Open Sea 88 [10098]</option>
                        <option value="10099,1000,1000">Open Sea 89 [10099]</option>
                        <option value="10100,1000,1000">Open Sea 90 [10100]</option>
                        <option value="10101,1000,1000">Open Sea 91 [10101]</option>
                        <option value="10102,1000,1000">Open Sea 92 [10102]</option>
                        <option value="10103,1000,1000">Open Sea 93 [10103]</option>
                    </optgroup>
                    <optgroup label="Kelan Adasi Disi / Kelan Island Outdoor (11xxx)">
                        <option value="11002,1000,1000">Kelan Shore 0 [11002]</option>
                        <option value="11003,1000,1000">Kelan Shore 1 [11003]</option>
                        <option value="11004,1000,1000">Kelan Shore 2 [11004]</option>
                        <option value="11005,1000,1000">Kelan Shore 3 [11005]</option>
                        <option value="11006,1000,1000">Kelan Shore 4 [11006]</option>
                        <option value="11007,1000,1000">Kelan Shore 5 [11007]</option>
                        <option value="11008,1000,1000">Kelan Shore 6 [11008]</option>
                        <option value="11009,1000,1000">Kelan Shore 7 [11009]</option>
                        <option value="11010,1000,1000">Kelan Shore 8 [11010]</option>
                        <option value="11011,1000,1000">Kelan Shore 9 [11011]</option>
                        <option value="11012,1000,1000">Kelan Shore 10 [11012]</option>
                        <option value="11013,1000,1000">Kelan Shore 11 [11013]</option>
                        <option value="11014,1000,1000">Kelan Shore 12 [11014]</option>
                        <option value="11015,1000,1000">Kelan Shore 13 [11015]</option>
                        <option value="11016,1142,295">Shipwreck Beach [11016]</option>
                        <option value="11017,1000,1000">Kelan Shore 15 [11017]</option>
                        <option value="11018,1000,1000">Kelan Shore 16 [11018]</option>
                        <option value="11019,1000,1000">Kelan Shore 17 [11019]</option>
                        <option value="11020,1000,1000">Kelan Island Forest 0 [11020]</option>
                        <option value="11021,1000,1000">Kelan Island Forest 1 [11021]</option>
                        <option value="11022,1000,1000">Kelan Island Forest 2 [11022]</option>
                        <option value="11023,1000,1000">Kelan Island Forest 3 [11023]</option>
                        <option value="11024,1000,1000">Kelan Island Forest 4 [11024]</option>
                        <option value="11026,1000,1000">Kelan Island Forest 6 [11026]</option>
                        <option value="11027,1000,1000">Kelan Island Forest 7 [11027]</option>
                        <option value="11028,1000,1000">Kelan Island Forest 8 [11028]</option>
                        <option value="11029,1000,1000">Kelan Island Forest 9 [11029]</option>
                        <option value="11030,1000,1000">Kelan Island Forest 10 [11030]</option>
                        <option value="11031,1000,1000">Kelan Island Forest 11 [11031]</option>
                        <option value="11032,1000,1000">Kelan Island Forest 12 [11032]</option>
                        <option value="11033,1000,1000">Kelan Island Forest 13 [11033]</option>
                        <option value="11034,1000,1000">Kelan Island Forest 14 [11034]</option>
                        <option value="11035,1000,1000">Kelan Island Forest 15 [11035]</option>
                        <option value="11036,1000,1000">Kelan Island Forest 16 [11036]</option>
                        <option value="11037,1000,1000">Kelan Island Forest 17 [11037]</option>
                        <option value="11038,1000,1000">Kelan Island Forest 18 [11038]</option>
                        <option value="11039,1000,1000">Kelan Island Forest 19 [11039]</option>
                        <option value="11040,1000,1000">Kelan Island Forest 20 [11040]</option>
                        <option value="11041,1000,1000">Kelan Island Forest 21 [11041]</option>
                        <option value="11042,1000,1000">Kelan Island Forest 22 [11042]</option>
                        <option value="11043,1000,1000">Kelan Island Forest 23 [11043]</option>
                        <option value="11044,1000,1000">Kelan Island Forest 24 [11044]</option>
                        <option value="11045,1000,1000">Kelan Island Forest 25 [11045]</option>
                        <option value="11046,1000,1000">Kelan Island Forest 26 [11046]</option>
                        <option value="11047,1000,1000">Kelan Island Forest 27 [11047]</option>
                        <option value="11048,1000,1000">Kelan Island Forest 28 [11048]</option>
                        <option value="11049,1000,1000">Kelan Island Forest 29 [11049]</option>
                        <option value="11050,1000,1000">Kelan Island Forest 30 [11050]</option>
                        <option value="11051,1000,1000">Kelan Island Forest 31 [11051]</option>
                        <option value="11052,1000,1000">Kelan Island Forest 32 [11052]</option>
                        <option value="11053,1000,1000">Kelan Island Forest 33 [11053]</option>
                        <option value="11054,1000,1000">Kelan Island Forest 34 [11054]</option>
                        <option value="11055,1000,1000">Kelan Island Forest 35 [11055]</option>
                        <option value="11056,1000,1000">Kelan Island Forest 36 [11056]</option>
                        <option value="11057,1000,1000">Kelan Island Forest 37 [11057]</option>
                        <option value="11058,1000,1000">Kelan Island Forest 38 [11058]</option>
                        <option value="11059,1000,1000">Kelan Island Forest 39 [11059]</option>
                        <option value="11060,1000,1000">Kelan Island Cave 0 [11060]</option>
                        <option value="11061,1000,1000">Kelan Island Cave 1 [11061]</option>
                        <option value="11062,1000,1000">Kelan Island Cave 2 [11062]</option>
                        <option value="11063,1000,1000">Kelan Island Cave 3 [11063]</option>
                        <option value="11064,1000,1000">Kelan Island Cave 4 [11064]</option>
                        <option value="11065,1000,1000">Kelan Island Cave 5 [11065]</option>
                        <option value="11066,1000,1000">Kelan Island Cave 6 [11066]</option>
                        <option value="11067,1000,1000">Kelan Island Cave 7 [11067]</option>
                        <option value="11068,1000,1000">Kelan Island Cave 8 [11068]</option>
                        <option value="11069,1000,1000">Kelan Island Cave 9 [11069]</option>
                        <option value="11070,1000,1000">Kelan Island Cave 10 [11070]</option>
                        <option value="11071,1000,1000">Kelan Island Cave 11 [11071]</option>
                        <option value="11072,1000,1000">Kelan Island Cave 12 [11072]</option>
                        <option value="11073,1000,1000">Kelan Island Cave 13 [11073]</option>
                        <option value="11074,1000,1000">Kelan Island Cave 14 [11074]</option>
                        <option value="11075,1000,1000">Kelan Island Cave 15 [11075]</option>
                        <option value="11076,1000,1000">Kelan Island Cave 16 [11076]</option>
                        <option value="11077,1000,1000">Kelan Island Cave 17 [11077]</option>
                        <option value="11078,1000,1000">Kelan Island Cave 18 [11078]</option>
                        <option value="11079,1000,1000">Kelan Island Cave 19 [11079]</option>
                        <option value="11080,1000,1000">Kelan Island Cave 20 [11080]</option>
                        <option value="11081,1000,1000">Kelan Island Cave 21 [11081]</option>
                        <option value="11082,1000,1000">Kelan Island Cave 22 [11082]</option>
                        <option value="11083,1000,1000">Kelan Island Cave 23 [11083]</option>
                        <option value="11084,1000,1000">Kelan Island Cave 24 [11084]</option>
                        <option value="11085,1000,1000">Kelan Island Cave 25 [11085]</option>
                        <option value="11086,1000,1000">Kelan Island Cave 26 [11086]</option>
                        <option value="11087,1000,1000">Kelan Island Cave 27 [11087]</option>
                        <option value="11088,1000,1000">Kelan Island Cave 28 [11088]</option>
                        <option value="11089,1000,1000">Kelan Island Cave 29 [11089]</option>
                        <option value="11090,1000,1000">Kelan Island Cave 30 [11090]</option>
                        <option value="11091,1000,1000">Kelan Island Cave 31 [11091]</option>
                        <option value="11092,1000,1000">Kelan Island Cave 32 [11092]</option>
                        <option value="11093,1000,1000">Kelan Island Cave 33 [11093]</option>
                        <option value="11094,1000,1000">Kelan Island Cave 34 [11094]</option>
                        <option value="11095,1000,1000">Kelan Island Cave 35 [11095]</option>
                        <option value="11096,1000,1000">Kelan Island Cave 36 [11096]</option>
                        <option value="11097,1000,1000">Kelan Island Cave 37 [11097]</option>
                        <option value="11098,1000,1000">Kelan Island Cave 38 [11098]</option>
                        <option value="11099,1000,1000">Kelan Island Cave 39 [11099]</option>
                        <option value="11100,1000,1000">Kelan Island Mountain 0 [11100]</option>
                        <option value="11101,1000,1000">Kelan Island Mountain 1 [11101]</option>
                        <option value="11102,1000,1000">Kelan Island Mountain 2 [11102]</option>
                        <option value="11103,1000,1000">Kelan Island Mountain 3 [11103]</option>
                        <option value="11104,1000,1000">Kelan Island Mountain 4 [11104]</option>
                        <option value="11105,1000,1000">Kelan Island Mountain 5 [11105]</option>
                        <option value="11106,1000,1000">Kelan Island Mountain 6 [11106]</option>
                        <option value="11107,1000,1000">Kelan Island Mountain 7 [11107]</option>
                        <option value="11108,1000,1000">Kelan Island Mountain 8 [11108]</option>
                        <option value="11109,1000,1000">Kelan Island Mountain 9 [11109]</option>
                        <option value="11110,1000,1000">Kelan Island Mountain 10 [11110]</option>
                        <option value="11111,1000,1000">Kelan Island Mountain 11 [11111]</option>
                        <option value="11112,1000,1000">Kelan Island Mountain 12 [11112]</option>
                        <option value="11113,1000,1000">Kelan Island Mountain 13 [11113]</option>
                        <option value="11114,1000,1000">Kelan Island Mountain 14 [11114]</option>
                        <option value="11115,1000,1000">Kelan Island Mountain 15 [11115]</option>
                        <option value="11116,1000,1000">Kelan Island Mountain 16 [11116]</option>
                        <option value="11117,1000,1000">Kelan Island Mountain 17 [11117]</option>
                        <option value="11118,1000,1000">Kelan Island Mountain 18 [11118]</option>
                        <option value="11119,1000,1000">Kelan Island Mountain 19 [11119]</option>
                        <option value="11120,1000,1000">Kelan Island Mountain 20 [11120]</option>
                        <option value="11121,1000,1000">Kelan Island Mountain 21 [11121]</option>
                        <option value="11122,1000,1000">Kelan Island Mountain 22 [11122]</option>
                        <option value="11123,1000,1000">Kelan Island Mountain 23 [11123]</option>
                        <option value="11124,1000,1000">Kelan Island Mountain 24 [11124]</option>
                        <option value="11125,1000,1000">Kelan Island Mountain 25 [11125]</option>
                        <option value="11126,1000,1000">Kelan Island Mountain 26 [11126]</option>
                        <option value="11127,1000,1000">Kelan Island Mountain 27 [11127]</option>
                        <option value="11128,1000,1000">Kelan Island Mountain 28 [11128]</option>
                        <option value="11129,1000,1000">Kelan Island Mountain 29 [11129]</option>
                        <option value="11130,1000,1000">Kelan Island Mountain 30 [11130]</option>
                        <option value="11131,1000,1000">Kelan Island Mountain 31 [11131]</option>
                        <option value="11132,1000,1000">Kelan Island Mountain 32 [11132]</option>
                        <option value="11133,1000,1000">Kelan Island Mountain 33 [11133]</option>
                        <option value="11134,1000,1000">Kelan Island Mountain 34 [11134]</option>
                        <option value="11135,1000,1000">Kelan Island Mountain 35 [11135]</option>
                        <option value="11136,1000,1000">Kelan Island Mountain 36 [11136]</option>
                        <option value="11137,1000,1000">Kelan Island Mountain 37 [11137]</option>
                        <option value="11138,1000,1000">Kelan Island Mountain 38 [11138]</option>
                        <option value="11139,1000,1000">Kelan Island Mountain 39 [11139]</option>
                        <option value="11140,1000,1000">Kelan Island Mountain 40 [11140]</option>
                        <option value="11141,1000,1000">Kelan Island Mountain 41 [11141]</option>
                        <option value="11142,1000,1000">Kelan Island Mountain 42 [11142]</option>
                        <option value="11143,1000,1000">Kelan Island Mountain 43 [11143]</option>
                        <option value="11144,1000,1000">Kelan Island Mountain 44 [11144]</option>
                        <option value="11145,1000,1000">Kelan Island Mountain 45 [11145]</option>
                        <option value="11146,1000,1000">Kelan Island Mountain 46 [11146]</option>
                        <option value="11147,1000,1000">Kelan Island Mountain 47 [11147]</option>
                        <option value="11148,1000,1000">Kelan Island Mountain 48 [11148]</option>
                        <option value="11149,1000,1000">Kelan Island Mountain 49 [11149]</option>
                        <option value="11150,1000,1000">Kelan Island Dungeon 0 [11150]</option>
                        <option value="11151,1000,1000">Kelan Island Dungeon 1 [11151]</option>
                        <option value="11152,1000,1000">Kelan Island Dungeon 2 [11152]</option>
                        <option value="11153,1000,1000">Kelan Island Dungeon 3 [11153]</option>
                        <option value="11154,1000,1000">Kelan Island Dungeon 4 [11154]</option>
                        <option value="11155,1000,1000">Kelan Island Dungeon 5 [11155]</option>
                        <option value="11156,1000,1000">Kelan Island Dungeon 6 [11156]</option>
                        <option value="11157,1000,1000">Kelan Island Dungeon 7 [11157]</option>
                        <option value="11158,1000,1000">Kelan Island Dungeon 8 [11158]</option>
                        <option value="11159,1000,1000">Kelan Island Dungeon 9 [11159]</option>
                        <option value="11160,1000,1000">Kelan Island Dungeon 10 [11160]</option>
                        <option value="11161,1000,1000">Kelan Island Dungeon 11 [11161]</option>
                        <option value="11162,1000,1000">Kelan Island Dungeon 12 [11162]</option>
                        <option value="11163,1000,1000">Kelan Island Dungeon 13 [11163]</option>
                        <option value="11164,1000,1000">Kelan Island Dungeon 14 [11164]</option>
                        <option value="11165,1000,1000">Kelan Island Dungeon 15 [11165]</option>
                        <option value="11166,1000,1000">Kelan Island Dungeon 16 [11166]</option>
                        <option value="11167,1000,1000">Kelan Island Dungeon 17 [11167]</option>
                        <option value="11168,1000,1000">Kelan Island Dungeon 18 [11168]</option>
                        <option value="11169,1000,1000">Kelan Island Dungeon 19 [11169]</option>
                        <option value="11170,1000,1000">Kelan Island Dungeon 20 [11170]</option>
                        <option value="11171,1000,1000">Kelan Island Dungeon 21 [11171]</option>
                        <option value="11172,1000,1000">Kelan Island Dungeon 22 [11172]</option>
                        <option value="11173,1000,1000">Kelan Island Dungeon 23 [11173]</option>
                        <option value="11174,1000,1000">Kelan Island Dungeon 24 [11174]</option>
                        <option value="11175,1000,1000">Kelan Island Dungeon 25 [11175]</option>
                        <option value="11176,1000,1000">Kelan Island Dungeon 26 [11176]</option>
                        <option value="11177,1000,1000">Kelan Island Dungeon 27 [11177]</option>
                        <option value="11178,1000,1000">Kelan Island Dungeon 28 [11178]</option>
                        <option value="11179,1000,1000">Kelan Island Dungeon 29 [11179]</option>
                        <option value="11180,1000,1000">Kelan Island Dungeon 30 [11180]</option>
                        <option value="11181,1000,1000">Kelan Island Dungeon 31 [11181]</option>
                        <option value="11182,1000,1000">Kelan Island Dungeon 32 [11182]</option>
                        <option value="11183,1000,1000">Kelan Island Dungeon 33 [11183]</option>
                        <option value="11184,1000,1000">Kelan Island Dungeon 34 [11184]</option>
                        <option value="11185,1000,1000">Kelan Island Dungeon 35 [11185]</option>
                        <option value="11186,1000,1000">Kelan Island Dungeon 36 [11186]</option>
                        <option value="11187,1000,1000">Kelan Island Dungeon 37 [11187]</option>
                        <option value="11188,1000,1000">Kelan Island Dungeon 38 [11188]</option>
                        <option value="11189,1000,1000">Kelan Island Dungeon 39 [11189]</option>
                        <option value="11190,1000,1000">Kelan Island Dungeon 40 [11190]</option>
                        <option value="11191,1000,1000">Kelan Island Dungeon 41 [11191]</option>
                        <option value="11192,1000,1000">Kelan Island Dungeon 42 [11192]</option>
                        <option value="11193,1000,1000">Kelan Island Dungeon 43 [11193]</option>
                        <option value="11194,1000,1000">Kelan Island Dungeon 44 [11194]</option>
                        <option value="11195,1000,1000">Kelan Island Dungeon 45 [11195]</option>
                        <option value="11196,1000,1000">Kelan Island Dungeon 46 [11196]</option>
                        <option value="11197,1000,1000">Kelan Island Dungeon 47 [11197]</option>
                        <option value="11198,1000,1000">Kelan Island Dungeon 48 [11198]</option>
                        <option value="11199,1000,1000">Kelan Island Dungeon 49 [11199]</option>
                        <option value="11200,1000,1000">Kelan Island Dungeon 50 [11200]</option>
                        <option value="11201,1000,1000">Kelan Island Dungeon 51 [11201]</option>
                        <option value="11202,1000,1000">Kelan Island Dungeon 52 [11202]</option>
                        <option value="11203,1000,1000">Kelan Island Dungeon 53 [11203]</option>
                        <option value="11204,1000,1000">Kelan Island Dungeon 54 [11204]</option>
                        <option value="11205,1000,1000">Kelan Island Dungeon 55 [11205]</option>
                        <option value="11206,1000,1000">Kelan Island Dungeon 56 [11206]</option>
                        <option value="11207,1000,1000">Kelan Island Dungeon 57 [11207]</option>
                    </optgroup>
                    <optgroup label="Kelan Bolgesi / Kelan Region (12xxx)">
                        <option value="12000,1082,735">Kelan Village [12000]</option>
                        <option value="12001,230,360">Kelan Chief's House [12001]</option>
                        <option value="12002,400,280">Kelan Clinic [12002]</option>
                        <option value="12003,260,370">Kelan Casino [12003]</option>
                        <option value="12004,360,340">Kelan Props Shop [12004]</option>
                        <option value="12005,480,260">Kelan Temple [12005]</option>
                        <option value="12006,300,300">Kelan Weapon Shop [12006]</option>
                        <option value="12007,300,300">Kelan Tavern [12007]</option>
                        <option value="12008,300,300">Kelan Pet Shop [12008]</option>
                        <option value="12009,300,300">Kelan Bank [12009]</option>
                        <option value="12050,1000,1000">Kelan Cave 0 [12050]</option>
                        <option value="12051,1000,1000">Kelan Cave 1 [12051]</option>
                        <option value="12052,1000,1000">Kelan Cave 2 [12052]</option>
                        <option value="12053,1000,1000">Kelan Cave 3 [12053]</option>
                        <option value="12054,1000,1000">Kelan Cave 4 [12054]</option>
                        <option value="12055,1000,1000">Kelan Cave 5 [12055]</option>
                        <option value="12056,1000,1000">Kelan Cave 6 [12056]</option>
                        <option value="12057,1000,1000">Kelan Cave 7 [12057]</option>
                        <option value="12058,1000,1000">Kelan Cave 8 [12058]</option>
                        <option value="12059,1000,1000">Kelan Cave 9 [12059]</option>
                        <option value="12060,1000,1000">Kelan Cave 10 [12060]</option>
                        <option value="12061,1000,1000">Kelan Cave 11 [12061]</option>
                        <option value="12062,1000,1000">Kelan Cave 12 [12062]</option>
                        <option value="12063,1000,1000">Kelan Cave 13 [12063]</option>
                        <option value="12064,1000,1000">Kelan Cave 14 [12064]</option>
                        <option value="12065,1000,1000">Kelan Cave 15 [12065]</option>
                        <option value="12066,1000,1000">Kelan Cave 16 [12066]</option>
                        <option value="12067,1000,1000">Kelan Cave 17 [12067]</option>
                        <option value="12100,1000,1000">Kelan Forest 0 [12100]</option>
                        <option value="12101,1000,1000">Kelan Forest 1 [12101]</option>
                        <option value="12102,1000,1000">Kelan Forest 2 [12102]</option>
                        <option value="12103,1000,1000">Kelan Forest 3 [12103]</option>
                        <option value="12104,1000,1000">Kelan Forest 4 [12104]</option>
                        <option value="12105,1000,1000">Kelan Forest 5 [12105]</option>
                        <option value="12106,1000,1000">Kelan Forest 6 [12106]</option>
                        <option value="12107,1000,1000">Kelan Forest 7 [12107]</option>
                        <option value="12108,1000,1000">Kelan Forest 8 [12108]</option>
                        <option value="12109,1000,1000">Kelan Forest 9 [12109]</option>
                        <option value="12110,1000,1000">Kelan Forest 10 [12110]</option>
                        <option value="12111,1000,1000">Kelan Forest 11 [12111]</option>
                        <option value="12112,1000,1000">Kelan Forest 12 [12112]</option>
                        <option value="12113,1000,1000">Kelan Forest 13 [12113]</option>
                        <option value="12114,1000,1000">Kelan Forest 14 [12114]</option>
                        <option value="12115,1000,1000">Kelan Forest 15 [12115]</option>
                        <option value="12116,1000,1000">Kelan Forest 16 [12116]</option>
                        <option value="12117,1000,1000">Kelan Forest 17 [12117]</option>
                        <option value="12118,1000,1000">Kelan Forest 18 [12118]</option>
                        <option value="12119,1000,1000">Kelan Forest 19 [12119]</option>
                        <option value="12120,1000,1000">Kelan Forest 20 [12120]</option>
                        <option value="12121,1000,1000">Kelan Forest 21 [12121]</option>
                        <option value="12122,1000,1000">Kelan Forest 22 [12122]</option>
                        <option value="12123,1000,1000">Kelan Forest 23 [12123]</option>
                        <option value="12124,1000,1000">Kelan Forest 24 [12124]</option>
                        <option value="12125,1000,1000">Kelan Forest 25 [12125]</option>
                        <option value="12126,1000,1000">Kelan Forest 26 [12126]</option>
                        <option value="12127,1000,1000">Kelan Forest 27 [12127]</option>
                        <option value="12128,1000,1000">Kelan Forest 28 [12128]</option>
                        <option value="12129,1000,1000">Kelan Forest 29 [12129]</option>
                        <option value="12130,1000,1000">Kelan Forest 30 [12130]</option>
                        <option value="12131,1000,1000">Kelan Forest 31 [12131]</option>
                        <option value="12132,1000,1000">Kelan Forest 32 [12132]</option>
                        <option value="12133,1000,1000">Kelan Forest 33 [12133]</option>
                        <option value="12134,1000,1000">Kelan Forest 34 [12134]</option>
                        <option value="12135,1000,1000">Kelan Forest 35 [12135]</option>
                        <option value="12136,1000,1000">Kelan Forest 36 [12136]</option>
                        <option value="12137,1000,1000">Kelan Forest 37 [12137]</option>
                        <option value="12138,1000,1000">Kelan Forest 38 [12138]</option>
                        <option value="12139,1000,1000">Kelan Forest 39 [12139]</option>
                        <option value="12140,1000,1000">Kelan Forest 40 [12140]</option>
                        <option value="12141,1000,1000">Kelan Forest 41 [12141]</option>
                        <option value="12142,1000,1000">Kelan Forest 42 [12142]</option>
                        <option value="12143,1000,1000">Kelan Forest 43 [12143]</option>
                        <option value="12144,1000,1000">Kelan Forest 44 [12144]</option>
                        <option value="12145,1000,1000">Kelan Forest 45 [12145]</option>
                        <option value="12146,1000,1000">Kelan Forest 46 [12146]</option>
                        <option value="12147,1000,1000">Kelan Forest 47 [12147]</option>
                        <option value="12148,1000,1000">Kelan Forest 48 [12148]</option>
                        <option value="12149,1000,1000">Kelan Forest 49 [12149]</option>
                        <option value="12150,1000,1000">Kelan Forest 50 [12150]</option>
                        <option value="12151,1000,1000">Kelan Forest 51 [12151]</option>
                        <option value="12152,1000,1000">Kelan Forest 52 [12152]</option>
                        <option value="12153,1000,1000">Kelan Forest 53 [12153]</option>
                        <option value="12154,1000,1000">Kelan Forest 54 [12154]</option>
                        <option value="12155,1000,1000">Kelan Forest 55 [12155]</option>
                        <option value="12156,1000,1000">Kelan Forest 56 [12156]</option>
                        <option value="12157,1000,1000">Kelan Forest 57 [12157]</option>
                        <option value="12158,1000,1000">Kelan Forest 58 [12158]</option>
                        <option value="12159,1000,1000">Kelan Forest 59 [12159]</option>
                        <option value="12160,1000,1000">Kelan Forest 60 [12160]</option>
                        <option value="12161,1000,1000">Kelan Forest 61 [12161]</option>
                        <option value="12162,1000,1000">Kelan Forest 62 [12162]</option>
                        <option value="12163,1000,1000">Kelan Forest 63 [12163]</option>
                        <option value="12164,1000,1000">Kelan Forest 64 [12164]</option>
                        <option value="12165,1000,1000">Kelan Forest 65 [12165]</option>
                        <option value="12166,1000,1000">Kelan Forest 66 [12166]</option>
                        <option value="12167,1000,1000">Kelan Forest 67 [12167]</option>
                        <option value="12168,1000,1000">Kelan Forest 68 [12168]</option>
                        <option value="12169,1000,1000">Kelan Forest 69 [12169]</option>
                        <option value="12170,1000,1000">Kelan Forest 70 [12170]</option>
                        <option value="12171,1000,1000">Kelan Forest 71 [12171]</option>
                        <option value="12172,1000,1000">Kelan Forest 72 [12172]</option>
                        <option value="12173,1000,1000">Kelan Forest 73 [12173]</option>
                        <option value="12174,1000,1000">Kelan Forest 74 [12174]</option>
                        <option value="12175,1000,1000">Kelan Forest 75 [12175]</option>
                        <option value="12176,1000,1000">Kelan Forest 76 [12176]</option>
                        <option value="12177,1000,1000">Kelan Forest 77 [12177]</option>
                        <option value="12178,1000,1000">Kelan Forest 78 [12178]</option>
                        <option value="12200,1000,1000">Kelan Mountain 0 [12200]</option>
                        <option value="12201,1000,1000">Kelan Mountain 1 [12201]</option>
                        <option value="12202,1000,1000">Kelan Mountain 2 [12202]</option>
                        <option value="12203,1000,1000">Kelan Mountain 3 [12203]</option>
                        <option value="12204,1000,1000">Kelan Mountain 4 [12204]</option>
                        <option value="12205,1000,1000">Kelan Mountain 5 [12205]</option>
                        <option value="12206,1000,1000">Kelan Mountain 6 [12206]</option>
                        <option value="12207,1000,1000">Kelan Mountain 7 [12207]</option>
                        <option value="12208,1000,1000">Kelan Mountain 8 [12208]</option>
                        <option value="12209,1000,1000">Kelan Mountain 9 [12209]</option>
                        <option value="12210,1000,1000">Kelan Mountain 10 [12210]</option>
                        <option value="12211,1000,1000">Kelan Mountain 11 [12211]</option>
                        <option value="12212,1000,1000">Kelan Mountain 12 [12212]</option>
                        <option value="12250,1000,1000">Kelan Mine 0 [12250]</option>
                        <option value="12251,1000,1000">Kelan Mine 1 [12251]</option>
                        <option value="12252,1000,1000">Kelan Mine 2 [12252]</option>
                        <option value="12253,1000,1000">Kelan Mine 3 [12253]</option>
                        <option value="12254,1000,1000">Kelan Mine 4 [12254]</option>
                        <option value="12255,1000,1000">Kelan Mine 5 [12255]</option>
                        <option value="12256,1000,1000">Kelan Mine 6 [12256]</option>
                        <option value="12257,1000,1000">Kelan Mine 7 [12257]</option>
                        <option value="12258,1000,1000">Kelan Mine 8 [12258]</option>
                        <option value="12259,1000,1000">Kelan Mine 9 [12259]</option>
                        <option value="12260,1000,1000">Kelan Mine 10 [12260]</option>
                        <option value="12261,1000,1000">Kelan Mine 11 [12261]</option>
                        <option value="12262,1000,1000">Kelan Mine 12 [12262]</option>
                        <option value="12263,1000,1000">Kelan Mine 13 [12263]</option>
                        <option value="12264,1000,1000">Kelan Mine 14 [12264]</option>
                        <option value="12265,1000,1000">Kelan Mine 15 [12265]</option>
                        <option value="12266,1000,1000">Kelan Mine 16 [12266]</option>
                        <option value="12267,1000,1000">Kelan Mine 17 [12267]</option>
                        <option value="12268,1000,1000">Kelan Mine 18 [12268]</option>
                        <option value="12269,1000,1000">Kelan Mine 19 [12269]</option>
                        <option value="12270,1000,1000">Kelan Mine 20 [12270]</option>
                        <option value="12271,1000,1000">Kelan Mine 21 [12271]</option>
                        <option value="12272,1000,1000">Kelan Mine 22 [12272]</option>
                        <option value="12273,1000,1000">Kelan Mine 23 [12273]</option>
                        <option value="12274,1000,1000">Kelan Mine 24 [12274]</option>
                        <option value="12275,1000,1000">Kelan Mine 25 [12275]</option>
                        <option value="12276,1000,1000">Kelan Mine 26 [12276]</option>
                        <option value="12277,1000,1000">Kelan Mine 27 [12277]</option>
                        <option value="12278,1000,1000">Kelan Mine 28 [12278]</option>
                        <option value="12279,1000,1000">Kelan Mine 29 [12279]</option>
                        <option value="12280,1000,1000">Kelan Mine 30 [12280]</option>
                        <option value="12281,1000,1000">Kelan Mine 31 [12281]</option>
                        <option value="12282,1000,1000">Kelan Mine 32 [12282]</option>
                        <option value="12283,1000,1000">Kelan Mine 33 [12283]</option>
                        <option value="12284,1000,1000">Kelan Mine 34 [12284]</option>
                        <option value="12285,1000,1000">Kelan Mine 35 [12285]</option>
                        <option value="12286,1000,1000">Kelan Mine 36 [12286]</option>
                        <option value="12287,1000,1000">Kelan Mine 37 [12287]</option>
                        <option value="12288,1000,1000">Kelan Mine 38 [12288]</option>
                        <option value="12289,1000,1000">Kelan Mine 39 [12289]</option>
                        <option value="12290,1000,1000">Kelan Mine 40 [12290]</option>
                        <option value="12291,1000,1000">Kelan Mine 41 [12291]</option>
                        <option value="12292,1000,1000">Kelan Mine 42 [12292]</option>
                        <option value="12293,1000,1000">Kelan Mine 43 [12293]</option>
                        <option value="12294,1000,1000">Kelan Mine 44 [12294]</option>
                        <option value="12295,1000,1000">Kelan Mine 45 [12295]</option>
                        <option value="12296,1000,1000">Kelan Mine 46 [12296]</option>
                        <option value="12297,1000,1000">Kelan Mine 47 [12297]</option>
                        <option value="12298,1000,1000">Kelan Mine 48 [12298]</option>
                        <option value="12299,1000,1000">Kelan Mine 49 [12299]</option>
                        <option value="12300,1000,1000">Kelan Mine 50 [12300]</option>
                        <option value="12301,1000,1000">Kelan Mine 51 [12301]</option>
                        <option value="12302,1000,1000">Kelan Mine 52 [12302]</option>
                        <option value="12303,1000,1000">Kelan Mine 53 [12303]</option>
                        <option value="12304,1000,1000">Kelan Mine 54 [12304]</option>
                        <option value="12305,1000,1000">Kelan Mine 55 [12305]</option>
                        <option value="12306,1000,1000">Kelan Mine 56 [12306]</option>
                        <option value="12307,1000,1000">Kelan Mine 57 [12307]</option>
                        <option value="12312,1000,1000">Kelan Mine 62 [12312]</option>
                        <option value="12313,1000,1000">Kelan Mine 63 [12313]</option>
                        <option value="12314,1000,1000">Kelan Mine 64 [12314]</option>
                        <option value="12350,1000,1000">Kelan Dungeon 0 [12350]</option>
                        <option value="12351,1000,1000">Kelan Dungeon 1 [12351]</option>
                        <option value="12352,1000,1000">Kelan Dungeon 2 [12352]</option>
                        <option value="12353,1000,1000">Kelan Dungeon 3 [12353]</option>
                        <option value="12354,1000,1000">Kelan Dungeon 4 [12354]</option>
                        <option value="12355,1000,1000">Kelan Dungeon 5 [12355]</option>
                        <option value="12356,1000,1000">Kelan Dungeon 6 [12356]</option>
                        <option value="12357,1000,1000">Kelan Dungeon 7 [12357]</option>
                        <option value="12358,1000,1000">Kelan Dungeon 8 [12358]</option>
                        <option value="12359,1000,1000">Kelan Dungeon 9 [12359]</option>
                        <option value="12360,1000,1000">Kelan Dungeon 10 [12360]</option>
                        <option value="12361,1000,1000">Kelan Dungeon 11 [12361]</option>
                        <option value="12362,1000,1000">Kelan Dungeon 12 [12362]</option>
                        <option value="12363,1000,1000">Kelan Dungeon 13 [12363]</option>
                        <option value="12364,1000,1000">Kelan Dungeon 14 [12364]</option>
                        <option value="12365,1000,1000">Kelan Dungeon 15 [12365]</option>
                        <option value="12366,1000,1000">Kelan Dungeon 16 [12366]</option>
                        <option value="12367,1000,1000">Kelan Dungeon 17 [12367]</option>
                        <option value="12368,1000,1000">Kelan Dungeon 18 [12368]</option>
                        <option value="12369,1000,1000">Kelan Dungeon 19 [12369]</option>
                        <option value="12370,1000,1000">Kelan Dungeon 20 [12370]</option>
                        <option value="12371,1000,1000">Kelan Dungeon 21 [12371]</option>
                        <option value="12372,1000,1000">Kelan Dungeon 22 [12372]</option>
                        <option value="12373,1000,1000">Kelan Dungeon 23 [12373]</option>
                        <option value="12375,1000,1000">Kelan Dungeon 25 [12375]</option>
                        <option value="12376,1000,1000">Kelan Dungeon 26 [12376]</option>
                        <option value="12377,1000,1000">Kelan Dungeon 27 [12377]</option>
                        <option value="12378,1000,1000">Kelan Dungeon 28 [12378]</option>
                        <option value="12379,1000,1000">Kelan Dungeon 29 [12379]</option>
                        <option value="12380,1000,1000">Kelan Dungeon 30 [12380]</option>
                        <option value="12400,1000,1000">Kelan Tower 0 [12400]</option>
                        <option value="12401,1000,1000">Kelan Tower 1 [12401]</option>
                        <option value="12402,1000,1000">Kelan Tower 2 [12402]</option>
                        <option value="12403,1000,1000">Kelan Tower 3 [12403]</option>
                        <option value="12404,1000,1000">Kelan Tower 4 [12404]</option>
                        <option value="12405,1000,1000">Kelan Tower 5 [12405]</option>
                        <option value="12406,1000,1000">Kelan Tower 6 [12406]</option>
                        <option value="12407,1000,1000">Kelan Tower 7 [12407]</option>
                        <option value="12408,1000,1000">Kelan Tower 8 [12408]</option>
                        <option value="12450,1000,1000">Kelan Volcano 0 [12450]</option>
                        <option value="12451,1000,1000">Kelan Volcano 1 [12451]</option>
                        <option value="12452,1000,1000">Kelan Volcano 2 [12452]</option>
                        <option value="12453,1000,1000">Kelan Volcano 3 [12453]</option>
                        <option value="12454,1000,1000">Kelan Volcano 4 [12454]</option>
                        <option value="12455,1000,1000">Kelan Volcano 5 [12455]</option>
                        <option value="12456,1000,1000">Kelan Volcano 6 [12456]</option>
                        <option value="12457,1000,1000">Kelan Volcano 7 [12457]</option>
                        <option value="12458,1000,1000">Kelan Volcano 8 [12458]</option>
                        <option value="12459,1000,1000">Kelan Volcano 9 [12459]</option>
                        <option value="12460,1000,1000">Kelan Volcano 10 [12460]</option>
                        <option value="12461,1000,1000">Kelan Volcano 11 [12461]</option>
                        <option value="12462,1000,1000">Kelan Volcano 12 [12462]</option>
                        <option value="12463,1000,1000">Kelan Volcano 13 [12463]</option>
                        <option value="12464,1000,1000">Kelan Volcano 14 [12464]</option>
                        <option value="12465,1000,1000">Kelan Volcano 15 [12465]</option>
                        <option value="12466,1000,1000">Kelan Volcano 16 [12466]</option>
                        <option value="12467,1000,1000">Kelan Volcano 17 [12467]</option>
                        <option value="12468,1000,1000">Kelan Volcano 18 [12468]</option>
                        <option value="12469,1000,1000">Kelan Volcano 19 [12469]</option>
                        <option value="12500,1000,1000">Kelan Sea Cave 0 [12500]</option>
                        <option value="12501,1000,1000">Kelan Sea Cave 1 [12501]</option>
                        <option value="12502,1000,1000">Kelan Sea Cave 2 [12502]</option>
                        <option value="12503,1000,1000">Kelan Sea Cave 3 [12503]</option>
                        <option value="12504,1000,1000">Kelan Sea Cave 4 [12504]</option>
                        <option value="12505,1000,1000">Kelan Sea Cave 5 [12505]</option>
                        <option value="12506,1000,1000">Kelan Sea Cave 6 [12506]</option>
                        <option value="12507,1000,1000">Kelan Sea Cave 7 [12507]</option>
                        <option value="12508,1000,1000">Kelan Sea Cave 8 [12508]</option>
                        <option value="12509,1000,1000">Kelan Sea Cave 9 [12509]</option>
                        <option value="12510,1000,1000">Kelan Sea Cave 10 [12510]</option>
                        <option value="12511,1000,1000">Kelan Sea Cave 11 [12511]</option>
                        <option value="12512,1000,1000">Kelan Sea Cave 12 [12512]</option>
                        <option value="12513,1000,1000">Kelan Sea Cave 13 [12513]</option>
                        <option value="12514,1000,1000">Kelan Sea Cave 14 [12514]</option>
                        <option value="12515,1000,1000">Kelan Sea Cave 15 [12515]</option>
                        <option value="12516,1000,1000">Kelan Sea Cave 16 [12516]</option>
                        <option value="12517,1000,1000">Kelan Sea Cave 17 [12517]</option>
                        <option value="12518,1000,1000">Kelan Sea Cave 18 [12518]</option>
                        <option value="12519,1000,1000">Kelan Sea Cave 19 [12519]</option>
                        <option value="12520,1000,1000">Kelan Sea Cave 20 [12520]</option>
                        <option value="12521,1000,1000">Kelan Sea Cave 21 [12521]</option>
                        <option value="12523,1000,1000">Kelan Sea Cave 23 [12523]</option>
                        <option value="12524,1000,1000">Kelan Sea Cave 24 [12524]</option>
                        <option value="12525,1000,1000">Kelan Sea Cave 25 [12525]</option>
                        <option value="12526,1000,1000">Kelan Sea Cave 26 [12526]</option>
                        <option value="12527,1000,1000">Kelan Sea Cave 27 [12527]</option>
                        <option value="12528,1000,1000">Kelan Sea Cave 28 [12528]</option>
                        <option value="12529,1000,1000">Kelan Sea Cave 29 [12529]</option>
                        <option value="12530,1000,1000">Kelan Sea Cave 30 [12530]</option>
                        <option value="12531,1000,1000">Kelan Sea Cave 31 [12531]</option>
                        <option value="12532,1000,1000">Kelan Sea Cave 32 [12532]</option>
                        <option value="12533,1000,1000">Kelan Sea Cave 33 [12533]</option>
                        <option value="12534,1000,1000">Kelan Sea Cave 34 [12534]</option>
                        <option value="12535,1000,1000">Kelan Sea Cave 35 [12535]</option>
                        <option value="12536,1000,1000">Kelan Sea Cave 36 [12536]</option>
                        <option value="12537,1000,1000">Kelan Sea Cave 37 [12537]</option>
                        <option value="12538,1000,1000">Kelan Sea Cave 38 [12538]</option>
                        <option value="12539,1000,1000">Kelan Sea Cave 39 [12539]</option>
                        <option value="12540,1000,1000">Kelan Sea Cave 40 [12540]</option>
                        <option value="12541,1000,1000">Kelan Sea Cave 41 [12541]</option>
                        <option value="12542,1000,1000">Kelan Sea Cave 42 [12542]</option>
                        <option value="12543,1000,1000">Kelan Sea Cave 43 [12543]</option>
                        <option value="12544,1000,1000">Kelan Sea Cave 44 [12544]</option>
                        <option value="12545,1000,1000">Kelan Sea Cave 45 [12545]</option>
                        <option value="12546,1000,1000">Kelan Sea Cave 46 [12546]</option>
                        <option value="12547,1000,1000">Kelan Sea Cave 47 [12547]</option>
                        <option value="12548,1000,1000">Kelan Sea Cave 48 [12548]</option>
                        <option value="12549,1000,1000">Kelan Sea Cave 49 [12549]</option>
                        <option value="12551,1000,1000">Kelan Sea Cave 51 [12551]</option>
                        <option value="12552,1000,1000">Kelan Sea Cave 52 [12552]</option>
                        <option value="12553,1000,1000">Kelan Sea Cave 53 [12553]</option>
                        <option value="12554,1000,1000">Kelan Sea Cave 54 [12554]</option>
                        <option value="12555,1000,1000">Kelan Sea Cave 55 [12555]</option>
                        <option value="12600,1000,1000">Kelan Deep Forest 0 [12600]</option>
                        <option value="12601,1000,1000">Kelan Deep Forest 1 [12601]</option>
                        <option value="12602,1000,1000">Kelan Deep Forest 2 [12602]</option>
                        <option value="12603,1000,1000">Kelan Deep Forest 3 [12603]</option>
                        <option value="12604,1000,1000">Kelan Deep Forest 4 [12604]</option>
                        <option value="12605,1000,1000">Kelan Deep Forest 5 [12605]</option>
                        <option value="12606,1000,1000">Kelan Deep Forest 6 [12606]</option>
                        <option value="12607,1000,1000">Kelan Deep Forest 7 [12607]</option>
                        <option value="12608,1000,1000">Kelan Deep Forest 8 [12608]</option>
                        <option value="12609,1000,1000">Kelan Deep Forest 9 [12609]</option>
                        <option value="12610,1000,1000">Kelan Deep Forest 10 [12610]</option>
                        <option value="12611,1000,1000">Kelan Deep Forest 11 [12611]</option>
                        <option value="12612,1000,1000">Kelan Deep Forest 12 [12612]</option>
                        <option value="12613,1000,1000">Kelan Deep Forest 13 [12613]</option>
                        <option value="12614,1000,1000">Kelan Deep Forest 14 [12614]</option>
                        <option value="12615,1000,1000">Kelan Deep Forest 15 [12615]</option>
                        <option value="12616,1000,1000">Kelan Deep Forest 16 [12616]</option>
                        <option value="12617,1000,1000">Kelan Deep Forest 17 [12617]</option>
                        <option value="12618,1000,1000">Kelan Deep Forest 18 [12618]</option>
                        <option value="12619,1000,1000">Kelan Deep Forest 19 [12619]</option>
                        <option value="12620,1000,1000">Kelan Deep Forest 20 [12620]</option>
                        <option value="12621,1000,1000">Kelan Deep Forest 21 [12621]</option>
                        <option value="12622,1000,1000">Kelan Deep Forest 22 [12622]</option>
                        <option value="12623,1000,1000">Kelan Deep Forest 23 [12623]</option>
                        <option value="12624,1000,1000">Kelan Deep Forest 24 [12624]</option>
                        <option value="12625,1000,1000">Kelan Deep Forest 25 [12625]</option>
                        <option value="12626,1000,1000">Kelan Deep Forest 26 [12626]</option>
                        <option value="12627,1000,1000">Kelan Deep Forest 27 [12627]</option>
                        <option value="12628,1000,1000">Kelan Deep Forest 28 [12628]</option>
                        <option value="12629,1000,1000">Kelan Deep Forest 29 [12629]</option>
                        <option value="12630,1000,1000">Kelan Deep Forest 30 [12630]</option>
                        <option value="12631,1000,1000">Kelan Deep Forest 31 [12631]</option>
                        <option value="12633,1000,1000">Kelan Deep Forest 33 [12633]</option>
                        <option value="12634,1000,1000">Kelan Deep Forest 34 [12634]</option>
                        <option value="12635,1000,1000">Kelan Deep Forest 35 [12635]</option>
                        <option value="12636,1000,1000">Kelan Deep Forest 36 [12636]</option>
                        <option value="12637,1000,1000">Kelan Deep Forest 37 [12637]</option>
                        <option value="12638,1000,1000">Kelan Deep Forest 38 [12638]</option>
                        <option value="12639,1000,1000">Kelan Deep Forest 39 [12639]</option>
                        <option value="12640,1000,1000">Kelan Deep Forest 40 [12640]</option>
                        <option value="12641,1000,1000">Kelan Deep Forest 41 [12641]</option>
                        <option value="12642,1000,1000">Kelan Deep Forest 42 [12642]</option>
                        <option value="12643,1000,1000">Kelan Deep Forest 43 [12643]</option>
                        <option value="12644,1000,1000">Kelan Deep Forest 44 [12644]</option>
                        <option value="12645,1000,1000">Kelan Deep Forest 45 [12645]</option>
                        <option value="12646,1000,1000">Kelan Deep Forest 46 [12646]</option>
                        <option value="12647,1000,1000">Kelan Deep Forest 47 [12647]</option>
                        <option value="12649,1000,1000">Kelan Deep Forest 49 [12649]</option>
                        <option value="12650,1000,1000">Kelan Deep Forest 50 [12650]</option>
                        <option value="12651,1000,1000">Kelan Deep Forest 51 [12651]</option>
                        <option value="12652,1000,1000">Kelan Deep Forest 52 [12652]</option>
                        <option value="12653,1000,1000">Kelan Deep Forest 53 [12653]</option>
                        <option value="12654,1000,1000">Kelan Deep Forest 54 [12654]</option>
                        <option value="12655,1000,1000">Kelan Deep Forest 55 [12655]</option>
                        <option value="12656,1000,1000">Kelan Deep Forest 56 [12656]</option>
                        <option value="12657,1000,1000">Kelan Deep Forest 57 [12657]</option>
                        <option value="12658,1000,1000">Kelan Deep Forest 58 [12658]</option>
                        <option value="12659,1000,1000">Kelan Deep Forest 59 [12659]</option>
                        <option value="12660,1000,1000">Kelan Deep Forest 60 [12660]</option>
                        <option value="12661,1000,1000">Kelan Deep Forest 61 [12661]</option>
                        <option value="12662,1000,1000">Kelan Deep Forest 62 [12662]</option>
                        <option value="12663,1000,1000">Kelan Deep Forest 63 [12663]</option>
                        <option value="12664,1000,1000">Kelan Deep Forest 64 [12664]</option>
                        <option value="12665,1000,1000">Kelan Deep Forest 65 [12665]</option>
                        <option value="12666,1000,1000">Kelan Deep Forest 66 [12666]</option>
                        <option value="12667,1000,1000">Kelan Deep Forest 67 [12667]</option>
                        <option value="12668,1000,1000">Kelan Deep Forest 68 [12668]</option>
                        <option value="12669,1000,1000">Kelan Deep Forest 69 [12669]</option>
                        <option value="12670,1000,1000">Kelan Deep Forest 70 [12670]</option>
                        <option value="12671,1000,1000">Kelan Deep Forest 71 [12671]</option>
                        <option value="12672,1000,1000">Kelan Deep Forest 72 [12672]</option>
                        <option value="12673,1000,1000">Kelan Deep Forest 73 [12673]</option>
                        <option value="12674,1000,1000">Kelan Deep Forest 74 [12674]</option>
                        <option value="12675,1000,1000">Kelan Deep Forest 75 [12675]</option>
                        <option value="12676,1000,1000">Kelan Deep Forest 76 [12676]</option>
                        <option value="12700,1000,1000">Kelan Ruins 0 [12700]</option>
                        <option value="12701,1000,1000">Kelan Ruins 1 [12701]</option>
                        <option value="12702,1000,1000">Kelan Ruins 2 [12702]</option>
                        <option value="12703,1000,1000">Kelan Ruins 3 [12703]</option>
                        <option value="12704,1000,1000">Kelan Ruins 4 [12704]</option>
                        <option value="12705,1000,1000">Kelan Ruins 5 [12705]</option>
                        <option value="12706,1000,1000">Kelan Ruins 6 [12706]</option>
                        <option value="12707,1000,1000">Kelan Ruins 7 [12707]</option>
                        <option value="12750,1000,1000">Kelan Ancient Temple 0 [12750]</option>
                        <option value="12751,1000,1000">Kelan Ancient Temple 1 [12751]</option>
                        <option value="12752,1000,1000">Kelan Ancient Temple 2 [12752]</option>
                        <option value="12753,1000,1000">Kelan Ancient Temple 3 [12753]</option>
                        <option value="12754,1000,1000">Kelan Ancient Temple 4 [12754]</option>
                        <option value="12755,1000,1000">Kelan Ancient Temple 5 [12755]</option>
                        <option value="12756,1000,1000">Kelan Ancient Temple 6 [12756]</option>
                        <option value="12757,1000,1000">Kelan Ancient Temple 7 [12757]</option>
                        <option value="12758,1000,1000">Kelan Ancient Temple 8 [12758]</option>
                        <option value="12759,1000,1000">Kelan Ancient Temple 9 [12759]</option>
                        <option value="12760,1000,1000">Kelan Ancient Temple 10 [12760]</option>
                        <option value="12761,1000,1000">Kelan Ancient Temple 11 [12761]</option>
                        <option value="12762,1000,1000">Kelan Ancient Temple 12 [12762]</option>
                        <option value="12763,1000,1000">Kelan Ancient Temple 13 [12763]</option>
                        <option value="12764,1000,1000">Kelan Ancient Temple 14 [12764]</option>
                        <option value="12765,1000,1000">Kelan Ancient Temple 15 [12765]</option>
                        <option value="12766,1000,1000">Kelan Ancient Temple 16 [12766]</option>
                        <option value="12767,1000,1000">Kelan Ancient Temple 17 [12767]</option>
                        <option value="12768,1000,1000">Kelan Ancient Temple 18 [12768]</option>
                        <option value="12800,1000,1000">Kelan Grotto 0 [12800]</option>
                        <option value="12801,1000,1000">Kelan Grotto 1 [12801]</option>
                        <option value="12802,1000,1000">Kelan Grotto 2 [12802]</option>
                        <option value="12803,1000,1000">Kelan Grotto 3 [12803]</option>
                        <option value="12804,1000,1000">Kelan Grotto 4 [12804]</option>
                        <option value="12805,1000,1000">Kelan Grotto 5 [12805]</option>
                        <option value="12806,1000,1000">Kelan Grotto 6 [12806]</option>
                        <option value="12807,1000,1000">Kelan Grotto 7 [12807]</option>
                        <option value="12808,1000,1000">Kelan Grotto 8 [12808]</option>
                        <option value="12809,1000,1000">Kelan Grotto 9 [12809]</option>
                        <option value="12810,1000,1000">Kelan Grotto 10 [12810]</option>
                        <option value="12811,1000,1000">Kelan Grotto 11 [12811]</option>
                        <option value="12812,1000,1000">Kelan Grotto 12 [12812]</option>
                        <option value="12813,1000,1000">Kelan Grotto 13 [12813]</option>
                        <option value="12814,1000,1000">Kelan Grotto 14 [12814]</option>
                        <option value="12815,1000,1000">Kelan Grotto 15 [12815]</option>
                        <option value="12816,1000,1000">Kelan Grotto 16 [12816]</option>
                        <option value="12817,1000,1000">Kelan Grotto 17 [12817]</option>
                        <option value="12818,1000,1000">Kelan Grotto 18 [12818]</option>
                        <option value="12819,1000,1000">Kelan Grotto 19 [12819]</option>
                        <option value="12820,1000,1000">Kelan Grotto 20 [12820]</option>
                        <option value="12821,1000,1000">Kelan Grotto 21 [12821]</option>
                        <option value="12822,1000,1000">Kelan Grotto 22 [12822]</option>
                        <option value="12823,1000,1000">Kelan Grotto 23 [12823]</option>
                        <option value="12824,1000,1000">Kelan Grotto 24 [12824]</option>
                        <option value="12825,1000,1000">Kelan Grotto 25 [12825]</option>
                        <option value="12826,1000,1000">Kelan Grotto 26 [12826]</option>
                        <option value="12827,1000,1000">Kelan Grotto 27 [12827]</option>
                        <option value="12828,1000,1000">Kelan Grotto 28 [12828]</option>
                        <option value="12829,1000,1000">Kelan Grotto 29 [12829]</option>
                        <option value="12830,1000,1000">Kelan Grotto 30 [12830]</option>
                        <option value="12831,1000,1000">Kelan Grotto 31 [12831]</option>
                        <option value="12832,1000,1000">Kelan Grotto 32 [12832]</option>
                        <option value="12833,1000,1000">Kelan Grotto 33 [12833]</option>
                        <option value="12834,1000,1000">Kelan Grotto 34 [12834]</option>
                        <option value="12835,1000,1000">Kelan Grotto 35 [12835]</option>
                        <option value="12836,1000,1000">Kelan Grotto 36 [12836]</option>
                        <option value="12837,1000,1000">Kelan Grotto 37 [12837]</option>
                        <option value="12838,1000,1000">Kelan Grotto 38 [12838]</option>
                        <option value="12839,1000,1000">Kelan Grotto 39 [12839]</option>
                        <option value="12840,1000,1000">Kelan Grotto 40 [12840]</option>
                        <option value="12841,1000,1000">Kelan Grotto 41 [12841]</option>
                        <option value="12842,1000,1000">Kelan Grotto 42 [12842]</option>
                        <option value="12845,1000,1000">Kelan Underground 0 [12845]</option>
                        <option value="12846,1000,1000">Kelan Underground 1 [12846]</option>
                        <option value="12847,1000,1000">Kelan Underground 2 [12847]</option>
                        <option value="12850,1000,1000">Kelan Underground 5 [12850]</option>
                        <option value="12851,1000,1000">Kelan Underground 6 [12851]</option>
                        <option value="12852,1000,1000">Kelan Underground 7 [12852]</option>
                        <option value="12853,1000,1000">Kelan Underground 8 [12853]</option>
                        <option value="12854,1000,1000">Kelan Underground 9 [12854]</option>
                        <option value="12855,1000,1000">Kelan Underground 10 [12855]</option>
                        <option value="12856,1000,1000">Kelan Underground 11 [12856]</option>
                        <option value="12857,1000,1000">Kelan Underground 12 [12857]</option>
                        <option value="12858,1000,1000">Kelan Underground 13 [12858]</option>
                        <option value="12859,1000,1000">Kelan Underground 14 [12859]</option>
                        <option value="12860,1000,1000">Kelan Underground 15 [12860]</option>
                        <option value="12861,1000,1000">Kelan Underground 16 [12861]</option>
                        <option value="12862,1000,1000">Kelan Underground 17 [12862]</option>
                        <option value="12863,1000,1000">Kelan Underground 18 [12863]</option>
                        <option value="12864,1000,1000">Kelan Underground 19 [12864]</option>
                        <option value="12865,1000,1000">Kelan Underground 20 [12865]</option>
                        <option value="12866,1000,1000">Kelan Underground 21 [12866]</option>
                        <option value="12867,1000,1000">Kelan Underground 22 [12867]</option>
                        <option value="12868,1000,1000">Kelan Underground 23 [12868]</option>
                        <option value="12869,1000,1000">Kelan Underground 24 [12869]</option>
                        <option value="12870,1000,1000">Kelan Underground 25 [12870]</option>
                        <option value="12871,1000,1000">Kelan Underground 26 [12871]</option>
                        <option value="12872,1000,1000">Kelan Underground 27 [12872]</option>
                        <option value="12873,1000,1000">Kelan Underground 28 [12873]</option>
                        <option value="12874,1000,1000">Kelan Underground 29 [12874]</option>
                        <option value="12875,1000,1000">Kelan Underground 30 [12875]</option>
                        <option value="12876,1000,1000">Kelan Underground 31 [12876]</option>
                        <option value="12877,1000,1000">Kelan Underground 32 [12877]</option>
                        <option value="12878,1000,1000">Kelan Underground 33 [12878]</option>
                        <option value="12879,1000,1000">Kelan Underground 34 [12879]</option>
                        <option value="12880,1000,1000">Kelan Underground 35 [12880]</option>
                        <option value="12900,1000,1000">Kelan Abyss 0 [12900]</option>
                        <option value="12901,1000,1000">Kelan Abyss 1 [12901]</option>
                        <option value="12902,1000,1000">Kelan Abyss 2 [12902]</option>
                        <option value="12903,1000,1000">Kelan Abyss 3 [12903]</option>
                        <option value="12904,1000,1000">Kelan Abyss 4 [12904]</option>
                        <option value="12905,1000,1000">Kelan Abyss 5 [12905]</option>
                        <option value="12906,1000,1000">Kelan Abyss 6 [12906]</option>
                        <option value="12907,1000,1000">Kelan Abyss 7 [12907]</option>
                        <option value="12908,1000,1000">Kelan Abyss 8 [12908]</option>
                        <option value="12909,1000,1000">Kelan Abyss 9 [12909]</option>
                        <option value="12910,1000,1000">Kelan Abyss 10 [12910]</option>
                        <option value="12911,1000,1000">Kelan Abyss 11 [12911]</option>
                        <option value="12912,1000,1000">Kelan Abyss 12 [12912]</option>
                        <option value="12913,1000,1000">Kelan Abyss 13 [12913]</option>
                        <option value="12914,1000,1000">Kelan Abyss 14 [12914]</option>
                        <option value="12915,1000,1000">Kelan Abyss 15 [12915]</option>
                        <option value="12916,1000,1000">Kelan Abyss 16 [12916]</option>
                        <option value="12917,1000,1000">Kelan Abyss 17 [12917]</option>
                        <option value="12918,1000,1000">Kelan Abyss 18 [12918]</option>
                        <option value="12919,1000,1000">Kelan Abyss 19 [12919]</option>
                        <option value="12920,1000,1000">Kelan Abyss 20 [12920]</option>
                        <option value="12921,1000,1000">Kelan Abyss 21 [12921]</option>
                        <option value="12922,1000,1000">Kelan Abyss 22 [12922]</option>
                        <option value="12923,1000,1000">Kelan Abyss 23 [12923]</option>
                        <option value="12924,1000,1000">Kelan Abyss 24 [12924]</option>
                        <option value="12925,1000,1000">Kelan Abyss 25 [12925]</option>
                        <option value="12926,1000,1000">Kelan Abyss 26 [12926]</option>
                        <option value="12950,1000,1000">Kelan Final Area 0 [12950]</option>
                        <option value="12951,1000,1000">Kelan Final Area 1 [12951]</option>
                        <option value="12952,1000,1000">Kelan Final Area 2 [12952]</option>
                        <option value="12953,1000,1000">Kelan Final Area 3 [12953]</option>
                        <option value="12954,1000,1000">Kelan Final Area 4 [12954]</option>
                        <option value="12955,1000,1000">Kelan Final Area 5 [12955]</option>
                        <option value="12956,1000,1000">Kelan Final Area 6 [12956]</option>
                        <option value="12957,1000,1000">Kelan Final Area 7 [12957]</option>
                        <option value="12958,1000,1000">Kelan Final Area 8 [12958]</option>
                        <option value="12959,1000,1000">Kelan Final Area 9 [12959]</option>
                        <option value="12960,1000,1000">Kelan Final Area 10 [12960]</option>
                        <option value="12962,1000,1000">Kelan Final Area 12 [12962]</option>
                        <option value="12963,1000,1000">Kelan Final Area 13 [12963]</option>
                    </optgroup>
                    <optgroup label="Welling Bolgesi / Welling Region (13xxx)">
                        <option value="13000,2400,1200">Welling Village [13000]</option>
                        <option value="13001,340,360">Welling Chief's House [13001]</option>
                        <option value="13002,300,300">Welling Clinic [13002]</option>
                        <option value="13003,280,380">Welling Weapon Shop [13003]</option>
                        <option value="13004,380,340">Welling Props Shop [13004]</option>
                        <option value="13005,400,300">Welling Temple [13005]</option>
                        <option value="13006,300,300">Welling Tavern [13006]</option>
                        <option value="13007,300,300">Welling Pet Shop [13007]</option>
                        <option value="13008,300,300">Welling Bank [13008]</option>
                        <option value="13009,300,300">Welling Casino [13009]</option>
                        <option value="13010,1000,1000">Map 13010 [13010]</option>
                        <option value="13011,1000,1000">Map 13011 [13011]</option>
                        <option value="13012,1000,1000">Map 13012 [13012]</option>
                        <option value="13013,1000,1000">Map 13013 [13013]</option>
                        <option value="13014,1000,1000">Map 13014 [13014]</option>
                        <option value="13015,1000,1000">Map 13015 [13015]</option>
                        <option value="13016,1000,1000">Map 13016 [13016]</option>
                        <option value="13017,1000,1000">Map 13017 [13017]</option>
                        <option value="13018,1000,1000">Map 13018 [13018]</option>
                        <option value="13019,1000,1000">Map 13019 [13019]</option>
                        <option value="13020,1000,1000">Map 13020 [13020]</option>
                        <option value="13021,1000,1000">Map 13021 [13021]</option>
                        <option value="13022,1000,1000">Map 13022 [13022]</option>
                        <option value="13050,1000,1000">Welling Cave 0 [13050]</option>
                        <option value="13051,1000,1000">Welling Cave 1 [13051]</option>
                        <option value="13052,1000,1000">Welling Cave 2 [13052]</option>
                        <option value="13053,1000,1000">Welling Cave 3 [13053]</option>
                        <option value="13054,1000,1000">Welling Cave 4 [13054]</option>
                        <option value="13055,1000,1000">Welling Cave 5 [13055]</option>
                        <option value="13056,1000,1000">Welling Cave 6 [13056]</option>
                        <option value="13057,1000,1000">Welling Cave 7 [13057]</option>
                        <option value="13100,1000,1000">Welling Forest 0 [13100]</option>
                        <option value="13101,1000,1000">Welling Forest 1 [13101]</option>
                        <option value="13102,1000,1000">Welling Forest 2 [13102]</option>
                        <option value="13103,1000,1000">Welling Forest 3 [13103]</option>
                        <option value="13104,1000,1000">Welling Forest 4 [13104]</option>
                        <option value="13105,1000,1000">Welling Forest 5 [13105]</option>
                        <option value="13106,1000,1000">Welling Forest 6 [13106]</option>
                        <option value="13107,1000,1000">Welling Forest 7 [13107]</option>
                        <option value="13108,1000,1000">Welling Forest 8 [13108]</option>
                        <option value="13109,1000,1000">Welling Forest 9 [13109]</option>
                        <option value="13110,1000,1000">Welling Forest 10 [13110]</option>
                        <option value="13111,1000,1000">Welling Forest 11 [13111]</option>
                        <option value="13112,1000,1000">Welling Forest 12 [13112]</option>
                        <option value="13113,1000,1000">Welling Forest 13 [13113]</option>
                        <option value="13114,1000,1000">Welling Forest 14 [13114]</option>
                        <option value="13115,1000,1000">Welling Forest 15 [13115]</option>
                        <option value="13116,1000,1000">Welling Forest 16 [13116]</option>
                        <option value="13117,1000,1000">Welling Forest 17 [13117]</option>
                        <option value="13118,1000,1000">Welling Forest 18 [13118]</option>
                        <option value="13119,1000,1000">Welling Forest 19 [13119]</option>
                        <option value="13120,1000,1000">Welling Forest 20 [13120]</option>
                        <option value="13121,1000,1000">Welling Forest 21 [13121]</option>
                        <option value="13122,1000,1000">Welling Forest 22 [13122]</option>
                        <option value="13123,1000,1000">Welling Forest 23 [13123]</option>
                        <option value="13124,1000,1000">Welling Forest 24 [13124]</option>
                        <option value="13125,1000,1000">Welling Forest 25 [13125]</option>
                        <option value="13126,1000,1000">Welling Forest 26 [13126]</option>
                        <option value="13150,1000,1000">Welling Mountain 0 [13150]</option>
                        <option value="13151,1000,1000">Welling Mountain 1 [13151]</option>
                        <option value="13152,1000,1000">Welling Mountain 2 [13152]</option>
                        <option value="13153,1000,1000">Welling Mountain 3 [13153]</option>
                        <option value="13154,1000,1000">Welling Mountain 4 [13154]</option>
                        <option value="13155,1000,1000">Welling Mountain 5 [13155]</option>
                        <option value="13156,1000,1000">Welling Mountain 6 [13156]</option>
                        <option value="13157,1000,1000">Welling Mountain 7 [13157]</option>
                        <option value="13158,1000,1000">Welling Mountain 8 [13158]</option>
                        <option value="13159,1000,1000">Welling Mountain 9 [13159]</option>
                        <option value="13160,1000,1000">Welling Mountain 10 [13160]</option>
                        <option value="13161,1000,1000">Welling Mountain 11 [13161]</option>
                        <option value="13162,1000,1000">Welling Mountain 12 [13162]</option>
                        <option value="13163,1000,1000">Welling Mountain 13 [13163]</option>
                        <option value="13164,1000,1000">Welling Mountain 14 [13164]</option>
                        <option value="13165,1000,1000">Welling Mountain 15 [13165]</option>
                        <option value="13166,1000,1000">Welling Mountain 16 [13166]</option>
                        <option value="13167,1000,1000">Welling Mountain 17 [13167]</option>
                        <option value="13168,1000,1000">Welling Mountain 18 [13168]</option>
                        <option value="13169,1000,1000">Welling Mountain 19 [13169]</option>
                        <option value="13170,1000,1000">Welling Mountain 20 [13170]</option>
                        <option value="13171,1000,1000">Welling Mountain 21 [13171]</option>
                        <option value="13172,1000,1000">Welling Mountain 22 [13172]</option>
                        <option value="13173,1000,1000">Welling Mountain 23 [13173]</option>
                        <option value="13174,1000,1000">Welling Mountain 24 [13174]</option>
                        <option value="13175,1000,1000">Welling Mountain 25 [13175]</option>
                        <option value="13176,1000,1000">Welling Mountain 26 [13176]</option>
                        <option value="13177,1000,1000">Welling Mountain 27 [13177]</option>
                        <option value="13178,1000,1000">Welling Mountain 28 [13178]</option>
                        <option value="13179,1000,1000">Welling Mountain 29 [13179]</option>
                        <option value="13180,1000,1000">Welling Mountain 30 [13180]</option>
                        <option value="13181,1000,1000">Welling Mountain 31 [13181]</option>
                        <option value="13182,1000,1000">Welling Mountain 32 [13182]</option>
                        <option value="13183,1000,1000">Welling Mountain 33 [13183]</option>
                        <option value="13200,1000,1000">Welling Plains 0 [13200]</option>
                        <option value="13201,1000,1000">Welling Plains 1 [13201]</option>
                        <option value="13202,1000,1000">Welling Plains 2 [13202]</option>
                        <option value="13203,1000,1000">Welling Plains 3 [13203]</option>
                        <option value="13204,1000,1000">Welling Plains 4 [13204]</option>
                        <option value="13205,1000,1000">Welling Plains 5 [13205]</option>
                        <option value="13206,1000,1000">Welling Plains 6 [13206]</option>
                        <option value="13207,1000,1000">Welling Plains 7 [13207]</option>
                        <option value="13208,1000,1000">Welling Plains 8 [13208]</option>
                        <option value="13209,1000,1000">Welling Plains 9 [13209]</option>
                        <option value="13210,1000,1000">Welling Plains 10 [13210]</option>
                        <option value="13211,1000,1000">Welling Plains 11 [13211]</option>
                        <option value="13212,1000,1000">Welling Plains 12 [13212]</option>
                        <option value="13213,1000,1000">Welling Plains 13 [13213]</option>
                        <option value="13214,1000,1000">Welling Plains 14 [13214]</option>
                        <option value="13215,1000,1000">Welling Plains 15 [13215]</option>
                        <option value="13216,1000,1000">Welling Plains 16 [13216]</option>
                        <option value="13217,1000,1000">Welling Plains 17 [13217]</option>
                        <option value="13218,1000,1000">Welling Plains 18 [13218]</option>
                        <option value="13219,1000,1000">Welling Plains 19 [13219]</option>
                        <option value="13220,1000,1000">Welling Plains 20 [13220]</option>
                        <option value="13221,1000,1000">Welling Plains 21 [13221]</option>
                        <option value="13222,1000,1000">Welling Plains 22 [13222]</option>
                        <option value="13223,1000,1000">Welling Plains 23 [13223]</option>
                        <option value="13224,1000,1000">Welling Plains 24 [13224]</option>
                        <option value="13225,1000,1000">Welling Plains 25 [13225]</option>
                        <option value="13226,1000,1000">Welling Plains 26 [13226]</option>
                        <option value="13227,1000,1000">Welling Plains 27 [13227]</option>
                        <option value="13228,1000,1000">Welling Plains 28 [13228]</option>
                        <option value="13229,1000,1000">Welling Plains 29 [13229]</option>
                        <option value="13230,1000,1000">Welling Plains 30 [13230]</option>
                        <option value="13231,1000,1000">Welling Plains 31 [13231]</option>
                        <option value="13232,1000,1000">Welling Plains 32 [13232]</option>
                        <option value="13233,1000,1000">Welling Plains 33 [13233]</option>
                        <option value="13234,1000,1000">Welling Plains 34 [13234]</option>
                        <option value="13235,1000,1000">Welling Plains 35 [13235]</option>
                        <option value="13236,1000,1000">Welling Plains 36 [13236]</option>
                        <option value="13237,1000,1000">Welling Plains 37 [13237]</option>
                        <option value="13238,1000,1000">Welling Plains 38 [13238]</option>
                        <option value="13239,1000,1000">Welling Plains 39 [13239]</option>
                        <option value="13240,1000,1000">Welling Plains 40 [13240]</option>
                        <option value="13241,1000,1000">Welling Plains 41 [13241]</option>
                        <option value="13250,1000,1000">Welling Ruins 0 [13250]</option>
                        <option value="13251,1000,1000">Welling Ruins 1 [13251]</option>
                        <option value="13252,1000,1000">Welling Ruins 2 [13252]</option>
                        <option value="13253,1000,1000">Welling Ruins 3 [13253]</option>
                        <option value="13254,1000,1000">Welling Ruins 4 [13254]</option>
                        <option value="13255,1000,1000">Welling Ruins 5 [13255]</option>
                        <option value="13256,1000,1000">Welling Ruins 6 [13256]</option>
                        <option value="13257,1000,1000">Welling Ruins 7 [13257]</option>
                        <option value="13258,1000,1000">Welling Ruins 8 [13258]</option>
                        <option value="13259,1000,1000">Welling Ruins 9 [13259]</option>
                        <option value="13260,1000,1000">Welling Ruins 10 [13260]</option>
                        <option value="13261,1000,1000">Welling Ruins 11 [13261]</option>
                        <option value="13262,1000,1000">Welling Ruins 12 [13262]</option>
                        <option value="13263,1000,1000">Welling Ruins 13 [13263]</option>
                        <option value="13264,1000,1000">Welling Ruins 14 [13264]</option>
                        <option value="13265,1000,1000">Welling Ruins 15 [13265]</option>
                        <option value="13266,1000,1000">Welling Ruins 16 [13266]</option>
                        <option value="13267,1000,1000">Welling Ruins 17 [13267]</option>
                        <option value="13268,1000,1000">Welling Ruins 18 [13268]</option>
                        <option value="13269,1000,1000">Welling Ruins 19 [13269]</option>
                        <option value="13270,1000,1000">Welling Ruins 20 [13270]</option>
                        <option value="13271,1000,1000">Welling Ruins 21 [13271]</option>
                        <option value="13272,1000,1000">Welling Ruins 22 [13272]</option>
                        <option value="13300,1000,1000">Welling Dungeon 0 [13300]</option>
                        <option value="13301,1000,1000">Welling Dungeon 1 [13301]</option>
                        <option value="13400,1000,1000">Welling Dungeon 100 [13400]</option>
                        <option value="13401,1000,1000">Welling Dungeon 101 [13401]</option>
                        <option value="13402,1000,1000">Welling Dungeon 102 [13402]</option>
                        <option value="13403,1000,1000">Welling Dungeon 103 [13403]</option>
                        <option value="13404,1000,1000">Welling Dungeon 104 [13404]</option>
                        <option value="13406,1000,1000">Welling Dungeon 106 [13406]</option>
                    </optgroup>
                    <optgroup label="Arena (30xxx)">
                        <option value="30000,1000,1000">Arena [30000]</option>
                        <option value="30001,1000,1000">Arena 1 [30001]</option>
                        <option value="30002,1000,1000">Arena 2 [30002]</option>
                        <option value="30003,1000,1000">Arena 3 [30003]</option>
                        <option value="30004,1000,1000">Arena 4 [30004]</option>
                        <option value="30005,1000,1000">Arena 5 [30005]</option>
                        <option value="30006,1000,1000">Arena 6 [30006]</option>
                        <option value="30007,1000,1000">Arena 7 [30007]</option>
                        <option value="30008,1000,1000">Arena 8 [30008]</option>
                        <option value="30009,1000,1000">Arena 9 [30009]</option>
                        <option value="30010,1000,1000">Arena 10 [30010]</option>
                        <option value="30011,1000,1000">Arena 11 [30011]</option>
                        <option value="30012,1000,1000">Arena 12 [30012]</option>
                        <option value="30013,1000,1000">Arena 13 [30013]</option>
                        <option value="30014,1000,1000">Arena 14 [30014]</option>
                        <option value="30015,1000,1000">Arena 15 [30015]</option>
                        <option value="30016,1000,1000">Arena 16 [30016]</option>
                        <option value="30017,1000,1000">Arena 17 [30017]</option>
                        <option value="30018,1000,1000">Arena 18 [30018]</option>
                        <option value="30019,1000,1000">Arena 19 [30019]</option>
                        <option value="30020,1000,1000">Arena 20 [30020]</option>
                        <option value="30021,1000,1000">Arena 21 [30021]</option>
                        <option value="30022,1000,1000">Arena 22 [30022]</option>
                    </optgroup>
                    <optgroup label="Ozel Etkinlik / Special Event (58xxx)">
                        <option value="58001,1000,1000">Special Event 0 [58001]</option>
                        <option value="58002,1000,1000">Special Event 1 [58002]</option>
                    </optgroup>
                    <optgroup label="Kuzey Adasi / North Island (60xxx)">
                        <option value="60000,2000,2000">North Island Forest [60000]</option>
                        <option value="60001,1500,1500">Welling Forest [60001]</option>
                        <option value="60002,1000,1000">North Island 2 [60002]</option>
                        <option value="60003,1000,1000">North Island 3 [60003]</option>
                        <option value="60004,1000,1000">North Island 4 [60004]</option>
                        <option value="60005,1000,1000">North Island 5 [60005]</option>
                        <option value="60006,1000,1000">North Island 6 [60006]</option>
                        <option value="60007,1000,1000">North Island 7 [60007]</option>
                        <option value="60008,1000,1000">North Island 8 [60008]</option>
                        <option value="60009,1000,1000">North Island 9 [60009]</option>
                        <option value="60010,1000,1000">North Island 10 [60010]</option>
                        <option value="60011,1000,1000">North Island 11 [60011]</option>
                        <option value="60012,1000,1000">North Island 12 [60012]</option>
                        <option value="60013,1000,1000">North Island 13 [60013]</option>
                        <option value="60014,1000,1000">North Island 14 [60014]</option>
                        <option value="60015,1000,1000">North Island 15 [60015]</option>
                    </optgroup>
                </select>
            </div>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Or Enter Custom Map ID</label>
                <input type="number" id="warp-map" value="12000">
            </div>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>X coordinate</label>
                <input type="number" id="warp-x" value="1000">
            </div>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Y coordinate</label>
                <input type="number" id="warp-y" value="1000">
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeWarpModal()">Cancel</button>
                <button onclick="confirmWarp()">Teleport</button>
            </div>
        </div>
    </div>

    <!-- Gold Modal -->
    <div class="modal" id="gold-modal">
        <div class="modal-content">
            <div class="modal-header">Give Gold to Player</div>
            <input type="hidden" id="gold-player-name">
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Gold Amount</label>
                <input type="number" id="gold-amt" value="1000">
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeGoldModal()">Cancel</button>
                <button onclick="confirmGold()">Give Gold</button>
            </div>
        </div>
    </div>

    <!-- Level Modal -->
    <div class="modal" id="level-modal">
        <div class="modal-content">
            <div class="modal-header">Set Player Level</div>
            <input type="hidden" id="level-player-name">
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Level (1-199)</label>
                <input type="number" id="level-val" value="50" min="1" max="199">
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeLevelModal()">Cancel</button>
                <button onclick="confirmLevel()">Set Level</button>
            </div>
        </div>
    </div>

    <!-- Item Modal -->
    <div class="modal" id="item-modal">
        <div class="modal-content">
            <div class="modal-header">Give Item to Player</div>
            <input type="hidden" id="item-player-name">
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Item Name or ID</label>
                <div class="searchable-dropdown" id="item-searchable-dropdown">
                    <div class="dropdown-select-box" onclick="toggleSearchableDropdown('item')">
                        <span id="item-selected-label">27001 - Red Potion</span>
                        <span class="arrow"></span>
                    </div>
                    <div class="dropdown-content-menu" id="item-dropdown-menu">
                        <div class="dropdown-search-wrapper">
                            <input type="text" class="dropdown-search-input" id="item-dropdown-search" placeholder="Search item by name or ID..." oninput="onFilterSearchableDropdown('item', this.value)">
                        </div>
                        <div class="dropdown-list-container" id="item-dropdown-list">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                    <input type="hidden" id="item-id-search" value="27001">
                </div>
            </div>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Amount / Quantity</label>
                <input type="number" id="item-amt" value="1" min="1">
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeItemModal()">Cancel</button>
                <button onclick="confirmItem()">Give Item</button>
            </div>
        </div>
    </div>

    <!-- Pet Modal -->
    <div class="modal" id="pet-modal">
        <div class="modal-content">
            <div class="modal-header">Give Pet to Player</div>
            <input type="hidden" id="pet-player-name">
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Pet Name or ID</label>
                <div class="searchable-dropdown" id="pet-searchable-dropdown">
                    <div class="dropdown-select-box" onclick="toggleSearchableDropdown('pet')">
                        <span id="pet-selected-label">11058 - Shasha</span>
                        <span class="arrow"></span>
                    </div>
                    <div class="dropdown-content-menu" id="pet-dropdown-menu">
                        <div class="dropdown-search-wrapper">
                            <input type="text" class="dropdown-search-input" id="pet-dropdown-search" placeholder="Search pet by name or ID..." oninput="onFilterSearchableDropdown('pet', this.value)">
                        </div>
                        <div class="dropdown-list-container" id="pet-dropdown-list">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                    <input type="hidden" id="pet-id-search" value="11058">
                </div>
            </div>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label>Pet Level</label>
                <input type="number" id="pet-lvl" value="1" min="1" max="199">
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closePetModal()">Cancel</button>
                <button onclick="confirmPet()">Give Pet</button>
            </div>
        </div>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('uptime').innerText = formatUptime(data.uptime);
                document.getElementById('online-count').innerText = 'Online: ' + data.online_count + ' Players';
                document.getElementById('exp-rate').value = data.exp_multiplier;
                document.getElementById('gold-rate').value = data.gold_multiplier;
            } catch(e) {
                console.error("Error fetching status", e);
            }
        }

        async function fetchPlayers() {
            try {
                const res = await fetch('/api/players');
                const players = await res.json();
                const tbody = document.getElementById('players-list');
                tbody.innerHTML = '';
                if(players.length === 0) {
                    tbody.innerHTML = '<tr><td colspan=\"7\" style=\"text-align: center; color: var(--text-muted);\">No players currently online.</td></tr>';
                    return;
                }
                players.forEach(p => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${p.name}</strong></td>
                        <td><span class="badge badge-cyan">Lv.${p.level}</span></td>
                        <td>🪙 ${p.gold}</td>
                        <td>🗺️ ${p.map_id}</td>
                        <td>${p.x}, ${p.y}</td>
                        <td>${p.ip}</td>
                        <td class="player-actions">
                            <button onclick="openWarpModal('${p.name}')">Teleport</button>
                            <button onclick="openLevelModal('${p.name}', ${p.level})">Level</button>
                            <button onclick="openGoldModal('${p.name}', ${p.gold})">Gold</button>
                            <button onclick="openItemModal('${p.name}')">Item</button>
                            <button onclick="openPetModal('${p.name}')">Pet</button>
                            <button style="background:linear-gradient(135deg,#667eea,#764ba2);" onclick="openDetailModal('${p.name}')">&#128203; Details</button>
                            <button class="btn-danger" onclick="kickPlayer('${p.name}')">Kick</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch(e) {
                console.error("Error fetching players", e);
            }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const logs = await res.json();
                const consoleDiv = document.getElementById('console');
                const isScrolledToBottom = consoleDiv.scrollHeight - consoleDiv.clientHeight <= consoleDiv.scrollTop + 1;
                
                consoleDiv.innerHTML = '';
                logs.forEach(line => {
                    const div = document.createElement('div');
                    div.className = 'console-line';
                    if (line.includes('[INFO]')) div.classList.add('info');
                    else if (line.includes('[WARNING]')) div.classList.add('warning');
                    else if (line.includes('[ERROR]') || line.includes('[CRITICAL]')) div.classList.add('error');
                    div.innerText = line;
                    consoleDiv.appendChild(div);
                });

                if (isScrolledToBottom) {
                    consoleDiv.scrollTop = consoleDiv.scrollHeight;
                }
            } catch(e) {
                console.error("Error fetching logs", e);
            }
        }

        async function updateConfig() {
            const exp = parseFloat(document.getElementById('exp-rate').value);
            const gold = parseFloat(document.getElementById('gold-rate').value);
            try {
                await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({exp_multiplier: exp, gold_multiplier: gold})
                });
                alert("Multipliers updated successfully!");
                fetchStatus();
            } catch(e) {
                alert("Failed to update config.");
            }
        }

        async function sendBroadcast() {
            const input = document.getElementById('broadcast-msg');
            const msg = input.value;
            if(!msg) return;
            try {
                await fetch('/api/broadcast', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                input.value = '';
                alert("Announcement broadcasted!");
            } catch(e) {
                alert("Failed to broadcast.");
            }
        }

        async function kickPlayer(name) {
            if(!confirm("Are you sure you want to kick " + name + "?")) return;
            try {
                await fetch('/api/players/kick', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                });
                fetchPlayers();
            } catch(e) {
                alert("Failed to kick player.");
            }
        }

        // Warp Modal Controls
        function openWarpModal(name) {
            document.getElementById('warp-player-name').value = name;
            document.getElementById('warp-preset').value = '';
            document.getElementById('warp-modal').style.display = 'flex';
        }
        function onPresetMapChange() {
            const select = document.getElementById('warp-preset');
            const val = select.value;
            if (!val) return;
            const parts = val.split(',');
            document.getElementById('warp-map').value = parts[0];
            document.getElementById('warp-x').value = parts[1];
            document.getElementById('warp-y').value = parts[2];
        }
        function closeWarpModal() {
            document.getElementById('warp-modal').style.display = 'none';
        }
        async function confirmWarp() {
            const name = document.getElementById('warp-player-name').value;
            const map = parseInt(document.getElementById('warp-map').value);
            const x = parseInt(document.getElementById('warp-x').value);
            const y = parseInt(document.getElementById('warp-y').value);
            try {
                await fetch('/api/players/warp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, map_id: map, x: x, y: y})
                });
                closeWarpModal();
                fetchPlayers();
            } catch(e) {
                alert("Failed to teleport player.");
            }
        }

        // Gold Modal Controls
        function openGoldModal(name, currentGold) {
            document.getElementById('gold-player-name').value = name;
            document.getElementById('gold-amt').value = currentGold + 1000;
            document.getElementById('gold-modal').style.display = 'flex';
        }
        function closeGoldModal() {
            document.getElementById('gold-modal').style.display = 'none';
        }
        async function confirmGold() {
            const name = document.getElementById('gold-player-name').value;
            const gold = parseInt(document.getElementById('gold-amt').value);
            try {
                await fetch('/api/players/gold', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, gold: gold})
                });
                closeGoldModal();
                fetchPlayers();
            } catch(e) {
                alert("Failed to set player gold.");
            }
        }

        // Level Modal Controls
        function openLevelModal(name, currentLevel) {
            document.getElementById('level-player-name').value = name;
            document.getElementById('level-val').value = currentLevel;
            document.getElementById('level-modal').style.display = 'flex';
        }
        function closeLevelModal() {
            document.getElementById('level-modal').style.display = 'none';
        }
        async function confirmLevel() {
            const name = document.getElementById('level-player-name').value;
            const level = parseInt(document.getElementById('level-val').value);
            try {
                await fetch('/api/players/level', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, level: level})
                });
                closeLevelModal();
                fetchPlayers();
            } catch(e) {
                alert("Failed to set player level.");
            }
        }

        // Item Modal Controls
        function openItemModal(name) {
            document.getElementById('item-player-name').value = name;
            document.getElementById('item-id-search').value = '27001';
            document.getElementById('item-selected-label').textContent = '27001 - Red Potion';
            document.getElementById('item-amt').value = '1';
            document.getElementById('item-modal').style.display = 'flex';
        }function closeItemModal() {
            document.getElementById('item-modal').style.display = 'none';
        }
        async function confirmItem() {
            const name = document.getElementById('item-player-name').value;
            const val = document.getElementById('item-id-search').value;
            const itemId = parseInt(val.split(' ')[0]);
            if (isNaN(itemId)) { alert('Invalid Item ID'); return; }
            const amount = parseInt(document.getElementById('item-amt').value);
            try {
                const res = await fetch('/api/players/item', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, item_id: itemId, amount: amount})
                });
                const data = await res.json();
                if (data.status === "success") {
                    closeItemModal();
                    alert("Item given successfully!");
                } else {
                    alert("Error: " + data.message);
                }
            } catch(e) {
                alert("Failed to give item.");
            }
        }

        // Pet Modal Controls
        function openPetModal(name) {
            document.getElementById('pet-player-name').value = name;
            document.getElementById('pet-id-search').value = '11058';
            document.getElementById('pet-selected-label').textContent = '11058 - Shasha';
            document.getElementById('pet-lvl').value = '1';
            document.getElementById('pet-modal').style.display = 'flex';
        }function closePetModal() {
            document.getElementById('pet-modal').style.display = 'none';
        }
        async function confirmPet() {
            const name = document.getElementById('pet-player-name').value;
            const val = document.getElementById('pet-id-search').value;
            const petId = parseInt(val.split(' ')[0]);
            if (isNaN(petId)) { alert('Invalid Pet ID'); return; }
            const level = parseInt(document.getElementById('pet-lvl').value);
            try {
                const res = await fetch('/api/players/pet', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, pet_id: petId, level: level})
                });
                const data = await res.json();
                if (data.status === "success") {
                    closePetModal();
                    alert("Pet given successfully!");
                } else {
                    alert("Error: " + data.message);
                }
            } catch(e) {
                alert("Failed to give pet.");
            }
        }

        // ── Player Detail Modal ────────────────────────────────────────────
        let _detailPlayerName = '';
        let _detailData = null;

        async function openDetailModal(name) {
            _detailPlayerName = name;
            document.getElementById('detail-modal-title').textContent = '👤 ' + name + ' — Player Details';
            document.getElementById('detail-modal').style.display = 'flex';
            switchDetailTab('items');
            await refreshDetailData();
        }

        function closeDetailModal() {
            document.getElementById('detail-modal').style.display = 'none';
        }

        function switchDetailTab(tab) {
            document.querySelectorAll('.detail-tab').forEach((t,i) => {
                t.classList.toggle('active', (i===0 && tab==='items') || (i===1 && tab==='pets'));
            });
            document.getElementById('detail-items-section').classList.toggle('active', tab==='items');
            document.getElementById('detail-pets-section').classList.toggle('active', tab==='pets');
        }

        async function refreshDetailData() {
            try {
                const res = await fetch('/api/players/details?name=' + encodeURIComponent(_detailPlayerName));
                if (!res.ok) { alert('Player not found or offline.'); return; }
                _detailData = await res.json();
                renderDetailItems(_detailData.items || []);
                renderDetailPets(_detailData.pets || []);
            } catch(e) { alert('Failed to load player details.'); }
        }

        function renderDetailItems(items) {
            const tbody = document.getElementById('detail-items-body');
            if (!items.length) { tbody.innerHTML = '<tr><td colspan="4" class="empty-msg">No items in inventory.</td></tr>'; return; }
            tbody.innerHTML = items.map((it, i) => `
                <tr>
                    <td>${i+1}</td>
                    <td><span class="badge badge-cyan">${it.item_id}</span></td>
                    <td>${it.amount || 1}</td>
                    <td><button class="btn-xs btn-sm-danger" onclick="adminDeleteItem(${it.slot})">🗑 Delete</button></td>
                </tr>
            `).join('');
        }

        function renderDetailPets(pets) {
            const tbody = document.getElementById('detail-pets-body');
            if (!pets.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty-msg">No pets.</td></tr>'; return; }
            tbody.innerHTML = pets.map((p, i) => `
                <tr>
                    <td>${i+1}</td>
                    <td><span class="badge badge-cyan">${p.pet_id}</span></td>
                    <td><input class="lvl-input" id="pet-lvl-input-${i}" type="number" min="1" max="199" value="${p.level}"> <button class="btn-xs btn-teal" onclick="adminSetPetLevel(${i})">✓</button></td>
                    <td>${p.exp || 0}</td>
                    <td>${p.amity || 100}</td>
                    <td style="font-size:0.78rem;">${p.str||5}/${p.con||5}/${p.agi||5}/${p.int||5}/${p.wis||5}</td>
                    <td><button class="btn-xs btn-sm-danger" onclick="adminDeletePet(${i})">🗑 Delete</button></td>
                </tr>
            `).join('');
        }

        async function adminDeleteItem(slot) {
            if (!confirm(`Delete item at inventory slot ${slot}?`)) return;
            const res = await fetch('/api/players/delete_item', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({name: _detailPlayerName, slot: slot})
            });
            const data = await res.json();
            if (data.status === 'success') { await refreshDetailData(); }
            else alert('Error: ' + data.message);
        }

        async function adminDeletePet(idx) {
            if (!confirm(`Delete pet at slot ${idx+1}?`)) return;
            const res = await fetch('/api/players/delete_pet', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({name: _detailPlayerName, slot: idx+1})
            });
            const data = await res.json();
            if (data.status === 'success') { await refreshDetailData(); }
            else alert('Error: ' + data.message);
        }

        async function adminSetPetLevel(idx) {
            const newLevel = parseInt(document.getElementById(`pet-lvl-input-${idx}`).value);
            if (isNaN(newLevel) || newLevel < 1 || newLevel > 199) { alert('Level must be 1-199.'); return; }
            const res = await fetch('/api/players/pet_level', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({name: _detailPlayerName, slot: idx+1, level: newLevel})
            });
            const data = await res.json();
            if (data.status === 'success') { await refreshDetailData(); alert(`Pet level set to ${newLevel}!`); }
            else alert('Error: ' + data.message);
        }
        // ──────────────────────────────────────────────────────────────────

        function formatUptime(secs) {
            const h = Math.floor(secs / 3600);
            const m = Math.floor((secs % 3600) / 60);
            const s = Math.floor(secs % 60);
            return `${h}h ${m}m ${s}s`;
        }

        async function fetchUsers() {
            try {
                const res = await fetch('/api/users');
                const users = await res.json();
                const tbody = document.getElementById('users-list');
                tbody.innerHTML = '';
                
                users.forEach(user => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${user.id}</td>
                        <td style="font-weight: 600; color: var(--accent-cyan);">${user.username}</td>
                        <td>
                            <button class="btn-danger" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="deleteUser(${user.id}, '${user.username}')">Delete / Sil</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch(e) {
                console.error("Failed to fetch users", e);
            }
        }

        async function deleteUser(userId, username) {
            if(!confirm(`Are you sure you want to delete the user "${username}" (ID: ${userId})? This will also delete all their characters!`)) {
                return;
            }
            try {
                const res = await fetch('/api/users/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId})
                });
                const data = await res.json();
                if(data.status === 'success') {
                    fetchUsers();
                    fetchPlayers();
                } else {
                    alert("Error: " + data.message);
                }
            } catch(e) {
                alert("Failed to delete user.");
            }
        }

        // Auto-refresh loops
        fetchStatus();
        fetchPlayers();
        fetchLogs();
        fetchUsers();
        setInterval(fetchStatus, 3000);
        setInterval(fetchPlayers, 2000);
        setInterval(fetchLogs, 1000);
        setInterval(fetchUsers, 5000);

        // Database Browser / Editor JS Logic
        let dbCurrentTable = '';
        let dbColumns = [];
        let dbPrimaryKey = '';
        let dbCurrentPage = 1;
        let dbPageLimit = 20;
        let dbSearch = '';
        let dbEditMode = 'add';
        let dbEditRowData = null;
        let dbTotalRows = 0;
        let dbRows = [];

        async function loadDbTables() {
            try {
                const res = await fetch('/api/db/tables');
                const tables = await res.json();
                const select = document.getElementById('db-table-select');
                select.innerHTML = '';
                tables.forEach(table => {
                    const option = document.createElement('option');
                    option.value = table;
                    option.textContent = table;
                    select.appendChild(option);
                });
                if (tables.length > 0) {
                    dbCurrentTable = tables[0];
                    loadDbTableData();
                }
            } catch (e) {
                console.error("Failed to load DB tables", e);
            }
        }

        async function loadDbTableData() {
            if (!dbCurrentTable) return;
            try {
                const url = `/api/db/query?table=${dbCurrentTable}&page=${dbCurrentPage}&limit=${dbPageLimit}&search=${encodeURIComponent(dbSearch)}`;
                const res = await fetch(url);
                const data = await res.json();
                
                dbColumns = data.columns || [];
                dbPrimaryKey = data.pk || '';
                dbRows = data.rows || [];
                dbTotalRows = data.total || 0;

                // Render Header
                const thead = document.getElementById('db-table-header');
                thead.innerHTML = '';
                const headerTr = document.createElement('tr');
                dbColumns.forEach(col => {
                    const th = document.createElement('th');
                    th.textContent = col;
                    headerTr.appendChild(th);
                });
                const thActions = document.createElement('th');
                thActions.textContent = 'Actions';
                headerTr.appendChild(thActions);
                thead.appendChild(headerTr);

                // Render Body
                const tbody = document.getElementById('db-table-body');
                tbody.innerHTML = '';
                if (dbRows.length === 0) {
                    const tr = document.createElement('tr');
                    const td = document.createElement('td');
                    td.colSpan = dbColumns.length + 1;
                    td.textContent = 'No records found';
                    td.style.textAlign = 'center';
                    tr.appendChild(td);
                    tbody.appendChild(tr);
                } else {
                    dbRows.forEach((row, idx) => {
                        const tr = document.createElement('tr');
                        dbColumns.forEach(col => {
                            const td = document.createElement('td');
                            td.textContent = row[col] !== null ? row[col] : 'NULL';
                            tr.appendChild(td);
                        });
                        const tdActions = document.createElement('td');
                        tdActions.innerHTML = `
                            <button onclick="openEditRowModal(${idx})" class="btn-success" style="padding: 0.2rem 0.5rem; font-size: 0.8rem; margin-right: 0.25rem;">Edit</button>
                            <button onclick="deleteDbRow(${idx})" class="btn-danger" style="padding: 0.2rem 0.5rem; font-size: 0.8rem;">Delete</button>
                        `;
                        tr.appendChild(tdActions);
                        tbody.appendChild(tr);
                    });
                }

                // Update Pagination Info
                const start = dbTotalRows === 0 ? 0 : (dbCurrentPage - 1) * dbPageLimit + 1;
                const end = Math.min(dbCurrentPage * dbPageLimit, dbTotalRows);
                document.getElementById('db-pagination-info').textContent = `Showing ${start} to ${end} of ${dbTotalRows} entries`;
                
                document.getElementById('db-prev-btn').disabled = dbCurrentPage <= 1;
                document.getElementById('db-next-btn').disabled = end >= dbTotalRows;
            } catch (e) {
                console.error("Failed to load table data", e);
            }
        }

        function changeTable() {
            dbCurrentTable = document.getElementById('db-table-select').value;
            dbCurrentPage = 1;
            dbSearch = '';
            document.getElementById('db-search-input').value = '';
            loadDbTableData();
        }

        let dbSearchTimeout;
        function searchTable() {
            clearTimeout(dbSearchTimeout);
            dbSearchTimeout = setTimeout(() => {
                dbSearch = document.getElementById('db-search-input').value.trim();
                dbCurrentPage = 1;
                loadDbTableData();
            }, 300);
        }

        function prevPage() {
            if (dbCurrentPage > 1) {
                dbCurrentPage--;
                loadDbTableData();
            }
        }

        function nextPage() {
            const end = dbCurrentPage * dbPageLimit;
            if (end < dbTotalRows) {
                dbCurrentPage++;
                loadDbTableData();
            }
        }

        function openAddRowModal() {
            dbEditMode = 'add';
            dbEditRowData = null;
            document.getElementById('db-edit-modal-title').textContent = `Add New Row to ${dbCurrentTable}`;
            const form = document.getElementById('db-edit-form');
            form.innerHTML = '';
            
            dbColumns.forEach(col => {
                const group = document.createElement('div');
                group.className = 'form-group';
                
                const label = document.createElement('label');
                label.textContent = col;
                
                const input = document.createElement('input');
                input.type = 'text';
                input.id = `db-input-${col}`;
                input.placeholder = col === dbPrimaryKey ? 'Autogenerated if integer' : `Enter ${col}`;
                
                group.appendChild(label);
                group.appendChild(input);
                form.appendChild(group);
            });
            
            document.getElementById('db-edit-modal').style.display = 'flex';
        }

        function openEditRowModal(rowIndex) {
            dbEditMode = 'edit';
            dbEditRowData = dbRows[rowIndex];
            document.getElementById('db-edit-modal-title').textContent = `Edit Row in ${dbCurrentTable}`;
            const form = document.getElementById('db-edit-form');
            form.innerHTML = '';
            
            dbColumns.forEach(col => {
                const group = document.createElement('div');
                group.className = 'form-group';
                
                const label = document.createElement('label');
                label.textContent = col;
                
                const input = document.createElement('input');
                input.type = 'text';
                input.id = `db-input-${col}`;
                input.value = dbEditRowData[col] !== null ? dbEditRowData[col] : '';
                if (col === dbPrimaryKey) {
                    input.disabled = true;
                    input.style.opacity = '0.5';
                }
                
                group.appendChild(label);
                group.appendChild(input);
                form.appendChild(group);
            });
            
            document.getElementById('db-edit-modal').style.display = 'flex';
        }

        function closeDbEditModal() {
            document.getElementById('db-edit-modal').style.display = 'none';
        }

        async function saveDbRow() {
            const rowData = {};
            dbColumns.forEach(col => {
                const val = document.getElementById(`db-input-${col}`).value.trim();
                if (dbEditMode === 'add' && col === dbPrimaryKey && val === '') {
                    return;
                }
                rowData[col] = val === '' ? null : val;
            });

            try {
                let url = '';
                let payload = {};
                if (dbEditMode === 'edit') {
                    url = '/api/db/update';
                    payload = {
                        table: dbCurrentTable,
                        pk_col: dbPrimaryKey,
                        pk_val: dbEditRowData[dbPrimaryKey],
                        row_data: rowData
                    };
                } else {
                    url = '/api/db/insert';
                    payload = {
                        table: dbCurrentTable,
                        row_data: rowData
                    };
                }

                const res = await fetch(url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    closeDbEditModal();
                    loadDbTableData();
                } else {
                    alert("Error: " + data.message);
                }
            } catch (e) {
                alert("Failed to save database row.");
            }
        }

        async function deleteDbRow(rowIndex) {
            const row = dbRows[rowIndex];
            const pkVal = row[dbPrimaryKey];
            if (!confirm(`Are you sure you want to delete this row from ${dbCurrentTable} where ${dbPrimaryKey} = ${pkVal}?`)) {
                return;
            }
            try {
                const res = await fetch('/api/db/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        table: dbCurrentTable,
                        pk_col: dbPrimaryKey,
                        pk_val: pkVal
                    })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    loadDbTableData();
                } else {
                    alert("Error: " + data.message);
                }
            } catch (e) {
                alert("Failed to delete database row.");
            }
        }

        // Initialize DB tables dropdown & Search lists
        loadDbTables();
        fetchSearchLists();

        // Searchable Custom Dropdown logic
        let allItems = [];
        let allPets = [];
        let activeDropdownType = null;

        async function fetchSearchLists() {
            try {
                const res = await fetch('/api/search_lists?_t=' + Date.now());
                const data = await res.json();
                allItems = data.items || [];
                allPets = data.monsters || [];
                
                // Initialize default displays
                renderDropdownOptions('item', allItems);
                renderDropdownOptions('pet', allPets);
            } catch(e) {
                console.error("Failed to load search lists", e);
            }
        }

        function renderDropdownOptions(type, list) {
            const listContainer = document.getElementById(`${type}-dropdown-list`);
            if(!listContainer) return;
            
            let html = '';
            // Limit rendered items to 200 for performance
            const limit = 200;
            const itemsToRender = list.slice(0, limit);
            
            if(itemsToRender.length === 0) {
                html = '<div class="empty-msg" style="padding: 1rem;">No matches found</div>';
            } else {
                itemsToRender.forEach(item => {
                    const isSelected = document.getElementById(`${type}-id-search`).value == item.id;
                    const cleanName = item.name.replace(/"/g, '&quot;');
                    html += `
                        <div class="dropdown-option-item ${isSelected ? 'selected' : ''}" onclick="selectSearchableOption('${type}', '${item.id}', '${cleanName}')">
                            <span>${cleanName}</span>
                            <span class="option-id">ID: ${item.id}</span>
                        </div>
                    `;
                });
            }
            listContainer.innerHTML = html;
        }

        function toggleSearchableDropdown(type) {
            const menu = document.getElementById(`${type}-dropdown-menu`);
            const selectBox = menu.previousElementSibling;
            
            // Close other dropdowns if open
            if(activeDropdownType && activeDropdownType !== type) {
                closeSearchableDropdown(activeDropdownType);
            }
            
            if(menu.style.display === 'flex') {
                closeSearchableDropdown(type);
            } else {
                menu.style.display = 'flex';
                selectBox.classList.add('active');
                activeDropdownType = type;
                
                // Focus the search input automatically
                setTimeout(() => {
                    const searchInput = document.getElementById(`${type}-dropdown-search`);
                    if(searchInput) {
                        searchInput.value = '';
                        searchInput.focus();
                        // Reset filter to show all
                        if(type === 'item') {
                            renderDropdownOptions('item', allItems);
                        } else {
                            renderDropdownOptions('pet', allPets);
                        }
                    }
                }, 50);
            }
        }

        function closeSearchableDropdown(type) {
            const menu = document.getElementById(`${type}-dropdown-menu`);
            if(menu) {
                menu.style.display = 'none';
                menu.previousElementSibling.classList.remove('active');
            }
            if(activeDropdownType === type) {
                activeDropdownType = null;
            }
        }

        function selectSearchableOption(type, id, name) {
            document.getElementById(`${type}-id-search`).value = id;
            document.getElementById(`${type}-selected-label`).textContent = `${id} - ${name}`;
            closeSearchableDropdown(type);
        }

        function onFilterSearchableDropdown(type, query) {
            const list = type === 'item' ? allItems : allPets;
            const q = query.toLowerCase().trim();
            
            let filtered = list;
            if(q) {
                filtered = list.filter(item => 
                    item.id.toString().includes(q) || 
                    item.name.toLowerCase().includes(q)
                );
            }
            renderDropdownOptions(type, filtered);
        }

        // Close dropdowns when clicking outside
        document.addEventListener('click', function(event) {
            if(activeDropdownType) {
                const container = document.getElementById(`${activeDropdownType}-searchable-dropdown`);
                if(container && !container.contains(event.target)) {
                    closeSearchableDropdown(activeDropdownType);
                }
            }
        });
    </script>
</body>
</html>
"""

class WebAdminServer:
    def __init__(self, game_server):
        self.game_server = game_server
        self.start_time = time.time()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/players', self.handle_players)
        self.app.router.add_post('/api/config', self.handle_update_config)
        self.app.router.add_post('/api/broadcast', self.handle_broadcast)
        self.app.router.add_post('/api/players/kick', self.handle_kick)
        self.app.router.add_post('/api/players/warp', self.handle_warp)
        self.app.router.add_post('/api/players/gold', self.handle_gold)
        self.app.router.add_post('/api/players/level', self.handle_level)
        self.app.router.add_post('/api/players/item', self.handle_give_item)
        self.app.router.add_post('/api/players/pet', self.handle_give_pet)
        self.app.router.add_get('/api/search_lists', self.handle_search_lists)
        self.app.router.add_get('/api/logs', self.handle_logs)
        self.app.router.add_get('/api/users', self.handle_get_users)
        self.app.router.add_post('/api/users/delete', self.handle_delete_user)
        self.app.router.add_get('/api/players/details', self.handle_player_details)
        self.app.router.add_post('/api/players/delete_item', self.handle_delete_item)
        self.app.router.add_post('/api/players/delete_pet', self.handle_delete_pet)
        self.app.router.add_post('/api/players/pet_level', self.handle_pet_level)
        self.app.router.add_get('/api/db/tables', self.handle_db_tables)
        self.app.router.add_get('/api/db/query', self.handle_db_query)
        self.app.router.add_post('/api/db/update', self.handle_db_update)
        self.app.router.add_post('/api/db/insert', self.handle_db_insert)
        self.app.router.add_post('/api/db/delete', self.handle_db_delete)

    async def handle_index(self, request):
        return web.Response(text=HTML_CONTENT, content_type='text/html')

    async def handle_status(self, request):
        status = {
            "uptime": time.time() - self.start_time,
            "online_count": len(self.game_server.active_sessions),
            "exp_multiplier": self.game_server.exp_multiplier,
            "gold_multiplier": self.game_server.gold_multiplier,
            "encounter_multiplier": self.game_server.encounter_multiplier
        }
        return web.json_response(status)

    async def handle_players(self, request):
        players = []
        # Create a copy to prevent concurrent modification exceptions
        for session in list(self.game_server.active_sessions):
            players.append({
                "name": session.char_name or "Slot Select Screen",
                "level": session.level,
                "gold": session.gold,
                "map_id": session.map_id,
                "x": session.x,
                "y": session.y,
                "ip": session.ip
            })
        return web.json_response(players)

    async def handle_update_config(self, request):
        try:
            data = await request.json()
            if 'exp_multiplier' in data:
                self.game_server.exp_multiplier = float(data['exp_multiplier'])
            if 'gold_multiplier' in data:
                self.game_server.gold_multiplier = float(data['gold_multiplier'])
            logger.info(f"[WebAdmin] Configuration updated: EXP rate={self.game_server.exp_multiplier}x, Gold rate={self.game_server.gold_multiplier}x")
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def handle_broadcast(self, request):
        try:
            from server.network import PacketWriter
            data = await request.json()
            message = data.get('message', '')
            if message:
                # 1. System message packet AC 23 Sub 57 Type 0
                pkt_sys = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(message)
                # 2. Loudspeaker scrolling announcement AC 70 Sub 1 channel 23
                pkt_speaker = PacketWriter().write_8(70).write_8(1).write_8(23).write_string(message).write_16(194).write_8(0)
                # 3. Direct chat log delivery (AC 2 Sub 2 from SYSTEM)
                pkt_chat = PacketWriter().write_8(2).write_8(2).write_32(0).write_string_n(f"[SYSTEM]: {message}")
                
                for session in list(self.game_server.active_sessions):
                    await session.send_packet(pkt_sys)
                    await session.send_packet(pkt_speaker)
                    await session.send_packet(pkt_chat)
                logger.info(f"[WebAdmin] Broadcasted global message: '{message}'")
                return web.json_response({"status": "success"})
            return web.json_response({"status": "error", "message": "Empty message"}, status=400)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_kick(self, request):
        try:
            data = await request.json()
            name = data.get('name', '')
            for session in list(self.game_server.active_sessions):
                if session.char_name == name:
                    session.writer.close()
                    logger.info(f"[WebAdmin] Kicked player: {name}")
                    return web.json_response({"status": "success"})
            return web.json_response({"status": "error", "message": "Player not found"}, status=404)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_warp(self, request):
        try:
            data = await request.json()
            name = data.get('name')
            map_id = int(data.get('map_id'))
            x = int(data.get('x'))
            y = int(data.get('y'))
            
            for session in list(self.game_server.active_sessions):
                if session.char_name == name:
                    await self.game_server.warp_player(session, map_id, x, y)
                    logger.info(f"[WebAdmin] Teleported player {name} to {map_id} ({x},{y})")
                    return web.json_response({"status": "success"})
            return web.json_response({"status": "error", "message": "Player not found"}, status=404)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_gold(self, request):
        try:
            from server.network import PacketWriter
            data = await request.json()
            name = data.get('name')
            gold = int(data.get('gold'))
            
            for session in list(self.game_server.active_sessions):
                if session.char_name == name:
                    session.gold = max(0, gold)
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    self.game_server.save_player_to_db(session)
                    logger.info(f"[WebAdmin] Set gold of {name} to {gold}")
                    return web.json_response({"status": "success"})
            return web.json_response({"status": "error", "message": "Player not found"}, status=404)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_level(self, request):
        try:
            from server.network import PacketWriter
            data = await request.json()
            name = data.get('name')
            level = int(data.get('level'))
            level = max(1, min(199, level))
            
            for session in list(self.game_server.active_sessions):
                if session.char_name == name:
                    session.exp = self.game_server.get_cumulative_exp_for_level(level, session.reborn)
                    session.level = level
                    session.update_max_hp_sp()
                    session.hp = session.max_hp
                    session.sp = session.max_sp
                    
                    await self.game_server.send_stats_update(session)
                    await self.game_server.send_sidebar_stats(session)
                    self.game_server.save_player_to_db(session)
                    
                    logger.info(f"[WebAdmin] Set level of {name} to {level}")
                    return web.json_response({"status": "success"})
            return web.json_response({"status": "error", "message": "Player not found"}, status=404)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_give_item(self, request):
        try:
            from server.network import PacketWriter
            from server.gameserver import add_item_to_inventory
            data = await request.json()
            name = data.get('name')
            item_id = int(data.get('item_id'))
            amount = int(data.get('amount', 1))
            
            for session in list(self.game_server.active_sessions):
                if session.char_name == name:
                    if len(session.inventory) >= 50:
                        return web.json_response({"status": "error", "message": "Inventory is full (50/50)"}, status=400)
                    
                    success = add_item_to_inventory(session, item_id, amount=amount)
                    if success:
                        self.game_server.save_player_to_db(session)
                        
                        # Dynamic visual update: [23, 6, item_id (uint16), amount (uint8), 26 bytes of zero]
                        item_pkt = PacketWriter()
                        item_pkt.write_8(23).write_8(6).write_16(item_id).write_8(amount).write_bytes(bytes(26))
                        await session.send_packet(item_pkt)
                        
                        # System chat message confirmation: [23, 57, 0]
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Admin gave you Item {item_id} (x{amount})."
                        )
                        await session.send_packet(sys_msg)
                        
                        logger.info(f"[WebAdmin] Gave item {item_id} (x{amount}) to {name}")
                        return web.json_response({"status": "success"})
                    else:
                        return web.json_response({"status": "error", "message": "Failed to add item to inventory"}, status=500)
            return web.json_response({"status": "error", "message": "Player not found"}, status=404)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_give_pet(self, request):
        try:
            from server.network import PacketWriter
            data = await request.json()
            name = data.get('name')
            pet_id = int(data.get('pet_id'))
            level = int(data.get('level', 1))
            
            for session in list(self.game_server.active_sessions):
                if session.char_name == name:
                    # Calculate pet stats with WLO formulas
                    lvl = max(1, min(199, level))
                    base_con = 5 + lvl // 3
                    base_wis = 5 + lvl // 3
                    base_str = 5 + lvl // 3
                    base_agi = 5 + lvl // 3
                    base_int = 5 + lvl // 3
                    max_hp = int(round(((lvl ** 0.35) * base_con * 2) + (lvl * 1) + (base_con * 2) + 180))
                    max_sp = int(round(((lvl ** 0.3) * base_wis * 3.2) + (lvl * 1) + (base_wis * 2) + 94))
                    
                    # Add pet dict to session.pets with full stats
                    pet_data = {
                        "pet_id": pet_id,
                        "level": lvl,
                        "exp": self.game_server.get_cumulative_exp_for_level(lvl, False),
                        "amity": 100,
                        "reborn": 0,
                        "potential": 0,
                        "str": base_str,
                        "con": base_con,
                        "int": base_int,
                        "wis": base_wis,
                        "agi": base_agi,
                        "hp": max_hp,
                        "sp": max_sp,
                        "skills": []
                    }
                    session.pets.append(pet_data)
                    self.game_server.save_player_to_db(session)
                    
                    # Companion dynamics addition packet 15, 1
                    pkt = PacketWriter()
                    pkt.write_8(15).write_8(1)
                    pkt.write_32(session.char_id)
                    pkt.write_32(pet_id)
                    pkt.write_8(lvl)
                    pkt.write_32(0) # EXP
                    pkt.write_8(1).write_32(0) # Skill 1 Grade, EXP
                    pkt.write_8(1).write_32(0) # Skill 2 Grade, EXP
                    pkt.write_8(1).write_32(0) # Skill 3 Grade, EXP
                    pkt.write_8(1).write_16(0).write_16(0).write_8(0) # Skill 4 + Padding
                    
                    await session.send_packet(pkt)
                    
                    # Refresh the client pet companion list UI
                    await self.game_server.send_pet_list(session)
                    
                    # System chat message confirmation
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Admin gave you Pet NPC {pet_id} (Lv {lvl})."
                    )
                    await session.send_packet(sys_msg)
                    
                    logger.info(f"[WebAdmin] Gave pet NPC {pet_id} (Lv {lvl}) to {name}")
                    return web.json_response({"status": "success"})
            return web.json_response({"status": "error", "message": "Player not found"}, status=404)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_logs(self, request):
        return web.json_response(list(recent_logs))

    async def handle_player_details(self, request):
        """Returns inventory items and pets for a named online player."""
        try:
            name = request.rel_url.query.get('name', '').strip()
            session = next((s for s in self.game_server.active_sessions if s.char_name == name), None)
            if not session:
                return web.json_response({'status': 'error', 'message': 'Player not found or offline'}, status=404)
            items = [
                {'slot': it.get('slot', 0), 'item_id': it.get('item_id', 0), 'amount': it.get('amount', 1)}
                for it in session.inventory
            ]
            pets = [
                {
                    'pet_id': p.get('pet_id', 0), 'level': p.get('level', 1), 'exp': p.get('exp', 0),
                    'amity': p.get('amity', 100), 'str': p.get('str', 5), 'con': p.get('con', 5),
                    'agi': p.get('agi', 5), 'int': p.get('int', 5), 'wis': p.get('wis', 5),
                    'reborn': p.get('reborn', 0), 'potential': p.get('potential', 0)
                }
                for p in session.pets
            ]
            return web.json_response({'items': items, 'pets': pets})
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)

    async def handle_delete_item(self, request):
        """Removes an item at the given inventory slot for an online player."""
        try:
            data = await request.json()
            name = data.get('name', '').strip()
            slot = int(data.get('slot', 0))
            session = next((s for s in self.game_server.active_sessions if s.char_name == name), None)
            if not session:
                return web.json_response({'status': 'error', 'message': 'Player not found'}, status=404)
            before = len(session.inventory)
            session.inventory = [it for it in session.inventory if it.get('slot') != slot]
            if len(session.inventory) == before:
                return web.json_response({'status': 'error', 'message': f'No item found at slot {slot}'}, status=404)
            self.game_server.save_player_to_db(session)
            # Notify client to clear the slot visually
            from server.network import PacketWriter
            slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(slot).write_8(0)
            await session.send_packet(slot_pkt)
            logger.info(f"[WebAdmin] Deleted item at slot {slot} from {name}")
            return web.json_response({'status': 'success'})
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)

    async def handle_delete_pet(self, request):
        """Removes a pet at the given slot (1-based) for an online player."""
        try:
            data = await request.json()
            name = data.get('name', '').strip()
            slot = int(data.get('slot', 0))
            session = next((s for s in self.game_server.active_sessions if s.char_name == name), None)
            if not session:
                return web.json_response({'status': 'error', 'message': 'Player not found'}, status=404)
            if slot < 1 or slot > len(session.pets):
                return web.json_response({'status': 'error', 'message': 'Invalid pet slot'}, status=400)
            session.pets.pop(slot - 1)
            self.game_server.save_player_to_db(session)
            await self.game_server.send_pet_list(session)
            logger.info(f"[WebAdmin] Deleted pet at slot {slot} from {name}")
            return web.json_response({'status': 'success'})
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)

    async def handle_pet_level(self, request):
        """Sets the level (and recalculates stats) of a pet at the given slot for an online player."""
        try:
            data = await request.json()
            name = data.get('name', '').strip()
            slot = int(data.get('slot', 0))
            new_level = max(1, min(199, int(data.get('level', 1))))
            session = next((s for s in self.game_server.active_sessions if s.char_name == name), None)
            if not session:
                return web.json_response({'status': 'error', 'message': 'Player not found'}, status=404)
            if slot < 1 or slot > len(session.pets):
                return web.json_response({'status': 'error', 'message': 'Invalid pet slot'}, status=400)
            pet = session.pets[slot - 1]
            pet['level'] = new_level
            # Recalculate base stats proportional to new level
            pet['str'] = 5 + new_level // 3
            pet['con'] = 5 + new_level // 3
            pet['agi'] = 5 + new_level // 3
            pet['int'] = 5 + new_level // 3
            pet['wis'] = 5 + new_level // 3
            con = pet['con']; wis = pet['wis']
            pet['hp'] = int(round(((new_level ** 0.35) * con * 2) + new_level + (con * 2) + 180))
            pet['sp'] = int(round(((new_level ** 0.3) * wis * 3.2) + new_level + (wis * 2) + 94))
            pet['exp'] = self.game_server.get_cumulative_exp_for_level(new_level, False)
            self.game_server.save_player_to_db(session)
            await self.game_server.send_pet_list(session)
            logger.info(f"[WebAdmin] Set pet slot {slot} level={new_level} for {name}")
            return web.json_response({'status': 'success'})
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)

    async def handle_get_users(self, request):
        try:
            users = self.game_server.db.get_all_users()
            return web.json_response(users)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_delete_user(self, request):
        try:
            data = await request.json()
            user_id = int(data.get('user_id'))
            
            # Kick online player sessions belonging to this user
            for session in list(self.game_server.active_sessions):
                if session.user_id == user_id:
                    session.writer.close()
                    logger.info(f"[WebAdmin] Kicked player {session.char_name} because user account {user_id} was deleted.")
            
            self.game_server.db.delete_user(user_id)
            logger.info(f"[WebAdmin] Deleted user account ID {user_id}")
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_db_tables(self, request):
        try:
            import sqlite3
            conn = sqlite3.connect(self.game_server.static_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            tables = [r[0] for r in cursor.fetchall()]
            conn.close()
            tables.append("drop_table")
            return web.json_response(tables)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_db_query(self, request):
        try:
            import sqlite3
            table = request.rel_url.query.get('table', '').strip()
            page = int(request.rel_url.query.get('page', 1))
            limit = int(request.rel_url.query.get('limit', 20))
            search = request.rel_url.query.get('search', '').strip()
            
            if not table or ';' in table or ' ' in table:
                return web.json_response({"status": "error", "message": "Invalid table name"}, status=400)
                
            offset = (page - 1) * limit
            
            if table == "drop_table":
                rules = []
                rule_idx = 0
                
                mon_names = {}
                try:
                    import sqlite3
                    conn_npc = sqlite3.connect(self.game_server.static_db_path)
                    conn_npc.row_factory = sqlite3.Row
                    cursor_npc = conn_npc.cursor()
                    cursor_npc.execute("SELECT id, name FROM npc_data")
                    for r_npc in cursor_npc.fetchall():
                        m_id = str(r_npc["id"])
                        m_name = r_npc["name"]
                        if isinstance(m_name, str):
                            m_name = m_name.split('\x00')[0].strip()
                        elif isinstance(m_name, bytes):
                            m_name = m_name.split(b'\x00')[0].decode('utf-8', 'ignore').strip()
                        mon_names[m_id] = m_name
                    conn_npc.close()
                except Exception as e:
                    logger.error(f"Failed to load npc names: {e}")

                item_names = {}
                try:
                    import json, os
                    item_names_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "items.json")
                    if os.path.exists(item_names_path):
                        with open(item_names_path, 'r', encoding='utf-8') as f:
                            item_names = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load item names: {e}")

                for mon_id, items in self.game_server.drop_tables.items():
                    m_name = mon_names.get(str(mon_id), "Unknown")
                    for item in items:
                        i_id = str(item["item_id"])
                        i_name = item_names.get(i_id, "Unknown")
                        rules.append({
                            "id": rule_idx,
                            "monster_id": mon_id,
                            "monster_name": m_name,
                            "item_id": item["item_id"],
                            "item_name": i_name,
                            "chance": item["chance"],
                            "amount": item["amount"]
                        })
                        rule_idx += 1

                if search:
                    search_lower = search.lower()
                    rules = [
                        r for r in rules
                        if search_lower in str(r["monster_id"]).lower() or search_lower in str(r["item_id"]).lower() or search_lower in str(r["monster_name"]).lower() or search_lower in str(r.get("item_name", "")).lower()
                    ]

                total = len(rules)
                paginated_rules = rules[offset:offset+limit]

                return web.json_response({
                    "columns": ["id", "monster_id", "monster_name", "item_id", "item_name", "chance", "amount"],
                    "pk": "id",
                    "rows": paginated_rules,
                    "total": total,
                    "page": page,
                    "limit": limit
                })
            
            conn = sqlite3.connect(self.game_server.static_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(f"PRAGMA table_info({table})")
            cols_info = cursor.fetchall()
            columns = [c['name'] for c in cols_info]
            pk_col = next((c['name'] for c in cols_info if c['pk'] == 1), None)
            if not pk_col and columns:
                pk_col = columns[0]
                
            where_clause = ""
            params = []
            if search and columns:
                clauses = []
                for col in columns:
                    clauses.append(f"{col} LIKE ?")
                    params.append(f"%{search}%")
                where_clause = " WHERE " + " OR ".join(clauses)
                
            cursor.execute(f"SELECT COUNT(*) FROM {table}{where_clause}", params)
            total = cursor.fetchone()[0]
            
            query = f"SELECT * FROM {table}{where_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, params + [limit, offset])
            rows = []
            for r in cursor.fetchall():
                row_dict = {}
                for col in columns:
                    val = r[col]
                    if isinstance(val, str):
                        val = val.split('\x00')[0]
                    row_dict[col] = val
                rows.append(row_dict)
                
            conn.close()
            return web.json_response({
                "columns": columns,
                "pk": pk_col,
                "rows": rows,
                "total": total,
                "page": page,
                "limit": limit
            })
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_db_update(self, request):
        try:
            import sqlite3, json
            data = await request.json()
            table = data.get('table', '').strip()
            pk_col = data.get('pk_col', '').strip()
            pk_val = data.get('pk_val')
            row_data = data.get('row_data', {})
            
            if not table or ';' in table or ' ' in table:
                return web.json_response({"status": "error", "message": "Invalid table name"}, status=400)
            if not pk_col or ';' in pk_col or ' ' in pk_col:
                return web.json_response({"status": "error", "message": "Invalid PK column"}, status=400)
                
            if table == "drop_table":
                target_idx = int(pk_val)
                rules = []
                for mon_id, items in self.game_server.drop_tables.items():
                    for item in items:
                        rules.append((mon_id, item))
                
                if target_idx < 0 or target_idx >= len(rules):
                    return web.json_response({"status": "error", "message": "Rule index out of range"}, status=404)

                old_mon_id, target_item = rules[target_idx]
                
                val_mon_id = row_data.get("monster_id")
                new_mon_id = str(val_mon_id if val_mon_id is not None else old_mon_id).strip()
                
                val_item_id = row_data.get("item_id")
                new_item_id = int(val_item_id if val_item_id is not None else target_item["item_id"])
                
                val_chance = row_data.get("chance")
                chance_val = val_chance if val_chance is not None else target_item["chance"]
                if isinstance(chance_val, str):
                    chance_val = chance_val.replace(',', '.')
                new_chance = float(chance_val)
                
                val_amount = row_data.get("amount")
                new_amount = int(val_amount if val_amount is not None else target_item["amount"])

                self.game_server.drop_tables[old_mon_id].remove(target_item)
                if not self.game_server.drop_tables[old_mon_id]:
                    del self.game_server.drop_tables[old_mon_id]

                if new_mon_id not in self.game_server.drop_tables:
                    self.game_server.drop_tables[new_mon_id] = []
                self.game_server.drop_tables[new_mon_id].append({
                    "item_id": new_item_id,
                    "chance": new_chance,
                    "amount": new_amount
                })

                json_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "drop_table.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(self.game_server.drop_tables, f, indent=4, ensure_ascii=False)

                logger.info(f"[WebAdmin] Updated drop_table rule at index {target_idx}")
                return web.json_response({"status": "success"})

            conn = sqlite3.connect(self.game_server.static_db_path)
            cursor = conn.cursor()
            
            set_clauses = []
            params = []
            for col, val in row_data.items():
                if col == pk_col:
                    continue
                set_clauses.append(f"{col} = ?")
                params.append(val)
                
            query = f"UPDATE {table} SET " + ", ".join(set_clauses) + f" WHERE {pk_col} = ?"
            params.append(pk_val)
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            logger.info(f"[WebAdmin] Updated row in {table} where {pk_col}={pk_val}")
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_db_insert(self, request):
        try:
            import sqlite3, json
            data = await request.json()
            table = data.get('table', '').strip()
            row_data = data.get('row_data', {})
            
            if not table or ';' in table or ' ' in table:
                return web.json_response({"status": "error", "message": "Invalid table name"}, status=400)
                
            if table == "drop_table":
                val_mon_id = row_data.get("monster_id")
                mon_id = str(val_mon_id if val_mon_id is not None else "default").strip()
                
                val_item_id = row_data.get("item_id")
                item_id = int(val_item_id if val_item_id is not None else 0)
                
                val_chance = row_data.get("chance")
                chance_val = val_chance if val_chance is not None else 0.0
                if isinstance(chance_val, str):
                    chance_val = chance_val.replace(',', '.')
                chance = float(chance_val)
                
                val_amount = row_data.get("amount")
                amount = int(val_amount if val_amount is not None else 1)

                if mon_id not in self.game_server.drop_tables:
                    self.game_server.drop_tables[mon_id] = []
                self.game_server.drop_tables[mon_id].append({
                    "item_id": item_id,
                    "chance": chance,
                    "amount": amount
                })

                json_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "drop_table.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(self.game_server.drop_tables, f, indent=4, ensure_ascii=False)

                logger.info(f"[WebAdmin] Inserted new drop_table rule for monster {mon_id}")
                return web.json_response({"status": "success"})

            conn = sqlite3.connect(self.game_server.static_db_path)
            cursor = conn.cursor()
            
            columns = list(row_data.keys())
            placeholders = ["?"] * len(columns)
            params = list(row_data.values())
            
            query = f"INSERT INTO {table} (" + ", ".join(columns) + ") VALUES (" + ", ".join(placeholders) + ")"
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            logger.info(f"[WebAdmin] Inserted new row into {table}")
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_db_delete(self, request):
        try:
            import sqlite3, json
            data = await request.json()
            table = data.get('table', '').strip()
            pk_col = data.get('pk_col', '').strip()
            pk_val = data.get('pk_val')
            
            if not table or ';' in table or ' ' in table:
                return web.json_response({"status": "error", "message": "Invalid table name"}, status=400)
            if not pk_col or ';' in pk_col or ' ' in pk_col:
                return web.json_response({"status": "error", "message": "Invalid PK column"}, status=400)
                
            if table == "drop_table":
                target_idx = int(pk_val)
                rules = []
                for mon_id, items in self.game_server.drop_tables.items():
                    for item in items:
                        rules.append((mon_id, item))
                
                if target_idx < 0 or target_idx >= len(rules):
                    return web.json_response({"status": "error", "message": "Rule index out of range"}, status=404)

                mon_id, target_item = rules[target_idx]
                self.game_server.drop_tables[mon_id].remove(target_item)
                if not self.game_server.drop_tables[mon_id]:
                    del self.game_server.drop_tables[mon_id]

                json_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "drop_table.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(self.game_server.drop_tables, f, indent=4, ensure_ascii=False)

                logger.info(f"[WebAdmin] Deleted drop_table rule at index {target_idx}")
                return web.json_response({"status": "success"})

            conn = sqlite3.connect(self.game_server.static_db_path)
            cursor = conn.cursor()
            
            query = f"DELETE FROM {table} WHERE {pk_col} = ?"
            cursor.execute(query, (pk_val,))
            conn.commit()
            conn.close()
            logger.info(f"[WebAdmin] Deleted row from {table} where {pk_col}={pk_val}")
            return web.json_response({"status": "success"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def start(self, host="0.0.0.0", port=8080):
        runner = web.AppRunner(self.app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        display_host = "127.0.0.1" if host == "0.0.0.0" else host
        logger.info(f"Web Administration Panel successfully started on http://{display_host}:{port}")

    async def handle_search_lists(self, request):
        monsters = []
        try:
            import json, os
            npc_names_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "npc.json")
            if os.path.exists(npc_names_path):
                with open(npc_names_path, 'r', encoding='utf-8') as f:
                    npc_names = json.load(f)
                for n_id, n_name in sorted(npc_names.items(), key=lambda x: int(x[0])):
                    monsters.append({"id": n_id, "name": n_name})
        except Exception as e:
            pass

        items = []
        try:
            import json, os
            item_names_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "items.json")
            if os.path.exists(item_names_path):
                with open(item_names_path, 'r', encoding='utf-8') as f:
                    item_names = json.load(f)
                for i_id, i_name in item_names.items():
                    items.append({"id": i_id, "name": i_name})
        except Exception as e:
            pass

        import aiohttp.web as web
        return web.json_response({"monsters": monsters, "items": items}, headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
