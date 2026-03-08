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
    <div className="flex flex-col gap-3 select-none">
      {keys.map((row, rowIndex) => (
        <div key={rowIndex} className="flex justify-center gap-3">
          {row.map((key, keyIndex) => (
            <motion.button
              key={key}
              whileTap={{ scale: 0.95 }}
              onClick={() => onKeyPress(key)}
              className="w-20 h-16 rounded-xl bg-slate-700/80 hover:bg-slate-600 border-2 border-slate-600 hover:border-cyan-400 text-white font-bold text-2xl transition-all shadow-lg hover:shadow-cyan-500/30"
            >
              {key}
            </motion.button>
          ))}
          {/* Backspace button on the last row */}
          {rowIndex === keys.length - 1 && (
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={onBackspace}
              className="w-20 h-16 rounded-xl bg-red-600/80 hover:bg-red-500 border-2 border-red-500 hover:border-red-400 text-white font-bold transition-all shadow-lg hover:shadow-red-500/30 flex items-center justify-center"
            >
              <Delete className="w-6 h-6" />
            </motion.button>
          )}
        </div>
      ))}
    </div>
  );
}