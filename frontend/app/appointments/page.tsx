'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Calendar,
  Clock,
  User,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  ArrowLeft,
  PhoneCall,
  Sparkles,
} from 'lucide-react';

interface Slot {
  id: string;
  day: string;
  time: string;
  bookedBy: string | null;
  pin: string | null;
  status: 'available' | 'booked';
  updatedAt: string;
}

export default function AppointmentsPage() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'booked' | 'available'>('all');
  const [selectedDay, setSelectedDay] = useState<string>('all');

  const fetchSlots = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/appointments');
      const data = await res.json();
      if (data.slots) {
        setSlots(data.slots);
      }
    } catch (err) {
      console.error('Failed to load slots', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSlots();
    const interval = setInterval(fetchSlots, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredSlots = slots.filter((slot) => {
    const matchesFilter =
      filter === 'all' ? true : filter === 'booked' ? slot.status === 'booked' : slot.status === 'available';
    const matchesDay = selectedDay === 'all' || slot.day.toLowerCase() === selectedDay.toLowerCase();
    const matchesSearch =
      !search ||
      slot.day.toLowerCase().includes(search.toLowerCase()) ||
      slot.time.toLowerCase().includes(search.toLowerCase()) ||
      (slot.bookedBy && slot.bookedBy.toLowerCase().includes(search.toLowerCase())) ||
      (slot.pin && slot.pin.includes(search));

    return matchesFilter && matchesDay && matchesSearch;
  });

  const bookedCount = slots.filter((s) => s.status === 'booked').length;
  const availableCount = slots.filter((s) => s.status === 'available').length;

  return (
    <div className="relative min-h-screen w-full bg-[#06080d] px-4 py-8 text-slate-100 md:px-12">
      {/* Background Ambient Glows */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-20 -left-20 size-[400px] rounded-full bg-cyan-500/10 blur-[130px]" />
        <div className="absolute top-1/2 -right-20 size-[450px] rounded-full bg-violet-600/10 blur-[140px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl">
        {/* Top Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <Link
                href="/"
                className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition-all hover:border-cyan-500/40 hover:bg-white/10 hover:text-white"
              >
                <ArrowLeft className="size-3.5" />
                Back to Voice Receptionist
              </Link>
              <span className="flex items-center gap-1.5 rounded-full border border-cyan-500/20 bg-cyan-950/30 px-3 py-1 text-xs font-medium text-cyan-300">
                <Sparkles className="size-3 text-cyan-400" />
                Live Sync Active
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Appointments & Schedule Manager
            </h1>
            <p className="text-sm text-slate-400">
              Live appointment book updated automatically by the VoiceDesk AI Receptionist
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchSlots}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-slate-200 transition-colors hover:bg-white/10 disabled:opacity-50"
            >
              <RefreshCw className={`size-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
              Refresh
            </button>
            <Link
              href="/"
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 transition-all hover:brightness-110"
            >
              <PhoneCall className="size-3.5" />
              Make Voice Call
            </Link>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Total Available Slots</span>
              <Calendar className="size-4 text-cyan-400" />
            </div>
            <div className="mt-2 text-3xl font-bold text-white">{availableCount}</div>
            <p className="mt-1 text-xs text-emerald-400">Ready for booking</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Booked Appointments</span>
              <CheckCircle2 className="size-4 text-violet-400" />
            </div>
            <div className="mt-2 text-3xl font-bold text-white">{bookedCount}</div>
            <p className="mt-1 text-xs text-violet-400">Confirmed with PIN</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Schedule Occupancy</span>
              <Clock className="size-4 text-blue-400" />
            </div>
            <div className="mt-2 text-3xl font-bold text-white">
              {slots.length ? Math.round((bookedCount / slots.length) * 100) : 0}%
            </div>
            <p className="mt-1 text-xs text-slate-400">{slots.length} total scheduled slots</p>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.02] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {(['all', 'booked', 'available'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-all ${
                  filter === tab
                    ? 'border border-cyan-500/30 bg-cyan-500/20 text-cyan-300'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }`}
              >
                {tab === 'all' ? 'All Slots' : tab}
              </button>
            ))}

            <div className="mx-2 hidden h-4 w-px bg-white/10 sm:block" />

            {(['all', 'Monday', 'Tuesday', 'Wednesday'] as const).map((day) => (
              <button
                key={day}
                onClick={() => setSelectedDay(day)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  selectedDay === day
                    ? 'border border-white/20 bg-white/10 text-white'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                {day === 'all' ? 'All Days' : day}
              </button>
            ))}
          </div>

          <div className="relative">
            <Search className="absolute top-2.5 left-3 size-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search patient, day, or PIN..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/40 py-1.5 pr-4 pl-9 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none sm:w-64"
            />
          </div>
        </div>

        {/* Appointment Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredSlots.map((slot) => (
            <div
              key={slot.id}
              className={`relative overflow-hidden rounded-2xl border p-5 transition-all ${
                slot.status === 'booked'
                  ? 'border-violet-500/30 bg-gradient-to-b from-violet-950/20 to-black/30 shadow-lg shadow-violet-950/20'
                  : 'border-white/10 bg-gradient-to-b from-white/[0.03] to-black/30'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1 font-mono text-[11px] font-semibold text-cyan-300 uppercase">
                    {slot.day.slice(0, 3)}
                  </span>
                  <span className="flex items-center gap-1 text-sm font-semibold text-white">
                    <Clock className="size-3.5 text-slate-400" />
                    {slot.time}
                  </span>
                </div>

                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                    slot.status === 'booked'
                      ? 'border border-violet-500/30 bg-violet-500/20 text-violet-300'
                      : 'border border-emerald-500/30 bg-emerald-500/20 text-emerald-300'
                  }`}
                >
                  {slot.status === 'booked' ? (
                    <>
                      <CheckCircle2 className="size-3" />
                      Booked
                    </>
                  ) : (
                    <>
                      <AlertCircle className="size-3" />
                      Available
                    </>
                  )}
                </span>
              </div>

              <div className="mt-4 border-t border-white/5 pt-4">
                {slot.status === 'booked' ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        <User className="size-3.5 text-violet-400" />
                        Patient:
                      </span>
                      <span className="font-semibold text-white">{slot.bookedBy}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        <KeyRound className="size-3.5 text-cyan-400" />
                        Security PIN:
                      </span>
                      <span className="rounded border border-cyan-500/20 bg-cyan-950/40 px-2 py-0.5 font-mono text-xs text-cyan-300">
                        {slot.pin || '••••'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="py-2 text-center text-xs text-slate-500">
                    No booking yet. Patient can book via voice call.
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {filteredSlots.length === 0 && (
          <div className="mt-12 rounded-2xl border border-white/5 bg-white/[0.01] p-12 text-center text-slate-500">
            No matching appointment slots found.
          </div>
        )}
      </div>
    </div>
  );
}
