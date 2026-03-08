import { Delete } from 'lucide-react';
import { motion } from 'motion/react';

interface AlphabeticKeypadProps {
  onKeyPress: (value: string) => void;
  onBackspace: () => void;
  onSpace: () => void;
}

export function AlphabeticKeypad({ onKeyPress, onBackspace, onSpace }: AlphabeticKeypadProps) {
  const rows = [
    ['A', 'Z', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['Q', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M'],
    ['W', 'X', 'C', 'V', 'B', 'N']
  ];

  return (
    <div className="flex flex-col gap-3 select-none">
      {rows.map((row, rowIndex) => (
        <div key={rowIndex} className="flex justify-center gap-2.5">
          {row.map((key) => (
            <motion.button
              key={key}
              whileTap={{ scale: 0.95 }}
              onClick={() => onKeyPress(key)}
              className="w-14 h-14 rounded-xl bg-slate-700/80 hover:bg-slate-600 border-2 border-slate-600 hover:border-cyan-400 text-white font-bold text-xl transition-all shadow-lg hover:shadow-cyan-500/30"
            >
              {key}
            </motion.button>
          ))}
        </div>
      ))}
      
      {/* Bottom row with Space and Backspace */}
      <div className="flex justify-center gap-2.5">
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={onBackspace}
          className="w-24 h-14 rounded-xl bg-red-600/80 hover:bg-red-500 border-2 border-red-500 hover:border-red-400 text-white font-bold transition-all shadow-lg hover:shadow-red-500/30 flex items-center justify-center"
        >
          <Delete className="w-6 h-6" />
        </motion.button>
        
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={onSpace}
          className="flex-1 max-w-md h-14 rounded-xl bg-slate-700/80 hover:bg-slate-600 border-2 border-slate-600 hover:border-cyan-400 text-white font-semibold text-base transition-all shadow-lg hover:shadow-cyan-500/30"
        >
          ESPACE
        </motion.button>
      </div>
    </div>
  );
}