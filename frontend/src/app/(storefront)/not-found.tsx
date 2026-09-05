import ButtonLink from '@/components/ui/ButtonLink';
import { Container, Section } from '@/components/ui/Layout';
import { EmptyState } from '@/components/ui/States';

export const metadata = {
  title: 'Page not found',
};

/**
 * Lives at the route-group level rather than inside (shell).
 *
 * A not-found boundary nested below this one renders the page but answers
 * 200, which is a soft 404 -- wrong for a URL that genuinely is not a page.
 * Here the response carries a real 404.
 */
export default function NotFound() {
  return (
    <Section>
      <Container>
        <EmptyState
          title="We couldn't find that"
          body="The page may have moved, or the piece may no longer be in the collection."
          action={<ButtonLink href="/shop">Browse the collection</ButtonLink>}
        />
      </Container>
    </Section>
  );
}
