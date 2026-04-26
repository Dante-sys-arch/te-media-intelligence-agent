"""
TE Communications — E-Mail-Versand-Modul
=========================================
Versendet den taeglichen Report per E-Mail an das TE-Team.
Wird vom GitHub Actions Workflow nach erfolgreichem Lauf aufgerufen.

Benoetigt drei GitHub Secrets:
  SMTP_USER         — z.B. te.intelligence@gmail.com
  SMTP_PASS         — Gmail App-Passwort (16 Zeichen, kein normales Passwort!)
  EMAIL_RECIPIENTS  — komma-separierte Liste, z.B. sdj@te-communications.com,team@te-communications.com
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timedelta

DASHBOARD_URL = "https://dante-sys-arch.github.io/te-media-intelligence-agent/"
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
    """Find the most recent HTML report."""
    output_dir = Path("output")
    if not output_dir.exists():
        return None
    htmls = sorted(output_dir.glob("*_TE_Media_Intelligence.html"), reverse=True)
    return htmls[0] if htmls else None


def build_email_html(date_str, report_path):
    """Build a clean HTML email with key info + dashboard link."""
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #1f2937; line-height: 1.6; background: #fafafa; }}
  .header {{ text-align: center; border-bottom: 3px solid #002a3e; padding-bottom: 16px; margin-bottom: 20px; background: #fff; padding: 20px; border-radius: 8px; }}
  .header .label {{ font-size: 10px; letter-spacing: 0.3em; text-transform: uppercase; color: #002a3e; font-weight: 700; }}
  .header h1 {{ font-size: 22px; color: #002a3e; margin: 8px 0 4px; }}
  .header .date {{ font-size: 13px; color: #6b7280; }}
  .cta {{ display: block; background: #002a3e; color: #fff !important; text-align: center; padding: 14px 24px; border-radius: 6px; text-decoration: none; font-size: 16px; font-weight: 700; margin: 20px 0; }}
  .info {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 16px 20px; margin-bottom: 16px; font-size: 14px; }}
  .info h2 {{ font-size: 14px; color: #002a3e; margin-bottom: 8px; }}
  .info ul {{ padding-left: 20px; margin: 0; }}
  .info li {{ margin-bottom: 4px; font-size: 13.5px; }}
  .badges {{ display: block; margin-top: 12px; font-size: 11px; color: #6b7280; }}
  .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; text-align: center; }}
</style>
</head>
<body>

<div class="header">
  <div class="label">TE Communications — Daily Media Intelligence</div>
  <h1>Tagesreport ist da</h1>
  <div class="date">{date_str} — 07:00 CET</div>
</div>

<div class="info">
  <h2>Was Du im Report findest:</h2>
  <ul>
    <li><strong>Top 5 Themen des Tages</strong> — Schnelluebersicht</li>
    <li><strong>Markt-Narrativ</strong> mit Zweitrundeneffekten und Belastbarkeit</li>
    <li><strong>White Spaces</strong> — unterdiskutierte Themen mit Pitch-Chance</li>
    <li><strong>Konkurrenz-Beobachtung</strong> — was machen BlackRock, DWS, Apollo &amp; Co.</li>
    <li><strong>Live-Sprecher-Recherche</strong> pro Kunde (heute verifiziert)</li>
    <li><strong>Positionierungs-Mapping</strong> mit fertigen Pitches pro Kunde</li>
    <li><strong>Top-7 Pitch-Empfehlungen</strong> mit ready-to-send Mail-Vorschlaegen</li>
    <li><strong>Termine</strong> der naechsten 7 Tage</li>
  </ul>
</div>

<a href="{DASHBOARD_URL}" class="cta">▶ Aktuellen Report &amp; Dashboard oeffnen</a>

<div class="info">
  <h2>Tipp: Als App auf Deinem Geraet</h2>
  <p style="margin: 0; font-size: 13px;">Oeffne den Dashboard-Link in Safari (iPad/iPhone) oder Chrome (Desktop) und speichere ihn als App auf dem Home-Bildschirm: <em>Teilen-Symbol &rarr; Zum Home-Bildschirm</em>. Dann hast Du jeden Morgen ein Tap-Icon fuer den aktuellen Report.</p>
</div>

<div class="footer">
  <strong>Kunden:</strong><br>
  PGIM &middot; T. Rowe Price &middot; MK Global Kapital &middot; Franklin Templeton &middot; PIMCO &middot; Eurizon &middot; Temasek &middot; Bitcoin Suisse &middot; KKR<br><br>
  <strong>TE Communications GmbH</strong> &mdash; Frankfurt &middot; Zuerich &middot; St. Gallen &middot; Lausanne<br>
  Automatisierter Versand. Antworten an: sdj@te-communications.com
</div>

</body>
</html>"""


def send_report_email():
    """Send the daily report via SMTP to all recipients."""
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
    report_path = find_latest_report()
    if not report_path:
        print("[EMAIL] No report file found — skipping")
        return False

    print(f"[EMAIL] Sending report '{report_path.name}' to {len(recipients)} recipients...")

    msg = EmailMessage()
    msg["Subject"] = f"TE Daily Media Intelligence — {date_str}"
    msg["From"] = f"TE Media Intelligence <{smtp_user}>"
    msg["To"] = ", ".join(recipients)
    msg["Reply-To"] = "sdj@te-communications.com"

    # Plain text fallback
    plain = f"""TE Communications — Daily Media Intelligence
{date_str} — 07:00 CET

Der Tagesreport ist da.

Aktuellen Report im Dashboard oeffnen:
{DASHBOARD_URL}

Im Anhang: vollstaendiger Report als HTML zum direkten Lesen.

Was Du im Report findest:
- Top 5 Themen des Tages
- Markt-Narrativ mit Zweitrundeneffekten und Belastbarkeit
- White Spaces (unterdiskutierte Themen)
- Konkurrenz-Beobachtung
- Live-Sprecher-Recherche pro Kunde
- Positionierungs-Mapping mit fertigen Pitches
- Top-7 Pitch-Empfehlungen mit ready-to-send Mails
- Termine der naechsten 7 Tage

Kunden: PGIM, T. Rowe Price, MK Global Kapital, Franklin Templeton,
PIMCO, Eurizon, Temasek, Bitcoin Suisse, KKR

TE Communications GmbH — Frankfurt, Zuerich, St. Gallen, Lausanne
"""
    msg.set_content(plain)

    # HTML body
    html_body = build_email_html(date_str, report_path)
    msg.add_alternative(html_body, subtype="html")

    # Attach the full HTML report
    try:
        with open(report_path, "rb") as f:
            report_data = f.read()
        msg.add_attachment(
            report_data,
            maintype="text",
            subtype="html",
            filename=report_path.name
        )
        print(f"[EMAIL] Attached report ({len(report_data):,} bytes)")
    except Exception as e:
        print(f"[EMAIL] Could not attach report: {e}")

    # Send via SMTP
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
    success = send_report_email()
    # Don't fail the workflow if email fails — report is still on dashboard
    exit(0)
