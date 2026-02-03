# Documentação do Projeto: The Lost Archives

## Índice
| Documento | Descrição | Última Atualização |
|-----------|-----------|-------------------|
| MIGRATION-PLAN.md | Plano mestre de migração | 2026-02-03 |
| ARCHITECTURE.md | Arquitetura do sistema | 2026-02-03 |
| SCALE-ARCHITECTURE.md | Arquitetura de escala | 2026-02-03 |
| WORKER-SPECS.md | Especificação dos 8 workers | 2026-02-03 |
| TEST-PLAN.md | Plano de testes | 2026-02-03 |
| DEPLOY-PLAN.md | Plano de deploy faseado | 2026-02-03 |
| AUDIT-REPORT.md | Auditoria do projeto | 2026-02-03 |
| POST-IMPLEMENTATION.md | Checklist pós-implementação | 2026-02-03 |

## Ordem de Leitura Recomendada
1. MIGRATION-PLAN.md (visão geral)
2. SCALE-ARCHITECTURE.md (como escala)
3. ARCHITECTURE.md (detalhes da implementação)
4. WORKER-SPECS.md (detalhes de cada worker)
5. TEST-PLAN.md (como testar)
6. DEPLOY-PLAN.md (como deployar)

## Decisões Tomadas
- YouTube NÃO suporta A/B no upload → selecionar 1 de 3 opções antes do upload.
- Títulos são gerados por IA baseados em SEO e NÃO são editáveis pelo usuário, apenas selecionáveis.
- Orquestrador descentralizado: cada worker é responsável por verificar e disparar a próxima fase do pipeline (`check_and_advance`).
- Jobs granulares por cena (não por vídeo) para permitir processamento paralelo massivo.
- Retry automático para jobs: 3 tentativas com backoff exponencial.
