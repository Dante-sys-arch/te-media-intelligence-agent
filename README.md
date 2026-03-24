# TE Communications — Daily Media Intelligence Agent

Vollautomatisches tägliches Finanzmarkt-Morning-Briefing.  
Läuft jeden Morgen um **07:00 CET** via GitHub Actions.

## Funktionsweise

1. **06:00 UTC / 07:00 CET**: GitHub Actions startet den Agent
2. Der Agent ruft die **Anthropic Claude API mit Web Search** auf
3. Claude durchsucht systematisch **60+ seriöse Finanz- und Wirtschaftsmedien** weltweit
4. Alle **13 Themenfelder** werden abgedeckt
5. **Vergleich mit dem Vortag**: Jedes Thema wird als [NEU], [ESKALATION], [ENTSPANNUNG] oder [FORTLAUFEND] gekennzeichnet
6. Output: **HTML-Report** und **Textdatei** unter `output/`
7. Reports werden automatisch ins Repo committed

## 13 Themenfelder

| # | Themenfeld |
|---|---|
| 1 | Makroökonomie & Konjunktur |
| 2 | Geopolitik & Sicherheitspolitik |
| 3 | Energie & Rohstoffe |
| 4 | Zentralbanken & Geldpolitik |
| 5 | Aktienmärkte |
| 6 | Anleihemärkte & Fixed Income |
| 7 | FX / Devisen |
| 8 | Private Credit / Private Markets |
| 9 | Emerging Markets |
| 10 | Krypto / Digital Assets / Tokenisierung |
| 11 | Immobilienmärkte |
| 12 | ESG / Sustainable Finance / Regulierung |
| 13 | M&A / Deals / IPOs im Asset Management |

## Einordnung für

- **PGIM** — Fixed Income, Real Estate, Multi-Asset, CLO
- **T. Rowe Price** — Equities, Fixed Income, Growth
- **MK Global Kapital** — Private Credit, Impact, Microfinance, EM, Tokenisierung
- **Franklin Templeton** — Fixed Income, EM, Multi-Asset, Alternatives
- **PIMCO** — Fixed Income, Multi-Asset, Alternatives, Commodities
- **Eurizon** — Euro Fixed Income, EM Debt, Quantitative, ESG

## Quellenspektrum (60+)

**Deutsch:** Handelsblatt, FAZ, Börsen-Zeitung, SZ, WiWo, Spiegel, Manager Magazin, finanzen.net, boerse.de, dpa-AFX, Fonds Professionell, Citywire, DAS INVESTMENT, Institutional Money  
**Schweiz:** Finanz und Wirtschaft, NZZ, Cash, Moneycab, payoff  
**International:** Reuters, FT, Bloomberg, WSJ, CNBC, Fortune, Axios  
**Branche:** IPE, Morningstar, Seeking Alpha, The TRADE, CoinDesk  
**Immobilien:** CBRE, Cushman & Wakefield, JLL  
**Institutionen:** IEA, EZB, Fed, Bundesbank, OECD

## Setup

### 1. Anthropic API Key als Secret anlegen

1. Geh zu **console.anthropic.com** → API Keys → Create Key
2. Im GitHub Repo: **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**: Name = `ANTHROPIC_API_KEY`, Value = dein `sk-ant-...` Key

### 2. Workflow-Permissions prüfen

1. Repo **Settings** → **Actions** → **General**
2. Unter "Workflow permissions": **Read and write permissions** auswählen
3. **Save**

### 3. Erster Testlauf

1. **Actions** Tab → **TE Daily Media Intelligence** → **Run workflow**
2. Nach ca. 2-3 Minuten liegt der Report unter `output/`

## Output-Struktur

```
output/
├── 20260324_TE_Media_Intelligence.html    ← Formatierter Report
├── 20260324_TE_Media_Intelligence.txt     ← Plaintext
└── history/
    ├── 20260324.json                       ← Summary für Vortagesvergleich
    └── 20260323.json
```

## Kosten

Ca. **$0.50–1.50 pro Tag** (1-2 API-Calls mit Web Search, Claude Sonnet).

---

**TE Communications GmbH** | Frankfurt · Zürich · St. Gallen · Lausanne
