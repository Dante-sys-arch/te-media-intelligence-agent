"""
TE Communications — Daily Media Intelligence Agent v3.0
=======================================================
Two-pass architecture: Opus 4.7 (research) + Sonnet 4.6 (positioning)
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
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
# Models — using best available as of April 2026
# Opus 4.7 = most capable model publicly available (Mythos is restricted)
# Sonnet 4.6 = preferred over previous Opus 4.5 by 59% of users, 1/5 the cost of Opus
# Haiku 4.5 = fastest fallback, retains good quality
MODEL_RESEARCH = "claude-opus-4-7"
MODEL_POSITIONING = "claude-sonnet-4-6"
MODEL_FALLBACK = "claude-haiku-4-5-20251001"
MAX_TOKENS_RESEARCH = 16000  # Opus 4.7 supports up to 128k output
MAX_TOKENS_POSITIONING = 16000  # Sonnet 4.6 — detailed journalist-grade pitches
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

# === LAYER 3: PER-CLIENT MONITORING (each client's website + name searches) ===
# These feeds find: press releases, insights, commentaries, news mentions per client
CLIENT_FEEDS = [
    # PGIM
    "https://news.google.com/rss/search?q=site%3Apgim.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=PGIM+Deutschland+OR+%22PGIM+Real+Estate%22&hl=de&gl=DE&ceid=DE:de",
    # T. Rowe Price
    "https://news.google.com/rss/search?q=site%3Atroweprice.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22T.+Rowe+Price%22+Deutschland+OR+Lustig+OR+Wieladek&hl=de&gl=DE&ceid=DE:de",
    # MK Global Kapital
    "https://news.google.com/rss/search?q=%22MK+Global+Kapital%22+OR+%22Mikrofinanz%22+Luxemburg&hl=de&gl=DE&ceid=DE:de",
    # Franklin Templeton
    "https://news.google.com/rss/search?q=site%3Afranklintempleton.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site%3Afranklintempleton.de+OR+%22Franklin+Templeton%22+Deutschland&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Martin+Lück%22+OR+%22Martin+Lueck%22+Franklin&hl=de&gl=DE&ceid=DE:de",
    # PIMCO
    "https://news.google.com/rss/search?q=site%3Apimco.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Frank+Witt%22+OR+%22Konstantin+Veit%22+PIMCO&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=PIMCO+Deutschland+OR+M%C3%BCnchen+OR+Allianz&hl=de&gl=DE&ceid=DE:de",
    # Eurizon
    "https://news.google.com/rss/search?q=site%3Aeurizoncapital.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Eurizon+Deutschland+OR+Frankfurt+%22Intesa+Sanpaolo%22&hl=de&gl=DE&ceid=DE:de",
    # Temasek
    "https://news.google.com/rss/search?q=site%3Atemasek.com.sg&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Temasek+Deutschland+OR+Europa+Investment&hl=de&gl=DE&ceid=DE:de",
    # Bitcoin Suisse
    "https://news.google.com/rss/search?q=site%3Abitcoinsuisse.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Bitcoin+Suisse%22+OR+%22Dirk+Klee%22&hl=de&gl=DE&ceid=DE:de",
    # KKR
    "https://news.google.com/rss/search?q=site%3Akkr.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=KKR+Deutschland+OR+Frankfurt+%22Philipp+Freise%22&hl=de&gl=DE&ceid=DE:de",
]

# === LAYER 4: DIRECT WEBSITE CRAWLING — Insights/Press pages of each client ===
# These URLs are scraped directly to find publishable content, whitepapers, commentaries
CLIENT_INSIGHTS_URLS = {
    "PGIM": [
        "https://www.pgim.com/insights",
        "https://www.pgim.com/news",
    ],
    "T. Rowe Price": [
        "https://www.troweprice.com/personal-investing/resources/insights.html",
        "https://www.troweprice.com/corporate/en/press.html",
    ],
    "MK Global Kapital": [
        "https://www.mk-global.com/news/",
        "https://www.mk-global.com/insights/",
    ],
    "Franklin Templeton": [
        "https://www.franklintempleton.de/articles",
        "https://www.franklintempleton.com/articles",
        "https://www.franklintempleton.com/press-releases",
    ],
    "PIMCO": [
        "https://www.pimco.com/de/de/insights",
        "https://www.pimco.com/en-us/insights",
        "https://www.pimco.com/en-us/about-us/newsroom",
    ],
    "Eurizon": [
        "https://www.eurizoncapital.com/en/strategy/market-views",
        "https://www.eurizoncapital.com/en/news-events",
    ],
    "Temasek": [
        "https://www.temasek.com.sg/en/news-and-views",
        "https://www.temasek.com.sg/en/news-and-resources/news-room",
    ],
    "Bitcoin Suisse": [
        "https://www.bitcoinsuisse.com/research",
        "https://www.bitcoinsuisse.com/news",
    ],
    "KKR": [
        "https://www.kkr.com/insights",
        "https://www.kkr.com/news",
    ],
}

# === CLIENT PROFILES (FACTS ONLY, no speakers — those are researched live) ===
# These are stable facts that don't change: company structure, asset classes, history
CLIENT_PROFILES = {
    "PGIM": {
        "type": "Globaler Vermoegensverwalter, Tochter von Prudential Financial",
        "aum": "ca. $1,5 Bio.",
        "hq": "Newark, NJ",
        "dach": "Frankfurt, Muenchen, Zuerich",
        "boutiques": "PGIM Fixed Income, PGIM Real Estate, PGIM Private Capital, Jennison Associates, QMA, PGIM Quantitative Solutions",
        "core_competencies": "Fixed Income (IG/HY/EMD/CLO/Structured), Real Estate (Equity+Debt), Private Capital, Public Equities (Jennison/QMA), Multi-Asset/OCIO",
        "target_media_dach": "Handelsblatt, Boersen-Zeitung, FAZ, Fonds Professionell, Institutional Money, portfolio institutionell, dpn, Citywire, DAS INVESTMENT, IPE",
        "tone": "institutionell, analytisch, datenbasiert, eher nuechtern als zugespitzt, globale Perspektive mit DACH-Uebersetzung",
        "taboo": "keine politischen Statements, keine spekulativen Kursprognosen, keine Konkurrenzvergleiche",
    },
    "T. Rowe Price": {
        "type": "Globaler aktiver Asset Manager, gegruendet 1937",
        "aum": "ca. $1,5 Bio.",
        "hq": "Baltimore, MD",
        "dach": "Frankfurt, Zuerich",
        "boutiques": "Active Equity, Multi-Asset, Fixed Income, ETF-Strategie Europa (relativ neu)",
        "core_competencies": "Active Equity (US/Global/EM/Growth-Schwerpunkt), Multi-Asset/Target Date Funds, Fixed Income, Aktive ETFs (neu in Europa)",
        "target_media_dach": "Handelsblatt, Fonds Professionell, DAS INVESTMENT, Citywire, Boersen-Zeitung, FAZ, ETF Stream, justETF",
        "tone": "investment-orientiert, meinungsstark, Storytelling ueber Einzeltitel, laengere Hintergrundinterviews willkommen",
        "taboo": "keine konkreten Kauf-/Verkaufsempfehlungen, keine politischen Stellungnahmen",
    },
    "MK Global Kapital": {
        "type": "Spezialist fuer Impact Investing und Mikrofinanz",
        "aum": "Spezialist (kleinere Plattform)",
        "hq": "Luxemburg",
        "dach": "Luxemburg, DACH-Vertrieb",
        "boutiques": "Mikrofinanz, SME-Kredite EM, Impact, Tokenisierung, ESG/SDG-Alignment",
        "core_competencies": "Mikrofinanz (Kreditvergabe an MFIs), SME-Kredite Schwellenlaender, Impact Investing, Tokenisierung von Privatmarkt-Investments, ESG/SDG-Alignment",
        "target_media_dach": "Fonds Professionell, DAS INVESTMENT, private banking magazin, altii, Institutional Money, Responsible Investor, ESG Today, finews, NZZ, FuW",
        "tone": "werteorientiert ohne moralisierend, verbindet Impact-Narrativ mit klarer finanzieller Logik, Storytelling ueber Wirkungsbeispiele",
        "taboo": "keine Greenwashing-Vorwuerfe gegen andere Haeuser, keine politischen Statements zu Konfliktregionen",
    },
    "Franklin Templeton": {
        "type": "Globaler Vermoegensverwalter, gegruendet 1947",
        "aum": "ca. $1,74 Bio.",
        "hq": "San Mateo, CA",
        "dach": "Frankfurt, Zuerich, Wien",
        "boutiques": "Templeton (Value/Global), Franklin Equity, ClearBridge, Brandywine, Western Asset, Royce, Martin Currie, Lexington Partners (Secondaries), Benefit Street Partners (Private Credit), Clarion Partners (Real Estate)",
        "core_competencies": "Multi-Asset, Emerging Markets, Fixed Income (Western Asset, Brandywine), ETF-Plattform, Private Markets (Lexington), Tokenisierung (BENJI Money Market Fund auf Blockchain)",
        "target_media_dach": "Handelsblatt, FAZ, Boersen-Zeitung, Fonds Professionell, DAS INVESTMENT, Citywire, Institutional Money, ETF Stream, BTC-Echo (Tokenisierung), FuW, NZZ",
        "tone": "globale Perspektive, klare Botschaften; Tokenisierung-Vorreiterrolle; geeignet fuer TV/Online-Video und Print",
        "taboo": "keine US-parteipolitischen Statements, vorsichtig bei China-Themen, Lexington-Themen separat von Liquid-Markets-Kommunikation",
    },
    "PIMCO": {
        "type": "Globaler Fixed-Income-Spezialist, gegruendet 1971, Allianz-Tochter seit 2000",
        "aum": "ca. $2 Bio.",
        "hq": "Newport Beach, CA",
        "dach": "Muenchen (Allianz-Zentrale), Frankfurt, Zuerich",
        "boutiques": "Fixed Income (Kernkompetenz), Multi-Asset/Alternatives, Private Credit/Direct Lending, Real Estate (CRE Debt+Equity), Commodities, Sustainable Investing",
        "core_competencies": "Fixed Income (Government/Credit/HY/EMD/Securitized), Multi-Asset, Private Credit (wachsendes Segment), CRE, Commodities (eigene Plattform), ESG-Integration in Bonds",
        "target_media_dach": "Handelsblatt, FAZ, Boersen-Zeitung, Fonds Professionell, Institutional Money, Anleihencheck, BondGuide, Risk.net, Reuters, Bloomberg, FT (Bond-Marktfuehrer), NZZ, FuW, n-tv Teleboerse",
        "tone": "akademisch, bond-mathematisch fundiert, globale Top-Tier-Glaubwuerdigkeit, eher zurueckhaltend, Standardformat: Cyclical Outlook (quartalsweise), Secular Outlook (jaehrlich), Asset Allocation Outlook",
        "taboo": "keine politischen Statements zu Wahlen, Allianz-Konzernthemen separat halten, keine konkreten Trades oeffentlich kommentieren",
    },
    "Eurizon": {
        "type": "Asset-Management-Tochter der Intesa Sanpaolo Gruppe (Italiens groesste Bank)",
        "aum": "ca. EUR 440 Mrd.",
        "hq": "Mailand",
        "dach": "Frankfurt, Wien, Zuerich",
        "boutiques": "Euro Fixed Income (Schwerpunkt), Emerging Markets Debt, Multi-Asset/Income, Quantitative Strategien, ESG/Sustainable, Real Assets",
        "core_competencies": "Euro Fixed Income (Staaten/Corporates/Credit), Emerging Markets Debt (Hartwaehrung+Lokal), Multi-Asset, Quant/Smart Beta/Factor, ESG (italienische ESG-Tradition)",
        "target_media_dach": "Fonds Professionell, DAS INVESTMENT, Citywire, Institutional Money, Handelsblatt, Boersen-Zeitung, FAZ (Italien-Bezug), Responsible Investor, FuW",
        "tone": "europaeisch-institutionell, akademisch fundiert ohne uebertriebene Zuspitzung, gute Bruecken zur italienischen Marktperspektive",
        "taboo": "Italien-politische Themen vorsichtig, Bankensektor-Themen sehr vorsichtig (Konzernbezug), US-Themen sind nicht Eurizons Staerke",
    },
    "Temasek": {
        "type": "Singapurer Staatsfonds, gegruendet 1974",
        "aum": "ca. SGD 430 Mrd.",
        "hq": "Singapur",
        "dach": "London-Hub deckt Europa ab, vereinzelte direkte Investments in DACH",
        "boutiques": "Eigentuemer-Investor (nicht Asset Manager), direkte Beteiligungen",
        "core_competencies": "Long-Term Investment (20-Jahres-Renditen), direkte Beteiligungen (Banken/Telecom/Tech/Konsumgueter/Infrastruktur), Sektoren: FSI/TMT/Transportation/Consumer-RE/Life Sciences-Agri, Asia-Fokus (~60%) aber global, Sustainability (Net-Zero 2050)",
        "target_media_dach": "Handelsblatt, FAZ, Boersen-Zeitung (selten, bei konkreten Investments), FT, Reuters, Bloomberg, Nikkei Asia (haeufiger), branchenspezifische Wirtschaftsmedien bei DACH-Investments",
        "tone": "sehr zurueckhaltend, staatsmaennisch, selten direkte Marktkommentare, bevorzugt Whitepaper/Annual Reports/ausgewaehlte Top-Tier-Interviews",
        "taboo": "politische Themen (Singapur-Regierung-Bezug), konkrete Spekulation ueber Einzelinvestments, China-USA-Spannungen sehr vorsichtig, keine Konkurrenz-Kommentierung",
    },
    "Bitcoin Suisse": {
        "type": "Schweizer Krypto-Finanzdienstleister, gegruendet 2013 (einer der aeltesten)",
        "aum": "Spezialist (Custody/Trading/Staking)",
        "hq": "Zug (Crypto Valley)",
        "dach": "Zug, Liechtenstein, Markteintritt Deutschland (BaFin-Prozess)",
        "boutiques": "Custody, Trading/Brokerage (OTC), Staking (institutionell), Lending/Borrowing, Krypto-Bonds/strukturierte Produkte, Tokenisierung",
        "core_competencies": "institutionelle Krypto-Verwahrung, OTC-Handel grosse Tickets, institutionelles Staking (Ethereum/Cosmos), Lending gegen Krypto-Sicherheiten, Tokenisierung Real World Assets",
        "target_media_dach": "finews, NZZ, FuW, Cash, Handelszeitung, BTC-Echo, CoinDesk DE, finews crypto, Kryptokompass, Handelsblatt (Tech/Krypto), FAZ Wirtschaft, Manager Magazin, Boersen-Zeitung (MiCA/Regulierung), Risk.net",
        "tone": "institutionell, ruhig, kompetent (TradFi-Bruecke), bewusste Abgrenzung von Krypto-Hype und Bitcoin-Maximalismus, TradFi-Sprache statt Krypto-Jargon",
        "taboo": "keine Kursprognosen einzelner Coins, keine Empfehlungen einzelner Tokens, vorsichtig bei Stablecoin-Risiken, Konkurrenz nicht kommentieren, Krypto-Kriminalitaet nur sehr nuanciert",
    },
    "KKR": {
        "type": "Globaler Investmentmanager (Alternatives), gegruendet 1976, Co-CEOs Joseph Bae und Scott Nuttall, NYSE-notiert",
        "aum": "ca. $640 Mrd.",
        "hq": "New York",
        "dach": "Frankfurt, Muenchen, Zuerich",
        "boutiques": "Private Equity (Buyouts/Growth/Core), Infrastructure, Real Estate (Equity+Credit), Credit/Private Credit (Direct Lending/Junior Capital/Special Situations), Capital Markets, Insurance Solutions (Global Atlantic)",
        "core_competencies": "Private Equity (Buyouts/Growth), Infrastructure (Energy Transition), Real Estate (Wohnen/Logistik/Datenzentren), Private Credit, Insurance Asset Management",
        "target_media_dach": "Handelsblatt, FAZ, Boersen-Zeitung, Manager Magazin, WiWo, FINANCE Magazin, Going Public, Private Equity Magazin, Reuters, FT, Bloomberg, WSJ, PEI, Buyouts, FuW, NZZ",
        "tone": "selbstbewusst, marktfuehrend, pitch-orientiert (KKR investiert massiv in Markenbildung), ungezwungener als Asset-Manager-Haeuser (Eigeninvestor)",
        "taboo": "konkrete Deal-Spekulationen vor Abschluss vermeiden, Carry-/Verguetungsdebatten heikel, Heuschrecken-Narrativ vorsichtig adressieren, politische Statements vermeiden, Konkurrenz nicht direkt kommentieren",
    },
}

CLIENTS = """- PGIM ($1,5 Bio. AuM): Institutional, Multi-Asset, Real Estate, Fixed Income, CLO
- T. Rowe Price: Active Equity, Multi-Asset, ETF-Strategie Europa
- MK Global Kapital (Luxemburg): Impact/Microfinance, EM, Tokenisierung, SME-Kredite
- Franklin Templeton ($1,74 Bio. AuM): Multi-Asset, EM, ETF, Tokenisierung
- PIMCO: Fixed Income, Alternatives, Commodities, Credit (Allianz-Tochter)
- Eurizon (Intesa Sanpaolo): Euro Fixed Income, EM Debt, ESG, Quantitative
- Temasek: Singapurer Staatsfonds, Infrastruktur, Tech, Life Sciences
- Bitcoin Suisse: Krypto-Finanzdienstleister, MiCA, Custody, Staking
- KKR: Private Equity, Infrastruktur, Real Estate, Credit"""

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


CLIENT_KEYWORDS = {
    "PGIM": ["pgim", "prudential financial"],
    "T. Rowe Price": ["t. rowe price", "t rowe price", "trowe price"],
    "MK Global Kapital": ["mk global", "mk global kapital"],
    "Franklin Templeton": ["franklin templeton", "martin lueck", "martin lück"],
    "PIMCO": ["pimco"],
    "Eurizon": ["eurizon", "intesa sanpaolo"],
    "Temasek": ["temasek"],
    "Bitcoin Suisse": ["bitcoin suisse"],
    "KKR": ["kkr", "kohlberg kravis"],
}


def fetch_single_feed(url, cutoff):
    """Fetch a single RSS feed (called in parallel)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "TE-Media-Intelligence/3.1 (Financial PR Research)",
            "Accept": "application/rss+xml, application/xml, text/xml"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        feed_items = []
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
                feed_items.append({"s": source, "t": title, "d": desc, "p": pub[:25], "l": link})
        return feed_items, True
    except Exception as e:
        return [], False


