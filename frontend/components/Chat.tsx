"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { SendIcon, Settings, CheckCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import type { SyntaxHighlighterProps } from "react-syntax-highlighter"
import { oneDark, oneLight } from "react-syntax-highlighter/dist/cjs/styles/prism"
import { useTranslation } from "react-i18next"
import { v4 as uuidv4 } from "uuid"
import { useTheme } from "next-themes"
import ToolSelectionDialog from "@/components/ToolSelectionDialog"
import { cn } from "@/lib/utils"
import { debounce } from "lodash"

type Message = {
  id: string
  conversation_id: number | undefined
  text: string
  sender: "user" | "bot"
  created_at: string
  isError?: boolean
  isStreaming?: boolean
}

interface ChatProps {
  conversationId: number | undefined
}

const availableTools = ["Wiedza z plików", "Generowanie fiszek", "Generowanie egzaminu", "Wyszukaj w internecie"]

const TypingIndicator = React.memo(() => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    className="flex items-center space-x-1 px-4 py-3"
  >
    <div className="flex space-x-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 bg-primary/60 rounded-full"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 1.5,
            repeat: Number.POSITIVE_INFINITY,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
    <span className="text-sm text-muted-foreground ml-2">Thinking...</span>
  </motion.div>
))
TypingIndicator.displayName = 'TypingIndicator'

const MessageBubble = React.memo<{
  message: Message
  isLast: boolean
}>(({ message, isLast }) => {
  const { theme } = useTheme()
  const [showTimestamp, setShowTimestamp] = useState(false)
  const isUser = message.sender === "user"
  const isError = message.isError

  const formatTime = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    })
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn("group relative mb-4 flex", isUser ? "justify-end" : "justify-start")}
      onMouseEnter={() => setShowTimestamp(true)}
      onMouseLeave={() => setShowTimestamp(false)}
    >
      <div
        className={cn(
          "relative max-w-[90%] md:max-w-[90%] rounded-2xl px-4 py-3 shadow-sm transition-all duration-200",
          "hover:shadow-md hover:scale-[1.01]",
          isUser
            ? "bg-primary text-primary-foreground ml-auto"
            : isError
              ? "bg-destructive/10 border border-destructive/20 text-destructive"
              : "bg-card text-card-foreground border border-border",
        )}
      >
        <div className="relative">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className={cn(
              "prose max-w-none break-words",
              isUser ? "prose-invert text-primary-foreground" : "text-card-foreground",
              "prose-sm prose-p:my-1 prose-pre:my-2 prose-code:text-sm",
              isUser
                ? "[&>*]:text-primary-foreground [&_strong]:text-primary-foreground [&_em]:text-primary-foreground/90"
                : "[&>*]:text-card-foreground [&_strong]:text-foreground [&_em]:text-muted-foreground",
            )}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "")
                const language = match ? match[1] : ""
                const isInline = !match

                return isInline ? (
                  <code
                    className={cn(
                      "px-1.5 py-0.5 rounded-md text-sm font-mono",
                      isUser
                        ? "bg-primary-foreground/20 text-primary-foreground"
                        : "bg-muted text-foreground",
                    )}
                    {...props}
                  >
                    {children}
                  </code>
                ) : (
                  <div className="my-3 rounded-lg overflow-hidden border border-border">
                    <SyntaxHighlighter
                      style={theme === "dark" ? oneDark : oneLight}
                      language={language}
                      PreTag="div"
                      className="!m-0 !bg-transparent"
                      {...(props as SyntaxHighlighterProps)}
                    >
                      {String(children).replace(/\n$/, "")}
                    </SyntaxHighlighter>
                  </div>
                )
              },
              pre: ({ children }) => <div className="overflow-x-auto">{children}</div>,
              h1: ({ children }) => (
                <h1 className={cn("text-lg font-bold", isUser ? "text-primary-foreground" : "text-foreground")}>
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className={cn("text-base font-semibold", isUser ? "text-primary-foreground" : "text-foreground")}>
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className={cn("text-sm font-medium", isUser ? "text-primary-foreground" : "text-foreground")}>
                  {children}
                </h3>
              ),
              ul: ({ children }) => (
                <ul className={cn("list-disc list-inside", isUser ? "text-primary-foreground" : "text-card-foreground")}>
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className={cn("list-decimal list-inside", isUser ? "text-primary-foreground" : "text-card-foreground")}>
                  {children}
                </ol>
              ),
              p: ({ children }) => (
                <p className={cn("leading-relaxed", isUser ? "text-primary-foreground" : "text-card-foreground")}>
                  {children}
                </p>
              ),
            }}
          >
            {message.text}
          </ReactMarkdown>
        </div>
        {isUser && (
          <div className="flex items-center justify-end mt-1 space-x-1">
            <CheckCheck className="w-3 h-3 text-primary-foreground/70" />
          </div>
        )}
        <AnimatePresence>
          {showTimestamp && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className={cn(
                "absolute -top-8 px-2 py-1 bg-popover text-popover-foreground border border-border rounded-md text-xs shadow-lg",
                isUser ? "right-0" : "left-0",
              )}
            >
              {formatTime(message.created_at)}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
})
MessageBubble.displayName = 'MessageBubble'

