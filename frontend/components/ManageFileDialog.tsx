'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Upload, X, Loader2, File as FileIcon, Save } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface UploadedFileRead {
  id: number;
  name: string;
  description?: string;
  category: string;
}

interface ManageFileDialogProps {
  isPanelVisible: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';

const ManageFileDialog: React.FC<ManageFileDialogProps> = ({ isPanelVisible }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRead[]>([]);
  const [fileDescription, setFileDescription] = useState<string>('');
  const [category, setCategory] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { t } = useTranslation();

  const fetchUploadedFiles = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/list/`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('error_fetch_files'));
      }

      const data: UploadedFileRead[] = await response.json();
      setUploadedFiles(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('error_unexpected_fetch_files'));
      }
      console.error('Fetch files error:', err);
    }
  }, [t]);

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
    if (!selectedFile || !fileDescription.trim() || !category.trim()) {
      setError(t('error_required_fields_missing'));
      return;
    }

    const formData = new FormData();
    formData.append('file_description', fileDescription);
    formData.append('category', category);
    formData.append('file', selectedFile);

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload/`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t('error_upload_file'));
      }

      const data: UploadedFileRead = await response.json();
      setUploadedFiles((prev) => [...prev, data]);
      setFileDescription('');
      setCategory('');
      setSelectedFile(null);
      setSuccessMessage(t('file_uploaded_successfully'));
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('error_unexpected_upload_file'));
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog>
      <DialogTrigger>
        <Button
          variant="outline"
          className={`w-full flex items-center justify-${isPanelVisible ? 'start' : 'center'} space-x-2`}
        >
          <Upload className="h-4 w-4" />
          {isPanelVisible && <span>{t('manage_files')}</span>}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-background border border-border text-foreground p-6 rounded-lg w-[90vw] max-w-3xl flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold">{t('manage_uploaded_files')}</DialogTitle>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {successMessage && <p className="text-sm text-success">{successMessage}</p>}

        <div className="mt-4">
          <label className="block text-sm font-medium text-foreground mb-1">{t('file_description')}</label>
          <input
            type="text"
            value={fileDescription}
            onChange={(e) => setFileDescription(e.target.value)}
            className="w-full rounded-md border border-input bg-background text-foreground p-2"
          />

          <label className="block text-sm font-medium text-foreground mt-4 mb-1">{t('category')}</label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-md border border-input bg-background text-foreground p-2"
          />

          <div className="mt-4 flex items-center space-x-2">
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={handleFileSelection}
            />
            <Button
              variant="outline"
              className="flex items-center space-x-2"
              onClick={handleChooseFile}
            >
              <FileIcon className="h-4 w-4" />
              <span>{t('choose_file')}</span>
            </Button>
            <Button
              variant="default"
              className="flex items-center space-x-2"
              onClick={handleUploadFile}
              disabled={uploading || !selectedFile}
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{t('uploading')}</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>{t('upload')}</span>
                </>
              )}
            </Button>
          </div>
        </div>

        <ScrollArea className="mt-6 h-40 bg-background rounded-md border border-border">
          {uploadedFiles.length ? (
            <ul className="space-y-2 p-2">
              {uploadedFiles.map((file) => (
                <li key={file.id} className="flex justify-between items-center p-2 bg-card rounded-md">
                  <span className="text-sm text-foreground">{file.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => console.log(`Delete file ${file.id}`)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground p-4">{t('no_files_uploaded')}</p>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

export default ManageFileDialog;
