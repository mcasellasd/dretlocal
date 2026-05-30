'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'

type HealthResponse = {
  status: string
  corpus_ready: boolean
  corpus_size: number
  openai_ready: boolean
  supabase_ready: boolean
}

type Citation = {
  id: string
  municipality: string
  document_title: string
  article_title?: string | null
  url?: string | null
  similarity?: number | null
  excerpt: string
}

type ChatResponse = {
  answer: string
  citations: Citation[]
  confidence: string
  territory: string
  refusal: boolean
}

type SearchHit = {
  id: string
  municipality: string
  document_title: string
  article_title?: string | null
  url?: string | null
  similarity?: number | null
  excerpt: string
}

type SearchResponse = {
  hits: SearchHit[]
}

type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const MUNICIPALITIES = [
  '',
  'Guils de Cerdanya',
  'Puigcerdà',
  'Bellver de Cerdanya',
  'Alp',
  'Bolvir',
  'Das',
  'Fontanals de Cerdanya',
  'Ger',
  'Isòvol',
  'Lles de Cerdanya',
  'Llívia',
  'Meranges',
  'Montellà i Martinet',
  'Prats i Sansor',
  'Riu de Cerdanya',
  'Urús',
]

const QUICK_PROMPTS = [
  'Quin regim hi ha per a llicencies urbanistiques?',
  'Quines taxes s’apliquen per a una activitat?',
  'Quins requisits hi ha per ocupar la via publica?',
]

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

