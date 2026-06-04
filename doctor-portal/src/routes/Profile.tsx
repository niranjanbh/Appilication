import { useEffect, useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

interface DoctorProfile {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  nmc_registration_number: string;
  nmc_state_council: string | null;
  specialty: string[];
  conditions_treated: string[];
  consultation_languages: string[];
  bio_short: string | null;
  bio_long: string | null;
  status: string;
  consultation_duration_minutes_default: number;
  buffer_time_minutes: number;
  has_bank_details: boolean;
}

function formatCategory(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function ReadOnlyRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex gap-4 py-2.5 border-b border-stone/10 last:border-0">
      <dt className="font-body text-caption text-stone w-44 shrink-0">{label}</dt>
      <dd className="font-body text-body text-ink">{value || '—'}</dd>
    </div>
  );
}

export function Profile() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['doctor-me'],
    queryFn: () => apiFetch<DoctorProfile>('/v1/doctor/me'),
  });

  // Profile edit state
  const [bioShort, setBioShort] = useState('');
  const [bioLong, setBioLong] = useState('');
  const [languages, setLanguages] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [conditionsTreated, setConditionsTreated] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Bank details state
  const [bankName, setBankName] = useState('');
  const [accountHolder, setAccountHolder] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [ifscCode, setIfscCode] = useState('');
  const [bankSaving, setBankSaving] = useState(false);
  const [bankSaved, setBankSaved] = useState(false);
  const [bankError, setBankError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setBioShort(data.bio_short ?? '');
      setBioLong(data.bio_long ?? '');
      setLanguages(data.consultation_languages.join(', '));
      setSpecialty(data.specialty.join(', '));
      setConditionsTreated(data.conditions_treated.join(', '));
    }
  }, [data]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await apiFetch('/v1/doctor/me', {
        method: 'PATCH',
        body: JSON.stringify({
          bio_short: bioShort || null,
          bio_long: bioLong || null,
          consultation_languages: languages.split(',').map(s => s.trim()).filter(Boolean),
          specialty: specialty.split(',').map(s => s.trim()).filter(Boolean),
          conditions_treated: conditionsTreated.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ['doctor-me'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleBankSave(e: FormEvent) {
    e.preventDefault();
    setBankSaving(true);
    setBankError(null);
    setBankSaved(false);
    try {
      await apiFetch('/v1/doctor/me/bank-details', {
        method: 'POST',
        body: JSON.stringify({
          account_holder_name: accountHolder,
          account_number: accountNumber,
          ifsc_code: ifscCode.toUpperCase(),
          bank_name: bankName,
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ['doctor-me'] });
      setBankSaved(true);
      setTimeout(() => setBankSaved(false), 5000);
      // Clear sensitive fields from UI state
      setAccountNumber('');
      setIfscCode('');
    } catch (err) {
      setBankError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setBankSaving(false);
    }
  }

  if (isLoading || !data) {
    return (
      <div className="px-8 py-8">
        <p className="font-body text-body text-stone">Loading…</p>
      </div>
    );
  }

  return (
    <div className="px-8 py-8 max-w-2xl">
      <h1 className="font-display text-h2 text-forest font-medium mb-6">Profile</h1>

      {/* Read-only */}
      <div className="bg-white rounded-card p-5 mb-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-3">Credentials</h2>
        <dl>
          <ReadOnlyRow label="Name" value={data.name} />
          <ReadOnlyRow label="NMC registration" value={data.nmc_registration_number} />
          <ReadOnlyRow label="State council" value={data.nmc_state_council} />
          <ReadOnlyRow label="Specialty" value={data.specialty.map(formatCategory).join(', ')} />
          <ReadOnlyRow label="Conditions treated" value={data.conditions_treated.map(formatCategory).join(', ')} />
          <ReadOnlyRow label="Duration (default)" value={`${data.consultation_duration_minutes_default} min`} />
          <ReadOnlyRow label="Status" value={data.status} />
        </dl>
        <p className="font-body text-caption text-stone mt-3">
          NMC credentials are set by Kyros admin and cannot be edited here.
        </p>
      </div>

      {/* Editable */}
      <div className="bg-white rounded-card p-5">
        <h2 className="font-display text-h3 text-forest font-medium mb-4">Edit profile</h2>

        {error && (
          <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-4">
            {error}
          </div>
        )}
        {saved && (
          <div className="bg-sage/20 border border-sage/40 text-forest font-body text-caption rounded-md px-4 py-3 mb-4">
            Profile saved.
          </div>
        )}

        <form onSubmit={(e) => { void handleSave(e); }} className="space-y-5">
          <div>
            <label className="block font-body text-caption text-stone mb-1.5">Short bio</label>
            <input
              type="text"
              maxLength={500}
              value={bioShort}
              onChange={e => setBioShort(e.target.value)}
              className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
              placeholder="One-line professional summary"
            />
          </div>

          <div>
            <label className="block font-body text-caption text-stone mb-1.5">Extended bio</label>
            <textarea
              rows={5}
              value={bioLong}
              onChange={e => setBioLong(e.target.value)}
              className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors resize-y"
              placeholder="Detailed background for your public profile"
            />
          </div>

          <div>
            <label className="block font-body text-caption text-stone mb-1.5">
              Specialty <span className="text-stone/60">(comma-separated, e.g. thyroid, pcos)</span>
            </label>
            <input
              type="text"
              value={specialty}
              onChange={e => setSpecialty(e.target.value)}
              className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
              placeholder="thyroid, weight"
            />
          </div>

          <div>
            <label className="block font-body text-caption text-stone mb-1.5">
              Conditions treated <span className="text-stone/60">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={conditionsTreated}
              onChange={e => setConditionsTreated(e.target.value)}
              className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
              placeholder="hypothyroidism, pcos"
            />
          </div>

          <div>
            <label className="block font-body text-caption text-stone mb-1.5">
              Consultation languages <span className="text-stone/60">(comma-separated, e.g. en, hi)</span>
            </label>
            <input
              type="text"
              value={languages}
              onChange={e => setLanguages(e.target.value)}
              className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
              placeholder="en, hi"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="bg-forest text-ivory font-body text-body font-semibold px-6 py-2.5 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </form>
      </div>

      {/* Bank details */}
      <div className="bg-white rounded-card p-5 mt-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-1">Bank details</h2>
        <p className="font-body text-caption text-stone mb-4">
          {data.has_bank_details
            ? 'Bank details on file. Update below to change them.'
            : 'No bank details on file. Add them for revenue share.'}
          {' '}Details are encrypted and only visible to Kyros admin.
        </p>

        {bankError && (
          <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-4">
            {bankError}
          </div>
        )}
        {bankSaved && (
          <div className="bg-sage/20 border border-sage/40 text-forest font-body text-caption rounded-md px-4 py-3 mb-4">
            Bank details saved. A Kyros admin will verify and confirm.
          </div>
        )}

        <form onSubmit={(e) => { void handleBankSave(e); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">Account holder name</label>
              <input
                type="text"
                required
                value={accountHolder}
                onChange={e => setAccountHolder(e.target.value)}
                className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
                placeholder="As on bank records"
              />
            </div>
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">Bank name</label>
              <input
                type="text"
                required
                value={bankName}
                onChange={e => setBankName(e.target.value)}
                className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
                placeholder="HDFC Bank"
              />
            </div>
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">Account number</label>
              <input
                type="text"
                required
                value={accountNumber}
                onChange={e => setAccountNumber(e.target.value)}
                className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
                placeholder="9-18 digit account number"
              />
            </div>
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">IFSC code</label>
              <input
                type="text"
                required
                pattern="^[A-Za-z]{4}0[A-Za-z0-9]{6}$"
                value={ifscCode}
                onChange={e => setIfscCode(e.target.value.toUpperCase())}
                className="w-full border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest uppercase"
                placeholder="HDFC0001234"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={bankSaving}
            className="bg-forest text-ivory font-body text-body font-semibold px-6 py-2.5 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
          >
            {bankSaving ? 'Saving…' : data.has_bank_details ? 'Update bank details' : 'Save bank details'}
          </button>
        </form>
      </div>
    </div>
  );
}
