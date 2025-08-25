import React, { useState } from 'react';
import { Search, FileText, AlertCircle, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'react-toastify';

import Button from './ui/Button';
import Card from './ui/Card';
import Input from './ui/Input';
import Badge from './ui/Badge';
import { apiService } from '../services/api';

const AppealSearch = () => {
  const [appealId, setAppealId] = useState('');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState([]);
  const [originalAppeal, setOriginalAppeal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedResponses, setExpandedResponses] = useState({});

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!appealId.trim()) {
      setError('Por favor, informe um ID de recurso');
      return;
    }

    setLoading(true);
    setResults([]);
    setOriginalAppeal(null);
    setError('');

    try {
      const data = await apiService.findSimilarAppeals(appealId.trim(), topK);
      
      // Verificar se a resposta tem a estrutura esperada
      if (!data || !data.similar_appeals) {
        throw new Error('Resposta da API inválida');
      }
      
      if (data.similar_appeals.length === 0) {
        toast.info('Nenhum recurso similar encontrado para este ID');
      } else {
        toast.success(`${data.similar_appeals.length} recursos similares encontrados!`);
      }
      
      setOriginalAppeal(data.original_appeal);
      setResults(data.similar_appeals);
    } catch (error) {
      console.error('Erro na busca por recurso:', error);
      
      if (error.response?.status === 404) {
        setError(`Recurso com ID '${appealId}' não encontrado na base de dados`);
        toast.error('Recurso não encontrado');
      } else {
        setError('Erro ao realizar busca. Tente novamente.');
        toast.error(error.response?.data?.detail || 'Erro ao buscar recurso');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAppealIdChange = (e) => {
    setAppealId(e.target.value);
    if (error) setError('');
  };

  const formatResponse = (response) => {
    // Trata respostas vazias, nulas ou apenas com espaços
    if (!response || response.trim() === '') {
      return 'Resposta não disponível no sistema';
    }
    return response.trim();
  };

  const getResponseStyle = (response) => {
    // Estilo diferente para respostas indisponíveis
    if (!response || response.trim() === '') {
      return 'text-sm text-gray-400 leading-relaxed bg-gray-50 p-3 rounded border border-gray-200 italic flex items-center';
    }
    return 'text-sm text-gray-600 leading-relaxed bg-white p-3 rounded border';
  };

  const getOriginalResponseStyle = (response) => {
    // Estilo diferente para respostas indisponíveis na seção verde
    if (!response || response.trim() === '') {
      return 'text-sm text-green-400 leading-relaxed bg-green-25 p-3 rounded border border-green-200 italic flex items-center';
    }
    return 'text-sm text-green-700 leading-relaxed bg-white p-3 rounded border border-green-200';
  };

  const getDecisionBadgeVariant = (decision) => {
    if (decision === 'Deferido') return 'success';
    if (decision === 'Indeferido') return 'danger';
    if (decision === 'Parcialmente Deferido') return 'warning';
    if (decision === 'Não conhecimento') return 'default';
    if (decision === 'Perda de objeto') return 'default';
    return 'default';
  };

  const toggleResponseExpansion = (appealId) => {
    setExpandedResponses(prev => ({
      ...prev,
      [appealId]: !prev[appealId]
    }));
  };

  const renderExpandableText = (text, appealId, maxLength = 500) => {
    const isExpanded = expandedResponses[appealId];
    const shouldTruncate = text.length > maxLength;
    
    if (!shouldTruncate) {
      return <span>{text}</span>;
    }

    return (
      <div>
        <span>
          {isExpanded ? text : `${text.substring(0, maxLength)}...`}
        </span>
        <button
          onClick={() => toggleResponseExpansion(appealId)}
          className="ml-2 text-primary-600 hover:text-primary-800 text-xs font-medium inline-flex items-center"
        >
          {isExpanded ? (
            <>
              Ver menos <ChevronUp className="w-3 h-3 ml-1" />
            </>
          ) : (
            <>
              Ver mais <ChevronDown className="w-3 h-3 ml-1" />
            </>
          )}
        </button>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      {/* Formulário de Busca */}
      <Card>
        <Card.Header>
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <FileText className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Busca por Recurso</h2>
              <p className="text-sm text-gray-500">
                Encontre recursos similares a partir de um ID de recurso específico
              </p>
            </div>
          </div>
        </Card.Header>
        
        <Card.Content>
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <Input
                  label="ID do Recurso *"
                  value={appealId}
                  onChange={handleAppealIdChange}
                  placeholder="Ex: 12345"
                  error={error}
                  helperText="Informe o ID numérico do recurso"
                />
              </div>

              <Input
                label="Quantidade de Similares"
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                helperText="Máximo de recursos similares (1-20)"
              />
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                loading={loading}
                disabled={loading || !appealId.trim()}
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

      {/* Recurso Original */}
      {originalAppeal && (
        <Card>
          <Card.Header>
            <h3 className="text-lg font-semibold text-green-900 flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
              Recurso Consultado: ID {originalAppeal.id}
            </h3>
          </Card.Header>
          <Card.Content>
            <div className="bg-green-50 border border-green-200 rounded-lg p-6">
              {/* Cabeçalho do Recurso Original */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <Badge variant="default" size="sm" className="bg-green-100 text-green-800">
                    ORIGINAL
                  </Badge>
                  <div className="font-mono text-sm text-green-700 font-semibold">
                    ID: {originalAppeal.id}
                  </div>
                  <Badge 
                    variant={getDecisionBadgeVariant(originalAppeal.decision)}
                    size="sm"
                  >
                    {originalAppeal.decision}
                  </Badge>
                  <span className="text-sm text-green-600">
                    {originalAppeal.instance}
                  </span>
                </div>
              </div>

              {/* Conteúdo do Recurso Original */}
              <div className="space-y-4">
                {/* Descrição */}
                <div>
                  <h4 className="text-sm font-semibold text-green-700 mb-2 flex items-center">
                    <FileText className="w-4 h-4 mr-1" />
                    Descrição do Recurso
                  </h4>
                  <p className={getOriginalResponseStyle(originalAppeal.description)}>
                    {!originalAppeal.description || originalAppeal.description.trim() === '' ? (
                      <>
                        <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                        {formatResponse(originalAppeal.description)}
                      </>
                    ) : (
                      formatResponse(originalAppeal.description)
                    )}
                  </p>
                </div>

                {/* Resposta */}
                {originalAppeal.response && originalAppeal.response !== originalAppeal.description && (
                  <div>
                    <h4 className="text-sm font-semibold text-green-700 mb-2">
                      Resposta Oficial
                    </h4>
                    <p className="text-sm text-green-700 leading-relaxed bg-white p-3 rounded border border-green-200">
                      {renderExpandableText(originalAppeal.response, `original-${originalAppeal.id}`, 500)}
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
              Recursos Similares Encontrados ({results.length})
            </h3>
          </Card.Header>
          <Card.Content>
            <div className="space-y-6">
              {results.map((appeal, index) => (
                <div key={appeal.id} className="border rounded-lg p-6 bg-gray-50 hover:bg-gray-100 transition-colors">
                  {/* Cabeçalho do Recurso */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <Badge variant="default" size="sm">
                        #{index + 1}
                      </Badge>
                      <div className="font-mono text-sm text-gray-600">
                        ID: {appeal.id}
                      </div>
                      <Badge 
                        variant={getDecisionBadgeVariant(appeal.decision)}
                        size="sm"
                      >
                        {appeal.decision}
                      </Badge>
                      <span className="text-sm text-gray-600">
                        {appeal.instance}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        Similaridade: {(appeal.score * 100).toFixed(1)}%
                      </div>
                      <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                        <div 
                          className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${appeal.score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  {/* Conteúdo do Recurso */}
                  <div className="space-y-4">
                    {/* Descrição */}
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                        <FileText className="w-4 h-4 mr-1" />
                        Descrição do Recurso
                      </h4>
                      <p className={getResponseStyle(appeal.description)}>
                        {!appeal.description || appeal.description.trim() === '' ? (
                          <>
                            <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                            {formatResponse(appeal.description)}
                          </>
                        ) : (
                          formatResponse(appeal.description)
                        )}
                      </p>
                    </div>

                    {/* Resposta */}
                    {appeal.response && appeal.response !== appeal.description && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">
                          Resposta Oficial
                        </h4>
                        <p className="text-sm text-gray-600 leading-relaxed bg-white p-3 rounded border">
                          {renderExpandableText(appeal.response, `similar-${appeal.id}`, 500)}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Rodapé */}
                  <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                      <span>ID: {appeal.id}</span>
                      <span>•</span>
                      <span>Score: {appeal.score.toFixed(4)}</span>
                    </div>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(appeal.id.toString());
                        toast.success('ID do recurso copiado!');
                      }}
                    >
                      <ExternalLink className="w-3 h-3 mr-1" />
                      Copiar ID
                    </Button>
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
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhuma busca realizada</h3>
              <p className="mt-1 text-sm text-gray-500">
                Digite um ID de recurso acima para encontrar recursos similares
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
              <h3 className="mt-2 text-sm font-medium text-gray-900">Recurso não encontrado</h3>
              <p className="mt-1 text-sm text-gray-500">
                {error}
              </p>
              <div className="mt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setError('');
                    setAppealId('');
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

export default AppealSearch;