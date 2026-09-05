import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

import AddressForm from '@/components/checkout/AddressForm';
import DeleteAddress from '@/components/checkout/DeleteAddress';
import Badge from '@/components/ui/Badge';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';
import { addressApi } from '@/lib/api/addresses';
import { getAccessToken } from '@/lib/auth/session';

import styles from '../Account.module.css';

export const metadata: Metadata = {
  title: 'Addresses',
  robots: { index: false, follow: false },
};

export default async function AddressesPage() {
  const token = await getAccessToken();
  if (!token) redirect('/signin?next=/account/addresses');

  const addresses = await addressApi.list(token).catch(() => []);

  return (
    <main>
      <Section>
        <Container width="text">
          <h1>Addresses</h1>

          {addresses.length === 0 ? (
            <EmptyState title="No addresses yet" body="Add one so we know where to deliver." />
          ) : (
            <div className={styles.list}>
              {addresses.map((address) => (
                <div key={address.id} className={styles.card}>
                  <p className={styles.address}>
                    <span className={styles.name}>{address.full_name}</span>
                    {address.is_default && (
                      <>
                        {' '}
                        <Badge tone="accent">Default</Badge>
                      </>
                    )}
                    <br />
                    {address.address_line_1}
                    {address.address_line_2 ? `, ${address.address_line_2}` : ''}
                    <br />
                    {address.city}, {address.state} {address.postal_code}
                    <br />
                    {address.country} &middot; {address.phone}
                  </p>

                  <DeleteAddress addressId={address.id} />
                </div>
              ))}
            </div>
          )}

          <div className={styles.formWrap}>
            <h2>Add an address</h2>
            <AddressForm />
          </div>
        </Container>
      </Section>
    </main>
  );
}
