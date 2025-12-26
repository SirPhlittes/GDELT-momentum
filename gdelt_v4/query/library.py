"""
GDELT v4.0 Query Library
=========================
Predefined query components for tactical query assembly.

Provides structured dropdown options for:
- Domain: Thematic anchor (e.g., GEOPOLITICS, TECHNOLOGY)
- Focus: Operational core (e.g., SANCTIONS, REGULATION)
- Target: Target group/region (e.g., CHINA, EUROPE)

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from typing import Dict, List, Tuple


# =============================================================================
# DOMAIN OPTIONS (Thematic Anchor)
# =============================================================================

DOMAIN_OPTIONS: List[Tuple[str, str]] = [
    ("", "— Select Domain —"),
    ("GEOPOLITICS", "GEOPOLITICS"),
    ("TECHNOLOGY", "TECHNOLOGY"),
    ("ECONOMY", "ECONOMY"),
    ("ENERGY", "ENERGY"),
    ("CLIMATE", "CLIMATE"),
    ("HEALTH", "HEALTH"),
    ("SECURITY", "SECURITY"),
    ("TRADE", "TRADE"),
    ("DIPLOMACY", "DIPLOMACY"),
    ("MILITARY", "MILITARY"),
    ("CYBER", "CYBER"),
    ("SOCIAL", "SOCIAL"),
    ("ENVIRONMENT", "ENVIRONMENT"),
]

DOMAIN_QUERIES: Dict[str, str] = {
    "GEOPOLITICS": "(GEOPOLITICS OR GEOPOLITICAL OR DIPLOMACY OR FOREIGN_POLICY)",
    "TECHNOLOGY": "(TECHNOLOGY OR TECH OR ARTIFICIAL_INTELLIGENCE OR AI OR DIGITAL)",
    "ECONOMY": "(ECONOMY OR ECONOMIC OR FINANCE OR FINANCIAL OR TRADE)",
    "ENERGY": "(ENERGY OR OIL OR GAS OR PETROLEUM OR RENEWABLE)",
    "CLIMATE": "(CLIMATE OR CLIMATE_CHANGE OR EMISSION OR CARBON)",
    "HEALTH": "(HEALTH OR HEALTHCARE OR MEDICAL OR PANDEMIC OR DISEASE)",
    "SECURITY": "(SECURITY OR TERRORISM OR THREAT OR DEFENSE)",
    "TRADE": "(TRADE OR COMMERCE OR EXPORT OR IMPORT OR TARIFF)",
    "DIPLOMACY": "(DIPLOMACY OR DIPLOMATIC OR NEGOTIATION OR TREATY)",
    "MILITARY": "(MILITARY OR DEFENSE OR ARMED_FORCES OR WAR)",
    "CYBER": "(CYBER OR CYBERSECURITY OR HACKING OR DIGITAL_THREAT)",
    "SOCIAL": "(SOCIAL OR SOCIETY OR CIVIL OR PROTEST OR DEMONSTRATION)",
    "ENVIRONMENT": "(ENVIRONMENT OR ENVIRONMENTAL OR POLLUTION OR CONSERVATION)",
}


# =============================================================================
# FOCUS OPTIONS (Operational Core)
# =============================================================================

FOCUS_OPTIONS: List[Tuple[str, str]] = [
    ("", "— Select Focus —"),
    ("SANCTIONS", "SANCTIONS"),
    ("REGULATION", "REGULATION"),
    ("CONFLICT", "CONFLICT"),
    ("COOPERATION", "COOPERATION"),
    ("CRISIS", "CRISIS"),
    ("AGREEMENT", "AGREEMENT"),
    ("PROTEST", "PROTEST"),
    ("BREAKTHROUGH", "BREAKTHROUGH"),
    ("BAN", "BAN"),
    ("RESTRICTION", "RESTRICTION"),
    ("PARTNERSHIP", "PARTNERSHIP"),
    ("SUMMIT", "SUMMIT"),
    ("TREATY", "TREATY"),
    ("WAR", "WAR"),
    ("PEACE", "PEACE"),
]

FOCUS_QUERIES: Dict[str, str] = {
    "SANCTIONS": "(SANCTION OR SANCTIONS OR EMBARGO)",
    "REGULATION": "(REGULATION OR REGULATORY OR LEGISLATION)",
    "CONFLICT": "(CONFLICT OR CONFLICTS OR DISPUTE OR TENSION)",
    "COOPERATION": "(COOPERATION OR COOPERATE OR COLLABORATION)",
    "CRISIS": "(CRISIS OR CRISES OR EMERGENCY)",
    "AGREEMENT": "(AGREEMENT OR AGREEMENTS OR DEAL OR ACCORD)",
    "PROTEST": "(PROTEST OR PROTESTS OR DEMONSTRATION OR RIOT)",
    "BREAKTHROUGH": "(BREAKTHROUGH OR BREAKTHROUGHS OR INNOVATION)",
    "BAN": "(BAN OR BANNED OR PROHIBITION)",
    "RESTRICTION": "(RESTRICTION OR RESTRICTIONS OR LIMIT)",
    "PARTNERSHIP": "(PARTNERSHIP OR PARTNER OR ALLIANCE)",
    "SUMMIT": "(SUMMIT OR SUMMITS OR CONFERENCE OR MEETING)",
    "TREATY": "(TREATY OR TREATIES OR ACCORD)",
    "WAR": "(WAR OR WARFARE OR CONFLICT)",
    "PEACE": "(PEACE OR PEACEFUL OR RESOLUTION)",
}


# =============================================================================
# TARGET OPTIONS (Target Group/Region)
# =============================================================================

TARGET_OPTIONS: List[Tuple[str, str]] = [
    ("", "— Select Target —"),
    ("CHINA", "CHINA"),
    ("RUSSIA", "RUSSIA"),
    ("USA", "USA / UNITED_STATES"),
    ("EUROPE", "EUROPE"),
    ("MIDDLE_EAST", "MIDDLE_EAST"),
    ("ASIA", "ASIA"),
    ("AFRICA", "AFRICA"),
    ("LATIN_AMERICA", "LATIN_AMERICA"),
    ("UK", "UNITED_KINGDOM"),
    ("GERMANY", "GERMANY"),
    ("FRANCE", "FRANCE"),
    ("JAPAN", "JAPAN"),
    ("INDIA", "INDIA"),
    ("IRAN", "IRAN"),
    ("NORTH_KOREA", "NORTH_KOREA"),
    ("ISRAEL", "ISRAEL"),
    ("TURKEY", "TURKEY"),
    ("SAUDI_ARABIA", "SAUDI_ARABIA"),
    ("UKRAINE", "UKRAINE"),
]

TARGET_QUERIES: Dict[str, str] = {
    "CHINA": "(CHINA OR CHINESE OR BEIJING)",
    "RUSSIA": "(RUSSIA OR RUSSIAN OR MOSCOW)",
    "USA": "(USA OR UNITED_STATES OR AMERICA OR WASHINGTON)",
    "EUROPE": "(EUROPE OR EUROPEAN OR EU OR BRUSSELS)",
    "MIDDLE_EAST": "(MIDDLE_EAST OR MIDEAST OR GULF)",
    "ASIA": "(ASIA OR ASIAN)",
    "AFRICA": "(AFRICA OR AFRICAN)",
    "LATIN_AMERICA": "(LATIN_AMERICA OR SOUTH_AMERICA OR LATAM)",
    "UK": "(UNITED_KINGDOM OR UK OR BRITAIN OR BRITISH OR LONDON)",
    "GERMANY": "(GERMANY OR GERMAN OR BERLIN)",
    "FRANCE": "(FRANCE OR FRENCH OR PARIS)",
    "JAPAN": "(JAPAN OR JAPANESE OR TOKYO)",
    "INDIA": "(INDIA OR INDIAN OR NEW_DELHI)",
    "IRAN": "(IRAN OR IRANIAN OR TEHRAN)",
    "NORTH_KOREA": "(NORTH_KOREA OR DPRK OR PYONGYANG)",
    "ISRAEL": "(ISRAEL OR ISRAELI OR JERUSALEM)",
    "TURKEY": "(TURKEY OR TURKISH OR ANKARA)",
    "SAUDI_ARABIA": "(SAUDI_ARABIA OR SAUDI OR RIYADH)",
    "UKRAINE": "(UKRAINE OR UKRAINIAN OR KYIV)",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_domain_options() -> List[str]:
    """Get list of domain option values (excluding empty option)."""
    return [opt[0] for opt in DOMAIN_OPTIONS if opt[0]]


def get_focus_options() -> List[str]:
    """Get list of focus option values (excluding empty option)."""
    return [opt[0] for opt in FOCUS_OPTIONS if opt[0]]


def get_target_options() -> List[str]:
    """Get list of target option values (excluding empty option)."""
    return [opt[0] for opt in TARGET_OPTIONS if opt[0]]


def get_domain_query(domain: str) -> str:
    """Get query string for a domain."""
    return DOMAIN_QUERIES.get(domain, "")


def get_focus_query(focus: str) -> str:
    """Get query string for a focus."""
    return FOCUS_QUERIES.get(focus, "")


def get_target_query(target: str) -> str:
    """Get query string for a target."""
    return TARGET_QUERIES.get(target, "")


def assemble_query(
    domain: str = "",
    focus: str = "",
    target: str = "",
    custom_keywords: str = "",
) -> str:
    """
    Assemble a GDELT Boolean query from components.
    
    Structure: (DOMAIN) AND (FOCUS) AND (TARGET) AND (CUSTOM_KEYWORDS)
    
    Empty components are ignored to avoid null matches.
    
    Args:
        domain: Selected domain option.
        focus: Selected focus option.
        target: Selected target option.
        custom_keywords: Optional custom keywords (comma or space separated).
        
    Returns:
        Assembled Boolean query string.
        
    Example:
        >>> assemble_query("GEOPOLITICS", "SANCTIONS", "CHINA", "EPSTEIN")
        '(GEOPOLITICS OR GEOPOLITICAL OR DIPLOMACY OR FOREIGN_POLICY) AND (SANCTION OR SANCTIONS OR EMBARGO) AND (CHINA OR CHINESE OR BEIJING) AND (EPSTEIN)'
    """
    components = []
    
    # Add domain
    if domain and domain in DOMAIN_QUERIES:
        components.append(get_domain_query(domain))
    
    # Add focus
    if focus and focus in FOCUS_QUERIES:
        components.append(get_focus_query(focus))
    
    # Add target
    if target and target in TARGET_QUERIES:
        components.append(get_target_query(target))
    
    # Add custom keywords
    if custom_keywords:
        # Parse custom keywords (comma or space separated)
        keywords = [
            kw.strip().upper()
            for kw in custom_keywords.replace(",", " ").split()
            if kw.strip()
        ]
        if keywords:
            if len(keywords) == 1:
                components.append(f"({keywords[0]})")
            else:
                components.append(f"({' OR '.join(keywords)})")
    
    # Join with AND
    if not components:
        return ""
    
    return " AND ".join(components)


def validate_assembled_query(query: str, max_length: int = 500) -> Tuple[bool, str]:
    """
    Validate an assembled query.
    
    Args:
        query: The query string to validate.
        max_length: Maximum allowed query length.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    if not query:
        return False, "Query cannot be empty"
    
    if len(query) > max_length:
        return False, f"Query too long (max {max_length} characters, got {len(query)})"
    
    # Check for balanced parentheses
    open_count = query.count("(")
    close_count = query.count(")")
    if open_count != close_count:
        return False, f"Unbalanced parentheses (opening: {open_count}, closing: {close_count})"
    
    # Basic syntax check - no consecutive AND/OR
    if " AND AND " in query or " OR OR " in query:
        return False, "Invalid syntax: consecutive operators"
    
    if query.startswith(" AND ") or query.startswith(" OR "):
        return False, "Query cannot start with operator"
    
    if query.endswith(" AND ") or query.endswith(" OR "):
        return False, "Query cannot end with operator"
    
    return True, ""

