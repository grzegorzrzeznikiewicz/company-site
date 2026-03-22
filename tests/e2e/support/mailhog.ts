import type { APIRequestContext } from '@playwright/test';

type MailHogMessage = {
  MIME?: {
    Parts?: Array<{
      Body?: string;
    }>;
  };
  Content?: {
    Headers?: Record<string, string[]>;
    Body?: string;
  };
  Raw?: {
    Data?: string;
  };
};

type MailHogListResponse = {
  items?: MailHogMessage[];
};

function getHeader(message: MailHogMessage, name: string): string {
  return message.Content?.Headers?.[name]?.[0] ?? '';
}

function getBody(message: MailHogMessage): string {
  return (
    message.MIME?.Parts?.map((part) => part.Body ?? '').join('\n') ??
    message.Content?.Body ??
    message.Raw?.Data ??
    ''
  );
}

export async function findMailhogMessageByToken(
  request: APIRequestContext,
  mailhogUrl: string,
  token: string,
): Promise<{
  from: string;
  to: string;
  subject: string;
  body: string;
} | null> {
  const response = await request.get(`${mailhogUrl}/api/v2/messages`);

  if (!response.ok()) {
    throw new Error(`MailHog request failed with status ${response.status()}.`);
  }

  const payload = (await response.json()) as MailHogListResponse;

  for (const message of payload.items ?? []) {
    const body = getBody(message);

    if (!body.includes(token)) {
      continue;
    }

    return {
      from: getHeader(message, 'From'),
      to: getHeader(message, 'To'),
      subject: getHeader(message, 'Subject'),
      body,
    };
  }

  return null;
}
