'use client';

import Link from 'next/link';
import { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

export default function SignUp() {
  const [agreed, setAgreed] = useState(true);
  const router = useRouter()
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [identifier, setIdentifier] = useState('');

  const [errors, setErrors] = useState({
    firstName: '',
    lastName: '',
    identifier: '',
    agreed: '',
  });

  const clearForm = () => {
    setFirstName('');
    setLastName('');
    setIdentifier('');
  };

  // Email validation
  const isEmail = (value: string) => {
    return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(value);
  };

  // Phone validation
  const isPhone = (value: string) => {
    return /^[0-9]{10}$/.test(value);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const newErrors = {
      firstName: '',
      lastName: '',
      identifier: '',
      agreed: '',
    };

    // First name validation
    if (!firstName.trim()) {
      newErrors.firstName = 'First name is required';
    }

    // Last name validation
    if (!lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    }

    // Email / Phone validation
    const value = identifier.trim();

    if (!value) {
      newErrors.identifier = 'Email or phone number is required';
    } else if (!isEmail(value) && !isPhone(value)) {
      newErrors.identifier = 'Enter a valid email or 10-digit phone number';
    }

    // Terms validation
    if (!agreed) {
      newErrors.agreed = 'Please accept the Terms & Conditions';
    }

    setErrors(newErrors);

    // Stop if validation fails
    if (Object.values(newErrors).some(error => error !== '')) {
      return;
    }

    const signupData = {
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      identifier: value,
    };

    console.log('Signup data:', signupData);

   router.push('/')
    /*
    try {
      const response = await fetch(
        'http://localhost:5000/api/auth/register',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(signupData),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        console.log('Signup failed:', data);
        return;
      }

      console.log('Signup successful:', data);

      // Redirect to OTP verification page
      // router.push(
      //   `/verify-otp?identifier=${encodeURIComponent(value)}`
      // );

    } catch (error) {
      console.log('Something went wrong:', error);
    }
    */
   router.push(`/otp-verification?identifier=${encodeURIComponent(value)}`)

    clearForm();
  };

  return (
    <div className="page">
      <div className="card">
        {/* ================= LEFT PANEL ================= */}

        <div className="imageWrap">
          <img src="/assets/cloth-0.webp" alt="Desert dunes at dusk"  className="image" />
        </div>

        {/* ================= RIGHT PANEL ================= */}

        <div className="formWrap">
          <div className="formInner">
            <h1 className="title">Create an account</h1>

            <p className="subtitle">
              Already have an account?{' '}
              <Link href="/signin" className="link">
                Sign In
              </Link>
            </p>

            <form className="form" onSubmit={handleSubmit} noValidate>
              {/* ================= FIRST + LAST NAME ================= */}

              <div className="nameRow">
                {/* First name */}

                <div>
                  <input
                    maxLength={60}
                    type="text"
                    value={firstName}
                    placeholder="First name"
                    className="input"
                    onChange={e => {
                      const inputName = e.target.value.replace(/[^A-Za-z ]/g, '');

                      setFirstName(inputName);

                      setErrors(prev => ({
                        ...prev,
                        firstName: '',
                      }));
                    }}
                  />

                  {errors.firstName && <p className="error">{errors.firstName}</p>}
                </div>

                {/* Last name */}

                <div>
                  <input
                    maxLength={40}
                    type="text"
                    value={lastName}
                    placeholder="Last name"
                    className="input"
                    onChange={e => {
                      const inputName = e.target.value.replace(/[^A-Za-z ]/g, '');

                      setLastName(inputName);

                      setErrors(prev => ({
                        ...prev,
                        lastName: '',
                      }));
                    }}
                  />

                  {errors.lastName && <p className="error">{errors.lastName}</p>}
                </div>
              </div>

              {/* ================= EMAIL / PHONE ================= */}

              <div>
                <input
                  maxLength={60}
                  type="text"
                  value={identifier}
                  placeholder="Email or phone number"
                  className="input"
                  autoComplete="username"
                  onChange={e => {
                    const inputValue = e.target.value.replace(/[^A-Za-z0-9@.+]/g, '');

                    setIdentifier(inputValue);

                    setErrors(prev => ({
                      ...prev,
                      identifier: '',
                    }));
                  }}
                />

                {errors.identifier && <p className="error">{errors.identifier}</p>}
              </div>

              {/* ================= TERMS ================= */}

              <div>
                <label className="checkboxLabel">
                  <button
                    type="button"
                    onClick={() => {
                      setAgreed(a => !a);

                      setErrors(prev => ({
                        ...prev,
                        agreed: '',
                      }));
                    }}
                    className={`checkbox ${agreed ? 'checkboxChecked' : ''}`}
                    aria-pressed={agreed}>
                    {agreed && <CheckIcon />}
                  </button>

                  <span className="checkboxText">
                    I agree to the{' '}
                    <a href="#" className="link">
                      Terms &amp; Conditions
                    </a>
                  </span>
                </label>

                {errors.agreed && <p className="error">{errors.agreed}</p>}
              </div>

              {/* ================= SUBMIT ================= */}

              <button type="submit" className="submitButton">
                Create account
              </button>
            </form>

            {/* ================= DIVIDER ================= */}

            <div className="divider">
              <span className="dividerLine" />

              <span className="dividerText">Or register with</span>

              <span className="dividerLine" />
            </div>

            {/* ================= SOCIAL LOGIN ================= */}

            <div className="oauthRow">
              <button className="oauthButton" type="button">
                <GoogleIcon />
                Google
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================
   Check Icon
========================= */

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* =========================
   Google Icon
========================= */

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1v-.01z"
      />

      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.25 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A10.99 10.99 0 0 0 12 23z"
      />

      <path
        fill="#FBBC05"
        d="M5.84 14.09A6.6 6.6 0 0 1 5.5 12c0-.73.12-1.43.34-2.09V7.07H2.18A10.99 10.99 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z"
      />

      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1a10.99 10.99 0 0 0-9.82 6.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}
