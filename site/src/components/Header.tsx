'use client';
import { useTranslations, useLocale } from 'next-intl';
import { Link, usePathname, useRouter } from '@/i18n/routing';

export default function Header() {
  const t = useTranslations('Header');
  const locale = useLocale();
  const pathname = usePathname();

  return (
    <div className="w-full flex flex-col z-50 sticky top-0 bg-beige-0 border-b border-rule">
      {/* 4.1 Top strip */}
      <div className="w-full border-b border-rule flex justify-between items-center px-4 py-1.5 font-mono text-[11px] md:text-xs">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ink opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-ink"></span>
          </span>
          <span className="text-ink-soft uppercase">SCANNING SOLANA — NEW SWEEP EVERY 10 SECONDS</span>
        </div>
        <div className="flex gap-2 text-ink-faint">
          {['ua', 'en', 'ru', 'es'].map((l, index) => (
            <span key={l} className="flex items-center gap-2 uppercase">
              <Link 
                href={pathname}
                locale={l}
                className={`transition-colors hover:text-ink ${locale === l ? 'text-ink underline underline-offset-2' : ''}`}
              >
                {l}
              </Link>
              {index < 3 && <span>·</span>}
            </span>
          ))}
        </div>
      </div>

      {/* 4.2 Header */}
      <header className="w-full flex justify-between items-center px-4 py-4 md:px-8">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 md:w-20 md:h-20 relative text-ink">
             <img src="/logo.png" alt="Patrol MD Logo" className="object-contain w-full h-full" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-2xl font-semibold leading-none">PATROL</span>
            <span className="font-mono text-[10px] md:text-xs text-ink-soft uppercase tracking-widest mt-1">SOLANA ANALYTICS & SCAM PROTECTION</span>
          </div>
        </div>
        
        <nav className="hidden md:flex gap-6 font-mono text-sm text-ink-soft">
          {['Live Feed', 'Methodology', 'Growth', 'Quarantine', 'About'].map((item) => (
             <a key={item} href={`#${item.toLowerCase().replace(' ', '-')}`} className="hover:text-ink transition-colors">
               {item}
             </a>
          ))}
        </nav>
      </header>
    </div>
  );
}
