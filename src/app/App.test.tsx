import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import App from './App';

describe('App navigation', () => {
  it('toggles the mobile navigation menu with accessible attributes', async () => {
    const user = userEvent.setup();

    render(<App />);

    const toggleButton = screen.getByRole('button', {
      name: 'Otwórz menu nawigacyjne',
    });

    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggleButton);

    expect(
      screen.getByRole('button', { name: 'Zamknij menu nawigacyjne' }),
    ).toHaveAttribute('aria-expanded', 'true');
    expect(document.getElementById('mobile-navigation-menu')).not.toBeNull();
  });
});
