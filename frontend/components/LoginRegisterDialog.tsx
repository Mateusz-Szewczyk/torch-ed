'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';

interface LoginRegisterDialogProps {
  children: React.ReactNode;
  setIsAuthenticated: (val: boolean) => void; // Callback to set logged-in state
}

export function LoginRegisterDialog({ children, setIsAuthenticated }: LoginRegisterDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  const router = useRouter();

  // Fields for login
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Fields for registration
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerPassword2, setRegisterPassword2] = useState('');

  // State to track if registration confirmation is needed
  const [registrationConfirmationMessage, setRegistrationConfirmationMessage] = useState('');

  // Local state for success message after login
  const [loginSuccessMessage, setLoginSuccessMessage] = useState('');

  // Pobierz bazowy URL API z zmiennej środowiskowej
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_FLASK_URL || 'http://localhost:14440/api/v1';

  // Handler: login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_name: loginEmail,
          password: loginPassword,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to login');
      }

      // Instead of alert, set a success message
      setLoginSuccessMessage('Zalogowano pomyślnie');
      // Hide the dialog
      setIsOpen(false);

      // Mark user as authenticated
      setIsAuthenticated(true);

      // Redirect to home
      router.push('/');

      // Clear the success message after 3 seconds
      setTimeout(() => {
        setLoginSuccessMessage('');
      }, 3000);

    } catch (err) {
      console.error('Error logging in:', err);
      alert('Nie udało się zalogować: ' + String(err));
    }
  };

  // Handler: register
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (registerPassword !== registerPassword2) {
        alert('Hasła nie są takie same!');
        return;
      }
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_name: registerEmail,
          password: registerPassword,
          password2: registerPassword2,
          email: registerEmail,
          age: 0,
          role: 'user',
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to register');
      }

      // Show confirmation message after successful registration
      setRegistrationConfirmationMessage('Rejestracja zakończona! Sprawdź swoją pocztę, aby potwierdzić konto. Wystarczy kliknąć w link rejestracyjny.');

      // Hide the dialog
      setIsOpen(false);

    } catch (err) {
      console.error('Error registering:', err);
      alert('Nie udało się zarejestrować: ' + String(err));
    }
  };

  return (
    <>
      {/* This is the dialog itself */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger>{children}</DialogTrigger>
        <DialogContent className="sm:max-w-[425px] bg-background text-foreground">
          <DialogHeader>
            <DialogTitle>{t('login_register_dialog.title')}</DialogTitle>
          </DialogHeader>
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">
                {t('login_register_dialog.login')}
              </TabsTrigger>
              <TabsTrigger value="register">
                {t('login_register_dialog.register')}
              </TabsTrigger>
            </TabsList>

            {/* LOGIN TAB */}
            <TabsContent value="login">
              <form onSubmit={handleLogin}>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="email">
                      {t('login_register_dialog.email')}
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="Podaj email"
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="password">
                      {t('login_register_dialog.password')}
                    </Label>
                    <Input
                      id="password"
                      type="password"
                      required
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full">
                  {t('login_register_dialog.login')}
                </Button>
              </form>
            </TabsContent>

            {/* REGISTER TAB */}
            <TabsContent value="register">
              <form onSubmit={handleRegister}>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="register-email">
                      {t('login_register_dialog.email')}
                    </Label>
                    <Input
                      id="register-email"
                      type="email"
                      placeholder="Podaj email"
                      required
                      value={registerEmail}
                      onChange={(e) => setRegisterEmail(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="register-password">
                      {t('login_register_dialog.password')}
                    </Label>
                    <Input
                      id="register-password"
                      type="password"
                      required
                      value={registerPassword}
                      onChange={(e) => setRegisterPassword(e.target.value)}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="confirm-password">
                      {t('login_register_dialog.confirm_password')}
                    </Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      required
                      value={registerPassword2}
                      onChange={(e) => setRegisterPassword2(e.target.value)}
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full">
                  {t('login_register_dialog.register')}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Conditional message for registration confirmation */}
      {registrationConfirmationMessage && (
        <div className="fixed bottom-4 left-0 w-full flex justify-center z-50">
          <div className="bg-yellow-500 text-white px-4 py-2 rounded shadow-lg animate-fadeIn">
            {registrationConfirmationMessage}
          </div>
        </div>
      )}

      {/* This conditionally rendered "toast" for successful login */}
      {loginSuccessMessage && (
        <div className="fixed bottom-4 left-0 w-full flex justify-center z-50">
          <div className="bg-green-500 text-white px-4 py-2 rounded shadow-lg animate-fadeIn">
            {loginSuccessMessage}
          </div>
        </div>
      )}
    </>
  );
}