def fetch_client_website(client_name, urls):
    """Fetch client insights/news pages directly from their website."""
    results = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; TE-Media-Intelligence/3.2; +https://te-communications.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")[:50000]  # First 50k chars
            
            # Extract titles, links, dates from HTML
            # Look for common article/insight patterns
            articles = []
            
            # Pattern 1: <h2>/<h3> with link inside
            h_pattern = re.findall(r'<h[2-4][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{15,150})</a>', html, re.IGNORECASE)
            for href, title in h_pattern[:10]:
                if any(skip in title.lower() for skip in ["cookie", "privacy", "terms", "menu", "navigation", "search"]):
                    continue
                # Make URL absolute
                if href.startswith("/"):
                    base = "/".join(url.split("/")[:3])
                    href = base + href
                articles.append({
                    "client": client_name,
                    "title": re.sub(r'\s+', ' ', title).strip(),
                    "url": href,
                    "source_page": url,
                })
            
            # Pattern 2: <article> tags with linked headlines
            if not articles:
                a_pattern = re.findall(r'<a[^>]+href=["\']([^"\']+(?:insights?|articles?|news|press|research|outlook)[^"\']*)["\'][^>]*>([^<]{20,150})</a>', html, re.IGNORECASE)
                for href, title in a_pattern[:8]:
                    if any(skip in title.lower() for skip in ["cookie", "privacy", "terms", "menu", "subscribe"]):
                        continue
                    if href.startswith("/"):
                        base = "/".join(url.split("/")[:3])
                        href = base + href
                    articles.append({
                        "client": client_name,
                        "title": re.sub(r'\s+', ' ', title).strip(),
                        "url": href,
                        "source_page": url,
                    })
            
            results.extend(articles[:5])  # Max 5 per URL
        except Exception as e:
            continue
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:10]  # Max 10 per client


