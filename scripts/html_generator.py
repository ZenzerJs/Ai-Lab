# scripts/html_generator.py
"""
HTML artifact generators for EXP-005 and EXP-007 benchmarks.
"""

from exp007_templates import get_exp007_vanilla_html, get_exp007_governed_html

def get_vanilla_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PulseEngine - Real-Time API Analytics</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-900 font-sans antialiased min-h-screen flex flex-col">

  <!-- 1. Sticky Navbar -->
  <header class="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <!-- Logo -->
      <a href="#" class="flex items-center space-x-2.5">
        <span class="p-2 bg-indigo-600 rounded-lg text-white">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        </span>
        <span class="text-xl font-bold tracking-tight text-gray-900">PulseEngine</span>
      </a>

      <!-- Navigation Links -->
      <nav class="hidden md:flex space-x-8 text-sm font-medium text-gray-600">
        <a href="#features" class="hover:text-indigo-600 transition-colors">Features</a>
        <a href="#pricing" class="hover:text-indigo-600 transition-colors">Pricing</a>
        <a href="#docs" class="hover:text-indigo-600 transition-colors">Documentation</a>
      </nav>

      <!-- Primary Action -->
      <div class="flex items-center space-x-4">
        <a href="#pricing" class="hidden sm:inline-block text-sm font-medium text-gray-600 hover:text-gray-900">Log in</a>
        <a href="#pricing" class="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm">
          Get Started
        </a>
      </div>
    </div>
  </header>

  <main class="flex-grow">
    <!-- 2. Hero Section -->
    <section class="relative pt-16 pb-20 lg:pt-24 lg:pb-32 overflow-hidden">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <!-- Badge -->
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mb-8">
          <span class="w-2 h-2 rounded-full bg-indigo-600"></span>
          Next-Gen API Observability
        </div>

        <!-- Bold Value Prop -->
        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 tracking-tight max-w-4xl mx-auto leading-tight">
          Real-Time API Analytics for Modern Engineering Teams
        </h1>

        <!-- Subheading -->
        <p class="mt-6 text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto">
          Gain instant visibility into API latencies, error spikes, and usage trends with sub-millisecond ingestion and zero-overhead SDKs.
        </p>

        <!-- Dual CTAs -->
        <div class="mt-10 flex flex-col sm:flex-row gap-4 justify-center items-center">
          <a href="#pricing" class="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-md transition-all">
            Start Free 14-Day Trial
          </a>
          <a href="#features" class="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-all">
            Explore Features
          </a>
        </div>

        <!-- Social Proof Metric Badges -->
        <div class="mt-16 pt-10 border-t border-gray-200 max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div class="p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
            <div class="text-3xl font-extrabold text-indigo-600">99.99%</div>
            <div class="text-sm font-medium text-gray-500 mt-1">Platform Uptime SLA</div>
          </div>
          <div class="p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
            <div class="text-3xl font-extrabold text-indigo-600">500M+</div>
            <div class="text-sm font-medium text-gray-500 mt-1">Daily Ingested Requests</div>
          </div>
          <div class="p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
            <div class="text-3xl font-extrabold text-indigo-600">&lt; 10ms</div>
            <div class="text-sm font-medium text-gray-500 mt-1">Global Telemetry Latency</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. Feature Grid -->
    <section id="features" class="py-16 bg-white border-y border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto mb-16">
          <h2 class="text-xs font-bold text-indigo-600 uppercase tracking-widest">Capabilities</h2>
          <p class="mt-2 text-3xl font-bold text-gray-900 tracking-tight sm:text-4xl">Everything required to monitor production APIs</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div class="p-8 bg-gray-50 rounded-2xl border border-gray-200 hover:border-indigo-400 hover:shadow-lg transition-all duration-300">
            <div class="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-6">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900">Real-Time Ingestion</h3>
            <p class="mt-3 text-gray-600 leading-relaxed">
              Process hundreds of thousands of concurrent calls without choking user latency. Stream directly into unified dashboards.
            </p>
          </div>

          <div class="p-8 bg-gray-50 rounded-2xl border border-gray-200 hover:border-indigo-400 hover:shadow-lg transition-all duration-300">
            <div class="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-6">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900">Automated Anomaly Detection</h3>
            <p class="mt-3 text-gray-600 leading-relaxed">
              Catch 5xx error spikes, token rate limit thresholds, and latency degradation before customers notice and churn.
            </p>
          </div>

          <div class="p-8 bg-gray-50 rounded-2xl border border-gray-200 hover:border-indigo-400 hover:shadow-lg transition-all duration-300">
            <div class="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-6">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900">Developer-First SDKs</h3>
            <p class="mt-3 text-gray-600 leading-relaxed">
              Drop two lines of code into Node.js, Python, Go, or Rust middleware. Export raw metrics to OpenTelemetry anytime.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. Interactive Pricing Switch & Cards -->
    <section id="pricing" class="py-16 lg:py-24">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto mb-12">
          <h2 class="text-xs font-bold text-indigo-600 uppercase tracking-widest">Transparent Pricing</h2>
          <p class="mt-2 text-3xl font-bold text-gray-900 tracking-tight sm:text-4xl">Scale smoothly from MVP to enterprise</p>

          <div class="mt-8 inline-flex items-center justify-center p-1 bg-gray-200 rounded-xl space-x-2">
            <button id="monthlyBtn" class="px-5 py-2 rounded-lg text-sm font-semibold bg-white text-gray-900 shadow-sm transition-all">Monthly</button>
            <button id="annualBtn" class="px-5 py-2 rounded-lg text-sm font-semibold text-gray-600 hover:text-gray-900 transition-all flex items-center gap-1.5">
              <span>Annual</span>
              <span class="px-2 py-0.5 text-xs font-bold text-emerald-700 bg-emerald-100 rounded-md">Save 20%</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <!-- Starter Tier ($29/mo) -->
          <div class="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm flex flex-col justify-between">
            <div>
              <h3 class="text-xl font-bold text-gray-900">Starter</h3>
              <p class="mt-2 text-sm text-gray-500">Perfect for indie hackers and high-growth MVPs.</p>
              <div class="mt-6 flex items-baseline">
                <span class="text-4xl font-extrabold text-gray-900" id="starterPrice">$29</span>
                <span class="text-gray-500 ml-2" id="starterPeriod">/month</span>
              </div>
              <p class="text-xs text-gray-400 mt-1" id="starterBilled">Billed monthly</p>

              <ul class="mt-6 space-y-4 text-sm text-gray-600">
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Up to 5M API events / month
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  7-day retention window
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Basic webhook alerting
                </li>
              </ul>
            </div>
            <a href="#" class="mt-8 block w-full py-3 text-center text-sm font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors">
              Choose Starter
            </a>
          </div>

          <!-- Enterprise Tier ($99/mo) -->
          <div class="bg-white p-8 rounded-2xl border-2 border-indigo-600 shadow-xl relative flex flex-col justify-between">
            <span class="absolute -top-3 right-8 bg-indigo-600 text-white text-xs font-bold uppercase tracking-wider py-1 px-3 rounded-full">
              Recommended
            </span>
            <div>
              <h3 class="text-xl font-bold text-gray-900">Pro Enterprise</h3>
              <p class="mt-2 text-sm text-gray-500">For scaling microservices and production apps.</p>
              <div class="mt-6 flex items-baseline">
                <span class="text-4xl font-extrabold text-gray-900" id="proPrice">$99</span>
                <span class="text-gray-500 ml-2" id="proPeriod">/month</span>
              </div>
              <p class="text-xs text-gray-400 mt-1" id="proBilled">Billed monthly</p>

              <ul class="mt-6 space-y-4 text-sm text-gray-600">
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Up to 50M API events / month
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  90-day retention & cold query storage
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Slack, PagerDuty, & Custom Webhooks
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Dedicated 24/7 Slack channel support
                </li>
              </ul>
            </div>
            <a href="#" class="mt-8 block w-full py-3 text-center text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-md">
              Start Pro Trial
            </a>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- 5. Clean Minimalist Footer -->
  <footer class="bg-white border-t border-gray-200 py-10">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center space-x-2">
        <span class="p-1.5 bg-indigo-600 rounded text-white">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
        </span>
        <span class="font-bold text-gray-900 text-sm">PulseEngine</span>
      </div>
      <div class="flex space-x-6 text-sm text-gray-500">
        <a href="#" class="hover:text-gray-900">Privacy Policy</a>
        <a href="#" class="hover:text-gray-900">Terms of Service</a>
        <a href="#" class="hover:text-gray-900">System Status</a>
        <a href="#" class="hover:text-gray-900">Security</a>
      </div>
      <p class="text-xs text-gray-400">© 2026 PulseEngine, Inc. All rights reserved.</p>
    </div>
  </footer>

  <script>
    const monthlyBtn = document.getElementById('monthlyBtn');
    const annualBtn = document.getElementById('annualBtn');
    const starterPrice = document.getElementById('starterPrice');
    const proPrice = document.getElementById('proPrice');
    const starterBilled = document.getElementById('starterBilled');
    const proBilled = document.getElementById('proBilled');

    let isAnnual = false;
    function updatePricing() {
      if (isAnnual) {
        starterPrice.textContent = '$23';
        proPrice.textContent = '$79';
        starterBilled.textContent = 'Billed annually ($276/yr)';
        proBilled.textContent = 'Billed annually ($948/yr)';
        annualBtn.classList.add('bg-white', 'text-gray-900', 'shadow-sm');
        annualBtn.classList.remove('text-gray-600');
        monthlyBtn.classList.remove('bg-white', 'text-gray-900', 'shadow-sm');
        monthlyBtn.classList.add('text-gray-600');
      } else {
        starterPrice.textContent = '$29';
        proPrice.textContent = '$99';
        starterBilled.textContent = 'Billed monthly';
        proBilled.textContent = 'Billed monthly';
        monthlyBtn.classList.add('bg-white', 'text-gray-900', 'shadow-sm');
        monthlyBtn.classList.remove('text-gray-600');
        annualBtn.classList.remove('bg-white', 'text-gray-900', 'shadow-sm');
        annualBtn.classList.add('text-gray-600');
      }
    }
    monthlyBtn.addEventListener('click', () => { isAnnual = false; updatePricing(); });
    annualBtn.addEventListener('click', () => { isAnnual = true; updatePricing(); });
  </script>
