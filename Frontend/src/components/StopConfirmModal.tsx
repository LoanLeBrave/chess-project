import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface StopConfirmModalProps {
  isVisible: boolean;
  onCancel: () => void;
  onConfirm: (replaceBoard: boolean) => void;
}

export function StopConfirmModal({ isVisible, onCancel, onConfirm }: StopConfirmModalProps) {
  const [shouldReplace, setShouldReplace] = useState(false);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-slate-800 border border-slate-500 rounded-2xl p-6 shadow-2xl max-w-sm w-full mx-4">
        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-white font-bold text-lg">Arrêter la partie ?</h2>
            <p className="text-slate-300 text-sm mt-1">
              Le robot s'arrêtera immédiatement et la partie en cours sera terminée.
            </p>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white transition-colors flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toggle replacer les pièces */}
        <div className="flex items-center justify-between p-3 bg-slate-700 rounded-lg mb-5">
          <div>
            <p className="text-white text-sm font-medium">Replacer les pièces automatiquement</p>
            <p className="text-slate-400 text-xs mt-0.5">Le robot remettra toutes les pièces en position initiale</p>
          </div>
          <button
            onClick={() => setShouldReplace(!shouldReplace)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 ml-3 ${
              shouldReplace ? 'bg-cyan-600' : 'bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                shouldReplace ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-slate-600 hover:bg-slate-500 text-white transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={() => onConfirm(shouldReplace)}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-500 text-white transition-colors"
          >
            Arrêter
          </button>
        </div>
      </div>
    </div>
  );
}
