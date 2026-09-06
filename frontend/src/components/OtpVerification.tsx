'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

const OTP_LENGTH = 6;
const RESEND_SECONDS = 60;

type Status = 'idle' | 'verifying' | 'verified' | 'error';

export default function OtpVerification() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signIn } = useAuth();
  // Get email or phone from URL
  const identifier = searchParams.get('identifier') || '';

  const [otp, setOtp] = useState<string[]>(Array(OTP_LENGTH).fill(''));

  const [seconds, setSeconds] = useState<number>(RESEND_SECONDS);

  const [status, setStatus] = useState<Status>('idle');

  const [errorMessage, setErrorMessage] = useState('');

  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);

  /*
   * -----------------------------------------
   * OTP COUNTDOWN
   * -----------------------------------------
   */

  useEffect(() => {
    if (!identifier) {
      router.push('/signin');
    }
  }, [identifier, router]);

  useEffect(() => {
    if (seconds <= 0) return;

    const timer = setTimeout(() => {
      setSeconds(prev => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [seconds]);

  /*
   * -----------------------------------------
   * OTP INPUT
   * -----------------------------------------
   */

  const updateDigit = (index: number, value: string) => {
    // Only allow numbers
    if (!/^\d?$/.test(value)) {
      return;
    }

    const newOtp = [...otp];

    newOtp[index] = value;

    setOtp(newOtp);

    setStatus('idle');
    setErrorMessage('');

    // Move to next input
    if (value && index < OTP_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  /*
   * -----------------------------------------
   * BACKSPACE
   * -----------------------------------------
   */

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  /*
   * -----------------------------------------
   * PASTE OTP
   * -----------------------------------------
   */

  const handlePaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    e.preventDefault();

    const pastedOtp = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);

    if (!pastedOtp) return;

    const newOtp = Array(OTP_LENGTH).fill('');

    pastedOtp.split('').forEach((digit, index) => {
      newOtp[index] = digit;
    });

    setOtp(newOtp);

    setStatus('idle');
    setErrorMessage('');

    const focusIndex = Math.min(pastedOtp.length, OTP_LENGTH - 1);

    inputsRef.current[focusIndex]?.focus();
  };

  /*
   * -----------------------------------------
   * VERIFY OTP
   * -----------------------------------------
   */

  const handleVerify = async () => {
    const enteredOtp = otp.join('');

    // Identifier check
    if (!identifier) {
      setErrorMessage('Email or phone number is missing.');
      setStatus('error');
      return;
    }

    // OTP validation
    if (!enteredOtp) {
      setErrorMessage('Please enter the OTP.');
      setStatus('error');
      return;
    }

    if (!/^\d{6}$/.test(enteredOtp)) {
      setErrorMessage('Please enter a valid 6-digit OTP.');
      setStatus('error');
      return;
    }

    try {
      //   setStatus('verifying');
      //   setErrorMessage('');

      //   const response = await fetch('http://localhost:5000/api/auth/verify-otp', {
      //     method: 'POST',

      //     headers: {
      //       'Content-Type': 'application/json',
      //     },

      //     // Important if backend uses cookies
      //     credentials: 'include',

      //     body: JSON.stringify({
      //       identifier: identifier,
      //       otp: enteredOtp,
      //     }),
      //   });

      //   const data = await response.json();
      //    signIn(data.user)  // context auth

      //   if (!response.ok) {
      //     setStatus('error');

      //     setErrorMessage(data.message || 'Invalid or expired OTP.');

      //     return;
      //   }

      /*
       * OTP successfully verified
       */

      // console.log('OTP verified successfully:', data);

      setStatus('verified');

      /*
       * Backend should have created the
       * authentication session/cookie here.
       */

      router.push('/');
    } catch (error) {
      console.error('OTP verification failed:', error);

      setStatus('error');

      setErrorMessage('Something went wrong. Please try again.');
    }
  };

  /*
   * -----------------------------------------
   * RESEND OTP
   * -----------------------------------------
   */

  const handleResend = async () => {
    if (seconds > 0) {
      return;
    }

    if (!identifier) {
      setErrorMessage('Email or phone number is missing.');

      setStatus('error');

      return;
    }

    try {
      // setErrorMessage('');
      // setStatus('idle');
      // const response = await fetch('http://localhost:5000/api/auth/send-otp', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({
      //     identifier: identifier,
      //   }),
      // });
      // const data = await response.json();
      // if (!response.ok) {
      //   setStatus('error');
      //   setErrorMessage(data.message || 'Failed to resend OTP.');
      //   return;
      // }
      // console.log('OTP resent successfully:', data);
      // // Clear old OTP
      // setOtp(Array(OTP_LENGTH).fill(''));
      // // Restart timer
      // setSeconds(RESEND_SECONDS);
      // // Focus first box
      // inputsRef.current[0]?.focus();
    } catch (error) {
      console.error('Resend OTP failed:', error);

      setStatus('error');

      setErrorMessage('Something went wrong. Please try again.');
    }
  };

  /*
   * -----------------------------------------
   * VERIFIED
   * -----------------------------------------
   */

  if (status === 'verified') {
    return (
      <div className="otpverification-page">
        <div className="otpverification-success-wrap">
          <h1 className="otpverification-title">Verified</h1>

          <p className="otpverification-subtitle">Your account has been verified successfully.</p>
        </div>
      </div>
    );
  }

  /*
   * -----------------------------------------
   * UI
   * -----------------------------------------
   */

  return (
    <div className="otpverification-page">
      <div className="otpverification-container">
        <div className="otpverification-card">
          <h1 className="otpverification-title">Verify your account</h1>

          <p className="otpverification-description">Enter the 6-digit OTP sent to your email or phone number.</p>

          {/* OTP INPUTS */}

          <div className="otpverification-otp-row" onPaste={handlePaste}>
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={element => {
                  inputsRef.current[index] = element;
                }}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                value={digit}
                onChange={e => updateDigit(index, e.target.value)}
                onKeyDown={e => handleKeyDown(e, index)}
                className={`otpverification-otp-input${status === 'error' ? ' otpverification-otp-input-error' : ''}`}
                autoComplete={index === 0 ? 'one-time-code' : 'off'}
              />
            ))}
          </div>

          {/* ERROR */}

          {errorMessage && <p className="otpverification-error-text">{errorMessage}</p>}

          {/* VERIFY */}

          <button
            type="button"
            onClick={handleVerify}
            disabled={otp.join('').length !== OTP_LENGTH || status === 'verifying'}
            className="otpverification-verify-button">
            {status === 'verifying' ? 'Verifying...' : 'Verify'}
          </button>

          {/* RESEND */}

          <div className="otpverification-resend-wrap">
            {seconds > 0 ? (
              <p className="otpverification-resend-text">
                Resend code in <span className="otpverification-resend-count">{seconds}s</span>
              </p>
            ) : (
              <button type="button" onClick={handleResend} className="otpverification-resend-button">
                Resend code
              </button>
            )}
          </div>
        </div>

        <p className="otpverification-edit-text">
          Wrong details?{' '}
          <Link
            href="/signin"
            type="button"
            className="otpverification-edit-link"
            onClick={() => router.push('/signin')}>
            Go back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
