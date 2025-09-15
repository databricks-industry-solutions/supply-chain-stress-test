# Supply Chain Stress Testing Bot - Complete Setup Guide

This guide provides step-by-step instructions to set up and deploy the Supply Chain Stress Testing Bot with frontend UI integration.

## 📋 Prerequisites

- **Python 3.8+** installed on your system
- **Node.js 16+** and **npm** for frontend development
- **Git** for version control
- **Databricks workspace** with appropriate permissions
- **PostgreSQL database** access (Databricks SQL Warehouse)
- **Supply Chain agent Deployed using Agent Framework** For agent development see **[agent/README.md](./agent/README.md)**



## 🚀 Quick Start

### Step 1: Clone and Navigate to Project
```bash
git clone <repository-url>
cd supply-chain-stress-test-1
```

### Step 2: Complete Setup (Recommended)
```bash
make setup
```
This single command will:
- Install uv package manager
- Create Python virtual environment
- Install all backend dependencies
- Install frontend dependencies
- Create environment file template

## 🔧 Detailed Setup Instructions

### Step 1: Install UV Package Manager
If not already installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Environment Configuration

#### 2.1 Create Environment File
```bash
cp env.example .env
```

#### 2.2 Configure Databricks Credentials
Edit your `.env` file with the following required values:

```bash
# Databricks Configuration
DATABRICKS_HOST=your-workspace.cloud.databricks.com
LOCAL_API_TOKEN=your_personal_access_token_here

# Database Configuration (PostgreSQL via Databricks)
DB_USERNAME=your-username@company.com
DB_INSTANCE_NAME=your-sql-warehouse-instance
CLIENT_ID=your-oauth-client-id
CLIENT_SECRET=your-oauth-client-secret
SCHEMA_NAME=chatbot_schema

# MLflow Configuration
MLFLOW_EXPERIMENT_ID=your-experiment-id

# Supply Chain Bot Configuration
SERVING_ENDPOINT_NAME=your-endpoint-name

# Lakehouse App Configuration
LAKEHOUSE_APP_NAME=supply-chain-stress-testing
APP_FOLDER_IN_WORKSPACE=/Workspace/Users/your-email/supply-chain-stress-testing
```

#### 2.3 How to Get Databricks Credentials

**Personal Access Token:**
1. Go to your Databricks workspace
2. Click your user profile → User Settings
3. Navigate to Developer → Access tokens
4. Generate new token with appropriate scope

**OAuth Credentials (CLIENT_ID & CLIENT_SECRET):**
1. In Databricks workspace, go to Settings → Developer → App credentials
2. Create a new OAuth application
3. Note the Client ID and Client Secret
4. Configure redirect URIs if needed

**Database Instance Name:**
1. Go to SQL → SQL Warehouses in your Databricks workspace
2. Note your SQL Warehouse's Server hostname
3. Extract the instance name from the connection details

**MLflow Experiment ID:**
1. Navigate to MLflow in your Databricks workspace
2. Create or select an experiment
3. Copy the experiment ID from the URL or experiment details

### Step 3: Install Dependencies

#### 3.1 Backend Dependencies
```bash
make install-backend
```

#### 3.2 Frontend Dependencies
```bash
make install-frontend
```

#### 3.3 Install All Dependencies
```bash
make install
```

### Step 4: Database Setup

#### 4.1 Verify Environment Configuration
```bash
make check-env
```

#### 4.2 Setup Database Schema
```bash
make db-schema-setup
```

This script will:
- Create the schema specified by `SCHEMA_NAME` environment variable (defaults to `chatbot_schema`) in your PostgreSQL database
- Set up proper roles and permissions
- Configure the `chatbot_app` role for the application
- Grant necessary permissions to your CLIENT_ID

**Expected Output:**
```
🚀 Database Schema Setup
==================================================
📋 Using schema: your_schema_name (from SCHEMA_NAME env variable)
✅ Environment variables configured
🔧 Setting up your_schema_name...
📋 Creating schema...
✅ Schema created
🔑 Granting permissions to your-client-id...
✅ Permissions granted to your-client-id
👤 Setting up chatbot_app role...
✅ chatbot_app role configured
✅ Schema setup completed successfully!
```

**Note:** The schema name will be whatever you set in the `SCHEMA_NAME` environment variable. If not specified, it defaults to `chatbot_schema`.

## 🎨 Frontend Setup

### Step 1: Build Frontend for Development
```bash
make build-frontend
```

This command:
- Installs all React dependencies
- Builds the production-ready frontend
- Outputs build files to `frontend/build-chat-app/`

### Step 2: Frontend Configuration
The frontend configuration is located in `frontend/src/config.ts`. Key configurations:

- **API_BASE_URL**: Backend API endpoint (defaults to `/chat-api`)
- **DATABRICKS_HOST**: Your Databricks workspace host
- **MLFLOW_EXPERIMENT_ID**: MLflow experiment for tracking

## 🚀 Running the Application

### Development Mode
```bash
make dev
```

This starts:
- Backend server on `http://localhost:8000`
- Hot-reload enabled for development
- Real-time code changes reflection

### Production Mode
```bash
make run
```

This starts:
- Production server with Gunicorn
- Multiple workers for better performance
- Optimized for production deployment

### Check Application Status
```bash
make check-env
```

