import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ContactForm } from './ContactForm';

describe('ContactForm', () => {
  beforeEach(() => {
    vi.spyOn(global, 'fetch');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function fillForm(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText('Imię i nazwisko'), 'Jan Kowalski');
    await user.type(screen.getByLabelText('E-mail'), 'jan@example.com');
    await user.type(screen.getByLabelText('Telefon'), '123456789');
    await user.type(screen.getByLabelText('Wiadomość'), 'Dzień dobry');
  }

  it('submits the form and resets fields after success', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ message: 'Dziękujemy! Wrócimy do Ciebie wkrótce.' }),
        {
          status: 201,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      ),
    );

    render(<ContactForm />);

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: 'Wyślij wiadomość' }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    expect(
      screen.getByText('Dziękujemy! Wrócimy do Ciebie wkrótce.'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Imię i nazwisko')).toHaveValue('');
    expect(screen.getByLabelText('Wiadomość')).toHaveValue('');
  });

  it('maps backend validation errors to form fields', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          message: 'Proszę uzupełnić wszystkie pola.',
          errors: {
            email: ['Podaj poprawny adres e-mail.'],
            message: ['Wiadomość nie może być pusta.'],
          },
        }),
        {
          status: 422,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      ),
    );

    render(<ContactForm />);

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: 'Wyślij wiadomość' }));

    expect(
      await screen.findByText('Podaj poprawny adres e-mail.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Wiadomość nie może być pusta.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Proszę uzupełnić wszystkie pola.'),
    ).toBeInTheDocument();
  });

  it('shows a general transport error when the request fails', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockRejectedValue(new Error('Network down'));

    render(<ContactForm />);

    await fillForm(user);
    await user.click(screen.getByRole('button', { name: 'Wyślij wiadomość' }));

    expect(
      await screen.findByText('Coś poszło nie tak. Spróbuj ponownie później.'),
    ).toBeInTheDocument();
  });
});
