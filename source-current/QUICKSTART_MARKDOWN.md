# HistoScroll Markdown-Format (V5)

Du kannst jetzt ganze Bücher/Clip-Pakete als **Markdown** exportieren und wieder importieren.

## Minimales Beispiel

```md
---
book_title: Taschenlehrbuch Histologie
author: Lüllmann-Rauch · Asan
edition: Eigener Import
page_count: 600
---

## CLIP
title: ADH öffnet den Wasserweg
category: Harnorgane
kind: editorial
pages: 564

### SCENE 1 | Einstieg
ADH erhöht die Wasserdurchlässigkeit von Hauptzellen im Sammelrohr.

### SCENE 2 | Denk kurz nach
:::reveal
prompt: Welcher Kanal wird in die apikale Membran eingebaut?
answer: AQP2.
:::

### SCENE 3 | Mini-Quiz
:::mcq
question: Wo sitzt der V2-Rezeptor?
+ Basolateral
- Apikal
- Im Zellkern
explanation: ADH bindet basolateral an den V2-Rezeptor.
:::
```

## Interaktive Typen

### Reveal-Karte

```md
### SCENE 2 | Denk kurz nach
:::reveal
prompt: Was wird in die apikale Membran eingebaut?
answer: AQP2.
:::
```

### Multiple Choice

```md
### SCENE 3 | Mini-Quiz
:::mcq
question: Wo sitzt der V2-Rezeptor?
+ Basolateral
- Apikal
- Im Zellkern
explanation: ADH bindet basolateral an den V2-Rezeptor.
:::
```

## Hinweise
- `+` markiert die **richtige Antwort**.
- `-` markiert eine **falsche Antwort**.
- Exportierte Markdown-Dateien lassen sich gut mit **NotebookLM** gegenchecken.