const Chat: React.FC<ChatProps> = ({ conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [isToolDialogOpen, setIsToolDialogOpen] = useState(false)
  const [inputHeight, setInputHeight] = useState("auto")
  const endRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { t } = useTranslation()
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

  // Debounced fetch messages
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fetchMessages = useCallback(
    debounce(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          method: "GET",
        })
        if (res.ok) {
          const data: Message[] = await res.json()
          setMessages(data.map((msg) => ({ ...msg, isError: false, isStreaming: false })))
        } else {
          setError(`Failed to fetch messages: ${res.statusText}`)
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error"
        setError(`Error fetching messages: ${errorMessage}`)
      }
    }, 300),
    [API_BASE_URL, conversationId]
  )

  useEffect(() => {
    if (conversationId) {
      fetchMessages()
    }
    return () => fetchMessages.cancel()
  }, [conversationId, fetchMessages])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      const scrollHeight = textareaRef.current.scrollHeight
      const newHeight = Math.min(scrollHeight, 120)
      textareaRef.current.style.height = `${newHeight}px`
      setInputHeight(`${newHeight}px`)
    }
  }, [input])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, isLoading])

  const handleStreamingResponse = useCallback(async (userInput: string) => {
    // Save user message to database first
    try {
      await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender: "user", text: userInput }),
      })
    } catch (err) {
      console.error("Failed to save user message:", err)
    }

    // Create initial bot message (empty, streaming)
    const botMsgId = uuidv4()
    const botMsg: Message = {
      id: botMsgId,
      conversation_id: conversationId,
      text: "",
      sender: "bot",
      created_at: new Date().toISOString(),
      isStreaming: true,
    }
    setMessages((prev) => [...prev, botMsg])

    try {
      // Start streaming request
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
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let accumulatedText = ""

      if (!reader) {
        throw new Error("No reader available")
      }

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        // Decode chunk
        const chunk = decoder.decode(value, { stream: true })

        // Parse SSE format (data: {...}\n\n)
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonData = JSON.parse(line.slice(6))

              if (jsonData.error) {
                throw new Error(jsonData.error)
              }

              // Handle chunks (including empty final chunk)
              if (jsonData.chunk !== undefined) {
                accumulatedText += jsonData.chunk

                // Update message with accumulated text
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === botMsgId
                      ? { ...msg, text: accumulatedText, isStreaming: !jsonData.done }
                      : msg
                  )
                )
              }

              // Handle completion
              if (jsonData.done) {
                // Ensure cursor is removed even if chunk was empty
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === botMsgId
                      ? { ...msg, text: accumulatedText, isStreaming: false }
                      : msg
                  )
                )

                // Save final bot message to database
                if (accumulatedText) {
                  await fetch(`${API_BASE_URL}/chats/${conversationId}/messages/`, {
                    method: "POST",
                    credentials: "include",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ sender: "bot", text: accumulatedText }),
                  })
                }
                break
              }
            } catch (parseErr) {
              console.error("Failed to parse SSE chunk:", parseErr)
            }
          }
        }
      }

      setSelectedTools([])
    } catch (err) {
      const errorText = err instanceof Error ? err.message : String(err)

      // Update message with error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMsgId
            ? { ...msg, text: errorText, isError: true, isStreaming: false }
            : msg
        )
      )
      setError(errorText)
    }
  }, [conversationId, selectedTools, API_BASE_URL])

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return

    const userInput = input.trim()
    setInput("")
    setError("")

    const userMsg: Message = {
      id: uuidv4(),
      conversation_id: conversationId,
      text: userInput,
      sender: "user",
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    setIsLoading(true)

    try {
      await handleStreamingResponse(userInput)
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, conversationId, handleStreamingResponse])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  // Check if we should show "Thinking" indicator
  const shouldShowThinking = isLoading && (
    messages.length === 0 ||
    messages[messages.length - 1]?.sender !== 'bot' ||
    (messages[messages.length - 1]?.sender === 'bot' && !messages[messages.length - 1]?.text)
  )

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-background via-background to-muted/20">
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <AnimatePresence>
            {messages.map((message, index) => (
              <MessageBubble key={message.id} message={message} isLast={index === messages.length - 1} />
            ))}
          </AnimatePresence>
          <AnimatePresence>
            {shouldShowThinking && <TypingIndicator />}
          </AnimatePresence>
          <div ref={endRef} />
        </div>
      </div>
      <div className="border-t border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-4xl mx-auto p-4">
          <motion.div
            layout
            className="relative bg-card border border-border rounded-2xl shadow-lg hover:shadow-xl transition-all duration-200"
          >
            <div className="flex items-end gap-3 p-4">
              <div className="flex-1 relative">
                <Textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={t("type_message") || "Type your message..."}
                  className={cn(
                    "min-h-[44px] max-h-[120px] resize-none border-0 bg-transparent text-card-foreground",
                    "focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60",
                    "scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent",
                  )}
                  style={{ height: inputHeight }}
                  disabled={isLoading}
                />
              </div>
              <Button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                size="icon"
                className={cn(
                  "h-11 w-11 rounded-xl transition-all duration-200",
                  "hover:scale-105 active:scale-95",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                )}
              >
                <motion.div
                  animate={isLoading ? { rotate: 360 } : { rotate: 0 }}
                  transition={{ duration: 1, repeat: isLoading ? Number.POSITIVE_INFINITY : 0 }}
                >
                  <SendIcon className="h-5 w-5" />
                </motion.div>
              </Button>
            </div>
            <div className="px-4 pb-4">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
              >
                <Button
                  variant="ghost"
                  onClick={() => setIsToolDialogOpen(true)}
                  className={cn(
                    "h-9 px-3 rounded-lg border border-dashed border-border",
                    "hover:border-primary/50 hover:bg-primary/5 transition-all duration-200",
                    "group",
                  )}
                >
                  <Settings className="h-4 w-4 mr-2 text-primary group-hover:rotate-90 transition-transform duration-200" />
                  <span className="text-sm text-muted-foreground group-hover:text-primary">
                    {t("tools") || "Tools"}
                  </span>
                  <AnimatePresence>
                    {selectedTools.length > 0 && (
                      <motion.span
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        className="ml-2 bg-primary text-primary-foreground rounded-full px-2 py-0.5 text-xs font-medium"
                      >
                        {selectedTools.length}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </Button>
                <AnimatePresence>
                  {error && (
                    <motion.p
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className="text-sm text-destructive"
                    >
                      {error}
                    </motion.p>
                  )}
                </AnimatePresence>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </div>
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
