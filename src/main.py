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
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 12000
OUTPUT_DIR = Path("output")
HISTORY_DIR = Path("output/history")

# === RSS FEED ARCHITECTURE ===
# Layer 1: Direct RSS feeds from specific media outlets (most reliable, real-time)
# Layer 2: Google News thematic searches (broader, cross-source)

MEDIA_RSS_FEEDS = [
    # === DEUTSCHE LEITMEDIEN ===
    "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "https://www.handelsblatt.com/contentexport/feed/top-themen",
    "https://www.handelsblatt.com/contentexport/feed/unternehmen",
    "https://www.faz.net/rss/aktuell/finanzen/",
    "https://www.faz.net/rss/aktuell/wirtschaft/",
    "https://www.faz.net/rss/aktuell/finanzen/finanzmarkt/",
    "https://www.sueddeutsche.de/wirtschaft?output=rss",
    "https://www.sueddeutsche.de/geld?output=rss",
    "https://www.wiwo.de/rss/feed.finanzen.rss",
    "https://www.wiwo.de/rss/feed.geldanlage.rss",
    "https://www.wiwo.de/rss/feed.unternehmen.rss",
    "https://www.spiegel.de/wirtschaft/index.rss",
    "https://www.manager-magazin.de/finanzen/index.rss",
    "https://www.manager-magazin.de/unternehmen/index.rss",
    "https://www.tagesschau.de/wirtschaft/boerse/index~rss2.xml",
    "https://www.tagesschau.de/wirtschaft/index~rss2.xml",
    "https://www.finanzen.net/rss/news",
    "https://www.n-tv.de/wirtschaft/rss",
    "https://www.welt.de/feeds/section/finanzen.rss",
    "https://www.welt.de/feeds/section/wirtschaft.rss",
    "https://www.tagesspiegel.de/wirtschaft/rss",
    "https://www.zeit.de/wirtschaft/index",
    "https://www.stern.de/wirtschaft/feed.rss",
    # === DEUTSCHE FACHMEDIEN (Finanzen/AM) ===
    "https://www.fondsprofessionell.de/rss/news.xml",
    "https://www.dasinvestment.com/feed/",
    "https://citywire.de/rss",
    "https://www.institutional-money.com/rss/news.xml",
    "https://www.private-banking-magazin.de/feed/",
    "https://www.altii.de/feed/",
    "https://www.portfolio-institutionell.de/feed/",
    "https://www.fundresearch.de/rss/news.xml",
    "https://www.boerse-online.de/rss/news",
    "https://www.4investors.de/rss/rss_alle_news.php",
    "https://www.anleihencheck.de/rss/",
    "https://www.bondguide.de/feed/",
    "https://www.exxecnews.de/feed/",
    "https://www.dpn-online.com/feed/",
    # === DEUTSCHE IMMOBILIEN ===
    "https://www.iz.de/rss/news.xml",
    "https://www.thomas-daily.de/feed/",
    # === SCHWEIZER MEDIEN ===
    "https://www.nzz.ch/finanzen.rss",
    "https://www.nzz.ch/wirtschaft.rss",
    "https://www.fuw.ch/feed",
    "https://www.cash.ch/rss/news",
    "https://www.handelszeitung.ch/rss.xml",
    "https://www.finews.ch/rss",
    "https://www.moneycab.com/feed/",
    "https://www.investrends.ch/feed/",
    # === OESTERREICHISCHE MEDIEN ===
    "https://www.diepresse.com/rss/wirtschaft",
    "https://www.derstandard.at/rss/wirtschaft",
    "https://www.boersen-kurier.at/feed/",
    # === INTERNATIONALE LEITMEDIEN ===
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/companyNews",
    "https://www.ft.com/rss/home/uk",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.wsj.com/xml/rss/3_7085.xml",
    "https://www.wsj.com/xml/rss/3_7014.xml",
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://www.theguardian.com/business/rss",
    "https://fortune.com/feed/",
    # === INTERNATIONALE FACHMEDIEN (AM/PE/Institutionell) ===
    "https://www.ipe.com/rss",
    "https://www.pionline.com/rss",
    "https://www.institutionalinvestor.com/rss",
    "https://www.privateequitywire.co.uk/rss.xml",
    "https://www.privatedebtinvestor.com/feed/",
    "https://www.infrastructureinvestor.com/feed/",
    "https://www.realdeals.eu.com/feed/",
    "https://www.buyoutsnews.com/feed/",
    "https://www.preqin.com/feed",
    "https://www.hedgeweek.com/rss.xml",
    "https://www.fundssociety.com/en/rss",
    "https://www.etfstream.com/feed/",
    "https://www.ignites.com/rss",
    "https://citywire.com/rss",
    # === KRYPTO / DIGITAL ASSETS ===
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://www.theblock.co/rss.xml",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
    # === ROHSTOFFE / ENERGIE ===
    "https://oilprice.com/rss/main",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/oil",
    # === ESG / NACHHALTIGKEIT ===
    "https://www.responsible-investor.com/feed/",
    "https://www.esgtoday.com/feed/",
    # === NOTENBANKEN / INSTITUTIONEN ===
    "https://www.ecb.europa.eu/rss/press.html",
    "https://www.bis.org/doclist/bis_fsi_publs.rss",
]

