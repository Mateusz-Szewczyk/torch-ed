// components/LeftPanel.tsx
'use client';

import { Home, BookOpen, TestTube, Mail } from 'lucide-react'; // Dodano Mail jako ikonę dla Feedback
import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  UserCircle,
  Settings,
  Plus,
  ChevronDown,
  ChevronUp,
  Trash2,
  Edit2,
  MoreVertical,
} from 'lucide-react';
import Link from 'next/link';
import { LoginRegisterDialog } from '@/components/LoginRegisterDialog';
import { SettingsDialog } from '@/components/SettingsDialog';
import ManageFileDialog from '@/components/ManageFileDialog';
import { useTranslation } from 'react-i18next';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import FeedbackModal from '@/components/FeedbackModal'; // Importuj FeedbackModal

interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
}

interface LeftPanelProps {
  userId: string;
  isPanelVisible: boolean;
  setIsPanelVisible: React.Dispatch<React.SetStateAction<boolean>>;
  currentConversationId: number | null;
  setCurrentConversationId: React.Dispatch<React.SetStateAction<number | null>>;
}

export function LeftPanel({
  setCurrentConversationId,
  currentConversationId,
}: LeftPanelProps) {
  const [isPanelVisible, setIsPanelVisible] = useState(true);
  const [isHovered, setIsHovered] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const router = useRouter();
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { t, i18n } = useTranslation();
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

  const userId = 'user-123'; // Zastąp rzeczywistym ID użytkownika z uwierzytelniania

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

  useEffect(() => {
    const handleLanguageChange = () => setCurrentLanguage(i18n.language);
    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  useEffect(() => {
    router.prefetch('/flashcards');
    router.prefetch('/tests'); // Prefetch tests route
    router.prefetch('/'); // Prefetch home route as well
  }, [router]);

  // Fetch conversations from API
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/chats/?user_id=${userId}`);
        if (response.ok) {
          const data = await response.json();
          setConversations(data);
        } else {
          console.error('Failed to fetch conversations:', response.statusText);
        }
      } catch (error) {
        console.error('Error fetching conversations:', error);
      }
    };

    fetchConversations();
  }, [userId, API_BASE_URL]);

  const handleNewConversation = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chats/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      if (response.ok) {
        const newConv = await response.json();
        setConversations((prev) => [...prev, newConv]);
        setCurrentConversationId(newConv.id);
        router.push(`/chat/${newConv.id}`);
      } else {
        console.error('Failed to create conversation:', response.statusText);
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  const handleConversationClick = (conversationId: number) => {
    setCurrentConversationId(conversationId);
    router.push(`/chat/${conversationId}`);
  };

  const handleDeleteConversation = async (conversationId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chats/${conversationId}`, {
        method: 'DELETE',
      });
      if (response.ok || response.status === 204) {
        setConversations((prev) => prev.filter((conv) => conv.id !== conversationId));

        // If deleting the current conversation, redirect to home
        if (conversationId === currentConversationId) {
          setCurrentConversationId(null);
          router.push('/');
        }
      } else {
        console.error('Failed to delete conversation:', response.statusText);
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentEditingConv, setCurrentEditingConv] =
    useState<Conversation | null>(null);
  const [newTitle, setNewTitle] = useState('');

  const openEditDialog = (conv: Conversation) => {
    setCurrentEditingConv(conv);
    setNewTitle(conv.title || '');
    setIsEditDialogOpen(true);
  };

  const handleSaveNewTitle = async () => {
    if (currentEditingConv) {
      try {
        const response = await fetch(
          `${API_BASE_URL}/chats/${currentEditingConv.id}`,
          {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle }),
          }
        );
        if (response.ok) {
          // Update conversation state
          setConversations((prevConversations) =>
            prevConversations.map((conv) =>
              conv.id === currentEditingConv.id
                ? { ...conv, title: newTitle }
                : conv
            )
          );
          setIsEditDialogOpen(false);
        } else {
          console.error('Failed to update conversation:', response.statusText);
        }
      } catch (error) {
        console.error('Error updating conversation:', error);
      }
    }
  };

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] =
    useState<Conversation | null>(null);

  const openDeleteDialog = (conv: Conversation) => {
    setConversationToDelete(conv);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (conversationToDelete) {
      await handleDeleteConversation(conversationToDelete.id);
      setIsDeleteDialogOpen(false);
      setConversationToDelete(null);
    }
  };

  const [menuOpenForConvId, setMenuOpenForConvId] = useState<number | null>(
    null
  );

  const toggleMenuForConv = (convId: number) => {
    setMenuOpenForConvId((prev) => (prev === convId ? null : convId));
  };

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(true), 200);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(false), 200);
    setMenuOpenForConvId(null);
  };

  // Stan do zarządzania modalem feedbacku
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);

  return (
    <div
      className={`bg-card text-foreground border-r border-border transition-all duration-300 z-50 flex flex-col ${
        isPanelVisible ? 'w-64' : 'w-20 items-center'
      }`}
    >
      <div className="p-4 flex-grow flex flex-col">
        {/* Header with Menu and Home Button */}
        <div
          className={`flex items-center mb-4 ${
            isPanelVisible ? 'justify-between' : 'justify-center'
          }`}
        >
          {!isPanelVisible ? (
            // Menu icon when panel is closed - screen reader only
            <h2 className="sr-only">{t('menu')}</h2>
          ) : (
            <h2 className="text-xl font-semibold">{t('menu')}</h2>
          )}
          {/* Home Button */}
          <Button
            asChild
            variant="ghost"
            className={`p-2 rounded-full hover:bg-secondary/80 transition-colors duration-200 ${
              !isPanelVisible ? 'mx-auto' : ''
            }`}
            aria-label={t('home')}
          >
            <Link href="/">
              <Home className="h-6 w-6" />
            </Link>
          </Button>
        </div>

        <div className="space-y-4 flex-1 flex flex-col">
          <ManageFileDialog userId={userId} isPanelVisible={isPanelVisible} />

          <Button
            asChild
            variant="outline"
            className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center'}`}
          >
            <Link href="/flashcards">
              <BookOpen className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">{t('flashcards')}</span>}
            </Link>
          </Button>

          {/* New Tests Button */}
          <Button
            asChild
            variant="outline"
            className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center'}`}
          >
            <Link href="/tests">
              <TestTube className="h-4 w-4" /> {/* Użyj odpowiedniej ikony */}
              {isPanelVisible && <span className="ml-2">{t('tests')}</span>}
            </Link>
          </Button>

          {/* Chat button with conversation list */}
          <div
            className="relative"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            <Collapsible open={isHovered && isPanelVisible}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="outline"
                  className={`w-full group hover:bg-secondary/80 transition-colors duration-200 ${
                    isPanelVisible ? 'justify-start' : 'justify-center'
                  }`}
                >
                  <MessageSquare className="h-4 w-4" />
                  {isPanelVisible && (
                    <>
                      <span className="ml-2 flex-grow text-left">
                        {t('chat')}
                      </span>
                      {isHovered ? (
                        <ChevronUp className="h-4 w-4 transition-transform duration-200 ease-in-out" />
                      ) : (
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 ease-in-out" />
                      )}
                    </>
                  )}
                </Button>
              </CollapsibleTrigger>
              {isPanelVisible && (
                <CollapsibleContent className="mt-2 bg-secondary/50 rounded-md shadow-lg overflow-auto">
                  <div className="p-2 space-y-2">
                    <Button
                      className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
                      onClick={handleNewConversation}
                    >
                      <Plus className="h-4 w-4" />
                      {t('new_conversation')}
                    </Button>
                    {conversations.map((conv) => (
                      <div key={conv.id} className="relative flex items-center w-full overflow-hidden">
                        <Button
                          variant="ghost"
                          className="flex-grow justify-start text-sm hover:bg-secondary/80 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap truncate"
                          onClick={() => handleConversationClick(conv.id)}
                          title={conv.title || t('conversation')} // Tooltip with full name
                        >
                          {conv.title || `${t('conversation')}`}
                        </Button>
                        <Button
                          variant="ghost"
                          className="text-gray-500 hover:bg-secondary/80 transition-colors duration-200"
                          onClick={() => toggleMenuForConv(conv.id)}
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                        {menuOpenForConvId === conv.id && (
                          <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-md shadow-lg z-50">
                            <Button
                              variant="ghost"
                              className="w-full justify-start text-sm hover:bg-secondary/80 transition-colors duration-200"
                              onClick={() => {
                                openEditDialog(conv);
                                setMenuOpenForConvId(null);
                              }}
                            >
                              <Edit2 className="h-4 w-4 mr-2" />
                              {t('edit_title')}
                            </Button>
                            <Button
                              variant="ghost"
                              className="w-full justify-start text-sm text-red-500 hover:bg-secondary/80 transition-colors duration-200"
                              onClick={() => {
                                openDeleteDialog(conv);
                                setMenuOpenForConvId(null);
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t('delete_conversation')}
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CollapsibleContent>
              )}
            </Collapsible>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Dodany Przycisk Feedbacku - Umieszczony niżej */}
          <Button
            onClick={() => setIsFeedbackOpen(true)}
            variant="outline"
            className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center'}`}
          >
            <Mail className="h-4 w-4" />
            {isPanelVisible && <span className="ml-2">{t('send_feedback')}</span>}
          </Button>

          {/* Sekcja Logowania/Rejestracji i Ustawień */}
          <div className="space-y-2 mt-4">
            <LoginRegisterDialog>
              <Button
                variant="outline"
                className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${
                  isPanelVisible ? 'justify-start' : 'justify-center'
                }`}
              >
                <UserCircle className="h-4 w-4" />
                {isPanelVisible && (
                  <span className="ml-2">{t('login_register')}</span>
                )}
              </Button>
            </LoginRegisterDialog>
            <SettingsDialog>
              <Button
                variant="outline"
                className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${
                  isPanelVisible ? 'justify-start' : 'justify-center'
                }`}
              >
                <Settings className="h-4 w-4" />
                {isPanelVisible && (
                  <span className="ml-2">{t('settings')}</span>
                )}
              </Button>
            </SettingsDialog>
          </div>
        </div>

        {/* Toggle panel button */}
        <Button
          variant="ghost"
          className={`mb-4 hover:bg-secondary/80 transition-colors duration-200 ${
            isPanelVisible ? 'self-end mr-2' : 'mx-auto'
          }`}
          onClick={() => setIsPanelVisible(!isPanelVisible)}
          aria-label={isPanelVisible ? t('hide_panel') : t('show_panel')}
        >
          {isPanelVisible ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>

        {/* Edit Conversation Title Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('edit_conversation_title')}</DialogTitle>
            </DialogHeader>
            <Input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder={t('enter_new_title')}
              className="mt-2"
            />
            <DialogFooter>
              <Button
                variant="secondary"
                onClick={() => setIsEditDialogOpen(false)}
              >
                {t('cancel')}
              </Button>
              <Button variant="primary" onClick={handleSaveNewTitle}>
                {t('save')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Conversation Confirmation Dialog */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('confirm_delete_title')}</DialogTitle>
              <DialogDescription>
                {t('confirm_delete_description')}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="secondary"
                onClick={() => setIsDeleteDialogOpen(false)}
              >
                {t('cancel')}
              </Button>
              <Button variant="destructive" onClick={handleConfirmDelete}>
                {t('delete')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Feedback Modal */}
        <FeedbackModal isOpen={isFeedbackOpen} onClose={() => setIsFeedbackOpen(false)} />
      </div>
    </div>
  );
}
