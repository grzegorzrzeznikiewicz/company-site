<?php

namespace App\Tests\Controller;

use App\Controller\ContactController;
use App\Dto\ContactRequest;
use App\Exception\ContactDeliveryException;
use App\Service\Contact\ContactMailerInterface;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Validator\ConstraintViolation;
use Symfony\Component\Validator\ConstraintViolationList;
use Symfony\Component\Validator\Validator\ValidatorInterface;

final class ContactControllerTest extends TestCase
{
    public function testReturnsBadRequestForMalformedJson(): void
    {
        $controller = new ContactController();
        $validator = $this->createMock(ValidatorInterface::class);
        $mailer = $this->createMock(ContactMailerInterface::class);

        $validator->expects(self::never())->method('validate');
        $mailer->expects(self::never())->method('send');

        $response = $controller(
            Request::create('/api/contact', 'POST', server: [], content: '{"name":'),
            $validator,
            $mailer,
        );

        self::assertSame(Response::HTTP_BAD_REQUEST, $response->getStatusCode());
        self::assertSame(
            ['message' => 'Nieprawidłowy format żądania.'],
            json_decode((string) $response->getContent(), true, 512, JSON_THROW_ON_ERROR),
        );
    }

    public function testReturnsValidationErrorsPerField(): void
    {
        $controller = new ContactController();
        $validator = $this->createMock(ValidatorInterface::class);
        $mailer = $this->createMock(ContactMailerInterface::class);

        $violations = new ConstraintViolationList([
            new ConstraintViolation('Podaj poprawny adres e-mail.', '', [], null, 'email', 'zly-email'),
            new ConstraintViolation('Wiadomość nie może być pusta.', '', [], null, 'message', ''),
        ]);

        $validator
            ->expects(self::once())
            ->method('validate')
            ->with(self::isInstanceOf(ContactRequest::class))
            ->willReturn($violations);

        $mailer->expects(self::never())->method('send');

        $response = $controller(
            Request::create(
                '/api/contact',
                'POST',
                server: [],
                content: json_encode([
                    'name' => 'Jan Kowalski',
                    'email' => 'zly-email',
                    'phone' => '123456789',
                    'message' => '',
                ], JSON_THROW_ON_ERROR),
            ),
            $validator,
            $mailer,
        );

        self::assertSame(Response::HTTP_UNPROCESSABLE_ENTITY, $response->getStatusCode());
        self::assertSame(
            [
                'message' => 'Proszę uzupełnić wszystkie pola.',
                'errors' => [
                    'email' => ['Podaj poprawny adres e-mail.'],
                    'message' => ['Wiadomość nie może być pusta.'],
                ],
            ],
            json_decode((string) $response->getContent(), true, 512, JSON_THROW_ON_ERROR),
        );
    }

    public function testReturnsBadGatewayWhenDeliveryFails(): void
    {
        $controller = new ContactController();
        $validator = $this->createMock(ValidatorInterface::class);
        $mailer = $this->createMock(ContactMailerInterface::class);

        $validator->method('validate')->willReturn(new ConstraintViolationList());
        $mailer
            ->expects(self::once())
            ->method('send')
            ->willThrowException(new ContactDeliveryException('Transport error'));

        $response = $controller(
            Request::create(
                '/api/contact',
                'POST',
                server: [],
                content: json_encode([
                    'name' => 'Jan Kowalski',
                    'email' => 'jan@example.com',
                    'phone' => '123456789',
                    'message' => 'Dzień dobry',
                ], JSON_THROW_ON_ERROR),
            ),
            $validator,
            $mailer,
        );

        self::assertSame(Response::HTTP_BAD_GATEWAY, $response->getStatusCode());
        self::assertSame(
            ['message' => 'Nie udało się wysłać wiadomości. Spróbuj ponownie później.'],
            json_decode((string) $response->getContent(), true, 512, JSON_THROW_ON_ERROR),
        );
    }
}
