import { useState } from 'react';
import { RotateCcw, X } from 'lucide-react';

interface RestartConfirmModalProps {
  isVisible: boolean;
  onCancel: () => void;
  onConfirm: (replaceBoard: boolean) => void;
}

export function RestartConfirmModal({ isVisible, onCancel, onConfirm }: RestartConfirmModalProps) {
  const [replaceBoard, setReplaceBoard] = useState(false);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-slate-800 border border-slate-600 rounded-2xl p-6 shadow-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-start gap-3 mb-5">
          <RotateCcw className="w-6 h-6 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-white font-bold text-lg">Relancer une partie ?</h2>
            <p className="text-slate-300 text-sm mt-1">
              La partie en cours sera terminée et une nouvelle partie commencera.
            </p>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white transition-colors flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Replacement Toggle */}
        <div className="mb-6 bg-slate-700/30 rounded-xl p-4 border border-slate-600/50">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="text-white font-semibold text-sm mb-1">
                Replacement automatique
              </h3>
              <p className="text-slate-400 text-xs">
                Le robot replace automatiquement toutes les pièces en position initiale avant de commencer
              </p>
            </div>
            <button
              onClick={() => setReplaceBoard(!replaceBoard)}
              className={`
                relative inline-flex h-8 w-14 items-center rounded-full transition-colors duration-300 ml-3 flex-shrink-0
                ${replaceBoard ? 'bg-cyan-500' : 'bg-slate-600'}
              `}
            >
              <span
                className={`
                  inline-block h-6 w-6 transform rounded-full bg-white transition-transform duration-300
                  ${replaceBoard ? 'translate-x-7' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
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
            onClick={() => onConfirm(replaceBoard)}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white transition-colors"
          >
            Relancer
          </button>
        </div>
      </div>
    </div>
  );
}
