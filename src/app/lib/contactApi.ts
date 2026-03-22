import type { ContactFormValues } from '../types/contact';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof apiBaseUrl === 'string' ? apiBaseUrl : 'http://localhost:8080';

type ContactApiPayload = {
  message?: string;
  errors?: Partial<Record<keyof ContactFormValues, string[]>>;
};

export class ContactApiError extends Error {
  status: number;
  fieldErrors?: Partial<Record<keyof ContactFormValues, string[]>>;

  constructor(
    message: string,
    status: number,
    fieldErrors?: Partial<Record<keyof ContactFormValues, string[]>>,
  ) {
    super(message);
    this.name = 'ContactApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

export async function submitContactRequest(
  values: ContactFormValues,
): Promise<{ message: string }> {
  const endpoint = `${API_BASE_URL.replace(/\/$/, '')}/api/contact`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(values),
  });

  const payload = (await response.json().catch(() => ({
    message: 'Nie udało się przetworzyć odpowiedzi serwera.',
  }))) as ContactApiPayload;

  if (!response.ok) {
    throw new ContactApiError(
      payload.message ?? 'Nie udało się wysłać wiadomości. Spróbuj ponownie.',
      response.status,
      payload.errors,
    );
  }

  return {
    message: payload.message ?? 'Dziękujemy! Wkrótce się odezwiemy.',
  };
}
