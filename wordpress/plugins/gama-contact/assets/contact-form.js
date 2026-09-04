(() => {
  'use strict';

  const config = window.gamaContactForm;
  if (!config) return;

  document.querySelectorAll('.gama-contact-form').forEach((form) => {
    const status = form.querySelector('.gama-contact-form__status');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = form.querySelector('[type="submit"]');
      const fields = ['name', 'email', 'phone', 'message'];
      fields.forEach((name) => {
        const field = form.elements.namedItem(name);
        field?.removeAttribute('aria-invalid');
        const error = form.querySelector(`[data-error-for="${name}"]`);
        if (error) error.textContent = '';
      });
      status.textContent = '';
      submit.disabled = true;
      let failureMessage = config.genericError;

      try {
        const data = Object.fromEntries(new FormData(form).entries());
        const response = await fetch(config.endpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-Gama-Contact-Nonce': config.nonce,
          },
          body: JSON.stringify(data),
        });
        const payload = await response.json();
        if (!response.ok) {
          let firstInvalidField = null;
          Object.entries(payload.field_errors ?? {}).forEach(([name, message]) => {
            const field = form.elements.namedItem(name);
            field?.setAttribute('aria-invalid', 'true');
            if (!firstInvalidField && field instanceof HTMLElement) {
              firstInvalidField = field;
            }
            const error = form.querySelector(`[data-error-for="${name}"]`);
            if (error) error.textContent = String(message);
          });
          firstInvalidField?.focus();
          failureMessage = payload.message || config.genericError;
          throw new Error('Contact submission rejected');
        }
        form.reset();
        status.textContent = payload.message;
      } catch {
        status.textContent = failureMessage;
      } finally {
        submit.disabled = false;
      }
    });
  });
})();
