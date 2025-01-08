// components/ManageFileDialog.tsx

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Upload, X, Loader2, File as FileIcon, Save } from 'lucide-react';
import { useTranslation } from 'react-i18next'; // Importujemy hook useTranslation

interface UploadedFileRead {
  id: number;
  name: string;
  description?: string;
  category: string;
}

interface UploadResponse {
  message: string;
  uploaded_files: UploadedFileRead[];
  user_id: string;
  file_name: string;
  file_description?: string;
  category?: string;
}

interface DeleteKnowledgeResponse {
  message: string;
  deleted_from_vector_store: boolean;
  deleted_from_graph: boolean;
}

interface DeleteKnowledgeRequest {
  file_name: string;
}

interface ManageFileDialogProps {
  isPanelVisible: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

const ManageFileDialog: React.FC<ManageFileDialogProps> = ({ isPanelVisible }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRead[]>([]);
  const [fileDescription, setFileDescription] = useState<string>('');
  const [category, setCategory] = useState<string>('');
  const [startPage, setStartPage] = useState<number | undefined>(undefined);
  const [endPage, setEndPage] = useState<number | undefined>(undefined);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const { t } = useTranslation();

  /**
   * Funkcja do pobierania listy załadowanych plików z backendu.
   * Używa natywnego fetch z credentials: 'include' aby przesyłać ciasteczka autoryzacyjne.
   */
  const fetchUploadedFiles = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/list/`, {
        method: 'GET', // Zmieniono z POST na GET
        credentials: 'include', // Przesyłanie ciasteczek
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('error_fetch_files') || 'Error fetching files.');
      }

      const data: UploadedFileRead[] = await response.json();
      setUploadedFiles(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('error_unexpected_fetch_files') || 'Unexpected error fetching files.');
      }
      console.error('Fetch files error:', err);
    }
  }, [t]);

  /**
   * Efekt uruchamiający pobranie plików, gdy panel jest widoczny.
   */
  useEffect(() => {
    if (isPanelVisible) {
      fetchUploadedFiles();
    }
  }, [isPanelVisible, fetchUploadedFiles]);

  /**
   * Funkcja do wywołania okna wyboru pliku.
   */
  const handleChooseFile = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  /**
   * Funkcja obsługująca wybór pliku przez użytkownika.
   */
  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setSuccessMessage(null);
      setError(null);
    }
  };

  /**
   * Funkcja obsługująca przesyłanie pliku.
   */
  const handleUploadFile = async () => {
    if (!selectedFile) {
      setError(t('error_no_file_selected'));
      return;
    }

    if (!fileDescription.trim()) {
      setError(t('error_file_description_required'));
      return;
    }

    if (!category.trim()) {
      setError(t('error_category_required'));
      return;
    }

    const formData = new FormData();
    // Usunięto dodawanie 'user_id' do formData
    formData.append('file_description', fileDescription);
    formData.append('category', category);
    if (startPage !== undefined) {
      formData.append('start_page', startPage.toString());
    }
    if (endPage !== undefined) {
      formData.append('end_page', endPage.toString());
    }
    formData.append('file', selectedFile);

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload/`, {
        method: 'POST',
        credentials: 'include', // Przesyłanie ciasteczek
        body: formData, // 'Content-Type' jest ustawiany automatycznie przez fetch dla multipart/form-data
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('error_upload_file') || 'Error uploading file.');
      }

      const data: UploadResponse = await response.json();

      if (!data.uploaded_files) {
        throw new Error(t('error_upload_file') || 'Error uploading file.');
      }

      const newUploadedFiles: UploadedFileRead[] = data.uploaded_files.map(f => ({
        id: f.id,
        name: f.name,
        description: f.description,
        category: f.category,
      }));

      setUploadedFiles(prev => [...prev, ...newUploadedFiles]);

