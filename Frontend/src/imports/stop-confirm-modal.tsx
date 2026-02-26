import { AlertTriangle, X } from 'lucide-react';

interface StopConfirmModalProps {
  isVisible: boolean;
  onCancel: () => void;
  onConfirm: (replaceBoard: boolean) => void;
}

export function StopConfirmModal({ isVisible, onCancel, onConfirm }: StopConfirmModalProps) {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-slate-800 border border-slate-600 rounded-2xl p-6 shadow-2xl max-w-sm w-full mx-4">
        {/* Header */}
        <div className="flex items-start gap-3 mb-5">
          <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-white font-bold text-lg">Arrêter la partie ?</h2>
            <p className="text-slate-300 text-sm mt-1">
              Le robot s'arrêtera immédiatement et la partie en cours sera terminée.
              Les pièces peuvent être replacées manuellement.
            </p>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white transition-colors flex-shrink-0"
          >
            <X className="w-5 h-5" />
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
            onClick={() => onConfirm(false)}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-500 text-white transition-colors"
          >
            Arrêter
          </button>
        </div>
      </div>
    </div>
  );
}