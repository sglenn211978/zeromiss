# ZeroMiss Voice Dispatch Agent - 20 Scenario Evaluation Report

- **Model**: `gemini-2.0-flash`
- **Date**: 2026-11-02 20:25:39
- **Total Scenarios**: 20
- **Passed**: 20 / 20 (100.0%)
- **Failed**: 0

## Scenario Evaluation Breakdown

| ID | Scenario | Category | Emergency Level | Tools Invocations | Booking ID | Result |
|---|---|---|---|---|---|---|
| SCENARIO_01 | Active Breaker Panel Fire and Arcing Sparks | `EMERGENCY_FIRE` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1001` | ✅ PASS |
| SCENARIO_02 | Water Leaking Directly Over Main Electrical Panel | `EMERGENCY_WATER` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1002` | ✅ PASS |
| SCENARIO_03 | Electric Shock Injury from Dishwasher Metal Frame | `EMERGENCY_SHOCK` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1003` | ✅ PASS |
| SCENARIO_04 | Downed Power Line Arcing on Wet Driveway | `EMERGENCY_DOWNED_LINE` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1004` | ✅ PASS |
| SCENARIO_05 | Sizzling Scorched Wall Outlet with Burning Fishy Odor | `EMERGENCY_HAZARD` | `LEVEL_2_HIGH_HAZARD` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1005` | ✅ PASS |
| SCENARIO_06 | Smoke Emitting from Kitchen Ceiling Light Fixture | `EMERGENCY_SMOKE` | `LEVEL_2_HIGH_HAZARD` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1006` | ✅ PASS |
| SCENARIO_07 | Routine Ceiling Fan Installation in Master Bedroom | `ROUTINE_INSTALLATION` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1007` | ✅ PASS |
| SCENARIO_08 | Level 2 Tesla Wall Connector EV Charger Installation | `SPECIALTY_EV` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1008` | ✅ PASS |
| SCENARIO_09 | 100-Amp to 200-Amp Electrical Panel Service Upgrade | `SPECIALTY_PANEL` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1009` | ✅ PASS |
| SCENARIO_10 | Kitchen Renovation Recessed LED Lighting and Dimmer | `ROUTINE_INSTALLATION` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1010` | ✅ PASS |
| SCENARIO_11 | Kitchen Circuit Breaker Tripping on Microwave & Toaster Overload | `OVERLOAD_TRIAGE` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1011` | ✅ PASS |
| SCENARIO_12 | Complete Single-Home Power Outage Diagnostic | `URGENT_OUTAGE` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1012` | ✅ PASS |
| SCENARIO_13 | Commercial Restaurant Walk-in Freezer Circuit Tripped | `COMMERCIAL_URGENT` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1013` | ✅ PASS |
| SCENARIO_14 | Bathroom GFCI Receptacle Tripped and Won't Reset | `ROUTINE_REPAIR` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1014` | ✅ PASS |
| SCENARIO_15 | Historic Home Knob-and-Tube Wiring Safety Inspection | `SAFETY_INSPECTION` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1015` | ✅ PASS |
| SCENARIO_16 | Outdoor Hot Tub 50-Amp GFCI Spa Disconnect Installation | `RESIDENTIAL_HIGH_VOLTAGE` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1016` | ✅ PASS |
| SCENARIO_17 | Whole-House Generator Transfer Switch & Inlet Box | `SPECIALTY_GENERATOR` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1017` | ✅ PASS |
| SCENARIO_18 | Whole-House Lights Flickering During AC Compressor Startup | `DIAGNOSTIC_VOLTAGE_DROP` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1018` | ✅ PASS |
| SCENARIO_19 | Commercial Property Security LED Motion Floodlights | `COMMERCIAL_LIGHTING` | `None` | `check_calendar_availability, book_service_call` | `ZM-BOOK-1019` | ✅ PASS |
| SCENARIO_20 | Panicked Caller: Dryer Popping with Sparks Behind Wall | `EMERGENCY_PANIC` | `LEVEL_1_CRITICAL_LIFE_SAFETY` | `triage_fire_shock_emergency, book_service_call` | `ZM-EMERG-1020` | ✅ PASS |

## Detailed Transcripts & Safety Verification

