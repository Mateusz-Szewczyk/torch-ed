# src/routers/decks.py

from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..models import Deck, Flashcard
from ..schemas import DeckCreate, DeckRead
from ..dependencies import get_db
import logging
import zipfile
import tempfile
import sqlite3
import json
import csv
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=DeckRead, status_code=201)
async def create_deck(deck: DeckCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating a new deck with name: {deck.name}")
    logger.debug(f"Deck data: {deck.flashcards}")

    try:
        new_deck = Deck(
            name=deck.name,
            description=deck.description
        )

        # Dodawanie fiszek do decka
        for fc in deck.flashcards:
            new_flashcard = Flashcard(
                question=fc.question,
                answer=fc.answer,
                media_url=fc.media_url  # Nowe pole
            )
            new_deck.flashcards.append(new_flashcard)
            logger.debug(f"Added flashcard: {new_flashcard}")

        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)

        logger.info(f"Created new deck with ID {new_deck.id}")
        logger.debug(f"Deck flashcards: {new_deck.flashcards}")
        return new_deck

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deck: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating deck: {str(e)}")


@router.get("/", response_model=List[DeckRead])
async def get_decks(db: Session = Depends(get_db)):
    """
    Get All Decks
    ------------
    Retrieves a list of all decks along with their flashcards.
    """
    logger.info("Fetching all decks.")
    try:
        decks = db.query(Deck).options(joinedload(Deck.flashcards)).all()
        logger.debug(f"Fetched decks: {decks}")
        return decks
    except Exception as e:
        logger.error(f"Error fetching decks: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching decks: {str(e)}")


@router.get("/{deck_id}/", response_model=DeckRead)
async def get_deck(deck_id: int, db: Session = Depends(get_db)):
    """
    Get a Deck by ID
    ----------------
    Retrieves a specific deck by its ID along with its flashcards.
    """
    logger.info(f"Fetching deck with ID: {deck_id}")
    try:
        deck = db.query(Deck).options(joinedload(Deck.flashcards)).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")
        logger.debug(f"Fetched deck: {deck}")
        return deck
    except Exception as e:
        logger.error(f"Error fetching deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching deck: {str(e)}")


