import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from ..models import User, Deck, Flashcard, ShareableContent, UserDeckAccess
from ..dependencies import get_db
from ..auth import get_current_user
from ..utils import (
    create_shareable_deck, add_deck_by_code, get_user_shared_decks,
    get_shareable_content_info, generate_share_code
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ===========================================
# STATYCZNE ENDPOINTY (bez parametrów path)
# ===========================================

@router.get("/", response_model=List[dict])
def get_decks(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        include_shared: bool = Query(default=False, description="Include shared decks")
):
    """Pobiera wszystkie deck'i użytkownika"""
    try:
        # Pobierz deck'i własne użytkownika
        own_decks = db.query(Deck).filter(
            Deck.user_id == current_user.id_,
            Deck.template_id.is_(None)  # Exclude copies from shared decks
        ).options(joinedload(Deck.flashcards)).all()

        result = []

        # Dodaj własne deck'i
        for deck in own_decks:
            flashcard_count = len(deck.flashcards) if deck.flashcards else 0
            result.append({
                'id': deck.id,
                'name': deck.name,
                'description': deck.description,
                'created_at': deck.created_at.isoformat() if deck.created_at else None,
                'flashcard_count': flashcard_count,
                'is_shared': deck.is_template,
                'is_own': True,
                'original_deck_id': None
            })

        # Jeśli requested, dodaj udostępnione deck'i
        if include_shared:
            shared_decks_data = get_user_shared_decks(current_user.id_, db)
            for shared_deck in shared_decks_data:
                deck = db.query(Deck).filter(Deck.id == shared_deck['user_deck_id']).first()
                if deck:
                    flashcard_count = db.query(Flashcard).filter(Flashcard.deck_id == deck.id).count()
                    result.append({
                        'id': deck.id,
                        'name': deck.name,
                        'description': deck.description,
                        'created_at': deck.created_at.isoformat() if deck.created_at else None,
                        'flashcard_count': flashcard_count,
                        'is_shared': False,
                        'is_own': False,
                        'original_deck_id': shared_deck['original_deck_id'],
                        'added_at': shared_deck['added_at'],
                        'code_used': shared_deck['code_used']
                    })

        return result

    except Exception as e:
        logger.error(f"Error fetching decks for user {current_user.id_}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch decks")


@router.post("/")
def create_deck(
        deck_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Tworzy nowy deck wraz z flashcardami"""
    try:
        deck = Deck(
            name=deck_data.get('name'),
            description=deck_data.get('description', ''),
            user_id=current_user.id_,
            is_template=False
        )

        db.add(deck)
        db.commit()
        db.refresh(deck)

        # Create flashcards if provided
        flashcards_data = deck_data.get('flashcards', [])
        created_flashcards = []
        if flashcards_data:
            for fc_data in flashcards_data:
                flashcard = Flashcard(
                    question=fc_data.get('question', ''),
                    answer=fc_data.get('answer', ''),
                    deck_id=deck.id,
                    media_url=fc_data.get('media_url')
                )
                db.add(flashcard)
                created_flashcards.append(flashcard)

            db.commit()
            for fc in created_flashcards:
                db.refresh(fc)

        logger.info(f"Deck created successfully: {deck.id} by user {current_user.id_} with {len(created_flashcards)} flashcards")

        return {
            'id': deck.id,
            'name': deck.name,
            'description': deck.description,
            'created_at': deck.created_at.isoformat(),
            'flashcard_count': len(created_flashcards),
            'message': 'Deck created successfully'
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deck: {e}")
        raise HTTPException(status_code=500, detail="Failed to create deck")


@router.get("/shared")
def get_user_shared_decks_endpoint(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Pobiera listę udostępnionych deck'ów użytkownika"""
    try:
        shared_decks = get_user_shared_decks(current_user.id_, db)
        return shared_decks

    except Exception as e:
        logger.error(f"Error getting user shared decks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shared decks")


@router.get("/my-shared-codes")
def get_my_shared_codes(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Pobiera listę kodów udostępniania utworzonych przez użytkownika"""
    try:
        # Pobierz wszystkie kody utworzone przez użytkownika dla deck'ów
        shared_contents = db.query(ShareableContent).filter(
            ShareableContent.creator_id == current_user.id_,
            ShareableContent.content_type == 'deck',
            ShareableContent.is_public == True
        ).all()

        result = []
        for content in shared_contents:
            original_deck = db.query(Deck).filter(Deck.id == content.content_id).first()
            if original_deck:
                flashcard_count = db.query(Flashcard).filter(Flashcard.deck_id == original_deck.id).count()
                result.append({
                    'share_code': content.share_code,
                    'content_id': content.content_id,
                    'deck_name': original_deck.name,
                    'flashcard_count': flashcard_count,
                    'created_at': content.created_at.isoformat(),
                    'access_count': content.access_count
                })

        return result

    except Exception as e:
        logger.error(f"Error getting my shared codes: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shared codes")


@router.get("/share-statistics")
def get_deck_share_statistics(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Pobiera statystyki udostępniania deck'ów dla użytkownika"""
    try:
        # Statystyki utworzonych kodów dla deck'ów
        created_codes = db.query(ShareableContent).filter(
            ShareableContent.creator_id == current_user.id_,
            ShareableContent.content_type == 'deck'
        ).count()

        # Statystyki pobranych deck'ów
        added_decks = db.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == current_user.id_,
            UserDeckAccess.is_active == True
        ).count()

        # Łączna liczba dostępów do Twoich kodów deck'ów - POPRAWKA
        total_access_count = db.query(ShareableContent).filter(
            ShareableContent.creator_id == current_user.id_,
            ShareableContent.content_type == 'deck'
        ).with_entities(
            func.sum(ShareableContent.access_count)  # Użyj func.sum zamiast db.func.sum
        ).scalar() or 0

        statistics = {
            'created_share_codes': created_codes,
            'added_shared_decks': added_decks,
            'total_deck_accesses': total_access_count
        }

        return statistics

    except Exception as e:
        logger.error(f"Error getting deck share statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@router.post("/add-by-code")
def add_deck_by_share_code(
        share_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Dodaje deck do biblioteki użytkownika na podstawie kodu"""
    try:
        if not share_data.get('code'):
            raise HTTPException(status_code=400, detail="Share code is required")

        share_code = share_data.get('code').strip().upper()

        # Walidacja formatu kodu
        if len(share_code) != 12:
            raise HTTPException(status_code=400, detail="Invalid share code format")

        # Dodaj deck przez kod
        result = add_deck_by_code(current_user.id_, share_code, db)

        if result['success']:
            logger.info(f"Deck added successfully for user {current_user.id_} with code {share_code}")
            return {
                'success': True,
                'message': result['message'],
                'deck_id': result.get('deck_id'),
                'deck_name': result.get('deck_name')
            }
        else:
            raise HTTPException(status_code=400, detail=result['message'])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding deck by code: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add deck")

# ===========================================
# ENDPOINTY Z PREFIKSAMI (share-info, shared, shared-code)
# ===========================================

@router.get("/share-info/{share_code}")
def get_deck_share_info(
        share_code: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Pobiera informacje o udostępnianym deck'u przed dodaniem"""
    try:
        original_code = share_code
        share_code = share_code.strip().upper()

        logger.info(f"Looking for share code: '{original_code}' -> '{share_code}'")

        # Sprawdź czy kod istnieje w bazie danych
        shareable_content = db.query(ShareableContent).filter(
            ShareableContent.share_code == share_code,
            ShareableContent.content_type == 'deck'
        ).first()

        if not shareable_content:
            logger.warning(f"Share code '{share_code}' not found in database")
            # Sprawdź czy kod istnieje ale z innym content_type
            any_content = db.query(ShareableContent).filter(
                ShareableContent.share_code == share_code
            ).first()
            if any_content:
                logger.warning(f"Code exists but with content_type: '{any_content.content_type}'")
            raise HTTPException(status_code=404, detail="Invalid or expired share code")

        logger.info(f"Found shareable content: ID={shareable_content.id}, is_public={shareable_content.is_public}")

        if not shareable_content.is_public:
            logger.warning(f"Share code '{share_code}' is not public (deactivated)")
            raise HTTPException(status_code=404, detail="Invalid or expired share code")

        # Pobierz informacje o deck'u
        deck = db.query(Deck).filter(Deck.id == shareable_content.content_id).first()
        if not deck:
            logger.error(f"Deck with ID {shareable_content.content_id} not found")
            raise HTTPException(status_code=404, detail="Deck not found")

        # Policz flashcards
        flashcard_count = db.query(Flashcard).filter(Flashcard.deck_id == deck.id).count()

        # Sprawdź czy użytkownik już ma ten deck
        existing_access = db.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == current_user.id_,
            UserDeckAccess.original_deck_id == deck.id,
            UserDeckAccess.is_active == True
        ).first()

        # Sprawdź czy to własny deck użytkownika
        is_own_deck = deck.user_id == current_user.id_

        info = {
            'share_code': share_code,
            'content_id': deck.id,
            'deck_name': deck.name,
            'deck_description': deck.description,
            'flashcard_count': flashcard_count,
            'creator_id': shareable_content.creator_id,
            'created_at': shareable_content.created_at.isoformat(),
            'access_count': shareable_content.access_count,
            'already_added': existing_access is not None,
            'is_own_deck': is_own_deck
        }

        logger.info(f"Returning deck info: {info}")
        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deck share info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get share info")


@router.delete("/shared/{deck_id}")
def remove_shared_deck(
        deck_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Usuwa udostępniony deck z biblioteki użytkownika (tylko dezaktywacja dostępu)"""
    try:
        logger.info(f"Removing shared deck {deck_id} from user {current_user.id_} library")

        # Sprawdź czy użytkownik ma dostęp do tego deck'a jako udostępniony
        access = db.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == current_user.id_,
            UserDeckAccess.user_deck_id == deck_id,
            UserDeckAccess.is_active == True
        ).first()

        if not access:
            logger.warning(f"Shared deck access {deck_id} not found for user {current_user.id_}")
            raise HTTPException(status_code=404, detail="Shared deck not found in your library")

        # Sprawdź czy to rzeczywiście udostępniony deck (ma template_id)
        user_deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.template_id.isnot(None)  # Upewnij się, że to kopia
        ).first()

        if not user_deck:
            logger.warning(f"Deck {deck_id} is not a shared deck copy")
            raise HTTPException(status_code=400, detail="This is not a shared deck")

        access.is_active = False

        db.commit()

        logger.info(f"Successfully removed shared deck {deck_id} from user {current_user.id_} library")

        return {
            'success': True,
            'message': f'Deck "{user_deck.name}" removed from your library. The original deck remains available to its owner.'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing shared deck from library: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove deck from library")


@router.post("/shared-code/{share_code}/deactivate")
def deactivate_share_code(
        share_code: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Dezaktywuje kod udostępniania"""
    try:
        shared_content = db.query(ShareableContent).filter(
            ShareableContent.share_code == share_code.upper(),
            ShareableContent.creator_id == current_user.id_,
            ShareableContent.content_type == 'deck'
        ).first()

        if not shared_content:
            raise HTTPException(status_code=404, detail="Share code not found")

        shared_content.is_public = False
        db.commit()

        logger.info(f"Share code {share_code} deactivated by user {current_user.id_}")

        return {
            'success': True,
            'message': 'Share code has been deactivated'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating share code: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to deactivate share code")

# ===========================================
# DYNAMICZNE ENDPOINTY (z parametrem deck_id)
# ===========================================

@router.get("/", response_model=List[dict])
def get_decks(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        include_shared: bool = Query(default=True, description="Include shared decks")  # Domyślnie True
):
    """Pobiera wszystkie deck'i użytkownika"""
    try:
        # Pobierz deck'i własne użytkownika
        own_decks = db.query(Deck).filter(
            Deck.user_id == current_user.id_,
            Deck.template_id.is_(None)  # Exclude copies from shared decks
        ).options(joinedload(Deck.flashcards)).all()

        result = []

        # Dodaj własne deck'i
        for deck in own_decks:
            flashcard_count = len(deck.flashcards) if deck.flashcards else 0
            result.append({
                'id': deck.id,
                'name': deck.name,
                'description': deck.description,
                'created_at': deck.created_at.isoformat() if deck.created_at else None,
                'flashcard_count': flashcard_count,
                'is_shared': deck.is_template,
                'is_own': True,
                'access_type': 'owner',  # Dodane
                'conversation_id': deck.conversation_id,
                'last_session': None
            })

        # Jeśli requested, dodaj udostępnione deck'i (zawsze jako kopie użytkownika)
        if include_shared:
            shared_decks_data = get_user_shared_decks(current_user.id_, db)
            for shared_deck in shared_decks_data:
                deck = db.query(Deck).filter(Deck.id == shared_deck['user_deck_id']).first()
                if deck:
                    flashcard_count = db.query(Flashcard).filter(Flashcard.deck_id == deck.id).count()
                    result.append({
                        'id': deck.id,
                        'name': deck.name,
                        'description': deck.description,
                        'created_at': deck.created_at.isoformat() if deck.created_at else None,
                        'flashcard_count': flashcard_count,
                        'is_shared': False,
                        'is_own': False,
                        'access_type': 'shared',  # Dodane
                        'original_deck_id': shared_deck['original_deck_id'],
                        'added_at': shared_deck['added_at'],
                        'code_used': shared_deck['code_used'],
                        'conversation_id': deck.conversation_id,
                        'last_session': None
                    })

        return result

    except Exception as e:
        logger.error(f"Error fetching decks for user {current_user.id_}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch decks")


@router.get("/get_deck/{deck_id}")
def get_deck(
        deck_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Pobiera pojedynczy deck z flashcards"""
    try:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id_
        ).options(joinedload(Deck.flashcards)).first()

        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found or access denied")

        return {
            'id': deck.id,
            'user_id': deck.user_id,
            'name': deck.name,
            'description': deck.description,
            'created_at': deck.created_at.isoformat() if deck.created_at else None,
            'conversation_id': deck.conversation_id,
            'is_template': deck.is_template,
            'template_id': deck.template_id,
            'flashcards': [
                {
                    'id': card.id,
                    'question': card.question,
                    'answer': card.answer,
                    'media_url': card.media_url
                }
                for card in deck.flashcards
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching deck {deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch deck")


@router.put("/{deck_id}")
def update_deck(
        deck_id: int,
        deck_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Aktualizuje deck"""
    try:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id_
        ).first()

        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found or access denied")

        # Aktualizuj podstawowe pola
        if 'name' in deck_data:
            deck.name = deck_data['name']
        if 'description' in deck_data:
            deck.description = deck_data['description']
        if 'conversation_id' in deck_data:
            deck.conversation_id = deck_data['conversation_id']

        # TYLKO jeśli flashcards są explicite podane, aktualizuj je
        if 'flashcards' in deck_data:
            # Usuń stare flashcards TYLKO jeśli są nowe
            db.query(Flashcard).filter(Flashcard.deck_id == deck_id).delete()

            # Dodaj nowe flashcards
            for fc_data in deck_data['flashcards']:
                flashcard = Flashcard(
                    question=fc_data.get('question'),
                    answer=fc_data.get('answer'),
                    media_url=fc_data.get('media_url'),
                    deck_id=deck_id
                )
                db.add(flashcard)

        db.commit()
        db.refresh(deck)

        # Pobierz flashcards do response
        flashcards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()

        return {
            'id': deck.id,
            'name': deck.name,
            'description': deck.description,
            'created_at': deck.created_at.isoformat() if deck.created_at else None,
            'conversation_id': deck.conversation_id,
            'flashcards': [
                {
                    'id': card.id,
                    'question': card.question,
                    'answer': card.answer,
                    'media_url': card.media_url
                }
                for card in flashcards
            ],
            'message': 'Deck updated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating deck {deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update deck")


@router.delete("/{deck_id}")
def delete_deck(
        deck_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Usuwa deck"""
    try:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id_
        ).first()

        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found or access denied")

        # Jeśli deck jest udostępniony, dezaktywuj kod udostępniania
        if deck.is_template:
            shared_content = db.query(ShareableContent).filter(
                ShareableContent.content_type == 'deck',
                ShareableContent.content_id == deck_id,
                ShareableContent.creator_id == current_user.id_
            ).first()
            if shared_content:
                shared_content.is_public = False
                logger.info(f"Deactivated share code for deleted deck {deck_id}")

        # Usuń flashcards
        db.query(Flashcard).filter(Flashcard.deck_id == deck_id).delete()

        # Usuń deck
        db.delete(deck)
        db.commit()

        logger.info(f"Deck {deck_id} deleted by user {current_user.id_}")

        return {'message': 'Deck deleted successfully. Existing copies owned by other users remain unaffected.'}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting deck {deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete deck")


@router.patch("/{deck_id}/conversation")
def update_deck_conversation(
        deck_id: int,
        conversation_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Aktualizuje tylko conversation_id dla deck'a"""
    try:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id_
        ).first()

        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found or access denied")

        # Aktualizuj tylko conversation_id
        if 'conversation_id' in conversation_data:
            deck.conversation_id = conversation_data['conversation_id']

        db.commit()
        db.refresh(deck)

        return {
            'id': deck.id,
            'conversation_id': deck.conversation_id,
            'message': 'Conversation ID updated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating conversation for deck {deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update conversation ID")


@router.delete("/{deck_id}")
def delete_deck(
        deck_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Usuwa deck"""
    try:
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id_
        ).first()

        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found or access denied")

        # Sprawdź czy deck jest udostępniony
        if deck.is_template:
            shared_content = db.query(ShareableContent).filter(
                ShareableContent.content_type == 'deck',
                ShareableContent.content_id == deck_id,
                ShareableContent.is_public == True
            ).first()
            if shared_content and shared_content.access_count > 0:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot delete deck that has been shared and accessed by others"
                )

        # Usuń flashcards
        db.query(Flashcard).filter(Flashcard.deck_id == deck_id).delete()

        # Usuń deck
        db.delete(deck)
        db.commit()

        logger.info(f"Deck {deck_id} deleted by user {current_user.id_}")

        return {'message': 'Deck deleted successfully'}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting deck {deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete deck")


@router.post("/{deck_id}/share")
def create_deck_share_code(
        deck_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Generuje kod udostępniania dla deck'a"""
    try:
        logger.info(f"Creating share code for deck {deck_id} by user {current_user.id_}")

        # Sprawdź czy użytkownik jest właścicielem deck'a
        deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == current_user.id_
        ).first()

        if not deck:
            logger.warning(f"Deck {deck_id} not found or access denied for user {current_user.id_}")
            raise HTTPException(status_code=404, detail="Deck not found or access denied")

        # Sprawdź czy deck ma jakieś flashcards
        flashcard_count = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).count()
        if flashcard_count == 0:
            logger.warning(f"Cannot share empty deck {deck_id}")
            raise HTTPException(status_code=400, detail="Cannot share empty deck")

        # Utwórz udostępnialny deck - przekaż sesję DB
        share_code = create_shareable_deck(deck_id, current_user.id_, db)

        logger.info(f"Share code created successfully: {share_code} for deck {deck_id}")

        return {
            'success': True,
            'share_code': share_code,
            'deck_name': deck.name,
            'message': 'Share code generated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating deck share code: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create share code")


@router.post("/{deck_id}/flashcards")
def add_flashcard(
        deck_id: int,
        flashcard_data: dict,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Dodaje nową flashcard do deck'a"""
    try:
        # Sprawdź dostęp do deck'a
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Sprawdź uprawnienia (właściciel lub dostęp przez udostępnienie)
        has_access = False
        if deck.user_id == current_user.id_:
            has_access = True
        else:
            access = db.query(UserDeckAccess).filter(
                UserDeckAccess.user_id == current_user.id_,
                UserDeckAccess.user_deck_id == deck_id,
                UserDeckAccess.is_active == True
            ).first()
            if access:
                has_access = True

        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

        flashcard = Flashcard(
            question=flashcard_data.get('question'),
            answer=flashcard_data.get('answer'),
            deck_id=deck_id,
            media_url=flashcard_data.get('media_url')
        )

        db.add(flashcard)
        db.commit()
        db.refresh(flashcard)

        return {
            'id': flashcard.id,
            'question': flashcard.question,
            'answer': flashcard.answer,
            'media_url': flashcard.media_url,
            'message': 'Flashcard added successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding flashcard: {e}")
        raise HTTPException(status_code=500, detail="Failed to add flashcard")


@router.get("/{deck_id}/flashcards")
def get_deck_flashcards(
        deck_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Pobiera wszystkie flashcards z deck'a"""
    try:
        # Sprawdź dostęp do deck'a
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Sprawdź uprawnienia
        has_access = False
        if deck.user_id == current_user.id_:
            has_access = True
        else:
            access = db.query(UserDeckAccess).filter(
                UserDeckAccess.user_id == current_user.id_,
                UserDeckAccess.user_deck_id == deck_id,
                UserDeckAccess.is_active == True
            ).first()
            if access:
                has_access = True

        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

        flashcards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()

        return [
            {
                'id': card.id,
                'question': card.question,
                'answer': card.answer,
                'media_url': card.media_url
            }
            for card in flashcards
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flashcards: {e}")
        raise HTTPException(status_code=500, detail="Failed to get flashcards")


@router.get("/debug/shareable-content")
def debug_shareable_content(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Debug endpoint - pokazuje ShareableContent w bazie"""
    try:
        all_shareable = db.query(ShareableContent).filter(
            ShareableContent.content_type == 'deck'
        ).all()

        result = []
        for item in all_shareable:
            deck = db.query(Deck).filter(Deck.id == item.content_id).first()
            result.append({
                'id': item.id,
                'share_code': item.share_code,
                'content_id': item.content_id,
                'deck_name': deck.name if deck else 'NOT FOUND',
                'creator_id': item.creator_id,
                'is_public': item.is_public,
                'access_count': item.access_count,
                'created_at': item.created_at.isoformat()
            })

        return {
            'total_count': len(result),
            'items': result
        }
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(status_code=500, detail="Debug failed")
