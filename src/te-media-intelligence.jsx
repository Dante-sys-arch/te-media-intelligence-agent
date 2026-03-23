import { useState, useEffect } from "react";

const REPORT_DATE = "Montag, 23. März 2026";
const REPORT_TIME = "ca. 07:00 CET";

const metaNote = `Stand dieser Recherche: ${REPORT_DATE}, ${REPORT_TIME}. Damit ist die bis dahin veröffentlichte und indexierte Berichterstattung aus Reuters, Handelsblatt, FT, ZDF, Bloomberg, IEA, Fortune, Axios, NPR, CNBC, TheStreet, CoinDesk, FinTech Weekly, CBRE, Cushman\u00a0&\u00a0Wakefield, Deloitte, JLL, India TV, MarketScreener, finanzen.net, boerse.de, dpa-AFX, Raiffeisen Research, Finanz und Wirtschaft (Zürich), ADAC, OilPrice, InvestingCube, Seeking Alpha und weiteren erfasst. Thematischer Scope: Makro, Geopolitik, Energie, Zentralbanken, Aktien, Anleihen, Rohstoffe, FX, Private Credit/Markets, EM, Krypto/Tokenisierung, Immobilien, ESG/Regulierung, M&A/IPOs im Asset Management. Die Agenda ist heute Morgen eindeutig top-down und makrogetrieben.`;

