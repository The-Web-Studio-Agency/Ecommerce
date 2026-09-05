'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface LoginErrors {
  identifier: string;
  password: string;
}

export default function AdminSignIn() {
  const router = useRouter();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');

  const [errors, setErrors] = useState<LoginErrors>({
    identifier: '',
    password: '',
  });

  const [loading, setLoading] = useState(false);

  const clearForm = () => {
    setIdentifier('');
    setPassword('');
  };

  // Check whether input is an email
  const isEmail = (value: string) => {
    return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(value);
  };


 
  const handleSubmit = async (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    const value = identifier.trim();

    const newErrors: LoginErrors = {
      identifier: '',
      password: '',
    };

    // ================= VALIDATION =================

    // Identifier validation
    if (!value) {
      newErrors.identifier = 'Email is required';
    } else if (!isEmail(value)) {
      newErrors.identifier = 'Enter a valid email ';
    }

    // Password validation
    if (!password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);

    // Stop if validation failed
    if (newErrors.identifier || newErrors.password) {
      return;
    }

    // ================= API REQUEST =================

    try {
      //   setLoading(true);

      //   const response = await fetch('http://localhost:5000/api/auth/signin', {
      //     method: 'POST',
      //     headers: {
      //       'Content-Type': 'application/json',
      //     },
      //     credentials: 'include',
      //     body: JSON.stringify({
      //       identifier: value,
      //       password: password,
      //     }),
      //   });

      //   const data = await response.json();

      //   if (!response.ok) {
      //     setErrors({
      //       identifier: data.message || 'Invalid email/phone or password',
      //       password: '',
      //     });

      //     return;
      //   }

      //   console.log('Login successful:', data);

      // Clear form
    //   clearForm();

      // Go to admin page

      if (identifier === 'admin@gmail.com' && password === 'admin@123') {
        router.push('/admin');
      }
      else{
        throw new Error('Incorrect password')
      }
    } catch (error) {
      console.error('Sign in error:', error);

      setErrors({
        identifier: 'Something went wrong. Please try again.',
        password: '',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-page-card">
        <div className="login-page-grid">
          {/* ================= LEFT IMAGE ================= */}

          <div className="login-page-image-panel">
            <Image
              src="/assets/cloth-0.webp"
              alt="Portrait against a light neutral backdrop"
              width={500}
              height={500}
              className="login-page-image"
              priority
            />
          </div>

          {/* ================= RIGHT FORM ================= */}

          <div className="login-page-form-panel">
            <div className="login-page-form-inner">
              <h1 className="login-page-heading">Sign in</h1>

              {/* ================= LOGIN FORM ================= */}

              <form className="login-page-fields" onSubmit={handleSubmit} noValidate>
                {/* ================= EMAIL / PHONE ================= */}

                <div>
                  <input
                    type="text"
                    placeholder="Enter you email"
                    value={identifier}
                    maxLength={60}
                    className="login-page-input"
                    onChange={e => {
                      const inputValue = e.target.value.replace(/[^A-Za-z0-9@.]/g, '');

                      setIdentifier(inputValue);

                      setErrors(prev => ({
                        ...prev,
                        identifier: '',
                      }));
                    }}
                  />

                  {errors.identifier && <p className="login-page-error">{errors.identifier}</p>}
                </div>

                {/* ================= PASSWORD ================= */}

                <div>
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    maxLength={100}
                    className="login-page-input"
                    onChange={e => {
                      setPassword(e.target.value);

                      setErrors(prev => ({
                        ...prev,
                        password: '',
                      }));
                    }}
                  />

                  {errors.password && <p className="login-page-error">{errors.password}</p>}
                </div>

                {/* ================= FORGOT PASSWORD ================= */}

                {/* ================= SUBMIT ================= */}

                <button type="submit" className="login-page-submit-button" disabled={loading}>
                  {loading ? 'Signing in...' : 'Sign in'}
                </button>
              </form>

              {/* ================= DIVIDER ================= */}

              {/* ================= GOOGLE ================= */}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ========================= Google Icon ========================= */

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
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
