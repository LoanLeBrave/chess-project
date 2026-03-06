import { Delete } from 'lucide-react';
import { motion } from 'motion/react';

interface NumericKeypadProps {
  onKeyPress: (value: string) => void;
  onBackspace: () => void;
}

export function NumericKeypad({ onKeyPress, onBackspace }: NumericKeypadProps) {
  const keys = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['0']
  ];

  return (
    <div className="flex flex-col gap-2 select-none">
      {keys.map((row, rowIndex) => (
        <div key={rowIndex} className="flex justify-center gap-2">
          {row.map((key, keyIndex) => (
            <motion.button
              key={key}
              whileTap={{ scale: 0.95 }}
              onClick={() => onKeyPress(key)}
              className="w-14 h-12 rounded-lg bg-slate-700/80 hover:bg-slate-600 border border-slate-600 hover:border-cyan-400 text-white font-bold text-lg transition-all shadow-md hover:shadow-cyan-500/20"
            >
              {key}
            </motion.button>
          ))}
          {/* Backspace button on the last row */}
          {rowIndex === keys.length - 1 && (
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={onBackspace}
              className="w-14 h-12 rounded-lg bg-red-600/80 hover:bg-red-500 border border-red-500 hover:border-red-400 text-white font-bold transition-all shadow-md hover:shadow-red-500/20 flex items-center justify-center"
            >
              <Delete className="w-5 h-5" />
            </motion.button>
          )}
        </div>
      ))}
    </div>
  );
}