def fetch_all_client_insights():
    """Crawl all 9 client websites in parallel for current insights/news."""
    print(f"  Crawling {len(CLIENT_INSIGHTS_URLS)} client websites for insights...")
    insights_by_client = {}
    
    with ThreadPoolExecutor(max_workers=9) as executor:
        future_to_client = {
            executor.submit(fetch_client_website, client, urls): client
            for client, urls in CLIENT_INSIGHTS_URLS.items()
        }
        for future in as_completed(future_to_client):
            client = future_to_client[future]
            try:
                items = future.result()
                if items:
                    insights_by_client[client] = items
            except:
                pass
    
    total = sum(len(v) for v in insights_by_client.values())
    success_count = len(insights_by_client)
    print(f"  Client insights: {success_count}/9 websites scraped, {total} articles found")
    return insights_by_client


def fetch_rss_intelligence():
    """Parallel fetch of all RSS feeds with health tracking and client-mention detection."""
    all_feeds = MEDIA_RSS_FEEDS + GOOGLE_NEWS_FEEDS + CLIENT_FEEDS
    items = []
    client_specific = []  # Items from CLIENT_FEEDS (per-client monitoring)
    health = {"ok": 0, "fail": 0, "sources": set()}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=28)
    client_mentions = {client: [] for client in CLIENT_KEYWORDS}
    client_feed_set = set(CLIENT_FEEDS)

    # PARALLEL FETCH (10x faster than sequential)
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(fetch_single_feed, url, cutoff): url for url in all_feeds}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                feed_items, ok = future.result()
                if ok:
                    health["ok"] += 1
                    for it in feed_items:
                        items.append(it)
                        health["sources"].add(it["s"])
                        # Tag items from CLIENT_FEEDS as client-specific
                        if url in client_feed_set:
                            client_specific.append(it)
                else:
                    health["fail"] += 1
            except:
                health["fail"] += 1

    # Deduplicate by title
    seen = set()
    unique = []
    for it in items:
        k = it["t"][:55].lower()
        if k not in seen:
            seen.add(k)
            unique.append(it)

    # Deduplicate client_specific too
    seen_cs = set()
    unique_cs = []
    for it in client_specific:
        k = it["t"][:55].lower()
        if k not in seen_cs:
            seen_cs.add(k)
            unique_cs.append(it)

    # Client mention detection (across all feeds)
    for it in unique:
        haystack = (it["t"] + " " + it["d"]).lower()
        for client_name, keywords in CLIENT_KEYWORDS.items():
            if any(kw in haystack for kw in keywords):
                client_mentions[client_name].append(it)

    health["sources"] = len(health["sources"])
    mentions_found = sum(1 for v in client_mentions.values() if v)
    print(f"  RSS: {health['ok']}/{len(all_feeds)} feeds, {len(unique)} items total, {len(unique_cs)} client-specific, {health['sources']} sources, {mentions_found}/9 clients mentioned")
    return unique, health, client_mentions, unique_cs


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


