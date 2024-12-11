// components/ManageFileDialog.tsx

'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios, { AxiosError } from 'axios';
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
  user_id: string;
  file_name: string;
}

interface ManageFileDialogProps {
  userId: string;
  isPanelVisible: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api';

const ManageFileDialog: React.FC<ManageFileDialogProps> = ({ userId, isPanelVisible }) => {
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

  const fetchUploadedFiles = useCallback(async () => {
    try {
      const response = await axios.post<UploadedFileRead[]>(
        `${API_BASE_URL}/files/list/`,
        { user_id: userId },
        { headers: { 'Content-Type': 'application/json' } }
      );
      setUploadedFiles(response.data);
    } catch (err) {
      const error = err as AxiosError;
      console.error('Fetch files error:', error);
      setError(t('error_fetch_files'));
    }
  }, [userId, t]);

  useEffect(() => {
    if (isPanelVisible) {
      fetchUploadedFiles();
    }
  }, [isPanelVisible, fetchUploadedFiles]);

  const handleChooseFile = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setSuccessMessage(null);
      setError(null);
    }
  };

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
    formData.append('user_id', userId);
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
      const response = await axios.post<UploadResponse>(`${API_BASE_URL}/files/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      console.log('Upload response:', response.data);

      if (!response.data.uploaded_files) {
        throw new Error(t('error_upload_file'));
      }

      const newUploadedFiles: UploadedFileRead[] = response.data.uploaded_files.map(f => ({
        id: f.id,
        name: f.name,
        description: f.description,
        category: f.category,
      }));

      setUploadedFiles(prev => [...prev, ...newUploadedFiles]);

      // Reset after successful upload
      setFileDescription('');
      setCategory('');
      setStartPage(undefined);
      setEndPage(undefined);
      setSelectedFile(null);
      setSuccessMessage(t('settings_saved_successfully'));
    } catch (err) {
      const error = err as AxiosError;
      console.error('Upload error:', error);
      setError(error.response?.data?.detail || t('error_upload_file'));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number, fileName: string) => {
    setDeletingFileId(id);
    setDeleteError(null);
    setSuccessMessage(null);

    try {
      const deleteRequest: DeleteKnowledgeRequest = { user_id: userId, file_name: fileName };

      const response = await axios.delete<DeleteKnowledgeResponse>(`${API_BASE_URL}/files/delete-file/`, {
        data: deleteRequest,
        headers: { 'Content-Type': 'application/json' }
      });

      console.log('Delete response:', response.data);

      if (!response.data.message) {
        throw new Error(t('error_delete_file'));
      }

      if (response.data.deleted_from_vector_store || response.data.deleted_from_graph) {
        setUploadedFiles(prev => prev.filter(file => file.id !== id));
        setSuccessMessage(t('file_deleted_successfully'));
      } else {
        throw new Error(t('error_deletion_failed'));
      }
    } catch (err) {
      const error = err as AxiosError;
      console.error('Delete file error:', error);
      setDeleteError(error.response?.data?.detail || t('error_delete_file'));
    } finally {
      setDeletingFileId(null);
    }
  };

  const canSaveFile = selectedFile && fileDescription.trim() && category.trim() && !uploading;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" className="w-full justify-start bg-background text-foreground border-border hover:bg-secondary/80 transition-colors">
          <Upload className="h-4 w-4" />
          {isPanelVisible && <span className="ml-2">{t('manage_files')}</span>}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-background border border-border text-foreground p-6 rounded-lg max-w-3xl w-full">
        <DialogHeader>
          <DialogTitle className="text-foreground text-lg font-bold">{t('manage_uploaded_files')}</DialogTitle>
        </DialogHeader>

        {/* Success / Error Messages */}
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
        <div className="space-y-4 mt-6 bg-secondary/10 p-4 rounded-md">
          <p className="text-sm text-muted-foreground">{t('upload_instructions')}</p>

          {/* Description */}
          <div>
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
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">{t('category')}</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
              placeholder={t('enter_category')}
            />
          </div>

          {/* Pages */}
          <div className="flex space-x-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-foreground mb-1">{t('start_page')} ({t('optional')})</label>
              <input
                type="number"
                min={0}
                value={startPage !== undefined ? startPage : ''}
                onChange={(e) => setStartPage(e.target.value ? parseInt(e.target.value) : undefined)}
                className="block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
              />
            </div>
            <div className="flex-1">
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

          {/* File selection */}
          <div className="flex items-center space-x-2 mt-4">
            <input
              type="file"
              className="hidden"
              ref={fileInputRef}
              onChange={handleFileSelection}
            />
            <Button
              variant="outline"
              className="flex items-center justify-center space-x-2 bg-background hover:bg-secondary/80 transition-colors"
              onClick={handleChooseFile}
              disabled={uploading}
            >
              <FileIcon className="h-4 w-4" />
              <span>{t('choose_file')}</span>
            </Button>

            <Button
              variant="primary"
              className="flex items-center justify-center space-x-2 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
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
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-2">{t('uploaded_files')}</h3>
          <ScrollArea className="h-64 w-full pr-4 bg-background border border-border rounded-md">
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
