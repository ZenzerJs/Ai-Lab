# scripts/exp008_templates.py
"""
HTML Templates for EXP-008: ResumeForge Interview Intelligence System
"""

def get_exp008_vanilla_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ResumeForge Interview - Baseline (Arm A)</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-800 font-sans p-6 min-h-screen">
  <div class="max-w-4xl mx-auto bg-white p-6 rounded shadow border border-gray-300">
    <header class="border-b pb-4 mb-4 flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Interview Session</h1>
        <p class="text-sm text-gray-500">Track: System Design & Behavioral</p>
      </div>
      <button id="start-session-btn" onclick="startSession()" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm font-semibold">
        Start Session
      </button>
    </header>

    <div id="session-container" class="hidden space-y-6">
      <div class="flex justify-between items-center text-sm font-medium text-gray-600">
        <span id="turn-indicator">Turn 1 of 3</span>
        <span>Candidate: John Doe</span>
      </div>

      <!-- Question & Evidence Block -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="p-4 bg-gray-50 rounded border border-gray-200">
          <h2 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Question</h2>
          <div id="question-display" class="text-gray-800 text-sm font-medium">
            Can you explain how you designed the distributed lock service at Stripe to prevent concurrency race conditions?
          </div>
        </div>

        <div id="evidence-card" class="p-4 bg-blue-50 rounded border border-blue-200 text-sm">
          <h3 class="text-xs font-bold text-blue-700 uppercase tracking-wider mb-1">Evidence Citation</h3>
          <p class="text-blue-900 font-medium">Stripe — Distributed Systems Engineer (2022–2024)</p>
          <p class="text-xs text-blue-800 mt-1">Architected multi-region Redis lock manager with TTL heartbeat rollback.</p>
        </div>
      </div>

      <!-- Response Area -->
      <div class="space-y-2">
        <label class="block text-xs font-bold text-gray-600 uppercase">Your Response</label>
        <textarea id="response-input" rows="4" class="w-full p-3 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" placeholder="Enter your technical response..."></textarea>
        <div class="flex justify-end">
          <button id="submit-turn-btn" onclick="submitTurn()" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm font-semibold">
            Submit Turn
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Scorecard Dialog -->
  <div id="scorecard-dialog" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
    <div class="bg-white rounded p-6 max-w-md w-full shadow-lg border border-gray-300">
      <h2 class="text-xl font-bold text-gray-900 mb-2">Interview Performance Scorecard</h2>
      <p class="text-sm text-gray-600 mb-4">Evaluated across 4-axis rubric grounding.</p>
      
      <div class="text-center py-4 bg-gray-50 rounded mb-4">
        <span class="text-xs text-gray-500 font-bold uppercase">Composite Score</span>
        <div id="composite-score" class="text-3xl font-extrabold text-blue-600">88.5 / 100</div>
      </div>

      <div class="space-y-2 text-xs text-gray-700 mb-6">
        <div class="flex justify-between"><span>Technical Accuracy:</span><span class="font-bold">90%</span></div>
        <div class="flex justify-between"><span>Architectural Depth:</span><span class="font-bold">86%</span></div>
        <div class="flex justify-between"><span>Communication Conciseness:</span><span class="font-bold">85%</span></div>
        <div class="flex justify-between"><span>Evidence Grounding:</span><span class="font-bold">93%</span></div>
      </div>

      <button onclick="document.getElementById('scorecard-dialog').classList.add('hidden')" class="w-full bg-gray-800 text-white py-2 rounded text-sm font-semibold hover:bg-gray-900">
        Close Scorecard
      </button>
    </div>
  </div>

  <script>
    let currentTurn = 1;
    const questions = [
      "Can you explain how you designed the distributed lock service at Stripe to prevent concurrency race conditions?",
      "How did you guarantee atomicity and avoid split-brain scenarios during network partitions?",
      "What were the telemetry metrics and p99 latency results achieved by this implementation?"
    ];

    function startSession() {
      document.getElementById('session-container').classList.remove('hidden');
      document.getElementById('start-session-btn').classList.add('hidden');
    }

    function submitTurn() {
      const resp = document.getElementById('response-input').value.trim();
      if (!resp) return;
      document.getElementById('response-input').value = '';
      currentTurn++;
      if (currentTurn <= 3) {
        document.getElementById('turn-indicator').textContent = 'Turn ' + currentTurn + ' of 3';
        document.getElementById('question-display').textContent = questions[currentTurn - 1];
      } else {
        document.getElementById('scorecard-dialog').classList.remove('hidden');
      }
    }
  </script>
