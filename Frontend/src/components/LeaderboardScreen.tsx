import { ArrowLeft, Trophy, Medal, Award, TrendingDown } from 'lucide-react';
import { useState, useEffect } from 'react';

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

  // Charger et calculer le classement depuis localStorage
  useEffect(() => {
    const leaderboardData = localStorage.getItem('chessLeaderboard');
    if (!leaderboardData) {
      setLeaderboard([]);
      return;
    }

    const games = JSON.parse(leaderboardData);
    
    // Grouper par joueur et calculer les statistiques
    const playerStats: { [name: string]: { 
      totalAcpl: number; 
      count: number;
      wins: number;
      losses: number;
      abandoned: number;
    } } = {};
    
    games.forEach((game: any) => {
      if (!playerStats[game.playerName]) {
        playerStats[game.playerName] = { 
          totalAcpl: 0, 
          count: 0,
          wins: 0,
          losses: 0,
          abandoned: 0
        };
      }
      playerStats[game.playerName].totalAcpl += game.acpl;
      playerStats[game.playerName].count += 1;
      
      // Compter les résultats
      if (game.result === 'win') playerStats[game.playerName].wins += 1;
      else if (game.result === 'lose') playerStats[game.playerName].losses += 1;
      else if (game.result === 'abandoned') playerStats[game.playerName].abandoned += 1;
    });

    // Créer le tableau de classement
    const rankings: PlayerScore[] = Object.entries(playerStats)
      .map(([name, stats]) => ({
        rank: 0,
        name,
        acpl: Math.round(stats.totalAcpl / stats.count),
        games: stats.count,
        wins: stats.wins,
        losses: stats.losses,
        abandoned: stats.abandoned
      }))
      .sort((a, b) => a.acpl - b.acpl) // Trier par ACPL croissant (plus bas = meilleur)
      .map((player, index) => ({ ...player, rank: index + 1 }));

    setLeaderboard(rankings);
  }, []);
  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Trophy className="w-6 h-6 text-yellow-400" />;
      case 2:
        return <Medal className="w-6 h-6 text-slate-300" />;
      case 3:
        return <Award className="w-6 h-6 text-amber-600" />;
      default:
        return <span className="text-slate-500 font-bold text-lg">{rank}</span>;
    }
  };

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/30';
      case 2:
        return 'bg-gradient-to-r from-slate-400/20 to-slate-500/20 border-slate-400/30';
      case 3:
        return 'bg-gradient-to-r from-amber-600/20 to-orange-600/20 border-amber-600/30';
      default:
        return 'bg-slate-800/30 border-slate-700/50';
    }
  };

  const getACPLColor = (acpl: number) => {
    if (acpl <= 20) return 'text-green-400';
    if (acpl <= 40) return 'text-cyan-400';
    if (acpl <= 60) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getACPLLabel = (acpl: number) => {
    if (acpl <= 20) return 'Excellent';
    if (acpl <= 40) return 'Très bon';
    if (acpl <= 60) return 'Bon';
    return 'Correct';
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group"
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
            <div className="relative">
              <div className="absolute inset-0 bg-yellow-500 blur-xl opacity-50"></div>
              <Trophy className="w-14 h-14 text-yellow-400 relative" strokeWidth={1.5} />
            </div>
            <h1 className="text-5xl font-bold bg-gradient-to-r from-yellow-400 via-amber-400 to-orange-400 bg-clip-text text-transparent">
              Classement
            </h1>
          </div>
          <p className="text-xl text-slate-400 mb-4">
            Les meilleurs joueurs face au robot UR7e
          </p>
          <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg px-4 py-2">
            <TrendingDown className="w-4 h-4 text-cyan-400" />
            <span className="text-cyan-400 text-sm font-medium">
              Score ACPL : Plus bas = Meilleur
            </span>
          </div>
        </div>

        {/* Info ACPL */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700 mb-6">
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <div className="w-8 h-8 bg-cyan-500/20 rounded-lg flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-cyan-400" />
            </div>
            Qu'est-ce que l'ACPL ?
          </h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            <span className="text-white font-semibold">ACPL (Average Centipawn Loss)</span> mesure la perte moyenne par coup 
            par rapport au meilleur coup possible selon Stockfish. Un score de <span className="text-green-400">0</span> signifierait 
            que vous jouez parfaitement. En pratique, un score inférieur à <span className="text-green-400">20</span> est excellent, 
            et inférieur à <span className="text-cyan-400">40</span> est très bon.
          </p>
        </div>

        {/* Leaderboard Table */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 px-6 py-4 bg-slate-900/50 border-b border-slate-700 text-slate-400 text-sm font-semibold">
            <div className="col-span-1 text-center">Rang</div>
            <div className="col-span-4">Joueur</div>
            <div className="col-span-2 text-center">Score ACPL</div>
            <div className="col-span-2 text-center">Parties</div>
            <div className="col-span-3 text-center">V / D / A</div>
          </div>

          {/* Table Body */}
          <div className="divide-y divide-slate-700/50">
            {leaderboard.length > 0 ? (
              leaderboard.map((player) => (
                <div
                  key={player.rank}
                  className={`grid grid-cols-12 gap-4 px-6 py-4 items-center transition-all hover:bg-slate-700/30 ${getRankBg(player.rank)} border-l-4`}
                >
                  {/* Rank */}
                  <div className="col-span-1 flex justify-center">
                    <div className="w-10 h-10 flex items-center justify-center">
                      {getRankIcon(player.rank)}
                    </div>
                  </div>

                  {/* Name */}
                  <div className="col-span-4">
                    <p className="text-white font-semibold text-lg">{player.name}</p>
                  </div>

                  {/* ACPL Score */}
                  <div className="col-span-2 text-center">
                    <div className="inline-flex flex-col items-center">
                      <span className={`text-2xl font-bold ${getACPLColor(player.acpl)}`}>
                        {player.acpl}
                      </span>
                      <span className="text-xs text-slate-500 mt-1">
                        {getACPLLabel(player.acpl)}
                      </span>
                    </div>
                  </div>

                  {/* Games Played */}
                  <div className="col-span-2 text-center">
                    <span className="text-slate-300 font-medium">{player.games}</span>
                    <span className="text-slate-500 text-sm ml-1">parties</span>
                  </div>

                  {/* Win / Loss / Abandoned */}
                  <div className="col-span-3 text-center">
                    <div className="flex items-center justify-center gap-3 text-sm">
                      <span className="text-green-400 font-semibold">{player.wins}</span>
                      <span className="text-slate-600">/</span>
                      <span className="text-red-400 font-semibold">{player.losses}</span>
                      <span className="text-slate-600">/</span>
                      <span className="text-orange-400 font-semibold">{player.abandoned}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Victoires / Défaites / Abandons
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-16 text-center">
                <Trophy className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 text-lg font-medium mb-2">
                  Aucune partie enregistrée
                </p>
                <p className="text-slate-500 text-sm">
                  Soyez le premier à jouer et à figurer dans le classement !
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer Note */}
        <div className="mt-6 text-center">
          <p className="text-slate-500 text-sm">
            Le classement est calculé sur la moyenne des 5 dernières parties de chaque joueur
          </p>
        </div>
      </div>
    </div>
  );
}