def load_recent_summaries(days=5):
    """Load summaries from last N days for trend tracking."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:days]
    summaries = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                summaries.append({"date": data.get("date", ""), "summary": data.get("summary", "")[:400]})
        except: pass
    return summaries


def run_briefing():
    """Two-pass briefing: Opus 4.7 researches, Sonnet 4.6 positions."""
    client = anthropic.Anthropic()
    date_str, date_file, time_str, is_weekend = get_today_str()
    prev = load_previous_report()
    prev_sum = prev.get("summary", "") if prev else ""
    multi_day = load_recent_summaries(5)

    print(f"[{time_str}] TE Media Intelligence Agent v3.1 (parallel RSS + client mentions + trend tracking)")
    print(f"[{time_str}] {date_str} | Weekend: {is_weekend} | History: {len(multi_day)} days")

    # --- RSS (PARALLEL) ---
    t0 = time.time()
    rss_items, health, client_mentions, client_specific = fetch_rss_intelligence()
    rss_block = "\n".join(
        f"- [{it['s']}] {it['t']}" + (f" — {it['d']}" if it['d'] else "") + (f" ({it['p']})" if it['p'] else "")
        for it in rss_items[:80]
    )
    rss_time = round(time.time()-t0, 1)
    
    # --- DIRECT WEBSITE CRAWLING of client insights pages ---
    tw0 = time.time()
    client_insights = fetch_all_client_insights()
    insights_blocks = []
    for client, items in client_insights.items():
        block = f"\n=== {client} — Aktuelle Eigen-Inhalte (Webseite gerade gecrawlt) ===\n"
        for it in items[:6]:
            block += f"- {it['title']}\n  URL: {it['url']}\n"
        insights_blocks.append(block)
    insights_total_block = "\n".join(insights_blocks) if insights_blocks else "Keine Webseiten-Crawls erfolgreich."
    web_time = round(time.time()-tw0, 1)

    # Client-specific items block (from CLIENT_FEEDS — direct news on each client)
    client_specific_block = "\n".join(
        f"- [{it['s']}] {it['t']}" + (f" — {it['d']}" if it['d'] else "") + (f" ({it['p']})" if it['p'] else "")
        for it in client_specific[:40]
    ) if client_specific else "Keine kunden-spezifischen Treffer aus den dedizierten Kunden-Feeds."

    # Client mentions block (clients mentioned across general feeds)
    mention_lines = []
    for client_name, items in client_mentions.items():
        if items:
            mention_lines.append(f"\n[{client_name}] — {len(items)} Erwaehnung(en) in allg. Medien:")
            for it in items[:3]:
                mention_lines.append(f"  - [{it['s']}] {it['t']}")
    mentions_block = "\n".join(mention_lines) if mention_lines else "Keine direkten Kunden-Erwaehnungen in allgemeinen Medien."

    # Multi-day trend context
    trend_block = ""
    if len(multi_day) >= 2:
        trend_block = "\nLETZTE TAGE — TREND-KONTEXT:\n"
        for i, d in enumerate(multi_day[1:5]):  # Skip today (index 0)
            trend_block += f"\n{d['date']}: {d['summary'][:300]}\n"

    # --- PASS 1: Research ---
    diff = f"\nVORTAG: {prev_sum[:600]}\nKennzeichne: [NEU]/[ESKALATION]/[ENTSPANNUNG]/[FORTLAUFEND]\n" if prev_sum else ""
    wknd = "\nWochenende: Fokus auf Analysen, Ausblicke, Hintergrund.\n" if is_weekend else ""

    # Build client profile context block (stable facts only)
    profile_block = ""
    for client, p in CLIENT_PROFILES.items():
        profile_block += f"\n[{client}]\n"
        profile_block += f"  Typ: {p['type']} | AuM: {p['aum']} | HQ: {p['hq']} | DACH: {p['dach']}\n"
        profile_block += f"  Kernkompetenzen: {p['core_competencies']}\n"
        profile_block += f"  Zielmedien DACH: {p['target_media_dach']}\n"
        profile_block += f"  Tonfall: {p['tone']}\n"
        profile_block += f"  Tabu: {p['taboo']}\n"
    
    p1 = f"""Du bist der weltweit beste Medienanalyst und Finanzkommunikationsberater. 
