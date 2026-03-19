import { useState } from 'react';
import logo from '../assets/606550a668ee67574ee51adad0d7a231ffcce05b.png';
import logoOptimized from '../assets/logo-256.webp';
import logoOptimizedLarge from '../assets/logo-512.webp';
import { Menu, X, ShoppingCart, MessageCircle, Bot, Package } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { cn } from './components/ui/utils';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080';

type BrandLogoProps = {
  className?: string;
  loading?: 'eager' | 'lazy';
  intrinsicSize?: number;
};

const BrandLogo = ({ className, loading = 'eager', intrinsicSize = 96 }: BrandLogoProps) => (
  <picture>
    <source srcSet={`${logoOptimized} 1x, ${logoOptimizedLarge} 2x`} type="image/webp" />
    <img
      src={logo}
      alt="Gama Software"
      width={intrinsicSize}
      height={intrinsicSize}
      loading={loading}
      decoding="async"
      className={cn('h-auto', className)}
    />
  </picture>
);

function App() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    message: ''
  });
  const [formStatus, setFormStatus] = useState<{ state: 'idle' | 'loading' | 'success' | 'error'; message?: string }>({
    state: 'idle'
  });

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setMobileMenuOpen(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormStatus({ state: 'loading' });

    const endpoint = `${API_BASE_URL.replace(/\/$/, '')}/api/contact`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      const payload = await response
        .json()
        .catch(() => ({ message: 'Nie udało się przetworzyć odpowiedzi serwera.' }));

      if (!response.ok) {
        setFormStatus({
          state: 'error',
          message: payload?.message ?? 'Nie udało się wysłać wiadomości. Spróbuj ponownie.'
        });
        return;
      }

      setFormStatus({
        state: 'success',
        message: payload?.message ?? 'Dziękujemy! Wkrótce się odezwiemy.'
      });
      setFormData({ name: '', email: '', phone: '', message: '' });
    } catch (error) {
      console.error('Contact form submission failed', error);
      setFormStatus({ state: 'error', message: 'Coś poszło nie tak. Spróbuj ponownie później.' });
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-white/95 backdrop-blur-sm border-b border-gray-200 z-50" aria-label="Główna nawigacja">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center">
              <BrandLogo className="w-16 md:w-20 drop-shadow-lg mix-blend-multiply" intrinsicSize={80} />
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex space-x-8">
              <button 
                onClick={() => scrollToSection('home')}
                className="text-gray-700 hover:text-blue-600 transition-colors"
              >
                Start
              </button>
              <button 
                onClick={() => scrollToSection('services')}
                className="text-gray-700 hover:text-blue-600 transition-colors"
              >
                Usługi
              </button>
              <button 
                onClick={() => scrollToSection('modules')}
                className="text-gray-700 hover:text-blue-600 transition-colors"
              >
                Moduły
              </button>
              <button 
                onClick={() => scrollToSection('blog')}
                className="text-gray-700 hover:text-blue-600 transition-colors"
              >
                Blog
              </button>
              <button 
                onClick={() => scrollToSection('contact')}
                className="text-gray-700 hover:text-blue-600 transition-colors"
              >
                Kontakt
              </button>
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="text-gray-700 hover:text-blue-600"
                aria-label={mobileMenuOpen ? 'Zamknij menu nawigacji' : 'Otwórz menu nawigacji'}
                aria-expanded={mobileMenuOpen}
                aria-controls="mobile-navigation"
              >
                {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 bg-white" id="mobile-navigation">
            <div className="px-4 pt-2 pb-3 space-y-1">
              <button 
                onClick={() => scrollToSection('home')}
                className="block w-full text-left px-3 py-2 text-gray-700 hover:text-blue-600 hover:bg-gray-50 rounded-md"
              >
                Start
              </button>
              <button 
                onClick={() => scrollToSection('services')}
                className="block w-full text-left px-3 py-2 text-gray-700 hover:text-blue-600 hover:bg-gray-50 rounded-md"
              >
                Usługi
              </button>
              <button 
                onClick={() => scrollToSection('modules')}
                className="block w-full text-left px-3 py-2 text-gray-700 hover:text-blue-600 hover:bg-gray-50 rounded-md"
              >
                Moduły
              </button>
              <button 
                onClick={() => scrollToSection('blog')}
                className="block w-full text-left px-3 py-2 text-gray-700 hover:text-blue-600 hover:bg-gray-50 rounded-md"
              >
                Blog
              </button>
              <button 
                onClick={() => scrollToSection('contact')}
                className="block w-full text-left px-3 py-2 text-gray-700 hover:text-blue-600 hover:bg-gray-50 rounded-md"
              >
                Kontakt
              </button>
            </div>
          </div>
        )}
      </nav>

      <main id="main-content" className="pt-32">
        {/* Hero Section */}
        <section id="home" className="pb-20 px-4">
          <div className="max-w-7xl mx-auto text-center">
            <h1 className="text-5xl md:text-6xl mb-6 text-gray-900">
              Gama Software
            </h1>
            <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-8">
              Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI dla Twojego biznesu
            </p>
            <Button
              size="lg"
              onClick={() => scrollToSection('services')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-6 text-lg"
            >
              Poznaj nasze usługi
            </Button>
          </div>
        </section>

        {/* Services Section */}
        <section id="services" className="py-20 px-4 bg-gray-50">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-4xl text-center mb-12 text-gray-900">
              Nasze Usługi
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
            <div>
              <Card className="border-none shadow-lg hover:shadow-xl transition-shadow">
                <CardHeader>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <ShoppingCart className="text-blue-600" size={24} />
                  </div>
                  <CardTitle>Wdrożenia E-commerce</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    Kompleksowe wdrożenia platform e-commerce, w tym Magento 2, dostosowane do potrzeb Twojego biznesu. Od analizy wymagań po uruchomienie sklepu.
                  </CardDescription>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="border-none shadow-lg hover:shadow-xl transition-shadow">
                <CardHeader>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <MessageCircle className="text-blue-600" size={24} />
                  </div>
                  <CardTitle>Konsultacje E-commerce</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    Profesjonalne doradztwo w zakresie strategii e-commerce, optymalizacji procesów sprzedażowych oraz wyboru najlepszych rozwiązań technologicznych.
                  </CardDescription>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="border-none shadow-lg hover:shadow-xl transition-shadow">
                <CardHeader>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                    <Bot className="text-blue-600" size={24} />
                  </div>
                  <CardTitle>Agenci AI</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    Budujemy inteligentnych asystentów AI, którzy automatyzują obsługę klienta, wspierają sprzedaż i podnoszą efektywność Twojego biznesu online.
                  </CardDescription>
                </CardContent>
              </Card>
            </div>
            </div>
          </div>
        </section>

        {/* Modules Section */}
        <section id="modules" className="py-20 px-4">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-4xl mb-4 text-gray-900">Moduły Magento 2</h2>
              <p className="text-xl text-gray-600">
                Profesjonalne rozszerzenia dostępne w modelu subskrypcji
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="mb-2">Advanced SEO Suite</CardTitle>
                      <CardDescription>
                        Kompleksowe narzędzie do optymalizacji SEO
                      </CardDescription>
                    </div>
                    <Package className="text-blue-600" size={24} />
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• Automatyczne generowanie meta tagów</li>
                    <li>• Optymalizacja URL</li>
                    <li>• Rich snippets</li>
                    <li>• Sitemap XML</li>
                    <li>• Analiza SEO on-page</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="mb-2">Smart Product Recommendations</CardTitle>
                      <CardDescription>
                        AI-powered rekomendacje produktów
                      </CardDescription>
                    </div>
                    <Package className="text-blue-600" size={24} />
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• Algorytmy uczenia maszynowego</li>
                    <li>• Personalizacja dla użytkownika</li>
                    <li>• Cross-selling i up-selling</li>
                    <li>• Analityka skuteczności</li>
                    <li>• A/B testing</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="mb-2">Enhanced Checkout</CardTitle>
                      <CardDescription>
                        Zoptymalizowany proces zakupowy
                      </CardDescription>
                    </div>
                    <Package className="text-blue-600" size={24} />
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• One-step checkout</li>
                    <li>• Autouzupełnianie adresów</li>
                    <li>• Integracje z kurierami</li>
                    <li>• Płatności Express</li>
                    <li>• Optymalizacja konwersji</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="mb-2">Inventory Management Pro</CardTitle>
                      <CardDescription>
                        Zaawansowane zarządzanie magazynem
                      </CardDescription>
                    </div>
                    <Package className="text-blue-600" size={24} />
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• Multi-warehouse support</li>
                    <li>• Automatyczne powiadomienia</li>
                    <li>• Prognozowanie zapasów</li>
                    <li>• Integracja z ERP</li>
                    <li>• Raporty i analityka</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="mb-2">Customer Loyalty Program</CardTitle>
                      <CardDescription>
                        Program lojalnościowy dla klientów
                      </CardDescription>
                    </div>
                    <Package className="text-blue-600" size={24} />
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• System punktów i nagród</li>
                    <li>• Poziomy lojalnościowe</li>
                    <li>• Spersonalizowane promocje</li>
                    <li>• Gamifikacja</li>
                    <li>• Integracja z newsletter</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <div>
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="mb-2">Performance Optimizer</CardTitle>
                      <CardDescription>
                        Optymalizacja wydajności sklepu
                      </CardDescription>
                    </div>
                    <Package className="text-blue-600" size={24} />
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• Lazy loading obrazów</li>
                    <li>• Optymalizacja bazy danych</li>
                    <li>• Cache management</li>
                    <li>• CDN integration</li>
                    <li>• Monitoring wydajności</li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="text-center mt-12">
            <p className="text-gray-600 mb-4">
              Wkrótce dostępne w formie subskrypcji
            </p>
            <Button 
              size="lg"
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Zapisz się na listę oczekujących
            </Button>
            </div>
          </div>
        </section>

        {/* Blog Section */}
        <section id="blog" className="py-20 px-4 bg-gray-50">
          <div className="max-w-7xl mx-auto text-center">
            <h2 className="text-4xl mb-6 text-gray-900">Blog</h2>
            <div className="bg-white rounded-lg shadow-md p-12 max-w-2xl mx-auto">
              <div className="text-6xl mb-4">🚧</div>
              <h3 className="text-2xl mb-4 text-gray-900">W budowie</h3>
              <p className="text-gray-600">
                Nasz blog jest obecnie w przygotowaniu. Wkrótce znajdziesz tutaj cenne artykuły o e-commerce, technologiach AI i najlepszych praktykach w branży.
              </p>
            </div>
          </div>
        </section>

        {/* Contact Section */}
        <section id="contact" className="py-20 px-4">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-4xl text-center mb-6 text-gray-900">
              Kontakt
            </h2>
            <div className="bg-white rounded-lg shadow-md p-8 md:p-12 max-w-2xl mx-auto">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="text-left">
                  <Label htmlFor="name">Imię i nazwisko</Label>
                  <Input 
                    type="text" 
                    id="name" 
                    name="name" 
                    value={formData.name} 
                    onChange={handleChange} 
                    required 
                    className="mt-1"
                  />
                </div>
                <div className="text-left">
                  <Label htmlFor="email">E-mail</Label>
                  <Input 
                    type="email" 
                    id="email" 
                    name="email" 
                    value={formData.email} 
                    onChange={handleChange} 
                    required 
                    className="mt-1"
                  />
                </div>
              </div>
              <div className="text-left">
                <Label htmlFor="phone">Telefon</Label>
                <Input 
                  type="tel" 
                  id="phone" 
                  name="phone" 
                  value={formData.phone} 
                  onChange={handleChange} 
                  required 
                  className="mt-1"
                />
              </div>
              <div className="text-left">
                <Label htmlFor="message">Wiadomość</Label>
                <Textarea 
                  id="message" 
                  name="message" 
                  rows={5}
                  value={formData.message} 
                  onChange={handleChange} 
                  required 
                  className="mt-1"
                />
              </div>
              <div className="text-center pt-2 space-y-3">
                <Button 
                  type="submit"
                  size="lg"
                  disabled={formStatus.state === 'loading'}
                  className="bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {formStatus.state === 'loading' ? 'Wysyłanie...' : 'Wyślij wiadomość'}
                </Button>
                {formStatus.state === 'success' && (
                  <p className="text-green-600 text-sm" aria-live="polite">
                    {formStatus.message}
                  </p>
                )}
                {formStatus.state === 'error' && (
                  <p className="text-red-600 text-sm" aria-live="polite">
                    {formStatus.message}
                  </p>
                )}
              </div>
            </form>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <BrandLogo className="w-12 mx-auto mb-6 brightness-0 invert" intrinsicSize={64} loading="lazy" />
          <p className="text-gray-400 mb-4">
            © 2026 Gama Software. Wszystkie prawa zastrzeżone.
          </p>
          <div className="flex justify-center space-x-6 text-sm text-gray-400">
            <a href="#" className="hover:text-white transition-colors">Polityka prywatności</a>
            <a href="#" className="hover:text-white transition-colors">Regulamin</a>
            <a href="#" className="hover:text-white transition-colors">Kontakt</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
