# Agenda de contacte

![CI](https://github.com/marianvitalie/map-proiect/actions/workflows/ci.yml/badge.svg)

Proiect individual la disciplina Metode avansate de programare, anul universitar 2026-2027.

## Autor

- **Nume:** Marian Vitalie
- **Grupa:** 1.2
- **Marca:** 715739
- **Tema:** 1 - Agenda de contacte

## Descriere

Serviciu web care gestionează o agendă de contacte. Permite adăugarea de contacte cu nume, email, telefon și categorie, căutarea după nume, filtrarea pe categorie, ștergerea și statistici pe categorii. Datele sunt validate la intrare, iar emailul este unic, indiferent de majuscule sau minuscule. Aplicația este scrisă în Python cu Flask, rulează într-un container Docker și este testată automat prin GitHub Actions.

## Tehnologii

Python 3.13 cu Flask

## Rulare

```
docker build -t map-proiect .
docker run -d -p 8080:8080 map-proiect
```

Aplicatia asculta pe portul 8080. Verificati:

```
curl http://localhost:8080/health
curl http://localhost:8080/version
```

## Testare

```
pip install -r requirements.txt pytest pytest-cov
python -m pytest --cov=src
```

## Rutele implementate

| Ruta | Metoda | Cod succes | Descriere |
|---|---|---|---|
| `/health` | GET | `200` | Starea serviciului și timpul de funcționare (`uptime_seconds`) |
| `/version` | GET | `200` | Versiunea aplicației și commit-ul din care a fost construită |
| `/` | GET | `200` | Pagina HTML de prezentare |
| `/reset` | POST | `204` | Golește datele din memorie și resetează ID-urile de la 1 |
| `/contacts` | POST | `201` | Adaugă un contact nou; verifică unicitatea email-ului |
| `/contacts` | GET | `200` | Listează contactele ordonate alfabetic, cu filtrare opțională (`category`) și căutare (`q`) |
| `/contacts/{id}` | GET | `200` | Returnează datele unui contact sau `404` |
| `/contacts/{id}` | DELETE | `204` | Șterge contactul fără corp de răspuns, sau `404` dacă nu există |
| `/stats` | GET | `200` | Numărul total de contacte și numărul pe fiecare categorie |

## Contractul de date și erori

Toate cererile și răspunsurile folosesc `application/json` (UTF-8). Răspunsurile de eroare respectă formatul:

```json
{
  "error": "<cod>",
  "message": "<explicație>"
}
```

- `400 validation`: Date lipsă, tip greșit sau în afara limitelor (ex: telefon diferit de 10 cifre, nume peste 50 de caractere, JSON invalid).
- `404 not_found`: Contactul sau ruta solicitată nu există.
- `409 conflict`: Încercarea de a adăuga un contact cu un email existent (indiferent de majuscule/minuscule).

## Exemple de testare manuală (PowerShell)

```powershell
# Golește datele
curl.exe -i -X POST http://localhost:8080/reset

# Adaugă contact
curl.exe -i -H "Content-Type: application/json" -d '{\"name\":\"Ana Pop\",\"email\":\"ana@example.com\",\"phone\":\"0722334455\",\"category\":\"work\"}' http://localhost:8080/contacts

# Verifică duplicat email (returnează 409)
curl.exe -i -H "Content-Type: application/json" -d '{\"name\":\"Ana P.\",\"email\":\"Ana@Example.COM\",\"phone\":\"0733445566\",\"category\":\"friends\"}' http://localhost:8080/contacts

# Listare cu filtrare și căutare combinate
curl.exe -i "http://localhost:8080/contacts?category=work&q=ana"

# Statistici
curl.exe -i http://localhost:8080/stats

# Ștergere contact
curl.exe -i -X DELETE http://localhost:8080/contacts/1
```

## Decizii de implementare

- **Stocare în memorie:** Datele sunt păstrate într-un dicționar `store.contacts` indexat după `id` întreg, garantând acces și căutare rapidă $O(1)$ la operațiile pe ID.
- **Normalizare email vs afișare:** Emailul se compară normalizat (`.strip().lower()`) pentru verificarea unicității, dar în dicționar se păstrează exact textul scris de utilizator.
- **Validare modulară:** Validarea este izolată în funcția `validate_contact(data)`, permițând testarea unitară directă a tuturor cazurilor de margine fără a depinde de contextul HTTP.
- **Departajare la sortare:** Conform convenției comune din enunț, contactele sunt sortate crescător după `name`, iar în caz de egalitate, departajarea se face crescător după `id` (`key=lambda c: (c["name"], c["id"])`).
- **Inițializarea statisticilor:** În ruta `/stats`, dicționarul `by_category` este pre-inițializat cu `0` pentru toate categoriile valide (`family`, `friends`, `other`, `work`), asigurând un răspuns JSON uniform chiar și atunci când unele categorii nu au contacte asociate.