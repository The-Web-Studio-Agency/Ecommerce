import { Container, Section } from '@/components/ui/Layout';
import { Skeleton } from '@/components/ui/States';

/**
 * Shaped like the catalogue it stands in for, so the page does not jump.
 *
 * Scoped to /shop rather than the whole shell on purpose: a loading file
 * opens a Suspense boundary, and once a response starts streaming its
 * status is already committed -- which turns a product page's notFound()
 * into a soft 404.
 */
export default function ShellLoading() {
  return (
    <Section>
      <Container>
        <Skeleton width="14rem" height="2.5rem" />

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(14rem, 1fr))',
            gap: 'var(--space-5)',
            marginTop: 'var(--space-6)',
          }}
        >
          {Array.from({ length: 8 }, (_, index) => (
            <div key={index}>
              <div style={{ aspectRatio: '4 / 5' }}>
                <Skeleton height="100%" radius="0" />
              </div>
              <div style={{ marginTop: 'var(--space-3)' }}>
                <Skeleton width="70%" height="1.1rem" />
              </div>
              <div style={{ marginTop: 'var(--space-2)' }}>
                <Skeleton width="40%" height="0.9rem" />
              </div>
            </div>
          ))}
        </div>
      </Container>
    </Section>
  );
}
