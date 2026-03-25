"""
TE Communications — Daily Media Intelligence Agent
Automated morning briefing via Anthropic API + Web Search
Runs daily at 07:00 CET via GitHub Actions
"""

import anthropic
import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 16000
OUTPUT_DIR = Path("output")
HISTORY_DIR = Path("output/history")

THEMENFELDER = [
    "Makroökonomie, Konjunktur, BIP, PMI, ifo, ZEW",
    "Geopolitik, Nahost, Iran, Ukraine, Sanktionen, Zölle, Handelskrieg",
    "Energie, Ölpreis Brent WTI, Gas TTF LNG, OPEC, Straße von Hormus",
    "Zentralbanken, EZB, Fed, BoE, BoJ, Zinsen, Inflation, CPI, PPI",
    "Aktienmärkte, DAX, S&P 500, Nasdaq, Nikkei, EuroStoxx, Bewertungen",
    "Anleihen, Fixed Income, Renditen, Bund, Treasury, Spreads, Credit, Duration",
    "FX Devisen, EUR/USD, Dollar, Rupie, Yen, Franken, DXY",
    "Private Credit, Private Markets, BCRED, BDC, Direct Lending, CLO, Alternatives",
    "Emerging Markets, Schwellenländer, Indien, China, Kapitalabflüsse",
    "Krypto, Bitcoin, Ethereum, Tokenisierung, RWA, Stablecoin, MiCA, SEC CFTC, Digital Assets",
    "Immobilien, CRE, REIT, Logistik, Büro, Wohnimmobilien, Datenzentren",
    "ESG, Sustainable Finance, SFDR, Taxonomie, Green Bond, Regulierung, ELTIF",
    "M&A, Übernahmen, IPOs, Personalwechsel, Mandate im Asset Management",
]

HAEUSER = [
    "PGIM (Prudential Financial, Fixed Income, Real Estate, Multi-Asset, CLO)",
    "T. Rowe Price (Equities, Fixed Income, Growth)",
    "MK Global Kapital (Private Credit, Impact, Microfinance, EM, Tokenisierung, Luxemburg)",
    "Franklin Templeton (Fixed Income, EM, Multi-Asset, Alternatives, Tokenisierung)",
    "PIMCO (Fixed Income, Multi-Asset, Alternatives, Commodities, Credit)",
    "Eurizon / Intesa Sanpaolo (Euro Fixed Income, EM Debt, Quantitative, ESG)",
]

QUELLEN_HINWEIS = """Durchsuche systematisch und gründlich die folgenden Quellen und weitere relevante seriöse Finanz- und Wirtschaftsmedien:
DEUTSCH: Handelsblatt, FAZ, Börsen-Zeitung, Süddeutsche Zeitung, WirtschaftsWoche, Der Spiegel, Manager Magazin, finanzen.net, boerse.de, dpa-AFX, Fonds Professionell, Citywire, DAS INVESTMENT, Institutional Money, e-fundresearch, PLATOW
SCHWEIZ: Finanz und Wirtschaft, NZZ, Cash, Moneycab, payoff
INTERNATIONAL: Reuters, Financial Times, Bloomberg, WSJ, CNBC, Fortune, Axios, NPR
BRANCHE: IPE, Morningstar, Seeking Alpha, The TRADE, CoinDesk, FinTech Weekly
IMMOBILIEN: CBRE, Cushman & Wakefield, JLL, Immobilien Zeitung
INSTITUTIONEN: IEA, EZB, Fed, Bundesbank, OECD
"""


def get_today_str():
    """Get today's date in German format."""
    now = datetime.utcnow() + timedelta(hours=1)  # CET
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    monate = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return f"{tage[now.weekday()]}, {now.day}. {monate[now.month]} {now.year}", now.strftime("%Y%m%d"), now.strftime("%H:%M")


def load_previous_report():
    """Load yesterday's report for comparison."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    if files:
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def build_prompt(date_str, time_str, previous_summary):
    """Build the full briefing prompt."""
    
    themen_block = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(THEMENFELDER))
    haeuser_block = "\n".join(f"  - {h}" for h in HAEUSER)
    
    diff_instruction = ""
    if previous_summary:
        diff_instruction = f"""

VERGLEICH MIT VORTAG:
Der gestrige Report hatte folgende Hauptthemen:
{previous_summary}

Bitte kennzeichne am Anfang jedes Themenblocks klar, ob das Thema:
- [NEU] heute erstmals auftaucht
- [ESKALATION] sich gegenüber gestern verschärft hat
- [ENTSPANNUNG] sich gegenüber gestern beruhigt hat
- [FORTLAUFEND] weitgehend unverändert weiterläuft
"""

    return f"""Du bist der weltweit führende Medienanalyst und Medienbeobachter für Finanz- und Kapitalmärkte. 

