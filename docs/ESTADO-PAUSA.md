# The Lost Archives - Estado de Pausa

> **Data da pausa:** 2026-02-03  
> **Motivo:** Projeto pausado para focar em outras prioridades  
> **Nível de completude:** ~70% (pipeline funcional, SaaS arquitetado mas não completamente testado)

---

## 📊 Resumo Executivo

O projeto The Lost Archives foi desenvolvido até um estado funcional:
- ✅ Pipeline v1 monolítico funcionando (3 vídeos publicados no YouTube)
- ✅ Arquitetura SaaS completa implementada (API + 8 workers + Dashboard)
- ⚠️ Alguns workers do SaaS nunca testados em produção
- ⚠️ 1 bug conhecido não corrigido (render_worker)

**Estado atual:** Infraestrutura deployada e funcionando. Custos zerados quando ocioso (min-instances=0).

---

## 🏗️ Infraestrutura Deployada

### Cloud Services

| Serviço | URL/Identificador | Descrição | Status |
|---------|-------------------|-----------|--------|
| **API (Cloud Run)** | `https://tla-api-69772481550.us-central1.run.app` | FastAPI com 10 endpoints REST | ✅ Funcionando |
| **Workers (Cloud Run)** | `https://tla-workers-69772481550.us-central1.run.app` | 8 workers especializados | ⚠️ Parcialmente testado |
| **Pipeline v1 (Cloud Run)** | `https://lost-archives-69772481550.us-central1.run.app` | Pipeline monolítico original | ✅ Funcionando |
| **Dashboard (Vercel)** | `https://the-lost-archives-dashboard.vercel.app` | Interface Next.js | ✅ Funcionando |
| **Supabase** | ref `wjpjiykhyecfxubnrvoc` | 5 tabelas, 4 buckets, stored procedures | ✅ Funcionando |

### Repositórios e Canais

- **GitHub:** `tiagogladstone/the-lost-archives`
- **YouTube:** @TheLostArchives-g3t (3 vídeos publicados)
- **Email do canal:** channelthelostarchives@gmail.com
- **GCloud Project:** `project-75d9e1c4-e2a7-4da9-923`

### Configuração dos Workers (Cloud Run)

Todos configurados com:
- `--min-instances=0` → Custo zero quando ocioso
- `--max-instances=1` → Evita custos descontrolados
- `--memory=2Gi` → Suficiente para processamento de vídeo
- `--timeout=3600s` → 1 hora para renders longos
- Secrets: `SUPABASE_URL`, `SUPABASE_KEY`, `GCP_PROJECT_ID`, `PEXELS_API_KEY`

---

## ✅ O que funciona (testado e validado)

### Pipeline v1 (Monolítico)
- ✅ Geração completa de vídeos (script → imagens → áudio → render → upload)
- ✅ 3 vídeos publicados com sucesso no YouTube
- ✅ Integração com Gemini (roteiros), Imagen 4 (imagens), Google Cloud TTS (narração)
- ✅ Effects avançados: Ken Burns, transições, zoom
- ✅ Upload automático para YouTube com metadata

### API FastAPI
- ✅ Health check funcionando
- ✅ POST `/stories` → cria nova história no Supabase
- ✅ GET `/stories` → lista histórias com filtros
- ✅ GET `/stories/{id}` → detalhes de história específica
- ✅ PATCH `/stories/{id}` → atualiza status/dados
- ✅ Integração completa com Supabase (tabelas + storage)

### Workers Funcionais (testados)
1. **script_worker** → Gera roteiros com Gemini ✅
2. **image_worker** → Gera imagens com Imagen 4 ✅
3. **audio_worker** → Gera narração com Google Cloud TTS ✅
   - Fix do tempfile aplicado (criação explícita de arquivo temporário)

### Dashboard (Next.js/Vercel)
- ✅ Conectado ao Supabase (leitura/escrita)
- ✅ Página de listagem de stories
- ✅ Página de review (seleção de título/thumbnail/publicação)
- ✅ Interface responsiva e funcional
- ✅ Deploy automatizado via Vercel

---

## 🐛 Bugs Conhecidos (não corrigidos)

### 1. render_worker.py - Bug crítico (BLOCKER)

**Localização:** `backend/workers/render_worker.py`, linha ~73  
**Problema:** Ao criar arquivo de concatenação do FFmpeg, o código escreve `\\n` literal em vez de quebra de linha real.

