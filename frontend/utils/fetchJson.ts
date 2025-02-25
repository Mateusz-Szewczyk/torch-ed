// src/utils/fetchJson.ts

export async function fetchJson<T>(
  input: RequestInfo,
  init?: RequestInit
): Promise<T> {
  // Domyślne ustawienia z `credentials: 'include'`
  const defaultInit: RequestInit = {
    credentials: 'include', // Umożliwia przesyłanie ciasteczek i uwierzytelnienie
  };

  // Łączenie domyślnych opcji z przekazanymi w `init`
  const finalInit = { ...defaultInit, ...init };

  // Wykonanie zapytania
  const response = await fetch(input, finalInit);

  // Sprawdzenie statusu odpowiedzi
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || response.statusText;
    throw new Error(errorMessage);
  }

  // Zwrot danych odpowiedzi w postaci JSON
  const data: T = await response.json();
  return data;
}
