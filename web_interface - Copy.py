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

# Enhanced HTML Template
PROFESSIONAL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Download Manager{% if not session.logged_in %} - Login{% endif %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        :root {
            --bg-primary: #0a0a0a;
            --bg-secondary: #111;
            --bg-tertiary: #1a1a1a;
            --border: #333;
            --text-primary: #fff;
            --text-secondary: #ccc;
            --text-muted: #888;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }
        
        body { 
            background: var(--bg-primary); 
            color: var(--text-primary); 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
        }
        
        .surface { 
            background: var(--bg-secondary); 
            border: 1px solid var(--border);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        
        .surface-hover:hover { 
            background: var(--bg-tertiary); 
            border-color: var(--accent);
            transform: translateY(-1px);
            transition: all 0.2s ease;
        }
        
        .accent { color: var(--accent); }
        .success { color: var(--success); }
        .warning { color: var(--warning); }
        .error { color: var(--error); }
        
        .gradient-progress { 
            background: linear-gradient(90deg, var(--accent), #8b5cf6, var(--success)); 
            background-size: 200% 100%;
            animation: progressShine 2s infinite;
        }
        
        @keyframes progressShine {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        .animate-spin { animation: spin 1s linear infinite; }
        .animate-bounce { animation: bounce 1s infinite; }
        
        input, textarea, select, button { 
            background: var(--bg-secondary); 
            border: 1px solid var(--border); 
            color: var(--text-primary);
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        
        input:focus, textarea:focus, select:focus { 
            border-color: var(--accent); 
            outline: none; 
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        button:hover:not(:disabled) { 
            background: var(--bg-tertiary); 
            transform: translateY(-1px);
        }
        
        .btn-accent { 
            background: var(--accent); 
            color: white;
            font-weight: 500;
        }
        .btn-accent:hover { 
            background: var(--accent-hover); 
        }
        
        .btn-success { background: var(--success); color: white; }
        .btn-warning { background: var(--warning); color: white; }
        .btn-error { background: var(--error); color: white; }
        
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { 
            background: var(--border); 
            border-radius: 4px; 
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
        
        .tab-active { 
            background: var(--accent); 
            color: white; 
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        
        .status-dot { 
            width: 8px; 
            height: 8px; 
            border-radius: 50%; 
            display: inline-block;
        }
        
        .tooltip {
            position: relative;
        }
        
        .tooltip:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 1000;
            border: 1px solid var(--border);
        }
        
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s ease;
        }
        
        .card:hover {
            border-color: var(--accent);
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.1);
        }
        
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .fade-in {
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="min-h-screen">
    {% if not session.logged_in %}
    <!-- Professional Login Form -->
    <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900/20 to-purple-900/20">
        <div class="w-full max-w-md">
            <div class="card text-center mb-8">
                <i class="fas fa-download text-4xl text-blue-500 mb-4"></i>
                <h1 class="text-3xl font-bold mb-2">Professional DM</h1>
                <p class="text-gray-400">Ultra Advanced Download Manager</p>
            </div>
            
            <div class="card">
                <h2 class="text-xl font-semibold mb-6 text-center">Welcome Back</h2>
                
                {% if error %}
                <div class="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg mb-4 flex items-center">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    {{ error }}
                </div>
                {% endif %}
                
                <form method="POST" action="/login" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Username</label>
                        <input name="username" type="text" placeholder="Enter username" 
                               class="w-full px-4 py-3 focus:ring-2 focus:ring-blue-500" required>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Password</label>
                        <input name="password" type="password" placeholder="Enter password" 
                               class="w-full px-4 py-3 focus:ring-2 focus:ring-blue-500" required>
                    </div>
                    
                    <button type="submit" class="w-full py-3 btn-accent rounded-lg font-medium flex items-center justify-center">
                        <i class="fas fa-sign-in-alt mr-2"></i>
                        Sign In
                    </button>
                </form>
            </div>
            
            <div class="text-center mt-6 text-gray-500 text-sm">
                <p>Professional Download Manager v2.0</p>
                <p>Multi-Engine • Multi-Platform • Ultra Fast</p>
            </div>
        </div>
    </div>
    {% else %}
    <!-- Main Professional Interface -->
    <div class="flex h-screen bg-gray-900">
        <!-- Sidebar -->
        <div class="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
            <!-- Logo -->
            <div class="p-6 border-b border-gray-700">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                        <i class="fas fa-download text-white"></i>
                    </div>
                    <div>
                        <h1 class="font-bold text-lg">Pro DM</h1>
                        <p class="text-xs text-gray-400">v2.0 Professional</p>
                    </div>
                </div>
            </div>
            
            <!-- Navigation -->
            <nav class="flex-1 p-4">
                <div class="space-y-2">
                    <button onclick="showTab('dashboard')" id="dashboardTab" 
                            class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg tab-active transition-all">
                        <i class="fas fa-tachometer-alt"></i>
                        <span>Dashboard</span>
                    </button>
                    
                    <button onclick="showTab('download')" id="downloadTab" 
                            class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg surface-hover transition-all">
                        <i class="fas fa-download"></i>
                        <span>Downloads</span>
                        <span id="downloadCount" class="ml-auto badge bg-blue-600 text-white">0</span>
                    </button>
                    
                    <button onclick="showTab('upload')" id="uploadTab" 
                            class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg surface-hover transition-all">
                        <i class="fas fa-upload"></i>
                        <span>Uploads</span>
                        <span id="uploadCount" class="ml-auto badge bg-green-600 text-white">0</span>
                    </button>
                    
                    <button onclick="showTab('files')" id="filesTab" 
                            class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg surface-hover transition-all">
                        <i class="fas fa-folder"></i>
                        <span>Files</span>
                    </button>
                    
                    <button onclick="showTab('analytics')" id="analyticsTab" 
                            class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg surface-hover transition-all">
                        <i class="fas fa-chart-line"></i>
                        <span>Analytics</span>
                    </button>
                    
                    <button onclick="showTab('settings')" id="settingsTab" 
                            class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg surface-hover transition-all">
                        <i class="fas fa-cog"></i>
                        <span>Settings</span>
                    </button>
                </div>
            </nav>
            
            <!-- User Menu -->
            <div class="p-4 border-t border-gray-700">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                            <i class="fas fa-user text-sm"></i>
                        </div>
                        <span class="text-sm">Admin</span>
                    </div>
                    <a href="/logout" class="text-gray-400 hover:text-white transition-colors">
                        <i class="fas fa-sign-out-alt"></i>
                    </a>
                </div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="flex-1 flex flex-col overflow-hidden">
            <!-- Header -->
            <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <h2 id="pageTitle" class="text-xl font-semibold">Dashboard</h2>
                        <div class="flex items-center space-x-2">
                            <div class="status-dot bg-green-500 animate-pulse" id="statusDot"></div>
                            <span class="text-sm text-gray-400" id="statusText">Online</span>
                        </div>
                    </div>
                    
                    <div class="flex items-center space-x-4">
                        <!-- Speed Indicator -->
                        <div class="flex items-center space-x-2 text-sm">
                            <i class="fas fa-tachometer-alt text-blue-400"></i>
                            <span id="totalSpeed">0 KB/s</span>
                        </div>
                        
                        <!-- Active Downloads -->
                        <div class="flex items-center space-x-2 text-sm">
                            <i class="fas fa-download text-green-400"></i>
                            <span id="activeDownloads">0/4</span>
                        </div>
                        
                        <!-- Telegram Queue -->
                        <div class="flex items-center space-x-2 text-sm">
                            <i class="fab fa-telegram text-blue-400"></i>
                            <span id="telegramQueue">0</span>
                        </div>
                        
                        <!-- Quick Actions -->
                        <button onclick="openDownloadsFolder()" class="btn-accent px-3 py-1 rounded-lg text-sm">
                            <i class="fas fa-folder-open mr-1"></i>
                            Folder
                        </button>
                    </div>
                </div>
            </header>
            
            <!-- Content Area -->
            <main class="flex-1 overflow-y-auto p-6">
                <!-- Dashboard Panel -->
                <div id="dashboardPanel" class="space-y-6">
                    <!-- Statistics Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <div class="card">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="text-gray-400 text-sm">Total Downloads</p>
                                    <p class="text-2xl font-bold" id="totalDownloads">0</p>
                                </div>
                                <div class="w-12 h-12 bg-blue-600/20 rounded-lg flex items-center justify-center">
                                    <i class="fas fa-download text-blue-400 text-xl"></i>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="text-gray-400 text-sm">Active Downloads</p>
                                    <p class="text-2xl font-bold" id="activeDownloadsCount">0</p>
                                </div>
                                <div class="w-12 h-12 bg-green-600/20 rounded-lg flex items-center justify-center">
                                    <i class="fas fa-play text-green-400 text-xl animate-bounce"></i>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="text-gray-400 text-sm">Completed</p>
                                    <p class="text-2xl font-bold" id="completedDownloads">0</p>
                                </div>
                                <div class="w-12 h-12 bg-green-600/20 rounded-lg flex items-center justify-center">
                                    <i class="fas fa-check text-green-400 text-xl"></i>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="text-gray-400 text-sm">Total Size</p>
                                    <p class="text-2xl font-bold" id="totalSize">0 GB</p>
                                </div>
                                <div class="w-12 h-12 bg-purple-600/20 rounded-lg flex items-center justify-center">
                                    <i class="fas fa-hdd text-purple-400 text-xl"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Quick Start -->
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-rocket mr-2 text-blue-400"></i>
                            Quick Start
                        </h3>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="space-y-3">
                                <input id="quickUrl" type="url" placeholder="Paste any URL here..." 
                                       class="w-full px-4 py-3 text-sm">
                                
                                <div class="flex space-x-2">
                                    <select id="quickQuality" class="flex-1 px-3 py-2 text-sm">
                                        <option value="best">Best Quality</option>
                                        <option value="1080p">1080p</option>
                                        <option value="720p">720p</option>
                                        <option value="480p">480p</option>
                                        <option value="audio">Audio Only</option>
                                    </select>
                                    
                                    <button onclick="quickDownload()" class="btn-accent px-6 py-2 rounded-lg">
                                        <i class="fas fa-download mr-2"></i>
                                        Download
                                    </button>
                                </div>
                            </div>
                            
                            <div class="text-sm text-gray-400">
                                <p class="mb-2"><strong>Supported platforms:</strong></p>
                                <div class="flex flex-wrap gap-2">
                                    <span class="badge bg-red-600">YouTube</span>
                                    <span class="badge bg-pink-600">Instagram</span>
                                    <span class="badge bg-blue-600">Twitter</span>
                                    <span class="badge bg-black">TikTok</span>
                                    <span class="badge bg-blue-800">Facebook</span>
                                    <span class="badge bg-gray-600">Direct Files</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Activity -->
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-history mr-2 text-green-400"></i>
                            Recent Activity
                        </h3>
                        <div id="recentActivity" class="space-y-3">
                            <div class="text-center text-gray-500 py-4">
                                <i class="fas fa-inbox text-2xl mb-2"></i>
                                <p>No recent activity</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Engine Performance -->
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-engine mr-2 text-orange-400"></i>
                            Engine Performance
                        </h3>
                        <div id="enginePerformance" class="space-y-3">
                            <div class="text-center text-gray-500 py-4">
                                <i class="fas fa-chart-bar text-2xl mb-2"></i>
                                <p>Loading performance data...</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Download Panel -->
                <div id="downloadPanel" class="hidden space-y-6">
                    <!-- Add Download -->
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-plus mr-2 text-blue-400"></i>
                            Add New Download
                        </h3>
                        
                        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            <div class="lg:col-span-2 space-y-4">
                                <input id="downloadUrl" type="url" placeholder="https://example.com/file.zip or YouTube URL" 
                                       class="w-full px-4 py-3 text-sm">
                                
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <textarea id="downloadDescription" placeholder="Description (optional)" 
                                            class="px-4 py-3 text-sm resize-none h-24"></textarea>
                                    <textarea id="downloadTags" placeholder="Tags (comma separated)" 
                                            class="px-4 py-3 text-sm resize-none h-24"></textarea>
                                </div>
                                
                                <div class="flex space-x-4">
                                    <select id="downloadQuality" class="flex-1 px-3 py-2 text-sm">
                                        <option value="best">Best Quality</option>
                                        <option value="1080p">1080p</option>
                                        <option value="720p">720p</option>
                                        <option value="480p">480p</option>
                                    </select>
                                    
                                    <label class="flex items-center space-x-2 text-sm">
                                        <input type="checkbox" id="extractAudio" class="rounded">
                                        <span>Extract Audio</span>
                                    </label>
                                </div>
                            </div>
                            
                            <div class="space-y-4">
                                <button onclick="addDownload()" id="addDownloadBtn" 
                                        class="w-full btn-accent py-3 rounded-lg font-medium">
                                    <i class="fas fa-download mr-2"></i>
                                    Start Download
                                </button>
                                
                                <div class="text-sm text-gray-400">
                                    <p class="mb-2"><strong>Features:</strong></p>
                                    <ul class="space-y-1">
                                        <li><i class="fas fa-check text-green-400 mr-2"></i>Multi-engine support</li>
                                        <li><i class="fas fa-check text-green-400 mr-2"></i>Resume capability</li>
                                        <li><i class="fas fa-check text-green-400 mr-2"></i>Auto Telegram upload</li>
                                        <li><i class="fas fa-check text-green-400 mr-2"></i>Format conversion</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Download Queue -->
                    <div class="card">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-semibold flex items-center">
                                <i class="fas fa-list mr-2 text-green-400"></i>
                                Download Queue
                            </h3>
                            
                            <div class="flex space-x-2">
                                <button onclick="pauseAllDownloads()" class="btn-warning px-3 py-1 rounded text-sm">
                                    <i class="fas fa-pause mr-1"></i>
                                    Pause All
                                </button>
                                <button onclick="clearCompleted()" class="btn-error px-3 py-1 rounded text-sm">
                                    <i class="fas fa-trash mr-1"></i>
                                    Clear Completed
                                </button>
                                <button onclick="refreshDownloads()" class="surface px-3 py-1 rounded text-sm">
                                    <i class="fas fa-refresh mr-1"></i>
                                    Refresh
                                </button>
                            </div>
                        </div>
                        
                        <div id="downloadsList" class="space-y-3 max-h-96 overflow-y-auto">
                            <div class="text-center text-gray-500 py-8">
                                <i class="fas fa-download text-3xl mb-3"></i>
                                <p class="text-lg">No downloads yet</p>
                                <p class="text-sm">Add a URL above to start downloading</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Upload Panel -->
                <div id="uploadPanel" class="hidden space-y-6">
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-cloud-upload-alt mr-2 text-green-400"></i>
                            Upload Files to Telegram
                        </h3>
                        
                        <div class="space-y-4">
                            <div class="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-blue-500 transition-colors" 
                                 id="dropZone">
                                <input type="file" id="fileInput" multiple class="hidden" onchange="handleFileSelect()">
                                <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-4"></i>
                                <p class="text-lg mb-2">Drag & Drop Files Here</p>
                                <p class="text-gray-400 mb-4">or</p>
                                <button onclick="document.getElementById('fileInput').click()" 
                                        class="btn-accent px-6 py-3 rounded-lg font-medium">
                                    <i class="fas fa-folder-open mr-2"></i>
                                    Choose Files
                                </button>
                                <p class="text-sm text-gray-500 mt-4">
                                    Max size: 4GB per file • Supports all formats
                                </p>
                            </div>
                            
                            <div id="selectedFilesList" class="hidden">
                                <h4 class="font-semibold mb-3">Selected Files:</h4>
                                <div id="selectedFilesContainer" class="space-y-2"></div>
                            </div>
                            
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <textarea id="uploadDescription" placeholder="Description (optional)" 
                                        class="px-4 py-3 text-sm resize-none h-24"></textarea>
                                <textarea id="uploadTags" placeholder="Tags (comma separated)" 
                                        class="px-4 py-3 text-sm resize-none h-24"></textarea>
                            </div>
                            
                            <button onclick="uploadFiles()" id="uploadBtn" 
                                    class="w-full btn-success py-3 rounded-lg font-medium">
                                <i class="fas fa-upload mr-2"></i>
                                Upload to Telegram
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Files Panel -->
                <div id="filesPanel" class="hidden space-y-6">
                    <div class="card">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-semibold flex items-center">
                                <i class="fas fa-folder mr-2 text-yellow-400"></i>
                                File Manager
                            </h3>
                            
                            <div class="flex space-x-2">
                                <select id="fileTypeFilter" class="px-3 py-1 text-sm rounded">
                                    <option value="">All Types</option>
                                    <option value="video">Videos</option>
                                    <option value="audio">Audio</option>
                                    <option value="image">Images</option>
                                    <option value="document">Documents</option>
                                </select>
                                
                                <button onclick="refreshFiles()" class="surface px-3 py-1 rounded text-sm">
                                    <i class="fas fa-refresh mr-1"></i>
                                    Refresh
                                </button>
                            </div>
                        </div>
                        
                        <div id="filesList" class="space-y-3 max-h-96 overflow-y-auto">
                            <div class="text-center text-gray-500 py-8">
                                <i class="fas fa-folder-open text-3xl mb-3"></i>
                                <p>Loading files...</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Analytics Panel -->
                <div id="analyticsPanel" class="hidden space-y-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div class="card">
                            <h3 class="text-lg font-semibold mb-4 flex items-center">
                                <i class="fas fa-chart-line mr-2 text-blue-400"></i>
                                Download Statistics
                            </h3>
                            <div id="downloadStats" class="space-y-4">
                                <div class="text-center text-gray-500 py-4">
                                    <i class="fas fa-chart-bar text-2xl mb-2"></i>
                                    <p>Loading statistics...</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <h3 class="text-lg font-semibold mb-4 flex items-center">
                                <i class="fas fa-engine mr-2 text-orange-400"></i>
                                Engine Performance
                            </h3>
                            <div id="engineStats" class="space-y-4">
                                <div class="text-center text-gray-500 py-4">
                                    <i class="fas fa-cogs text-2xl mb-2"></i>
                                    <p>Loading engine data...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-database mr-2 text-purple-400"></i>
                            Storage Information
                        </h3>
                        <div id="storageInfo" class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="text-center text-gray-500 py-4">
                                <i class="fas fa-hdd text-2xl mb-2"></i>
                                <p>Loading storage data...</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Settings Panel -->
                <div id="settingsPanel" class="hidden space-y-6">
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-cog mr-2 text-gray-400"></i>
                            General Settings
                        </h3>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div class="space-y-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-400 mb-2">Max Concurrent Downloads</label>
                                    <input type="number" id="maxConcurrent" min="1" max="10" value="4" 
                                           class="w-full px-3 py-2 text-sm">
                                </div>
                                
                                <div>
                                    <label class="block text-sm font-medium text-gray-400 mb-2">Default Quality</label>
                                    <select id="defaultQuality" class="w-full px-3 py-2 text-sm">
                                        <option value="best">Best Quality</option>
                                        <option value="1080p">1080p</option>
                                        <option value="720p">720p</option>
                                        <option value="480p">480p</option>
                                    </select>
                                </div>
                                
                                <div>
                                    <label class="flex items-center space-x-2 text-sm">
                                        <input type="checkbox" id="autoTelegramUpload" checked class="rounded">
                                        <span>Auto Upload to Telegram</span>
                                    </label>
                                </div>
                            </div>
                            
                            <div class="space-y-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-400 mb-2">Telegram Bot Token</label>
                                    <input type="password" id="telegramToken" placeholder="Enter bot token" 
                                           class="w-full px-3 py-2 text-sm">
                                </div>
                                
                                <div>
                                    <label class="block text-sm font-medium text-gray-400 mb-2">Telegram Channel ID</label>
                                    <input type="text" id="telegramChannel" placeholder="Enter channel ID" 
                                           class="w-full px-3 py-2 text-sm">
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex justify-end mt-6">
                            <button onclick="saveSettings()" class="btn-success px-6 py-2 rounded-lg">
                                <i class="fas fa-save mr-2"></i>
                                Save Settings
                            </button>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3 class="text-lg font-semibold mb-4 flex items-center">
                            <i class="fas fa-tools mr-2 text-yellow-400"></i>
                            Maintenance
                        </h3>
                        
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <button onclick="cleanupFiles()" class="btn-warning py-3 rounded-lg">
                                <i class="fas fa-broom mr-2"></i>
                                Cleanup Files
                            </button>
                            
                            <button onclick="clearDatabase()" class="btn-error py-3 rounded-lg">
                                <i class="fas fa-database mr-2"></i>
                                Clear Database
                            </button>
                            
                            <button onclick="exportLogs()" class="surface py-3 rounded-lg">
                                <i class="fas fa-download mr-2"></i>
                                Export Logs
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>
    
    <!-- Toast Container -->
    <div id="toastContainer" class="fixed top-4 right-4 z-50 space-y-2"></div>
    {% endif %}

    <script>
        // Global state
        let currentTab = 'dashboard';
        let downloads = {};
        let uploads = {};
        let stats = {};
        let updateInterval;
        
        // Initialize app
        {% if session.logged_in %}
        document.addEventListener('DOMContentLoaded', function() {
            initializeApp();
        });
        
        function initializeApp() {
            // Start real-time updates
            updateInterval = setInterval(updateData, 2000);
            updateData();
            
            // Setup event listeners
            setupEventListeners();
            
            // Load initial data
            loadDashboard();
            
            console.log('Professional Download Manager initialized');
        }
        
        function setupEventListeners() {
            // URL input enter key
            document.getElementById('quickUrl')?.addEventListener('keypress', e => {
                if (e.key === 'Enter') quickDownload();
            });
            
            document.getElementById('downloadUrl')?.addEventListener('keypress', e => {
                if (e.key === 'Enter') addDownload();
            });
            
            // Drag and drop for uploads
            const dropZone = document.getElementById('dropZone');
            if (dropZone) {
                dropZone.addEventListener('dragover', handleDragOver);
                dropZone.addEventListener('dragleave', handleDragLeave);
                dropZone.addEventListener('drop', handleDrop);
            }
            
            // File type filter
            document.getElementById('fileTypeFilter')?.addEventListener('change', filterFiles);
        }
        
        // Tab Management
        function showTab(tabName) {
            // Hide all panels
            document.querySelectorAll('[id$="Panel"]').forEach(panel => {
                panel.classList.add('hidden');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('[id$="Tab"]').forEach(tab => {
                tab.classList.remove('tab-active');
                tab.classList.add('surface-hover');
            });
            
            // Show selected panel
            document.getElementById(tabName + 'Panel')?.classList.remove('hidden');
            
            // Activate selected tab
            const tab = document.getElementById(tabName + 'Tab');
            if (tab) {
                tab.classList.add('tab-active');
                tab.classList.remove('surface-hover');
            }
            
            // Update page title
            document.getElementById('pageTitle').textContent = tabName.charAt(0).toUpperCase() + tabName.slice(1);
            
            currentTab = tabName;
            
            // Load tab-specific data
            switch(tabName) {
                case 'dashboard':
                    loadDashboard();
                    break;
                case 'files':
                    loadFiles();
                    break;
                case 'analytics':
                    loadAnalytics();
                    break;
                case 'settings':
                    loadSettings();
                    break;
            }
        }
        
        // Data Updates
        async function updateData() {
            try {
                const response = await fetch('/api/data');
                if (!response.ok) {
                    if (response.status === 302 || response.status === 401) {
                        window.location.reload();
                        return;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                downloads = data.downloads || {};
                uploads = data.uploads || {};
                stats = data.stats || {};
                
                updateUI();
                
            } catch (error) {
                console.error('Update failed:', error);
                updateStatusIndicator(false);
            }
        }
        
        function updateUI() {
            updateHeaderStats();
            updateStatusIndicator(true);
            
            if (currentTab === 'dashboard') {
                updateDashboard();
            } else if (currentTab === 'download') {
                renderDownloads();
            } else if (currentTab === 'files') {
                renderFiles();
            }
        }
        
        function updateHeaderStats() {
            const downloadStats = stats.downloads || {};
            
            document.getElementById('totalSpeed').textContent = formatSpeed(stats.speed || 0);
            document.getElementById('activeDownloads').textContent = `${downloadStats.downloading || 0}/4`;
            document.getElementById('telegramQueue').textContent = stats.telegram_queue || 0;
            
            // Update sidebar counters
            document.getElementById('downloadCount').textContent = downloadStats.total || 0;
            document.getElementById('uploadCount').textContent = Object.keys(uploads).length || 0;
        }
        
        function updateStatusIndicator(online) {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            
            if (online) {
                dot.className = 'status-dot bg-green-500 animate-pulse';
                text.textContent = 'Online';
            } else {
                dot.className = 'status-dot bg-red-500';
                text.textContent = 'Offline';
            }
        }
        
        // Dashboard Functions
        function loadDashboard() {
            updateDashboardStats();
            loadRecentActivity();
            loadEnginePerformance();
        }
        
        function updateDashboard() {
            updateDashboardStats();
        }
        
        function updateDashboardStats() {
            const downloadStats = stats.downloads || {};
            
            document.getElementById('totalDownloads').textContent = downloadStats.total || 0;
            document.getElementById('activeDownloadsCount').textContent = downloadStats.downloading || 0;
            document.getElementById('completedDownloads').textContent = downloadStats.completed || 0;
            
            // Calculate total size
            let totalSize = 0;
            Object.values(downloads).forEach(download => {
                if (download.status === 'completed') {
                    totalSize += download.size || 0;
                }
            });
            document.getElementById('totalSize').textContent = formatSize(totalSize);
        }
        
        async function loadRecentActivity() {
            try {
                const response = await fetch('/api/recent-activity');
                const activities = await response.json();
                
                const container = document.getElementById('recentActivity');
                if (activities.length === 0) {
                    container.innerHTML = `
                        <div class="text-center text-gray-500 py-4">
                            <i class="fas fa-inbox text-2xl mb-2"></i>
                            <p>No recent activity</p>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = activities.map(activity => `
                    <div class="flex items-center space-x-3 p-3 surface rounded-lg">
                        <i class="fas fa-${getActivityIcon(activity.type)} text-blue-400"></i>
                        <div class="flex-1">
                            <p class="text-sm">${activity.description}</p>
                            <p class="text-xs text-gray-400">${formatTime(activity.timestamp)}</p>
                        </div>
                        <span class="badge bg-${getActivityColor(activity.type)}-600">${activity.type}</span>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Failed to load recent activity:', error);
            }
        }
        
        async function loadEnginePerformance() {
            try {
                const response = await fetch('/api/engine-performance');
                const engines = await response.json();
                
                const container = document.getElementById('enginePerformance');
                if (Object.keys(engines).length === 0) {
                    container.innerHTML = `
                        <div class="text-center text-gray-500 py-4">
                            <i class="fas fa-chart-bar text-2xl mb-2"></i>
                            <p>No performance data available</p>
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = Object.entries(engines).map(([name, perf]) => `
                    <div class="flex items-center justify-between p-3 surface rounded-lg">
                        <div class="flex items-center space-x-3">
                            <i class="fas fa-${getEngineIcon(name)} text-orange-400"></i>
                            <div>
                                <p class="font-medium">${name}</p>
                                <p class="text-xs text-gray-400">${perf.total_attempts} attempts</p>
                            </div>
                        </div>
                        <div class="text-right">
                            <p class="text-sm font-medium">${perf.success_rate.toFixed(1)}%</p>
                            <p class="text-xs text-gray-400">${formatDuration(perf.avg_duration)}</p>
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Failed to load engine performance:', error);
            }
        }
        
        // Download Functions
        async function quickDownload() {
            const url = document.getElementById('quickUrl').value.trim();
            const quality = document.getElementById('quickQuality').value;
            
            if (!url) {
                showToast('Please enter a URL', 'error');
                return;
            }
            
            const success = await startDownload(url, '', '', quality, false);
            if (success) {
                document.getElementById('quickUrl').value = '';
                showTab('download');
            }
        }
        
        async function addDownload() {
            const url = document.getElementById('downloadUrl').value.trim();
            const description = document.getElementById('downloadDescription').value.trim();
            const tags = document.getElementById('downloadTags').value.trim();
            const quality = document.getElementById('downloadQuality').value;
            const extractAudio = document.getElementById('extractAudio').checked;
            
            if (!url) {
                showToast('Please enter a URL', 'error');
                return;
            }
            
            const success = await startDownload(url, description, tags, quality, extractAudio);
            if (success) {
                // Clear form
                document.getElementById('downloadUrl').value = '';
                document.getElementById('downloadDescription').value = '';
                document.getElementById('downloadTags').value = '';
                document.getElementById('extractAudio').checked = false;
            }
        }
        
        async function startDownload(url, description, tags, quality, extractAudio) {
            const button = document.getElementById('addDownloadBtn') || event.target;
            const originalText = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-spinner animate-spin mr-2"></i>Starting...';
            button.disabled = true;
            
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: url,
                        description: description,
                        tags: tags,
                        quality: quality,
                        extract_audio: extractAudio
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast('Download started successfully!', 'success');
                    return true;
                } else {
                    showToast(result.error || 'Failed to start download', 'error');
                    return false;
                }
                
            } catch (error) {
                showToast('Network error occurred', 'error');
                console.error('Download error:', error);
                return false;
            } finally {
                button.innerHTML = originalText;
                button.disabled = false;
            }
        }
        
        function renderDownloads() {
            const container = document.getElementById('downloadsList');
            const downloadArray = Object.values(downloads);
            
            if (downloadArray.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <i class="fas fa-download text-3xl mb-3"></i>
                        <p class="text-lg">No downloads yet</p>
                        <p class="text-sm">Add a URL above to start downloading</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = downloadArray.map(download => createDownloadCard(download)).join('');
        }
        
        function createDownloadCard(download) {
            const progress = Math.round(download.progress || 0);
            const status = getDownloadStatus(download.status);
            const controls = getDownloadControls(download.id, download.status);
            
            return `
                <div class="card fade-in">
                    <div class="flex items-center space-x-4">
                        <!-- Status Icon -->
                        <div class="w-12 h-12 ${status.bgColor} rounded-lg flex items-center justify-center">
                            <i class="fas fa-${status.icon} ${status.textColor} ${status.animation}"></i>
                        </div>
                        
                        <!-- File Info -->
                        <div class="flex-1 min-w-0">
                            <h4 class="font-medium truncate" title="${download.filename}">${download.filename}</h4>
                            <div class="flex items-center space-x-4 text-sm text-gray-400 mt-1">
                                <span>
                                    <i class="fas fa-${getPlatformIcon(download.platform)} mr-1"></i>
                                    ${download.platform}
                                </span>
                                <span>
                                    <i class="fas fa-cog mr-1"></i>
                                    ${download.engine}
                                </span>
                                <span>
                                    <i class="fas fa-hdd mr-1"></i>
                                    ${formatSize(download.downloaded || 0)}${download.size ? ` / ${formatSize(download.size)}` : ''}
                                </span>
                                ${download.status === 'downloading' ? `
                                    <span>
                                        <i class="fas fa-tachometer-alt mr-1"></i>
                                        ${formatSpeed(download.speed || 0)}
                                    </span>
                                ` : ''}
                            </div>
                            
                            ${download.description ? `
                                <p class="text-sm text-gray-500 mt-2">${download.description}</p>
                            ` : ''}
                            
                            <!-- Progress Bar -->
                            ${(download.status === 'downloading' || download.status === 'paused') && download.size > 0 ? `
                                <div class="mt-3">
                                    <div class="flex items-center justify-between text-xs text-gray-400 mb-1">
                                        <span>${progress}%</span>
                                        ${download.eta ? `<span>ETA: ${formatDuration(download.eta)}</span>` : ''}
                                    </div>
                                    <div class="w-full bg-gray-700 rounded-full h-2">
                                        <div class="gradient-progress h-2 rounded-full transition-all duration-300" 
                                             style="width: ${progress}%"></div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${download.error_message ? `
                                <div class="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-400">
                                    <i class="fas fa-exclamation-triangle mr-1"></i>
                                    ${download.error_message}
                                </div>
                            ` : ''}
                        </div>
                        
                        <!-- Actions -->
                        <div class="flex items-center space-x-2">
                            ${download.share_link ? `
                                <a href="${download.share_link}" target="_blank" 
                                   class="tooltip p-2 surface rounded-lg hover:bg-blue-600/20" 
                                   data-tooltip="Open in Telegram">
                                    <i class="fab fa-telegram text-blue-400"></i>
                                </a>
                            ` : ''}
                            
                            ${controls}
                        </div>
                    </div>
                </div>
            `;
        }
        
        function getDownloadStatus(status) {
            const statusMap = {
                downloading: {
                    icon: 'download',
                    textColor: 'text-blue-400',
                    bgColor: 'bg-blue-600/20',
                    animation: 'animate-bounce'
                },
                completed: {
                    icon: 'check',
                    textColor: 'text-green-400',
                    bgColor: 'bg-green-600/20',
                    animation: ''
                },
                paused: {
                    icon: 'pause',
                    textColor: 'text-yellow-400',
                    bgColor: 'bg-yellow-600/20',
                    animation: ''
                },
                error: {
                    icon: 'exclamation-triangle',
                    textColor: 'text-red-400',
                    bgColor: 'bg-red-600/20',
                    animation: ''
                },
                initializing: {
                    icon: 'cog',
                    textColor: 'text-gray-400',
                    bgColor: 'bg-gray-600/20',
                    animation: 'animate-spin'
                }
            };
            
            return statusMap[status] || statusMap.error;
        }
        
        function getDownloadControls(id, status) {
            const btnClass = 'p-2 surface rounded-lg hover:bg-gray-600/50 tooltip';
            
            switch (status) {
                case 'downloading':
                    return `
                        <button onclick="controlDownload('${id}', 'pause')" 
                                class="${btnClass}" data-tooltip="Pause">
                            <i class="fas fa-pause text-yellow-400"></i>
                        </button>
                        <button onclick="controlDownload('${id}', 'cancel')" 
                                class="${btnClass}" data-tooltip="Cancel">
                            <i class="fas fa-times text-red-400"></i>
                        </button>
                    `;
                    
                case 'paused':
                    return `
                        <button onclick="controlDownload('${id}', 'resume')" 
                                class="${btnClass}" data-tooltip="Resume">
                            <i class="fas fa-play text-green-400"></i>
                        </button>
                        <button onclick="controlDownload('${id}', 'cancel')" 
                                class="${btnClass}" data-tooltip="Cancel">
                            <i class="fas fa-times text-red-400"></i>
                        </button>
                    `;
                    
                case 'completed':
                case 'error':
                    return `
                        <button onclick="controlDownload('${id}', 'remove')" 
                                class="${btnClass}" data-tooltip="Remove">
                            <i class="fas fa-trash text-red-400"></i>
                        </button>
                    `;
                    
                default:
                    return `
                        <button onclick="controlDownload('${id}', 'remove')" 
                                class="${btnClass}" data-tooltip="Remove">
                            <i class="fas fa-trash text-red-400"></i>
                        </button>
                    `;
            }
        }
        
        async function controlDownload(id, action) {
            try {
                const response = await fetch('/api/download/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, action })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`Download ${action}ed successfully`, 'success');
                } else {
                    showToast(result.error || `Failed to ${action} download`, 'error');
                }
                
            } catch (error) {
                showToast(`Failed to ${action} download`, 'error');
                console.error('Control error:', error);
            }
        }
        
        // Upload Functions
        function handleFileSelect() {
            const files = Array.from(document.getElementById('fileInput').files);
            displaySelectedFiles(files);
        }
        
        function handleDragOver(e) {
            e.preventDefault();
            e.currentTarget.classList.add('border-blue-500', 'bg-blue-500/5');
        }
        
        function handleDragLeave(e) {
            e.preventDefault();
            e.currentTarget.classList.remove('border-blue-500', 'bg-blue-500/5');
        }
        
        function handleDrop(e) {
            e.preventDefault();
            e.currentTarget.classList.remove('border-blue-500', 'bg-blue-500/5');
            
            const files = Array.from(e.dataTransfer.files);
            document.getElementById('fileInput').files = e.dataTransfer.files;
            displaySelectedFiles(files);
        }
        
        function displaySelectedFiles(files) {
            const container = document.getElementById('selectedFilesContainer');
            const listDiv = document.getElementById('selectedFilesList');
            
            if (files.length === 0) {
                listDiv.classList.add('hidden');
                return;
            }
            
            listDiv.classList.remove('hidden');
            
            container.innerHTML = files.map((file, index) => `
                <div class="flex items-center justify-between p-3 surface rounded-lg">
                    <div class="flex items-center space-x-3">
                        <i class="fas fa-${getFileIcon(file.name)} text-blue-400"></i>
                        <div>
                            <p class="font-medium">${file.name}</p>
                            <p class="text-sm text-gray-400">${formatSize(file.size)}</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="badge ${file.size > 4 * 1024 * 1024 * 1024 ? 'bg-red-600' : 'bg-green-600'}">
                            ${file.size > 4 * 1024 * 1024 * 1024 ? 'Too Large' : 'Ready'}
                        </span>
                        <button onclick="removeFile(${index})" class="p-1 text-red-400 hover:text-red-300">
                            <i class="fas fa-times"></i>
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
            displaySelectedFiles(Array.from(fileInput.files));
        }
        
        async function uploadFiles() {
            const fileInput = document.getElementById('fileInput');
            const description = document.getElementById('uploadDescription').value.trim();
            const tags = document.getElementById('uploadTags').value.trim();
            const button = document.getElementById('uploadBtn');
            
            if (fileInput.files.length === 0) {
                showToast('Please select files first', 'error');
                return;
            }
            
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner animate-spin mr-2"></i>Uploading...';
            button.disabled = true;
            
            try {
                const formData = new FormData();
                Array.from(fileInput.files).forEach(file => {
                    if (file.size <= 4 * 1024 * 1024 * 1024) { // 4GB limit
                        formData.append('files', file);
                    }
                });
                formData.append('description', description);
                formData.append('tags', tags);
                
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`Successfully uploaded ${result.count} files`, 'success');
                    
                    // Clear form
                    fileInput.value = '';
                    document.getElementById('uploadDescription').value = '';
                    document.getElementById('uploadTags').value = '';
                    document.getElementById('selectedFilesList').classList.add('hidden');
                } else {
                    showToast(result.error || 'Upload failed', 'error');
                }
                
            } catch (error) {
                showToast('Upload error occurred', 'error');
                console.error('Upload error:', error);
            } finally {
                button.innerHTML = originalText;
                button.disabled = false;
            }
        }
        
        // Files Functions
        async function loadFiles() {
            try {
                const response = await fetch('/api/files');
                const result = await response.json();
                renderFiles(result.files);
            } catch (error) {
                console.error('Failed to load files:', error);
            }
        }
        
        function renderFiles(files = null) {
            const container = document.getElementById('filesList');
            const fileArray = files || getAllFiles();
            
            if (fileArray.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <i class="fas fa-folder-open text-3xl mb-3"></i>
                        <p>No files available</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = fileArray.map(file => createFileCard(file)).join('');
        }
        
        function getAllFiles() {
            const downloadFiles = Object.values(downloads).filter(d => d.status === 'completed');
            const uploadFiles = Object.values(uploads);
            
            return [...downloadFiles.map(f => ({...f, type: 'download'})), 
                    ...uploadFiles.map(f => ({...f, type: 'upload'}))];
        }
        
        function createFileCard(file) {
            return `
                <div class="card fade-in">
                    <div class="flex items-center space-x-4">
                        <div class="w-12 h-12 bg-purple-600/20 rounded-lg flex items-center justify-center">
                            <i class="fas fa-${getFileIcon(file.filename || file.original_filename)} text-purple-400"></i>
                        </div>
                        
                        <div class="flex-1 min-w-0">
                            <h4 class="font-medium truncate">${file.filename || file.original_filename}</h4>
                            <div class="flex items-center space-x-4 text-sm text-gray-400 mt-1">
                                <span>
                                    <i class="fas fa-hdd mr-1"></i>
                                    ${formatSize(file.size)}
                                </span>
                                <span>
                                    <i class="fas fa-clock mr-1"></i>
                                    ${formatTime(file.finished_at || file.uploaded_at)}
                                </span>
                                <span class="badge bg-${file.type === 'download' ? 'blue' : 'green'}-600">
                                    ${file.type}
                                </span>
                            </div>
                            
                            ${file.description ? `
                                <p class="text-sm text-gray-500 mt-2">${file.description}</p>
                            ` : ''}
                        </div>
                        
                        <div class="flex items-center space-x-2">
                            ${file.share_link ? `
                                <a href="${file.share_link}" target="_blank" 
                                   class="tooltip p-2 surface rounded-lg hover:bg-blue-600/20" 
                                   data-tooltip="Open in Telegram">
                                    <i class="fab fa-telegram text-blue-400"></i>
                                </a>
                            ` : ''}
                            
                            <button onclick="deleteFile('${file.id}', '${file.type}')" 
                                    class="tooltip p-2 surface rounded-lg hover:bg-red-600/20" 
                                    data-tooltip="Delete">
                                <i class="fas fa-trash text-red-400"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function filterFiles() {
            const filter = document.getElementById('fileTypeFilter').value;
            const allFiles = getAllFiles();
            
            if (!filter) {
                renderFiles(allFiles);
                return;
            }
            
            const filteredFiles = allFiles.filter(file => {
                const filename = file.filename || file.original_filename;
                const fileType = getFileType(filename);
                return fileType === filter;
            });
            
            renderFiles(filteredFiles);
        }
        
        async function deleteFile(id, type) {
            if (!confirm('Are you sure you want to delete this file?')) {
                return;
            }
            
            try {
                const endpoint = type === 'download' ? '/api/download/control' : '/api/upload/control';
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, action: 'remove' })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast('File deleted successfully', 'success');
                    loadFiles();
                } else {
                    showToast(result.error || 'Failed to delete file', 'error');
                }
                
            } catch (error) {
                showToast('Failed to delete file', 'error');
                console.error('Delete error:', error);
            }
        }
        
        // Analytics Functions
        async function loadAnalytics() {
            try {
                const [statsResponse, storageResponse] = await Promise.all([
                    fetch('/api/analytics/stats'),
                    fetch('/api/analytics/storage')
                ]);
                
                const statsData = await statsResponse.json();
                const storageData = await storageResponse.json();
                
                renderAnalytics(statsData, storageData);
                
            } catch (error) {
                console.error('Failed to load analytics:', error);
            }
        }
        
        function renderAnalytics(statsData, storageData) {
            renderDownloadStats(statsData);
            renderEngineStats(statsData.engine_performance);
            renderStorageInfo(storageData);
        }
        
        function renderDownloadStats(stats) {
            const container = document.getElementById('downloadStats');
            const downloadStats = stats.downloads || {};
            
            container.innerHTML = `
                <div class="space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div class="text-center p-4 surface rounded-lg">
                            <div class="text-2xl font-bold text-blue-400">${downloadStats.completed?.count || 0}</div>
                            <div class="text-sm text-gray-400">Completed</div>
                        </div>
                        <div class="text-center p-4 surface rounded-lg">
                            <div class="text-2xl font-bold text-red-400">${downloadStats.error?.count || 0}</div>
                            <div class="text-sm text-gray-400">Failed</div>
                        </div>
                    </div>
                    <div class="text-center p-4 surface rounded-lg">
                        <div class="text-xl font-bold text-green-400">${formatSize(downloadStats.completed?.total_size || 0)}</div>
                        <div class="text-sm text-gray-400">Total Downloaded</div>
                    </div>
                </div>
            `;
        }
        
        function renderEngineStats(engines) {
            const container = document.getElementById('engineStats');
            
            if (!engines || Object.keys(engines).length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-4">
                        <i class="fas fa-cogs text-2xl mb-2"></i>
                        <p>No engine data available</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = Object.entries(engines).map(([name, perf]) => `
                <div class="flex items-center justify-between p-3 surface rounded-lg">
                    <div class="flex items-center space-x-3">
                        <i class="fas fa-${getEngineIcon(name)} text-orange-400"></i>
                        <div>
                            <p class="font-medium">${name}</p>
                            <p class="text-xs text-gray-400">${perf.total_attempts} attempts</p>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="text-sm font-medium">${perf.success_rate.toFixed(1)}%</div>
                        <div class="text-xs text-gray-400">${formatDuration(perf.avg_duration)}</div>
                    </div>
                    <div class="w-20">
                        <div class="w-full bg-gray-700 rounded-full h-2">
                            <div class="bg-orange-400 h-2 rounded-full" style="width: ${perf.success_rate}%"></div>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        function renderStorageInfo(storage) {
            const container = document.getElementById('storageInfo');
            
            container.innerHTML = Object.entries(storage).map(([name, info]) => `
                <div class="text-center p-4 surface rounded-lg">
                    <div class="w-12 h-12 bg-purple-600/20 rounded-lg flex items-center justify-center mx-auto mb-3">
                        <i class="fas fa-${getStorageIcon(name)} text-purple-400"></i>
                    </div>
                    <div class="text-xl font-bold">${formatSize(info.size)}</div>
                    <div class="text-sm text-gray-400">${name.charAt(0).toUpperCase() + name.slice(1)}</div>
                    <div class="text-xs text-gray-500 mt-1">${info.count} files</div>
                </div>
            `).join('');
        }
        
        // Settings Functions
        function loadSettings() {
            // Load current settings from backend or local storage
            // This would typically fetch from your API
        }
        
        async function saveSettings() {
            const settings = {
                maxConcurrent: document.getElementById('maxConcurrent').value,
                defaultQuality: document.getElementById('defaultQuality').value,
                autoTelegramUpload: document.getElementById('autoTelegramUpload').checked,
                telegramToken: document.getElementById('telegramToken').value,
                telegramChannel: document.getElementById('telegramChannel').value
            };
            
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast('Settings saved successfully', 'success');
                } else {
                    showToast(result.error || 'Failed to save settings', 'error');
                }
                
            } catch (error) {
                showToast('Failed to save settings', 'error');
                console.error('Settings error:', error);
            }
        }
        
        // Maintenance Functions
        async function cleanupFiles() {
            if (!confirm('This will remove temporary files. Continue?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/maintenance/cleanup', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`Cleaned up ${result.count} files`, 'success');
                } else {
                    showToast('Cleanup failed', 'error');
                }
                
            } catch (error) {
                showToast('Cleanup failed', 'error');
                console.error('Cleanup error:', error);
            }
        }
        
        async function clearDatabase() {
            if (!confirm('This will clear all download history. This action cannot be undone. Continue?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/maintenance/clear-database', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast('Database cleared successfully', 'success');
                    updateData(); // Refresh data
                } else {
                    showToast('Failed to clear database', 'error');
                }
                
            } catch (error) {
                showToast('Failed to clear database', 'error');
                console.error('Clear database error:', error);
            }
        }
        
        async function exportLogs() {
            try {
                const response = await fetch('/api/maintenance/export-logs');
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `logs_${new Date().toISOString().split('T')[0]}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    showToast('Logs exported successfully', 'success');
                } else {
                    showToast('Failed to export logs', 'error');
                }
                
            } catch (error) {
                showToast('Failed to export logs', 'error');
                console.error('Export logs error:', error);
            }
        }
        
        // Quick Actions
        async function pauseAllDownloads() {
            try {
                const response = await fetch('/api/download/pause-all', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`Paused ${result.count} downloads`, 'success');
                } else {
                    showToast('Failed to pause downloads', 'error');
                }
                
            } catch (error) {
                showToast('Failed to pause downloads', 'error');
                console.error('Pause all error:', error);
            }
        }
        
        async function clearCompleted() {
            try {
                const response = await fetch('/api/download/clear-completed', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`Cleared ${result.count} completed downloads`, 'success');
                } else {
                    showToast('Failed to clear completed downloads', 'error');
                }
                
            } catch (error) {
                showToast('Failed to clear completed downloads', 'error');
                console.error('Clear completed error:', error);
            }
        }
        
        function refreshDownloads() {
            updateData();
            showToast('Downloads refreshed', 'success');
        }
        
        function refreshFiles() {
            if (currentTab === 'files') {
                loadFiles();
                showToast('Files refreshed', 'success');
            }
        }
        
        async function openDownloadsFolder() {
            try {
                await fetch('/api/open-folder', {
                    method: 'POST'
                });
                showToast('Opening downloads folder', 'success');
            } catch (error) {
                showToast('Failed to open folder', 'error');
                console.error('Open folder error:', error);
            }
        }
        
        // Utility Functions
        function formatSize(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }
        
        function formatSpeed(speed) {
            if (!speed || speed === 0) return '0 B/s';
            const k = 1024;
            const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
            const i = Math.floor(Math.log(speed) / Math.log(k));
            return parseFloat((speed / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }
        
        function formatTime(timestamp) {
            if (!timestamp) return 'Unknown';
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;
            
            if (diff < 60000) return 'Just now';
            if (diff < 3600000) return Math.floor(diff / 60000) + ' minutes ago';
            if (diff < 86400000) return Math.floor(diff / 3600000) + ' hours ago';
            return Math.floor(diff / 86400000) + ' days ago';
        }
        
        function formatDuration(seconds) {
            if (!seconds || seconds === 0) return '0s';
            if (seconds < 60) return Math.round(seconds) + 's';
            if (seconds < 3600) return Math.round(seconds / 60) + 'm';
            return Math.round(seconds / 3600) + 'h';
        }
        
        function getPlatformIcon(platform) {
            const icons = {
                youtube: 'play',
                instagram: 'camera',
                twitter: 'twitter',
                tiktok: 'music',
                facebook: 'facebook',
                direct: 'link'
            };
            return icons[platform] || 'link';
        }
        
        function getFileIcon(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            const icons = {
                mp4: 'video', avi: 'video', mkv: 'video', mov: 'video',
                mp3: 'music', wav: 'music', flac: 'music', aac: 'music',
                jpg: 'image', jpeg: 'image', png: 'image', gif: 'image',
                pdf: 'file-pdf', doc: 'file-word', txt: 'file-alt',
                zip: 'file-archive', rar: 'file-archive', '7z': 'file-archive'
            };
            return icons[ext] || 'file';
        }
        
        function getFileType(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            const types = {
                video: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
                audio: ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
                image: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
                document: ['pdf', 'doc', 'docx', 'txt', 'zip', 'rar', '7z']
            };
            
            for (const [type, extensions] of Object.entries(types)) {
                if (extensions.includes(ext)) return type;
            }
            return 'document';
        }
        
        function getEngineIcon(engine) {
            const icons = {
                'yt-dlp': 'play-circle',
                'aria2': 'bolt',
                'requests': 'globe',
                'wget': 'download',
                'curl': 'terminal'
            };
            return icons[engine] || 'cog';
        }
        
        function getStorageIcon(name) {
            const icons = {
                downloads: 'download',
                uploads: 'upload',
                temp: 'clock'
            };
            return icons[name] || 'folder';
        }
        
        function getActivityIcon(type) {
            const icons = {
                download: 'download',
                upload: 'upload',
                complete: 'check',
                error: 'exclamation-triangle'
            };
            return icons[type] || 'info';
        }
        
        function getActivityColor(type) {
            const colors = {
                download: 'blue',
                upload: 'green',
                complete: 'green',
                error: 'red'
            };
            return colors[type] || 'gray';
        }
        
        // Toast System
        function showToast(message, type = 'info', duration = 5000) {
            const container = document.getElementById('toastContainer');
            const toastId = Date.now();
            
            const colors = {
                success: 'bg-green-600',
                error: 'bg-red-600',
                warning: 'bg-yellow-600',
                info: 'bg-blue-600'
            };
            
            const icons = {
                success: 'check',
                error: 'exclamation-triangle',
                warning: 'exclamation',
                info: 'info'
            };
            
            const toast = document.createElement('div');
            toast.id = `toast-${toastId}`;
            toast.className = `${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg transform translate-x-full transition-transform duration-300 flex items-center space-x-3 min-w-80`;
            toast.innerHTML = `
                <i class="fas fa-${icons[type]}"></i>
                <span class="flex-1">${message}</span>
                <button onclick="removeToast('${toastId}')" class="opacity-70 hover:opacity-100 transition-opacity">
                    <i class="fas fa-times"></i>
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
        {% endif %}
    </script>
</body>
</html>"""

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == config.LOGIN_USERNAME and password == config.LOGIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            session['last_activity'] = datetime.now().isoformat()
            
            logger.get_logger('main').info(f"User logged in successfully: {username}")
            return redirect('/')
        else:
            logger.get_logger('main').warning(f"Failed login attempt: {username}")
            return render_template_string(PROFESSIONAL_TEMPLATE, error="Invalid username or password")
    
    return render_template_string(PROFESSIONAL_TEMPLATE)

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    logger.get_logger('main').info(f"User logged out: {username}")
    return redirect('/login')

@app.route('/')
@login_required
def index():
    return render_template_string(PROFESSIONAL_TEMPLATE)

# API Routes
@app.route('/api/data')
@login_required
def api_get_data():
    try:
        # Get all downloads (runtime + database)
        all_downloads = {}
        
        # Add runtime downloads
        for dl_id, dl_data in downloader.downloads.items():
            all_downloads[dl_id] = dl_data
        
        # Add completed downloads from database
        db_downloads = db.get_downloads()
        for db_dl in db_downloads:
            if db_dl['id'] not in all_downloads:
                all_downloads[db_dl['id']] = db_dl
        
        # Check for completed downloads needing Telegram upload
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
                    priority=1  # High priority for completed downloads
                )
        
        # Get upload data
        uploads = {u['id']: u for u in db.get_uploads()}
        
        # Get statistics
        download_stats = downloader.get_stats()
        total_speed = sum(d.get('speed', 0) for d in all_downloads.values() if d.get('status') == 'downloading')
        telegram_status = telegram_bot.get_queue_status()
        
        return jsonify({
            'downloads': all_downloads,
            'uploads': uploads,
            'stats': {
                'downloads': download_stats,
                'speed': total_speed,
                'telegram_queue': telegram_status['queue_length']
            }
        })
        
    except Exception as e:
        logger.get_logger('error').error(f"API data fetch error: {e}")
        return jsonify({
            'downloads': {},
            'uploads': {},
            'stats': {
                'downloads': {'total': 0, 'downloading': 0, 'completed': 0, 'paused': 0, 'failed': 0},
                'speed': 0,
                'telegram_queue': 0
            }
        })

# اضافه کردن این routes به web_interface.py

@app.route('/api/telegram/retry-failed', methods=['POST'])
@login_required
def retry_failed_uploads():
    """Retry failed Telegram uploads"""
    try:
        count = telegram_bot.retry_failed()
        logger.get_logger('main').info(f"Retrying {count} failed uploads")
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Retry failed uploads error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/detailed-status')
@login_required
def get_detailed_telegram_status():
    """Get detailed Telegram bot status"""
    try:
        status = telegram_bot.get_queue_status()
        
        # Add more detailed information
        detailed_status = {
            **status,
            'connection_test': telegram_bot.bot is not None,
            'last_activity': datetime.now().isoformat(),
            'engine_names': [engine['name'] for engine in telegram_bot.upload_engines] if telegram_bot.upload_engines else []
        }
        
        return jsonify(detailed_status)
        
    except Exception as e:
        logger.get_logger('error').error(f"Detailed status error: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/files/cleanup', methods=['POST'])
@login_required
def cleanup_files():
    """Cleanup temporary and locked files"""
    try:
        temp_count = file_manager.cleanup_temp_files()
        file_manager.cleanup_expired_locks()
        
        return jsonify({
            'success': True, 
            'temp_files_cleaned': temp_count,
            'message': f'Cleaned up {temp_count} temporary files'
        })
        
    except Exception as e:
        logger.get_logger('error').error(f"File cleanup error: {e}")
        return jsonify({'success': False, 'error': str(e)})
