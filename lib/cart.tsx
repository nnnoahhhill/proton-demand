"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { QuoteResponse } from './api';

// Define types
export type CartItem = {
  id: string;            // Quote ID
  baseQuoteId?: string;  // New: Base quote ID if this is a suffixed quote
  suffix?: string;       // New: Suffix letter for this part (A, B, C, etc)
  fileName: string;
  process: string;
  technology?: string;   // Technology (FDM, SLA, SLS, etc.)
  material: string;
  finish?: string;
  price: number;
  currency?: string;
  quantity: number;
  weightInKg: number;    // Weight for shipping calculation
};

type CartContextType = {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  updateItem: (id: string, updates: Partial<CartItem>) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: (isSuccessfulOrder?: boolean) => void;
  totalItems: number;
  subtotalPrice: number;
  shippingCost: number;
  totalPrice: number;
  isInitialized: boolean;
  
  // New: Add a method to group items by base quote ID
  getRelatedItems: (baseQuoteId: string) => CartItem[];
};

// Create context
const CartContext = createContext<CartContextType | undefined>(undefined);

// Local storage key
const CART_STORAGE_KEY = 'protondemand_cart';
const CART_CLEARED_KEY = 'protondemand_cart_cleared';

// Cart provider component
export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Initialize cart from localStorage
  useEffect(() => {
    try {
      // Check if cart was recently cleared due to a successful order
      const wasCleared = localStorage.getItem(CART_CLEARED_KEY) === 'true';
      
      if (wasCleared) {
        // If cart was cleared due to a successful order, don't reload items
        console.log('Cart was previously cleared due to successful order, keeping empty');
        localStorage.removeItem(CART_CLEARED_KEY); // Reset the flag
        setItems([]);
      } else {
        // Otherwise load normally from localStorage
        const savedCart = localStorage.getItem(CART_STORAGE_KEY);
        if (savedCart) {
          const parsedCart = JSON.parse(savedCart);
          
          // Add baseQuoteId if missing (backward compatibility)
          const updatedCart = parsedCart.map((item: CartItem) => {
            if (!item.baseQuoteId) {
              // Extract base quote ID from the ID (which may be suffixed)
              const parts = item.id.split('-');
              // If the ID has at least 2 parts and the final part is a single letter, 
              // it's likely a suffixed ID (e.g., Q-12345-A)
              if (parts.length > 2 && parts[parts.length - 1].length === 1) {
                return {
                  ...item,
                  baseQuoteId: parts.slice(0, -1).join('-'),
                  suffix: parts[parts.length - 1]
                };
              } else {
                // Not suffixed, use the ID as is
                return {
                  ...item,
                  baseQuoteId: item.id
                };
              }
            }
            return item;
          });
          
          setItems(updatedCart);
          console.log('Cart loaded from localStorage:', updatedCart);
        }
      }
      setIsInitialized(true);
    } catch (error) {
      console.error('Error loading cart from localStorage:', error);
      setIsInitialized(true);
    }
  }, []);
  
  // Save cart to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
      console.log('Cart saved to localStorage:', items);
    } catch (error) {
      console.error('Error saving cart to localStorage:', error);
    }
  }, [items]);
  
  // Add an item to the cart
  const addItem = (item: CartItem) => {
    // Extract base quote ID if not provided
    let baseQuoteId = item.baseQuoteId;
    let suffix = item.suffix;
    
    if (!baseQuoteId) {
      const parts = item.id.split('-');
      if (parts.length > 2 && parts[parts.length - 1].length === 1) {
        baseQuoteId = parts.slice(0, -1).join('-');
        suffix = parts[parts.length - 1];
      } else {
        baseQuoteId = item.id;
      }
    }
    
    // Check if item already exists in cart
    const existingItemIndex = items.findIndex(i => i.id === item.id);
    
    if (existingItemIndex !== -1) {
      // Update existing item
      setItems(
        items.map((i, index) => 
          index === existingItemIndex 
            ? { 
                ...i, 
                quantity: i.quantity + (item.quantity || 1),
                baseQuoteId,
                suffix
              }
            : i
        )
      );
    } else {
      // Add new item with base quote ID
      setItems([...items, { ...item, baseQuoteId, suffix }]);
    }
  };
  
  // Update an item
  const updateItem = (id: string, updates: Partial<CartItem>) => {
    setItems(
      items.map(item => 
        item.id === id 
          ? { ...item, ...updates }
          : item
      )
    );
  };
  
  // Remove an item
  const removeItem = (id: string) => {
    setItems(items.filter(item => item.id !== id));
  };
  
  // Update quantity
  const updateQuantity = (id: string, quantity: number) => {
    setItems(
      items.map(item => 
        item.id === id 
          ? { ...item, quantity }
          : item
      )
    );
  };
  
  // Clear the cart
  const clearCart = useCallback((isSuccessfulOrder = false) => {
    setItems([]);
    if (isSuccessfulOrder) {
      // Set a flag indicating the cart was cleared due to a successful order
      localStorage.setItem(CART_CLEARED_KEY, 'true');
    }
  }, []);
  
  // Calculate totals
  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  
  const subtotalPrice = items.reduce(
    (sum, item) => sum + (item.price * item.quantity), 
    0
  );
  
  // Calculate shipping based on weight
  const shippingCost = items.length > 0
    ? Math.max(
        5, // Minimum shipping charge
        10 + // Base fee
        items.reduce((sum, item) => {
          // $20 per kg shipping
          return sum + (item.weightInKg * item.quantity * 20);
        }, 0)
      )
    : 0;
  
  const totalPrice = subtotalPrice + shippingCost;
  
  // Get related items by base quote ID
  const getRelatedItems = (baseQuoteId: string): CartItem[] => {
    return items.filter(item => item.baseQuoteId === baseQuoteId);
  };
  
  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        updateItem,
        removeItem,
        updateQuantity,
        clearCart,
        totalItems,
        subtotalPrice,
        shippingCost,
        totalPrice,
        getRelatedItems,
        isInitialized
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

// Hook to use the cart context
export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
} 