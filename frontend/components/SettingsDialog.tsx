'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
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

  useEffect(() => {
    const savedLanguage = Cookies.get('language') || 'en';
    setLanguage(savedLanguage);
    i18n.changeLanguage(savedLanguage);
  }, [i18n]);

  useEffect(() => {
    console.log('Current theme:', theme);
  }, [theme]);

  const handleSaveChanges = () => {
    Cookies.set('language', language, { expires: 365 });
    i18n.changeLanguage(language);
    setIsOpen(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[425px] bg-background text-foreground">
        <DialogHeader>
          <DialogTitle>{t('settings')}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Dark Mode Toggle - Fixed Layout */}
          <div className="grid grid-cols-[1fr,auto] items-center gap-4">
            <div className="space-y-1.5">
              <Label className="text-base font-semibold">{t("dark_mode")}</Label>
              <p className="text-sm text-muted-foreground">
                {t("dark_mode_description")}
              </p>
            </div>
            <div className="toggle-switch">
              <label className="switch-label">
                <input
                    type="checkbox"
                    className="checkbox"
                    checked={theme === "dark"}
                    onChange={(e) => setTheme(e.target.checked ? "dark" : "light")}
                />
                <span className="slider"></span>
              </label>
            </div>
          </div>

          {/* Language Selection */}
          <div className="flex flex-col space-y-1.5">
            <Label htmlFor="language">{t('language')}</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger id="language">
                <SelectValue placeholder={t('select_language')}/>
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value="en">{t('english')}</SelectItem>
                <SelectItem value="pl">{t('polish')}</SelectItem>
                <SelectItem value="es">{t('spanish')}</SelectItem>
                <SelectItem value="fr">{t('french')}</SelectItem>
                <SelectItem value="de">{t('german')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleSaveChanges}>
              {t('save_changes')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}