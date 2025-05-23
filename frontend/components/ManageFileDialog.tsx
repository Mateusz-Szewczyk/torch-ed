"use client"

import type React from "react"
import { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Checkbox } from "@/components/ui/checkbox"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Upload,
  X,
  Loader2,
  FileIcon,
  Search,
  Trash2,
  FileText,
  FileImage,
  FileArchive,
  FileAudio,
  FileVideo,
  FilePlus,
  AlertCircle,
  CheckCircle2,
  Info,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"

// ------------------- INTERFACES -------------------
// Zaktualizowany interfejs pasujący do odpowiedzi z backendu
interface UploadedFileRead {
  id: number
  name: string
  description: string
  category: string
  created_at: string // Kluczowe pole z datą z API
}

// Założenie, że odpowiedź na upload zwraca tę samą strukturę
interface UploadResponseData {
  message: string
  uploaded_files: UploadedFileRead[]
}


interface ManageFileDialogProps {
  isPanelVisible: boolean
}

// ------------------- CONSTANTS -------------------
const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api"

// ------------------- HELPERS -------------------
const getFileIcon = (fileName: string) => {
  const extension = fileName.split(".").pop()?.toLowerCase() || ""
  switch (extension) {
    case "pdf": return <FileText className="h-5 w-5 text-red-500" />;
    case "doc": case "docx": return <FileText className="h-5 w-5 text-blue-500" />;
    case "txt": return <FileText className="h-5 w-5 text-gray-400" />;
    case "jpg": case "jpeg": case "png": return <FileImage className="h-5 w-5 text-purple-500" />;
    case "zip": case "rar": return <FileArchive className="h-5 w-5 text-yellow-500" />;
    case "mp3": case "wav": return <FileAudio className="h-5 w-5 text-pink-500" />;
    case "mp4": case "avi": return <FileVideo className="h-5 w-5 text-indigo-500" />;
    default: return <FileIcon className="h-5 w-5 text-gray-500" />;
  }
}

const formatDate = (dateString?: string): string => {
  if (!dateString) return "Nieznana data"
  const date = new Date(dateString)
  return date.toLocaleDateString("pl-PL", { year: "numeric", month: "long", day: "numeric", hour: '2-digit', minute: '2-digit' })
}