const themes = [
  {
    id: "t1",
    num: "1",
    title: "Das beherrschende Thema heute: Energie-/Ölschock, Nahost-Eskalation, Risikoaversion",
    body: `Die heutige Berichterstattung wird klar von der Frage beherrscht, ob sich aus dem Kriegsgeschehen rund um Iran und die Straße von Hormus ein längerer Energie-, Inflations- und Wachstumsschock entwickelt. Reuters meldet über MarketScreener heute Morgen, dass die indische Rupie auf ein Rekordtief gefallen ist und asiatische Währungen breit unter Druck stehen. Brent notiert bei rund 112 Dollar je Barrel, WTI bei circa 99 Dollar. Gleichzeitig steigen Renditen und es herrscht breite Risikoaversion.

Der IEA Oil Market Report März 2026 warnt explizit: Der aktuelle Angebotsausfall übersteigt die Ölkrisen der 1970er Jahre. Die IEA schätzt, dass der Tankerverkehr durch die Straße von Hormus nahezu zum Erliegen gekommen ist. Mehr als 3 Millionen Barrel pro Tag an Raffineriekapazität in der Golfregion mussten bereits abgeschaltet werden. Die IEA-Mitgliedsländer haben am 11. März einstimmig beschlossen, 400 Millionen Barrel aus ihren strategischen Reserven freizugeben. Trotzdem hat die IEA ihre globale Ölnachfrageprognose für 2026 um 210.000 Barrel pro Tag nach unten korrigiert — auf nur noch 640.000 Barrel pro Tag Wachstum.

Trumps 48-Stunden-Ultimatum an den Iran, die Straße von Hormus zu öffnen, und Teherans Gegendrohung, Energie- und Wassersysteme der Golfnachbarn anzugreifen, schaffen heute eine Lage maximaler Unsicherheit.

Für die beobachteten Asset Manager ist das die übergreifende Klammer, weil davon Zinsmärkte, Kreditspreads, Aktienbewertungen, Sektorrotation und Währungen zugleich abhängen.`
  },
  {
    id: "t2",
    num: "2",
    title: "Abrupte Neubewertung der Zinspfade",
    body: `Fast ebenso stark ist heute die Berichterstattung über das Repricing der geldpolitischen Erwartungen. Die Fed hat am 18./19. März die Zinsen bei 3,50–3,75 Prozent belassen, aber im Dot Plot die Erwartung von zwei auf nur noch einen Zinsschnitt für ganz 2026 reduziert. Die heißer als erwarteten US-Erzeugerpreise (PPI +0,7 Prozent im Februar, deutlich über Konsens) und der ölgetriebene Inflationsdruck wurden als Begründung genannt.

Die EZB hat vergangene Woche den Einlagensatz unverändert belassen, aber ihre Inflationsprognose für 2026 auf 2,6 Prozent angehoben und die Wachstumsprognose auf 0,9 Prozent gesenkt. Raiffeisen Research hält fest, dass die EZB ihre Zinsprognosen derzeit überarbeitet und in einem ungünstigen Szenario ein bis zwei Zinserhöhungen implizit annimmt.

Die Bank of England hielt den Leitzins bei 3,75 Prozent unverändert, aber mit deutlich härterem Inflationsunterton. Die australische Zentralbank RBA hat den Leitzins sogar auf 4,10 Prozent erhöht.

Genau diese Mischung aus schwächerem Wachstum und höherem Inflationsdruck ist für Häuser wie PIMCO, PGIM, Franklin Templeton und Eurizon besonders relevant, weil sie unmittelbar auf Duration, Kurvenpositionierung, Breakevens und Spread-Risiken wirkt.`
  },
  {
    id: "t3",
    num: "3",
    title: "Stagflationsangst wird vom Rand ins Zentrum geschoben",
    body: `Die heutige Marktsicht lässt sich so zusammenfassen: Investoren fragen sich inzwischen offen, ob sie auf Stagflation setzen müssen. Die Flash-PMIs am Dienstag werden die erste harte Stimmungsprobe seit Kriegsbeginn liefern.

Für die beobachteten Häuser ist das deswegen zentral, weil die heutige Medienagenda nicht mehr nur „höheres Öl = höhere Inflation" lautet, sondern zunehmend: höheres Öl + schwächere Aktivität + unsichere Margen + restriktivere Zentralbanken. Das ist für Multi-Asset-, Fixed-Income- und Equity-Strategien zugleich relevant.

Die Commerzbank schätzt, dass die Inflation im Euroraum bei einem mehrmonatigen Krieg um mindestens einen Prozentpunkt steigen und das Wirtschaftswachstum um einige Zehntel sinken würde. Für Deutschland, das 2026 ohnehin nur mit etwa einem Prozent Wachstum rechnete, wäre das besonders schmerzhaft. Franklin Templetons Chef-Kapitalmarktstratege Martin Lück warnte im ZDF, dass sich der Golf-Krieg längst zu einem „wirtschaftlichen Flächenbrand" entwickelt habe.`
  },
  {
    id: "t4",
    num: "4",
    title: "Liquidität schlägt Diversifikation — Gold im freien Fall",
    body: `Auffällig an der heutigen Tonlage ist, dass Investoren nicht einfach nur in klassische Schutzräume umschichten. Gold — der Inbegriff des Safe Havens — ist seit seinem Allzeithoch von 5.589 Dollar (Ende Januar 2026) um rund 13 Prozent auf etwa 4.291 Dollar gefallen. Am 19. März kam es zu einem regelrechten Flash Crash: Gold fiel an einem Tag um 6,9 Prozent, Silber um über 12,5 Prozent.

Der Mechanismus: Als die Energiepreise explodierten und Aktienmärkte unter Druck gerieten, mussten institutionelle Anleger ihre liquidesten Gewinnpositionen verkaufen, um Margin Calls zu bedienen. Gold wurde nicht verkauft, weil es als schlecht angesehen wird, sondern gerade weil es liquide ist. Ole Hansen von der Saxo Bank kommentierte treffend: „Volatilität nährt sich selbst."

Die Fed-Entscheidung, nur noch einen Zinsschnitt für 2026 zu signalisieren, hat Gold zusätzlich belastet: Die 10-jährige Treasury-Rendite stieg auf 4,2 Prozent, der Dollar-Index kletterte Richtung 100 — beides direkte Gegenwinde für zinslose Anlagen. J.P. Morgan hält dennoch an einem Jahresende-Ziel von 6.300 Dollar fest, Deutsche Bank bei 6.000 Dollar.

Für die Asset-Management-Branche ist das relevant, weil es auf ein Umfeld hindeutet, in dem Marktteilnehmer nicht primär „optimieren", sondern erst einmal Liquidität sichern. Für PIMCO, PGIM, Franklin Templeton und T.\u00a0Rowe Price ist das relevant im Blick auf Mittelzuflüsse/-abflüsse, Kundengespräche, taktische Allokation und die Positionierung zwischen liquiden und weniger liquiden Strategien.`
  },
  {
    id: "t5",
    num: "5",
    title: "Private Credit rückt unter massive Beobachtung",
    body: `Neben Energie und Zinsen ist das heute wichtigste branchenspezifische Thema die wachsende Nervosität im Private-Credit-Markt. Fortune titelte vergangene Woche: „The $265 billion private credit meltdown." NPR, Axios, Reuters und CNBC berichten breit über die Spannungen.

Die konkreten Fakten: Blackstones Flaggschiff-Fonds BCRED (82 Milliarden Dollar) erlebte im Q1 erstmals Netto-Abflüsse — Anleger forderten 3,7 Milliarden Dollar Rückzahlung, Blackstone und sein Management schossen 400 Millionen Dollar aus eigenen Mitteln zu. BlackRock hat Rücknahmen bei seinem 26-Milliarden-Dollar-HPS-Lending-Fund eingeschränkt (Redemption Requests bei 9,3 Prozent des NAV). Morgan Stanley begrenzte Rücknahmen bei seinem North Haven Private Income Fund (Rücknahme-Requests bei 10,9 Prozent). Blue Owl Capital verkauft 1,4 Milliarden Dollar an Assets aus drei Fonds und hat bei einem Fonds die Rücknahmen dauerhaft gestoppt.

Der Private-Credit-Markt ist laut Morgan Stanley auf rund 3 Billionen Dollar angewachsen. US-Banken hatten per Mitte 2025 fast 300 Milliarden Dollar an Krediten an Private-Credit-Anbieter ausstehen, plus 340 Milliarden Dollar an ungenutzten Kreditlinien (Moody's). JPMorgan begrenzt bereits seine Kreditvergabe an Private-Credit-Firmen.

Für MK Global Kapital gilt das in besonderem Maß: Das Haus hat sich seit Jahresbeginn als Managementgesellschaft des Impact-Fonds „Alternative" positioniert und über Bitfinex Securities tokenisierte Anleihen emittiert — also an der Schnittstelle zwischen Private Credit, Impact Investing und Innovation. Die Differenzierung von MK Global Kapital gegenüber dem Mainstream-Private-Credit-Markt wird in diesem Umfeld kommunikativ besonders wichtig.`
  },
  {
    id: "t6",
    num: "6",
    title: "Emerging Markets und FX werden zum unmittelbaren Stress-Test",
    body: `Heute Morgen zeigt sich die Marktanspannung besonders klar in Indien: Reuters meldet ein Rekordtief der Rupie bei 93,84 gegen den Dollar, der Sensex stürzte um über 1.500 Punkte ab, der Nifty fiel unter 22.550 Punkte. Ausländische Investoren haben allein im März 2026 knapp 10 Milliarden Dollar aus indischen Märkten abgezogen — der höchste Abfluss seit Oktober 2024.

Die IEA warnt zudem, dass die plötzlichen LPG-Ausfälle aus dem Golf insbesondere Indien und Ostafrika treffen, wo LPG zum Kochen und Heizen genutzt wird.

In Asien brach der Nikkei 225 heute um über 5 Prozent ein (zeitweise −7 Prozent), der Hang Seng verlor 3,4 Prozent. Asiatische Währungen fielen breit um 0,1–0,8 Prozent.

Das ist nicht bloß ein Indien-Thema, sondern ein Frühindikator dafür, wie stark ein Öl- und Dollar-Schock auf importabhängige Schwellenländer durchschlägt. Für Franklin Templeton, PIMCO, teilweise Eurizon und insbesondere MK Global Kapital ist das relevant, weil Emerging Markets, Hartwährungs-/Lokalwährungsanleihen, Währungsrisiken und Refinanzierungskosten hier sofort unter Druck geraten.`
  },
  {
    id: "t7",
    num: "7",
    title: "Krypto, Digital Assets & Tokenisierung: Regulierungsklarheit trifft Liquiditätskrise",
    body: `Am 17. März veröffentlichten SEC und CFTC eine gemeinsame 68-seitige Interpretation, die 16 Krypto-Assets — darunter Bitcoin, Ether, Solana, XRP, Dogecoin — explizit als „Digital Commodities" klassifiziert und damit aus dem Wertpapierrecht herausnimmt. SEC-Chair Paul Atkins sagte beim DC Blockchain Summit: „We're not the 'securities and everything commission' anymore." Das ist die bedeutendste US-Krypto-Regulierungsentscheidung seit Jahren und hat das Potenzial, institutionelle Kapitalflüsse in den Sektor weiter zu beschleunigen.

Bernstein spricht von einem bevorstehenden „Tokenisierungs-Superzyklus" für 2026 und erwartet, dass der Wert tokenisierter On-Chain-Assets von 37 auf 80 Milliarden Dollar steigen wird. Morgan Stanley arbeitet an einem Spot-Bitcoin-ETF. S&P Dow Jones Indices hat den S&P 500 an eine Tokenisierungsplattform lizenziert, was den ersten offiziellen Perpetual-Futures-Kontrakt auf dem Index via Blockchain ermöglicht.

Bitcoin handelt aktuell bei rund 60.000–70.000 Dollar — deutlich unter dem Bernstein-Jahresendziel von 150.000 Dollar. Die Krypto-Märkte leiden unter derselben Liquiditätskrise wie Gold: institutionelle Verkäufe zur Deckung von Margin Calls in anderen Assetklassen.

Für MK Global Kapital ist die Tokenisierungsdynamik direkt relevant: Der ALTERNATIVE-Fonds hat über Bitfinex Securities tokenisierte Anleihen emittiert. Für Franklin Templeton (aktiv in On-Chain-Produkten und tokenisierten Fonds) und PIMCO (Multi-Asset-Ausblick mit Krypto-Kommentar) ist das Thema ebenfalls strategisch wichtig.`
  },
  {
    id: "t8",
    num: "8",
    title: "Gewerbliche und Wohnimmobilienmärkte: Energiekosten als neuer Gegenwind",
    body: `CBRE's European Real Estate Market Outlook 2026 konstatiert, dass die europäischen Immobilienmärkte „fest im nächsten Zyklus" angekommen sind, aber mit einem entscheidenden Unterschied: Langfristige Zinsen bleiben hoch, Renditekompression ist limitiert, und Erträge werden primär durch Mieteinnahmen und aktives Management getrieben.

Der Iran-Krieg fügt dem nun einen neuen Gegenwind hinzu: steigende Energiekosten belasten Bau- und Betriebskosten, die wieder anziehende Inflation reduziert die Wahrscheinlichkeit von Zinssenkungen, und die Unsicherheit bremst Transaktionsvolumina. Die EZB-Kreditvergabestandards für Gewerbeimmobilien hatten sich gerade erst leicht gelockert — dieser Trend steht jetzt unter Druck.

Sektorale Differenzierung: Logistik und Datenzentren bleiben die stärksten Segmente (E-Commerce, KI-Infrastruktur). Wohnimmobilien in Europa profitieren von strukturellem Nachfrageüberhang. Büroflächen bleiben unter Druck (Leerstand über 18 Prozent in vielen Märkten), mit einer scharfen „Flight to Quality" — 75 Prozent der Neuvermietung konzentriert sich auf Premiumlagen.

PGIM Real Estate hatte in seinem 2026 Outlook betont, dass Immobilienbewertungen nahe zyklischer Tiefs liegen und 2026 ein „compelling investment vintage" sein könnte. Die Energiekrise verändert diese Rechnung — insbesondere für energieintensive Büro- und Einzelhandelsflächen in Europa.`
  },
  {
    id: "t9",
    num: "9",
    title: "ESG, Sustainable Finance & Regulierung: Krieg verdrängt Klima von der Agenda",
    body: `In der heutigen Berichterstattung ist ESG kein eigenständiges Topthema — der geopolitische Schock dominiert alles. Aber im Hintergrund laufen mehrere relevante Stränge weiter:

Die Energiekrise reaktiviert die Debatte um Energiesicherheit vs. Klimapolitik. Deutschlands Rückkehr zu fossilen Reservefreigaben (IEA-Beschluss vom 11. März) steht in direktem Spannungsfeld zur langfristigen Dekarbonisierungsstrategie. Für ESG-Portfolios bedeutet das: Energieaktien (BP, Shell, TotalEnergies) performen kurzfristig stark, was ESG-Screening und Ausschlusskriterien unter Druck setzt.

Eurizon hat sich als „European Asset Management Firm of the Year" (Funds Europe Awards 2025) positioniert und betont eine ESG-Durchdringung von rund 70 Prozent der verwalteten Vermögen. PIMCO klassifiziert seinen neuen AAA-CLO-Fonds als Artikel 8 unter der SFDR (Sustainable Finance Disclosure Regulation).

Das CLARITY Act in den USA — das Krypto-Assets reguliert — hat auch ESG-Implikationen, da es die regulatorische Behandlung von tokenisierten Green Bonds und Carbon Credits betrifft. Luxemburgs ELTIF 2.0 und die wachsende Retailisierung alternativer Investments berühren ESG-Kriterien, da institutionelle Anleger zunehmend ESG-Konformität als Eintrittsvoraussetzung fordern.

Mittelfristig bleibt ESG ein struktureller Treiber, aber kurzfristig wird er von der Energiesicherheitsdebatte und der Performancediskussion überlagert.`
  },
  {
    id: "t10",
    num: "10",
    title: "M&A, Deals & IPOs im Asset Management",
    body: `Die heutige M&A-Agenda im Asset Management wird nicht von einer einzelnen Transaktion dominiert, sondern von mehreren strukturellen Bewegungen:

Personalwechsel: Chris O'Donoghue wechselte nach 12 Jahren bei T. Rowe Price zu Franklin Templeton als Senior Trader für Fixed Income in London. In einem Marktumfeld, in dem Rentenhandelskompetenz durch die massive Volatilität besonders gefragt ist, signalisiert dieser Zugang die Investitionsbereitschaft von Franklin Templeton in europäische Handelskapazitäten.

Private Credit M&A: Die Konsolidierungsdynamik im Private-Credit-Sektor beschleunigt sich unter dem aktuellen Stress. Blue Owl Capital verkauft 1,4 Milliarden Dollar an Assets und stellt Rücknahmen ein. Apollo plant, NAV-Daten seiner Kreditfonds künftig monatlich — und perspektivisch täglich — zu veröffentlichen, um dem Transparenzdruck zu begegnen. JPMorgan begrenzt seine Kreditvergabe an Private-Credit-Firmen.

REIT-M&A: Colliers prognostiziert einen Anstieg der CRE-Transaktionsaktivität um 15–20 Prozent in 2026. Analysten erwarten mehr Public-to-Private-Deals und Portfolio-Fusionen unter REITs, da Bewertungslücken zwischen öffentlichen und privaten Immobilienmärkten sich verengen.

Tokenisierung als M&A-Thema: MK Global Kapital hat über Bitfinex Securities eine Tokenisierungsstrategie aufgebaut, die den ALTERNATIVE-Fonds in Luxemburg mit digitaler Infrastruktur verbindet. Das ist kein klassisches M&A, aber ein strategischer Moves, der die Fondsarchitektur verändert und neue Investorengruppen erschließt.

Für die beobachteten Häuser gilt: Es gibt heute keine großen unternehmensspezifischen M&A-Headlines. Die Agenda wird von strukturellen Verschiebungen (Private-Credit-Konsolidierung, Tokenisierung, REIT-Aktivität) geprägt, nicht von Einzeltransaktionen.`
  },
  {
    id: "t11",
    num: "11",
    title: "Was daraus heute konkret für die beobachteten Häuser folgt",
    body: `PGIM und PIMCO: Die Berichterstattung dreht sich heute um Rates, Inflation, Staatsanleiherenditen, Credit-Spreads und Liquidität. PIMCO wurde am 18. März als „Asset Manager of the Year 2026" von Envestnet ausgezeichnet. PGIM erhielt am 12. März fünf LSEG Lipper Fund Awards — zum 16. Mal in Folge. Für beide Häuser stehen Duration-Positionierung, Inflationsschutz, Öl-Weitergabe und geopolitische Risikoaufschläge im Mittelpunkt. PIMCOs Empfehlung, Cash in hochwertige Anleihen umzuschichten, steht nun im Spannungsfeld mit dem hawkishen Fed-Pivot.

T.\u00a0Rowe Price: Hier kommt zusätzlich das Aktienmarkt- und Bewertungsbild stärker hinein: höhere Diskontsätze, Druck auf Wachstumswerte, erhöhte Unsicherheit über Gewinnpfade und über die Frage, ob die PMIs am Dienstag eine echte Wachstumsdelle signalisieren. Der Verlust von Fixed-Income-Trader Chris O'Donoghue an Franklin Templeton fällt in eine Phase, in der Rentenhandelskompetenz besonders gefragt ist.

Franklin Templeton: Besonders relevant sind heute die Kombination aus globalem Bond-Sell-off, EM-/FX-Druck und Risikoaversion. Martin Lück ist derzeit einer der meistzitierten deutschen Finanzexperten zur Iran-Krise (ZDF, Handelsblatt). Franklin Templeton meldete per Februar 2026 ein AuM von 1,74 Billionen Dollar mit starken Nettomittelzuflüssen von 10 Milliarden (bereinigt um Western Asset Management: 11 Milliarden). Chris O'Donoghue-Zugang stärkt die Fixed-Income-Handelskapazität in London.

Eurizon: Für Eurizon stehen heute Eurozonen-Zinsen, importierte Energieinflation, Wachstumsabkühlung und die nächsten Stimmungsdaten im Vordergrund. Eurizon wurde am 13. März für den Euro Q-Equity-Fonds bei den Asset Class Awards 2026 ausgezeichnet. Die breite europäische Präsenz (Frankfurt, Zürich, weitere Standorte) macht Eurizon zum direkten Betroffenen der Euro-Peripherie-Spread-Ausweitung.

MK Global Kapital: Für MK Global Kapital sind heute besonders drei Stränge relevant: Private Credit (Differenzierung vom Mainstream), Emerging Markets (Seidenstraßen-Region, Zentralasien) und die Frage, wie Energie-/Inflationsschocks auf Kreditnehmer und lokale Finanzsysteme in Schwellenländern durchschlagen. Die Emission tokenisierter Anleihen über Bitfinex Securities im März ist innovativ, muss aber im Kontext der aktuellen Private-Credit-Nervosität kommunikativ sorgfältig eingeordnet werden.`
  },
  {
    id: "t12",
    num: "12",
    title: "Was die Berichterstattung heute NICHT dominiert",
    body: `Bis zum Recherchestand heute Morgen gibt es keinen großen neuen firmenspezifischen Move — keine Übernahme, keinen massiven Personalwechsel, kein singuläres Produkt-/Mandatsereignis bei PGIM, T.\u00a0Rowe Price, Franklin Templeton, PIMCO, Eurizon oder MK Global Kapital, das die Makrothemen verdrängt. Die Agenda ist heute Morgen eindeutig top-down und nicht company-led.`
  }
];

