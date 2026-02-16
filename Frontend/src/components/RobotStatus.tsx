import { Bot, Cpu, Activity, AlertCircle, WifiOff } from 'lucide-react';
import type { RobotStatus as RobotStatusType } from '../hooks/useChessRobot';

interface RobotStatusProps {
  status: RobotStatusType;
}

export function RobotStatus({ status }: RobotStatusProps) {
  const statusConfig = {
    idle: {
      label: 'En attente',
      color: 'text-slate-400',
      bgColor: 'bg-slate-700',
      icon: Bot,
      description: 'Le robot attend votre coup'
    },
    thinking: {
      label: 'Analyse',
      color: 'text-blue-400',
      bgColor: 'bg-blue-900/30',
      icon: Cpu,
      description: 'Calcul du meilleur coup'
    },
    moving: {
      label: 'En mouvement',
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-900/30',
      icon: Activity,
      description: 'Déplacement de la pièce'
    },
    error: {
      label: 'Erreur',
      color: 'text-red-400',
      bgColor: 'bg-red-900/30',
      icon: AlertCircle,
      description: 'Erreur détectée'
    },
    disconnected: {
      label: 'Déconnecté',
      color: 'text-orange-400',
      bgColor: 'bg-orange-900/30',
      icon: WifiOff,
      description: 'Connexion au serveur perdue'
    }
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2 text-sm">
        <div className="w-1 h-4 bg-cyan-400 rounded-full"></div>
        Robot UR7e
      </h3>

      <div className={`${config.bgColor} rounded-lg p-3 border border-slate-600`}>
        <div className="flex items-start gap-3">
          <div className={`${config.color}`}>
            <Icon className="w-6 h-6" strokeWidth={1.5} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className={`${config.color} font-bold`}>
                {config.label}
              </span>
              {status !== 'idle' && status !== 'error' && (
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse"></div>
                  <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                </div>
              )}
            </div>
            <p className="text-slate-400 text-xs">{config.description}</p>
          </div>
        </div>
      </div>

      {/* Robot Info */}
      <div className="mt-3 space-y-1 text-xs">
        <div className="flex justify-between text-slate-400">
          <span>Connexion</span>
          <span className="text-green-400 flex items-center gap-1">
            <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
            Connecté
          </span>
        </div>
        <div className="flex justify-between text-slate-400">
          <span>Précision</span>
          <span className="text-cyan-400 font-mono">±0.03mm</span>
        </div>
      </div>
    </div>
  );
}