```python
# ERRADO (atual):
concat_file.write(f"file '{clip}'\\n")  # Escreve string "\\n" literal

# CORRETO (fix aplicado localmente mas NÃO deployado):
concat_file.write(f"file '{clip}'\n")  # Quebra de linha real
```

**Impacto:** FFmpeg falha ao tentar ler o arquivo de concatenação.  
**Status:** Fix identificado e aplicado no código local, mas **NÃO foi deployado** no Cloud Run.  
**Próximo passo:** Deploy do render_worker corrigido.

### 2. Workers nunca testados em produção

Os seguintes workers foram implementados mas **nunca rodaram** em ambiente de produção:
- **thumbnail_worker** → Cria thumbnail com título sobreposto
- **metadata_worker** → Gera título, descrição e tags otimizadas
- **upload_worker** → Faz upload para YouTube

**Motivo:** Pipeline E2E do SaaS nunca foi completado (bloqueado pelo bug do render_worker).

### 3. check_and_advance incompleto

**Localização:** `backend/workers/base_worker.py`  
**Problema:** Lógica de transição de status após rendering está incompleta.  
**Impacto:** Workers podem não avançar corretamente após render.  
**Status:** Identificado mas não corrigido.

---

## 🚀 Próximos Passos para Retomar

### Fase 1: Corrigir e Testar (1-2 dias)
1. ✅ **Deploy do render_worker corrigido** (fix do `\\n` já está no código local)
2. ⚙️ Testar pipeline E2E completo:
   - Criar story via API
   - Rodar script_worker → image_worker → audio_worker → render_worker
   - Validar output final (vídeo gerado)
3. ⚙️ Validar thumbnail_worker e metadata_worker em produção
4. ⚙️ Corrigir lógica de `check_and_advance` no base_worker

### Fase 2: YouTube Integration (1 dia)
1. 🔐 Configurar YouTube OAuth token no Cloud Run
   - Criar secret `YOUTUBE_CREDENTIALS` no Secret Manager
   - Atualizar deploy do upload_worker
2. ⚙️ Testar upload_worker com vídeo real
3. ✅ Validar metadata no YouTube (título, descrição, tags)

### Fase 3: Dashboard Real-time (1 dia)
1. 🔌 Integrar Supabase Realtime no dashboard
   - Subscribe to `stories` table changes
   - Atualizar UI em tempo real (progresso dos workers)
2. 🎨 Adicionar progress bar visual por etapa
3. 📊 Dashboard de estatísticas (vídeos criados, tempo médio, etc.)

### Fase 4: Scaling e Monitoramento (1-2 dias)
1. 📈 Configurar Cloud Monitoring (alertas de erro, latência)
2. 💰 Configurar alertas de custo (GCP Budget)
3. 🔄 Testar comportamento com múltiplas stories simultâneas
4. 📊 Validar auto-scaling dos workers

**Tempo estimado total para retomada completa:** 4-6 dias

---

## 🔐 Credenciais (no Vault)

Todas as credenciais estão armazenadas no macOS Keychain via `./scripts/vault.sh`:

| Serviço | Chave no Vault | Uso |
|---------|----------------|-----|
| Pexels API | `pexels-lost-archives` | Baixar imagens/vídeos de stock |
| Google Cloud | `gcp-lost-archives-apikey` | Gemini, Imagen, TTS, Cloud Run |
| Supabase URL | `supabase-lost-archives-url` | Conexão com banco de dados |
| Supabase Key | `supabase-lost-archives-key` | Autenticação no Supabase |
| Supabase Access Token | `supabase-lost-archives-access-token` | Admin access |
| Vercel Token | `vercel-token` | Deploy do dashboard |

**⚠️ Importante:** YouTube OAuth credentials **não estão** no vault ainda. Precisam ser adicionadas antes de testar upload_worker.

### Recuperar credenciais:
```bash
./scripts/vault.sh get pexels-lost-archives
./scripts/vault.sh get gcp-lost-archives-apikey
# etc.
```

---

## 💰 Custos Atuais

### Configuração de Cost Optimization

Todos os serviços Cloud Run configurados com `--min-instances=0`:
- **Quando ocioso:** $0.00/mês
- **Quando ativo:** Cobrado apenas pelo tempo de execução

### Breakdown de Custos por Vídeo (estimado)

| Componente | Custo | Observação |
|------------|-------|------------|
| Gemini (script) | ~$0.02 | Geração de roteiro |
| Imagen 4 (imagens) | ~$0.20 | 10-15 imagens por vídeo |
| Google Cloud TTS | ~$0.03 | Narração de ~2-3 minutos |
| Cloud Run (workers) | ~$0.05 | Tempo de processamento |
| Cloud Storage | ~$0.01 | Armazenamento temporário |
| Bandwidth | ~$0.04 | Upload/download |
| **TOTAL** | **~$0.35** | Por vídeo completo |