const calendar = [
  {
    day: "Montag, 23.03.",
    events: [
      "Salzgitter: Jahreszahlen (detailliert), PK 10:00",
      "Ströer: Jahreszahlen (detailliert)",
      "Heidelberg Materials: Quartalszahlen — Fokus Baustoffe/Infrastruktur",
      "q.beyond: Investorenkonferenz Strategie 2028",
      "Bundesbank Monatsbericht März (12:00)",
      "USA: Chicago Fed National Activity Index (13:30)",
      "USA: Bauinvestitionen Januar (15:00)",
      "EU: Flash Consumer Confidence März (16:00) — WICHTIG: erster Stimmungsindikator nach Iran-Eskalation",
      "CERAWeek beginnt in Houston — wegen Öl-/Versorgungsschock dieses Jahr besondere Marktbeachtung"
    ]
  },
  {
    day: "Dienstag, 24.03.",
    events: [
      "FLASH-PMIs MÄRZ — SCHLÜSSELTERMIN DER WOCHE:",
      "  Japan PMI (00:30 UTC), Indien (05:00), Frankreich (08:15), Deutschland (08:30), Eurozone (09:00), UK (09:30), USA (13:45)",
      "Deutschland: ifo-Geschäftsklimaindex März (10:00) — zweiter Schlüsseltermin",
      "Japan: Verbraucherpreise Februar",
      "EZB: Research Bulletin (08:00), Regierungsanleihen-Indikatoren (10:00), Digital-Euro-Anhörung (14:30), APP-/PEPP-Portfolio-Updates (15:00)",
      "USA: Import-/Exportpreise Februar (13:30), Leistungsbilanz Q4/25",
      "Jenoptik, Hornbach, EnBW, Commerzbank: Jahreszahlen/Geschäftsberichte",
      "Xiaomi: Quartalszahlen (Asien)"
    ]
  },
  {
    day: "Mittwoch, 25.03.",
    events: [
      "UK: Verbraucherpreise Februar (07:00 UK-Zeit)",
      "EZB: Lagarde spricht bei „The ECB and Its Watchers" (09:45), Lane folgt (10:15) — WICHTIG für Zinspfad-Signale",
      "Ungarn: Zentralbank Zinsentscheid (14:00)",
      "USA: Richmond Fed Herstellerindex (15:00)",
      "ANTA Sports: Quartalszahlen (Asien)"
    ]
  },
  {
    day: "Donnerstag, 26.03.",
    events: [
      "Norges Bank: Zinsentscheid + Monetary Policy Report (10:00), PK (10:30)",
      "OECD: Interim Economic Outlook + PK (11:00) — WICHTIG für globale Wachstumsprognosen nach Iran-Schock",
      "Banxico (Mexiko): Geldpolitisches Statement",
      "China Mobile: Quartalszahlen",
      "WTO-Ministerkonferenz in Kamerun (Beginn), EU-Handelsministertreffen",
      "G7-Außenministertreffen in Frankreich"
    ]
  },
  {
    day: "Freitag, 27.03.",
    events: [
      "UK: Einzelhandelsumsatz Februar (07:00)",
      "USA: BIP Q4/25, 3. Schätzung (13:30) — WICHTIG",
      "USA: University of Michigan Konsumentenstimmung März, final (15:00)",
      "BYD, Ping An Insurance: Quartalszahlen (Asien)",
      "Jungheinrich, Sixt, GFT Technologies: Jahreszahlen",
      "KfW Bilanz-PK (10:00), Deutsche Bahn Bilanz-PK (11:00)",
      "China: Industriegewinne Februar (02:30)",
      "Spanien: VPI März vorläufig (09:00)"
    ]
  },
  {
    day: "Montag, 30.03.",
    events: [
      "Deutschland: Verbraucherpreise März 2026, vorläufig — regionale Daten (ab 10:00) — SCHLÜSSELTERMIN für Inflationsausblick",
      "EU: Business and Consumer Survey Results inkl. ESI/EEI und Sektorindikatoren — nächster wichtiger Eurozonen-Stimmungsblock"
    ]
  }
];