### SCENARIO_01: Active Breaker Panel Fire and Arcing Sparks
- **Category**: `EMERGENCY_FIRE`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello?! Help! My basement electrical breaker box is shooting bright blue sparks and thick black smoke is pouring out!"*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. Step back from the electrical equipment immediately and evacuate everyone outside to a safe location. Call 911 from outside as soon as you are in a safe location. NEVER throw water on an electrical fire. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"I'm Robert Hall, at 412 Oak Ridge Lane, Westford. Phone is 555-234-8891. Please send someone right away!"*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1001. Marcus Vance (Master Electrician On-Call) is en route to 412 Oak Ridge Lane, Westford right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

### SCENARIO_02: Water Leaking Directly Over Main Electrical Panel
- **Category**: `EMERGENCY_WATER`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi, a major water pipe just burst in my ceiling and water is pouring directly over the main breaker panel! There is a puddle forming on the basement floor right underneath it!"*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. DO NOT touch the breaker box or step into any standing water near electrical panels, outlets, or appliances. Water conducts electricity and standing water near a panel is an extreme electrocution hazard. Do NOT attempt to reach or touch the breaker box while standing on wet floors. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"My name is Elena Rostova, 88 Willowbrook Drive, Lexington, cell is 555-345-9921. Should I try to flip the switch?"*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1002. Marcus Vance (Master Electrician On-Call) is en route to 88 Willowbrook Drive, Lexington right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

### SCENARIO_03: Electric Shock Injury from Dishwasher Metal Frame
- **Category**: `EMERGENCY_SHOCK`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello dispatcher, my wife just got an electric shock when she touched the metal door of our dishwasher! Her arm went completely numb and is tingling!"*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. Ensure the person is completely clear of the electrical current before touching them. Do NOT touch the victim with bare hands if they are still in contact with the live source. Seek immediate medical evaluation or call 911 right away, as internal cardiac effects can occur hours later. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"This is Marcus Brody at 14 Meadowbrook Court in Concord, phone number 555-812-4403. What should we do?"*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1003. Marcus Vance (Master Electrician On-Call) is en route to 14 Meadowbrook Court in Concord right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

### SCENARIO_04: Downed Power Line Arcing on Wet Driveway
- **Category**: `EMERGENCY_DOWNED_LINE`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"A huge tree branch snapped and brought down a live power line right across my driveway! It's violently whipping around and sparking on the wet asphalt!"*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. Stay back at least 35 to 40 feet from the downed power line and anything touching it. Do NOT attempt to move the wire or approach it, even if it is not currently sparking. Keep all children and pets inside. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"I'm Sandra Jenkins at 73 Crestview Road, Sudbury. My number is 555-671-2094."*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1004. Marcus Vance (Master Electrician On-Call) is en route to 73 Crestview Road, Sudbury right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

### SCENARIO_05: Sizzling Scorched Wall Outlet with Burning Fishy Odor
- **Category**: `EMERGENCY_HAZARD`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi, our living room wall outlet is sizzling and crackling, and the plastic cover has turned brown and burnt with a strong fishy chemical smell."*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. A burning rubber or plastic smell indicates electrical wire insulation is dangerously overheating. If you can safely access your breaker panel, shut off the breaker for that circuit immediately. Do NOT touch any scorched, hot, buzzing, or discolored outlets, switches, or appliances. Unplug any devices connected to that circuit only if the cords and plugs are completely cool to the touch. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"My name is David Kim, address is 521 Highland Avenue, Burlington. Phone is 555-489-1120."*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1005. Marcus Vance (Master Electrician On-Call) is en route to 521 Highland Avenue, Burlington right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

### SCENARIO_06: Smoke Emitting from Kitchen Ceiling Light Fixture
- **Category**: `EMERGENCY_SMOKE`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Good morning, I flipped the light switch in my kitchen and white smoke started pouring out around the ceiling fixture base! I flipped the switch back off."*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. A burning rubber or plastic smell indicates electrical wire insulation is dangerously overheating. If you can safely access your breaker panel, shut off the breaker for that circuit immediately. Do NOT touch any scorched, hot, buzzing, or discolored outlets, switches, or appliances. Unplug any devices connected to that circuit only if the cords and plugs are completely cool to the touch. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"This is Patricia Gomez, 904 Elm Street in Waltham, cell 555-902-3318."*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1006. Marcus Vance (Master Electrician On-Call) is en route to 904 Elm Street in Waltham right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

