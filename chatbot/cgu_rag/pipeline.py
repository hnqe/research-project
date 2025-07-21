# pipeline.py
import os
import pickle
import time

import numpy as np
import pandas as pd
from tqdm import tqdm

# LangChain core
from langchain.schema.document import Document
# FAISS vectorstore
from langchain_community.vectorstores import FAISS
# HuggingFace embeddings
from langchain_huggingface import HuggingFaceEmbeddings


class CGURecommendationPipeline:
    """
    Pipeline de recomendação para recursos de acesso à informação da CGU
    utilizando LangChain para processamento e recuperação.
    """

    def __init__(self, embedding_model_name, device="cpu"):
        """
        Inicializa o pipeline com o modelo de embeddings especificado.

        Args:
            embedding_model_name: Nome do modelo de embeddings do HuggingFace.
            device: Dispositivo para processamento ("cpu" ou "cuda").
        """
        self.embedding_model_name = embedding_model_name
        self.device = device

        # Inicializar modelo de embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_name,
            model_kwargs={"device": device}
        )

        # Armazenar vectorstores
        self.vectorstore_pedidos = None
        self.vectorstore_recursos = None

    def save_embeddings_to_pickle(self, ids, embeddings, file_path, include_metadata=None):
        """
        Salva embeddings em formato pickle para carregamento rápido.

        Args:
            ids: Lista de IDs (ProtocoloPedido ou IdRecurso).
            embeddings: Array numpy com os embeddings.
            file_path: Caminho completo para salvar o arquivo pickle.
            include_metadata: DataFrame com metadados a incluir (opcional).
        """
        embeddings_dict = {
            'ids': ids,
            'embeddings': embeddings,
            'model_name': self.embedding_model_name,
            'created_at': time.time()
        }

        if include_metadata is not None:
            metadata_dict = include_metadata.to_dict(orient='records')
            embeddings_dict['metadata'] = metadata_dict

        with open(file_path, 'wb') as f:
            pickle.dump(embeddings_dict, f)

        print(f"Embeddings salvos em {file_path}")
        print(f"Total de {len(ids)} embeddings salvos, tamanho do modelo: {embeddings.shape}")
        return file_path

    def load_embeddings_from_pickle(self, file_path):
        """
        Carrega embeddings de arquivo pickle.

        Args:
            file_path: Caminho para o arquivo pickle.

        Returns:
            Tupla (ids, embeddings, metadata).
        """
        print(f"Carregando embeddings de {file_path}...")
        start_time = time.time()

        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)

            ids = data['ids']
            embeddings = data['embeddings']
            metadata = data.get('metadata', None)
            model_name = data.get('model_name', 'unknown')

            print(f"Embeddings carregados em {time.time() - start_time:.2f} segundos")
            print(f"Modelo original: {model_name}")
            print(f"Total de {len(ids)} embeddings carregados, tamanho: {embeddings.shape}")

            if model_name != self.embedding_model_name:
                print(
                    f"AVISO: O modelo usado para gerar os embeddings ({model_name}) é diferente do atual ({self.embedding_model_name})")

            return ids, embeddings, metadata

        except Exception as e:
            print(f"Erro ao carregar embeddings: {e}")
            return None, None, None

    def generate_and_save_embeddings(self, df, text_column='sentence', id_column='ProtocoloPedido',
                                     output_path=None, batch_size=128, include_metadata=False):
        """
        Gera embeddings para textos em um DataFrame e salva em pickle.
        """
        texts = df[text_column].fillna('').astype(str).tolist()
        ids = df[id_column].tolist()

        if output_path is None:
            model_name_short = self.embedding_model_name.replace('/', '_')
            output_path = f"embeddings_{id_column}_{model_name_short}.pkl"

        print(f"Gerando embeddings para {len(texts)} textos em lotes de {batch_size}...")
        start_time = time.time()

        all_embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Gerando embeddings"):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embeddings.embed_documents(batch_texts)
            all_embeddings.extend(batch_embeddings)

        embeddings_array = np.array(all_embeddings, dtype='float32')
        print(f"Embeddings gerados em {time.time() - start_time:.2f} segundos")

        metadata_to_include = df if include_metadata else None
        self.save_embeddings_to_pickle(ids, embeddings_array, output_path, metadata_to_include)

        return ids, embeddings_array

    def build_vectorstore_from_embeddings(self, ids, embeddings, store_type='pedidos', persist_directory=None):
        """
        Constrói um vectorstore a partir de embeddings pré-calculados.
        (Refatorado para usar o método direto `FAISS.from_embeddings`)
        """
        print(f"Construindo vectorstore para {len(ids)} {store_type}...")

        # Cria pares de (texto_placeholder, embedding)
        text_embeddings = list(zip([""] * len(ids), embeddings.tolist()))

        # Cria metadados com os IDs corretos
        id_key = 'ProtocoloPedido' if store_type == 'pedidos' else 'IdRecurso'
        metadatas = [{id_key: str(id_val)} for id_val in ids]

        # Usa o método direto do FAISS, que é mais simples e eficiente
        vectorstore = FAISS.from_embeddings(
            text_embeddings=text_embeddings,
            embedding=self.embeddings,  # Fornece o embedder para futuras consultas
            metadatas=metadatas
        )

        # Salvar e armazenar (lógica mantida)
        if persist_directory:
            os.makedirs(persist_directory, exist_ok=True)
            save_path = os.path.join(persist_directory, f"{store_type}.faiss")
            vectorstore.save_local(save_path)
            print(f"Vectorstore salvo em {save_path}")

        if store_type == 'pedidos':
            self.vectorstore_pedidos = vectorstore
        elif store_type == 'recursos':
            self.vectorstore_recursos = vectorstore

        return vectorstore

    def prepare_documents_from_dataframe(self, df, text_column='sentence'):
        """
        Prepara documentos a partir de um DataFrame para uso no LangChain.
        (Refatorado para usar to_dict('records') para melhor performance)
        """
        documents = []
        # Usar to_dict é muito mais rápido que iterrows
        for record in df.to_dict('records'):
            text = record.get(text_column)
            if pd.isna(text) or text == '':
                continue

            # O metadata já é um dicionário limpo
            metadata = {k: v for k, v in record.items() if k != text_column}

            # Converte tipos numpy para tipos nativos do Python
            for key, value in metadata.items():
                if isinstance(value, np.integer):
                    metadata[key] = int(value)
                elif isinstance(value, np.floating):
                    metadata[key] = float(value)
                elif isinstance(value, np.ndarray):
                    metadata[key] = value.tolist()
                elif pd.isna(value):
                    metadata[key] = None

            doc = Document(page_content=str(text), metadata=metadata)
            documents.append(doc)

        return documents

    def create_vectorstore(self, documents, store_name="default", persist_directory=None):
        """
        Cria um vectorstore FAISS a partir de documentos LangChain.
        """
        print(f"Criando vectorstore '{store_name}' com {len(documents)} documentos...")

        vectorstore = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings
        )

        if persist_directory:
            os.makedirs(persist_directory, exist_ok=True)
            save_path = os.path.join(persist_directory, f"{store_name}.faiss")
            vectorstore.save_local(save_path)
            print(f"Vectorstore salvo em {save_path}")

        return vectorstore

    def build_pedidos_vectorstore(self, df_pedidos, persist_directory=None):
        """Constrói o vectorstore para pedidos."""
        if 'sentence' not in df_pedidos.columns:
            df_pedidos['sentence'] = (
                    df_pedidos['ResumoSolicitacao'].fillna('')
                    + ' <SEP> '
                    + df_pedidos['DetalhamentoSolicitacao'].fillna('')
            )
        documents = self.prepare_documents_from_dataframe(df_pedidos)
        self.vectorstore_pedidos = self.create_vectorstore(
            documents, store_name="pedidos", persist_directory=persist_directory
        )
        return self.vectorstore_pedidos

    def build_recursos_vectorstore(self, df_recursos, persist_directory=None):
        """Constrói o vectorstore para recursos."""
        if 'sentence' not in df_recursos.columns:
            df_recursos['sentence'] = (
                    df_recursos['TipoRecurso'].fillna('')
                    + ' <SEP> '
                    + df_recursos['DescRecurso'].fillna('')
            )
        documents = self.prepare_documents_from_dataframe(df_recursos)
        self.vectorstore_recursos = self.create_vectorstore(
            documents, store_name="recursos", persist_directory=persist_directory
        )
        return self.vectorstore_recursos

    def load_vectorstore(self, path, store_name="pedidos"):
        """Carrega um vectorstore salvo anteriormente."""
        store_path = os.path.join(path, f"{store_name}.faiss")
        if not os.path.exists(store_path):
            raise FileNotFoundError(f"Arquivo {store_path} não encontrado")

        print(f"Carregando vectorstore de {store_path}...")
        vectorstore = FAISS.load_local(
            store_path, self.embeddings, allow_dangerous_deserialization=True
        )

        if store_name == "pedidos":
            self.vectorstore_pedidos = vectorstore
        elif store_name == "recursos":
            self.vectorstore_recursos = vectorstore
        return vectorstore

    def _find_similar(self, vectorstore, id_column, df, query_text=None, query_id=None, k=10, filter_query=False):
        """
        Método privado e genérico para encontrar itens similares.
        (Refatorado para unificar a lógica de busca)
        """
        if vectorstore is None:
            raise ValueError("Vectorstore não inicializado para a busca.")

        if query_id is not None:
            query_id = str(query_id)
            if df is None:
                raise ValueError("DataFrame é necessário quando query_id é fornecido.")

            item = df[df[id_column].astype(str) == query_id]
            if item.empty:
                raise ValueError(f"Item com ID {query_id} na coluna {id_column} não encontrado.")
            query_text = item['sentence'].iloc[0]

        if query_text is None:
            raise ValueError("É necessário fornecer query_text ou query_id + df")

        search_k = k + 1 if filter_query and query_id is not None else k
        docs_with_scores = vectorstore.similarity_search_with_score(query=query_text, k=search_k)

        if filter_query and query_id is not None:
            docs_with_scores = [
                                   (doc, score) for doc, score in docs_with_scores
                                   if str(doc.metadata.get(id_column)) != query_id
                               ][:k]

        results = []
        for doc, score in docs_with_scores:
            meta = doc.metadata.copy()
            meta['score'] = score
            meta['page_content'] = doc.page_content
            results.append(meta)

        results_df = pd.DataFrame(results)
        docs = [doc for doc, _ in docs_with_scores]
        return docs, results_df

    def find_similar_pedidos(self, query_text=None, query_id=None, df_pedidos=None, k=10, filter_query=False):
        """Encontra pedidos similares a partir de um texto ou ID."""
        return self._find_similar(
            vectorstore=self.vectorstore_pedidos,
            id_column='ProtocoloPedido',
            df=df_pedidos,
            query_text=query_text,
            query_id=query_id,
            k=k,
            filter_query=filter_query
        )

    def find_similar_recursos(self, query_text=None, query_id=None, df_recursos=None, k=10, filter_query=False):
        """Encontra recursos similares a partir de um texto ou ID."""
        return self._find_similar(
            vectorstore=self.vectorstore_recursos,
            id_column='IdRecurso',
            df=df_recursos,
            query_text=query_text,
            query_id=query_id,
            k=k,
            filter_query=filter_query
        )

    def batch_similar_search(self, query_ids, df, vectorstore_type='pedidos', k=10):
        """Realiza busca em lote para vários IDs."""
        all_results = []
        id_field = 'ProtocoloPedido' if vectorstore_type == 'pedidos' else 'IdRecurso'

        for qid in tqdm(query_ids, desc=f"Buscando similares para {len(query_ids)} {vectorstore_type}"):
            try:
                if vectorstore_type == 'pedidos':
                    _, results = self.find_similar_pedidos(
                        query_id=qid, df_pedidos=df, k=k, filter_query=True
                    )
                else:
                    _, results = self.find_similar_recursos(
                        query_id=qid, df_recursos=df, k=k, filter_query=True
                    )

                if not results.empty:
                    results['query_id'] = qid
                    results = results[['query_id', id_field, 'score', 'page_content']]
                    all_results.append(results)

            except Exception as e:
                print(f"Erro ao processar {vectorstore_type} {qid}: {e}")

        return pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()

    def evaluate_with_annotated_data(self, df_annotated, df_pedidos, k_values=[1, 5, 10, 20, 50, 100]):
        """Avalia o desempenho do pipeline usando dados anotados."""
        if self.vectorstore_pedidos is None:
            raise ValueError("Vectorstore de pedidos não inicializado")

        results = []
        unique_queries = df_annotated['NUP'].unique()
        print(f"Avaliando {len(unique_queries)} consultas com {len(df_annotated)} pares anotados")

        for k in k_values:
            hits = 0
            total_pairs = 0
            for query_nup in tqdm(unique_queries, desc=f"Avaliando com k={k}"):
                similar_nups = set(df_annotated[df_annotated['NUP'] == query_nup]['NUP_semelhante'])
                if not similar_nups:
                    continue

                try:
                    _, results_df = self.find_similar_pedidos(
                        query_id=query_nup, df_pedidos=df_pedidos, k=k, filter_query=True
                    )
                    predicted_nups = set(results_df['ProtocoloPedido'])
                    hits += len(similar_nups.intersection(predicted_nups))
                    total_pairs += len(similar_nups)
                except ValueError as e:
                    print(f"Aviso: Ignorando query {query_nup} durante avaliação: {e}")

            recall = hits / total_pairs if total_pairs > 0 else 0
            results.append({'k': k, 'hits': hits, 'total_annotated_pairs': total_pairs, 'recall_at_k': recall})

        return pd.DataFrame(results)