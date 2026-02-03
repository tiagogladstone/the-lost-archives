# Documentação Pós-Implementação

Este documento serve como um checklist e guia para a documentação final a ser produzida **após** a implementação bem-sucedida do pipeline SaaS.

## Checklist de Documentação

-   [ ] **Atualizar `README.md` do repositório:**
    -   [ ] Adicionar uma nova seção "Arquitetura SaaS".
    -   [ ] Incluir um diagrama de arquitetura simplificado.
    -   [ ] Descrever o fluxo de 3 fases.
    -   [ ] Listar todos os workers e suas funções.
    -   [ ] Adicionar instruções claras sobre como rodar o ambiente de desenvolvimento local (API, workers, dashboard).

-   [ ] **Documentar Variáveis de Ambiente:**
    -   [ ] Criar um arquivo `env.example` na raiz do projeto.
    -   [ ] Listar todas as variáveis necessárias para cada serviço (API, workers, dashboard).
        -   `SUPABASE_URL`
        -   `SUPABASE_KEY` (service_role)
        -   `NEXT_PUBLIC_SUPABASE_ANON_KEY` (para o dashboard)
        -   `GOOGLE_API_KEY`
        -   `YOUTUBE_TOKEN_JSON` (em base64)
    -   [ ] Adicionar uma breve descrição para cada variável, explicando o que é e onde obtê-la.

-   [ ] **Criar Guia: "Como Adicionar um Novo Worker":**
    -   [ ] Criar um novo documento em `docs/guides/adding-a-new-worker.md`.
    -   [ ] Descrever o processo passo a passo:
        1.  Heredar da classe `BaseWorker`.
        2.  Implementar o método `process(job)`.
        3.  Adicionar o novo `job_type` às enums/validações.
        4.  Criar o `Dockerfile` para o novo worker.
        5.  Configurar o serviço no Cloud Run.
        6.  Adicionar o worker ao plano de deploy e testes.

-   [ ] **Criar Guia: "Troubleshooting Comum":**
    -   [ ] Criar um novo documento em `docs/guides/troubleshooting.md`.
    -   [ ] Listar erros comuns e suas soluções:
        -   **Erro:** Falha na autenticação do YouTube. **Solução:** Como regenerar e atualizar o `YOUTUBE_TOKEN_JSON`.
        -   **Erro:** `ffmpeg` falha durante a renderização. **Solução:** Como verificar os logs do `render-worker` e interpretar erros comuns do ffmpeg.
        -   **Erro:** API do Gemini/Imagen retorna 429 (Rate Limit). **Solução:** Explicar os limites e a necessidade de backoff exponencial.
        -   **Erro:** Jobs ficam "presos" no estado `processing`. **Solução:** Como verificar os logs do worker específico e forçar um reinício.

-   [ ] **Criar Runbook Operacional:**
    -   [ ] Criar um novo documento em `docs/ops/runbook.md`.
    -   [ ] Descrever procedimentos operacionais padrão:
        -   **Monitoramento:** Como monitorar a saúde dos serviços no Cloud Run e o status dos jobs no Supabase.
        -   **Retentativa de Falhas:** Procedimento para reenfileirar uma `story` ou `job` que falhou.
        -   **Deploy de Hotfix:** Como deployar rapidamente uma correção para um único worker sem interromper o resto do sistema.
        -   **Backup e Restore:** Mencionar a política de backups do Supabase.
