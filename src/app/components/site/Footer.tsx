const FOOTER_LINKS = [
  { label: 'Polityka prywatności', href: '#' },
  { label: 'Regulamin', href: '#' },
  { label: 'Kontakt', href: '#contact' },
];

type FooterProps = {
  logoSrc: string;
};

export function Footer({ logoSrc }: FooterProps) {
  return (
    <footer className="bg-gray-900 px-4 py-12 text-white">
      <div className="mx-auto max-w-7xl text-center">
        <img src={logoSrc} alt="Gama Software" className="mx-auto mb-6 h-8 brightness-0 invert" />
        <p className="mb-4 text-gray-400">© 2026 Gama Software. Wszystkie prawa zastrzeżone.</p>
        <div className="flex justify-center space-x-6 text-sm text-gray-400">
          {FOOTER_LINKS.map((link) => (
            <a key={link.label} href={link.href} className="transition-colors hover:text-white">
              {link.label}
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
}
