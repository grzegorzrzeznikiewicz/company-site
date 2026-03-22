<?php

namespace App\Controller;

use App\Dto\ContactRequest;
use App\Exception\ContactDeliveryException;
use App\Service\Contact\ContactMailerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Validator\ConstraintViolationListInterface;
use Symfony\Component\Validator\Validator\ValidatorInterface;

class ContactController
{
    #[Route('/api/contact', name: 'api_contact', methods: ['POST', 'OPTIONS'])]
    public function __invoke(
        Request $request,
        ValidatorInterface $validator,
        ContactMailerInterface $contactMailer,
    ): JsonResponse {
        if ($request->isMethod('OPTIONS')) {
            return new JsonResponse(status: Response::HTTP_NO_CONTENT);
        }

        try {
            $payload = json_decode($request->getContent(), true, 512, JSON_THROW_ON_ERROR);
        } catch (\JsonException) {
            return new JsonResponse([
                'message' => 'Nieprawidłowy format żądania.',
            ], Response::HTTP_BAD_REQUEST);
        }

        if (!is_array($payload)) {
            return new JsonResponse([
                'message' => 'Nieprawidłowy format żądania.',
            ], Response::HTTP_BAD_REQUEST);
        }

        $contactRequest = ContactRequest::fromArray($payload);
        $errors = $validator->validate($contactRequest);

        if (count($errors) > 0) {
            return new JsonResponse([
                'message' => 'Proszę uzupełnić wszystkie pola.',
                'errors' => $this->formatErrors($errors),
            ], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        try {
            $contactMailer->send($contactRequest);
        } catch (ContactDeliveryException) {
            return new JsonResponse([
                'message' => 'Nie udało się wysłać wiadomości. Spróbuj ponownie później.',
            ], Response::HTTP_BAD_GATEWAY);
        }

        return new JsonResponse([
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
}
