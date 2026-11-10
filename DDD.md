# Zadanie 1 – model fragmentu aplikacji bankowej

Model obejmuje klienta, jego konta i przelewy pomiędzy kontami w tym samym banku. Podzieliłem go na trzy konteksty: Klienci, Konta i Przelewy. Każdy kontekst odpowiada za własne dane, a pozostałe obiekty wskazuje przez identyfikatory. Dla uproszczenia obsługiwane są tylko przelewy w PLN, bez kredytów i przewalutowania.

## Model

![Model DDD](docs/ddd-model.png)

## Konteksty i agregaty

- **Klienci** – agregat `Klient`, którego korzeniem jest encja Klient. Przechowuje dane osoby oraz obiekt wartości Adres.
- **Konta** – agregat `KontoBankowe`, z encją KontoBankowe jako korzeniem. Konto przechowuje identyfikator właściciela, NumerRachunku i saldo jako obiekt wartości Pieniadze.
- **Przelewy** – agregat `Przelew`, z encją Przelew jako korzeniem. Zawiera identyfikatory obu kont, kwotę i status realizacji.

Encje mają własną tożsamość (UUID). Obiekty wartości nie mają ID: porównuję je po zawartości i przy zmianie zastępuję całym nowym obiektem.

## Atrybuty i ograniczenia

| Element | Atrybuty i przyjęte zasady |
| --- | --- |
| Klient (encja) | `id: UUID`, `imie`, `nazwisko`, `email`, `adres: Adres`. Imię i nazwisko: 1–50 znaków po usunięciu skrajnych spacji, litery Unicode, spacja, apostrof i myślnik. Email: do 254 znaków, sprawdzany parserem adresów email, bez znaków sterujących. |
| Adres (obiekt wartości) | `ulica: 1–100 znaków`, `numer: 1–10 znaków`, `miasto: 1–60 znaków`, `kodPocztowy: NN-NNN`, `kraj: PL`. Pola wymagane; tekst bez HTML i znaków sterujących. |
| KontoBankowe (encja) | `id: UUID`, `klientId: UUID`, `numer: NumerRachunku`, `saldo: Pieniadze`, `status: AKTYWNE / ZABLOKOWANE / ZAMKNIETE`. Jeden właściciel, klient może mieć wiele kont. Numer rachunku jest unikalny. Saldo nie może być ujemne. |
| NumerRachunku (obiekt wartości) | Polski IBAN: `PL` i 26 cyfr, bez spacji w zapisie wewnętrznym. Oprócz formatu sprawdzana suma kontrolna modulo 97. |
| Pieniadze (obiekt wartości) | `wartosc: Decimal`, maksymalnie dwa miejsca po przecinku, `waluta: PLN`. Nie używam float. Saldo może wynosić 0; kwota przelewu musi być większa od 0 i nie większa niż 10 000,00 PLN. |
| Przelew (encja) | `id: UUID`, `kontoNadawcyId`, `kontoOdbiorcyId`, `kwota: Pieniadze`, `tytul: 1–140 znaków`, `utworzono: data i czas UTC`, `status: ZLECONY / WYKONANY / ODRZUCONY`. Tytuł jako zwykły tekst bez HTML i znaków sterujących. Konta muszą być różne. |

## Operacje i współpraca

1. Klient może zostać zarejestrowany po sprawdzeniu danych. Kontekst Konta sprawdza istnienie klienta przed otwarciem rachunku.
2. Zalogowany klient zleca przelew. Tożsamość pochodzi z sesji, a backend sprawdza, czy klient jest właścicielem konta nadawcy; samo podanie ID konta nie daje uprawnienia.
3. Kontekst Przelewy sprawdza format danych, kwotę i różne ID kont. Kontekst Konta sprawdza istnienie i aktywność obu rachunków oraz dostępne środki.
4. W tym małym modelu konteksty są modułami jednej aplikacji ze wspólną bazą. Obciążenie nadawcy, uznanie odbiorcy i zmiana statusu na WYKONANY odbywają się w jednej transakcji z blokadą obu kont. Błąd powoduje wycofanie zmian, więc pieniądze nie znikają pomiędzy kontami.
5. Ponowne żądanie z tym samym ID przelewu zwraca jego dotychczasowy wynik i nie obciąża konta ponownie. Przelewu wykonanego nie można edytować ani wykonać drugi raz.
6. Dane są sprawdzane na backendzie przy tworzeniu i zmianie obiektów. Hasła i logowanie pozostają poza zakresem modelu; zakładam istniejący moduł uwierzytelniania.
