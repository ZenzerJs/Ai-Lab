"""
scripts/exp007_templates.py - HTML artifact generators for EXP-007 real-time telemetry benchmark.
"""

def get_exp007_vanilla_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PulseEngine Sandbox - Dynamic API Gateway Simulator</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-900 font-sans min-h-screen p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-4 rounded-lg border border-gray-300 shadow-sm gap-4">
      <div>
        <h1 class="text-xl font-bold">PulseEngine Sandbox (Vanilla Baseline)</h1>
        <p class="text-xs text-gray-500">Dynamic API Gateway Topology & Real-Time Telemetry Simulator</p>
      </div>
      <div class="flex items-center space-x-3">
        <button id="open-settings-btn" class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 border border-gray-300 text-xs font-semibold rounded">
          Threshold Settings
        </button>
        <button id="toggle-chaos" class="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded shadow-sm">
          Toggle Chaos Mode
        </button>
      </div>
    </header>

    <!-- Alert Banner -->
    <div id="alert-banner" class="hidden bg-red-100 border border-red-400 text-red-800 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <span class="font-bold text-xs uppercase px-2 py-0.5 bg-red-200 rounded text-red-900">Alert</span>
        <span>Anomaly detected: p99 threshold breached (142ms latency spike in Billing service)</span>
      </div>
      <span class="text-xs text-red-600 font-mono">ERR_LATENCY_P99</span>
    </div>

    <!-- Controls Bar -->
    <div class="bg-white p-4 rounded-lg border border-gray-300 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4 text-xs">
      <div class="flex items-center space-x-3 w-full md:w-1/2">
        <label class="font-semibold whitespace-nowrap">Throughput (RPS):</label>
        <input type="range" id="rps-slider" min="10000" max="500000" step="5000" value="125000" class="w-full">
        <span id="rps-value" class="font-mono font-bold w-16 text-right">125k</span>
      </div>
      <div class="flex space-x-4 text-gray-600">
        <span>Status: <strong id="gateway-status" class="text-green-600">NORMAL</strong></span>
        <span>Ingestion: <strong>Active</strong></span>
      </div>
    </div>

    <!-- Interactive Topology Canvas -->
    <div id="topology-canvas" class="bg-white p-6 rounded-lg border border-gray-300 shadow-sm relative overflow-hidden">
      <h2 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Service Topology Canvas</h2>
      <svg class="w-full h-64" viewBox="0 0 800 240">
        <!-- Connecting lines -->
        <line x1="130" y1="120" x2="320" y2="60" stroke="#cbd5e1" stroke-width="2" />
        <line x1="130" y1="120" x2="320" y2="120" stroke="#cbd5e1" stroke-width="2" />
        <line x1="130" y1="120" x2="320" y2="180" stroke="#cbd5e1" stroke-width="2" />
        <line x1="440" y1="60" x2="640" y2="120" stroke="#cbd5e1" stroke-width="2" />
        <line x1="440" y1="120" x2="640" y2="120" stroke="#cbd5e1" stroke-width="2" />
        <line x1="440" y1="180" x2="640" y2="120" stroke="#cbd5e1" stroke-width="2" />

        <!-- Nodes -->
        <g data-node="ingress" transform="translate(40, 85)">
          <rect width="90" height="70" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="2" />
          <text x="45" y="32" text-anchor="middle" font-size="11" font-weight="bold" fill="#1e293b">Ingress</text>
          <text x="45" y="50" text-anchor="middle" font-size="10" fill="#64748b">Gateway</text>
        </g>

        <g data-node="auth" transform="translate(320, 25)">
          <rect width="120" height="65" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="1.5" />
          <text x="60" y="30" text-anchor="middle" font-size="11" font-weight="bold" fill="#1e293b">Auth Service</text>
          <text x="60" y="48" text-anchor="middle" font-size="10" fill="#16a34a">Healthy</text>
        </g>

        <g data-node="billing" id="node-billing" transform="translate(320, 90)">
          <rect id="billing-rect" width="120" height="65" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="1.5" />
          <text x="60" y="30" text-anchor="middle" font-size="11" font-weight="bold" fill="#1e293b">Billing Service</text>
          <text id="billing-status" x="60" y="48" text-anchor="middle" font-size="10" fill="#16a34a">Healthy</text>
        </g>

        <g data-node="search" transform="translate(320, 155)">
          <rect width="120" height="65" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="1.5" />
          <text x="60" y="30" text-anchor="middle" font-size="11" font-weight="bold" fill="#1e293b">Search Engine</text>
          <text x="60" y="48" text-anchor="middle" font-size="10" fill="#16a34a">Healthy</text>
        </g>

        <g data-node="sink" transform="translate(640, 85)">
          <rect width="100" height="70" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="2" />
          <text x="50" y="32" text-anchor="middle" font-size="11" font-weight="bold" fill="#1e293b">Influx Sink</text>
          <text x="50" y="50" text-anchor="middle" font-size="10" fill="#64748b">Telemetry DB</text>
        </g>
      </svg>
    </div>

    <!-- Real-Time Metrics Sparklines -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white p-4 rounded-lg border border-gray-300 shadow-sm">
        <div class="flex justify-between text-xs text-gray-500 font-semibold mb-1">
          <span>p50 Latency</span>
          <span id="val-p50" class="font-mono text-gray-900 font-bold">4.2ms</span>
        </div>
        <svg class="w-full h-12" viewBox="0 0 100 30">
          <polyline id="poly-p50" fill="none" stroke="#3b82f6" stroke-width="2" points="0,25 20,22 40,24 60,20 80,21 100,23" />
        </svg>
      </div>

      <div class="bg-white p-4 rounded-lg border border-gray-300 shadow-sm">
        <div class="flex justify-between text-xs text-gray-500 font-semibold mb-1">
          <span>p95 Latency</span>
          <span id="val-p95" class="font-mono text-gray-900 font-bold">12.8ms</span>
        </div>
        <svg class="w-full h-12" viewBox="0 0 100 30">
          <polyline id="poly-p95" fill="none" stroke="#f59e0b" stroke-width="2" points="0,20 20,18 40,22 60,15 80,17 100,19" />
        </svg>
      </div>

      <div class="bg-white p-4 rounded-lg border border-gray-300 shadow-sm">
        <div class="flex justify-between text-xs text-gray-500 font-semibold mb-1">
          <span>p99 Latency</span>
          <span id="val-p99" class="font-mono text-gray-900 font-bold">18.4ms</span>
        </div>
        <svg class="w-full h-12" viewBox="0 0 100 30">
          <polyline id="poly-p99" fill="none" stroke="#ef4444" stroke-width="2" points="0,16 20,14 40,19 60,12 80,15 100,14" />
        </svg>
      </div>
    </div>
  </div>

  <!-- Settings Dialog (Modal) -->
  <div id="settings-dialog" class="hidden fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-lg border border-gray-300 shadow-xl max-w-md w-full p-6 space-y-4">
      <div class="flex justify-between items-center border-b pb-3">
        <h3 class="text-sm font-bold">Threshold Configuration</h3>
        <button id="close-settings-btn" class="text-gray-400 hover:text-gray-600 text-sm font-bold">&times;</button>
      </div>
      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-gray-600 mb-1">p99 Latency Alert Threshold (ms):</label>
          <input type="number" value="25" class="w-full p-2 border rounded font-mono">
        </div>
        <div>
          <label class="block text-gray-600 mb-1">5xx Error Spike Threshold (%):</label>
          <input type="number" value="2.0" step="0.1" class="w-full p-2 border rounded font-mono">
        </div>
      </div>
      <div class="flex justify-end space-x-2 pt-2 border-t">
        <button id="save-settings-btn" class="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded">Save Changes</button>
      </div>
    </div>
  </div>

  <script>
    let chaos = false;
    const alertBanner = document.getElementById('alert-banner');
    const toggleChaosBtn = document.getElementById('toggle-chaos');
    const settingsDialog = document.getElementById('settings-dialog');
    const openSettingsBtn = document.getElementById('open-settings-btn');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const billingRect = document.getElementById('billing-rect');
    const billingStatus = document.getElementById('billing-status');
    const rpsSlider = document.getElementById('rps-slider');
    const rpsVal = document.getElementById('rps-value');

    rpsSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      rpsVal.textContent = Math.round(val / 1000) + 'k';
    });

    toggleChaosBtn.addEventListener('click', () => {
      chaos = !chaos;
      if (chaos) {
        alertBanner.classList.remove('hidden');
        billingRect.setAttribute('stroke', '#ef4444');
        billingRect.setAttribute('fill', '#fef2f2');
        billingStatus.textContent = 'Degraded (p99 > 25ms)';
        billingStatus.setAttribute('fill', '#ef4444');
      } else {
        alertBanner.classList.add('hidden');
        billingRect.setAttribute('stroke', '#64748b');
        billingRect.setAttribute('fill', '#f8fafc');
        billingStatus.textContent = 'Healthy';
        billingStatus.setAttribute('fill', '#16a34a');
      }
    });

    openSettingsBtn.addEventListener('click', () => settingsDialog.classList.remove('hidden'));
    const hideDialog = () => settingsDialog.classList.add('hidden');
    closeSettingsBtn.addEventListener('click', hideDialog);
    saveSettingsBtn.addEventListener('click', hideDialog);

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hideDialog();
    });

    // 800ms metrics ticker
    setInterval(() => {
      const p50 = chaos ? (18 + Math.random() * 8).toFixed(1) : (4 + Math.random() * 2).toFixed(1);
      const p95 = chaos ? (85 + Math.random() * 20).toFixed(1) : (11 + Math.random() * 3).toFixed(1);
      const p99 = chaos ? (142 + Math.random() * 35).toFixed(1) : (17 + Math.random() * 4).toFixed(1);

      document.getElementById('val-p50').textContent = p50 + 'ms';
      document.getElementById('val-p95').textContent = p95 + 'ms';
      document.getElementById('val-p99').textContent = p99 + 'ms';
    }, 800);
  </script>
