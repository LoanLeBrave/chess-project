import { ArrowLeft, Trophy, Medal, Award, TrendingDown, RefreshCw } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';

interface LeaderboardScreenProps {
  onBack: () => void;
}


interface PlayerScore {
  rank: number;
  name: string;
  acpl: number;
  games: number;
  wins: number;
  losses: number;
  abandoned: number;
}

export function LeaderboardScreen({ onBack }: LeaderboardScreenProps) {
  const [leaderboard, setLeaderboard] = useState<PlayerScore[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

  // Fonction pour charger le classement (mémoire du robot ou local)
  const fetchLeaderboard = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // 1. Tenter de récupérer les données du serveur (Fichier JSON du robot)
      const res = await fetch(`${API_BASE}/leaderboard?limit=10`);
      const data = await res.json();
      
      if (data.leaderboard) {
        setLeaderboard(data.leaderboard.map((p: any) => ({
          rank: p.rank,
          name: p.name,
          acpl: Math.round(p.acpl),
          games: p.games,
          wins: p.wins,
          losses: p.losses,
          abandoned: p.abandoned,
        })));
      }
    } catch (error) {
      console.warn("API Leaderboard indisponible, lecture du stockage local...");
      
      // 2. Fallback LocalStorage si le robot est déconnecté
      const leaderboardData = localStorage.getItem('chessLeaderboard');
      if (!leaderboardData) {
        setLeaderboard([]);
      } else {
        const games = JSON.parse(leaderboardData);
        const playerStats: { [name: string]: any } = {};

        games.forEach((game: any) => {
          if (!playerStats[game.playerName]) {
            playerStats[game.playerName] = { totalAcpl: 0, count: 0, wins: 0, losses: 0, abandoned: 0 };
          }
          playerStats[game.playerName].totalAcpl += game.acpl;
          playerStats[game.playerName].count += 1;
          if (game.result === 'win') playerStats[game.playerName].wins += 1;
          else if (game.result === 'lose') playerStats[game.playerName].losses += 1;
          else if (game.result === 'abandoned') playerStats[game.playerName].abandoned += 1;
        });

        const rankings = Object.entries(playerStats)
          .map(([name, stats]: [string, any]) => ({
            rank: 0,
            name,
            acpl: Math.round(stats.totalAcpl / stats.count),
            games: stats.count,
            wins: stats.wins,
            losses: stats.losses,
            abandoned: stats.abandoned
          }))
          .sort((a, b) => a.acpl - b.acpl) // Meilleur ACPL en haut
          .slice(0, 10) // GARDER UNIQUEMENT LES 10 PREMIERS
          .map((player, index) => ({ ...player, rank: index + 1 }));

        setLeaderboard(rankings);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [API_BASE]);

  // Chargement initial + Rafraîchissement automatique toutes les 5 secondes
  useEffect(() => {
    fetchLeaderboard();
    const interval = setInterval(fetchLeaderboard, 5000); 
    return () => clearInterval(interval);
  }, [fetchLeaderboard]);

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1: return <Trophy className="w-6 h-6 text-yellow-400" />;
      case 2: return <Medal className="w-6 h-6 text-slate-300" />;
      case 3: return <Award className="w-6 h-6 text-amber-600" />;
      default: return <span className="text-slate-500 font-bold text-lg">{rank}</span>;
    }
  };

  const getRankBg = (rank: number) => {
    if (rank === 1) return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/30';
    if (rank === 2) return 'bg-gradient-to-r from-slate-400/20 to-slate-500/20 border-slate-400/30';
    if (rank === 3) return 'bg-gradient-to-r from-amber-600/20 to-orange-600/20 border-amber-600/30';
    return 'bg-slate-800/30 border-slate-700/50';
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-10"
      >
        <div className="w-10 h-10 rounded-full bg-slate-800/50 border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all">
          <ArrowLeft className="w-5 h-5" />
        </div>
        <span className="font-medium">Retour</span>
      </button>

      <div className="max-w-4xl w-full">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Trophy className="w-14 h-14 text-yellow-400" />
            <h1 className="text-5xl font-bold bg-gradient-to-r from-yellow-400 via-amber-400 to-orange-400 bg-clip-text text-transparent">
              Top 10 Junia
            </h1>
          </div>
          <p className="text-xl text-slate-400 mb-4">Les meilleurs cerveaux face au robot UR7e</p>
          <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg px-4 py-2 text-cyan-400 text-sm">
            <TrendingDown className="w-4 h-4" />
            <span>Score ACPL : Plus bas = Meilleur</span>
          </div>
        </div>

        {/* Bouton de rafraîchissement manuel discret */}
        <div className="absolute top-6 right-6">
          <RefreshCw className={`w-5 h-5 text-slate-500 ${isRefreshing ? 'animate-spin' : ''}`} />
        </div>

        {/* Tableau */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
          <div className="grid grid-cols-12 gap-4 px-6 py-4 bg-slate-900/50 border-b border-slate-700 text-slate-400 text-sm font-semibold text-center">
            <div className="col-span-1">Rang</div>
            <div className="col-span-4 text-left">Joueur</div>
            <div className="col-span-2">ACPL</div>
            <div className="col-span-2">Parties</div>
            <div className="col-span-3">V / D / A</div>
          </div>

          <div className="divide-y divide-slate-700/50">
            {leaderboard.length > 0 ? (
              leaderboard.map((player) => (
                <div
                  key={player.name}
                  className={`grid grid-cols-12 gap-4 px-6 py-4 items-center transition-all ${getRankBg(player.rank)} border-l-4`}
                >
                  <div className="col-span-1 flex justify-center">{getRankIcon(player.rank)}</div>
                  <div className="col-span-4 text-left text-white font-semibold text-lg">{player.name}</div>
                  <div className="col-span-2 text-center text-2xl font-bold text-cyan-400">{player.acpl}</div>
                  <div className="col-span-2 text-center text-slate-300">{player.games}</div>
                  <div className="col-span-3 text-center flex justify-center gap-2 text-sm font-mono">
                    <span className="text-green-400">{player.wins}W</span>
                    <span className="text-red-400">{player.losses}L</span>
                    <span className="text-orange-400">{player.abandoned}A</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-16 text-center text-slate-500">Aucun champion détecté pour le moment...</div>
            )}
          </div>
        </div>

        <div className="mt-6 text-center text-slate-500 text-sm">
          Fichier de données synchronisé en temps réel avec le robot. Seuls les 10 meilleurs scores sont affichés.
        </div>
      </div>
    </div>
  );
}