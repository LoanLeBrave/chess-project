import { useState, useRef, useEffect, useCallback } from 'react';
import { CheckCircle, AlertCircle, RefreshCw, ArrowLeft, Play, Camera } from 'lucide-react';
import { motion } from 'motion/react';

interface PlacementConfirmationScreenProps {
  onConfirm: () => void;
  onBack: () => void;
}

const API_BASE = `${globalThis.location.protocol}//${globalThis.location.hostname}:8000`;

interface MissingPiece {
  square: string;
  code: string;
  name: string;
  color: 'white' | 'black';
}

interface Corner { x: number; y: number }
interface Corners { TL: Corner; TR: Corner; BR: Corner; BL: Corner }

// Position de départ standard
const STARTING_POSITION: Record<string, string> = {
  a1: 'WR', b1: 'WN', c1: 'WB', d1: 'WQ', e1: 'WK', f1: 'WB', g1: 'WN', h1: 'WR',
  a2: 'WP', b2: 'WP', c2: 'WP', d2: 'WP', e2: 'WP', f2: 'WP', g2: 'WP', h2: 'WP',
  a7: 'BP', b7: 'BP', c7: 'BP', d7: 'BP', e7: 'BP', f7: 'BP', g7: 'BP', h7: 'BP',
  a8: 'BR', b8: 'BN', c8: 'BB', d8: 'BQ', e8: 'BK', f8: 'BB', g8: 'BN', h8: 'BR',
};

// Convertit une case échecs (ex: 'e4') en coordonnées u/v [0,1] dans le plateau 8x8.
// Les coins calibrés sont les coins physiques du plateau 8x8 (A8=TL, H8=TR, H1=BR, A1=BL).
// u=0 → bord gauche (colonne A), u=1 → bord droit (colonne H)
// v=0 → bord haut (rangée 8),   v=1 → bord bas (rangée 1)
function squareToUV(square: string): { u: number; v: number } {
  const col = (square.codePointAt(0) ?? 0) - ('a'.codePointAt(0) ?? 0) + 1; // a=1 … h=8
  const row = Number.parseInt(square[1], 10);                                 // 1-8
  return {
    u: (col - 0.5) / 8,       // centre de la colonne dans [0,1]
    v: (8 - row + 0.5) / 8,   // centre de la rangée dans [0,1] (rangée 8 en haut)
  };
}

// Interpolation bilinéaire dans le quadrilatère défini par les 4 coins
function lerp(c: Corners, u: number, v: number): Corner {
  return {
    x: (1 - u) * (1 - v) * c.TL.x + u * (1 - v) * c.TR.x + u * v * c.BR.x + (1 - u) * v * c.BL.x,
    y: (1 - u) * (1 - v) * c.TL.y + u * (1 - v) * c.TR.y + u * v * c.BR.y + (1 - u) * v * c.BL.y,
  };
}

