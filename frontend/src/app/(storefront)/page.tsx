import { Metadata } from "next";
import HomePage from "./(home)/home/page";

export const metadata : Metadata = {
  title: "Avera | Timeless Leather Handbags",
  description:
    "Avera crafts timeless leather handbags with exceptional craftsmanship, premium materials, and modern elegance. Discover the signature Lumière collection.",
};

export default function Home() {
  return (
    <div >
      <main>
          <HomePage />  
      </main>    
    </div>
  );
}