### Custos Mensais (estimados)

- **Produção baixa (10 vídeos/mês):** ~$3.50/mês
- **Produção média (50 vídeos/mês):** ~$17.50/mês
- **Produção alta (200 vídeos/mês):** ~$70/mês

**Serviços free tier:**
- Supabase: Free tier (500 MB database, 1 GB storage)
- Vercel: Free tier (hobby plan)
- YouTube: Grátis (sem limites de upload)

---

## 📚 Documentação Existente

Toda documentação está em `projects/the-lost-archives/docs/`:

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `ARCHITECTURE.md` | Arquitetura completa do SaaS (API + Workers + Dashboard) | ✅ Completo |
| `MIGRATION-PLAN.md` | Plano de migração pipeline→SaaS | ✅ Completo |
| `SCALE-ARCHITECTURE.md` | Arquitetura de escala (multi-tenant, queues) | ✅ Completo |
| `WORKER-SPECS.md` | Especificações detalhadas dos 8 workers | ✅ Completo |
| `TEST-PLAN.md` | Plano de testes (unitários, integração, E2E) | ✅ Completo |
| `DEPLOY-PLAN.md` | Plano de deploy faseado | ✅ Completo |
| `AUDIT-REPORT.md` | Relatório de auditoria (3 blockers resolvidos) | ✅ Completo |
| `POST-IMPLEMENTATION.md` | Checklist pós-implementação | ⚠️ Parcial |
| `README.md` | Índice de toda documentação | ✅ Completo |

**Documentação de memória:**
- `memory/projetos/conteudo-automatizado/CONTEXTO.md` → Contexto completo do projeto
- `memory/projetos/conteudo-automatizado/PENDENCIAS.md` → Tarefas pendentes
- `memory/projetos/conteudo-automatizado/ESTADO-PAUSA.md` → Este arquivo

---

## 🔍 Commits Importantes

Principais marcos do desenvolvimento:

### Pipeline v1 (Monolítico)
- `8295aa6` - Pipeline v2.0 com Ken Burns + Imagen 4
- `5a3c91d` - Integração com Google Cloud TTS
- `2f8e4b1` - Upload automático para YouTube

### SaaS Architecture
- `5063e76` - Implementação inicial dos workers
- `87791a1` - API FastAPI com endpoints CRUD
- `5d27f30` - Integração Supabase (tabelas + buckets)

### Dashboard
- `f82eb3e` - Dashboard Next.js inicial
- `364872d` - Review page (seleção de título/thumb)
- `1c9a5f2` - Deploy no Vercel

### Bug Fixes
- `b8587be` - Fix do audio_worker (tempfile explícito)
- **❌ Não deployado:** Fix do render_worker (`\\n` literal)

---

## 🎯 Estado de cada Componente

### Backend (FastAPI)
| Componente | Status | Observação |
|------------|--------|------------|
| API endpoints | ✅ 100% | Todos funcionando |
| Supabase integration | ✅ 100% | CRUD completo |
| Error handling | ⚠️ 80% | Precisa melhorar logs |
| Authentication | ❌ 0% | Não implementado (não necessário para MVP) |

### Workers
| Worker | Status | Testado? | Observação |
|--------|--------|----------|------------|
| script_worker | ✅ 100% | ✅ Sim | Funcionando perfeitamente |
| image_worker | ✅ 100% | ✅ Sim | Imagen 4 integrado |
| audio_worker | ✅ 100% | ✅ Sim | Fix do tempfile aplicado |
| render_worker | ⚠️ 95% | ❌ Não | Bug do `\\n` não deployado |
| thumbnail_worker | ⚠️ 90% | ❌ Não | Implementado mas não testado |
| metadata_worker | ⚠️ 90% | ❌ Não | Implementado mas não testado |
| upload_worker | ⚠️ 80% | ❌ Não | Falta YouTube credentials |
| check_worker | ✅ 100% | ✅ Sim | Monitora e dispara workers |

### Dashboard
| Feature | Status | Observação |
|---------|--------|------------|
| Listagem de stories | ✅ 100% | Funcionando |
| Review page | ✅ 100% | Funcionando |
| Real-time updates | ❌ 0% | Não implementado |
| Estatísticas | ❌ 0% | Não implementado |
| Configurações | ❌ 0% | Não implementado |

