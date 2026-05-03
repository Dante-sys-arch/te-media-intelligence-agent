"""
TE Communications — Shared Section Metadata
============================================
Single source of truth for section icons and short descriptions
("Was bedeutet diese Kategorie / Wofuer ist sie gut?").

Used by BOTH dashboard (src/main.py) AND email (src/send_email.py)
to ensure visual + textual consistency.

Each section has:
- keywords: list of partial title matches (case-insensitive) used to identify the section
- icon: SVG inline (so it works in email without external resources)
- short: 2-3 Saetze Kurzerlaeuterung — was die Kategorie bedeutet, wofuer sie gut ist
- linklabel: text fuer den Deep-Link aus der E-Mail zum Dashboard
"""

# Inline SVG icons (24x24, currentColor) — render in email AND web
ICON_DATA = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 5-5"/></svg>'
ICON_TOP = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15 9 22 9 17 14 19 21 12 17 5 21 7 14 2 9 9 9 12 2"/></svg>'
ICON_MARKET = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>'
ICON_DEEP = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-9 6 18 3-9h4"/></svg>'
ICON_TRENDS = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>'
ICON_WHITE = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5"/></svg>'
ICON_COMPETE = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/><circle cx="17" cy="7" r="3"/><path d="M21 21v-2a3 3 0 0 0-2-3"/></svg>'
ICON_LIVE = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9"/></svg>'
ICON_PRIO = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="9" y2="18"/></svg>'
ICON_FILTER = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>'
ICON_SPEAKER = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1v-6h3zM3 19a2 2 0 0 0 2 2h1v-6H3z"/></svg>'
ICON_PITCH = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L4 9v8l8 7 8-7V9z"/><path d="M9 11l2 2 4-4"/></svg>'
ICON_CLIENT = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-6 9 6v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'
ICON_CALENDAR = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
ICON_FAZIT = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>'
ICON_SOURCES = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'

