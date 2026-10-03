'use client';

import React, { useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'motion/react';
import { Mic, Sparkles } from 'lucide-react';

interface FluidGlassButtonProps {
  onClick: () => void;
  text?: string;
  className?: string;
  disabled?: boolean;
}

export function FluidGlassButton({
  onClick,
  text = 'INITIALIZE VOICE LINK',
  className = '',
  disabled = false,
}: FluidGlassButtonProps) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Mouse tracking coordinates for 3D liquid tilt and iridescent refraction
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const smoothX = useSpring(mouseX, { stiffness: 180, damping: 18 });
  const smoothY = useSpring(mouseY, { stiffness: 180, damping: 18 });

  // 3D Parallax tilt angles
  const rotateX = useTransform(smoothY, [-0.5, 0.5], [10, -10]);
  const rotateY = useTransform(smoothX, [-0.5, 0.5], [-10, 10]);

  // Dynamic specular light translation
  const sheenX = useTransform(smoothX, [-0.5, 0.5], [-80, 80]);
  const sheenY = useTransform(smoothY, [-0.5, 0.5], [-80, 80]);

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!buttonRef.current || disabled) return;
    const rect = buttonRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    mouseX.set(x);
    mouseY.set(y);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
    setIsHovered(false);
  };

  return (
    <div className="relative inline-flex items-center justify-center p-[2px]">
      {/* Outer ambient breathing aura */}
      <motion.div
        animate={{
          scale: isHovered ? [1.02, 1.08, 1.02] : [1, 1.04, 1],
          opacity: isHovered ? [0.6, 0.9, 0.6] : [0.35, 0.55, 0.35],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="pointer-events-none absolute -inset-2 rounded-full bg-gradient-to-r from-cyan-500/40 via-violet-600/30 to-fuchsia-500/30 blur-xl"
      />

      <motion.button
        ref={buttonRef}
        onClick={onClick}
        disabled={disabled}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX,
          rotateY,
          transformStyle: 'preserve-3d',
        }}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.96 }}
        className={`group relative flex items-center justify-center gap-3 overflow-hidden rounded-full border border-white/20 bg-slate-950/60 px-9 py-4 font-mono text-xs font-bold tracking-widest text-cyan-200 uppercase shadow-2xl backdrop-blur-2xl transition-shadow duration-300 hover:border-cyan-400/50 hover:shadow-[0_0_35px_rgba(0,240,255,0.4)] disabled:opacity-50 disabled:pointer-events-none ${className}`}
      >
        {/* Specular fluid glass gradient border */}
        <span className="pointer-events-none absolute inset-0 rounded-full border border-white/25 bg-gradient-to-b from-white/30 via-white/5 to-cyan-500/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)]" />

        {/* Dynamic liquid iridescent sheen following cursor coordinates */}
        <motion.span
          className="pointer-events-none absolute -inset-10 rounded-full opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-75"
          style={{
            background:
              'radial-gradient(circle 140px at center, rgba(0, 240, 255, 0.75), rgba(168, 85, 247, 0.5), transparent)',
            x: sheenX,
            y: sheenY,
          }}
        />

        {/* Ambient interior glass backdrop */}
        <span className="pointer-events-none absolute inset-[1px] rounded-full bg-gradient-to-b from-slate-900/80 to-slate-950/90 backdrop-blur-3xl" />

        {/* Scanning specular light ray */}
        <motion.span
          animate={{
            x: ['-100%', '200%'],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: 'easeInOut',
            repeatDelay: 2,
          }}
          className="pointer-events-none absolute inset-0 w-1/3 -skew-x-12 bg-gradient-to-r from-transparent via-white/15 to-transparent opacity-0 group-hover:opacity-100"
        />

        {/* Interactive button content */}
        <span className="relative z-10 flex items-center gap-3 drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]">
          <span className="relative flex size-2.5 items-center justify-center">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex size-1.5 rounded-full bg-cyan-300" />
          </span>

          <Mic className="size-4 text-cyan-300 transition-transform duration-300 group-hover:scale-110 group-hover:text-cyan-100" />
          
          <span className="font-semibold tracking-[0.2em] text-white/95">
            {text}
          </span>

          <Sparkles className="size-3.5 text-cyan-400/80 transition-all duration-300 group-hover:rotate-12 group-hover:text-cyan-200" />
        </span>
      </motion.button>
    </div>
  );
}