function uid(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

export default function Page() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [question, setQuestion] = useState('Quin regim hi ha per a llicencies urbanistiques?')
  const [municipality, setMunicipality] = useState('Guils de Cerdanya')
  const [category, setCategory] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: uid('assistant'),
      role: 'assistant',
      content:
        'Soc el xat de Dret Local Cerdanya. Fes-me una pregunta sobre una norma municipal i et tornaré una resposta amb cites.',
    },
  ])
  const [citations, setCitations] = useState<Citation[]>([])
  const [searchHits, setSearchHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadHealth() {
      try {
        const response = await fetch(`${API_BASE}/health`)
        if (!response.ok) {
          throw new Error(`Health ${response.status}`)
        }
        const data = (await response.json()) as HealthResponse
        if (!cancelled) {
          setHealth(data)
          setHealthError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setHealthError(err instanceof Error ? err.message : "No s'ha pogut llegir l'estat del backend")
        }
      }
    }

    loadHealth()
    return () => {
      cancelled = true
    }
  }, [])

  const canSend = useMemo(() => question.trim().length > 0 && !loading, [loading, question])

  async function runSearch(query: string) {
    setSearching(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          municipality,
          category: category || null,
          limit: 5,
        }),
      })
      if (!response.ok) {
        throw new Error(`Search ${response.status}`)
      }
      const data = (await response.json()) as SearchResponse
      setSearchHits(data.hits)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error buscant')
    } finally {
      setSearching(false)
    }
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSend) return

    const cleanQuestion = question.trim()
    setLoading(true)
    setError(null)
    setMessages((current) => [...current, { id: uid('user'), role: 'user', content: cleanQuestion }])

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: cleanQuestion,
          municipality: municipality || null,
          category: category || null,
          messages: [],
        }),
      })

      if (!response.ok) {
        throw new Error(`Chat ${response.status}`)
      }

      const data = (await response.json()) as ChatResponse
      setMessages((current) => [...current, { id: uid('assistant'), role: 'assistant', content: data.answer }])
      setCitations(data.citations)
      void runSearch(cleanQuestion)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error consultant el xat')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <h1>Dret Local Cerdanya</h1>
            <p>Xat de consulta jurídica local amb cites, guardrails i focus territorial.</p>
          </div>
          <div className="status-row">
            <span className={`chip ${health?.corpus_ready ? 'ok' : 'warn'}`}>
              Corpus {health?.corpus_ready ? `llest (${health.corpus_size})` : 'pendent'}
            </span>
            <span className={`chip ${health?.supabase_ready ? 'ok' : 'warn'}`}>
              Supabase {health?.supabase_ready ? 'actiu' : 'off'}
            </span>
            <span className={`chip ${health?.openai_ready ? 'ok' : 'warn'}`}>
              OpenAI {health?.openai_ready ? 'actiu' : 'off'}
            </span>
          </div>
        </header>

        <section className="grid">
          <div className="panel">
            <div className="hero">
              <h2>Consulta normativa local sense soroll</h2>
              <p>
                Pregunta sobre ordenances, reglaments i normativa municipal de la Cerdanya. El sistema respon amb
                un to conservador, identificant si hi ha base suficient i mostrant les fonts recuperades.
              </p>
            </div>

            <div className="controls">
              <div className="field">
                <label htmlFor="municipality">Municipi</label>
                <select id="municipality" value={municipality} onChange={(event) => setMunicipality(event.target.value)}>
                  {MUNICIPALITIES.map((item) => (
                    <option key={item || 'all'} value={item}>
                      {item || 'Tots els municipis'}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="category">Categoria</label>
                <input
                  id="category"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  placeholder="urbanisme, fiscal, serveis..."
                />
              </div>
              <div className="field">
                <label htmlFor="search">Cerca ràpida</label>
                <input
                  id="search"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Escriu la consulta"
                />
              </div>
              <button className="primary-btn" onClick={() => void runSearch(question)} type="button" disabled={searching}>
                {searching ? 'Buscant...' : 'Buscar'}
              </button>
            </div>

            <div className="chat">
              <form className="composer" onSubmit={submitQuestion}>
                <div className="field">
                  <label htmlFor="question">Pregunta al xat</label>
                  <textarea
                    id="question"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Exemple: Quines llicencies urbanistiques calen per reformar un habitatge?"
                  />
                </div>

                <div className="inline-actions">
                  {QUICK_PROMPTS.map((prompt) => (
                    <button key={prompt} className="ghost-btn" type="button" onClick={() => setQuestion(prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>

                <div className="composer-row">
                  <button className="primary-btn" type="submit" disabled={!canSend}>
                    {loading ? 'Consultant...' : 'Enviar pregunta'}
                  </button>
                  <button
                    className="ghost-btn"
                    type="button"
                    onClick={() => {
                      setQuestion('')
                      setSearchHits([])
                      setCitations([])
                    }}
                  >
                    Netejar
                  </button>
                </div>
              </form>

              {error ? <div className="error">{error}</div> : null}

              <div className="thread" aria-live="polite">
                {messages.map((message) => (
                  <article key={message.id} className={`bubble ${message.role}`}>
                    <div className="bubble-meta">
                      <span>{message.role === 'user' ? 'Tu' : 'Dret Local Cerdanya'}</span>
                      <span>{message.role === 'assistant' ? 'Resposta' : 'Consulta'}</span>
                    </div>
                    {message.content}
                  </article>
                ))}
              </div>
            </div>
          </div>

          <aside className="side">
            <section className="panel">
              <h3 className="section-title">Estat del sistema</h3>
              {healthError ? <div className="error">{healthError}</div> : null}
              <div className="citation-list">
                <div className="card">
                  <strong>Corpus</strong>
                  <small>{health?.corpus_ready ? `${health.corpus_size} chunks carregats` : 'Esperant dades'}</small>
                </div>
                <div className="card">
                  <strong>Backend</strong>
                  <small>{health?.status || 'Sense resposta'}</small>
                </div>
                <div className="card">
                  <strong>Mode</strong>
                  <small>{health?.openai_ready ? 'Generació amb OpenAI' : 'Fallback local amb cites'}</small>
                </div>
              </div>
            </section>

            <section className="panel">
              <h3 className="section-title">Cites recuperades</h3>
              <div className="citation-list">
                {citations.length === 0 ? (
                  <div className="card">
                    <strong>Sense cites encara</strong>
                    <small>Envia una pregunta per veure les fonts que sustenten la resposta.</small>
                  </div>
                ) : (
                  citations.map((citation, index) => (
                    <div key={citation.id} className="card">
                      <strong>
                        [{index + 1}] {citation.document_title}
                      </strong>
                      <small>
                        {citation.municipality}
                        {citation.article_title ? ` · ${citation.article_title}` : ''}
                      </small>
                      <p>{citation.excerpt}</p>
                      {citation.url ? (
                        <a href={citation.url} target="_blank" rel="noreferrer">
                          Obre la font oficial
                        </a>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="panel">
              <h3 className="section-title">Explorador ràpid</h3>
              <div className="search-list">
                {searchHits.length === 0 ? (
                  <div className="card">
                    <strong>Cap resultat encara</strong>
                    <small>La cerca ràpida mostrarà fragments rellevants per a la consulta actual.</small>
                  </div>
                ) : (
                  searchHits.map((hit, index) => (
                    <div key={hit.id} className="card">
                      <strong>
                        {index + 1}. {hit.document_title}
                      </strong>
                      <small>
                        {hit.municipality}
                        {hit.article_title ? ` · ${hit.article_title}` : ''}
                      </small>
                      <p>{hit.excerpt}</p>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="panel">
              <h3 className="section-title">Notes d’ús</h3>
              <p>
                Aquest primer frontend està pensat per a consulta pública conservadora: sempre amb fonts, sempre dins
                l’abast de Cerdanya i amb possibilitat de rebuig quan no hi ha base suficient.
              </p>
              <div className="footer-note">
                Defineix <strong>NEXT_PUBLIC_API_BASE_URL</strong> si el backend no corre a <code>http://localhost:8000</code>.
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  )
}
