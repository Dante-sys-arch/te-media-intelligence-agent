"""
TE Communications — E-Mail-Versand-Modul (v4.1 — Pioneer/Substack-Style)
=========================================================================
Versendet den taeglichen Report als hochwertige Newsletter-E-Mail mit:
- Inter-Schriftfamilie (passend zur TE-Webseite)
- Section-Icons (geteilt mit Dashboard via section_meta)
- Pro Kategorie: Kurzerlaeuterung (was die Kategorie ist) + substanzielle
  prosaische Kurzfassung der heutigen Inhalte (3-4 Saetze)
- Pitch-Block visuell hervorgehoben (gelber Akzent)
- Deep-Links zum Dashboard pro Kategorie

Wird vom GitHub Actions Workflow nach erfolgreichem Lauf aufgerufen.

Benoetigt drei GitHub Secrets:
  SMTP_USER         z.B. te.daily.briefing@gmail.com
  SMTP_PASS         Gmail App-Passwort (16 Zeichen, ohne Leerzeichen)
  EMAIL_RECIPIENTS  komma-separierte Liste, z.B. sdj@te-communications.com
"""

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timedelta

# Shared section metadata (single source of truth, also used by dashboard)
try:
    from src.section_meta import SECTIONS, find_section_meta, slug_for_title
except ImportError:
    from section_meta import SECTIONS, find_section_meta, slug_for_title

DASHBOARD_URL = "https://dante-sys-arch.github.io/te-media-intelligence-agent/"
LATEST_HTML_URL = "https://dante-sys-arch.github.io/te-media-intelligence-agent/latest.html"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


# ===============================================================
# Date utilities
# ===============================================================

