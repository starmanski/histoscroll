# HistoScroll – GitHub Pages + private Konten + optionaler Pi-Videoserver

HistoScroll ist als installierbare Web-App (PWA) für Android, iPhone/iPad und Desktop aufgebaut.

## Mobile V2

Die aktuelle Version ist mobile-first: Fullscreen-Swiping, Gesehen-Status, Neu/Alle/Likes/Favoriten-Filter und geräteübergreifender Nutzerstatus via Supabase. Ein separater PC-Generator erzeugt echte 9:16-MP4-Clips mit deutscher Neural-TTS und Animationen.

## Architektur

- **GitHub Pages** hostet nur die statische App. Keine Lehrbuch-PDF und kein mitgelieferter Lehrbuchtext wird dort veröffentlicht.
- **Supabase Auth + private Storage/Postgres** verwaltet passwortlose Benutzerkonten sowie die privaten Clip-Pakete jedes Kontos. RLS sorgt dafür, dass Benutzer nur ihre eigenen Bücher und ihren eigenen Clip-Status sehen.
- **PDF-Verarbeitung bleibt lokal im Browser.** HistoScroll liest Text aus der ausgewählten PDF und lädt das Original-PDF nicht automatisch hoch.
- **Raspberry Pi 5 ist optional.** Er wird nur benötigt, wenn später echte MP4/WebM-Videos gespeichert und gestreamt werden sollen. Text-/Szenen-Clips funktionieren ohne Pi.

## Was funktioniert

- Passwortlose Konten per E-Mail-Einmalcode.
- Pro Konto getrennte Bücher, Clips und Fokus-Shorts.
- Gesehen, Like und Favorit pro Clip; Status wird pro Konto synchronisiert.
- Mobile App-Ansicht mit echtem Short-Swiping ohne Mitscrollen der Seite.
- Buchimport per PDF, Textpassage oder HistoScroll-JSON-Paket.
- Deutsche Browser-TTS-Stimmen.
- PWA-Installation auf Android und iOS.
- Optionales echtes Video pro Clip über Pi-Medienserver.

## Datenschutz / Lehrbücher

Das öffentliche Repository enthält keine Daten des mitgelieferten Histologie-Lehrbuchs.

## Optional: echte Videos auf dem PC

Der HistoScroll-PC-Generator erzeugt echte 9:16-MP4-Dateien mit Animation, Textszenen und deutscher Neural-TTS. Die erzeugten Videos können später auf dem Pi-Medienserver gespeichert und mit den jeweiligen Clips verknüpft werden.
