import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface StopConfirmModalProps {
  isVisible: boolean;
  onCancel: () => void;
  onConfirm: (replaceBoard: boolean) => void;
}

export function StopConfirmModal({ isVisible, onCancel, onConfirm }: StopConfirmModalProps) {
  const [replaceBoard, setReplaceBoard] = useState(false);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      
      {/* BACKDROP */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* MODAL */}
      <div className="
        relative z-10 w-full max-w-md mx-4
        bg-gradient-to-br from-slate-900 to-slate-800
        border border-slate-700
        rounded-2xl shadow-2xl
        p-6
        animate-in fade-in zoom-in-95
      ">

        {/* HEADER */}
        <div className="flex items-start gap-3 mb-5">
          <div className="w-10 h-10 flex items-center justify-center rounded-xl bg-amber-500/10">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          </div>

          <div className="flex-1">
            <h2 className="text-white font-semibold text-lg">
              Arrêter la partie ?
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              La partie sera arrêtée immédiatement.
            </p>
          </div>

          <button
            onClick={onCancel}
            className="text-slate-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* TOGGLE CARD */}
        <div className="
          mb-6 p-4 rounded-xl
          bg-slate-800/60
          border border-slate-700
          hover:border-slate-600
          transition-colors
        ">
          <div className="flex items-center justify-between gap-4">
            
            <div>
              <h3 className="text-white font-medium text-sm">
                Replacement automatique
              </h3>
              <p className="text-slate-500 text-xs mt-1">
                Replace les pièces sur le plateau
              </p>
            </div>

            {/* SWITCH */}
            <button
              onClick={() => setReplaceBoard(!replaceBoard)}
              className={`
                relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-300
                ${replaceBoard 
                  ? 'bg-cyan-500 shadow-md shadow-cyan-500/30' 
                  : 'bg-slate-600'}
              `}
            >
              <span
                className={`
                  inline-block h-5 w-5 transform rounded-full bg-white transition-transform duration-300
                  ${replaceBoard ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        </div>

        {/* ACTIONS */}
        <div className="flex gap-3">
          
          <button
            onClick={onCancel}
            className="
              flex-1 py-2.5 rounded-xl
              text-sm font-medium
              bg-slate-700 hover:bg-slate-600
              text-white
              transition-all duration-200
            "
          >
            Annuler
          </button>

          <button
            onClick={() => onConfirm(replaceBoard)}
            className="
              flex-1 py-2.5 rounded-xl
              text-sm font-medium
              bg-red-600 hover:bg-red-500
              text-white
              transition-all duration-200
              shadow-lg hover:shadow-red-500/20
            "
          >
            Arrêter
          </button>

        </div>
      </div>
    </div>
  );
}