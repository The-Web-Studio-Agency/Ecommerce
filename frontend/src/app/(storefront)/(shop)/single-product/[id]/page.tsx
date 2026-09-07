import CommanLayout from '@/components/CommanLayout';
import SingleProduct from '@/elements/SingleProductPage/SingleProduct';
import CommonBanner2 from '@/components/CommonBanner2';

const SingleProductPage = async ({ params }: { params: Promise<{ id: string }> }) => {
  const { id } = await params;

  const product = {
    id: id,
    // Single Product only
    images: ['/assets/cloth-0.webp', '/assets/cloth-1.webp', '/assets/cloth-2.webp'],
    name: 'Ribbed Knit Cardigan',
    price: 1485.04,
    oldPrice: 1765,
    discount: 16,
    rating: 4.5,
    stockCount: 10,
    colors: ['#000000', '#FFFFFF', '#1C1C1C', '#36454F'],
    sizes: ['XS', 'SM', 'MD', 'LG', 'XL', 'XXL'],
    description: 'A beautifully crafted cardigan that blends rich texture with effortless sophistication.',
  };

  return (
    <CommanLayout>
      <CommonBanner2 parentText="Shop" currentText="Ribbed Knit Cardigan" mainText="Shop Standard"></CommonBanner2>
      <SingleProduct
        productId={product.id}
        name={product.name}
        price={product.price}
        images={product.images}
        colors={product.colors}
        sizes={product.sizes}
        rating={product.rating}
        stockCount={product.stockCount}
        description={product.description}
      />
    </CommanLayout>
  );
};

export default SingleProductPage;