Stand: {date_str}, {time_str} CET. Erfasse die LETZTEN 24 STUNDEN bis 7 TAGE.{wknd}

=== TEIL A: MARKT-RECHERCHE ===

ALLGEMEINE RSS-SCHLAGZEILEN ({len(rss_items)} Artikel, {health['sources']} Quellen, abgerufen {time_str} CET):
{rss_block}

KUNDEN-SPEZIFISCHE TREFFER aus dedizierten Kunden-Feeds ({len(client_specific)} Treffer):
{client_specific_block}

KUNDEN-ERWAEHNUNGEN IN ALLG. MEDIEN:
{mentions_block}
{trend_block}

=== TEIL B: KUNDEN-EIGEN-INHALTE (DIREKT VON DEN WEBSEITEN GECRAWLT) ===

WICHTIG: Diese Inhalte wurden JUST EBEN von den Kunden-Webseiten gescraped. Das sind die aktuellsten Eigen-Publikationen der Kunden. Sie sind Goldwert fuer Presseverteiler-Versand und Journalisten-Pitches:
{insights_total_block}

=== TEIL C: STABILE KUNDEN-PROFILE (Unternehmenswissen) ===

Diese Fakten sind stabil und seit Jahren gueltig (Geschaeftsmodell, Kernkompetenzen, Zielmedien, Tonfall, Tabus). Sprecher sind hier NICHT genannt, weil die wechseln — Sprecher musst du LIVE recherchieren.
{profile_block}

=== AUFGABE ===

Themenfelder: {', '.join(THEMENFELDER)}
{diff}

AUSGABE (beginne direkt, keine Einleitung):

## Schritt 0 — Quellen- und Zugriffslage
In 3-4 Saetzen: Welche Quellen waren heute gut auswertbar? Welche eingeschraenkt (Paywalls, Snippets)? Was ist die Gesamt-Belastbarkeit der heutigen Recherche? Macht Luecken transparent statt sie zu verstecken.

## Top 3 Themen des Tages
Die 3 wichtigsten Markt-Themen heute in je 2 Saetzen.

## Schritt 1 — Marktrecherche-Ueberblick
Gesamtcharakter, uebergreifendes Narrativ, dominante Themencluster.

## Schritt 2 — Themen die das Markt-Narrativ treiben
Nummerierte Bloecke nach Relevanz. Pro Block:
- Was dominiert die Headlines (Fakten, Zahlen, Quellen mit Datum)
- ZWEITRUNDENEFFEKTE / Zweite Ebene: Nicht das offensichtliche Thema, sondern was es konkret fuer Kreditqualitaet, Margen, Refinanzierung, Spreads, Waehrungen, EM-Uebertragung bedeutet. Genau hier liegt der differenzierende Pitch-Wert!
- Narrativ und Kausalkette
- Veraenderung gegenueber Vortagen
- Sentiment (positiv/neutral/kritisch fuer wen?)
- Belastbarkeit der Quellenlage: hoch / mittel / niedrig

## Schritt 3 — Unterdiskutierte Themen / White Spaces
Welche relevanten Themen sind heute KAUM in den Medien, koennten aber gepitcht werden? Wo gibt es ein Erzaehl-Vakuum, das ein Kunde fuellen koennte?

