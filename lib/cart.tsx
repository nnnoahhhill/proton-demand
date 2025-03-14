"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { QuoteResponse } from './api';

// Define cart item interface
export interface CartItem {
  id: string;  // quote ID
  process: string;
  material: string;
  finish: string;
  price: number;
  currency: string;
  leadTimeInDays: number;
  fileName: string;
  addedAt: Date;
  quantity: number;
  weightInKg: number; // Weight in kg for shipping calculation
}

// Define cart context interface
interface CartContextType {
  items: CartItem[];
  addItem: (quote: QuoteResponse, fileName: string) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  totalItems: number;
  totalPrice: number;
  subtotalPrice: number;
  shippingCost: number;
}

// Create context with default values
const CartContext = createContext<CartContextType>({
  items: [],
  addItem: () => {},
  removeItem: () => {},
  updateQuantity: () => {},
  clearCart: () => {},
  totalItems: 0,
  totalPrice: 0,
  subtotalPrice: 0,
  shippingCost: 0,
});

// Hook to use cart context
export const useCart = () => useContext(CartContext);

// Cart provider component
export function CartProvider({ children }: { children: ReactNode }) {
  // Initialize state from localStorage if available
  const [items, setItems] = useState<CartItem[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load cart from localStorage on initial render
  useEffect(() => {
    const storedCart = localStorage.getItem('cart');
    if (storedCart) {
      try {
        const parsedCart = JSON.parse(storedCart);
        // Convert string dates back to Date objects
        const processedCart = parsedCart.map((item: any) => ({
          ...item,
          addedAt: new Date(item.addedAt)
        }));
        setItems(processedCart);
      } catch (error) {
        console.error('Error parsing cart from localStorage:', error);
      }
    }
    setIsInitialized(true);
  }, []);

  // Save cart to localStorage whenever it changes
  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem('cart', JSON.stringify(items));
    }
  }, [items, isInitialized]);

  // Add item to cart
  const addItem = (quote: QuoteResponse, fileName: string) => {
    if (!quote.success || !quote.price) return;

    // Calculate weight in kg - we'll use volume as an approximation if actual weight isn't available
    // Assuming a density of 1.05 g/cm³ for typical 3D printing materials
    const volume = quote.manufacturingDetails?.volume || 0; // in mm³
    const volumeInCm3 = volume / 1000; // Convert mm³ to cm³
    const estimatedWeightInKg = volumeInCm3 * 0.00105; // Convert to kg using density

    const newItem: CartItem = {
      id: quote.quoteId,
      process: quote.manufacturingDetails?.process || '',
      material: quote.manufacturingDetails?.material || '',
      finish: quote.manufacturingDetails?.finish || '',
      price: quote.price,
      currency: quote.currency || 'USD',
      leadTimeInDays: 10, // Set fixed lead time to 10 business days
      fileName,
      addedAt: new Date(),
      quantity: 1,
      weightInKg: estimatedWeightInKg,
    };

    // Check if item already exists
    const existingItemIndex = items.findIndex(item => item.id === newItem.id);

    if (existingItemIndex >= 0) {
      // Update existing item
      const updatedItems = [...items];
      updatedItems[existingItemIndex].quantity += 1;
      setItems(updatedItems);
    } else {
      // Add new item
      setItems(prevItems => [...prevItems, newItem]);
    }
  };

  // Remove item from cart
  const removeItem = (id: string) => {
    setItems(prevItems => prevItems.filter(item => item.id !== id));
  };

  // Update item quantity
  const updateQuantity = (id: string, quantity: number) => {
    if (quantity < 1) return;
    
    setItems(prevItems => 
      prevItems.map(item => 
        item.id === id ? { ...item, quantity } : item
      )
    );
  };

  // Clear cart
  const clearCart = () => {
    setItems([]);
  };

  // Calculate total items
  const totalItems = items.reduce((total, item) => total + item.quantity, 0);

  // Calculate subtotal price (before shipping)
  const subtotalPrice = items.reduce((total, item) => total + (item.price * item.quantity), 0);

  // Calculate shipping cost ($20/kg)
  const shippingCost = items.reduce((total, item) => 
    total + (item.weightInKg * item.quantity * 20), 0);

  // Calculate total price (including shipping)
  const totalPrice = subtotalPrice + shippingCost;

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        totalItems,
        totalPrice,
        subtotalPrice,
        shippingCost
      }}
    >
      {children}
    </CartContext.Provider>
  );
} 