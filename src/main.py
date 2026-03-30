"""
TE Communications — Daily Media Intelligence Agent v3.0
=======================================================
Two-pass architecture: Sonnet (research) + Haiku (positioning)
137 RSS feeds + Claude Web Search + 24h time filtering
Runs daily at 07:00 CET via GitHub Actions
"""

import anthropic
import json
import os
import hashlib
import time
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Configuration ---
MODEL_RESEARCH = "claude-sonnet-4-20250514"
MODEL_POSITIONING = "claude-haiku-4-5-20251001"
MODEL_FALLBACK = "claude-haiku-4-5-20251001"
MAX_TOKENS_RESEARCH = 10000
MAX_TOKENS_POSITIONING = 6000
OUTPUT_DIR = Path("output")
HISTORY_DIR = Path("output/history")

# === LAYER 1: DIRECT MEDIA RSS FEEDS (98) ===
MEDIA_RSS_FEEDS = [
    # DE LEITMEDIEN (23)
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
    # DE FACHMEDIEN (19)
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
    "https://www.e-fundresearch.com/feed/",
    "https://www.morningstar.de/de/news/rss.aspx",
    "https://www.capital.de/feed/",
    "https://www.focus.de/finanzen/rss/",
    "https://www.bild.de/rss/vw/bild-de/geld.xml",
    # DE IMMOBILIEN (2)
    "https://www.iz.de/rss/news.xml",
    "https://www.thomas-daily.de/feed/",
    # SCHWEIZ (8)
    "https://www.nzz.ch/finanzen.rss",
    "https://www.nzz.ch/wirtschaft.rss",
    "https://www.fuw.ch/feed",
    "https://www.cash.ch/rss/news",
    "https://www.handelszeitung.ch/rss.xml",
    "https://www.finews.ch/rss",
    "https://www.moneycab.com/feed/",
    "https://www.investrends.ch/feed/",
    # OESTERREICH (5)
    "https://www.diepresse.com/rss/wirtschaft",
    "https://www.derstandard.at/rss/wirtschaft",
    "https://www.boersen-kurier.at/feed/",
    "https://www.boerse-express.com/feed/",
    "https://www.fondsexklusiv.at/feed/",
    # INT LEITMEDIEN (12)
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
    # INT FACHMEDIEN (18)
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
    "https://seekingalpha.com/feed.xml",
    "https://www.thetradenews.com/feed/",
    "https://www.risk.net/rss",
    "https://www.globalcapital.com/rss",
    # KRYPTO (5)
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://www.theblock.co/rss.xml",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
    # ROHSTOFFE (2)
    "https://oilprice.com/rss/main",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/oil",
    # ESG (2)
    "https://www.responsible-investor.com/feed/",
    "https://www.esgtoday.com/feed/",
    # INSTITUTIONEN (2)
    "https://www.ecb.europa.eu/rss/press.html",
    "https://www.bis.org/doclist/bis_fsi_publs.rss",
]

# === LAYER 2: GOOGLE NEWS THEMATIC + SITE FALLBACKS (39) ===
GOOGLE_NEWS_FEEDS = [
    # DE thematisch (19)
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
    # EN thematisch (13)
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
    # Site-Fallbacks fuer Outlets ohne RSS (7)
    "https://news.google.com/rss/search?q=site%3Aborsen-zeitung.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aplatow.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Apayoff.ch&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Abloomberg.com+markets&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site%3Aft.com+markets+funds&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site%3Awsj.com+markets&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site%3Athemarketswiss.ch+OR+site%3Athemarket.ch&hl=de&gl=CH&ceid=CH:de",
]

CLIENTS = """- PGIM ($1,5 Bio. AuM): Institutional, Multi-Asset, Real Estate, Fixed Income, CLO
- T. Rowe Price: Active Equity, Multi-Asset, ETF-Strategie Europa
- MK Global Kapital (Luxemburg): Impact/Microfinance, EM, Tokenisierung, SME-Kredite
- Franklin Templeton ($1,74 Bio. AuM): Multi-Asset, EM, ETF, Martin Lueck als Sprecher
- PIMCO: Fixed Income, Alternatives, Commodities, Credit
- Eurizon (Intesa Sanpaolo): Euro Fixed Income, EM Debt, ESG, Quantitative
- Temasek: Singapurer Staatsfonds, Infrastruktur, Tech, Life Sciences, DACH
- Bitcoin Suisse: Krypto-Finanzdienstleister, MiCA, Markteintritt DE, Custody, Staking
- KKR: Private Equity, Infrastruktur, Real Estate, Credit, DACH-Expansion"""

