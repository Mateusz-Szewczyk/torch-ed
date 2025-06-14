"use client"

import type React from "react"
import { useState } from "react"
import { Plus, Edit2, Trash2, MoreVertical, ChevronDown, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import {router} from "next/client";
import {t} from "i18next";

interface Conversation {
  id: number
  title: string | null
  created_at: string
}

interface ConversationListProps {
  conversations: Conversation[]
  onConversationClick: (id: number) => void
  onNewConversation: () => void
  AI_API_BASE_URL: string
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>
  setCurrentConversationId: (id: number | null) => void
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  onConversationClick,
  onNewConversation,
  AI_API_BASE_URL,
  setConversations,
  setCurrentConversationId
}) => {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [currentEditingConv, setCurrentEditingConv] = useState<Conversation | null>(null)
  const [conversationToDelete, setConversationToDelete] = useState<Conversation | null>(null)
  const [newTitle, setNewTitle] = useState("")

  // Open edit dialog
  const openEditDialog = (conv: Conversation) => {
    setCurrentEditingConv(conv)
    setNewTitle(conv.title || "")
    setIsEditDialogOpen(true)
  }

  // Save edited title
  const handleSaveNewTitle = async () => {
    if (!currentEditingConv) return
    try {
      const resp = await fetch(`${AI_API_BASE_URL}/chats/${currentEditingConv.id}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      })
      if (resp.ok) {
        setConversations((prev) => prev.map((c) => (c.id === currentEditingConv.id ? { ...c, title: newTitle } : c)))
      } else {
        console.error("Failed to update conversation:", resp.statusText)
      }
    } catch (err: unknown) {
      console.error("Error updating conversation:", err)
    }
    setIsEditDialogOpen(false)
  }

  // Open delete dialog
  const openDeleteDialog = (conv: Conversation) => {
    setConversationToDelete(conv)
    setIsDeleteDialogOpen(true)
  }

  // Confirm delete
  const handleConfirmDelete = async () => {
    if (!conversationToDelete) return
    try {
      const resp = await fetch(`${AI_API_BASE_URL}/chats/${conversationToDelete.id}`, {
        method: "DELETE",
        credentials: "include",
      })
      if (resp.ok || resp.status === 204) {
        setConversations((prev) => prev.filter((c) => c.id !== conversationToDelete.id))
        setCurrentConversationId(null)
        router.push("/")
      } else {
        console.error("Failed to delete conversation:", resp.statusText)
      }
    } catch (err: unknown) {
      console.error("Error deleting conversation:", err)
    }
    setIsDeleteDialogOpen(false)
    setConversationToDelete(null)
  }

  return (
    <div
      className="w-full max-w-full overflow-hidden box-border"
      id="conversations-section"
    >
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full flex items-center justify-between px-2 mb-1 hover:bg-secondary/50 transition-colors"
          >
            <span className="font-medium">{t("chat_history")}</span>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent className="space-y-2">
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start gap-2 text-primary hover:text-primary hover:bg-primary/5"
            onClick={onNewConversation}
          >
            <Plus className="h-4 w-4" />
            {t("new_conversation")}
          </Button>

          <ScrollArea className="h-[calc(100vh-350px)] pr-2 w-full max-w-full overflow-hidden">
            <div className="space-y-1 py-1 w-full max-w-full box-border">
              {conversations.length === 0 ? (
                <p className="text-sm text-muted-foreground px-2 py-2 text-center italic">{t("no_conversations")}</p>
              ) : (
                conversations.map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    conversation={conv}
                    onClick={() => onConversationClick(conv.id)}
                    onEdit={() => openEditDialog(conv)}
                    onDelete={() => openDeleteDialog(conv)}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        </CollapsibleContent>
      </Collapsible>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("edit_conversation_title")}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <label htmlFor="title" className="text-sm font-medium">
                {t("new_title")}
              </label>
              <input
                id="title"
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder={t("enter_new_title")}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              {t("cancel")}
            </Button>
            <Button onClick={handleSaveNewTitle}>{t("save")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("confirm_delete_title")}</DialogTitle>
            <DialogDescription>{t("confirm_delete_description")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              {t("cancel")}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              {t("delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

interface ConversationItemProps {
  conversation: Conversation
  onClick: () => void
  onEdit: () => void
  onDelete: () => void
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  onClick,
  onEdit,
  onDelete
}) => {
  return (
    <div className="group flex items-center rounded-md hover:bg-secondary/50 transition-colors w-full max-w-full min-w-0 overflow-hidden box-border">
      <Button
        variant="ghost"
        size="sm"
        className="flex-1 justify-start text-sm py-1 px-2 h-8 min-w-0 overflow-hidden"
        onClick={onClick}
      >
        <span className="truncate block max-w-full">
          {conversation.title || "Untitled"}
        </span>
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 flex-shrink-0 min-w-[28px] max-w-[28px]"
          >
            <MoreVertical className="h-4 w-4" />
            <span className="sr-only">Options</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onClick={onEdit}>
            <Edit2 className="h-4 w-4 mr-2" />
            <span>{t("edit_title")}</span>
          </DropdownMenuItem>
          <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={onDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            <span>{t("delete")}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
