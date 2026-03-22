<?php

namespace App\Tests\Service;

use App\Dto\ContactRequest;
use App\Exception\ContactDeliveryException;
use App\Service\Contact\ContactMailer;
use PHPUnit\Framework\TestCase;
use Psr\Log\NullLogger;
use Symfony\Component\Mailer\Exception\TransportException;
use Symfony\Component\Mailer\MailerInterface;
use Symfony\Component\Mime\Email;

final class ContactMailerTest extends TestCase
{
    public function testBuildsMessageWithConfiguredSenderAndReplyTo(): void
    {
        $mailer = $this->createMock(MailerInterface::class);
        $contactMailer = new ContactMailer(
            $mailer,
            new NullLogger(),
            'founders@gama-software.com',
            'no-reply@gama-software.com',
        );

        $request = ContactRequest::fromArray([
            'name' => 'Jan Kowalski',
            'email' => 'jan@example.com',
            'phone' => '123456789',
            'message' => 'Dzień dobry',
        ]);

        $mailer
            ->expects(self::once())
            ->method('send')
            ->with(self::callback(function (Email $email): bool {
                self::assertSame('no-reply@gama-software.com', $email->getFrom()[0]->getAddress());
                self::assertSame('jan@example.com', $email->getReplyTo()[0]->getAddress());
                self::assertSame('founders@gama-software.com', $email->getTo()[0]->getAddress());
                self::assertStringContainsString('Jan Kowalski', $email->getTextBody() ?? '');
                self::assertStringContainsString('Dzień dobry', $email->getHtmlBody() ?? '');

                return true;
            }));

        $contactMailer->send($request);
    }

    public function testWrapsTransportErrorsWithDomainException(): void
    {
        $mailer = $this->createMock(MailerInterface::class);
        $contactMailer = new ContactMailer(
            $mailer,
            new NullLogger(),
            'founders@gama-software.com',
            'no-reply@gama-software.com',
        );

        $request = ContactRequest::fromArray([
            'name' => 'Jan Kowalski',
            'email' => 'jan@example.com',
            'phone' => '123456789',
            'message' => 'Dzień dobry',
        ]);

        $mailer
            ->expects(self::once())
            ->method('send')
            ->willThrowException(new TransportException('SMTP unavailable'));

        $this->expectException(ContactDeliveryException::class);

        $contactMailer->send($request);
    }
}
