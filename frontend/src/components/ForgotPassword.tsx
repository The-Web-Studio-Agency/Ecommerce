'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';

interface ForgotPasswordErrors {
  email: string;
}

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState<ForgotPasswordErrors>({
    email: '',
  });
  const clearForm = () => {
    setEmail('');
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const newErrors: ForgotPasswordErrors = {
      email: '',
    };

    // Email validation
    if (!email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email)) {
      newErrors.email = 'Enter a valid email address';
    }

    setErrors(newErrors);

    // Stop if validation fails
    if (Object.values(newErrors).some(error => error !== '')) {
      return;
    }

    const forgotPasswordData = { email };

    // try {
    //   const response = await fetch("http://localhost:5000/api/auth/forgot-password", {
    //     method: "POST",
    //     headers: { "Content-Type": "application/json" },
    //     body: JSON.stringify(forgotPasswordData),
    //   });
    //   const data = await response.json();
    //   if (!response.ok) {
    //     console.log("Request failed:", data);
    //     return;
    //   }
    //   console.log("Reset link sent:", clearForm());
    // } catch (error) {
    //   console.log("Something went wrong:", error);
    // }

    console.log(forgotPasswordData);
    console.log('Reset link sent:');
    setSubmitted(true);
    clearForm();
  };

  return (
    <div className="forgot-password-wrapper">
      <div className="forgot-password-card">
        <div className="forgot-password-grid">
          {/* Left: image panel */}
          <div className="forgot-password-image-panel">
            <Image
              src="/assets/cloth-0.webp"
              alt="Portrait against a light neutral backdrop"
        
              fill
              className="forgot-password-image"
            />
          </div>

          <div className="forgot-password-form-panel">
            <div className="forgot-password-form-inner">
              <h1 className="forgot-password-heading">Forgot password?</h1>
              <p className="forgot-password-subtext">
                Enter the email linked to your account and we&rsquo;ll send you a link to reset your password.
              </p>

              {submitted ? (
                <p className="forgot-password-success">
                  If an account exists for that email, a reset link is on its way.
                </p>
              ) : (
                <form className="forgot-password-fields" onSubmit={handleSubmit} noValidate>
                  <div className='forget-password-input-container'>
                    <input
                      maxLength={60}
                      type="email"
                      value={email}
                      placeholder="Email"
                      className="forgot-password-input"
                      onChange={e => {
                        const inputEmail = e.target.value.replace(/[^A-Za-z0-9@.]/g, '');
                        setEmail(inputEmail);
                        setErrors(prev => ({
                          ...prev,
                          email: '',
                        }));
                      }}
                    />
                    {errors.email && <p className="forgot-password-error">{errors.email}</p>}
                  </div>

                  {/* Submit */}
                  <button type="submit" className="forgot-password-submit-button">
                    Send reset link
                  </button>
                </form>
              )}

              <p className="forgot-password-back">
                <Link href="/signin" className="forgot-password-back-link">
                  Back to log in
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