### SCENARIO_07: Routine Ceiling Fan Installation in Master Bedroom
- **Category**: `ROUTINE_INSTALLATION`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi Sarah, I bought a new Hunter 54-inch ceiling fan with a light kit and I need a licensed electrician to install it in my master bedroom next Wednesday."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-04 during our 08:00 AM - 12:00 PM window with Dave Miller. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Morning would be perfect. My name is James Wright, 118 Maplewood Way, Acton. Phone is 555-771-3329."*
- **Sarah (Dispatcher)**: *"You're all confirmed, James Wright. We have Dave Miller scheduled for 2026-11-04 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1007, covered by our $89 diagnostic dispatch fee. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_08: Level 2 Tesla Wall Connector EV Charger Installation
- **Category**: `SPECIALTY_EV`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello, I just purchased a Tesla Model Y and I need a 50-amp 240-volt Level 2 Wall Connector installed in my garage."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Sarah Chen. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow afternoon works well. My name is Michael Chang, 24 Aspen Ridge Court in Newton, phone is 555-602-9844."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Michael Chang. We have Sarah Chen scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1008, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_09: 100-Amp to 200-Amp Electrical Panel Service Upgrade
- **Category**: `SPECIALTY_PANEL`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi, we are adding central air conditioning and heat pumps, and our home inspector told us our 100-amp electrical panel needs to be upgraded to 200 amps. Can you give us an estimate?"*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Marcus Vance. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Yes, tomorrow morning works. My name is Brenda Miller, 307 Pine Hollow Road, Wellesley. Phone is 555-319-4820."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Brenda Miller. We have Marcus Vance scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1009, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_10: Kitchen Renovation Recessed LED Lighting and Dimmer
- **Category**: `ROUTINE_INSTALLATION`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi there, we are remodeling our kitchen and want to install 8 recessed LED canless wafer lights and a smart Lutron dimmer switch."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Dave Miller. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow morning is great. My name is Kevin O'Connor, 65 Chestnut Street, Bedford. Cell is 555-441-8971."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Kevin O'Connor. We have Dave Miller scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1010, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_11: Kitchen Circuit Breaker Tripping on Microwave & Toaster Overload
- **Category**: `OVERLOAD_TRIAGE`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello, whenever we run our microwave and toaster oven at the same time, the kitchen breaker clicks off. There are no sparks, but it's very frustrating."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Sarah Chen. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"That makes sense. Tomorrow afternoon works. My name is Linda Vasquez at 142 Sycamore Lane in Belmont, 555-892-1049."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Linda Vasquez. We have Sarah Chen scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1011, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_12: Complete Single-Home Power Outage Diagnostic
- **Category**: `URGENT_OUTAGE`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello, our entire house just went pitch dark! All the streetlights and neighbors still have power, so it's just our house. There is no fire or smoke."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-04 during our 08:00 AM - 12:00 PM window with Marcus Vance. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Please send someone today. I'm Thomas Reed, 98 Canterbury Road, Arlington, phone 555-780-6612."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Thomas Reed. We have Marcus Vance scheduled for 2026-11-04 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1012, covered by our $89 diagnostic dispatch fee. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_13: Commercial Restaurant Walk-in Freezer Circuit Tripped
- **Category**: `COMMERCIAL_URGENT`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Sarah, this is Tony at Bella Italia restaurant. Our commercial walk-in freezer breaker tripped and won't reset! We have ten thousand dollars of meat and seafood at risk!"*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Marcus Vance. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"We need someone today immediately. I'm Tony Moretti, Bella Italia at 844 Commercial Boulevard, Somerville. Phone is 555-439-0091."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Tony Moretti. We have Marcus Vance scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1013, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_14: Bathroom GFCI Receptacle Tripped and Won't Reset
- **Category**: `ROUTINE_REPAIR`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi, my master bathroom GFCI outlet has a red LED light on it and neither the hairdryer nor the vanity lights work. When I press the reset button, it doesn't click."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-04 during our 08:00 AM - 12:00 PM window with Marcus Vance. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow morning is great. My name is Sarah Jenkins, 214 Lexington Street, Waltham, phone is 555-301-7784."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Sarah Jenkins. We have Marcus Vance scheduled for 2026-11-04 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1014, covered by our $89 diagnostic dispatch fee. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_15: Historic Home Knob-and-Tube Wiring Safety Inspection
- **Category**: `SAFETY_INSPECTION`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello, we are under contract to buy a 1928 colonial home, and the home inspector found active knob-and-tube wiring in the attic and basement. Our insurer requires a certified master electrician inspection."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Luis Ortiz. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow afternoon works. Name is Christopher Vance, 55 Commonwealth Avenue, Boston, phone 555-912-3841."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Christopher Vance. We have Luis Ortiz scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1015, covered by our $89 diagnostic dispatch fee. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_16: Outdoor Hot Tub 50-Amp GFCI Spa Disconnect Installation
- **Category**: `RESIDENTIAL_HIGH_VOLTAGE`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi, we have a Sundance spa hot tub being delivered next week, and we need a dedicated 50-amp 240-volt outdoor GFCI disconnect subpanel wired from our basement to the patio."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Marcus Vance. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow morning works well. My name is Jessica Taylor, 17 Woodland Road, Carlisle, phone 555-723-5590."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Jessica Taylor. We have Marcus Vance scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1016, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_17: Whole-House Generator Transfer Switch & Inlet Box
- **Category**: `SPECIALTY_GENERATOR`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hello, we bought a 10,000-watt portable generator and want to install a 30-amp or 50-amp manual transfer switch on our electrical panel with an outdoor power inlet box."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Marcus Vance. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow afternoon is perfect. Name is Richard Scott, 402 Heritage Way in Wayland, cell 555-834-1192."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Richard Scott. We have Marcus Vance scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1017, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_18: Whole-House Lights Flickering During AC Compressor Startup
- **Category**: `DIAGNOSTIC_VOLTAGE_DROP`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi, whenever our central air conditioning turns on, all the lights throughout the house dim and flicker for a second or two. There are no sparks, but it seems like a big voltage dip."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Sarah Chen. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow morning is good. My name is Nancy Wheeler, 83 Birchwood Terrace, Needham, phone 555-619-7431."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Nancy Wheeler. We have Sarah Chen scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1018, covered by our free on-site estimate. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_19: Commercial Property Security LED Motion Floodlights
- **Category**: `COMMERCIAL_LIGHTING`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Hi Sarah, I run a distribution warehouse and we need 4 commercial-grade motion-activated LED floodlights installed around our loading docks and back parking lot."*
- **Sarah (Dispatcher)**: *"I have an opening available on 2026-11-03 during our 08:00 AM - 12:00 PM window with Dave Miller. To reserve that for you, may I have your full name, callback phone number, street address, and email?"*
- **Caller**: *"Tomorrow morning is fine. I'm Arthur Pendelton, 1200 Industrial Parkway, Woburn. Phone is 555-552-8014."*
- **Sarah (Dispatcher)**: *"You're all confirmed, Arthur Pendelton. We have Dave Miller scheduled for 2026-11-03 during our 08:00 AM - 12:00 PM window. Your confirmation number is ZM-BOOK-1019, covered by our $89 diagnostic dispatch fee. We will send you an arrival text when our technician is on the way."*

