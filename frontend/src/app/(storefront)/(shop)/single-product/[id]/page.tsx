import { notFound } from 'next/navigation';

import CommanLayout from '@/components/CommanLayout';
import CommonBanner2 from '@/components/CommonBanner2';
import SingleProduct from '@/elements/SingleProductPage/SingleProduct';
import { catalogueApi } from '@/lib/api/catalogue';
import { ApiError } from '@/lib/api/errors';
import { reviewApi } from '@/lib/api/reviews';
import type { ProductStorefront } from '@/types/catalogue';

const SingleProductPage = async ({ params }: { params: Promise<{ id: string }> }) => {
  const { id } = await params;

  let product: ProductStorefront;

  try {
    product = await catalogueApi.getProduct(id);
  } catch (error) {
    if (error instanceof ApiError && error.isNotFound) notFound();
    throw error;
  }

  /* A product with no reviews still renders, with an empty star row, and
     "you might also like" falls back to nothing rather than to filler. */
  const [summary, related] = await Promise.all([
    reviewApi.summary(id).catch(() => null),
    catalogueApi
      .listProducts({ category_id: product.category.id, page_size: 4 })
      .then(page => page.items.filter(item => item.id !== product.id).slice(0, 3))
      .catch(() => []),
  ]);

  return (
    <CommanLayout>
      <CommonBanner2 parentText="Shop" currentText={product.name} mainText={product.category.name} />
      <SingleProduct
        product={product}
        rating={summary ? summary.average_rating : 0}
        related={related}
      />
    </CommanLayout>
  );
};

export default SingleProductPage;