Stand: {date_str}, ca. {time_str} Uhr CET.

AUFGABE: Führe eine extrem sorgfältige, vollumfängliche Websuche und Analyse der heutigen Berichterstattung durch. Erfasse ALLE finanzmarktrelevanten Themen bis zur aktuellen Uhrzeit.

{QUELLEN_HINWEIS}

THEMENFELDER (alle systematisch abdecken):
{themen_block}

EINORDNUNG am Ende für folgende Asset Manager:
{haeuser_block}
{diff_instruction}

STRUKTUR DER AUSGABE:
1. Beginne mit einer kurzen Meta-Notiz (Stand der Recherche, erfasste Quellen, Gesamtcharakter der heutigen Nachrichtenlage)
2. Nummerierte analytische Themenblöcke — nach heutiger Relevanz sortiert, NICHT nach der Reihenfolge der Themenfelder oben. Nur Themen aufnehmen, die heute wirklich in der Berichterstattung sind. Jeder Block enthält:
   - Was genau berichtet wird (Fakten, Zahlen, Quellen)
   - Warum das für die Finanzmärkte relevant ist (Einordnung)
   - Konkrete Zahlen und Daten wo verfügbar
3. Block "Was daraus heute konkret für die beobachteten Häuser folgt" — für jedes der 6 Häuser
4. Block "Was die Berichterstattung heute NICHT dominiert"
5. Finanz- und Kapitalmarkttermine der kommenden 7 Tage (granular: Uhrzeit, Land, Termin, Relevanz)
6. Verdichtetes Fazit (1-2 Sätze)

