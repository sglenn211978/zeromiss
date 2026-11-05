"""Emergency triage tool for electrical fire, shock, and severe hazard situations."""

from typing import Any, Dict, List, Optional
from phone_agent.database import DB
from phone_agent.models import EmergencySeverity


def triage_fire_shock_emergency(
    hazard_type: str,
    location_in_property: str,
    is_fire_visible: bool = False,
    is_person_injured: bool = False,
    is_water_present: bool = False,
    can_safely_access_panel: bool = True,
    caller_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Triages electrical emergencies involving fire, smoke, electric shock, water contact, or severe arcing.

    Parameters:
        hazard_type: Nature of hazard ('active_sparking', 'burning_smell_smoke', 'water_electrical_contact',
                     'electric_shock_injury', 'exposed_live_wire', 'downed_power_line', 'hot_outlet_switch', 'breaker_buzzing').
        location_in_property: Where hazard is ('breaker_panel', 'basement', 'kitchen', 'bathroom', 'appliance', 'yard_exterior', 'commercial_area').
        is_fire_visible: Whether open flame, embers, or thick active smoke is present.
        is_person_injured: Whether someone received a shock, burns, or requires medical attention.
        is_water_present: Whether standing water, flooding, or leaking water is near the electrical components.
        can_safely_access_panel: Whether the caller can safely reach the main breaker without touching water or approaching flames.
        caller_description: Additional caller context or specific hazard notes.

    Returns:
        Structured emergency assessment including severity level, immediate life-safety spoken instructions,
        utility shutoff recommendations, and emergency dispatch directive.
    """
    hazard_clean = hazard_type.lower().strip()
    loc_clean = location_in_property.lower().strip()
    notes_clean = (caller_description or "").lower()

    life_safety_actions: List[str] = []
    severity: EmergencySeverity = EmergencySeverity.LEVEL_3_MODERATE_RISK
    utility_shutoff = False
    emergency_dispatch = True

    # 1. Check for Level 1 Critical Life-Safety Triggers
    is_downed_line = "downed" in hazard_clean or "power_line" in hazard_clean or "pole" in notes_clean
    is_shock_injury = is_person_injured or "shock" in hazard_clean or "electrocution" in notes_clean
    is_active_fire = is_fire_visible or "sparking" in hazard_clean or "arcing" in notes_clean or "flame" in notes_clean
    is_water_hazard = is_water_present or "water" in hazard_clean or "flooding" in notes_clean or ("basement" in loc_clean and is_water_present)

    if is_downed_line:
        severity = EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY
        utility_shutoff = True
        emergency_dispatch = False  # Exclusive electric utility and 911 jurisdiction; independent electricians cannot touch utility lines
        life_safety_actions.extend([
            "Stay back at least 35 to 40 feet from the downed power line and anything touching it.",
            "Do NOT attempt to move the wire or approach it, even if it is not currently sparking.",
            "Keep all children and pets inside.",
            "Call 911 and your power utility emergency line immediately — utility distribution lines are strictly utility jurisdiction.",
            "If inside a vehicle touching a wire, remain inside until utility personnel clear it.",
            "An independent electrician can only be dispatched for customer-owned meter mast, weatherhead, or point-of-attachment repairs after the utility de-energizes and secures the line.",
        ])
        action_plan = "CRITICAL CODE RED: Downed power line arcing. Exclusive electric utility and 911 jurisdiction. Caller instructed to stay 40 ft back and call 911/Utility immediately. Independent line dispatch prohibited; service call only applicable if customer meter mast or weatherhead is damaged post-utility isolation."

    elif is_shock_injury:
        severity = EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY
        life_safety_actions.extend([
            "Ensure the person is completely clear of the electrical current before touching them.",
            "Do NOT touch the victim with bare hands if they are still in contact with the live source.",
            "Seek immediate medical evaluation or call 911 right away, as internal cardiac effects can occur hours later.",
            "Do NOT plug anything back into that outlet or use that appliance.",
        ])
        action_plan = "CRITICAL LIFE SAFETY: Electric shock incident reported. Medical evaluation advised. Circuit isolation required."

    elif is_active_fire or (is_fire_visible and "panel" in loc_clean):
        severity = EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY
        life_safety_actions.extend([
            "Step back from the electrical equipment immediately and evacuate everyone outside to a safe location.",
            "Call 911 from outside as soon as you are in a safe location.",
            "NEVER throw water on an electrical fire.",
            "Only attempt to turn off the main electrical breaker if it is safely located away from the smoke and flames.",
            "Wait outside for first responders and our emergency master electrician.",
        ])
        action_plan = "CRITICAL CODE RED: Active electrical sparking/fire. Immediate building evacuation and 911 call ordered."

    elif is_water_hazard and ("panel" in loc_clean or "breaker" in loc_clean or "basement" in loc_clean):
        severity = EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY
        utility_shutoff = True
        life_safety_actions.extend([
            "DO NOT touch the breaker box or step into any standing water near electrical panels, outlets, or appliances.",
            "Water conducts electricity and standing water near a panel is an extreme electrocution hazard.",
            "Do NOT attempt to reach or touch the breaker box while standing on wet floors.",
            "Move upstairs or to a dry area immediately.",
            "We are dispatching our emergency master electrician and notifying the utility for an exterior meter disconnect if necessary.",
        ])
        action_plan = "CRITICAL LIFE SAFETY: Water contacting electrical distribution equipment. Electrocution risk. Stay clear of wet floors."

    # 2. Check for Level 2 High Hazard Triggers
    elif (
        "burning" in hazard_clean
        or "smoke" in hazard_clean
        or "hot_outlet" in hazard_clean
        or "buzzing" in hazard_clean
        or "exposed" in hazard_clean
        or "rubber" in hazard_clean or "rubber" in notes_clean
        or "plastic" in hazard_clean or "plastic" in notes_clean
        or "odor" in hazard_clean or "odor" in notes_clean
        or "fishy" in hazard_clean or "fishy" in notes_clean
        or "emergency" in hazard_clean or "emergency" in notes_clean
        or "hazard" in hazard_clean
    ):
        severity = EmergencySeverity.LEVEL_2_HIGH_HAZARD
        if can_safely_access_panel and not is_water_present:
            life_safety_actions.extend([
                "A burning rubber or plastic smell indicates electrical wire insulation is dangerously overheating. If you can safely access your breaker panel, shut off the breaker for that circuit immediately.",
                "Do NOT touch any scorched, hot, buzzing, or discolored outlets, switches, or appliances.",
                "Unplug any devices connected to that circuit only if the cords and plugs are completely cool to the touch.",
                "Keep a Class C electrical fire extinguisher nearby, and if you see active flame or smoke develops, evacuate immediately and call 911.",
                "Keep people and pets away from the affected room until our electrician inspects it.",
            ])
        else:
            life_safety_actions.extend([
                "A burning rubber or plastic smell indicates overheating wire insulation. Do not approach the breaker panel or affected device.",
                "Evacuate that room immediately and keep children and pets away.",
                "If the burning odor intensifies or you see smoke or sparks, evacuate the building and call 911 immediately.",
            ])
        action_plan = "HIGH HAZARD: Thermal/wire insulation degradation risk detected. Immediate circuit isolation advised. Expedited emergency dispatch initiated."

    # 3. Level 3 Moderate Risk Triggers
    else:
        severity = EmergencySeverity.LEVEL_3_MODERATE_RISK
        emergency_dispatch = False
        life_safety_actions.extend([
            "Do NOT repeatedly force or hold a tripped circuit breaker in the ON position.",
            "Unplug high-draw appliances (space heaters, microwaves, hair dryers) on that circuit.",
            "Leave the breaker switched OFF until a licensed electrician inspects the circuit.",
        ])
        action_plan = "MODERATE RISK: Overload or intermittent fault. Breaker left off. Priority standard dispatch scheduled."

    # Record in DB
    report = DB.record_emergency_triage(
        hazard_type=hazard_type,
        location_in_property=location_in_property,
        severity_level=severity,
        is_fire_visible=is_fire_visible,
        is_person_injured=is_person_injured,
        is_water_present=is_water_present,
        can_safely_access_panel=can_safely_access_panel,
        immediate_life_safety_actions=life_safety_actions,
        emergency_dispatch_recommended=emergency_dispatch,
        utility_shutoff_required=utility_shutoff,
        recommended_action_plan=action_plan,
        notes=caller_description,
    )

    # Format voice-spoken emergency directives
    voice_spoken_bullet = " ".join([f"First: {act}" if i == 0 else f"Next: {act}" for i, act in enumerate(life_safety_actions[:3])])
    voice_announcement = (
        f"This is an electrical safety alert. {voice_spoken_bullet} "
        f"I have opened Emergency Case {report.triage_case_id} and our emergency team is alerted."
    )

    return {
        "status": "TRIAGE_COMPLETE",
        "triage_case_id": report.triage_case_id,
        "severity_level": severity.value,
        "hazard_type": hazard_type,
        "location": location_in_property,
        "immediate_life_safety_actions": life_safety_actions,
        "emergency_dispatch_recommended": emergency_dispatch,
        "utility_shutoff_required": utility_shutoff,
        "action_plan": action_plan,
        "voice_directives": voice_announcement,
    }
