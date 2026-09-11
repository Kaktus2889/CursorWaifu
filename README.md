# CursorWaifu

Oryginalna chibi anime, która mieszka na pulpicie i płynnie biega za kursorem.

## Pobierz dla Windows

**[Pobierz CursorWaifu.exe](https://github.com/Kaktus2889/ProgramTestowy/releases/latest/download/CursorWaifu.exe)**

Pobierz plik i uruchom — instalowanie Pythona ani rozpakowywanie ZIP-a nie jest wymagane. Program nie ma podpisu cyfrowego; sprawdź, czy pobierasz go z tego repozytorium.

## Możliwości

- płynny ruch z przyspieszaniem i hamowaniem,
- osiem nowych klatek biegu z tempem kroków zależnym od prędkości,
- ruch niezależny od FPS, płynne hamowanie i stabilny dystans od kursora,
- rozciąganie, taniec, podskoki, machanie i oddychanie; łącznie 28 klatek,
- animacje bezczynności, mrugania, reakcji i snu,
- przeciąganie postaci lewym przyciskiem myszy,
- reakcja na kliknięcie i podwójne kliknięcie,
- menu pod prawym przyciskiem oraz ikona w zasobniku,
- trzy rozmiary i trzy prędkości,
- zapamiętywanie ustawień i pozycji,
- opcjonalny start razem z Windowsem.

## Uruchomienie

Wymagany jest Python 3.10 lub nowszy.

```powershell
python -m pip install -r requirements.txt
python app.py
```

## Budowanie programu EXE

Na Windowsie uruchom plik `build.bat`. Gotowy program pojawi się jako:

```text
dist\CursorWaifu.exe
```

## Sterowanie

- **lewy przycisk i przeciągnięcie** — przenoszenie postaci,
- **podwójne kliknięcie** — taniec,
- **puszczenie po przeciągnięciu** — podskok,
- **prawy przycisk** — taniec, rozciąganie, siadanie, sen i wybudzenie,
- **prawy przycisk** — ustawienia i zamknięcie programu,
- **ikona obok zegara** — ponowne pokazanie i zamknięcie aplikacji.

Grafika postaci została przygotowana specjalnie dla tego projektu. Nie zawiera postaci z istniejącego anime.
