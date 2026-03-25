"""
TE Communications — Daily Media Intelligence Agent
Automated morning briefing via Anthropic API + Web Search + Google News RSS
Runs daily at 07:00 CET via GitHub Actions
"""

import anthropic
import json
import os
import hashlib
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 8000
OUTPUT_DIR = Path("output")
HISTORY_DIR = Path("output/history")

# Google News RSS feeds for pre-research
GOOGLE_NEWS_FEEDS = [
    "https://news.google.com/rss/search?q=Finanzmärkte+Kapitalmärkte+aktuell&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=DAX+Börse+heute&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=EZB+Fed+Zinsen+Inflation+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Ölpreis+Energie+Nahost+Iran+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Asset+Management+Fonds+ETF+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Private+Credit+Private+Debt+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Immobilien+REIT+Gewerbeimmobilien+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Bitcoin+Krypto+Tokenisierung+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=ESG+Sustainable+Finance+Regulierung+2026&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Emerging+Markets+Schwellenländer+Rupie+2026&hl=de&gl=DE&ceid=DE:de",
    # English feeds
    "https://news.google.com/rss/search?q=PIMCO+OR+PGIM+OR+%22Franklin+Templeton%22+OR+%22T+Rowe+Price%22+OR+Eurizon+OR+Temasek&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=oil+price+Iran+war+markets+today&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=gold+price+crash+liquidity+2026&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=private+credit+BCRED+BlackRock+withdrawal+2026&hl=en&gl=US&ceid=US:en",
]

THEMENFELDER = [
    "Makro/Konjunktur (BIP, PMI, ifo, ZEW)",
    "Geopolitik (Nahost/Iran, Ukraine, Zölle, Handelskrieg)",
    "Energie/Rohstoffe (Öl, Gas, Gold, Kupfer)",
    "Zentralbanken (EZB, Fed, BoE, Zinsen, Inflation)",
    "Aktien-/Anleihemärkte (DAX, S&P, Renditen, Spreads)",
    "FX/Devisen, Private Credit, Emerging Markets",
    "Krypto/Tokenisierung, Immobilien, ESG/Regulierung",
    "M&A/Deals/IPOs im Asset Management",
]


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


def fetch_google_news_headlines():
    """Fetch current headlines from Google News RSS feeds."""
    headlines = []
    for feed_url in GOOGLE_NEWS_FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "TE-Media-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:8]:  # Max 8 per feed
                title = item.findtext("title", "")
                source = item.findtext("source", "")
                pub_date = item.findtext("pubDate", "")
                link = item.findtext("link", "")
                if title:
                    headlines.append(f"- {title} ({source}, {pub_date[:16]})")
        except Exception as e:
            print(f"  RSS feed error: {e}")
            continue
    # Deduplicate
    seen = set()
    unique = []
    for h in headlines:
        key = h[:80].lower()
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return unique[:60]  # Max 60 headlines to keep prompt short


def build_prompt(date_str, time_str, previous_summary, rss_headlines):
    """Build the full briefing prompt."""
    
    diff_instruction = ""
    if previous_summary:
        diff_instruction = f"""
VERGLEICH MIT VORTAG — kennzeichne jedes Thema mit:
[NEU] / [ESKALATION] / [ENTSPANNUNG] / [FORTLAUFEND]
Gestern: {previous_summary[:800]}
"""

    headlines_block = "\n".join(rss_headlines[:40]) if rss_headlines else "Keine RSS-Headlines verfuegbar."

    return f"""Du bist ein strategischer Finanzkommunikationsberater bei einer PR-Beratung. Du suchst Medien-Positionierungsmoeglichkeiten (Gastbeitraege, Interviews, Kommentare) fuer diese Kunden:
- PGIM: Institutional, Multi-Asset, Real Estate, Fixed Income
- T. Rowe Price: Active Equity, Multi-Asset, ETF-Strategie
- MK Global Kapital: Impact/Microfinance, EM, Tokenisierung
- Franklin Templeton: Multi-Asset, EM, ETF, Martin Lueck als Sprecher
- PIMCO: Fixed Income, Alternatives, Commodities
- Eurizon: Euro Fixed Income, EM Debt, ESG
- Temasek: Singapurer Staatsfonds, globale Investments, Infrastruktur, Tech, Life Sciences, DACH-Praesenz

Stand: {date_str}, {time_str} CET. Durchsuche Handelsblatt, FAZ, Boersen-Zeitung, finanzen.net, Reuters, FT, Bloomberg, Fonds Professionell, Citywire, DAS INVESTMENT, NZZ, CNBC u.v.m.

AKTUELLE GOOGLE NEWS SCHLAGZEILEN (als Kontext fuer deine Recherche):
{headlines_block}

Themenfelder: {', '.join(THEMENFELDER)}
{diff_instruction}
AUSGABE in 5 Schritten:

## Schritt 1 — Recherche-Ueberblick
Was heute geprueft wurde, Gesamtcharakter der Nachrichtenlage, uebergreifendes Narrativ.

## Schritt 2 — Themen die das Markt-Narrativ treiben
Nummerierte Bloecke, nach Relevanz sortiert. Pro Block:
- Was dominiert die Headlines heute (Fakten, Zahlen, Quellen)
- Narrativ und Einordnung: Was ist die groessere Story dahinter? Gibt es einen Trendwechsel? Ist das eine Eskalation, eine Wende, eine Fortsetzung? Welches uebergeordnete Thema (z.B. Stagflation, Energiesicherheit, Liquiditaetskrise) wird hier sichtbar?
- Veraenderung: Hat sich gegenueber den Vortagen etwas Wesentliches verschoben?

## Schritt 3 — Positionierungs-Mapping auf die Kunden
Fuer jedes Haus: Ueber welche Achsen ist es HEUTE kommunikativ anschlussfaehig? Konkrete Pitch-Ideen, Gastbeitrag-Themen, Interview-Aufhaenger. KEINE Portfolio-Empfehlungen, KEINE Trading-Sprache. Denke wie ein PR-Berater: Mit welchem Thema kann ich diesen Kunden in FAZ, Handelsblatt, Fonds Professionell oder FT platzieren?

## Schritt 4 — Termine naechste 7 Tage
Datum, Uhrzeit, Land, Termin, Relevanz.

## Schritt 5 — Konkrete Pitch-Ableitungen
3-5 umsetzbare Ideen: Thema, Format (Kommentar/Gastbeitrag/Interview), welcher Kunde, welches Medium.

## Gesamtfazit
2-3 Saetze: Was ist das uebergeordnete Narrativ heute? Welche groesseren Trends oder Verschiebungen werden sichtbar?

Regeln: Nicht halluzinieren. Quellenbasiert. Deutsch. Keine Trading-Sprache. Stattdessen: "Anschlussfaehig ueber...", "Pitch-Idee:", "Gastbeitrag-Thema:".
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
    """Run the full briefing via Anthropic API with web search + Google News RSS."""
    
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    
    date_str, date_file, time_str = get_today_str()
    previous = load_previous_report()
    previous_summary = previous.get("summary", "") if previous else None
    
    # Step 1: Fetch Google News RSS headlines
    print(f"[{time_str} CET] Fetching Google News RSS feeds ({len(GOOGLE_NEWS_FEEDS)} feeds)...")
    rss_headlines = fetch_google_news_headlines()
    print(f"[{time_str} CET] Collected {len(rss_headlines)} unique headlines from Google News")
    
    # Step 2: Build prompt with RSS context
    prompt = build_prompt(date_str, time_str, previous_summary, rss_headlines)
    
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
