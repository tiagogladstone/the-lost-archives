# Docs — Documentação Técnica

## Documentos-Chave

| Arquivo | Conteúdo |
|---------|----------|
| `ARCHITECTURE.md` | Arquitetura de 3 fases, fluxo de dados, diagrama de componentes |
| `WORKER-SPECS.md` | Especificações detalhadas de cada worker (contratos, I/O, erros) |
| `MIGRATION-PLAN.md` | Plano de migração de scripts standalone para workers |
| `AUDIT-REPORT.md` | Relatório de auditoria — **contém riscos bloqueantes identificados** |
| `DEPLOY-PLAN.md` | Plano de deploy (Cloud Run, Docker, CI/CD) |
| `SCALE-ARCHITECTURE.md` | Arquitetura para escala futura |
| `TEST-PLAN.md` | Plano de testes (unitários, integração, E2E) |
| `POST-IMPLEMENTATION.md` | Checklist pós-implementação |
| `ESTADO-PAUSA.md` | Estado atual do projeto no momento da pausa |

## Convenções

- Manter docs atualizados ao fazer mudanças arquiteturais
- `AUDIT-REPORT.md` deve ser revisado antes de ir para produção
- `ESTADO-PAUSA.md` serve como snapshot — atualizar ao retomar ou pausar trabalho