// ------------------- SUB-COMPONENTS -------------------
const FileCard: React.FC<{
  file: UploadedFileRead
  onDelete: (fileName: string) => void
  isSelected: boolean
  onSelect: (id: number) => void
}> = ({ file, onDelete, isSelected, onSelect }) => {
  const { t } = useTranslation()
  const [showConfirm, setShowConfirm] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const handleDelete = () => {
    if (showConfirm) {
      onDelete(file.name)
      setShowConfirm(false)
    } else {
      setShowConfirm(true)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "group relative p-3 sm:p-4 rounded-lg border transition-all duration-200",
        "hover:shadow-md hover:border-primary/30",
        isSelected ? "border-primary bg-primary/5" : "border-border bg-card",
      )}
    >
      <div className="absolute top-3 left-3">
        <Checkbox checked={isSelected} onCheckedChange={() => onSelect(file.id)} className="h-4 w-4" />
      </div>
      <div className="ml-6 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {getFileIcon(file.name)}
            <h4 className="font-medium text-foreground truncate">{file.name}</h4>
          </div>
          <div className="mt-2 space-y-1">
            <div className="flex items-center text-xs text-muted-foreground">
              <span>{formatDate(file.created_at)}</span>
            </div>
            <div className="flex flex-wrap gap-1 mt-1">
              <Badge variant="outline" className="text-xs">{file.category}</Badge>
            </div>
            {file.description && (
              <div className="mt-2">
                <p className={cn("text-xs text-muted-foreground", !isExpanded && "line-clamp-1")}>{file.description}</p>
                {file.description.length > 50 && (
                  <button onClick={() => setIsExpanded(!isExpanded)} className="text-xs text-primary mt-1 hover:underline">
                    {isExpanded ? t("show_less") : t("show_more")}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center">
          {showConfirm ? (
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={() => setShowConfirm(false)}>
                <X className="h-4 w-4" />
              </Button>
              <Button variant="destructive" size="icon" className="h-7 w-7" onClick={handleDelete}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={handleDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

const UploadProgress: React.FC<{
  file: File
  progress: number
  onCancel: () => void
}> = ({ file, progress, onCancel }) => {
  return (
    <div className="p-4 border border-border rounded-lg bg-card/50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getFileIcon(file.name)}
          <span className="font-medium text-sm truncate max-w-[200px]">{file.name}</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onCancel}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-end text-xs">
          <span>{progress}%</span>
        </div>
        <Progress value={progress} className="h-1.5" />
      </div>
    </div>
  )
}

const FileDropZone: React.FC<{
  onFileSelect: (file: File) => void
}> = ({ onFileSelect }) => {
  const { t } = useTranslation()
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelect(e.dataTransfer.files[0])
    }
  }

  return (
    <div
      className={cn(
        "border-2 border-dashed rounded-lg p-4 sm:p-8 text-center transition-colors cursor-pointer",
        isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
      )}
      onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop} onClick={() => fileInputRef.current?.click()}
    >
      <input type="file" ref={fileInputRef} className="hidden" onChange={(e) => { if (e.target.files?.length) { onFileSelect(e.target.files[0]) } }} />
      <div className="flex flex-col items-center gap-2">
        <div className="p-3 rounded-full bg-primary/10 text-primary"><Upload className="h-6 w-6" /></div>
        <h3 className="font-medium text-foreground">{isDragging ? t("drop_file_here") : t("drag_drop_file_here")}</h3>
        <p className="text-sm text-muted-foreground">{t("or_click_to_browse")}</p>
        <p className="text-xs text-muted-foreground mt-2">{t("supported_file_types")}</p>
      </div>
    </div>
  )
}

// ------------------- MAIN COMPONENT -------------------
const ManageFileDialog: React.FC<ManageFileDialogProps> = ({ isPanelVisible }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRead[]>([])
  const [fileDescription, setFileDescription] = useState<string>("")
  const [category, setCategory] = useState<string>("")
  const [uploading, setUploading] = useState<boolean>(false)
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [selectedFileIds, setSelectedFileIds] = useState<number[]>([])
  const [isOpen, setIsOpen] = useState<boolean>(false)
  const { t } = useTranslation()

  const fetchUploadedFiles = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/list/`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || t("error_fetch_files"))
      }
      const data: UploadedFileRead[] = await response.json()
      setUploadedFiles(data) // Bezpośrednie ustawienie danych z API
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t("error_unexpected_fetch_files")
      setError(errorMessage)
      console.error("Fetch files error:", err)
    }
  }, [t])

  useEffect(() => {
    if (isOpen) {
      fetchUploadedFiles()
    }
  }, [isOpen, fetchUploadedFiles])

  const handleUploadFile = async () => {
    if (!selectedFile || !fileDescription.trim() || !category.trim()) {
      setError(t("error_required_fields_missing"))
      return
    }

    const formData = new FormData()
    formData.append("file_description", fileDescription)
    formData.append("category", category)
    formData.append("file", selectedFile)

    setUploading(true)
    setError(null)
    setSuccessMessage(null)

    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => (prev >= 95 ? prev : prev + Math.floor(Math.random() * 10)))
    }, 300)

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload/`, {
        method: "POST",
        credentials: "include",
        body: formData,
      })

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || t("error_upload_file"))
      }
      const data: UploadResponseData = await response.json()

      if (data.uploaded_files?.length) {
        setUploadedFiles((prev) => [...prev, ...data.uploaded_files])
      }

      setFileDescription("")
      setCategory("")
      setSelectedFile(null)
      setUploadProgress(0)
      setSuccessMessage(t("file_uploaded_successfully"))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t("error_unexpected_upload_file")
      setError(errorMessage)
    } finally {
      setUploading(false)
      clearInterval(progressInterval)
    }
  }

  const handleDeleteFile = async (fileName: string) => {
    try {
      setError(null)
      setSuccessMessage(null)

      const response = await fetch(`${API_BASE_URL}/files/delete-file/`, {
        method: "DELETE",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_name: fileName }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || t("error_deleting_file"))
      }
      setUploadedFiles((prev) => prev.filter((f) => f.name !== fileName))
      setSuccessMessage(t("file_deleted_successfully"))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t("error_unexpected_deleting_file")
      setError(errorMessage)
      console.error("Error deleting file:", err)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedFileIds.length === 0) return
    setError(null)
    setSuccessMessage(null)
    const filesToDelete = uploadedFiles.filter((file) => selectedFileIds.includes(file.id))
    let deletedCount = 0
    for (const file of filesToDelete) {
      try {
        await handleDeleteFile(file.name)
        deletedCount++
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : t("error_unexpected_deleting_file")
        setError(t("bulk_delete_error", { fileName: file.name, error: errorMessage }))
        break
      }
    }
    setSelectedFileIds([])
    if (deletedCount > 0) {
      setSuccessMessage(t("files_deleted_successfully", { count: deletedCount }))
    }
  }

  const toggleFileSelection = (id: number) => {
    setSelectedFileIds((prev) => (prev.includes(id) ? prev.filter((fileId) => fileId !== id) : [...prev, id]))
  }

  const filteredFiles = uploadedFiles.filter((file) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      file.name.toLowerCase().includes(query) ||
      file.description?.toLowerCase().includes(query) ||
      file.category.toLowerCase().includes(query)
    )
  })

  const selectAllFiles = () => {
    if (selectedFileIds.length === filteredFiles.length) {
      setSelectedFileIds([])
    } else {
      setSelectedFileIds(filteredFiles.map((file) => file.id))
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className={cn("flex w-full", isPanelVisible ? "justify-start" : "justify-center")}>
          <Upload className="h-4 w-4" />
          {isPanelVisible && <span className="ml-2">{t("manage_files")}</span>}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[90vw] md:max-w-[900px] lg:max-w-[1100px] xl:max-w-[1200px] p-0 gap-0 overflow-hidden">
        <div className="flex flex-col h-[80vh] max-h-[800px]">
          <DialogHeader className="px-6 py-4 border-b">
            <DialogTitle className="text-xl font-semibold flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {t("manage_uploaded_files")}
            </DialogTitle>
          </DialogHeader>
          <div className="flex flex-col lg:flex-row h-full overflow-hidden">
            <div className="w-full lg:w-[350px] p-4 sm:p-6 border-b lg:border-b-0 lg:border-r border-border overflow-y-auto">
              <div className="space-y-6">
                <h3 className="text-lg font-medium">{t("upload_new_file")}</h3>
                {selectedFile ? (
                  <UploadProgress file={selectedFile} progress={uploading ? uploadProgress : 0} onCancel={() => setSelectedFile(null)} />
                ) : (
                  <FileDropZone onFileSelect={setSelectedFile} />
                )}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">{t("file_description")}</label>
                    <Textarea value={fileDescription} onChange={(e) => setFileDescription(e.target.value)} placeholder={t("placeholder_file_description")} className="resize-none" rows={3} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">{t("category")}</label>
                    <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder={t("placeholder_category")} />
                  </div>
                  <Button className="w-full" onClick={handleUploadFile} disabled={uploading || !selectedFile || !fileDescription || !category}>
                    {uploading ? ( <><Loader2 className="h-4 w-4 mr-2 animate-spin" />{t("uploading")}</> ) : ( <><FilePlus className="h-4 w-4 mr-2" />{t("upload_file")}</> )}
                  </Button>
                </div>
                <AnimatePresence>
                  {error && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                      <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>{error}</AlertDescription></Alert>
                    </motion.div>
                  )}
                  {successMessage && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                      <Alert variant="success" className="bg-green-500/10 text-green-600 border-green-500/20"><CheckCircle2 className="h-4 w-4" /><AlertDescription>{successMessage}</AlertDescription></Alert>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
            <div className="w-full lg:flex-1 flex flex-col overflow-hidden">
              <div className="p-4 border-b border-border flex flex-col sm:flex-row gap-3 justify-between">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input placeholder={t("search_files_placeholder")} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 w-full" />
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" className="text-xs h-9" onClick={selectAllFiles}>
                    {selectedFileIds.length === filteredFiles.length && filteredFiles.length > 0 ? t("deselect_all") : t("select_all")}
                  </Button>
                  {selectedFileIds.length > 0 && (
                    <Button variant="destructive" size="sm" className="text-xs h-9" onClick={handleBulkDelete}>
                      <Trash2 className="h-3.5 w-3.5 mr-1" />{t("delete_count", { count: selectedFileIds.length })}
                    </Button>
                  )}
                </div>
              </div>
              <ScrollArea className="flex-1 p-4">
                {filteredFiles.length > 0 ? (
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                    <AnimatePresence>
                      {filteredFiles.map((file) => (
                        <FileCard key={file.id} file={file} onDelete={handleDeleteFile} isSelected={selectedFileIds.includes(file.id)} onSelect={toggleFileSelection} />
                      ))}
                    </AnimatePresence>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center p-8">
                    <div className="p-3 rounded-full bg-muted"><Info className="h-6 w-6 text-muted-foreground" /></div>
                    <h3 className="mt-4 text-lg font-medium">{searchQuery ? t("no_matching_files") : t("no_files_uploaded")}</h3>
                    <p className="mt-2 text-sm text-muted-foreground max-w-sm">{searchQuery ? t("no_matching_files_description") : t("upload_first_file_prompt")}</p>
                    {searchQuery && (<Button variant="outline" className="mt-4" onClick={() => setSearchQuery("")}>{t("clear_search")}</Button>)}
                  </div>
                )}
              </ScrollArea>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default ManageFileDialog