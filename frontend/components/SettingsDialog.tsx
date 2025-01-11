// components/SettingsDialog.tsx

'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useTheme } from 'next-themes';
import Cookies from 'js-cookie';
import { useTranslation } from 'react-i18next';

export function SettingsDialog({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  const { t, i18n } = useTranslation();
  const [language, setLanguage] = useState('en');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Inicjalizacja języka na podstawie ciasteczka
  useEffect(() => {
    const savedLanguage = Cookies.get('language') || 'en';
    setLanguage(savedLanguage);
    i18n.changeLanguage(savedLanguage);
  }, [i18n]);

  // Logowanie aktualnego motywu (opcjonalne)
  useEffect(() => {
    console.log('Current theme:', theme);
  }, [theme]);

  const handleSaveChanges = () => {
    // Zapisz język do ciasteczka
    Cookies.set('language', language, { expires: 365 });
    setSuccessMessage(t('settings_saved_successfully'));

    // Aktualizacja języka w i18next
    i18n.changeLanguage(language);

    // Zapisz motyw do ciasteczka (next-themes automatycznie to robi)

    // Zamknij dialog po zapisaniu
    setIsOpen(false);

    // Usuń komunikat sukcesu po krótkim czasie
    setTimeout(() => {
      setSuccessMessage(null);
    }, 3000);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger>{children}</DialogTrigger>
      <DialogContent
        className={`
          sm:max-w-[425px] 
          bg-background text-foreground
          dark:bg-background dark:text-foreground
        `}
      >
        <DialogHeader>
          <DialogTitle>{t('settings')}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {/* Toggle Dark Mode */}
          <div className="flex items-center justify-between">
            <Label
              htmlFor="dark-mode"
              className="flex flex-col space-y-1"
            >
              <span>{t('dark_mode')}</span>
              <span className="font-normal text-sm text-muted-foreground">
                {t('dark_mode_description')}
              </span>
            </Label>
            <Switch
              id="dark-mode"
              checked={theme === 'dark'}
              onCheckedChange={(checked: boolean) => setTheme(checked ? 'dark' : 'light')}
            />
          </div>

          {/* Select Language */}
          <div className="flex flex-col space-y-1.5">
            <Label htmlFor="language">{t('language')}</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger id="language">
                <SelectValue placeholder={t('select_language')} />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value="en">{t('english')}</SelectItem>
                <SelectItem value="pl">{t('polish')}</SelectItem>
                <SelectItem value="es">{t('spanish')}</SelectItem>
                <SelectItem value="fr">{t('french')}</SelectItem>
                <SelectItem value="de">{t('german')}</SelectItem>
                {/* Dodaj więcej języków w razie potrzeby */}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Komunikat Sukcesu */}
        {successMessage && (
          <p className="mt-2 text-sm text-green-600">
            {successMessage}
          </p>
        )}

        {/* Przycisk Zapisz Zmiany */}
        <Button onClick={handleSaveChanges}>{t('save_changes')}</Button>
      </DialogContent>
    </Dialog>
  );
}
