import { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, RefreshCw, ArrowLeft, Play } from 'lucide-react';
import { motion } from 'motion/react';

interface PlacementConfirmationScreenProps {
  onConfirm: () => void;
  onBack: () => void;
}

const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

interface MissingPiece {
  square: string;
  code: string;
  name: string;
  color: 'white' | 'black';
}

export function PlacementConfirmationScreen({ onConfirm, onBack }: PlacementConfirmationScreenProps) {
  const [imageBase64, setImageBase64] = useState<string>('');
  const [cameraDetected, setCameraDetected] = useState<number>(0);
  const [missingPieces, setMissingPieces] = useState<MissingPiece[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string>('');

  const loadData = async () => {
    setIsLoading(true);
    setError('');
    try {
      // Récupérer les pièces manquantes via l'endpoint hybride
      const missingRes = await fetch(`${API_BASE}/vision/hybrid/missing`);
      const missingData = await missingRes.json();
      setCameraDetected(missingData.camera_pieces_count ?? 0);
      setMissingPieces(missingData.missing_pieces ?? []);

      // Récupérer l'image caméra
      const imgRes = await fetch(`${API_BASE}/camera/capture`, { method: 'POST' });
      const imgData = await imgRes.json();
      if (imgData.success && imgData.image_base64) {
        setImageBase64(imgData.image_base64);
      }
    } catch (e) {
      setError('Impossible de contacter le serveur. Vérifiez la connexion.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleConfirm = async () => {
    setIsConfirming(true);
    try {
      // Appel à l'endpoint hybride : simule les pièces manquantes dans le baseline
      const res = await fetch(`${API_BASE}/vision/hybrid/confirm`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        onConfirm();
      } else {
        setError('Erreur lors de la confirmation du placement.');
      }
    } catch (e) {
      setError('Impossible de confirmer. Vérifiez la connexion.');
    } finally {
      setIsConfirming(false);
    }
  };

  const allDetected = missingPieces.length === 0;
  const imageSrc = imageBase64
    ? `data:image/jpeg;base64,${imageBase64}`
    : '';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-5xl"
      >
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-white mb-2">
            Vérification du Plateau
          </h1>
          <p className="text-slate-400">
            Vérifiez que toutes les pièces sont bien placées, puis confirmez
          </p>
        </div>

        {/* Main Content */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-6 shadow-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Image de la caméra */}
            <div className="lg:col-span-2">
              <div className="relative bg-slate-900/80 rounded-xl overflow-hidden border border-slate-700">
                {isLoading ? (
                  <div className="aspect-video flex items-center justify-center">
                    <RefreshCw className="w-12 h-12 text-cyan-500 animate-spin" />
                  </div>
                ) : imageSrc ? (
                  <img
                    src={imageSrc}
                    alt="Vue caméra"
                    className="w-full h-auto"
                  />
                ) : (
                  <div className="aspect-video flex items-center justify-center">
                    <p className="text-slate-500 text-sm">Caméra non disponible</p>
                  </div>
                )}
              </div>

              <button
                onClick={loadData}
                disabled={isLoading}
                className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-700/50 hover:bg-slate-700 text-white rounded-xl transition-all duration-300 disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
                Actualiser
              </button>
            </div>

            {/* Panneau d'informations */}
            <div className="space-y-4">

              {/* Statut */}
              <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                <div className="flex items-center gap-3 mb-3">
                  {allDetected ? (
                    <CheckCircle className="w-8 h-8 text-green-500 shrink-0" />
                  ) : (
                    <AlertCircle className="w-8 h-8 text-yellow-500 shrink-0" />
                  )}
                  <div>
                    <h3 className="text-white font-bold">Pièces détectées</h3>
                    <p className="text-2xl font-bold text-cyan-400">
                      {cameraDetected} / 32
                    </p>
                  </div>
                </div>
                {allDetected ? (
                  <p className="text-green-400 text-sm">Toutes les pièces sont visibles</p>
                ) : (
                  <p className="text-yellow-400 text-sm">
                    {missingPieces.length} pièce(s) non détectée(s) — elles seront simulées automatiquement
                  </p>
                )}
              </div>

              {/* Liste des pièces manquantes */}
              {missingPieces.length > 0 && (
                <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                  <h3 className="text-white font-bold mb-3">Pièces non détectées</h3>
                  <div className="space-y-1.5 max-h-52 overflow-y-auto">
                    {missingPieces.map((p: MissingPiece) => (
                      <div
                        key={p.square}
                        className="flex items-center justify-between text-sm bg-slate-800/50 rounded-lg px-3 py-1.5"
                      >
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

              {/* Note hybride */}
              <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-3">
                <p className="text-cyan-300 text-xs leading-relaxed">
                  <strong>Mode hybride :</strong> les pièces non détectées par la caméra sont simulées en position initiale. Elles seront reconnues dès qu'elles se déplacent.
                </p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                  <p className="text-red-400 text-xs">{error}</p>
                </div>
              )}
            </div>
          </div>

          {/* Boutons d'action */}
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
              onClick={handleConfirm}
              disabled={isLoading || isConfirming}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-bold rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isConfirming ? (
                <RefreshCw className="w-6 h-6 animate-spin" />
              ) : (
                <Play className="w-6 h-6" fill="white" />
              )}
              {isConfirming ? 'Confirmation...' : 'Confirmer et lancer la partie'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}