## Schritt 4 — Konkurrenz-Beobachtung
Welche grossen Wettbewerber unserer Kunden (BlackRock, Vanguard, Fidelity, Goldman Sachs AM, JPMorgan AM, Amundi, DWS, Allianz GI, AXA IM, Schroders, Invesco, State Street, Northern Trust, Apollo, Blackstone, Carlyle, TPG, Brookfield, EQT, Permira, Advent, CVC, Coinbase, Kraken, Gemini) sind heute in den Medien? Was kommunizieren sie? Wo koennten unsere Kunden kontern?

## Schritt 5 — KUNDEN-LIVE-RECHERCHE
Fuer JEDEN der 9 Kunden FUEHRE WEB-SEARCH DURCH:

### [Kundenname]
- **Aktuelle DACH-Sprecher** (Stand 2026, NUR live verifiziert!):
  Suche per Web Search auf der Unternehmensseite, LinkedIn, juengsten Pressemeldungen. Wer ist heute aktueller DACH-Sprecher? Name, Rolle, Quellennachweis (Link), Jahr der letzten Erwaehnung. WICHTIG: NUR Personen, die 2025/2026 nachweislich aktiv sind. Bei Unsicherheit: "nicht aktuell verifizierbar — bitte intern abstimmen".
- **Heutige direkte Erwaehnungen**:
  Wenn der Kunde in den allgemeinen Medien zitiert/erwaehnt wurde: in welchem Kontext, mit welchem Sprecher, Sentiment?
- **Themen-Schwerpunkte des Hauses aktuell**:
  Aus den oben gecrawlten Eigen-Inhalten + Live-Recherche: Worueber kommuniziert das Haus aktuell aktiv?

KRITISCH: Bei Sprechern und aktuellen Statements NICHTS halluzinieren. Lieber "nicht verifizierbar" als falschen Namen.

## Schritt 6 — Termine naechste 7 Tage
Datum, Uhrzeit, Land, Termin, Relevanz.

## Schritt 6a — Priorisierte Themen-Tabelle (Schnellueberblick)
Erstelle eine kompakte Tabelle der heutigen Top-Themen mit Zuordnung:

| Prio | Thema | Beste Kunden | Dringlichkeit | Medienarbeits-Eignung |
|------|-------|--------------|---------------|------------------------|
| 1 | [Top-Thema] | [1-3 Kunden] | hoch/mittel/niedrig | hoch/mittel/niedrig |
| 2 | ... | ... | ... | ... |
| ... bis Prio 7-8 | | | | |

Wichtig: Wenn fuer ein Themenfeld heute KEIN Stichtagsanlass besteht (z.B. Tokenisierung), liste es trotzdem mit "niedrig / niedrig" und der Begruendung "kein klarer Stichtagsanlass". Lieber ehrlich als zwanghaft Pitches generieren.

## Mehrtages-Trends
Was zieht sich seit Tagen durch? Was eskaliert/klingt ab?

## Gesamtfazit
2-3 Saetze zum uebergeordneten Narrativ. Plus: Welcher Pitch-Winkel ist der differenzierendste fuer heute (zweite Ebene, nicht das offensichtliche Thema)?

## Quellenverzeichnis
ALLE verwendeten Quellen: Medium — Titel (Datum) — URL. Keine erfundenen URLs.

QUALITAETSREGELN — ABSOLUT KRITISCH:
- Sprecher nur, wenn 2025/2026 nachweislich noch im Haus aktiv (sonst "nicht verifizierbar").
- Bei JEDER Zahl: Quelle + Datum.
- Nicht halluzinieren. Keine erfundenen URLs/Zitate/Personen.
- Englischsprachige Artikel gruendlich ins Deutsche uebertragen.
- Einfache, klare Sprache, keine Telegrammstil-Sprache.
- Kausalketten und Zusammenhaenge erklaeren.
- ZWEITE EBENE statt Offensichtliches: Differenzierung kommt aus den Zweitrundeneffekten, nicht aus generischen Marktkommentaren.
- Wenn fuer ein Thema/Kunden heute kein Stichtagsanlass existiert: ehrlich sagen statt zwanghaft pitchen."""

    print(f"[{time_str}] PASS 1: Opus 4.7 + Web Search (most capable model)...")
    t1s = time.time()
    r1, m1 = api_call(client, MODEL_RESEARCH, MAX_TOKENS_RESEARCH,
                       [{"role":"user","content":p1}],
                       tools=[{"type":"web_search_20250305","name":"web_search"}])
    txt1 = "".join(b.text for b in r1.content if hasattr(b,"text"))
    t1 = round(time.time()-t1s, 1)
    print(f"[{time_str}] PASS 1: {len(txt1)} chars via {m1} in {t1}s")

    # --- PASS 2: Positioning ---
    print(f"[{time_str}] Waiting 30s...")
    time.sleep(30)

    # Build profile + insights summary for Pass 2 (compact)
    insights_summary = "\n".join([f"\n[{c}] {len(items)} Eigen-Inhalte gefunden:\n" + "\n".join(f"  - {i['title']} → {i['url']}" for i in items[:4]) for c, items in client_insights.items()])
    
    p2 = f"""Du bist seit 20 Jahren Wirtschafts- und Finanzjournalist in DACH. Du hast bei Handelsblatt, FAZ, Boersen-Zeitung, Reuters und Bloomberg gearbeitet. Du weisst genau, was Journalisten tatsaechlich brauchen, um ein Pitch zu nehmen, und was sofort im Papierkorb landet.

Du wechselst jetzt die Rolle: Du arbeitest als Senior Director bei TE Communications und sollst aus Journalistensicht Pitches fuer 9 Kunden formulieren.

