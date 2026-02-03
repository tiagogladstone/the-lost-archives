# 🗃️ The Lost Archives

**The Lost Archives** é um canal do YouTube totalmente automatizado que cria conteúdo sobre história e curiosidades em múltiplos idiomas. O pipeline completo, desde a criação do roteiro até o upload para o YouTube, é executado de forma autônoma.

## 📜 Visão Geral do Projeto

O objetivo deste projeto é explorar o potencial da automação de conteúdo utilizando inteligência artificial para gerar vídeos educacionais e de entretenimento. O sistema é projetado para ser modular, permitindo a fácil substituição ou melhoria de cada componente do pipeline.

## ✨ Features

- 🌍 **Suporte Multi-idioma:** Conteúdo gerado em Português, Inglês e Espanhol.
- 🤖 **Pipeline 100% Automatizado:** Da ideia ao vídeo pronto no YouTube sem intervenção manual.
- 📝 **Roteiros por IA:** Scripts dinâmicos e criativos gerados pelo **Google Gemini**.
- 🎙️ **Narração Neural:** Vozes realistas e de alta qualidade via **Google Cloud TTS**.
- 🎬 **Mídia de Stock:** Vídeos e imagens de alta resolução da API do **Pexels**.
- 📊 **Metadados Otimizados:** Títulos, descrições e tags gerados por IA para otimização de SEO.
- 🚀 **Orquestração em Nuvem:** Deploy e execução via Cloud Run ou GitHub Actions.

## 🏛️ Arquitetura do Pipeline

O pipeline é composto por uma série de scripts Python que executam etapas específicas do processo de criação do vídeo.

Para uma descrição visual e detalhada de cada componente, veja o documento de arquitetura:
**[➡️ `docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**

## 🔧 Scripts do Projeto

Aqui está uma lista de todos os scripts principais e suas responsabilidades no pipeline:

| Script | Descrição |
| :--- | :--- |
| **`main.py`** | Ponto de entrada para execução em servidor (Cloud Run). Orquestra a chamada dos outros scripts. |
| **`scripts/generate_script.py`** | Usa o Gemini para criar um roteiro sobre um determinado tópico. |
| **`scripts/generate_tts.py`** | Converte o roteiro de texto em um arquivo de áudio (`.mp3`) usando Google TTS. |
| **`scripts/generate_metadata.py`**| Gera títulos, descrições e tags para o vídeo, otimizados para YouTube. |
| **`scripts/fetch_media.py`** | Baixa vídeos e imagens do Pexels com base nas palavras-chave do roteiro. |
| **`scripts/render_video.py`** | Utiliza o `FFmpeg` para unir o áudio, vídeos, imagens e música de fundo no vídeo final. |
| **`scripts/upload_youtube.py`**| Faz o upload do vídeo renderizado para o YouTube usando a API de Dados. |
| **`scripts/translate_content.py`** | (Opcional) Traduz o roteiro e metadados para outros idiomas. |

## ⚙️ Como Configurar

### Requisitos

Antes de começar, garanta que você tenha os seguintes softwares instalados:

- **Python 3.10+**
- **FFmpeg:** Essencial para a renderização de vídeo.
- **Git**
- **Google Cloud SDK** (opcional, para deploy no Cloud Run)

### Passos para Instalação

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/tiagogladstone/the-lost-archives.git
   cd the-lost-archives
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   # No Windows: venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

### Configuração de API Keys e OAuth

O projeto requer acesso a várias APIs. Siga os passos abaixo para configurar as credenciais:

1. **Google Cloud (Gemini, TTS):**
   - Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/).
   - Ative as APIs "Vertex AI" e "Cloud Text-to-Speech".
   - Crie uma chave de API e salve-a em um local seguro.
   - Configure a variável de ambiente `GCP_API_KEY` com o valor da sua chave.

2. **Pexels API:**
   - Crie uma conta no [Pexels](https://www.pexels.com/api/).
   - Solicite uma chave de API.
   - Configure a variável de ambiente `PEXELS_API_KEY` com o valor da sua chave.

3. **YouTube Data API (OAuth 2.0):**
   - No mesmo projeto do Google Cloud, ative a "YouTube Data API v3".
   - Crie credenciais do tipo "Tela de consentimento OAuth" e configure-a.
   - Crie uma credencial do tipo "ID do cliente OAuth".
   - Baixe o arquivo JSON com as credenciais e salve-o como `client_secrets.json` na raiz do projeto. Na primeira vez que você executar o script de upload, será necessário autorizar o acesso à sua conta do YouTube através do navegador. Um arquivo `token.json` será gerado para autenticações futuras.

## 🚀 Como Usar

### Executando o Pipeline Completo

O `main.py` pode ser usado para executar o pipeline localmente através de uma simples requisição HTTP.

1. **Inicie o servidor local:**
   ```bash
   python main.py
   ```

2. **Envie uma requisição POST para gerar um vídeo:**
   ```bash
   curl -X POST http://localhost:8080/generate \
   -H "Content-Type: application/json" \
   -d '{
     "topic": "A História do Chocolate",
     "language": "pt-BR"
   }'
   ```

### Executando Scripts Individualmente

Você também pode executar cada script do pipeline de forma independente para depuração ou testes.

**Exemplo: Gerar apenas o roteiro**
```bash
python scripts/generate_script.py --topic "A Grande Muralha da China" --language "pt-BR" --output /tmp/roteiro.txt
```

**Exemplo: Renderizar um vídeo**
```bash
python scripts/render_video.py --audio_path /tmp/narration.mp3 --output /tmp/video.mp4
```

## 📜 Licença

Este projeto é privado e todos os direitos são reservados.
