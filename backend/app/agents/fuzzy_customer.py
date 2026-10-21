import re
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz
from app.config import settings

# Devanagari transliteration mapping to Roman characters
DEVANAGARI_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'i', 'उ': 'u', 'ऊ': 'u',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
}

DEVANAGARI_MATRAS = {
    'ा': 'a', 'ि': 'i', 'ी': 'i', 'ु': 'u', 'ू': 'u',
    'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    'ं': 'n', 'ँ': 'n', 'ः': 'h',
}

DEVANAGARI_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
    'ष': 'sh', 'स': 's', 'ह': 'h', 'क्ष': 'ksh', 'त्र': 'tr', 'ज्ञ': 'gy',
    'क़': 'q', 'ख़': 'kh', 'ग़': 'g', 'ज़': 'z', 'ड़': 'd', 'ढ़': 'dh', 'फ़': 'f',
}

HONORIFICS = {"ji", "sir", "saab", "sab", "bhai", "bhaiya", "uncle", "aunty", "seth", "sethji", "babu"}

def transliterate_devanagari(text: str) -> str:
    """
    Transliterate Devanagari Hindi characters into Roman phonetic characters.
    Properly handles consonants with inherent 'a' (e.g. व + र् + म + ा = verma/varma).
    """
    if not text:
        return ""
    chars = list(text)
    n = len(chars)
    out = []
    i = 0
    while i < n:
        ch = chars[i]
        if ch in DEVANAGARI_VOWELS:
            out.append(DEVANAGARI_VOWELS[ch])
        elif ch in DEVANAGARI_MATRAS:
            out.append(DEVANAGARI_MATRAS[ch])
        elif ch in DEVANAGARI_CONSONANTS:
            cons = DEVANAGARI_CONSONANTS[ch]
            # Check what follows
            next_ch = chars[i + 1] if i + 1 < n else None
            if next_ch == '्':  # Halant / Virama (no vowel)
                out.append(cons)
                i += 1  # Skip virama
            elif next_ch in DEVANAGARI_MATRAS or next_ch in DEVANAGARI_VOWELS or next_ch == ' ' or next_ch is None:
                out.append(cons)
            else:
                # Inherent 'a' / 'e' for hindi phonetics e.g. 'v' + 'a' -> va/ve
                out.append(cons + "a")
        else:
            out.append(ch)
        i += 1
    res = "".join(out)
    # Common Hindi romanization normalization e.g. 'varma' <-> 'verma'
    return res

def normalize_name(name: str) -> str:
    """
    Normalize names:
    - Transliterate Devanagari to Roman
    - Lowercase
    - Strip punctuation and extra spaces
    Note: Preserves honorific tokens in the string so 'Sharma ji' and 'Sharma Sir' stay distinct!
    """
    if not name:
        return ""
    # Transliterate first
    t = transliterate_devanagari(name)
    # Lowercase
    t = t.lower()
    # Strip punctuation (keep only alphanumeric and whitespace)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    # Collapse multiple spaces
    t = re.sub(r'\s+', ' ', t).strip()
    # Normalize common Hindi variant spellings: ee->i, oo->u, w->v, varma->verma
    t = re.sub(r'ee', 'i', t)
    t = re.sub(r'oo', 'u', t)
    t = re.sub(r'\bvarma\b', 'verma', t)
    return t

def extract_base_and_honorific(norm_name: str) -> Tuple[str, Optional[str]]:
    """
    Extract base name and trailing honorific if present.
    Example: 'sharma ji' -> ('sharma', 'ji')
    'sharma sir' -> ('sharma', 'sir')
    'vermaji' -> ('verma', 'ji') if attached
    """
    tokens = norm_name.split()
    if not tokens:
        return ("", None)
    
    if len(tokens) > 1 and tokens[-1] in HONORIFICS:
        return (" ".join(tokens[:-1]), tokens[-1])
    
    # Check attached suffix e.g. 'vermaji'
    first = tokens[0]
    for h in HONORIFICS:
        if first.endswith(h) and len(first) > len(h) + 2:
            base = first[:-len(h)]
            return (base, h)
            
    return (norm_name, None)

class FuzzyMatchResult:
    def __init__(
        self,
        decision: str, # "AUTO_MATCH", "ASK_USER", "NEW_CUSTOMER"
        customer: Optional[Dict[str, Any]] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        score: float = 0.0,
        near_duplicate_warning: Optional[str] = None
    ):
        self.decision = decision
        self.customer = customer
        self.candidates = candidates or []
        self.score = score
        self.near_duplicate_warning = near_duplicate_warning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "customer": self.customer,
            "candidates": self.candidates,
            "score": self.score,
            "near_duplicate_warning": self.near_duplicate_warning,
        }

