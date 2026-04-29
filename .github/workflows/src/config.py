RECIPIENT_EMAIL = "thomas.garcia@eiqus.com"
SENDER_EMAIL    = "thomas.garcia@eiqus.com"
SCORE_THRESHOLD = 70

EIQUS_CONTEXT = """
EIQUS NGA = acteur hybride santé mentale + innovation deeptech (France).
Protocole PSCE® breveté INPI 21 02798, validé 650+ cas. JEI, Bpifrance DeepTech TRL6.
Modules IA : SCORING, TRACE, REACT, EVA. VR VRET (Cocoon). Biofeedback EEG/HRV/EDA. Médiation équine.
Clients : AG2R La Mondiale, La Banque Postale, Mutuelle des Motards, Château de Versailles, Royal Canin, Pôle Emploi.
Marchés : France (priorité), Italie (Roma GTM actif, EQUAL+), Suisse (Thomas Garcia basé Zurich).
"""

QUERY_BATCHES = [
    {"label": "Marchés publics France", "queries": [
        "site:boamp.fr \"santé mentale\" OR \"QVCT\" OR \"RPS\" OR \"bien-être au travail\" 2025 2026",
        "\"appel d'offres\" \"risques psychosociaux\" OR \"qualité de vie au travail\" \"plateforme numérique\" France 2025 2026",
        "\"marché public\" \"programme d'aide aux salariés\" OR \"EAP\" OR \"soutien psychologique\" France 2025 2026",
        "\"accord-cadre\" \"burn-out\" OR \"épuisement professionnel\" prévention France 2025 2026",
    ]},
    {"label": "Assureurs & Mutuelles France", "queries": [
        "\"appel d'offres\" assureur mutuelle \"santé mentale\" AG2R Malakoff MGEN Harmonie Apicil 2025 2026",
        "\"appel d'offres\" \"médiation équine\" OR \"médiation animale\" OR \"thérapie assistée\" entreprise France",
        "\"appel d'offres\" \"réalité virtuelle\" OR \"VRET\" santé mentale France 2026",
        "\"consultation\" \"bien-être psychologique\" salarié mutuelle prévoyance 2026",
    ]},
    {"label": "Italie + Suisse", "queries": [
        "\"bando\" OR \"gara appalto\" \"salute mentale\" OR \"benessere aziendale\" 2025 2026",
        "\"pet therapy\" OR \"mediazione equina\" bando appalto Italia 2025 2026",
        "site:simap.ch \"psychische Gesundheit\" OR \"Wohlbefinden\" Ausschreibung 2025 2026",
        "\"santé mentale\" \"appel d'offres\" Suisse assureur 2025 2026",
    ]},
    {"label": "TED Europa + EU", "queries": [
        "site:ted.europa.eu \"mental health\" OR \"wellbeing\" OR \"employee assistance\" tender 2025 2026",
        "\"procurement\" \"digital mental health\" OR \"behavioral health\" Europe 2025 2026",
        "\"Ausschreibung\" \"psychische Gesundheit\" Versicherung 2026",
        "\"benessere aziendale\" \"prevenzione burnout\" assicurazione 2025 2026",
    ]},
    {"label": "Grants publics FR/EU", "queries": [
        "Bpifrance \"Grand Défi\" \"dispositifs médicaux numériques\" \"santé mentale\" France 2030",
        "ARS \"fonds innovation organisationnelle psychiatrie\" FIOP appel projets 2025 2026",
        "\"Agence du Numérique en Santé\" \"Structures 3.0\" santé mentale 2025 2026",
        "\"Horizon Europe\" HORIZON-HLTH-2026 \"mental health\" digital call 2026",
    ]},
    {"label": "Fondations assureurs", "queries": [
        "\"La Fabrique Abeille Assurances\" OR \"Fondation AG2R\" OR \"Fondation Apicil\" appel projets santé 2025 2026",
        "\"Fondation Groupama\" OR \"Fondation Malakoff\" \"santé mentale\" appel projets 2026",
        "\"The Human Safety Net\" Generali OR \"INAIL\" salute mentale 2025 2026",
        "\"Innosuisse\" OR \"Mobiliar\" \"santé mentale\" financement Suisse 2026",
    ]},
]
