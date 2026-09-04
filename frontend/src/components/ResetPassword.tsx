'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';


interface ResetPasswordErrors {
  password: string;
  confirmPassword: string;
}

export default function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const [errors, setErrors] = useState<ResetPasswordErrors>({
    password: '',
    confirmPassword: '',
  });

  const clearForm = () => {
    setPassword('');
    setConfirmPassword('');
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const newErrors: ResetPasswordErrors = {
      password: '',
      confirmPassword: '',
    };

    // Password validation
    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (!/[A-Z]/.test(password)) {
      newErrors.password = 'Password must include an uppercase letter';
    } else if (!/[0-9]/.test(password)) {
      newErrors.password = 'Password must include a number';
    }

    // Confirm password validation
    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please re-enter your password';
    } else if (password && confirmPassword !== password) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);

    // Stop if validation fails
    if (Object.values(newErrors).some(error => error !== '')) {
      return;
    }

    const resetPasswordData = { password };

    // try {
    //   const response = await fetch("http://localhost:5000/api/auth/reset-password", {
    //     method: "POST",
    //     headers: { "Content-Type": "application/json" },
    //     body: JSON.stringify(resetPasswordData),
    //   });
    //   const data = await response.json();
    //   if (!response.ok) {
    //     console.log("Reset failed:", data);
    //     return;
    //   }
    //   console.log("Password reset:", clearForm());
    // } catch (error) {
    //   console.log("Something went wrong:", error);
    // }

    console.log(resetPasswordData);
    console.log('Password reset:');
    setSubmitted(true);
    clearForm();
  };

  return (
    <div className="reset-password-wrapper">
      <div className="reset-password-card">
        <div className="reset-password-grid">
          {/* Left: image panel */}
          <div className="reset-password-image-panel">
            <Image
              src="/assets/cloth-0.webp"
              alt="Portrait against a light neutral backdrop"
              fill
              sizes="(min-width: 768px) 50vw, 100vw"
              className="reset-password-image"
              priority
            />
          </div>

          {/* Right: form panel */}
          <div className="reset-password-form-panel">
            <div className="reset-password-form-inner">
              <h1 className="reset-password-heading">Reset password</h1>
              <p className="reset-password-subtext">Choose a new password for your account.</p>

              {submitted ? (
                <p className="reset-password-success">
                  Your password has been reset. You can now log in with your new password.
                </p>
              ) : (
                <form className="reset-password-fields" onSubmit={handleSubmit} noValidate>
                  {/* New password */}
                  <div>
                    <div className="reset-password-password-wrapper">
                      <input
                        maxLength={60}
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        placeholder="Enter new password"
                        className="reset-password-password-input"
                        onChange={e => {
                          setPassword(e.target.value);
                          setErrors(prev => ({ ...prev, password: '' }));
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(s => !s)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        className="reset-password-eye-button">
                        {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                      </button>
                    </div>
                    {errors.password && <p className="reset-password-error">{errors.password}</p>}
                  </div>

                  {/* Confirm password */}
                  <div>
                    <div className="reset-password-password-wrapper">
                      <input
                        maxLength={60}
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={confirmPassword}
                        placeholder="Re-enter new password"
                        className="reset-password-password-input"
                        onChange={e => {
                          setConfirmPassword(e.target.value);
                          setErrors(prev => ({ ...prev, confirmPassword: '' }));
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(s => !s)}
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                        className="reset-password-eye-button">
                        {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                      </button>
                    </div>
                    {errors.confirmPassword && <p className="reset-password-error">{errors.confirmPassword}</p>}
                  </div>

                  {/* Submit */}
                  <button type="submit" className="reset-password-submit-button">
                    Reset password
                  </button>
                </form>
              )}

              <p className="reset-password-back">
                <Link href="/login" className="reset-password-back-link">
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

/* ========================= Eye Icon ========================= */
function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/* ========================= Eye Off Icon ========================= */
function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a20.3 20.3 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a20.3 20.3 0 0 1-2.16 3.19M14.12 14.12a3 3 0 1 1-4.24-4.24M1 1l22 22"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