## 🔧 Advanced Configuration

### Database Configuration Options

#### PostgreSQL (Recommended)
```bash
# In .env file
DB_USERNAME=your-username@company.com
DB_INSTANCE_NAME=your-databricks-sql-warehouse
CLIENT_ID=your-oauth-client-id
CLIENT_SECRET=your-oauth-client-secret
SCHEMA_NAME=chatbot_schema
```

#### SQLite (Development Only)
```bash
# In .env file - uncomment for local development
SQLITE_DB_PATH=chat_history.db
```


## 🚀 Deployment

### Step 1: Prepare for Deployment
Ensure all configurations are set in your `.env` file, especially:
```bash
LAKEHOUSE_APP_NAME=supply-chain-stress-testing
APP_FOLDER_IN_WORKSPACE=/Workspace/Users/your-email/supply-chain-stress-testing
```

### Step 2: Deploy to Databricks
```bash
make deploy
```

This deployment script:
1. **Frontend Build**: Compiles React application for production
2. **Backend Packaging**: Freezes Python dependencies
3. **File Sync**: Uploads application to Databricks workspace
4. **App Deployment**: Deploys as Databricks Lakehouse App

### Step 3: Monitor Deployment
After deployment, the application will be available at:
```
https://your-workspace.cloud.databricks.com/apps/your-app-name
```

## 🛠️ Troubleshooting

### Common Issues

#### Environment Variables Not Found
```bash
❌ Missing required environment variables: CLIENT_ID, CLIENT_SECRET
```
**Solution**: Ensure all required variables are set in your `.env` file

#### Database Connection Failed
```bash
❌ Error creating database connection
```
**Solutions**:
1. Verify `DB_INSTANCE_NAME` is correct
2. Check `CLIENT_ID` and `CLIENT_SECRET` are valid
3. Ensure your user has database permissions

#### Frontend Build Failed
```bash
❌ Frontend build failed
```
**Solutions**:
1. Run `cd frontend && npm install` to reinstall dependencies
2. Check Node.js version (requires 16+)
3. Clear npm cache: `npm cache clean --force`

#### Permission Denied Errors
```bash
❌ Error granting permissions
```
**Solution**: Ensure your Databricks user has admin permissions or database ownership

### Useful Debug Commands

#### Check Environment
```bash
make check-env
```

#### View Dependencies
```bash
make check-deps
```

#### Clean and Restart
```bash
make clean
make setup
```

#### Stop All Services
```bash
make stop
```

## 📝 Additional Commands

### Code Quality
```bash
# Format code
make format

# Run linting
make lint
```

### Database Management
```bash
# Setup database configuration guide
make db-setup

# Setup schema with permissions
make db-schema-setup
```

### Cleanup
```bash
# Remove all generated files and dependencies
make clean
```

## 🎉 Success!

Once setup is complete, you should have:
- ✅ Databricks workspace connected
- ✅ Database schema configured
- ✅ Frontend built and ready
- ✅ Backend server running
- ✅ Full UI integration working

Visit `http://localhost:8000` to access your Supply Chain Stress Testing Bot!

## 📚 Next Steps

1. **Explore Notebooks**: Check out the Jupyter notebooks in the project root for supply chain analysis
2. **Agent Development**: Review files in the `agent/` directory for AI agent configuration
3. **Custom Configuration**: Modify settings in `utils/config.py` for advanced customization
4. **Production Deployment**: Use `make deploy` when ready to deploy to Databricks

## 🤖 Creating the Supply Chain Agent Bot

This project includes an intelligent agent system that bridges the gap between business requirements and mathematical optimization tools. To create and deploy the agent bot:

### Agent Overview
The supply chain agent leverages large language models to democratize supply chain technologies by:
- Interpreting business requirements in natural language
- Accessing supply chain data and optimization tools
- Providing transparent, explainable recommendations
- Reducing the need for specialized mathematical modeling expertise

### Quick Start for Agent Development
1. **Navigate to Agent Directory**:
   ```bash
   cd agent/
   ```

2. **Review Agent Documentation**: 
   See **[agent/README.md](./agent/README.md)** for detailed information about:
   - Business problem and use cases
   - Agent architecture and design
   - Integration with mathematical optimization tools
   - Benefits of LLM-powered supply chain management

3. **Explore Agent Notebooks**:
   - `01_build_agent.ipynb` - Build and configure the agent
   - `02_evaluate_agent.ipynb` - Test and evaluate agent performance  
   - `03_deploy_agent.ipynb` - Deploy the agent to production

4. **Agent Configuration**:
   The agent uses the same environment variables configured in your `.env` file:
   - `SERVING_ENDPOINT_NAME` - Your model serving endpoint
   - `MLFLOW_EXPERIMENT_ID` - For tracking agent experiments
   - `DATABRICKS_HOST` - Your workspace connection

### Agent Architecture
The agent system provides a conversational interface that can:
- Understand supply chain business questions
- Execute mathematical optimization models
- Interpret results in business-friendly language
- Provide actionable recommendations

For complete details on the agent's capabilities and implementation, refer to the **[agent/README.md](./agent/README.md)** guide.

## 🆘 Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all environment variables are correctly set
3. Ensure Databricks permissions are properly configured
4. Review the application logs for detailed error messages

For additional support, refer to the project documentation or contact your Databricks administrator.
