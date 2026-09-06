'use client';

import { createContext, useContext, useState } from 'react';

export interface CartItem {
  productId: string;
  name: string;
  image: string;
  price: number;
  rating: number;
  stockCount: number;
  color: string;
  size: string;
  quantity: number;
}

interface CartContextType {
  cartItems: CartItem[];
  addToCart: (item: CartItem) => void;
  updateQuantity: (productId: string, color: string, size: string, quantity: number) => void;
  removeFromCart: (productId: string, color: string, size: string) => void;
}

const CartContext = createContext<CartContextType | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);

  // -----------------------------------
  // ADD TO CART
  // -----------------------------------

  const addToCart = (item: CartItem) => {
    setCartItems(prevItems => {
      const existingItem = prevItems.find(
        cartItem =>
          cartItem.productId === item.productId && cartItem.color === item.color && cartItem.size === item.size,
      );

      if (existingItem) {
        return prevItems.map(cartItem =>
          cartItem.productId === item.productId && cartItem.color === item.color && cartItem.size === item.size
            ? {
                ...cartItem,
                quantity: Math.min(cartItem.quantity + item.quantity, cartItem.stockCount),
              }
            : cartItem,
        );
      }

      return [...prevItems, item];
    });
  };

  // -----------------------------------
  // UPDATE QUANTITY
  // -----------------------------------

  const updateQuantity = (productId: string, color: string, size: string, quantity: number) => {
    setCartItems(prevItems =>
      prevItems.map(item =>
        item.productId === productId && item.color === color && item.size === size
          ? {
              ...item,
              quantity: Math.min(quantity, item.stockCount),
            }
          : item,
      ),
    );
  };

  // -----------------------------------
  // REMOVE FROM CART
  // -----------------------------------

  const removeFromCart = (productId: string, color: string, size: string) => {
    setCartItems(prevItems =>
      prevItems.filter(item => !(item.productId === productId && item.color === color && item.size === size)),
    );
  };

  return (
    <CartContext.Provider
      value={{
        cartItems,
        addToCart,
        updateQuantity,
        removeFromCart,
      }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);

  if (!context) {
    throw new Error('useCart must be used inside CartProvider');
  }

  return context;
}
