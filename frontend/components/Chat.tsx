"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { SendIcon, Settings, ArrowDown, ArrowUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { SyntaxHighlighterProps } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism"
import { useTranslation } from "react-i18next"
import { v4 as uuidv4 } from "uuid"
import BouncingDots from "@/components/BouncingDots"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from "@/components/ui/dialog"

type Message = {
  id: string
  conversation_id: number
  text: string
  sender: "user" | "bot"
  created_at: string
  isError?: boolean
}

interface ChatProps {
  conversationId: number
}

const availableTools = [
  "Wiedza z plików",
  "Generowanie fiszek",
  "Generowanie egzaminu",
  "Wyszukaj w internecie"
]

const ToolSelectionDialog: React.FC<{
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  selectedTools: string[]
  setSelectedTools: React.Dispatch<React.SetStateAction<string[]>>
  availableTools: string[]
}> = ({ isOpen, onOpenChange, selectedTools, setSelectedTools, availableTools }) => {
  const [tempSelectedTools, setTempSelectedTools] = useState<string[]>(selectedTools)

  useEffect(() => {
    setTempSelectedTools(selectedTools)
  }, [selectedTools])

  const moveToolUp = (index: number) => {
    if (index > 0) {
      const newTools = [...tempSelectedTools]
      ;[newTools[index - 1], newTools[index]] = [newTools[index], newTools[index - 1]]
      setTempSelectedTools(newTools)
    }
  }

  const moveToolDown = (index: number) => {
    if (index < tempSelectedTools.length - 1) {
      const newTools = [...tempSelectedTools]
      ;[newTools[index], newTools[index + 1]] = [newTools[index + 1], newTools[index]]
      setTempSelectedTools(newTools)
    }
  }

  const handleSave = () => {
    setSelectedTools(tempSelectedTools)
    onOpenChange(false)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold mb-4">Select and Order Tools</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          <div className="space-y-4">
            {tempSelectedTools.map((tool, index) => (
              <div key={tool} className="flex items-center space-x-2 bg-secondary p-3 rounded-lg relative">
                <span className="font-medium">{tool}</span>
                <div className="flex-grow" />
                <Button variant="ghost" size="sm" onClick={() => moveToolUp(index)} disabled={index === 0}>
                  <ArrowUp className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => moveToolDown(index)} disabled={index === tempSelectedTools.length - 1}>
                  <ArrowDown className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setTempSelectedTools((prev) => prev.filter((t) => t !== tool))}>
                  Remove
                </Button>
                {index < tempSelectedTools.length - 1 && (
                  <ArrowDown className="h-4 w-4 top-16 text-primary absolute -bottom-3 left-1/2 transform -translate-x-1/2" />
                )}
              </div>
            ))}
          </div>
          <div>
            <h4 className="text-lg font-semibold mb-3">Available Tools</h4>
            <div className="flex flex-wrap gap-2">
              {availableTools
                .filter((tool) => !tempSelectedTools.includes(tool))
                .map((tool) => (
                  <Button key={tool} variant="outline" size="sm" onClick={() => setTempSelectedTools((prev) => [...prev, tool])}>
                    {tool}
                  </Button>
                ))}
            </div>
          </div>
        </div>
        <div className="flex justify-end space-x-2 mt-6">
          <DialogClose>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button onClick={handleSave}>
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

