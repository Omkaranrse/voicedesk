'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, ExternalLink, X, ArrowUpRight } from 'lucide-react';

export function PortfolioBadge() {
  const [showSpeechBubble, setShowSpeechBubble] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="fixed right-5 bottom-5 z-50 flex flex-col items-end select-none">
      {/* 1. Attractive Speech Bubble Popup */}
      <AnimatePresence>
        {showSpeechBubble && (
          <motion.div
            initial={{ opacity: 0, y: 15, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.9 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300, delay: 0.4 }}
            className="relative mb-3 max-w-[280px] rounded-2xl border border-cyan-500/40 bg-[#0b101b]/95 p-3.5 text-left text-white shadow-2xl shadow-cyan-950/50 backdrop-blur-xl sm:max-w-[320px]"
          >
            {/* Close / Dismiss Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSpeechBubble(false);
              }}
              aria-label="Dismiss message"
              className="absolute top-2 right-2 rounded-full p-1 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="size-3.5" />
            </button>

            {/* Bubble Content */}
            <div className="pr-4">
              <div className="mb-1 flex items-center gap-1.5">
                <span className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
                </span>
                <span className="font-mono text-[10px] font-bold tracking-wider text-cyan-400 uppercase">
                  Creator Spotlight
                </span>
              </div>

              <p className="text-xs font-semibold text-white">
                Hey, I&apos;m <span className="text-cyan-300">Omkar Anarse</span> 👋
              </p>
              <p className="mt-0.5 text-[11px] font-medium text-slate-300">
                AI Full Stack Engineer
              </p>

              <a
                href="https://omkar-anarse.vercel.app"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-md shadow-cyan-500/20 transition-all hover:brightness-110 active:scale-95"
              >
                <span>Click me to see my portfolio</span>
                <ArrowUpRight className="size-3" />
              </a>
            </div>

            {/* Speech Bubble Pointer Arrow */}
            <div className="absolute -bottom-2 right-6 size-3.5 rotate-45 border-r border-b border-cyan-500/40 bg-[#0b101b]" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* 2. Magnetic Interactive Avatar Button */}
      <motion.a
        href="https://omkar-anarse.vercel.app"
        target="_blank"
        rel="noopener noreferrer"
        onMouseEnter={() => {
          setIsHovered(true);
          setShowSpeechBubble(true);
        }}
        onMouseLeave={() => setIsHovered(false)}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.94 }}
        className="group relative flex items-center gap-3 rounded-full border border-cyan-500/40 bg-[#080d1a]/90 p-1.5 pr-4 shadow-[0_0_25px_rgba(6,182,212,0.25)] backdrop-blur-2xl transition-all duration-300 hover:border-cyan-400 hover:shadow-[0_0_35px_rgba(6,182,212,0.45)]"
      >
        {/* Pulsing Aura Rings */}
        <span className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-violet-500/20 blur-md transition-all group-hover:blur-lg" />

        {/* Avatar Container with Glowing Ring */}
        <div className="relative size-12 shrink-0 overflow-hidden rounded-full border-2 border-cyan-400/80 bg-slate-900 shadow-inner">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/omkar-avatar.png"
            alt="Omkar Anarse"
            className="size-full object-cover object-top transition-transform duration-300 group-hover:scale-110"
          />
          {/* Online Indicator Badge */}
          <span className="absolute right-0.5 bottom-0.5 size-2.5 rounded-full border border-black bg-emerald-400" />
        </div>

        {/* Text Badge */}
        <div className="flex flex-col text-left">
          <span className="flex items-center gap-1 font-mono text-[10px] font-bold tracking-wider text-cyan-400 uppercase">
            <Sparkles className="size-2.5 text-cyan-300 animate-pulse" />
            Produced by
          </span>
          <span className="flex items-center gap-1 text-xs font-bold text-white transition-colors group-hover:text-cyan-200">
            Omkar Anarse
            <ExternalLink className="size-3 opacity-60 transition-opacity group-hover:opacity-100" />
          </span>
        </div>
      </motion.a>
    </div>
  );
}
