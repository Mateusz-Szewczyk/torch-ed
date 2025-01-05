'use client';

import {
  Home, BookOpen, TestTube, Mail, MoreVertical,
  MessageSquare, ChevronLeft, ChevronRight,
  UserCircle, Settings, Plus, ChevronDown, ChevronUp, Edit2, Trash2
} from 'lucide-react';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
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
import FeedbackModal from '@/components/FeedbackModal';

interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
}

interface LeftPanelProps {
  isAuthenticated: boolean;
  setIsAuthenticated: (val: boolean) => void;

  isPanelVisible: boolean;
  setIsPanelVisible: React.Dispatch<React.SetStateAction<boolean>>;
  currentConversationId: number | null;
  setCurrentConversationId: React.Dispatch<React.SetStateAction<number | null>>;
}

export function LeftPanel({
  isAuthenticated,
  setIsAuthenticated,
  isPanelVisible,
  setIsPanelVisible,
  setCurrentConversationId,
}: LeftPanelProps) {

  // States from your existing code
  const [isHovered, setIsHovered] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const router = useRouter();
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { t, i18n } = useTranslation();
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // API endpoints
  const AI_API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';
  const BE_API_BASE_URL = 'http://localhost:14440/api/v1/auth';

  // ----------------
  // (1) 3-dots menu states
  // ----------------
  const [menuOpenForConvId, setMenuOpenForConvId] = useState<number | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const collapsibleContainerRef = useRef<HTMLDivElement | null>(null);
  const conversationButtonRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  // Toggle small menu for a conversation
  const toggleMenuForConv = (convId: number) => {
    if (menuOpenForConvId === convId) {
      // Close if already open
      setMenuOpenForConvId(null);
      return;
    }
    const btnEl = conversationButtonRefs.current[convId];
    const containerEl = collapsibleContainerRef.current;
    if (btnEl && containerEl) {
      const containerRect = containerEl.getBoundingClientRect();
      const btnRect = btnEl.getBoundingClientRect();

      const top = btnRect.bottom - containerRect.top + 4;
      const left = btnRect.left - containerRect.left - 120;
      setMenuPosition({ top, left });
    }
    setMenuOpenForConvId(convId);
  };

  // ----------------
  // (2) Edit dialog states
  // ----------------
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentEditingConv, setCurrentEditingConv] = useState<Conversation | null>(null);
  const [newTitle, setNewTitle] = useState('');

  // Opens edit dialog
  const openEditDialog = (conv: Conversation) => {
    setCurrentEditingConv(conv);
    setNewTitle(conv.title || '');
    setIsEditDialogOpen(true);
  };

  // Saves new conversation title
  const handleSaveNewTitle = async () => {
    if (!currentEditingConv) return;
    try {
      // PATCH /chats/:id
      const resp = await fetch(`${AI_API_BASE_URL}/chats/${currentEditingConv.id}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });
      if (resp.ok) {
        // Update local state
        setConversations((prev) =>
          prev.map((c) => (c.id === currentEditingConv.id ? { ...c, title: newTitle } : c))
        );
      } else {
        console.error('Failed to update conversation:', resp.statusText);
      }
    } catch (err) {
      console.error('Error updating conversation:', err);
    }
    setIsEditDialogOpen(false);
  };

  // ----------------
  // (3) Delete dialog states
  // ----------------
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<Conversation | null>(null);

  // Opens delete confirm
  const openDeleteDialog = (conv: Conversation) => {
    setConversationToDelete(conv);
    setIsDeleteDialogOpen(true);
  };

  // Confirms delete
  const handleConfirmDelete = async () => {
    if (!conversationToDelete) return;
    try {
      // DELETE /chats/:id
      const resp = await fetch(`${AI_API_BASE_URL}/chats/${conversationToDelete.id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (resp.ok || resp.status === 204) {
        // Remove from local list
        setConversations((prev) => prev.filter((c) => c.id !== conversationToDelete.id));
        setCurrentConversationId(null);
        router.push('/');
      } else {
        console.error('Failed to delete conversation:', resp.statusText);
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
    setIsDeleteDialogOpen(false);
    setConversationToDelete(null);
  };

  // Sync language changes
  useEffect(() => {
    const handleLanguageChange = () => setCurrentLanguage(i18n.language);
    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  // Prefetch routes (optional)
  useEffect(() => {
    router.prefetch('/flashcards');
    router.prefetch('/tests');
    router.prefetch('/');
  }, [router]);

  // (4) Fetch conversations if logged in
  useEffect(() => {
    if (!isAuthenticated) return;
    const fetchConversations = async () => {
      try {
        const response = await fetch(`${AI_API_BASE_URL}/chats/`, {
          credentials: 'include',
        });
        if (response.ok) {
          const data: Conversation[] = await response.json();
          setConversations(data);
        } else {
          console.error('Failed to fetch conversations:', response.statusText);
        }
      } catch (error) {
        console.error('Error fetching conversations:', error);
      }
    };
    fetchConversations();
  }, [AI_API_BASE_URL, isAuthenticated]);

  // Create conversation
  const handleNewConversation = async () => {
    try {
      const response = await fetch(`${AI_API_BASE_URL}/chats/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const newConv: Conversation = await response.json();
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

  // Go to conversation
  const handleConversationClick = (conversationId: number) => {
    setCurrentConversationId(conversationId);
    router.push(`/chat/${conversationId}`);
  };

  // Hover logic
  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(true), 200);
  };
  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(false), 200);
    // Also close the menu
    setMenuOpenForConvId(null);
  };

  // Logout
  const handleLogout = async () => {
    try {
      // NOTE: changed from `http://localhost:8043/api/v1/auth/logout` to `BE_API_BASE_URL + '/logout'`
      const res = await fetch(`${BE_API_BASE_URL}/logout`, {
        method: 'GET',
        credentials: 'include',
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Logout failed');
      }
      setIsProfileOpen(false);
      setIsAuthenticated(false);
      router.push('/');
    } catch (err) {
      console.error('Error logging out:', err);
      alert('Nie udało się wylogować: ' + String(err));
    }
  };

  return (
    <div
      className={`bg-card text-foreground border-r border-border transition-all duration-300 z-20 flex flex-col ${
        isPanelVisible ? 'w-64' : 'w-20 items-center'
      } relative`}
    >
      <div className="p-4 flex-grow flex flex-col">
        {/* Header: Home */}
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

        {/* Main content / navigation (spaced out) */}
        <div className="flex flex-col space-y-4 flex-1">
          {isAuthenticated && (
            <>
              <ManageFileDialog userId="unused" isPanelVisible={isPanelVisible} />

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

              {/* Chat Collapsible */}
              <div
                className="relative scroll-thin"
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
                    <CollapsibleContent
                      ref={collapsibleContainerRef}
                      className="relative mt-2 bg-secondary/50 rounded-md shadow-lg overflow-visible p-2"
                    >
                      <Button
                        className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
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
                            title={conv.title || t('conversation')}
                          >
                            {conv.title || t('conversation')}
                          </Button>

                          {/* 3-dots button */}
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

                      {/* The small context menu for Edit/Delete */}
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
                              const conv = conversations.find((c) => c.id === menuOpenForConvId);
                              if (conv) openEditDialog(conv);
                              setMenuOpenForConvId(null);
                            }}
                          >
                            <Edit2 className="h-4 w-4 mr-2" />
                            {t('edit_title') || 'Edit Title'}
                          </Button>
                          <Button
                            variant="ghost"
                            className="w-full justify-start text-sm text-red-500 hover:bg-secondary/80 transition-colors duration-200"
                            onClick={() => {
                              const conv = conversations.find((c) => c.id === menuOpenForConvId);
                              if (conv) openDeleteDialog(conv);
                              setMenuOpenForConvId(null);
                            }}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            {t('delete_conversation') || 'Delete'}
                          </Button>
                        </div>
                      )}
                    </CollapsibleContent>
                  )}
                </Collapsible>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Bottom area (pinned to bottom) */}
      <div className="flex flex-col space-y-4 p-4">
        <Button
          onClick={() => setIsFeedbackOpen(true)}
          variant="outline"
          className={`w-full 
                      ${isPanelVisible ? 'justify-start' : 'justify-center'}
                      animate-pulseButton`}
        >
          <Mail className="h-4 w-4" />
          {isPanelVisible && <span className="ml-2">{t('send_feedback')}</span>}
        </Button>

        {!isAuthenticated && (
          <LoginRegisterDialog setIsAuthenticated={setIsAuthenticated}>
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
        )}

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

        {isAuthenticated && (
          <Button
            variant="outline"
            onClick={() => setIsProfileOpen(true)}
            className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${
              isPanelVisible ? 'justify-start' : 'justify-center'
            }`}
          >
            <UserCircle className="h-4 w-4" />
            {isPanelVisible && <span className="ml-2">Mój profil</span>}
          </Button>
        )}
      </div>

      <Button
        variant="ghost"
        className={`border-r-2 absolute top-1/2 transform -translate-y-1/2 right-0 translate-x-1/3 hover:bg-secondary/80 transition-colors duration-200 rounded-full w-6 h-6 shadow-lg bg-card`}
        onClick={() => setIsPanelVisible(!isPanelVisible)}
        aria-label={isPanelVisible ? t('hide_panel') : t('show_panel')}
      >
        {isPanelVisible ? (
          <ChevronLeft className="h-5 w-5" />
        ) : (
          <ChevronRight className="h-5 w-5" />
        )}
      </Button>

      {/* Feedback Modal */}
      <FeedbackModal isOpen={isFeedbackOpen} onClose={() => setIsFeedbackOpen(false)} />

      {/* Dialog: Mój profil */}
      <Dialog open={isProfileOpen} onOpenChange={setIsProfileOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mój profil</DialogTitle>
            <DialogDescription>Tutaj można dodać info o userze, itd.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="destructive"
              onClick={async () => {
                try {
                  // FIX: use BE_API_BASE_URL for logout
                  const res = await fetch(`${BE_API_BASE_URL}/logout`, {
                    method: 'GET',
                    credentials: 'include',
                  });
                  if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.error || 'Logout failed');
                  }
                  setIsProfileOpen(false);
                  setIsAuthenticated(false);
                  router.push('/');
                } catch (err) {
                  console.error('Error logging out:', err);
                  alert('Nie udało się wylogować: ' + String(err));
                }
              }}
            >
              Wyloguj
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Edit conversation title */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('edit_conversation_title') || 'Edit Title'}</DialogTitle>
          </DialogHeader>
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder={t('enter_new_title') || 'New title...'}
            className="mt-2 w-full border border-gray-300 px-3 py-2 rounded"
          />
          <DialogFooter>
            <Button variant="secondary" onClick={() => setIsEditDialogOpen(false)}>
              {t('cancel') || 'Cancel'}
            </Button>
            <Button variant="primary" onClick={handleSaveNewTitle}>
              {t('save') || 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Delete conversation */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('confirm_delete_title') || 'Confirm Delete'}</DialogTitle>
            <DialogDescription>
              {t('confirm_delete_description') || 'Are you sure you want to delete?'}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setIsDeleteDialogOpen(false)}>
              {t('cancel') || 'Cancel'}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              {t('delete') || 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
