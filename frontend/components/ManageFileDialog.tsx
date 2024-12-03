// components/ManageFileDialog.tsx

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import axios, { AxiosError } from 'axios'
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Upload, X, Loader2 } from 'lucide-react'

// Import Pydantic Schemas from Backend
interface UploadedFileRead {
  id: number
  name: string
}

interface UploadResponse {
  message: string
  uploaded_files: UploadedFileRead[]
  user_id: string
  file_name: string
  file_description?: string
  category?: string
}

interface DeleteKnowledgeResponse {
  message: string
  deleted_from_vector_store: boolean
  deleted_from_graph: boolean
}

interface DeleteKnowledgeRequest {
  user_id: string
  file_name: string
}

interface ListFilesRequest {
  user_id: string
}

interface ManageFileDialogProps {
  userId: string
  isPanelVisible: boolean
}

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8043/api'

const ManageFileDialog: React.FC<ManageFileDialogProps> = ({ userId, isPanelVisible }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRead[]>([])
  const [fileDescription, setFileDescription] = useState<string>('')
  const [category, setCategory] = useState<string>('')
  const [startPage, setStartPage] = useState<number | undefined>(undefined)
  const [endPage, setEndPage] = useState<number | undefined>(undefined)
  const [uploading, setUploading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Funkcja pobierająca listę plików z backendu
  const fetchUploadedFiles = useCallback(async () => {
    try {
      const response = await axios.post<UploadedFileRead[]>(`${API_BASE_URL}/files/list/`, {
        user_id: userId
      }, {
        headers: {
          'Content-Type': 'application/json'
        }
      })
      setUploadedFiles(response.data)
    } catch (err) {
      const error = err as AxiosError
      console.error('Fetch files error:', error)
      setError(error.response?.data?.detail || 'An error occurred while fetching uploaded files.')
    }
  }, [userId])

  useEffect(() => {
    if (isPanelVisible) {
      fetchUploadedFiles()
    }
  }, [isPanelVisible, fetchUploadedFiles])

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const file = files[0] // Upload one file at a time

    const formData = new FormData()
    formData.append('user_id', userId)
    formData.append('file_description', fileDescription)
    formData.append('category', category)
    if (startPage !== undefined) {
      formData.append('start_page', startPage.toString())
    }
    if (endPage !== undefined) {
      formData.append('end_page', endPage.toString())
    }
    formData.append('file', file)

    setUploading(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const response = await axios.post<UploadResponse>(`${API_BASE_URL}/files/upload/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      console.log('Upload response:', response.data)

      if (!response.data.uploaded_files) {
        throw new Error('uploaded_files is undefined in the response')
      }

      const newUploadedFiles: UploadedFileRead[] = response.data.uploaded_files.map(file => ({
        id: file.id,
        name: file.name
      }))

      setUploadedFiles(prev => [...prev, ...newUploadedFiles])

      // Reset form fields after successful upload
      setFileDescription('')
      setCategory('')
      setStartPage(undefined)
      setEndPage(undefined)
      setSuccessMessage('File uploaded successfully.')
    } catch (err) {
      const error = err as AxiosError
      console.error('Upload error:', error)
      setError(error.response?.data?.detail || 'An error occurred during file upload.')
    } finally {
      setUploading(false)
      // Reset the file input
      if (event.target) {
        event.target.value = ''
      }
    }
  }

  const handleDelete = async (id: number, fileName: string) => {
    setDeletingFileId(id)
    setDeleteError(null)
    setSuccessMessage(null)

    try {
      const deleteRequest: DeleteKnowledgeRequest = {
        user_id: userId,
        file_name: fileName
      }

      const response = await axios.delete<DeleteKnowledgeResponse>(`${API_BASE_URL}/files/delete-file/`, {
        data: deleteRequest,
        headers: {
          'Content-Type': 'application/json'
        }
      })

      console.log('Delete response:', response.data)

      if (!response.data.message) {
        throw new Error('No message returned from delete response')
      }

      if (response.data.deleted_from_vector_store || response.data.deleted_from_graph) {
        // Remove the file from the state
        setUploadedFiles(prev => prev.filter(file => file.id !== id))
        setSuccessMessage('File deleted successfully.')
      } else {
        throw new Error('Deletion failed on both vector store and graph.')
      }
    } catch (err) {
      const error = err as AxiosError
      console.error('Delete file error:', error)
      setDeleteError(error.response?.data?.detail || 'An error occurred while deleting the file.')
    } finally {
      setDeletingFileId(null)
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-start bg-background text-foreground border-border"
        >
          <Upload className="h-4 w-4" />
          {isPanelVisible && <span className="ml-2">Manage Files</span>}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-background border-border text-foreground p-6 rounded-lg max-w-3xl w-full">
        <DialogHeader>
          <DialogTitle className="text-foreground">Manage Uploaded Files</DialogTitle>
        </DialogHeader>

        {/* Success Message */}
        {successMessage && (
          <p className="mt-2 text-sm text-green-600">
            {successMessage}
          </p>
        )}

        {/* File Upload Form */}
        <div className="space-y-4 mt-4">
          <div>
            <label className="block text-sm font-medium text-foreground">File Description</label>
            <input
              type="text"
              value={fileDescription}
              onChange={(e) => setFileDescription(e.target.value)}
              className="mt-1 block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
              placeholder="Enter a description for the file"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground">Category</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1 block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
              placeholder="Enter a category"
            />
          </div>
          <div className="flex space-x-4">
            <div>
              <label className="block text-sm font-medium text-foreground">Start Page</label>
              <input
                type="number"
                min={0}
                value={startPage !== undefined ? startPage : ''}
                onChange={(e) => setStartPage(e.target.value ? parseInt(e.target.value) : undefined)}
                className="mt-1 block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
                placeholder="Optional"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground">End Page</label>
              <input
                type="number"
                min={0}
                value={endPage !== undefined ? endPage : ''}
                onChange={(e) => setEndPage(e.target.value ? parseInt(e.target.value) : undefined)}
                className="mt-1 block w-full rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground p-2"
                placeholder="Optional"
              />
            </div>
          </div>
        </div>

        {/* Error Handling */}
        {(error || deleteError) && (
          <p className="mt-2 text-sm text-destructive">
            {error || deleteError}
          </p>
        )}

        {/* Upload Button */}
        <Button
          asChild
          className="w-full mt-4 bg-primary text-primary-foreground"
          disabled={uploading}
        >
          <label className="flex items-center justify-center cursor-pointer w-full">
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload New File
              </>
            )}
            <input type="file" className="hidden" onChange={handleFileUpload} />
          </label>
        </Button>

        {/* Uploaded Files List */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-2">Uploaded Files</h3>
          <ScrollArea className="h-64 w-full pr-4 bg-background">
            {uploadedFiles.length === 0 ? (
              <p className="text-center text-muted-foreground">No files uploaded yet.</p>
            ) : (
              uploadedFiles.map(file => (
                <div
                  key={file.id}
                  className="flex items-center justify-between py-2 bg-background text-foreground"
                >
                  <span className="truncate text-foreground">{file.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:bg-destructive/10"
                    onClick={() => handleDelete(file.id, file.name)}
                    disabled={deletingFileId === file.id}
                  >
                    {deletingFileId === file.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <X className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              ))
            )}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default ManageFileDialog
