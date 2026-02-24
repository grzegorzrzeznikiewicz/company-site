<?php

namespace App\Controller;

use App\Dto\ContactRequest;
use Psr\Log\LoggerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Mailer\Exception\TransportExceptionInterface;
use Symfony\Component\Mailer\MailerInterface;
use Symfony\Component\Mime\Email;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Validator\ConstraintViolationListInterface;
use Symfony\Component\Validator\Validator\ValidatorInterface;

class ContactController extends AbstractController
{
    #[Route('/api/contact', name: 'api_contact', methods: ['POST', 'OPTIONS'])]
    public function __invoke(
        Request $request,
        ValidatorInterface $validator,
        MailerInterface $mailer,
        LoggerInterface $logger,
        #[Autowire('%env(string:CONTACT_RECIPIENT)%')] string $recipient,
        #[Autowire('%env(default:CONTACT_SENDER)%')] ?string $sender = null,
    ): JsonResponse {
        if ($request->isMethod('OPTIONS')) {
            return new JsonResponse(status: Response::HTTP_NO_CONTENT);
        }

        try {
            $payload = json_decode($request->getContent(), true, 512, JSON_THROW_ON_ERROR);
        } catch (\JsonException) {
            return $this->json([
                'message' => 'Nieprawidłowy format żądania.',
            ], Response::HTTP_BAD_REQUEST);
        }

        if (!is_array($payload)) {
            return $this->json([
                'message' => 'Nieprawidłowy format żądania.',
            ], Response::HTTP_BAD_REQUEST);
        }

        $contactRequest = ContactRequest::fromArray($payload);
        $errors = $validator->validate($contactRequest);

        if (count($errors) > 0) {
            return $this->json([
                'message' => 'Proszę uzupełnić wszystkie pola.',
                'errors' => $this->formatErrors($errors),
            ], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $email = (new Email())
            ->subject('Gama Software – nowe zapytanie kontaktowe')
            ->from($sender ?: $contactRequest->email)
            ->replyTo($contactRequest->email)
            ->to($recipient)
            ->text($this->buildPlainBody($contactRequest))
            ->html($this->buildHtmlBody($contactRequest));

        try {
            $mailer->send($email);
        } catch (TransportExceptionInterface $exception) {
            $logger->error('Nie udało się wysłać wiadomości kontaktowej', [
                'exception' => $exception,
            ]);

            return $this->json([
                'message' => 'Nie udało się wysłać wiadomości. Spróbuj ponownie później.',
            ], Response::HTTP_BAD_GATEWAY);
        }

        return $this->json([
            'message' => 'Dziękujemy! Wrócimy do Ciebie wkrótce.',
        ], Response::HTTP_CREATED);
    }

    /**
     * @return array<string, array<int, string>>
     */
    private function formatErrors(ConstraintViolationListInterface $errors): array
    {
        $formatted = [];

        foreach ($errors as $error) {
            $formatted[$error->getPropertyPath()][] = $error->getMessage();
        }

        return $formatted;
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
            sprintf('<p><strong>Imię i nazwisko:</strong> %s</p>', htmlspecialchars($request->name ?? '')),
            sprintf('<p><strong>E-mail:</strong> %s</p>', htmlspecialchars($request->email ?? '')),
            sprintf('<p><strong>Telefon:</strong> %s</p>', htmlspecialchars($request->phone ?? '')),
            '<p><strong>Wiadomość:</strong></p>',
            sprintf('<p style="white-space:pre-line">%s</p>', htmlspecialchars($request->message ?? '')),
        ];

        return implode("\n", $lines);
    }
}
