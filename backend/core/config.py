import re

# =====================================================
# THRESHOLDS
# =====================================================

CONFIDENCE_THRESHOLDS = {
    "person": 0.65,
    "brand": 0.60,
    "organization": 0.65,
    "city": 0.65,
    "country": 0.65,
    "location": 0.65
}

# =====================================================
# FILTER LISTS
# =====================================================

PRONOUNS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", 
    "myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves", "themselves"
}

GENERIC_BUSINESS_WORDS = {
    "customers", "shareholders", "investors", "employees", "staff", "management", 
    "board", "directors", "legal", "company", "business", "enterprise", "industry",
    "market", "sector", "department", "team", "group", "committee", "businesses",
    "good companies", "legal departments", "industry bodies", "companies", "organizations",
    "departments", "teams", "groups", "committees", "markets", "sectors"
}

INVALID_PERSON_ROLES = {
    "managing director", "general counsel", "ceo", "founder", "director", "president",
    "chairman", "chief executive officer", "chief technology officer", "cto", "cfo", "coo",
    "clo", "gc", "aspiring lawyers", "lawyers", "lawyer", "attorney", "advocate", "judge",
    "counsel"
}

# Combine for quick lookups where necessary
ALL_STOPWORDS = PRONOUNS.union(GENERIC_BUSINESS_WORDS).union(INVALID_PERSON_ROLES)

# =====================================================
# NORMALIZATION CONFIG
# =====================================================

ORG_SUFFIXES = [
    r'\bbrand\b',
    r'\bcompany\b',
    r'\blimited\b',
    r'\bltd\.?\b',
    r'\binc\.?\b',
    r'\bcorp\.?\b',
    r'\bcorporation\b',
    r'\bllc\b',
    r'\bplc\b'
]

# Compile suffixes into a single regex for stripping
ORG_SUFFIX_REGEX = re.compile(r'(?i)\s+(' + '|'.join(ORG_SUFFIXES) + r')\s*$')

# =====================================================
# HEURISTIC DICTIONARIES (AUTHOR INTELLIGENCE)
# =====================================================

MALE_NAMES = {"john", "david", "michael", "james", "robert", "navdeep"} # Extendable
FEMALE_NAMES = {"mary", "patricia", "linda", "barbara", "elizabeth", "sarah"} # Extendable

ROLE_PATTERNS = {
    "CEO": [r'\bceo\b', r'chief executive officer'],
    "CLO": [r'\bclo\b', r'chief legal officer'],
    "CTO": [r'\bcto\b', r'chief technology officer'],
    "CFO": [r'\bcfo\b', r'chief financial officer'],
    "General Counsel": [r'\bgc\b', r'general counsel'],
    "Director": [r'director', r'managing director', r'md'],
    "Founder": [r'founder', r'co-founder'],
    "Manager": [r'manager', r'head of'],
    "Partner": [r'partner']
}
