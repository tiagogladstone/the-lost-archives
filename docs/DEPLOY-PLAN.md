# Plano de Deploy

Este documento descreve a ordem de deploy e os passos de validação para a infraestrutura SaaS do The Lost Archives no Google Cloud (Cloud Run) e Vercel.

## Ordem de Deploy (com validação entre etapas)

A estratégia é um deploy faseado, onde cada componente principal da arquitetura é deployado e validado antes de prosseguir para o próximo, minimizando riscos.

### Etapa 1: Banco de Dados (Supabase)
O banco de dados é a fundação. Tudo depende dele estar configurado corretamente.

1.  **Ação:** Acessar o projeto no Supabase Studio.
2.  **Ação:** Navegar até o "SQL Editor" e colar o conteúdo do arquivo `database/schema.sql`.
3.  **Ação:** Executar o script para criar as tabelas (`stories`, `scenes`, `title_options`, `thumbnail_options`, `jobs`).
4.  **Ação:** Navegar até "Storage" e criar os buckets públicos: `images`, `audio`, `videos`, `thumbnails`.
5.  **Ação:** Navegar até "Database" -> "Replication" e habilitar o realtime para as tabelas `stories`, `title_options`, e `thumbnail_options`.
6.  **VALIDAÇÃO:** Rodar um script local (`database/supabase_setup.py`) que se conecta ao Supabase e confirma que consegue inserir e ler um registro de teste na tabela `stories`.

### Etapa 2: API (FastAPI no Cloud Run)
A API é o ponto de entrada central. Os workers e o dashboard dependerão dela.

1.  **Ação:** Criar um novo serviço no Cloud Run chamado `tla-api`.
2.  **Ação:** Configurar o build para usar o `Dockerfile` na raiz do projeto e apontar para o entrypoint da API (`main.py` com `uvicorn`).
3.  **Ação:** Adicionar as variáveis de ambiente necessárias: `SUPABASE_URL` e `SUPABASE_KEY`.
4.  **Ação:** Fazer o deploy da primeira versão.
5.  **VALIDAÇÃO:** Usar `curl` ou um cliente de API para fazer uma chamada `POST /stories` com dados de teste. A chamada deve retornar um status `200` ou `201` e o ID da nova story.
6.  **VALIDAÇÃO:** Fazer uma chamada `GET /stories` e verificar se a story criada aparece na lista.

### Etapa 3: Workers Fase 1 (Cloud Run)
O `script_worker` é o primeiro passo do pipeline automatizado.

1.  **Ação:** Criar um serviço no Cloud Run para o `script_worker` (`tla-script-worker`).
2.  **Ação:** Configurar o build e o entrypoint para `workers/script_worker.py`.
3.  **Ação:** Adicionar as variáveis de ambiente: `SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_API_KEY`.
4.  **VALIDAÇÃO:** Criar uma nova story via API (Etapa 2). Observar os logs do `script-worker` para ver se ele pega o job.
5.  **VALIDAÇÃO:** Verificar no Supabase Studio se o status da `story` mudou para `producing` e se a tabela `scenes` foi populada com os dados corretos.

### Etapa 4: Workers Fase 2 (Cloud Run)
Deploy dos workers paralelos.

1.  **Ação:** Deployar `image_worker`, `audio_worker`, e `translation_worker` como serviços separados no Cloud Run (`tla-image-worker`, etc.).
2.  **Ação:** Configurar as mesmas variáveis de ambiente da Etapa 3 para cada um.
3.  **VALIDAÇÃO:** Criar uma nova story. Após a conclusão da Fase 1, verificar os logs dos três workers para confirmar que eles estão processando as cenas em paralelo.
4.  **VALIDAÇÃO:** Verificar no Supabase se as `scenes` estão sendo atualizadas com `image_url`, `audio_url`, e `translated_text`.
5.  **VALIDAÇÃO:** Verificar nos buckets do Supabase Storage se os arquivos de imagem e áudio estão sendo criados.

### Etapa 5: Workers Fase 3 (Render, Thumb, Meta) (Cloud Run)
Deploy dos workers de pós-produção.

1.  **Ação:** Deployar `render_worker`, `thumbnail_worker`, e `metadata_worker` como serviços separados. O `render-worker` pode precisar de mais memória/CPU.
2.  **Ação:** Configurar as variáveis de ambiente necessárias.
3.  **VALIDAÇÃO:** Acompanhar uma story que completou a Fase 2. Verificar se o `render-worker` é acionado.
4.  **VALIDAÇÃO:** Verificar se o status da `story` muda para `ready_for_review` e se um `video_url` é adicionado. O vídeo deve existir no bucket `videos`.
5.  **VALIDAÇÃO:** Verificar se o `thumbnail_worker` e o `metadata_worker` rodam em seguida, populando as tabelas `thumbnail_options` e `title_options`, e o campo `metadata` da `story`.

### Etapa 6: Dashboard (Vercel)
A interface do usuário para revisão e publicação.

1.  **Ação:** Criar um novo projeto no Vercel e conectá-lo ao repositório do GitHub.
2.  **Ação:** Adicionar as variáveis de ambiente do Vercel, incluindo `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, e a URL da API do Cloud Run (`NEXT_PUBLIC_API_URL`).
3.  **Ação:** Fazer o deploy.
4.  **VALIDAÇÃO:** Acessar a URL do Vercel. A lista de stories (incluindo as de teste) deve aparecer.
5.  **VALIDAÇÃO:** Criar uma nova story a partir do dashboard. Observar o status mudar em tempo real (indicando que o realtime do Supabase está funcionando).
6.  **VALIDAÇÃO:** Navegar para a página de revisão de uma story que esteja `ready_for_review`. O vídeo, títulos e thumbnails devem ser exibidos corretamente. A aprovação de um item deve funcionar.

### Etapa 7: Upload Worker (Cloud Run)
O passo final e crítico da publicação.

1.  **Ação:** Deployar o `upload_worker` como um serviço Cloud Run.
2.  **Ação:** Adicionar a variável de ambiente `YOUTUBE_TOKEN_JSON` (em base64), além das do Supabase.
3.  **VALIDAÇÃO:** Em uma story de teste na página de revisão do dashboard, aprovar todos os itens e clicar em "Publicar".
4.  **VALIDAÇÃO:** Verificar os logs do `upload-worker` para confirmar que ele foi acionado.
5.  **VALIDAÇÃO:** Verificar o canal do YouTube para confirmar que o vídeo de teste foi publicado corretamente como "Não Listado".
6.  **VALIDAÇÃO:** Verificar se o status da `story` no Supabase foi atualizado para `published` e a `youtube_url` foi preenchida.

### Etapa 8: Teste E2E Final
Uma verificação completa do fluxo integrado.

1.  **Ação:** Criar uma story do zero, usando o dashboard Vercel.
2.  **Ação:** Acompanhar todas as fases através do dashboard, verificando as atualizações de status.
3.  **Ação:** Na página de revisão, solicitar a regeneração de pelo menos um título e uma thumbnail para testar o fluxo de feedback.
4.  **Ação:** Após aprovar tudo, publicar o vídeo.
5.  **VALIDAÇÃO FINAL:** Confirmar que o vídeo está no YouTube com os metadados corretos e que o ciclo de vida da `story` no banco de dados está completo e correto.
