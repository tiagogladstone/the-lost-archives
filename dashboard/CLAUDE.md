# Dashboard — Frontend Next.js

## Stack

- **Next.js 16** com App Router
- **React 19**, **TypeScript 5** (strict)
- **Tailwind CSS 4** — tema dark padrão
- **shadcn/ui** + Radix UI — componentes UI
- **Supabase SSR** — auth server-side com cookies
- **Lucide React** — ícones

## Estrutura

```
src/
├── app/                          # App Router pages
│   ├── page.tsx                  # Home — lista de stories
│   ├── layout.tsx                # Root layout
│   ├── globals.css               # Estilos globais
│   ├── new/page.tsx              # Criar nova story
│   └── stories/[id]/
│       ├── page.tsx              # Detalhe da story
│       └── review/page.tsx       # Revisão (títulos + thumbnails)
├── components/
│   ├── stories-table.tsx         # Tabela com realtime subscriptions
│   ├── sidebar.tsx               # Navegação lateral
│   └── ui/                       # Primitivos shadcn/ui (10+ componentes)
├── lib/
│   ├── utils.ts                  # Utilitário cn() (clsx + tailwind-merge)
│   └── supabase/
│       ├── client.ts             # Supabase client-side
│       └── server.ts             # Supabase server-side (cookies)
└── types/
    └── index.ts                  # Type Story
```

## Realtime

`StoriesTable` usa Supabase Realtime subscriptions na tabela `stories` para atualizar status automaticamente.

## Variáveis de Ambiente

```
NEXT_PUBLIC_SUPABASE_URL      # URL do projeto Supabase
NEXT_PUBLIC_SUPABASE_ANON_KEY # Anon key (pública)
NEXT_PUBLIC_API_URL           # URL da API FastAPI
```

## Comandos

```bash
npm run dev     # Desenvolvimento (porta 3000)
npm run build   # Build produção
npm run lint    # ESLint
```

## Convenções

- Componentes UI primitivos em `src/components/ui/` (shadcn/ui)
- Componentes de negócio em `src/components/`
- Utilitário `cn()` de `src/lib/utils.ts` para classes condicionais
- Server Components por padrão, Client Components com `"use client"` quando necessário