GOOGLE_NEWS_FEEDS = [
    # --- THEMATISCHE SUCHEN DEUTSCH ---
    "https://news.google.com/rss/search?q=Finanzm%C3%A4rkte+Kapitalm%C3%A4rkte+aktuell&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=DAX+B%C3%B6rse+heute&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=EZB+Fed+Zinsen+Inflation&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%C3%96lpreis+Energie+Nahost+Iran&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Asset+Management+Fonds+ETF&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Private+Credit+Private+Debt&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Private+Equity+Private+Markets+Buyout&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Immobilien+Gewerbeimmobilien+REIT&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Bitcoin+Krypto+Tokenisierung+MiCA&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Bitcoin+Suisse%22+Krypto+Deutschland&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=ESG+Sustainable+Finance+Regulierung&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Emerging+Markets+Schwellenl%C3%A4nder&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Geopolitik+Handelspolitik+Z%C3%B6lle+Sanktionen&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Anleihen+Staatsanleihen+Rendite+Spread&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Gold+Rohstoffe+Kupfer+Silber&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Infrastruktur+Investitionen+Deutschland&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Versicherung+Pensionsfonds+institutionelle+Anleger&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=Mikrofinanz+Impact+Investing+Nachhaltigkeit&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=IPO+B%C3%B6rsengang+%C3%9Cbernahme+M%26A&hl=de&gl=DE&ceid=DE:de",
    # --- THEMATISCHE SUCHEN ENGLISCH ---
    "https://news.google.com/rss/search?q=PIMCO+OR+PGIM+OR+%22Franklin+Templeton%22+OR+%22T+Rowe+Price%22+OR+Eurizon+OR+Temasek&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=oil+price+Iran+energy+markets+today&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=gold+price+bonds+yields+fed+ecb&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=private+credit+BCRED+BlackRock+withdrawal&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22private+equity%22+%22private+markets%22+fundraising+buyout&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Bitcoin+Suisse%22+OR+%22crypto+regulation%22+MiCA&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Temasek+investments+Asia&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=KKR+private+equity+infrastructure+credit&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=emerging+markets+India+rupee+China&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=real+estate+REIT+commercial+property&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=ESG+sustainable+finance+green+bonds&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=stagflation+recession+central+banks&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=ETF+flows+active+management+asset+management&hl=en&gl=US&ceid=US:en",
]

