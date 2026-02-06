import { useState } from 'react';
import { Lock, Unlock, CheckCircle, MoveHorizontal, MoveVertical, Hand, ArrowLeft } from 'lucide-react';

interface CalibrationScreenProps {
  onCalibrationComplete: () => void;
  onBack: () => void;
}

export function CalibrationScreen({ onCalibrationComplete, onBack }: CalibrationScreenProps) {
  const [pin, setPin] = useState(['', '', '', '']);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [calibrationStep, setCalibrationStep] = useState<'a1' | 'h8' | 'done'>('a1');
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
    setCalibrationStep('done');
  };

  const handleComplete = () => {
    onCalibrationComplete();
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group"
      >
        <div className="w-10 h-10 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all">
          <ArrowLeft className="w-5 h-5" />
        </div>
        <span className="font-medium">Retour</span>
      </button>

      <div className="max-w-4xl w-full">
        {!isUnlocked ? (
          // PIN Entry Screen
          <div className="text-center">
            <div className="mb-8">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-xl shadow-cyan-500/20">
                <Lock className="w-10 h-10 text-white" strokeWidth={2} />
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
                <input
                  key={index}
                  id={`pin-${index}`}
                  type="password"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handlePinChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  autoFocus={index === 0}
                  className={`w-16 h-20 text-center text-3xl font-bold rounded-xl border-2 bg-slate-800/50 text-white
                    transition-all duration-200 outline-none
                    ${error ? 'border-red-500 animate-shake' : 'border-slate-600 focus:border-cyan-400'}
                    ${digit ? 'border-cyan-500' : ''}`}
                />
              ))}
            </div>

            {error && (
              <p className="text-red-400 mb-4 animate-pulse">{error}</p>
            )}

            <p className="text-slate-500 text-sm">
              Code par défaut : <span className="text-slate-400 font-mono">0000</span>
            </p>
          </div>
        ) : calibrationStep !== 'done' ? (
          // Calibration Screen
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
                        Déplacez manuellement le préhenseur du robot au-dessus de la case A1 de l'échiquier
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
                        Déplacez manuellement le préhenseur du robot au-dessus de la case H8 de l'échiquier
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

              {/* Right - Visual Guide */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <Hand className="w-5 h-5 text-cyan-400" />
                  Guide de déplacement
                </h3>

                {/* Chessboard visualization */}
                <div className="bg-slate-900/50 rounded-lg p-4 mb-4 border border-slate-700">
                  <div className="aspect-square relative">
                    <div className="absolute inset-0 grid grid-cols-8 grid-rows-8 gap-[2px]">
                      {Array.from({ length: 64 }, (_, i) => {
                        const file = i % 8;
                        const rank = 7 - Math.floor(i / 8);
                        const isLight = (file + rank) % 2 === 0;
                        const isA1 = file === 0 && rank === 0;
                        const isH8 = file === 7 && rank === 7;
                        
                        return (
                          <div
                            key={i}
                            className={`relative ${isLight ? 'bg-slate-300' : 'bg-slate-600'}`}
                          >
                            {isA1 && (
                              <div className={`absolute inset-0 flex items-center justify-center
                                ${a1Calibrated ? 'bg-green-500' : 'bg-cyan-500 animate-pulse'}`}>
                                <span className="text-white font-bold text-xs">A1</span>
                              </div>
                            )}
                            {isH8 && (
                              <div className={`absolute inset-0 flex items-center justify-center
                                ${h8Calibrated ? 'bg-green-500' : calibrationStep === 'h8' ? 'bg-cyan-500 animate-pulse' : 'bg-slate-500'}`}>
                                <span className="text-white font-bold text-xs">H8</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Movement instructions */}
                <div className="space-y-3">
                  <div className="flex items-start gap-3 text-sm">
                    <div className="w-8 h-8 bg-cyan-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <MoveHorizontal className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">Déplacement horizontal (X)</p>
                      <p className="text-slate-400 text-xs">Déplacez le robot de gauche à droite</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 text-sm">
                    <div className="w-8 h-8 bg-cyan-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <MoveVertical className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">Déplacement vertical (Y)</p>
                      <p className="text-slate-400 text-xs">Déplacez le robot de bas en haut</p>
                    </div>
                  </div>

                  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mt-4">
                    <p className="text-amber-400 text-xs font-medium">
                      ⚠️ Assurez-vous que le préhenseur est centré au-dessus de la case avant de valider
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Calibration Complete
          <div className="text-center">
            <div className="mb-8">
              <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl mx-auto mb-6 flex items-center justify-center shadow-xl shadow-green-500/20 animate-pulse">
                <CheckCircle className="w-10 h-10 text-white" strokeWidth={2.5} />
              </div>
              <h1 className="text-4xl font-bold text-white mb-3">
                Calibration Terminée !
              </h1>
              <p className="text-slate-400 text-lg mb-8">
                Le robot UR7e connaît maintenant les positions de toutes les cases de l'échiquier
              </p>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-green-500/30 mb-8 inline-block">
              <div className="flex items-center gap-8">
                <div className="text-center">
                  <div className="text-green-400 font-bold text-2xl mb-1">A1</div>
                  <div className="text-slate-400 text-sm">Calibrée ✓</div>
                </div>
                <div className="w-px h-12 bg-slate-700"></div>
                <div className="text-center">
                  <div className="text-green-400 font-bold text-2xl mb-1">H8</div>
                  <div className="text-slate-400 text-sm">Calibrée ✓</div>
                </div>
              </div>
            </div>

            <button
              onClick={handleComplete}
              className="bg-gradient-to-r from-green-500 to-emerald-600 text-white px-8 py-4 rounded-xl font-bold text-lg
                hover:from-green-600 hover:to-emerald-700 transition-all shadow-xl shadow-green-500/30
                flex items-center justify-center gap-3 mx-auto"
            >
              Continuer vers la sécurité
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
