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
MODEL_POSITIONING = "claude-opus-4-7"
MODEL_FALLBACK = "claude-sonnet-4-6"
MAX_TOKENS_RESEARCH = 22000  # Opus 4.7 — deep multi-stage analysis with 8-point framework
MAX_TOKENS_POSITIONING = 32000  # Sonnet 4.6 — 15 clients × 2 pitches each needs ~25-30k tokens
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
    # DE FACHMEDIEN (27)
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
    "https://www.fundview.de/feed/",
    "https://www.morningstar.de/de/news/rss.aspx",
    "https://www.capital.de/feed/",
    "https://www.focus.de/finanzen/rss/",
    "https://www.bild.de/rss/vw/bild-de/geld.xml",
    # NEU: weitere DE Fachmedien (8)
    "https://www.asscompact.de/rss.xml",
    "https://versicherungswirtschaft-heute.de/feed/",
    "https://www.finanzwelt.de/feed/",
    "https://www.intelligent-investors.de/feed/",
    "https://www.boersen-zeitung.de/rss",
    "https://www.dpa-afx.de/rss",
    "https://www.dpa.com/de/produkte/themendienste/wirtschaft/rss",
    "https://www.euro-magazin.de/rss",
    # NEU: weitere deutsche Online-Portale + Brieffachdienste
    "https://www.onvista.de/news/feed/all.rss",
    "https://www.t-online.de/wirtschaft/rss.xml",
    "https://www.focus.de/finanzen/boerse/rss.xml",
    "https://www.dfpa.info/rss/",
    # NEU: Reichweitenstarke Online-Finanzportale (Layer 1)
    "https://www.wallstreet-online.de/rss/news",
    "https://www.boersennews.de/rss",
    "https://www.finanznachrichten.de/rss-aktien-news.htm",
    "https://www.ariva.de/news.m?archiv=1&inhalt=ATOM",
    "https://www.finanzen100.de/rss/",
    "https://www.finanztreff.de/rss/news.html",
    # NEU: Banken-/Sparkassen-Fachmedien
    "https://www.springerprofessional.de/rss/bankmagazin",
    "https://bankinghub.de/feed",
    "https://www.bankingclub.de/feed/",
    # NEU: Versicherungs-Fachmedien (offizielle RSS-Feeds)
    "https://www.versicherungsjournal.de/rss/VersicherungsJournal.xml",
    "https://www.procontra-online.de/feed/",
    "https://www.versicherungsmagazin.de/rss",
    "https://www.cash-online.de/feed",
    # NEU: Immobilien-Fachpresse
    "https://www.immobilienmanager.de/feed",
    "https://www.haufe.de/immobilien/rss",
    "https://www.property-magazine.de/rss/news.xml",
    "https://www.deal-magazin.com/rss",
    # NEU: Anleger-Magazine
    "https://www.smartinvestor.de/feed/",
    "https://www.deraktionaer.de/rss/aktuell.xml",
    # DE IMMOBILIEN (urspruenglich)
    "https://www.iz.de/rss/news.xml",
    "https://www.thomas-daily.de/feed/",
    # SCHWEIZ — verstaerkter Fokus
    "https://www.nzz.ch/finanzen.rss",
    "https://www.nzz.ch/wirtschaft.rss",
    "https://www.fuw.ch/feed",
    "https://www.cash.ch/rss/news",
    "https://www.handelszeitung.ch/rss.xml",
    "https://www.finews.ch/rss",
    "https://www.moneycab.com/feed/",
    "https://www.investrends.ch/feed/",
    "https://www.bilanz.ch/rss",
    "https://themarket.ch/rss",
    # OESTERREICH — verstaerkter Fokus
    "https://www.diepresse.com/rss/wirtschaft",
    "https://www.derstandard.at/rss/wirtschaft",
    "https://www.boersen-kurier.at/feed/",
    "https://www.boerse-express.com/feed/",
    "https://www.fondsexklusiv.at/feed/",
    "https://www.gewinn.com/rss/",
    "https://www.derboersianer.com/feed/",
    "https://www.geld-magazin.at/rss",
    "https://www.trend.at/rss",
    # INT NACHRICHTEN-AGENTUREN (Reuters, Bloomberg, Dow Jones — gewuenscht)
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/companyNews",
    "https://feeds.bloomberg.com/markets/news.rss",
    # Dow Jones direkt nicht oeffentlich verfuegbar — Site-Fallback weiter unten in GOOGLE_NEWS_FEEDS
    # INT FACHMEDIEN — institutionell, fuer Fonds/AM/PE
    "https://www.ipe.com/rss",
    "https://www.privatedebtinvestor.com/feed/",
    "https://www.infrastructureinvestor.com/feed/",
    "https://www.preqin.com/feed",
    "https://www.etfstream.com/feed/",
    "https://citywire.com/rss",
    "https://www.risk.net/rss",
    "https://www.globalcapital.com/rss",
    # NEU Stufe-A: Citywire DACH-Plattformen (eigenstaendig)
    "https://citywire.com/de/rss",
    "https://citywire.com/ch/rss",
    "https://citywire.com/selector/rss",
    # NEU Stufe-A: Hedgeweek (Alternatives mit DACH-Coverage)
    "https://www.hedgeweek.com/feed/",
    # NEU Stufe-A: Funds Europe (Optional Stufe-B aber sinnvoll)
    "https://www.funds-europe.com/feed",
    # NEU Stufe-A: ESG / Sustainable Finance DACH
    "https://www.ecoreporter.de/feed/",
    # NEU Stufe-A: Krypto DACH
    "https://www.btc-echo.de/feed/",
    "https://cvj.ch/feed/",
    "https://bitcoinnews.ch/feed/",  # optional Stufe-B
    # NEU Stufe-A: Schweizer Spezialmedien (Investigativ + neues Wirtschaftsportal)
    "https://insideparadeplatz.ch/feed/",
    "https://www.tippinpoint.ch/feed/",
    "https://www.finews.com/feed",  # englisches CH-Schwesterportal
    # NEU Stufe-A: Family Office / Premium-Briefe
    # Elite Report: kein RSS, ueber Google News abgedeckt
    # Fuchsbriefe: kein offener RSS, ueber Google News abgedeckt
    # NEU Stufe-A: Boersenbriefe + Newsletter
    "https://www.bernecker.info/feed",
    "https://www.cashkurs.com/rss",
    "https://financefwd.com/feed",
    "https://www.thepioneer.de/feed",  # RSS-Versuch fuer Pioneer Briefing
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
    # EN thematisch — filtert vor allem Treffer aus Reuters/Bloomberg/Dow Jones
    # die in deutscher Berichterstattung oft nur verzoegert auftauchen
    "https://news.google.com/rss/search?q=PGIM+OR+%22Franklin+Templeton%22+OR+%22T+Rowe+Price%22+OR+Eurizon&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Bitcoin+Suisse%22+OR+%22crypto+regulation%22+MiCA&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=KKR+investment&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Aegon+OR+%22DNB+Asset%22+OR+%22Insight+Investment%22+OR+JOHCM&hl=en&gl=US&ceid=US:en",
    # Site-Fallbacks fuer Outlets ohne oeffentlichen RSS
    # DACH-Fokus — angelsaechsische Medien (FT, WSJ, BBC, CNBC, Economist, Guardian, Fortune) wurden entfernt
    "https://news.google.com/rss/search?q=site%3Aborsen-zeitung.de&hl=de&gl=DE&ceid=DE:de",
    # Platow Brief — Premium-Wirtschaftsbrief, kein oeffentlicher RSS
    "https://news.google.com/rss/search?q=site%3Aplatow.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Platow+Brief%22&hl=de&gl=DE&ceid=DE:de",
    # Czerwensky intern — Premium-Brief Banken/Versicherungen, kein oeffentlicher RSS
    "https://news.google.com/rss/search?q=%22Czerwensky+intern%22&hl=de&gl=DE&ceid=DE:de",
    # onvista — falls direkter RSS scheitert
    "https://news.google.com/rss/search?q=site%3Aonvista.de&hl=de&gl=DE&ceid=DE:de",
    # t-online Wirtschaft — Verbrauchermedium, falls direkter RSS scheitert
    "https://news.google.com/rss/search?q=site%3At-online.de+wirtschaft&hl=de&gl=DE&ceid=DE:de",
    # Bloomberg-Themensuche
    "https://news.google.com/rss/search?q=site%3Abloomberg.com+markets&hl=en&gl=US&ceid=US:en",
    # The Market (NZZ-Premium-Schweiz)
    "https://news.google.com/rss/search?q=site%3Athemarket.ch+OR+site%3Athemarketswiss.ch&hl=de&gl=CH&ceid=CH:de",
    # Bilanz — Schweiz
    "https://news.google.com/rss/search?q=site%3Abilanz.ch&hl=de&gl=CH&ceid=CH:de",
    # Oesterreich-Premiummedien
    "https://news.google.com/rss/search?q=site%3Atrend.at&hl=de&gl=AT&ceid=AT:de",
    "https://news.google.com/rss/search?q=site%3Agewinn.com&hl=de&gl=AT&ceid=AT:de",
    "https://news.google.com/rss/search?q=site%3Aderboersianer.com&hl=de&gl=AT&ceid=AT:de",
    "https://news.google.com/rss/search?q=site%3Ageld-magazin.at&hl=de&gl=AT&ceid=AT:de",
    # DACH-Fachmedien Backup
    "https://news.google.com/rss/search?q=site%3Adpa-afx.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22dpa-AFX%22&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Dow+Jones+Newswires%22+OR+%22Dow+Jones%22+Markt&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aasscompact.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aversicherungswirtschaft-heute.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Afinanzwelt.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aintelligent-investors.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Adfpa.info&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Afundview.de&hl=de&gl=DE&ceid=DE:de",
    # NEU: Fallbacks fuer Online-Finanzportale (falls direkter RSS scheitert)
    "https://news.google.com/rss/search?q=site%3Awallstreet-online.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aboersennews.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Afinanznachrichten.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aariva.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Afinanzen100.de&hl=de&gl=DE&ceid=DE:de",
    # NEU: Fallbacks fuer Banken-Fachmedien
    "https://news.google.com/rss/search?q=site%3Abankmagazin.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Abankinghub.de&hl=de&gl=DE&ceid=DE:de",
    # NEU: Fallbacks fuer Versicherungsfachmedien
    "https://news.google.com/rss/search?q=site%3Aversicherungsjournal.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aprocontra-online.de&hl=de&gl=DE&ceid=DE:de",
    # NEU: Fallbacks fuer Immobilien-Fachmedien
    "https://news.google.com/rss/search?q=site%3Aimmobilienmanager.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aproperty-magazine.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Adeal-magazin.com&hl=de&gl=DE&ceid=DE:de",
    # NEU: Fallback fuer Anleger-Magazine
    "https://news.google.com/rss/search?q=site%3Asmartinvestor.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Aderaktionaer.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Euro+am+Sonntag%22+OR+%22Euro+Magazin%22&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Focus+Money%22&hl=de&gl=DE&ceid=DE:de",
    # NEU Stufe-A: Citywire DACH-Fallbacks
    "https://news.google.com/rss/search?q=site%3Acitywire.com%2Fde&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Acitywire.com%2Fch&hl=de&gl=CH&ceid=CH:de",
    # NEU Stufe-A: Family Office / Premium-Briefe Site-Fallbacks
    "https://news.google.com/rss/search?q=site%3Aelitereport.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Elite+Report%22+Verm%C3%B6gensverwalter&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Afuchsbriefe.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Fuchsbriefe%22+OR+%22FUCHS-Briefe%22+OR+%22Fuchs-Richter%22&hl=de&gl=DE&ceid=DE:de",
    # NEU Stufe-A: The Pioneer + Table.Media (Premium-Newsletter)
    "https://news.google.com/rss/search?q=site%3Athepioneer.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Pioneer+Briefing%22+OR+%22Gabor+Steingart%22&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Atable.media&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Table.Briefings%22+OR+%22ESG.Table%22+OR+%22CEO.Table%22&hl=de&gl=DE&ceid=DE:de",
    # NEU Stufe-A: Schweizer Investigativ + Tippinpoint
    "https://news.google.com/rss/search?q=site%3Ainsideparadeplatz.ch&hl=de&gl=CH&ceid=CH:de",
    "https://news.google.com/rss/search?q=site%3Atippinpoint.ch&hl=de&gl=CH&ceid=CH:de",
    # NEU Stufe-A: Krypto-DACH Backups
    "https://news.google.com/rss/search?q=site%3Abtc-echo.de&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=site%3Acvj.ch&hl=de&gl=CH&ceid=CH:de",
    # NEU Stufe-A: ESG Backup
    "https://news.google.com/rss/search?q=site%3Aecoreporter.de&hl=de&gl=DE&ceid=DE:de",
    # NEU Stufe-A: Boersenbriefe Backups
    "https://news.google.com/rss/search?q=site%3Abernecker.info&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Hellmeyer+Report%22+OR+%22Folker+Hellmeyer%22&hl=de&gl=DE&ceid=DE:de",
    # NEU Stufe-A: AWP + Hedgeweek Backups
    "https://news.google.com/rss/search?q=%22AWP+Finanznachrichten%22&hl=de&gl=CH&ceid=CH:de",
    "https://news.google.com/rss/search?q=site%3Ahedgeweek.com&hl=en&gl=US&ceid=US:en",
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
    # Eurizon
    "https://news.google.com/rss/search?q=site%3Aeurizoncapital.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Eurizon+Deutschland+OR+Frankfurt+%22Intesa+Sanpaolo%22&hl=de&gl=DE&ceid=DE:de",
    # Bitcoin Suisse
    "https://news.google.com/rss/search?q=site%3Abitcoinsuisse.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Bitcoin+Suisse%22+OR+%22Dirk+Klee%22&hl=de&gl=DE&ceid=DE:de",
    # KKR
    "https://news.google.com/rss/search?q=site%3Akkr.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=KKR+Deutschland+OR+Frankfurt+%22Philipp+Freise%22&hl=de&gl=DE&ceid=DE:de",
    # Aegon Asset Management
    "https://news.google.com/rss/search?q=site%3Aaegonam.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Aegon+Asset+Management%22+OR+%22Aegon+AM%22&hl=de&gl=DE&ceid=DE:de",
    # Bendura Bank
    "https://news.google.com/rss/search?q=site%3Abendura.li&hl=de&gl=DE&ceid=DE:de",
    "https://news.google.com/rss/search?q=%22Bendura+Bank%22+Liechtenstein&hl=de&gl=DE&ceid=DE:de",
    # DNB Asset Management
    "https://news.google.com/rss/search?q=site%3Adnbam.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22DNB+Asset+Management%22+OR+%22DNB+AM%22+Norwegen&hl=de&gl=DE&ceid=DE:de",
    # Insight Investment
    "https://news.google.com/rss/search?q=site%3Ainsightinvestment.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Insight+Investment%22+BNY+OR+LDI&hl=de&gl=DE&ceid=DE:de",
    # JOHCM (J O Hambro Capital Management)
    "https://news.google.com/rss/search?q=site%3Ajohcm.com&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=JOHCM+OR+%22J.O.+Hambro%22+OR+%22JO+Hambro%22&hl=de&gl=DE&ceid=DE:de",
    # Maverix Securities
    "https://news.google.com/rss/search?q=site%3Amavx.com&hl=de&gl=CH&ceid=CH:de",
    "https://news.google.com/rss/search?q=%22Maverix+Securities%22+OR+%22Maverix+AG%22&hl=de&gl=DE&ceid=DE:de",
]

