import { type ReactNode } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Calendar, CalendarDays, LogOut, Stethoscope, User, Users } from 'lucide-react';
import { logout } from '../lib/auth';

const NAV = [
  { to: '/dashboard', label: 'Dashboard',    Icon: CalendarDays },
  { to: '/patients',  label: 'Patients',     Icon: Users },
  { to: '/consultations/today', label: 'Consultations', Icon: Stethoscope },
  { to: '/schedule',  label: 'Schedule',     Icon: Calendar },
  { to: '/profile',   label: 'Profile',      Icon: User },
];

export function Layout({ children, doctorName }: { children: ReactNode; doctorName?: string }) {
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="flex min-h-screen bg-ivory">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-forest text-ivory flex flex-col">
        <Link to="/dashboard" className="px-6 py-6 border-b border-white/10">
          <p className="font-display text-h3 font-medium text-ivory">Kyros</p>
          <p className="font-body text-caption text-ivory/60 mt-0.5">Doctor Portal</p>
        </Link>

        <nav className="flex-1 py-4">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }: { isActive: boolean }) =>
                `flex items-center gap-3 px-6 py-3 font-body text-body transition-colors ${
                  isActive
                    ? 'bg-white/10 text-ivory'
                    : 'text-ivory/70 hover:bg-white/5 hover:text-ivory'
                }`
              }
            >
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-6 py-5 border-t border-white/10">
          {doctorName && (
            <p className="font-body text-caption text-ivory/60 mb-3 truncate">{doctorName}</p>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 font-body text-caption text-ivory/70 hover:text-ivory transition-colors"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
