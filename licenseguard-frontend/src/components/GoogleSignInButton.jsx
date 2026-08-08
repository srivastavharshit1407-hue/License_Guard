/**
 * Renders Google's official button and hands the resulting ID token to the API.
 *
 * The <script src="https://accounts.google.com/gsi/client"> tag in index.html
 * defines window.google. It loads async, so we poll briefly before giving up
 * rather than assuming it is ready on first render.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { readError } from '../lib/api'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function GoogleSignInButton({ onError }) {
  const divRef = useRef(null)
  const navigate = useNavigate()
  const { loginWithGoogle } = useAuth()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!CLIENT_ID) return
    let tries = 0
    const timer = setInterval(() => {
      if (window.google?.accounts?.id) {
        clearInterval(timer)
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: async ({ credential }) => {
            try {
              await loginWithGoogle(credential)
              navigate('/dashboard')
            } catch (error) {
              onError?.(readError(error, 'Google sign-in failed.'))
            }
          },
        })
        window.google.accounts.id.renderButton(divRef.current, {
          theme: 'outline', size: 'large', width: 320, text: 'continue_with',
        })
        setReady(true)
      } else if (++tries > 40) {
        clearInterval(timer)
      }
    }, 100)
    return () => clearInterval(timer)
  }, [loginWithGoogle, navigate, onError])

  if (!CLIENT_ID) {
    return (
      <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
        Set <code className="font-mono">VITE_GOOGLE_CLIENT_ID</code> in <code className="font-mono">.env</code> to enable Google SSO.
      </p>
    )
  }

  return (
    <div className="flex justify-center">
      <div ref={divRef} />
      {!ready && <div className="h-10 w-full animate-pulse rounded-lg bg-ink-100" />}
    </div>
  )
}
