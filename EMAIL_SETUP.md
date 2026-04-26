# E-Mail-Versand einrichten (5 Minuten)

Damit der tägliche Report automatisch per E-Mail an Dich und das Team verschickt wird, brauchst Du **drei GitHub Secrets**.

## Schritt 1 — Gmail App-Passwort erstellen (3 Minuten)

Du brauchst ein dediziertes Gmail-Konto (oder ein bestehendes), das die Reports verschickt.

1. Gehe zu **https://myaccount.google.com/security**
2. Aktiviere **2-Faktor-Authentifizierung** (falls noch nicht aktiv) — Pflicht für App-Passwörter
3. Gehe zu **https://myaccount.google.com/apppasswords**
4. App-Name eingeben: `TE Media Intelligence`
5. **Erstellen** → 16-stelliges Passwort wird angezeigt (z.B. `xxxx xxxx xxxx xxxx`)
6. **Notiere dieses Passwort** — Du brauchst es gleich, ohne Leerzeichen

Wichtig: Das ist NICHT Dein normales Gmail-Passwort. App-Passwörter sind sicherer und können jederzeit widerrufen werden.

## Schritt 2 — GitHub Secrets eintragen (2 Minuten)

Gehe zu **https://github.com/Dante-sys-arch/te-media-intelligence-agent/settings/secrets/actions**

Klicke auf **New repository secret** und trage diese drei Secrets ein:

### Secret 1: `SMTP_USER`
- **Name:** `SMTP_USER`
- **Value:** Deine Gmail-Adresse, z.B. `te.intelligence@gmail.com`

### Secret 2: `SMTP_PASS`
- **Name:** `SMTP_PASS`
- **Value:** Das 16-stellige App-Passwort von Schritt 1, ohne Leerzeichen

### Secret 3: `EMAIL_RECIPIENTS`
- **Name:** `EMAIL_RECIPIENTS`
- **Value:** Komma-separierte Liste der Empfänger, z.B.:
  ```
  sdj@te-communications.com,team@te-communications.com,bo@te-communications.com
  ```

## Schritt 3 — Testen

Starte den Workflow manuell:
**https://github.com/Dante-sys-arch/te-media-intelligence-agent/actions** → Run workflow

Nach ca. 5 Minuten sollte der Report im Posteingang aller Empfänger sein.

## Was die E-Mail enthält

- Begrüßung mit Datum
- Großer "Report öffnen"-Button → Dashboard
- Übersicht der Report-Inhalte (Stichpunkte)
- Hinweis "Als App auf dem Home-Bildschirm"
- Anhang: Vollständiger HTML-Report

## Wenn keine E-Mail kommt

Schau in die Workflow-Logs:
- Wenn dort steht `[EMAIL] SMTP_USER or SMTP_PASS not configured` → Secrets fehlen
- Wenn dort steht `SMTP authentication failed` → App-Passwort falsch eingegeben
- Wenn dort steht `Sent successfully` aber Du bekommst nichts → Spam-Ordner prüfen

## Empfänger ändern

Einfach das Secret `EMAIL_RECIPIENTS` aktualisieren (neuer Wert überschreibt alten). Beim nächsten Lauf gilt die neue Liste.
