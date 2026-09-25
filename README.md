# HistoScroll – GitHub Pages + private Konten + optionaler Pi-Videoserver

HistoScroll ist als installierbare Web-App (PWA) für Android, iPhone/iPad und Desktop aufgebaut.

## Architektur

- **GitHub Pages** hostet nur die statische App (`public/`). Keine Lehrbuch-PDF und kein mitgelieferter Lehrbuchtext wird dort veröffentlicht.
- **Supabase Auth + private Storage/Postgres** verwaltet passwortlose Benutzerkonten sowie die privaten Clip-Pakete jedes Kontos. RLS sorgt dafür, dass Benutzer nur ihre eigenen Bücher sehen.
- **PDF-Verarbeitung bleibt lokal im Browser.** HistoScroll liest Text aus der ausgewählten PDF und lädt das Original-PDF nicht automatisch hoch.
- **Raspberry Pi 5 ist optional.** Er wird nur benötigt, wenn später echte MP4/WebM-Videos gespeichert und gestreamt werden sollen. Text-/Szenen-Clips funktionieren ohne Pi.

## Was jetzt funktioniert

- Passwortlose Konten per E-Mail-Einmalcode. Eine neue E-Mail-Adresse erhält beim ersten Login automatisch ein eigenes Konto.
- Pro Konto getrennte Bücher, Clips und Fokus-Shorts.
- Buchimport per PDF, Textpassage oder HistoScroll-JSON-Paket.
- Zentrale Synchronisierung: Auf PC/Laptop Clips erstellen oder importieren, danach auf S24 Ultra/iPhone mit demselben Konto abrufen.
- Lückenfüller für bislang nicht als Fokusclip verwendete Quellabschnitte.
- Deutsche Browser-TTS-Stimmen; keine englische Stimme als Fallback für deutschen Text.
- PWA-Installation auf Android und iOS.
- Optionales echtes Video pro Clip. Eine Datei kann auf den Pi geladen und mit dem Clip verknüpft werden. Die App ruft beim Abspielen einen 15 Minuten gültigen signierten URL vom Pi ab.
- Bestehender Canvas/WebM-Export bleibt verfügbar.

## Datenschutz / Lehrbücher

`public/` enthält **keine** Daten des mitgelieferten Histologie-Lehrbuchs.

Dein bisheriges privates 803-Clip-Paket gehört **nicht** ins öffentliche Repository. Importiere es nach der ersten Anmeldung über **Clip-Studio → Vorbereitetes Clip-Paket importieren**.

## Einrichtung

Siehe **GITHUB_SUPABASE_SETUP.md**. Supabase-Projekt und RLS-Schema sind für diese Deployment-Version bereits vorbereitet; `public/config.js` enthält nur den dafür vorgesehenen öffentlichen Publishable Key.

Für GitHub Pages muss unter GitHub → Settings → Pages als Source **GitHub Actions** ausgewählt sein. Der enthaltene Workflow veröffentlicht `public/` automatisch.

## Optional: echte Videos auf dem Pi 5

Siehe **PI_VIDEO_SETUP.md**. Der Ordner `pi-media-server/` enthält einen Docker-Dienst mit:

- Upload nur für angemeldete HistoScroll-Benutzer,
- Benutzertrennung anhand des Supabase-Tokens,
- SQLite-Metadaten,
- großen Videodateien auf einem frei wählbaren Pi-Laufwerk,
- kurzlebigen HMAC-signierten Streaming-URLs.

## Lokaler Test / Build

```bash
npm test
npm run build
```

Der statische GitHub-Pages-Build landet in `dist/`. Private Seed-Daten und Pi-Server werden absichtlich nicht in `dist/` kopiert.
