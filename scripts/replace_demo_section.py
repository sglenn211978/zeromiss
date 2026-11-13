#!/usr/bin/env python3
"""Replaces the old placeholder audio preview in index.html with the full 3-scenario showcase."""

from pathlib import Path

INDEX_PATH = Path(__file__).resolve().parent.parent / "index.html"

NEW_SECTION = '''    <!-- 3. "HEAR IT + SEE THE TICKET" LIVE AUDIO & DISPATCH SHOWCASE (#audio-preview) -->
    <section id="audio-preview" class="border-y border-carbon-800 bg-carbon-900/60 py-20 relative">
        <div class="max-w-7xl mx-auto px-4 sm:px-6">
            <div class="text-center mb-10">
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono font-bold mb-3">
                    <i data-lucide="headphones" class="w-3.5 h-3.5 text-amber-400"></i>
                    HEAR IT + SEE THE TICKET &bull; REAL DISPATCH ENGINE OUTPUTS
                </div>
                <h2 class="text-3xl sm:text-4xl font-extrabold text-white font-display">
                    Listen to a Live Call &amp; See the Dispatch Ticket
                </h2>
                <p class="text-slate-300 text-sm sm:text-base max-w-2xl mx-auto mt-2">
                    Real two-speaker audio synthesized from our live voice dispatch pipeline paired side-by-side with the exact structured work order tickets created in your FSM software.
                </p>
            </div>

            <!-- 3 Scenario Selector Tabs -->
            <div class="flex flex-wrap items-center justify-center gap-2 sm:gap-3 mb-8 max-w-4xl mx-auto" role="tablist">
                <button 
                    type="button"
                    id="callTab-emergency"
                    onclick="switchCallDemo('emergency')"
                    class="call-demo-tab px-4 py-2.5 rounded-xl font-mono text-xs font-bold transition flex items-center gap-2 bg-amber-500 text-carbon-950 shadow-lg shadow-amber-500/20 active:scale-95"
                >
                    <span class="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
                    <span>1. 11:48 PM Emergency Call</span>
                    <span class="text-[10px] opacity-75 font-normal hidden sm:inline">(Cherry Hill, NJ)</span>
                </button>
                <button 
                    type="button"
                    id="callTab-ev-charger"
                    onclick="switchCallDemo('ev-charger')"
                    class="call-demo-tab px-4 py-2.5 rounded-xl font-mono text-xs font-semibold text-slate-300 hover:text-white bg-carbon-900 border border-carbon-700 transition flex items-center gap-2 active:scale-95"
                >
                    <span class="w-2 h-2 rounded-full bg-electric-400"></span>
                    <span>2. Level 2 EV Charger Lead</span>
                    <span class="text-[10px] text-slate-400 font-normal hidden sm:inline">(Moorestown, NJ)</span>
                </button>
                <button 
                    type="button"
                    id="callTab-filtered"
                    onclick="switchCallDemo('filtered')"
                    class="call-demo-tab px-4 py-2.5 rounded-xl font-mono text-xs font-semibold text-slate-300 hover:text-white bg-carbon-900 border border-carbon-700 transition flex items-center gap-2 active:scale-95"
                >
                    <span class="w-2 h-2 rounded-full bg-slate-400"></span>
                    <span>3. Out-of-Area Filter</span>
                    <span class="text-[10px] text-slate-400 font-normal hidden sm:inline">(Princeton, NJ)</span>
                </button>
            </div>

            <!-- SCENARIO 1: AFTER-HOURS EMERGENCY PANEL -->
            <div id="callPanel-emergency" class="call-demo-panel">
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start max-w-6xl mx-auto">
                    <!-- Left Column: Audio Player & Live Spoken Transcript -->
                    <div class="lg:col-span-5 chassis-card rounded-2xl p-5 sm:p-6 hardware-corner flex flex-col h-full">
                        <div class="flex items-center justify-between pb-3 border-b border-carbon-800 mb-4">
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                                <span class="text-xs font-mono font-bold text-red-400 uppercase tracking-wider">Scenario A &bull; Emergency</span>
                            </div>
                            <span class="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                                1:34 Audio
                            </span>
                        </div>

                        <div class="mb-4">
                            <h3 class="text-base font-bold font-display text-white mb-1">
                                Burning Odor + Buzzing Breaker Panel
                            </h3>
                            <p class="text-xs text-slate-300 font-mono">
                                Caller: Mike Reynolds &bull; 11:48 PM
                            </p>
                        </div>

                        <!-- Browser-Ready HTML5 Audio Player -->
                        <div class="p-3 rounded-xl bg-carbon-950 border border-carbon-800 mb-4">
                            <label class="block text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                                <span>Voice Dispatch Audio Stream</span>
                                <span class="text-electric-400">Two-Speaker Recording</span>
                            </label>
                            <audio 
                                controls 
                                preload="metadata" 
                                src="/assets/demo/demo-emergency.mp3" 
                                class="w-full h-10 rounded-lg call-demo-audio accent-amber-500"
                            >
                                Your browser does not support the audio element.
                            </audio>
                        </div>

                        <!-- Spoken Dialogue Transcript Box -->
                        <div class="flex-1">
                            <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                                <i data-lucide="message-square" class="w-3.5 h-3.5 text-amber-400"></i>
                                <span>Spoken Call Transcript</span>
                            </span>
                            <div class="space-y-3 font-mono text-xs max-h-72 overflow-y-auto pr-1">
                                <!-- Turn 1 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-electric-500/20 text-slate-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-electric-400">Sarah (JobLatch Dispatcher)</span>
                                        <span class="text-slate-500">0:00</span>
                                    </div>
                                    <p class="leading-relaxed">"Thank you for calling JobLatch AI Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?"</p>
                                </div>
                                <!-- Turn 2 -->
                                <div class="p-2.5 rounded-lg bg-carbon-950 border border-carbon-800 text-slate-300">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-slate-300">Mike Reynolds (Caller)</span>
                                        <span class="text-slate-500">0:08</span>
                                    </div>
                                    <p class="leading-relaxed">"Hi, this is Mike Reynolds. I smell burning plastic and there's a buzzing sound coming from the breaker panel in my basement. Half my kitchen just lost power."</p>
                                </div>
                                <!-- Turn 3 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-amber-500/30 text-amber-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-amber-400">Sarah (Safety-First Triage)</span>
                                        <span class="text-slate-500">0:18</span>
                                    </div>
                                    <p class="leading-relaxed">"Please listen carefully for your safety. A burning rubber or plastic smell indicates electrical wire insulation is dangerously overheating. If you can safely access your breaker panel, shut off the breaker for that circuit immediately. Do NOT touch any scorched, hot, buzzing, or discolored outlets, switches, or appliances. I am alerting our on-call master electrician right now. What is your street address and best callback phone number?"</p>
                                </div>
                                <!-- Turn 4 -->
                                <div class="p-2.5 rounded-lg bg-carbon-950 border border-carbon-800 text-slate-300">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-slate-300">Mike Reynolds (Caller)</span>
                                        <span class="text-slate-500">0:52</span>
                                    </div>
                                    <p class="leading-relaxed">"It's 418 Oakwood Ave, Cherry Hill, New Jersey. My callback is 856-555-0142."</p>
                                </div>
                                <!-- Turn 5 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-emerald-500/30 text-emerald-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-emerald-400">Sarah (Dispatch Confirmed)</span>
                                        <span class="text-slate-500">0:59</span>
                                    </div>
                                    <p class="leading-relaxed">"Emergency dispatch is confirmed under reference ZM-EMERG-1005. Marcus Vance (Master Electrician On-Call) is en route to 418 Oakwood Ave, Cherry Hill, New Jersey right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Right Column: Real Structured Dispatch Ticket -->
                    <div class="lg:col-span-7 chassis-card rounded-2xl p-5 sm:p-6 hardware-corner flex flex-col h-full bg-carbon-950/90 border border-carbon-700">
                        <!-- Ticket Header Bar -->
                        <div class="flex items-center justify-between pb-3.5 border-b border-carbon-800 mb-4">
                            <div class="flex items-center gap-2 sm:gap-3">
                                <span class="px-2.5 py-1 rounded bg-carbon-900 border border-carbon-750 font-mono text-xs font-bold text-white flex items-center gap-1.5">
                                    <i data-lucide="file-text" class="w-3.5 h-3.5 text-amber-400"></i>
                                    <span>ZM-EMERG-1005</span>
                                </span>
                                <span class="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-[10px] font-mono text-blue-300">
                                    Housecall Pro #HCP-1005
                                </span>
                            </div>
                            <span class="px-2.5 py-1 rounded-full bg-red-500/15 border border-red-500/40 text-red-400 font-mono text-[10px] font-bold flex items-center gap-1">
                                <span class="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping"></span>
                                EMERGENCY CODE RED
                            </span>
                        </div>

                        <!-- Ticket Details Grid -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs mb-4">
                            <!-- Caller & Phone -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Caller / Contact</span>
                                <span class="font-bold text-white text-sm block">Mike Reynolds</span>
                                <span class="text-amber-400">(856) 555-0142</span>
                            </div>

                            <!-- Address & Town -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Service Address</span>
                                <span class="font-bold text-white block">418 Oakwood Ave</span>
                                <span class="text-emerald-400 flex items-center gap-1">
                                    <i data-lucide="check" class="w-3 h-3"></i>
                                    Cherry Hill, NJ (In Territory)
                                </span>
                            </div>

                            <!-- Assigned Technician -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Assigned On-Call Lead</span>
                                <span class="font-bold text-white block">Marcus Vance</span>
                                <span class="text-slate-300 text-[11px]">Master Electrician &bull; TRUCK-01</span>
                            </div>

                            <!-- Arrival Window -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Arrival ETA</span>
                                <span class="font-bold text-red-400 block">45–60 Minutes</span>
                                <span class="text-slate-400 text-[11px]">Priority Emergency Route</span>
                            </div>
                        </div>

                        <!-- Hazard Triage & Safety Guidance Box -->
                        <div class="p-3.5 rounded-xl bg-red-950/20 border border-red-500/30 mb-4 font-mono text-xs">
                            <div class="flex items-center gap-1.5 text-red-400 font-bold mb-1">
                                <i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>
                                <span>Hazard Triage Assessment &bull; Burning Plastic Insulation</span>
                            </div>
                            <p class="text-slate-300 leading-relaxed text-[11px]">
                                Thermal degradation detected on basement panel with active buzzing and partial kitchen outage. Homeowner instructed to de-energize circuit breaker if safe and evacuate/call 911 if flame occurs.
                            </p>
                        </div>

                        <!-- Financials / Revenue Recouped Strip -->
                        <div class="grid grid-cols-2 gap-3 p-3 rounded-xl bg-carbon-900 border border-carbon-800 mb-4 font-mono text-xs">
                            <div>
                                <span class="text-[10px] uppercase text-slate-400 block">Emergency Pre-Auth Hold</span>
                                <span class="font-bold text-amber-400 text-sm">$199.00</span>
                                <span class="text-[10px] text-slate-400 block">SMS Card Pre-Auth Queued</span>
                            </div>
                            <div>
                                <span class="text-[10px] uppercase text-slate-400 block">Estimated Job Value</span>
                                <span class="font-bold text-emerald-400 text-sm">+$1,850.00</span>
                                <span class="text-[10px] text-slate-400 block">Panel Rebuild / Diagnostic</span>
                            </div>
                        </div>

                        <!-- Actions Automated -->
                        <div class="border-t border-carbon-800 pt-3 mt-auto">
                            <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">Automated Actions Executed:</span>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] font-mono text-slate-300">
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Ring-1 Spoken Safety Triage</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Master Electrician Truck Alert</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Synced to Housecall Pro (HCP-1005)</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Stripe Pre-Auth SMS Sent</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SCENARIO 2: HIGH-VALUE EV CHARGER LEAD PANEL -->
            <div id="callPanel-ev-charger" class="call-demo-panel hidden">
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start max-w-6xl mx-auto">
                    <!-- Left Column: Audio Player & Live Spoken Transcript -->
                    <div class="lg:col-span-5 chassis-card rounded-2xl p-5 sm:p-6 hardware-corner flex flex-col h-full">
                        <div class="flex items-center justify-between pb-3 border-b border-carbon-800 mb-4">
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-electric-400 animate-pulse"></span>
                                <span class="text-xs font-mono font-bold text-electric-400 uppercase tracking-wider">Scenario B &bull; High-Value Lead</span>
                            </div>
                            <span class="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                                1:10 Audio
                            </span>
                        </div>

                        <div class="mb-4">
                            <h3 class="text-base font-bold font-display text-white mb-1">
                                Level 2 Tesla Charger Installation
                            </h3>
                            <p class="text-xs text-slate-300 font-mono">
                                Caller: Sarah Jenkins &bull; Daytime Inquiry
                            </p>
                        </div>

                        <!-- Browser-Ready HTML5 Audio Player -->
                        <div class="p-3 rounded-xl bg-carbon-950 border border-carbon-800 mb-4">
                            <label class="block text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                                <span>Voice Dispatch Audio Stream</span>
                                <span class="text-electric-400">Two-Speaker Recording</span>
                            </label>
                            <audio 
                                controls 
                                preload="metadata" 
                                src="/assets/demo/demo-ev-charger.mp3" 
                                class="w-full h-10 rounded-lg call-demo-audio accent-amber-500"
                            >
                                Your browser does not support the audio element.
                            </audio>
                        </div>

                        <!-- Spoken Dialogue Transcript Box -->
                        <div class="flex-1">
                            <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                                <i data-lucide="message-square" class="w-3.5 h-3.5 text-amber-400"></i>
                                <span>Spoken Call Transcript</span>
                            </span>
                            <div class="space-y-3 font-mono text-xs max-h-72 overflow-y-auto pr-1">
                                <!-- Turn 1 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-electric-500/20 text-slate-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-electric-400">Sarah (JobLatch Dispatcher)</span>
                                        <span class="text-slate-500">0:00</span>
                                    </div>
                                    <p class="leading-relaxed">"Thank you for calling JobLatch AI Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?"</p>
                                </div>
                                <!-- Turn 2 -->
                                <div class="p-2.5 rounded-lg bg-carbon-950 border border-carbon-800 text-slate-300">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-slate-300">Sarah Jenkins (Caller)</span>
                                        <span class="text-slate-500">0:08</span>
                                    </div>
                                    <p class="leading-relaxed">"Hi, I'd like a quote to install a Level 2 Tesla charger in my attached garage. I have a 200 amp main panel in the basement, so it's about a 50 to 60 foot run."</p>
                                </div>
                                <!-- Turn 3 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-electric-500/30 text-electric-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-electric-400">Sarah (Calendar Sync)</span>
                                        <span class="text-slate-500">0:19</span>
                                    </div>
                                    <p class="leading-relaxed">"I have an opening available tomorrow during our 12:00 PM - 04:00 PM window with Sarah Chen. To reserve that for you, may I have your full name, callback phone number, street address, and email?"</p>
                                </div>
                                <!-- Turn 4 -->
                                <div class="p-2.5 rounded-lg bg-carbon-950 border border-carbon-800 text-slate-300">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-slate-300">Sarah Jenkins (Caller)</span>
                                        <span class="text-slate-500">0:33</span>
                                    </div>
                                    <p class="leading-relaxed">"Sure. My name is Sarah Jenkins, address is 92 Maple St, Moorestown, New Jersey. My phone is 609-555-0188."</p>
                                </div>
                                <!-- Turn 5 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-emerald-500/30 text-emerald-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-emerald-400">Sarah (Estimate Booked)</span>
                                        <span class="text-slate-500">0:43</span>
                                    </div>
                                    <p class="leading-relaxed">"You're all confirmed, Sarah Jenkins. We have Sarah Chen scheduled for tomorrow during our 12:00 PM - 04:00 PM window. Your confirmation number is ZM-BOOK-1008, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Right Column: Real Structured Dispatch Ticket -->
                    <div class="lg:col-span-7 chassis-card rounded-2xl p-5 sm:p-6 hardware-corner flex flex-col h-full bg-carbon-950/90 border border-carbon-700">
                        <!-- Ticket Header Bar -->
                        <div class="flex items-center justify-between pb-3.5 border-b border-carbon-800 mb-4">
                            <div class="flex items-center gap-2 sm:gap-3">
                                <span class="px-2.5 py-1 rounded bg-carbon-900 border border-carbon-750 font-mono text-xs font-bold text-white flex items-center gap-1.5">
                                    <i data-lucide="file-text" class="w-3.5 h-3.5 text-amber-400"></i>
                                    <span>ZM-BOOK-1008</span>
                                </span>
                                <span class="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-[10px] font-mono text-blue-300">
                                    Housecall Pro #HCP-1008
                                </span>
                            </div>
                            <span class="px-2.5 py-1 rounded-full bg-electric-500/15 border border-electric-500/40 text-electric-300 font-mono text-[10px] font-bold flex items-center gap-1">
                                <i data-lucide="calendar" class="w-3 h-3 text-electric-400"></i>
                                CONFIRMED APPOINTMENT
                            </span>
                        </div>

                        <!-- Ticket Details Grid -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs mb-4">
                            <!-- Caller & Phone -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Customer / Contact</span>
                                <span class="font-bold text-white text-sm block">Sarah Jenkins</span>
                                <span class="text-amber-400">(609) 555-0188</span>
                            </div>

                            <!-- Address & Town -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Service Address</span>
                                <span class="font-bold text-white block">92 Maple St</span>
                                <span class="text-emerald-400 flex items-center gap-1">
                                    <i data-lucide="check" class="w-3 h-3"></i>
                                    Moorestown, NJ (In Territory)
                                </span>
                            </div>

                            <!-- Assigned Technician -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Assigned Specialist</span>
                                <span class="font-bold text-white block">Sarah Chen</span>
                                <span class="text-electric-300 text-[11px]">EV &bull; TRUCK-03 (EV Van)</span>
                            </div>

                            <!-- Appointment Window -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Scheduled Slot</span>
                                <span class="font-bold text-white block">Tomorrow Afternoon</span>
                                <span class="text-amber-400 text-[11px]">12:00 PM – 04:00 PM Window</span>
                            </div>
                        </div>

                        <!-- Scope & Technical Specification Box -->
                        <div class="p-3.5 rounded-xl bg-carbon-900 border border-carbon-800 mb-4 font-mono text-xs">
                            <div class="flex items-center gap-1.5 text-electric-400 font-bold mb-1">
                                <i data-lucide="zap" class="w-3.5 h-3.5"></i>
                                <span>Project Scope &bull; Level 2 EV Charger Consultation</span>
                            </div>
                            <p class="text-slate-300 leading-relaxed text-[11px]">
                                Homeowner requesting Level 2 Tesla wall connector installation in attached garage. 200A main panel located in basement (~50–60 ft run). Automatically matched to EV-certified technician with conduit load routing expertise.
                            </p>
                        </div>

                        <!-- Financials / Revenue Recouped Strip -->
                        <div class="grid grid-cols-2 gap-3 p-3 rounded-xl bg-carbon-900 border border-carbon-800 mb-4 font-mono text-xs">
                            <div>
                                <span class="text-[10px] uppercase text-slate-400 block">Consultation Fee</span>
                                <span class="font-bold text-slate-300 text-sm">$0.00</span>
                                <span class="text-[10px] text-slate-400 block">Free On-Site Estimate</span>
                            </div>
                            <div>
                                <span class="text-[10px] uppercase text-slate-400 block">Estimated Pipeline Value</span>
                                <span class="font-bold text-emerald-400 text-sm">+$1,450.00</span>
                                <span class="text-[10px] text-slate-400 block">Charger + 50ft 240V Circuit</span>
                            </div>
                        </div>

                        <!-- Actions Automated -->
                        <div class="border-t border-carbon-800 pt-3 mt-auto">
                            <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">Automated Actions Executed:</span>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] font-mono text-slate-300">
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Live Calendar Opening Queried</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Matched to EV-Certified Specialist</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Synced to Housecall Pro (HCP-1008)</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Dispatch Notification Queued</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SCENARIO 3: OUT-OF-AREA FILTER PANEL -->
            <div id="callPanel-filtered" class="call-demo-panel hidden">
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start max-w-6xl mx-auto">
                    <!-- Left Column: Audio Player & Live Spoken Transcript -->
                    <div class="lg:col-span-5 chassis-card rounded-2xl p-5 sm:p-6 hardware-corner flex flex-col h-full">
                        <div class="flex items-center justify-between pb-3 border-b border-carbon-800 mb-4">
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-slate-400"></span>
                                <span class="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">Scenario C &bull; Area Filter</span>
                            </div>
                            <span class="text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                                0:49 Audio
                            </span>
                        </div>

                        <div class="mb-4">
                            <h3 class="text-base font-bold font-display text-white mb-1">
                                Out-of-Territory Request Declined Politely
                            </h3>
                            <p class="text-xs text-slate-300 font-mono">
                                Caller from Princeton, NJ &bull; Whole-Home Rewiring
                            </p>
                        </div>

                        <!-- Browser-Ready HTML5 Audio Player -->
                        <div class="p-3 rounded-xl bg-carbon-950 border border-carbon-800 mb-4">
                            <label class="block text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                                <span>Voice Dispatch Audio Stream</span>
                                <span class="text-electric-400">Two-Speaker Recording</span>
                            </label>
                            <audio 
                                controls 
                                preload="metadata" 
                                src="/assets/demo/demo-filtered.mp3" 
                                class="w-full h-10 rounded-lg call-demo-audio accent-amber-500"
                            >
                                Your browser does not support the audio element.
                            </audio>
                        </div>

                        <!-- Spoken Dialogue Transcript Box -->
                        <div class="flex-1">
                            <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                                <i data-lucide="message-square" class="w-3.5 h-3.5 text-amber-400"></i>
                                <span>Spoken Call Transcript</span>
                            </span>
                            <div class="space-y-3 font-mono text-xs max-h-72 overflow-y-auto pr-1">
                                <!-- Turn 1 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-electric-500/20 text-slate-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-electric-400">Sarah (JobLatch Dispatcher)</span>
                                        <span class="text-slate-500">0:00</span>
                                    </div>
                                    <p class="leading-relaxed">"Thank you for calling JobLatch AI Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?"</p>
                                </div>
                                <!-- Turn 2 -->
                                <div class="p-2.5 rounded-lg bg-carbon-950 border border-carbon-800 text-slate-300">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-slate-300">Caller (Princeton, NJ)</span>
                                        <span class="text-slate-500">0:08</span>
                                    </div>
                                    <p class="leading-relaxed">"Hi, I'm calling from Princeton, New Jersey. I need my whole house rewired. Do you cover my area? My number is 609-555-0199."</p>
                                </div>
                                <!-- Turn 3 -->
                                <div class="p-2.5 rounded-lg bg-carbon-900 border border-carbon-700 text-slate-200">
                                    <div class="flex items-center justify-between mb-1 text-[10px]">
                                        <span class="font-bold text-amber-400">Sarah (Territory Filter + Safety)</span>
                                        <span class="text-slate-500">0:17</span>
                                    </div>
                                    <p class="leading-relaxed">"Thanks for calling. Unfortunately Princeton is outside our service area, so we're not able to schedule a technician there. We cover Cherry Hill, Moorestown, Haddonfield, Voorhees and the surrounding towns. I'd recommend contacting a licensed electrician local to Princeton. If you ever smell burning or see sparks, please leave the home and call 911."</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Right Column: Filter Audit & Capacity Protection Card -->
                    <div class="lg:col-span-7 chassis-card rounded-2xl p-5 sm:p-6 hardware-corner flex flex-col h-full bg-carbon-950/90 border border-carbon-700">
                        <!-- Ticket Header Bar -->
                        <div class="flex items-center justify-between pb-3.5 border-b border-carbon-800 mb-4">
                            <div class="flex items-center gap-2 sm:gap-3">
                                <span class="px-2.5 py-1 rounded bg-carbon-900 border border-carbon-750 font-mono text-xs font-bold text-slate-300 flex items-center gap-1.5">
                                    <i data-lucide="shield-alert" class="w-3.5 h-3.5 text-amber-400"></i>
                                    <span>TERRITORY GUARDIAN AUDIT</span>
                                </span>
                                <span class="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-[10px] font-mono text-amber-300">
                                    Zero Human Time Wasted
                                </span>
                            </div>
                            <span class="px-2.5 py-1 rounded-full bg-carbon-800 border border-carbon-700 text-slate-300 font-mono text-[10px] font-bold flex items-center gap-1">
                                <i data-lucide="map-pin-off" class="w-3 h-3 text-amber-400"></i>
                                OUT OF SERVICE RADIUS
                            </span>
                        </div>

                        <!-- Ticket Details Grid -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs mb-4">
                            <!-- Caller & Phone -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Caller Origin</span>
                                <span class="font-bold text-white text-sm block">Princeton, NJ</span>
                                <span class="text-slate-400">(609) 555-0199</span>
                            </div>

                            <!-- Radius Audit -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Coverage Territory</span>
                                <span class="font-bold text-amber-400 block">Outside Shop Radius</span>
                                <span class="text-slate-400 text-[11px]">&gt;35 Miles from Shop Hub</span>
                            </div>

                            <!-- Shop Primary Radius -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Contractor Core Hub</span>
                                <span class="font-bold text-white block">Cherry Hill / Moorestown</span>
                                <span class="text-slate-400 text-[11px]">Camden &amp; Burlington Co.</span>
                            </div>

                            <!-- Board Impact -->
                            <div class="p-3 rounded-xl bg-carbon-900 border border-carbon-800">
                                <span class="text-[10px] uppercase text-slate-400 font-semibold block mb-0.5">Dispatch Board Impact</span>
                                <span class="font-bold text-emerald-400 block">0 Wasted Truck Runs</span>
                                <span class="text-slate-400 text-[11px]">Roster 100% Protected</span>
                            </div>
                        </div>

                        <!-- Technical Triage Assessment Box -->
                        <div class="p-3.5 rounded-xl bg-carbon-900 border border-carbon-800 mb-4 font-mono text-xs">
                            <div class="flex items-center gap-1.5 text-amber-400 font-bold mb-1">
                                <i data-lucide="shield-check" class="w-3.5 h-3.5"></i>
                                <span>Autonomous Filtering &amp; Polite Local Referral</span>
                            </div>
                            <p class="text-slate-300 leading-relaxed text-[11px]">
                                Sarah parsed the caller's stated location (Princeton, NJ), matched it against the contractor's configured township radius, and declined the job politely without booking. She explained the primary territory, recommended local certified contractors, and reminded caller of 911 life-safety precautions.
                            </p>
                        </div>

                        <!-- Capacity Savings Strip -->
                        <div class="grid grid-cols-2 gap-3 p-3 rounded-xl bg-carbon-900 border border-carbon-800 mb-4 font-mono text-xs">
                            <div>
                                <span class="text-[10px] uppercase text-slate-400 block">Windshield Time Saved</span>
                                <span class="font-bold text-amber-400 text-sm">~90+ Minutes</span>
                                <span class="text-[10px] text-slate-400 block">Avoided unproductive drive</span>
                            </div>
                            <div>
                                <span class="text-[10px] uppercase text-slate-400 block">Fuel &amp; Fleet Cost Saved</span>
                                <span class="font-bold text-emerald-400 text-sm">~$150.00</span>
                                <span class="text-[10px] text-slate-400 block">Wear, tear &amp; deadhead miles</span>
                            </div>
                        </div>

                        <!-- Actions Automated -->
                        <div class="border-t border-carbon-800 pt-3 mt-auto">
                            <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">Automated Actions Executed:</span>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] font-mono text-slate-300">
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Town Radius Verification</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Polite Spoken Decline &amp; Referral</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> 911 Life Safety Advisory Given</span>
                                <span class="flex items-center gap-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i> Zero Contractor Schedule Clutter</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Fictional Demo Data Disclaimer -->
            <div class="mt-8 pt-4 border-t border-carbon-800 text-[10px] font-mono text-slate-400 text-center max-w-3xl mx-auto">
                * Simulated trade call scenario. Caller names, addresses (555 exchange), and contractor transaction details are fictional demo data generated by the JobLatch AI voice dispatch pipeline.
            </div>
        </div>
    </section>'''