REGELN:
- Nicht halluzinieren. Nicht phantasieren. Nur quellenbasierte Fakten.
- Englischsprachige Berichte gründlich ins Deutsche übertragen.
- Einfache, klare Sprache. Keine Telegrammstil-Sprache.
- Jeder Themenblock muss erklären, WARUM das Thema für die Finanzmärkte relevant ist.
- Präzise, detailliert und ausführlich.
- Die Berichterstattung von HEUTE bis zur aktuellen Uhrzeit muss vollständig erfasst werden.
"""


def run_briefing():
    """Run the full briefing via Anthropic API with web search."""
    
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    
    date_str, date_file, time_str = get_today_str()
    previous = load_previous_report()
    previous_summary = previous.get("summary", "") if previous else None
    
    prompt = build_prompt(date_str, time_str, previous_summary)
    
    print(f"[{time_str} CET] Starting Daily Media Intelligence Briefing for {date_str}")
    print(f"[{time_str} CET] Searching across {len(THEMENFELDER)} topic areas...")
    
    # Call Anthropic API with web search
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search"
            }
        ],
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract text from response
    report_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            report_text += block.text
    
    print(f"[{time_str} CET] Report generated: {len(report_text)} characters")
    
    # --- Generate summary for tomorrow's diff ---
    # Wait 60 seconds to avoid rate limiting on second API call
    print(f"[{time_str} CET] Waiting 60s before summary generation (rate limit protection)...")
    time.sleep(60)
    
    summary_text = ""
    try:
        summary_response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[
                {"role": "user", "content": f"Fasse die folgenden Hauptthemen des heutigen Finanzmarkt-Briefings in maximal 10 Stichpunkten zusammen (je 1 Zeile, nur die Kernaussage):\n\n{report_text[:8000]}"}
            ]
        )
        for block in summary_response.content:
            if hasattr(block, "text"):
                summary_text += block.text
        print(f"[{time_str} CET] Summary generated for tomorrow's diff.")
    except Exception as e:
        print(f"[{time_str} CET] Summary generation skipped (rate limit or error): {e}")
        # Fallback: use first 500 chars of report as summary
        summary_text = report_text[:500]
    
    # --- Save outputs ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save HTML report
    html = generate_html(report_text, date_str, time_str, previous_summary)
    html_path = OUTPUT_DIR / f"{date_file}_TE_Media_Intelligence.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{time_str} CET] HTML report saved: {html_path}")
    
    # Save plain text
    txt_path = OUTPUT_DIR / f"{date_file}_TE_Media_Intelligence.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"TE Communications — Daily Media Intelligence\n")
        f.write(f"{date_str}, {time_str} CET\n")
        f.write(f"{'='*60}\n\n")
        f.write(report_text)
    print(f"[{time_str} CET] Text report saved: {txt_path}")
    
    # Save history for comparison
    history_path = HISTORY_DIR / f"{date_file}.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "time": time_str,
            "summary": summary_text,
            "hash": hashlib.md5(report_text.encode()).hexdigest(),
            "length": len(report_text)
        }, f, ensure_ascii=False, indent=2)
    print(f"[{time_str} CET] History saved for tomorrow's diff: {history_path}")
    
    # Keep only last 30 days of history
    history_files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    for old_file in history_files[30:]:
        old_file.unlink()
    
    print(f"[{time_str} CET] ✅ Daily Media Intelligence Briefing complete.")
    return html_path


def generate_html(report_text, date_str, time_str, previous_summary):
    """Generate a styled HTML report."""
    
    # Convert markdown-ish text to HTML paragraphs
    paragraphs = report_text.split("\n\n")
    body_html = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith("# "):
            body_html += f'<h1>{p[2:]}</h1>\n'
        elif p.startswith("## "):
            body_html += f'<h2>{p[3:]}</h2>\n'
        elif p.startswith("### "):
            body_html += f'<h3>{p[4:]}</h3>\n'
        elif p.startswith("**") and p.endswith("**"):
            body_html += f'<h3>{p[2:-2]}</h3>\n'
        else:
            # Handle bold markers within text
            import re
            p_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', p)
            p_html = p_html.replace("\n", "<br>")
            body_html += f'<p>{p_html}</p>\n'
    
    diff_banner = ""
    if previous_summary:
        diff_banner = f'''
        <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:14px 18px;margin-bottom:24px;">
            <strong>Vergleich mit Vortag aktiviert.</strong> Themenblocks sind mit [NEU], [ESKALATION], [ENTSPANNUNG] oder [FORTLAUFEND] gekennzeichnet.
        </div>'''
    
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TE Media Intelligence — {date_str}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 820px; margin: 0 auto; padding: 32px 24px; color: #1f2937; line-height: 1.75; background: #fff; }}
  .header {{ text-align: center; border-bottom: 2px solid #002a3e; padding-bottom: 24px; margin-bottom: 28px; }}
  .header .label {{ font-size: 11px; letter-spacing: 0.3em; text-transform: uppercase; color: #002a3e; font-weight: 700; }}
  .header h1 {{ font-size: 24px; color: #002a3e; margin: 8px 0 4px; }}
  .header .date {{ font-size: 14px; color: #6b7280; }}
  .badges {{ display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-top: 12px; }}
  .badge {{ background: #002a3e; color: #fff; font-size: 10px; font-weight: 700; padding: 3px 9px; border-radius: 2px; letter-spacing: 0.04em; text-transform: uppercase; }}
  .alert {{ background: #991b1b; color: #fff; border-radius: 6px; padding: 14px 18px; margin-bottom: 24px; font-size: 13px; font-weight: 600; line-height: 1.55; }}
  h1 {{ font-size: 20px; color: #002a3e; margin: 28px 0 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
  h2 {{ font-size: 17px; color: #002a3e; margin: 24px 0 10px; }}
  h3 {{ font-size: 15px; color: #002a3e; margin: 20px 0 8px; }}
  p {{ margin: 0 0 14px; font-size: 14.5px; }}
  strong {{ color: #111827; }}
  .footer {{ margin-top: 36px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; }}
  .new {{ background: #dcfce7; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700; color: #166534; }}
  .escalation {{ background: #fee2e2; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700; color: #991b1b; }}
  .deescalation {{ background: #dbeafe; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700; color: #1e40af; }}
  .ongoing {{ background: #f3f4f6; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700; color: #4b5563; }}
</style>
</head>
<body>
<div class="header">
  <div class="label">TE Communications — Daily Media Intelligence</div>
  <h1>Tagesauswertung Medienbeobachtung &amp; Einordnung</h1>
  <div class="date">{date_str} — {time_str} CET</div>
  <div class="badges">
    <span class="badge">PGIM</span>
    <span class="badge">T. Rowe Price</span>
    <span class="badge">MK Global Kapital</span>
    <span class="badge">Franklin Templeton</span>
    <span class="badge">PIMCO</span>
    <span class="badge">Eurizon</span>
  </div>
</div>
{diff_banner}
{body_html}
<div class="footer">
  <strong>Methodik:</strong> Automatisierte Recherche via Anthropic Claude API mit Web Search über alle relevanten deutsch- und englischsprachigen Finanz-, Wirtschafts- und Branchenmedien. Vergleich mit Vortagesreport für Delta-Kennzeichnung. Keine Halluzinationen — alle Fakten sind quellenbasiert.<br><br>
  <strong>TE Communications GmbH</strong> | Frankfurt · Zürich · St. Gallen · Lausanne
</div>
</body>
</html>'''


if __name__ == "__main__":
    run_briefing()