const Chat: React.FC<ChatProps> = ({ conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [isToolDialogOpen, setIsToolDialogOpen] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const { t } = useTranslation()

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

  // Autoscroll do najnowszej wiadomości
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [isLoading, messages])

  // Fetch wiadomości z API
  const fetchMessages = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        method: "GET",
      })
      if (res.ok) {
        const data: Message[] = await res.json()
        setMessages(data.map((msg) => ({ ...msg, isError: false })))
      } else {
        console.error("Failed to fetch messages:", res.statusText)
      }
    } catch (err) {
      console.error("Error fetching messages:", err)
    }
  }, [API_BASE_URL, conversationId])

  useEffect(() => {
    if (conversationId) {
      fetchMessages()
    }
  }, [fetchMessages, conversationId])

  // Funkcja wysyłania wiadomości
  const handleSend = async () => {
    if (!input.trim()) return
    const userInput = input.trim()
    setInput("")

    const userMsg: Message = {
      id: uuidv4(),
      conversation_id: conversationId,
      text: userInput,
      sender: "user",
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      setIsLoading(true)
      setError("")

      // Zapisz wiadomość użytkownika
      const userMessageResponse = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender: "user", text: userInput }),
      })

      if (!userMessageResponse.ok) {
        const errData = await userMessageResponse.json()
        throw new Error(errData.detail || "Error sending user message.")
      }

      // Wywołanie endpointu zapytania – przesyłamy również selectedTools
      const response = await fetch(`${API_BASE_URL}/query/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          query: userInput,
          selected_tools: selectedTools,
        }),
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || `Error: ${response.statusText}`)
      }

      const data = await response.json()

      const botMsg: Message = {
        id: uuidv4(),
        conversation_id: conversationId,
        text: data.answer,
        sender: "bot",
        created_at: new Date().toISOString(),
      }

      // Zapisz wiadomość bota
      const botMessageResponse = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender: "bot", text: data.answer }),
      })

      if (!botMessageResponse.ok) {
        const errData = await botMessageResponse.json()
        throw new Error(errData.detail || "Error sending bot message.")
      }

      setMessages((prev) => [...prev, botMsg])
      // Czyścimy wybrane narzędzia po wysłaniu
      setSelectedTools([])
    } catch (err) {
      console.error("Error sending message:", err)
      const errorText = err instanceof Error ? err.message : String(err)
      const errorMessage: Message = {
        id: uuidv4(),
        conversation_id: conversationId,
        text: errorText,
        sender: "bot",
        created_at: new Date().toISOString(),
        isError: true,
      }
      setMessages((prev) => [...prev, errorMessage])
      setError(errorText)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background text-foreground">
      {/* Lista wiadomości */}
      <div className="flex-1 overflow-auto mx-auto p-4 pb-32 w-full md:w-3/5">
        {messages.map((message) => {
          const alignmentClass = message.sender === "user" ? "ml-auto mr-0" : "mr-auto ml-0"
          return (
            <div key={message.id} className="flex">
              <div
                className={`inline-block p-3 rounded-lg ${alignmentClass} max-w-full sm:max-w-4/5 break-words ${
                  message.sender === "user"
                    ? "bg-secondary text-secondary-foreground"
                    : "bg-background text-foreground"
                }`}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose dark:prose-invert break-words max-w-none"
                  components={{
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || "")
                      const language = match ? match[1] : ""
                      const isInline = !match
                      return isInline ? (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      ) : (
                        <SyntaxHighlighter
                          style={oneDark}
                          language={language}
                          PreTag="div"
                          {...(props as SyntaxHighlighterProps)}
                        >
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      )
                    },
                  }}
                >
                  {message.text}
                </ReactMarkdown>
              </div>
            </div>
          )
        })}
        {isLoading && (
          <div className="flex">
            <div className="inline-block p-3 rounded-lg mr-auto max-w-full sm:max-w-4/5 bg-secondary text-secondary-foreground break-words">
              <BouncingDots />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      {/* Kontener z polem tekstowym, przybornikiem i przyciskiem */}
      <div className="p-2 w-4/5 bg-secondary rounded-2xl self-center m-6 flex flex-col sm:flex-row items-center">
        <div className="flex gap-2 w-full">
          <Button
            onClick={() => setIsToolDialogOpen(true)}
            variant="outline"
            className="shrink-0 self-center"
          >
            <Settings className="h-4 w-4" />
            <span className="sr-only">Select Tools</span>
          </Button>
          <div className="flex-grow m-2">
            <Input
              multiline
              maxRows={12}
              value={input}
              onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
                setInput(e.target.value)
              }
              placeholder={t("type_message") || "Type your message..."}
              className="bg-secondary rounded-2xl flex-1 text-black dark:text-white text-base sm:text-sm md:text-lg"
              disabled={isLoading}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            variant="default"
            className="shrink-0 self-center mr-2"
          >
            <SendIcon className="h-4 w-4" />
            <span className="sr-only">{t("send")}</span>
          </Button>
        </div>
        {error && (
          <p className="mt-2 text-sm sm:text-base text-destructive text-center">
            {error}
          </p>
        )}
      </div>

      {/* Tool Selection Dialog */}
      <ToolSelectionDialog
        isOpen={isToolDialogOpen}
        onOpenChange={setIsToolDialogOpen}
        selectedTools={selectedTools}
        setSelectedTools={setSelectedTools}
        availableTools={availableTools}
      />
    </div>
  )
}

export default Chat
