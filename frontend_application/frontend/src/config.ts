// Frontend Configuration
// These values can be overridden by environment variables, build-time configuration, or backend API

export const config = {
  // Databricks Configuration
  DATABRICKS_HOST: process.env.REACT_APP_DATABRICKS_HOST || 'adb-984752964297111.11.azuredatabricks.net',
  
  // MLflow Configuration
  MLFLOW_EXPERIMENT_ID: process.env.REACT_APP_MLFLOW_EXPERIMENT_ID || '3668845090573368',
  
  // API Configuration
  API_BASE_URL: process.env.REACT_APP_API_BASE_URL || '/chat-api',
};

// Dynamic configuration that can be loaded from backend
export interface BackendConfig {
  databricks_host: string;
  mlflow_experiment_id: string;
  serving_endpoint_name: string;
}

// Helper function to build trace URLs
export const buildTraceUrl = (traceId: string, customConfig?: Partial<BackendConfig>): string => {
  const host = customConfig?.databricks_host || config.DATABRICKS_HOST;
  const experimentId = customConfig?.mlflow_experiment_id || config.MLFLOW_EXPERIMENT_ID;
  return `https://${host}/ml/experiments/${experimentId}/traces?selectedEvaluationId=${traceId}`;
};

// Function to fetch configuration from backend
export const fetchBackendConfig = async (): Promise<BackendConfig | null> => {
  try {
    const response = await fetch(`${config.API_BASE_URL}/config`);
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Failed to fetch backend configuration, using defaults:', error);
  }
  return null;
}; 