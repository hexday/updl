import os
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, redirect, session, send_file
from werkzeug.utils import secure_filename

from config import config
from database import db
from downloader import downloader
from telegram_bot import telegram_bot
from file_manager import file_manager
from logger import logger

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.TELEGRAM.max_file_size

# Session configuration
app.permanent_session_lifetime = timedelta(seconds=config.SERVER.session_timeout)

def login_required(f):
    """Login required decorator with session extension"""
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        
        session.permanent = True
        session['last_activity'] = datetime.now().isoformat()
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Template دقیقاً مطابق درخواست + ویژگی‌های اضافی
ULTRA_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultra DM{% if not session.logged_in %} - Login{% endif %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root { 
            --bg: #0a0a0a; 
            --surface: #111; 
            --border: #222; 
            --text: #fff; 
            --accent: #3b82f6; 
        }
        
        body { 
            background: var(--bg); 
            color: var(--text); 
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; 
        }
        
        .surface { 
            background: var(--surface); 
            border: 1px solid var(--border); 
        }
        
        .hover\\:surface:hover { 
            background: #1a1a1a; 
        }
        
        .accent { 
            color: var(--accent); 
        }
        
        .progress { 
            background: linear-gradient(90deg, var(--accent), #8b5cf6); 
        }
        
        .animate-pulse { 
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; 
        }
        
        .animate-spin { 
            animation: spin 1s linear infinite; 
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: .5; }
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        input, button, textarea, select { 
            background: var(--surface); 
            border: 1px solid var(--border); 
            color: var(--text); 
        }
        
        input:focus, textarea:focus, select:focus { 
            border-color: var(--accent); 
            outline: none; 
        }
        
        button:hover { 
            background: #1a1a1a; 
        }
        
        .btn-accent { 
            background: var(--accent); 
        }
        
        .btn-accent:hover { 
            background: #2563eb; 
        }
        
        .btn-danger { 
            background: #dc2626; 
        }
        
        .btn-danger:hover { 
            background: #b91c1c; 
        }
        
        ::-webkit-scrollbar { 
            width: 8px; 
        }
        
        ::-webkit-scrollbar-track { 
            background: var(--bg); 
        }
        
        ::-webkit-scrollbar-thumb { 
            background: var(--border); 
            border-radius: 4px; 
        }
        
        .modal { 
            background: rgba(0,0,0,0.8); 
        }
        
        .tab-active { 
            background: var(--accent); 
            color: white; 
        }
        
        /* اضافه کردن استایل‌های جدید */
        .fade-in {
            animation: fadeIn 0.3s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .status-indicator {
            position: relative;
            display: inline-block;
        }
        
        .status-indicator::after {
            content: '';
            position: absolute;
            top: -2px;
            right: -2px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.offline::after {
            background: #ef4444;
            animation: none;
        }
        
        .tooltip {
            position: relative;
        }
        
        .tooltip:hover::before {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--surface);
            color: var(--text);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 1000;
            border: 1px solid var(--border);
        }
        
        .progress-bar {
            background: var(--surface);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), #8b5cf6);
            transition: width 0.3s ease;
            border-radius: 4px;
        }
        
        .upload-zone {
            transition: all 0.3s ease;
        }
        
        .upload-zone.dragover {
            border-color: var(--accent);
            background: rgba(59, 130, 246, 0.1);
        }
        
        .engine-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .engine-ytdlp { background: #ff0000; color: white; }
        .engine-aria2 { background: #00b4d8; color: white; }
        .engine-requests { background: #10b981; color: white; }
        .engine-wget { background: #f59e0b; color: white; }
        .engine-curl { background: #8b5cf6; color: white; }
        
        .platform-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 500;
        }
        
        .platform-youtube { background: #ff0000; color: white; }
        .platform-instagram { background: #e4405f; color: white; }
        .platform-twitter { background: #1da1f2; color: white; }
        .platform-tiktok { background: #000000; color: white; }
        .platform-facebook { background: #1877f2; color: white; }
        .platform-direct { background: #6b7280; color: white; }
    </style>
</head>
<body class="min-h-screen p-4">
    {% if not session.logged_in %}
    <!-- Login Form -->
    <div class="max-w-md mx-auto mt-20">
        <div class="surface rounded-lg p-8 fade-in">
            <h1 class="text-2xl font-bold text-center mb-6">Ultra DM Login</h1>
            {% if error %}
            <div class="bg-red-600 text-white p-3 rounded mb-4 fade-in">{{ error }}</div>
            {% endif %}
            <form method="POST" action="/login" class="space-y-4">
                <input name="username" type="text" placeholder="Username" 
                       class="w-full px-3 py-2 rounded transition-all duration-200" required>
                <input name="password" type="password" placeholder="Password" 
                       class="w-full px-3 py-2 rounded transition-all duration-200" required>
                <button type="submit" 
                        class="w-full btn-accent py-2 rounded font-medium transition-all duration-200 hover:scale-105">
                    Login
                </button>
            </form>
            <div class="text-center mt-4 text-xs text-gray-400">
                Ultra Download Manager v2.0 • Professional Edition
            </div>
        </div>
    </div>
    {% else %}
    <!-- Main Application -->
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center space-x-3">
                <div class="w-8 h-8 surface rounded flex items-center justify-center status-indicator" id="statusIndicator">
                    <div id="spinner" class="w-3 h-3 border border-t-accent rounded-full animate-spin hidden"></div>
                    <div id="idle" class="w-3 h-3 accent">●</div>
                </div>
                <div>
                    <h1 class="text-lg font-bold">Ultra DM</h1>
                    <div class="text-xs text-gray-400">Professional Edition v2.0</div>
                </div>
            </div>
            <div class="flex items-center space-x-4 text-sm text-gray-400">
                <div class="tooltip" data-tooltip="Total Speed">
                    <span id="speed">0 KB/s</span>
                </div>
                <div class="tooltip" data-tooltip="Active Downloads">
                    <span id="active">0/4</span>
                </div>
                <div class="tooltip" data-tooltip="Telegram Queue">
                    <span id="telegramQueue">0</span>
                </div>
                <button onclick="openFolder()" 
                        class="px-3 py-1 surface rounded hover:surface tooltip transition-all duration-200" 
                        data-tooltip="Open Downloads Folder">
                    Folder
                </button>
                <a href="/logout" 
                   class="px-3 py-1 btn-danger rounded text-white tooltip transition-all duration-200" 
                   data-tooltip="Logout">
                    Logout
                </a>
            </div>
        </div>

        <!-- Tabs -->
        <div class="mb-6">
            <div class="flex space-x-2">
                <button onclick="showTab('download')" id="downloadTab" 
                        class="px-4 py-2 rounded tab-active transition-all duration-200">
                    Download
                </button>
                <button onclick="showTab('upload')" id="uploadTab" 
                        class="px-4 py-2 surface rounded hover:surface transition-all duration-200">
                    Upload
                </button>
                <button onclick="showTab('files')" id="filesTab" 
                        class="px-4 py-2 surface rounded hover:surface transition-all duration-200">
                    Files
                </button>
            </div>
        </div>

        <!-- Download Tab -->
        <div id="downloadPanel" class="space-y-6">
            <!-- Add Download -->
            <div class="surface rounded-lg p-4 fade-in">
                <div class="space-y-3">
                    <div class="relative">
                        <input id="url" type="url" 
                               placeholder="https://example.com/file.zip or YouTube URL" 
                               class="w-full px-3 py-2 rounded text-sm transition-all duration-200 pr-10">
                        <div class="absolute right-3 top-1/2 transform -translate-y-1/2">
                            <div id="urlStatus" class="w-2 h-2 rounded-full bg-gray-500"></div>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <textarea id="description" placeholder="Description (optional)" 
                                class="px-3 py-2 rounded text-sm resize-none h-20 transition-all duration-200"></textarea>
                        <textarea id="tags" placeholder="Tags (comma separated)" 
                                class="px-3 py-2 rounded text-sm resize-none h-20 transition-all duration-200"></textarea>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <select id="quality" class="px-3 py-2 rounded text-sm">
                            <option value="best">Best Quality</option>
                            <option value="1080p">1080p</option>
                            <option value="720p">720p</option>
                            <option value="480p">480p</option>
                            <option value="audio">Audio Only</option>
                        </select>
                        
                        <select id="engine" class="px-3 py-2 rounded text-sm">
                            <option value="auto">Auto Select Engine</option>
                            <option value="yt-dlp">yt-dlp</option>
                            <option value="aria2">aria2</option>
                            <option value="requests">requests</option>
                            <option value="wget">wget</option>
                            <option value="curl">curl</option>
                        </select>
                        
                        <label class="flex items-center space-x-2 px-3 py-2">
                            <input type="checkbox" id="extractAudio" class="rounded">
                            <span class="text-sm">Extract Audio</span>
                        </label>
                    </div>
                    
                    <button onclick="addDownload()" id="addBtn" 
                            class="w-full btn-accent py-2 rounded text-sm font-medium transition-all duration-200 hover:scale-105">
                        Add Download
                    </button>
                </div>
            </div>

            <!-- Stats -->
            <div class="grid grid-cols-4 gap-3 fade-in">
                <div class="surface rounded-lg p-3 text-center hover:surface transition-all duration-200">
                    <div class="text-lg font-bold" id="totalCount">0</div>
                    <div class="text-xs text-gray-400">Total</div>
                </div>
                <div class="surface rounded-lg p-3 text-center hover:surface transition-all duration-200">
                    <div class="text-lg font-bold accent" id="activeCount">0</div>
                    <div class="text-xs text-gray-400">Active</div>
                </div>
                <div class="surface rounded-lg p-3 text-center hover:surface transition-all duration-200">
                    <div class="text-lg font-bold text-green-400" id="doneCount">0</div>
                    <div class="text-xs text-gray-400">Done</div>
                </div>
                <div class="surface rounded-lg p-3 text-center hover:surface transition-all duration-200">
                    <div class="text-lg font-bold text-yellow-400" id="pausedCount">0</div>
                    <div class="text-xs text-gray-400">Paused</div>
                </div>
            </div>

            <!-- Downloads List -->
            <div class="surface rounded-lg overflow-hidden fade-in">
                <div class="p-4 border-b border-gray-800">
                    <div class="flex items-center justify-between">
                        <h2 class="font-medium">Downloads</h2>
                        <div class="flex space-x-2">
                            <button onclick="pauseAll()" 
                                    class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" 
                                    data-tooltip="Pause All Downloads">
                                Pause All
                            </button>
                            <button onclick="clearDone()" 
                                    class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" 
                                    data-tooltip="Clear Completed Downloads">
                                Clear Done
                            </button>
                            <button onclick="refreshDownloads()" 
                                    class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" 
                                    data-tooltip="Refresh Downloads">
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>
                <div id="downloadsList" class="max-h-96 overflow-y-auto">
                    <div class="p-8 text-center text-gray-500">
                        <div class="text-2xl mb-2">↓</div>
                        <div class="text-sm">No downloads</div>
                        <div class="text-xs text-gray-400 mt-2">Add a URL above to start downloading</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Upload Tab -->
        <div id="uploadPanel" class="hidden space-y-6">
            <div class="surface rounded-lg p-6 fade-in">
                <h2 class="text-lg font-bold mb-4">Upload Files to Telegram</h2>
                <form id="uploadForm" enctype="multipart/form-data" class="space-y-4">
                    <div class="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center upload-zone transition-all duration-300" 
                         id="uploadZone">
                        <input type="file" id="fileInput" multiple class="hidden" onchange="handleFileSelect()">
                        <button type="button" onclick="document.getElementById('fileInput').click()" 
                                class="btn-accent px-6 py-3 rounded font-medium transition-all duration-200 hover:scale-105">
                            Choose Files
                        </button>
                        <p class="text-sm text-gray-400 mt-2">Or drag and drop files here</p>
                        <p class="text-xs text-gray-500 mt-1">Max size: 4GB per file • All formats supported</p>
                    </div>
                    
                    <div id="fileList" class="hidden">
                        <h3 class="font-medium mb-2">Selected Files:</h3>
                        <div id="selectedFiles" class="space-y-2"></div>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <textarea id="uploadDescription" placeholder="Description (optional)" 
                                class="px-3 py-2 rounded text-sm resize-none h-20 transition-all duration-200"></textarea>
                        <textarea id="uploadTags" placeholder="Tags (comma separated)" 
                                class="px-3 py-2 rounded text-sm resize-none h-20 transition-all duration-200"></textarea>
                    </div>
                    
                    <button type="button" onclick="uploadFiles()" id="uploadBtn" 
                            class="w-full btn-accent py-2 rounded font-medium transition-all duration-200 hover:scale-105">
                        Upload Files to Telegram
                    </button>
                </form>
            </div>
            
            <!-- Upload Queue -->
            <div class="surface rounded-lg fade-in">
                <div class="p-4 border-b border-gray-800">
                    <div class="flex items-center justify-between">
                        <h3 class="font-medium">Upload Queue</h3>
                        <div class="flex space-x-2">
                            <button onclick="clearUploadQueue()" 
                                    class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" 
                                    data-tooltip="Clear Upload Queue">
                                Clear Queue
                            </button>
                        </div>
                    </div>
                </div>
                <div id="uploadQueueList" class="max-h-48 overflow-y-auto p-4">
                    <div class="text-center text-gray-500 py-4">
                        <div class="text-sm">No uploads in queue</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Files Tab -->
        <div id="filesPanel" class="hidden space-y-6">
            <div class="surface rounded-lg fade-in">
                <div class="p-4 border-b border-gray-800">
                    <div class="flex items-center justify-between">
                        <h2 class="font-medium">All Files</h2>
                        <div class="flex space-x-2">
                            <select id="fileFilter" class="text-xs px-2 py-1 surface rounded">
                                <option value="">All Files</option>
                                <option value="video">Videos</option>
                                <option value="audio">Audio</option>
                                <option value="image">Images</option>
                                <option value="document">Documents</option>
                            </select>
                            <button onclick="refreshFiles()" 
                                    class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" 
                                    data-tooltip="Refresh Files">
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>
                <div id="filesList" class="max-h-96 overflow-y-auto p-4">
                    <div class="text-center text-gray-500 py-8">
                        <div class="text-2xl mb-2">📁</div>
                        <div class="text-sm">Loading files...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Toast Container -->
    <div id="toastContainer" class="fixed top-4 right-4 z-50 space-y-2"></div>
    
    <!-- Loading Overlay -->
    <div id="loadingOverlay" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
        <div class="surface rounded-lg p-6 text-center">
            <div class="animate-spin w-8 h-8 border-2 border-accent border-t-transparent rounded-full mx-auto mb-4"></div>
            <div class="text-sm">Processing...</div>
        </div>
    </div>
    {% endif %}

    <script>
        let downloads = {};
        let uploads = {};
        let stats = {};
        let currentTab = 'download';
        let updateInterval;
        let isUpdating = false;

        // Initialize
        {% if session.logged_in %}
        document.addEventListener('DOMContentLoaded', function() {
            initializeApp();
        });
        
        function initializeApp() {
            updateInterval = setInterval(updateData, 2000);
            updateData();
            
            // URL input validation
            const urlInput = document.getElementById('url');
            urlInput.addEventListener('input', validateUrl);
            urlInput.addEventListener('keypress', e => {
                if (e.key === 'Enter') addDownload();
            });
            
            // File filter
            document.getElementById('fileFilter').addEventListener('change', filterFiles);
            
            // Drag and drop setup
            setupDragAndDrop();
            
            console.log('Ultra DM initialized successfully');
        }
        
        function validateUrl() {
            const url = document.getElementById('url').value.trim();
            const status = document.getElementById('urlStatus');
            
            if (!url) {
                status.className = 'w-2 h-2 rounded-full bg-gray-500';
                return;
            }
            
            try {
                new URL(url);
                status.className = 'w-2 h-2 rounded-full bg-green-500';
            } catch {
                status.className = 'w-2 h-2 rounded-full bg-red-500';
            }
        }
        
        function setupDragAndDrop() {
            const uploadZone = document.getElementById('uploadZone');
            if (!uploadZone) return;
            
            uploadZone.addEventListener('dragover', e => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
                uploadZone.classList.add('dragover');
            });
            
            uploadZone.addEventListener('dragleave', e => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
            });
            
            uploadZone.addEventListener('drop', e => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = Array.from(e.dataTransfer.files);
                handleDroppedFiles(files);
            });
        }
        {% endif %}

        function showTab(tab) {
            // Hide all panels
            document.getElementById('downloadPanel').classList.add('hidden');
            document.getElementById('uploadPanel').classList.add('hidden');
            document.getElementById('filesPanel').classList.add('hidden');
            
            // Remove active class from all tabs
            document.getElementById('downloadTab').classList.remove('tab-active');
            document.getElementById('uploadTab').classList.remove('tab-active');
            document.getElementById('filesTab').classList.remove('tab-active');
            
            // Show selected panel and activate tab
            document.getElementById(tab + 'Panel').classList.remove('hidden');
            document.getElementById(tab + 'Tab').classList.add('tab-active');
            
            currentTab = tab;
            
            if (tab === 'files') {
                loadFiles();
            } else if (tab === 'upload') {
                loadUploadQueue();
            }
        }

        async function addDownload() {
            const urlInput = document.getElementById('url');
            const descInput = document.getElementById('description');
            const tagsInput = document.getElementById('tags');
            const qualityInput = document.getElementById('quality');
            const engineInput = document.getElementById('engine');
            const extractAudioInput = document.getElementById('extractAudio');
            const addBtn = document.getElementById('addBtn');
            
            const url = urlInput.value.trim();
            if (!url) {
                toast('Please enter a URL', 'error');
                return;
            }
            
            // Validate URL
            try {
                new URL(url);
            } catch {
                toast('Please enter a valid URL', 'error');
                return;
            }
            
            const originalText = addBtn.innerHTML;
            addBtn.innerHTML = '<div class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full inline-block mr-2"></div>Adding...';
            addBtn.disabled = true;
            
            try {
                const res = await fetch('/api/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        url: url,
                        description: descInput.value.trim(),
                        tags: tagsInput.value.trim(),
                        quality: qualityInput.value,
                        engine: engineInput.value,
                        extract_audio: extractAudioInput.checked
                    })
                });
                
                const data = await res.json();
                if (data.success) {
                    urlInput.value = '';
                    descInput.value = '';
                    tagsInput.value = '';
                    extractAudioInput.checked = false;
                    document.getElementById('urlStatus').className = 'w-2 h-2 rounded-full bg-gray-500';
                    toast('Download started successfully!', 'success');
                } else {
                    toast(data.error || 'Failed to start download', 'error');
                }
            } catch (e) {
                toast('Network error occurred', 'error');
                console.error('Download error:', e);
            } finally {
                addBtn.innerHTML = originalText;
                addBtn.disabled = false;
            }
        }

        function handleFileSelect() {
            const files = Array.from(document.getElementById('fileInput').files);
            handleDroppedFiles(files);
        }

        function handleDroppedFiles(files) {
            const fileList = document.getElementById('fileList');
            const selectedFiles = document.getElementById('selectedFiles');
            
            if (files.length === 0) {
                fileList.classList.add('hidden');
                return;
            }
            
            fileList.classList.remove('hidden');
            selectedFiles.innerHTML = files.map((file, index) => `
                <div class="flex items-center justify-between p-3 surface rounded hover:surface transition-all duration-200">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 surface rounded flex items-center justify-center">
                            ${getFileIcon(file.name)}
                        </div>
                        <div>
                            <div class="text-sm font-medium">${file.name}</div>
                            <div class="text-xs text-gray-400">${formatSize(file.size)} • ${getFileType(file.name)}</div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-xs px-2 py-1 rounded ${file.size > 4*1024*1024*1024 ? 'bg-red-600' : 'bg-green-600'}">
                            ${file.size > 4*1024*1024*1024 ? 'Too Large' : 'Ready'}
                        </span>
                        <button onclick="removeFile(${index})" 
                                class="w-6 h-6 flex items-center justify-center surface rounded hover:bg-red-600 transition-all duration-200">
                            ×
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        function removeFile(index) {
            const fileInput = document.getElementById('fileInput');
            const dt = new DataTransfer();
            
            Array.from(fileInput.files).forEach((file, i) => {
                if (i !== index) dt.items.add(file);
            });
            
            fileInput.files = dt.files;
            handleDroppedFiles(Array.from(fileInput.files));
        }

        async function uploadFiles() {
            const fileInput = document.getElementById('fileInput');
            const uploadBtn = document.getElementById('uploadBtn');
            const description = document.getElementById('uploadDescription').value.trim();
            const tags = document.getElementById('uploadTags').value.trim();
            
            if (fileInput.files.length === 0) {
                toast('Please select files first', 'error');
                return;
            }
            
            const originalText = uploadBtn.innerHTML;
            uploadBtn.innerHTML = '<div class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full inline-block mr-2"></div>Uploading...';
            uploadBtn.disabled = true;
            
            const formData = new FormData();
            Array.from(fileInput.files).forEach(file => {
                if (file.size <= 4*1024*1024*1024) { // 4GB limit
                    formData.append('files', file);
                }
            });
            formData.append('description', description);
            formData.append('tags', tags);
            
            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await res.json();
                if (data.success) {
                    fileInput.value = '';
                    document.getElementById('uploadDescription').value = '';
                    document.getElementById('uploadTags').value = '';
                    document.getElementById('fileList').classList.add('hidden');
                    toast(`Successfully uploaded ${data.count} files`, 'success');
                    loadUploadQueue(); // Refresh upload queue
                } else {
                    toast(data.error || 'Upload failed', 'error');
                }
            } catch (e) {
                toast('Upload error occurred', 'error');
                console.error('Upload error:', e);
            } finally {
                uploadBtn.innerHTML = originalText;
                uploadBtn.disabled = false;
            }
        }

        async function control(id, action, type = 'download') {
            try {
                const endpoint = type === 'download' ? '/api/download/control' : '/api/upload/control';
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id, action})
                });
                
                const data = await res.json();
                if (data.success) {
                    toast(`${action.charAt(0).toUpperCase() + action.slice(1)} successful`, 'success');
                } else {
                    toast(data.error || `Failed to ${action}`, 'error');
                }
            } catch (e) {
                toast(`Failed to ${action}`, 'error');
                console.error('Control error:', e);
            }
        }

        async function updateData() {
            if (isUpdating) return;
            isUpdating = true;
            
            try {
                const res = await fetch('/api/data');
                if (!res.ok) {
                    if (res.status === 302 || res.status === 401) {
                        window.location.reload();
                        return;
                    }
                    throw new Error(`HTTP ${res.status}`);
                }
                
                const data = await res.json();
                downloads = data.downloads || {};
                uploads = data.uploads || {};
                stats = data.stats || {};
                
                updateUI();
                updateStatusIndicator(true);
                
            } catch (e) {
                console.error('Update failed:', e);
                updateStatusIndicator(false);
            } finally {
                isUpdating = false;
            }
        }
        
        function updateUI() {
            if (currentTab === 'download') {
                renderDownloads();
            } else if (currentTab === 'upload') {
                loadUploadQueue();
            } else if (currentTab === 'files') {
                renderFiles();
            }
            
            updateStats();
        }
        
        function updateStatusIndicator(online) {
            const indicator = document.getElementById('statusIndicator');
            const spinner = document.getElementById('spinner');
            const idle = document.getElementById('idle');
            
            if (online) {
                indicator.classList.remove('offline');
                if ((stats.downloads?.downloading || 0) > 0) {
                    spinner.classList.remove('hidden');
                    idle.classList.add('hidden');
                } else {
                    spinner.classList.add('hidden');
                    idle.classList.remove('hidden');
                }
            } else {
                indicator.classList.add('offline');
                spinner.classList.add('hidden');
                idle.classList.remove('hidden');
            }
        }

        function renderDownloads() {
            const container = document.getElementById('downloadsList');
            const downloadArray = Object.values(downloads);
            
            if (downloadArray.length === 0) {
                container.innerHTML = `
                    <div class="p-8 text-center text-gray-500">
                        <div class="text-2xl mb-2">↓</div>
                        <div class="text-sm">No downloads</div>
                        <div class="text-xs text-gray-400 mt-2">Add a URL above to start downloading</div>
                    </div>
                `;
                return;
            }
            
            // Sort by creation time (newest first)
            downloadArray.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
            
            const html = downloadArray.map(dl => {
                const progress = Math.round(dl.progress || 0);
                const statusConfig = getStatus(dl.status);
                const controls = getControls(dl.id, dl.status, 'download');
                
                return `
                    <div class="p-3 border-b border-gray-800 last:border-b-0 hover:surface fade-in transition-all duration-200">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center space-x-3 flex-1 min-w-0">
                                <div class="w-6 h-6 flex items-center justify-center">
                                    <div class="${statusConfig.class}">${statusConfig.icon}</div>
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm font-medium truncate" title="${dl.filename || 'Processing...'}">${dl.filename || 'Processing...'}</div>
                                    <div class="flex items-center space-x-2 text-xs text-gray-400 mt-1">
                                        ${dl.platform ? `<span class="platform-badge platform-${dl.platform}">${dl.platform.toUpperCase()}</span>` : ''}
                                        ${dl.engine ? `<span class="engine-badge engine-${dl.engine}">${dl.engine}</span>` : ''}
                                        <span>${formatSize(dl.downloaded || 0)}${dl.size ? ` / ${formatSize(dl.size)}` : ''}</span>
                                        ${dl.status === 'downloading' && dl.speed ? `<span>${formatSpeed(dl.speed)}</span>` : ''}
                                        ${dl.status === 'downloading' && dl.eta ? `<span>ETA: ${formatTime(dl.eta)}</span>` : ''}
                                    </div>
                                    ${dl.description ? `<div class="text-xs text-gray-500 mt-1">${dl.description}</div>` : ''}
                                    ${dl.error_message ? `<div class="text-xs text-red-400 mt-1">Error: ${dl.error_message}</div>` : ''}
                                </div>
                            </div>
                            <div class="flex items-center space-x-1">
                                ${dl.share_link ? `<a href="${dl.share_link}" target="_blank" class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" data-tooltip="Open in Telegram">📎</a>` : ''}
                                ${controls}
                            </div>
                        </div>
                        ${(dl.status === 'downloading' || dl.status === 'paused') && dl.size > 0 ? `
                            <div class="progress-bar h-1 mb-1">
                                <div class="progress-fill" style="width: ${progress}%"></div>
                            </div>
                            <div class="text-xs text-gray-400">${progress}% complete</div>
                        ` : ''}
                    </div>
                `;
            }).join('');
            
            container.innerHTML = html;
        }

        function updateStats() {
            const downloadStats = stats.downloads || {};
            
            document.getElementById('totalCount').textContent = downloadStats.total || 0;
            document.getElementById('activeCount').textContent = downloadStats.downloading || 0;
            document.getElementById('doneCount').textContent = downloadStats.completed || 0;
            document.getElementById('pausedCount').textContent = downloadStats.paused || 0;
            
            // Update header stats
            document.getElementById('speed').textContent = formatSpeed(stats.speed || 0);
            document.getElementById('active').textContent = `${downloadStats.downloading || 0}/${stats.max_workers || 4}`;
            document.getElementById('telegramQueue').textContent = stats.telegram_queue || 0;
        }

        async function loadFiles() {
            try {
                const res = await fetch('/api/files');
                const data = await res.json();
                renderFiles(data.files);
            } catch (e) {
                console.error('Failed to load files:', e);
                document.getElementById('filesList').innerHTML = '<div class="text-center text-red-400 py-8">Error loading files</div>';
            }
        }
        
        function renderFiles(files = []) {
            const container = document.getElementById('filesList');
            
            if (files.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <div class="text-2xl mb-2">📁</div>
                        <div class="text-sm">No files available</div>
                    </div>
                `;
                return;
            }
            
            const html = files.map(file => `
                <div class="flex items-center justify-between p-3 border-b border-gray-800 last:border-b-0 hover:surface fade-in transition-all duration-200">
                    <div class="flex items-center space-x-3 flex-1 min-w-0">
                        <div class="w-8 h-8 surface rounded flex items-center justify-center">
                            ${getFileIcon(file.filename || file.original_filename)}
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-medium truncate">${file.filename || file.original_filename}</div>
                            <div class="text-xs text-gray-400">
                                ${formatSize(file.size)} • ${getFileType(file.filename || file.original_filename)}
                                ${file.uploaded_at || file.finished_at ? ` • ${formatDate(file.uploaded_at || file.finished_at)}` : ''}
                                ${file.description ? ` • ${file.description}` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="text-xs px-2 py-1 rounded ${file.type === 'download' ? 'bg-blue-600' : 'bg-green-600'}">
                            ${file.type}
                        </span>
                        ${file.share_link ? `<a href="${file.share_link}" target="_blank" class="text-xs px-2 py-1 surface rounded hover:surface tooltip transition-all duration-200" data-tooltip="Open in Telegram">📎</a>` : ''}
                        <button onclick="control('${file.id}', 'remove', '${file.type}')" class="text-xs px-2 py-1 surface rounded hover:bg-red-600 tooltip transition-all duration-200" data-tooltip="Delete File">✗</button>
                    </div>
                </div>
            `).join('');
            
            container.innerHTML = html;
        }
        
        function filterFiles() {
            const filter = document.getElementById('fileFilter').value;
            // This would filter the current files list
            loadFiles(); // For now, just reload
        }
        
        async function loadUploadQueue() {
            try {
                const res = await fetch('/api/telegram/status');
                const data = await res.json();
                
                const container = document.getElementById('uploadQueueList');
                
                if (data.queue_length === 0) {
                    container.innerHTML = `
                        <div class="text-center text-gray-500 py-4">
                            <div class="text-sm">No uploads in queue</div>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="space-y-2">
                        <div class="text-sm text-gray-400">
                            Queue: ${data.queue_length} files • Processing: ${data.processing_count}
                        </div>
                        ${data.next_files ? data.next_files.map(file => `
                            <div class="text-xs text-gray-500 p-2 surface rounded">
                                ${file}
                            </div>
                        `).join('') : ''}
                    </div>
                `;
                
            } catch (e) {
                console.error('Failed to load upload queue:', e);
            }
        }

        function getStatus(status) {
            const configs = {
                downloading: {icon: '↓', class: 'text-blue-400 animate-pulse'},
                completed: {icon: '✓', class: 'text-green-400'},
                paused: {icon: '⏸', class: 'text-yellow-400'},
                error: {icon: '✗', class: 'text-red-400'},
                initializing: {icon: '⟳', class: 'text-gray-400 animate-spin'},
                cancelled: {icon: '⏹', class: 'text-gray-400'}
            };
            return configs[status] || configs.error;
        }

        function getControls(id, status, type) {
            const btn = 'px-2 py-1 text-xs surface rounded hover:surface tooltip transition-all duration-200';
            
            switch (status) {
                case 'downloading':
                    return `
                        <button onclick="control('${id}', 'pause', '${type}')" class="${btn}" data-tooltip="Pause">⏸</button>
                        <button onclick="control('${id}', 'cancel', '${type}')" class="${btn}" data-tooltip="Cancel">✗</button>
                    `;
                case 'paused':
                    return `
                        <button onclick="control('${id}', 'resume', '${type}')" class="${btn}" data-tooltip="Resume">▶</button>
                        <button onclick="control('${id}', 'cancel', '${type}')" class="${btn}" data-tooltip="Cancel">✗</button>
                    `;
                case 'completed':
                case 'error':
                case 'cancelled':
                    return `<button onclick="control('${id}', 'remove', '${type}')" class="${btn}" data-tooltip="Remove">✗</button>`;
                default:
                    return `<button onclick="control('${id}', 'remove', '${type}')" class="${btn}" data-tooltip="Remove">✗</button>`;
            }
        }

        // Quick actions
        async function openFolder() {
            try {
                await fetch('/api/open-folder', {method: 'POST'});
                toast('Opening downloads folder', 'success');
            } catch (e) {
                toast('Failed to open folder', 'error');
            }
        }

        async function pauseAll() {
            try {
                const res = await fetch('/api/download/pause-all', {method: 'POST'});
                const data = await res.json();
                toast(`Paused ${data.count} downloads`, 'success');
            } catch (e) {
                toast('Failed to pause downloads', 'error');
            }
        }

        async function clearDone() {
            try {
                const res = await fetch('/api/download/clear-completed', {method: 'POST'});
                const data = await res.json();
                toast(`Cleared ${data.count} completed downloads`, 'success');
            } catch (e) {
                toast('Failed to clear completed', 'error');
            }
        }
        
        async function clearUploadQueue() {
            try {
                const res = await fetch('/api/telegram/clear-queue', {method: 'POST'});
                const data = await res.json();
                toast(`Cleared ${data.count} items from queue`, 'success');
                loadUploadQueue();
            } catch (e) {
                toast('Failed to clear queue', 'error');
            }
        }

        function refreshDownloads() {
            updateData();
            toast('Downloads refreshed', 'success');
        }
        
        function refreshFiles() {
            loadFiles();
            toast('Files refreshed', 'success');
        }

        // Utility functions
        function formatSpeed(speed) {
            if (!speed || speed === 0) return '0 B/s';
            const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
            let i = 0;
            while (speed >= 1024 && i < units.length - 1) {
                speed /= 1024;
                i++;
            }
            return `${speed.toFixed(1)} ${units[i]}`;
        }

        function formatSize(size) {
            if (!size || size === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let i = 0;
            while (size >= 1024 && i < units.length - 1) {
                size /= 1024;
                i++;
            }
            return `${size.toFixed(1)} ${units[i]}`;
        }

        function formatTime(seconds) {
            if (!seconds || !isFinite(seconds)) return '--';
            if (seconds < 60) return `${Math.round(seconds)}s`;
            if (seconds < 3600) return `${Math.round(seconds/60)}m`;
            return `${Math.round(seconds/3600)}h`;
        }
        
        function formatDate(dateString) {
            if (!dateString) return 'Unknown';
            try {
                const date = new Date(dateString);
                const now = new Date();
                const diff = now - date;
                
                if (diff < 60000) return 'Just now';
                if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
                if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
                return date.toLocaleDateString();
            } catch {
                return 'Unknown';
            }
        }
        
        function getFileIcon(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            const icons = {
                mp4: '🎬', avi: '🎬', mkv: '🎬', mov: '🎬', wmv: '🎬',
                mp3: '🎵', wav: '🎵', flac: '🎵', aac: '🎵', ogg: '🎵',
                jpg: '🖼', jpeg: '🖼', png: '🖼', gif: '🖼', webp: '🖼',
                pdf: '📄', doc: '📄', docx: '📄', txt: '📄',
                zip: '📦', rar: '📦', '7z': '📦', tar: '📦'
            };
            return icons[ext] || '📁';
        }
        
        function getFileType(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            const types = {
                video: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
                audio: ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
                image: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
                document: ['pdf', 'doc', 'docx', 'txt'],
                archive: ['zip', 'rar', '7z', 'tar', 'gz']
            };
            
            for (const [type, extensions] of Object.entries(types)) {
                if (extensions.includes(ext)) return type;
            }
            return 'file';
        }

        // Toast notification system
        function toast(message, type = 'info', duration = 5000) {
            const container = document.getElementById('toastContainer');
            const toastId = Date.now();
            
            const colors = {
                success: 'bg-green-600',
                error: 'bg-red-600',
                warning: 'bg-yellow-600',
                info: 'bg-blue-600'
            };
            
            const icons = {
                success: '✓',
                error: '✗',
                warning: '⚠',
                info: 'ℹ'
            };
            
            const toast = document.createElement('div');
            toast.id = `toast-${toastId}`;
            toast.className = `${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg transform translate-x-full transition-transform duration-300 flex items-center space-x-3 min-w-80 fade-in`;
            toast.innerHTML = `
                <span class="text-lg">${icons[type]}</span>
                <span class="flex-1">${message}</span>
                <button onclick="removeToast('${toastId}')" class="opacity-70 hover:opacity-100 transition-opacity">
                    ✕
                </button>
            `;
            
            container.appendChild(toast);
            
            // Slide in
            setTimeout(() => toast.classList.remove('translate-x-full'), 100);
            
            // Auto remove
            setTimeout(() => removeToast(toastId), duration);
        }
        
        function removeToast(toastId) {
            const toast = document.getElementById(`toast-${toastId}`);
            if (toast) {
                toast.classList.add('translate-x-full');
                setTimeout(() => toast.remove(), 300);
            }
        }
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', function() {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        });
    </script>
</body>
</html>"""

# Routes - تمام routes مشابه قبل ولی با endpoint های API
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == config.LOGIN_USERNAME and password == config.LOGIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            session['last_activity'] = datetime.now().isoformat()
            
            logger.get_logger('main').info(f"User logged in: {username}")
            return redirect('/')
        else:
            logger.get_logger('main').warning(f"Failed login: {username}")
            return render_template_string(ULTRA_TEMPLATE, error="Invalid username or password")
    
    return render_template_string(ULTRA_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    logger.get_logger('main').info("User logged out")
    return redirect('/login')

@app.route('/')
@login_required
def index():
    return render_template_string(ULTRA_TEMPLATE)

# Compatibility routes (old endpoints)
@app.route('/add', methods=['POST'])
@login_required
def add_download_old():
    return add_download_new()

@app.route('/upload', methods=['POST'])
@login_required
def upload_files_old():
    return upload_files_new()

@app.route('/data')
@login_required
def get_data_old():
    return get_data_new()

@app.route('/control', methods=['POST'])
@login_required
def control_download_old():
    return control_download_new()

@app.route('/files')
@login_required
def get_files_old():
    return get_files_new()

@app.route('/folder', methods=['POST'])
@login_required
def open_folder_old():
    return open_folder_new()

@app.route('/pause-all', methods=['POST'])
@login_required
def pause_all_old():
    return pause_all_new()

@app.route('/clear', methods=['POST'])
@login_required
def clear_done_old():
    return clear_done_new()

# New API endpoints
def add_download_new():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        url = data.get('url', '').strip()
        description = data.get('description', '').strip()
        tags = data.get('tags', '').strip()
        quality = data.get('quality', 'best')
        extract_audio = data.get('extract_audio', False)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'})
        
        logger.get_logger('main').info(f"Starting download: {url}")
        
        download_id, error = downloader.start_download(url, description, tags, quality, extract_audio)
        
        if error:
            return jsonify({'success': False, 'error': error})
        
        return jsonify({'success': True, 'id': download_id})
        
    except Exception as e:
        logger.get_logger('error').error(f"Download error: {e}")
        return jsonify({'success': False, 'error': str(e)})

def upload_files_new():
    try:
        files = request.files.getlist('files')
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        
        if not files or not files[0].filename:
            return jsonify({'success': False, 'error': 'No files selected'})
        
        uploaded_count = 0
        
        for file in files:
            if file and file.filename:
                try:
                    file.seek(0, 2)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > config.TELEGRAM.max_file_size:
                        continue
                    
                    filename = secure_filename(file.filename)
                    if not filename:
                        filename = f"upload_{int(time.time())}.bin"
                    
                    upload_id = hashlib.md5(f"{filename}{time.time()}".encode()).hexdigest()[:16]
                    filepath = config.UPLOADS_DIR / f"{upload_id}_{filename}"
                    
                    file.save(str(filepath))
                    actual_size = filepath.stat().st_size
                    
                    upload_data = {
                        'id': upload_id,
                        'original_filename': filename,
                        'filepath': str(filepath),
                        'file_type': config.detect_file_type(filename),
                        'size': actual_size,
                        'description': description,
                        'tags': tags,
                        'uploaded_at': datetime.now().isoformat()
                    }
                    
                    db.save_upload(upload_data)
                    telegram_bot.queue_upload(str(filepath), upload_id, 'upload', description, tags, priority=2)
                    
                    uploaded_count += 1
                    
                except Exception as e:
                    logger.get_logger('error').error(f"Upload file error: {e}")
                    continue
        
        return jsonify({'success': True, 'count': uploaded_count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)})

def get_data_new():
    try:
        # Get downloads
        all_downloads = {}
        for dl_id, dl_data in downloader.downloads.items():
            all_downloads[dl_id] = dl_data
        
        db_downloads = db.get_downloads()
        for db_dl in db_downloads:
            if db_dl['id'] not in all_downloads:
                all_downloads[db_dl['id']] = db_dl
        
        # Check for Telegram upload
        for dl_id, dl_data in all_downloads.items():
            if (dl_data.get('status') == 'completed' and 
                not dl_data.get('telegram_file_id') and 
                dl_data.get('filepath') and 
                Path(dl_data['filepath']).exists()):
                
                telegram_bot.queue_upload(
                    dl_data['filepath'],
                    dl_id,
                    'download',
                    dl_data.get('description', ''),
                    dl_data.get('tags', ''),
                    priority=1
                )
        
        uploads = {u['id']: u for u in db.get_uploads()}
        download_stats = downloader.get_stats()
        total_speed = sum(d.get('speed', 0) for d in all_downloads.values() if d.get('status') == 'downloading')
        telegram_status = telegram_bot.get_queue_status()
        
        return jsonify({
            'downloads': all_downloads,
            'uploads': uploads,
            'stats': {
                'downloads': download_stats,
                'speed': total_speed,
                'telegram_queue': telegram_status['queue_length'],
                'max_workers': config.SERVER.max_workers
            }
        })
        
    except Exception as e:
        logger.get_logger('error').error(f"Data fetch error: {e}")
        return jsonify({
            'downloads': {},
            'uploads': {},
            'stats': {'downloads': {}, 'speed': 0, 'telegram_queue': 0}
        })

def control_download_new():
    try:
        data = request.get_json()
        download_id = data.get('id')
        action = data.get('action')
        
        if action == 'pause':
            downloader.pause_download(download_id)
        elif action == 'resume':
            downloader.resume_download(download_id)
        elif action in ['cancel', 'remove']:
            downloader.cancel_download(download_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def get_files_new():
    try:
        downloads = [dict(d, type='download') for d in db.get_downloads() if d.get('status') == 'completed']
        uploads = [dict(u, type='upload') for u in db.get_uploads()]
        
        all_files = downloads + uploads
        all_files.sort(key=lambda x: x.get('finished_at') or x.get('uploaded_at') or '', reverse=True)
        
        return jsonify({'files': all_files})
        
    except Exception as e:
        return jsonify({'files': []})

def open_folder_new():
    try:
        import subprocess
        import platform
        
        folder_path = str(config.DOWNLOADS_DIR)
        system = platform.system()
        
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":
            subprocess.run(["open", folder_path])
        else:
            subprocess.run(["xdg-open", folder_path])
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def pause_all_new():
    try:
        count = 0
        for dl_id, dl_data in downloader.downloads.items():
            if dl_data.get('status') == 'downloading':
                downloader.pause_download(dl_id)
                count += 1
        
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def clear_done_new():
    try:
        count = downloader.cleanup_completed()
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
