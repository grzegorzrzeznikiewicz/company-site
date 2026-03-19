<?php

namespace App\Dto;

use Symfony\Component\Validator\Constraints as Assert;

class ContactRequest
{
    #[Assert\NotBlank(message: 'Podaj swoje imię i nazwisko.')]
    #[Assert\Length(max: 120)]
    public ?string $name = null;

    #[Assert\NotBlank(message: 'Adres e-mail jest wymagany.')]
    #[Assert\Email(message: 'Podaj poprawny adres e-mail.')]
    #[Assert\Length(max: 180)]
    public ?string $email = null;

    #[Assert\NotBlank(message: 'Podaj numer telefonu.')]
    #[Assert\Length(max: 40)]
    public ?string $phone = null;

    #[Assert\NotBlank(message: 'Wiadomość nie może być pusta.')]
    #[Assert\Length(max: 1000)]
    public ?string $message = null;

    public static function fromArray(array $payload): self
    {
        $dto = new self();
        $dto->name = isset($payload['name']) ? (string) $payload['name'] : null;
        $dto->email = isset($payload['email']) ? (string) $payload['email'] : null;
        $dto->phone = isset($payload['phone']) ? (string) $payload['phone'] : null;
        $dto->message = isset($payload['message']) ? (string) $payload['message'] : null;

        return $dto;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'email' => $this->email,
            'phone' => $this->phone,
            'message' => $this->message,
        ];
    }
}
