import { useState, useRef, useCallback, useEffect } from 'react';
import { Camera, RotateCcw, CheckCircle, X, Loader2 } from 'lucide-react';
import { motion } from 'motion/react';

interface CameraCalibrationScreenProps {
  onComplete: () => void;
  onCancel: () => void;
}

const API_BASE = `http://${window.location.hostname}:8000`;

const CORNER_NAMES = ['TL', 'TR', 'BR', 'BL'] as const;
const CORNER_LABELS: Record<string, string> = {
  TL: 'Haut-Gauche',
  TR: 'Haut-Droite',
  BR: 'Bas-Droite',
  BL: 'Bas-Gauche',
};
const CORNER_COLORS: Record<string, string> = {
  TL: '#ef4444',
  TR: '#22c55e',
  BR: '#3b82f6',
  BL: '#eab308',
};

type Corner = { x: number; y: number };

export function CameraCalibrationScreen({ onComplete, onCancel }: CameraCalibrationScreenProps) {
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imagePath, setImagePath] = useState('');
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [corners, setCorners] = useState<Corner[]>([]);
  const [capturing, setCapturing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  const currentCornerIdx = corners.length;
  const allCornersPlaced = corners.length === 4;

  const getScale = useCallback(() => {
    if (!canvasRef.current || imageSize.width === 0) return 1;
    return canvasRef.current.width / imageSize.width;
  }, [imageSize.width]);

  // Dessiner le canvas
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Dessiner l'image
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    const scale = getScale();

    // Dessiner les coins places
    corners.forEach((corner, i) => {
      const name = CORNER_NAMES[i];
      const color = CORNER_COLORS[name];
      const sx = corner.x * scale;
      const sy = corner.y * scale;

      // Croix
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx - 15, sy);
      ctx.lineTo(sx + 15, sy);
      ctx.moveTo(sx, sy - 15);
      ctx.lineTo(sx, sy + 15);
      ctx.stroke();

      // Cercle
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(sx, sy, 5, 0, Math.PI * 2);
      ctx.fill();

      // Label
      ctx.font = 'bold 14px sans-serif';
      ctx.fillStyle = color;
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 3;
      ctx.strokeText(name, sx + 10, sy - 10);
      ctx.fillText(name, sx + 10, sy - 10);
    });

    // Dessiner les lignes entre les coins
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
      // Fermer le quadrilatere si 4 coins
      if (corners.length === 4) {
        ctx.beginPath();
        ctx.moveTo(corners[3].x * scale, corners[3].y * scale);
        ctx.lineTo(corners[0].x * scale, corners[0].y * scale);
        ctx.stroke();

        // Dessiner la grille 10x10 en perspective
        drawGrid(ctx, corners, scale);
      }
    }
  }, [corners, getScale]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  const drawGrid = (ctx: CanvasRenderingContext2D, pts: Corner[], scale: number) => {
    // Calcul de la transformation perspective simplifiee
    // On interpole bilineairement entre les 4 coins
    const tl = { x: pts[0].x * scale, y: pts[0].y * scale };
    const tr = { x: pts[1].x * scale, y: pts[1].y * scale };
    const br = { x: pts[2].x * scale, y: pts[2].y * scale };
    const bl = { x: pts[3].x * scale, y: pts[3].y * scale };

    ctx.strokeStyle = 'rgba(0, 255, 0, 0.4)';
    ctx.lineWidth = 1;

    const interpolate = (u: number, v: number) => ({
      x: (1 - u) * (1 - v) * tl.x + u * (1 - v) * tr.x + u * v * br.x + (1 - u) * v * bl.x,
      y: (1 - u) * (1 - v) * tl.y + u * (1 - v) * tr.y + u * v * br.y + (1 - u) * v * bl.y,
    });

    // Lignes horizontales et verticales (grille 10x10)
    for (let i = 0; i <= 10; i++) {
      const t = i / 10;
      // Ligne horizontale
      ctx.beginPath();
      const h0 = interpolate(0, t);
      const h1 = interpolate(1, t);
      ctx.moveTo(h0.x, h0.y);
      ctx.lineTo(h1.x, h1.y);
      ctx.stroke();

      // Ligne verticale
      ctx.beginPath();
      const v0 = interpolate(t, 0);
      const v1 = interpolate(t, 1);
      ctx.moveTo(v0.x, v0.y);
      ctx.lineTo(v1.x, v1.y);
      ctx.stroke();
    }

    // Bordure du plateau central 8x8 (1/10 a 9/10)
    ctx.strokeStyle = 'rgba(0, 200, 255, 0.7)';
    ctx.lineWidth = 2;
    const inner = [
      interpolate(0.1, 0.1),
      interpolate(0.9, 0.1),
      interpolate(0.9, 0.9),
      interpolate(0.1, 0.9),
    ];
    ctx.beginPath();
    ctx.moveTo(inner[0].x, inner[0].y);
    for (let i = 1; i < 4; i++) ctx.lineTo(inner[i].x, inner[i].y);
    ctx.closePath();
    ctx.stroke();
  };

  const handleCapture = async () => {
    setCapturing(true);
    setError('');
    setCorners([]);
    try {
      const resp = await fetch(`${API_BASE}/camera/capture`, { method: 'POST' });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || 'Echec capture');

      setImageBase64(data.image_base64);
      setImagePath(data.image_path);
      setImageSize({ width: data.width, height: data.height });

      // Charger l'image dans un element img pour le canvas
      const img = new Image();
      img.onload = () => {
        imageRef.current = img;
        // Configurer le canvas
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
      setError(e instanceof Error ? e.message : 'Erreur inconnue');
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

    // Convertir en coordonnees image originale
    const scale = getScale();
    const origX = Math.round(canvasX / scale);
    const origY = Math.round(canvasY / scale);

    setCorners(prev => [...prev, { x: origX, y: origY }]);
  };

  const handleReset = () => {
    setCorners([]);
  };

  const handleSave = async () => {
    if (!allCornersPlaced) return;
    setSaving(true);
    setError('');
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

      onComplete();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur inconnue');
    }
    setSaving(false);
  };

  return (
    <div className="h-screen flex flex-col items-center p-4 overflow-auto">
      {/* Header */}
      <div className="w-full max-w-4xl mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-xl shadow-purple-500/20">
              <Camera className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Calibration Camera</h1>
              <p className="text-slate-400 text-xs">Cliquez les 4 coins du plateau sur la photo</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="w-9 h-9 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center hover:border-red-400 transition-all text-slate-400 hover:text-red-400"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Contenu principal */}
      <div className="w-full max-w-4xl flex-1 flex flex-col gap-4">
        {/* Bouton capture si pas d'image */}
        {!imageBase64 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex-1 flex items-center justify-center"
          >
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
          </motion.div>
        )}

        {/* Canvas + controles */}
        {imageBase64 && (
          <>
            {/* Instructions */}
            <div className="flex items-center gap-3 flex-wrap">
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
                onClick={handleReset}
                disabled={corners.length === 0}
                className="bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-amber-400
                  text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-all
                  flex items-center gap-2 disabled:opacity-50"
              >
                <RotateCcw className="w-4 h-4" />
                Reset coins
              </button>

              <button
                onClick={handleSave}
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
                  4 coins selectionnes - Verifiez la grille puis cliquez "Valider la calibration"
                </p>
              </div>
            )}
          </>
        )}

        {/* Erreur */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-center">
            <p className="text-red-400 text-sm font-medium">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