NEW_JS = '''        // 6. "Hear It + See the Ticket" Interactive Tab Switching
        function switchCallDemo(scenarioId) {
            // Pause any active audio players
            document.querySelectorAll('.call-demo-audio').forEach(audio => {
                audio.pause();
                audio.currentTime = 0;
            });

            // Reset tab buttons & hide all scenario panels
            ['emergency', 'ev-charger', 'filtered'].forEach(id => {
                const panel = document.getElementById(`callPanel-${id}`);
                const tab = document.getElementById(`callTab-${id}`);
                if (panel) panel.classList.add('hidden');
                if (tab) {
                    tab.className = 'call-demo-tab px-4 py-2.5 rounded-xl font-mono text-xs font-semibold text-slate-300 hover:text-white bg-carbon-900 border border-carbon-700 transition flex items-center gap-2 active:scale-95';
                }
            });

            // Activate chosen panel and button
            const activePanel = document.getElementById(`callPanel-${scenarioId}`);
            const activeTab = document.getElementById(`callTab-${scenarioId}`);
            if (activePanel) activePanel.classList.remove('hidden');
            if (activeTab) {
                activeTab.className = 'call-demo-tab px-4 py-2.5 rounded-xl font-mono text-xs font-bold transition flex items-center gap-2 bg-amber-500 text-carbon-950 shadow-lg shadow-amber-500/20 active:scale-95';
            }
            if (window.lucide && typeof lucide.createIcons === 'function') {
                lucide.createIcons();
            }
        }'''