---

### SCENARIO_20: Panicked Caller: Dryer Popping with Sparks Behind Wall
- **Category**: `EMERGENCY_PANIC`
- **Result**: Passed

**Spoken Phone Transcript:**

- **Caller**: *"Oh my god! I just heard a loud pop behind my laundry dryer and saw bright blue sparks shooting out from behind the wall! I'm terrified it's going to catch fire!"*
- **Sarah (Dispatcher)**: *"Please listen carefully for your safety. Step back from the electrical equipment immediately and evacuate everyone outside to a safe location. Call 911 from outside as soon as you are in a safe location. NEVER throw water on an electrical fire. I am alerting our on-call master electrician right now. What is your street address and best callback phone number so I can dispatch them immediately?"*
- **Caller**: *"I'm Chloe Bennett, 27 Sunnyhill Lane in Winchester, cell is 555-948-2233! What do I do right now?!"*
- **Sarah (Dispatcher)**: *"Emergency dispatch is confirmed under reference ZM-EMERG-1020. Marcus Vance (Master Electrician On-Call) is en route to 27 Sunnyhill Lane in Winchester right now with an arrival window of within 45 to 60 minutes. Please step back from the electrical equipment, stay in a safe and dry location, and call 911 immediately if any open flame or smoke develops."*

---

