<?php

namespace App\Service\Contact;

use App\Dto\ContactRequest;
use App\Exception\ContactDeliveryException;
use Psr\Log\LoggerInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\Mailer\Exception\TransportExceptionInterface;
use Symfony\Component\Mailer\MailerInterface;
use Symfony\Component\Mime\Email;

final class ContactMailer implements ContactMailerInterface
{
    public function __construct(
        private readonly MailerInterface $mailer,
        private readonly LoggerInterface $logger,
        #[Autowire('%env(string:CONTACT_RECIPIENT)%')] private readonly string $recipient,
        #[Autowire('%env(string:CONTACT_SENDER)%')] private readonly string $sender,
    ) {
    }

    public function send(ContactRequest $contactRequest): void
    {
        $email = (new Email())
            ->subject('Gama Software – nowe zapytanie kontaktowe')
            ->from($this->sender)
            ->replyTo($contactRequest->email ?? $this->sender)
            ->to($this->recipient)
            ->text($this->buildPlainBody($contactRequest))
            ->html($this->buildHtmlBody($contactRequest));

        try {
            $this->mailer->send($email);
        } catch (TransportExceptionInterface $exception) {
            $this->logger->error('Nie udało się wysłać wiadomości kontaktowej', [
                'exception' => $exception,
            ]);

            throw new ContactDeliveryException('Wysyłka wiadomości kontaktowej nie powiodła się.', 0, $exception);
        }
    }

    private function buildPlainBody(ContactRequest $request): string
    {
        return sprintf(
            "Nowa wiadomość ze strony firmowej:\n\nImię i nazwisko: %s\nE-mail: %s\nTelefon: %s\n\nWiadomość:\n%s\n",
            $request->name,
            $request->email,
            $request->phone,
            $request->message,
        );
    }

    private function buildHtmlBody(ContactRequest $request): string
    {
        $lines = [
            '<p><strong>Nowa wiadomość ze strony firmowej:</strong></p>',
            sprintf('<p><strong>Imię i nazwisko:</strong> %s</p>', $this->escape($request->name)),
            sprintf('<p><strong>E-mail:</strong> %s</p>', $this->escape($request->email)),
            sprintf('<p><strong>Telefon:</strong> %s</p>', $this->escape($request->phone)),
            '<p><strong>Wiadomość:</strong></p>',
            sprintf('<p style="white-space:pre-line">%s</p>', $this->escape($request->message)),
        ];

        return implode("\n", $lines);
    }

    private function escape(?string $value): string
    {
        return htmlspecialchars((string) $value, \ENT_QUOTES | \ENT_SUBSTITUTE, 'UTF-8');
    }
}
