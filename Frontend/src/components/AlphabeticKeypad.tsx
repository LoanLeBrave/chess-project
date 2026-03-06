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
    <div className="flex flex-col gap-2.5 select-none">
      {rows.map((row, rowIndex) => (
        <div key={rowIndex} className="flex justify-center gap-2">
          {row.map((key) => (
            <motion.button
              key={key}
              whileTap={{ scale: 0.95 }}
              onClick={() => onKeyPress(key)}
              className="w-12 h-12 rounded-lg bg-slate-700/80 hover:bg-slate-600 border border-slate-600 hover:border-cyan-400 text-white font-bold text-base transition-all shadow-md hover:shadow-cyan-500/20"
            >
              {key}
            </motion.button>
          ))}
        </div>
      ))}
      
      {/* Bottom row with Space and Backspace */}
      <div className="flex justify-center gap-2">
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={onBackspace}
          className="w-20 h-12 rounded-lg bg-red-600/80 hover:bg-red-500 border border-red-500 hover:border-red-400 text-white font-bold transition-all shadow-md hover:shadow-red-500/20 flex items-center justify-center"
        >
          <Delete className="w-5 h-5" />
        </motion.button>
        
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={onSpace}
          className="flex-1 max-w-md h-12 rounded-lg bg-slate-700/80 hover:bg-slate-600 border border-slate-600 hover:border-cyan-400 text-white font-semibold text-sm transition-all shadow-md hover:shadow-cyan-500/20"
        >
          ESPACE
        </motion.button>
      </div>
    </div>
  );
}