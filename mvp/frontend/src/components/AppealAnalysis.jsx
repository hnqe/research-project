import React, { useState, useEffect } from 'react';
import { Search, FileText, Brain, Clock, AlertTriangle, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { toast } from 'react-toastify';

import Button from './ui/Button';
import Card from './ui/Card';
import Input from './ui/Input';
import Textarea from './ui/Textarea';
import Select from './ui/Select';
import Badge from './ui/Badge';
import { apiService } from '../services/api';

const AppealAnalysis = () => {
  const [formData, setFormData] = useState({
    text: '',
    top_k: 10,
    instance_filter: '',
    min_score: 0.0
  });

  const [instances, setInstances] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [includeDraft, setIncludeDraft] = useState(false);
  const [errors, setErrors] = useState({});
  const [expandedResponses, setExpandedResponses] = useState({});

  // Carregar instâncias disponíveis
  useEffect(() => {
    const loadInstances = async () => {
      try {
        const instanceList = await apiService.getInstances();
        setInstances(instanceList);
      } catch (error) {
        console.error('Erro ao carregar instâncias:', error);
        toast.error('Erro ao carregar lista de instâncias');
      }
    };

    loadInstances();
  }, []);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.text.trim()) {
      newErrors.text = 'O texto do recurso é obrigatório';
    } else if (formData.text.length < 10) {
      newErrors.text = 'O texto deve ter pelo menos 10 caracteres';
    } else if (formData.text.length > 5000) {
      newErrors.text = 'O texto deve ter no máximo 5000 caracteres';
    }

    if (formData.top_k < 1 || formData.top_k > 50) {
      newErrors.top_k = 'O número de casos similares deve estar entre 1 e 50';
    }

    if (formData.min_score < 0 || formData.min_score > 1) {
      newErrors.min_score = 'O score mínimo deve estar entre 0.0 e 1.0';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      toast.error('Por favor, corrija os erros no formulário');
      return;
    }

    setLoading(true);
    setResults(null);

    try {
      let result;
      
      if (includeDraft) {
        result = await apiService.analyzeAppealWithDraft(formData);
        toast.success('Análise com minuta gerada com sucesso!');
      } else {
        result = await apiService.analyzeAppeal(formData);
        toast.success('Análise realizada com sucesso!');
      }
      
      setResults(result);
    } catch (error) {
      console.error('Erro na análise:', error);
      
      if (error.response?.status === 404) {
        toast.error('Nenhum recurso similar encontrado com os critérios especificados');
      } else if (error.response?.status === 501) {
        toast.error('Funcionalidade de geração de minutas não disponível. Configure a API Key do Groq.');
        setIncludeDraft(false);
      } else {
        toast.error(error.response?.data?.detail || 'Erro ao realizar análise');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'top_k' ? parseInt(value) || 1 : 
              name === 'min_score' ? parseFloat(value) || 0 : 
              value
    }));
    
    // Limpar erro específico quando usuário começa a digitar
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const getDecisionBadgeVariant = (decision) => {
    if (decision.includes('Deferido')) return 'success';
    if (decision.includes('Indeferido')) return 'danger';
    if (decision.includes('Provavelmente')) return 'warning';
    return 'default';
  };

  const toggleResponseExpansion = (appealId) => {
    setExpandedResponses(prev => ({
      ...prev,
      [appealId]: !prev[appealId]
    }));
  };

  const renderExpandableText = (text, appealId, maxLength = 300) => {
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

  const downloadMinuta = async () => {
    if (!results?.draft_response) return;
    
    try {
      // Preparar dados para envio ao backend
      const minutaData = {
        appeal_text: formData.text,
        draft_response: results.draft_response,
        likely_decision: results.likely_decision,
        decision_stats: results.decision_stats || {},
        generation_metadata: results.generation_metadata || {},
        similar_appeals_count: results.similar_appeals?.length || 0
      };

      // Fazer requisição para o backend
      const response = await apiService.downloadMinuta(minutaData);
      
      // Extrair nome do arquivo do cabeçalho Content-Disposition
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'Minuta_CGU_LAI.txt';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Converter blob para texto antes de criar data URI
      let textData;
      if (response.data instanceof Blob) {
        textData = await response.data.text();
      } else {
        textData = response.data;
      }
      
      const encodedContent = encodeURIComponent(textData);
      const dataUri = `data:text/plain;charset=utf-8,${encodedContent}`;
      
      // Criar elemento de download
      const link = document.createElement('a');
      link.href = dataUri;
      link.download = filename;
      link.style.display = 'none';
      
      // Adicionar ao DOM, clicar e remover
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast.success('Minuta baixada com sucesso!');
    } catch (error) {
      console.error('Erro ao baixar minuta:', error);
      toast.error('Erro ao baixar a minuta');
    }
  };

  return (
    <div className="space-y-8">
      {/* Formulário de Análise */}
      <Card>
        <Card.Header>
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <Brain className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Análise de Recurso LAI</h2>
              <p className="text-sm text-gray-500">
                Utilize IA para analisar recursos e obter predições baseadas em casos similares
              </p>
            </div>
          </div>
        </Card.Header>
        
        <Card.Content>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Texto do Recurso */}
            <Textarea
              label="Texto do Recurso *"
              name="text"
              value={formData.text}
              onChange={handleInputChange}
              placeholder="Cole aqui o texto completo do recurso a ser analisado..."
              rows={6}
              error={errors.text}
              helperText={`${formData.text.length}/5000 caracteres`}
            />

            {/* Configurações Avançadas */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Input
                label="Casos Similares"
                name="top_k"
                type="number"
                value={formData.top_k}
                onChange={handleInputChange}
                min="1"
                max="50"
                error={errors.top_k}
                helperText="Máximo de casos similares (1-50)"
              />

              <Select
                label="Filtrar por Instância"
                name="instance_filter"
                value={formData.instance_filter}
                onChange={handleInputChange}
                helperText="Opcional: filtrar por órgão específico"
              >
                <option value="">Todas as instâncias</option>
                {instances.map(instance => (
                  <option key={instance} value={instance}>
                    {instance}
                  </option>
                ))}
              </Select>

              <Input
                label="Score Mínimo"
                name="min_score"
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={formData.min_score}
                onChange={handleInputChange}
                error={errors.min_score}
                helperText="Similaridade mínima (0.0-1.0)"
              />
            </div>

            {/* Opções de Geração */}
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="includeDraft"
                checked={includeDraft}
                onChange={(e) => setIncludeDraft(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label htmlFor="includeDraft" className="text-sm font-medium text-gray-700">
                Gerar minuta de resposta automaticamente
              </label>
              <div className="flex items-center space-x-1">
                <Clock className="h-4 w-4 text-gray-400" />
                <span className="text-xs text-gray-500">+30-60s</span>
              </div>
            </div>

            {/* Botão de Análise */}
            <div className="flex justify-end">
              <Button
                type="submit"
                loading={loading}
                disabled={loading}
                size="lg"
                className="min-w-40"
              >
                {loading ? (includeDraft ? 'Analisando e Gerando...' : 'Analisando...') : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    {includeDraft ? 'Analisar + Gerar Minuta' : 'Analisar Recurso'}
                  </>
                )}
              </Button>
            </div>
          </form>
        </Card.Content>
      </Card>

      {/* Resultados da Análise */}
      {results && (
        <div className="space-y-6">
          {/* Predição e Estatísticas */}
          <Card>
            <Card.Header>
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Brain className="w-5 h-5 mr-2 text-primary-600" />
                Predição da IA
              </h3>
            </Card.Header>
            <Card.Content>
              <div className="space-y-4">
                <div className="text-center p-6 bg-gray-50 rounded-lg">
                  <Badge 
                    variant={getDecisionBadgeVariant(results.likely_decision)}
                    size="lg"
                    className="text-base px-4 py-2"
                  >
                    {results.likely_decision}
                  </Badge>
                </div>

                {/* Estatísticas por Decisão */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(results.decision_stats).map(([decision, stats]) => (
                    <div key={decision} className="bg-white border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">{decision}</span>
                        <Badge 
                          variant={decision.includes('Deferido') ? 'success' : 'danger'}
                          size="sm"
                        >
                          {stats.count} casos
                        </Badge>
                      </div>
                      <div className="mt-2">
                        <div className="text-2xl font-bold text-gray-900">
                          {stats.percentage.toFixed(1)}%
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className={`h-2 rounded-full ${
                              decision.includes('Deferido') ? 'bg-success-500' : 'bg-danger-500'
                            }`}
                            style={{ width: `${stats.percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card.Content>
          </Card>

          {/* Minuta Gerada (se disponível) */}
          {results.draft_response && (
            <Card>
              <Card.Header>
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <FileText className="w-5 h-5 mr-2 text-primary-600" />
                    Minuta Gerada pela IA
                  </h3>
                  <div className="flex items-center space-x-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={downloadMinuta}
                      className="flex items-center"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Baixar Minuta
                    </Button>
                    <Badge variant="warning" size="sm">
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Requer Revisão
                    </Badge>
                  </div>
                </div>
              </Card.Header>
              <Card.Content>
                <div className="bg-gray-50 border rounded-lg p-4">
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                    {results.draft_response}
                  </pre>
                </div>
                
                {/* Metadados da Geração */}
                {results.generation_metadata && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Informações da Geração</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                      {Object.entries(results.generation_metadata).map(([key, value]) => (
                        <div key={key}>
                          <span className="font-medium capitalize">
                            {key.replace('_', ' ')}:
                          </span>
                          <span className="ml-1">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card.Content>
            </Card>
          )}

          {/* Casos Similares */}
          {results.similar_appeals && results.similar_appeals.length > 0 && (
            <Card>
              <Card.Header>
                <h3 className="text-lg font-semibold text-gray-900">
                  Casos Similares Encontrados ({results.similar_appeals.length})
                </h3>
              </Card.Header>
              <Card.Content>
                <div className="space-y-4">
                  {results.similar_appeals.map((appeal, index) => (
                    <div key={appeal.id} className="border rounded-lg p-4 bg-gray-50">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <Badge variant="default" size="sm">
                            ID: {appeal.id}
                          </Badge>
                          <Badge 
                            variant={appeal.decision.includes('Deferido') ? 'success' : 'danger'}
                            size="sm"
                          >
                            {appeal.decision}
                          </Badge>
                          <span className="text-sm text-gray-600">
                            {appeal.instance}
                          </span>
                        </div>
                        <div className="text-sm font-mono text-gray-500">
                          Similaridade: {(appeal.score * 100).toFixed(1)}%
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-1">Descrição:</h4>
                          <p className="text-sm text-gray-600 leading-relaxed">
                            {appeal.description}
                          </p>
                        </div>

                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-1">Resposta:</h4>
                          <p className="text-sm text-gray-600 leading-relaxed">
                            {renderExpandableText(appeal.response, `response-${appeal.id}`, 300)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Content>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

export default AppealAnalysis;