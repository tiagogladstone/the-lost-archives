# The Lost Archives

Canal do YouTube totalmente automatizado que gera vídeos sobre história e curiosidades usando IA.

## Stack

- **Backend:** Python 3.11, FastAPI, Supabase (PostgreSQL + Storage)
- **Frontend:** Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui
- **IA:** Google Gemini 1.5 Flash, Imagen 4, Google Cloud TTS (Wavenet)
- **Mídia:** FFmpeg, Pexels API (stock footage)
- **Upload:** YouTube Data API v3 (OAuth 2.0)
- **Infra:** Docker, Google Cloud Run, GitHub Actions

## Estrutura de Diretórios

```
├── api/            # FastAPI server (endpoints REST)
├── workers/        # 8 workers de processamento (job queue)
├── scripts/        # Scripts standalone CLI (legado/utilitário)
├── dashboard/      # Frontend Next.js (App Router)
├── database/       # Schema SQL + setup Supabase
├── config/         # YAML configs (settings, voices, prompts)
├── docs/           # Documentação técnica
├── assets/         # Recursos estáticos
├── output/         # Outputs gerados
├── main.py         # Entrypoint HTTP legado (Cloud Run)
├── worker_runner.py # Runner multiprocessing (inicia 8 workers)
└── upload_youtube.py # Script upload YouTube standalone
```

## Arquitetura: Pipeline de 3 Fases

### Fase 1 — Script (Sequencial)
`script_worker` gera roteiro via Gemini → divide em scenes → cria jobs para fase 2

### Fase 2 — Production (Paralela)
`image_worker`, `audio_worker`, `translation_worker` processam scenes simultaneamente → `render_worker` compila vídeo final com FFmpeg

### Fase 3 — Review & Publish (Human-in-the-loop)
`thumbnail_worker` + `metadata_worker` geram opções → usuário revisa no dashboard → `upload_worker` publica no YouTube

## Fluxo de Status (stories)

```
pending → generating_script → producing → rendering → ready_for_review → publishing → published
                                                                                    → failed
```

## Variáveis de Ambiente

```
SUPABASE_URL          # URL do projeto Supabase
SUPABASE_KEY          # Service role key
GOOGLE_API_KEY        # Gemini + Google Cloud APIs
PEXELS_API_KEY        # Stock footage
API_KEY               # Autenticação da API FastAPI
PORT                  # Porta do servidor (default 8080)
```

Dashboard (em `dashboard/.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_URL
```

## Convenções

- Workers herdam de `BaseWorker` e implementam `process(job)`
- Job claiming atômico via stored procedure `claim_next_job` (FOR UPDATE SKIP LOCKED)
- Scripts standalone em `/scripts` com `if __name__ == "__main__"` + argparse
- Jobs são granulares: 1 job por cena (imagem, áudio, tradução)
- Multi-idioma via JSONB (`translated_text` em scenes)
- Retry automático com backoff: 30s → 60s → 120s, max 3 tentativas

## Comandos Úteis

```bash
# API
cd api && uvicorn main:app --reload --port 8000

# Workers (todos de uma vez)
python worker_runner.py

# Worker individual
python -m workers.script_worker

# Dashboard
cd dashboard && npm run dev

# Script standalone (exemplo)
python scripts/generate_script.py --topic "Ancient Rome"
```
