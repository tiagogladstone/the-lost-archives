# Arquitetura de Escala: Fila Global de Jobs

Este documento descreve a arquitetura de processamento assíncrono do The Lost Archives, projetada para escalar horizontalmente através de uma fila de jobs global e workers genéricos.

## 1. Conceito Central: Fila Global

A base da arquitetura é a tabela `jobs` no Supabase, que atua como uma **fila global e centralizada** para todas as tarefas do sistema. Workers não são mais dedicados a um vídeo específico; eles são processos genéricos que requisitam o próximo trabalho disponível de seu tipo na fila.

Isso nos permite processar múltiplos vídeos simultaneamente e de forma eficiente. Se houver 100 imagens para gerar (de 10 vídeos diferentes), 10 instâncias do `image_worker` podem processar 10 imagens em paralelo, em vez de um único worker processando todas as 100 imagens sequencialmente.

## 2. Granularidade dos Jobs

A mudança mais impactante é a **granularidade** dos jobs. Em vez de jobs que operam em um vídeo inteiro, os jobs são atômicos e operam na menor unidade de trabalho possível.

- **Modelo Antigo (Errado):**
  ```
  job: { type: 'generate_images', story_id: 1 } → Gera TODAS as 15 imagens.
  ```

- **Modelo Escalável (Certo):**
  ```
  job: { type: 'generate_image', story_id: 1, scene_id: 1 } → Gera 1 imagem.
  job: { type: 'generate_image', story_id: 1, scene_id: 2 } → Gera 1 imagem.
  job: { type: 'generate_image', story_id: 2, scene_id: 1 } → Gera 1 imagem.
  ```

### Tipos de Job Granulares
Os `job_type` refletem essa granularidade:
- `generate_script` (1 por story)
- `generate_image` (1 por CENA)
- `generate_audio` (1 por CENA)
- `translate_scene` (1 por CENA por IDIOMA)
- `render_video` (1 por story)
- `generate_thumbnails` (1 por story)
- `generate_metadata` (1 por story)
- `upload_youtube` (1 por story)

## 3. Diagrama da Arquitetura

```
┌──────────────────────────────────────────────┐
│              FILA GLOBAL (Tabela `jobs`)     │
│                                              │
│  generate_script: [story3, story4]           │
│  generate_image:  [s1-c3, s2-c1, s1-c5...]   │
│  generate_audio:  [s1-c2, s3-c1, s2-c4...]   │
│  translate_scene: [s1-c1-pt, s2-c1-es...]   │
│  render_video:    [story1]                   │
│  generate_thumbnails: [story2]               │
│  upload_youtube:  []                         │
└──────────────┬───────────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Worker 1   Worker 2   Worker N
 (image)    (audio)    (image)
 (Pega qualquer job `generate_image` livre)
```

## 4. Fluxo de Orquestração Descentralizada

A orquestração não depende de um "cérebro" central. Cada worker, ao concluir seu job, é responsável por verificar se pode disparar a próxima etapa do processo para a `story` associada.

1.  **`POST /stories`**: Cria a `story` e o primeiro job: `{ "job_type": "generate_script", "story_id": "..." }`.

2.  **`script_worker`**:
    - Pega o job `generate_script`.
    - Gera o roteiro e o divide em N cenas.
    - **Cria N jobs `generate_image`** (um para cada cena).
    - **Cria N jobs `generate_audio`** (um para cada cena).
    - **Cria N jobs `translate_scene`** para cada idioma.
    - Atualiza o status da `story` para `producing`.

3.  **`image_worker`, `audio_worker`, `translation_worker`**:
    - Processam seus jobs individuais (`generate_image`, `generate_audio`, etc.) em paralelo.
    - Ao concluir, cada worker executa uma verificação (`check_and_advance`).

