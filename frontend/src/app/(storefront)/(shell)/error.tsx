'use client';

import Button from '@/components/ui/Button';
import { Container, Section } from '@/components/ui/Layout';
import { ErrorState } from '@/components/ui/States';

/** Catches anything a page throws, so a failure never blanks the site. */
export default function ShellError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Section>
      <Container>
        <ErrorState action={<Button onClick={reset}>Try again</Button>} />
      </Container>
    </Section>
  );
}