export function PlacementConfirmationScreen({ onConfirm, onBack }: Readonly<PlacementConfirmationScreenProps>) {
  const [imageBase64, setImageBase64] = useState('');
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [corners, setCorners] = useState<Corners | null>(null);
  const [missingPieces, setMissingPieces] = useState<MissingPiece[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState('');
  const [imageReady, setImageReady] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  // ── Dessin du canvas ─────────────────────────────────────────────────────────
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    if (!corners) return;

    const scale = canvas.width / img.naturalWidth;

    // Coins mis à l'échelle du canvas
    const sc: Corners = {
      TL: { x: corners.TL.x * scale, y: corners.TL.y * scale },
      TR: { x: corners.TR.x * scale, y: corners.TR.y * scale },
      BR: { x: corners.BR.x * scale, y: corners.BR.y * scale },
      BL: { x: corners.BL.x * scale, y: corners.BL.y * scale },
    };

    // Grille 10×10 (cimetière inclus via extrapolation bilinéaire)
    // Les coins calibrés sont les coins du plateau 8x8 → le cimetière s'étend au-delà.
    // g(i) mappe l'index [0..10] vers le paramètre bilinéaire :
    //   i=0 → -1/8 (cimetière), i=1 → 0 (bord plateau), i=9 → 1, i=10 → 9/8 (cimetière)
    const g = (i: number) => (i - 1) / 8;
    ctx.strokeStyle = 'rgba(0, 255, 0, 0.35)';
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    for (let i = 0; i <= 10; i++) {
      const h0 = lerp(sc, g(0), g(i)); const h1 = lerp(sc, g(10), g(i));
      ctx.beginPath(); ctx.moveTo(h0.x, h0.y); ctx.lineTo(h1.x, h1.y); ctx.stroke();
      const v0 = lerp(sc, g(i), g(0)); const v1 = lerp(sc, g(i), g(10));
      ctx.beginPath(); ctx.moveTo(v0.x, v0.y); ctx.lineTo(v1.x, v1.y); ctx.stroke();
    }

    // Contour du plateau 8×8 (exactement aux coins calibrés)
    ctx.strokeStyle = 'rgba(0, 200, 255, 0.7)';
    ctx.lineWidth = 2;
    const p = [lerp(sc, 0, 0), lerp(sc, 1, 0), lerp(sc, 1, 1), lerp(sc, 0, 1)];
    ctx.beginPath();
    ctx.moveTo(p[0].x, p[0].y);
    p.slice(1).forEach(pt => ctx.lineTo(pt.x, pt.y));
    ctx.closePath();
    ctx.stroke();

    // Marqueurs de pièces
    const missingSet = new Set(missingPieces.map((mp: MissingPiece) => mp.square));
    for (const [square, code] of Object.entries(STARTING_POSITION)) {
      const { u, v } = squareToUV(square);
      const pos = lerp(sc, u, v);
      const detected = !missingSet.has(square);
      const white = code.startsWith('W');

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);

      if (detected) {
        ctx.fillStyle = white ? 'rgba(255,255,255,0.9)' : 'rgba(20,20,20,0.9)';
        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
      } else {
        ctx.fillStyle = 'rgba(239,68,68,0.35)';
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 3]);
      }
      ctx.fill();
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [corners, missingPieces]);

  // ── Chargement de l'image dans le canvas ──────────────────────────────────
  useEffect(() => {
    if (!imageBase64 || !imageSize.width) return;
    const img = new Image();
    img.onload = () => {
      imageRef.current = img;
      const canvas = canvasRef.current;
      if (canvas) {
        const maxW = Math.min(900, 1200);
        const ratio = imageSize.height / imageSize.width;
        canvas.width = maxW;
        canvas.height = Math.round(maxW * ratio);
      }
      setImageReady(true);
    };
    img.src = `data:image/jpeg;base64,${imageBase64}`;
  }, [imageBase64, imageSize]);

  // ── Redessiner à chaque changement ──────────────────────────────────────────
  useEffect(() => {
    if (imageReady) drawCanvas();
  }, [imageReady, drawCanvas]);

  // ── Chargement des données ───────────────────────────────────────────────────
  const loadData = async () => {
    setIsLoading(true);
    setImageReady(false);
    imageRef.current = null;
    setError('');
    try {
      const [captureRes, calibRes, missingRes] = await Promise.all([
        fetch(`${API_BASE}/camera/capture`, { method: 'POST' }),
        fetch(`${API_BASE}/camera/calibration`),
        fetch(`${API_BASE}/vision/hybrid/missing`),
      ]);

      type CaptureData = { success: boolean; image_base64: string; width: number; height: number; error?: string };
      type CalibData   = { success: boolean; corners?: Corners; error?: string };
      type MissingData = { camera_pieces_count: number; missing_pieces: MissingPiece[] };

      const [captureData, calibData, missingData] = await Promise.all([
        captureRes.json(),
        calibRes.json(),
        missingRes.json(),
      ]) as [CaptureData, CalibData, MissingData];

      setMissingPieces(missingData.missing_pieces ?? []);

      if (calibData.success && calibData.corners) {
        setCorners(calibData.corners);
      }

      if (captureData.success && captureData.image_base64) {
        setImageSize({ width: captureData.width, height: captureData.height });
        setImageBase64(captureData.image_base64);
      } else {
        setError(captureData.error ?? 'Échec de la capture caméra.');
      }
    } catch (err) {
      setError(`Impossible de contacter le serveur : ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void loadData(); }, []);

  // ── Confirmation ─────────────────────────────────────────────────────────────
  const handleConfirm = async () => {
    setIsConfirming(true);
    try {
      const res = await fetch(`${API_BASE}/vision/hybrid/confirm`, { method: 'POST' });
      const data = await res.json() as { success: boolean; error?: string };
      if (data.success) {
        onConfirm();
      } else {
        setError(data.error ?? 'Erreur lors de la confirmation.');
      }
    } catch (err) {
      setError(`Impossible de confirmer : ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsConfirming(false);
    }
  };

  const allDetected = missingPieces.length === 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-5xl"
      >
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-white mb-2">Vérification du Plateau</h1>
          <p className="text-slate-400">Vérifiez que toutes les pièces sont bien placées, puis confirmez</p>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-6 shadow-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Zone canvas */}
            <div className="lg:col-span-2">
              <div className="relative bg-slate-900/80 rounded-xl overflow-hidden border border-slate-700 flex items-center justify-center min-h-48">
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-slate-900/70 z-10">
                    <RefreshCw className="w-10 h-10 text-cyan-500 animate-spin" />
                  </div>
                )}
                {imageBase64 ? (
                  <canvas ref={canvasRef} className="max-w-full" />
                ) : (
                  !isLoading && (
                    <div className="py-16 flex flex-col items-center gap-3 text-slate-500">
                      <Camera className="w-12 h-12" />
                      <p className="text-sm">Cliquez Actualiser pour prendre une photo</p>
                    </div>
                  )
                )}
              </div>

              {imageBase64 && (
                <div className="mt-2 flex items-center gap-4 text-xs text-slate-400 px-1">
                  {[
                    { cls: 'bg-white border-green-500',     label: 'Détectée (blanche)' },
                    { cls: 'bg-slate-800 border-green-500', label: 'Détectée (noire)' },
                    { cls: 'bg-red-500/40 border-red-500',  label: 'Non détectée' },
                  ].map(item => (
                    <div key={item.label} className="flex items-center gap-1.5">
                      <span className={`inline-block w-3 h-3 rounded-full border-2 ${item.cls}`}></span>
                      <span>{item.label}</span>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => { void loadData(); }}
                disabled={isLoading}
                className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-700/50 hover:bg-slate-700 text-white rounded-xl transition-all duration-300 disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
                Actualiser
              </button>
            </div>

            {/* Panneau info */}
            <div className="space-y-4">
              <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                <div className="flex items-center gap-3 mb-3">
                  {allDetected
                    ? <CheckCircle className="w-8 h-8 text-green-500 shrink-0" />
                    : <AlertCircle className="w-8 h-8 text-yellow-500 shrink-0" />
                  }
                  <div>
                    <h3 className="text-white font-bold">Pièces bien placées</h3>
                    <p className="text-2xl font-bold text-cyan-400">{32 - missingPieces.length} / 32</p>
                  </div>
                </div>
                {allDetected
                  ? <p className="text-green-400 text-sm">Toutes les pièces sont visibles</p>
                  : <p className="text-yellow-400 text-sm">{missingPieces.length} pièce(s) simulées automatiquement</p>
                }
              </div>

              {missingPieces.length > 0 && (
                <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                  <h3 className="text-white font-bold mb-3">Pièces non détectées</h3>
                  <div className="space-y-1.5 max-h-52 overflow-y-auto">
                    {missingPieces.map((p: MissingPiece) => (
                      <div key={p.square} className="flex items-center justify-between text-sm bg-slate-800/50 rounded-lg px-3 py-1.5">
                        <span className="font-mono text-slate-400 w-8">{p.square.toUpperCase()}</span>
                        <span className="text-white flex-1 ml-2">{p.name}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${p.color === 'white' ? 'bg-slate-200 text-slate-900' : 'bg-slate-700 text-slate-300'}`}>
                          {p.color === 'white' ? 'B' : 'N'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-3">
                <p className="text-cyan-300 text-xs leading-relaxed">
                  <strong>Mode hybride :</strong> les pièces non détectées sont simulées en position initiale. Elles seront reconnues dès qu'elles se déplacent.
                </p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                  <p className="text-red-400 text-xs">{error}</p>
                </div>
              )}
            </div>
          </div>

          {/* Boutons */}
          <div className="flex items-center gap-4 mt-6">
            <button
              onClick={onBack}
              disabled={isConfirming}
              className="flex items-center gap-2 px-6 py-3 bg-slate-700/50 hover:bg-slate-700 text-white rounded-xl transition-all duration-300 disabled:opacity-50"
            >
              <ArrowLeft className="w-5 h-5" />
              Retour
            </button>

            <button
              onClick={() => { void handleConfirm(); }}
              disabled={isLoading || isConfirming}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-bold rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isConfirming
                ? <RefreshCw className="w-6 h-6 animate-spin" />
                : <Play className="w-6 h-6" fill="white" />
              }
              {isConfirming ? 'Confirmation...' : 'Confirmer et lancer la partie'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}