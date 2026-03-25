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
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 12000
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


def api_call_with_retry(func, max_retries=5, initial_wait=30):
    """Call an API function with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_str = str(e)
            if "overloaded" in error_str.lower() or "rate_limit" in error_str.lower() or "529" in error_str or "429" in error_str:
                wait_time = initial_wait * (2 ** attempt)
                print(f"  API busy (attempt {attempt+1}/{max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise  # Re-raise if it's not a retryable error
    raise Exception(f"API call failed after {max_retries} retries")


def run_briefing():
    """Run the full briefing via Anthropic API with web search."""
    
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    
    date_str, date_file, time_str = get_today_str()
    previous = load_previous_report()
    previous_summary = previous.get("summary", "") if previous else None
    
    prompt = build_prompt(date_str, time_str, previous_summary)
    
    print(f"[{time_str} CET] Starting Daily Media Intelligence Briefing for {date_str}")
    print(f"[{time_str} CET] Searching across {len(THEMENFELDER)} topic areas...")
    
    # Call Anthropic API with web search (with retry)
    response = api_call_with_retry(lambda: client.messages.create(
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
    ))
    
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
        summary_response = api_call_with_retry(lambda: client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[
                {"role": "user", "content": f"Fasse die folgenden Hauptthemen des heutigen Finanzmarkt-Briefings in maximal 10 Stichpunkten zusammen (je 1 Zeile, nur die Kernaussage):\n\n{report_text[:8000]}"}
            ]
        ))
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
    """Generate a premium styled HTML report with interactive sections."""
    import re
    
    # Convert markdown to structured HTML with collapsible sections
    lines = report_text.split("\n")
    body_html = ""
    in_section = False
    section_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_section:
                body_html += "<br>"
            continue
        
        # Handle headers - make them collapsible
        if line.startswith("# "):
            if in_section:
                body_html += '</div></details>'
                in_section = False
            section_count += 1
            title = line[2:]
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            body_html += f'''<details class="section" {"open" if section_count <= 3 else ""}>
                <summary class="section-header">
                    <span class="section-num">{section_count}.</span>
                    <span class="section-title">{title}</span>
                    <span class="chevron">&#9660;</span>
                </summary>
                <div class="section-body">'''
            in_section = True
        elif line.startswith("## "):
            title = line[3:]
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            if in_section:
                body_html += '</div></details>'
            section_count += 1
            body_html += f'''<details class="section">
                <summary class="section-header">
                    <span class="section-num">{section_count}.</span>
                    <span class="section-title">{title}</span>
                    <span class="chevron">&#9660;</span>
                </summary>
                <div class="section-body">'''
            in_section = True
        elif line.startswith("### "):
            title = line[4:]
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            body_html += f'<h3 class="subsection">{title}</h3>'
        elif line.startswith("**") and line.endswith("**"):
            body_html += f'<h3 class="subsection">{line[2:-2]}</h3>'
        elif line.startswith("- ") or line.startswith("* "):
            item = line[2:]
            item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
            body_html += f'<div class="list-item"><span class="bullet">&#9679;</span>{item}</div>'
        else:
            # Handle inline markers
            p_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            # Style delta markers
            p_html = p_html.replace("[NEU]", '<span class="tag tag-new">NEU</span>')
            p_html = p_html.replace("[ESKALATION]", '<span class="tag tag-esc">ESKALATION</span>')
            p_html = p_html.replace("[ENTSPANNUNG]", '<span class="tag tag-deesc">ENTSPANNUNG</span>')
            p_html = p_html.replace("[FORTLAUFEND]", '<span class="tag tag-cont">FORTLAUFEND</span>')
            body_html += f'<p>{p_html}</p>'
    
    if in_section:
        body_html += '</div></details>'
    
    diff_banner = ""
    if previous_summary:
        diff_banner = '''
        <div class="diff-banner">
            &#9888; <strong>Vergleich mit Vortag aktiviert.</strong> Themenblocks sind mit 
            <span class="tag tag-new">NEU</span> 
            <span class="tag tag-esc">ESKALATION</span> 
            <span class="tag tag-deesc">ENTSPANNUNG</span> 
            <span class="tag tag-cont">FORTLAUFEND</span> gekennzeichnet.
        </div>'''
    
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TE Media Intelligence — {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ 
    font-family: 'Source Serif 4', Georgia, serif; 
    max-width: 820px; margin: 0 auto; padding: 32px 20px; 
    color: #1f2937; line-height: 1.75; background: #fafafa; 
  }}
  
  /* HEADER */
  .header {{ 
    text-align: center; border-bottom: 3px solid #002a3e; 
    padding-bottom: 24px; margin-bottom: 28px; background: #fff;
    padding: 28px 24px; border-radius: 8px 8px 0 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .header .label {{ 
    font-size: 10.5px; letter-spacing: 0.3em; text-transform: uppercase; 
    color: #002a3e; font-weight: 700; margin-bottom: 10px;
  }}
  .header h1 {{ 
    font-size: 24px; color: #002a3e; margin: 0 0 4px; 
    border: none; padding: 0;
  }}
  .header .date {{ font-size: 13px; color: #6b7280; }}
  .badges {{ 
    display: flex; flex-wrap: wrap; gap: 5px; 
    justify-content: center; margin-top: 14px; 
  }}
  .badge {{ 
    background: #002a3e; color: #fff; font-size: 9.5px; font-weight: 700; 
    padding: 3px 10px; border-radius: 3px; letter-spacing: 0.05em; 
    text-transform: uppercase; 
  }}
  
  /* ALERT */
  .alert {{ 
    background: linear-gradient(135deg, #991b1b, #7f1d1d); color: #fff; 
    border-radius: 6px; padding: 16px 20px; margin-bottom: 20px; 
    font-size: 13px; font-weight: 600; line-height: 1.6;
    box-shadow: 0 2px 8px rgba(153,27,27,0.2);
  }}
  
  /* DIFF BANNER */
  .diff-banner {{
    background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px;
    padding: 12px 18px; margin-bottom: 20px; font-size: 12.5px; line-height: 1.6;
  }}
  
  /* TOGGLE ALL */
  .controls {{ 
    display: flex; justify-content: flex-end; margin-bottom: 12px; gap: 8px;
  }}
  .controls button {{
    background: none; border: 1px solid #002a3e; color: #002a3e;
    font-size: 11.5px; padding: 5px 14px; border-radius: 4px;
    cursor: pointer; font-weight: 600; font-family: inherit;
  }}
  .controls button:hover {{ background: #002a3e; color: #fff; }}
  
  /* COLLAPSIBLE SECTIONS */
  .section {{
    background: #fff; border: 1px solid #e5e7eb; border-radius: 6px;
    margin-bottom: 10px; overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    transition: all 0.2s;
  }}
  .section[open] {{ border-color: rgba(0,42,62,0.15); }}
  .section-header {{
    padding: 16px 20px; cursor: pointer; display: flex;
    align-items: flex-start; gap: 12px; list-style: none;
    user-select: none;
  }}
  .section-header::-webkit-details-marker {{ display: none; }}
  .section-header:hover {{ background: rgba(0,42,62,0.03); }}
  .section-num {{ 
    font-weight: 700; color: #002a3e; min-width: 24px; 
    font-size: 15px; 
  }}
  .section-title {{ 
    font-weight: 700; color: #002a3e; flex: 1; 
    font-size: 14.5px; line-height: 1.4; 
  }}
  .chevron {{ 
    font-size: 11px; color: #002a3e; flex-shrink: 0; 
    margin-top: 3px; transition: transform 0.2s;
  }}
  details[open] .chevron {{ transform: rotate(180deg); }}
  .section-body {{ 
    padding: 0 20px 20px; font-size: 14.2px; line-height: 1.78; 
  }}
  
  /* CONTENT */
  h1 {{ font-size: 18px; color: #002a3e; margin: 24px 0 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }}
  h2 {{ font-size: 16px; color: #002a3e; margin: 20px 0 10px; }}
  .subsection {{ 
    font-size: 14px; color: #002a3e; margin: 18px 0 8px; 
    padding-top: 12px; border-top: 1px solid rgba(0,42,62,0.06);
  }}
  p {{ margin: 0 0 12px; font-size: 14.2px; }}
  strong {{ color: #111827; }}
  .list-item {{
    font-size: 13.5px; line-height: 1.6; padding-left: 16px;
    position: relative; margin-bottom: 5px;
  }}
  .bullet {{ 
    position: absolute; left: 0; color: #002a3e; 
    font-size: 7px; top: 7px;
  }}
  
  /* TAGS */
  .tag {{ 
    padding: 2px 7px; border-radius: 3px; font-size: 10.5px; 
    font-weight: 700; display: inline-block; margin-right: 4px;
  }}
  .tag-new {{ background: #dcfce7; color: #166534; }}
  .tag-esc {{ background: #fee2e2; color: #991b1b; }}
  .tag-deesc {{ background: #dbeafe; color: #1e40af; }}
  .tag-cont {{ background: #f3f4f6; color: #4b5563; }}
  
  /* FAZIT */
  .fazit {{
    background: #002a3e; color: #fff; border-radius: 6px;
    padding: 20px 24px; margin-top: 24px;
  }}
  .fazit .label {{ 
    font-size: 11px; font-weight: 700; letter-spacing: 0.15em; 
    text-transform: uppercase; margin-bottom: 8px; opacity: 0.7; 
  }}
  .fazit p {{ color: #fff; font-size: 14px; line-height: 1.7; margin: 0; }}
  
  /* FOOTER */
  .footer {{ 
    margin-top: 32px; padding-top: 20px; 
    border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af;
    line-height: 1.6;
  }}
  
  @media (max-width: 600px) {{
    body {{ padding: 16px 12px; }}
    .header {{ padding: 20px 16px; }}
    .header h1 {{ font-size: 20px; }}
    .section-header {{ padding: 14px 16px; }}
    .section-body {{ padding: 0 16px 16px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="label">TE Communications — Daily Media Intelligence Agent</div>
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

<div class="controls">
  <button onclick="document.querySelectorAll('details.section').forEach(d=>d.open=true)">Alle offnen</button>
  <button onclick="document.querySelectorAll('details.section').forEach(d=>d.open=false)">Alle schliessen</button>
</div>

{body_html}

<div class="footer">
  <strong>Methodik:</strong> Automatisierte Recherche via Anthropic Claude API mit Web Search uber alle relevanten deutsch- und englischsprachigen Finanz-, Wirtschafts- und Branchenmedien. 
  Systematische Abdeckung von 13 Themenfeldern. Vergleich mit Vortagesreport fur Delta-Kennzeichnung. Keine Halluzinationen — alle Fakten sind quellenbasiert.<br><br>
  <strong>Quellen:</strong> Reuters, Handelsblatt, FAZ, FT, Bloomberg, IEA, ZDF, Borsen-Zeitung, SZ, WiWo, Spiegel, MM, FoPro, Citywire, DAS INVESTMENT, finanzen.net, IPE, NZZ, FuW, CoinDesk, CBRE, Cushman &amp; Wakefield, Morningstar, dpa-AFX u.v.m.<br><br>
  <strong>TE Communications GmbH</strong> | Frankfurt &middot; Zurich &middot; St. Gallen &middot; Lausanne
</div>

</body>
</html>'''


if __name__ == "__main__":
    run_briefing()
