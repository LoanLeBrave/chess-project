import { useState, useEffect, useRef, useCallback } from 'react';
import { Lock, Unlock, CheckCircle, MoveVertical, Hand, ArrowLeft, ChevronUp, ChevronDown, SkipForward, AlignVerticalSpaceAround, Camera } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { CameraCalibrationScreen } from './CameraCalibrationScreen';

interface CalibrationScreenProps {
  onCalibrationComplete: () => void;
  onBack: () => void;
}

const API_BASE = `http://${window.location.hostname}:8000`;

export function CalibrationScreen({ onCalibrationComplete, onBack }: CalibrationScreenProps) {
  const [pin, setPin] = useState(['', '', '', '']);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [calibrationStep, setCalibrationStep] = useState<'a1' | 'h8' | 'z'>('a1');
  const [a1Calibrated, setA1Calibrated] = useState(false);
  const [h8Calibrated, setH8Calibrated] = useState(false);
  const [zCalibrated, setZCalibrated] = useState(false);
  const [error, setError] = useState('');
  const [freedriveActive, setFreedriveActive] = useState(false);
  const [showCameraCalib, setShowCameraCalib] = useState(false);

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
        // Fermer le gripper pour la calibration
        fetch(`${API_BASE}/robot/calibrate/close-gripper`, {
          method: 'POST',
        }).catch(() => {});
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

  const handleValidateA1 = async () => {
    try {
      await fetch(`${API_BASE}/robot/calibrate/point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point: 'a1' }),
      });
    } catch { /* continue meme si API indisponible */ }
    setA1Calibrated(true);
    setCalibrationStep('h8');
  };

  const handleValidateH8 = async () => {
    try {
      await fetch(`${API_BASE}/robot/calibrate/point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point: 'h8' }),
      });
      // Desactiver freedrive pour passer aux controles Z
      await fetch(`${API_BASE}/robot/calibrate/freedrive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable: false }),
      });
    } catch { /* continue */ }
    setFreedriveActive(false);
    setH8Calibrated(true);
    setCalibrationStep('z');
  };

  const handleValidateZ = async () => {
    try {
      // Enregistrer le point Z de surface
      await fetch(`${API_BASE}/robot/calibrate/point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point: 'z' }),
      });
      // Calculer et sauvegarder la calibration
      await fetch(`${API_BASE}/robot/calibrate/save`, { method: 'POST' });
    } catch { /* continue */ }
    setZCalibrated(true);
    setTimeout(() => {
      onCalibrationComplete();
    }, 500);
  };

  // --- Mouvement Z fluide (start/stop) ---
  const movingDirection = useRef<string | null>(null);
  const [movingZ, setMovingZ] = useState<'up' | 'down' | null>(null);

  const startMoveZ = useCallback((direction: 'up' | 'down') => {
    if (!isUnlocked || movingDirection.current === direction) return;
    movingDirection.current = direction;
    setMovingZ(direction);
    fetch(`${API_BASE}/robot/calibrate/move-z/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ direction }),
    }).catch(() => {});
  }, [isUnlocked]);

  const stopMoveZ = useCallback(() => {
    if (!movingDirection.current) return;
    movingDirection.current = null;
    setMovingZ(null);
    fetch(`${API_BASE}/robot/calibrate/move-z/stop`, {
      method: 'POST',
    }).catch(() => {});
  }, []);

  // Binding clavier global : W/ArrowUp = monter, S/ArrowDown = descendre
  useEffect(() => {
    if (!isUnlocked) return;

    const onKeyDown = (e: KeyboardEvent) => {
      // Ignorer si on est dans un input (PIN)
      if ((e.target as HTMLElement)?.tagName === 'INPUT') return;
      if (e.repeat) return; // Ignorer les repeat du OS

      if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') {
        e.preventDefault();
        startMoveZ('up');
      } else if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') {
        e.preventDefault();
        startMoveZ('down');
      }
    };

    const onKeyUp = (e: KeyboardEvent) => {
      if (
        e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp' ||
        e.key === 's' || e.key === 'S' || e.key === 'ArrowDown'
      ) {
        stopMoveZ();
      }
    };

    // Securite : arreter si la fenetre perd le focus
    const onBlur = () => stopMoveZ();

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('blur', onBlur);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      window.removeEventListener('blur', onBlur);
      // Arreter le mouvement au demontage
      if (movingDirection.current) {
        fetch(`${API_BASE}/robot/calibrate/move-z/stop`, { method: 'POST' }).catch(() => {});
      }
    };
  }, [isUnlocked, startMoveZ, stopMoveZ]);

  const handleToggleFreedrive = async () => {
    const newState = !freedriveActive;
    try {
      await fetch(`${API_BASE}/robot/calibrate/freedrive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable: newState }),
      });
      setFreedriveActive(newState);
    } catch { /* continue */ }
  };

  const handleAutoLevel = () => {
    setFreedriveActive(false);
    fetch(`${API_BASE}/robot/calibrate/auto-level`, {
      method: 'POST',
    }).catch(() => {});
  };

  // Afficher la calibration camera si demandee
  if (showCameraCalib) {
    return (
      <CameraCalibrationScreen
        onComplete={() => setShowCameraCalib(false)}
        onCancel={() => setShowCameraCalib(false)}
      />
    );
  }

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
            {freedriveActive ? (
              <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-1.5">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-green-400 text-xs font-medium">
                  Free Drive actif - Vous pouvez deplacer le robot manuellement
                </span>
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 bg-slate-500/10 border border-slate-500/30 rounded-lg px-3 py-1.5">
                <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                <span className="text-slate-400 text-xs font-medium">
                  Free Drive inactif
                </span>
              </div>
            )}

            {/* Boutons secondaires */}
            <div className="mt-3 flex gap-3 justify-center flex-wrap">
              <button
                onClick={() => setShowCameraCalib(true)}
                className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-xs font-medium
                  bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 hover:border-purple-500
                  rounded-lg px-3 py-1.5 transition-all"
              >
                <Camera className="w-3.5 h-3.5" />
                Calibrer la camera
              </button>
              <button
                onClick={onCalibrationComplete}
                className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-xs font-medium
                  bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 hover:border-slate-500
                  rounded-lg px-3 py-1.5 transition-all"
              >
                <SkipForward className="w-3.5 h-3.5" />
                Utiliser la calibration actuelle
              </button>
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
              {/* Robot Controls */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2 text-sm">
                  <Hand className="w-4 h-4 text-cyan-400" />
                  Controles Robot
                </h3>

                <div className="space-y-2">
                  {/* Toggle Freedrive */}
                  <button
                    onClick={handleToggleFreedrive}
                    disabled={calibrationStep === 'z'}
                    className={`w-full px-4 py-3 rounded-lg text-sm font-medium transition-all
                      flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed
                      ${freedriveActive
                        ? 'bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 hover:border-green-400 text-green-400'
                        : 'bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400 text-white'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all
                      ${freedriveActive ? 'bg-green-500/30' : 'bg-cyan-500/20 group-hover:bg-cyan-500/30'}`}>
                      <Hand className={`w-5 h-5 ${freedriveActive ? 'text-green-400' : 'text-cyan-400'}`} strokeWidth={2.5} />
                    </div>
                    <span>{freedriveActive ? 'Desactiver FreeDrive' : 'Activer FreeDrive'}</span>
                  </button>

                  {/* Auto-Level */}
                  <button
                    onClick={handleAutoLevel}
                    className="w-full bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400
                      text-white px-4 py-3 rounded-lg text-sm font-medium transition-all
                      flex items-center justify-center gap-2 group"
                  >
                    <div className="w-8 h-8 bg-cyan-500/20 group-hover:bg-cyan-500/30 rounded-lg flex items-center justify-center transition-all">
                      <AlignVerticalSpaceAround className="w-5 h-5 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Remettre la pince droite</span>
                  </button>
                </div>
              </div>

              {/* Z-Axis Controls */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700 transition-all">
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2 text-sm">
                  <MoveVertical className="w-4 h-4 text-cyan-400" />
                  Contrôle Hauteur (Z)
                </h3>

                <div className="space-y-2">
                  {/* Move Up Button */}
                  <button
                    onMouseDown={() => startMoveZ('up')}
                    onMouseUp={stopMoveZ}
                    onMouseLeave={stopMoveZ}
                    onTouchStart={() => startMoveZ('up')}
                    onTouchEnd={stopMoveZ}
                    className={`w-full border text-white px-4 py-3 rounded-lg text-sm font-medium transition-all
                      flex items-center justify-center gap-2 group select-none
                      ${movingZ === 'up'
                        ? 'bg-cyan-500/20 border-cyan-400'
                        : 'bg-slate-700/50 hover:bg-slate-600/50 border-slate-600 hover:border-cyan-400'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all
                      ${movingZ === 'up' ? 'bg-cyan-500/40' : 'bg-cyan-500/20 group-hover:bg-cyan-500/30'}`}>
                      <ChevronUp className="w-5 h-5 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Monter (W / ↑)</span>
                  </button>

                  {/* Move Down Button */}
                  <button
                    onMouseDown={() => startMoveZ('down')}
                    onMouseUp={stopMoveZ}
                    onMouseLeave={stopMoveZ}
                    onTouchStart={() => startMoveZ('down')}
                    onTouchEnd={stopMoveZ}
                    className={`w-full border text-white px-4 py-3 rounded-lg text-sm font-medium transition-all
                      flex items-center justify-center gap-2 group select-none
                      ${movingZ === 'down'
                        ? 'bg-cyan-500/20 border-cyan-400'
                        : 'bg-slate-700/50 hover:bg-slate-600/50 border-slate-600 hover:border-cyan-400'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all
                      ${movingZ === 'down' ? 'bg-cyan-500/40' : 'bg-cyan-500/20 group-hover:bg-cyan-500/30'}`}>
                      <ChevronDown className="w-5 h-5 text-cyan-400" strokeWidth={2.5} />
                    </div>
                    <span>Descendre (S / ↓)</span>
                  </button>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5 mt-3">
                  <p className="text-amber-400 text-xs font-medium">
                    Maintenez W/↑ ou S/↓ pour un mouvement continu, relacher pour arreter
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