</body>
</html>
"""

def get_governed_html() -> str:
    return """<!DOCTYPE html>
<html lang="en" class="dark scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PulseEngine | Enterprise API Telemetry & Intelligence Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#eef2ff',
              100: '#e0e7ff',
              400: '#818cf8',
              500: '#6366f1',
              600: '#4f46e5',
              900: '#312e81',
              950: '#1e1b4b'
            }
          }
        }
      }
    }
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .glass-card {
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .glow-effect {
      box-shadow: 0 0 35px -8px rgba(99, 102, 241, 0.35);
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 antialiased selection:bg-brand-500/30 selection:text-brand-400 min-h-screen flex flex-col">

  <!-- Ambient background glow -->
  <div class="fixed inset-0 pointer-events-none z-0 overflow-hidden">
    <div class="absolute -top-40 left-1/2 -translate-x-1/2 w-[750px] h-[500px] bg-brand-500/15 rounded-full blur-[140px]"></div>
    <div class="absolute top-1/3 -right-40 w-[500px] h-[400px] bg-purple-500/10 rounded-full blur-[120px]"></div>
  </div>

  <!-- 1. Modern Sticky Navbar with Backdrop Blur -->
  <header class="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800/80 transition-all duration-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <!-- Logo with pulsing beacon -->
      <a href="#" class="flex items-center space-x-3 group">
        <div class="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 p-0.5 shadow-lg shadow-brand-500/20 group-hover:scale-105 transition-transform">
          <div class="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
            <svg class="w-5 h-5 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">PulseEngine</span>
          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20">v2.4</span>
        </div>
      </a>

      <!-- Desktop Nav Links -->
      <nav class="hidden md:flex items-center space-x-8 text-sm font-medium text-slate-300">
        <a href="#features" class="hover:text-white transition-colors">Features</a>
        <a href="#pricing" class="hover:text-white transition-colors">Pricing</a>
        <a href="#docs" class="hover:text-white transition-colors">Documentation</a>
      </nav>

      <!-- CTA / Sign In -->
      <div class="hidden sm:flex items-center space-x-4">
        <a href="#pricing" class="text-sm font-medium text-slate-400 hover:text-white transition-colors">Sign in</a>
        <a href="#pricing" class="inline-flex items-center justify-center px-4 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 rounded-lg shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 hover:-translate-y-0.5 transition-all">
          Get Started
          <svg class="w-4 h-4 ml-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </a>
      </div>

      <!-- Mobile Hamburger Button -->
      <button id="mobileMenuBtn" aria-label="Toggle navigation menu" class="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 focus:outline-none">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path id="menuIcon" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      </button>
    </div>

    <!-- Mobile Drawer -->
    <div id="mobileDrawer" class="hidden md:hidden px-4 pt-2 pb-6 bg-slate-950/95 border-b border-slate-800 text-slate-200">
      <div class="flex flex-col space-y-3 text-sm font-medium">
        <a href="#features" class="py-2 hover:text-white">Features</a>
        <a href="#pricing" class="py-2 hover:text-white">Pricing</a>
        <a href="#docs" class="py-2 hover:text-white">Documentation</a>
        <div class="pt-3 border-t border-slate-800 flex flex-col gap-3">
          <a href="#pricing" class="text-center py-2 text-slate-400">Sign in</a>
          <a href="#pricing" class="text-center py-2.5 text-sm font-semibold text-white bg-brand-600 rounded-lg">Get Started</a>
        </div>
      </div>
    </div>
  </header>

  <main class="flex-grow z-10">
    <!-- 2. Hero Section -->
    <section class="relative pt-20 pb-24 lg:pt-32 lg:pb-36 overflow-hidden">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <!-- Status Pill with pulsing dot -->
        <div class="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full text-xs font-medium glass-card text-slate-300 mb-8 hover:border-brand-500/40 transition-colors">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span class="text-slate-200 font-semibold">PulseEngine v2.4 Live</span>
          <span class="text-slate-600">•</span>
          <span class="text-brand-400">eBPF Telemetry Ingest &rarr;</span>
        </div>

        <!-- Headline with Gradient Clipping -->
        <h1 class="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight max-w-5xl mx-auto leading-[1.1]">
          Real-Time API Analytics for
          <span class="bg-gradient-to-r from-brand-400 via-indigo-200 to-purple-300 bg-clip-text text-transparent">Modern Engineering</span>
        </h1>

        <!-- Subheading -->
        <p class="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Ingest billions of API calls with zero latency penalty. Isolate microservice regressions, inspect payload diffs, and halt error cascades in real time.
        </p>

        <!-- Dual CTA Buttons -->
        <div class="mt-10 flex flex-col sm:flex-row gap-4 justify-center items-center">
          <a href="#pricing" class="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-white bg-brand-600 hover:bg-brand-500 rounded-xl shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2">
            <span>Start Free 14-Day Trial</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </a>
          <a href="#features" class="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-slate-300 glass-card hover:bg-slate-800/80 hover:text-white rounded-xl transition-all">
            Schedule Architecture Review
          </a>
        </div>

        <!-- Social Proof Metric Badges -->
        <div class="mt-20 pt-10 border-t border-slate-800/80 max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div class="p-6 rounded-2xl glass-card text-center hover:border-brand-500/30 transition-colors">
            <div class="text-4xl font-extrabold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">99.999%</div>
            <div class="text-xs font-semibold uppercase tracking-wider text-slate-400 mt-2">Guaranteed Enterprise SLA</div>
          </div>
          <div class="p-6 rounded-2xl glass-card text-center hover:border-brand-500/30 transition-colors">
            <div class="text-4xl font-extrabold bg-gradient-to-r from-brand-400 to-indigo-300 bg-clip-text text-transparent">500M+</div>
            <div class="text-xs font-semibold uppercase tracking-wider text-slate-400 mt-2">Daily Production Calls</div>
          </div>
          <div class="p-6 rounded-2xl glass-card text-center hover:border-brand-500/30 transition-colors">
            <div class="text-4xl font-extrabold bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">&lt; 4ms</div>
            <div class="text-xs font-semibold uppercase tracking-wider text-slate-400 mt-2">P99 Global Telemetry Ingest</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. Feature Grid with SVG Icons & Micro-Interactions -->
    <section id="features" class="py-20 lg:py-28 relative border-t border-slate-800/80 bg-slate-900/30">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto mb-16">
          <span class="text-xs font-bold text-brand-400 uppercase tracking-widest">Observable Systems</span>
          <h2 class="mt-2 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Built for scale, tuned for developers</h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <!-- Card 1 -->
          <div class="p-8 rounded-2xl glass-card hover:border-brand-500/50 hover:-translate-y-1 transition-all duration-300 group">
            <div class="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mb-6 group-hover:bg-brand-500/20 transition-colors">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-white group-hover:text-brand-300 transition-colors">Ultra-Fast Stream Ingestion</h3>
            <p class="mt-3 text-sm text-slate-400 leading-relaxed">
              Handle sustained bursts up to 250k RPS per edge gateway. Ring-buffered asynchronous workers ensure zero blocking overhead on user requests.
            </p>
          </div>

          <!-- Card 2 -->
          <div class="p-8 rounded-2xl glass-card hover:border-brand-500/50 hover:-translate-y-1 transition-all duration-300 group">
            <div class="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mb-6 group-hover:bg-brand-500/20 transition-colors">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-white group-hover:text-brand-300 transition-colors">Predictive Anomaly Shield</h3>
            <p class="mt-3 text-sm text-slate-400 leading-relaxed">
              Continuous probabilistic distribution models identify microservice latency drift and error regressions 12 minutes before alerts hit PagerDuty.
            </p>
          </div>

          <!-- Card 3 -->
          <div class="p-8 rounded-2xl glass-card hover:border-brand-500/50 hover:-translate-y-1 transition-all duration-300 group">
            <div class="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mb-6 group-hover:bg-brand-500/20 transition-colors">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
              </svg>
            </div>
            <h3 class="text-xl font-bold text-white group-hover:text-brand-300 transition-colors">Native OpenTelemetry SDKs</h3>
            <p class="mt-3 text-sm text-slate-400 leading-relaxed">
              Drop-in wrappers for Node, Go, Python, Java, and Rust. Export traces and metrics directly to Datadog, Prometheus, or Grafana Tempo.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. Interactive Monthly / Annual Pricing Switch with 20% Discount -->
    <section id="pricing" class="py-20 lg:py-28 relative">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto mb-16">
          <span class="text-xs font-bold text-brand-400 uppercase tracking-widest">Deterministic Pricing</span>
          <h2 class="mt-2 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">Predictable costs as your traffic accelerates</h2>

          <!-- Interactive Switch (shadcn style) -->
          <div class="mt-8 inline-flex items-center gap-3 p-1.5 rounded-full glass-card">
            <span id="monthlyLabel" class="text-sm font-semibold px-4 py-1.5 rounded-full bg-brand-600 text-white transition-all cursor-pointer">Monthly</span>
            <button id="billingToggle" type="button" role="switch" aria-checked="false" aria-label="Toggle annual pricing" class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-slate-800 transition-colors duration-200 ease-in-out focus:outline-none">
              <span id="toggleThumb" aria-hidden="true" class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out translate-x-0"></span>
            </button>
            <span id="annualLabel" class="text-sm font-semibold px-4 py-1.5 rounded-full text-slate-400 hover:text-white transition-all cursor-pointer flex items-center gap-1.5">
              <span>Annual</span>
              <span class="px-2 py-0.5 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full">Save 20%</span>
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <!-- Tier 1: Starter ($29/mo) -->
          <div class="p-8 rounded-2xl glass-card flex flex-col justify-between hover:border-slate-700 transition-all">
            <div>
              <div class="flex items-center justify-between">
                <h3 class="text-xl font-bold text-white">Starter</h3>
                <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">Developers</span>
              </div>
              <p class="mt-3 text-sm text-slate-400">Everything needed to monitor standalone APIs and high-growth microservices.</p>
              <div class="mt-6 flex items-baseline">
                <span class="text-5xl font-extrabold text-white" id="starterCost">$29</span>
                <span class="text-slate-400 text-sm ml-2 font-medium" id="starterCadence">/month</span>
              </div>
              <p class="text-xs text-slate-500 mt-1" id="starterSub">Billed monthly</p>

              <ul class="mt-8 space-y-4 text-sm text-slate-300">
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  10,000,000 monthly API calls
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  14-day raw trace retention
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Automated latency percentile heatmaps
                </li>
              </ul>
            </div>
            <a href="#" class="mt-8 block w-full py-3 text-center text-sm font-semibold text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 rounded-xl border border-slate-700 hover:border-slate-600 transition-all">
              Choose Starter
            </a>
          </div>

          <!-- Tier 2: Pro ($99/mo) -->
          <div class="p-8 rounded-2xl glass-card border-brand-500/50 glow-effect relative flex flex-col justify-between">
            <span class="absolute -top-3 right-8 px-3 py-1 rounded-full text-xs font-bold bg-brand-600 text-white shadow-lg shadow-brand-500/40">
              Most Popular
            </span>
            <div>
              <div class="flex items-center justify-between">
                <h3 class="text-xl font-bold text-white">Pro Enterprise</h3>
                <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">Scale</span>
              </div>
              <p class="mt-3 text-sm text-slate-400">High-throughput architecture for mission-critical core microservices.</p>
              <div class="mt-6 flex items-baseline">
                <span class="text-5xl font-extrabold text-white" id="proCost">$99</span>
                <span class="text-slate-400 text-sm ml-2 font-medium" id="proCadence">/month</span>
              </div>
              <p class="text-xs text-slate-500 mt-1" id="proSub">Billed monthly</p>

              <ul class="mt-8 space-y-4 text-sm text-slate-300">
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  100,000,000 monthly API calls
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  90-day cold retention + S3/BigQuery sync
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Real-time webhook triggers & Slack bot integration
                </li>
                <li class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-brand-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                  Dedicated solutions engineer & Slack connect
                </li>
              </ul>
            </div>
            <a href="#" class="mt-8 block w-full py-3.5 text-center text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 rounded-xl shadow-lg shadow-brand-500/30 hover:shadow-brand-500/50 transition-all">
              Start 14-Day Pro Trial
            </a>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- 5. Clean Minimalist Footer -->
  <footer class="border-t border-slate-800/80 py-12 z-10 bg-slate-950/90">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
      <div class="flex items-center space-x-3">
        <div class="w-6 h-6 rounded-md bg-brand-600 flex items-center justify-center">
          <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
        </div>
        <span class="font-bold text-white text-sm">PulseEngine, Inc.</span>
        <span class="text-xs text-slate-500">|</span>
        <span class="text-xs text-emerald-400 flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          All Systems Operational
        </span>
      </div>
      <div class="flex space-x-6 text-xs text-slate-400">
        <a href="#" class="hover:text-white transition-colors">Privacy Policy</a>
        <a href="#" class="hover:text-white transition-colors">Terms of Service</a>
        <a href="#" class="hover:text-white transition-colors">SOC-2 Compliance</a>
        <a href="#" class="hover:text-white transition-colors">Status</a>
      </div>
      <p class="text-xs text-slate-500">© 2026 PulseEngine, Inc. All rights reserved.</p>
    </div>
  </footer>

  <script>
    const toggle = document.getElementById('billingToggle');
    const thumb = document.getElementById('toggleThumb');
    const monthlyLabel = document.getElementById('monthlyLabel');
    const annualLabel = document.getElementById('annualLabel');
    const starterCost = document.getElementById('starterCost');
    const proCost = document.getElementById('proCost');
    const starterCadence = document.getElementById('starterCadence');
    const proCadence = document.getElementById('proCadence');
    const starterSub = document.getElementById('starterSub');
    const proSub = document.getElementById('proSub');

    let isAnnual = false;
    function renderPricing() {
      if (isAnnual) {
        starterCost.textContent = '$23';
        proCost.textContent = '$79';
        starterCadence.textContent = '/month';
        proCadence.textContent = '/month';
        starterSub.textContent = 'Billed annually ($276/yr)';
        proSub.textContent = 'Billed annually ($948/yr)';

        thumb.classList.remove('translate-x-0');
        thumb.classList.add('translate-x-5');
        toggle.classList.remove('bg-slate-800');
        toggle.classList.add('bg-brand-600');
        toggle.setAttribute('aria-checked', 'true');

        annualLabel.classList.add('bg-brand-600', 'text-white');
        annualLabel.classList.remove('text-slate-400');
        monthlyLabel.classList.remove('bg-brand-600', 'text-white');
        monthlyLabel.classList.add('text-slate-400');
      } else {
        starterCost.textContent = '$29';
        proCost.textContent = '$99';
        starterCadence.textContent = '/month';
        proCadence.textContent = '/month';
        starterSub.textContent = 'Billed monthly';
        proSub.textContent = 'Billed monthly';

        thumb.classList.remove('translate-x-5');
        thumb.classList.add('translate-x-0');
        toggle.classList.remove('bg-brand-600');
        toggle.classList.add('bg-slate-800');
        toggle.setAttribute('aria-checked', 'false');

        monthlyLabel.classList.add('bg-brand-600', 'text-white');
        monthlyLabel.classList.remove('text-slate-400');
        annualLabel.classList.remove('bg-brand-600', 'text-white');
        annualLabel.classList.add('text-slate-400');
      }
    }

    toggle.addEventListener('click', () => { isAnnual = !isAnnual; renderPricing(); });
    monthlyLabel.addEventListener('click', () => { isAnnual = false; renderPricing(); });
    annualLabel.addEventListener('click', () => { isAnnual = true; renderPricing(); });

    const mobileBtn = document.getElementById('mobileMenuBtn');
    const mobileDrawer = document.getElementById('mobileDrawer');
    if (mobileBtn && mobileDrawer) {
      mobileBtn.addEventListener('click', () => {
        mobileDrawer.classList.toggle('hidden');
      });
    }
  </script>
</body>
</html>
"""

