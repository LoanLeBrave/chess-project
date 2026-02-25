import { useState } from 'react';
import { Crown } from 'lucide-react';

interface PromotionModalProps {
  isVisible: boolean;
  promotionSquare: string;
  promotionColor: 'white' | 'black';
  onConfirm: (fromSq: string) => void;
}

export function PromotionModal({ isVisible, promotionSquare, promotionColor, onConfirm }: PromotionModalProps) {
  const [fromSq, setFromSq] = useState('');

  if (!isVisible) return null;

  const colorStr = promotionColor === 'white' ? 'blanche' : 'noire';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-800 border border-amber-500/50 rounded-2xl p-6 shadow-2xl max-w-sm w-full mx-4">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <Crown className="w-7 h-7 text-amber-400 flex-shrink-0" />
          <div>
            <h2 className="text-white font-bold text-lg">Promotion !</h2>
            <p className="text-slate-400 text-sm">
              Pion {colorStr} arrivé en <span className="text-amber-400 font-mono font-semibold">{promotionSquare}</span>
            </p>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-3 mb-4 text-sm text-amber-200 space-y-1">
          <p className="font-medium">Étapes :</p>
          <ol className="list-decimal list-inside space-y-1 text-amber-300/90">
            <li>Placez une dame {colorStr} sur une case libre accessible (ex&nbsp;: bord du plateau)</li>
            <li>Notez la case où vous l'avez déposée</li>
            <li>Entrez cette case ci-dessous et confirmez</li>
          </ol>
        </div>

        {/* Input */}
        <div className="mb-4">
          <label className="text-slate-400 text-xs mb-1.5 block">
            Case où la dame est placée <span className="text-slate-500">(ex : a0, h9, 99…)</span>
          </label>
          <input
            type="text"
            value={fromSq}
            onChange={e => setFromSq(e.target.value.toLowerCase().trim())}
            placeholder="ex: a0"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-amber-500 transition-colors"
            maxLength={2}
            autoFocus
            onKeyDown={e => { if (e.key === 'Enter' && fromSq.length >= 2) onConfirm(fromSq); }}
          />
        </div>

        {/* Confirm button */}
        <button
          onClick={() => onConfirm(fromSq)}
          disabled={fromSq.length < 2}
          className="w-full px-4 py-2.5 rounded-lg text-sm font-medium bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
        >
          Le robot place la dame
        </button>
      </div>
    </div>
  );
}