WAS JOURNALISTEN BRAUCHEN (du kennst das aus 20 Jahren Praxis):
1. NEWS-AUFHAENGER: Klare aktuelle Begruendung "warum heute". Ohne Aufhaenger keine Story.
2. THESE: Eine pointierte Aussage, kein "Sowohl-als-auch". Journalisten lieben Reibung, nicht Diplomatie.
3. ZWEI BIS DREI BELEGE: konkrete Zahlen, Daten, Zitate, Quellen — nichts Vages.
4. SPRECHER MIT EXPERTISE: Konkrete Person, ihre Rolle, warum SIE genau das beurteilen kann.
5. WAS DAS UEBER DEN TAG HINAUSGEHT: Trend, Umbruch, Konflikt.
6. EXKLUSIVITAET ODER SUBSTANZ: Was bekommt der Journalist hier, was er nirgends sonst bekommt?
7. PASSGENAUIGKEIT ZUM MEDIUM: Boersen-Zeitung will Tiefe, Handelsblatt will News+Analyse, FAZ will Einordnung, n-tv will klare Zuspitzung.
8. KOPF-ZUERST-PRINZIP: Erste 2 Saetze entscheiden ueber Annahme oder Ablehnung.

Was Journalisten SOFORT NERVT (du weisst das auch):
- "Markteinschaetzung von..." als Betreff (zu generisch)
- Buzzwords ohne Substanz ("disruptiv", "robust positioniert", "ganzheitlich")
- Lange Marketing-Vorbemerkungen
- Pitches ohne klaren Aufhaenger ("Wir haben da was Interessantes...")
- Wenn der Sprecher zum Thema nicht passt
- Wenn Konkurrenz schon dasselbe gepitcht hat
- Wenn die These weichgespuelt ist

KUNDEN-PROFILE:
{profile_block}

LIVE-MARKTANALYSE VON HEUTE ({date_str}):
{txt1[:8000]}

DIREKT GECRAWLTE EIGEN-INHALTE DER KUNDEN (frische Eigen-Materialien fuer Presseversand):
{insights_summary}

KUNDEN-MENTIONS HEUTE:
{mentions_block}

AUFGABE: Erstelle zwei Abschnitte. Beide muessen so brauchbar sein, dass ein TE-Berater sie sofort 1:1 verwenden kann, ohne nochmal nachzubessern.

## Schritt 7 — Positionierungs-Mapping pro Kunde

Fuer JEDEN der 9 Kunden, in dieser klaren Struktur:

### [Kundenname]

**Heute anschlussfaehig ueber:**
- [Themen-Achse 1 mit konkretem Bezug zur heutigen Marktlage]
- [Themen-Achse 2]
- [optional Themen-Achse 3]

**Empfohlener Sprecher:**
- [Name, Rolle] — [warum genau diese Person zu diesem Thema passt — z.B. juengste Aussage, Spezialgebiet, mediale Erfahrung]
- WENN nicht live verifiziert: "Sprecher intern abstimmen — Profil legt [Frank Witt / Konstantin Veit / etc.] nahe"

---

**PITCH 1 — [pointierte These als Titel, journalistentauglich]**
Format: [Gastbeitrag / Hintergrundgespraech / Interview-Angebot / Kommentar fuer Presseverteiler / TV-Schalte]
Dringlichkeit: [heute / diese Woche / naechste Woche]
Zielmedium primaer: [konkretes Medium aus Profil]
Zielmedium sekundaer: [2-3 weitere Medien]

E-Mail-Betreff (vorgeschlagen): "[konkreter Betreff, max 70 Zeichen, mit Aufhaenger]"

Pitch-Aufhaenger (warum heute):
- [konkrete Marktbewegung/Schlagzeile/Datenpunkt von heute, mit Datum + Quelle]

These des Pitches:
- [pointierte Kernaussage in 1 Satz, die der Sprecher vertreten wuerde]

3 Belege/Argumente fuer Journalisten:
- [Beleg 1: konkrete Zahl/Studie/Marktbewegung]
- [Beleg 2]
- [Beleg 3]

Was der Journalist konkret bekommt:
- Sprecher-Verfuegbarkeit: [z.B. "heute ab 14 Uhr per Telefon", "binnen 24h schriftliches Statement"]
- Eigen-Material zum Andocken: [konkrete URL aus den oben gecrawlten Inhalten]
- Optional: [exklusive Daten / Whitepaper / Studie]

Story-Winkel fuer das jeweilige Medium:
- [Wie genau dieser Pitch in [Zielmedium] passt — was ist der Hook fuer DESSEN Leserschaft]

Vorschlag fuer Pitch-Mail (1 Absatz, max 6 Saetze, im Stil eines erfahrenen Pressesprechers):
"[Sehr geehrter Herr/Frau [...], aktuell zeigen sich [konkrete Marktbewegung] und [konkrete Folge]. [Sprecher-Name], [Rolle bei Kunde], hat dazu eine pointierte Lesart: [These in 1 Satz]. Die Kernpunkte: [3 stichpunktartige Belege]. Material zum Andocken: [URL]. [Sprecher] ist [Verfuegbarkeit] verfuegbar. Sollen wir Ihnen ein Statement / einen Gastbeitrag / ein Hintergrundgespraech anbieten?]"

---

**PITCH 2 — [zweite, andere These als Titel]**
[gleiche Struktur wie Pitch 1]

---

**Aufgreifbare Eigen-Inhalte des Kunden (Presseverteiler-Versand HEUTE):**
- [Titel] → [URL] — [in 1 Satz: warum jetzt versenden, an welche Liste]

**Konkurrenz-Konter (falls heute relevant):**
- [Wettbewerber X] hat heute [Y] kommuniziert. Unser Kunde kann mit [Konter-Argument] in [Medium] kontern.

**Tabu-Warnung (wenn vorhanden):**
- [Was darf in keinem Pitch erwaehnt werden, basierend auf Profil-Tabus]

WICHTIG: Wenn fuer einen Kunden heute KEIN guter Pitch sinnvoll ist, schreibe das offen: "Heute kein passender Aufhaenger fuer [Kunde] — Profil-Themen heute nicht in den Schlagzeilen. Empfehlung: stattdessen [Alternative wie 'Vortagsanalyse fuer Wochenausblick verwenden']."

---

## Schritt 8 — Top-7 Pitch-Empfehlungen fuer HEUTE (sortiert nach Erfolgswahrscheinlichkeit)

Die besten 7 Pitches aus Schritt 7, neu sortiert. Pro Pitch:

