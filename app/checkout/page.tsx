"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '@/lib/cart';
import { useLoading } from '@/lib/loading-context';
import { sendOrderNotification } from '@/lib/slack';
import { GlowButton } from '@/components/ui/glow-button';

export default function CheckoutPage() {
  const { items, totalPrice, subtotalPrice, shippingCost, clearCart, removeItem, updateQuantity } = useCart();
  const router = useRouter();
  const { showLoadingOverlay, hideLoadingOverlay } = useLoading();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState(1); // 1 = Shipping, 2 = Payment

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
    specialInstructions: '',

    // Payment info
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Handle form changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
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
      if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.email = 'Invalid email format';
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
    showLoadingOverlay();

    try {
      // Generate a random order number
      const orderNumber = `ORD-${Math.floor(Math.random() * 1000000).toString().padStart(6, '0')}`;

      // Send order notification to Slack
      await sendOrderNotification({
        orderId: orderNumber,
        customerName: formData.fullName,
        customerEmail: formData.email,
        items: items.map(item => ({
          id: item.id,
          fileName: item.fileName,
          process: item.process,
          material: item.material,
          finish: item.finish,
          quantity: item.quantity,
          price: item.price
        })),
        totalPrice,
        currency: 'USD',
        specialInstructions: formData.specialInstructions,
        shippingAddress: {
          line1: formData.address,
          city: formData.city,
          state: formData.state,
          postal_code: formData.zipCode,
          country: formData.country
        }
      });

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Clear the cart
      clearCart();

      // Redirect to success page
      router.push('/checkout/success');
    } catch (error) {
      console.error('Error processing order:', error);
      alert('There was a problem processing your order. Please try again.');
      hideLoadingOverlay();
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

  return (
    <div className="container px-4 md:px-6 py-8">
      <h1 className="text-3xl font-andale mb-8 text-center">Checkout</h1>

      {/* Estimated delivery notice */}
      <div className="glow-card rounded-none border border-[#F46036] bg-[#F46036]/10 p-3 mb-6 text-center">
        <p className="font-andale text-[#F46036]">
          All orders ship within 10 business days from order confirmation to delivery
        </p>
      </div>

      {/* Checkout steps */}
      <div className="mb-6">
        <div className="flex justify-center items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 1 ? 'bg-[#F46036] text-white' : 'bg-[#1E2A45] text-white/70'}`}>
            1
          </div>
          <div className={`h-1 w-12 ${currentStep > 1 ? 'bg-[#F46036]' : 'bg-[#1E2A45]'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 2 ? 'bg-[#F46036] text-white' : 'bg-[#1E2A45] text-white/70'}`}>
            2
          </div>
        </div>
        <div className="flex justify-center mt-1">
          <div className={`text-xs w-20 text-center ${currentStep === 1 ? 'text-white' : 'text-white/70'}`}>Shipping</div>
          <div className={`text-xs w-20 text-center ${currentStep === 2 ? 'text-white' : 'text-white/70'}`}>Payment</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form section */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit}>
            {/* Step 1: Shipping Information */}
            {currentStep === 1 && (
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-5 backdrop-blur-sm">
                <h2 className="text-xl font-andale mb-4">Shipping Information</h2>

                <div className="space-y-2">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                      <label className="block text-white/70 mb-1 text-xs font-avenir">Full Name</label>
                      <input
                        type="text"
                        name="fullName"
                        value={formData.fullName}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                      />
                      {errors.fullName && <p className="text-[#F46036] text-xs mt-0.5">{errors.fullName}</p>}
                    </div>

                    <div>
                      <label className="block text-white/70 mb-1 text-xs font-avenir">Email</label>
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                      />
                      {errors.email && <p className="text-[#F46036] text-xs mt-0.5">{errors.email}</p>}
                    </div>
                  </div>

                  <div>
                    <label className="block text-white/70 mb-1 text-xs font-avenir">Phone</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                    />
                    {errors.phone && <p className="text-[#F46036] text-xs mt-0.5">{errors.phone}</p>}
                  </div>

                  <div>
                    <label className="block text-white/70 mb-1 text-xs font-avenir">Address</label>
                    <input
                      type="text"
                      name="address"
                      value={formData.address}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                    />
                    {errors.address && <p className="text-[#F46036] text-xs mt-0.5">{errors.address}</p>}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    <div>
                      <label className="block text-white/70 mb-1 text-xs font-avenir">City</label>
                      <input
                        type="text"
                        name="city"
                        value={formData.city}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                      />
                      {errors.city && <p className="text-[#F46036] text-xs mt-0.5">{errors.city}</p>}
                    </div>

                    <div>
                      <label className="block text-white/70 mb-1 text-xs font-avenir">State</label>
                      <input
                        type="text"
                        name="state"
                        value={formData.state}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                      />
                      {errors.state && <p className="text-[#F46036] text-xs mt-0.5">{errors.state}</p>}
                    </div>

                    <div>
                      <label className="block text-white/70 mb-1 text-xs font-avenir">ZIP Code</label>
                      <input
                        type="text"
                        name="zipCode"
                        value={formData.zipCode}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
                      />
                      {errors.zipCode && <p className="text-[#F46036] text-xs mt-0.5">{errors.zipCode}</p>}
                    </div>

                    <div>
                      <label className="block text-white/70 mb-1 text-xs font-avenir">Country</label>
                      <select
                        name="country"
                        value={formData.country}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm"
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

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-2 items-end">
                    <div className="md:col-span-3">
                      <label className="block text-white/70 mb-1 text-xs font-avenir">Special Instructions (Optional)</label>
                      <textarea
                        name="specialInstructions"
                        value={formData.specialInstructions}
                        onChange={handleChange}
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-1.5 rounded-none text-white font-avenir text-sm min-h-[60px]"
                        placeholder="Any special requirements or notes for your order..."
                      />
                    </div>
                    <div className="md:col-span-1 flex items-end justify-end h-full">
                      <GlowButton
                        type="button"
                        onClick={nextStep}
                        className="bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80 w-full md:w-auto"
                      >
                        Continue to Payment
                      </GlowButton>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Payment Information */}
            {currentStep === 2 && (
              <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-5 backdrop-blur-sm">
                <h2 className="text-xl font-andale mb-4">Payment Information</h2>

                <div className="space-y-3">
                  <div>
                    <label className="block text-white/70 mb-1 text-sm font-avenir">Card Number</label>
                    <input
                      type="text"
                      name="cardNumber"
                      value={formData.cardNumber}
                      onChange={handleChange}
                      placeholder="1234 5678 9012 3456"
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir"
                    />
                    {errors.cardNumber && <p className="text-[#F46036] text-xs mt-1">{errors.cardNumber}</p>}
                  </div>

                  <div>
                    <label className="block text-white/70 mb-1 text-sm font-avenir">Name on Card</label>
                    <input
                      type="text"
                      name="cardName"
                      value={formData.cardName}
                      onChange={handleChange}
                      className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir"
                    />
                    {errors.cardName && <p className="text-[#F46036] text-xs mt-1">{errors.cardName}</p>}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-white/70 mb-1 text-sm font-avenir">Expiry Date</label>
                      <input
                        type="text"
                        name="expiryDate"
                        value={formData.expiryDate}
                        onChange={handleChange}
                        placeholder="MM/YY"
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir"
                      />
                      {errors.expiryDate && <p className="text-[#F46036] text-xs mt-1">{errors.expiryDate}</p>}
                    </div>

                    <div>
                      <label className="block text-white/70 mb-1 text-sm font-avenir">CVV</label>
                      <input
                        type="text"
                        name="cvv"
                        value={formData.cvv}
                        onChange={handleChange}
                        placeholder="123"
                        className="w-full bg-[#0A1525] border border-[#1E2A45] p-2 rounded-none text-white font-avenir"
                      />
                      {errors.cvv && <p className="text-[#F46036] text-xs mt-1">{errors.cvv}</p>}
                    </div>
                  </div>
                </div>

                <div className="mt-5 flex justify-between">
                  <GlowButton
                    type="button"
                    onClick={prevStep}
                    variant="outline"
                  >
                    Back to Shipping
                  </GlowButton>
                </div>
              </div>
            )}
          </form>
        </div>

        {/* Order summary sidebar */}
        <div className="lg:col-span-1">
          <div className="glow-card rounded-none border border-[#1E2A45] bg-[#0C1F3D]/30 p-5 backdrop-blur-sm sticky top-10">
            <h2 className="text-xl font-andale mb-3">Order Summary</h2>

            {/* Delivery notice */}
            <div className="p-2 mb-3 border border-[#1E2A45] bg-[#0A1525]/50">
              <p className="text-sm text-[#5fe496] font-andale">10-day delivery</p>
            </div>

            <div className="mb-3 max-h-[40vh] overflow-y-auto pr-2">
              {items.map((item, index) => (
                <div key={item.id || `item-${index}`} className="mb-3 pb-3 border-b border-[#1E2A45]">
                  <div className="flex justify-between mb-1">
                    <div className="font-medium">{item.process || 'Custom Part'}</div>
                    <button
                      onClick={() => removeItem(item.id)}
                      className="text-[#F46036] text-sm hover:underline"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="text-sm text-white/70">
                    <div>Material: {item.material || 'Standard'}</div>
                    <div>Finish: {item.finish || 'Standard'}</div>
                    <div>File: {item.fileName || 'Uploaded file'}</div>
                    <div>Weight: {((item.weightInKg || 0.1) * item.quantity).toFixed(3)} kg</div>
                  </div>
                  <div className="flex justify-between mt-2 items-center">
                    <div className="flex items-center">
                      <button
                        onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                        className="w-7 h-7 bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center text-white"
                      >
                        -
                      </button>
                      <span className="w-8 text-center">{item.quantity}</span>
                      <button
                        onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                        className="w-7 h-7 bg-[#0A1525] border border-[#1E2A45] flex items-center justify-center text-white"
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

            <div className="flex justify-between py-3 text-lg font-andale">
              <div>Total</div>
              <div>${totalPrice.toFixed(2)}</div>
            </div>

            {/* Place Order button moved here */}
            <div className="mt-4">
              <GlowButton
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting || currentStep !== 2}
                className="w-full bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80"
              >
                {isSubmitting ? 'Processing...' : 'Place Order'}
              </GlowButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
