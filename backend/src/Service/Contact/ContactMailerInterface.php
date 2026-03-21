<?php

namespace App\Service\Contact;

use App\Dto\ContactRequest;

interface ContactMailerInterface
{
    public function send(ContactRequest $contactRequest): void;
}
