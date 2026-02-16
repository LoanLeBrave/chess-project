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
  const [calibrationStep, setCalibrationStep] = useState<'a1' | 'h8' | 'z'>('a1');
  const [a1Calibrated, setA1Calibrated] = useState(false);
  const [h8Calibrated, setH8Calibrated] = useState(false);
  const [zCalibrated, setZCalibrated] = useState(false);
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
    setCalibrationStep('z');
  };

  const handleValidateZ = () => {
    setZCalibrated(true);
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
    <div className="h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-4 left-4 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-10"
      >
        <div className="w-9 h-9 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all">
          <ArrowLeft className="w-4 h-4" />
        </div>
        <span className="font-medium text-sm">Retour</span>
      </button>

      {/* Main Calibration Content (always rendered, blurred when locked) */}
      <div className={`max-w-6xl w-full transition-all duration-500 ${!isUnlocked ? 'blur-sm pointer-events-none select-none' : ''}`}>
        {/* Calibration Screen */}
        <div>
          <div className="mb-4 text-center">
            <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl mx-auto mb-3 flex items-center justify-center shadow-xl shadow-green-500/20">
              <Unlock className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">
              Calibration Robot UR7e
            </h1>
            <p className="text-slate-400 text-sm mb-2">
              Mode <span className="text-green-400 font-semibold">Free Drive</span> activé
            </p>
            <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-1.5">
              <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-400 text-xs font-medium">
                Vous pouvez déplacer le robot manuellement
              </span>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Left - Instructions */}
            <div className="space-y-3">
              {/* Step A1 */}
              <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border-2 transition-all
                ${calibrationStep === 'a1' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : a1Calibrated ? 'border-green-500 opacity-75' : 'border-slate-700 opacity-50'}`}>
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0
                    ${a1Calibrated ? 'bg-green-500' : 'bg-cyan-500'}`}>
                    {a1Calibrated ? (
                      <CheckCircle className="w-5 h-5 text-white" strokeWidth={2.5} />
                    ) : (
                      <span className="text-white font-bold text-lg">1</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-base mb-1">
                      Position A1 (Coin bas à gauche)
                    </h3>
                    <p className="text-slate-400 text-xs mb-3">
                      Déplacez manuellement le préhenseur du robot (X, Y) au-dessus de la case A1.
                    </p>
                    
                    {calibrationStep === 'a1' && !a1Calibrated && (
                      <button
                        onClick={handleValidateA1}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Valider position A1
                      </button>
                    )}
                    
                    {a1Calibrated && (
                      <div className="flex items-center gap-2 text-green-400 text-xs">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Step H8 */}
              <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border-2 transition-all
                ${calibrationStep === 'h8' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : h8Calibrated ? 'border-green-500 opacity-75' : 'border-slate-700 opacity-50'}`}>
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0
                    ${h8Calibrated ? 'bg-green-500' : 'bg-cyan-500'}`}>
                    {h8Calibrated ? (
                      <CheckCircle className="w-5 h-5 text-white" strokeWidth={2.5} />
                    ) : (
                      <span className="text-white font-bold text-lg">2</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-base mb-1">
                      Position H8 (Coin haut à droite)
                    </h3>
                    <p className="text-slate-400 text-xs mb-3">
                      Déplacez manuellement le préhenseur du robot (X, Y) au-dessus de la case H8.
                    </p>
                    
                    {calibrationStep === 'h8' && !h8Calibrated && (
                      <button
                        onClick={handleValidateH8}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Valider position H8
                      </button>
                    )}
                    
                    {h8Calibrated && (
                      <div className="flex items-center gap-2 text-green-400 text-xs">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Step Z */}
              <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border-2 transition-all
                ${calibrationStep === 'z' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : zCalibrated ? 'border-green-500 opacity-75' : 'border-slate-700 opacity-50'}`}>
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0
                    ${zCalibrated ? 'bg-green-500' : 'bg-cyan-500'}`}>
                    {zCalibrated ? (
                      <CheckCircle className="w-5 h-5 text-white" strokeWidth={2.5} />
                    ) : (
                      <span className="text-white font-bold text-lg">3</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-base mb-1">
                      Hauteur Z (Contact avec le plateau)
                    </h3>
                    <p className="text-slate-400 text-xs mb-3">
                      Utilisez les boutons à droite pour descendre le bout de la pince jusqu'à ce qu'elle touche le plateau de l'échiquier.
                    </p>
                    
                    {calibrationStep === 'z' && !zCalibrated && (
                      <button
                        onClick={handleValidateZ}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Valider hauteur Z
                      </button>
                    )}
                    
                    {zCalibrated && (
                      <div className="flex items-center gap-2 text-green-400 text-xs">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Right - Video Guide & Z Controls */}
            <div className="space-y-3">
              {/* Video Placeholder */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
                <div className="relative h-48 bg-slate-900/80 flex items-center justify-center">
                  {/* Placeholder for video */}
                  <div className="text-center p-4">
                    <div className="w-14 h-14 mx-auto mb-2 rounded-full bg-slate-700/50 flex items-center justify-center">
                      <svg className="w-7 h-7 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                      </svg>
                    </div>
                    <p className="text-slate-400 text-sm font-medium">
                      Vidéo explicative de calibration
                    </p>
                    <p className="text-slate-500 text-xs mt-1">
                      Instructions pour positionner le robot
                    </p>
                  </div>
                </div>
              </div>

              {/* Z-Axis Controls */}
              <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700 transition-all
                ${calibrationStep !== 'z' ? 'opacity-40 pointer-events-none' : ''}`}>
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2 text-sm">
                  <MoveVertical className="w-4 h-4 text-cyan-400" />
                  Contrôle Hauteur (Z)
                </h3>

                <div className="space-y-2">
                  {/* Move Up Button */}
                  <button
                    onClick={handleMoveUp}
                    disabled={calibrationStep !== 'z'}
                    className="w-full bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400
                      text-white px-4 py-3 rounded-lg text-sm font-medium transition-all
                      flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="w-8 h-8 bg-cyan-500/20 group-hover:bg-cyan-500/30 rounded-lg flex items-center justify-center transition-all">
                      <ChevronUp className="w-5 h-5 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Monter le robot</span>
                  </button>

                  {/* Move Down Button */}
                  <button
                    onClick={handleMoveDown}
                    disabled={calibrationStep !== 'z'}
                    className="w-full bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400
                      text-white px-4 py-3 rounded-lg text-sm font-medium transition-all
                      flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="w-8 h-8 bg-cyan-500/20 group-hover:bg-cyan-500/30 rounded-lg flex items-center justify-center transition-all">
                      <ChevronDown className="w-5 h-5 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Descendre le robot</span>
                  </button>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 mt-3">
                  <p className="text-amber-400 text-xs font-medium">
                    {calibrationStep === 'z' 
                      ? '⚠️ Descendez lentement la pince jusqu\'au contact avec le plateau'
                      : '⚠️ Les contrôles Z seront disponibles à l\'étape 3'
                    }
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
              <div className="mb-6">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-cyan-500 blur-3xl opacity-40 animate-pulse"></div>
                  <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-2xl shadow-cyan-500/50 relative">
                    <Lock className="w-8 h-8 text-white" strokeWidth={2} />
                  </div>
                </div>
                <h1 className="text-3xl font-bold text-white mb-2">
                  Mode Superviseur
                </h1>
                <p className="text-slate-400 text-base">
                  Entrez le code PIN pour accéder à la calibration du robot
                </p>
              </div>

              {/* PIN Input */}
              <div className="flex justify-center gap-3 mb-5">
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
                    className={`w-14 h-16 text-center text-2xl font-bold rounded-xl border-2 bg-slate-800/70 text-white
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
                  className="text-red-400 mb-3 font-semibold text-sm"
                >
                  {error}
                </motion.p>
              )}

              <div className="bg-slate-800/60 backdrop-blur-sm rounded-xl px-5 py-2.5 inline-block border border-slate-700">
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
