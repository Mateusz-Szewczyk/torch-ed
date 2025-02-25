"use client"

import { useState, useEffect, useCallback, type MouseEvent } from "react"
import { EditDeckDialog } from "@/components/EditDeckDialog"
import { ImportFlashcardsModal } from "@/components/ImportFlashcardsModal"
import { Button } from "@/components/ui/button"
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight, MoreVertical, Edit2, Trash2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { StudyDeck } from "@/components/StudyDeck"
import { CustomTooltip } from "@/components/CustomTooltip"
import { useTranslation } from "react-i18next"

import type { Deck, Flashcard, ErrorResponse } from "@/types"

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<Deck[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const [studyingDeck, setStudyingDeck] = useState<{
    deck: Deck
    study_session_id: number | null
    available_cards: Flashcard[]
    next_session_date: string | null
    conversation_id: number
  } | null>(null)

  const [openCollapsibles, setOpenCollapsibles] = useState<{ [key: number]: boolean }>({})

  const { t } = useTranslation()

  const API_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"
  const API_BASE_URL = `${API_URL}/decks/`
  const STUDY_SESSIONS_URL = `${API_URL}/study_sessions/`
  const CONVERSATIONS_URL = `${API_URL}/chats/`

  /**
   * Fetch decks from backend.
   */
  const fetchDecks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(API_BASE_URL, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || "Nie udało się pobrać decków.")
      }
      const data: Deck[] = await response.json()
      setDecks(data)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || t("error_fetch_decks"))
      } else {
        setError(t("error_unexpected_fetch_decks"))
      }
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [API_BASE_URL, t])

  useEffect(() => {
    fetchDecks()
  }, [fetchDecks])

  /**
   * Saves (creates/updates) a deck.
   */
  const handleSave = async (updatedDeck: Deck): Promise<void> => {
    try {
      const bodyData = {
        name: updatedDeck.name,
        description: updatedDeck.description,
        flashcards: updatedDeck.flashcards.map((fc) => ({
          question: fc.question,
          answer: fc.answer,
          media_url: fc.media_url,
        })),
        conversation_id: updatedDeck.conversation_id,
      }

      if (updatedDeck.id === 0) {
        // Create a new deck (with conversation_id defaulting to 0)
        const response = await fetch(API_BASE_URL, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        })
        if (!response.ok) {
          const errorData: ErrorResponse = await response.json()
          throw new Error((errorData.detail as string) || "Nie udało się stworzyć decka.")
        }
        const newDeck: Deck = await response.json()
        setDecks((prevDecks) => [...prevDecks, newDeck])
      } else {
        // Update existing deck
        const response = await fetch(`${API_BASE_URL}${updatedDeck.id}/`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        })
        if (!response.ok) {
          const errorData: ErrorResponse = await response.json()
          throw new Error((errorData.detail as string) || "Nie udało się zaktualizować decka.")
        }
        const updatedDeckFromServer: Deck = await response.json()
        setDecks((prevDecks) =>
          prevDecks.map((deck) => (deck.id === updatedDeckFromServer.id ? updatedDeckFromServer : deck)),
        )
      }
      // Close collapsible panel after save
      setOpenCollapsibles((prev) => ({ ...prev, [updatedDeck.id]: false }))
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t("error_saving_deck")}: ${err.message}`)
      } else {
        setError(t("error_unexpected_saving_deck"))
      }
      console.error("Error saving deck:", err)
    }
  }

  // Wrapper to pass to EditDeckDialog
  const handleSaveWrapper = (updatedDeck: Deck): void => {
    void handleSave(updatedDeck)
  }

  const handleDelete = async (deckId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}${deckId}/`, {
        method: "DELETE",
        credentials: "include",
      })
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        throw new Error((errorData.detail as string) || "Nie udało się usunąć decka.")
      }
      setDecks((prev) => prev.filter((deck) => deck.id !== deckId))
      setOpenCollapsibles((prev) => ({ ...prev, [deckId]: false }))
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t("error_deleting_deck")}: ${err.message}`)
      } else {
        setError(t("error_unexpected_deleting_deck"))
      }
      console.error("Error deleting deck:", err)
    }
  }

  /**
   * Starts a study session for a deck.
   * If the deck does not have a conversation_id (or it is 0),
   * create a new conversation, update the deck in the database (and locally),
   * then start the study session using the updated conversation_id.
   */
  const handleStudy = async (deck: Deck) => {
    try {
      let convId = deck.conversation_id
      if (!convId || convId === 0) {
        // Create a new conversation for the deck
        const convResponse = await fetch(CONVERSATIONS_URL, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
        if (!convResponse.ok) {
          const convError = await convResponse.json()
          throw new Error(convError.detail || "Nie udało się utworzyć konwersacji.")
        }
        const newConv = await convResponse.json()
        convId = newConv.id
        // Update the deck in the database with the new conversation_id
        const updateResponse = await fetch(`${API_BASE_URL}${deck.id}/`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: deck.name,
            description: deck.description,
            flashcards: deck.flashcards.map((fc) => ({
              id: fc.id,
              question: fc.question,
              answer: fc.answer,
              media_url: fc.media_url,
            })),
            conversation_id: convId,
          }),
        })
        if (!updateResponse.ok) {
          const updateError = await updateResponse.json()
          throw new Error(updateError.detail || "Nie udało się zaktualizować decka.")
        }
        const updatedDeck = await updateResponse.json()
        setDecks((prev) => prev.map((d) => (d.id === deck.id ? updatedDeck : d)))
        deck = updatedDeck // update local deck object
      }

      // Start the study session using the conversation_id from the deck
      const response = await fetch(`${STUDY_SESSIONS_URL}start`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deck_id: deck.id, conversation_id: convId }),
      })
      if (!response.ok) {
        const errorData: ErrorResponse = await response.json()
        let errorMessage = "Nie udało się rozpocząć sesji nauki."
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map((err) => (typeof err === "object" && "msg" in err ? err.msg : String(err)))
            .join(", ")
        } else if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail
        }
        throw new Error(errorMessage)
      }
      const data = await response.json()
      const { study_session_id, available_cards, next_session_date } = data
      if (!Array.isArray(available_cards)) {
        throw new Error("Invalid response format: available_cards is not an array.")
      }
      setStudyingDeck({
        deck,
        study_session_id,
        available_cards,
        next_session_date,
        conversation_id: convId,
      })
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t("error_starting_study")}: ${err.message}`)
      } else {
        setError(t("error_unexpected_starting_study"))
      }
      console.error("Error starting study session:", err)
    }
  }

  const handleExitStudy = () => {
    setStudyingDeck(null)
  }

  const toggleCollapsibles = (deckId: number) => {
    setOpenCollapsibles((prev) => ({
      ...prev,
      [deckId]: !prev[deckId],
    }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="mr-2 h-16 w-16 animate-spin text-primary" />
        <span className="text-2xl font-semibold text-primary">{t("loading_decks")}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl font-bold text-destructive">{t("error")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchDecks} className="w-full">
              {t("try_again")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  if (studyingDeck) {
    return (
      <StudyDeck
        deck={studyingDeck.deck}
        study_session_id={studyingDeck.study_session_id}
        available_cards={studyingDeck.available_cards}
        next_session_date={studyingDeck.next_session_date}
        conversation_id={studyingDeck.conversation_id}
        onExit={handleExitStudy}
      />
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-primary mb-2">{t("flashcards")}</h1>
        <CustomTooltip content={t("flashcards_tooltip")}>
          <Button variant="ghost" size="sm" className="rounded-full">
            <Info className="h-5 w-5" />
            <span className="sr-only">{t("more_information")}</span>
          </Button>
        </CustomTooltip>
      </div>

      {decks.length === 0 ? (
        <Card className="w-full max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle className="text-2xl font-bold">{t("welcome_flashcards")}</CardTitle>
            <CardDescription>{t("get_started_create_deck")}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center space-y-6 py-8">
            <BookOpen className="h-24 w-24 text-muted-foreground" />
            <p className="text-center text-muted-foreground">{t("no_flashcard_decks")}</p>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <ImportFlashcardsModal
              trigger={<Button className="w-full">{t("import_flashcards")}</Button>}
              onImportSuccess={fetchDecks}
            />
            <EditDeckDialog
              deck={{ id: 0, name: "", description: "", flashcards: [], conversation_id: 0 }}
              onSave={handleSaveWrapper}
              trigger={
                <Button className="w-full" variant="default">
                  <PlusCircle className="h-5 w-5 mr-2" />
                  {t("create_your_first_deck")}
                </Button>
              }
            />
          </CardFooter>
        </Card>
      ) : (
        <>
          {/* Buttons for Import and Create New Deck */}
          <div className="mb-8 flex flex-col sm:flex-row justify-center sm:justify-end space-y-4 sm:space-y-0 sm:space-x-4">
            <ImportFlashcardsModal
              trigger={<Button className="w-full sm:w-auto">{t("import_flashcards")}</Button>}
              onImportSuccess={fetchDecks}
            />
            <EditDeckDialog
              deck={{ id: 0, name: "", description: "", flashcards: [], conversation_id: 0 }}
              onSave={handleSaveWrapper}
              trigger={
                <Button className="w-full sm:w-auto" variant="default">
                  <PlusCircle className="h-5 w-5 mr-2" />
                  {t("create_new_deck")}
                </Button>
              }
            />
          </div>
          {/* Decks grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {decks.map((deck) => (
              <div key={deck.id} className="relative group">
                <Card
                  className="flex flex-col w-full transition-all duration-300 hover:shadow-xl hover:-translate-y-1 group-hover:z-10"
                  style={{
                    minHeight: "400px",
                    height: "auto",
                    maxHeight: "400px",
                    transition: "all 0.3s ease-in-out",
                  }}
                >
                  <CardHeader className="flex-shrink-0">
                    <div className="flex justify-between items-center">
                      <CardTitle className="text-xl font-bold truncate">{deck.name}</CardTitle>
                      <Collapsible
                        open={openCollapsibles[deck.id] || false}
                        onOpenChange={() => toggleCollapsibles(deck.id)}
                      >
                        <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="p-1" aria-label="Options">
                            <MoreVertical className="h-5 w-5" />
                          </Button>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="absolute right-4 top-12 bg-card border border-border rounded-md shadow-lg z-50 p-2">
                          <div className="flex flex-col">
                            <EditDeckDialog
                              deck={deck}
                              onSave={handleSaveWrapper}
                              trigger={
                                <Button variant="ghost" size="sm" className="justify-start">
                                  <Edit2 className="h-4 w-4 mr-2" />
                                  {t("edit")}
                                </Button>
                              }
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              className="justify-start text-destructive"
                              onClick={(e: MouseEvent<HTMLButtonElement>) => {
                                e.stopPropagation()
                                handleDelete(deck.id)
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t("delete")}
                            </Button>
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-grow overflow-hidden">
                    <p className="text-sm text-muted-foreground">{deck.description || t("no_description")}</p>
                  </CardContent>
                  <CardFooter className="mt-auto flex justify-between items-center">
                    <p className="text-sm font-medium text-muted-foreground">
                      {deck.flashcards.length} {t("cards")}
                    </p>
                    <Button variant="default" onClick={() => handleStudy(deck)}>
                      {t("study")}
                      <ChevronRight className="h-5 w-5 ml-2" />
                    </Button>
                  </CardFooter>
                </Card>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

