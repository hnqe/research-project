# 🏛️ MVP CGU - Análise de Recursos LAI

**Sistema de Análise Inteligente para Recursos da Lei de Acesso à Informação**

Uma aplicação completa que utiliza **Inteligência Artificial** e **Recuperação de Informação** para analisar recursos LAI, prever decisões e gerar minutas automatizadas para a Controladoria-Geral da União (CGU).

> **📦 Imagem Docker Oficial**: [`hnqe/mvp-cgu-data:latest`](https://hub.docker.com/r/hnqe/mvp-cgu-data) - Dados pré-processados (862k+ registros)

---

## 📋 Índice

- [🎯 Visão Geral](#-visão-geral)
- [⚡ Funcionalidades](#-funcionalidades)
- [🛠️ Tecnologias](#️-tecnologias)
- [📦 Instalação](#-instalação)
- [🚀 Como Usar](#-como-usar)
- [🔧 Configuração](#-configuração)
- [📊 Dados](#-dados)
- [🤖 IA e Predições](#-ia-e-predições)
- [📄 API Documentation](#-api-documentation)
- [🔧 Scripts](#-scripts)
- [🔍 Troubleshooting](#-troubleshooting)

---

## 🎯 Visão Geral

O **MVP CGU** é uma solução inovadora que combina **Recuperação Aumentada por Geração (RAG)** com análise preditiva para auxiliar na tomada de decisões em recursos LAI. O sistema:

- 🔍 **Analisa** recursos usando similaridade semântica
- 📊 **Prediz** decisões baseadas em casos históricos  
- 📝 **Gera** minutas automatizadas seguindo padrões CGU
- 🔎 **Busca** casos similares por ID ou protocolo
- 📈 **Exibe** estatísticas e métricas de decisão

### Arquitetura RAG

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │────│   FastAPI       │────│   Qdrant        │
│   React         │    │   Backend       │    │   Vector DB     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   Groq API      │
                       │   (LLaMA 3-70B) │
                       └─────────────────┘
```

---

## ⚡ Funcionalidades

### 🧠 **Análise Inteligente de Recursos**
- Análise preditiva baseada em IA
- Identificação de casos similares por embeddings
- Estatísticas de decisões históricas
- Geração automática de minutas oficiais

### 🔍 **Busca Avançada**
- **Por Recurso**: Encontre recursos similares por ID
- **Por Protocolo**: Localize pedidos similares por número de protocolo
- Filtros por instância (CGU, outros órgãos)
- Configuração de score mínimo de similaridade

### 📊 **Dashboard e Métricas**
- Visualização de estatísticas em tempo real
- Percentuais de deferimento/indeferimento
- Métricas de similaridade e confiança
- Interface responsiva e intuitiva

### 📄 **Geração de Documentos**
- Minutas formatadas segundo padrões CGU
- Download em formato texto
- Metadados de geração incluídos
- Aviso de necessidade de revisão manual

---

## 🛠️ Tecnologias

### Backend
- **FastAPI** - Framework web moderno e rápido
- **Qdrant** - Banco de dados vetorial para similarity search
- **HuggingFace Transformers** - Embeddings multilíngues (E5-base)
- **Groq API** - LLaMA 3-70B para geração de texto
- **Pandas** - Processamento de dados
- **Pydantic** - Validação de dados

### Frontend  
- **React** - Interface de usuário moderna
- **Tailwind CSS** - Design system responsivo
- **Lucide Icons** - Iconografia consistente
- **React Toastify** - Notificações elegantes

### Infraestrutura
- **Docker Hub** - Dados pré-processados (`hnqe/mvp-cgu-data`)
- **Docker Compose** - Orquestração do Qdrant
- **Python 3.8+** - Runtime do backend
- **Node.js 16+** - Runtime do frontend

---

## 📦 Instalação

O MVP CGU oferece **duas estratégias** para obter os dados vetorizados:

### 🐳 **Opção 1: Dados Pré-processados (Docker Hub)**

Use nossa **imagem Docker oficial** com todos os dados já processados (~3GB de embeddings):

#### Pré-requisitos
- **Python 3.8+**
- **Node.js 16+** 
- **Docker & Docker Compose**
- **Git**

#### Setup Rápido
```bash
# Clone o repositório
git clone https://github.com/hnqe/research-project
cd research-project/mvp

# Configure ambiente
cp .env.example .env
# Edite .env e adicione sua GROQ_API_KEY

# Instale dependências
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Inicie dados + Qdrant (baixa automaticamente a imagem)
docker-compose up -d

# Indexe dados do Docker no Qdrant (uma única vez)
python scripts/index_from_docker.py

# Inicie aplicação
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Em outro terminal:
cd frontend && npm start
```

✅ **Pronto!** Aplicação rodando com **862k+ registros** indexados.

---

### 🔬 **Opção 2: Processamento Próprio (Jupyter Notebook)**

Para quem quer **gerar os próprios embeddings** ou usar dados customizados:

#### Processamento de Dados
1. **Execute o notebook** `../LangChainIMPL.ipynb` (pasta raiz do projeto IC)
2. **Processe seus dados** para gerar os arquivos:
   - `dt_recursos.parquet` e `dt_pedidos.parquet` 
   - `vetores/recursos_2015_2023.pkl` e `vetores/pedidos_2015_2023.pkl`

#### Setup com Dados Locais
```bash
# Após processar dados no notebook
git clone https://github.com/hnqe/research-project
cd research-project/mvp

# Configure ambiente
cp .env.example .env
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Inicie apenas Qdrant
docker-compose up -d qdrant

# Indexe dados locais
python scripts/index_to_qdrant.py

# Inicie aplicação
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm start
```

---

### 📋 **Comparação das Estratégias**

| Aspecto | Docker Hub (hnqe/mvp-cgu-data) | Notebook Próprio |
|---------|--------------------------------|------------------|
| **⏱️ Tempo** | ~10 min (download + indexação) | ~2h (processamento + indexação) |
| **💾 Tamanho** | ~3GB download | Dados originais + processamento |
| **🎯 Uso** | Demonstração/Produção | Pesquisa/Customização |
| **📊 Dados** | 862k registros (2015-2023) | Configurável |
| **🔧 Flexibilidade** | Dados fixos | Totalmente customizável |

**💡 Recomendação**: Use a **Opção 1** para demonstrações e a **Opção 2** para pesquisa.

---

## 🚀 Como Usar

### Iniciando a Aplicação

#### 1. **Backend (Terminal 1)**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
✅ API disponível em: http://localhost:8000

#### 2. **Frontend (Terminal 2)**  
```bash
cd frontend
npm start
```
✅ Interface disponível em: http://localhost:3000

### Navegação Principal

#### 🏠 **Dashboard**
- Visão geral do sistema
- Status das conexões
- Estatísticas gerais

#### 🧠 **Análise de Recursos**
1. Cole o texto do recurso LAI
2. Configure parâmetros (casos similares, filtros)
3. Escolha se quer gerar minuta automaticamente  
4. Clique em **"Analisar Recurso"**
5. Veja a predição e casos similares
6. Baixe a minuta se gerada

#### 🔍 **Busca por Recurso**
1. Digite o ID do recurso
2. Configure quantidade de similares
3. Clique em **"Buscar"**
4. Explore os recursos similares encontrados

#### 📄 **Busca por Protocolo**
1. Digite o número do protocolo LAI
2. Configure quantidade de similares
3. Clique em **"Buscar"**  
4. Veja pedidos similares e seus protocolos

### Funcionalidades Especiais

#### 📖 **Texto Expansível**
- Clique em **"Ver mais"** para expandir respostas longas
- Clique em **"Ver menos"** para recolher

#### 📊 **Métricas de Similaridade**
- Scores exibidos em percentual
- Barras de progresso visuais
- Filtragem por score mínimo

#### 🏷️ **Badges Informativos**
- **Verde**: Deferido
- **Vermelho**: Indeferido  
- **Amarelo**: Parcialmente Deferido
- **Cinza**: Outras decisões

---

## 🔧 Configuração

### Variáveis de Ambiente (.env)
```bash
# API Key para geração de minutas (opcional)
GROQ_API_KEY=your_groq_api_key_here

# Configurações do Qdrant (automáticas via Docker)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Configurações da API

#### Parâmetros de Busca
- **top_k**: 1-50 (padrão: 10)
- **min_score**: 0.0-1.0 (padrão: 0.0)
- **instance_filter**: Filtro por órgão (opcional)

#### Configurações de IA
- **Modelo de Embeddings**: `intfloat/multilingual-e5-base`
- **Modelo de Geração**: `llama3-70b-8192` (Groq)
- **Similaridade**: Cosseno

---

## 📊 Dados

### Estrutura dos Dados
```
data/                       # Obtidos via Docker ou processamento próprio
├── dt_recursos.parquet     # 82k recursos LAI (2015-2023)
├── dt_pedidos.parquet      # 780k pedidos LAI (2015-2023)    
└── vetores/                # Embeddings pré-calculados (768D)
    ├── recursos_2015_2023.pkl  # Vetores dos recursos
    └── pedidos_2015_2023.pkl   # Vetores dos pedidos
```

> **ℹ️ Nota sobre Vetores**: Os embeddings pré-computados foram gerados utilizando o script `LangChainIMPL` localizado na pasta raiz do projeto IC. Este script implementa a pipeline completa de processamento e vetorização dos dados históricos LAI.

### Coleções Qdrant
- **recursos_cgu_v1**: 82.124 recursos com decisões (deferido/indeferido)
- **pedidos_cgu_v1**: 780.084 pedidos originais LAI

### Metadados dos Recursos
- **ID**: Identificador único do recurso
- **Decision**: Decisão final (Deferido/Indeferido/Parcialmente)
- **Instance**: Órgão responsável pela decisão
- **Description**: Texto do recurso analisado

### Metadados dos Pedidos  
- **ID**: Identificador único do pedido
- **Protocol**: Número do protocolo LAI
- **Summary**: Resumo do pedido
- **Response**: Resposta oficial do órgão

---

## 🤖 IA e Predições

### Como Funciona a Predição

1. **Embeddings Semânticos**
   - Texto convertido para vetor 768D
   - Modelo multilíngue otimizado para português

2. **Busca por Similaridade**  
   - Comparação cosseno entre vetores
   - Recuperação dos K casos mais similares

3. **Análise Estatística**
   - Contagem de decisões históricas
   - Cálculo de percentuais
   - Predição baseada em maioria

4. **Geração de Minuta**
   - Prompt estruturado com contexto legal
   - LLaMA 3-70B via Groq API
   - Formatação segundo padrões CGU

### Exemplo de Predição
```
📊 Análise de 10 casos similares:
├── Indeferido: 7 casos (70%)
├── Deferido: 2 casos (20%)  
└── Parcialmente Deferido: 1 caso (10%)

🎯 Predição: "Provavelmente Indeferido"
```

---

## 📄 API Documentation

### Endpoints Principais

#### `POST /analyze-appeal`
Análise preditiva de recurso
```json
{
  "text": "Texto do recurso LAI...",
  "top_k": 10,
  "instance_filter": "CGU",
  "min_score": 0.0
}
```

#### `POST /analyze-appeal-with-draft`  
Análise + geração de minuta
```json
{
  "text": "Texto do recurso LAI...",
  "top_k": 10,
  "instance_filter": "CGU", 
  "min_score": 0.0
}
```

#### `GET /context-by-protocol/{protocol_id}`
Busca por protocolo
```
GET /context-by-protocol/23546026306202248?top_k=5
```

#### `GET /similar-appeals/{appeal_id}`
Busca recursos similares
```
GET /similar-appeals/4288666?top_k=5
```

#### `GET /instances`
Lista instâncias disponíveis
```json
["CGU", "Ministério da Fazenda", "INSS", ...]
```

#### `GET /health`
Status do sistema
```json
{
  "status": "healthy",
  "qdrant_connection": "ok",
  "collections": ["recursos_cgu_v1", "pedidos_cgu_v1"]
}
```

### Swagger UI
Acesse a documentação interativa em:
**http://localhost:8000/docs**

---

## 🔍 Troubleshooting

### Problemas Comuns

#### ❌ Qdrant não conecta
```bash
# Verifique se o Docker está rodando
docker ps

# Reinicie o Qdrant
docker-compose down
docker-compose up -d

# Teste a conexão
curl http://localhost:6333/health
```

#### ❌ Coleções vazias
```bash
# Re-execute a indexação
python scripts/index_to_qdrant.py

# Verifique as coleções
python scripts/health_check.py
```

#### ❌ API Groq não funciona
- Verifique se `GROQ_API_KEY` está configurada no `.env`
- Teste sem geração de minuta primeiro
- Verifique sua quota na Groq

#### ❌ Frontend não carrega
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

#### ❌ Erro de CORS
- Backend deve estar em `http://localhost:8000`
- Frontend deve estar em `http://localhost:3000`
- Verifique as configurações de CORS no FastAPI

### Logs e Debug

#### Backend
```bash
# Logs detalhados
uvicorn app.main:app --reload --log-level debug

# Health check
python scripts/health_check.py
```

#### Frontend
```bash
# Console do navegador (F12)
# Network tab para requisições
# Console tab para erros JavaScript
```

#### Qdrant
```bash
# Dashboard do Qdrant
http://localhost:6333/dashboard

# Logs do container
docker logs $(docker-compose ps -q qdrant)
```

---

## 🔧 Scripts

O MVP CGU oferece **2 scripts de indexação** para diferentes cenários:

### 📊 **Scripts Disponíveis**

| Script | Fonte dos Dados | Quando Usar |
|--------|-----------------|-------------|
| `scripts/index_from_docker.py` | **Container Docker** | ✅ **Recomendado** - Produção, dados pré-processados |
| `scripts/index_to_qdrant.py` | **Arquivos locais** | Desenvolvimento, dados customizados |

### 🐳 **Script Principal: `index_from_docker.py`**

**Para usuários da imagem Docker oficial:**
```bash
# Após docker-compose up -d
python scripts/index_from_docker.py
```

**Características:**
- ✅ Usa dados da imagem `hnqe/mvp-cgu-data:latest`
- ✅ **862k+ registros** (82k recursos + 780k pedidos)
- ✅ Copia automaticamente do container
- ✅ Otimizado para estabilidade
- ✅ Limpeza automática de arquivos temporários

### 🗂️ **Script Alternativo: `index_to_qdrant.py`**

**Para usuários com dados próprios:**
```bash
# Após processar dados no notebook
python scripts/index_to_qdrant.py
```

**Características:**
- ✅ Usa dados da pasta `./data/` local
- ✅ Para desenvolvimento e experimentação
- ✅ Dados processados via Jupyter Notebook
- ✅ Maior controle sobre dados

### 📋 **Documentação Completa**

Para detalhes técnicos, troubleshooting e comparações:
**👉 Consulte: `SCRIPTS.md`**

---