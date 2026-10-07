# Agenda de contacte

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

| Ruta | Metoda | Descriere |
|---|---|---|
| `/health` | GET | Starea serviciului |
| `/version` | GET | Versiunea si commit-ul din care a fost construita imaginea |
| `/` | GET | Pagina de prezentare |
| `/reset` | POST | Goleste datele din memorie |
| `/contacts` | POST | Adauga un contact |
| `/contacts` | GET | Listeaza contactele, cu filtrare dupa categorie si cautare dupa nume |
| `/contacts/{id}` | GET | Intoarce un contact sau 404 |
| `/contacts/{id}` | DELETE | Sterge un contact |
| `/stats` | GET | Numarul total de contacte si numarul pe categorii |

## Decizii de implementare

- Datele sunt păstrate în memorie, într-un dicționar, pentru că enunțul nu cere persistență, iar soluția rămâne simplă și ușor de testat.
- Emailul se compară normalizat (litere mici), dar se păstrează forma scrisă de utilizator, pentru ca unicitatea să nu depindă de majuscule.
- Validarea se face într-o funcție separată de rute, ca să poată fi testată direct.