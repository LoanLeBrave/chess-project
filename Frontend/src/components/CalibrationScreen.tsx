import { useState, useEffect, useRef, useCallback } from 'react';
import { Lock, Unlock, CheckCircle, Hand, ArrowLeft, SkipForward, AlignVerticalSpaceAround, Camera, Home, RotateCcw, Loader2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface CalibrationScreenProps {
  onCalibrationComplete: () => void;
  onBack: () => void;
}

const API_BASE = `http://${window.location.hostname}:8000`;

// Camera calibration constants
const CORNER_NAMES = ['TL', 'TR', 'BR', 'BL'] as const;
const CORNER_LABELS: Record<string, string> = {
  TL: 'Coin A8 (Haut-Gauche)',
  TR: 'Coin H8 (Haut-Droite)',
  BR: 'Coin H1 (Bas-Droite)',
  BL: 'Coin A1 (Bas-Gauche)',
};
const CORNER_COLORS: Record<string, string> = {
  TL: '#ef4444',
  TR: '#22c55e',
  BR: '#3b82f6',
  BL: '#eab308',
};

type Corner = { x: number; y: number };
type TabType = 'camera' | 'board';

export function CalibrationScreen({ onCalibrationComplete, onBack }: CalibrationScreenProps) {
  const [pin, setPin] = useState(['', '', '', '']); // Vide par défaut
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [error, setError] = useState('');
  
  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('board');
  const [cameraCalibCompleted, setCameraCalibCompleted] = useState(false);
  
  // Camera calibration state
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imagePath, setImagePath] = useState('');
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [corners, setCorners] = useState<Corner[]>([]);
  const [capturing, setCapturing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  // Board calibration state
  const [calibrationStep, setCalibrationStep] = useState<'a1' | 'h8' | 'z'>('a1');
  const [a1Calibrated, setA1Calibrated] = useState(false);
  const [h8Calibrated, setH8Calibrated] = useState(false);
  const [zCalibrated, setZCalibrated] = useState(false);
  const [freedriveActive, setFreedriveActive] = useState(false);
  const [homeSaved, setHomeSaved] = useState(false);

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
        // Remettre la pince droite, puis fermer le gripper
        fetch(`${API_BASE}/robot/calibrate/auto-level`, { method: 'POST' })
          .catch(() => {})
          .finally(() => {
            fetch(`${API_BASE}/robot/calibrate/close-gripper`, { method: 'POST' }).catch(() => {});
          });
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

  // ======= CAMERA CALIBRATION FUNCTIONS =======
  const currentCornerIdx = corners.length;
  const allCornersPlaced = corners.length === 4;

  const getScale = useCallback(() => {
    if (!canvasRef.current || imageSize.width === 0) return 1;
    return canvasRef.current.width / imageSize.width;
  }, [imageSize.width]);

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    const scale = getScale();

    corners.forEach((corner, i) => {
      const name = CORNER_NAMES[i];
      const color = CORNER_COLORS[name];
      const sx = corner.x * scale;
      const sy = corner.y * scale;

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx - 15, sy);
      ctx.lineTo(sx + 15, sy);
      ctx.moveTo(sx, sy - 15);
      ctx.lineTo(sx, sy + 15);
      ctx.stroke();

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(sx, sy, 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.font = 'bold 14px sans-serif';
      ctx.fillStyle = color;
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 3;
      ctx.strokeText(name, sx + 10, sy - 10);
      ctx.fillText(name, sx + 10, sy - 10);
    });

    if (corners.length >= 2) {
      ctx.strokeStyle = '#f97316';
      ctx.lineWidth = 2;
      ctx.setLineDash([]);
      for (let i = 0; i < corners.length - 1; i++) {
        ctx.beginPath();
        ctx.moveTo(corners[i].x * scale, corners[i].y * scale);
        ctx.lineTo(corners[i + 1].x * scale, corners[i + 1].y * scale);
        ctx.stroke();
      }
      if (corners.length === 4) {
        ctx.beginPath();
        ctx.moveTo(corners[3].x * scale, corners[3].y * scale);
        ctx.lineTo(corners[0].x * scale, corners[0].y * scale);
        ctx.stroke();

        drawGrid(ctx, corners, scale);
      }
    }
  }, [corners, getScale]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  const drawGrid = (ctx: CanvasRenderingContext2D, pts: Corner[], scale: number) => {
    const tl = { x: pts[0].x * scale, y: pts[0].y * scale };
    const tr = { x: pts[1].x * scale, y: pts[1].y * scale };
    const br = { x: pts[2].x * scale, y: pts[2].y * scale };
    const bl = { x: pts[3].x * scale, y: pts[3].y * scale };

    const interpolate = (u: number, v: number) => ({
      x: (1 - u) * (1 - v) * tl.x + u * (1 - v) * tr.x + u * v * br.x + (1 - u) * v * bl.x,
      y: (1 - u) * (1 - v) * tl.y + u * (1 - v) * tr.y + u * v * br.y + (1 - u) * v * bl.y,
    });

    const g = (i: number) => (i - 1) / 8;

    ctx.strokeStyle = 'rgba(0, 255, 0, 0.4)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      ctx.beginPath();
      ctx.moveTo(interpolate(g(0), g(i)).x, interpolate(g(0), g(i)).y);
      ctx.lineTo(interpolate(g(10), g(i)).x, interpolate(g(10), g(i)).y);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(interpolate(g(i), g(0)).x, interpolate(g(i), g(0)).y);
      ctx.lineTo(interpolate(g(i), g(10)).x, interpolate(g(i), g(10)).y);
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(0, 200, 255, 0.8)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(interpolate(0, 0).x, interpolate(0, 0).y);
    ctx.lineTo(interpolate(1, 0).x, interpolate(1, 0).y);
    ctx.lineTo(interpolate(1, 1).x, interpolate(1, 1).y);
    ctx.lineTo(interpolate(0, 1).x, interpolate(0, 1).y);
    ctx.closePath();
    ctx.stroke();
  };

  const handleCapture = async () => {
    setCapturing(true);
    setCameraError('');
    setCorners([]);
    try {
      const resp = await fetch(`${API_BASE}/camera/capture`, { method: 'POST' });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || 'Echec capture');

      setImageBase64(data.image_base64);
      setImagePath(data.image_path);
      setImageSize({ width: data.width, height: data.height });

      const img = new Image();
      img.onload = () => {
        imageRef.current = img;
        const canvas = canvasRef.current;
        if (canvas) {
          const maxWidth = Math.min(800, window.innerWidth - 40);
          const ratio = data.height / data.width;
          canvas.width = maxWidth;
          canvas.height = maxWidth * ratio;
          const ctx = canvas.getContext('2d');
          if (ctx) ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        }
      };
      img.src = `data:image/jpeg;base64,${data.image_base64}`;
    } catch (e: unknown) {
      setCameraError(e instanceof Error ? e.message : 'Erreur inconnue');
    }
    setCapturing(false);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || allCornersPlaced) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    const canvasX = (e.clientX - rect.left) * scaleX;
    const canvasY = (e.clientY - rect.top) * scaleY;

    const scale = getScale();
    const origX = Math.round(canvasX / scale);
    const origY = Math.round(canvasY / scale);

    setCorners(prev => [...prev, { x: origX, y: origY }]);
  };

  const handleResetCorners = () => {
    setCorners([]);
  };

  const handleSaveCamera = async () => {
    if (!allCornersPlaced) return;
    setSaving(true);
    setCameraError('');
    try {
      const cornersObj: Record<string, Corner> = {};
      CORNER_NAMES.forEach((name, i) => {
        cornersObj[name] = corners[i];
      });

      const resp = await fetch(`${API_BASE}/camera/calibrate/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ corners: cornersObj, source_image: imagePath }),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || 'Echec sauvegarde');

      setCameraCalibCompleted(true);
      setActiveTab('board');
    } catch (e: unknown) {
      setCameraError(e instanceof Error ? e.message : 'Erreur inconnue');
    }
    setSaving(false);
  };

  // ======= BOARD CALIBRATION FUNCTIONS =======
  const handleValidateA1 = async () => {
    try {
      await fetch(`${API_BASE}/robot/calibrate/point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point: 'a1' }),
      });
    } catch { /* continue */ }
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
      await fetch(`${API_BASE}/robot/calibrate/point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point: 'z' }),
      });
      await fetch(`${API_BASE}/robot/calibrate/save`, { method: 'POST' });
    } catch { /* continue */ }
    setZCalibrated(true);
    setTimeout(() => {
      onCalibrationComplete();
    }, 500);
  };

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

  const handleSaveHome = async () => {
    try {
      const resp = await fetch(`${API_BASE}/robot/save-home-position`, { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        setHomeSaved(true);
        setTimeout(() => setHomeSaved(false), 3000);
      }
    } catch { /* continue */ }
  };

  return (
    <div className="h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-4 left-4 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-30"
      >
        <div className="w-9 h-9 rounded-full bg-slate-800/50 backdrop-blur-sm border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all shadow-lg">
          <ArrowLeft className="w-4 h-4" />
        </div>
        <span className="font-medium text-sm">Retour</span>
      </button>

      {/* Main Calibration Content (always rendered, blurred when locked) */}
      <div className={`max-w-6xl w-full transition-all duration-500 ${!isUnlocked ? 'blur-sm pointer-events-none select-none' : ''}`}>
        <div>
          <div className="mb-6 text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-xl shadow-green-500/20">
              <Unlock className="w-8 h-8 text-white" strokeWidth={2} />
            </div>
            <h1 className="text-4xl font-bold text-white mb-3">
              Calibration Robot UR7e
            </h1>

            {/* Skip button */}
            <div className="mt-2 flex gap-3 justify-center items-center">
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

          {/* Board Calibration Content */}
          <div className="space-y-6">
              {/* Control Buttons - Top Row */}
              <div className="flex gap-3 justify-center flex-wrap">
                {/* Toggle Freedrive */}
                <button
                  onClick={handleToggleFreedrive}
                  className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                    flex items-center justify-center gap-2 group
                    ${freedriveActive
                      ? 'bg-green-500/30 hover:bg-green-500/40 border-2 border-green-500 hover:border-green-400 text-green-300 shadow-lg shadow-green-500/30'
                      : 'bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400 text-white'
                    }`}
                >
                  <Hand className={`w-4 h-4 ${freedriveActive ? 'text-green-300' : 'text-cyan-400'}`} strokeWidth={2.5} />
                  <span>{freedriveActive ? 'Désactiver' : 'Activer'} FreeDrive</span>
                </button>

                {/* Auto-Level */}
                <button
                  onClick={handleAutoLevel}
                  className="bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400
                    text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                    flex items-center justify-center gap-2 group"
                >
                  <AlignVerticalSpaceAround className="w-4 h-4 text-cyan-400" strokeWidth={2.5} />
                  <span>Remettre la pince droite</span>
                </button>

                {/* Save home position */}
                <button
                  onClick={handleSaveHome}
                  className={`border px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                    flex items-center justify-center gap-2 group
                    ${homeSaved
                      ? 'bg-cyan-500/30 border-2 border-cyan-500 text-cyan-300 shadow-lg shadow-cyan-500/30'
                      : 'bg-slate-700/50 hover:bg-slate-600/50 border-slate-600 hover:border-cyan-400 text-white'
                    }`}
                >
                  {homeSaved
                    ? <CheckCircle className="w-4 h-4 text-cyan-300" strokeWidth={2.5} />
                    : <Home className="w-4 h-4 text-cyan-400" strokeWidth={2.5} />
                  }
                  <span>{homeSaved ? 'Position sauvegardée !' : 'Sauvegarder position de démarrage'}</span>
                </button>

                {/* Small Camera Calibration Button */}
                <button
                  onClick={() => setActiveTab('camera')}
                  className="bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-purple-400
                    text-slate-300 hover:text-white px-3 py-2.5 rounded-lg text-xs font-medium transition-all
                    flex items-center justify-center gap-2 group"
                >
                  <Camera className="w-3.5 h-3.5 text-purple-400" strokeWidth={2.5} />
                  <span>Calibrer la caméra</span>
                </button>
              </div>

              {/* Calibration Steps - Horizontal */}
              <div className="grid grid-cols-3 gap-4">
                {/* Step A1 */}
                <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl overflow-hidden border-2 transition-all
                  ${calibrationStep === 'a1' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : a1Calibrated ? 'border-green-500' : 'border-slate-700 opacity-60'}`}>
                  {/* Image - Format carré fixe comme SafetyScreen */}
                  <div className="w-40 h-40 mx-auto bg-slate-900/80 rounded-lg overflow-hidden relative">
                    <img 
                      src="https://images.unsplash.com/photo-1763788427927-87bc7c1fbcf7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxyb2JvdGljJTIwYXJtJTIwY2hlc3MlMjBib2FyZCUyMHBvc2l0aW9uJTIwY29ybmVyfGVufDF8fHx8MTc3MjA5NTgyNXww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                      alt="Robot positioning A1"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-3 left-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center backdrop-blur-md border-2
                        ${a1Calibrated ? 'bg-green-500/90 border-green-400' : 'bg-cyan-500/90 border-cyan-400'}`}>
                        {a1Calibrated ? (
                          <CheckCircle className="w-6 h-6 text-white" strokeWidth={2.5} />
                        ) : (
                          <span className="text-white font-bold text-xl">1</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Content */}
                  <div className="p-4">
                    <h3 className="text-white font-bold text-lg mb-2">
                      Étape 1 : Position A1
                    </h3>
                    <p className="text-cyan-400 text-sm font-medium mb-2">
                      Coin bas gauche de l'échiquier
                    </p>
                    <p className="text-slate-400 text-sm mb-4 leading-relaxed">
                      Positionnez le bras du robot au-dessus de la case A1 (coin inférieur gauche du plateau).
                    </p>
                    
                    {calibrationStep === 'a1' && !a1Calibrated && (
                      <button
                        onClick={handleValidateA1}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-4 py-3 rounded-lg text-sm font-bold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-5 h-5" />
                        Valider position A1
                      </button>
                    )}
                    
                    {a1Calibrated && (
                      <div className="flex items-center justify-center gap-2 text-green-400 text-sm font-semibold bg-green-500/10 py-2 rounded-lg">
                        <CheckCircle className="w-5 h-5" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>

                {/* Step H8 */}
                <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl overflow-hidden border-2 transition-all
                  ${calibrationStep === 'h8' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : h8Calibrated ? 'border-green-500' : 'border-slate-700 opacity-60'}`}>
                  {/* Image - Format carré fixe comme SafetyScreen */}
                  <div className="w-40 h-40 mx-auto bg-slate-900/80 rounded-lg overflow-hidden relative">
                    <img 
                      src="https://images.unsplash.com/photo-1712238107648-4e94c158ab3d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbmR1c3RyaWFsJTIwcm9ib3QlMjBhcm0lMjBjYWxpYnJhdGlvbiUyMHBvc2l0aW9uaW5nfGVufDF8fHx8MTc3MjA5NTgyNnww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                      alt="Robot positioning H8"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-3 left-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center backdrop-blur-md border-2
                        ${h8Calibrated ? 'bg-green-500/90 border-green-400' : 'bg-cyan-500/90 border-cyan-400'}`}>
                        {h8Calibrated ? (
                          <CheckCircle className="w-6 h-6 text-white" strokeWidth={2.5} />
                        ) : (
                          <span className="text-white font-bold text-xl">2</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Content */}
                  <div className="p-4">
                    <h3 className="text-white font-bold text-lg mb-2">
                      Étape 2 : Position H8
                    </h3>
                    <p className="text-cyan-400 text-sm font-medium mb-2">
                      Coin haut droit de l'échiquier
                    </p>
                    <p className="text-slate-400 text-sm mb-4 leading-relaxed">
                      Positionnez le bras du robot au-dessus de la case H8 (coin supérieur droit du plateau).
                    </p>
                    
                    {calibrationStep === 'h8' && !h8Calibrated && (
                      <button
                        onClick={handleValidateH8}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-4 py-3 rounded-lg text-sm font-bold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-5 h-5" />
                        Valider position H8
                      </button>
                    )}
                    
                    {h8Calibrated && (
                      <div className="flex items-center justify-center gap-2 text-green-400 text-sm font-semibold bg-green-500/10 py-2 rounded-lg">
                        <CheckCircle className="w-5 h-5" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>

                {/* Step Z */}
                <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl overflow-hidden border-2 transition-all
                  ${calibrationStep === 'z' ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : zCalibrated ? 'border-green-500' : 'border-slate-700 opacity-60'}`}>
                  {/* Image - Format carré fixe comme SafetyScreen */}
                  <div className="w-40 h-40 mx-auto bg-slate-900/80 rounded-lg overflow-hidden relative">
                    <img 
                      src="https://images.unsplash.com/photo-1744659883786-af50c0e72588?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxyb2JvdCUyMGdyaXBwZXIlMjBoZWlnaHQlMjBhZGp1c3RtZW50JTIwdmVydGljYWx8ZW58MXx8fHwxNzcyMDk1ODI2fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                      alt="Robot height adjustment"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-3 left-3">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center backdrop-blur-md border-2
                        ${zCalibrated ? 'bg-green-500/90 border-green-400' : 'bg-cyan-500/90 border-cyan-400'}`}>
                        {zCalibrated ? (
                          <CheckCircle className="w-6 h-6 text-white" strokeWidth={2.5} />
                        ) : (
                          <span className="text-white font-bold text-xl">3</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Content */}
                  <div className="p-4">
                    <h3 className="text-white font-bold text-lg mb-2">
                      Étape 3 : Hauteur Z
                    </h3>
                    <p className="text-cyan-400 text-sm font-medium mb-2">
                      Ajustement de la hauteur de la pince
                    </p>
                    <p className="text-slate-400 text-sm mb-4 leading-relaxed">
                      Utilisez le FreeDrive pour descendre la pince jusqu'à ce qu'elle touche légèrement le plateau.
                    </p>
                    
                    {calibrationStep === 'z' && !zCalibrated && (
                      <button
                        onClick={handleValidateZ}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-4 py-3 rounded-lg text-sm font-bold
                          hover:from-cyan-600 hover:to-blue-700 transition-all shadow-lg shadow-cyan-500/30
                          flex items-center justify-center gap-2"
                      >
                        <CheckCircle className="w-5 h-5" />
                        Valider hauteur Z
                      </button>
                    )}
                    
                    {zCalibrated && (
                      <div className="flex items-center justify-center gap-2 text-green-400 text-sm font-semibold bg-green-500/10 py-2 rounded-lg">
                        <CheckCircle className="w-5 h-5" />
                        Position validée
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
        </div>
      </div>

      {/* Camera Calibration Modal */}
      <AnimatePresence>
        {activeTab === 'camera' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center z-30 bg-slate-900/95 backdrop-blur-md p-4"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-slate-800/90 rounded-2xl border border-slate-700 p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
                    <Camera className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">Calibration de la caméra</h2>
                    <p className="text-slate-400 text-sm">Définir les coins du plateau d'échecs</p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('board')}
                  className="w-10 h-10 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-red-400
                    text-slate-400 hover:text-white transition-all flex items-center justify-center"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Camera Content */}
              <div className="space-y-4">
                <p className="text-slate-400 text-sm text-center">
                  Cliquez les 4 coins du plateau d'échecs 8×8 (sans le cimetière)
                </p>

                {/* Bouton capture si pas d'image */}
                {!imageBase64 && (
                  <div className="flex items-center justify-center py-12">
                    <button
                      onClick={handleCapture}
                      disabled={capturing}
                      className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-8 py-4 rounded-xl text-lg font-semibold
                        hover:from-purple-600 hover:to-indigo-700 transition-all shadow-lg shadow-purple-500/30
                        flex items-center gap-3 disabled:opacity-50"
                    >
                      {capturing ? (
                        <>
                          <Loader2 className="w-6 h-6 animate-spin" />
                          Capture en cours...
                        </>
                      ) : (
                        <>
                          <Camera className="w-6 h-6" />
                          Prendre une photo
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Canvas + controles */}
                {imageBase64 && (
                  <>
                    {/* Instructions */}
                    <div className="flex items-center gap-3 flex-wrap justify-center">
                      {CORNER_NAMES.map((name, i) => (
                        <div
                          key={name}
                          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all
                            ${i < corners.length
                              ? 'bg-green-500/10 border-green-500/30 text-green-400'
                              : i === corners.length
                                ? 'bg-white/10 border-white/30 text-white animate-pulse'
                                : 'bg-slate-800/50 border-slate-700 text-slate-500'
                            }`}
                        >
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: i < corners.length ? '#22c55e' : CORNER_COLORS[name] }}
                          />
                          {i < corners.length ? (
                            <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                          ) : null}
                          <span>{name} - {CORNER_LABELS[name]}</span>
                        </div>
                      ))}
                    </div>

                    {/* Canvas */}
                    <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden flex items-center justify-center p-2">
                      <canvas
                        ref={canvasRef}
                        onClick={handleCanvasClick}
                        className={`max-w-full ${!allCornersPlaced ? 'cursor-crosshair' : 'cursor-default'}`}
                      />
                    </div>

                    {/* Boutons d'action */}
                    <div className="flex gap-3 justify-center flex-wrap">
                      <button
                        onClick={handleCapture}
                        disabled={capturing}
                        className="bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-purple-400
                          text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                          flex items-center gap-2 disabled:opacity-50"
                      >
                        <Camera className="w-4 h-4" />
                        Reprendre photo
                      </button>

                      <button
                        onClick={handleResetCorners}
                        disabled={corners.length === 0}
                        className="bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-amber-400
                          text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                          flex items-center gap-2 disabled:opacity-50"
                      >
                        <RotateCcw className="w-4 h-4" />
                        Reset coins
                      </button>

                      <button
                        onClick={handleSaveCamera}
                        disabled={!allCornersPlaced || saving}
                        className="bg-gradient-to-r from-green-500 to-emerald-600 text-white px-6 py-2.5 rounded-lg text-sm font-semibold
                          hover:from-green-600 hover:to-emerald-700 transition-all shadow-lg shadow-green-500/30
                          flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {saving ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Sauvegarde...
                          </>
                        ) : (
                          <>
                            <CheckCircle className="w-4 h-4" />
                            Valider la calibration
                          </>
                        )}
                      </button>
                    </div>

                    {/* Info */}
                    {!allCornersPlaced && currentCornerIdx < 4 && (
                      <div className="text-center">
                        <p className="text-slate-400 text-sm">
                          Cliquez sur le coin{' '}
                          <span className="font-bold" style={{ color: CORNER_COLORS[CORNER_NAMES[currentCornerIdx]] }}>
                            {CORNER_NAMES[currentCornerIdx]} ({CORNER_LABELS[CORNER_NAMES[currentCornerIdx]]})
                          </span>
                          {' '}du plateau
                        </p>
                      </div>
                    )}

                    {allCornersPlaced && (
                      <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-center">
                        <p className="text-green-400 text-sm font-medium">
                          4 coins sélectionnés - Vérifiez la grille puis cliquez "Valider la calibration"
                        </p>
                      </div>
                    )}
                  </>
                )}

                {/* Erreur */}
                {cameraError && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-center">
                    <p className="text-red-400 text-sm font-medium">{cameraError}</p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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
                    type="text"
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
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
