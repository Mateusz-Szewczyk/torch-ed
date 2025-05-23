"use client"

import type React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface ProfileDialogProps {
  isOpen: boolean
  onClose: () => void
  onLogout: () => void
  t: (key: string) => string
}

export const ProfileDialog: React.FC<ProfileDialogProps> = ({ isOpen, onClose, onLogout, t }) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("my_profile")}</DialogTitle>
          <DialogDescription>
            {t("profile_description") || "Zarządzaj ustawieniami konta i preferencjami."}
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="flex justify-between sm:justify-between">
          <Button variant="outline" onClick={onClose}>
            {t("close") || "Zamknij"}
          </Button>
          <Button variant="destructive" onClick={onLogout}>
            {t("logout") || "Wyloguj"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
