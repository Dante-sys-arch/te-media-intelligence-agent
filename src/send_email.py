"""
TE Communications — E-Mail-Versand-Modul (v3.10 — Teaser-Struktur)
=================================================================
Versendet den taeglichen Report als anteasernde E-Mail mit Deep-Links
zum Dashboard. Jeder Abschnitt enthaelt eine Kurzfassung; vollstaendige
Inhalte werden im Dashboard geoeffnet.

Wird vom GitHub Actions Workflow nach erfolgreichem Lauf aufgerufen.

Benoetigt drei GitHub Secrets:
  SMTP_USER         — z.B. te.daily.briefing@gmail.com
  SMTP_PASS         — Gmail App-Passwort (16 Zeichen, kein normales Passwort!)
  EMAIL_RECIPIENTS  — komma-separierte Liste, z.B. sdj@te-communications.com,team@te-communications.com
"""

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timedelta

DASHBOARD_URL = "https://dante-sys-arch.github.io/te-media-intelligence-agent/"
LATEST_HTML_URL = "https://dante-sys-arch.github.io/te-media-intelligence-agent/latest.html"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


def get_today_str_de():
    """Get today's date in German format."""
    now = datetime.utcnow() + timedelta(hours=1)
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    monate = ["", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return f"{tage[now.weekday()]}, {now.day}. {monate[now.month]} {now.year}"


def find_latest_report():
    """Find the most recent HTML report file and the corresponding markdown source."""
    output_dir = Path("output")
    if not output_dir.exists():
        return None, None
    htmls = sorted(output_dir.glob("*_TE_Media_Intelligence.html"), reverse=True)
    mds = sorted(output_dir.glob("*_TE_Media_Intelligence.md"), reverse=True)
    html_path = htmls[0] if htmls else None
    md_path = mds[0] if mds else None
    return html_path, md_path


def slug(text):
    """Generate URL anchor from section title (matches HTML anchor generation)."""
    s = re.sub(r'[^\w\s-]', '', text.lower())
    s = re.sub(r'[\s_]+', '-', s).strip('-')
    return s[:60]


def parse_report_sections(md_text):
    """Parse markdown report into ordered sections (title -> content)."""
    if not md_text:
        return {}
    sections = {}
    current_title = None
    current_content = []

    for line in md_text.split("\n"):
        if line.startswith("## "):
            if current_title:
                sections[current_title] = "\n".join(current_content).strip()
            current_title = line[3:].strip()
            current_content = []
        elif line.startswith("# "):
            if current_title:
                sections[current_title] = "\n".join(current_content).strip()
            current_title = line[2:].strip()
            current_content = []
        else:
            if current_title:
                current_content.append(line)

    if current_title:
        sections[current_title] = "\n".join(current_content).strip()

    return sections


def teaser(text, max_chars=400, max_lines=5):
    """Extract a short teaser from a section's content."""
    if not text:
        return ""
    cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    cleaned = re.sub(r'\*(.+?)\*', r'\1', cleaned)
    cleaned = re.sub(r'`(.+?)`', r'\1', cleaned)

    lines = [l for l in cleaned.split("\n") if l.strip()]
    teaser_lines = []
    total_chars = 0

    for line in lines[:max_lines * 2]:
        line = line.strip()
        if not line:
            continue
        if total_chars + len(line) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 50:
                line = line[:remaining].rsplit(' ', 1)[0] + "…"
                teaser_lines.append(line)
            break
        teaser_lines.append(line)
        total_chars += len(line)
        if len(teaser_lines) >= max_lines:
            break

    return "\n".join(teaser_lines)


def find_section(sections, *keywords):
    """Find a section whose title contains any of the keywords."""
    for title, content in sections.items():
        title_lower = title.lower()
        if any(kw.lower() in title_lower for kw in keywords):
            return title, content
    return None, ""


def section_link(title):
    """Build a deep link to a specific section in the dashboard."""
    return f"{LATEST_HTML_URL}#{slug(title)}"


def section_block_html(title, teaser_text, link_label="Vollständig im Report öffnen"):
    """Build an HTML block for a single section with teaser + deep link."""
    if not teaser_text or not title:
        return ""

    teaser_html = teaser_text.replace("\n", "<br>")
    teaser_html = re.sub(r'^[-•]\s+', '• ', teaser_html, flags=re.MULTILINE)

    link = section_link(title)

    return f'''
<div class="sec">
  <div class="sec-title">{title.upper()}</div>
  <div class="sec-body">{teaser_html}</div>
  <a class="sec-link" href="{link}">→ {link_label}</a>
</div>
'''


def build_email_html(date_str, sections, meta_info=""):
    """Build the full HTML email with all section teasers."""

    title_quellen, c_quellen = find_section(sections, "Quellen", "Zugriffslage")
    title_top5, c_top5 = find_section(sections, "Top 5 Themen", "Top 3 Themen")
    title_ueber, c_ueber = find_section(sections, "Marktrecherche-Ueberblick", "Markt-Recherche", "Marktanalyse")
    title_tiefe, c_tiefe = find_section(sections, "Tiefenanalyse", "Themen die das")
    title_white, c_white = find_section(sections, "White Spaces", "Unterdiskutiert")
    title_konk, c_konk = find_section(sections, "Konkurrenz")
    title_live, c_live = find_section(sections, "KUNDEN-LIVE", "Live-Recherche", "Kunden-Live")
    title_termine, c_termine = find_section(sections, "Termine")
    title_prio, c_prio = find_section(sections, "Priorisierte Themen", "Themen-Tabelle")
    title_pos, c_pos = find_section(sections, "Positionierungs-Mapping")
    title_pitches, c_pitches = find_section(sections, "Pitch-Empfehlungen", "Top-7", "Pitch-Empf")
    title_trends, c_trends = find_section(sections, "Mehrtages-Trends")
    title_fazit, c_fazit = find_section(sections, "Gesamtfazit", "Fazit")

    blocks = []

    if title_quellen:
        blocks.append(section_block_html(title_quellen, teaser(c_quellen, 350, 4), "Volle Quellenliste"))

    if title_top5:
        blocks.append(section_block_html(title_top5, teaser(c_top5, 600, 7), "Vollständige Tiefenanalyse"))

    if title_ueber:
        blocks.append(section_block_html(title_ueber, teaser(c_ueber, 400, 4), "Vollständige Marktanalyse"))

    if title_tiefe:
        compact = []
        for line in c_tiefe.split("\n"):
            if line.startswith("### "):
                compact.append(f"• {line[4:].strip()}")
                if len(compact) >= 4:
                    break
        teaser_t = "\n".join(compact) if compact else teaser(c_tiefe, 400, 5)
        blocks.append(section_block_html(title_tiefe, teaser_t, "Vollständige 8-Punkte-Analyse pro Thema"))

    if title_white:
        blocks.append(section_block_html(title_white, teaser(c_white, 500, 5), "Volle White-Space-Analyse"))

    if title_konk:
        blocks.append(section_block_html(title_konk, teaser(c_konk, 500, 6), "Volle Konkurrenz-Beobachtung"))

    if title_live:
        blocks.append(section_block_html(title_live, teaser(c_live, 500, 7), "Volle Sprecher-Recherche aller 13 Kunden"))

    if title_termine:
        blocks.append(section_block_html(title_termine, teaser(c_termine, 500, 7), "Vollständiger Termin-Überblick"))

    if title_prio:
        blocks.append(section_block_html(title_prio, teaser(c_prio, 500, 7), "Volle Prioritäten-Tabelle"))

    if title_pos:
        blocks.append(section_block_html(title_pos, teaser(c_pos, 600, 8), "Volles Mapping pro Kunde (13)"))

    if title_pitches:
        compact = []
        for line in c_pitches.split("\n"):
            stripped = line.strip()
            if re.match(r'^\d+\.\s', stripped) or stripped.startswith("**"):
                clean = re.sub(r'\*\*', '', stripped)
                if len(clean) > 10:
                    compact.append("• " + clean[:130])
                    if len(compact) >= 7:
                        break
        teaser_p = "\n".join(compact) if compact else teaser(c_pitches, 600, 7)
        blocks.append(section_block_html(title_pitches, teaser_p, "Volle Pitches mit fertigen Mail-Vorschlägen"))

    if title_trends:
        blocks.append(section_block_html(title_trends, teaser(c_trends, 350, 4), "Volle Trend-Analyse"))

    if title_fazit:
        blocks.append(section_block_html(title_fazit, teaser(c_fazit, 400, 4), "Volltext"))

    sections_html = "\n".join(blocks)

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 640px; margin: 0 auto; padding: 0; color: #1f2937; line-height: 1.55; background: #f3f4f6; }}
  .wrap {{ background: #fff; padding: 0; }}
  .hd {{ background: #002a3e; color: #fff; padding: 28px 24px 22px; text-align: center; }}
  .hd .lb {{ font-size: 10px; letter-spacing: 0.32em; text-transform: uppercase; color: #fbbf24; font-weight: 700; }}
  .hd h1 {{ font-size: 22px; margin: 10px 0 4px; color: #fff; font-weight: 600; }}
  .hd .dt {{ font-size: 13px; color: #cbd5e1; }}
  .cta-wrap {{ padding: 24px; background: #fff; text-align: center; }}
  .cta {{ display: inline-block; background: #002a3e; color: #fff !important; padding: 14px 32px; border-radius: 4px; text-decoration: none; font-size: 15px; font-weight: 700; letter-spacing: 0.02em; }}
  .meta {{ font-size: 12px; color: #6b7280; margin-top: 12px; line-height: 1.6; }}
  .sec {{ padding: 18px 24px; border-bottom: 1px solid #e5e7eb; }}
  .sec-title {{ font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: #002a3e; font-weight: 700; margin-bottom: 10px; }}
  .sec-body {{ font-size: 14px; line-height: 1.65; color: #374151; margin-bottom: 12px; }}
  .sec-link {{ display: inline-block; font-size: 12.5px; color: #1e40af; text-decoration: none; font-weight: 600; padding: 6px 0; border-bottom: 1px solid #1e40af; }}
  .ft {{ background: #f9fafb; padding: 24px; font-size: 11.5px; color: #6b7280; line-height: 1.7; border-top: 2px solid #002a3e; }}
  .ft strong {{ color: #1f2937; }}
  .tip {{ background: #fffbeb; border: 1px solid #fbbf24; border-radius: 4px; padding: 14px 18px; margin: 0; font-size: 13px; color: #78350f; }}
  .tip strong {{ color: #92400e; }}
</style>
</head>
<body>
<div class="wrap">

<div class="hd">
  <div class="lb">TE Communications — Daily Media Intelligence</div>
  <h1>Tagesreport</h1>
  <div class="dt">{date_str} — 07:00 CET</div>
</div>

<div class="cta-wrap">
  <a class="cta" href="{DASHBOARD_URL}">▶ Vollständigen Report öffnen</a>
  <div class="meta">{meta_info}</div>
</div>

{sections_html}

<div class="tip">
  <strong>Tipp:</strong> Den Report als App auf Deinem Home-Bildschirm speichern — auf dem iPad/iPhone Safari öffnen, Teilen-Symbol antippen → "Zum Home-Bildschirm". Auf dem Desktop in Chrome via Drei-Punkte-Menü → "App installieren".
</div>

<div class="ft">
  <strong>Methodik:</strong> Zwei-Pass-Architektur — Pass 1 (Opus 4.7 + Web Search) für Markt-Tiefenanalyse, Pass 2 (Sonnet 4.6) für Pitch-Erstellung. 213+ RSS-Feeds, 14 direkte Webseiten-Crawls, Live Web Search.<br><br>

  <strong>13 Kunden im Briefing:</strong><br>
  PGIM &middot; T. Rowe Price &middot; MK Global Kapital &middot; Franklin Templeton &middot; Eurizon &middot; Bitcoin Suisse &middot; KKR &middot; Aegon AM &middot; Bendura Bank &middot; DNB AM &middot; Insight Investment &middot; JOHCM &middot; Maverix<br><br>

  <strong>Qualitätshinweis:</strong> Automatisch erstellt. Kurse, Zahlen und Sprecher-Angaben vor Verwendung in Kundenkommunikation gegen zweite Quelle prüfen.<br><br>

  <strong>TE Communications GmbH</strong> &mdash; Frankfurt &middot; Zürich &middot; St. Gallen &middot; Lausanne<br>
  Automatisierter Versand. Antworten an: sdj@te-communications.com
</div>

</div>
</body>
</html>'''


def build_plain_text(date_str, sections):
    """Plain text fallback for email clients without HTML."""
    text = f"""TE COMMUNICATIONS — DAILY MEDIA INTELLIGENCE
{date_str} — 07:00 CET
{'=' * 50}

Vollstaendigen Report im Dashboard oeffnen:
{DASHBOARD_URL}

DIESE E-MAIL ENTHAELT KURZFASSUNGEN ALLER ABSCHNITTE.
Fuer vollstaendige Inhalte den Link oben oeffnen.

"""

    section_keywords = [
        ("Quellenlage", ["Quellen", "Zugriffslage"]),
        ("Top 5 Themen", ["Top 5 Themen", "Top 3 Themen"]),
        ("Markt-Narrativ", ["Marktrecherche-Ueberblick", "Markt-Recherche"]),
        ("Tiefenanalyse", ["Tiefenanalyse", "Themen die das"]),
        ("White Spaces", ["White Spaces", "Unterdiskutiert"]),
        ("Konkurrenz", ["Konkurrenz"]),
        ("Kunden-Live-Recherche", ["KUNDEN-LIVE", "Live-Recherche"]),
        ("Termine", ["Termine"]),
        ("Themen-Priorisierung", ["Priorisierte Themen", "Themen-Tabelle"]),
        ("Positionierungs-Mapping", ["Positionierungs-Mapping"]),
        ("Top-7 Pitches", ["Pitch-Empfehlungen", "Top-7"]),
        ("Mehrtages-Trends", ["Mehrtages-Trends"]),
        ("Gesamtfazit", ["Gesamtfazit", "Fazit"]),
    ]

    for label, kws in section_keywords:
        title, content = find_section(sections, *kws)
        if title and content:
            text += f"\n{'-' * 50}\n{label.upper()}\n{'-' * 50}\n"
            text += teaser(content, 400, 6) + "\n"
            text += f"\n→ {LATEST_HTML_URL}#{slug(title)}\n"

    text += f"""

{'=' * 50}
TE Communications GmbH
Frankfurt | Zuerich | St. Gallen | Lausanne
Automatisierter Versand. Antworten an: sdj@te-communications.com
"""
    return text


def send_report_email():
    """Send the daily report as a teaser email with deep links."""
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").strip()
    recipients_raw = os.environ.get("EMAIL_RECIPIENTS", "").strip()

    if not smtp_user or not smtp_pass:
        print("[EMAIL] SMTP_USER or SMTP_PASS not configured — skipping email send")
        return False
    if not recipients_raw:
        print("[EMAIL] No EMAIL_RECIPIENTS configured — skipping email send")
        return False

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        print("[EMAIL] No valid recipients found — skipping")
        return False

    date_str = get_today_str_de()
    html_path, md_path = find_latest_report()

    if not md_path:
        print("[EMAIL] No markdown report found — cannot generate teaser email")
        return False

    print(f"[EMAIL] Loading report sections from {md_path.name}")

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
    except Exception as e:
        print(f"[EMAIL] Could not read report: {e}")
        return False

    sections = parse_report_sections(md_text)
    print(f"[EMAIL] Parsed {len(sections)} sections from report")

    meta_info = f"{len(sections)} Abschnitte | Vollständige Analyse im Dashboard"

    print(f"[EMAIL] Sending teaser email to {len(recipients)} recipients...")

    msg = EmailMessage()
    msg["Subject"] = f"TE Daily Media Intelligence — {date_str}"
    msg["From"] = f"TE Media Intelligence <{smtp_user}>"
    msg["To"] = ", ".join(recipients)
    msg["Reply-To"] = "sdj@te-communications.com"

    msg.set_content(build_plain_text(date_str, sections))

    html_body = build_email_html(date_str, sections, meta_info)
    msg.add_alternative(html_body, subtype="html")

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx, timeout=30) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[EMAIL] ✓ Sent successfully to: {', '.join(recipients)}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] ✗ SMTP authentication failed. Check that SMTP_PASS is a Gmail App-Password (16 chars, no spaces).")
        return False
    except Exception as e:
        print(f"[EMAIL] ✗ Send failed: {e}")
        return False


if __name__ == "__main__":
    send_report_email()
    exit(0)
