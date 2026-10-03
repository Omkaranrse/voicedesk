'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'motion/react';
import { Activity, Calendar, Clock, Radio, ShieldCheck, Sparkles, Waves } from 'lucide-react';
import { FluidGlassButton } from '@/components/ui/fluid-glass-button';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [isCoreHovered, setIsCoreHovered] = useState(false);

  const availableSlots = [
    { day: 'MON', time: '10:00 AM', label: 'Doctor Consult', open: true },
    { day: 'TUE', time: '11:00 AM', label: 'Clinical Checkup', open: true },
    { day: 'WED', time: '2:00 PM', label: 'General Intake', open: true },
  ];

  return (
    <div
      ref={ref}
      className="relative flex min-h-screen w-full flex-col items-center justify-between overflow-hidden bg-[#06080d] px-4 py-8 text-slate-100 select-none md:px-8"
    >
      {/* 1. Cinematic Ambient Background & Bioluminescent Mesh Orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Cyan Orb */}
        <motion.div
          animate={{
            x: [0, 40, -30, 0],
            y: [0, -50, 20, 0],
            scale: [1, 1.15, 0.95, 1],
          }}
          transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -top-20 -left-20 size-[420px] rounded-full bg-cyan-500/15 blur-[120px]"
        />

        {/* Deep Violet Orb */}
        <motion.div
          animate={{
            x: [0, -60, 40, 0],
            y: [0, 40, -30, 0],
            scale: [1, 1.2, 0.9, 1],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-1/3 -right-24 size-[500px] rounded-full bg-violet-600/20 blur-[140px]"
        />

        {/* Neon Emerald / Teal Orb */}
        <motion.div
          animate={{
            x: [0, 30, -50, 0],
            y: [0, -30, 40, 0],
            scale: [0.95, 1.1, 1, 0.95],
          }}
          transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -bottom-28 left-1/3 size-[460px] rounded-full bg-emerald-500/15 blur-[130px]"
        />

        {/* Micro-dot Matrix Texture */}
        <div className="absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.08)_1px,transparent_1px)] [background-size:24px_24px] opacity-70" />

        {/* Vignette Shadow Overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_20%,#06080d_85%)]" />
      </div>

      {/* 2. Top Header Telemetry HUD */}
      <header className="relative z-20 flex w-full max-w-5xl items-center justify-between pt-2">
        {/* Left Telemetry Pill */}
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-slate-900/60 px-3.5 py-1.5 backdrop-blur-xl shadow-lg shadow-cyan-950/20">
          <span className="relative flex size-2 items-center justify-center">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-80" />
            <span className="relative inline-flex size-1.5 rounded-full bg-emerald-400" />
          </span>
          <span className="font-mono text-[10px] font-semibold tracking-wider text-slate-300 uppercase">
            System Live <span className="text-slate-500">•</span> STT & TTS Online
          </span>
        </div>

        {/* Center / Right Latency, Telemetry & Dashboard Navigation */}
        <div className="flex items-center gap-3">
          <Link
            href="/appointments"
            className="flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1.5 font-mono text-[11px] font-semibold text-cyan-300 shadow-md shadow-cyan-950/30 backdrop-blur-md transition-all hover:border-cyan-400 hover:bg-cyan-900/60 hover:text-white"
          >
            <Calendar className="size-3.5 text-cyan-400" />
            <span>Appointments</span>
          </Link>

          <div className="hidden items-center gap-3 sm:flex">
            <div className="flex items-center gap-1.5 rounded-full border border-cyan-500/20 bg-cyan-950/30 px-3 py-1 font-mono text-[10px] font-medium tracking-wider text-cyan-300 backdrop-blur-md">
              <Activity className="size-3 text-cyan-400" />
              <span>P95 TTFB &lt; 400MS</span>
            </div>

            <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-slate-900/50 px-3 py-1 font-mono text-[10px] text-slate-400 backdrop-blur-md">
              <Radio className="size-3 text-violet-400" />
              <span>24KHZ DIRECT PCM</span>
            </div>
          </div>
        </div>
      </header>

      {/* 3. Main Center Stage (Audio Gyroscope Core + Hero Text + Fluid Glass Button) */}
      <main className="relative z-20 flex flex-1 flex-col items-center justify-center py-6 text-center">
        {/* Reactive Gyroscope Audio Core */}
        <div
          className="relative mb-8 flex size-44 items-center justify-center"
          onMouseEnter={() => setIsCoreHovered(true)}
          onMouseLeave={() => setIsCoreHovered(false)}
        >
          {/* Outer Wave Pulse Ring 1 */}
          <motion.div
            animate={{
              scale: isCoreHovered ? [1, 1.45, 1] : [1, 1.25, 1],
              opacity: isCoreHovered ? [0.4, 0, 0.4] : [0.25, 0, 0.25],
            }}
            transition={{
              duration: isCoreHovered ? 1.8 : 3.2,
              repeat: Infinity,
              ease: 'easeOut',
            }}
            className="absolute inset-0 rounded-full border border-cyan-400/40"
          />

          {/* Outer Wave Pulse Ring 2 */}
          <motion.div
            animate={{
              scale: isCoreHovered ? [1, 1.7, 1] : [1, 1.4, 1],
              opacity: isCoreHovered ? [0.35, 0, 0.35] : [0.2, 0, 0.2],
            }}
            transition={{
              duration: isCoreHovered ? 2.2 : 3.8,
              repeat: Infinity,
              delay: 0.6,
              ease: 'easeOut',
            }}
            className="absolute inset-0 rounded-full border border-violet-500/30"
          />

          {/* Gyroscopic Orbital Ring A (Clockwise) */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{
              duration: isCoreHovered ? 8 : 18,
              repeat: Infinity,
              ease: 'linear',
            }}
            className="absolute size-36 rounded-full border-t-2 border-r border-cyan-400/70 border-b-transparent border-l-transparent drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]"
          />

          {/* Gyroscopic Orbital Ring B (Counter-Clockwise) */}
          <motion.div
            animate={{ rotate: -360 }}
            transition={{
              duration: isCoreHovered ? 11 : 24,
              repeat: Infinity,
              ease: 'linear',
            }}
            className="absolute size-28 rounded-full border-b-2 border-l border-violet-400/60 border-t-transparent border-r-transparent drop-shadow-[0_0_10px_rgba(168,85,247,0.5)]"
          />

          {/* Central Bioluminescent Orb Core */}
          <motion.div
            animate={{
              scale: isCoreHovered ? [1, 1.12, 1] : [1, 1.05, 1],
              boxShadow: isCoreHovered
                ? [
                    '0 0 30px rgba(0,240,255,0.7)',
                    '0 0 50px rgba(168,85,247,0.8)',
                    '0 0 30px rgba(0,240,255,0.7)',
                  ]
                : [
                    '0 0 20px rgba(0,240,255,0.4)',
                    '0 0 35px rgba(0,240,255,0.6)',
                    '0 0 20px rgba(0,240,255,0.4)',
                  ],
            }}
            transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
            className="relative flex size-20 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-500 via-indigo-500 to-violet-500 p-[2px]"
          >
            <div className="flex size-full items-center justify-center rounded-full bg-slate-950/85 backdrop-blur-md">
              <Waves className="size-8 text-cyan-300 drop-shadow-[0_0_10px_rgba(0,240,255,0.9)] transition-transform duration-300" />
            </div>
          </motion.div>
        </div>

        {/* Hero Title & Subtitle */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8 max-w-xl space-y-3"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-[11px] font-medium tracking-widest text-cyan-300 uppercase backdrop-blur-md">
            <Sparkles className="size-3 text-cyan-400" />
            VoiceDesk Clinical Intelligence
          </div>

          <h1 className="bg-gradient-to-b from-white via-slate-100 to-slate-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent sm:text-5xl">
            Autonomous Voice Receptionist
          </h1>

          <p className="mx-auto max-w-md text-sm leading-relaxed text-slate-400 sm:text-base font-light">
            Real-time appointment triage and schedule dispatch powered by LiveKit WebRTC, faster-whisper, and Kokoro speech synthesis.
          </p>
        </motion.div>

        {/* 4. Fluid Glass Hero Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          onMouseEnter={() => setIsCoreHovered(true)}
          onMouseLeave={() => setIsCoreHovered(false)}
          className="mb-10"
        >
          <FluidGlassButton
            onClick={onStartCall}
            text={startButtonText || 'INITIALIZE VOICE LINK'}
          />
        </motion.div>

        {/* 5. Live Schedule Radar Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="w-full max-w-2xl"
        >
          <div className="mb-3 flex items-center justify-between px-2 text-left">
            <span className="flex items-center gap-1.5 font-mono text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
              <Calendar className="size-3.5 text-cyan-400" />
              Verified Schedule Radar
            </span>
            <span className="flex items-center gap-1 font-mono text-[10px] text-emerald-400">
              <ShieldCheck className="size-3" />
              Anti-Hallucination Guardrails
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {availableSlots.map((slot, idx) => (
              <div
                key={idx}
                className="group relative overflow-hidden rounded-xl border border-white/10 bg-slate-900/40 p-3.5 text-left backdrop-blur-xl transition-all duration-300 hover:border-cyan-500/40 hover:bg-slate-900/70 hover:shadow-[0_0_20px_rgba(0,240,255,0.15)]"
              >
                {/* Specular Sheen on Hover */}
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

                <div className="relative z-10 flex items-center justify-between">
                  <span className="font-mono text-xs font-bold tracking-wider text-cyan-400">
                    {slot.day}
                  </span>
                  <span className="flex items-center gap-1 font-mono text-[10px] text-slate-400">
                    <Clock className="size-2.5 text-slate-500" />
                    {slot.time}
                  </span>
                </div>

                <div className="relative z-10 mt-1.5 text-xs font-medium text-slate-200">
                  {slot.label}
                </div>

                <div className="relative z-10 mt-2 flex items-center gap-1.5 text-[10px] font-mono text-emerald-400">
                  <span className="size-1.5 rounded-full bg-emerald-400" />
                  Available Now
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </main>

      {/* 6. Bottom Status Footer */}
      <footer className="relative z-20 flex w-full max-w-5xl items-center justify-between border-t border-white/10 pt-4 text-[11px] text-slate-400 font-mono">
        <div className="flex items-center gap-2">
          <span className="size-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(0,240,255,0.8)]" />
          <span>VOICEDESK v1.0 • OLLAMA LLAMA3.2:3B</span>
        </div>

        <div className="flex items-center gap-4">
          <span className="hidden sm:inline text-slate-400">
            Natural Speech Endpointing (550ms)
          </span>
          <span className="rounded bg-white/5 px-2 py-0.5 text-[10px] text-cyan-300 border border-white/10">
            SILERO VAD
          </span>
        </div>
      </footer>
    </div>
  );
};