def main():
    content = INDEX_PATH.read_text(encoding="utf-8")
    
    # 1. Replace HTML section 3
    start_marker = '    <!-- 3. "LISTEN TO SARAH IN ACTION" AUDIO PLAYER MODULE (#audio-preview) -->'
    end_marker = '    <!-- 4. LIVE INTERACTIVE DEMO (TACTILE CARBON CHASSIS) (#demo) -->'
    
    if start_marker not in content or end_marker not in content:
        raise RuntimeError("Could not find section 3 markers in index.html")
    
    prefix = content.split(start_marker)[0]
    suffix = content.split(end_marker)[1]
    
    updated = prefix + NEW_SECTION + "\n\n" + end_marker + suffix
    
    # 2. Replace old toggleAudioSimulation JS with switchCallDemo
    js_start = '        // 6. Audio Player Simulation Logic'
    if js_start in updated:
        js_prefix = updated.split(js_start)[0]
        # Keep everything after the function
        js_rest = updated.split(js_start)[1]
        # Find the next section comment or closing script tag
        next_comment_marker = '    </script>'
        if next_comment_marker in js_rest:
            js_suffix = js_rest.split(next_comment_marker)[1]
            updated = js_prefix + NEW_JS + "\n" + next_comment_marker + js_suffix
        else:
            updated = js_prefix + NEW_JS + "\n    </script>\n</body>\n</html>\n"
    
    INDEX_PATH.write_text(updated, encoding="utf-8")
    print(f"[OK] Successfully updated {INDEX_PATH}")

if __name__ == "__main__":
    main()