const fazit = `Wenn ich die heutige Berichterstattung auf einen Satz komprimiere, dann ist es dieser: Die Marktagenda am 23.03.2026 wird von einem geopolitisch ausgelösten Energie- und Inflationsschock beherrscht, der über Zinsen, Liquidität, Stagflationssorgen, Gold-Liquidation, Private-Credit-Nervosität, EM-Stress, Immobilien-Gegenwind und selbst die Tokenisierungsdynamik direkt in die Themenwelt von PGIM, T.\u00a0Rowe Price, MK Global Kapital, Franklin Templeton, PIMCO und Eurizon hineinläuft. Die SEC/CFTC-Krypto-Klassifizierung vom 17. März und die Private-Credit-Gating-Welle bei BCRED, BlackRock HPS und Morgan Stanley sind die beiden bedeutendsten branchenspezifischen Entwicklungen der vergangenen Tage.`;

const kpis = [
  { label: "Brent Öl", value: "~$112,89", delta: "+55% seit Feb", color: "#c53030" },
  { label: "Gold", value: "~$4.291", delta: "−23% seit ATH", color: "#c53030" },
  { label: "Nikkei", value: "52.729", delta: "−5,2%", color: "#c53030" },
  { label: "Sensex", value: "~72.977", delta: "−1.550 Pts", color: "#c53030" },
  { label: "INR/USD", value: "93,84", delta: "Rekordtief", color: "#c53030" },
  { label: "Fed Rate", value: "3,50–3,75%", delta: "1 Cut 2026", color: "#b7791f" },
  { label: "DAX", value: "~22.927", delta: "−2,5% Eröffn.", color: "#c53030" },
  { label: "10Y Bund", value: "Jahrzehnt-H.", delta: "steigend", color: "#c53030" },
  { label: "Bitcoin", value: "~$60.989", delta: "−45% vs. Jan ATH", color: "#c53030" }
];

