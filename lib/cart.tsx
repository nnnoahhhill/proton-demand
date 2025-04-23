"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
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
  metadata?: {
    technology?: string; // FDM, SLA, SLS
    originalFileName?: string;
    [key: string]: any;
  };
}

// Define cart context interface
interface CartContextType {
  items: CartItem[];
  addItem: (quote: QuoteResponse, fileName: string, quantity?: number) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  totalItems: number;
  totalPrice: number;
  subtotalPrice: number;
  shippingCost: number;
  isInitialized: boolean;
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
  isInitialized: false,
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
  const addItem = useCallback((quote: QuoteResponse, fileName: string, quantity: number = 1) => {
    // Use customer_price instead of price
    if (!quote.success || !quote.customer_price) {
        console.error("Cannot add item to cart: Quote was not successful or price is missing.", quote);
        return;
    }

    // Ensure quantity is at least 1
    const itemQuantity = Math.max(1, quantity);

    // Calculate weight in kg using cost_estimate if available
    const weightInGrams = quote.cost_estimate?.material_weight_g;
    // Fallback to a rough estimate using volume if weight is not directly provided
    // Density assumption (1.05 g/cm³) might need refinement
    const volumeInCm3 = quote.cost_estimate?.total_volume_cm3 || 0;
    const estimatedWeightInKg = weightInGrams
      ? weightInGrams / 1000
      : volumeInCm3 * 0.00105; // Convert cm³ to kg using assumed density

    // Get technology from localStorage if available
    let technology = undefined;
    try {
      if (typeof window !== 'undefined' && localStorage) {
        const storedFileData = localStorage.getItem(`model_file_${quote.quote_id}`);
        if (storedFileData) {
          const fileData = JSON.parse(storedFileData);
          technology = fileData.technology;
        }
      }
    } catch (e) {
      console.error('Error getting technology from localStorage:', e);
    }

    const newItem: CartItem = {
      id: quote.quote_id, // Use quote_id instead of quoteId
      process: quote.process || '', // Use quote.process
      material: quote.material_info?.name || '', // Use quote.material_info.name
      // Finish might not be explicitly in the response, using standard for now
      finish: 'Standard High-Quality', // Assuming standard finish based on form display
      price: quote.customer_price, // Use customer_price
      currency: quote.material_info?.currency || 'USD', // Use material_info.currency
      leadTimeInDays: 10, // TODO: Get this from quote response if available later
      fileName,
      addedAt: new Date(),
      quantity: itemQuantity,
      // Use calculated weight, ensuring it's a number
      weightInKg: typeof estimatedWeightInKg === 'number' ? estimatedWeightInKg : 0,
      // Add metadata including technology if available
      metadata: {
        technology: technology || quote.technology, // Use either stored or response technology
        originalFileName: fileName,
      }
    };

    console.log(`Adding item to cart: ${newItem.id} with quantity ${itemQuantity}`);

    // Check if item already exists
    const existingItemIndex = items.findIndex(item => item.id === newItem.id);

    if (existingItemIndex >= 0) {
      // Update existing item quantity
      const updatedItems = [...items];
      updatedItems[existingItemIndex].quantity = itemQuantity;
      console.log(`Updated quantity for item ${newItem.id} to ${itemQuantity}`);
      setItems(updatedItems);
    } else {
      // Add new item
      console.log(`Adding new item ${newItem.id} to cart with quantity ${itemQuantity}`);
      setItems(prevItems => [...prevItems, newItem]);
    }
  }, [items]);

  // Remove item from cart
  const removeItem = useCallback((id: string) => {
    setItems(prevItems => prevItems.filter(item => item.id !== id));
  }, []);

  // Update item quantity
  const updateQuantity = useCallback((id: string, quantity: number) => {
    if (quantity < 1) return;
    
    setItems(prevItems => 
      prevItems.map(item => 
        item.id === id ? { ...item, quantity } : item
      )
    );
  }, []);

  // Clear cart
  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  // Calculate total items
  const totalItems = items.reduce((total, item) => total + item.quantity, 0);

  // Calculate subtotal price (before shipping)
  const subtotalPrice = items.reduce((total, item) => total + (item.price * item.quantity), 0);

  // Calculate shipping cost ($10 base + $20/kg)
  const baseShippingFee = items.length > 0 ? 10 : 0; // Add $10 base fee if cart is not empty
  const weightBasedShippingCost = items.reduce((total, item) => 
    total + (item.weightInKg * item.quantity * 20), // $20 per kg
  0);
  const shippingCost = baseShippingFee + weightBasedShippingCost;

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
        shippingCost,
        isInitialized
      }}
    >
      {children}
    </CartContext.Provider>
  );
} 