# Section definitions in display order
SECTIONS = [
    {
        "id": "datenlage",
        "keywords": ["Datenlage und Recherche-Status", "Datenlage", "Zugriffslage", "Recherche-Status"],
        "title": "Datenlage und Recherche-Status",
        "icon": ICON_DATA,
        "short": "Hier zeigen wir, wie belastbar die heutige Datenbasis ist: Wie viele RSS-Feeds wurden erfolgreich abgerufen, welche Quellen waren eingeschraenkt, wie aktuell ist die Recherche. Wichtig fuer die Einordnung der nachfolgenden Inhalte.",
        "linklabel": "Volle Recherche-Statistik",
    },
    {
        "id": "top-themen-des-tages",
        "keywords": ["Top-Themen des Tages", "Top 5 Themen"],
        "title": "Top-Themen des Tages",
        "icon": ICON_TOP,
        "short": "Die fuenf wichtigsten Markt-Themen heute, jeweils in zwei Saetzen. Schneller Ueberblick, was den Tag bewegt — Tiefe folgt im naechsten Abschnitt.",
        "linklabel": "Vollstaendige Top-Themen",
    },
    {
        "id": "marktbild-des-tages",
        "keywords": ["Marktbild", "Markt-Recherche", "Marktanalyse"],
        "title": "Marktbild des Tages",
        "icon": ICON_MARKET,
        "short": "Das uebergreifende Narrativ: Welche Metageschichte verbindet die einzelnen Themen? Hilft, hinter den Tagesschlagzeilen das groessere Bild zu erkennen.",
        "linklabel": "Vollstaendige Marktanalyse",
    },
    {
        "id": "tiefenanalyse--top-themen",
        "keywords": ["Tiefenanalyse"],
        "title": "Tiefenanalyse — Top-Themen",
        "icon": ICON_DEEP,
        "short": "Pro Top-Thema die strukturierte Acht-Punkte-Analyse: Fakten, Kausalkette, Cross-Asset-Wirkung, historische Analogie, Szenarien, Konsens vs. Kontrarian, blinder Fleck. Diese Tiefe ist die Grundlage fuer belastbare Pitch-Empfehlungen.",
        "linklabel": "Vollstaendige Tiefenanalyse",
    },
    {
        "id": "mehrtages-trends",
        "keywords": ["Mehrtages-Trends"],
        "title": "Mehrtages-Trends",
        "icon": ICON_TRENDS,
        "short": "Was zieht sich seit mehreren Tagen durch die Berichterstattung? Was eskaliert, was klingt ab? Wichtig, um nicht in jeder Tagesausgabe bei Null anzufangen.",
        "linklabel": "Volle Trend-Analyse",
    },
    {
        "id": "unterdiskutierte-themen--white-spaces",
        "keywords": ["White Spaces", "Unterdiskutiert"],
        "title": "Unterdiskutierte Themen — White Spaces",
        "icon": ICON_WHITE,
        "short": "Themen mit Erzaehl-Vakuum: kaum in den Medien, aber relevant. Hier liegen die staerksten Pitch-Chancen, weil Journalisten neue Winkel suchen, die keine Konkurrenz schon abgegrast hat.",
        "linklabel": "Volle White-Space-Analyse",
    },
    {
        "id": "konkurrenz-beobachtung",
        "keywords": ["Konkurrenz"],
        "title": "Konkurrenz-Beobachtung",
        "icon": ICON_COMPETE,
        "short": "Was kommunizieren BlackRock, DWS, Apollo, Allianz GI und weitere grosse Wettbewerber unserer Kunden heute? Wo entstehen Konter-Chancen — Themen, zu denen unsere Kunden eine differenzierende Sicht beisteuern koennen.",
        "linklabel": "Volle Konkurrenz-Beobachtung",
    },
    {
        "id": "live-recherche-pro-kunde",
        "keywords": ["Live-Recherche", "KUNDEN-LIVE"],
        "title": "Live-Recherche pro Kunde",
        "icon": ICON_LIVE,
        "short": "Pro Kunde die heutigen Live-Befunde: aktuell verifizierte DACH-Sprecher, direkte Erwaehnungen in den Medien heute, aktuelle Themen-Schwerpunkte des Hauses. Basis fuer alle Pitch-Empfehlungen darunter.",
        "linklabel": "Volle Sprecher-Recherche aller 13 Kunden",
    },
    {
        "id": "themen-priorisierung",
        "keywords": ["Themen-Priorisierung", "Priorisierte Themen"],
        "title": "Themen-Priorisierung",
        "icon": ICON_PRIO,
        "short": "Tabellarische Sicht: Welche Themen haben heute welche Dringlichkeit, welche Medienarbeits-Eignung, welche Kunden passen am besten dazu. Hilft beim Tages-Workflow, wo zuerst angesetzt werden sollte.",
        "linklabel": "Volle Prioritaeten-Tabelle",
    },
    {
        "id": "themen-filter--was-ist-heute-pitchbar",
        "keywords": ["Themen-Filter"],
        "title": "Themen-Filter — Was ist heute pitchbar?",
        "icon": ICON_FILTER,
        "short": "Anwendung der fuenf inhaltlichen Pitch-Kriterien (Aktualitaet, Neuheit, Differenzierung, Konflikt, Belegbarkeit) auf alle Tages-Themen. Transparente Filterung mit Begruendung — auch fuer verworfene Themen.",
        "linklabel": "Volle Pitch-Filterung mit Begruendung",
    },
    {
        "id": "sprecher-mapping--wer-von-uns-kann-pitchen",
        "keywords": ["Sprecher-Mapping"],
        "title": "Sprecher-Mapping — Wer von uns kann pitchen?",
        "icon": ICON_SPEAKER,
        "short": "Pro pitchbarem Thema: welcher unserer 13 Kunden hat den passenden Sprecher mit Asset-Klassen-Autoritaet und aktueller Live-Verifikation? Wenn keiner passt, wird das ehrlich ausgewiesen.",
        "linklabel": "Volles Sprecher-Mapping pro Thema",
    },
    {
        "id": "pitch-empfehlungen-hergeleitet",
        "keywords": ["Pitch-Empfehlungen"],
        "title": "Pitch-Empfehlungen (hergeleitet)",
        "icon": ICON_PITCH,
        "short": "Das zentrale Ergebnis des Tages: vier bis sieben hergeleitete Pitches mit dokumentierter Bewertung, fertigem Pitch-Material, Sprecher-Match und Zielmedium. Jeder Pitch ist nachvollziehbar begruendet — keine Black Box.",
        "linklabel": "Volle Pitch-Briefings (mit Herleitung + Mail-Vorschlag)",
    },
    {
        "id": "kunden-sicht--was-bedeutet-das-pro-kunde",
        "keywords": ["Kunden-Sicht"],
        "title": "Kunden-Sicht — Was bedeutet das pro Kunde?",
        "icon": ICON_CLIENT,
        "short": "Umsortierung nach Kunden: welche Kunden haben heute einen Pitch, welche nicht, mit ehrlicher Begruendung. Hilft beim Kunden-Briefing und bei der internen Tagessteuerung.",
        "linklabel": "Volle Kunden-Sicht (mit/ohne Pitch heute)",
    },
    {
        "id": "termin-vorschau-7-tage",
        "keywords": ["Termin-Vorschau", "Termine"],
        "title": "Termin-Vorschau 7 Tage",
        "icon": ICON_CALENDAR,
        "short": "Wirtschafts- und Finanztermine der naechsten Woche mit Datum, Uhrzeit und Relevanz. Vorlauf fuer kommende Pitch-Anlaesse.",
        "linklabel": "Vollstaendiger Termin-Ueberblick",
    },
    {
        "id": "gesamtfazit",
        "keywords": ["Gesamtfazit"],
        "title": "Gesamtfazit",
        "icon": ICON_FAZIT,
        "short": "In zwei bis drei Saetzen das uebergeordnete Narrativ und der differenzierendste Pitch-Winkel fuer heute. Die Quintessenz des Briefings.",
        "linklabel": "Volltext",
    },
    {
        "id": "quellenverzeichnis",
        "keywords": ["Quellenverzeichnis"],
        "title": "Quellenverzeichnis",
        "icon": ICON_SOURCES,
        "short": "Vollstaendige Liste aller heute ausgewerteten Quellen, sortiert nach Kategorien (Deutsche Leitmedien, Fachmedien, Schweiz, International). Transparenz ueber die Recherche-Breite.",
        "linklabel": "Volle Quellenliste",
    },
]


def find_section_meta(title_or_text):
    """Given a section title from the report, return the matching SECTIONS entry or None."""
    if not title_or_text:
        return None
    lower = title_or_text.lower()
    for s in SECTIONS:
        for kw in s["keywords"]:
            if kw.lower() in lower:
                return s
    return None


def slug_for_title(title):
    """Generate URL anchor from section title (must match generation in main.py)."""
    import re
    s = re.sub(r'[^\w\s-]', '', title.lower())
    s = re.sub(r'[\s_]+', '-', s).strip('-')
    return s[:60]