### Pipeline v1 (Monolítico)
| Feature | Status | Observação |
|---------|--------|------------|
| Script generation | ✅ 100% | Gemini integrado |
| Image generation | ✅ 100% | Imagen 4 + Pexels |
| Audio generation | ✅ 100% | Google Cloud TTS |
| Video rendering | ✅ 100% | FFmpeg com effects |
| YouTube upload | ✅ 100% | 3 vídeos publicados |

---

## 🔄 Workflow Atual (quando retomar)

```
1. Criar story via API
   POST /stories { topic, metadata }
   
2. Workers processam automaticamente (check_worker coordena):
   - script_worker: Gera roteiro
   - image_worker: Gera/baixa imagens
   - audio_worker: Gera narração
   - render_worker: Monta vídeo
   - thumbnail_worker: Cria thumbnail
   - metadata_worker: Gera título/descrição/tags
   - upload_worker: Publica no YouTube

3. Dashboard mostra progresso em tempo real
   - Review antes de publicar (opcional)
   - Aprovação manual de título/thumbnail
```

**⚠️ Atualmente o workflow está quebrado no passo do render_worker** devido ao bug do `\\n`.

---

## 📝 Lições Aprendidas

### O que funcionou bem
- ✅ Arquitetura de workers separados (fácil de debugar)
- ✅ Uso de Cloud Run com min-instances=0 (custo otimizado)
- ✅ Supabase como backend (rápido de configurar)
- ✅ Pipeline v1 monolítico como prova de conceito (validou a viabilidade)
- ✅ Documentação extensiva (facilitou pausa sem perda de contexto)

### O que pode melhorar
- ⚠️ Testes E2E antes de deploy (render_worker foi deployado com bug)
- ⚠️ Logs estruturados (Cloud Logging não está bem configurado)
- ⚠️ Monitoramento proativo (falta alertas de erro)
- ⚠️ CI/CD automatizado (deploy manual é propenso a erros)

### Decisões técnicas importantes
- **Por que Cloud Run?** Auto-scaling + min-instances=0 + fácil deploy
- **Por que workers separados?** Modularidade + reusabilidade + debug mais fácil
- **Por que Supabase?** Free tier generoso + Postgres + Storage + Realtime
- **Por que não Pub/Sub?** Para MVP, polling é suficiente (mais simples)

---

## 🎬 Vídeos Publicados (Referência)

| Título | URL | Status | Data |
|--------|-----|--------|------|
| *[Vídeo 1 - título não registrado]* | youtube.com/watch?v=... | ✅ Publicado | ~Jan 2026 |
| *[Vídeo 2 - título não registrado]* | youtube.com/watch?v=... | ✅ Publicado | ~Jan 2026 |
| *[Vídeo 3 - título não registrado]* | youtube.com/watch?v=... | ✅ Publicado | ~Jan 2026 |

**Nota:** URLs exatas não foram registradas. Podem ser encontradas no canal @TheLostArchives-g3t.

---

## 🔮 Visão de Futuro (quando retomar)

### Curto Prazo (1-2 semanas)
- Corrigir bugs conhecidos
- Completar pipeline E2E do SaaS
- Dashboard com progresso em tempo real
- Publicar 10 vídeos via SaaS (validar estabilidade)

### Médio Prazo (1-2 meses)
- Multi-tenancy (permitir outros usuários criarem vídeos)
- Queue system (Pub/Sub ou Cloud Tasks)
- Analytics dashboard (views, engagement, custos)
- API pública (permitir integrações externas)

### Longo Prazo (3-6 meses)
- Marketplace de templates (estilos de vídeo)
- Editor visual de vídeos (drag-and-drop)
- Integração com outras plataformas (TikTok, Instagram)
- White-label (permitir outras empresas usarem a infraestrutura)

---

## 📞 Contato e Recursos

- **Repositório:** https://github.com/tiagogladstone/the-lost-archives
- **Dashboard:** https://the-lost-archives-dashboard.vercel.app
- **Canal YouTube:** https://youtube.com/@TheLostArchives-g3t
- **Email do canal:** channelthelostarchives@gmail.com

---

**Última atualização:** 2026-02-03  
**Próxima revisão:** Quando o projeto for retomado

---

*Este documento foi criado para garantir que NENHUM contexto seja perdido durante a pausa. Qualquer pessoa deve conseguir retomar o projeto lendo apenas este arquivo + a documentação em `docs/`.*
