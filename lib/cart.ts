/**
 * Cart functionality for the application
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Cart item interface
 */
export interface CartItem {
  id: string;
  fileName: string;
  process: string;
  material: string;
  finish: string;
  quantity: number;
  price: number;
  weightInKg: number;
}

/**
 * Cart store interface
 */
interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
}

/**
 * Cart store implementation using Zustand
 */
export const useCart = create<CartStore>()(
  persist(
    (set) => ({
      items: [],
      
      addItem: (item) => set((state) => {
        const existingItem = state.items.find((i) => i.id === item.id);
        
        if (existingItem) {
          return {
            items: state.items.map((i) =>
              i.id === item.id
                ? { ...i, quantity: i.quantity + item.quantity }
                : i
            ),
          };
        }
        
        return { items: [...state.items, item] };
      }),
      
      removeItem: (id) => set((state) => ({
        items: state.items.filter((item) => item.id !== id),
      })),
      
      updateQuantity: (id, quantity) => set((state) => ({
        items: state.items.map((item) =>
          item.id === id ? { ...item, quantity } : item
        ),
      })),
      
      clearCart: () => set({ items: [] }),
    }),
    {
      name: 'cart-storage',
    }
  )
);
