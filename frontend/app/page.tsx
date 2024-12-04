'use client'; // Dodaj tę linię

import { useTranslation } from 'react-i18next';
import Chat from '@/components/Chat';

export default function Page() {
  const { t } = useTranslation();

  return (
      <Chat  userId={'user-123'}/>
  );
}