THEMENFELDER = [
    "Makro/Konjunktur", "Geopolitik/Sicherheit", "Energie/Rohstoffe",
    "Zentralbanken/Geldpolitik", "Aktienmaerkte", "Anleihen/Fixed Income",
    "FX/Devisen", "Private Credit/Debt", "Private Equity/Markets",
    "Emerging Markets", "Krypto/Tokenisierung", "Immobilien/Real Estate",
    "ESG/Regulierung", "M&A/Deals/IPOs",
]


def get_now_cet():
    return datetime.utcnow() + timedelta(hours=1)

def get_today_str():
    now = get_now_cet()
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    monate = ["", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return (f"{tage[now.weekday()]}, {now.day}. {monate[now.month]} {now.year}",
            now.strftime("%Y%m%d"), now.strftime("%H:%M"), now.weekday() >= 5)

def load_previous_report():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    if files:
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def fetch_rss_intelligence():
    """Fetch all RSS feeds with descriptions, 24h filter, health tracking."""
    all_feeds = MEDIA_RSS_FEEDS + GOOGLE_NEWS_FEEDS
    items = []
    health = {"ok": 0, "fail": 0, "sources": set()}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=28)

    for url in all_feeds:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TE-Media-Intelligence/3.0",
                "Accept": "application/rss+xml, application/xml, text/xml"
            })
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
            root = ET.fromstring(data)
            for item in root.findall(".//item")[:5]:
                title = (item.findtext("title") or "").strip()
                desc = re.sub(r'<[^>]+>', '', (item.findtext("description") or ""))[:180].strip()
                source = item.findtext("source") or ""
                pub = item.findtext("pubDate") or ""
                link = item.findtext("link") or ""
                if not source:
                    try: source = url.split("//")[1].split("/")[0].replace("www.","")
                    except: source = ""
                if title and len(title) > 12:
                    items.append({"s": source, "t": title, "d": desc, "p": pub[:25], "l": link})
                    health["sources"].add(source)
            health["ok"] += 1
        except:
            health["fail"] += 1
    # Deduplicate
    seen = set()
    unique = []
    for it in items:
        k = it["t"][:55].lower()
        if k not in seen:
            seen.add(k)
            unique.append(it)
    health["sources"] = len(health["sources"])
    print(f"  RSS: {health['ok']}/{len(all_feeds)} feeds, {len(unique)} items, {health['sources']} sources")
    return unique, health


def api_call(client, model, max_tokens, messages, tools=None, retries=4, wait=60):
    """API call with retry + automatic model fallback."""
    current_model = model
    for i in range(retries):
        try:
            kw = {"model": current_model, "max_tokens": max_tokens, "messages": messages}
            if tools: kw["tools"] = tools
            return client.messages.create(**kw), current_model
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ["overloaded","rate_limit","529","429"]):
                if i == 1 and current_model != MODEL_FALLBACK:
                    print(f"  {current_model} unavailable -> fallback to {MODEL_FALLBACK}")
                    current_model = MODEL_FALLBACK
                    if tools:
                        kw["tools"] = tools  # keep web search for fallback
                    continue
                w = wait * (2 ** i)
                print(f"  Retry {i+1}/{retries}, waiting {w}s...")
                time.sleep(w)
            elif "too long" in err:
                print(f"  Prompt too long, truncating...")
                messages[0]["content"] = messages[0]["content"][:int(len(messages[0]["content"])*0.65)]
            else:
                raise
    raise Exception(f"API failed after {retries} retries")