THEMENFELDER = [
    "Makro/Konjunktur (BIP, PMI, ifo, ZEW)",
    "Geopolitik (Nahost/Iran, Ukraine, Zölle, Handelskrieg)",
    "Energie/Rohstoffe (Öl, Gas, Gold, Kupfer)",
    "Zentralbanken (EZB, Fed, BoE, Zinsen, Inflation)",
    "Aktien-/Anleihemärkte (DAX, S&P, Renditen, Spreads)",
    "FX/Devisen, Private Credit, Private Equity/Private Markets, Emerging Markets",
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
    """Fetch current headlines from direct media RSS feeds + Google News RSS."""
    headlines = []
    all_feeds = MEDIA_RSS_FEEDS + GOOGLE_NEWS_FEEDS
    successful_feeds = 0
    failed_feeds = 0
    
    for feed_url in all_feeds:
        try:
            req = urllib.request.Request(feed_url, headers={
                "User-Agent": "TE-Media-Intelligence-Agent/2.0 (Financial PR Research)",
                "Accept": "application/rss+xml, application/xml, text/xml"
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            feed_items = 0
            for item in root.findall(".//item")[:6]:  # Max 6 per feed
                title = item.findtext("title", "")
                source = item.findtext("source", "")
                pub_date = item.findtext("pubDate", "")
                link = item.findtext("link", "")
                if not source:
                    # Extract source from feed URL
                    try:
                        source = feed_url.split("//")[1].split("/")[0].replace("www.", "").split(".")[0].capitalize()
                    except:
                        source = "Unknown"
                if title and len(title) > 10:
                    headlines.append(f"- [{source}] {title} ({pub_date[:22] if pub_date else 'kein Datum'})")
                    feed_items += 1
            if feed_items > 0:
                successful_feeds += 1
        except Exception as e:
            failed_feeds += 1
            continue
    
    print(f"  RSS results: {successful_feeds} feeds OK, {failed_feeds} failed, {len(headlines)} total headlines")
    
    # Deduplicate by title similarity
    seen = set()
    unique = []
    for h in headlines:
        key = h[h.find("]")+2:h.find("]")+50].lower() if "]" in h else h[:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return unique[:80]  # Max 80 headlines for broader coverage


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
- Bitcoin Suisse: Schweizer Krypto-Finanzdienstleister, MiCA/Liechtenstein-Lizenz, Markteintritt Deutschland, Custody, Staking, Handel
- KKR: Globaler Investmentmanager, Private Equity, Infrastruktur, Real Estate, Credit, DACH-Expansion

Stand: {date_str}, {time_str} CET. Durchsuche Handelsblatt, FAZ, Boersen-Zeitung, finanzen.net, Reuters, FT, Bloomberg, Fonds Professionell, Citywire, DAS INVESTMENT, NZZ, CNBC u.v.m.

WICHTIG ZUR AKTUALITAET: Es ist jetzt {time_str} Uhr CET am {date_str}. Du musst die Berichterstattung der LETZTEN 24 STUNDEN erfassen — also von gestern {time_str} Uhr bis jetzt. Aeltere Berichte nur erwaehnen, wenn sie fuer den heutigen Kontext wichtig sind. Bei jedem Fakt, jeder Zahl, jedem Kurs: nenne die Quelle und wann die Information veroeffentlicht wurde (Datum, moeglichst Uhrzeit). Wenn du nur aeltere Daten findest, sage das offen.

AKTUELLE SCHLAGZEILEN aus direkten Medien-RSS-Feeds (Handelsblatt, FAZ, SZ, WiWo, Spiegel, MM, finanzen.net, NZZ, FuW, Reuters, FT, BBC, CNBC, FoPro, DAS INVESTMENT, Citywire, Institutional Money, CoinDesk) und Google News Themensuchen — abgerufen um {time_str} CET:
{headlines_block}

Themenfelder: {', '.join(THEMENFELDER)}
{diff_instruction}
AUSGABE in 5 Schritten (beginne DIREKT mit Schritt 1, keine Einleitungs-Ueberschrift davor):

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

## Quellenverzeichnis
Liste ALLE Quellen auf, die du fuer diesen Report verwendet hast. Format pro Quelle:
- Medienname: "Artikeltitel oder Thema" (Datum/Uhrzeit falls bekannt) — URL
Sortiert nach Relevanz. Nur Quellen, die du tatsaechlich gelesen und ausgewertet hast. Keine erfundenen Links.

Regeln: Nicht halluzinieren. Quellenbasiert. Deutsch. Keine Trading-Sprache. Stattdessen: "Anschlussfaehig ueber...", "Pitch-Idee:", "Gastbeitrag-Thema:".

KRITISCHE QUALITAETSREGELN:
- AKTUALITAET: Verwende NUR Informationen aus den letzten 24 Stunden. Wenn ein Fakt aelter ist, kennzeichne ihn explizit mit dem Datum.
- QUELLEN: Nenne bei JEDEM Fakt die Quelle (Medienname + Datum). Bei Kursen/Zahlen immer Zeitpunkt angeben.
- Schreibe NUR ueber Themen, die du durch deine Web-Recherche tatsaechlich verifiziert hast.
- Wenn du dir bei einem Fakt nicht sicher bist, schreibe es NICHT. Lieber lueckenhaft als falsch.
- Wenn du fuer einen Kunden keine anschlussfaehige Positionierung findest, schreibe das offen.
- Erfinde KEINE Zitate, KEINE Kurse, KEINE Termine, KEINE URLs. Nur was du gefunden hast.
- Das Quellenverzeichnis am Ende muss ALLE verwendeten Quellen mit echten URLs enthalten.
"""


def api_call_with_retry(func, max_retries=5, initial_wait=60):
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
    
    # Step 1: Fetch RSS feeds from direct media outlets + Google News
    rss_fetch_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%H:%M")
    print(f"[{rss_fetch_time} CET] Fetching RSS feeds: {len(MEDIA_RSS_FEEDS)} direct media + {len(GOOGLE_NEWS_FEEDS)} Google News = {len(MEDIA_RSS_FEEDS)+len(GOOGLE_NEWS_FEEDS)} total feeds...")
    rss_headlines = fetch_google_news_headlines()
    print(f"[{rss_fetch_time} CET] Collected {len(rss_headlines)} unique headlines")
    
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
                # Check if previous section was empty, remove it
                if body_html.endswith('<div class="section-body">'):
                    body_html = body_html[:body_html.rfind('<details')]
                    section_count -= 1
                else:
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
                if body_html.endswith('<div class="section-body">'):
                    body_html = body_html[:body_html.rfind('<details')]
                    section_count -= 1
                else:
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
            item = re.sub(r'(https?://[^\s<>"\')\]]+)', r'<a href="\1" target="_blank">\1</a>', item)
            body_html += f'<div class="list-item"><span class="bullet">&#9679;</span>{item}</div>'
        else:
            # Handle inline markers
            p_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            # Auto-link URLs
            p_html = re.sub(r'(https?://[^\s<>"\')\]]+)', r'<a href="\1" target="_blank">\1</a>', p_html)
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
  p a {{ color: #002a3e; text-decoration: underline; }}
  p a:hover {{ color: #0066aa; }}
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
  <div style="font-size:11px;color:#9ca3af;margin-top:4px;">Datenstand: {len(MEDIA_RSS_FEEDS)} Medien-RSS + {len(GOOGLE_NEWS_FEEDS)} Google News Feeds abgerufen um {time_str} CET | Web-Recherche via Claude Sonnet | Letzte 24h erfasst</div>
  <div class="badges">
    <span class="badge">PGIM</span>
    <span class="badge">T. Rowe Price</span>
    <span class="badge">MK Global Kapital</span>
    <span class="badge">Franklin Templeton</span>
    <span class="badge">PIMCO</span>
    <span class="badge">Eurizon</span>
    <span class="badge">Temasek</span>
    <span class="badge">Bitcoin Suisse</span>
    <span class="badge">KKR</span>
  </div>
</div>

{diff_banner}

<div class="controls">
  <button onclick="document.querySelectorAll('details.section').forEach(d=>d.open=true)">Alle offnen</button>
  <button onclick="document.querySelectorAll('details.section').forEach(d=>d.open=false)">Alle schliessen</button>
</div>

{body_html}

<div class="footer">
  <strong>Methodik:</strong> Automatisierte Recherche via Anthropic Claude Sonnet API mit Web Search + Google News RSS-Feeds uber alle relevanten deutsch- und englischsprachigen Finanz-, Wirtschafts- und Branchenmedien. 
  Systematische Abdeckung von 8+ Themenfeldern. Vergleich mit Vortagesreport fur Delta-Kennzeichnung.<br><br>
  <strong>Qualitaetshinweis:</strong> Dieser Report wird automatisiert erstellt. Die Fakten basieren auf Web-Recherche und Google News zum Erstellungszeitpunkt. Trotz Anti-Halluzinations-Massnahmen koennen einzelne Angaben unvollstaendig oder veraltet sein. Kurse und Zahlen sollten vor der Verwendung in Kundenkommunikation gegen eine zweite Quelle geprueft werden. Der Report ersetzt keine eigene Recherche, sondern dient als strukturierte Ausgangsbasis fuer den Arbeitstag.<br><br>
  <strong>Quellen:</strong> Reuters, Handelsblatt, FAZ, FT, Bloomberg, IEA, ZDF, Borsen-Zeitung, SZ, WiWo, Spiegel, MM, FoPro, Citywire, DAS INVESTMENT, finanzen.net, IPE, NZZ, FuW, CoinDesk, CBRE, Cushman &amp; Wakefield, Morningstar, dpa-AFX u.v.m.<br><br>
  <strong>TE Communications GmbH</strong> | Frankfurt &middot; Zurich &middot; St. Gallen &middot; Lausanne
</div>

</body>
</html>'''


if __name__ == "__main__":
    run_briefing()
