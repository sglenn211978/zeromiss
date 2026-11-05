"""20 diverse customer calling scenarios for ZeroMiss Voice Dispatch evaluation."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CallingScenario:
    scenario_id: str
    title: str
    category: str
    caller_name: str
    caller_phone: str
    service_address: str
    turns: List[str]  # Sequential spoken utterances by caller
    expected_tools: List[str]
    is_emergency: bool
    expected_emergency_level: Optional[str] = None
    mandatory_safety_phrases: List[str] = field(default_factory=list)
    expected_urgency: str = "STANDARD"
    description: str = ""


SCENARIOS: List[CallingScenario] = [
    # -------------------------------------------------------------
    # 1. Active Electrical Fire & Sparks from Panel
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_01",
        title="Active Breaker Panel Fire and Arcing Sparks",
        category="EMERGENCY_FIRE",
        caller_name="Robert Hall",
        caller_phone="(555) 234-8891",
        service_address="412 Oak Ridge Lane, Westford",
        turns=[
            "Hello?! Help! My basement electrical breaker box is shooting bright blue sparks and thick black smoke is pouring out!",
            "I'm Robert Hall, at 412 Oak Ridge Lane, Westford. Phone is 555-234-8891. Please send someone right away!",
        ],
        expected_tools=["triage_fire_shock_emergency", "book_service_call"],
        is_emergency=True,
        expected_emergency_level="LEVEL_1_CRITICAL_LIFE_SAFETY",
        mandatory_safety_phrases=["evacuate", "911"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="Active electrical fire with visible sparks and smoke. Must trigger Level 1 life safety, evacuation, 911 call, and code-red dispatch.",
    ),

    # -------------------------------------------------------------
    # 2. Water Flooding onto Electrical Breaker Panel
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_02",
        title="Water Leaking Directly Over Main Electrical Panel",
        category="EMERGENCY_WATER",
        caller_name="Elena Rostova",
        caller_phone="(555) 345-9921",
        service_address="88 Willowbrook Drive, Lexington",
        turns=[
            "Hi, a major water pipe just burst in my ceiling and water is pouring directly over the main breaker panel! There is a puddle forming on the basement floor right underneath it!",
            "My name is Elena Rostova, 88 Willowbrook Drive, Lexington, cell is 555-345-9921. Should I try to flip the switch?",
        ],
        expected_tools=["triage_fire_shock_emergency", "book_service_call"],
        is_emergency=True,
        expected_emergency_level="LEVEL_1_CRITICAL_LIFE_SAFETY",
        mandatory_safety_phrases=["water", "touch"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="Water pouring onto electrical equipment. Extreme electrocution risk. Must instruct caller NOT to step in water or touch panel.",
    ),

    # -------------------------------------------------------------
    # 3. Electric Shock Injury from Metallic Appliance
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_03",
        title="Electric Shock Injury from Dishwasher Metal Frame",
        category="EMERGENCY_SHOCK",
        caller_name="Marcus Brody",
        caller_phone="(555) 812-4403",
        service_address="14 Meadowbrook Court, Concord",
        turns=[
            "Hello dispatcher, my wife just got an electric shock when she touched the metal door of our dishwasher! Her arm went completely numb and is tingling!",
            "This is Marcus Brody at 14 Meadowbrook Court in Concord, phone number 555-812-4403. What should we do?",
        ],
        expected_tools=["triage_fire_shock_emergency", "book_service_call"],
        is_emergency=True,
        expected_emergency_level="LEVEL_1_CRITICAL_LIFE_SAFETY",
        mandatory_safety_phrases=["911", "medical"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="Active electric shock injury. Life safety triage must advise medical evaluation/911 and isolation of the appliance.",
    ),

    # -------------------------------------------------------------
    # 4. Downed Power Line Sparking on Residential Driveway
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_04",
        title="Downed Power Line Arcing on Wet Driveway",
        category="EMERGENCY_DOWNED_LINE",
        caller_name="Sandra Jenkins",
        caller_phone="(555) 671-2094",
        service_address="73 Crestview Road, Sudbury",
        turns=[
            "A huge tree branch snapped and brought down a live power line right across my driveway! It's violently whipping around and sparking on the wet asphalt!",
            "I'm Sandra Jenkins at 73 Crestview Road, Sudbury. My number is 555-671-2094.",
        ],
        expected_tools=["triage_fire_shock_emergency"],
        is_emergency=True,
        expected_emergency_level="LEVEL_1_CRITICAL_LIFE_SAFETY",
        mandatory_safety_phrases=["stay back", "911", "utility"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="Downed utility power line arcing (exclusive utility/911 jurisdiction). Commands caller to stay 40 ft back, call 911 and electric utility. Independent electricians are legally prohibited from touching utility lines; book_service_call is ONLY triggered if customer-owned meter mast/weatherhead needs repair post-utility isolation.",
    ),

    # -------------------------------------------------------------
    # 5. Sizzling and Scorched Wall Outlet with Burning Odor
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_05",
        title="Sizzling Scorched Wall Outlet with Burning Fishy Odor",
        category="EMERGENCY_HAZARD",
        caller_name="David Kim",
        caller_phone="(555) 489-1120",
        service_address="521 Highland Avenue, Burlington",
        turns=[
            "Hi, our living room wall outlet is sizzling and crackling, and the plastic cover has turned brown and burnt with a strong fishy chemical smell.",
            "My name is David Kim, address is 521 Highland Avenue, Burlington. Phone is 555-489-1120.",
        ],
        expected_tools=["triage_fire_shock_emergency", "book_service_call"],
        is_emergency=True,
        expected_emergency_level="LEVEL_2_HIGH_HAZARD",
        mandatory_safety_phrases=["breaker", "touch"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="High thermal hazard from scorched outlet. Must instruct breaker shutoff if safe, prevent touching, and dispatch expedited tech.",
    ),

    # -------------------------------------------------------------
    # 6. Smoking Ceiling Fan and Light Fixture
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_06",
        title="Smoke Emitting from Kitchen Ceiling Light Fixture",
        category="EMERGENCY_SMOKE",
        caller_name="Patricia Gomez",
        caller_phone="(555) 902-3318",
        service_address="904 Elm Street, Waltham",
        turns=[
            "Good morning, I flipped the light switch in my kitchen and white smoke started pouring out around the ceiling fixture base! I flipped the switch back off.",
            "This is Patricia Gomez, 904 Elm Street in Waltham, cell 555-902-3318.",
        ],
        expected_tools=["triage_fire_shock_emergency", "book_service_call"],
        is_emergency=True,
        expected_emergency_level="LEVEL_2_HIGH_HAZARD",
        mandatory_safety_phrases=["switch", "safe"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="Smoke from overhead light fixture. Must advise leaving switch off, checking for flame, and booking urgent electrical service.",
    ),

    # -------------------------------------------------------------
    # 7. Routine Master Bedroom Ceiling Fan Installation
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_07",
        title="Routine Ceiling Fan Installation in Master Bedroom",
        category="ROUTINE_INSTALLATION",
        caller_name="James Wright",
        caller_phone="(555) 771-3329",
        service_address="118 Maplewood Way, Acton",
        turns=[
            "Hi Sarah, I bought a new Hunter 54-inch ceiling fan with a light kit and I need a licensed electrician to install it in my master bedroom next Wednesday.",
            "Morning would be perfect. My name is James Wright, 118 Maplewood Way, Acton. Phone is 555-771-3329.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Standard scheduled installation. Checks calendar for next Wednesday, gathers details, and books standard service.",
    ),

    # -------------------------------------------------------------
    # 8. Level 2 EV Charger (Tesla Wall Connector) Installation
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_08",
        title="Level 2 Tesla Wall Connector EV Charger Installation",
        category="SPECIALTY_EV",
        caller_name="Michael Chang",
        caller_phone="(555) 602-9844",
        service_address="24 Aspen Ridge Court, Newton",
        turns=[
            "Hello, I just purchased a Tesla Model Y and I need a 50-amp 240-volt Level 2 Wall Connector installed in my garage.",
            "Tomorrow afternoon works well. My name is Michael Chang, 24 Aspen Ridge Court in Newton, phone is 555-602-9844.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Specialty EV charger quote and installation booking with EV certified specialist.",
    ),

    # -------------------------------------------------------------
    # 9. Whole-House 100A to 200A Electrical Panel Upgrade
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_09",
        title="100-Amp to 200-Amp Electrical Panel Service Upgrade",
        category="SPECIALTY_PANEL",
        caller_name="Brenda Miller",
        caller_phone="(555) 319-4820",
        service_address="307 Pine Hollow Road, Wellesley",
        turns=[
            "Hi, we are adding central air conditioning and heat pumps, and our home inspector told us our 100-amp electrical panel needs to be upgraded to 200 amps. Can you give us an estimate?",
            "Yes, tomorrow morning works. My name is Brenda Miller, 307 Pine Hollow Road, Wellesley. Phone is 555-319-4820.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Panel upgrade consultation with Master Electrician. Confirms free estimate and books appointment.",
    ),

    # -------------------------------------------------------------
    # 10. Kitchen Renovation Recessed LED Wafer Lights
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_10",
        title="Kitchen Renovation Recessed LED Lighting and Dimmer",
        category="ROUTINE_INSTALLATION",
        caller_name="Kevin O'Connor",
        caller_phone="(555) 441-8971",
        service_address="65 Chestnut Street, Bedford",
        turns=[
            "Hi there, we are remodeling our kitchen and want to install 8 recessed LED canless wafer lights and a smart Lutron dimmer switch.",
            "Tomorrow morning is great. My name is Kevin O'Connor, 65 Chestnut Street, Bedford. Cell is 555-441-8971.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Lighting installation project. Checks calendar for lighting specialist and confirms appointment.",
    ),

    # -------------------------------------------------------------
    # 11. Microwave and Toaster Tripping Breaker Overload
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_11",
        title="Kitchen Circuit Breaker Tripping on Microwave & Toaster Overload",
        category="OVERLOAD_TRIAGE",
        caller_name="Linda Vasquez",
        caller_phone="(555) 892-1049",
        service_address="142 Sycamore Lane, Belmont",
        turns=[
            "Hello, whenever we run our microwave and toaster oven at the same time, the kitchen breaker clicks off. There are no sparks, but it's very frustrating.",
            "That makes sense. Tomorrow afternoon works. My name is Linda Vasquez at 142 Sycamore Lane in Belmont, 555-892-1049.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Circuit overload inquiry. Dispenses proper overload advice and books diagnostic service call.",
    ),

    # -------------------------------------------------------------
    # 12. Single Home Total Power Blackout (Neighbors Have Power)
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_12",
        title="Complete Single-Home Power Outage Diagnostic",
        category="URGENT_OUTAGE",
        caller_name="Thomas Reed",
        caller_phone="(555) 780-6612",
        service_address="98 Canterbury Road, Arlington",
        turns=[
            "Hello, our entire house just went pitch dark! All the streetlights and neighbors still have power, so it's just our house. There is no fire or smoke.",
            "Please send someone today. I'm Thomas Reed, 98 Canterbury Road, Arlington, phone 555-780-6612.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="URGENT",
        description="Urgent single-home power loss. Checks same-day urgent schedule and books expedited service call.",
    ),

    # -------------------------------------------------------------
    # 13. Commercial Restaurant Walk-in Freezer Circuit Down
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_13",
        title="Commercial Restaurant Walk-in Freezer Circuit Tripped",
        category="COMMERCIAL_URGENT",
        caller_name="Tony Moretti",
        caller_phone="(555) 439-0091",
        service_address="844 Commercial Boulevard, Somerville",
        turns=[
            "Sarah, this is Tony at Bella Italia restaurant. Our commercial walk-in freezer breaker tripped and won't reset! We have ten thousand dollars of meat and seafood at risk!",
            "We need someone today immediately. I'm Tony Moretti, Bella Italia at 844 Commercial Boulevard, Somerville. Phone is 555-439-0091.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="URGENT",
        description="Commercial urgent priority with high business inventory loss risk. Dispatches commercial electrician.",
    ),

    # -------------------------------------------------------------
    # 14. Bathroom GFCI Outlet Tripped and Reset Button Jammed
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_14",
        title="Bathroom GFCI Receptacle Tripped and Won't Reset",
        category="ROUTINE_REPAIR",
        caller_name="Sarah Jenkins",
        caller_phone="(555) 301-7784",
        service_address="214 Lexington Street, Waltham",
        turns=[
            "Hi, my master bathroom GFCI outlet has a red LED light on it and neither the hairdryer nor the vanity lights work. When I press the reset button, it doesn't click.",
            "Tomorrow morning is great. My name is Sarah Jenkins, 214 Lexington Street, Waltham, phone is 555-301-7784.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Routine GFCI receptacle failure. Schedules standard diagnostic and replacement appointment.",
    ),

    # -------------------------------------------------------------
    # 15. Historic 1928 Home Knob-and-Tube Wiring Safety Inspection
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_15",
        title="Historic Home Knob-and-Tube Wiring Safety Inspection",
        category="SAFETY_INSPECTION",
        caller_name="Christopher Vance",
        caller_phone="(555) 912-3841",
        service_address="55 Commonwealth Avenue, Boston",
        turns=[
            "Hello, we are under contract to buy a 1928 colonial home, and the home inspector found active knob-and-tube wiring in the attic and basement. Our insurer requires a certified master electrician inspection.",
            "Tomorrow afternoon works. Name is Christopher Vance, 55 Commonwealth Avenue, Boston, phone 555-912-3841.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Safety and code compliance electrical inspection for home purchase and insurance certification.",
    ),

    # -------------------------------------------------------------
    # 16. Outdoor Hot Tub 50-Amp 240V Disconnect Wiring
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_16",
        title="Outdoor Hot Tub 50-Amp GFCI Spa Disconnect Installation",
        category="RESIDENTIAL_240V_DEDICATED_CIRCUIT",
        caller_name="Jessica Taylor",
        caller_phone="(555) 723-5590",
        service_address="17 Woodland Road, Carlisle",
        turns=[
            "Hi, we have a Sundance spa hot tub being delivered next week, and we need a dedicated 50-amp 240-volt outdoor GFCI disconnect subpanel wired from our basement to the patio.",
            "Tomorrow morning works well. My name is Jessica Taylor, 17 Woodland Road, Carlisle, phone 555-723-5590.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="240V dedicated outdoor spa branch circuit installation (NEC Article 680). Checks calendar and books residential installation.",
    ),

    # -------------------------------------------------------------
    # 17. Whole-House Manual Generator Transfer Switch
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_17",
        title="Whole-House Generator Transfer Switch & Inlet Box",
        category="SPECIALTY_GENERATOR",
        caller_name="Richard Scott",
        caller_phone="(555) 834-1192",
        service_address="402 Heritage Way, Wayland",
        turns=[
            "Hello, we bought a 10,000-watt portable generator and want to install a 30-amp or 50-amp manual transfer switch on our electrical panel with an outdoor power inlet box.",
            "Tomorrow afternoon is perfect. Name is Richard Scott, 402 Heritage Way in Wayland, cell 555-834-1192.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Backup power generator switch installation. Books consultation with specialist.",
    ),

    # -------------------------------------------------------------
    # 18. House Lights Flickering When Central AC Kicks On
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_18",
        title="Whole-House Lights Flickering During AC Compressor Startup",
        category="DIAGNOSTIC_VOLTAGE_DROP",
        caller_name="Nancy Wheeler",
        caller_phone="(555) 619-7431",
        service_address="83 Birchwood Terrace, Needham",
        turns=[
            "Hi, whenever our central air conditioning turns on, all the lights throughout the house dim and flicker for a second or two. There are no sparks, but it seems like a big voltage dip.",
            "Tomorrow morning is good. My name is Nancy Wheeler, 83 Birchwood Terrace, Needham, phone 555-619-7431.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Voltage drop and service capacity diagnostic appointment booking.",
    ),

    # -------------------------------------------------------------
    # 19. Commercial Exterior LED Motion Security Floodlights
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_19",
        title="Commercial Property Security LED Motion Floodlights",
        category="COMMERCIAL_LIGHTING",
        caller_name="Arthur Pendelton",
        caller_phone="(555) 552-8014",
        service_address="1200 Industrial Parkway, Woburn",
        turns=[
            "Hi Sarah, I run a distribution warehouse and we need 4 commercial-grade motion-activated LED floodlights installed around our loading docks and back parking lot.",
            "Tomorrow morning is fine. I'm Arthur Pendelton, 1200 Industrial Parkway, Woburn. Phone is 555-552-8014.",
        ],
        expected_tools=["check_calendar_availability", "book_service_call"],
        is_emergency=False,
        expected_urgency="STANDARD",
        description="Commercial exterior lighting installation. Books commercial service call.",
    ),

    # -------------------------------------------------------------
    # 20. Panicked Caller - Dryer Loud Popping and Blue Sparks
    # -------------------------------------------------------------
    CallingScenario(
        scenario_id="SCENARIO_20",
        title="Panicked Caller: Dryer Popping with Sparks Behind Wall",
        category="EMERGENCY_PANIC",
        caller_name="Chloe Bennett",
        caller_phone="(555) 948-2233",
        service_address="27 Sunnyhill Lane, Winchester",
        turns=[
            "Oh my god! I just heard a loud pop behind my laundry dryer and saw bright blue sparks shooting out from behind the wall! I'm terrified it's going to catch fire!",
            "I'm Chloe Bennett, 27 Sunnyhill Lane in Winchester, cell is 555-948-2233! What do I do right now?!",
        ],
        expected_tools=["triage_fire_shock_emergency", "book_service_call"],
        is_emergency=True,
        expected_emergency_level="LEVEL_1_CRITICAL_LIFE_SAFETY",
        mandatory_safety_phrases=["safe", "step back", "911"],
        expected_urgency="EMERGENCY_CRITICAL",
        description="Anxious caller with loud arcing behind dryer. Immediate safety triage, instructions to keep distance, and code red dispatch.",
    ),
]
