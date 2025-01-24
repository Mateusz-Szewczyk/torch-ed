// src/components/LeftPanel.tsx

'use client';

import React, { useState, useEffect, useRef, useContext } from 'react';
import {
  Home,
  BookOpen,
  TestTube,
  Mail,
  MoreVertical,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  UserCircle,
  Settings,
  Plus,
  ChevronDown,
  ChevronUp,
  Edit2,
  Trash2,
} from 'lucide-react';
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
import { ConversationContext } from "@/contexts/ConversationContext";
import { AuthContext } from '@/contexts/AuthContext'; // Import AuthContext

interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
}

interface LeftPanelProps {
  isPanelVisible: boolean;
  isMobile: boolean;
  togglePanel: () => void;
}

const LeftPanel: React.FC<LeftPanelProps> = ({ isPanelVisible, isMobile, togglePanel }) => {
  const {isAuthenticated, setIsAuthenticated} = useContext(AuthContext); // Using AuthContext
  const [isHovered, setIsHovered] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const router = useRouter();
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const {t, i18n} = useTranslation();
  const {setCurrentConversationId} = useContext(ConversationContext); // Get setCurrentConversationId
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const FLASK_API_BASE_URL =
      process.env.NEXT_PUBLIC_API_FLASK_URL || 'http://localhost:14440/api/v1/auth';

  const AI_API_BASE_URL =
      process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';
  const BE_API_BASE_URL =
      `${FLASK_API_BASE_URL}/auth` || 'http://localhost:14440/api/v1/auth';

  const [menuOpenForConvId, setMenuOpenForConvId] = useState<number | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const collapsibleContainerRef = useRef<HTMLDivElement | null>(null);
  const conversationButtonRefs = useRef<Record<number, HTMLButtonElement | null>>({});

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentEditingConv, setCurrentEditingConv] = useState<Conversation | null>(null);
  const [newTitle, setNewTitle] = useState('');

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<Conversation | null>(null);

  // Handle language change
  useEffect(() => {
    const handleLanguageChange = (lng: string) => {
      console.log('Language changed to:', lng);
    };
    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  // Prefetch routes
  useEffect(() => {
    router.prefetch('/flashcards');
    router.prefetch('/tests');
    router.prefetch('/');
  }, [router]);

  // Fetch conversations if authenticated
  useEffect(() => {
    if (!isAuthenticated) return;
    const fetchConversations = async () => {
      try {
        const response = await fetch(`${AI_API_BASE_URL}/chats/`, {
          credentials: 'include',
          headers: {Authorization: 'TorchED_AUTH'}, // Ensure headers are correct
        });
        if (response.ok) {
          const data: Conversation[] = await response.json();
          setConversations(data);
        } else {
          console.error('Failed to fetch conversations:', response.statusText);
        }
      } catch (error: unknown) {
        console.error('Error fetching conversations:', error);
      }
    };
    fetchConversations();
  }, [AI_API_BASE_URL, isAuthenticated]);

  // Toggle menu for conversation
  const toggleMenuForConv = (convId: number) => {
    if (menuOpenForConvId === convId) {
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
      setMenuPosition({top, left});
    }
    setMenuOpenForConvId(convId);
  };

  // Open edit dialog
  const openEditDialog = (conv: Conversation) => {
    setCurrentEditingConv(conv);
    setNewTitle(conv.title || '');
    setIsEditDialogOpen(true);
  };

  // Save new title
  const handleSaveNewTitle = async () => {
    if (!currentEditingConv) return;
    try {
      // Log request details for debugging
      console.log('Request URL:', `${AI_API_BASE_URL}/chats/${currentEditingConv.id}`);
      console.log('Available cookies:', document.cookie);

      const resp = await fetch(`${AI_API_BASE_URL}/chats/${currentEditingConv.id}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: newTitle}),
      });

      // Log response details for debugging
      console.log('Response status:', resp.status);
      console.log('Response status text:', resp.statusText);

      if (resp.ok) {
        setConversations((prev) =>
            prev.map((c) => (c.id === currentEditingConv.id ? {...c, title: newTitle} : c))
        );
      } else {
        console.error('Failed to update conversation:', resp.statusText);
      }
    } catch (err: unknown) {
      console.error('Error updating conversation:', err);
    }
    setIsEditDialogOpen(false);
  };

  // Open delete dialog
  const openDeleteDialog = (conv: Conversation) => {
    setConversationToDelete(conv);
    setIsDeleteDialogOpen(true);
  };

  // Confirm delete
  const handleConfirmDelete = async () => {
    if (!conversationToDelete) return;
    try {
      const resp = await fetch(`${AI_API_BASE_URL}/chats/${conversationToDelete.id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (resp.ok || resp.status === 204) {
        setConversations((prev) => prev.filter((c) => c.id !== conversationToDelete.id));
        setCurrentConversationId(null);
        router.push('/');
      } else {
        console.error('Failed to delete conversation:', resp.statusText);
      }
    } catch (err: unknown) {
      console.error('Error deleting conversation:', err);
    }
    setIsDeleteDialogOpen(false);
    setConversationToDelete(null);
  };

  // Handle new conversation
  const handleNewConversation = async () => {
    try {
      // Log request details for debugging
      console.log('New conversation Request URL:', `${AI_API_BASE_URL}/chats/`);
      console.log('Available cookies:', document.cookie);

      const response = await fetch(`${AI_API_BASE_URL}/chats/`, {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
      });

      // Log response details for debugging
      console.log('New conversation Response status:', response.status);
      console.log('New conversation Response status text:', response.statusText);

      if (response.ok) {
        const newConv: Conversation = await response.json();
        console.log('New conversation created:', newConv);
        setConversations((prev) => [...prev, newConv]);
        setCurrentConversationId(newConv.id);
        router.push(`/chat`);
      } else {
        console.error('Failed to create conversation:', response.statusText);
      }
    } catch (error: unknown) {
      console.error('Error creating conversation:', error);
    }
  };

  // Handle conversation click
  const handleConversationClick = (conversationId: number) => {
    console.log(`Setting currentConversationId to: ${conversationId}`);
    setCurrentConversationId(conversationId);
    router.push(`/chat`);
  };

  // Handle mouse enter and leave for chat collapsible
  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(true), 200);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => setIsHovered(false), 200);
    setMenuOpenForConvId(null);
  };

  return (
      <div>
        <div
            className={`
          fixed top-0 left-0 h-full bg-card text-foreground border-r border-border
          transition-all duration-300 z-50 flex flex-col
          ${isMobile ? (isPanelVisible ? 'w-64' : 'w-0') : isPanelVisible ? 'w-64' : 'w-16'}
          ${isMobile && !isPanelVisible ? 'overflow-hidden' : ''}
        `}
        >
          {(!isMobile || isPanelVisible) && (
              <>
                <div className="p-4 flex-grow flex flex-col overflow-y-auto">
                  <div className="flex items-center mb-4 justify-between">
                    <h2 className={`font-semibold ${isPanelVisible ? 'text-xl' : 'w-0 opacity-0 -z-20'}`}>
                      {t('menu')}
                    </h2>
                    <Button
                        asChild
                        variant="ghost"
                        className="p-2 rounded-full hover:bg-secondary/80 transition-colors duration-200"
                        aria-label={t('home')}
                    >
                      <Link href="/">
                        <Home className="h-6 w-6"/>
                      </Link>
                    </Button>
                  </div>

                  <div className="flex flex-col space-y-4 items-center">
                    {isAuthenticated && (
                        <>
                          <ManageFileDialog isPanelVisible={isPanelVisible}/>

                          <Button
                              asChild
                              variant="outline"
                              className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center items-center'}`}
                          >
                            <Link href="/flashcards">
                              <BookOpen className="h-4 w-4"/>
                              {isPanelVisible && <span className="ml-2">{t('flashcards')}</span>}
                            </Link>
                          </Button>

                          <Button
                              asChild
                              variant="outline"
                              className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center items-center'}`}
                          >
                            <Link href="/tests">
                              <TestTube className="h-4 w-4"/>
                              {isPanelVisible && <span className="ml-2">{t('tests')}</span>}
                            </Link>
                          </Button>

                          <div
                              className="relative scroll-thin w-full"
                              onMouseEnter={handleMouseEnter}
                              onMouseLeave={handleMouseLeave}
                          >
                            <Collapsible open={isHovered}>
                              <CollapsibleTrigger asChild>
                                <Button
                                    variant="outline"
                                    className={`w-full flex items-center ${isPanelVisible ? 'justify-start' : 'justify-center'}`}
                                >
                                  <MessageSquare className="h-4 w-4"/>
                                  {isPanelVisible && (
                                      <>
                                        <span className="ml-2 text-left">{t('chat')}</span>
                                        {isHovered ? (
                                            <ChevronUp className="h-4 w-4 ml-auto"/>
                                        ) : (
                                            <ChevronDown className="h-4 w-4 ml-auto"/>
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
                                      <Plus className="h-4 w-4"/>
                                      {t('new_conversation')}
                                    </Button>

                                    {conversations.map((conv) => (
                                        <div key={conv.id}
                                             className="relative flex items-center w-full overflow-hidden">
                                          <Button
                                              variant="ghost"
                                              className="flex-grow justify-start text-sm hover:bg-secondary/80 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap truncate"
                                              onClick={() => handleConversationClick(conv.id)}
                                              title={conv.title || t('conversation')}
                                          >
                                            {conv.title || t('conversation')}
                                          </Button>

                                          <Button
                                              variant="ghost"
                                              className="text-gray-500 hover:bg-secondary/80 transition-colors duration-200"
                                              onClick={() => toggleMenuForConv(conv.id)}
                                              ref={(el) => {
                                                conversationButtonRefs.current[conv.id] = el;
                                              }}
                                          >
                                            <MoreVertical className="h-4 w-4"/>
                                          </Button>
                                        </div>
                                    ))}

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
                                              className="w-full justify-start text-sm hover:bg-secondary/80 transition-colors duration-200 flex items-center"
                                              onClick={() => {
                                                const conv = conversations.find((c) => c.id === menuOpenForConvId);
                                                if (conv) openEditDialog(conv);
                                                setMenuOpenForConvId(null);
                                              }}
                                          >
                                            <Edit2 className="h-4 w-4 mr-2"/>
                                            {t('edit_title') || 'Edit Title'}
                                          </Button>
                                          <Button
                                              variant="ghost"
                                              className="w-full justify-start text-sm text-red-500 hover:bg-secondary/80 transition-colors duration-200 flex items-center"
                                              onClick={() => {
                                                const conv = conversations.find((c) => c.id === menuOpenForConvId);
                                                if (conv) openDeleteDialog(conv);
                                                setMenuOpenForConvId(null);
                                              }}
                                          >
                                            <Trash2 className="h-4 w-4 mr-2"/>
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
                <div className="flex flex-col space-y-4 p-4">
                  <Button
                      onClick={() => setIsFeedbackOpen(true)}
                      variant="outline"
                      className={`w-full ${isPanelVisible ? 'justify-start' : 'justify-center items-center'} animate-pulseButton`}
                  >
                    <Mail className="h-4 w-4"/>
                    {isPanelVisible && <span className="ml-2">{t('send_feedback')}</span>}
                  </Button>

                  {!isAuthenticated && (
                      <LoginRegisterDialog setIsAuthenticated={setIsAuthenticated}>
                        <Button
                            variant="outline"
                            className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${isPanelVisible ? 'justify-start' : 'justify-center items-center'}`}
                        >
                          <UserCircle className="h-4 w-4"/>
                          {isPanelVisible && <span className="ml-2">{t('login_register')}</span>}
                        </Button>
                      </LoginRegisterDialog>
                  )}

                  <SettingsDialog>
                    <Button
                        variant="outline"
                        className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${isPanelVisible ? 'justify-start' : 'justify-center items-center'}`}
                    >
                      <Settings className="h-4 w-4"/>
                      {isPanelVisible && <span className="ml-2">{t('settings')}</span>}
                    </Button>
                  </SettingsDialog>

                  {isAuthenticated && (
                      <Button
                          variant="outline"
                          onClick={() => setIsProfileOpen(true)}
                          className={`w-full hover:bg-secondary/80 transition-colors duration-200 ${isPanelVisible ? 'justify-start' : 'justify-center items-center'}`}
                      >
                        <UserCircle className="h-4 w-4"/>
                        {isPanelVisible && <span className="ml-2">{t('my_profile') || 'Mój profil'}</span>}
                      </Button>
                  )}
                </div>
              </>)}

          {/* Close panel button */}
            {(!isMobile || isPanelVisible) && (
                <Button
                    variant="ghost"
                    className={`bg-card border-r-2 border-border absolute top-1/2 -right-3 transform -translate-y-1/2 transition-transform duration-300 hover:bg-secondary/80 rounded-full w-8 h-8 flex items-center justify-center`}
                    onClick={togglePanel}
                    aria-label={isPanelVisible ? t('close_menu') || 'Close Menu' : t('open_menu') || 'Open Menu'}
                >
                    {isPanelVisible ? (
                        <ChevronLeft className="h-4 w-4" />
                    ) : (
                        <ChevronRight className="h-4 w-4" />
                    )}
                </Button>
            )}
        </div>

        {/* Feedback Modal */}
        <FeedbackModal isOpen={isFeedbackOpen} onClose={() => setIsFeedbackOpen(false)}/>

        {/* Profile Dialog */}
        <Dialog open={isProfileOpen} onOpenChange={setIsProfileOpen}>
          <DialogContent className="z-[51]">
            <DialogHeader>
              <DialogTitle>{t('my_profile') || 'Mój profil'}</DialogTitle>
              <DialogDescription>{t('profile_description') || 'Tutaj można dodać info o userze, itd.'}</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                  variant="destructive"
                  onClick={async () => {
                    try {
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
                      localStorage.removeItem('token'); // Remove token from localStorage
                      router.push('/');
                    } catch (err: unknown) {
                      console.error('Error logging out:', err);
                      if (err instanceof Error) {
                        alert('Nie udało się wylogować: ' + err.message);
                      } else {
                        alert('Nie udało się wylogować.');
                      }
                    }
                  }}
              >
                {t('logout') || 'Wyloguj'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit Conversation Title Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="z-[51]">
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
              <Button variant="default" onClick={handleSaveNewTitle}>
                {t('save') || 'Save'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Conversation Confirmation Dialog */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent className="z-[51]">
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
};
  export default LeftPanel;
