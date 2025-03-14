"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '@/lib/cart';
import { GlowButton } from '@/components/ui/glow-button';

export default function CheckoutPage() {
  const { items, totalPrice, subtotalPrice, shippingCost, clearCart, removeItem, updateQuantity } = useCart();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  
  // Form states
  const [formData, setFormData] = useState({
    // Shipping info
    fullName: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: 'US',
    
    // Payment info
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Handle form changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when field is edited
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };
  
  // Validate current step
  const validateStep = () => {
    const newErrors: Record<string, string> = {};
    
    if (currentStep === 1) {
      // Validate shipping info
      if (!formData.fullName) newErrors.fullName = 'Name is required';
      if (!formData.email) newErrors.email = 'Email is required';
      if (formData.email && !/^\S+@\S+\.\S+$/.test(formData.email)) newErrors.email = 'Invalid email format';
      if (!formData.phone) newErrors.phone = 'Phone is required';
      if (!formData.address) newErrors.address = 'Address is required';
      if (!formData.city) newErrors.city = 'City is required';
      if (!formData.state) newErrors.state = 'State is required';
      if (!formData.zipCode) newErrors.zipCode = 'ZIP code is required';
    } else if (currentStep === 2) {
      // Validate payment info
      if (!formData.cardNumber) newErrors.cardNumber = 'Card number is required';
      if (formData.cardNumber && !/^\d{16}$/.test(formData.cardNumber.replace(/\s/g, ''))) {
        newErrors.cardNumber = 'Invalid card number';
      }
      if (!formData.cardName) newErrors.cardName = 'Name on card is required';
      if (!formData.expiryDate) newErrors.expiryDate = 'Expiry date is required';
      if (formData.expiryDate && !/^(0[1-9]|1[0-2])\/\d{2}$/.test(formData.expiryDate)) {
        newErrors.expiryDate = 'Invalid format (MM/YY)';
      }
      if (!formData.cvv) newErrors.cvv = 'CVV is required';
      if (formData.cvv && !/^\d{3,4}$/.test(formData.cvv)) {
        newErrors.cvv = 'Invalid CVV';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Navigate to next step
  const nextStep = () => {
    if (validateStep()) {
      setCurrentStep(prev => prev + 1);
    }
  };
  
  // Navigate to previous step
  const prevStep = () => {
    setCurrentStep(prev => prev - 1);
  };
  
  // Handle quantity change
  const handleQuantityChange = (id: string, newQuantity: number) => {
    if (newQuantity < 1) return;
    updateQuantity(id, newQuantity);
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateStep()) return;
    
    if (items.length === 0) {
      alert('Your cart is empty');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Here you would normally send the order to your backend
      // For now we'll just simulate a successful order
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Clear the cart
      clearCart();
      
      // Redirect to success page
      router.push('/checkout/success');
    } catch (error) {
      console.error('Error processing order:', error);
      alert('There was a problem processing your order. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // If cart is empty, show a message
  if (items.length === 0) {
    return (
      <div className="container px-4 md:px-6 py-12">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-3xl font-andale mb-6">Your Cart is Empty</h1>
          <p className="text-white/70 mb-8 font-avenir">
            You haven't added any items to your cart yet.
          </p>
          <GlowButton asChild>
            <a href="/quote">Get a Quote</a>
          </GlowButton>
        </div>
      </div>
    );
  }
  
  // Calculate total weight
  const totalWeight = items.reduce((total, item) => total + (item.weightInKg * item.quantity), 0);
  
  return (
    <div className="container px-4 md:px-6 py-12">
      <h1 className="text-3xl font-andale mb-12 text-center">Checkout</h1>
      
      {/* Estimated delivery notice */}
      <div className="glow-card rounded-none border border-[#F46036] bg-[#F46036]/10 p-4 mb-8 text-center">
        <p className="font-andale text-[#F46036]">
          All orders ship within 10 business days from order confirmation to delivery
        </p>
      </div>
      
      {/* Checkout steps */}
      <div className="mb-10">
        <div className="flex justify-center items-center">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${currentStep >= 1 ? 'border-[#5fe496] bg-[#5fe496]/10 text-[#5fe496]' : 'border-[#1E2A45] bg-[#0C1F3D]/30 text-white/50'}`}>1</div>
          <div className={`flex-1 h-1 max-w-[100px] ${currentStep >= 2 ? 'bg-[#5fe496]' : 'bg-[#1E2A45]'}`}></div>
          <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${currentStep >= 2 ? 'border-[#5fe496] bg-[#5fe496]/10 text-[#5fe496]' : 'border-[#1E2A45] bg-[#0C1F3D]/30 text-white/50'}`}>2</div>
          <div className={`flex-1 h-1 max-w-[100px] ${currentStep >= 3 ? 'bg-[#5fe496]' : 'bg-[#1E2A45]'}`}></div>
          <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${currentStep >= 3 ? 'border-[#5fe496] bg-[#5fe496]/10 text-[#5fe496]' : 'border-[#1E2A45] bg-[#0C1F3D]/30 text-white/50'}`}>3</div>
        </div>
        <div className="flex justify-center mt-2">
          <div className={`text-sm w-20 text-center ${currentStep >= 1 ? 'text-[#5fe496]' : 'text-white/50'}`}>Shipping</div>
          <div className="w-[100px]"></div>
          <div className={`text-sm w-20 text-center ${currentStep >= 2 ? 'text-[#5fe496]' : 'text-white/50'}`}>Payment</div>
          <div className="w-[100px]"></div>
          <div className={`text-sm w-20 text-center ${currentStep >= 3 ? 'text-[#5fe496]' : 'text-white/50'}`}>Review</div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Form section */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit}>
            {/* Step 1: Shipping Information */}
            {currentStep === 1 && (
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm">
                <h2 className="text-2xl font-andale mb-6">Shipping Information</h2>
                
                {/* Delivery estimate notice */}
                <div className="mb-6 p-3 border border-[#1E2A45] bg-[#0A1525]/50">
                  <p className="text-sm text-white/70 font-avenir mb-1">Estimated Delivery</p>
                  <p className="font-andale">10 business days from order confirmation</p>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-white/70 mb-2 font-avenir">Full Name</label>
                    <input
                      type="text"
                      name="fullName"
                      value={formData.fullName}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                    />
                    {errors.fullName && <p className="text-[#F46036] text-sm mt-1">{errors.fullName}</p>}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">Email</label>
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.email && <p className="text-[#F46036] text-sm mt-1">{errors.email}</p>}
                    </div>
                    
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">Phone</label>
                      <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.phone && <p className="text-[#F46036] text-sm mt-1">{errors.phone}</p>}
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-white/70 mb-2 font-avenir">Address</label>
                    <input
                      type="text"
                      name="address"
                      value={formData.address}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                    />
                    {errors.address && <p className="text-[#F46036] text-sm mt-1">{errors.address}</p>}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">City</label>
                      <input
                        type="text"
                        name="city"
                        value={formData.city}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.city && <p className="text-[#F46036] text-sm mt-1">{errors.city}</p>}
                    </div>
                    
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">State</label>
                      <input
                        type="text"
                        name="state"
                        value={formData.state}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.state && <p className="text-[#F46036] text-sm mt-1">{errors.state}</p>}
                    </div>
                    
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">ZIP Code</label>
                      <input
                        type="text"
                        name="zipCode"
                        value={formData.zipCode}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.zipCode && <p className="text-[#F46036] text-sm mt-1">{errors.zipCode}</p>}
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-white/70 mb-2 font-avenir">Country</label>
                    <select
                      name="country"
                      value={formData.country}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                    >
                      <option value="US">United States</option>
                      <option value="CA">Canada</option>
                      <option value="UK">United Kingdom</option>
                      <option value="AU">Australia</option>
                      <option value="DE">Germany</option>
                      <option value="FR">France</option>
                    </select>
                  </div>
                </div>
                
                <div className="mt-8 flex justify-end">
                  <GlowButton
                    onClick={nextStep}
                    className="bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
                  >
                    Continue to Payment
                  </GlowButton>
                </div>
              </div>
            )}
            
            {/* Step 2: Payment Information */}
            {currentStep === 2 && (
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm">
                <h2 className="text-2xl font-andale mb-6">Payment Information</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-white/70 mb-2 font-avenir">Card Number</label>
                    <input
                      type="text"
                      name="cardNumber"
                      value={formData.cardNumber}
                      onChange={handleChange}
                      placeholder="1234 5678 9012 3456"
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                    />
                    {errors.cardNumber && <p className="text-[#F46036] text-sm mt-1">{errors.cardNumber}</p>}
                  </div>
                  
                  <div>
                    <label className="block text-white/70 mb-2 font-avenir">Name on Card</label>
                    <input
                      type="text"
                      name="cardName"
                      value={formData.cardName}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                    />
                    {errors.cardName && <p className="text-[#F46036] text-sm mt-1">{errors.cardName}</p>}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">Expiry Date</label>
                      <input
                        type="text"
                        name="expiryDate"
                        value={formData.expiryDate}
                        onChange={handleChange}
                        placeholder="MM/YY"
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.expiryDate && <p className="text-[#F46036] text-sm mt-1">{errors.expiryDate}</p>}
                    </div>
                    
                    <div>
                      <label className="block text-white/70 mb-2 font-avenir">CVV</label>
                      <input
                        type="text"
                        name="cvv"
                        value={formData.cvv}
                        onChange={handleChange}
                        placeholder="123"
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-3 rounded-none text-white font-avenir"
                      />
                      {errors.cvv && <p className="text-[#F46036] text-sm mt-1">{errors.cvv}</p>}
                    </div>
                  </div>
                </div>
                
                <div className="mt-8 flex justify-between">
                  <GlowButton
                    type="button"
                    onClick={prevStep}
                    variant="outline"
                  >
                    Back to Shipping
                  </GlowButton>
                  
                  <GlowButton
                    type="button"
                    onClick={nextStep}
                    className="bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
                  >
                    Review Order
                  </GlowButton>
                </div>
              </div>
            )}
            
            {/* Step 3: Order Review */}
            {currentStep === 3 && (
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-8 backdrop-blur-sm">
                <h2 className="text-2xl font-andale mb-6">Review Your Order</h2>
                
                {/* Delivery estimate notice */}
                <div className="mb-6 p-3 border border-[#F46036] bg-[#F46036]/10 text-[#F46036]">
                  <p className="font-andale">Your order will be delivered within 10 business days</p>
                </div>
                
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-andale mb-2">Shipping Information</h3>
                    <div className="text-white/70 font-avenir">
                      <p>{formData.fullName}</p>
                      <p>{formData.email}</p>
                      <p>{formData.phone}</p>
                      <p>{formData.address}</p>
                      <p>{formData.city}, {formData.state} {formData.zipCode}</p>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-xl font-andale mb-2">Payment Information</h3>
                    <div className="text-white/70 font-avenir">
                      <p>Card ending in {formData.cardNumber.slice(-4)}</p>
                      <p>{formData.cardName}</p>
                      <p>Expires {formData.expiryDate}</p>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-xl font-andale mb-2">Order Summary</h3>
                    <div className="space-y-2">
                      {items.map(item => (
                        <div key={item.id} className="p-3 border border-[#1E2A45] bg-[#0A1525]/50">
                          <div className="flex justify-between">
                            <div className="font-medium">{item.process}</div>
                            <div>${(item.price * item.quantity).toFixed(2)}</div>
                          </div>
                          <div className="text-sm text-white/70">
                            <div>Material: {item.material}</div>
                            <div>Finish: {item.finish}</div>
                            <div>Quantity: {item.quantity}</div>
                            <div>Estimated Weight: {(item.weightInKg * item.quantity).toFixed(3)} kg</div>
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <div className="mt-4 space-y-2">
                      <div className="flex justify-between py-2 border-b border-[#1E2A45] text-white/70">
                        <div>Subtotal</div>
                        <div>${subtotalPrice.toFixed(2)}</div>
                      </div>
                      
                      <div className="flex justify-between py-2 border-b border-[#1E2A45] text-white/70">
                        <div>Shipping ($20/kg × {totalWeight.toFixed(3)} kg)</div>
                        <div>${shippingCost.toFixed(2)}</div>
                      </div>
                      
                      <div className="flex justify-between py-2 text-[#5fe496] font-medium">
                        <div>Total</div>
                        <div>${totalPrice.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-8 flex justify-between">
                  <GlowButton
                    type="button"
                    onClick={prevStep}
                    variant="outline"
                  >
                    Back to Payment
                  </GlowButton>
                  
                  <GlowButton
                    type="submit"
                    disabled={isSubmitting}
                    className="bg-[#F46036] text-white hover:bg-[#F46036]/80"
                  >
                    {isSubmitting ? 'Processing...' : 'Place Order'}
                  </GlowButton>
                </div>
              </div>
            )}
          </form>
        </div>
        
        {/* Order summary sidebar */}
        <div className="lg:col-span-1">
          <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-6 backdrop-blur-sm sticky top-10">
            <h2 className="text-xl font-andale mb-4">Order Summary</h2>
            
            {/* Delivery notice */}
            <div className="p-3 mb-4 border border-[#1E2A45] bg-[#0A1525]/50">
              <p className="text-sm text-[#5fe496] font-andale">10-day delivery</p>
            </div>
            
            <div className="mb-4 max-h-[50vh] overflow-y-auto pr-2">
              {items.map(item => (
                <div key={item.id} className="mb-4 pb-4 border-b border-[#1E2A45]">
                  <div className="flex justify-between mb-1">
                    <div className="font-medium">{item.process}</div>
                    <button
                      onClick={() => removeItem(item.id)}
                      className="text-[#F46036] text-sm hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="text-sm text-white/70">
                    <div>Material: {item.material}</div>
                    <div>Finish: {item.finish}</div>
                    <div>File: {item.fileName}</div>
                    <div>Weight: {(item.weightInKg * item.quantity).toFixed(3)} kg</div>
                  </div>
                  <div className="flex justify-between mt-2 items-center">
                    <div className="flex items-center">
                      <button
                        onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                        className="w-8 h-8 bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center text-white"
                      >
                        -
                      </button>
                      <span className="w-10 text-center">{item.quantity}</span>
                      <button
                        onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                        className="w-8 h-8 bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center text-white"
                      >
                        +
                      </button>
                    </div>
                    <div className="font-medium">${(item.price * item.quantity).toFixed(2)}</div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="flex justify-between py-2 border-b border-[#1E2A45] text-white/70">
              <div>Subtotal</div>
              <div>${subtotalPrice.toFixed(2)}</div>
            </div>
            
            <div className="flex justify-between py-2 border-b border-[#1E2A45] text-white/70">
              <div>Shipping</div>
              <div>${shippingCost.toFixed(2)}</div>
            </div>
            
            <div className="flex justify-between py-4 text-lg font-andale">
              <div>Total</div>
              <div>${totalPrice.toFixed(2)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 