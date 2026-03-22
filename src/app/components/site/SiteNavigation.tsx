import { Menu, X } from 'lucide-react';

type NavigationItem = {
  id: string;
  label: string;
};

type SiteNavigationProps = {
  items: NavigationItem[];
  logoSrc: string;
  mobileMenuOpen: boolean;
  onNavigate: (id: string) => void;
  onToggleMobileMenu: () => void;
};

const mobileMenuId = 'mobile-navigation-menu';

export function SiteNavigation({
  items,
  logoSrc,
  mobileMenuOpen,
  onNavigate,
  onToggleMobileMenu,
}: SiteNavigationProps) {
  return (
    <nav className="fixed top-0 z-50 w-full border-b border-gray-200 bg-white/95 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-20 items-center justify-between">
          <div className="flex items-center">
            <img
              src={logoSrc}
              alt="Gama Software"
              className="h-16 drop-shadow-lg mix-blend-multiply md:h-20"
            />
          </div>

          <div className="hidden space-x-8 md:flex">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                className="text-gray-700 transition-colors hover:text-blue-600"
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="md:hidden">
            <button
              type="button"
              aria-label={
                mobileMenuOpen
                  ? 'Zamknij menu nawigacyjne'
                  : 'Otwórz menu nawigacyjne'
              }
              aria-controls={mobileMenuId}
              aria-expanded={mobileMenuOpen}
              onClick={onToggleMobileMenu}
              className="text-gray-700 hover:text-blue-600"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {mobileMenuOpen && (
        <div
          id={mobileMenuId}
          className="border-t border-gray-200 bg-white md:hidden"
        >
          <div className="space-y-1 px-4 pb-3 pt-2">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                className="block w-full rounded-md px-3 py-2 text-left text-gray-700 hover:bg-gray-50 hover:text-blue-600"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