def get_today_str_de():
    """Get today's date in German format."""
    now = datetime.utcnow() + timedelta(hours=1)
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    monate = ["", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return f"{tage[now.weekday()]}, {now.day}. {monate[now.month]} {now.year}"


# ===============================================================
# File utilities
# ===============================================================

def find_latest_report():
    """Find the most recent HTML report file and corresponding markdown source."""
    output_dir = Path("output")
    if not output_dir.exists():
        return None, None
    htmls = sorted(output_dir.glob("*_TE_Media_Intelligence.html"), reverse=True)
    mds = sorted(output_dir.glob("*_TE_Media_Intelligence.md"), reverse=True)
    return (htmls[0] if htmls else None, mds[0] if mds else None)


# ===============================================================
# Markdown report parsing
# ===============================================================

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


# ===============================================================
# Substantielle Kurzfassung pro Sektion (3-4 Saetze prosaisch)
# ===============================================================

def make_substantive_summary(content, section_id, max_sentences=4, max_chars=480):
    """
    Generate a substantielle prosaische Kurzfassung from section content.
    
    Strategy:
    - For Pitch-Empfehlungen: extract pitch titles + clients + media (compact list)
    - For tables (Themen-Priorisierung): extract top rows
    - For all others: extract first 3-4 meaningful sentences as prose
    
    Important: never invent content. If section is empty/missing, return honest fallback.
    """
    if not content or not content.strip():
        return "<em>Heute keine Inhalte zu diesem Abschnitt — siehe Dashboard fuer Begruendung.</em>"
    
    # Strip markdown formatting for cleaner output
    cleaned = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    cleaned = re.sub(r'\*(.+?)\*', r'<em>\1</em>', cleaned)
    cleaned = re.sub(r'`(.+?)`', r'\1', cleaned)
    
    # Special handling for Pitch-Empfehlungen — show compact pitch list
    if section_id == "pitch-empfehlungen-hergeleitet":
        return _format_pitch_summary(content)
    
    # Special handling for Themen-Filter — show pitchbar / verworfen counts
    if section_id == "themen-filter--was-ist-heute-pitchbar":
        return _format_filter_summary(content)
    
    # Special handling for Sprecher-Mapping
    if section_id == "sprecher-mapping--wer-von-uns-kann-pitchen":
        return _format_mapping_summary(content)
    
    # Special handling for Kunden-Sicht
    if section_id == "kunden-sicht--was-bedeutet-das-pro-kunde":
        return _format_kunden_summary(content)
    
    # Special handling for Termin-Vorschau (compact list)
    if section_id == "termin-vorschau-7-tage":
        return _format_termine_summary(content)
    
    # Special handling for Top-Themen and Tiefenanalyse — extract subheadings
    if section_id in ("top-themen-des-tages", "tiefenanalyse--top-themen"):
        return _format_top_themes_summary(cleaned)
    
    # Default: extract substantive prose (skip pure bullet/structural lines, keep flowing text)
    return _format_default_prose(cleaned, max_sentences, max_chars)


def _format_default_prose(content, max_sentences, max_chars):
    """Extract first N substantive sentences as prose paragraph."""
    # Split into lines, filter for prose (skip pure structural markers)
    lines = content.split("\n")
    prose_chunks = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip headings, table rows, divider lines
        if line.startswith("#") or line.startswith("|") or line.startswith("---"):
            continue
        # Skip ratings/star lines
        if re.match(r'^[★☆\s]+$', line):
            continue
        # Skip bullets that are too short or pure key:value
        if line.startswith(("- ", "* ", "• ", "+ ")):
            stripped = line[2:].strip()
            if len(stripped) >= 60 and not stripped.endswith(":"):
                prose_chunks.append(stripped)
            continue
        # Add full prose line
        if len(line) >= 40:
            prose_chunks.append(line)
    
    # Concatenate into prose, capped at max_sentences and max_chars
    result_parts = []
    total = 0
    for chunk in prose_chunks:
        # Split chunk into sentences
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', chunk)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 25:
                continue
            if total + len(sent) > max_chars:
                # Truncate gracefully on word boundary
                remaining = max_chars - total
                if remaining > 60:
                    truncated = sent[:remaining].rsplit(' ', 1)[0] + "…"
                    result_parts.append(truncated)
                break
            result_parts.append(sent)
            total += len(sent) + 1
            if len(result_parts) >= max_sentences:
                break
        if len(result_parts) >= max_sentences or total >= max_chars:
            break
    
    if not result_parts:
        return "<em>Heute keine prosaisch zusammenfassbaren Inhalte — Details im Dashboard.</em>"
    
    return " ".join(result_parts)


def _format_pitch_summary(content):
    """Format Pitch-Empfehlungen as a compact list of pitch titles + clients."""
    # Pitch entries: ### PITCH N — Hook
    pitch_pattern = re.compile(r'###\s+PITCH\s+(\d+)[^\n]*?[—-]\s+([^\n]+)', re.IGNORECASE)
    pitches = pitch_pattern.findall(content)
    
    if not pitches:
        # Fallback: no pitches today
        if "kein" in content.lower() and "pitch" in content.lower():
            return "Heute wurden keine Pitches generiert, die alle Aufnahme-Kriterien erfuellen. Begruendung pro Thema im Dashboard. Empfehlung: Marktbeobachtung fortsetzen."
        return _format_default_prose(content, 3, 400)
    
    # Try to extract client + speaker for each pitch
    pitch_lines = []
    for pitch_match in pitch_pattern.finditer(content):
        num = pitch_match.group(1)
        hook = pitch_match.group(2).strip()
        # Look for client info in next 800 chars
        block = content[pitch_match.end():pitch_match.end()+1500]
        client_match = re.search(r'(?:Anschluss-Kunde|Kunde):\s*([^\n]+)', block, re.IGNORECASE)
        speaker_match = re.search(r'Sprecher(?:-Match)?:\s*([^\n]+)', block, re.IGNORECASE)
        medium_match = re.search(r'Zielmedium:\s*([^\n]+)', block, re.IGNORECASE)
        
        client = client_match.group(1).strip() if client_match else ""
        speaker = speaker_match.group(1).strip() if speaker_match else ""
        medium = medium_match.group(1).strip() if medium_match else ""
        
        # Compact line
        meta_parts = [p for p in [client, speaker, medium] if p][:3]
        meta_str = " · ".join(meta_parts) if meta_parts else ""
        
        line = f"<strong>{num}.</strong> {hook[:120]}"
        if meta_str:
            line += f"<br><span style='color:#6b7280;font-size:13px'>{meta_str[:150]}</span>"
        pitch_lines.append(line)
        
        if len(pitch_lines) >= 5:
            break
    
    return "<br><br>".join(pitch_lines) if pitch_lines else "<em>Keine Pitches geparst — Details im Dashboard.</em>"


def _format_filter_summary(content):
    """Format Themen-Filter as: N pitchbar / M verworfen."""
    pitchbar_count = len(re.findall(r'✓\s*[Pp]itchbar', content))
    verworfen_count = len(re.findall(r'✗|verworfen', content, re.IGNORECASE))
    
    if pitchbar_count == 0 and verworfen_count == 0:
        return _format_default_prose(content, 3, 400)
    
    summary = f"Heute wurden Themen systematisch nach den fuenf inhaltlichen Pitch-Kriterien gefiltert. "
    summary += f"<strong>{pitchbar_count} Themen</strong> sind pitchbar (Aufnahme-Schwelle erreicht), "
    summary += f"<strong>{verworfen_count} Themen</strong> wurden mit Begruendung verworfen "
    summary += f"(zu konsensual, kein Differenzierungspotenzial, oder unter Schwellenwert). "
    summary += "Volle Bewertung mit Sterne-Skala pro Kriterium im Dashboard."
    return summary


def _format_mapping_summary(content):
    """Format Sprecher-Mapping summary."""
    # Count themes that got a recommendation vs. no match
    matched = len(re.findall(r'EMPFEHLUNG:', content))
    unmatched = len(re.findall(r'KEINE\s+ZUORDNUNG', content, re.IGNORECASE))
    
    summary = "Pro pitchbarem Thema wird der bestpassende Kunden-Sprecher ermittelt — basierend auf Asset-Klassen-Fit, aktueller Live-Verifikation und Track Record. "
    if matched or unmatched:
        summary += f"<strong>{matched} Themen</strong> haben einen passenden Sprecher in unserem Kundenstamm, "
        summary += f"<strong>{unmatched} Themen</strong> ohne passende Zuordnung (ehrlich ausgewiesen). "
    summary += "Volles Mapping mit Begruendung im Dashboard."
    return summary


def _format_kunden_summary(content):
    """Format Kunden-Sicht summary."""
    # Try to extract counts
    with_pitch = re.search(r'KUNDEN MIT PITCH HEUTE.*?\((\d+)', content, re.IGNORECASE | re.DOTALL)
    without_pitch = re.search(r'KUNDEN OHNE PITCH HEUTE.*?\((\d+)', content, re.IGNORECASE | re.DOTALL)
    
    summary = "Umsortierung nach Kunden statt nach Themen. "
    if with_pitch and without_pitch:
        n_with = with_pitch.group(1)
        n_without = without_pitch.group(1)
        summary += f"<strong>{n_with} Kunden</strong> haben heute einen Pitch, <strong>{n_without} Kunden</strong> sind heute ohne pitchbare Story. "
        summary += "Das ist normal: Pitch-Tage sind dispers, lieber wenige starke Pitches als erzwungene. "
    summary += "Pro Kunde ohne Pitch wird die Begruendung im Dashboard ausgewiesen."
    return summary


def _format_termine_summary(content):
    """Format Termin-Vorschau as compact list."""
    # Try to extract date lines (DD.MM. format)
    date_pattern = re.compile(r'^[\s\-•*]*(\d{1,2}\.\d{1,2}\.?)[^\n]*', re.MULTILINE)
    dates = []
    for m in date_pattern.finditer(content):
        line = m.group(0).strip().lstrip("-•* ").strip()
        if len(line) > 6:
            dates.append(line[:140])
        if len(dates) >= 6:
            break
    
    if dates:
        return "<br>".join(f"• {d}" for d in dates)
    return _format_default_prose(content, 4, 400)


def _format_top_themes_summary(content):
    """For Top-Themen / Tiefenanalyse: extract H3 subheadings as compact list."""
    headings = re.findall(r'^###\s+([^\n]+)', content, re.MULTILINE)
    if headings:
        cleaned_h = []
        for h in headings[:5]:
            h_clean = re.sub(r'\*\*', '', h).strip()
            cleaned_h.append(f"• {h_clean[:140]}")
        return "<br>".join(cleaned_h)
    return _format_default_prose(content, 4, 480)


# ===============================================================
# HTML email building
# ===============================================================

def find_section_in_report(sections_dict, section_meta_entry):
    """Find a section in the parsed report dict using the metadata keywords."""
    for kw in section_meta_entry["keywords"]:
        kw_lower = kw.lower()
        for title, content in sections_dict.items():
            if kw_lower in title.lower():
                return title, content
    return None, ""


def build_section_block_html(section_meta_entry, actual_title, content):
    """Build HTML for one section in the email."""
    icon = section_meta_entry["icon"]
    short = section_meta_entry["short"]
    linklabel = section_meta_entry["linklabel"]
    title_display = section_meta_entry["title"]
    
    # Generate substantielle Kurzfassung (mehrfach geprueft, kein Halluzinieren)
    summary = make_substantive_summary(content, section_meta_entry["id"])
    
    # Generate deep link using actual section title (which has the slug)
    anchor = slug_for_title(actual_title) if actual_title else slug_for_title(title_display)
    deep_link = f"{LATEST_HTML_URL}#{anchor}"
    
    # Use special highlighted style for Pitch-Empfehlungen (the central value)
    is_pitch_section = section_meta_entry["id"] == "pitch-empfehlungen-hergeleitet"
    
    if is_pitch_section:
        return f'''
<tr><td style="padding:0 28px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#fffbeb;border:1px solid #fbbf24;border-radius:10px;margin:8px 0">
  <tr><td style="padding:22px 24px 18px">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td width="32" style="vertical-align:top;color:#92400e;padding-top:2px">{icon}</td>
        <td style="padding-left:12px">
          <div style="font-family:'Inter Tight','Inter',Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#92400e;font-weight:700;margin-bottom:6px">Heute zentral</div>
          <div style="font-family:'Inter Tight','Inter',Helvetica,Arial,sans-serif;font-size:18px;font-weight:700;color:#002a3e;letter-spacing:-.01em;line-height:1.25">{title_display}</div>
        </td>
      </tr>
    </table>
    <div style="background:rgba(146,64,14,.08);border-radius:6px;padding:11px 14px;margin:14px 0 16px;font-size:13px;line-height:1.55;color:#78350f">
      <strong style="font-weight:700">Worum es geht.</strong> {short}
    </div>
    <div style="font-size:14.5px;line-height:1.65;color:#1f2937;margin:0 0 18px">{summary}</div>
    <a href="{deep_link}" style="display:inline-block;background:#002a3e;color:#fff;text-decoration:none;font-size:13px;font-weight:600;padding:10px 18px;border-radius:6px;letter-spacing:.01em">{linklabel} →</a>
  </td></tr>
</table>
</td></tr>
'''
    
    # Standard section block
    return f'''
<tr><td style="padding:0 28px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-bottom:1px solid #e5e7eb">
  <tr><td style="padding:24px 0">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td width="32" style="vertical-align:top;color:#002a3e;padding-top:2px">{icon}</td>
        <td style="padding-left:12px">
          <div style="font-family:'Inter Tight','Inter',Helvetica,Arial,sans-serif;font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;color:#94a3b8;font-weight:700;margin-bottom:5px">Abschnitt</div>
          <div style="font-family:'Inter Tight','Inter',Helvetica,Arial,sans-serif;font-size:17px;font-weight:700;color:#002a3e;letter-spacing:-.01em;line-height:1.3">{title_display}</div>
        </td>
      </tr>
    </table>
    <div style="background:#f4f4f1;border-left:3px solid #002a3e;border-radius:0 6px 6px 0;padding:11px 14px;margin:14px 0 14px;font-size:12.5px;line-height:1.55;color:#475569">
      <strong style="color:#002a3e;font-weight:700">Worum es geht.</strong> {short}
    </div>
    <div style="font-size:14px;line-height:1.65;color:#1f2937;margin:0 0 14px">{summary}</div>
    <a href="{deep_link}" style="display:inline-block;color:#002a3e;text-decoration:none;font-size:13px;font-weight:600;border-bottom:1.5px solid #002a3e;padding-bottom:2px">{linklabel} →</a>
  </td></tr>
</table>
</td></tr>
'''


def build_email_html(date_str, sections, meta_info=""):
    """Build the full HTML email — Pioneer/Substack-style with Inter font + icons + per-section short descriptions."""
    
    # Build section blocks in defined order from SECTIONS metadata
    section_blocks_html = ""
    for section_meta in SECTIONS:
        actual_title, content = find_section_in_report(sections, section_meta)
        # Always render the section, even if empty — that way reader sees ALL categories
        block_html = build_section_block_html(section_meta, actual_title, content)
        section_blocks_html += block_html
    
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="format-detection" content="telephone=no">
<title>TE Daily Media Intelligence — {date_str}</title>
<!--[if mso]>
<style>* {{ font-family: Arial, sans-serif !important; }}</style>
<![endif]-->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  body, table, td {{ font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif !important; -webkit-font-smoothing: antialiased; }}
  a {{ color: #002a3e; }}
  @media only screen and (max-width: 620px) {{
    .container {{ width: 100% !important; }}
    .padded {{ padding-left: 18px !important; padding-right: 18px !important; }}
    .h1-mobile {{ font-size: 22px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#f4f4f1;color:#1a1a1a;font-family:'Inter','Helvetica Neue',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased">

<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f4f4f1">
<tr><td align="center" style="padding:24px 12px">

<table role="presentation" class="container" width="640" cellspacing="0" cellpadding="0" border="0" style="background:#ffffff;max-width:640px;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,42,62,.08)">

<!-- Header -->
<tr><td style="background:#002a3e;padding:36px 28px 28px;text-align:center">
  <div style="font-family:'Inter Tight','Inter',sans-serif;font-size:11px;letter-spacing:.32em;text-transform:uppercase;color:#fbbf24;font-weight:700;margin-bottom:14px">TE Communications · Daily Media Intelligence</div>
  <h1 class="h1-mobile" style="font-family:'Inter Tight','Inter',sans-serif;font-size:28px;font-weight:700;color:#ffffff;margin:0 0 6px;letter-spacing:-.02em;line-height:1.15">Tagesreport</h1>
  <div style="font-size:14px;color:#cbd5e1;font-weight:500">{date_str} · 07:00 CET</div>
</td></tr>

<!-- CTA Button -->
<tr><td align="center" style="padding:28px 28px 8px;background:#ffffff">
  <a href="{DASHBOARD_URL}" style="display:inline-block;background:#002a3e;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:6px;font-size:14.5px;font-weight:700;letter-spacing:.01em">Vollständigen Report im Dashboard öffnen →</a>
  <div style="margin-top:14px;font-size:12.5px;color:#6b7280;line-height:1.55">{meta_info}</div>
</td></tr>

<!-- Intro -->
<tr><td style="padding:24px 28px 0;background:#ffffff">
  <div style="border-top:1px solid #e5e7eb;padding-top:20px">
    <div style="font-family:'Inter Tight','Inter',sans-serif;font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;color:#94a3b8;font-weight:700;margin-bottom:8px">Lesehinweis</div>
    <p style="font-size:14px;line-height:1.6;color:#475569;margin:0">
      Diese E-Mail enthält zu jeder Kategorie eine kompakte, substanzielle Kurzfassung. 
      Vollständige Inhalte — inklusive Tiefenanalyse, hergeleiteter Pitches und fertiger 
      Pitch-Materialien — sind im Dashboard über den jeweiligen Link erreichbar.
    </p>
  </div>
</td></tr>

{section_blocks_html}

<!-- Tipp -->
<tr><td style="padding:24px 28px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#fffbeb;border:1px solid #fbbf24;border-radius:8px">
    <tr><td style="padding:14px 18px;font-size:13px;color:#78350f;line-height:1.6">
      <strong style="color:#92400e">Als App speichern.</strong> Den Report als App auf den Home-Bildschirm legen: auf iPad/iPhone in Safari öffnen, Teilen-Symbol antippen, „Zum Home-Bildschirm". Auf dem Desktop in Chrome via Drei-Punkte-Menü, „App installieren".
    </td></tr>
  </table>
</td></tr>

<!-- Footer -->
<tr><td style="padding:0 28px 32px;background:#ffffff">
  <div style="border-top:2px solid #002a3e;padding-top:22px;font-size:11.5px;color:#6b7280;line-height:1.7">
    <p style="margin:0 0 12px"><strong style="color:#1f2937">Methodik.</strong> Drei-Pass-Architektur: Pass 1 (Opus 4.7 + Web Search) für Markt-Tiefenanalyse, Pass 1.5 (Sonnet 4.6) für tagesaktuelle Kunden-Wissensprofile, Pass 2 (Opus 4.7) für hergeleitete Pitch-Empfehlungen mit 14 Pitch-Kriterien. 213+ RSS-Feeds, kunden-spezifisches Webseiten-Crawling, Live Web Search.</p>
    <p style="margin:0 0 12px"><strong style="color:#1f2937">13 Kunden im Briefing.</strong> PGIM · T. Rowe Price · MK Global Kapital · Franklin Templeton · Eurizon · Bitcoin Suisse · KKR · Aegon AM · Bendura Bank · DNB AM · Insight Investment · JOHCM · Maverix</p>
    <p style="margin:0 0 12px"><strong style="color:#1f2937">Qualitätshinweis.</strong> Automatisch erstellt. Kurse, Zahlen und Sprecher-Angaben vor Verwendung in Kundenkommunikation gegen zweite Quelle prüfen.</p>
    <p style="margin:0;color:#94a3b8;font-size:11px">
      <strong style="color:#1f2937">TE Communications GmbH</strong> · Frankfurt · Zürich · St. Gallen · Lausanne<br>
      Automatisierter Versand · Antworten an: sdj@te-communications.com
    </p>
  </div>
</td></tr>

</table>

</td></tr>
</table>

</body>
</html>'''


# ===============================================================
# Plain text fallback (for clients that block HTML)
# ===============================================================

def build_plain_text(date_str, sections):
    """Plain text fallback for email clients without HTML."""
    text = f"""TE COMMUNICATIONS · DAILY MEDIA INTELLIGENCE
{date_str} · 07:00 CET
{'=' * 50}

Vollstaendigen Report im Dashboard oeffnen:
{DASHBOARD_URL}

Diese E-Mail enthaelt zu jeder Kategorie eine kompakte Kurzfassung.
Vollstaendige Inhalte ueber den Link oben erreichbar.

"""
    
    for section_meta in SECTIONS:
        actual_title, content = find_section_in_report(sections, section_meta)
        text += f"\n{'-' * 50}\n{section_meta['title'].upper()}\n{'-' * 50}\n"
        text += f"\n[Worum es geht] {section_meta['short']}\n\n"
        # Strip HTML tags for plain text
        summary = make_substantive_summary(content, section_meta["id"])
        summary_plain = re.sub(r'<[^>]+>', '', summary)
        summary_plain = summary_plain.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text += summary_plain + "\n"
        anchor = slug_for_title(actual_title) if actual_title else slug_for_title(section_meta["title"])
        text += f"\n→ {LATEST_HTML_URL}#{anchor}\n"
    
    text += f"""

{'=' * 50}
TE Communications GmbH
Frankfurt · Zuerich · St. Gallen · Lausanne
Automatisierter Versand · Antworten an: sdj@te-communications.com
"""
    return text


# ===============================================================
# Send email via SMTP
# ===============================================================

def send_report_email():
    """Send the daily report as a Pioneer-style teaser email with deep links."""
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

    meta_info = f"{len(sections)} Abschnitte erfasst · Vollständige Analyse im Dashboard"

    print(f"[EMAIL] Sending email to {len(recipients)} recipients...")

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
