# 🗨️ Chat-CGU: Assistente Inteligente para a Lei de Acesso à Informação

Um sistema de chatbot RAG (Retrieval-Augmented Generation) avançado, projetado para consultar pedidos e recursos da Lei de Acesso à Informação (LAI) de forma intuitiva e precisa, utilizando processamento de linguagem natural e um pipeline de recuperação de múltiplas etapas.

## ✨ Visão Geral

O Chat-CGU transforma a maneira como os usuários interagem com grandes volumes de dados de transparência. Em vez de filtros e buscas manuais, o usuário pode "conversar" com os dados, fazendo perguntas complexas e recebendo respostas contextuais e baseadas em evidências.

O sistema se destaca por sua arquitetura robusta, projetada para **minimizar alucinações** e responder perguntas que exigem o cruzamento de diferentes tipos de informação.

## 🚀 Recursos Principais

-   **Busca Semântica Inteligente:** Encontra pedidos e recursos relevantes mesmo que as palavras-chave não correspondam exatamente.
-   **Roteamento de Intenção:** Detecta automaticamente se o usuário busca um protocolo, um recurso por ID, ou um tópico geral, e escolhe a melhor estratégia de busca.
-   **Busca Multi-Etapas:** Responde a perguntas complexas como *"Quais pedidos sobre COVID-19 possuem recursos?"*, cruzando informações de diferentes datasets.
-   **Alta Fidelidade:** Graças a um prompt de engenharia rígida e à formatação de contexto enriquecida, o modelo é instruído a se basear estritamente nos documentos recuperados.
-   **Interface Web Responsiva:** Uma interface de usuário limpa, rápida e amigável, construída com HTML, CSS e JavaScript puros.
-   **API RESTful:** Todas as funcionalidades são expostas através de uma API FastAPI bem documentada.

## 🛠️ Arquitetura e Tecnologias

O sistema é construído sobre uma pilha de tecnologias moderna e eficiente:

-   **Back-end:** Python, FastAPI, Pydantic
-   **LLM:** Cohere Command-R+
-   **Embeddings:** `intfloat/multilingual-e5-base` (via HuggingFace)
-   **Vector Store:** FAISS (para buscas de similaridade ultrarrápidas)
-   **Core ML/NLP:** LangChain, Pandas, NumPy
-   **Front-end:** HTML5, CSS3 (com Variáveis), JavaScript (vanilla)

## ⚙️ Instalação e Execução

Siga os passos abaixo para executar a aplicação localmente.

### 1. Pré-requisitos
-   Python 3.9+
-   Git
-   Uma chave de API da [Cohere](https://cohere.com/)

### 2. Clone e Configure o Ambiente
```bash
# 1. Clone o repositório
git clone https://github.com/hnqe/research-project.git
cd research-project

# 2. Crie e ative um ambiente virtual
python -m venv venv
# No Linux/macOS:
source venv/bin/activate
# No Windows:
venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt
```

### 3. Configure as Variáveis de Ambiente
Crie um arquivo chamado `.env` na raiz do projeto e adicione suas credenciais:
```dotenv
# .env
COHERE_API_KEY="sua-chave-secreta-do-cohere-aqui"
EMBEDDING_MODEL="intfloat/multilingual-e5-base"
USE_CUDA="false" # Mude para "true" se você possui uma GPU NVIDIA configurada
```

### 4. Prepare os Dados e Vetores
1.  **Datasets:** Coloque seus arquivos `dt_pedidos.parquet` e `dt_recursos.parquet` na pasta `data/`.
2.  **Geração dos Vetores:** Os vetores semânticos (embeddings) precisam ser gerados. Este é um processo intensivo, idealmente executado em um ambiente com GPU (como Google Colab).

    O script `build_vectors.py` gerencia este processo. Como ele faz parte do pacote `cgu_rag`, execute-o como um módulo usando a flag `-m`:
    ```bash
    python -m cgu_rag.build_vectors
    ```
    > **Nota:** Se você gerou os vetores no Colab, basta baixar a pasta `data/vetores/` para o seu projeto local. Você pode usar o script `build_vectors.py` no modo `USE_PRECOMPUTED_EMBEDDINGS = True` para reconstruir os índices rapidamente a partir dos arquivos `.pkl` sem precisar de GPU.

### 5. Inicie a Aplicação
Com os vetores no lugar, inicie o servidor FastAPI:
```bash
uvicorn main:app --reload
```
A aplicação estará disponível em **http://localhost:8000**.

## 📁 Estrutura do Projeto
```
research-project/
├── cgu_rag/                # Pacote principal da aplicação
│   ├── __init__.py
│   ├── build_vectors.py    # Script para gerar/construir os vetores
│   ├── pipeline.py         # Classe para embeddings, FAISS e recuperação
│   └── settings.py         # Configurações do projeto (caminhos, modelos)
├── data/
│   ├── dt_pedidos.parquet  # Dataset de pedidos
│   ├── dt_recursos.parquet # Dataset de recursos
│   └── vetores/            # Saída dos índices FAISS e embeddings .pkl
├── static/                 # Arquivos do front-end (HTML, CSS, JS)
├── .env                    # Arquivo de variáveis de ambiente 
├── main.py                 # Ponto de entrada da API FastAPI
├── requirements.txt        # Dependências do Python
└── README.md               # Este arquivo
```