import React, { useState } from 'react';
import {
  Mic,
  Zap,
  Shield,
  ArrowRight,
  Server,
  Phone,
  CreditCard,
  CheckCircle,
  Clock,
  AlertTriangle,
  Calendar,
  Layers,
  ChevronRight,
  ExternalLink,
  Sparkles,
  Lock,
  RotateCcw,
  Sliders,
  DollarSign,
  TrendingUp,
  Cpu,
  Smartphone
} from 'lucide-react';

export default function JobLatchLanding() {
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState('electrical');

  const tradePills = [
    { id: 'electrical', label: '⚡ Electrical Contractors', avgTicket: '$1,850', emergType: 'Burning Odor / Sparking Panel' },
    { id: 'hvac', label: '❄️ HVAC & Mechanical', avgTicket: '$2,400', emergType: 'No Heat in Freezing Weather / Frozen Coil' },
    { id: 'plumbing', label: '🔧 Emergency Plumbing', avgTicket: '$1,250', emergType: 'Burst Pipe / Active Water Heater Leak' },
    { id: 'roofing', label: '🏠 Roofing & Restoration', avgTicket: '$3,800', emergType: 'Storm Damage / Tree on Roof' }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-cyan-200 antialiased overflow-x-hidden">
      {/* BACKGROUND GLOWS */}
      <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-gradient-to-b from-blue-600/20 via-cyan-500/10 to-transparent blur-[140px]"></div>
        <div className="absolute top-[800px] left-1/4 w-[600px] h-[600px] bg-indigo-600/15 rounded-full blur-[160px]"></div>
        <div className="absolute top-[1600px] right-1/4 w-[700px] h-[700px] bg-cyan-600/15 rounded-full blur-[170px]"></div>
      </div>

      {/* 1. TOP NAVIGATION */}
      <nav className="border-b border-white/10 bg-slate-950/70 backdrop-blur-xl sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/25 border border-cyan-400/40">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xl font-extrabold tracking-tight text-white">
                JobLatch<span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">.ai</span>
              </span>
              <span className="hidden sm:inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-cyan-950 text-cyan-300 border border-cyan-500/30 ml-2">
                Gemini 2.0 Flash
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#demo" className="hover:text-cyan-400 transition-colors flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Interactive Demo
            </a>
            <a href="#features" className="hover:text-white transition-colors">Core Engine</a>
            <a href="#triage" className="hover:text-white transition-colors">Safety Triage</a>
            <a href="#integrations" className="hover:text-white transition-colors">FSM Integrations</a>
            <a href="#roi" className="hover:text-white transition-colors">ROI Calculator</a>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="https://joblatchai.com"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 transition"
            >
              Open Direct App <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
            <a
              href="#demo"
              className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold px-5 py-2.5 rounded-xl text-sm transition-all shadow-lg shadow-cyan-500/20 flex items-center gap-2 group"
            >
              Test Sarah AI
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>
          </div>
        </div>
      </nav>

      {/* 2. HERO SECTION */}
      <section className="relative max-w-7xl mx-auto px-6 pt-20 pb-20 text-center">
        {/* Eyebrow Announcement Pill */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900/90 border border-cyan-500/30 text-cyan-300 text-xs sm:text-sm font-semibold mb-8 shadow-xl backdrop-blur-md">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>Sub-Second Speech-to-Speech Engine</span>
          <span className="hidden sm:inline text-slate-500">•</span>
          <span className="hidden sm:inline text-slate-400">Zero Voicemails. 100% Locked Dispatches.</span>
        </div>

        {/* Hero Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1] max-w-5xl mx-auto">
          Autonomous 24/7 Voice Dispatch{' '}
          <span className="block mt-2 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-400">
            for Trade Contractors.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-lg sm:text-xl text-slate-400 max-w-3xl mx-auto mb-10 leading-relaxed font-normal">
          Never lose another <strong className="text-white font-semibold">$3,500 emergency job</strong> to voicemail or tired call centers.
          Sarah AI answers in 1 ring, diagnoses technical hazards, places <strong className="text-cyan-300 font-semibold">$89–$199 Stripe pre-auth holds</strong> on the homeowner's card, and syncs directly into ServiceTitan or Housecall Pro while you sleep.
        </p>

        {/* Trade Contractor Audience Selector Bar */}
        <div className="max-w-4xl mx-auto mb-12 p-1.5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl flex flex-wrap justify-center gap-1.5">
          {tradePills.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                activeTab === t.id
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30 border border-cyan-400/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Call-to-Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-14">
          <a
            href="#demo"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 hover:from-cyan-300 hover:to-blue-500 text-slate-950 font-extrabold text-base transition-all shadow-xl shadow-cyan-500/25 flex items-center justify-center gap-2 group"
          >
            Launch Interactive Demo Console
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>
          <a
            href="#roi"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 font-bold text-base border border-slate-700/80 transition-all flex items-center justify-center gap-2"
          >
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            Calculate Lost Revenue
          </a>
        </div>

        {/* Trust Badges Strip */}
        <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs sm:text-sm font-medium text-slate-400 max-w-4xl mx-auto border-t border-slate-800/80 pt-8">
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-cyan-400" />
            <span>Twilio Voice SIP Trunking</span>
          </div>
          <div className="flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-emerald-400" />
            <span>Stripe Pre-Auth Deposit Holds</span>
          </div>
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-blue-400" />
            <span>ServiceTitan &amp; Housecall Pro 2-Way Sync</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-amber-400" />
            <span>NFPA 70E Safety Compliance</span>
          </div>
        </div>
      </section>

      {/* 3. STYLIZED MACOS-LIKE BROWSER WINDOW WRAPPER (#demo) */}
      <section id="demo" className="max-w-7xl mx-auto px-4 sm:px-6 pb-28">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 text-xs font-bold mb-3">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            LIVE PRODUCTION SANDBOX
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Try Sarah AI On Your Actual Business Call Flow
          </h2>
          <p className="text-slate-400 text-sm sm:text-base mt-2 max-w-2xl mx-auto">
            Interact with the actual live dispatch engine below. Trigger simulated dropped calls, test emergency electrical triage, inspect live Stripe pre-authorizations, and view printable work orders in real-time.
          </p>
        </div>

        <div className="relative group">
          {/* Neon Glow Aura */}
          <div className="absolute -inset-1.5 bg-gradient-to-r from-cyan-500/30 via-blue-600/40 to-indigo-600/30 rounded-3xl blur-2xl opacity-50 group-hover:opacity-80 transition duration-1000"></div>

          {/* macOS Browser Mockup */}
          <div className="relative rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl overflow-hidden flex flex-col h-[780px]">
            {/* macOS Chrome Header */}
            <div className="h-13 bg-slate-950/90 border-b border-slate-800 px-4 py-3 flex items-center justify-between gap-4 backdrop-blur-md">
              {/* Traffic Light Buttons */}
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-full bg-red-500/90 hover:opacity-80 cursor-pointer shadow-sm"></div>
                <div className="w-3.5 h-3.5 rounded-full bg-yellow-500/90 hover:opacity-80 cursor-pointer shadow-sm"></div>
                <div className="w-3.5 h-3.5 rounded-full bg-green-500/90 hover:opacity-80 cursor-pointer shadow-sm"></div>
              </div>

              {/* URL Address Bar */}
              <div className="flex-1 max-w-xl mx-auto bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-1.5 text-xs text-slate-300 flex items-center justify-between font-mono shadow-inner">
                <div className="flex items-center gap-2 truncate">
                  <Lock className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <span className="text-slate-400">https://</span>
                  <span className="text-white font-semibold">joblatchai.com</span>
                  <span className="text-cyan-400 text-[11px] font-sans px-1.5 py-0.2 rounded bg-cyan-950 border border-cyan-800/50">LIVE APP</span>
                </div>
                <div className="flex items-center gap-2 text-slate-500">
                  <RotateCcw
                    className="w-3.5 h-3.5 hover:text-white cursor-pointer transition"
                    onClick={() => {
                      const iframe = document.getElementById('demoIframe');
                      if (iframe) iframe.src = iframe.src;
                    }}
                    title="Reload demo"
                  />
                </div>
              </div>

              {/* Header Right Actions */}
              <div className="flex items-center gap-2">
                <a
                  href="https://joblatchai.com"
                  target="_blank"
                  rel="noreferrer"
                  className="hidden sm:inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
                >
                  <span>Open Fullscreen</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>
              </div>
            </div>

            {/* Embedded Live Web Application */}
            <div className="flex-1 bg-slate-950 relative overflow-hidden">
              {!iframeLoaded && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950 text-slate-400 gap-3 z-10">
                  <div className="w-8 h-8 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin"></div>
                  <span className="text-sm font-medium">Connecting to JobLatch AI Dispatch Server...</span>
                </div>
              )}
              <iframe
                id="demoIframe"
                src="https://joblatchai.com"
                onLoad={() => setIframeLoaded(true)}
                className="absolute inset-0 w-full h-full border-none bg-slate-950"
                title="JobLatch AI Live Interactive Demo"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              ></iframe>
            </div>
          </div>
        </div>
      </section>

      {/* 4. KEY FINANCIAL ROI & VALUE PROP RIBBON */}
      <section id="roi" className="border-y border-white/10 bg-slate-900/50 backdrop-blur-sm py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h3 className="text-xs uppercase tracking-widest text-cyan-400 font-bold mb-2">Hard Contractor ROI</h3>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white">The Real Cost of 1 Missed Call After 5:00 PM</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-6 text-center">
              <div className="text-4xl font-extrabold text-cyan-400 mb-1">2.8s</div>
              <div className="text-sm font-bold text-white mb-2">Missed-Call SMS Recovery</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Homeowner gets an instant 1-tap booking link texted before they can click your competitor on Google LSA.
              </p>
            </div>

            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-6 text-center">
              <div className="text-4xl font-extrabold text-emerald-400 mb-1">$14,200</div>
              <div className="text-sm font-bold text-white mb-2">Avg. Monthly Recouped Revenue</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Capturing 4-6 after-hours emergency calls per month that normally bounce straight to voicemail.
              </p>
            </div>

            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-6 text-center">
              <div className="text-4xl font-extrabold text-blue-400 mb-1">100%</div>
              <div className="text-sm font-bold text-white mb-2">Stripe Pre-Auth Capture Rate</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Pre-authorized deposit hold ($89–$199) locks the job commitment. Zero phantom rollouts or ghosted appointments.
              </p>
            </div>

            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-6 text-center">
              <div className="text-4xl font-extrabold text-purple-400 mb-1">$7,800/yr</div>
              <div className="text-sm font-bold text-white mb-2">Call Center Savings</div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Completely replaces sluggish $650/mo human answering services with instant, trade-literate AI triage.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. HOW IT WORKS (3-STEP TRADE CONTRACTOR PIPELINE) */}
      <section className="py-28 max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-950 text-blue-400 text-xs font-bold mb-3 border border-blue-500/30">
            AUTONOMOUS WORKFLOW
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            How JobLatch Locks In Jobs While You're in the Field
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto mt-3 text-sm sm:text-base">
            From first ring to signed work order, your trucks are booked with zero administrative overhead.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Step 1 */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 relative flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-blue-600/20 text-blue-400 font-extrabold text-xl flex items-center justify-center border border-blue-500/30 mb-6">
              1
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-3">1-Ring Instant Pickup or 3s SMS Recovery</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Sarah AI answers calls with ultra-low latency voice. If a caller hangs up before connecting, JobLatch fires a custom SMS with an instant self-scheduling link in under 3 seconds.
              </p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-cyan-300">
              ⚡ Sent self-scheduling SMS link to homeowner in 2.8s
            </div>
          </div>

          {/* Step 2 */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 relative flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-cyan-600/20 text-cyan-400 font-extrabold text-xl flex items-center justify-center border border-cyan-500/30 mb-6">
              2
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-3">NFPA 70E Safety Triage &amp; Calendar Matrix</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Diagnoses thermal hazards, burning odors, or arcing panels. Gives real-time life-safety directions and matches qualified electricians based on certifications and live vehicle GPS location.
              </p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-emerald-400">
              ✓ Assigned Marcus Vance (Master Lead • TRUCK-01)
            </div>
          </div>

          {/* Step 3 */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 relative flex flex-col justify-between">
            <div className="w-12 h-12 rounded-xl bg-indigo-600/20 text-indigo-400 font-extrabold text-xl flex items-center justify-center border border-indigo-500/30 mb-6">
              3
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-3">$89–$199 Stripe Pre-Auth &amp; FSM Push</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Places an authorization hold without charging the card immediately. Automatically creates the work order ticket in ServiceTitan, Housecall Pro, or Jobber with customer credentials pre-filled.
              </p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-purple-300">
              ✓ Stripe Pre-Auth Hold Active • Synced to ServiceTitan #ST-1002
            </div>
          </div>
        </div>
      </section>

      {/* 6. CORE FEATURES GRID */}
      <section id="features" className="py-20 bg-slate-900/40 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Built Exclusively for Trade Contractors
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto mt-2 text-sm sm:text-base">
              Generic chatbots fail on construction terms. JobLatch AI is trained on trade codebooks, hazard tiers, and real contracting business math.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-cyan-500/40 transition">
              <div className="w-10 h-10 rounded-xl bg-cyan-950 text-cyan-400 flex items-center justify-center border border-cyan-800/40 mb-4">
                <Mic className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Natural Conversational Flow</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
                Powered by Gemini 2.0 Flash. Sarah sounds like your most experienced shop dispatcher. Handles interruptions, background noise, and caller panic smoothly.
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-red-500/40 transition">
              <div className="w-10 h-10 rounded-xl bg-red-950 text-red-400 flex items-center justify-center border border-red-800/40 mb-4">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">NFPA 70E Code Red Triage</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
                Detects electrical smoke, water near live panels, and arcing. Instructs callers on breaker isolation and triggers immediate high-priority alert emails with ICS calendar links.
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-emerald-500/40 transition">
              <div className="w-10 h-10 rounded-xl bg-emerald-950 text-emerald-400 flex items-center justify-center border border-emerald-800/40 mb-4">
                <CreditCard className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">7-Day Stripe Pre-Auth Holds</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
                Direct Connect charges place temporary holds ($89 standard, $199 emergency). Settles instantly when tech logs on-site arrival on their tablet.
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-blue-500/40 transition">
              <div className="w-10 h-10 rounded-xl bg-blue-950 text-blue-400 flex items-center justify-center border border-blue-800/40 mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Native FSM Webhook Sync</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
                Zero double entry. Dispatches convert into standard API payloads for ServiceTitan, Housecall Pro, Jobber, and QuickBooks Online instantly.
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-purple-500/40 transition">
              <div className="w-10 h-10 rounded-xl bg-purple-950 text-purple-400 flex items-center justify-center border border-purple-800/40 mb-4">
                <Calendar className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Two-Way Google Calendar Sync</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
                Reads busy blocks from each electrician's personal calendar. Generates RFC 5545 master calendar feeds and individual tech alerts automatically.
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-amber-500/40 transition">
              <div className="w-10 h-10 rounded-xl bg-amber-950 text-amber-400 flex items-center justify-center border border-amber-800/40 mb-4">
                <Smartphone className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Field Tech Rugged Tablet View</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">
                Electricians in the truck receive instant dispatch dossiers, access codes, customer panel pictures, and on-site digital signature sign-offs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 7. FSM INTEGRATION ECOSYSTEM */}
      <section id="integrations" className="py-20 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <h3 className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-3">Seamless Compatibility</h3>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-8">Works with Your Existing Contractor Software</h2>
          
          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 max-w-4xl mx-auto">
            <div className="px-5 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-semibold text-sm flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-400" />
              ServiceTitan
            </div>
            <div className="px-5 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-semibold text-sm flex items-center gap-2">
              <span className="text-cyan-400">🏠</span>
              Housecall Pro
            </div>
            <div className="px-5 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-semibold text-sm flex items-center gap-2">
              <span className="text-emerald-400">💼</span>
              Jobber
            </div>
            <div className="px-5 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-semibold text-sm flex items-center gap-2">
              <span className="text-green-400">📗</span>
              QuickBooks Online
            </div>
            <div className="px-5 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-semibold text-sm flex items-center gap-2">
              <Calendar className="w-4 h-4 text-purple-400" />
              Google Calendar
            </div>
            <div className="px-5 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-semibold text-sm flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-cyan-400" />
              Stripe Connect
            </div>
          </div>
        </div>
      </section>

      {/* 8. BOTTOM HERO / CTA */}
      <section className="py-24 bg-gradient-to-b from-slate-950 via-blue-950/20 to-slate-950 border-t border-slate-800 relative">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center mx-auto mb-6 shadow-xl shadow-cyan-500/20 border border-cyan-400/40">
            <Zap className="w-8 h-8 text-slate-950 font-bold" />
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-6">
            Stop Losing Emergency Revenue to Voicemail.
          </h2>
          <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
            Deploy JobLatch AI on your shop's phone line today. Answer every midnight emergency, capture guaranteed upfront holds, and keep your crews fully booked.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="#demo"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-extrabold text-base transition-all shadow-xl shadow-cyan-400/20"
            >
              Test Live Interactive Demo
            </a>
            <a
              href="mailto:dispatch@joblatchai.com"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 font-bold text-base border border-slate-700 transition"
            >
              Contact Sales &amp; Onboarding
            </a>
          </div>
        </div>
      </section>

      {/* 9. FOOTER */}
      <footer className="border-t border-slate-800/80 py-12 bg-slate-950 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
              ⚡
            </div>
            <span className="font-bold text-slate-300">JobLatch AI</span>
            <span>&bull; Autonomous Voice Dispatch for Trade Contractors</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://joblatchai.com" className="hover:text-slate-300 transition">Live Demo Console</a>
            <a href="https://joblatchai.com/monitor" className="hover:text-slate-300 transition">Dispatch Monitor</a>
            <a href="https://joblatchai.com/api/dispatches" className="hover:text-slate-300 transition">REST API</a>
            <span className="text-slate-600">&copy; {new Date().getFullYear()} JobLatch AI</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
