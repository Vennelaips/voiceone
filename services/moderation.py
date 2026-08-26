import re
from typing import Dict, Any, List

class CivicModerationService:
    """
    Automated Civic Moderation Engine for VoiceOne.
    Enforces respectful, polite civic discourse.
    Detects and auto-removes content violating guidelines regarding:
    - Caste, Class, and Social Stratification discrimination
    - Religious hatred, communal vitriol, and sectarian slurs
    - Gender, Misogyny, and Sexual Orientation discrimination
    - Profanity, Harassment, Threats, and Abusive language
    """
    
    # Categorized patterns for prohibited content
    VIOLATION_RULES = {
        "CASTE_OR_CLASS_DISCRIMINATION": [
            r"\b(dalit|chamar|bhangi|shudra|untouchable|low\s*caste|subhuman\s*caste|casteist|sc\/st\s*quota\s*leech)\b",
            r"\b(poor\s*scum|peasant\s*trash|lower\s*class\s*filth)\b"
        ],
        "RELIGIOUS_HATRED": [
            r"\b(terrorist\s*religion|jihadi\s*infidel|kafir\s*pig|sanghi\s*terrorist|mullas?|rice\s*bag|convert\s*or\s*die)\b",
            r"\b(ban\s+(all\s+)?(islam|hinduism|christianity|sikhism)|destroy\s+all\s+(mosques|temples|churches|gurudwaras))\b",
            r"\b(hate\s+(all\s+)?(muslims|hindus|christians|sikhs|jews))\b"
        ],
        "GENDER_AND_SEXUAL_ORIENTATION": [
            r"\b(homo\s*freak|faggot|dyke|trans\s*freak|chhakka|hijra\s*slur|kill\s*all\s*gays|lgbtq\s*disease)\b",
            r"\b(whore|slut|bitch|submissive\s*women|women\s*belong\s*in\s*kitchen|anti\s*queer)\b"
        ],
        "ABUSIVE_AND_HARASSMENT": [
            r"\b(fuck|shit|asshole|bastard|madarchod|bhenchod|gandu|harami|bhosdike|idiot\s*scum|die\s*in\s*hell)\b",
            r"\b(kill\s*yourself|go\s*die|threaten\s*to\s*kill|murder\s*you|lynch)\b"
        ]
    }
    
    @classmethod
    def evaluate_text(cls, text: str) -> Dict[str, Any]:
        """
        Scans text against VoiceOne civic decency guidelines.
        Returns:
            {
                "is_approved": bool,
                "status": "APPROVED" | "REMOVED",
                "violations": list of categories violated,
                "flagged_keywords": list of detected terms,
                "reason": explanation message
            }
        """
        if not text or not text.strip():
            return {
                "is_approved": False,
                "status": "REMOVED",
                "violations": ["EMPTY_CONTENT"],
                "flagged_keywords": [],
                "reason": "Post cannot be empty."
            }
            
        lowered_text = text.lower()
        detected_violations: List[str] = []
        flagged_terms: List[str] = []
        
        for category, patterns in cls.VIOLATION_RULES.items():
            for pattern in patterns:
                matches = re.findall(pattern, lowered_text, flags=re.IGNORECASE)
                if matches:
                    if category not in detected_violations:
                        detected_violations.append(category)
                    for match in matches:
                        term = match if isinstance(match, str) else match[0]
                        if term not in flagged_terms:
                            flagged_terms.append(term)
                            
        if detected_violations:
            readable_violations = [cls._format_category(v) for v in detected_violations]
            return {
                "is_approved": False,
                "status": "REMOVED",
                "violations": detected_violations,
                "flagged_keywords": flagged_terms,
                "reason": f"Content removed: Violates VoiceOne Civility Guidelines ({', '.join(readable_violations)})."
            }
            
        return {
            "is_approved": True,
            "status": "APPROVED",
            "violations": [],
            "flagged_keywords": [],
            "reason": "Content complies with VoiceOne Polite Discourse Guidelines."
        }
        
    @staticmethod
    def _format_category(category_key: str) -> str:
        mapping = {
            "CASTE_OR_CLASS_DISCRIMINATION": "Caste & Class Bias",
            "RELIGIOUS_HATRED": "Religious Intolerance",
            "GENDER_AND_SEXUAL_ORIENTATION": "Gender & Orientation Discrimination",
            "ABUSIVE_AND_HARASSMENT": "Profanity & Harassment"
        }
        return mapping.get(category_key, category_key.replace("_", " ").title())
