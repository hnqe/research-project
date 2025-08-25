# 🔧 Scripts de Indexação - MVP CGU

Este documento explica os **scripts de indexação** disponíveis no projeto, suas diferenças e quando usar cada um.

## 📋 Visão Geral

O MVP CGU possui **2 scripts principais** para indexar dados no Qdrant:

| Script | Fonte dos Dados | Uso Principal |
|--------|-----------------|---------------|
| `index_to_qdrant.py` | **Dados locais** (`./data/`) | Desenvolvimento local, dados customizados |
| `index_from_docker.py` | **Container Docker** (`mvp-data`) | Produção, dados pré-processados |

---

## 🗂️ **Script 1: `index_to_qdrant.py`**

### 📌 **Quando Usar**
- ✅ Processou dados próprios via **Jupyter Notebook**
- ✅ Tem arquivos locais na pasta `./data/`
- ✅ **Desenvolvimento** e experimentação
- ✅ Dados **customizados** ou atualizados

### 📊 **Fonte dos Dados**
```
./data/
├── dt_recursos.parquet        # Dados dos recursos
├── dt_pedidos.parquet         # Dados dos pedidos
└── vetores/
    ├── recursos_2015_2023.pkl # Embeddings dos recursos
    └── pedidos_2015_2023.pkl  # Embeddings dos pedidos
```

### 🚀 **Como Executar**
```bash
# Certifique-se que Qdrant está rodando
docker-compose up -d qdrant

# Execute indexação
python scripts/index_to_qdrant.py

# Verifique resultado
python scripts/health_check.py
```

### ⚙️ **Configuração**
- Lê dados do diretório local `./data/`
- Usa configurações do arquivo `.env`
- Cria coleções `recursos_cgu_v1` e `pedidos_cgu_v1`

---

## 🐳 **Script 2: `index_from_docker.py`**

### 📌 **Quando Usar**
- ✅ Usa **imagem Docker** `hnqe/mvp-cgu-data:latest`
- ✅ **Produção** e demonstrações
- ✅ Setup rápido sem processamento local
- ✅ Dados **padronizados** e testados

### 📊 **Fonte dos Dados**
```
Container mvp-data:/data/
├── dt_recursos.parquet        # Copiado do container
├── dt_pedidos.parquet         # Copiado do container
└── vetores/
    ├── recursos_2015_2023.pkl # Copiado do container
    └── pedidos_2015_2023.pkl  # Copiado do container
```

### 🚀 **Como Executar**
```bash
# Certifique-se que containers estão rodando
docker-compose up -d

# Execute indexação a partir do Docker
python scripts/index_from_docker.py

# Não precisa health_check - script já valida
```

### ⚙️ **Configuração**
- **Copia automaticamente** dados do container `mvp-data`
- Usa **diretório temporário** durante processamento
- **Limpa** arquivos temporários após indexação
- Requer biblioteca `docker` Python: `pip install docker`

---

## 🔍 **Diferenças Técnicas**

### **Performance**
- `index_to_qdrant.py`: Leitura direta de disco (mais rápido)
- `index_from_docker.py`: Copy + extract + indexação (overhead de Docker)

### **Dependências**
```bash
# index_to_qdrant.py
pip install pandas qdrant-client sentence-transformers

# index_from_docker.py  
pip install pandas qdrant-client sentence-transformers docker
```

### **Tamanhos de Lote**
- `index_to_qdrant.py`: 1000 registros por lote
- `index_from_docker.py`: 500 registros por lote (otimizado para stability)

### **Tratamento de Erro**
- `index_to_qdrant.py`: Básico, falha em erros críticos
- `index_from_docker.py`: Avançado, retry automático, chunks menores

---

## 📊 **Dados Indexados**

Ambos os scripts indexam:

### **Recursos (82.124 registros)**
- Decisões de recursos LAI (2015-2023)
- Embeddings 768D (`intfloat/multilingual-e5-base`)
- Metadados: ID, Decision, Instance, Description, etc.

### **Pedidos (780.084 registros)**
- Pedidos LAI originais (2015-2023)  
- Embeddings 768D (`intfloat/multilingual-e5-base`)
- Metadados: ID, Protocol, Summary, Response, etc.

---

## 🔧 **Troubleshooting**

### **Erro: "Container não encontrado"**
```bash
# Verifique se container está rodando
docker ps | grep mvp-data

# Se não estiver, inicie:
docker-compose up -d
```

### **Erro: "Arquivo não encontrado"**
```bash
# Para index_to_qdrant.py
ls -la ./data/  # Verifique se arquivos existem

# Para index_from_docker.py  
docker exec mvp-data ls -la /data  # Verifique dados no container
```

### **Timeout durante indexação**
```bash
# Opção 1: Use script otimizado
python scripts/index_from_docker.py

# Opção 2: Indexe apenas recursos
# Edite script e comente seção dos pedidos
```

### **Erro de memória**
```bash
# Reduza batch_size nos scripts
# Edite linhas com batch_size = 1000 para batch_size = 200
```

---

## 🎯 **Recomendações de Uso**

### **Para Desenvolvimento**
```bash
# 1. Processe dados no notebook
jupyter notebook ../LangChainIMPL.ipynb

# 2. Use script local
python scripts/index_to_qdrant.py
```

### **Para Demonstração/Produção**
```bash
# 1. Use imagem Docker oficial
docker-compose up -d

# 2. Use script Docker
python scripts/index_from_docker.py
```

### **Para CI/CD**
```bash
# No pipeline, sempre use imagem Docker
- name: Index Data
  run: |
    docker-compose up -d
    python scripts/index_from_docker.py
```

---

## 📝 **Logs e Monitoramento**

### **Verificar Indexação**
```bash
# Health check
curl http://localhost:6333/collections

# Contagem de registros
curl http://localhost:6333/collections/recursos_cgu_v1
curl http://localhost:6333/collections/pedidos_cgu_v1

# Via aplicação
curl http://localhost:8000/health
```

### **Logs Detalhados**
```bash
# Com logs verbose
python scripts/index_from_docker.py 2>&1 | tee indexacao.log

# Filtrar apenas erros
python scripts/index_from_docker.py 2>&1 | grep -E "(ERROR|WARN)"
```

---

**💡 Dica**: Para setup inicial rápido, sempre use `index_from_docker.py` com a imagem `hnqe/mvp-cgu-data:latest`!