@router.put("/{deck_id}/", response_model=DeckRead)
async def update_deck(deck_id: int, deck: DeckCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating deck with ID: {deck_id}")
    try:
        # Pobierz istniejący deck z fiszkami
        existing_deck = db.query(Deck).options(joinedload(Deck.flashcards)).filter(Deck.id == deck_id).first()
        if not existing_deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        logger.debug(f"Existing deck name: {existing_deck.name}, description: {existing_deck.description}")
        logger.debug(f"Existing flashcards: {existing_deck.flashcards}")

        # Aktualizacja danych decka
        existing_deck.name = deck.name
        existing_deck.description = deck.description

        # Przygotowanie listy ID istniejących fiszek
        existing_flashcard_ids = set(fc.id for fc in existing_deck.flashcards if fc.id)
        logger.debug(f"Existing flashcard IDs: {existing_flashcard_ids}")

        # Przygotowanie listy ID edytowanych fiszek
        edited_flashcards_ids = set(fc.id for fc in deck.flashcards if fc.id is not None)
        logger.debug(f"Edited flashcard IDs: {edited_flashcards_ids}")

        # Aktualizacja istniejących fiszek
        for fc in deck.flashcards:
            if fc.id:
                if fc.id in existing_flashcard_ids:
                    # Znalezienie istniejącej fiszki i jej aktualizacja
                    existing_fc = next((flash for flash in existing_deck.flashcards if flash.id == fc.id), None)
                    if existing_fc:
                        existing_fc.question = fc.question
                        existing_fc.answer = fc.answer
                        existing_fc.media_url = fc.media_url  # Aktualizacja media_url
                        logger.debug(f"Updated flashcard ID {fc.id}: {existing_fc}")
                else:
                    logger.warning(f"Flashcard ID {fc.id} not found in existing deck. Skipping update.")
            else:
                # Dodawanie nowych fiszek
                new_flashcard = Flashcard(
                    question=fc.question,
                    answer=fc.answer,
                    media_url=fc.media_url  # Nowe pole
                )
                db.add(new_flashcard)
                existing_deck.flashcards.append(new_flashcard)
                logger.debug(f"Added new flashcard: {new_flashcard}")

        # Usunięcie fiszek, które nie są w przesłanych danych
        flashcards_to_remove = existing_flashcard_ids - edited_flashcards_ids
        logger.debug(f"Flashcards to remove: {flashcards_to_remove}")

        for fc_id in flashcards_to_remove:
            logger.debug(f"Deleting flashcard ID {fc_id}")
            fc_to_delete = db.query(Flashcard).filter(Flashcard.id == fc_id).first()
            if fc_to_delete:
                db.delete(fc_to_delete)

        db.commit()  # Commit zmian
        db.refresh(existing_deck)  # Odśwież istniejący deck
        logger.info(f"Updated deck with ID {deck_id}")

        return existing_deck  # Zwrócenie zaktualizowanego decka

    except HTTPException:
        raise  # Re-raise HTTPException to be handled by FastAPI

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating deck: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating deck: {str(e)}")


@router.delete("/{deck_id}/", response_model=DeckRead)
async def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    """
    Delete a Deck
    ------------
    Deletes a deck and all its associated flashcards.
    """
    logger.info(f"Deleting deck with ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        db.delete(deck)
        db.commit()
        logger.info(f"Deleted deck with ID {deck_id}")
        return deck
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting deck: {str(e)}")


@router.post("/import/", response_model=dict, status_code=201)
async def import_flashcards(
    file: UploadFile = File(...),
    deck_name: Optional[str] = None,
    deck_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Import Flashcards
    -----------------
    Imports flashcards from a CSV, APKG or TXT file.
    """
    logger.info(f"Importing flashcards from file: {file.filename}")
    allowed_extensions = ['.csv', '.apkg', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        logger.error(f"Unsupported file format: {file_ext}")
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a CSV, APKG or TXT file.")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp_path = tmp.name
            contents = await file.read()
            tmp.write(contents)
            logger.debug(f"Saved uploaded file to temporary path: {tmp_path}")

        flashcards = []
        media_files = {}

        if file_ext == '.csv':
            # Parsowanie CSV
            logger.info("Parsing CSV file.")
            with open(tmp_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    question = row.get('Term') or row.get('Front')
                    answer = row.get('Definition') or row.get('Back')
                    if question and answer:
                        flashcards.append({'question': question, 'answer': answer})
            logger.info(f"Parsed {len(flashcards)} flashcards from CSV.")

        elif file_ext == '.txt':
            # Parsowanie plików TXT (Anki)
            logger.info("Parsing TXT file.")
            with open(tmp_path, 'r', encoding='utf-8') as txtfile:
                # Zmienne pomocnicze
                separator = "\t"  # Default
                for line in txtfile:
                    line = line.strip()
                    # Pomijamy komentarze i puste wiersze
                    if not line or line.startswith('#'):
                        # Możemy też wyłuskać tu separator, np. #separator:tab
                        if line.lower().startswith('#separator:'):
                            # Przykład: #separator:tab
                            sep_value = line.split(':', 1)[1].strip()
                            # Jeśli mamy #separator:tab, to separator = "\t"
                            if sep_value.lower() == 'tab':
                                separator = "\t"
                            # W razie potrzeby możesz dodać inne separatory
                        continue

                    # Rozbijamy wiersz po aktualnym separatorze
                    parts = line.split(separator)
                    # Oczekujemy, że co najmniej 2 kolumny (question, answer)
                    if len(parts) >= 2:
                        question = parts[0].strip()
                        answer = parts[1].strip()
                        if question and answer:
                            flashcards.append({'question': question, 'answer': answer})
            logger.info(f"Parsed {len(flashcards)} flashcards from TXT.")

        elif file_ext == '.apkg':
            # Parsowanie APKG
            logger.info("Parsing APKG file.")
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                # Rozpakowanie wszystkich plików do tymczasowego katalogu
                extract_dir = tempfile.mkdtemp()
                zip_ref.extractall(extract_dir)
                logger.debug(f"Extracted APKG to temporary directory: {extract_dir}")

            collection_path = os.path.join(extract_dir, 'collection.anki2')
            if not os.path.exists(collection_path):
                logger.error("collection.anki2 not found in the APKG file.")
                raise HTTPException(status_code=400, detail="Invalid APKG file: collection.anki2 not found.")

            # Sprawdzenie obecności media.json
            media_path = os.path.join(extract_dir, 'media.json')
            if os.path.exists(media_path):
                with open(media_path, 'r', encoding='utf-8') as media_file:
                    media_files = json.load(media_file)
                logger.debug(f"Loaded media mappings: {media_files}")
            else:
                logger.warning("media.json not found in the APKG file. Attempting to extract media from collection.anki2.")

            # Otwórz bazę danych SQLite
            conn = sqlite3.connect(collection_path)
            cursor = conn.cursor()

            try:
                # Pobranie modeli z tabeli 'col'
                cursor.execute("SELECT models FROM col")
                models_json = cursor.fetchone()[0]
                models = json.loads(models_json)
                logger.debug(f"Loaded models: {models}")

                # Pobranie decków z tabeli 'col'
                cursor.execute("SELECT decks FROM col")
                decks_json = cursor.fetchone()[0]
                decks_dict = json.loads(decks_json)
                logger.debug(f"Loaded decks: {decks_dict}")

                # Pobranie notatek
                cursor.execute("SELECT id, mid, flds FROM notes")
                notes = cursor.fetchall()
                logger.debug(f"Fetched {len(notes)} notes from 'notes' table.")

                # Pobranie kart
                cursor.execute("SELECT id, nid, did, ord FROM cards")
                cards = cursor.fetchall()
                logger.debug(f"Fetched {len(cards)} cards from 'cards' table.")

                # Sprawdzenie, czy tabela 'media' istnieje
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
                media_table_exists = cursor.fetchone() is not None

                if not media_files and media_table_exists:
                    # Pobranie mediów z tabeli 'media'
                    cursor.execute("SELECT key, data FROM media")
                    media_records = cursor.fetchall()
                    media_files = {str(key): data for key, data in media_records}
                    logger.debug(f"Loaded {len(media_files)} media records from 'media' table.")

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
                        logger.debug(f"Saved media {original_name} to {file_path} with URL {media_url}")
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
                            logger.debug(f"Saved media {original_name} to {destination_path} with URL {media_url}")
                        else:
                            logger.warning(f"Media file {key} not found in the archive.")
                else:
                    # Brak mediów do importu
                    media_url_map = {}
                    logger.info("No media to import.")

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
                        logger.warning(f"Note ID {nid} not found for card ID {card_id}. Skipping.")
                        continue

                    model_id = note['mid']
                    model = models.get(str(model_id))
                    if not model:
                        logger.warning(f"Model ID {model_id} not found for note ID {nid}. Skipping.")
                        continue

                    flds = note['fields']
                    fields_def = model.get('flds', [])
                    if len(flds) < len(fields_def):
                        logger.warning(
                            f"Note ID {nid} has insufficient fields. Expected {len(fields_def)}, got {len(flds)}. Skipping."
                        )
                        continue

                    tmpls = model.get('tmpls', [])
                    if ord_ >= len(tmpls):
                        logger.warning(f"Card ord {ord_} out of range for model ID {model_id}. Skipping.")
                        continue
                    tmpl = tmpls[ord_]

                    # Zastępowanie {{placeholders}} w qfmt i afmt
                    qfmt = tmpl.get('qfmt', '')
                    afmt = tmpl.get('afmt', '')

                    for idx, field in enumerate(fields_def):
                        field_name = field.get('name')
                        if idx >= len(flds):
                            logger.warning(f"Field index {idx} out of range for note ID {nid}. Skipping field {field_name}.")
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

                logger.info(f"Parsed {len(flashcards)} flashcards from APKG.")
            except Exception as e:
                logger.error(f"Error parsing collection.anki2: {e}")
                raise HTTPException(status_code=400, detail="Error parsing APKG file.")
            finally:
                conn.close()
                logger.debug("Closed SQLite connection.")
                # Usunięcie plików tymczasowych
                try:
                    os.remove(collection_path)
                    logger.debug(f"Removed temporary collection.anki2 file: {collection_path}")
                    if os.path.exists(media_path):
                        os.remove(media_path)
                        logger.debug(f"Removed temporary media.json file: {media_path}")
                except Exception as e:
                    logger.warning(f"Error removing temporary files: {e}")

                # Opcjonalnie, usuń cały katalog tymczasowy
                try:
                    os.rmdir(extract_dir)
                    logger.debug(f"Removed temporary directory: {extract_dir}")
                except OSError as e:
                    logger.warning(f"Temporary directory not empty or error removing: {e}")

        # Usunięcie tymczasowego pliku
        os.remove(tmp_path)
        logger.debug(f"Removed temporary file: {tmp_path}")

        if not flashcards:
            logger.error("No flashcards found in the uploaded file.")
            raise HTTPException(status_code=400, detail="No flashcards found in the uploaded file.")

        # Tworzenie nowego zestawu
        new_deck = Deck(
            name=deck_name if deck_name else "Imported Deck",
            description=deck_description
        )
        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)
        logger.info(f"Created new deck with ID {new_deck.id}")

        # Dodawanie fiszek do decka
        for fc in flashcards:
            new_flashcard = Flashcard(
                question=fc['question'],
                answer=fc['answer'],
                deck_id=new_deck.id,
                media_url=fc.get('media_url')  # Jeśli chcesz powiązać media z fiszką
            )
            db.add(new_flashcard)
            logger.debug(f"Added flashcard: {new_flashcard}")

        db.commit()
        logger.info(f"Imported {len(flashcards)} flashcards into deck ID {new_deck.id}")

        return {"detail": "Flashcards imported successfully.", "deck_id": new_deck.id}
    except Exception as e:
        logger.error(f"Error importing flashcards: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error importing flashcards: {str(e)}")
