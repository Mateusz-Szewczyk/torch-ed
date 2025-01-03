'use client';

import { Home, BookOpen, TestTube, Mail } from 'lucide-react';
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
import FeedbackModal from '@/components/FeedbackModal';

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

  const userId = 'user-123'; // Przykładowe ID (zastąp realnym)
  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

  // ---------------
  // FETCH & PREFETCH
  // ---------------
  useEffect(() => {
    const handleLanguageChange = () => setCurrentLanguage(i18n.language);
    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  useEffect(() => {
    router.prefetch('/flashcards');
    router.prefetch('/tests');
    router.prefetch('/');
  }, [router]);

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
  }, [API_BASE_URL, userId]);

  // ---------------
  // HANDLERS: NEW, CLICK, DELETE
  // ---------------
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
        setConversations((prev) => prev.filter((c) => c.id !== conversationId));
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

  // ---------------
  // EDIT TITLE
  // ---------------
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
          setConversations((prev) =>
            prev.map((c) =>
              c.id === currentEditingConv.id ? { ...c, title: newTitle } : c
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

  // ---------------
  // DELETE CONFIRM
  // ---------------
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

  // ---------------
  // MENU
  // ---------------
  const [menuOpenForConvId, setMenuOpenForConvId] = useState<number | null>(null);

  // Kontener "CollapsibleContent" – tam będzie `position: relative`.
  const collapsibleContainerRef = useRef<HTMLDivElement | null>(null);

  // Stan do przechowywania pozycji menu (top, left) w px
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(
    null
  );

  // Refy do przycisków "trzech kropek"
  const conversationButtonRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  const toggleMenuForConv = (convId: number) => {
    if (menuOpenForConvId === convId) {
      // Zamknij, jeśli było otwarte
      setMenuOpenForConvId(null);
      return;
    }

    // Znajdź przycisk i kontener
    const btnEl = conversationButtonRefs.current[convId];
    const containerEl = collapsibleContainerRef.current;
    if (btnEl && containerEl) {
      // boundingRect kontenera
      const containerRect = containerEl.getBoundingClientRect();
      // boundingRect przycisku
      const btnRect = btnEl.getBoundingClientRect();

      // Oblicz offset przycisku względem kontenera "relative"
      const top = btnRect.bottom - containerRect.top + 4; // +4px odstępu
      const left = btnRect.left - containerRect.left - 120; // 120 - przybliżona szerokość menu

      setMenuPosition({ top, left });
    }

    setMenuOpenForConvId(convId);
  };

  // ---------------
  // HOVER MENU
  // ---------------
  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(true), 200);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(false), 200);
    setMenuOpenForConvId(null);
  };

  // ---------------
  // FEEDBACK
  // ---------------
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);

  // ---------------
  // RENDER
  // ---------------
  return (
    <div
      className={`bg-card text-foreground border-r border-border transition-all duration-300 z-50 flex flex-col ${
        isPanelVisible ? 'w-64' : 'w-20 items-center'
      }`}
    >
      <div className="p-4 flex-grow flex flex-col">
        {/* Header z Home */}
        <div
          className={`flex items-center mb-4 ${
            isPanelVisible ? 'justify-between' : 'justify-center'
          }`}
        >
          {!isPanelVisible ? (
            <h2 className="sr-only">{t('menu')}</h2>
          ) : (
            <h2 className="text-xl font-semibold">{t('menu')}</h2>
          )}
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

          <Button
            asChild
            variant="outline"
            className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center'}`}
          >
            <Link href="/tests">
              <TestTube className="h-4 w-4" />
              {isPanelVisible && <span className="ml-2">{t('tests')}</span>}
            </Link>
          </Button>

          {/* Chat – lista konwersacji */}
          <div
            className="relative scroll-thin"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            <Collapsible open={isHovered && isPanelVisible} className="scroll-thin">
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
                      <span className="ml-2 flex-grow text-left">{t('chat')}</span>
                      {isHovered ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </>
                  )}
                </Button>
              </CollapsibleTrigger>

              {isPanelVisible && (
                /**
                 * 1) Ten rodzic jest "relative overflow-visible"
                 *    aby menu mogło wyjść poza wiersze.
                 */
                <CollapsibleContent
                  ref={collapsibleContainerRef}
                  className="relative mt-2 bg-secondary/50 rounded-md shadow-lg overflow-visible p-2"
                >
                  <div className="space-y-2 overflow-auto max-h-64">
                    <Button
                      className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
                      onClick={handleNewConversation}
                    >
                      <Plus className="h-4 w-4" />
                      {t('new_conversation')}
                    </Button>

                    {conversations.map((conv) => (
                      <div
                        key={conv.id}
                        className="relative flex items-center w-full overflow-hidden"
                      >
                        {/* Przycisk wiersza konwersacji */}
                        <Button
                          variant="ghost"
                          className="flex-grow justify-start text-sm hover:bg-secondary/80 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap truncate"
                          onClick={() => handleConversationClick(conv.id)}
                          title={conv.title || t('conversation')}
                        >
                          {conv.title || `${t('conversation')}`}
                        </Button>

                        {/* Przycisk trzech kropek */}
                        <Button
                          variant="ghost"
                          className="text-gray-500 hover:bg-secondary/80 transition-colors duration-200"
                          onClick={() => toggleMenuForConv(conv.id)}
                          ref={(el) => (conversationButtonRefs.current[conv.id] = el)}
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>

                  {/**
                   * 3) Menu jest w tym samym CollapsibleContent
                   * (a nie w wierszu rozmowy)
                   * i jest absolutnie pozycjonowane.
                   */}
                  {menuOpenForConvId !== null && menuPosition && (
                    <div
                      className="z-50 w-48 bg-card border border-border rounded-md shadow-lg p-1"
                      style={{
                        position: 'absolute',
                        top: menuPosition.top,
                        left: menuPosition.left,
                      }}
                    >
                      <Button
                        variant="ghost"
                        className="w-full justify-start text-sm hover:bg-secondary/80 transition-colors duration-200"
                        onClick={() => {
                          const conv = conversations.find(
                            (c) => c.id === menuOpenForConvId
                          );
                          if (conv) {
                            openEditDialog(conv);
                          }
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
                          const conv = conversations.find(
                            (c) => c.id === menuOpenForConvId
                          );
                          if (conv) {
                            openDeleteDialog(conv);
                          }
                          setMenuOpenForConvId(null);
                        }}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        {t('delete_conversation')}
                      </Button>
                    </div>
                  )}
                </CollapsibleContent>
              )}
            </Collapsible>
          </div>

          <div className="flex-1" />

          <Button
            onClick={() => setIsFeedbackOpen(true)}
            variant="outline"
            className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center'}`}
          >
            <Mail className="h-4 w-4" />
            {isPanelVisible && <span className="ml-2">{t('send_feedback')}</span>}
          </Button>

          <div className="space-y-2 mt-4">
            <LoginRegisterDialog>
              <Button
                variant="outline"
                className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${
                  isPanelVisible ? 'justify-start' : 'justify-center'
                }`}
              >
                <UserCircle className="h-4 w-4" />
                {isPanelVisible && <span className="ml-2">{t('login_register')}</span>}
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
                {isPanelVisible && <span className="ml-2">{t('settings')}</span>}
              </Button>
            </SettingsDialog>
          </div>
        </div>

        {/* Przycisk do zwijania panelu */}
        <Button
          variant="ghost"
          className={`mb-4 hover:bg-secondary/80 transition-colors duration-200 overflow-visible ${
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

        {/* Dialog: Edycja tytułu */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('edit_conversation_title')}</DialogTitle>
            </DialogHeader>
            <Input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder={t('enter_new_title') || ''}
              className="mt-2"
            />
            <DialogFooter>
              <Button variant="secondary" onClick={() => setIsEditDialogOpen(false)}>
                {t('cancel')}
              </Button>
              <Button variant="primary" onClick={handleSaveNewTitle}>
                {t('save')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog: Usuwanie konwersacji */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('confirm_delete_title')}</DialogTitle>
              <DialogDescription>{t('confirm_delete_description')}</DialogDescription>
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
