<?php

namespace App\Controller\Admin;

use EasyCorp\Bundle\EasyAdminBundle\Config\Dashboard;
use EasyCorp\Bundle\EasyAdminBundle\Config\MenuItem;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractDashboardController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class DashboardController extends AbstractDashboardController
{
    #[Route('/admin', name: 'admin')]
    public function index(): Response
    {
        return $this->render('admin/dashboard.html.twig', [
            'modules' => [
                [
                    'title' => 'Strony CMS',
                    'description' => 'Zarządzaj treściami landing page, sekcją usług i stopką.',
                    'cta' => 'Dodaj encję Page + blokowy edytor w EasyAdmin.',
                ],
                [
                    'title' => 'Blog / Wiedza',
                    'description' => 'Plan publikacji artykułów, SEO i tagowanie.',
                    'cta' => 'Wprowadź encję Post z workflow Draft → Published.',
                ],
                [
                    'title' => 'Leady kontaktowe',
                    'description' => 'Historia zgłoszeń z formularza + notatki follow-up.',
                    'cta' => 'Zapisuj dane w DB i dodaj eksport CSV/Slack webhook.',
                ],
            ],
        ]);
    }

    public function configureDashboard(): Dashboard
    {
        return Dashboard::new()
            ->setTitle($this->getParameter('app.admin_panel_title'))
            ->renderContentMaximized();
    }

    public function configureMenuItems(): iterable
    {
        yield MenuItem::linkToRoute('Pulpit', 'fa fa-home', 'admin');

        yield MenuItem::section('CMS & treści');
        yield MenuItem::linkToUrl('Strony CMS', 'fa fa-file-text', '#')
            ->setBadge('w przygotowaniu', 'secondary');
        yield MenuItem::linkToUrl('Blog / Wpisy', 'fa fa-pen', '#')
            ->setBadge('w przygotowaniu', 'secondary');

        yield MenuItem::section('Leady i automatyzacje');
        yield MenuItem::linkToUrl('Lista leadów', 'fa fa-inbox', '#')
            ->setBadge('soon', 'info');
        yield MenuItem::linkToUrl('Eksport / Automation', 'fa fa-gear', '#');
    }
}
