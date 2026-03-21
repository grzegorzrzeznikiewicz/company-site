<?php

namespace App\Tests\Dto;

use App\Dto\ContactRequest;
use PHPUnit\Framework\TestCase;
use Symfony\Component\Validator\Validation;

final class ContactRequestTest extends TestCase
{
    public function testValidatesContactPayloadWithAttributes(): void
    {
        $validator = Validation::createValidatorBuilder()
            ->enableAttributeMapping()
            ->getValidator();

        $dto = ContactRequest::fromArray([
            'name' => '',
            'email' => 'invalid-email',
            'phone' => '',
            'message' => '',
        ]);

        $violations = $validator->validate($dto);

        self::assertCount(4, $violations);
    }
}
