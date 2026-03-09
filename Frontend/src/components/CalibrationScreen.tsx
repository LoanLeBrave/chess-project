import { useState, useEffect, useRef, useCallback } from 'react';
import { Lock, Unlock, CheckCircle, Hand, ArrowLeft, SkipForward, Camera, Home, RotateCcw, Loader2, X, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { RecalibrateCameraModal } from './RecalibrateCameraModal';
import { NumericKeypad } from './NumericKeypad';
import etape1Image from './images/etape1.jpg';
import etape2Image from './images/etape2.jpg';
import etape3Image from './images/etape3.jpg';

interface CalibrationScreenProps {
  onCalibrationComplete: () => void;
  onSkipCalibration: () => void;
  hasCalibrated: boolean;
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

export function CalibrationScreen({ onCalibrationComplete, onSkipCalibration, hasCalibrated, onBack }: CalibrationScreenProps) {
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
  const magCanvasRef = useRef<HTMLCanvasElement>(null);
  const [magnifier, setMagnifier] = useState<{ visible: boolean; x: number; y: number }>({ visible: false, x: 0, y: 0 });
  // Compteur de génération : chaque appel à handleCapture incrémente ce compteur.
  // La boucle de retry vérifie qu'elle est toujours la génération courante avant de continuer.
  const captureGenRef = useRef(0);

  // Board calibration state
  const [calibrationStep, setCalibrationStep] = useState<'a1' | 'h8' | 'z'>('a1');
  const [a1Calibrated, setA1Calibrated] = useState(false);
  const [h8Calibrated, setH8Calibrated] = useState(false);
  const [zCalibrated, setZCalibrated] = useState(false);
  const [freedriveActive, setFreedriveActive] = useState(false);
  const [homeSaved, setHomeSaved] = useState(false);

  // Modal states
  const [showRecalibrateCameraModal, setShowRecalibrateCameraModal] = useState(false);
  const [showCameraCalibPrompt, setShowCameraCalibPrompt] = useState(false);

  const CORRECT_PIN = '1303';

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

  // Handle keypad press
  const handleKeypadPress = (value: string) => {
    // Find first empty position
    const emptyIndex = pin.findIndex(d => d === '');
    if (emptyIndex !== -1) {
      handlePinChange(emptyIndex, value);
    }
  };

  // Handle backspace from keypad
  const handleKeypadBackspace = () => {
    // Find last filled position
    const lastFilledIndex = [...pin].reverse().findIndex(d => d !== '');
    if (lastFilledIndex !== -1) {
      const actualIndex = pin.length - 1 - lastFilledIndex;
      handlePinChange(actualIndex, '');
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
    captureGenRef.current += 1;
    const myGen = captureGenRef.current;

    setCapturing(true);
    setCameraError('');
    setCorners([]);

    const RETRY_DELAY_MS = 700;

    while (captureGenRef.current === myGen) {
      try {
        const resp = await fetch(`${API_BASE}/camera/capture`, { method: 'POST' });
        const data = await resp.json();

        if (captureGenRef.current !== myGen) break;

        if (!data.success) {
          // Caméra occupée par le pipeline vision → retry silencieux
          await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
          continue;
        }

        setImageBase64(data.image_base64);
        setImagePath(data.image_path);
        setImageSize({ width: data.width, height: data.height });

        const img = new Image();
        img.onload = () => {
          imageRef.current = img;
          const canvas = canvasRef.current;
          if (canvas) {
            const ratio = data.height / data.width;
            // Laisser ~320px pour le header, onglets, boutons, gaps
            const maxHeight = globalThis.innerHeight * 0.58;
            const maxWidth = Math.min(1400, globalThis.innerWidth - 40, maxHeight / ratio);
            canvas.width = maxWidth;
            canvas.height = maxWidth * ratio;
            const ctx = canvas.getContext('2d');
            if (ctx) ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          }
        };
        img.src = `data:image/jpeg;base64,${data.image_base64}`;
        break; // succès

      } catch {
        if (captureGenRef.current === myGen) {
          await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
        }
      }
    }

    if (captureGenRef.current === myGen) setCapturing(false);
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

  const CAL_MAG_SIZE = 220;
  const CAL_MAG_ZOOM = 4;

  const handleCanvasMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || !imageRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    const canvasX = (e.clientX - rect.left) * scaleX;
    const canvasY = (e.clientY - rect.top) * scaleY;
    const imgScale = getScale();
    const origX = canvasX / imgScale;
    const origY = canvasY / imgScale;

    setMagnifier({ visible: true, x: e.clientX, y: e.clientY });

    const magCanvas = magCanvasRef.current;
    if (!magCanvas) return;
    const magCtx = magCanvas.getContext('2d');
    if (!magCtx) return;

    const srcHalf = CAL_MAG_SIZE / (2 * CAL_MAG_ZOOM);
    magCtx.clearRect(0, 0, CAL_MAG_SIZE, CAL_MAG_SIZE);

    magCtx.save();
    magCtx.beginPath();
    magCtx.arc(CAL_MAG_SIZE / 2, CAL_MAG_SIZE / 2, CAL_MAG_SIZE / 2 - 1, 0, Math.PI * 2);
    magCtx.clip();

    magCtx.fillStyle = '#0f172a';
    magCtx.fillRect(0, 0, CAL_MAG_SIZE, CAL_MAG_SIZE);

    magCtx.drawImage(
      imageRef.current,
      origX - srcHalf, origY - srcHalf, srcHalf * 2, srcHalf * 2,
      0, 0, CAL_MAG_SIZE, CAL_MAG_SIZE
    );
    magCtx.restore();

    const idx = Math.min(corners.length, 3);
    const color = !allCornersPlaced ? CORNER_COLORS[CORNER_NAMES[idx]] : 'rgba(255,255,255,0.7)';
    const cx = CAL_MAG_SIZE / 2;
    const cy = CAL_MAG_SIZE / 2;
    magCtx.strokeStyle = 'rgba(0,0,0,0.5)';
    magCtx.lineWidth = 3;
    for (const [ax, ay, bx, by] of [
      [cx - 25, cy, cx - 7, cy], [cx + 7, cy, cx + 25, cy],
      [cx, cy - 25, cx, cy - 7], [cx, cy + 7, cx, cy + 25],
    ] as [number,number,number,number][]) {
      magCtx.beginPath(); magCtx.moveTo(ax, ay); magCtx.lineTo(bx, by); magCtx.stroke();
    }
    magCtx.strokeStyle = color;
    magCtx.lineWidth = 1.5;
    for (const [ax, ay, bx, by] of [
      [cx - 25, cy, cx - 7, cy], [cx + 7, cy, cx + 25, cy],
      [cx, cy - 25, cx, cy - 7], [cx, cy + 7, cx, cy + 25],
    ] as [number,number,number,number][]) {
      magCtx.beginPath(); magCtx.moveTo(ax, ay); magCtx.lineTo(bx, by); magCtx.stroke();
    }
    magCtx.fillStyle = color;
    magCtx.beginPath();
    magCtx.arc(cx, cy, 2.5, 0, Math.PI * 2);
    magCtx.fill();
  }, [corners.length, allCornersPlaced, getScale]);

  const handleCanvasMouseLeave = useCallback(() => {
    setMagnifier(prev => ({ ...prev, visible: false }));
  }, []);

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
      // Si le robot est déjà calibré (on vient de la modale post-calibration robot),
      // terminer directement le flow global
      if (zCalibrated) {
        onCalibrationComplete();
      } else {
        setActiveTab('board');
      }
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
        body: JSON.stringify({ point: 'a1', freedrive_active: freedriveActive }),
      });
    } catch { /* continue */ }
    setA1Calibrated(true);
    setCalibrationStep('h8');
  };

  const handleValidateH8 = async () => {
    try {
      // freedrive_active: freedriveActive -> backend réactive le freedrive après la remontée
      await fetch(`${API_BASE}/robot/calibrate/point`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point: 'h8', freedrive_active: freedriveActive }),
      });
    } catch { /* continue */ }
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
    // Le backend désactive le freedrive dans /calibrate/save, on sync l'état UI
    setFreedriveActive(false);
    setZCalibrated(true);
    // Proposer la calibration caméra avant de continuer
    setTimeout(() => {
      setShowCameraCalibPrompt(true);
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

            {/* Skip button - After unlock */}
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
                  onClick={() => setShowRecalibrateCameraModal(true)}
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
                  <div className="relative w-40 h-40 mx-auto bg-slate-900/80 rounded-lg overflow-hidden">
                    <img 
                      src={etape1Image}
                      alt="Robot positioning A1"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center backdrop-blur-md border-2
                        ${a1Calibrated ? 'bg-green-500/90 border-green-400' : 'bg-cyan-500/90 border-cyan-400'}`}>
                        {a1Calibrated ? (
                          <CheckCircle className="w-5 h-5 text-white" strokeWidth={2.5} />
                        ) : (
                          <span className="text-white font-bold text-lg">1</span>
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
                  <div className="relative w-40 h-40 mx-auto bg-slate-900/80 rounded-lg overflow-hidden">
                    <img 
                      src={etape2Image}
                      alt="Robot positioning H8"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center backdrop-blur-md border-2
                        ${h8Calibrated ? 'bg-green-500/90 border-green-400' : 'bg-cyan-500/90 border-cyan-400'}`}>
                        {h8Calibrated ? (
                          <CheckCircle className="w-5 h-5 text-white" strokeWidth={2.5} />
                        ) : (
                          <span className="text-white font-bold text-lg">2</span>
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
                  <div className="relative w-40 h-40 mx-auto bg-slate-900/80 rounded-lg overflow-hidden">
                    <img 
                      src={etape3Image}
                      alt="Robot height adjustment"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center backdrop-blur-md border-2
                        ${zCalibrated ? 'bg-green-500/90 border-green-400' : 'bg-cyan-500/90 border-cyan-400'}`}>
                        {zCalibrated ? (
                          <CheckCircle className="w-5 h-5 text-white" strokeWidth={2.5} />
                        ) : (
                          <span className="text-white font-bold text-lg">3</span>
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

              {/* Warning Banner - Remove Rooks */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-gradient-to-r from-orange-600/20 via-amber-600/20 to-orange-600/20 border-2 border-orange-500/50 rounded-xl p-4 backdrop-blur-sm"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-xl bg-orange-500/20 border-2 border-orange-400 flex items-center justify-center">
                      <AlertTriangle className="w-6 h-6 text-orange-400" strokeWidth={2.5} />
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-bold text-base mb-1.5">
                      ⚠️ Avant de commencer la calibration
                    </h3>
                    <p className="text-white text-sm leading-relaxed">
                      Veuillez retirer les 2 tours proches du trou de calibration de l'échiquier avant de commencer la calibration. 
                      Cela permet d'éviter que le robot entre en collision avec les tours pendant les déplacements de calibration du plateau.
                    </p>
                  </div>
                </div>
              </motion.div>
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
              className="bg-slate-800/90 rounded-2xl border border-slate-700 p-6 max-w-7xl w-full max-h-[90vh] overflow-y-auto"
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
                        onMouseMove={handleCanvasMouseMove}
                        onMouseLeave={handleCanvasMouseLeave}
                        className={`max-w-full ${!allCornersPlaced ? 'cursor-crosshair' : 'cursor-default'}`}
                      />
                    </div>

                    {/* Loupe */}
                    {imageBase64 && (
                      <div
                        className="fixed pointer-events-none z-[9999] transition-opacity duration-100"
                        style={{
                          left: magnifier.x + 28,
                          top: magnifier.y - CAL_MAG_SIZE - 28,
                          opacity: magnifier.visible ? 1 : 0,
                          transform: magnifier.x > window.innerWidth - CAL_MAG_SIZE - 50 ? 'translateX(calc(-100% - 56px))' : undefined,
                        }}
                      >
                        <div className="relative">
                          {/* Halo coloré */}
                          <div
                            className="absolute inset-0 rounded-full blur-xl opacity-50"
                            style={{
                              background: !allCornersPlaced
                                ? CORNER_COLORS[CORNER_NAMES[Math.min(corners.length, 3)]]
                                : '#ffffff',
                              transform: 'scale(1.15)',
                            }}
                          />
                          {/* Canvas loupe */}
                          <canvas
                            ref={magCanvasRef}
                            width={CAL_MAG_SIZE}
                            height={CAL_MAG_SIZE}
                            className="rounded-full relative"
                            style={{
                              border: `2.5px solid ${
                                !allCornersPlaced
                                  ? CORNER_COLORS[CORNER_NAMES[Math.min(corners.length, 3)]]
                                  : 'rgba(255,255,255,0.4)'
                              }`,
                              boxShadow: `0 0 0 1px rgba(0,0,0,0.6), 0 8px 32px rgba(0,0,0,0.7), 0 0 24px ${
                                !allCornersPlaced
                                  ? CORNER_COLORS[CORNER_NAMES[Math.min(corners.length, 3)]] + '60'
                                  : 'rgba(255,255,255,0.15)'
                              }`,
                            }}
                          />
                          {/* Badge zoom */}
                          <div
                            className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[10px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap backdrop-blur-sm bg-black/50 border"
                            style={{
                              color: !allCornersPlaced
                                ? CORNER_COLORS[CORNER_NAMES[Math.min(corners.length, 3)]]
                                : 'rgba(255,255,255,0.6)',
                              borderColor: !allCornersPlaced
                                ? CORNER_COLORS[CORNER_NAMES[Math.min(corners.length, 3)]] + '60'
                                : 'rgba(255,255,255,0.15)',
                            }}
                          >
                            ×{CAL_MAG_ZOOM} — {!allCornersPlaced ? CORNER_NAMES[Math.min(corners.length, 3)] : '✓'}
                          </div>
                        </div>
                      </div>
                    )}

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
                    type="password"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handlePinChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    autoFocus={index === 0}
                    style={{ 
                      WebkitTextSecurity: 'disc',
                    }}
                    className={`w-14 h-16 text-center text-2xl font-bold rounded-xl border-2 bg-slate-800/70 text-white
                      transition-all duration-200 outline-none backdrop-blur-sm
                      [&::-ms-reveal]:hidden [&::-ms-clear]:hidden [&::-webkit-credentials-auto-fill-button]:hidden
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

              {/* Numeric Keypad */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.4 }}
                className="mt-6 mb-6"
              >
                <NumericKeypad
                  onKeyPress={handleKeypadPress}
                  onBackspace={handleKeypadBackspace}
                />
              </motion.div>

              {/* Skip Calibration Button - Under PIN inputs */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="mt-6 pt-4 border-t border-slate-700/50"
              >
                <button
                  onClick={onSkipCalibration}
                  disabled={!hasCalibrated}
                  className={`px-6 py-3.5 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 mx-auto shadow-lg
                    ${hasCalibrated
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white border-2 border-purple-400 hover:scale-105'
                      : 'bg-slate-800/50 text-slate-600 border-2 border-slate-700 cursor-not-allowed opacity-60'
                    }`}
                >
                  {hasCalibrated ? (
                    <>
                      <SkipForward className="w-5 h-5" />
                      Garder la même calibration
                    </>
                  ) : (
                    <>
                      <Lock className="w-4 h-4" />
                      Calibration requise (première partie)
                    </>
                  )}
                </button>
                <p className={`text-xs text-center mt-3 transition-colors ${hasCalibrated ? 'text-slate-400' : 'text-slate-600'}`}>
                  {hasCalibrated 
                    ? '✨ Passez directement à la page de sécurité sans refaire la calibration'
                    : '🔒 Ce bouton sera disponible après votre première partie complète'
                  }
                </p>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Recalibrate Camera Modal */}
      <RecalibrateCameraModal
        isVisible={showRecalibrateCameraModal}
        onConfirm={() => {
          setShowRecalibrateCameraModal(false);
          setActiveTab('camera');
        }}
        onCancel={() => setShowRecalibrateCameraModal(false)}
      />

      {/* Camera Calibration Prompt — après fin de calibration robot */}
      <AnimatePresence>
        {showCameraCalibPrompt && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-gradient-to-br from-slate-800 to-slate-900 border-2 border-cyan-500/50 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
            >
              {/* Header */}
              <div className="bg-gradient-to-r from-cyan-600/20 via-sky-600/20 to-cyan-600/20 p-6 border-b border-cyan-500/30">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-cyan-500/20 border-2 border-cyan-400 flex items-center justify-center">
                    <Camera className="w-7 h-7 text-cyan-400" strokeWidth={2.5} />
                  </div>
                  <div className="flex-1">
                    <h2 className="text-2xl font-bold text-white mb-1">Calibration terminée !</h2>
                    <p className="text-cyan-300 text-sm font-medium">Calibration du robot effectuée avec succès</p>
                  </div>
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500/20 border border-green-400 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  </div>
                </div>
              </div>

              {/* Body */}
              <div className="p-6 space-y-4">
                <div className="bg-slate-700/50 border border-cyan-500/20 rounded-xl p-4">
                  <p className="text-white text-base leading-relaxed">
                    Souhaitez-vous calibrer la <span className="text-cyan-400 font-semibold">caméra</span> maintenant ?
                  </p>
                  <p className="text-slate-400 text-sm mt-2 leading-relaxed">
                    La calibration caméra est nécessaire pour que le robot détecte correctement les pièces sur le plateau.
                    Si la caméra a déjà été calibrée et n'a pas bougé, vous pouvez passer.
                  </p>
                </div>

                <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <p className="text-amber-300 text-xs">
                    Ne pas calibrer la caméra peut entraîner des erreurs de détection des pièces.
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="px-6 pb-6 flex gap-3">
                <button
                  onClick={() => {
                    setShowCameraCalibPrompt(false);
                    onCalibrationComplete();
                  }}
                  className="flex-1 px-4 py-3 rounded-xl text-sm font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white transition-colors"
                >
                  Passer
                </button>
                <button
                  onClick={() => {
                    setShowCameraCalibPrompt(false);
                    setActiveTab('camera');
                  }}
                  className="flex-1 px-4 py-3 rounded-xl text-sm font-bold bg-cyan-600 hover:bg-cyan-500 text-white transition-colors flex items-center justify-center gap-2"
                >
                  <Camera className="w-4 h-4" />
                  Calibrer la caméra
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}