# === LAYER 4: DIRECT WEBSITE CRAWLING — Insights/Press pages of each client ===
# These URLs are scraped directly to find publishable content, whitepapers, commentaries
CLIENT_INSIGHTS_URLS = {
    "PGIM": [
        # Insights & Research
        "https://www.pgim.com/insights",
        "https://www.pgim.com/insights/quarterly-outlook",
        "https://www.pgim.com/insights/megatrends",
        "https://www.pgim.com/fixed-income/insights",
        "https://www.pgim.com/real-estate/insights",
        "https://www.pgim.com/private-capital/insights",
        # News & Press
        "https://www.pgim.com/news",
        "https://www.pgim.com/press-releases",
        # Sprecher / About
        "https://www.pgim.com/about-pgim/leadership",
    ],
    "T. Rowe Price": [
        "https://www.troweprice.com/personal-investing/resources/insights.html",
        "https://www.troweprice.com/corporate/en/press.html",
        "https://www.troweprice.com/financial-intermediary/de/de/insights.html",
        "https://www.troweprice.com/corporate/en/insights/markets-economy.html",
        "https://www.troweprice.com/corporate/en/insights/multi-asset.html",
        "https://www.troweprice.com/corporate/en/insights/fixed-income.html",
        "https://www.troweprice.com/corporate/en/insights/equity.html",
        "https://www.troweprice.com/corporate/en/about/management-and-leadership.html",
    ],
    "MK Global Kapital": [
        "https://www.mk-global.com/news/",
        "https://www.mk-global.com/insights/",
        "https://www.mk-global.com/about/",
        "https://www.mk-global.com/strategies/",
        "https://www.mk-global.com/team/",
    ],
    "Franklin Templeton": [
        "https://www.franklintempleton.de/articles",
        "https://www.franklintempleton.de/insights",
        "https://www.franklintempleton.com/articles",
        "https://www.franklintempleton.com/insights",
        "https://www.franklintempleton.com/press-releases",
        "https://www.franklintempleton.de/news",
        "https://www.franklintempleton.com/our-thinking",
        "https://www.franklintempleton.com/about-us/our-people",
        "https://www.franklintempleton.de/articles/martin-luck",
    ],
    "Eurizon": [
        "https://www.eurizoncapital.com/en/strategy/market-views",
        "https://www.eurizoncapital.com/en/news-events",
        "https://www.eurizoncapital.com/en/strategy/research-publications",
        "https://www.eurizoncapital.com/en/about-us/our-people",
        "https://www.eurizoncapital.com/de/marktanalysen",
        "https://www.eurizoncapital.com/en/funds/sustainability",
    ],
    "Bitcoin Suisse": [
        "https://www.bitcoinsuisse.com/research",
        "https://www.bitcoinsuisse.com/news",
        "https://www.bitcoinsuisse.com/research/decrypt",
        "https://www.bitcoinsuisse.com/research/outlook",
        "https://www.bitcoinsuisse.com/about/team",
        "https://www.bitcoinsuisse.com/news/press-releases",
    ],
    "KKR": [
        "https://www.kkr.com/insights",
        "https://www.kkr.com/news",
        "https://www.kkr.com/insights/global-macro-trends",
        "https://www.kkr.com/insights/private-credit",
        "https://www.kkr.com/insights/infrastructure",
        "https://www.kkr.com/insights/real-estate",
        "https://www.kkr.com/our-firm/our-leadership",
        "https://www.kkr.com/news/press-releases",
    ],
    "Aegon AM": [
        "https://www.aegonam.com/insights/",
        "https://www.aegonam.com/news/",
        "https://www.aegonam.com/insights/multi-asset/",
        "https://www.aegonam.com/insights/fixed-income/",
        "https://www.aegonam.com/insights/responsible-investing/",
        "https://www.aegonam.com/about/our-people/",
        "https://www.aegonam.com/de/insights/",
    ],
    "Bendura Bank": [
        "https://www.bendura.li/aktuelles/",
        "https://www.bendura.li/",
        "https://www.bendura.li/ueber-uns/",
        "https://www.bendura.li/leistungen/vermoegensverwaltung/",
        "https://www.bendura.li/medien/",
    ],
    "DNB AM": [
        "https://dnbam.com/de/insights",
        "https://dnbam.com/de/news",
        "https://dnbam.com/de/strategies",
        "https://dnbam.com/en/insights",
        "https://dnbam.com/en/news",
        "https://dnbam.com/de/about/team",
        "https://dnbam.com/en/insights/sustainability",
    ],
    "Insight Investment": [
        "https://www.insightinvestment.com/deutschland/insights/",
        "https://www.insightinvestment.com/insights/",
        "https://www.insightinvestment.com/about-insight/news-and-views/",
        "https://www.insightinvestment.com/insights/fixed-income/",
        "https://www.insightinvestment.com/insights/liability-driven-investment/",
        "https://www.insightinvestment.com/insights/responsible-investment/",
        "https://www.insightinvestment.com/about-insight/our-team/",
        "https://www.insightinvestment.com/deutschland/news/",
    ],
    "JOHCM": [
        "https://www.johcm.com/de-de/insights",
        "https://www.johcm.com/uk/insights",
        "https://www.johcm.com/us/insights",
        "https://www.johcm.com/uk/news",
        "https://www.johcm.com/de-de/news",
        "https://www.johcm.com/uk/our-team",
        "https://www.johcm.com/uk/strategies",
    ],
    "Maverix": [
        "https://mavx.com/de/news/",
        "https://mavx.com/de/insights/",
        "https://mavx.com/de/strategie/",
        "https://mavx.com/de/team/",
        "https://mavx.com/de/research/",
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
    "Aegon AM": {
        "type": "Globaler Asset Manager, Tochter der Aegon NV (Niederlande)",
        "aum": "ca. EUR 320 Mrd. (Stand: aktuell live verifizieren)",
        "hq": "Den Haag (Niederlande), Edinburgh (UK)",
        "dach": "Vertrieb ueber niederlaendische und britische Hubs, deutscher Wholesale-Vertrieb",
        "boutiques": "Fixed Income (Schwerpunkt), Multi-Asset, Equities, Real Assets, Responsible Investment",
        "core_competencies": "Fixed Income (Investment Grade, High Yield, EMD, ABS), LDI fuer Pensionsfonds, Multi-Asset, Real Assets (Real Estate, Infrastructure), starker ESG-/Verantwortungsinvestment-Fokus, niederlaendische Pensionssystem-Expertise",
        "target_media_dach": "Fonds Professionell, DAS INVESTMENT, Citywire, Institutional Money, Handelsblatt, Boersen-Zeitung, IPE, dpn, portfolio institutionell, Responsible Investor",
        "tone": "europaeisch-institutionell, akademisch, ESG/Stewardship-orientiert, eher zurueckhaltend, niederlaendische Sachlichkeit",
        "taboo": "keine politischen Positionierungen, ESG-Greenwashing-Vorwuerfe gegen andere vermeiden, US-Wahlen-Themen vermeiden",
    },
    "Bendura Bank": {
        "type": "Liechtensteiner Privatbank, Vermoegensverwaltung",
        "aum": "Spezialist (Privatbank, kleinere Plattform — aktuell live verifizieren)",
        "hq": "Gamprin-Bendern, Liechtenstein",
        "dach": "Liechtenstein als Basis, Vertrieb DACH",
        "boutiques": "Private Banking, Vermoegensverwaltung, Family Office, Anlageberatung, Treuhand-Dienstleistungen",
        "core_competencies": "Private Banking fuer vermoegende Privatkunden und Family Offices, diskretionaere Vermoegensverwaltung, Wealth Structuring, Liechtensteinische Stiftungs- und Truststrukturen, Vermoegensnachfolge",
        "target_media_dach": "finews, NZZ, Finanz und Wirtschaft, Liechtensteiner Vaterland, Cash, Handelszeitung, private banking magazin, Elite Report, Capital, Manager Magazin Wealth, Handelsblatt Vermoegen",
        "tone": "diskret, vertraulich, Stil traditioneller Privatbank, Storytelling ueber Generationen-Vermoegen, eher zurueckhaltende Medienkommunikation",
        "taboo": "keine Kunden-Namen, keine Performance-Vergleiche, vorsichtig bei Steuer-/Offshore-Themen (Liechtenstein-Sensibilitaet), keine politischen Positionierungen",
    },
    "DNB AM": {
        "type": "Norwegischer Asset Manager, Tochter der DNB ASA (Norwegens groesste Bankgruppe)",
        "aum": "ca. EUR 80 Mrd. (Stand: aktuell live verifizieren)",
        "hq": "Oslo, Norwegen",
        "dach": "Vertrieb ueber Hubs in Luxemburg/Stockholm, deutscher Wholesale-Vertrieb (Frankfurt)",
        "boutiques": "Nordische Aktien (Renowned Strength), Globale Aktien, Technologie-Fonds (DNB Fund Technology bekannt), Fixed Income, Nachhaltigkeit (norwegische Praegung)",
        "core_competencies": "Nordische und globale Aktien (insb. Technologie und Nachhaltigkeit), nordische Anleihen, ESG-Integration mit norwegischer Ausrichtung (Norway-Fund-Vorbild), Stewardship",
        "target_media_dach": "Fonds Professionell, DAS INVESTMENT, Citywire, Institutional Money, Handelsblatt, Boersen-Zeitung, ETF Stream, Responsible Investor, e-fundresearch (Tech-Fokus)",
        "tone": "skandinavisch-sachlich, ESG-natuerlich (kein Marketing-Greenwashing), Tech-Expertise, langfristig orientiert",
        "taboo": "keine politischen Positionierungen (NATO/Russland), Norwegen-Oel-/Gas-Themen sensibel (Heimatmarkt-Bezug), keine Performance-Versprechen",
    },
    "Insight Investment": {
        "type": "Globaler Asset Manager, Tochter von BNY (Bank of New York)",
        "aum": "ca. $800+ Mrd. (Stand: aktuell live verifizieren)",
        "hq": "London, UK",
        "dach": "London als Hub, Vertrieb in Deutschland (Frankfurt), Schweiz, Wien",
        "boutiques": "Fixed Income (Schwerpunkt), LDI (Liability-Driven Investment, britische Pensionsfonds-Expertise), Currency Risk Management, Absolute Return Bond, ESG-Bonds",
        "core_competencies": "Fixed Income (alle Segmente), LDI (Marktfuehrer fuer britische Pensionskassen), Risk Management/Currency Overlay, Absolute Return, Klimainvestments und gruene Anleihen, taktische Asset Allocation",
        "target_media_dach": "Fonds Professionell, DAS INVESTMENT, Institutional Money, dpn, portfolio institutionell, Boersen-Zeitung, IPE, Risk.net, Anleihencheck",
        "tone": "akademisch-institutionell, datengetrieben, britischer Stil (sachlich, leicht ironisch), Pensionsfonds-Sprache, fuer hochkomplexe institutionelle Themen",
        "taboo": "BNY-Konzernthemen separat halten, keine politischen Stellungnahmen (Brexit-Sensibilitaet), Pensionskassen-Krisen vorsichtig adressieren",
    },
    "JOHCM": {
        "type": "J O Hambro Capital Management — britischer aktiver Aktien-Spezialist, Teil der Perpetual-Gruppe (Australien)",
        "aum": "ca. £35-40 Mrd. (Stand: aktuell live verifizieren)",
        "hq": "London, UK",
        "dach": "Vertrieb DACH ueber London/Frankfurt-Hub",
        "boutiques": "High-Conviction Active Equity-Fonds, autonome Fondsmanager-Teams (Boutique-Modell), regionale und globale Aktienstrategien",
        "core_competencies": "Aktiv gemanagte Aktien-Fonds (UK Equity, Global, Asia, Emerging Markets, US, European Select Values), High-Conviction Stockpicking, autonomes Fondsmanager-Modell (jedes Team eigenstaendig), Co-Investment der Manager",
        "target_media_dach": "Fonds Professionell, DAS INVESTMENT, Citywire, Boersen-Zeitung, Handelsblatt, IPE, Institutional Money, e-fundresearch",
        "tone": "klar pointiert (High Conviction), meinungsstark, traditionell britischer Investment-Stil, Storytelling ueber Einzeltitel-Theses",
        "taboo": "keine pauschalen Marktprognosen (passt nicht zum Stockpicking-Stil), Performance-Versprechen vermeiden, Konkurrenz-Vergleiche vermeiden",
    },
    "Maverix": {
        "type": "Maverix Securities AG — Schweizer Aktien-Boutique",
        "aum": "Spezialist (Boutique, kleineres Volumen — aktuell live verifizieren)",
        "hq": "Zuerich, Schweiz",
        "dach": "Schweiz, DACH-Vertrieb",
        "boutiques": "Long-Only Aktienfonds, qualitatives Stockpicking",
        "core_competencies": "Aktive Aktienauswahl mit Fokus auf Qualitaetsunternehmen, langfristige Investmenthorizonte, fundamentale Bottom-up-Analyse, Schweizer/Europa/Global Mandates",
        "target_media_dach": "finews, Finanz und Wirtschaft, Cash, NZZ, Handelszeitung, Fonds Professionell Schweiz, Citywire Schweiz",
        "tone": "schweizerisch-praezise, qualitativ-fundamental, langfristig orientiert, eher zurueckhaltend, Boutique-Stil",
        "taboo": "keine kurzfristigen Marktprognosen, keine spekulativen Themen, Konkurrenz-Boutiquen nicht kommentieren",
    },
}

CLIENTS = """- PGIM ($1,5 Bio. AuM): Institutional, Multi-Asset, Real Estate, Fixed Income, CLO
- T. Rowe Price: Active Equity, Multi-Asset, ETF-Strategie Europa
- MK Global Kapital (Luxemburg): Impact/Microfinance, EM, Tokenisierung, SME-Kredite
- Franklin Templeton ($1,74 Bio. AuM): Multi-Asset, EM, ETF, Tokenisierung
- Eurizon (Intesa Sanpaolo): Euro Fixed Income, EM Debt, ESG, Quantitative
- Bitcoin Suisse: Krypto-Finanzdienstleister, MiCA, Custody, Staking
- KKR: Private Equity, Infrastruktur, Real Estate, Credit
- Aegon Asset Management: Multi-Asset, Fixed Income, Verantwortungsvolles Investieren, niederlaendisch-britischer AM
- Bendura Bank: Liechtensteiner Privatbank, Vermoegensverwaltung, Family Office
- DNB Asset Management: Norwegischer AM, Nordische Aktien/Anleihen, Technologie, Nachhaltigkeit
- Insight Investment: $800+ Mrd. AuM, Fixed Income/LDI/Risk Management, BNY-Tochter
- JO Hambro Capital Management (JOHCM): Britischer aktiver AM, High-Conviction Equity-Fonds
- Maverix Securities: Schweizer Aktien-Boutique, Long-Only, qualitatives Stockpicking"""

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
            now.strftime("%Y%m%d"), now.strftime("%H:%M"), now.weekday() >= 5,
            now.weekday() == 0)  # is_monday flag

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
    "Eurizon": ["eurizon", "intesa sanpaolo"],
    "Bitcoin Suisse": ["bitcoin suisse"],
    "KKR": ["kkr", "kohlberg kravis"],
    "Aegon AM": ["aegon asset management", "aegon am"],
    "Bendura Bank": ["bendura bank", "bendura"],
    "DNB AM": ["dnb asset management", "dnb am", "dnb fund"],
    "Insight Investment": ["insight investment"],
    "JOHCM": ["johcm", "j.o. hambro", "jo hambro"],
    "Maverix": ["maverix securities", "maverix"],
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
    """Fetch client insights/news pages directly from their website with content extraction."""
    results = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; TE-Media-Intelligence/3.2; +https://te-communications.com)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")[:80000]  # First 80k chars
            
            # Extract main content from the landing page itself
            # Strip scripts, styles, navigation
            cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
            cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL|re.IGNORECASE)
            cleaned = re.sub(r'<nav[^>]*>.*?</nav>', '', cleaned, flags=re.DOTALL|re.IGNORECASE)
            cleaned = re.sub(r'<footer[^>]*>.*?</footer>', '', cleaned, flags=re.DOTALL|re.IGNORECASE)
            
            # Extract all text content (paragraphs)
            paragraphs = re.findall(r'<p[^>]*>([^<]{50,500})</p>', cleaned, re.IGNORECASE)
            page_text = " ".join(paragraphs[:20])[:3000]  # First 3000 chars of meaningful content
            
            articles = []
            
            # Pattern 1: <h2>/<h3> with link inside
            h_pattern = re.findall(r'<h[2-4][^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{15,150})</a>', cleaned, re.IGNORECASE)
            for href, title in h_pattern[:8]:
                if any(skip in title.lower() for skip in ["cookie", "privacy", "terms", "menu", "navigation", "search"]):
                    continue
                if href.startswith("/"):
                    base = "/".join(url.split("/")[:3])
                    href = base + href
                
                # Try to extract surrounding context for this article (excerpt)
                title_pos = cleaned.find(title)
                excerpt = ""
                if title_pos > 0:
                    # Look for paragraph after this title
                    after_title = cleaned[title_pos:title_pos+3000]
                    para_match = re.search(r'<p[^>]*>([^<]{40,400})</p>', after_title)
                    if para_match:
                        excerpt = re.sub(r'\s+', ' ', para_match.group(1)).strip()[:400]
                
                articles.append({
                    "client": client_name,
                    "title": re.sub(r'\s+', ' ', title).strip(),
                    "url": href,
                    "source_page": url,
                    "content": excerpt or page_text[:600],  # Excerpt or page-level fallback
                })
            
            # Pattern 2: Fallback for sites without h-pattern
            if not articles:
                a_pattern = re.findall(r'<a[^>]+href=["\']([^"\']+(?:insights?|articles?|news|press|research|outlook)[^"\']*)["\'][^>]*>([^<]{20,150})</a>', cleaned, re.IGNORECASE)
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
                        "content": page_text[:600],
                    })
            
            # If no articles but we got page content, capture as a generic entry
            if not articles and page_text and len(page_text) > 200:
                articles.append({
                    "client": client_name,
                    "title": f"Inhalt von {url.split('/')[-2] if url.endswith('/') else url.split('/')[-1] or 'Hauptseite'}",
                    "url": url,
                    "source_page": url,
                    "content": page_text[:800],
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
    return unique[:12]  # Max 12 per client (was 10)


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
    
    # DYNAMIC TIME WINDOW: Montag faengt Wochenende auf (Fr-Mittag bis Mo-frueh)
    # Andere Werktage: Standard 28h-Fenster
    now = datetime.now(timezone.utc)
    if now.weekday() == 0:  # Monday (0=Mon, 6=Sun)
        # Catch full weekend: from Friday 12:00 UTC until now
        # ca. 67h zurueck bei Lauf Mo 06:00 UTC = 67h bis Fr 11:00 UTC
        cutoff = now - timedelta(hours=72)
        print(f"  Monday-Modus: 72h-Fenster aktiv (faengt Wochenend-Berichterstattung seit Freitag-Mittag auf)")
    else:
        # Tu-Fr standard window
        cutoff = now - timedelta(hours=28)
    
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


def api_call(client, model, max_tokens, messages, tools=None, retries=4, wait=60, use_streaming=False):
    """API call with retry + automatic model fallback. Streams if needed for long operations."""
    current_model = model
    for i in range(retries):
        try:
            kw = {"model": current_model, "max_tokens": max_tokens, "messages": messages}
            if tools: kw["tools"] = tools
            
            if use_streaming:
                # Stream the response (required for long-running operations >10 min)
                full_text = ""
                content_blocks = []
                with client.messages.stream(**kw) as stream:
                    for text in stream.text_stream:
                        full_text += text
                    final_message = stream.get_final_message()
                # Return a response-like object with the same interface as non-streaming
                return final_message, current_model
            else:
                return client.messages.create(**kw), current_model
        except Exception as e:
            err = str(e).lower()
            # Auto-enable streaming if API requires it
            if "streaming is required" in err and not use_streaming:
                print(f"  API requires streaming for this size — enabling streaming mode...")
                use_streaming = True
                continue
            if any(x in err for x in ["overloaded","rate_limit","529","429"]):
                if i == 1 and current_model != MODEL_FALLBACK:
                    print(f"  {current_model} unavailable -> fallback to {MODEL_FALLBACK}")
                    current_model = MODEL_FALLBACK
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
    date_str, date_file, time_str, is_weekend, is_monday = get_today_str()
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
    for cname, items in client_insights.items():
        block = f"\n=== {cname} — Aktuelle Eigen-Inhalte (Webseite gerade gecrawlt) ===\n"
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
    if is_monday:
        wknd = "\nMONTAG-MODUS — WOCHENEND-AUFHOLER: Beruecksichtige die KOMPLETTE Berichterstattung von Freitag-Mittag bis Montag-frueh (72h-Fenster). Wochenende ist NICHT zu vernachlaessigen — Markt-Bewegungen, Wirtschaftspresse-Sonntagsausgaben (FAS, NZZ am Sonntag, SonntagsBlick), politische Entwicklungen und internationale Markt-Sessions am Sonntag-Abend (Asien-Eroeffnung) muessen erfasst werden. Was wurde am Wochenende publiziert, was Montag den Markt bewegt?\n"
    elif is_weekend:
        wknd = "\nWochenende: Fokus auf Analysen, Ausblicke, Hintergrund.\n"
    else:
        wknd = ""

    # Build client profile context block (stable facts only)
    profile_block = ""
    for cname, p in CLIENT_PROFILES.items():
        profile_block += f"\n[{cname}]\n"
        profile_block += f"  Typ: {p['type']} | AuM: {p['aum']} | HQ: {p['hq']} | DACH: {p['dach']}\n"
        profile_block += f"  Kernkompetenzen: {p['core_competencies']}\n"
        profile_block += f"  Zielmedien DACH: {p['target_media_dach']}\n"
        profile_block += f"  Tonfall: {p['tone']}\n"
        profile_block += f"  Tabu: {p['taboo']}\n"
    
    p1 = f"""Du bist seit 25 Jahren Senior Medienanalyst und Strategy Director bei einer der weltweit fuehrenden Strategieberatungen fuer Finanzkommunikation. Du arbeitest fuer die Top-PR-Agenturen weltweit (Edelman Smithfield, FGS Global, Brunswick, Teneo, FTI Consulting). Du hast in dieser Funktion mehr als 5.000 Tagesreports fuer institutionelle Asset Manager und Private-Markets-Haeuser erstellt. Du wirst in Fachkreisen als der praezisesteste Marktanalyst gehandelt.

Du denkst tiefer als ein Reporter. Tiefer als ein Sell-Side-Analyst. Tiefer als ein Buy-Side-Researcher. Du verbindest:
- Makro-Daten mit Mikro-Folgen (Margen, Spreads, Refinanzierung)
- Cross-Asset-Effekte (Aktien/Bonds/FX/Commodities/Private)
- Cross-Region-Effekte (DACH, Europa, USA, EM, Asien)
- Historische Analogien (1973, 1990, 1998, 2008, 2018, 2020)
- Sentiment-Verschiebungen (Konsens vs. Kontrarian)
- Was die Berichterstattung NICHT zeigt (blinde Flecken)

Du denkst SCHRITT FUER SCHRITT. Du arbeitest dich von 1st-Order-Effekten zu 2nd-, 3rd-, 4th-Order durch. Du erkennst Widerspruechen zwischen Datenpunkten als Signal, nicht als Stoerung.

DEIN ANALYSE-RAHMEN (auf jedes Top-Thema anwenden):

A) FAKTEN-EBENE: Was genau ist passiert? Konkrete Zahlen, Quellen, Zeit.

B) KAUSALKETTE (mehrstufig):
   - 1st-Order: direkte Marktreaktion
   - 2nd-Order: Folgewirkung auf Bewertungen, Spreads, Margen
   - 3rd-Order: strukturelle Effekte auf Anlageklassen, Sektoren, Regionen
   - 4th/5th-Order: politische, regulatorische, kapitalmarkt-strukturelle Folgen

C) CROSS-ASSET/CROSS-REGION-VERKNUEPFUNGEN: 
   Was sagt diese Bewegung in Verbindung mit anderen Datenpunkten? 
   z.B. "Brent +14% bei gleichzeitig fallenden DAX-Banken — das deutet auf X"

D) HISTORISCHE ANALOGIE:
   Wann gab es eine vergleichbare Konstellation? Was folgte damals?

E) SZENARIO-DENKEN (3 Pfade):
   - Bull-Case: Wahrscheinlichkeit X%, Trigger Y, Folge Z
   - Base-Case: ...
   - Bear-Case: ...

F) WIDERSPRUECHE / SIGNALE:
   Welche Datenpunkte passen heute NICHT zusammen? Das ist oft das wichtigste.

G) KONSENS vs. KONTRARIAN:
   Was ist die Mainstream-Lesart? Was waere die kontrarische — und welche Belege gibt es?

H) BLINDE FLECKEN:
   Was muesste in der Berichterstattung sein, ist es aber nicht?

Stand: {date_str}, {time_str} CET. Erfasse {"die LETZTEN 72 STUNDEN (Wochenend-Aufholer)" if is_monday else "die LETZTEN 24 STUNDEN"} bis 7 TAGE.{wknd}

=== TEIL A: MARKT-RECHERCHE ===

ALLGEMEINE RSS-SCHLAGZEILEN ({len(rss_items)} Artikel, {health['sources']} Quellen, abgerufen {time_str} CET):
{rss_block}

KUNDEN-SPEZIFISCHE TREFFER aus dedizierten Kunden-Feeds ({len(client_specific)} Treffer):
{client_specific_block}

KUNDEN-ERWAEHNUNGEN IN ALLG. MEDIEN:
{mentions_block}
{trend_block}

=== TEIL B: KUNDEN-EIGEN-INHALTE (DIREKT VON DEN WEBSEITEN GECRAWLT) ===

Diese Inhalte wurden JUST EBEN von den Kunden-Webseiten gescraped — Goldwert fuer Presseverteiler-Versand:
{insights_total_block}

=== TEIL C: STABILE KUNDEN-PROFILE (Strukturwissen) ===

{profile_block}

=== AUFGABE ===

Themenfelder: {', '.join(THEMENFELDER)}
{diff}

AUSGABE (beginne direkt, keine Einleitung):

## Datenlage und Recherche-Status
3-4 Saetze: Welche Quellen waren heute gut auswertbar? Welche eingeschraenkt? Gesamt-Belastbarkeit?

## Top-Themen des Tages
Die 5 wichtigsten Markt-Themen heute in je 2 Saetzen. Hier reicht knappe Form — Tiefe kommt darunter.

## Marktbild des Tages
Gesamtcharakter. Uebergreifendes Narrativ. Was ist die METATGESCHICHTE, die die einzelnen Themen verbindet?

## Tiefenanalyse — Top-Themen

Fuer JEDES der Top-Themen — wende den Analyse-Rahmen A bis H an. Nicht alle 8 Punkte muessen explizit aufgefuehrt sein, aber dein Ergebnis muss erkennbar darauf basieren:

### [Thema 1 — pointierter Titel mit These, nicht nur Schlagwort]

**A) Fakten-Ebene:**
- [konkrete Zahlen, Datum, Quelle]

**B) Kausalkette:**
- 1st-Order: [direkte Marktreaktion]
- 2nd-Order: [Folge auf Margen/Spreads/Bewertungen]
- 3rd-Order: [strukturelle Folge fuer Anlageklassen/Sektoren]
- 4th/5th-Order: [politische/regulatorische/strukturelle Folgen]

**C) Cross-Asset/Cross-Region-Verknuepfung:**
- [welche andere Marktbewegung verstaerkt das oder steht im Widerspruch?]

**D) Historische Analogie:**
- [vergleichbare Konstellation: wann, was folgte, Unterschiede heute]

**E) Drei Szenarien (naechste 4 Wochen):**
- Base-Case (XX%): [Trigger, Folge]
- Bull-Case (XX%): [Trigger, Folge]
- Bear-Case (XX%): [Trigger, Folge]

**F) Widerspruch / Signal:**
- [welcher Datenpunkt passt heute NICHT zum Mainstream-Narrativ — und was bedeutet das?]

**G) Konsens vs. Kontrarian:**
- Mainstream: [Lesart in den meisten Medien]
- Kontrarian: [alternative Lesart mit Belegen]

**H) Blinder Fleck:**
- [was fehlt in der heutigen Berichterstattung — und ist das eine Pitch-Chance?]

**Belastbarkeit der Quellenlage:** hoch / mittel / niedrig
**Veraenderung gegenueber Vortagen:** [konkret]
**Sentiment-Lage:** [positiv / neutral / kritisch — fuer wen?]

[gleiche Struktur fuer Themen 2, 3, 4, 5]

## Mehrtages-Trends
Was zieht sich seit Tagen durch? Was eskaliert/klingt ab? Welche Themen-Zyklen erkennst du?

## Unterdiskutierte Themen — White Spaces
Welche Themen sind heute KAUM in den Medien, koennten aber gepitcht werden? Wo gibt es ein Erzaehl-Vakuum?

## Konkurrenz-Beobachtung
Welche grossen Wettbewerber unserer Kunden (BlackRock, Vanguard, Fidelity, Goldman Sachs AM, JPMorgan AM, Amundi, DWS, Allianz GI, AXA IM, Schroders, Invesco, State Street, Northern Trust, Apollo, Blackstone, Carlyle, TPG, Brookfield, EQT, Permira, Advent, CVC, Coinbase, Kraken, Gemini, Vontobel, GAM, Robeco, Pictet, UBS AM, Credit Suisse AM, Lombard Odier IM, Carmignac, Comgest) sind heute in den Medien? Was kommunizieren sie? Wo koennten unsere Kunden kontern?

## Live-Recherche pro Kunde
Fuer JEDEN der 13 Kunden FUEHRE WEB-SEARCH DURCH:

### [Kundenname]
- **Aktuelle DACH-Sprecher** (Stand 2026, NUR live verifiziert!):
  Suche per Web Search auf der Unternehmensseite, LinkedIn, juengsten Pressemeldungen. NUR Personen, die 2025/2026 nachweislich aktiv sind. Bei Unsicherheit: "nicht aktuell verifizierbar — bitte intern abstimmen".
- **Heutige direkte Erwaehnungen**: Kontext, Sprecher, Sentiment.
- **Themen-Schwerpunkte des Hauses aktuell**: Aus den oben gecrawlten Eigen-Inhalten + Live-Recherche.

KRITISCH: Bei Sprechern und aktuellen Statements NICHTS halluzinieren.

## Themen-Priorisierung
| Prio | Thema | Beste Kunden | Dringlichkeit | Medienarbeits-Eignung |
|------|-------|--------------|---------------|------------------------|
| 1 | ... | ... | hoch/mittel/niedrig | hoch/mittel/niedrig |
| ... bis Prio 7-8 | | | | |

Bei fehlendem Stichtagsanlass ehrlich "niedrig / niedrig" mit Begruendung.

## Termin-Vorschau 7 Tage
Datum, Uhrzeit, Land, Termin, Relevanz.

## Gesamtfazit
2-3 Saetze zum uebergeordneten Narrativ. Plus: Welcher Pitch-Winkel ist der differenzierendste fuer heute (zweite Ebene, nicht das Offensichtliche)?

## Quellenverzeichnis
Hier muessen ALLE Quellen aufgefuehrt werden, nicht nur die Top-Treffer. Ziel: Transparenz ueber die Recherche-Breite.

Format pro Eintrag:
- Medium — "Artikeltitel" (Datum, Uhrzeit falls bekannt) — URL falls verfuegbar

Strukturiere nach Kategorien:
**Deutsche Leitmedien** (Handelsblatt, FAZ, SZ, WiWo, Spiegel, manager-magazin, Welt, Tagesschau, n-tv, Stern, ZEIT, Tagesspiegel, Bild, Capital, Focus, finanzen.net)
**Deutsche Fachmedien** (Boersen-Zeitung, Fonds Professionell, DAS INVESTMENT, Citywire, Institutional Money, Private Banking Magazin, altii, BondGuide, Anleihencheck, exxecnews, fundresearch, Boerse Online, dpn, e-fundresearch, Morningstar)
**Schweiz/Oesterreich** (NZZ, FuW, Cash, finews, Handelszeitung, moneycab, investrends, Die Presse, Der Standard, Boersen-Kurier)
**International** (Reuters, FT, Bloomberg, BBC, CNBC, WSJ, Economist, Guardian, Fortune, IPE, Pensions & Investments, Institutional Investor, Risk.net, GlobalCapital, ETF Stream)
**Krypto/Spezial** (CoinDesk, CoinTelegraph, The Block, Decrypt, Bitcoin Magazine, OilPrice, S&P Commodities, Responsible Investor, ESG Today)
**Institutionen/Primaerquellen** (EZB, BIS, Fed, Destatis, Bundesbank, IEA, OECD)
**Kunden-Eigeninhalte** (Webseiten der Kunden, gerade gecrawlt)

Wenn aus einer Kategorie keine Quellen ausgewertet wurden: "keine relevanten Treffer heute" schreiben. Niemals Kategorie weglassen.

QUALITAETSREGELN — ABSOLUT KRITISCH:
- Sprecher nur wenn 2025/2026 nachweislich aktiv (sonst "nicht verifizierbar").
- Bei JEDER Zahl: Quelle + Datum.
- Nicht halluzinieren. Keine erfundenen URLs/Zitate/Personen.
- Englischsprachige Artikel gruendlich ins Deutsche uebertragen.
- Einfache, klare Sprache. Keine Telegrammstil-Sprache.
- ZWEITE EBENE statt Offensichtliches. Differenzierung kommt aus Zweitrundeneffekten.
- Wenn fuer ein Thema/Kunden heute kein Stichtagsanlass existiert: ehrlich sagen.
- Denke SCHRITT FUER SCHRITT. Verknuepfe Datenpunkte aktiv.
- Wenn Datenpunkte sich widersprechen: das ist ein wichtiges Signal, nicht ein Problem."""

    print(f"[{time_str}] PASS 1: Opus 4.7 + Web Search (most capable model, streaming)...")
    t1s = time.time()
    r1, m1 = api_call(client, MODEL_RESEARCH, MAX_TOKENS_RESEARCH,
                       [{"role":"user","content":p1}],
                       tools=[{"type":"web_search_20250305","name":"web_search"}],
                       use_streaming=True)
    txt1 = "".join(b.text for b in r1.content if hasattr(b,"text"))
    t1 = round(time.time()-t1s, 1)
    print(f"[{time_str}] PASS 1: {len(txt1)} chars via {m1} in {t1}s")

    # --- PASS 1.5: Client Knowledge Profile Generation ---
    print(f"[{time_str}] Waiting 30s before Pass 1.5...")
    time.sleep(30)

    print(f"[{time_str}] PASS 1.5: Generating client knowledge profiles (Sonnet 4.6)...")
    t15s = time.time()
    
    client_knowledge_block = ""
    for cname in CLIENT_PROFILES.keys():
        # Aggregate crawled content for this client
        crawled = client_insights.get(cname, [])
        crawled_text = ""
        for item in crawled[:8]:  # Up to 8 items per client
            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "")[:1500]  # First 1500 chars per item
            crawled_text += f"\n--- {title} ({url}) ---\n{content}\n"
        
        # Get mentions of this client today
        mentions_for_client = client_mentions.get(cname, [])[:5]
        mentions_text = ""
        for m in mentions_for_client:
            mentions_text += f"- {m.get('s','')}: {m.get('t','')}\n"
        
        # Build profile knowledge prompt
        profile = CLIENT_PROFILES.get(cname, {})
        kp_prompt = f"""Du bist Senior Strategy Director fuer Finanzkommunikation. Du erstellst ein PRAEZISES, AKTUELLES Wissensprofil fuer {cname} — basierend ausschliesslich auf den frisch gecrawlten Eigeninhalten und Live-Mentions.

KUNDEN-STAMMDATEN:
- Typ: {profile.get('type','')}
- AuM: {profile.get('aum','')}
- HQ: {profile.get('hq','')}
- DACH: {profile.get('dach','')}
- Kernkompetenzen: {profile.get('core_competencies','')}

FRISCH GECRAWLTE EIGENINHALTE (heute, vom Kunden selbst):
{crawled_text if crawled_text else "[Keine Eigeninhalte heute gecrawlt — Crawling-Hindernisse oder Cookie-Walls]"}

LIVE-MENTIONS HEUTE (Kunde wurde erwaehnt):
{mentions_text if mentions_text else "[Keine Live-Mentions heute]"}

ERSTELLE EIN STRUKTURIERTES WISSENSPROFIL (max 600 Worte, deutsch):

### {cname} — Wissensprofil heute

**Aktuelle strategische Botschaften (aus Eigeninhalten der letzten 30 Tage):**
- [Botschaft 1: konkrete Argumentationslinie + Beleg aus Eigeninhalten]
- [Botschaft 2]
- [Botschaft 3 — falls aus Eigeninhalten erkennbar]

**Aktuell live verifizierte Sprecher (aus Eigeninhalten oder Mentions):**
- [Name, Rolle] — Quelle: [URL/Mention] — Themenfokus: [...]
- WENN keine live verifizierten Sprecher: "Keine Sprecher heute live verifiziert. Bitte intern abstimmen."

**Aktueller Content-Output (Top 3 Beitraege):**
- [Titel + Datum + URL — falls aus Crawling vorhanden]

**Positionierungs-Profil (was will das Haus heute kommunizieren):**
- [In 2-3 Saetzen: Wofuer steht das Haus aktuell? Welche Differenzierung sucht es?]

**Gemiedene Themen (aus Tabu-Profil + aktuellen Botschaften):**
- [Was wird aktuell vermieden]

**Kommunikative Opportunitaet HEUTE:**
- [Welcher Anschluss aus der Marktanalyse heute waere fuer das Haus besonders wertvoll? Begruendung in 2 Saetzen]

REGELN:
- KEINE Halluzinationen. Wenn keine Eigeninhalte gecrawlt wurden: ehrlich sagen "Crawling heute fehlgeschlagen — Profil basiert nur auf Stammdaten, keine aktuelle Verifikation moeglich."
- KEINE veralteten Sprecher-Angaben aus Modellwissen. Nur was heute belegt ist.
- Maximal 600 Worte. Knapp, praezise, sachlich.
"""
        
        try:
            kp_response, _ = api_call(client, MODEL_FALLBACK, 2000,
                                      [{"role":"user","content":kp_prompt}],
                                      use_streaming=False)
            kp_text = "".join(b.text for b in kp_response.content if hasattr(b,"text"))
            client_knowledge_block += "\n" + kp_text + "\n"
            print(f"  [Pass 1.5] {cname}: {len(kp_text)} chars knowledge profile generated")
        except Exception as e:
            print(f"  [Pass 1.5] {cname}: profile generation failed ({e}) — using stable profile only")
            client_knowledge_block += f"\n### {cname} — Wissensprofil heute\n[Profil heute nicht generierbar — bitte mit Stammdaten arbeiten]\n"
    
    t15 = round(time.time()-t15s, 1)
    print(f"[{time_str}] PASS 1.5 complete: {len(client_knowledge_block)} chars in {t15}s")

    # --- PASS 2: Positioning ---
    print(f"[{time_str}] Waiting 30s before Pass 2...")
    time.sleep(30)

    # Build profile + insights summary for Pass 2 (compact)
    insights_summary = "\n".join([f"\n[{c}] {len(items)} Eigen-Inhalte gefunden:\n" + "\n".join(f"  - {i['title']} → {i['url']}" for i in items[:4]) for c, items in client_insights.items()])
    
    p2 = f"""Du bist seit 25 Jahren Senior Strategy Director fuer Finanzkommunikation in DACH und arbeitest fuer eine der weltweit fuehrenden Strategieberatungen (Edelman Smithfield, FGS Global, Brunswick, Teneo). Du warst zuvor 15 Jahre Wirtschafts- und Finanzjournalist (Handelsblatt, Boersen-Zeitung, Reuters). Du verbindest beide Perspektiven: Du weisst, was Journalisten wirklich brauchen — und Du weisst, was Asset Manager pitchen sollten, um ihre Reputation und Positionierung zu staerken (nicht zu schwaechen).

═══════════════════════════════════════════════════════════════
DEINE AUFGABE HEUTE: SYSTEMATISCHE PITCH-HERLEITUNG
═══════════════════════════════════════════════════════════════

Du bekommst:
1. LIVE-MARKTANALYSE von heute ({date_str}) — was sind die Top-Themen
2. TIEFE KUNDEN-WISSENSPROFILE — fuer jeden der 13 Kunden ein aktuelles, taeglich neu generiertes Verstaendnis von Botschaften, Sprechern, Inhalten, Positionierung
3. DIREKT GECRAWLTE EIGEN-INHALTE der Kunden (frische Materialien)
4. KUNDEN-MENTIONS heute (wer wurde wo erwaehnt)

Du erstellst daraus eine PYRAMIDE in 5 STUFEN. Jede Stufe baut auf der vorherigen auf. Pitches sind das ERGEBNIS, nicht der Anfang.

═══════════════════════════════════════════════════════════════
DIE 14 PITCH-KRITERIEN (Praxis-Standard fuer DACH-Wirtschaftspresse)
═══════════════════════════════════════════════════════════════

INHALTLICHE KRITERIEN (was macht den Pitch wertvoll?):
1. AKTUALITAET — konkreter Hook in den letzten 72h
2. NEUHEIT / UNTERDISKUTIERTHEIT / BLINDER FLECK — was uebersehen alle anderen?
3. DIFFERENZIERUNG — eigene These, Kontrarian, 2nd-Order-Effekt
4. KONFLIKT / SPANNUNG — Reibung, gebrochene Erwartung
5. BELEGBARKEIT — konkrete Zahl, Trade, Anekdote, Studie

PERSONEN-KRITERIEN (wer pitcht?):
6. SPRECHER-AUTORITAET — Asset-Klassen-Erfahrung, Track Record
7. LIVE-VERIFIKATION — Sprecher 2025/2026 in aktueller Quelle bestaetigt — PFLICHT
8. CHARAKTER — Profil, Wiedererkennbarkeit, Zitierfaehigkeit

HANDWERKLICHE KRITERIEN (wie wird gepitcht?):
9. MEDIEN-FIT — Story passt zu Ressort, Tonalitaet, Format
10. TIMING zur REDAKTION — Pitch zur richtigen Zeit fuer Redaktionsschluss
11. SERVICEGEDANKE — Sprecher-Verfuegbarkeit, Material, Bilder, Zitate
12. EXKLUSIVITAET — wem geht der Pitch noch parallel?

STRATEGISCHE KRITERIEN:
13. VERBRENNUNGS-RISIKO — wann letzter Pitch zu Sprecher/Medium?
14. POSITIONIERUNGS-FIT — staerkt der Pitch die Reputation des Hauses oder verwaessert er sie?

═══════════════════════════════════════════════════════════════
PITCH-KILLER (sofortiges Verwerfen)
═══════════════════════════════════════════════════════════════
- Story stand heute schon in 3+ DACH-Medien
- Sprecher kann nur Konsens-Meinung wiedergeben
- Sprecher passt nicht zur Asset-Klasse
- Sprecher nicht 2025/2026 live verifiziert
- Pitch widerspricht der aktuellen Positionierung des Hauses
- Buzzwords ohne Substanz ("disruptiv", "robust", "ganzheitlich")
- Generische "Markteinschaetzung von..." Pitches

PITCH-AUFNAHME-SCHWELLE: 
Mindestens 3 von 5 inhaltlichen Kriterien mit Bewertung ★★★★+
UND Sprecher live verifiziert (Personen-Kriterium 7)
UND Positionierungs-Fit ≥ ★★★★

═══════════════════════════════════════════════════════════════
KUNDEN-WISSENSPROFILE (taeglich neu generiert)
═══════════════════════════════════════════════════════════════
{client_knowledge_block}

═══════════════════════════════════════════════════════════════
KUNDEN-PROFILE (stabile Strukturfakten)
═══════════════════════════════════════════════════════════════
{profile_block}

═══════════════════════════════════════════════════════════════
LIVE-MARKTANALYSE VON HEUTE
═══════════════════════════════════════════════════════════════
{txt1[:8000]}

═══════════════════════════════════════════════════════════════
DIREKT GECRAWLTE EIGEN-INHALTE DER KUNDEN
═══════════════════════════════════════════════════════════════
{insights_summary}

═══════════════════════════════════════════════════════════════
KUNDEN-MENTIONS HEUTE
═══════════════════════════════════════════════════════════════
{mentions_block}

═══════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════

ERSTELLE JETZT DEN BERICHT IN DIESER REIHENFOLGE:

═══════════════════════════════════════════════════════════════
## Themen-Filter — Was ist heute pitchbar?
═══════════════════════════════════════════════════════════════

Wende die 5 INHALTLICHEN Kriterien systematisch auf die Top-Themen aus der Marktanalyse an. Pro Thema:

### [Thema X — Titel]

**Inhaltliche Bewertung:**
- Aktualitaet:        ★★★★★ — [konkreter Hook + Datum]
- Neuheit:            ★★★★  — [was uebersehen andere?]
- Differenzierung:    ★★★   — [eigener Winkel?]
- Konflikt:           ★★★★  — [welche Reibung?]
- Belegbarkeit:       ★★★★  — [welche Daten?]

**Status:** ✓ pitchbar / ✗ verworfen — [knappe Begruendung]

Bewerte mindestens 6-8 Themen. Verworfene Themen ehrlich begruenden ("stand heute schon in N DACH-Medien" / "kein Differenzierungspotenzial" / "Konsensgemeinplatz").

ERGEBNIS: Die pitchbaren Themen werden in Stufe 2 weiterverarbeitet.

═══════════════════════════════════════════════════════════════
## Sprecher-Mapping — Wer von uns kann pitchen?
═══════════════════════════════════════════════════════════════

Fuer JEDES pitchbare Thema aus der Filterung: Welcher unserer 13 Kunden hat den richtigen Sprecher?

### [Pitchbares Thema]

Asset-Klasse: [Fixed Income / Equity / Real Estate / Multi-Asset / Krypto / etc.]

Bestpassende Haeuser (mit Live-Verifikations-Status):
- ★★★★★ [Kunde] ([Sprecher-Name], [Rolle]) ✓ live verifiziert ([Quelle + Datum])
- ★★★★  [Kunde] ([Sprecher]) ✓ live verifiziert
- ★★★   [Kunde] — Live-Verifikation ausstehend
- ★★    [Kunde] — Asset-Klasse passt, aber kein Sprecher live verifiziert

EMPFEHLUNG: [Welcher Kunde + warum — Sprecher-Fit + Track Record + aktuelle Positionierung]

WENN KEIN PASSENDER SPRECHER: ehrlich sagen "Heute kein Pitch zu diesem Thema moeglich — Begruendung: [...]"

═══════════════════════════════════════════════════════════════
## Pitch-Empfehlungen (hergeleitet)
═══════════════════════════════════════════════════════════════

NUR fuer die Themen-Kunden-Kombinationen, die durch Stufe 1+2 gekommen sind UND die Pitch-Aufnahme-Schwelle erfuellen.

ERWARTUNG: 4-7 Pitches insgesamt (nicht mehr!). Lieber wenige, hergeleitete Pitches als viele oberflaechliche.

Pro Pitch dieser Block:

### PITCH [N] von [Total] — [Hook in einem Satz]

**HERLEITUNG (warum dieser Pitch?)**
- Markt-Anlass: [Konkrete Story aus Marktanalyse mit Quelle + Datum]
- Pitch-Luecke: [Was sagen andere Haeuser dazu? Was uebersehen sie?]
- Anschluss-Kunde: [Welcher unserer 13 Kunden — und warum]
- Sprecher-Match: [Welcher Sprecher dieses Hauses — und warum genau diese Person]
- Positionierungs-Fit: [Wie passt der Pitch zur AKTUELLEN Botschaftslinie des Hauses laut Wissensprofil]

**INHALTLICHE BEWERTUNG (Pflicht: 3 von 5 mit ≥★★★★)**
- Aktualitaet:       ★★★★★  [konkrete Begruendung]
- Neuheit:           ★★★★   [was niemand sonst sagt]
- Differenzierung:   ★★★★★  [konkreter Take]
- Konflikt:          ★★★    [welche Reibung]
- Belegbarkeit:      ★★★★   [welche Daten]
✓ FILTER BESTANDEN

**PERSONEN-CHECK (alle Pflicht)**
- Sprecher: [Name + Rolle]
- Asset-Klassen-Fit: ✓ [Begruendung]
- Live-Verifikation: ✓ [Quelle + Datum]
- Charakter / Track Record: [bisherige Aussagen, Zitierfaehigkeit]

**HANDWERK**
- Zielmedium: [konkretes Medium + Ressort]
- Backup-Medien: [2-3 weitere Optionen]
- Timing: [bis wann muss Pitch raus?]
- Service: [Sprecher-Verfuegbarkeit, Material, Bilder, Zitate]
- Exklusivitaet: [exklusiv / parallel an X Haeuser, mit Frist]

**STRATEGIE**
- Verbrennungs-Check: [letzter Pitch zu diesem Sprecher / Medium — falls bekannt]
- Positionierungs-Fit: ★★★★★ — [wie staerkt dieser Pitch die Reputation des Hauses?]
- Konkurrenz-Kontext: [was haben BlackRock/DWS/Apollo/Allianz GI dazu schon gesagt?]

**PITCH-MATERIAL (fertig zum Versenden)**

E-Mail-Betreff: "[konkreter Betreff, max 70 Zeichen]"

Hook-Mail an Journalist:
"[Sehr geehrter Herr/Frau [...], 4-6 Saetze, im Stil eines erfahrenen Pressesprechers]"

3 Zitate-Vorschlaege fuer den Sprecher:
- "[Konkrete, pointierte Aussage — kann Journalist 1:1 zitieren]"
- "[Zweite These — kontrastierend oder vertiefend]"
- "[Dritte Aussage — mit konkreter Zahl/Daten]"

Hintergrund-Briefing (Stichpunkte fuer Journalisten-Recherche):
- [Datenpunkt 1]
- [Datenpunkt 2]
- [Hauseigene Studie/Outlook zum Andocken — URL falls vorhanden]
- [Historische Parallele]

═══════════════════════════════════════════════════════════════
## Kunden-Sicht — Was bedeutet das pro Kunde?
═══════════════════════════════════════════════════════════════

KUNDEN MIT PITCH HEUTE:
[Liste der Kunden + entsprechende Pitch-Nummer + Hook in 1 Zeile]

KUNDEN OHNE PITCH HEUTE:
[Liste mit ehrlicher Begruendung pro Kunde:]
- [Kunde] — [Begruendung: kein Themen-Anschluss / Live-Sprecher-Verifikation ausstehend / Themen ausserhalb Kernkompetenzen / kein Pitch-Niveau heute]

EHRLICHE EINORDNUNG:
[N von 13 Kunden haben heute einen Pitch. Das ist normal — Pitch-Tage sind dispers. Empfehlung: fokussierte Bearbeitung der N Pitches statt Verduennung durch erzwungene Pitches.]

═══════════════════════════════════════════════════════════════
ABSOLUTE QUALITAETSREGELN
═══════════════════════════════════════════════════════════════

- Sprecher NUR, wenn live verifiziert in den Wissensprofilen oder in der Live-Marktanalyse
- Falls nicht verifiziert: "Sprecher intern abstimmen — Profil legt [Name] nahe (zuletzt zitiert [Datum, Quelle])"
- KEINE Buzzwords ("ganzheitlich", "robust", "disruptiv")
- KEINE Trading-Sprache ("Overweight", "Underweight")
- These muss POINTIERT sein — Reibung, nicht Diplomatie
- Aufhaenger MUSS konkrete Schlagzeile/Datenpunkt aus den letzten 72h sein, mit Quelle
- Pitch-Mail-Vorschlag muss so sein, dass TE-Berater nur noch personalisiert
- Wenn Pitch das Profil-Tabu streift: NICHT vorschlagen, Alternative bieten
- KEIN Telegrammstil, aber auch keine PR-Floskeln
- Schreibstil wie ein erfahrener Wirtschaftsjournalist, nicht wie eine PR-Agentur
- LIEBER WENIGER ABER BESSER — keine erzwungenen Pitches

═══════════════════════════════════════════════════════════════
"""

    print(f"[{time_str}] PASS 2: Sonnet 4.6 journalist-grade pitch crafting (streaming)...")
    t2s = time.time()
    r2, m2 = api_call(client, MODEL_POSITIONING, MAX_TOKENS_POSITIONING,
                       [{"role":"user","content":p2}],
                       use_streaming=True)
    txt2 = "".join(b.text for b in r2.content if hasattr(b,"text"))
    t2 = round(time.time()-t2s, 1)
    print(f"[{time_str}] PASS 2: {len(txt2)} chars via {m2} in {t2}s")

    # --- Combine + Save ---
    # REORDERING: Pass 1 has Termine + Gesamtfazit + Quellenverzeichnis at end.
    # Pass 2 has Pitches at end. We want order: Pass1-Analytics + Pass2-Pitches + Pass1-Termine/Fazit/Quellen
    
    # Try to split Pass 1 at "## Termin-Vorschau" to insert Pass 2 BEFORE Termine
    split_marker = "## Termin-Vorschau"
    if split_marker in txt1:
        idx = txt1.find(split_marker)
        txt1_main = txt1[:idx].rstrip()
        txt1_tail = txt1[idx:]  # Termine + Gesamtfazit + Quellenverzeichnis
        full = txt1_main + "\n\n" + txt2 + "\n\n" + txt1_tail
    else:
        # Fallback: just concatenate
        full = txt1 + "\n\n" + txt2
    
    # === AUTOMATISCH GENERIERTES VOLLSTAENDIGES QUELLENVERZEICHNIS ===
    # Aus den tatsaechlich erfolgreich abgerufenen RSS-Items
    sources_by_category = {}
    for item in rss_items:
        src = item.get("s", "unknown").lower()
        # Kategorisierung
        if any(d in src for d in ["handelsblatt", "faz", "sueddeutsche", "wiwo", "spiegel", "manager-magazin", "tagesschau", "n-tv", "welt", "tagesspiegel", "zeit", "stern", "finanzen.net", "bild", "capital", "focus"]):
            cat = "Deutsche Leitmedien"
        elif any(d in src for d in ["fondsprofessionell", "dasinvestment", "citywire.de", "institutional-money", "private-banking", "altii", "portfolio-institutionell", "fundresearch", "fundview", "boerse-online", "anleihencheck", "bondguide", "exxecnews", "dpn", "e-fundresearch", "morningstar", "asscompact", "versicherungswirtschaft", "finanzwelt", "intelligent-investors", "boersen-zeitung", "dpa", "euro-magazin", "iz.de", "thomas-daily", "4investors", "onvista", "t-online", "dfpa", "wallstreet-online", "boersennews", "finanznachrichten", "ariva", "finanzen100", "finanztreff", "bankmagazin", "bankinghub", "bankingclub", "versicherungsjournal", "procontra", "versicherungsmagazin", "cash-online", "immobilienmanager", "haufe", "property-magazine", "deal-magazin", "smartinvestor", "deraktionaer", "ecoreporter", "btc-echo", "bernecker", "cashkurs", "financefwd", "thepioneer", "table.media", "fuchsbriefe", "elitereport"]):
            cat = "Deutsche Fachmedien"
        elif any(d in src for d in ["nzz", "fuw", "cash.ch", "handelszeitung", "finews.ch", "moneycab", "investrends", "diepresse", "derstandard", "boersen-kurier", "boerse-express", "fondsexklusiv", "bilanz", "themarket", "trend.at", "geld-magazin", "derboersianer", "gewinn", "insideparadeplatz", "tippinpoint", "cvj.ch", "bitcoinnews.ch"]):
            cat = "Schweiz / Oesterreich"
        elif any(d in src for d in ["reuters", "ft.com", "bloomberg", "bbc", "cnbc", "wsj", "economist", "guardian", "fortune", "ipe", "pionline", "institutionalinvestor", "risk.net", "globalcapital", "etfstream", "ignites", "citywire.com", "hedgeweek", "preqin", "fundssociety", "seekingalpha", "thetradenews", "privateequitywire", "privatedebtinvestor", "infrastructureinvestor", "realdeals", "buyoutsnews", "funds-europe", "finews.com"]):
            cat = "International"
        elif any(d in src for d in ["coindesk", "cointelegraph", "theblock", "decrypt", "bitcoinmagazine", "oilprice", "spglobal", "responsible-investor", "esgtoday"]):
            cat = "Krypto / Spezial"
        elif any(d in src for d in ["ecb.europa", "bis.org", "google.com"]):
            cat = "Institutionen / Aggregatoren"
        else:
            cat = "Weitere Quellen"
        sources_by_category.setdefault(cat, set()).add(src)
    
    auto_sources = "\n\n## Vollstaendiges Quellenverzeichnis (automatisch erstellt)\n\n"
    auto_sources += f"**Gesamt: {len(rss_items)} Artikel aus {health['sources']} Quellen ueber {health['ok']} erfolgreich abgerufene RSS-Feeds.**\n\n"
    auto_sources += f"_Hinweis: Dies ist die VOLLSTAENDIGE Liste aller heute ausgewerteten Quellen. Die KI-generierte Quellenliste oben fokussiert auf zitierte Top-Storys; diese Liste hier zeigt die volle Recherche-Breite._\n\n"
    
    category_order = ["Deutsche Leitmedien", "Deutsche Fachmedien", "Schweiz / Oesterreich", "International", "Krypto / Spezial", "Institutionen / Aggregatoren", "Weitere Quellen"]
    for cat in category_order:
        if cat in sources_by_category:
            sources_list = sorted(sources_by_category[cat])
            auto_sources += f"**{cat}** ({len(sources_list)} Quellen):\n"
            auto_sources += ", ".join(sources_list) + "\n\n"
    
    # Add scraped client websites
    if client_insights:
        auto_sources += f"**Direkt gecrawlte Kunden-Webseiten** ({len(client_insights)}/{len(CLIENT_INSIGHTS_URLS)}):\n"
        for cname in client_insights.keys():
            auto_sources += f"- {cname} ({len(client_insights[cname])} Eigen-Inhalte gefunden)\n"
        auto_sources += "\n"
    
    auto_sources += f"**Konfigurierte Feeds gesamt:** {len(MEDIA_RSS_FEEDS)} direkte Medien + {len(GOOGLE_NEWS_FEEDS)} Google News + {len(CLIENT_FEEDS)} Kunden-Feeds = {len(MEDIA_RSS_FEEDS)+len(GOOGLE_NEWS_FEEDS)+len(CLIENT_FEEDS)} Feeds insgesamt. Plus Claude Opus 4.7 Live Web Search.\n"
    
    full = full + auto_sources

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

    # Save markdown source — needed by email module for teaser extraction
    mp = OUTPUT_DIR / f"{date_file}_TE_Media_Intelligence.md"
    with open(mp,"w",encoding="utf-8") as f: f.write(full)

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
            # Generate anchor ID from title for deep-linking from email
            anchor = re.sub(r'[^\w\s-]', '', title.lower())
            anchor = re.sub(r'[\s_]+', '-', anchor).strip('-')[:60]
            body += f'<details class="sec" id="{anchor}" {op}><summary class="sh"><span class="sn">{sc}.</span><span class="st">{title}</span><span class="ch">&#9660;</span></summary><div class="sb">'
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
<span>PGIM</span><span>T. Rowe Price</span><span>MK Global Kapital</span><span>Franklin Templeton</span><span>Eurizon</span><span>Bitcoin Suisse</span><span>KKR</span><span>Aegon AM</span><span>Bendura</span><span>DNB AM</span><span>Insight</span><span>JOHCM</span><span>Maverix</span>
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
<script>
// Auto-open section when arriving via deep-link (e.g., from email)
if (window.location.hash) {{
  const target = document.querySelector(window.location.hash);
  if (target && target.tagName === 'DETAILS') {{
    target.open = true;
    setTimeout(() => target.scrollIntoView({{behavior:'smooth', block:'start'}}), 100);
  }}
}}
</script>
<div class="ft">
<b>Methodik:</b> Zwei-Pass-Architektur — Pass 1 (Opus 4.7 + Web Search) tiefe Marktrecherche, Pass 2 (Sonnet 4.6) PR-Positionierung. Opus 4.7 ist das aktuell leistungsstaerkste oeffentlich verfuegbare Anthropic-Modell. {meta['rss_ok']} RSS-Feeds aus {meta['rss_sources']} Medienquellen. 24h-Zeitfilter. 14 Themenfelder. Vortagesvergleich.<br><br>
<b>Qualitaetshinweis:</b> Automatisiert erstellt. Kurse und Zahlen vor Verwendung in Kundenkommunikation gegen zweite Quelle pruefen.<br><br>
<b>TE Communications GmbH</b> | Frankfurt &middot; Zuerich &middot; St. Gallen &middot; Lausanne
</div>
</body>
</html>'''


if __name__ == "__main__":
    run_briefing()
