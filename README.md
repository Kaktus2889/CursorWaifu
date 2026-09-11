# CursorWaifu

Oryginalna chibi anime, która mieszka na pulpicie i płynnie biega za kursorem.

## Pobierz dla Windows

**[Pobierz CursorWaifu.exe](https://github.com/Kaktus2889/ProgramTestowy/releases/latest/download/CursorWaifu.exe)**

Pobierz plik i uruchom — instalowanie Pythona ani rozpakowywanie ZIP-a nie jest wymagane. Program nie ma podpisu cyfrowego; sprawdź, czy pobierasz go z tego repozytorium.

## Możliwości

- płynny ruch z przyspieszaniem i hamowaniem,
- osiem nowych klatek biegu z tempem kroków zależnym od prędkości,
- ruch niezależny od FPS, płynne hamowanie i stabilny dystans od kursora,
- nowe pełne pozy stania bez uciętych stóp; bezpieczne marginesy klatek,
- rozciąganie, taniec, podskoki, machanie, rozglądanie, ziewanie, nieśmiała mina, kołysanie i oddychanie,
- na Windowsie opcjonalne obserwowanie miejsca pisania (pozycji kursora tekstowego),
- animacje bezczynności, mrugania, reakcji i snu,
- przeciąganie postaci lewym przyciskiem myszy,
- reakcja na kliknięcie i podwójne kliknięcie,
- menu pod prawym przyciskiem oraz ikona w zasobniku,
- trzy rozmiary i trzy prędkości,
- zapamiętywanie ustawień i pozycji,
- opcjonalny start razem z Windowsem.

## Uruchomienie

### Obserwowanie pisania i prywatność

Opcję **Patrz na miejsce pisania (bez odczytu tekstu)** wyłączysz prawym
przyciskiem myszy. Działa przy włączonym podążaniu. Postać podchodzi obok
systemowego kursora tekstowego, patrzy w jego stronę i mruga. Po kilku sekundach
bez zmiany pozycji kursora wraca do myszy. Można ją też ręcznie uśpić.

To obserwowanie geometrii, nie czytanie wiadomości: brak przechwytywania klawiszy,
odczytu tekstu, schowka, zrzutów ekranu i wysyłania danych. Nie rozumie wpisanej
treści. Niektóre przeglądarki, edytory i aplikacje rysują własny kursor i nie
udostępniają go tą metodą; wtedy działa zwykłe podążanie za myszą. Pozycję
ustala Windows [GetGUIThreadInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getguithreadinfo)
i [ClientToScreen](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-clienttoscreen).

### Z kodu źródłowego

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
