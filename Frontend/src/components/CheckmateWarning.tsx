import { AlertTriangle, Zap, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface CheckmateWarningProps {
  isVisible: boolean;
  type: 'danger' | 'opportunity'; // danger = user va perdre, opportunity = user va gagner
  onClose: () => void;
}

export function CheckmateWarning({ isVisible, type, onClose }: CheckmateWarningProps) {
  const config = {
    danger: {
      title: 'Mat imminent !',
      subtitle: 'Le robot a un mat forcé',
      icon: AlertTriangle,
      iconColor: 'text-red-400',
      bgGradient: 'from-red-500/20 via-red-600/20 to-orange-500/20',
      borderColor: 'border-red-500/60',
      glowColor: 'shadow-red-500/50',
      pulseColor: 'bg-red-500',
      textColor: 'text-red-300'
    },
    opportunity: {
      title: 'Mat possible !',
      subtitle: 'Vous avez un mat forcé',
      icon: Zap,
      iconColor: 'text-yellow-400',
      bgGradient: 'from-yellow-500/20 via-amber-500/20 to-orange-500/20',
      borderColor: 'border-yellow-500/60',
      glowColor: 'shadow-yellow-500/50',
      pulseColor: 'bg-yellow-500',
      textColor: 'text-yellow-300'
    }
  };

  const currentConfig = config[type];
  const Icon = currentConfig.icon;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.9 }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
          className="fixed top-24 left-1/2 -translate-x-1/2 z-40 pointer-events-none"
        >
          <div
            className={`
              relative bg-gradient-to-r ${currentConfig.bgGradient}
              backdrop-blur-xl rounded-2xl border-2 ${currentConfig.borderColor}
              shadow-2xl ${currentConfig.glowColor} px-6 py-4
              pointer-events-auto
            `}
          >
            {/* Pulse animation border */}
            <motion.div
              className={`absolute inset-0 rounded-2xl ${currentConfig.pulseColor} opacity-20`}
              animate={{
                scale: [1, 1.05, 1],
                opacity: [0.2, 0.4, 0.2]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut'
              }}
            />

            <div className="relative flex items-center gap-4">
              {/* Icon with animation */}
              <motion.div
                animate={{
                  rotate: type === 'danger' ? [0, -10, 10, -10, 10, 0] : 0,
                  scale: type === 'opportunity' ? [1, 1.2, 1] : 1
                }}
                transition={{
                  duration: type === 'danger' ? 0.5 : 1,
                  repeat: Infinity,
                  repeatDelay: type === 'danger' ? 1 : 0.5
                }}
              >
                <Icon className={`w-8 h-8 ${currentConfig.iconColor}`} strokeWidth={2} />
              </motion.div>

              {/* Text content */}
              <div className="flex-1">
                <h3 className={`font-bold text-lg ${currentConfig.textColor}`}>
                  {currentConfig.title}
                </h3>
                <p className="text-sm text-slate-300">
                  {currentConfig.subtitle}
                </p>
              </div>

              {/* Close button */}
              <button
                onClick={onClose}
                className="ml-2 p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5 text-slate-400 hover:text-white" />
              </button>
            </div>

            {/* Progress bar at bottom */}
            <motion.div
              className={`absolute bottom-0 left-0 h-1 ${currentConfig.pulseColor} rounded-b-2xl`}
              initial={{ width: '100%' }}
              animate={{ width: '0%' }}
              transition={{ duration: 8, ease: 'linear' }}
              onAnimationComplete={onClose}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
