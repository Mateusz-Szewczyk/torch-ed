# src/routers/decks.py

import os
import logging
import zipfile
import tempfile
import sqlite3
import json
import csv

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..models import Deck, Flashcard, User
from ..schemas import DeckCreate, DeckRead
from ..dependencies import get_db
from ..auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=DeckRead, status_code=201)
async def create_deck(
    deck: DeckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tworzy nowy zestaw (Deck) przypisany do zalogowanego użytkownika.
    """
    logger.info(f"Tworzenie nowego decka: {deck.name} dla user_id={current_user.id_}")

    try:
        # Tworzenie nowego decka przypisanego do użytkownika
        new_deck = Deck(
            user_id=str(current_user.id_),  # Przypisanie user_id
            name=deck.name,
            description=deck.description
        )

        # Dodawanie fiszek do decka
        for fc in deck.flashcards:
            new_flashcard = Flashcard(
                question=fc.question,
                answer=fc.answer,
                media_url=fc.media_url
            )
            new_deck.flashcards.append(new_flashcard)
            logger.debug(f"Dodano fiszkę: {new_flashcard}")

        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)

        logger.info(f"Utworzono nowy deck z ID={new_deck.id} dla user_id={current_user.id_}")
        return new_deck

    except Exception as e:
        db.rollback()
        logger.error(f"Błąd podczas tworzenia decka: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Błąd podczas tworzenia decka: {str(e)}")


@router.get("/", response_model=List[DeckRead])
async def get_decks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera wszystkie decki przypisane do zalogowanego użytkownika.
    """
    logger.info(f"Pobieranie wszystkich decków dla user_id={current_user.id_}")
    try:
        decks = (
            db.query(Deck)
            .options(joinedload(Deck.flashcards))
            .filter(Deck.user_id == str(current_user.id_))
            .all()
        )
        logger.debug(f"Pobrano decki: {decks}")
        return decks
    except Exception as e:
        logger.error(f"Błąd podczas pobierania decków: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd podczas pobierania decków: {str(e)}")


@router.get("/{deck_id}/", response_model=DeckRead)
async def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera konkretny deck po ID, jeśli należy do zalogowanego użytkownika.
    """
    logger.info(f"Pobieranie decka z ID={deck_id} dla user_id={current_user.id_}")
    try:
        deck = (
            db.query(Deck)
            .options(joinedload(Deck.flashcards))
            .filter(Deck.id == deck_id, Deck.user_id == str(current_user.id_))
            .first()
        )
        if not deck:
            logger.error(f"Deck z ID={deck_id} nie znaleziony dla tego użytkownika.")
            raise HTTPException(status_code=404, detail="Deck nie znaleziony.")
        logger.debug(f"Pobrano deck: {deck}")
        return deck
    except Exception as e:
        logger.error(f"Błąd podczas pobierania decka: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd podczas pobierania decka: {str(e)}")


@router.put("/{deck_id}/", response_model=DeckRead)
async def update_deck(
    deck_id: int,
    deck: DeckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aktualizuje deck po ID, jeśli należy do zalogowanego użytkownika.
    """
    logger.info(f"Aktualizacja decka z ID={deck_id} dla user_id={current_user.id_}")
    try:
        existing_deck = (
            db.query(Deck)
            .options(joinedload(Deck.flashcards))
            .filter(Deck.id == deck_id, Deck.user_id == str(current_user.id_))
            .first()
        )
        if not existing_deck:
            logger.error(f"Deck z ID={deck_id} nie znaleziony lub nie należy do użytkownika.")
            raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

        logger.debug(f"Przed aktualizacją decka: {existing_deck}")

        # Aktualizacja pól decka
        existing_deck.name = deck.name
        existing_deck.description = deck.description

        # Zbieranie istniejących ID fiszek
        existing_flashcard_ids = set(fc.id for fc in existing_deck.flashcards if fc.id)
        logger.debug(f"Istniejące ID fiszek: {existing_flashcard_ids}")

        # Zbieranie ID edytowanych fiszek
        edited_flashcards_ids = set(fc.id for fc in deck.flashcards if fc.id is not None)
        logger.debug(f"ID edytowanych fiszek: {edited_flashcards_ids}")

        # Aktualizacja istniejących lub dodawanie nowych fiszek
        for fc in deck.flashcards:
            if fc.id:
                if fc.id in existing_flashcard_ids:
                    existing_fc = next(
                        (flash for flash in existing_deck.flashcards if flash.id == fc.id),
                        None
                    )
                    if existing_fc:
                        existing_fc.question = fc.question
                        existing_fc.answer = fc.answer
                        existing_fc.media_url = fc.media_url
                        logger.debug(f"Aktualizowana fiszka ID={fc.id}: {existing_fc}")
                else:
                    logger.warning(f"Fiszka ID={fc.id} nie znaleziono w tym decku. Pomijanie.")
            else:
                # Dodawanie nowej fiszki
                new_flashcard = Flashcard(
                    question=fc.question,
                    answer=fc.answer,
                    media_url=fc.media_url
                )
                db.add(new_flashcard)
                existing_deck.flashcards.append(new_flashcard)
                logger.debug(f"Dodano nową fiszkę: {new_flashcard}")

        # Usuwanie fiszek, które nie są w przesłanych danych
        flashcards_to_remove = existing_flashcard_ids - edited_flashcards_ids
        logger.debug(f"Fiszki do usunięcia: {flashcards_to_remove}")

        for fc_id in flashcards_to_remove:
            logger.debug(f"Usuwanie fiszki ID={fc_id}")
            fc_to_delete = db.query(Flashcard).filter(Flashcard.id == fc_id).first()
            if fc_to_delete:
                db.delete(fc_to_delete)

        db.commit()
        db.refresh(existing_deck)
        logger.info(f"Zaktualizowano deck z ID={deck_id}")
        return existing_deck

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Błąd podczas aktualizacji decka: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Błąd podczas aktualizacji decka: {str(e)}")


@router.delete("/{deck_id}/", response_model=DeckRead)
async def delete_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Usuwa deck po ID, jeśli należy do zalogowanego użytkownika.
    """
    logger.info(f"Usuwanie decka z ID={deck_id} dla user_id={current_user.id_}")
    try:
        deck = (
            db.query(Deck)
            .filter(Deck.id == deck_id, Deck.user_id == str(current_user.id_))
            .first()
        )
        if not deck:
            logger.error(f"Deck z ID={deck_id} nie znaleziony lub nie należy do użytkownika.")
            raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

        db.delete(deck)
        db.commit()
        logger.info(f"Usunięto deck z ID={deck_id}")
        return deck
    except Exception as e:
        db.rollback()
        logger.error(f"Błąd podczas usuwania decka: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd podczas usuwania decka: {str(e)}")


@router.post("/import/", response_model=dict, status_code=201)
async def import_flashcards(
    file: UploadFile = File(...),
    deck_name: Optional[str] = None,
    deck_description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Importuje fiszki z pliku CSV, TXT lub APKG do nowego decka przypisanego do zalogowanego użytkownika.
    """
    logger.info(f"Importowanie fiszek z pliku: {file.filename} dla user_id={current_user.id_}")
    allowed_extensions = ['.csv', '.apkg', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        logger.error(f"Nieobsługiwany format pliku: {file_ext}")
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku. Proszę przesłać plik CSV, APKG lub TXT.")

    try:
        # Zapisz plik tymczasowo
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp_path = tmp.name
            contents = await file.read()
            tmp.write(contents)
            logger.debug(f"Zapisano plik do tymczasowej lokalizacji: {tmp_path}")

        flashcards = []
        media_files = {}

        if file_ext == '.csv':
            # Parsowanie CSV
            logger.info("Parsowanie pliku CSV.")
            with open(tmp_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    question = row.get('Term') or row.get('Front')
                    answer = row.get('Definition') or row.get('Back')
                    if question and answer:
                        flashcards.append({'question': question, 'answer': answer, 'media_url': row.get('MediaURL')})
            logger.info(f"Zparsowano {len(flashcards)} fiszek z CSV.")

        elif file_ext == '.txt':
            # Parsowanie TXT (Anki)
            logger.info("Parsowanie pliku TXT.")
            with open(tmp_path, 'r', encoding='utf-8') as txtfile:
                separator = "\t"  # Domyślny separator
                for line in txtfile:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        if line.lower().startswith('#separator:'):
                            sep_value = line.split(':', 1)[1].strip()
                            if sep_value.lower() == 'tab':
                                separator = "\t"
                            elif sep_value.lower() == 'comma':
                                separator = ","
                            # Dodaj inne separatory jeśli potrzebne
                        continue

                    parts = line.split(separator)
                    if len(parts) >= 2:
                        question = parts[0].strip()
                        answer = parts[1].strip()
                        media_url = parts[2].strip() if len(parts) >=3 else None
                        if question and answer:
                            flashcards.append({'question': question, 'answer': answer, 'media_url': media_url})
            logger.info(f"Zparsowano {len(flashcards)} fiszek z TXT.")

        elif file_ext == '.apkg':
            # Parsowanie APKG
            logger.info("Parsowanie pliku APKG.")
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                extract_dir = tempfile.mkdtemp()
                zip_ref.extractall(extract_dir)
                logger.debug(f"Rozpakowano APKG do: {extract_dir}")

            collection_path = os.path.join(extract_dir, 'collection.anki2')
            if not os.path.exists(collection_path):
                logger.error("collection.anki2 nie znaleziony w pliku APKG.")
                raise HTTPException(status_code=400, detail="Nieprawidłowy plik APKG: collection.anki2 nie znaleziony.")

            # Obsługa mediów
            media_path = os.path.join(extract_dir, 'media.json')
            if os.path.exists(media_path):
                with open(media_path, 'r', encoding='utf-8') as media_file:
                    media_files = json.load(media_file)
                logger.debug(f"Załadowano mapowanie mediów: {media_files}")
            else:
                logger.warning("media.json nie znaleziony w pliku APKG. Próba wyodrębnienia mediów z collection.anki2.")

            # Otwórz bazę danych SQLite
            conn = sqlite3.connect(collection_path)
            cursor = conn.cursor()

            try:
                # Pobranie modeli
                cursor.execute("SELECT models FROM col")
                models_json = cursor.fetchone()[0]
                models = json.loads(models_json)
                logger.debug(f"Załadowano modele: {models}")

                # Pobranie decków
                cursor.execute("SELECT decks FROM col")
                decks_json = cursor.fetchone()[0]
                decks_dict = json.loads(decks_json)
                logger.debug(f"Załadowano decki: {decks_dict}")

                # Pobranie notatek
                cursor.execute("SELECT id, mid, flds FROM notes")
                notes = cursor.fetchall()
                logger.debug(f"Pobrano {len(notes)} notatek z tabeli 'notes'.")

                # Pobranie kart
                cursor.execute("SELECT id, nid, did, ord FROM cards")
                cards = cursor.fetchall()
                logger.debug(f"Pobrano {len(cards)} kart z tabeli 'cards'.")

                # Sprawdzenie obecności tabeli 'media'
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
                media_table_exists = cursor.fetchone() is not None

                if not media_files and media_table_exists:
                    # Pobranie mediów z tabeli 'media'
                    cursor.execute("SELECT key, data FROM media")
                    media_records = cursor.fetchall()
                    media_files = {str(key): data for key, data in media_records}
                    logger.debug(f"Załadowano {len(media_files)} rekordów mediów z tabeli 'media'.")

                    # Zapisz media na serwerze i utwórz mapowanie klucz -> URL
                    media_storage_dir = os.path.join('public', 'media')
                    os.makedirs(media_storage_dir, exist_ok=True)
                    media_url_map = {}
                    for key, data in media_files.items():
                        original_name = f"media_{key}"
                        file_path = os.path.join(media_storage_dir, original_name)
                        with open(file_path, 'wb') as f:
                            f.write(data)
                        media_url = f"/media/{original_name}"
                        media_url_map[key] = media_url
                        logger.debug(f"Zapisano media {original_name} do {file_path} z URL {media_url}")
                elif media_files:
                    # Jeśli media.json jest dostępne, załaduj media_url_map z istniejących danych
                    media_storage_dir = os.path.join('public', 'media')
                    os.makedirs(media_storage_dir, exist_ok=True)
                    media_url_map = {}
                    for key, original_name in media_files.items():
                        media_file_path = os.path.join(extract_dir, key)
                        if os.path.exists(media_file_path):
                            destination_path = os.path.join(media_storage_dir, original_name)
                            os.rename(media_file_path, destination_path)
                            media_url = f"/media/{original_name}"
                            media_url_map[key] = media_url
                            logger.debug(f"Zapisano media {original_name} do {destination_path} z URL {media_url}")
                        else:
                            logger.warning(f"Plik mediów {key} nie znaleziony w archiwum.")
                else:
                    # Brak mediów do importu
                    media_url_map = {}
                    logger.info("Brak mediów do importu.")

                # Tworzenie mapy notatek
                notes_map = {}
                for note in notes:
                    note_id, mid, flds = note
                    fields = flds.split('\x1f')
                    notes_map[note_id] = {
                        'mid': mid,
                        'fields': fields
                    }

                # Tworzenie mapy decków
                decks_map = {}
                for deck_id, deck_info in decks_dict.items():
                    decks_map[int(deck_id)] = deck_info

                # Iteracja przez karty i tworzenie fiszek
                for card in cards:
                    card_id, nid, did, ord_ = card
                    note = notes_map.get(nid)
                    if not note:
                        logger.warning(f"Notatka ID={nid} nie znaleziona dla karty ID={card_id}. Pomijanie.")
                        continue

                    model_id = note['mid']
                    model = models.get(str(model_id))
                    if not model:
                        logger.warning(f"Model ID={model_id} nie znaleziony dla notatki ID={nid}. Pomijanie.")
                        continue

                    flds = note['fields']
                    fields_def = model.get('flds', [])
                    if len(flds) < len(fields_def):
                        logger.warning(
                            f"Notatka ID={nid} ma niewystarczającą liczbę pól. Oczekiwano {len(fields_def)}, otrzymano {len(flds)}. Pomijanie."
                        )
                        continue

                    tmpls = model.get('tmpls', [])
                    if ord_ >= len(tmpls):
                        logger.warning(f"Karta ord={ord_} poza zakresem dla modelu ID={model_id}. Pomijanie.")
                        continue
                    tmpl = tmpls[ord_]

                    # Zastępowanie {{placeholders}} w qfmt i afmt
                    qfmt = tmpl.get('qfmt', '')
                    afmt = tmpl.get('afmt', '')

                    for idx, field in enumerate(fields_def):
                        field_name = field.get('name')
                        if idx >= len(flds):
                            logger.warning(f"Indeks pola {idx} poza zakresem dla notatki ID={nid}. Pomijanie pola {field_name}.")
                            continue
                        field_value = flds[idx]
                        placeholder = f"{{{{{field_name}}}}}"
                        qfmt = qfmt.replace(placeholder, field_value)
                        afmt = afmt.replace(placeholder, field_value)

                    # Obsługa {{FrontSide}} w afmt
                    if "{{FrontSide}}" in afmt:
                        afmt = afmt.replace("{{FrontSide}}", qfmt)

                    # Obsługa mediów w polach
                    for key, media_url in media_url_map.items():
                        qfmt = qfmt.replace(key, media_url)
                        afmt = afmt.replace(key, media_url)

                    question = qfmt.strip()
                    answer = afmt.strip()

                    flashcards.append({
                        'question': question,
                        'answer': answer,
                        'media_url': None  # Możesz zaktualizować to pole, jeśli chcesz powiązać media z fiszką
                    })

                logger.info(f"Zparsowano {len(flashcards)} fiszek z APKG.")

            except Exception as e:
                logger.error(f"Błąd podczas parsowania collection.anki2: {e}")
                raise HTTPException(status_code=400, detail="Błąd podczas parsowania pliku APKG.")
            finally:
                conn.close()
                logger.debug("Zamknięto połączenie z SQLite.")
                # Usunięcie plików tymczasowych
                try:
                    os.remove(collection_path)
                    logger.debug(f"Usunięto plik tymczasowy: {collection_path}")
                    if os.path.exists(media_path):
                        os.remove(media_path)
                        logger.debug(f"Usunięto plik tymczasowy: {media_path}")
                except Exception as e:
                    logger.warning(f"Błąd podczas usuwania plików tymczasowych: {e}")

                # Opcjonalnie, usuń cały katalog tymczasowy
                try:
                    os.rmdir(extract_dir)
                    logger.debug(f"Usunięto katalog tymczasowy: {extract_dir}")
                except OSError as e:
                    logger.warning(f"Katalog tymczasowy nie jest pusty lub błąd podczas usuwania: {e}")

        # Usunięcie tymczasowego pliku
        os.remove(tmp_path)
        logger.debug(f"Usunięto plik tymczasowy: {tmp_path}")

        if not flashcards:
            logger.error("Nie znaleziono żadnych fiszek w przesłanym pliku.")
            raise HTTPException(status_code=400, detail="Nie znaleziono żadnych fiszek w przesłanym pliku.")

        try:
            # Tworzenie nowego decka przypisanego do użytkownika
            new_deck = Deck(
                user_id=str(current_user.id_),
                name=deck_name if deck_name else "Imported Deck",
                description=deck_description
            )
            db.add(new_deck)
            db.commit()
            db.refresh(new_deck)
            logger.info(f"Utworzono nowy deck z ID={new_deck.id} dla user_id={current_user.id_}")

            # Dodawanie fiszek do decka
            for fc in flashcards:
                new_flashcard = Flashcard(
                    question=fc['question'],
                    answer=fc['answer'],
                    deck_id=new_deck.id,
                    media_url=fc.get('media_url')
                )
                db.add(new_flashcard)
                logger.debug(f"Dodano fiszkę: {new_flashcard}")

            db.commit()
            logger.info(f"Zaimportowano {len(flashcards)} fiszek do decka z ID={new_deck.id}")

            return {"detail": "Fiszki zaimportowane pomyślnie.", "deck_id": new_deck.id}

        except Exception as e:
            db.rollback()
            logger.error(f"Błąd podczas importowania fiszek: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Błąd podczas importowania fiszek: {str(e)}")

    except HTTPException:
        raise