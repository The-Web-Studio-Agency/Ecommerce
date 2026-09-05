'use client';

import { useState, useMemo, SubmitEvent, ChangeEvent } from 'react';

import { useCart } from '@/context/CartContext';
import { useRouter } from 'next/navigation';

interface CheckoutFormState {
  email: string;
  phone: string;
  firstName: string;
  lastName: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  wantGst: boolean;
  gstin: string;
  paymentMethod: 'cod' | 'online';
  promo: string;
}

type FormErrors = Partial<Record<keyof CheckoutFormState, string>>;

const INDIAN_STATES = [
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chhattisgarh',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
];

const INDIAN_UNION_TERRITORIES = [
  'Andaman and Nicobar Islands',
  'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Jammu and Kashmir',
  'Ladakh',
  'Lakshadweep',
  'Puducherry',
];

const INITIAL_FORM: CheckoutFormState = {
  email: '',
  phone: '',

  firstName: '',
  lastName: '',

  address: '',
  city: '',
  state: '',
  pincode: '',

  wantGst: false,
  gstin: '',

  paymentMethod: 'cod',

  promo: '',
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const PHONE_RE = /^[6-9]\d{9}$/;

const PINCODE_RE = /^\d{6}$/;

const GSTIN_RE = /^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

function validate(form: CheckoutFormState): FormErrors {
  const errors: FormErrors = {};

  if (!form.email.trim()) {
    errors.email = 'Email is required.';
  } else if (!EMAIL_RE.test(form.email.trim())) {
    errors.email = 'Enter a valid email address.';
  }
  if (!form.phone.trim()) {
    errors.phone = 'Phone number is required.';
  } else if (!PHONE_RE.test(form.phone.trim())) {
    errors.phone = 'Enter a valid 10-digit Indian mobile number.';
  }

  if (!form.firstName.trim()) {
    errors.firstName = 'First name is required.';
  }
  if (!form.lastName.trim()) {
    errors.lastName = 'Last name is required.';
  }
  if (!form.address.trim()) {
    errors.address = 'Address is required.';
  }
  if (!form.city.trim()) {
    errors.city = 'City is required.';
  }

  if (!form.state.trim()) {
    errors.state = 'Select a state.';
  }
  if (!form.pincode.trim()) {
    errors.pincode = 'PIN code is required.';
  } else if (!PINCODE_RE.test(form.pincode.trim())) {
    errors.pincode = 'Enter a valid 6-digit PIN code.';
  }

  if (form.wantGst) {
    if (!form.gstin.trim()) {
      errors.gstin = 'GSTIN is required for a GST invoice.';
    } else if (!GSTIN_RE.test(form.gstin.trim().toUpperCase())) {
      errors.gstin = 'Enter a valid 15-character GSTIN.';
    }
  }

  return errors;
}

interface FieldProps {
  id: keyof CheckoutFormState;

  label: string;

  placeholder?: string;

  type?: string;

  value: string;

  span?: boolean;

  error?: string;

  maxLength?: number;

  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
}

function Field({ id, label, placeholder, type = 'text', value, span, error, maxLength, onChange }: FieldProps) {
  return (
    <label htmlFor={id} className={`checkout-page__field${span ? ' checkout-page__field--span' : ''}`}>
      <span className="checkout-page__label">{label}</span>

      <input
        id={id}
        name={id}
        type={type}
        value={value}
        placeholder={placeholder}
        maxLength={maxLength}
        onChange={onChange}
        className={`checkout-page__input${error ? ' checkout-page__input--error' : ''}`}
      />

      {error && <span className="checkout-page__error">{error}</span>}
    </label>
  );
}

export default function CheckoutPage() {
  const { cartItems } = useCart();
  const [form, setForm] = useState<CheckoutFormState>(INITIAL_FORM);
  const router = useRouter();

  const [errors, setErrors] = useState<FormErrors>({});

  const [submitting, setSubmitting] = useState(false);

  const [submitError, setSubmitError] = useState<string | null>(null);

  const [discount, setDiscount] = useState(0);

  const itemCount = useMemo(() => {
    return cartItems.reduce((total, item) => total + item.quantity, 0);
  }, [cartItems]);

  const subtotal = useMemo(() => {
    return cartItems.reduce((total, item) => total + item.price * item.quantity, 0);
  }, [cartItems]);

  const shipping = 0;

  const tax = useMemo(() => {
    const taxableAmount = Math.max(0, subtotal - discount);

    return Math.round(taxableAmount * 0.18);
  }, [subtotal, discount]);

  const total = Math.max(0, subtotal - discount) + shipping + tax;

  function handleChange(e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const target = e.target;

    const { name, value } = target;

    const isCheckbox = target instanceof HTMLInputElement && target.type === 'checkbox';

    let newValue: string | boolean = value;

    if (isCheckbox) {
      newValue = target.checked;
    }

    if (name === 'firstName' || name === 'lastName') {
      newValue = value.replace(/[^A-Za-z ]/g, '');
    }

    if (name === 'phone') {
      newValue = value.replace(/[^0-9]/g, '').slice(0, 10);
    }

    if (name === 'pincode') {
      newValue = value.replace(/[^0-9]/g, '').slice(0, 6);
    }

    if (name === 'email') {
      newValue = value.replace(/[^A-Za-z0-9@.]/g, '');
    }

    if (name === 'city') {
      newValue = value.replace(/[^A-Za-z ]/g, '');
    }

    if (name === 'gstin') {
      newValue = value
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '')
        .slice(0, 15);
    }

    /* ---------------------------------------------
       UPDATE FORM
    --------------------------------------------- */

    setForm(prev => ({
      ...prev,
      [name]: newValue,
    }));

    /* ---------------------------------------------
       REMOVE FIELD ERROR
    --------------------------------------------- */

    setErrors(prev => ({
      ...prev,
      [name]: undefined,
    }));

    setSubmitError(null);
  }

  /* =====================================================
     APPLY PROMO
  ===================================================== */

  function applyPromo() {
    const code = form.promo.trim().toUpperCase();

    if (!code) {
      setDiscount(0);
      return;
    }

    /* ---------------------------------------------
       DEMO PROMO CODE
    --------------------------------------------- */

    if (code === 'ZEEN10') {
      const discountAmount = subtotal * 0.1;

      setDiscount(discountAmount);

      setSubmitError(null);
    } else {
      setDiscount(0);

      setSubmitError('That promo code is not valid.');
    }
  }

  /* =====================================================
     SUBMIT ORDER
  ===================================================== */

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();

    setSubmitError(null);

    /* ---------------------------------------------
       CHECK EMPTY CART
    --------------------------------------------- */

    if (cartItems.length === 0) {
      setSubmitError('Your cart is empty.');

      return;
    }

    /* ---------------------------------------------
       VALIDATE FORM
    --------------------------------------------- */

    const validationErrors = validate(form);

    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);

    try {
      const orderData = {
        contact: {
          email: form.email.trim(),

          phone: form.phone.trim(),
        },
        shippingAddress: {
          firstName: form.firstName.trim(),

          lastName: form.lastName.trim(),

          address: form.address.trim(),

          city: form.city.trim(),

          state: form.state,

          pincode: form.pincode.trim(),
        },
        gst: form.wantGst
          ? {
              wantGst: true,

              gstin: form.gstin.trim().toUpperCase(),
            }
          : {
              wantGst: false,
            },

        paymentMethod: form.paymentMethod,
        promoCode: form.promo.trim() ? form.promo.trim().toUpperCase() : null,

        /* ---------------------------------------------
           CART ITEMS

           We only send the information needed
           to identify the cart item.

           DO NOT send:
           price
           subtotal
           tax
           total

           Backend should calculate those.
        --------------------------------------------- */

        items: cartItems.map(item => ({
          productId: item.productId,

          color: item.color,

          size: item.size,

          quantity: item.quantity,
        })),
      };

      console.log('ORDER DATA:', orderData);

      /*
      const response = await fetch(
        'http://localhost:5000/orders',
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json',
          },

          // Important:
          // Sends the authentication cookie
          // to your Express backend.

          credentials: 'include',

          body:
            JSON.stringify(orderData),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
          'Failed to place order'
        );
      }

      console.log(
        'ORDER CREATED:',
        data
      );

      // Example backend response:
      //
      // {
      //   orderId: "ORD12345"
      // }

      // Then redirect:
      //
      router.push(
        `/order-success?orderId=${data.orderId}`
      );
      */

      /* =================================================
         TEMPORARY DEMO
      ================================================= */

      await new Promise(resolve => setTimeout(resolve, 1000));

      console.log('Ready to send to backend:', orderData);

      alert('Checkout form is valid. Backend order API will be connected next.');
      router.push(`/order-success/${"1234"}`)
    } catch (error) {
      console.error('Checkout error:', error);

      setSubmitError('Could not place the order. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  /* =====================================================
     EMPTY CART
  ===================================================== */

  if (cartItems.length === 0) {
    return (
      <div className="checkout-page">
        <div className="checkout-page__container">
          <div className="checkout-page__confirmation">
            <h1 className="checkout-page__title">Your cart is empty</h1>

            <p className="checkout-page__confirmation-text">
              Add some products to your cart before proceeding to checkout.
            </p>
          </div>
        </div>
      </div>
    );
  }

  /* =====================================================
     UI
  ===================================================== */

  return (
    <div className="checkout-page">
      <div className="checkout-page__container">
        {/* ============================================
            HEADER
        ============================================ */}

        <div className="checkout-page__header">
          <h1 className="checkout-page__title">Checkout</h1>

          <span className="checkout-page__count">
            ({itemCount} {itemCount === 1 ? 'item' : 'items'})
          </span>
        </div>

        {/* ============================================
            CHECKOUT FORM
        ============================================ */}

        <form className="checkout-page__grid" onSubmit={handleSubmit} noValidate>
          {/* ==========================================
              LEFT COLUMN
          ========================================== */}

          <div className="checkout-page__column">
            {/* ========================================
                CONTACT
            ======================================== */}

            <section className="checkout-page__section">
              <h2 className="checkout-page__section-title">Contact</h2>

              <div className="checkout-page__row">
                {/* EMAIL */}

                <Field
                  id="email"
                  label="Email"
                  type="email"
                  placeholder="william@mail.com"
                  value={form.email}
                  maxLength={50}
                  onChange={handleChange}
                  error={errors.email}
                />

                {/* PHONE */}

                <Field
                  id="phone"
                  label="Phone number"
                  type="tel"
                  placeholder="9876543210"
                  value={form.phone}
                  maxLength={10}
                  onChange={handleChange}
                  error={errors.phone}
                />
              </div>
            </section>

            {/* ========================================
                SHIPPING ADDRESS
            ======================================== */}

            <section className="checkout-page__section">
              <h2 className="checkout-page__section-title">Shipping address</h2>

              <div className="checkout-page__row">
                {/* FIRST NAME */}

                <Field
                  id="firstName"
                  label="First name"
                  placeholder="Samantha"
                  value={form.firstName}
                  maxLength={50}
                  onChange={handleChange}
                  error={errors.firstName}
                />

                {/* LAST NAME */}

                <Field
                  id="lastName"
                  label="Last name"
                  placeholder="Doe"
                  value={form.lastName}
                  maxLength={50}
                  onChange={handleChange}
                  error={errors.lastName}
                />

                {/* ADDRESS */}

                <Field
                  id="address"
                  label="Address"
                  placeholder="Your address"
                  value={form.address}
                  maxLength={200}
                  onChange={handleChange}
                  error={errors.address}
                  span
                />

                {/* CITY */}

                <Field
                  id="city"
                  label="City"
                  placeholder="Kozhikode"
                  value={form.city}
                  maxLength={50}
                  onChange={handleChange}
                  error={errors.city}
                />

                {/* STATE */}

                <label htmlFor="state" className="checkout-page__field checkout-page__field--span">
                  <span className="checkout-page__label">State</span>

                  <select
                    id="state"
                    name="state"
                    value={form.state}
                    onChange={handleChange}
                    className={`checkout-page__select${errors.state ? ' checkout-page__input--error' : ''}`}>
                    <option value="">Select a state</option>

                    <optgroup label="States">
                      {INDIAN_STATES.map(state => (
                        <option key={state} value={state}>
                          {state}
                        </option>
                      ))}
                    </optgroup>

                    <optgroup label="Union Territories">
                      {INDIAN_UNION_TERRITORIES.map(state => (
                        <option key={state} value={state}>
                          {state}
                        </option>
                      ))}
                    </optgroup>
                  </select>

                  {errors.state && <span className="checkout-page__error">{errors.state}</span>}
                </label>

                {/* PINCODE */}

                <Field
                  id="pincode"
                  label="PIN code"
                  placeholder="673001"
                  value={form.pincode}
                  maxLength={6}
                  onChange={handleChange}
                  error={errors.pincode}
                />
              </div>

              {/* ======================================
                  GST
              ====================================== */}

              <div className="checkout-page__checkbox-row">
                <label className="checkout-page__checkbox-label">
                  <input
                    type="checkbox"
                    name="wantGst"
                    checked={form.wantGst}
                    onChange={handleChange}
                    className="checkout-page__checkbox"
                  />
                  I need a GST invoice for this order
                </label>

                {form.wantGst && (
                  <div className="checkout-page__row checkout-page__row--single">
                    <Field
                      id="gstin"
                      label="GSTIN"
                      placeholder="22AAAAA0000A1Z5"
                      value={form.gstin}
                      maxLength={15}
                      onChange={handleChange}
                      error={errors.gstin}
                    />
                  </div>
                )}
              </div>
            </section>

            {/* ========================================
                PAYMENT
            ======================================== */}

            <section className="checkout-page__section">
              <h2 className="checkout-page__section-title">Payment</h2>

              <div className="checkout-page__payment-options">
                {/* COD */}

                <label className="checkout-page__payment-option">
                  <input
                    type="radio"
                    name="paymentMethod"
                    value="cod"
                    checked={form.paymentMethod === 'cod'}
                    onChange={handleChange}
                  />

                  <div>
                    <strong>Cash on Delivery</strong>

                    <p>Pay when your order is delivered.</p>
                  </div>
                </label>

                {/* ONLINE */}

                <label className="checkout-page__payment-option">
                  <input
                    type="radio"
                    name="paymentMethod"
                    value="online"
                    checked={form.paymentMethod === 'online'}
                    onChange={handleChange}
                  />

                  <div>
                    <strong>Online Payment</strong>

                    <p>Pay securely online.</p>
                  </div>
                </label>
              </div>

              <p className="checkout-page__note">
                Online payment integration will be connected with the payment provider later.
              </p>
            </section>
          </div>

          {/* ==========================================
              RIGHT COLUMN
          ========================================== */}

          <aside className="checkout-page__summary">
            <h2 className="checkout-page__summary-title">Order Summary</h2>

            {/* ========================================
                CART ITEMS
            ======================================== */}

            <ul className="checkout-page__items">
              {cartItems.map(item => (
                <li key={`${item.productId}-${item.color}-${item.size}`} className="checkout-page__item">
                  {/* IMAGE */}

                  <div className="checkout-page__item-image">
                    <img src={item.image} alt={item.name} />
                  </div>

                  {/* INFORMATION */}

                  <div className="checkout-page__item-info">
                    <p className="checkout-page__item-title">{item.name}</p>

                    {/* COLOR */}

                    <p className="checkout-page__item-meta">
                      Color:
                      <span
                        style={{
                          display: 'inline-block',

                          width: '14px',

                          height: '14px',

                          borderRadius: '50%',

                          backgroundColor: item.color,

                          border: '1px solid #ccc',

                          marginLeft: '6px',

                          verticalAlign: 'middle',
                        }}
                      />
                    </p>

                    {/* SIZE */}

                    <p className="checkout-page__item-meta">Size: {item.size}</p>

                    {/* QUANTITY */}

                    <p className="checkout-page__item-meta">Qty: {item.quantity}</p>
                  </div>

                  {/* PRICE */}

                  <div className="checkout-page__item-price">
                    ₹{(item.price * item.quantity).toLocaleString('en-IN')}
                  </div>
                </li>
              ))}
            </ul>

            {/* ========================================
                TOTALS
            ======================================== */}

            <div className="checkout-page__totals">
              {/* SUBTOTAL */}

              <div className="checkout-page__totals-row">
                <span>Subtotal ({itemCount} items)</span>

                <span>₹{subtotal.toLocaleString('en-IN')}</span>
              </div>

              {/* DISCOUNT */}

              {discount > 0 && (
                <div className="checkout-page__totals-row">
                  <span>Discount</span>

                  <span>
                    −₹
                    {discount.toLocaleString('en-IN')}
                  </span>
                </div>
              )}

              {/* SHIPPING */}

              <div className="checkout-page__totals-row">
                <span>Shipping</span>

                <span>{shipping === 0 ? 'Free' : `₹${shipping}`}</span>
              </div>

              {/* GST */}

              <div className="checkout-page__totals-row">
                <span>GST (18%)</span>

                <span>₹{tax.toLocaleString('en-IN')}</span>
              </div>
            </div>

            {/* ========================================
                PROMO
            ======================================== */}

            <div className="checkout-page__promo">
              <input
                name="promo"
                value={form.promo}
                onChange={handleChange}
                placeholder="Promo code"
                maxLength={30}
                className="checkout-page__promo-input"
              />

              <button type="button" onClick={applyPromo} className="checkout-page__promo-button">
                Apply
              </button>
            </div>

            {/* ========================================
                TOTAL
            ======================================== */}

            <div className="checkout-page__total-row">
              <span>Total</span>

              <span>₹{total.toLocaleString('en-IN')}</span>
            </div>

            {/* ========================================
                ERROR
            ======================================== */}

            {submitError && <p className="checkout-page__submit-error">{submitError}</p>}

            {/* ========================================
                PLACE ORDER
            ======================================== */}

            <button type="submit" className="checkout-page__submit" disabled={submitting}>
              {submitting ? 'Placing order…' : form.paymentMethod === 'online' ? 'Pay Now' : 'Place Order'}
            </button>

            {/* ========================================
                NOTES
            ======================================== */}

            <div className="checkout-page__notes">
              <p className="checkout-page__note">Secure checkout</p>

              <p className="checkout-page__note">Free delivery on this order</p>
            </div>
          </aside>
        </form>
      </div>
    </div>
  );
}
