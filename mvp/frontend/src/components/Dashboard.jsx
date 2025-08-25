import React, { useState, useEffect } from 'react';
import { Activity, Database, Brain, Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'react-toastify';

import Button from './ui/Button';
import Card from './ui/Card';
import Badge from './ui/Badge';
import { apiService } from '../services/api';

const Dashboard = () => {
  const [healthData, setHealthData] = useState(null);
  const [appInfo, setAppInfo] = useState(null);
  const [minutaStatus, setMinutaStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [health, info, minuta] = await Promise.all([
        apiService.getHealthCheck(),
        apiService.getAppInfo(),
        apiService.getMinutaStatus()
      ]);

      setHealthData(health);
      setAppInfo(info);
      setMinutaStatus(minuta);
    } catch (error) {
      console.error('Erro ao carregar dados do dashboard:', error);
      toast.error('Erro ao carregar dados do sistema');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <Card.Content>
              <div className="animate-pulse space-y-4">
                <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                <div className="space-y-2">
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                </div>
              </div>
            </Card.Content>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {appInfo?.message || 'MVP CGU - Análise de Recursos LAI'}
        </h1>
        <p className="text-gray-600">
          Sistema de análise inteligente para recursos da Lei de Acesso à Informação
        </p>
        <div className="flex justify-center items-center space-x-2 mt-4">
          <Badge variant="primary" size="sm">
            Versão {appInfo?.version || '1.0.0'}
          </Badge>
          <Badge 
            variant={healthData?.status === 'ok' ? 'success' : 'danger'}
            size="sm"
          >
            {healthData?.status === 'ok' ? 'Sistema Online' : 'Sistema Offline'}
          </Badge>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Status da Conexão */}
        <Card>
          <Card.Content>
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Database className={`h-8 w-8 ${
                  healthData?.qdrant_connection ? 'text-success-500' : 'text-danger-500'
                }`} />
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">Base de Dados</h3>
                <p className="text-sm text-gray-600">
                  {healthData?.qdrant_connection ? 'Conectado' : 'Desconectado'}
                </p>
              </div>
            </div>
          </Card.Content>
        </Card>

        {/* Geração de Minutas */}
        <Card>
          <Card.Content>
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Brain className={`h-8 w-8 ${
                  minutaStatus?.available ? 'text-success-500' : 'text-warning-500'
                }`} />
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">IA Generativa</h3>
                <p className="text-sm text-gray-600">
                  {minutaStatus?.available ? 'Disponível' : 'Indisponível'}
                </p>
              </div>
            </div>
          </Card.Content>
        </Card>

        {/* Análise Preditiva */}
        <Card>
          <Card.Content>
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Activity className="h-8 w-8 text-primary-500" />
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">Análise Preditiva</h3>
                <p className="text-sm text-gray-600">
                  {appInfo?.features?.analise_preditiva ? 'Ativa' : 'Inativa'}
                </p>
              </div>
            </div>
          </Card.Content>
        </Card>
      </div>

      {/* Informações Detalhadas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Estatísticas da Base de Dados */}
        <Card>
          <Card.Header>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Database className="w-5 h-5 mr-2 text-primary-600" />
              Base de Dados
            </h3>
          </Card.Header>
          <Card.Content>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <span className="text-sm font-medium text-gray-700">Recursos (Appeals)</span>
                <Badge variant="primary" size="sm">
                  {healthData?.recursos_count?.toLocaleString() || '0'} registros
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <span className="text-sm font-medium text-gray-700">Pedidos (Requests)</span>
                <Badge variant="primary" size="sm">
                  {healthData?.pedidos_count?.toLocaleString() || '0'} registros
                </Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <span className="text-sm font-medium text-gray-700">Modelo de Embedding</span>
                <span className="text-sm text-gray-600 font-mono">
                  {healthData?.config?.model_name || 'N/A'}
                </span>
              </div>
            </div>
          </Card.Content>
        </Card>

        {/* Status da IA Generativa */}
        <Card>
          <Card.Header>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Brain className="w-5 h-5 mr-2 text-primary-600" />
              Geração de Minutas
            </h3>
          </Card.Header>
          <Card.Content>
            <div className="space-y-4">
              {minutaStatus?.available ? (
                <>
                  <div className="flex items-center space-x-2 text-success-700">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">Sistema Operacional</span>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Provedor</span>
                      <span className="text-sm font-medium">{minutaStatus.provider}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Modelo</span>
                      <span className="text-sm font-mono">{minutaStatus.model}</span>
                    </div>
                  </div>

                  {/* Estatísticas de Uso (se disponíveis) */}
                  {minutaStatus.usage_stats && (
                    <div className="pt-3 border-t border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Estatísticas de Uso</h4>
                      <div className="space-y-2">
                        {Object.entries(minutaStatus.usage_stats).map(([key, value]) => (
                          <div key={key} className="flex justify-between items-center text-sm">
                            <span className="text-gray-600 capitalize">
                              {key.replace('_', ' ')}:
                            </span>
                            <span className="font-medium">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex items-center space-x-2 text-warning-700">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="font-medium">Indisponível</span>
                  </div>
                  
                  <div className="p-3 bg-warning-50 border border-warning-200 rounded">
                    <p className="text-sm text-warning-700">
                      {minutaStatus?.message || 'Funcionalidade não configurada'}
                    </p>
                    {minutaStatus?.config_help && (
                      <p className="text-xs text-warning-600 mt-2">
                        {minutaStatus.config_help}
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>
          </Card.Content>
        </Card>
      </div>

      {/* Funcionalidades Disponíveis */}
      <Card>
        <Card.Header>
          <h3 className="text-lg font-semibold text-gray-900">Funcionalidades do Sistema</h3>
        </Card.Header>
        <Card.Content>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {appInfo?.features && Object.entries(appInfo.features).map(([feature, available]) => (
              <div key={feature} className="flex items-center space-x-3 p-3 bg-gray-50 rounded">
                {available ? (
                  <CheckCircle className="w-5 h-5 text-success-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-danger-500" />
                )}
                <span className="text-sm font-medium text-gray-700 capitalize">
                  {feature.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        </Card.Content>
      </Card>

      {/* Ações de Atualização */}
      <Card>
        <Card.Footer>
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              <span>Última atualização: {new Date().toLocaleString('pt-BR')}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadDashboardData}
            >
              Atualizar Status
            </Button>
          </div>
        </Card.Footer>
      </Card>
    </div>
  );
};

export default Dashboard;