import { useState } from 'react';
import { Lock, Unlock, CheckCircle, MoveHorizontal, MoveVertical, Hand, ArrowLeft, ChevronUp, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface CalibrationScreenProps {
  onCalibrationComplete: () => void;
  onBack: () => void;
}

export function CalibrationScreen({ onCalibrationComplete, onBack }: CalibrationScreenProps) {
  const [pin, setPin] = useState(['', '', '', '']);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [calibrationStep, setCalibrationStep] = useState<'a1' | 'h8'>('a1');
  const [a1Calibrated, setA1Calibrated] = useState(false);
  const [h8Calibrated, setH8Calibrated] = useState(false);
  const [error, setError] = useState('');

  const CORRECT_PIN = '0000';

  const handlePinChange = (index: number, value: string) => {
    if (value.length > 1) return;
    if (value && !/^\d$/.test(value)) return;

    const newPin = [...pin];
    newPin[index] = value;
    setPin(newPin);
    setError('');

    // Auto-focus next input
    if (value && index < 3) {
      const nextInput = document.getElementById(`pin-${index + 1}`);
      nextInput?.focus();
    }

    // Check PIN when all 4 digits are entered
    if (newPin.every(digit => digit !== '')) {
      const enteredPin = newPin.join('');
      if (enteredPin === CORRECT_PIN) {
        setTimeout(() => {
          setIsUnlocked(true);
        }, 300);
      } else {
        setError('Code incorrect');
        setTimeout(() => {
          setPin(['', '', '', '']);
          document.getElementById('pin-0')?.focus();
        }, 1000);
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !pin[index] && index > 0) {
      const prevInput = document.getElementById(`pin-${index - 1}`);
      prevInput?.focus();
    }
  };

  const handleValidateA1 = () => {
    setA1Calibrated(true);
    setCalibrationStep('h8');
  };

  const handleValidateH8 = () => {
    setH8Calibrated(true);
    // Petite pause pour l'effet visuel puis transition directe
    setTimeout(() => {
      onCalibrationComplete();
    }, 500);
  };

  const handleMoveUp = () => {
    // TODO: API call to move robot up in Z axis
    console.log('Moving robot UP (Z+)');
  };

  const handleMoveDown = () => {
    // TODO: API call to move robot down in Z axis
    console.log('Moving robot DOWN (Z-)');
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-10"
      >
        <div className="w-10 h-10 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all">
          <ArrowLeft className="w-5 h-5" />
        </div>
        <span className="font-medium">Retour</span>
      </button>

      {/* Main Calibration Content (always rendered, blurred when locked) */}
      <div className={`max-w-4xl w-full transition-all duration-500 ${!isUnlocked ? 'blur-sm pointer-events-none select-none' : ''}`}>
        {/* Calibration Screen */}
        <div>
          <div className="mb-8 text-center">
            <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-xl shadow-green-500/20">
              <Unlock className="w-10 h-10 text-white" strokeWidth={2} />
            </div>
            <h1 className="text-4xl font-bold text-white mb-3">
              Calibration Robot UR7e
            </h1>
            <p className="text-slate-400 text-lg mb-4">
              Mode <span className="text-green-400 font-semibold">Free Drive</span> activé
            </p>
            <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-400 text-sm font-medium">
                Vous pouvez déplacer le robot manuellement
              </span>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Left - Instructions */}
            <div className="space-y-6">
              {/* Step A1 */}
              <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border-2 transition-all
                ${calibrationStep === 'a1' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : a1Calibrated ? 'border-green-500 opacity-75' : 'border-slate-700 opacity-50'}`}>
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0
                    ${a1Calibrated ? 'bg-green-500' : 'bg-cyan-500'}`}>
                    {a1Calibrated ? (
                      <CheckCircle className="w-6 h-6 text-white" strokeWidth={2.5} />
                    ) : (
                      <span className="text-white font-bold text-xl">1</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-lg mb-2">
                      Position A1 (Coin inférieur gauche)
                    </h3>
                    <p className="text-slate-400 text-sm mb-4">
                      Déplacez manuellement le préhenseur du robot (X, Y) au-dessus de la case A1. Utilisez les boutons pour ajuster la hauteur (Z).
                    </p>
                    
                    {calibrationStep === 'a1' && !a1Calibrated && (
                      <button
                        onClick={handleValidateA1}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-6 py-3 rounded-lg font-semibold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-5 h-5" />
                        Valider position A1
                      </button>
                    )}
                    
                    {a1Calibrated && (
                      <div className="flex items-center gap-2 text-green-400 text-sm">
                        <CheckCircle className="w-4 h-4" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Step H8 */}
              <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border-2 transition-all
                ${calibrationStep === 'h8' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : h8Calibrated ? 'border-green-500 opacity-75' : 'border-slate-700 opacity-50'}`}>
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0
                    ${h8Calibrated ? 'bg-green-500' : 'bg-cyan-500'}`}>
                    {h8Calibrated ? (
                      <CheckCircle className="w-6 h-6 text-white" strokeWidth={2.5} />
                    ) : (
                      <span className="text-white font-bold text-xl">2</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-lg mb-2">
                      Position H8 (Coin supérieur droit)
                    </h3>
                    <p className="text-slate-400 text-sm mb-4">
                      Déplacez manuellement le préhenseur du robot (X, Y) au-dessus de la case H8. Utilisez les boutons pour ajuster la hauteur (Z).
                    </p>
                    
                    {calibrationStep === 'h8' && !h8Calibrated && (
                      <button
                        onClick={handleValidateH8}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-6 py-3 rounded-lg font-semibold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-5 h-5" />
                        Valider position H8
                      </button>
                    )}
                    
                    {h8Calibrated && (
                      <div className="flex items-center gap-2 text-green-400 text-sm">
                        <CheckCircle className="w-4 h-4" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Right - Video Guide & Z Controls */}
            <div className="space-y-6">
              {/* Video Placeholder */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
                <div className="relative aspect-video bg-slate-900/80 flex items-center justify-center">
                  {/* Placeholder for video */}
                  <div className="text-center p-8">
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-700/50 flex items-center justify-center">
                      <svg className="w-10 h-10 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                      </svg>
                    </div>
                    <p className="text-slate-400 text-lg font-medium">
                      Vidéo explicative de calibration
                    </p>
                    <p className="text-slate-500 text-sm mt-2">
                      Instructions pour positionner le robot
                    </p>
                  </div>
                </div>
              </div>

              {/* Z-Axis Controls */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <MoveVertical className="w-5 h-5 text-cyan-400" />
                  Contrôle Hauteur (Z)
                </h3>

                <div className="space-y-3">
                  {/* Move Up Button */}
                  <button
                    onClick={handleMoveUp}
                    className="w-full bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400
                      text-white px-6 py-4 rounded-lg font-medium transition-all
                      flex items-center justify-center gap-3 group"
                  >
                    <div className="w-10 h-10 bg-cyan-500/20 group-hover:bg-cyan-500/30 rounded-lg flex items-center justify-center transition-all">
                      <ChevronUp className="w-6 h-6 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Monter le robot</span>
                  </button>

                  {/* Move Down Button */}
                  <button
                    onClick={handleMoveDown}
                    className="w-full bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400
                      text-white px-6 py-4 rounded-lg font-medium transition-all
                      flex items-center justify-center gap-3 group"
                  >
                    <div className="w-10 h-10 bg-cyan-500/20 group-hover:bg-cyan-500/30 rounded-lg flex items-center justify-center transition-all">
                      <ChevronDown className="w-6 h-6 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Descendre le robot</span>
                  </button>
                </div>

                {/* Instructions */}
                <div className="mt-4 space-y-2">
                  <div className="flex items-start gap-2 text-sm">
                    <div className="w-5 h-5 bg-cyan-500/20 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                      <MoveHorizontal className="w-3 h-3 text-cyan-400" />
                    </div>
                    <p className="text-slate-400">
                      <span className="text-white font-medium">X et Y :</span> Déplacez manuellement le robot en mode Free Drive
                    </p>
                  </div>
                  <div className="flex items-start gap-2 text-sm">
                    <div className="w-5 h-5 bg-cyan-500/20 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                      <MoveVertical className="w-3 h-3 text-cyan-400" />
                    </div>
                    <p className="text-slate-400">
                      <span className="text-white font-medium">Z :</span> Utilisez les boutons ci-dessus pour la hauteur
                    </p>
                  </div>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mt-4">
                  <p className="text-amber-400 text-xs font-medium">
                    ⚠️ Assurez-vous que le préhenseur est bien centré au-dessus de la case avant de valider
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* PIN Overlay - appears above the blurred content */}
      <AnimatePresence>
        {!isUnlocked && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 flex items-center justify-center z-20 bg-slate-900/80 backdrop-blur-md"
          >
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="text-center"
            >
              <div className="mb-8">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-cyan-500 blur-3xl opacity-40 animate-pulse"></div>
                  <div className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-2xl shadow-cyan-500/50 relative">
                    <Lock className="w-10 h-10 text-white" strokeWidth={2} />
                  </div>
                </div>
                <h1 className="text-4xl font-bold text-white mb-3">
                  Mode Superviseur
                </h1>
                <p className="text-slate-400 text-lg">
                  Entrez le code PIN pour accéder à la calibration du robot
                </p>
              </div>

              {/* PIN Input */}
              <div className="flex justify-center gap-4 mb-6">
                {pin.map((digit, index) => (
                  <motion.input
                    key={index}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.2 + index * 0.1 }}
                    id={`pin-${index}`}
                    type="password"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handlePinChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    autoFocus={index === 0}
                    className={`w-16 h-20 text-center text-3xl font-bold rounded-xl border-2 bg-slate-800/70 text-white
                      transition-all duration-200 outline-none backdrop-blur-sm
                      ${error ? 'border-red-500 animate-shake' : 'border-slate-600 focus:border-cyan-400 focus:shadow-lg focus:shadow-cyan-500/30'}
                      ${digit ? 'border-cyan-500 bg-slate-700/70' : ''}`}
                  />
                ))}
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-red-400 mb-4 font-semibold"
                >
                  {error}
                </motion.p>
              )}

              <div className="bg-slate-800/60 backdrop-blur-sm rounded-xl px-6 py-3 inline-block border border-slate-700">
                <p className="text-slate-400 text-sm">
                  Code par défaut : <span className="text-cyan-400 font-mono font-semibold">0000</span>
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
