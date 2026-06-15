import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { confirmPasswordReset, requestPasswordReset } from '../lib/auth';

type Step = 'request' | 'confirm';

export function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('request');
  const [identifier, setIdentifier] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRequest(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await requestPasswordReset(identifier.trim());
      setNotice('If an account exists, a reset code has been sent to the registered channel.');
      setStep('confirm');
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    try {
      await confirmPasswordReset(identifier.trim(), otp.trim(), newPassword);
      navigate('/login');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'reset_failed';
      setError(
        msg === 'otp_invalid' || msg === 'otp_expired' || msg.includes('otp')
          ? 'Incorrect or expired code. Please request a new one.'
          : 'Could not reset your password. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          <p className="font-display text-h1 text-forest font-medium">Kyros</p>
          <p className="font-body text-body text-stone mt-1">Doctor Portal</p>
        </div>

        <div className="bg-white rounded-card p-8 shadow-sm">
          <h1 className="font-display text-h3 text-forest font-medium mb-6">Reset password</h1>

          {error && (
            <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-5">
              {error}
            </div>
          )}
          {notice && (
            <div className="bg-jade/10 border border-jade/30 text-forest font-body text-caption rounded-md px-4 py-3 mb-5">
              {notice}
            </div>
          )}

          {step === 'request' ? (
            <form onSubmit={(e) => { void handleRequest(e); }} className="space-y-5">
              <div>
                <label className="block font-body text-caption text-stone mb-1.5">Email or phone</label>
                <input
                  type="text"
                  autoComplete="username"
                  required
                  value={identifier}
                  onChange={e => setIdentifier(e.target.value)}
                  className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
                  placeholder="doctor@example.com"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-forest text-ivory font-body text-body font-semibold py-3 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
              >
                {loading ? 'Sending…' : 'Send reset code'}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => { void handleConfirm(e); }} className="space-y-5">
              <div>
                <label className="block font-body text-caption text-stone mb-1.5">Verification code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  required
                  value={otp}
                  onChange={e => setOtp(e.target.value)}
                  className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors tracking-[0.4em] text-center"
                  placeholder="••••••"
                />
              </div>
              <div>
                <label className="block font-body text-caption text-stone mb-1.5">New password</label>
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
                  placeholder="••••••••"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-forest text-ivory font-body text-body font-semibold py-3 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
              >
                {loading ? 'Updating…' : 'Set new password'}
              </button>
            </form>
          )}
        </div>

        <p className="text-center font-body text-caption text-stone mt-6">
          <button type="button" onClick={() => navigate('/login')} className="text-forest hover:underline">
            Back to sign in
          </button>
        </p>
      </div>
    </div>
  );
}
