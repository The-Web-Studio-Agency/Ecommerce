import type { Metadata } from 'next';
import { Newsreader, Schibsted_Grotesk } from 'next/font/google';

import { ToastProvider } from '@/components/ui/Toast';
import '@/styles/base.css';

/**
 * Newsreader carries product names and headings; Schibsted Grotesk does the
 * interface work and the numbers. Self-hosted by next/font, so there is no
 * third-party request and no layout shift on first paint.
 */
const newsreader = Newsreader({
  subsets: ['latin'],
  weight: ['400', '500'],
  style: ['normal', 'italic'],
  variable: '--font-newsreader',
  display: 'swap',
});

const schibsted = Schibsted_Grotesk({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-schibsted',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Zeen',
    template: '%s | Zeen',
  },
  description: 'Everyday pieces in considered fabrics -- clothing, bags and jewellery from Zeen.',
};

export default function StorefrontLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${newsreader.variable} ${schibsted.variable}`}>
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
