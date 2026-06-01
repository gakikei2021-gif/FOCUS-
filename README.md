import { useState, useEffect, useRef, useCallback } from "react";
import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Shield, X, Maximize, Clock, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const queryClient = new QueryClient();

type ScreenState = 'setup' | 'focus';

interface AppState {
  screen: ScreenState;
  durationMinutes: number;
  password: "";
}

function Home() {
  const [screen, setScreen] = useState<ScreenState>('setup');
  const [durationMinutes, setDurationMinutes] = useState<number>(45);
  const [password, setPassword] = useState("");
  const [sessionPassword, setSessionPassword] = useState("");
  const [timeLeft, setTimeLeft] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);

  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [exitPassword, setExitPassword] = useState("");
  const [shake, setShake] = useState(false);
  const [exitError, setExitError] = useState("");

  const durations = [25, 45, 60, 90];

  const handleStartSession = () => {
    if (password.length < 4) return;
    setSessionPassword(password);
    setTimeLeft(durationMinutes * 60);
    setSessionComplete(false);
    setScreen('focus');
  };

  const elapsedSeconds = durationMinutes * 60 - timeLeft;
  const canExit = elapsedSeconds >= 300; // locked for first 5 minutes

  const handleExitAttempt = () => {
    if (!canExit && !sessionComplete) return;
    if (sessionComplete) {
      exitFocusMode();
      return;
    }
    setIsPasswordModalOpen(true);
    setExitPassword("");
    setExitError("");
  };

  const verifyExitPassword = () => {
    if (exitPassword === sessionPassword) {
      setIsPasswordModalOpen(false);
      exitFocusMode();
    } else {
      setExitError("Wrong password — stay focused!");
      setShake(true);
      setTimeout(() => setShake(false), 400);
    }
  };

  const exitFocusMode = () => {
    setScreen('setup');
    setPassword("");
    setSessionPassword("");
  };

  useEffect(() => {
    if (screen === 'focus') {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          if (canExit || sessionComplete) handleExitAttempt();
        }
      };
      const handleContextMenu = (e: MouseEvent) => e.preventDefault();
      window.addEventListener("keydown", handleKeyDown);
      window.addEventListener("contextmenu", handleContextMenu);
      return () => {
        window.removeEventListener("keydown", handleKeyDown);
        window.removeEventListener("contextmenu", handleContextMenu);
      };
    }
  }, [screen, sessionComplete]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (screen === 'focus' && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            setSessionComplete(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [screen, timeLeft]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <AnimatePresence mode="wait">
      {screen === 'setup' ? (
        <motion.div
          key="setup"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4, ease: "easeInOut" }}
          className="min-h-screen w-full flex items-center justify-center bg-background p-4 sm:p-8"
        >
          <div className="w-full max-w-md bg-card/50 backdrop-blur-xl border border-white/5 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-primary opacity-50" />
            <div className="text-center mb-10">
              <div className="inline-flex items-center justify-center p-3 rounded-full bg-primary/10 mb-4">
                <Shield className="w-8 h-8 text-primary" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Desk Guard</h1>
              <p className="text-muted-foreground">Set your parameters. Lock in. Do the work.</p>
            </div>
            <div className="space-y-8">
              <div className="space-y-4">
                <Label className="text-sm font-medium text-white/80 uppercase tracking-wider flex items-center gap-2">
                  <Clock className="w-4 h-4" /> Session Duration
                </Label>
                <div className="grid grid-cols-4 gap-2">
                  {durations.map((mins) => (
                    <Button
                      key={mins}
                      variant={durationMinutes === mins ? "default" : "outline"}
                      className={cn("h-12", durationMinutes === mins ? "bg-primary text-white hover:bg-primary/90" : "bg-white/5 border-white/10 hover:bg-white/10 text-white")}
                      onClick={() => setDurationMinutes(mins)}
                    >
                      {mins}m
                    </Button>
                  ))}
                </div>
                <div className="flex items-center gap-4 mt-4">
                  <span className="text-sm text-muted-foreground shrink-0">Custom (mins):</span>
                  <Input
                    type="number"
                    min={1}
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(Math.max(1, parseInt(e.target.value) || 1))}
                    className="bg-black/20 border-white/10 text-white focus-visible:ring-primary"
                  />
                </div>
              </div>
              <div className="space-y-4">
                <Label className="text-sm font-medium text-white/80 uppercase tracking-wider flex items-center gap-2">
                  <Lock className="w-4 h-4" /> Exit Password
                </Label>
                <p className="text-xs text-muted-foreground mb-2">To prevent you from quitting easily. Minimum 4 characters.</p>
                <Input
                  type="password"
                  placeholder="e.g. im-not-quitting"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-black/20 border-white/10 text-white h-12 focus-visible:ring-primary"
                  data-testid="password-input"
                />
              </div>
              <Button
                onClick={handleStartSession}
                disabled={password.length < 4}
                className="w-full h-14 text-lg font-medium bg-white text-black hover:bg-white/90 disabled:opacity-50 transition-all rounded-xl"
                data-testid="start-button"
              >
                Start Focus Session
              </Button>
            </div>
          </div>
        </motion.div>
      ) : (
        <motion.div
          key="focus"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
          className="fixed inset-0 w-full h-full overflow-hidden flex items-center justify-center aurora-bg"
        >
          <div className="absolute inset-0 opacity-[0.03] pointer-events-none mix-blend-overlay" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.65\' numOctaves=\'3\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")' }} />
          <div className="relative z-10 w-full max-w-lg p-12 bg-black/30 backdrop-blur-2xl border border-white/5 rounded-3xl shadow-2xl flex flex-col items-center text-center">
            {
            