</body>
</html>
"""


def get_exp007_governed_html() -> str:
    return """<!DOCTYPE html>
<html lang="en" class="dark scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PulseEngine Sandbox | Autonomous API Gateway Telemetry</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              400: '#818cf8',
              500: '#6366f1',
              600: '#4f46e5',
              900: '#1e1b4b',
              950: '#0f172a'
            }
          }
        }
      }
    }
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .font-mono { font-family: 'JetBrains Mono', monospace; }
    .glass-card {
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    @keyframes flow-pulse {
      0% { stroke-dashoffset: 40; }
      100% { stroke-dashoffset: 0; }
    }
    .flow-active {
      stroke-dasharray: 6, 6;
      animation: flow-pulse 1s linear infinite;
    }
    .glow-accent {
      box-shadow: 0 0 25px -5px rgba(99, 102, 241, 0.4);
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-4 md:p-8 antialiased selection:bg-indigo-500 selection:text-white">
  <div class="max-w-6xl mx-auto space-y-6">

    <!-- Header / Navbar -->
    <header class="glass-card p-5 rounded-2xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-xl">
      <div class="flex items-center space-x-3">
        <span class="p-2.5 bg-gradient-to-tr from-indigo-600 to-violet-500 rounded-xl text-white font-extrabold text-sm shadow-lg shadow-indigo-500/30">
          PE
        </span>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-lg font-extrabold tracking-tight text-white">PulseEngine <span class="text-indigo-400">Sandbox</span></h1>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span> Live Ingress
            </span>
          </div>
          <p class="text-xs text-slate-400">Dynamic API Gateway Topology & Autonomous Chaos Simulation</p>
        </div>
      </div>

      <div class="flex items-center space-x-3 w-full sm:w-auto justify-end">
        <button id="open-settings-btn" class="px-3.5 py-2 glass-card hover:border-slate-600 text-xs font-semibold text-slate-300 rounded-xl transition-all flex items-center space-x-2">
          <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          <span>Thresholds</span>
        </button>

        <button id="toggle-chaos" role="switch" aria-checked="false" class="px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-red-500/20 transition-all flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
          <span>Toggle Chaos Mode</span>
        </button>
      </div>
    </header>

    <!-- Alert Banner -->
    <div id="alert-banner" class="hidden bg-red-950/80 border border-red-500/40 text-red-200 px-5 py-4 rounded-2xl text-xs backdrop-blur-md shadow-2xl shadow-red-500/10 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="px-2 py-0.5 rounded bg-red-600 text-white font-bold text-[10px] uppercase tracking-wider">Breach Alert</span>
        <span class="font-medium text-white">Anomaly detected: p99 threshold breached (154.2ms &gt; 25.0ms target in Billing Service)</span>
      </div>
      <span class="font-mono text-red-400 bg-red-900/40 px-2 py-0.5 rounded text-[11px]">CHAOS_INJECTOR_ACTIVE</span>
    </div>

    <!-- Controls Bar -->
    <div class="glass-card p-5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-5 text-xs">
      <div class="flex items-center space-x-4 w-full md:w-1/2">
        <label class="font-semibold text-slate-300 whitespace-nowrap">Load Velocity:</label>
        <input type="range" id="rps-slider" min="10000" max="500000" step="5000" value="145000" class="w-full accent-indigo-500 cursor-pointer">
        <span id="rps-value" class="font-mono text-indigo-400 font-bold w-20 text-right text-sm">145k RPS</span>
      </div>
      <div class="flex items-center space-x-6 text-slate-400">
        <div class="flex items-center space-x-2">
          <span class="text-slate-500">Topology State:</span>
          <span id="topo-state" class="text-emerald-400 font-bold font-mono">NOMINAL</span>
        </div>
        <div class="flex items-center space-x-2">
          <span class="text-slate-500">Packet Drop Rate:</span>
          <span id="drop-rate" class="text-slate-200 font-mono font-bold">0.00%</span>
        </div>
      </div>
    </div>

    <!-- Topology Canvas -->
    <div id="topology-canvas" class="glass-card p-6 rounded-2xl relative overflow-hidden shadow-2xl">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Active Microservice Network Topology</h2>
        <span class="text-[11px] font-mono text-indigo-400">Live Traffic Pulses</span>
      </div>

      <svg class="w-full h-72" viewBox="0 0 820 250">
        <!-- Connecting Paths -->
        <path id="path-auth" d="M 140 125 C 230 125, 230 55, 320 55" fill="none" stroke="#334155" stroke-width="2.5" class="flow-active" stroke="#6366f1" />
        <path id="path-billing" d="M 140 125 C 230 125, 230 125, 320 125" fill="none" stroke="#334155" stroke-width="2.5" class="flow-active" stroke="#6366f1" />
        <path id="path-search" d="M 140 125 C 230 125, 230 195, 320 195" fill="none" stroke="#334155" stroke-width="2.5" class="flow-active" stroke="#6366f1" />

        <path d="M 450 55 C 540 55, 540 125, 640 125" fill="none" stroke="#334155" stroke-width="2.5" class="flow-active" stroke="#8b5cf6" />
        <path d="M 450 125 C 540 125, 540 125, 640 125" fill="none" stroke="#334155" stroke-width="2.5" class="flow-active" stroke="#8b5cf6" />
        <path d="M 450 195 C 540 195, 540 125, 640 125" fill="none" stroke="#334155" stroke-width="2.5" class="flow-active" stroke="#8b5cf6" />

        <!-- Nodes -->
        <!-- Ingress Gateway -->
        <g data-node="ingress" transform="translate(40, 90)" class="cursor-pointer">
          <rect width="100" height="70" rx="12" fill="#0f172a" stroke="#4f46e5" stroke-width="2" class="shadow-lg" />
          <text x="50" y="32" text-anchor="middle" font-size="11" font-weight="700" fill="#ffffff">Ingress</text>
          <text x="50" y="50" text-anchor="middle" font-size="10" font-family="JetBrains Mono" fill="#818cf8">Gateway</text>
        </g>

        <!-- Auth Microservice -->
        <g data-node="auth" transform="translate(320, 20)" class="cursor-pointer">
          <rect width="130" height="65" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.5" />
          <text x="65" y="30" text-anchor="middle" font-size="11" font-weight="600" fill="#f8fafc">Auth Service</text>
          <text x="65" y="48" text-anchor="middle" font-size="10" font-family="JetBrains Mono" fill="#34d399">Healthy (2.1ms)</text>
        </g>

        <!-- Billing Microservice -->
        <g data-node="billing" id="node-billing-card" transform="translate(320, 92)" class="cursor-pointer">
          <rect id="billing-rect" width="130" height="65" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.5" />
          <text x="65" y="30" text-anchor="middle" font-size="11" font-weight="600" fill="#f8fafc">Billing Service</text>
          <text id="billing-status" x="65" y="48" text-anchor="middle" font-size="10" font-family="JetBrains Mono" fill="#34d399">Healthy (4.8ms)</text>
        </g>

        <!-- Search Microservice -->
        <g data-node="search" transform="translate(320, 164)" class="cursor-pointer">
          <rect width="130" height="65" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.5" />
          <text x="65" y="30" text-anchor="middle" font-size="11" font-weight="600" fill="#f8fafc">Search Engine</text>
          <text x="65" y="48" text-anchor="middle" font-size="10" font-family="JetBrains Mono" fill="#34d399">Healthy (6.2ms)</text>
        </g>

        <!-- Analytics Sink -->
        <g data-node="sink" transform="translate(640, 90)" class="cursor-pointer">
          <rect width="110" height="70" rx="12" fill="#0f172a" stroke="#8b5cf6" stroke-width="2" />
          <text x="55" y="32" text-anchor="middle" font-size="11" font-weight="700" fill="#ffffff">Influx Sink</text>
          <text x="55" y="50" text-anchor="middle" font-size="10" font-family="JetBrains Mono" fill="#c084fc">Analytics DB</text>
        </g>
      </svg>
    </div>

    <!-- Metric Meters (Real-time SVG Sparklines) -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="glass-card p-5 rounded-2xl space-y-2">
        <div class="flex justify-between items-center text-xs">
          <span class="text-slate-400 font-semibold">Latency (p50)</span>
          <span id="val-p50" class="font-mono text-indigo-400 font-bold text-sm">4.2ms</span>
        </div>
        <svg class="w-full h-14" viewBox="0 0 120 35">
          <polyline id="poly-p50" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" points="0,28 20,24 40,26 60,22 80,24 100,20 120,22" />
        </svg>
        <div class="text-[10px] text-slate-500 flex justify-between">
          <span>Target: &lt;10ms</span>
          <span class="text-emerald-400">Within Spec</span>
        </div>
      </div>

      <div class="glass-card p-5 rounded-2xl space-y-2">
        <div class="flex justify-between items-center text-xs">
          <span class="text-slate-400 font-semibold">Tail Latency (p95)</span>
          <span id="val-p95" class="font-mono text-amber-400 font-bold text-sm">13.6ms</span>
        </div>
        <svg class="w-full h-14" viewBox="0 0 120 35">
          <polyline id="poly-p95" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" points="0,22 20,20 40,25 60,17 80,19 100,16 120,18" />
        </svg>
        <div class="text-[10px] text-slate-500 flex justify-between">
          <span>Target: &lt;20ms</span>
          <span class="text-emerald-400">Nominal</span>
        </div>
      </div>

      <div class="glass-card p-5 rounded-2xl space-y-2">
        <div class="flex justify-between items-center text-xs">
          <span class="text-slate-400 font-semibold">Critical Tail (p99)</span>
          <span id="val-p99" class="font-mono text-rose-400 font-bold text-sm">18.9ms</span>
        </div>
        <svg class="w-full h-14" viewBox="0 0 120 35">
          <polyline id="poly-p99" fill="none" stroke="#f43f5e" stroke-width="2.5" stroke-linecap="round" points="0,18 20,16 40,20 60,14 80,17 100,13 120,15" />
        </svg>
        <div class="text-[10px] text-slate-500 flex justify-between">
          <span>Alert Limit: 25ms</span>
          <span id="p99-badge" class="text-emerald-400">Normal</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Accessible Settings Dialog / Drawer -->
  <div id="settings-dialog" class="hidden fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-md flex items-center justify-center p-4">
    <div class="glass-card border border-slate-700 max-w-md w-full p-6 rounded-2xl shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
      <div class="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h3 class="text-sm font-extrabold text-white tracking-tight">Alerting & Threshold Controls</h3>
          <p class="text-xs text-slate-400">Fine-tune automated chaos triggers and SLO bounds</p>
        </div>
        <button id="close-settings-btn" class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="space-y-4 text-xs">
        <div>
          <label class="block text-slate-300 font-medium mb-1.5">p99 Threshold Breached Limit (ms):</label>
          <input type="number" value="25" class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono focus:border-indigo-500 focus:outline-none">
        </div>
        <div>
          <label class="block text-slate-300 font-medium mb-1.5">Chaos Anomaly Duration (seconds):</label>
          <input type="number" value="15" class="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono focus:border-indigo-500 focus:outline-none">
        </div>
      </div>

      <div class="flex justify-end space-x-2 pt-2 border-t border-slate-800">
        <button id="save-settings-btn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition-all">
          Apply Configuration
        </button>
      </div>
    </div>
  </div>

  <script>
    let chaos = false;
    const alertBanner = document.getElementById('alert-banner');
    const toggleChaosBtn = document.getElementById('toggle-chaos');
    const settingsDialog = document.getElementById('settings-dialog');
    const openSettingsBtn = document.getElementById('open-settings-btn');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const billingRect = document.getElementById('billing-rect');
    const billingStatus = document.getElementById('billing-status');
    const topoState = document.getElementById('topo-state');
    const dropRate = document.getElementById('drop-rate');
    const p99Badge = document.getElementById('p99-badge');
    const rpsSlider = document.getElementById('rps-slider');
    const rpsVal = document.getElementById('rps-value');

    rpsSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      rpsVal.textContent = Math.round(val / 1000) + 'k RPS';
    });

    toggleChaosBtn.addEventListener('click', () => {
      chaos = !chaos;
      toggleChaosBtn.setAttribute('aria-checked', chaos ? 'true' : 'false');

      if (chaos) {
        alertBanner.classList.remove('hidden');
        billingRect.setAttribute('stroke', '#ef4444');
        billingRect.setAttribute('fill', 'rgba(239, 68, 68, 0.15)');
        billingStatus.textContent = 'Degraded (p99 breached)';
        billingStatus.setAttribute('fill', '#f87171');
        topoState.textContent = 'DEGRADED';
        topoState.className = 'text-rose-500 font-bold font-mono';
        dropRate.textContent = '4.82%';
        p99Badge.textContent = 'BREACHED';
        p99Badge.className = 'text-rose-400 font-bold';
      } else {
        alertBanner.classList.add('hidden');
        billingRect.setAttribute('stroke', '#334155');
        billingRect.setAttribute('fill', '#0f172a');
        billingStatus.textContent = 'Healthy (4.8ms)';
        billingStatus.setAttribute('fill', '#34d399');
        topoState.textContent = 'NOMINAL';
        topoState.className = 'text-emerald-400 font-bold font-mono';
        dropRate.textContent = '0.00%';
        p99Badge.textContent = 'Normal';
        p99Badge.className = 'text-emerald-400';
      }
    });

    openSettingsBtn.addEventListener('click', () => settingsDialog.classList.remove('hidden'));
    const hideDialog = () => settingsDialog.classList.add('hidden');
    closeSettingsBtn.addEventListener('click', hideDialog);
    saveSettingsBtn.addEventListener('click', hideDialog);

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hideDialog();
    });

    // 800ms telemetry ticker updating sparklines
    setInterval(() => {
      const p50 = chaos ? (22 + Math.random() * 9).toFixed(1) : (4 + Math.random() * 1.5).toFixed(1);
      const p95 = chaos ? (92 + Math.random() * 25).toFixed(1) : (12 + Math.random() * 2.5).toFixed(1);
      const p99 = chaos ? (154 + Math.random() * 40).toFixed(1) : (18 + Math.random() * 3).toFixed(1);

      document.getElementById('val-p50').textContent = p50 + 'ms';
      document.getElementById('val-p95').textContent = p95 + 'ms';
      document.getElementById('val-p99').textContent = p99 + 'ms';
    }, 800);
  </script>
</body>
</html>
"""

