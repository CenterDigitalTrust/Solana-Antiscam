import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';
import '../globals.css';

import { Fraunces, Inter, IBM_Plex_Mono } from 'next/font/google';

const fraunces = Fraunces({ 
  subsets: ['latin'],
  variable: '--font-serif',
  weight: ['300', '400', '500', '600', '700', '800', '900'],
  style: ['normal', 'italic']
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '700'],
});

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as any)) {
    notFound();
  }
 
  const messages = await getMessages();
 
  return (
    <html lang={locale} className={`${fraunces.variable} ${inter.variable} ${ibmPlexMono.variable}`}>
      <head>
        <title>PATROL MD - Autonomous Security</title>
        <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18355552908"></script>
        <script dangerouslySetInnerHTML={{
          __html: `
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'AW-18355552908');
          `
        }} />
      </head>
      <body className="bg-beige-0 text-ink antialiased">
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
