import { useState } from 'react';

import logo from '../assets/606550a668ee67574ee51adad0d7a231ffcce05b.png';
import { BlogSection } from './components/site/BlogSection';
import { ContactSection } from './components/site/ContactSection';
import { Footer } from './components/site/Footer';
import { HeroSection } from './components/site/HeroSection';
import { ModulesSection } from './components/site/ModulesSection';
import { ServicesSection } from './components/site/ServicesSection';
import { SiteNavigation } from './components/site/SiteNavigation';
import { NAVIGATION_ITEMS } from './content/siteContent';

function App() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);

    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setMobileMenuOpen(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <SiteNavigation
        items={NAVIGATION_ITEMS}
        logoSrc={logo}
        mobileMenuOpen={mobileMenuOpen}
        onNavigate={scrollToSection}
        onToggleMobileMenu={() => setMobileMenuOpen((open) => !open)}
      />

      <main>
        <HeroSection onExploreServices={() => scrollToSection('services')} />
        <ServicesSection />
        <ModulesSection />
        <BlogSection />
        <ContactSection />
      </main>

      <Footer logoSrc={logo} />
    </div>
  );
}

export default App;
