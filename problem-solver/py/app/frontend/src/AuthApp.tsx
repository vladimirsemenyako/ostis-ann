import React, { useEffect, useState } from 'react'

type TokenResponse = {
  access_token: string
  expires_in?: number
  refresh_expires_in?: number
  refresh_token?: string
  token_type?: string
  id_token?: string
}

const KEYCLOAK_BASE = (import.meta.env.VITE_KEYCLOAK_BASE as string) || 'http://localhost:8081'
const REALM = (import.meta.env.VITE_KEYCLOAK_REALM as string) || 'demo'
const CLIENT_ID = (import.meta.env.VITE_KEYCLOAK_CLIENT_ID as string) || 'spa-client'
const REDIRECT_URI = (import.meta.env.VITE_REDIRECT_URI as string) || (window.location.origin + '/auth/callback')

const AUTH_ENDPOINT = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/auth`
const TOKEN_ENDPOINT = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/token`
const USERINFO_ENDPOINT = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/userinfo`
const LOGOUT_ENDPOINT = `${KEYCLOAK_BASE}/realms/${REALM}/protocol/openid-connect/logout`

function base64UrlEncode(arrayBuffer: ArrayBuffer): string {
  const bytes = new Uint8Array(arrayBuffer)
  let str = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    str += String.fromCharCode(bytes[i])
  }
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function sha256(buffer: string) {
  return await crypto.subtle.digest('SHA-256', new TextEncoder().encode(buffer))
}

async function generatePKCECodes() {
  const rand = crypto.getRandomValues(new Uint8Array(64))
  const verifier = Array.from(rand).map(b => (b % 36).toString(36)).join('')
  const digest = await sha256(verifier)
  const challenge = base64UrlEncode(digest)
  return { verifier, challenge }
}

function jwtDecode(token: string | undefined) {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const payload = parts[1]
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))

    return JSON.parse(decodeURIComponent(escape(json)))
  } catch (e) {
    return null
  }
}

function buildAuthUrl({ code_challenge, scope = 'openid profile email', extraParams = {} as Record<string,string> } = {} as any) {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope,
    code_challenge_method: 'S256',
    code_challenge,
    prompt: 'consent'
  })
  Object.entries(extraParams).forEach(([k, v]) => params.set(k, v))
  return `${AUTH_ENDPOINT}?${params.toString()}`
}

function toFormUrlEncoded(obj: Record<string, string>) {
  return Object.entries(obj).map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v)).join('&')
}

export default function AuthApp(): JSX.Element {
  const [status, setStatus] = useState<'initializing'|'ready'|'exchanging_code'|'authenticated'|'error'>('initializing')
  const [tokens, setTokens] = useState<TokenResponse | null>(() => {
    try { return JSON.parse(sessionStorage.getItem('kc_tokens') || 'null') as TokenResponse | null } catch { return null }
  })
  const [idTokenPayload, setIdTokenPayload] = useState<any>(() => tokens ? jwtDecode(tokens.id_token) : null)
  const [userinfo, setUserinfo] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const url = new URL(window.location.href)
    const code = url.searchParams.get('code')
    if (code) {
      setStatus('exchanging_code')
      const stored = sessionStorage.getItem('pkce_verifier')
      if (!stored) {
        setError('Missing PKCE verifier in sessionStorage. Start login again.')
        setStatus('error')
        return
      }
      const code_verifier = stored
      exchangeCodeForToken(code, code_verifier).then(tks => {
        sessionStorage.removeItem('pkce_verifier')
        sessionStorage.setItem('kc_tokens', JSON.stringify(tks))
        window.location.replace(window.location.origin + '/')
      }).catch(err => {
        console.error(err)
        setError('Token exchange failed: ' + (err.message || JSON.stringify(err)))
        setStatus('error')
      })
    } else {
      if (tokens) {
        setStatus('authenticated')
      } else {
        setStatus('ready')
      }
    }
  }, [])

  useEffect(() => {
    if (tokens) setIdTokenPayload(jwtDecode(tokens.id_token))
  }, [tokens])

  async function exchangeCodeForToken(code: string, code_verifier: string) {
    const body = toFormUrlEncoded({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier
    })
    const res = await fetch(TOKEN_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body
    })
    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`Token endpoint returned ${res.status}: ${txt}`)
    }
    return await res.json() as TokenResponse
  }

  async function refreshTokens() {
    if (!tokens?.refresh_token) {
      setError('No refresh token available')
      return
    }
    try {
      const body = toFormUrlEncoded({
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        refresh_token: tokens.refresh_token
      })
      const res = await fetch(TOKEN_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body
      })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(`Refresh failed ${res.status}: ${txt}`)
      }
      const newTokens = await res.json() as TokenResponse
      const merged = { ...tokens, ...newTokens }
      setTokens(merged)
      sessionStorage.setItem('kc_tokens', JSON.stringify(merged))
      setIdTokenPayload(jwtDecode(merged.id_token))
      setError(null)
    } catch (e: any) {
      console.error(e)
      setError('Refresh failed: ' + e.message)
    }
  }

  function startLogin({ idpHint }:{idpHint?:string} = {}) {
    generatePKCECodes().then(({ verifier, challenge }) => {
      sessionStorage.setItem('pkce_verifier', verifier)
      const extra: Record<string,string> = {}
      if (idpHint) extra.kc_idp_hint = idpHint
      const url = buildAuthUrl({ code_challenge: challenge, extraParams: extra })
      window.location.href = url
    })
  }

  function startRegister() {
    const params = new URLSearchParams({ client_id: CLIENT_ID, redirect_uri: REDIRECT_URI, kc_action: 'register' })
    window.location.href = `${AUTH_ENDPOINT}?${params.toString()}`
  }

  async function callUserinfo() {
    if (!tokens?.access_token) return setError('No access token')
    try {
      const res = await fetch(USERINFO_ENDPOINT, { headers: { Authorization: 'Bearer ' + tokens.access_token } })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setUserinfo(data)
      setError(null)
    } catch (e: any) {
      console.error(e)
      setError('userinfo error: ' + e.message)
    }
  }

  function logout() {
    const id_token_hint = tokens?.id_token
    sessionStorage.removeItem('kc_tokens')
    setTokens(null)
    setIdTokenPayload(null)
    setUserinfo(null)
    const params = new URLSearchParams({ id_token_hint: id_token_hint || '', post_logout_redirect_uri: window.location.origin })
    window.location.href = `${LOGOUT_ENDPOINT}?${params.toString()}`
  }

  const url = new URL(window.location.href)
  const code = url.searchParams.get('code')

  if (code || status === 'exchanging_code') {
    return null
  }

  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', padding: 20, maxWidth: 900, margin: '0 auto' }}>
      <h2>Authentication demo (Keycloak)</h2>
      <p style={{ color: '#666' }}>Keycloak: {KEYCLOAK_BASE}/realms/{REALM}</p>

      <div style={{ marginTop: 16 }}>
        {status === 'initializing' && <div>Initializing…</div>}
        {status === 'ready' && (
          <div>
            <button onClick={() => startLogin()} style={btnStyle}>Sign in with Keycloak (login form)</button>
            <button onClick={() => startLogin({ idpHint: 'google' })} style={{ ...btnStyle, marginLeft: 8 }}>Sign in with Google</button>
            <button onClick={() => startRegister()} style={{ ...btnStyle, marginLeft: 8 }}>Register</button>
          </div>
        )}

        {status === 'authenticated' && tokens && (
          <div style={{ marginTop: 12 }}>
            <div style={{ marginBottom: 8 }}><strong>Logged in</strong></div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={callUserinfo} style={btnStyle}>Call /userinfo</button>
              <button onClick={refreshTokens} style={btnStyle}>Refresh tokens</button>
              <button onClick={logout} style={{ ...btnStyle, background: '#f66' }}>Logout</button>
            </div>

            <section style={{ marginTop: 12 }}>
              <h3>Tokens (decoded ID token)</h3>
              <pre style={preStyle}>{JSON.stringify(idTokenPayload, null, 2)}</pre>
            </section>

            <section style={{ marginTop: 12 }}>
              <h3>/userinfo response</h3>
              <pre style={preStyle}>{JSON.stringify(userinfo, null, 2)}</pre>
            </section>

            <section style={{ marginTop: 12 }}>
              <h3>Raw tokens</h3>
              <details>
                <summary>Show tokens</summary>
                <pre style={preStyle}>{JSON.stringify(tokens, null, 2)}</pre>
              </details>
            </section>

          </div>
        )}

        {status === 'error' && (
          <div style={{ color: 'red' }}>
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      <section style={{ marginTop: 24 }}>
        <h3>How it works (short)</h3>
        <ol>
          <li>Click Sign in → browser redirects to Keycloak login (or Google via Keycloak broker).</li>
          <li>On success Keycloak redirects back with <code>code</code> to <code>{REDIRECT_URI}</code>.</li>
          <li>Component exchanges code + PKCE verifier for tokens and stores them in sessionStorage.</li>
          <li>Use access_token to call backend APIs or /userinfo.</li>
        </ol>
      </section>

      <section style={{ marginTop: 24, color: '#666' }}>
        <h4>Notes</h4>
        <ul>
          <li>Make sure the Keycloak client is <strong>Public</strong> and allows PKCE.</li>
          <li>Tokens are stored in <code>sessionStorage</code> (safer than localStorage for some threat models).</li>
          <li>For production use HTTPS and consider refresh token rotation and secure cookie storage.</li>
        </ul>
      </section>

    </div>
  )
}

const btnStyle: React.CSSProperties = { padding: '10px 14px', background: '#2563eb', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }
const preStyle: React.CSSProperties = { background: '#f6f8fa', padding: 12, borderRadius: 6, overflowX: 'auto' }
