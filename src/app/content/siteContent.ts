import {
  Bot,
  MessageCircle,
  Package,
  ShoppingCart,
  type LucideIcon,
} from 'lucide-react';

type NavigationItem = {
  id: string;
  label: string;
};

type Service = {
  title: string;
  description: string;
  icon: LucideIcon;
};

type Module = {
  title: string;
  description: string;
  icon: LucideIcon;
  features: string[];
};

export const NAVIGATION_ITEMS: NavigationItem[] = [
  { id: 'home', label: 'Start' },
  { id: 'services', label: 'Usługi' },
  { id: 'modules', label: 'Moduły' },
  { id: 'blog', label: 'Blog' },
  { id: 'contact', label: 'Kontakt' },
];

export const SERVICES: Service[] = [
  {
    title: 'Wdrożenia E-commerce',
    description:
      'Kompleksowe wdrożenia platform e-commerce, w tym Magento 2, dostosowane do potrzeb Twojego biznesu. Od analizy wymagań po uruchomienie sklepu.',
    icon: ShoppingCart,
  },
  {
    title: 'Konsultacje E-commerce',
    description:
      'Profesjonalne doradztwo w zakresie strategii e-commerce, optymalizacji procesów sprzedażowych oraz wyboru najlepszych rozwiązań technologicznych.',
    icon: MessageCircle,
  },
  {
    title: 'Agenci AI',
    description:
      'Budujemy inteligentnych asystentów AI, którzy automatyzują obsługę klienta, wspierają sprzedaż i podnoszą efektywność Twojego biznesu online.',
    icon: Bot,
  },
];

export const MODULES: Module[] = [
  {
    title: 'Advanced SEO Suite',
    description: 'Kompleksowe narzędzie do optymalizacji SEO',
    icon: Package,
    features: [
      'Automatyczne generowanie meta tagów',
      'Optymalizacja URL',
      'Rich snippets',
      'Sitemap XML',
      'Analiza SEO on-page',
    ],
  },
  {
    title: 'Smart Product Recommendations',
    description: 'AI-powered rekomendacje produktów',
    icon: Package,
    features: [
      'Algorytmy uczenia maszynowego',
      'Personalizacja dla użytkownika',
      'Cross-selling i up-selling',
      'Analityka skuteczności',
      'A/B testing',
    ],
  },
  {
    title: 'Enhanced Checkout',
    description: 'Zoptymalizowany proces zakupowy',
    icon: Package,
    features: [
      'One-step checkout',
      'Autouzupełnianie adresów',
      'Integracje z kurierami',
      'Płatności Express',
      'Optymalizacja konwersji',
    ],
  },
  {
    title: 'Inventory Management Pro',
    description: 'Zaawansowane zarządzanie magazynem',
    icon: Package,
    features: [
      'Multi-warehouse support',
      'Automatyczne powiadomienia',
      'Prognozowanie zapasów',
      'Integracja z ERP',
      'Raporty i analityka',
    ],
  },
  {
    title: 'Customer Loyalty Program',
    description: 'Program lojalnościowy dla klientów',
    icon: Package,
    features: [
      'System punktów i nagród',
      'Poziomy lojalnościowe',
      'Spersonalizowane promocje',
      'Gamifikacja',
      'Integracja z newsletter',
    ],
  },
  {
    title: 'Performance Optimizer',
    description: 'Optymalizacja wydajności sklepu',
    icon: Package,
    features: [
      'Lazy loading obrazów',
      'Optymalizacja bazy danych',
      'Cache management',
      'CDN integration',
      'Monitoring wydajności',
    ],
  },
];