**[Rang]. ★[1-5 Sterne] [Pitch-Titel — pointierte These]**
- Warum top heute: [in 1-2 Saetzen — News-Lage + Sprecher-Passung + Medium-Bedarf]
- Format: [...] | Kunde: [...] | Sprecher: [...] (verifiziert/intern)
- Zielmedium: [primaer] | Backup: [sekundaer]
- Naechster Schritt fuer TE-Berater: [konkrete Aktion — z.B. "Sprecher heute 09:30 anrufen, Pitch-Mail bis 11 Uhr an Redakteur X bei Boersen-Zeitung"]
- Eigen-Material: [URL falls vorhanden]
- Erfolgs-Wahrscheinlichkeit: [hoch/mittel/niedrig] mit kurzer Begruendung

REGELN ABSOLUT:
- Sprecher NUR, wenn live verifiziert in Schritt 5. Sonst "intern abstimmen".
- KEINE Buzzwords ("ganzheitlich", "robust", "disruptiv", "innovative Loesung").
- KEINE Trading-Sprache ("Overweight", "Underweight").
- These muss POINTIERT sein — Reibung, nicht Diplomatie.
- Aufhaenger muss eine konkrete Schlagzeile/Datenpunkt von heute sein, mit Quelle.
- Pitch-Mail-Vorschlag muss so sein, dass ein TE-Berater ihn nur noch personalisieren muss.
- Wenn ein Pitch das Profil-Tabu streift: NICHT vorschlagen, sondern Alternative bieten.
- Deutsche Sprache, klar, nicht ueberladen.
- KEIN Telegrammstil, aber auch keine PR-Floskeln. Schreibstil wie ein erfahrener Wirtschaftsjournalist."""

    print(f"[{time_str}] PASS 2: Sonnet 4.6 journalist-grade pitch crafting...")
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
        "client_mentions": {k: len(v) for k, v in client_mentions.items()},
        "history_days": len(multi_day),
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
        f.write(f"TE Communications — Daily Media Intelligence v3.1\n{date_str}, {time_str} CET\n")
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
    
    # Client mentions box
    cm = meta.get('client_mentions', {})
    cm_active = {k: v for k, v in cm.items() if v > 0}
    if cm_active:
        cm_items = " ".join(f'<span class="cm-pill"><b>{k}</b>: {v}</span>' for k, v in cm_active.items())
        cm_box = f'<div class="cm-box"><div class="cm-title">&#128276; Direkte Kunden-Erwaehnungen heute ({sum(cm_active.values())} Treffer)</div>{cm_items}</div>'
    else:
        cm_box = '<div class="cm-box cm-empty">Keine direkten Kunden-Erwaehnungen in den heutigen RSS-Feeds gefunden. (Web Search-Recherche im Hauptreport koennte trotzdem Erwaehnungen aufdecken.)</div>'
    
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
.cm-box{{background:#fffbeb;border:1px solid #fbbf24;border-radius:6px;padding:14px 18px;margin-bottom:16px;font-size:12.5px}}
.cm-empty{{background:#f9fafb;border-color:#e5e7eb;color:#6b7280;font-style:italic}}
.cm-title{{font-weight:700;color:#92400e;margin-bottom:8px;font-size:12px;text-transform:uppercase;letter-spacing:.05em}}
.cm-empty .cm-title{{color:#6b7280}}
.cm-pill{{display:inline-block;background:#fff;border:1px solid #fbbf24;border-radius:14px;padding:4px 10px;margin:3px 4px 0 0;font-size:11.5px;color:#78350f}}
.cm-pill b{{color:#1f2937}}
.ft{{margin-top:32px;padding-top:20px;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;line-height:1.6}}
@media(max-width:600px){{body{{padding:16px 12px}}.hd{{padding:20px 16px}}.hd h1{{font-size:20px}}.sh{{padding:14px 16px}}.sb{{padding:0 16px 16px}}.kp{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="hd">
<div class="lb">TE Communications — Daily Media Intelligence Agent v3.1</div>
<h1>Tagesauswertung &amp; Positionierungs-Briefing</h1>
<div class="dt">{date_str} — {time_str} CET</div>
<div class="ml">Pass 1: {meta['m1']} + Web Search ({meta['t1']}s) | Pass 2: {meta['m2']} ({meta['t2']}s) | {meta['rss_ok']}/{meta['rss_total']} RSS-Feeds parallel | {meta.get('history_days',0)} Tage Trendkontext</div>
<div class="bg">
<span>PGIM</span><span>T. Rowe Price</span><span>MK Global Kapital</span><span>Franklin Templeton</span><span>PIMCO</span><span>Eurizon</span><span>Temasek</span><span>Bitcoin Suisse</span><span>KKR</span>
</div>
</div>
<div class="kp">
<div><div class="v">{meta['rss_items']}</div><div class="l">RSS Artikel</div></div>
<div><div class="v">{meta['rss_sources']}</div><div class="l">Quellen</div></div>
<div><div class="v">{sum(meta.get('client_mentions',{}).values())}</div><div class="l">Kunden-Mentions</div></div>
<div><div class="v">{meta['total']:,}</div><div class="l">Zeichen</div></div>
<div><div class="v">{tt}s</div><div class="l">Laufzeit</div></div>
</div>
{cm_box}
{diff_b}
<div class="ct">
<button onclick="document.querySelectorAll('details.sec').forEach(d=>d.open=true)">Alle oeffnen</button>
<button onclick="document.querySelectorAll('details.sec').forEach(d=>d.open=false)">Alle schliessen</button>
</div>
{body}
<div class="ft">
<b>Methodik:</b> Zwei-Pass-Architektur — Pass 1 (Opus 4.7 + Web Search) tiefe Marktrecherche, Pass 2 (Sonnet 4.6) PR-Positionierung. Opus 4.7 ist das aktuell leistungsstaerkste oeffentlich verfuegbare Anthropic-Modell. {meta['rss_ok']} RSS-Feeds aus {meta['rss_sources']} Medienquellen. 24h-Zeitfilter. 14 Themenfelder. Vortagesvergleich.<br><br>
<b>Qualitaetshinweis:</b> Automatisiert erstellt. Kurse und Zahlen vor Verwendung in Kundenkommunikation gegen zweite Quelle pruefen.<br><br>
<b>TE Communications GmbH</b> | Frankfurt &middot; Zuerich &middot; St. Gallen &middot; Lausanne
</div>
</body>
</html>'''


if __name__ == "__main__":
    run_briefing()
