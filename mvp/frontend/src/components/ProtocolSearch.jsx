import React, { useState } from 'react';
import { Search, FileSearch, AlertCircle, ExternalLink } from 'lucide-react';
import { toast } from 'react-toastify';

import Button from './ui/Button';
import Card from './ui/Card';
import Input from './ui/Input';
import Badge from './ui/Badge';
import { apiService } from '../services/api';

const ProtocolSearch = () => {
  const [protocolId, setProtocolId] = useState('');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState([]);
  const [originalRequest, setOriginalRequest] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!protocolId.trim()) {
      setError('Por favor, informe um número de protocolo');
      return;
    }

    setLoading(true);
    setResults([]);
    setOriginalRequest(null);
    setError('');

    try {
      const data = await apiService.findSimilarRequests(protocolId.trim(), topK);
      
      // Verificar se a resposta tem a estrutura esperada
      if (!data || !data.similar_requests) {
        throw new Error('Resposta da API inválida');
      }
      
      if (data.similar_requests.length === 0) {
        toast.info('Nenhum pedido similar encontrado para este protocolo');
      } else {
        toast.success(`${data.similar_requests.length} pedidos similares encontrados!`);
      }
      
      setOriginalRequest(data.original_request);
      setResults(data.similar_requests);
    } catch (error) {
      console.error('Erro na busca por protocolo:', error);
      
      if (error.response?.status === 404) {
        setError(`Protocolo '${protocolId}' não encontrado na base de dados`);
        toast.error('Protocolo não encontrado');
      } else {
        setError('Erro ao realizar busca. Tente novamente.');
        toast.error(error.response?.data?.detail || 'Erro ao buscar protocolo');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleProtocolChange = (e) => {
    setProtocolId(e.target.value);
    if (error) setError('');
  };

  const formatProtocol = (protocol) => {
    // Formata protocolos no padrão brasileiro se possível
    if (protocol && protocol.length > 10) {
      return protocol;
    }
    return protocol;
  };

  const formatSummary = (summary) => {
    // Trata resumos vazios, nulos ou apenas com espaços
    if (!summary || summary.trim() === '') {
      return 'Resumo não disponível no sistema';
    }
    return summary.trim();
  };

  const getSummaryStyle = (summary) => {
    // Estilo diferente para resumos indisponíveis
    if (!summary || summary.trim() === '') {
      return 'text-sm text-gray-400 leading-relaxed bg-gray-50 p-3 rounded border border-gray-200 italic flex items-center';
    }
    return 'text-sm text-gray-600 leading-relaxed bg-white p-3 rounded border';
  };

  const getOriginalSummaryStyle = (summary) => {
    // Estilo diferente para resumos indisponíveis na seção azul
    if (!summary || summary.trim() === '') {
      return 'text-sm text-blue-400 leading-relaxed bg-blue-25 p-3 rounded border border-blue-200 italic flex items-center';
    }
    return 'text-sm text-blue-700 leading-relaxed bg-white p-3 rounded border border-blue-200';
  };

  const getDecisionBadgeVariant = (decision) => {
    if (decision === 'Deferido') return 'success';
    if (decision === 'Indeferido') return 'danger';
    if (decision === 'Parcialmente Deferido') return 'warning';
    return 'default';
  };

  return (
    <div className="space-y-8">
      {/* Formulário de Busca */}
      <Card>
        <Card.Header>
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <FileSearch className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Busca por Protocolo</h2>
              <p className="text-sm text-gray-500">
                Encontre pedidos similares a partir de um número de protocolo específico
              </p>
            </div>
          </div>
        </Card.Header>
        
        <Card.Content>
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <Input
                  label="Número do Protocolo *"
                  value={protocolId}
                  onChange={handleProtocolChange}
                  placeholder="Ex: 60110003084201855"
                  error={error}
                  helperText="Informe o número completo do protocolo"
                />
              </div>

              <Input
                label="Quantidade de Similares"
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                helperText="Máximo de pedidos similares (1-20)"
              />
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                loading={loading}
                disabled={loading || !protocolId.trim()}
                size="lg"
                className="min-w-32"
              >
                {loading ? 'Buscando...' : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    Buscar
                  </>
                )}
              </Button>
            </div>
          </form>
        </Card.Content>
      </Card>

      {/* Protocolo Original */}
      {originalRequest && (
        <Card>
          <Card.Header>
            <h3 className="text-lg font-semibold text-blue-900 flex items-center">
              <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
              Protocolo Consultado: {formatProtocol(originalRequest.protocol)}
            </h3>
          </Card.Header>
          <Card.Content>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              {/* Cabeçalho do Protocolo Original */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <Badge variant="default" size="sm" className="bg-blue-100 text-blue-800">
                    ORIGINAL
                  </Badge>
                  <div className="font-mono text-sm text-blue-700 font-semibold">
                    {formatProtocol(originalRequest.protocol)}
                  </div>
                  <Badge 
                    variant={getDecisionBadgeVariant(originalRequest.decision)}
                    size="sm"
                  >
                    {originalRequest.decision}
                  </Badge>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-blue-900">
                    ID: {originalRequest.id}
                  </div>
                </div>
              </div>

              {/* Conteúdo do Protocolo Original */}
              <div className="space-y-4">
                {/* Resumo */}
                <div>
                  <h4 className="text-sm font-semibold text-blue-700 mb-2 flex items-center">
                    <FileSearch className="w-4 h-4 mr-1" />
                    Resumo da Solicitação
                  </h4>
                  <p className={getOriginalSummaryStyle(originalRequest.summary)}>
                    {!originalRequest.summary || originalRequest.summary.trim() === '' ? (
                      <>
                        <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                        {formatSummary(originalRequest.summary)}
                      </>
                    ) : (
                      formatSummary(originalRequest.summary)
                    )}
                  </p>
                </div>

                {/* Detalhes */}
                {originalRequest.details && originalRequest.details !== originalRequest.summary && (
                  <div>
                    <h4 className="text-sm font-semibold text-blue-700 mb-2">
                      Detalhamento
                    </h4>
                    <p className="text-sm text-blue-700 leading-relaxed bg-white p-3 rounded border border-blue-200">
                      {originalRequest.details.length > 500 
                        ? `${originalRequest.details.substring(0, 500)}...` 
                        : originalRequest.details
                      }
                    </p>
                  </div>
                )}
              </div>
            </div>
          </Card.Content>
        </Card>
      )}

      {/* Resultados da Busca */}
      {results.length > 0 && (
        <Card>
          <Card.Header>
            <h3 className="text-lg font-semibold text-gray-900">
              Pedidos Similares Encontrados ({results.length})
            </h3>
          </Card.Header>
          <Card.Content>
            <div className="space-y-6">
              {results.map((request, index) => (
                <div key={request.id} className="border rounded-lg p-6 bg-gray-50 hover:bg-gray-100 transition-colors">
                  {/* Cabeçalho do Pedido */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <Badge variant="default" size="sm">
                        #{index + 1}
                      </Badge>
                      <div className="bg-blue-100 px-3 py-1 rounded-md">
                        <span className="text-xs text-blue-600 font-medium">PROTOCOLO: </span>
                        <span className="font-mono text-sm font-bold text-blue-800">
                          {formatProtocol(request.protocol)}
                        </span>
                      </div>
                      <Badge 
                        variant={getDecisionBadgeVariant(request.decision)}
                        size="sm"
                      >
                        {request.decision}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        Similaridade: {(request.score * 100).toFixed(1)}%
                      </div>
                      <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                        <div 
                          className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${request.score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  {/* Conteúdo do Pedido */}
                  <div className="space-y-4">
                    {/* Resumo */}
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                        <FileSearch className="w-4 h-4 mr-1" />
                        Resumo da Solicitação
                      </h4>
                      <p className={getSummaryStyle(request.summary)}>
                        {!request.summary || request.summary.trim() === '' ? (
                          <>
                            <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                            {formatSummary(request.summary)}
                          </>
                        ) : (
                          formatSummary(request.summary)
                        )}
                      </p>
                    </div>

                    {/* Detalhes */}
                    {request.details && request.details !== request.summary && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">
                          Detalhamento
                        </h4>
                        <p className="text-sm text-gray-600 leading-relaxed bg-white p-3 rounded border">
                          {request.details.length > 500 
                            ? `${request.details.substring(0, 500)}...` 
                            : request.details
                          }
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Rodapé */}
                  <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                      <span>ID: {request.id}</span>
                      <span>•</span>
                      <span>Score: {request.score.toFixed(4)}</span>
                    </div>
                    
                    {request.protocol && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(request.protocol);
                          toast.success('Protocolo copiado!');
                        }}
                      >
                        <ExternalLink className="w-3 h-3 mr-1" />
                        Copiar Protocolo
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card.Content>
        </Card>
      )}

      {/* Estado Vazio */}
      {results.length === 0 && !loading && !error && (
        <Card>
          <Card.Content>
            <div className="text-center py-12">
              <FileSearch className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhuma busca realizada</h3>
              <p className="mt-1 text-sm text-gray-500">
                Digite um número de protocolo acima para encontrar pedidos similares
              </p>
            </div>
          </Card.Content>
        </Card>
      )}

      {/* Estado de Erro */}
      {error && !loading && (
        <Card>
          <Card.Content>
            <div className="text-center py-12">
              <AlertCircle className="mx-auto h-12 w-12 text-danger-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Protocolo não encontrado</h3>
              <p className="mt-1 text-sm text-gray-500">
                {error}
              </p>
              <div className="mt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setError('');
                    setProtocolId('');
                    setResults([]);
                  }}
                >
                  Tentar novamente
                </Button>
              </div>
            </div>
          </Card.Content>
        </Card>
      )}
    </div>
  );
};

export default ProtocolSearch;