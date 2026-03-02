import { useState, useEffect } from 'react';
import { Lock, Unlock, Star, Trash2, Download, RefreshCw, ArrowLeft, UserCircle, Calendar, Clock, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface FeedbackLogsScreenProps {
  onBack: () => void;
}

interface FeedbackEntry {
  id: string;
  rating: number;
  comment: string;
  timestamp: string;
  playerName?: string;
  difficulty?: string;
}

const API_BASE = `http://${window.location.hostname}:8000`;

export function FeedbackLogsScreen({ onBack }: FeedbackLogsScreenProps) {
  const [pin, setPin] = useState(['', '', '', '']);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [error, setError] = useState('');
  
  const [feedbacks, setFeedbacks] = useState<FeedbackEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    total: 0,
    average: 0,
    distribution: [0, 0, 0, 0, 0] // 1 to 5 stars
  });

  const CORRECT_PIN = '0000';

  // Load feedbacks when unlocked
  useEffect(() => {
    if (isUnlocked) {
      loadFeedbacks();
    }
  }, [isUnlocked]);

  const loadFeedbacks = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/feedback/logs`);
      const data = await res.json();
      
      if (data.feedbacks) {
        setFeedbacks(data.feedbacks);
        calculateStats(data.feedbacks);
      } else {
        setFeedbacks([]);
        calculateStats([]);
      }
    } catch (err) {
      console.log('API non disponible - Mode local');
      // Initialize with empty data when API is not available
      setFeedbacks([]);
      calculateStats([]);
    }
    setLoading(false);
  };

  const calculateStats = (data: FeedbackEntry[]) => {
    if (data.length === 0) {
      setStats({ total: 0, average: 0, distribution: [0, 0, 0, 0, 0] });
      return;
    }

    const distribution = [0, 0, 0, 0, 0];
    let sum = 0;

    data.forEach(fb => {
      sum += fb.rating;
      distribution[fb.rating - 1]++;
    });

    setStats({
      total: data.length,
      average: sum / data.length,
      distribution
    });
  };

  const generateMockFeedbacks = (): FeedbackEntry[] => {
    return [];
  };

  const handlePinChange = (index: number, value: string) => {
    if (value.length > 1) return;
    if (value && !/^\d$/.test(value)) return;

    const newPin = [...pin];
    newPin[index] = value;
    setPin(newPin);
    setError('');

    // Auto-focus next input
    if (value && index < 3) {
      const nextInput = document.getElementById(`feedback-pin-${index + 1}`);
      nextInput?.focus();
    }

    // Check PIN when all 4 digits are entered
    if (newPin.every(digit => digit !== '')) {
      const enteredPin = newPin.join('');
      if (enteredPin === CORRECT_PIN) {
        setTimeout(() => {
          setIsUnlocked(true);
        }, 300);
      } else {
        setError('Code incorrect');
        setTimeout(() => {
          setPin(['', '', '', '']);
          document.getElementById('feedback-pin-0')?.focus();
        }, 1000);
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !pin[index] && index > 0) {
      const prevInput = document.getElementById(`feedback-pin-${index - 1}`);
      prevInput?.focus();
    }
  };

  const handleResetLogs = async () => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer tous les feedbacks ?')) return;
    
    try {
      await fetch(`${API_BASE}/feedback/reset`, { method: 'POST' });
      setFeedbacks([]);
      setStats({ total: 0, average: 0, distribution: [0, 0, 0, 0, 0] });
    } catch (err) {
      console.error('Error resetting feedbacks:', err);
    }
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(feedbacks, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feedbacks-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStarPercentage = (starCount: number) => {
    if (stats.total === 0) return 0;
    return (stats.distribution[starCount - 1] / stats.total) * 100;
  };

  return (
    <div className="h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-4 left-4 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-30"
      >
        <div className="w-9 h-9 rounded-full bg-slate-800/50 backdrop-blur-sm border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all shadow-lg">
          <ArrowLeft className="w-4 h-4" />
        </div>
        <span className="font-medium text-sm">Retour</span>
      </button>

      {/* Main Content (blurred when locked) */}
      <div className={`max-w-6xl w-full transition-all duration-500 ${!isUnlocked ? 'blur-sm pointer-events-none select-none' : ''}`}>
        <div className="mb-6 text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-xl shadow-purple-500/20">
            <MessageSquare className="w-8 h-8 text-white" strokeWidth={2} />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">
            Journal des Feedbacks
          </h1>
          <p className="text-slate-400">
            Consultation des avis et statistiques des parties
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Total Feedbacks */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Total des avis</span>
              <MessageSquare className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="text-3xl font-bold text-white">{stats.total}</div>
          </div>

          {/* Average Rating */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Moyenne</span>
              <Star className="w-5 h-5 text-yellow-400" fill="currentColor" />
            </div>
            <div className="flex items-center gap-2">
              <div className="text-3xl font-bold text-white">
                {stats.average.toFixed(1)}
              </div>
              <div className="text-slate-400 text-sm">/ 5</div>
            </div>
          </div>

          {/* Distribution */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-3">
              <span className="text-slate-400 text-sm font-medium">Répartition</span>
              <Star className="w-5 h-5 text-yellow-400" />
            </div>
            <div className="space-y-1.5">
              {[5, 4, 3, 2, 1].map(stars => (
                <div key={stars} className="flex items-center gap-2">
                  <div className="flex items-center gap-1 min-w-[60px]">
                    <span className="text-xs text-slate-400 font-medium">{stars}</span>
                    <Star className="w-3 h-3 text-yellow-400" fill="currentColor" />
                  </div>
                  <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-yellow-400 to-amber-500 rounded-full transition-all"
                      style={{ width: `${getStarPercentage(stars)}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-400 min-w-[40px] text-right">
                    {stats.distribution[stars - 1]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mb-6 justify-center">
          <button
            onClick={loadFeedbacks}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-cyan-400 text-white text-sm font-medium transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
          
          <button
            onClick={handleExport}
            disabled={feedbacks.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600 hover:border-green-400 text-white text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            Exporter JSON
          </button>
          
          <button
            onClick={handleResetLogs}
            disabled={feedbacks.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 hover:border-red-400 text-red-300 text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-4 h-4" />
            Réinitialiser
          </button>
        </div>

        {/* Feedbacks List */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-xl font-bold text-white">Liste des avis</h2>
          </div>
          
          <div className="max-h-[400px] overflow-y-auto">
            {feedbacks.length === 0 ? (
              <div className="p-12 text-center">
                <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">Aucun feedback enregistré</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-700">
                {feedbacks.map((feedback) => (
                  <div key={feedback.id} className="p-4 hover:bg-slate-700/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      {/* Left: Player info and rating */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                            <UserCircle className="w-6 h-6 text-white" />
                          </div>
                          <div>
                            <div className="font-semibold text-white">
                              {feedback.playerName || 'Anonyme'}
                            </div>
                            {feedback.difficulty && (
                              <div className="text-xs text-slate-400">
                                Difficulté: {feedback.difficulty}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {/* Rating */}
                        <div className="flex items-center gap-1 mb-2">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Star
                              key={star}
                              className={`w-4 h-4 ${
                                star <= feedback.rating
                                  ? 'text-yellow-400 fill-yellow-400'
                                  : 'text-slate-600'
                              }`}
                            />
                          ))}
                          <span className="ml-2 text-sm font-medium text-slate-400">
                            {feedback.rating}/5
                          </span>
                        </div>
                        
                        {/* Comment */}
                        {feedback.comment && (
                          <p className="text-slate-300 text-sm leading-relaxed">
                            "{feedback.comment}"
                          </p>
                        )}
                      </div>
                      
                      {/* Right: Date and time */}
                      <div className="text-right text-xs text-slate-400 flex-shrink-0">
                        <div className="flex items-center gap-1 justify-end mb-1">
                          <Calendar className="w-3 h-3" />
                          <span>{formatDate(feedback.timestamp)}</span>
                        </div>
                        <div className="flex items-center gap-1 justify-end">
                          <Clock className="w-3 h-3" />
                          <span>{formatTime(feedback.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* PIN Overlay */}
      <AnimatePresence>
        {!isUnlocked && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 flex items-center justify-center z-20 bg-slate-900/80 backdrop-blur-md"
          >
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="text-center"
            >
              <div className="mb-6">
                <div className="relative inline-block">
                  <div className="absolute inset-0 bg-purple-500 blur-3xl opacity-40 animate-pulse"></div>
                  <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full mx-auto mb-4 flex items-center justify-center shadow-2xl shadow-purple-500/50 relative">
                    <UserCircle className="w-12 h-12 text-white" strokeWidth={2} />
                  </div>
                </div>
                <h1 className="text-3xl font-bold text-white mb-2">
                  Accès Superviseur
                </h1>
                <p className="text-slate-400 text-base">
                  Entrez le code PIN pour consulter les feedbacks
                </p>
              </div>

              {/* PIN Input */}
              <div className="flex justify-center gap-3 mb-5">
                {pin.map((digit, index) => (
                  <motion.input
                    key={index}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.2 + index * 0.1 }}
                    id={`feedback-pin-${index}`}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handlePinChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    autoFocus={index === 0}
                    className={`w-14 h-16 text-center text-2xl font-bold rounded-xl border-2 bg-slate-800/70 text-white
                      transition-all duration-200 outline-none backdrop-blur-sm
                      ${error ? 'border-red-500 animate-shake' : 'border-slate-600 focus:border-purple-400 focus:shadow-lg focus:shadow-purple-500/30'}
                      ${digit ? 'border-purple-500 bg-slate-700/70' : ''}`}
                  />
                ))}
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-red-400 mb-3 font-semibold text-sm"
                >
                  {error}
                </motion.p>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}