</body>
</html>
"""

def get_exp008_governed_html() -> str:
    return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ResumeForge Interview Workspace - Governed (Arm B)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            forgeBg: '#0b1326',
            forgeSurfaceLowest: '#060e20',
            forgeSurfaceLow: '#131b2e',
            forgeSurface: '#171f33',
            forgeSurfaceHigh: '#222a3d',
            forgeSurfaceHighest: '#2d3449',
            forgePrimary: '#ff8c00',
            forgePrimaryHover: '#e07b00',
            forgeSecondary: '#4edea3',
            forgeTertiary: '#ffb3ad'
          }
        }
      }
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    body { font-family: 'Hanken Grotesk', sans-serif; }
    .font-mono { font-family: 'JetBrains Mono', monospace; }
    .glass-card {
      background: rgba(23, 31, 51, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .glowing-badge {
      box-shadow: 0 0 12px rgba(78, 222, 163, 0.25);
    }
  </style>
</head>
<body class="bg-[#0b1326] text-slate-100 min-h-screen flex flex-col antialiased selection:bg-orange-500/30 selection:text-orange-200">

  <!-- Top Navigation Header -->
  <header class="h-14 border-b border-white/10 bg-[#060e20]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
    <div class="flex items-center space-x-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-lg shadow-orange-500/20">
        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
        </svg>
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <span class="font-bold tracking-tight text-white text-sm">ResumeForge</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-orange-500/10 text-orange-400 border border-orange-500/20">INTELLIGENCE</span>
        </div>
        <div class="text-[11px] text-slate-400 font-mono">STAR Behavioral & Distributed Systems Rubric</div>
      </div>
    </div>

    <div class="flex items-center space-x-4">
      <div class="hidden sm:flex items-center space-x-2 text-xs text-slate-400 font-mono bg-[#131b2e] px-3 py-1.5 rounded-full border border-white/5">
        <span class="w-2 h-2 rounded-full bg-[#4edea3] animate-pulse"></span>
        <span>AST Fact Grounding: ACTIVE</span>
      </div>
      <button id="start-session-btn" onclick="startSession()" class="px-4 py-1.5 rounded-lg bg-[#ff8c00] hover:bg-[#e07b00] text-white text-xs font-semibold shadow-md shadow-orange-500/20 transition-all flex items-center space-x-2">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>
        <span>Initialize Interview</span>
      </button>
    </div>
  </header>

  <!-- Main Console Layout -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col">
    <!-- Hero Status Bar -->
    <div class="flex flex-wrap items-center justify-between gap-4 mb-4 pb-3 border-b border-white/5">
      <div class="flex items-center space-x-3">
        <span id="turn-indicator" class="font-mono text-xs font-bold tracking-wider px-2.5 py-1 rounded-md bg-[#222a3d] text-orange-400 border border-orange-500/30">
          Turn 1 of 3
        </span>
        <span class="text-xs text-slate-400 font-mono">Model: <span class="text-slate-200">gemini-3.8-flash</span></span>
        <span class="text-xs text-slate-400 font-mono">Effort: <span class="text-[#4edea3]">Hierarchical Rationed</span></span>
      </div>
      <div class="flex items-center space-x-3 text-xs font-mono text-slate-400">
        <span>Elapsed: <span id="session-timer" class="text-slate-200">00:00</span></span>
        <span class="text-white/20">•</span>
        <span>Rubric: <span class="text-[#4edea3]">4-Axis Evidence-Grounded</span></span>
      </div>
    </div>

    <!-- Split-Console Workspace (Resizable Simulation) -->
    <div id="session-container" class="hidden flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[520px]">
      
      <!-- Left Pane: Turn Stream & Response Input (7 cols) -->
      <div class="lg:col-span-7 flex flex-col space-y-4">
        <!-- Question Card -->
        <div class="glass-card rounded-xl p-5 relative overflow-hidden border border-white/10 shadow-xl">
          <div class="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-orange-500 to-amber-500"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-[11px] font-mono uppercase tracking-wider font-semibold text-orange-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              Interview Prompt
            </span>
            <span class="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded">Dynamic STAR Synthesis</span>
          </div>
          <div id="question-display" class="text-slate-100 text-base sm:text-lg font-medium leading-relaxed">
            Can you explain how you designed the distributed lock service at Stripe to prevent concurrency race conditions during sudden burst events?
          </div>
        </div>

        <!-- Candidate Response Input -->
        <div class="glass-card rounded-xl p-5 flex-1 flex flex-col border border-white/10 shadow-xl">
          <div class="flex items-center justify-between mb-2">
            <label class="text-[11px] font-mono uppercase tracking-wider font-semibold text-slate-400">Your Technical Response</label>
            <span class="text-[10px] font-mono text-slate-500">Markdown & Code Blocks Supported</span>
          </div>
          <textarea id="response-input" rows="7" class="w-full flex-1 bg-[#060e20] text-slate-200 p-4 rounded-lg border border-white/10 text-sm font-mono focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-all resize-none" placeholder="Detail your architectural decision, state transitions, failover semantics, and ground your response in verified metrics..."></textarea>
          
          <div class="mt-4 flex items-center justify-between pt-3 border-t border-white/5">
            <div class="text-[11px] font-mono text-slate-400 flex items-center space-x-2">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>Guardrails: Real-Time Fact Citation Active</span>
            </div>
            <button id="submit-turn-btn" onclick="submitTurn()" class="px-5 py-2 rounded-lg bg-[#ff8c00] hover:bg-[#e07b00] text-white text-xs font-semibold shadow-lg shadow-orange-500/25 transition-all flex items-center space-x-2">
              <span>Submit Turn & Next Question</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Right Pane: Real-Time Grounding Inspector (5 cols) -->
      <div class="lg:col-span-5 flex flex-col space-y-4">
        <!-- Evidence Grounding Inspector Card -->
        <div id="evidence-card" class="glass-card rounded-xl p-5 border border-white/10 shadow-xl flex-1 flex flex-col">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-[#4edea3] glowing-badge"></span>
              <h3 class="text-xs font-mono uppercase tracking-wider font-bold text-slate-200">Verified Evidence Grounding</h3>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">VERIFIED CLAIM</span>
          </div>

          <div class="bg-[#131b2e] rounded-lg p-4 border border-white/5 mb-4">
            <div class="text-xs font-semibold text-white mb-1">Stripe — Senior Distributed Systems Engineer</div>
            <div class="text-[11px] font-mono text-slate-400 mb-2">2022 – 2024 • Payments & Infrastructure</div>
            <p class="text-xs text-slate-300 leading-relaxed font-mono bg-[#060e20] p-2.5 rounded border border-white/5">
              "Architected multi-region Redis lock manager with TTL heartbeat rollback, eliminating split-brain races and slashing p99 failover latency by 42% across 12M daily transactions."
            </p>
          </div>

          <!-- Keyword Alignment Spans -->
          <div class="space-y-2 mb-4">
            <div class="text-[11px] font-mono uppercase text-slate-400 font-semibold">Matched Provenance Claims</div>
            <div class="flex flex-wrap gap-1.5 text-[10px] font-mono">
              <span class="px-2 py-1 rounded bg-[#222a3d] text-emerald-300 border border-emerald-500/30">#distributed-locks</span>
              <span class="px-2 py-1 rounded bg-[#222a3d] text-emerald-300 border border-emerald-500/30">#redis-ttl-heartbeat</span>
              <span class="px-2 py-1 rounded bg-[#222a3d] text-orange-300 border border-orange-500/30">#p99-latency-42%</span>
              <span class="px-2 py-1 rounded bg-[#222a3d] text-cyan-300 border border-cyan-500/30">#12m-daily-txns</span>
            </div>
          </div>

          <!-- Live 4-Axis Rubric Telemetry -->
          <div class="mt-auto pt-4 border-t border-white/5 space-y-2.5">
            <div class="text-[11px] font-mono uppercase text-slate-400 font-semibold">Live Axis Rubric Radar</div>
            <div class="space-y-1.5 text-xs font-mono">
              <div>
                <div class="flex justify-between text-[11px] text-slate-300 mb-1">
                  <span>Technical Accuracy</span>
                  <span class="text-emerald-400">92%</span>
                </div>
                <div class="w-full bg-[#131b2e] rounded-full h-1.5 overflow-hidden">
                  <div class="bg-[#4edea3] h-full rounded-full" style="width: 92%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between text-[11px] text-slate-300 mb-1">
                  <span>Architectural Depth</span>
                  <span class="text-orange-400">88%</span>
                </div>
                <div class="w-full bg-[#131b2e] rounded-full h-1.5 overflow-hidden">
                  <div class="bg-[#ff8c00] h-full rounded-full" style="width: 88%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between text-[11px] text-slate-300 mb-1">
                  <span>Communication Conciseness</span>
                  <span class="text-cyan-400">85%</span>
                </div>
                <div class="w-full bg-[#131b2e] rounded-full h-1.5 overflow-hidden">
                  <div class="bg-cyan-400 h-full rounded-full" style="width: 85%"></div>
                </div>
              </div>
              <div>
                <div class="flex justify-between text-[11px] text-slate-300 mb-1">
                  <span>Evidence Grounding</span>
                  <span class="text-emerald-400">95%</span>
                </div>
                <div class="w-full bg-[#131b2e] rounded-full h-1.5 overflow-hidden">
                  <div class="bg-[#4edea3] h-full rounded-full" style="width: 95%"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Accessible Scorecard Modal Dialog -->
  <div id="scorecard-dialog" class="hidden fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
    <div class="glass-card rounded-2xl max-w-lg w-full p-6 sm:p-8 border border-white/15 shadow-2xl relative animate-in fade-in zoom-in duration-200">
      <div class="flex items-center justify-between pb-4 border-b border-white/10 mb-6">
        <div>
          <span class="text-[10px] font-mono text-orange-400 font-bold uppercase tracking-wider">EXP-008 Completion</span>
          <h2 class="text-xl font-bold text-white tracking-tight">Interview Performance Scorecard</h2>
        </div>
        <span class="px-2.5 py-1 rounded text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">PASSED</span>
      </div>

      <!-- Composite Score Beacon -->
      <div class="bg-gradient-to-br from-[#171f33] to-[#060e20] p-5 rounded-xl border border-white/10 text-center mb-6">
        <span class="text-xs font-mono text-slate-400 uppercase tracking-wider">Composite Rubric Score</span>
        <div id="composite-score" class="text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-300 my-1 font-mono">
          91.8 / 100
        </div>
        <p class="text-xs text-slate-400 font-mono">Zero Hallucinations • 100% Grounded in Verified Claim Nodes</p>
      </div>

      <!-- 4-Axis Breakdown -->
      <div class="grid grid-cols-2 gap-3 mb-6 text-xs font-mono">
        <div class="bg-[#131b2e] p-3 rounded-lg border border-white/5">
          <span class="text-slate-400 block text-[10px] uppercase">Technical Accuracy</span>
          <span class="text-base font-bold text-emerald-400">92%</span>
        </div>
        <div class="bg-[#131b2e] p-3 rounded-lg border border-white/5">
          <span class="text-slate-400 block text-[10px] uppercase">Architectural Depth</span>
          <span class="text-base font-bold text-orange-400">88%</span>
        </div>
        <div class="bg-[#131b2e] p-3 rounded-lg border border-white/5">
          <span class="text-slate-400 block text-[10px] uppercase">Conciseness</span>
          <span class="text-base font-bold text-cyan-400">85%</span>
        </div>
        <div class="bg-[#131b2e] p-3 rounded-lg border border-white/5">
          <span class="text-slate-400 block text-[10px] uppercase">Evidence Grounding</span>
          <span class="text-base font-bold text-emerald-400">95%</span>
        </div>
      </div>

      <button onclick="document.getElementById('scorecard-dialog').classList.add('hidden')" class="w-full py-3 rounded-xl bg-[#ff8c00] hover:bg-[#e07b00] text-white text-xs font-bold uppercase tracking-wider font-mono shadow-lg shadow-orange-500/25 transition-all">
        Close Scorecard & Inspect Telemetry
      </button>
    </div>
  </div>

  <script>
    let currentTurn = 1;
    let timerSeconds = 0;
    let timerInterval = null;

    const questions = [
      "Can you explain how you designed the distributed lock service at Stripe to prevent concurrency race conditions during sudden burst events?",
      "How did you guarantee atomicity and avoid split-brain scenarios during network partitions while maintaining p99 latency SLA?",
      "What were the exact telemetry metrics and rollback safeguards you implemented to verify fault-tolerance under peak load?"
    ];

    function startSession() {
      document.getElementById('session-container').classList.remove('hidden');
      document.getElementById('start-session-btn').classList.add('hidden');
      timerInterval = setInterval(() => {
        timerSeconds++;
        const mins = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
        const secs = String(timerSeconds % 60).padStart(2, '0');
        document.getElementById('session-timer').textContent = `${mins}:${secs}`;
      }, 1000);
    }

    function submitTurn() {
      const resp = document.getElementById('response-input').value.trim();
      if (!resp) return;
      document.getElementById('response-input').value = '';
      currentTurn++;
      if (currentTurn <= 3) {
        document.getElementById('turn-indicator').textContent = 'Turn ' + currentTurn + ' of 3';
        document.getElementById('question-display').textContent = questions[currentTurn - 1];
      } else {
        clearInterval(timerInterval);
        document.getElementById('scorecard-dialog').classList.remove('hidden');
      }
    }
  </script>
</body>
</html>
"""
