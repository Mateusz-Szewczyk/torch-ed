"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Upload,
  X,
  Loader2,
  File as FileIcon,
  Save,
} from "lucide-react";
import { useTranslation } from "react-i18next";

// ------------------- INTERFACES -------------------
interface UploadedFileRead {
  id: number;
  name: string;
  description?: string;
  category: string;
}

// Zwracane przez endpoint /files/upload/
interface UploadResponseData {
  message: string;
  uploaded_files: UploadedFileRead[];
  user_id: string;
  file_name: string;
  file_description: string;
  category: string;
}

// Zwracane przez endpoint /files/delete-file/
interface DeleteKnowledgeResponse {
  message: string;
  deleted_from_vector_store: boolean;
  deleted_from_graph: boolean;
}

interface ManageFileDialogProps {
  isPanelVisible: boolean;
}

// ------------------- CONSTANTS -------------------
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api";

const ManageFileDialog: React.FC<ManageFileDialogProps> = ({
  isPanelVisible,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRead[]>([]);
  const [fileDescription, setFileDescription] = useState<string>("");
  const [category, setCategory] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { t } = useTranslation();

  // ------------------- FETCH FILES -------------------
  const fetchUploadedFiles = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/list/`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t("error_fetch_files") || "Fetch error");
      }

      const data: UploadedFileRead[] = await response.json();
      setUploadedFiles(data);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("error_unexpected_fetch_files") || "Unexpected fetch error");
      }
      console.error("Fetch files error:", err);
    }
  }, [t]);

  // ------------------- USE EFFECT: FETCH ON OPEN -------------------
  useEffect(() => {
    if (isPanelVisible) {
      fetchUploadedFiles();
    }
  }, [isPanelVisible, fetchUploadedFiles]);

  // ------------------- FILE SELECTION -------------------
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

  // ------------------- UPLOAD FILE -------------------
  const handleUploadFile = async () => {
    if (!selectedFile || !fileDescription.trim() || !category.trim()) {
      setError(t("error_required_fields_missing") || "Required fields missing");
      return;
    }

    const formData = new FormData();
    formData.append("file_description", fileDescription);
    formData.append("category", category);
    formData.append("file", selectedFile);

    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload/`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || t("error_upload_file") || "File upload error"
        );
      }

      // Odpowiedź w formacie UploadResponseData
      const data: UploadResponseData = await response.json();

      // Dokładamy zwrócone pliki (zazwyczaj 1) do stanu
      if (data.uploaded_files && data.uploaded_files.length > 0) {
        setUploadedFiles((prev) => [...prev, ...data.uploaded_files]);
      }

      // Czyszczenie pól i ustawianie sukcesu
      setFileDescription("");
      setCategory("");
      setSelectedFile(null);
      setSuccessMessage(t("file_uploaded_successfully") || "File uploaded.");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("error_unexpected_upload_file") || "Unexpected upload error");
      }
    } finally {
      setUploading(false);
    }
  };

  // ------------------- DELETE FILE -------------------
  const handleDeleteFile = async (fileName: string) => {
    try {
      setError(null);
      setSuccessMessage(null);

      const response = await fetch(`${API_BASE_URL}/files/delete-file/`, {
        method: "DELETE",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_name: fileName }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || t("error_deleting_file") || "Delete error"
        );
      }

      const data: DeleteKnowledgeResponse = await response.json();

      // Tutaj można ewentualnie sprawdzić pola data.deleted_from_vector_store itp.
      console.log("Delete response:", data);

      // Sukces - usuwamy plik z local state
      setUploadedFiles((prev) => prev.filter((f) => f.name !== fileName));
      setSuccessMessage(t("file_deleted_successfully") || "File deleted.");
    } catch (err) {
      console.error("Error deleting file:", err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("error_unexpected_deleting_file") || "Unexpected delete error");
      }
    }
  };

  return (
    <Dialog>
      <DialogTrigger>
        <Button
          variant="outline"
          className={`flex items-center justify-center${
            isPanelVisible ? "start" : "center"
          } space-x-2`}
        >
          <Upload className="h-4 w-4" />
          {isPanelVisible && <span>{t("manage_files")}</span>}
        </Button>
      </DialogTrigger>

      <DialogContent className="bg-background border border-border text-foreground p-6 rounded-lg w-[90vw] max-w-3xl flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold">
            {t("manage_uploaded_files")}
          </DialogTitle>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {successMessage && (
          <p className="text-sm text-success">{successMessage}</p>
        )}

        <div className="mt-4">
          <label className="block text-sm font-medium text-foreground mb-1">
            {t("file_description")}
          </label>
          <input
            type="text"
            value={fileDescription}
            onChange={(e) => setFileDescription(e.target.value)}
            className="w-full rounded-md border border-input bg-background text-foreground p-2"
          />

          <label className="block text-sm font-medium text-foreground mt-4 mb-1">
            {t("category")}
          </label>
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
              <span>{t("choose_file")}</span>
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
                  <span>{t("uploading")}</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>{t("upload")}</span>
                </>
              )}
            </Button>
          </div>
        </div>

        <ScrollArea className="mt-6 h-40 bg-background rounded-md border border-border">
          {uploadedFiles.length ? (
            <ul className="space-y-2 p-2">
              {uploadedFiles.map((file) => (
                <li
                  key={file.id}
                  className="flex justify-between items-center p-2 bg-card rounded-md"
                >
                  <span className="text-sm text-foreground">{file.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => handleDeleteFile(file.name)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground p-4">
              {t("no_files_uploaded")}
            </p>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

export default ManageFileDialog;
