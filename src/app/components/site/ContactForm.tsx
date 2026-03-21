import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { ContactApiError, submitContactRequest } from '../../lib/contactApi';
import type { ContactFormValues } from '../../types/contact';
import { Button } from '../ui/button';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '../ui/form';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';

type FormStatus =
  | { state: 'idle' }
  | { state: 'success'; message: string }
  | { state: 'error'; message: string };

const DEFAULT_VALUES: ContactFormValues = {
  name: '',
  email: '',
  phone: '',
  message: '',
};

export function ContactForm() {
  const [formStatus, setFormStatus] = useState<FormStatus>({ state: 'idle' });
  const form = useForm<ContactFormValues>({
    defaultValues: DEFAULT_VALUES,
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    setFormStatus({ state: 'idle' });
    form.clearErrors();

    try {
      const response = await submitContactRequest(values);

      form.reset(DEFAULT_VALUES);
      setFormStatus({
        state: 'success',
        message: response.message,
      });
    } catch (error) {
      if (error instanceof ContactApiError) {
        if (error.fieldErrors) {
          for (const [fieldName, messages] of Object.entries(error.fieldErrors)) {
            const message = messages?.[0];

            if (message) {
              form.setError(fieldName as keyof ContactFormValues, {
                type: 'server',
                message,
              });
            }
          }
        }

        setFormStatus({
          state: 'error',
          message: error.message,
        });

        return;
      }

      setFormStatus({
        state: 'error',
        message: 'Coś poszło nie tak. Spróbuj ponownie później.',
      });
    }
  });

  const fieldClassName = 'mt-1';

  return (
    <Form {...form}>
      <form
        noValidate
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
        className="space-y-4"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="name"
            rules={{
              required: 'Podaj swoje imię i nazwisko.',
            }}
            render={({ field }) => (
              <FormItem className="text-left">
                <FormLabel>Imię i nazwisko</FormLabel>
                <FormControl>
                  <Input {...field} className={fieldClassName} autoComplete="name" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="email"
            rules={{
              required: 'Adres e-mail jest wymagany.',
            }}
            render={({ field }) => (
              <FormItem className="text-left">
                <FormLabel>E-mail</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="email"
                    className={fieldClassName}
                    autoComplete="email"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="phone"
          rules={{
            required: 'Podaj numer telefonu.',
          }}
          render={({ field }) => (
            <FormItem className="text-left">
              <FormLabel>Telefon</FormLabel>
              <FormControl>
                <Input {...field} type="tel" className={fieldClassName} autoComplete="tel" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="message"
          rules={{
            required: 'Wiadomość nie może być pusta.',
          }}
          render={({ field }) => (
            <FormItem className="text-left">
              <FormLabel>Wiadomość</FormLabel>
              <FormControl>
                <Textarea {...field} rows={5} className={fieldClassName} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="space-y-3 pt-2 text-center">
          <Button
            type="submit"
            size="lg"
            disabled={form.formState.isSubmitting}
            className="bg-blue-600 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {form.formState.isSubmitting ? 'Wysyłanie...' : 'Wyślij wiadomość'}
          </Button>

          {formStatus.state === 'success' && (
            <p className="text-sm text-green-600" aria-live="polite">
              {formStatus.message}
            </p>
          )}

          {formStatus.state === 'error' && (
            <p className="text-sm text-red-600" aria-live="polite">
              {formStatus.message}
            </p>
          )}
        </div>
      </form>
    </Form>
  );
}
