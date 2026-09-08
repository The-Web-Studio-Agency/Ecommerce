import HomeClient from "./_components/luxe/HomeClient";
import { catalogueApi } from "@/lib/api/catalogue";
import type { ProductStorefront } from "@/types/catalogue";

export const metadata = {
  title: "Avera | Timeless Leather Handbags",
  description:
    "Avera crafts timeless leather handbags with exceptional craftsmanship, premium materials, and modern elegance. Discover the signature Lumière collection.",
};

/** Newest first, so the grid moves as the catalogue does. */
const HomePage = async () => {
  const productsPage = await catalogueApi.listProducts({ page_size: 8, sort: "newest" });
  const products = productsPage.items;

  // The spotlight section shows one product full-detail (its own gallery,
  // not just the catalogue-tile thumbnail), so it needs the full record.
  const spotlightProduct: ProductStorefront | null = products[0]
    ? await catalogueApi.getProduct(products[0].id).catch(() => null)
    : null;

  return <HomeClient products={products} spotlightProduct={spotlightProduct} />;
};

export default HomePage;
