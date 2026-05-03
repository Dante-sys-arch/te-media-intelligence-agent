# E-Mail-Versand einrichten (v3.10 Teaser-Struktur)

Der Agent kann den Tagesreport als anteasernde E-Mail mit Deep-Links zum Dashboard an Kollegen versenden.

## Was die E-Mail enthält

- Header mit Datum + großer "Vollständigen Report öffnen"-Button
- 13 Abschnitts-Anteaser:
  - Quellenlage
  - Top 5 Themen
  - Markt-Narrativ
  - Tiefenanalyse (Themen-Übersicht)
  - White Spaces
  - Konkurrenz-Beobachtung
  - Kunden-Live-Recherche (Sprecher)
  - Termine 7 Tage
  - Themen-Priorisierung
  - Positionierungs-Mapping (kompakt)
  - Top-7 Pitches (Titel + Kunde)
  - Mehrtages-Trends
  - Gesamtfazit
- Jeder Anteaser: 350-600 Zeichen Kurzfassung + Deep-Link
- Footer mit Methodik + Kunden-Liste

## Was NICHT in der E-Mail steht

- Volle Tiefenanalyse pro Thema (8-Punkte-Framework)
- Komplette Pitch-Mails
- Detailliertes Quellenverzeichnis

→ All das ist im Dashboard, jeder Anteaser hat den Deep-Link zum jeweiligen Abschnitt.

---

## Setup in 3 Schritten

### 1. Dedizierte Gmail-Adresse anlegen

1. https://accounts.google.com/signup
2. Adresse z.B. `te.daily.briefing@gmail.com`
3. **2-Faktor-Authentifizierung aktivieren** (Pflicht für App-Passwort):
   https://myaccount.google.com/security → "Bestätigung in zwei Schritten"
4. **App-Passwort generieren:**
   https://myaccount.google.com/apppasswords
   - App-Name: "TE Agent"
   - 16-stelligen Code kopieren (NICHT das normale Passwort!)

### 2. GitHub Secrets eintragen

https://github.com/Dante-sys-arch/te-media-intelligence-agent/settings/secrets/actions

→ "New repository secret" dreimal:

| Name | Wert |
|---|---|
| `SMTP_USER` | `te.daily.briefing@gmail.com` |
| `SMTP_PASS` | 16-stelliges App-Passwort (OHNE Leerzeichen) |
| `EMAIL_RECIPIENTS` | Komma-separiert: `sdj@te-communications.com,kollege1@te-communications.com` |

### 3. Test-Lauf

https://github.com/Dante-sys-arch/te-media-intelligence-agent/actions
→ "Run workflow"

Logs prüfen — Schritt "Send report via email":
- `[EMAIL] ✓ Sent successfully to: ...` → Alles OK
- `SMTP authentication failed` → App-Passwort neu generieren
- `No EMAIL_RECIPIENTS configured` → Secret-Namen exakt prüfen

---

## Empfänger jederzeit anpassen

GitHub → Settings → Secrets → `EMAIL_RECIPIENTS` → "Update"
- Adressen mit Komma trennen
- Wirksam ab nächstem Lauf — kein Code-Push nötig

---

## Workflow-Verhalten

- E-Mail-Versand passiert NACH erfolgreichem Lauf
- `continue-on-error: true` — falls E-Mail-Versand scheitert, bleibt der Report trotzdem im Dashboard
- Reply-To auf `sdj@te-communications.com` — Antworten landen bei Dir

## Versand-Sicherheit

- TLS via SMTP_SSL (Port 465)
- App-Passwort statt normales Passwort
- 2FA auf der Gmail-Adresse Pflicht
- Keine Anhänge — nur HTML-Body mit Deep-Links
