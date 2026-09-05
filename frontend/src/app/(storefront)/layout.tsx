import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: {
    default: 'Zeen',
    template: '%s | Zeen',
  },
  description: 'Shop the Zeen collection.',
};

export default function StorefrontLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
