'use client';
import { useTranslations, useLocale } from 'next-intl';
import { usePathname, Link } from '@/i18n/routing';

export default function Footer() {
  const t = useTranslations('Footer');
  const locale = useLocale();
  const pathname = usePathname();

  return (
    <footer className="w-full bg-ink text-paper py-16 px-4 md:px-8 mt-16 border-t border-ink">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-start gap-12">
        
        {/* Left: Logo and Desc */}
        <div className="max-w-sm flex flex-col gap-6">
          <div className="flex items-start md:items-center gap-4 flex-col md:flex-row">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 relative text-paper">
                <img src="/logo.png" alt="Patrol MD Logo" className="object-contain w-full h-full filter brightness-0 invert" />
              </div>
              <span className="font-serif text-2xl font-semibold leading-none">PATROL</span>
            </div>
            <div className="flex flex-col gap-1 md:ml-2">
              <div className="flex gap-2">
                <a 
                  href="https://digitaltrust.living/en" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="bg-paper text-ink font-mono text-[10px] font-bold uppercase tracking-widest px-4 py-2 hover:opacity-90 transition-opacity whitespace-nowrap"
                >
                  WHO WE ARE
                </a>
                <a 
                  href="https://www.liqpay.ua/uk/checkout/card/i8424016426" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="bg-paper text-ink font-mono text-[10px] font-bold uppercase tracking-widest px-4 py-2 hover:opacity-90 transition-opacity whitespace-nowrap"
                >
                  DONATION
                </a>
              </div>
              <span className="text-[9px] text-[#8C8375] font-sans italic">
                * Please write the word "donation" in the payment comment
              </span>
            </div>
          </div>
          <p className="font-sans text-xs text-[#8C8375] leading-relaxed">
            {t('description')}
          </p>
        </div>

        {/* Right Side - Links */}
        <div className="flex gap-16 md:gap-24">
          <div className="flex flex-col gap-4">
            <div className="font-mono text-[9px] uppercase tracking-widest text-[#8C8375] mb-2">PRODUCT</div>
            <a href="#live-feed" className="font-sans text-xs text-paper hover:text-[#D8CDB6] transition-colors">Monitoring feed</a>
            <a href="#methodology" className="font-sans text-xs text-paper hover:text-[#D8CDB6] transition-colors">Methodology</a>
            <a href="#quarantine" className="font-sans text-xs text-paper hover:text-[#D8CDB6] transition-colors">Quarantine archive</a>
            <span className="font-sans text-xs text-[#8C8375]">Open API — coming soon</span>
          </div>

          <div className="flex flex-col gap-4">
            <div className="font-mono text-[9px] uppercase tracking-widest text-[#8C8375] mb-2">ORGANIZATION</div>
            <a href="#" className="font-sans text-xs text-paper hover:text-[#D8CDB6] transition-colors">Center Digital Trust NGO</a>
            <a href="#" className="font-sans text-xs text-paper hover:text-[#D8CDB6] transition-colors flex items-center gap-2">
              <span>{'\uD83D\uDCF1'}</span> +380961614151
            </a>
            <a href="mailto:admin@digitaltrust.living" className="font-sans text-xs text-paper hover:text-[#D8CDB6] transition-colors flex items-center gap-2">
              <span>{'\u2709\uFE0F'}</span> admin@digitaltrust.living
            </a>
            <div className="font-sans text-xs text-[#8C8375] leading-relaxed mt-2">
              Legal address:<br />
              Ukraine<br />
              m.Kamyanske, vul.Gaydamatska 13/11<br />
              NGO &quot;Digital Trust Center&quot;<br />
              EDRPOU<br />
              46286915
            </div>
          </div>
        </div>

      </div>

      <div className="max-w-6xl mx-auto mt-24 pt-8 border-t border-[#4A443B] flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="font-mono text-[9px] uppercase tracking-widest text-[#8C8375]">
          © 2026 CENTER DIGITAL TRUST NGO — PATROL DOES NOT PROVIDE FINANCIAL ADVICE
        </div>
        
        <div className="flex gap-4 font-mono text-[9px] text-[#8C8375] uppercase">
          {['ua', 'en', 'ru', 'es'].map((l) => (
            <Link 
              key={l}
              href={pathname}
              locale={l}
              className={`transition-colors hover:text-paper ${locale === l ? 'text-paper underline underline-offset-2' : ''}`}
            >
              {l}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