4.  **Lógica `check_and_advance(story_id)`**:
    - O último worker de produção a terminar (seja de imagem ou áudio) fará a seguinte verificação: "Todas as imagens E áudios desta `story` estão com `status = 'completed'`?"
    - **SIM**: Cria o job `{ "job_type": "render_video", "story_id": "..." }` e muda o status da `story` para `rendering`.
    - **NÃO**: Não faz nada.

5.  **`render_worker`**:
    - Pega o job `render_video`.
    - Renderiza o vídeo.
    - Ao concluir, **cria os jobs `generate_thumbnails` e `generate_metadata`**.

6.  **`thumbnail_worker`, `metadata_worker`**:
    - Processam seus jobs.
    - O último dos dois a terminar verifica se ambos concluíram e, se sim, muda o status da `story` para `ready_for_review`.

7.  **Revisão Humana e Publicação**:
    - O usuário aprova no dashboard.
    - O clique no botão "Publicar" cria o job `{ "job_type": "upload_youtube", "story_id": "..." }`.

8.  **`upload_worker`**:
    - Pega o job `upload_youtube` e publica o vídeo.
    - Muda o status da `story` para `published`.

## 5. Exemplo com 5 Vídeos Simultâneos

1.  Cinco chamadas `POST /stories` ocorrem em um curto intervalo.
2.  **Fila de Jobs:**
    - `generate_script`: 5 jobs.
3.  5 instâncias do `script_worker` (ou uma processando sequencialmente) pegam esses jobs. Conforme terminam, a fila é massivamente populada.
4.  **Fila de Jobs (após 2 scripts terminarem, com ~15 cenas/vídeo):**
    - `generate_script`: 3 jobs.
    - `generate_image`: 30 jobs.
    - `generate_audio`: 30 jobs.
    - `translate_scene`: 30 jobs (assumindo 1 idioma extra).
5.  Neste ponto, o sistema pode escalar horizontalmente. Se tivermos 20 instâncias de `image_worker` no Cloud Run, 20 imagens serão geradas em paralelo, independentemente de qual vídeo elas pertencem. A produção dos 5 vídeos acontece ao mesmo tempo, não um após o outro.

## 6. Métricas e Limites

-   **Métricas Chave:**
    -   `jobs_processed_per_minute`: Mede o throughput geral do sistema.
    -   `avg_queue_time_per_job_type`: Tempo médio que um job espera na fila. Se alto, indica falta de workers daquele tipo.
    -   `avg_processing_time_per_job_type`: Tempo médio de execução de um job.
-   **Limites (Quando escalar):**
    -   **`image_worker` / `audio_worker`**: Escalar instâncias quando `avg_queue_time` para `generate_image` ou `generate_audio` passar de 60 segundos. O Cloud Run pode ser configurado para escalar automaticamente com base no número de jobs na fila (via métricas customizadas).
    -   **`render_worker`**: É mais intensivo em CPU/memória. Escalar com base na utilização de recursos, não apenas no tamanho da fila. Geralmente, menos instâncias mais potentes são melhores.
    -   **API (FastAPI)**: Escalar com base em requisições por segundo (RPS).

## 7. Custos em Escala

A granularidade e o auto-scaling (ex: Cloud Run) otimizam os custos.

| Vídeos/Dia | `generate_image` jobs/dia | Custo Estimado (Imagen) | `generate_audio` jobs/dia | Custo Estimado (TTS) | Custo Total Estimado/Dia |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 10 | 150 | $3.00 | 150 | $0.20 | ~$3.50 |
| 50 | 750 | $15.00 | 750 | $1.00 | ~$17.50 |
| 100 | 1500 | $30.00 | 1500 | $2.00 | ~$35.00 |

*Cálculos baseados em 15 cenas/vídeo e custos de API de $0.02/imagem e ~$0.0013/cena de áudio. Não inclui custos de computação (Cloud Run), que são variáveis mas otimizados, pois as instâncias só rodam quando há trabalho a ser feito.*
