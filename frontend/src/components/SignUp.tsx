'use client';

import Link from 'next/link';
import { useState } from 'react';
import Image from 'next/image';
import { auto } from '@popperjs/core';

export default function SignUp() {
  const [showPassword, setShowPassword] = useState(false);
  const [agreed, setAgreed] = useState(true);

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [errors, setErrors] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    agreed: '',
  });

  const clearForm = () => {
    setFirstName('');
    setLastName('');
    setEmail('');
    setPassword('');
  };

  const handleSubmit = async (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    const newErrors = {
      firstName: '',
      lastName: '',
      email: '',
      password: '',
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

    // Email validation
    if (!email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[A-Za-z0-9]+@[A-Za-z0-9]+\.[A-Za-z]{2,}$/.test(email)) {
      newErrors.email = 'Enter a valid email address';
    }

    // Password validation
    if (!password.trim()) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
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
      firstName,
      lastName,
      email,
      password,
    };
    //   try {
    //   const response = await fetch("http://localhost:5000/api/auth/register", {
    //     method: "POST",
    //     headers: {
    //       "Content-Type": "application/json",
    //     },
    //     body: JSON.stringify(signupData),
    //   });

    //   const data = await response.json();

    //   if (!response.ok) {
    //     console.log("Signup failed:", data);
    //     return;
    //   }

    //   console.log("Signup successful:",clearForm());

    // } catch (error) {
    //   console.log("Something went wrong:", error);
    // }
    console.log(signupData);
    console.log('Signup successful:');
    clearForm();
  };

  return (
    <div className="page">
      <div className="card">
        {/* Left panel */}
        <div className="imageWrap">
          <Image src="/assets/cloth-0.webp" alt="Desert dunes at dusk" height={500} width={500} className="image" />
        </div>

        {/* Right panel */}
        <div className="formWrap">
          <div className="formInner">
            <h1 className="title">Create an account</h1>

            <p className="subtitle">
              Already have an account?{' '}
              <Link href="/signin" className="link">
                Sign In
              </Link>
            </p>

            <form className="form" onSubmit={handleSubmit}>
              {/* First name + Last name */}
              <div className="nameRow">
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

              {/* Email */}
              <div>
                <input
                  maxLength={60}
                  type="email"
                  value={email}
                  placeholder="Email"
                  className="input"
                  onChange={e => {
                    const inputEmail = e.target.value.replace(/[^A-Za-z0-9@.]/g, '');
                    setEmail(inputEmail);
                    setErrors(prev => ({
                      ...prev,
                      email: '',
                    }));
                  }}
                />

                {errors.email && <p className="error">{errors.email}</p>}
              </div>

              {/* Password */}
              <div>
                <div className="passwordField">
                  <input
                    maxLength={60}
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    placeholder="Enter your password"
                    className="input"
                    onChange={e => {
                      const inputPassword = e.target.value.replace(/\s/g, '');
                      setPassword(inputPassword);
                      setErrors(prev => ({
                        ...prev,
                        password: '',
                      }));
                    }}
                  />

                  <button
                    type="button"
                    onClick={() => setShowPassword(s => !s)}
                    className="eyeButton"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>

                {errors.password && <p className="error">{errors.password}</p>}
              </div>

              {/* Terms and conditions */}
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

              {/* Submit */}
              <button type="submit" className="submitButton">
                Create account
              </button>
            </form>

            {/* Divider */}
            <div className="divider">
              <span className="dividerLine" />

              <span className="dividerText">Or register with</span>

              <span className="dividerLine" />
            </div>

            {/* Social login */}
            <div className="oauthRow">
              <button className="oauthButton" type="button">
                <GoogleIcon />
                Google
              </button>

              <button className="oauthButton" type="button">
                <AppleIcon />
                Apple
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================
   Eye Icon
========================= */

function EyeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" strokeLinecap="round" strokeLinejoin="round" />

      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/* =========================
   Eye Off Icon
========================= */

function EyeOffIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a20.3 20.3 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a20.3 20.3 0 0 1-2.16 3.19M14.12 14.12a3 3 0 1 1-4.24-4.24M1 1l22 22"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
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

/* =========================
   Apple Icon
========================= */

function AppleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M16.365 1.43c0 1.14-.462 2.06-1.155 2.75-.75.75-1.97 1.33-2.94 1.25-.14-1.09.44-2.23 1.16-2.94.75-.75 2.02-1.31 2.94-1.06zm3.97 17.13c-.53 1.22-.78 1.77-1.46 2.85-.95 1.5-2.29 3.37-3.95 3.39-1.48.02-1.86-.96-3.87-.95-2.01.01-2.43.97-3.91.95-1.66-.02-2.93-1.7-3.88-3.2C1.1 17.98.36 14.1 1.5 11.44c.62-1.43 1.75-2.34 2.99-2.36 1.25-.02 2.03.96 3.68.96 1.65 0 2.35-.96 3.68-.94 1.13.02 2.34.63 3.02 1.73-2.65 1.45-2.22 5.24.13 6.7z" />
    </svg>
  );
}