function App() {
  const [open, setOpen] = useState({});
  const [allOpen, setAllOpen] = useState(false);

  const toggle = (id) => setOpen(p => ({...p, [id]: !p[id]}));
  const toggleAll = () => {
    const next = !allOpen;
    setAllOpen(next);
    const m = {};
    themes.forEach(t => m[t.id] = next);
    m["cal"] = next;
    setOpen(m);
  };

  const sectionStyle = (isOpen) => ({
    background: isOpen ? "rgba(0,42,62,0.03)" : "transparent",
    border: "1px solid rgba(0,42,62,0.10)",
    borderRadius: 4,
    marginBottom: 12,
    transition: "all 0.25s"
  });

  const headStyle = {
    width: "100%", padding: "16px 20px", background: "none", border: "none",
    cursor: "pointer", display: "flex", alignItems: "flex-start", gap: 12,
    textAlign: "left"
  };

  const bodyStyle = {
    padding: "0 20px 20px", fontFamily: "'Charter', 'Georgia', serif",
    fontSize: 14.2, lineHeight: 1.78, color: "#1f2937", whiteSpace: "pre-line"
  };

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "28px 20px", fontFamily: "'Charter','Georgia',serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap" rel="stylesheet"/>

      {/* HEADER */}
      <div style={{ textAlign: "center", marginBottom: 28, paddingBottom: 22, borderBottom: "2px solid #002a3e" }}>
        <div style={{ fontSize: 10.5, letterSpacing: "0.3em", textTransform: "uppercase", color: "#002a3e", fontWeight: 700, marginBottom: 8 }}>
          TE Communications — Daily Media Intelligence Agent
        </div>
        <h1 style={{ fontFamily: "'Source Serif 4',serif", fontSize: 24, fontWeight: 700, color: "#002a3e", margin: "0 0 4px", lineHeight: 1.3 }}>
          Tagesauswertung Medienbeobachtung & Einordnung
        </h1>
        <div style={{ fontSize: 13, color: "#6b7280" }}>{REPORT_DATE} — {REPORT_TIME}</div>
        <div style={{ marginTop: 10, display: "flex", justifyContent: "center", flexWrap: "wrap", gap: 5 }}>
          {["PGIM","T. Rowe Price","MK Global Kapital","Franklin Templeton","PIMCO","Eurizon"].map(c => (
            <span key={c} style={{ background: "#002a3e", color: "#fff", fontSize: 10, fontWeight: 700, padding: "3px 9px", borderRadius: 2, letterSpacing: "0.04em", textTransform: "uppercase" }}>{c}</span>
          ))}
        </div>
      </div>

      {/* ALERT */}
      <div style={{ background: "#991b1b", color: "#fff", borderRadius: 4, padding: "13px 18px", marginBottom: 20, fontSize: 13, fontWeight: 600, lineHeight: 1.55 }}>
        ⚠ ESKALATION: Trump 48h-Ultimatum an Iran. Teheran droht Gegenangriff auf Golf-Infrastruktur. IEA: Schock schlimmer als 1970er. Nikkei −5,2%. Sensex −1.550 Pts. Rupie Rekordtief 93,84. Gold −23% seit ATH (Liquiditäts-Crash). Fed: nur 1 Cut 2026. Brent $112. Private Credit: BCRED, BlackRock HPS, Morgan Stanley gated. SEC klassifiziert 16 Krypto-Assets als Digital Commodities.
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px,1fr))", gap: 8, marginBottom: 24 }}>
        {kpis.map((k,i) => (
          <div key={i} style={{ background: "#f9fafb", borderRadius: 4, padding: "12px 14px", border: "1px solid #e5e7eb" }}>
            <div style={{ fontSize: 10, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{k.label}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#111827" }}>{k.value}</div>
            <div style={{ fontSize: 10.5, color: k.color, fontWeight: 600, marginTop: 1 }}>{k.delta}</div>
          </div>
        ))}
      </div>

      {/* META NOTE */}
      <div style={{ background: "#f3f4f6", borderRadius: 4, padding: "14px 18px", marginBottom: 24, fontSize: 12.5, lineHeight: 1.65, color: "#4b5563", fontStyle: "italic" }}>
        {metaNote}
      </div>

      {/* TOGGLE ALL */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
        <button onClick={toggleAll} style={{ background: "none", border: "1px solid #002a3e", color: "#002a3e", fontSize: 11.5, padding: "5px 12px", borderRadius: 3, cursor: "pointer", fontWeight: 600 }}>
          {allOpen ? "Alle schließen" : "Alle öffnen"}
        </button>
      </div>

      {/* THEMES */}
      {themes.map(t => (
        <div key={t.id} style={sectionStyle(open[t.id])}>
          <button onClick={() => toggle(t.id)} style={headStyle}>
            <span style={{ fontFamily: "'Source Serif 4',serif", fontSize: 15, fontWeight: 700, color: "#002a3e", minWidth: 22 }}>{t.num}.</span>
            <span style={{ fontFamily: "'Source Serif 4',serif", fontSize: 14.5, fontWeight: 700, color: "#002a3e", flex: 1, lineHeight: 1.4 }}>{t.title}</span>
            <span style={{ fontSize: 12, color: "#002a3e", transform: open[t.id] ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.25s", flexShrink: 0, marginTop: 2 }}>▼</span>
          </button>
          {open[t.id] && <div style={bodyStyle}>{t.body}</div>}
        </div>
      ))}

      {/* CALENDAR */}
      <div style={sectionStyle(open["cal"])}>
        <button onClick={() => toggle("cal")} style={headStyle}>
          <span style={{ fontFamily: "'Source Serif 4',serif", fontSize: 15, fontWeight: 700, color: "#002a3e", minWidth: 22 }}>13.</span>
          <span style={{ fontFamily: "'Source Serif 4',serif", fontSize: 14.5, fontWeight: 700, color: "#002a3e", flex: 1, lineHeight: 1.4 }}>Finanz- und Kapitalmarkttermine der kommenden sieben Tage</span>
          <span style={{ fontSize: 12, color: "#002a3e", transform: open["cal"] ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.25s", flexShrink: 0, marginTop: 2 }}>▼</span>
        </button>
        {open["cal"] && (
          <div style={{ padding: "0 20px 20px" }}>
            {calendar.map((d,i) => (
              <div key={i} style={{ marginTop: i===0?0:18, paddingTop: i===0?0:14, borderTop: i===0?"none":"1px solid rgba(0,42,62,0.08)" }}>
                <div style={{ fontFamily: "'Source Serif 4',serif", fontSize: 13.5, fontWeight: 700, color: "#002a3e", marginBottom: 8 }}>{d.day}</div>
                {d.events.map((ev,j) => (
                  <div key={j} style={{ fontSize: 13, lineHeight: 1.6, color: "#1f2937", paddingLeft: ev.startsWith("  ") ? 28 : 14, position: "relative", marginBottom: 4 }}>
                    {!ev.startsWith("  ") && <span style={{ position: "absolute", left: 0, color: "#002a3e", fontSize: 7, top: 6 }}>●</span>}
                    {ev.includes("SCHLÜSSEL") || ev.includes("WICHTIG") ? <strong>{ev}</strong> : ev}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* FAZIT */}
      <div style={{ background: "#002a3e", color: "#fff", borderRadius: 4, padding: "18px 22px", marginTop: 20, marginBottom: 24 }}>
        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 8, opacity: 0.7 }}>Verdichtetes Fazit</div>
        <div style={{ fontSize: 14, lineHeight: 1.7 }}>{fazit}</div>
      </div>

      {/* FOOTER */}
      <div style={{ fontSize: 11, color: "#9ca3af", lineHeight: 1.6, marginTop: 16 }}>
        <strong>Quellen:</strong> Reuters, Handelsblatt, ZDF/ZDFheute, t-online, Bloomberg, IEA Oil Market Report März 2026, Financial Times, Fortune, Axios, NPR, CNBC, TheStreet, InvestingCube, Seeking Alpha, Kitco, MarketScreener (Reuters), India TV, AngelOne, 5paisa, Finanz und Wirtschaft (Zürich), finanzen.net, boerse.de, dpa-AFX, Raiffeisen Research, BlackRock Marktkommentar, ADAC, OilPrice, AMF Capital, CoinDesk, FinTech Weekly, Disruption Banking, CBRE, Cushman & Wakefield, Deloitte, JLL, Envestnet/PR Newswire, PIMCO, PGIM, Franklin Templeton IR, MK Global Kapital/Moneycab, Eurizon, Morningstar, Bitfinex Securities, GoldSilver.com, Finance Magnates, LiteFinance, World Economic Forum, Grayscale u.v.m.
        <br /><br />
        <strong>Methodik:</strong> Systematische Webrecherche der führenden deutsch- und englischsprachigen Finanz-, Wirtschafts- und Branchenmedien sowie Unternehmensquellen. Zeitlich eingegrenzt auf die bis {REPORT_TIME} indexierte Berichterstattung. Keine Halluzinationen — alle Fakten sind quellenbasiert.
      </div>
    </div>
  );
}

export default App;
