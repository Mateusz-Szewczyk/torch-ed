"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { EditDeckDialog } from "@/components/EditDeckDialog"
import { ImportFlashcardsModal } from "@/components/ImportFlashcardsModal"
import { CustomTooltip } from "@/components/CustomTooltip"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  PlusCircle,
  BookOpen,
  Info,
  ChevronRight,
  MoreHorizontal,
  Edit,
  Trash2,
  Search,
  Clock,
  X,
  ArrowLeft,
  SortAsc,
  SortDesc,
  Filter,
  CheckCircle2,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { StudyDeck } from "@/components/StudyDeck"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"

import type { Deck, Flashcard, ErrorResponse } from "@/types"

// Animation variants for framer-motion
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
}

// Sort options for decks
type SortOption = "name" | "cards" | "recent"
type SortDirection = "asc" | "desc"

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<Deck[]>([])
  const [filteredDecks, setFilteredDecks] = useState<Deck[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [sortBy, setSortBy] = useState<SortOption>("recent")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")
  const [isSearchFocused, setIsSearchFocused] = useState<boolean>(false)

  const [studyingDeck, setStudyingDeck] = useState<{
    deck: Deck
    study_session_id: number | null
    available_cards: Flashcard[]
    next_session_date: string | null
    conversation_id: number
  } | null>(null)

  const { t } = useTranslation()
  const searchInputRef = useRef<HTMLInputElement>(null)

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
        throw new Error((errorData.detail as string) || t("error_fetch_decks"))
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

  // Filter and sort decks based on search query and sort options
  useEffect(() => {
    let result = [...decks]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (deck) =>
          deck.name.toLowerCase().includes(query) ||
          (deck.description && deck.description.toLowerCase().includes(query)),
      )
    }

    // Apply sorting
    result.sort((a, b) => {
      if (sortBy === "name") {
        return sortDirection === "asc" ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name)
      } else if (sortBy === "cards") {
        return sortDirection === "asc"
          ? a.flashcards.length - b.flashcards.length
          : b.flashcards.length - a.flashcards.length
      } else {
        // recent
        // Using ID as a proxy for recency since we don't have created_at
        return sortDirection === "asc" ? a.id - b.id : b.id - a.id
      }
    })

    setFilteredDecks(result)
  }, [decks, searchQuery, sortBy, sortDirection])

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
          throw new Error((errorData.detail as string) || t("error_creating_deck"))
        }
        const newDeck: Deck = await response.json()
        setDecks((prevDecks) => [...prevDecks, newDeck])
        // Usuń powiadomienie toast
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
          throw new Error((errorData.detail as string) || t("error_updating_deck"))
        }
        const updatedDeckFromServer: Deck = await response.json()
        setDecks((prevDecks) =>
          prevDecks.map((deck) => (deck.id === updatedDeckFromServer.id ? updatedDeckFromServer : deck)),
        )
        // Usuń powiadomienie toast
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error("Error saving deck:", err.message)
        setError(err.message)
      } else {
        console.error("Unexpected error saving deck:", err)
        setError(t("error_unexpected_saving_deck"))
      }
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
        throw new Error((errorData.detail as string) || t("error_deleting_deck"))
      }
      setDecks((prev) => prev.filter((deck) => deck.id !== deckId))
      // Usuń powiadomienie toast
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error("Error deleting deck:", err.message)
        setError(err.message)
      } else {
        console.error("Unexpected error deleting deck:", err)
        setError(t("error_unexpected_deleting_deck"))
      }
    }
  }

  /**
   * Starts a study session for a deck.
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
          throw new Error(convError.detail || t("error_creating_conversation"))
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
          throw new Error(updateError.detail || t("error_updating_deck"))
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
        let errorMessage = t("error_starting_study")
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
        throw new Error(t("invalid_response_format"))
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
        console.error("Error starting study session:", err.message)
        setError(err.message)
      } else {
        console.error("Unexpected error starting study session:", err)
        setError(t("error_unexpected_starting_study"))
      }
    }
  }

  const handleExitStudy = () => {
    setStudyingDeck(null)
  }

  const handleClearSearch = () => {
    setSearchQuery("")
    if (searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }

  const toggleSortDirection = () => {
    setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"))
  }

  // Format date for display
// Loading state with skeleton UI
  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="flex flex-col items-center justify-center mb-12">
          <div className="w-48 h-10 bg-muted animate-pulse rounded-md mb-4"></div>
          <div className="w-64 h-6 bg-muted animate-pulse rounded-md"></div>
        </div>

        <div className="w-full max-w-md mx-auto mb-8 bg-muted animate-pulse h-10 rounded-md"></div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="bg-muted animate-pulse rounded-xl h-64"></div>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 flex items-center justify-center min-h-[50vh]">
        <Card className="w-full max-w-md border-destructive/20">
          <CardHeader className="pb-4">
            <CardTitle className="text-2xl font-bold text-destructive flex items-center gap-2">
              <X className="h-6 w-6" />
              {t("error")}
            </CardTitle>
            <CardDescription>{t("error_occurred")}</CardDescription>
          </CardHeader>
          <CardContent className="pb-6">
            <p className="text-destructive/90 bg-destructive/5 p-4 rounded-md border border-destructive/10">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchDecks} className="w-full">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t("try_again")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  // Study mode
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

  // Main content
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <motion.div
        className="flex flex-col items-center justify-center mb-8 md:mb-12"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent mb-2">
          {t("flashcards")}
        </h1>
        <p className="text-muted-foreground text-center max-w-xl mb-2">{t("flashcards_description")}</p>
        <CustomTooltip
          content={
            t("flashcards_tooltip") ||
            "Fiszki pomagają w nauce poprzez aktywne przypominanie. Twórz własne zestawy lub importuj gotowe materiały."
          }
        >
          <Button variant="ghost" size="sm" className="rounded-full h-8 w-8 p-0">
            <Info className="h-4 w-4" />
            <span className="sr-only">{t("more_information")}</span>
          </Button>
        </CustomTooltip>
      </motion.div>

      {decks.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="w-full max-w-2xl mx-auto border-dashed bg-background/50 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <CardTitle className="text-2xl font-bold">{t("welcome_flashcards")}</CardTitle>
              <CardDescription>{t("get_started_create_deck")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-6 py-12">
              <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center">
                <BookOpen className="h-12 w-12 text-primary" />
              </div>
              <p className="text-center text-muted-foreground max-w-md">{t("no_flashcard_decks_extended")}</p>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4 pt-2 pb-6">
              <ImportFlashcardsModal
                trigger={
                  <Button className="w-full" variant="outline">
                    {t("import_flashcards")}
                  </Button>
                }
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
        </motion.div>
      ) : (
        <>
          {/* Search and Filter Bar */}
          <motion.div
            className="mb-8 flex flex-col md:flex-row gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div
              className={cn(
                "relative flex-grow transition-all duration-300 rounded-lg",
                isSearchFocused ? "ring-2 ring-primary/20" : "",
              )}
            >
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("search_decks")}
                className="pl-10 pr-10 h-11 bg-background/60 backdrop-blur-sm border-muted"
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setIsSearchFocused(false)}
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 transform -translate-y-1/2 h-8 w-8 p-0"
                  onClick={handleClearSearch}
                >
                  <X className="h-4 w-4" />
                  <span className="sr-only">{t("clear_search")}</span>
                </Button>
              )}
            </div>

            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="h-11 gap-2">
                    <Filter className="h-4 w-4" />
                    <span className="hidden sm:inline">{t("sort_by")}</span>
                    <span className="font-medium">
                      {sortBy === "name" ? t("name") : sortBy === "cards" ? t("card_count") : t("recent")}
                    </span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem
                    onClick={() => setSortBy("name")}
                    className={cn(sortBy === "name" && "bg-primary/10 font-medium")}
                  >
                    {sortBy === "name" && <CheckCircle2 className="h-4 w-4 mr-2 text-primary" />}
                    {t("name")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setSortBy("cards")}
                    className={cn(sortBy === "cards" && "bg-primary/10 font-medium")}
                  >
                    {sortBy === "cards" && <CheckCircle2 className="h-4 w-4 mr-2 text-primary" />}
                    {t("card_count")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setSortBy("recent")}
                    className={cn(sortBy === "recent" && "bg-primary/10 font-medium")}
                  >
                    {sortBy === "recent" && <CheckCircle2 className="h-4 w-4 mr-2 text-primary" />}
                    {t("recent")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <CustomTooltip
                content={
                  sortDirection === "asc"
                    ? t("sort_ascending") || "Sortuj rosnąco"
                    : t("sort_descending") || "Sortuj malejąco"
                }
              >
                <Button variant="outline" size="icon" className="h-11 w-11" onClick={toggleSortDirection}>
                  {sortDirection === "asc" ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
                  <span className="sr-only">{sortDirection === "asc" ? t("ascending") : t("descending")}</span>
                </Button>
              </CustomTooltip>

              <CustomTooltip content={t("import_flashcards_tooltip") || "Importuj fiszki z plików CSV, APKG lub TXT"}>
                <ImportFlashcardsModal
                  trigger={
                    <Button variant="outline" className="h-11 gap-2">
                      <BookOpen className="h-4 w-4" />
                      <span className="hidden sm:inline">{t("import")}</span>
                    </Button>
                  }
                  onImportSuccess={fetchDecks}
                />
              </CustomTooltip>

              <CustomTooltip content={t("create_new_deck_tooltip") || "Utwórz nowy zestaw fiszek"}>
                <EditDeckDialog
                  deck={{ id: 0, name: "", description: "", flashcards: [], conversation_id: 0 }}
                  onSave={handleSaveWrapper}
                  trigger={
                    <Button className="h-11 gap-2">
                      <PlusCircle className="h-4 w-4" />
                      <span className="hidden sm:inline">{t("create")}</span>
                    </Button>
                  }
                />
              </CustomTooltip>
            </div>
          </motion.div>

          {/* Results count */}
          {searchQuery && (
            <div className="mb-4 text-sm text-muted-foreground">
              {filteredDecks.length === 0
                ? t("no_results_found")
                : t("showing_results", { count: filteredDecks.length, total: decks.length })}
            </div>
          )}

          {/* Decks grid */}
          {filteredDecks.length === 0 && searchQuery ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Search className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium mb-2">{t("no_matching_decks")}</h3>
              <p className="text-muted-foreground text-center max-w-md mb-6">{t("try_different_search")}</p>
              <Button variant="outline" onClick={handleClearSearch}>
                {t("clear_search")}
              </Button>
            </div>
          ) : (
            <motion.div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              <AnimatePresence>
                {filteredDecks.map((deck) => (
                  <motion.div
                    key={deck.id}
                    variants={itemVariants}
                    layout
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="group"
                  >
                    <Card className="flex flex-col h-full overflow-hidden border-border/60 bg-card/95 backdrop-blur-sm hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1">
                      <CardHeader className="pb-3 flex flex-row items-start justify-between space-y-0">
                        <div className="space-y-1.5">
                          <CardTitle className="text-xl font-bold line-clamp-1 pr-6">{deck.name}</CardTitle>
                          <CardDescription className="line-clamp-1">
                            {deck.description || t("no_description")}
                          </CardDescription>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreHorizontal className="h-4 w-4" />
                              <span className="sr-only">{t("options")}</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            <EditDeckDialog
                              deck={deck}
                              onSave={handleSaveWrapper}
                              trigger={
                                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                                  <Edit className="h-4 w-4 mr-2" />
                                  {t("edit")}
                                </DropdownMenuItem>
                              }
                            />
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onSelect={() => handleDelete(deck.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t("delete")}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </CardHeader>

                      <CardContent className="pb-3 flex-grow">
                        <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                          {deck.description || t("no_description")}
                        </p>

                        <div className="flex flex-wrap gap-2 mt-auto">
                          <Badge variant="secondary" className="flex items-center gap-1">
                            <BookOpen className="h-3 w-3" />
                            {deck.flashcards.length} {t("cards")}
                          </Badge>

                          {deck.conversation_id > 0 && (
                            <Badge variant="outline" className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {t("last_studied")}
                            </Badge>
                          )}
                        </div>
                      </CardContent>

                      <CardFooter className="pt-3 flex justify-end">
                        <CustomTooltip
                          content={t("start_study_session") || "Rozpocznij sesję nauki z tym zestawem fiszek"}
                        >
                          <Button
                            variant="default"
                            className="w-full sm:w-auto transition-all duration-300 group-hover:bg-primary/90"
                            onClick={() => handleStudy(deck)}
                          >
                            {t("study")}
                            <ChevronRight className="h-4 w-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
                          </Button>
                        </CustomTooltip>
                      </CardFooter>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </>
      )}
    </div>
  )
}