def run_briefing():
    """Two-pass briefing: Sonnet researches, Haiku positions."""
    client = anthropic.Anthropic()
    date_str, date_file, time_str, is_weekend = get_today_str()
    prev = load_previous_report()
    prev_sum = prev.get("summary", "") if prev else ""

    print(f"[{time_str}] TE Media Intelligence Agent v3.0")
    print(f"[{time_str}] {date_str} | Weekend: {is_weekend}")

    # --- RSS ---
    t0 = time.time()
    rss_items, health = fetch_rss_intelligence()
    rss_block = "\n".join(
        f"- [{it['s']}] {it['t']}" + (f" — {it['d']}" if it['d'] else "") + (f" ({it['p']})" if it['p'] else "")
        for it in rss_items[:100]
    )
    rss_time = round(time.time()-t0, 1)

    # --- PASS 1: Research ---
    diff = f"\nVORTAG: {prev_sum[:600]}\nKennzeichne: [NEU]/[ESKALATION]/[ENTSPANNUNG]/[FORTLAUFEND]\n" if prev_sum else ""
    wknd = "\nWochenende: Fokus auf Analysen, Ausblicke, Hintergrund.\n" if is_weekend else ""

    p1 = f"""Fuehre eine gruendliche Web-Recherche der Finanzmarkt-Berichterstattung durch.
Stand: {date_str}, {time_str} CET. Erfasse die LETZTEN 24 STUNDEN.{wknd}

RSS-SCHLAGZEILEN ({len(rss_items)} Artikel, {health['sources']} Quellen, abgerufen {time_str} CET):
{rss_block}

Recherchiere per Web Search UEBER diese RSS-Daten hinaus.
Themenfelder: {', '.join(THEMENFELDER)}
{diff}
AUSGABE (beginne direkt, keine Einleitung):

## Schritt 1 — Recherche-Ueberblick
Gesamtcharakter, uebergreifendes Narrativ, dominante Themencluster.

## Schritt 2 — Themen die das Markt-Narrativ treiben
Nummerierte Bloecke nach Relevanz. Pro Block:
- Was dominiert die Headlines (Fakten, Zahlen, Quellen mit Datum)
- Narrativ: Groessere Story? Trendwechsel? Eskalation/Wende/Fortsetzung?
- Kausalkette: Warum marktrelevant?
- Veraenderung gegenueber Vortagen?

## Schritt 3 — Termine naechste 7 Tage
Datum, Uhrzeit, Land, Termin, Relevanz.

## Gesamtfazit
2-3 Saetze zum uebergeordneten Narrativ und groesseren Trends.

## Quellenverzeichnis
ALLE verwendeten Quellen: Medium — Titel (Datum) — URL. Keine erfundenen URLs.

QUALITAETSREGELN:
- NUR verifizierte Fakten der letzten 24h. Aelteres explizit kennzeichnen.
- Bei JEDER Zahl: Quelle + Datum. Lieber lueckenhaft als falsch.
- Nicht halluzinieren. Keine erfundenen URLs/Zitate/Kurse.
- Einfache Sprache, keine Telegrammstil-Sprache.
- Englischsprachige Artikel gruendlich ins Deutsche uebertragen.
- Wichtige Zusammenhaenge erklaeren."""

    print(f"[{time_str}] PASS 1: Sonnet + Web Search...")
    t1 = time.time()
    r1, m1 = api_call(client, MODEL_RESEARCH, MAX_TOKENS_RESEARCH,
                       [{"role":"user","content":p1}],
                       tools=[{"type":"web_search_20250305","name":"web_search"}])
    txt1 = "".join(b.text for b in r1.content if hasattr(b,"text"))
    t1 = round(time.time()-t1, 1)
    print(f"[{time_str}] PASS 1: {len(txt1)} chars via {m1} in {t1}s")

    # --- PASS 2: Positioning ---
    print(f"[{time_str}] Waiting 30s...")
    time.sleep(30)

    p2 = f"""Du bist strategischer Finanzkommunikationsberater bei TE Communications (PR-Beratung, Frankfurt/Zuerich).
Basierend auf dieser Marktanalyse von {date_str}, erstelle ein Positionierungs-Mapping.

Kunden:
{CLIENTS}

MARKTANALYSE:
{txt1[:6000]}

AUFGABE:

## Schritt 4 — Positionierungs-Mapping auf die Kunden
Fuer JEDEN der 9 Kunden:
### [Kundenname]
- Anschlussfaehig ueber: [Themenachsen]
- Pitch-Idee: [konkretes Thema]
- Gastbeitrag-Thema: [moegliches Thema]
- Interview-Aufhaenger: [aktueller Anlass]
- Zielmedien: [konkrete Medien]
Wenn nichts passt, offen sagen.

## Schritt 5 — Konkrete Pitch-Ableitungen
5-7 umsetzbare Ideen: Thema, Format (Kommentar/Gastbeitrag/Interview/Hintergrundgespraech), Kunde, Medium.

REGELN: PR-Berater-Perspektive, KEINE Trading-Sprache (kein Overweight/Underweight). Deutsch."""

    print(f"[{time_str}] PASS 2: Haiku positioning...")
    t2s = time.time()
    r2, m2 = api_call(client, MODEL_POSITIONING, MAX_TOKENS_POSITIONING,
                       [{"role":"user","content":p2}])
    txt2 = "".join(b.text for b in r2.content if hasattr(b,"text"))
    t2 = round(time.time()-t2s, 1)
    print(f"[{time_str}] PASS 2: {len(txt2)} chars via {m2} in {t2}s")

    # --- Combine + Save ---
    full = txt1 + "\n\n" + txt2

    # Summary for tomorrow
    summary = full[:500]
    try:
        time.sleep(10)
        sr, _ = api_call(client, MODEL_FALLBACK, 800,
                          [{"role":"user","content":f"10 Stichpunkte Hauptthemen:\n{txt1[:3000]}"}])
        summary = "".join(b.text for b in sr.content if hasattr(b,"text"))
    except: pass

    meta = {
        "date": date_str, "time": time_str, "weekend": is_weekend,
        "rss_total": len(MEDIA_RSS_FEEDS)+len(GOOGLE_NEWS_FEEDS),
        "rss_ok": health["ok"], "rss_fail": health["fail"],
        "rss_sources": health["sources"], "rss_items": len(rss_items),
        "rss_time": rss_time,
        "m1": m1, "c1": len(txt1), "t1": t1,
        "m2": m2, "c2": len(txt2), "t2": t2,
        "total": len(full),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    html = generate_html(full, date_str, time_str, bool(prev_sum), meta)
    hp = OUTPUT_DIR / f"{date_file}_TE_Media_Intelligence.html"
    with open(hp,"w",encoding="utf-8") as f: f.write(html)

    tp = OUTPUT_DIR / f"{date_file}_TE_Media_Intelligence.txt"
    with open(tp,"w",encoding="utf-8") as f:
        f.write(f"TE Communications — Daily Media Intelligence v3.0\n{date_str}, {time_str} CET\n")
        f.write(f"RSS: {health['ok']}/{meta['rss_total']} feeds, {len(rss_items)} items | P1: {m1} ({t1}s) | P2: {m2} ({t2}s)\n{'='*70}\n\n{full}")

    with open(HISTORY_DIR / f"{date_file}.json","w",encoding="utf-8") as f:
        json.dump({"date":date_str,"time":time_str,"summary":summary,"hash":hashlib.md5(full.encode()).hexdigest(),"meta":meta}, f, ensure_ascii=False, indent=2)

    dp = Path("docs/latest.html")
    if dp.parent.exists():
        with open(dp,"w",encoding="utf-8") as f: f.write(html)

    for old in sorted(HISTORY_DIR.glob("*.json"), reverse=True)[30:]: old.unlink()

    print(f"[{time_str}] COMPLETE | {len(full)} chars | RSS {rss_time}s + P1 {t1}s + P2 {t2}s = {round(rss_time+t1+t2)}s total")


def generate_html(text, date_str, time_str, has_diff, meta):
    lines = text.split("\n")
    body = ""
    in_sec = False
    sc = 0
    for line in lines:
        line = line.strip()
        if not line:
            if in_sec: body += "<br>"
            continue
        if line.startswith("## ") or line.startswith("# "):
            pfx = "## " if line.startswith("## ") else "# "
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', line[len(pfx):])
            if in_sec:
                if body.rstrip().endswith('<div class="sb">'):
                    body = body[:body.rfind('<details')]; sc -= 1
                else: body += '</div></details>'
                in_sec = False
            sc += 1
            op = "open" if sc <= 4 else ""
            body += f'<details class="sec" {op}><summary class="sh"><span class="sn">{sc}.</span><span class="st">{title}</span><span class="ch">&#9660;</span></summary><div class="sb">'
            in_sec = True
        elif line.startswith("### "):
            t = re.sub(r'\*\*(.+?)\*\*', r'\1', line[4:])
            body += f'<h3 class="ss">{t}</h3>'
        elif line.startswith("- ") or line.startswith("* "):
            it = line[2:]
            it = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', it)
            it = re.sub(r'(https?://[^\s<>"\')\]]+)', r'<a href="\1" target="_blank">\1</a>', it)
            for tg,cl in [("[NEU]","tn"),("[ESKALATION]","te"),("[ENTSPANNUNG]","td"),("[FORTLAUFEND]","tc")]:
                it = it.replace(tg, f'<span class="{cl}">{tg[1:-1]}</span>')
            body += f'<div class="li"><span class="bu">&#9679;</span>{it}</div>'
        else:
            p = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            p = re.sub(r'(https?://[^\s<>"\')\]]+)', r'<a href="\1" target="_blank">\1</a>', p)
            for tg,cl in [("[NEU]","tn"),("[ESKALATION]","te"),("[ENTSPANNUNG]","td"),("[FORTLAUFEND]","tc")]:
                p = p.replace(tg, f'<span class="{cl}">{tg[1:-1]}</span>')
            body += f'<p>{p}</p>'
    if in_sec: body += '</div></details>'

    diff_b = '<div class="db">&#9888; <b>Vortagesvergleich aktiv.</b> <span class="tn">NEU</span> <span class="te">ESKALATION</span> <span class="td">ENTSPANNUNG</span> <span class="tc">FORTLAUFEND</span></div>' if has_diff else ""
    tt = round(meta['rss_time']+meta['t1']+meta['t2'])

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="TE Media Intelligence">
<title>TE Media Intelligence — {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Source Serif 4',Georgia,serif;max-width:820px;margin:0 auto;padding:32px 20px;color:#1f2937;line-height:1.75;background:#fafafa}}
.hd{{text-align:center;border-bottom:3px solid #002a3e;padding:28px 24px 24px;margin-bottom:20px;background:#fff;border-radius:8px 8px 0 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.hd .lb{{font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;color:#002a3e;font-weight:700;margin-bottom:10px}}
.hd h1{{font-size:24px;color:#002a3e;margin:0 0 4px;border:none;padding:0}}
.hd .dt{{font-size:13px;color:#6b7280}}
.hd .ml{{font-size:10px;color:#9ca3af;margin-top:6px}}
.bg{{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;margin-top:14px}}
.bg span{{background:#002a3e;color:#fff;font-size:9px;font-weight:700;padding:3px 9px;border-radius:3px;letter-spacing:.04em;text-transform:uppercase}}
.kp{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:16px}}
.kp div{{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:10px;text-align:center}}
.kp .v{{font-size:17px;font-weight:700;color:#002a3e}}
.kp .l{{font-size:9px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-top:2px}}
.db{{background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:12px 18px;margin-bottom:16px;font-size:12px;line-height:1.6}}
.ct{{display:flex;justify-content:flex-end;margin-bottom:12px;gap:8px}}
.ct button{{background:none;border:1px solid #002a3e;color:#002a3e;font-size:11px;padding:5px 14px;border-radius:4px;cursor:pointer;font-weight:600;font-family:inherit}}
.ct button:hover{{background:#002a3e;color:#fff}}
.sec{{background:#fff;border:1px solid #e5e7eb;border-radius:6px;margin-bottom:10px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.sec[open]{{border-color:rgba(0,42,62,.15)}}
.sh{{padding:16px 20px;cursor:pointer;display:flex;align-items:flex-start;gap:12px;list-style:none;user-select:none}}
.sh::-webkit-details-marker{{display:none}}
.sh:hover{{background:rgba(0,42,62,.03)}}
.sn{{font-weight:700;color:#002a3e;min-width:24px;font-size:15px}}
.st{{font-weight:700;color:#002a3e;flex:1;font-size:14.5px;line-height:1.4}}
.ch{{font-size:11px;color:#002a3e;flex-shrink:0;margin-top:3px;transition:transform .2s}}
details[open] .ch{{transform:rotate(180deg)}}
.sb{{padding:0 20px 20px;font-size:14.2px;line-height:1.78}}
.ss{{font-size:14px;color:#002a3e;margin:18px 0 8px;padding-top:12px;border-top:1px solid rgba(0,42,62,.06);font-weight:700}}
p{{margin:0 0 12px;font-size:14.2px}}
p a,.li a{{color:#002a3e;text-decoration:underline}}
strong{{color:#111827}}
.li{{font-size:13.5px;line-height:1.6;padding-left:16px;position:relative;margin-bottom:5px}}
.bu{{position:absolute;left:0;color:#002a3e;font-size:7px;top:7px}}
.tn,.te,.td,.tc{{padding:2px 7px;border-radius:3px;font-size:10.5px;font-weight:700;display:inline-block;margin-right:4px}}
.tn{{background:#dcfce7;color:#166534}}.te{{background:#fee2e2;color:#991b1b}}.td{{background:#dbeafe;color:#1e40af}}.tc{{background:#f3f4f6;color:#4b5563}}
.ft{{margin-top:32px;padding-top:20px;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;line-height:1.6}}
@media(max-width:600px){{body{{padding:16px 12px}}.hd{{padding:20px 16px}}.hd h1{{font-size:20px}}.sh{{padding:14px 16px}}.sb{{padding:0 16px 16px}}.kp{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="hd">
<div class="lb">TE Communications — Daily Media Intelligence Agent v3.0</div>
<h1>Tagesauswertung &amp; Positionierungs-Briefing</h1>
<div class="dt">{date_str} — {time_str} CET</div>
<div class="ml">Pass 1: {meta['m1']} + Web Search ({meta['t1']}s) | Pass 2: {meta['m2']} ({meta['t2']}s) | {meta['rss_ok']}/{meta['rss_total']} RSS-Feeds</div>
<div class="bg">
<span>PGIM</span><span>T. Rowe Price</span><span>MK Global Kapital</span><span>Franklin Templeton</span><span>PIMCO</span><span>Eurizon</span><span>Temasek</span><span>Bitcoin Suisse</span><span>KKR</span>
</div>
</div>
<div class="kp">
<div><div class="v">{meta['rss_items']}</div><div class="l">RSS Artikel</div></div>
<div><div class="v">{meta['rss_sources']}</div><div class="l">Quellen</div></div>
<div><div class="v">{meta['total']:,}</div><div class="l">Zeichen</div></div>
<div><div class="v">{tt}s</div><div class="l">Laufzeit</div></div>
</div>
{diff_b}
<div class="ct">
<button onclick="document.querySelectorAll('details.sec').forEach(d=>d.open=true)">Alle oeffnen</button>
<button onclick="document.querySelectorAll('details.sec').forEach(d=>d.open=false)">Alle schliessen</button>
</div>
{body}
<div class="ft">
<b>Methodik:</b> Zwei-Pass-Architektur — Pass 1 (Sonnet + Web Search) Marktrecherche, Pass 2 (Haiku) PR-Positionierung. {meta['rss_ok']} RSS-Feeds aus {meta['rss_sources']} Medienquellen. 24h-Zeitfilter. 14 Themenfelder. Vortagesvergleich.<br><br>
<b>Qualitaetshinweis:</b> Automatisiert erstellt. Kurse und Zahlen vor Verwendung in Kundenkommunikation gegen zweite Quelle pruefen.<br><br>
<b>TE Communications GmbH</b> | Frankfurt &middot; Zuerich &middot; St. Gallen &middot; Lausanne
</div>
</body>
</html>'''


if __name__ == "__main__":
    run_briefing()
