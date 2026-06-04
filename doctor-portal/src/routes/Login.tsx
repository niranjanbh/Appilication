import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../lib/auth';

export function Login() {
  const navigate = useNavigate();
  const [emailOrPhone, setEmailOrPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(emailOrPhone, password);
      navigate('/dashboard');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed';
      setError(msg === 'doctor_role_required'
        ? 'This portal is for doctors only. Please use the patient app.'
        : msg === '401' || msg.toLowerCase().includes('invalid')
          ? 'Incorrect email / phone or password.'
          : msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-10">
          <p className="font-display text-h1 text-forest font-medium">Kyros</p>
          <p className="font-body text-body text-stone mt-1">Doctor Portal</p>
        </div>

        <div className="bg-white rounded-card p-8 shadow-sm">
          <h1 className="font-display text-h3 text-forest font-medium mb-6">Sign in</h1>

          {error && (
            <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-5">
              {error}
            </div>
          )}

          <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-5">
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">
                Email or phone
              </label>
              <input
                type="text"
                autoComplete="username"
                required
                value={emailOrPhone}
                onChange={e => setEmailOrPhone(e.target.value)}
                className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
                placeholder="doctor@example.com"
              />
            </div>

            <div>
              <label className="block font-body text-caption text-stone mb-1.5">
                Password
              </label>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-forest text-ivory font-body text-body font-semibold py-3 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center font-body text-caption text-stone mt-6">
          Patient? Use the Kyros mobile app.
        </p>
      </div>
    </div>
  );
}
