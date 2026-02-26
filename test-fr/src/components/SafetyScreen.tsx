import { useState } from 'react';
import { AlertTriangle, Hand, ShieldAlert, CircleStop, CheckCircle, ArrowLeft } from 'lucide-react';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Card } from './ui/card';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import robotImage1 from './images/1.jpg';
import robotImage2 from './images/2.jpg';
import robotImage3 from './images/3.jpg';

interface SafetyScreenProps {
  onContinue: () => void;
  onBack: () => void;
}

export function SafetyScreen({ onContinue, onBack }: SafetyScreenProps) {
  const [hasAccepted, setHasAccepted] = useState(false);

  const safetyRules = [
    {
      icon: Hand,
      title: "Zone d'exclusion",
      description: "Ne jamais placer vos mains sur l'échiquier lorsque le bras est en mouvement.",
      color: "from-red-500 to-orange-500",
      iconBg: "bg-red-500/10",
      iconColor: "text-red-500"
    },
    {
      icon: ShieldAlert,
      title: "Interférence",
      description: "Merci de ne pas empêcher le robot de jouer ou de bloquer sa trajectoire.",
      color: "from-orange-500 to-yellow-500",
      iconBg: "bg-orange-500/10",
      iconColor: "text-orange-500"
    },
    {
      icon: CircleStop,
      title: "Arrêt d'urgence",
      description: "Repérez le bouton d'arrêt d'urgence physique avant de commencer.",
      color: "from-yellow-500 to-amber-500",
      iconBg: "bg-yellow-500/10",
      iconColor: "text-yellow-500"
    }
  ];

  return (
    <div className="h-screen flex items-center justify-center p-4 overflow-auto">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="absolute top-4 left-4 flex items-center gap-2 text-slate-400 hover:text-white transition-colors group z-10"
      >
        <div className="w-9 h-9 rounded-full bg-slate-800/50 backdrop-blur-sm border border-slate-700 flex items-center justify-center group-hover:border-cyan-400 transition-all shadow-lg">
          <ArrowLeft className="w-4 h-4" />
        </div>
        <span className="font-medium text-sm">Retour</span>
      </button>

      <div className="max-w-5xl w-full my-8">
        {/* Titre */}
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-2 mb-2">
            <AlertTriangle className="w-8 h-8 text-yellow-500" strokeWidth={2} />
            <h1 className="text-3xl font-bold text-white">
              Consignes de Sécurité
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Veuillez lire attentivement les consignes avant de continuer
          </p>
        </div>

        {/* Cartes d'avertissement */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {safetyRules.map((rule, index) => {
            const Icon = rule.icon;
            const images = [robotImage1, robotImage2, robotImage3];
            return (
              <Card 
                key={index}
                className="p-4 bg-slate-800/50 border-slate-700 hover:border-slate-600 transition-all duration-300"
              >
                {/* Image pour chaque carte - Taille fixe et carrée */}
                <div className="w-40 h-40 mx-auto bg-slate-900/80 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                  <img 
                    src={images[index]} 
                    alt={`${rule.title} - Robot UR7e`}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex items-center justify-center gap-2 mb-2">
                  <div className={`w-8 h-8 rounded-lg ${rule.iconBg} flex items-center justify-center`}>
                    <Icon className={`w-4 h-4 ${rule.iconColor}`} strokeWidth={2} />
                  </div>
                  <h3 className="text-xl font-bold text-white">{rule.title}</h3>
                </div>
                <p className="text-slate-400 text-base leading-relaxed text-center">{rule.description}</p>
              </Card>
            );
          })}
        </div>

        {/* Engagement */}
        <Alert className="mb-5 bg-slate-800/50 border-slate-600 py-3">
          <AlertTriangle className="h-4 w-4 text-yellow-500 flex-shrink-0" />
          <AlertTitle className="text-white text-sm">Important</AlertTitle>
          <AlertDescription className="text-slate-300 text-xs">
            Votre sécurité est notre priorité. En cochant la case ci-dessous, vous reconnaissez avoir pris connaissance des consignes et vous engagez à les respecter pendant toute la durée de votre partie.
          </AlertDescription>
        </Alert>

        {/* Case à cocher */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 mb-5">
          <div className="flex items-start gap-3">
            <Checkbox 
              id="safety-agreement"
              checked={hasAccepted}
              onCheckedChange={(checked) => setHasAccepted(checked === true)}
              className="mt-0.5 data-[state=checked]:bg-cyan-500 data-[state=checked]:border-cyan-500 flex-shrink-0"
            />
            <label 
              htmlFor="safety-agreement" 
              className="text-sm text-slate-200 cursor-pointer select-none flex-1"
            >
              J'ai lu les consignes de sécurité et je m'engage à les respecter pendant toute la durée de ma partie avec le robot UR7e.
            </label>
          </div>
        </div>

        {/* Bouton Continuer */}
        <div className="flex justify-center">
          <Button
            onClick={onContinue}
            disabled={!hasAccepted}
            size="lg"
            className={`
              px-8 py-5 rounded-xl text-base font-bold
              transition-all duration-300
              ${hasAccepted 
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-2xl shadow-cyan-500/50 hover:shadow-cyan-400/60 hover:scale-105' 
                : 'bg-slate-700 text-slate-500 cursor-not-allowed'
              }
              border-0
            `}
          >
            {hasAccepted ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Continuer
              </>
            ) : (
              'Veuillez accepter les consignes'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}