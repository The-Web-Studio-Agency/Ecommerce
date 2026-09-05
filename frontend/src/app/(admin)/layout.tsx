import type { Metadata } from 'next';
import { Newsreader, Schibsted_Grotesk } from 'next/font/google';

import '@/styles/base.css';

const newsreader = Newsreader({
  subsets: ['latin'],
  weight: ['400', '500'],
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
  title: { default: 'Zeen admin', template: '%s | Zeen admin' },
  robots: { index: false, follow: false },
};

export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${newsreader.variable} ${schibsted.variable}`}>
      <body>{children}</body>
    </html>
  );
}