def match_customer_fuzzy(
    query_name: str,
    customers_catalog: List[Dict[str, Any]],
    auto_threshold: Optional[float] = None,
    ask_threshold: Optional[float] = None,
) -> FuzzyMatchResult:
    """
    Feature 4: Fuzzy Customer Matching (plain Python, no model call)
    
    Rules & Constraints:
    - Normalizes query: lowercase, strips punctuation/extra spaces, transliterates Devanagari.
    - Thresholds from env (defaults):
      >= auto_threshold (92) and exactly ONE candidate -> AUTO_MATCH
      ask_threshold (75) to 92, OR multiple candidates -> ASK_USER
      < ask_threshold (75) -> NEW_CUSTOMER
    - HONORIFICS RULE:
      Do NOT strip honorifics (ji, sir, saab, bhai) in a way that merges different customers.
      'Sharma ji' and 'Sharma Sir' are different seeded customers.
      If the stripped base names are identical across multiple customers (e.g. 'Sharma'),
      always ask, never auto-match!
    - NEAR-DUPLICATE WARNING:
      If a "new customer" name scores >= 75 against an existing customer, show "Did you mean X?" first.
    """
    if auto_threshold is None:
        auto_threshold = getattr(settings, "FUZZY_MATCH_AUTO_THRESHOLD", 92.0)
    if ask_threshold is None:
        ask_threshold = getattr(settings, "FUZZY_MATCH_ASK_THRESHOLD", 75.0)

    norm_query = normalize_name(query_name)
    if not norm_query:
        return FuzzyMatchResult(decision="NEW_CUSTOMER", score=0.0)

    query_base, query_honorific = extract_base_and_honorific(norm_query)

    # Score each customer
    scored_candidates = []
    
    for c in customers_catalog:
        c_name = c["name"]
        norm_c_name = normalize_name(c_name)
        c_base, c_honorific = extract_base_and_honorific(norm_c_name)
        
        # Candidate names include canonical name + aliases
        names_to_compare = [norm_c_name]
        for a in c.get("aliases", []):
            names_to_compare.append(normalize_name(a))
            
        # Also include un-attached alias forms e.g. 'verma ji' for 'vermaji'
        if c_base and c_honorific:
            names_to_compare.append(f"{c_base} {c_honorific}")
            names_to_compare.append(f"{c_base}{c_honorific}")
            
        best_score = 0.0
        for cand_name in names_to_compare:
            # Using token_sort_ratio and ratio
            s1 = fuzz.ratio(norm_query, cand_name)
            s2 = fuzz.token_sort_ratio(norm_query, cand_name)
            s = max(s1, s2)
            if s > best_score:
                best_score = float(s)
                
        # Also check exact matching on base + honorific:
        # If query has honorific 'ji' and candidate has 'sir', they are DIFFERENT.
        honorific_conflict = False
        if query_honorific and c_honorific and query_honorific != c_honorific:
            honorific_conflict = True

        scored_candidates.append({
            "customer": c,
            "name": c_name,
            "id": str(c["_id"]),
            "score": best_score,
            "base": c_base,
            "honorific": c_honorific,
            "honorific_conflict": honorific_conflict,
        })

    # Sort descending by score
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    # Check how many customers share the same stripped base name in catalog
    base_matches_in_catalog = [sc for sc in scored_candidates if sc["base"] == query_base and sc["base"] != ""]
    
    # Check qualifying candidates
    high_candidates = [sc for sc in scored_candidates if sc["score"] >= auto_threshold and not sc["honorific_conflict"]]
    ask_candidates = [sc for sc in scored_candidates if sc["score"] >= ask_threshold]

    # Special check: If query matches base of multiple customers (e.g. query "Sharma", customers "Sharma ji", "Sharma Sir"),
    # or multiple customers have high scores, always ask!
    if len(base_matches_in_catalog) > 1 and (query_honorific is None or len(high_candidates) > 1):
        # Must ask, never auto-match!
        return FuzzyMatchResult(
            decision="ASK_USER",
            candidates=[sc["customer"] for sc in base_matches_in_catalog[:5]],
            score=scored_candidates[0]["score"] if scored_candidates else 0.0,
        )

    # Exactly one candidate >= auto_threshold without honorific conflict
    if len(high_candidates) == 1:
        top = high_candidates[0]
        # Ensure the runner up isn't tied or conflicting
        if len(scored_candidates) > 1 and scored_candidates[1]["score"] >= auto_threshold and not scored_candidates[1]["honorific_conflict"]:
            return FuzzyMatchResult(
                decision="ASK_USER",
                candidates=[sc["customer"] for sc in scored_candidates[:3]],
                score=top["score"],
            )
        return FuzzyMatchResult(
            decision="AUTO_MATCH",
            customer=top["customer"],
            candidates=[top["customer"]],
            score=top["score"],
        )

    # Multiple candidates >= auto_threshold
    if len(high_candidates) > 1:
        return FuzzyMatchResult(
            decision="ASK_USER",
            candidates=[sc["customer"] for sc in high_candidates[:5]],
            score=high_candidates[0]["score"],
        )

    # 75 <= score < 92: Ask user
    if ask_candidates:
        return FuzzyMatchResult(
            decision="ASK_USER",
            candidates=[sc["customer"] for sc in ask_candidates[:5]],
            score=ask_candidates[0]["score"],
            near_duplicate_warning=f"Did you mean {ask_candidates[0]['name']}?"
        )

    # Below 75: New customer, but check near duplicate warning if top score >= 70-74
    top_cand = scored_candidates[0] if scored_candidates else None
    warning = None
    if top_cand and top_cand["score"] >= 70.0:
        warning = f"Did you mean {top_cand['name']}?"

    return FuzzyMatchResult(
        decision="NEW_CUSTOMER",
        score=top_cand["score"] if top_cand else 0.0,
        near_duplicate_warning=warning
    )

def sanitize_alias(alias: str, max_length: Optional[int] = None) -> Optional[str]:
    """Sanitize spoken form before saving as an alias."""
    if max_length is None:
        max_length = getattr(settings, "ALIAS_MAX_LENGTH", 40)
    if not alias:
        return None
    # Strip control chars, special symbols
    s = re.sub(r'[\x00-\x1f\x7f]', '', alias).strip()
    s = re.sub(r'\s+', ' ', s)
    if not s:
        return None
    if len(s) > max_length:
        s = s[:max_length].strip()
    return s