      // Reset po udanym przesłaniu pliku
      setFileDescription('');
      setCategory('');
      setStartPage(undefined);
      setEndPage(undefined);
      setSelectedFile(null);
      setSuccessMessage(t('settings_saved_successfully'));
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t('error_upload_file')}: ${err.message}`);
      } else {
        setError(t('error_unexpected_upload_file') || 'Unexpected error uploading file.');
      }
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  /**
   * Funkcja obsługująca usuwanie pliku.
   */
  const handleDelete = async (id: number, fileName: string) => {
    setDeletingFileId(id);
    setDeleteError(null);
    setSuccessMessage(null);

    try {
      const deleteRequest: DeleteKnowledgeRequest = { file_name: fileName };
      // Używamy fetch zamiast axios do wysyłania DELETE z body

      const response = await fetch(`${API_BASE_URL}/files/delete-file/`, {
        method: 'DELETE',
        credentials: 'include', // Przesyłanie ciasteczek
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(deleteRequest),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('error_delete_file') || 'Error deleting file.');
      }

      const data: DeleteKnowledgeResponse = await response.json();

      if (!data.message) {
        throw new Error(t('error_delete_file') || 'Error deleting file.');
      }

      if (data.deleted_from_vector_store || data.deleted_from_graph) {
        setUploadedFiles(prev => prev.filter(file => file.id !== id));
        setSuccessMessage(t('file_deleted_successfully'));
      } else {
        throw new Error(t('error_deletion_failed') || 'Error deleting file.');
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDeleteError(`${t('error_delete_file')}: ${err.message}`);
      } else {
        setDeleteError(t('error_unexpected_delete_file') || 'Unexpected error deleting file.');
      }
      console.error('Delete file error:', err);
    } finally {
      setDeletingFileId(null);
    }
  };

  /**
   * Warunek sprawdzający, czy można zapisać plik (wszystkie wymagane pola są wypełnione i nie trwa już przesyłanie).
   */
  const canSaveFile = selectedFile && fileDescription.trim() && category.trim() && !uploading;

return (
    <Dialog>
      <DialogTrigger>
        <Button variant="outline" className="w-full justify-start bg-background text-foreground border-border hover:bg-secondary/80 transition-colors">
          <Upload className="h-4 w-4" />
          {isPanelVisible && <span className="ml-2">{t('manage_files')}</span>}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-background border border-border text-foreground p-4 sm:p-6 rounded-lg w-[90vw] max-w-3xl sm:max-w-md md:max-w-lg lg:max-w-xl xl:max-w-2xl flex flex-col h-[90vh] max-h-[800px]">
        <DialogHeader>
          <DialogTitle className="text-foreground text-lg font-bold">{t('manage_uploaded_files')}</DialogTitle>
        </DialogHeader>

        {/* Messages */}
        {successMessage && (
          <p className="mt-2 text-sm text-green-600">
            {successMessage}
          </p>
        )}
        {(error || deleteError) && (
          <p className="mt-2 text-sm text-destructive">
            {error || deleteError}
          </p>
        )}

        {/* File Upload Form */}
        <div className="space-y-4 mt-4 bg-secondary/10 p-4 rounded-md flex-none">
          <p className="text-sm text-muted-foreground">{t('upload_instructions')}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* File Description */}
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-foreground mb-1">{t('file_description')}</label>
              <input
                type="text"
                value={fileDescription}
                onChange={(e) => setFileDescription(e.target.value)}
                className="block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
                placeholder={t('enter_file_description')}
              />
            </div>

            {/* Category */}
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-foreground mb-1">{t('category')}</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
                placeholder={t('enter_category')}
              />
            </div>

            {/* Start Page */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">{t('start_page')} ({t('optional')})</label>
              <input
                type="number"
                min={0}
                value={startPage !== undefined ? startPage : ''}
                onChange={(e) => setStartPage(e.target.value ? parseInt(e.target.value) : undefined)}
                className="block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
              />
            </div>

            {/* End Page */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">{t('end_page')} ({t('optional')})</label>
              <input
                type="number"
                min={0}
                value={endPage !== undefined ? endPage : ''}
                onChange={(e) => setEndPage(e.target.value ? parseInt(e.target.value) : undefined)}
                className="block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
              />
            </div>
          </div>

          {/* File Selection and Upload */}
          <div className="flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-2 mt-4">
            <input
              type="file"
              className="hidden"
              ref={fileInputRef}
              onChange={handleFileSelection}
            />
            <Button
              variant="outline"
              className="w-full sm:w-auto flex items-center justify-center space-x-2 bg-background hover:bg-secondary/80 transition-colors"
              onClick={handleChooseFile}
              disabled={uploading}
            >
              <FileIcon className="h-4 w-4" />
              <span>{t('choose_file')}</span>
            </Button>

            <Button
              variant="default"
              className="w-full sm:w-auto flex items-center justify-center space-x-2 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              onClick={handleUploadFile}
              disabled={!canSaveFile}
            >
              {uploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  <span>{t('uploading')}</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>{t('save_file')}</span>
                </>
              )}
            </Button>
          </div>

          {selectedFile && (
            <p className="text-sm text-foreground mt-2">
              {t('selected_file')}: <span className="font-medium">{selectedFile.name}</span>
            </p>
          )}
        </div>

        {/* Uploaded Files List */}
        <div className="mt-6 flex-1 flex flex-col min-h-0">
          <h3 className="text-lg font-semibold mb-2">{t('uploaded_files')}</h3>
          <ScrollArea className="flex-1 w-full pr-4 bg-background border border-border rounded-md">
            {uploadedFiles.length === 0 ? (
              <p className="text-center text-muted-foreground m-4">{t('no_files_uploaded_yet')}</p>
            ) : (
              <ul className="space-y-2 p-2">
                {uploadedFiles.map(file => (
                  <li
                    key={file.id}
                    className="flex flex-col bg-card p-4 rounded-md shadow-sm border border-border"
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-foreground">{file.category}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:bg-destructive/10"
                        onClick={() => handleDelete(file.id, file.name)}
                        disabled={deletingFileId === file.id}
                        aria-label={t('delete_file')}
                      >
                        {deletingFileId === file.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <X className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    {file.description && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {file.description}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ManageFileDialog;