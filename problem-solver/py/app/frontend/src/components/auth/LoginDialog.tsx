import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { LogIn, Mail, Lock, Loader2 } from 'lucide-react';

// Keycloak config (same as AuthApp.tsx)
const KEYCLOAK_BASE = (import.meta.env.VITE_KEYCLOAK_BASE as string) || 'http://localhost:8081';
const REALM = (import.meta.env.VITE_KEYCLOAK_REALM as string) || 'ostis-ann';
const CLIENT_ID = (import.meta.env.VITE_KEYCLOAK_CLIENT_ID as string) || 'spa-client';
const REDIRECT_URI = (import.meta.env.VITE_REDIRECT_URI as string) || (window.location.origin + '/auth/callback');
const AUTH_ENDPOINT = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/auth`;

// PKCE helpers (from AuthApp.tsx)
function base64UrlEncode(arrayBuffer: ArrayBuffer): string {
  const bytes = new Uint8Array(arrayBuffer);
  let str = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    str += String.fromCharCode(bytes[i]);
  }
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function sha256(buffer: string) {
  return await crypto.subtle.digest('SHA-256', new TextEncoder().encode(buffer));
}

async function generatePKCECodes() {
  const rand = crypto.getRandomValues(new Uint8Array(64));
  const verifier = Array.from(rand).map(b => (b % 36).toString(36)).join('');
  const digest = await sha256(verifier);
  const challenge = base64UrlEncode(digest);
  return { verifier, challenge };
}

function buildAuthUrl({ code_challenge, scope = 'openid profile email', extraParams = {} as Record<string, string> } = {} as any) {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope,
    code_challenge_method: 'S256',
    code_challenge,
    prompt: 'consent'
  });
  Object.entries(extraParams).forEach(([k, v]) => params.set(k, v));
  return `${AUTH_ENDPOINT}?${params.toString()}`;
}

interface LoginDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const LoginDialog: React.FC<LoginDialogProps> = ({ open, onOpenChange }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleKeycloakLogin = async () => {
    setIsLoading(true);
    try {
      const { verifier, challenge } = await generatePKCECodes();
      sessionStorage.setItem('pkce_verifier', verifier);
      const url = buildAuthUrl({ code_challenge: challenge });
      window.location.href = url;
    } catch (error) {
      console.error('Login error:', error);
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    try {
      const { verifier, challenge } = await generatePKCECodes();
      sessionStorage.setItem('pkce_verifier', verifier);
      const url = buildAuthUrl({
        code_challenge: challenge,
        extraParams: { kc_idp_hint: 'google' }
      });
      window.location.href = url;
    } catch (error) {
      console.error('Google login error:', error);
      setIsLoading(false);
    }
  };

  // Handle callback from Keycloak
  useEffect(() => {
    const url = new URL(window.location.href);
    const code = url.searchParams.get('code');
    if (code) {
      // This will be handled by AuthApp.tsx callback handler
      onOpenChange(false);
    }
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-2xl">Вход в систему</DialogTitle>
          <DialogDescription>
            Выберите способ входа для доступа к платформе
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Keycloak Login Button */}
          <Button
            onClick={handleKeycloakLogin}
            disabled={isLoading}
            className="w-full"
            size="lg"
          >
            {isLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <LogIn className="mr-2 h-4 w-4" />
            )}
            Войти через Keycloak
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator className="w-full" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                или
              </span>
            </div>
          </div>

          {/* Google Login Button */}
          <Button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            variant="outline"
            className="w-full"
            size="lg"
          >
            {isLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            )}
            Войти через Google
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LoginDialog;