# TE Communications — Daily Media Intelligence Agent v3.1

Vollautomatischer Medienanalyse-Agent. Liefert jeden Morgen um 07:00 CET ein strategisches Finanzmarkt-Briefing mit Positionierungs-Mapping für 9 Kunden.

**Live Dashboard:** https://dante-sys-arch.github.io/te-media-intelligence-agent/

## Architektur (v3.1)

### Zwei-Pass-System
1. **Pass 1 — Marktrecherche** (Claude Sonnet + Web Search)
2. **Pass 2 — PR-Positionierung** (Claude Haiku)
3. Automatischer Modell-Fallback bei Überlastung

### 137 RSS-Feeds in 3 Schichten
- Layer 1: 98 direkte Medien-Feeds (DE/CH/AT/INT)
- Layer 2: 39 Google News Themensuchen
- Layer 3: Claude Live Web Search

### Performance-Features
- Paralleles RSS-Fetching (20 Threads, 5-10x schneller)
- Kunden-Mention-Detection für alle 9 Kunden
- 5-Tage-Trend-Tracking
- 24h-Zeitfilter

## 9 Kunden
PGIM, T. Rowe Price, MK Global Kapital, Franklin Templeton, PIMCO, Eurizon, Temasek, Bitcoin Suisse, KKR

## 14 Themenfelder
Makro, Geopolitik, Energie, Zentralbanken, Aktien, Anleihen, FX, Private Credit, Private Equity, EM, Krypto, Immobilien, ESG, M&A

## Tägliche Ausführung
- GitHub Actions Cron: 06:00 UTC = 07:00 CET
- Manuell: Actions → Run workflow

## Kontakt
TE Communications GmbH | Frankfurt · Zürich · St. Gallen · Lausanne
