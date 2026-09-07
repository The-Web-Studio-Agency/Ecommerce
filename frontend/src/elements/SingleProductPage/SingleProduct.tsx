'use client';

import Image from 'next/image';
import { useState } from 'react';
import { useCart } from '@/context/CartContext';
import { productData } from '@/constant/Alldata';
import ProductCard from '../Shop/ProductCard';

type Props = {
  productId: string;
  name: string;
  price: number;
  oldPrice?: number;
  discount?: number;
  images: string[];
  colors: string[];
  sizes: string[];
  rating: number;
  stockCount: number;
  description: string;
};

const SingleProduct = ({
  productId,
  name,
  price,
  oldPrice,
  discount,
  images,
  colors,
  sizes,
  rating,
  stockCount,
  description,
}: Props) => {
  const [selectedImage, setSelectedImage] = useState(0);
  const [selectedColor, setSelectedColor] = useState(0);
  const [selectedSize, setSelectedSize] = useState(0);
  const [quantity, setQuantity] = useState(1);

  const { addToCart } = useCart();

  const handleAddToCart = () => {
    addToCart({
      productId,
      name,
      image: images[0],
      price,
      rating,
      stockCount,
      color: colors[selectedColor],
      size: sizes[selectedSize],
      quantity,
    });
  };

  return (
    <section className="wrapper">
      {/* Single Product */}
      <div className="single-product-container">
        {/* Images */}
        <div className="single-product-image-section">
          <div className="product-thumbnail-gallery">
            {images.map((item, index) => (
              <div
                key={index}
                className={`${
                  selectedImage === index ? 'selected-product-thumdbnail' : 'unselected-products-thumbnail'
                } product-thumbnail`}>
                <Image
                  onClick={() => setSelectedImage(index)}
                  className="product-active-thumbnail"
                  src={item}
                  alt={name}
                  width={100}
                  height={150}
                />
              </div>
            ))}
          </div>

          <div className="single-product-image">
            <Image src={images[selectedImage]} alt={name} width={1000} height={1000} />
          </div>
        </div>

        {/* Product Details */}
        <div className="single-product-details">
          {/* Discount */}
          <div className="discount-offers">
            <p className="new-tag">NEW</p>

            {discount && <p className="discount-offer-tag">{discount}% OFF</p>}
          </div>

          {/* Name + Price */}
          <div className="product-name-price">
            <p className="product-type">Pants & Skirts</p>

            <p className="product-name">{name}</p>

            <div className="product-price">
              <span>${price.toFixed(2)} USD</span>

              {oldPrice && <span className="product-old-price">${oldPrice.toFixed(2)}</span>}
            </div>
          </div>

          {/* Colors */}
          <div className="product-colors-container">
            <p>Colors :</p>

            {colors.map((color, index) => (
              <p
                key={index}
                onClick={() => setSelectedColor(index)}
                className={`product-color ${selectedColor === index ? 'active' : ''}`}
                style={{
                  backgroundColor: color,
                }}
              />
            ))}
          </div>

          {/* Sizes */}
          <div className="product-size-container">
            <p>Sizes :</p>

            {sizes.map((size, index) => (
              <p
                key={index}
                onClick={() => setSelectedSize(index)}
                className={`product-size ${selectedSize === index ? 'active' : ''}`}>
                {size}
              </p>
            ))}
          </div>
          <div className="single-product-rating">
            {Array.from({ length: 5 }).map((_, index) => {
              if (index < Math.floor(rating)) {
                return <i key={index} className="fa-solid fa-star filled" />;
              }
              if (index < rating) {
                return <i key={index} className="fa-solid fa-star-half-stroke filled" />;
              }
              return <i key={index} className="fa-regular fa-star" />;
            })}
          </div>

          {/* Quantity + Cart */}
          <div className="product-quantity-cart-container">
            <div className="product-quantity-container">
              <p>Quantity</p>

              <div className="quantity-button">
                <button onClick={() => setQuantity(prev => (prev <= 1 ? prev : prev - 1))}>-</button>

                <p>{quantity}</p>

                <button onClick={() => setQuantity(prev => (prev < stockCount ? prev + 1 : prev))}>+</button>
              </div>
            </div>

            <button onClick={handleAddToCart} className="add-to-cart-btn">
              ADD TO CART
            </button>
          </div>

          {/* Description */}
          <div className="product-description-container">
            <p className="description-heading">DESCRIPTION</p>

            <p>{description}</p>
          </div>
        </div>
      </div>

      {/* Similar Products */}
      <div className="similiar-products-section">
        <p className="similiar-products-heading">YOU MIGHT ALSO LIKE</p>

        <div className="row gx-xl-4 g-3 mt-5 mb-5">
          {productData.slice(0, 3).map(item => (
            <div className="col-12 col-sm-6 col-md-4 col-lg-4 col-xl-4" key={item.id}>
              <ProductCard
                productId={item.id}
                image={item.image}
                title={item.name}
                price={item.price}
                oldPrice={item.oldPrice}
                sizes={item.sizes}
                discount={item.discount}
                colors={item.colors}
                rating={item.rating}
                stockCount={item.stockCount}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default SingleProduct;
