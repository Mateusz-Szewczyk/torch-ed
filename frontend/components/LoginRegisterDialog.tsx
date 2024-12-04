'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useTranslation } from 'react-i18next';

export function LoginRegisterDialog({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[425px] bg-background text-foreground">
        <DialogHeader>
          <DialogTitle className="text-foreground">{t('login_register_dialog.title')}</DialogTitle>
        </DialogHeader>
        <Tabs defaultValue="login" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">{t('login_register_dialog.login')}</TabsTrigger>
            <TabsTrigger value="register">{t('login_register_dialog.register')}</TabsTrigger>
          </TabsList>
          <TabsContent value="login">
            <form onSubmit={(e) => { e.preventDefault(); /* Handle login */ }}>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="email">{t('login_register_dialog.email')}</Label>
                  <Input id="email" type="email" placeholder={t('login_register_dialog.email_placeholder')} required />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="password">{t('login_register_dialog.password')}</Label>
                  <Input id="password" type="password" required />
                </div>
              </div>
              <Button type="submit" className="w-full">{t('login_register_dialog.login')}</Button>
            </form>
          </TabsContent>
          <TabsContent value="register">
            <form onSubmit={(e) => { e.preventDefault(); /* Handle registration */ }}>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="register-email">{t('login_register_dialog.email')}</Label>
                  <Input id="register-email" type="email" placeholder={t('login_register_dialog.email_placeholder')} required />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="register-password">{t('login_register_dialog.password')}</Label>
                  <Input id="register-password" type="password" required />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="confirm-password">{t('login_register_dialog.confirm_password')}</Label>
                  <Input id="confirm-password" type="password" required />
                </div>
              </div>
              <Button type="submit" className="w-full">{t('login_register_dialog.register')}</Button>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
