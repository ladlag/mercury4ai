#!/bin/bash
# 代码和配置完整性检查脚本
# Code and Configuration Integrity Check Script
#
# 此脚本用于检查 Mercury4AI 代码和配置的完整性
# This script checks the integrity of Mercury4AI code and configuration

set -e

# 颜色定义 / Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
PASSED=0
FAILED=0
WARNINGS=0

print_header() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    PASSED=$((PASSED+1))
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    FAILED=$((FAILED+1))
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    WARNINGS=$((WARNINGS+1))
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header "Mercury4AI 代码和配置完整性检查"
print_info "Code and Configuration Integrity Check"

print_header "1. 目录结构检查 / Directory Structure Check"

REQUIRED_DIRS=(
    "app"
    "app/api"
    "app/core"
    "app/models"
    "app/services"
    "app/workers"
    "app/schemas"
    "examples"
    "alembic"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        print_success "目录存在: $dir"
    else
        print_error "目录缺失: $dir"
    fi
done

print_header "2. 核心文件检查 / Core Files Check"

CORE_FILES=(
    "docker-compose.yml"
    "Dockerfile"
    "requirements.txt"
    ".env.example"
    ".gitignore"
    "README.md"
    "QUICKSTART.md"
    "validate.sh"
    "app/main.py"
    "app/__init__.py"
    "app/api/__init__.py"
    "app/api/health.py"
    "app/api/tasks.py"
    "app/api/runs.py"
    "app/api/import_export.py"
    "app/core/__init__.py"
    "app/core/config.py"
    "app/core/database.py"
    "app/core/auth.py"
    "app/core/minio_client.py"
    "app/core/redis_client.py"
    "app/services/__init__.py"
    "app/services/crawler_service.py"
    "app/services/task_service.py"
    "app/workers/__init__.py"
    "app/workers/crawl_worker.py"
    "app/models/__init__.py"
    "app/schemas/__init__.py"
    "alembic/README.md"
    "alembic.ini"
    "init-db.sql"
)

for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "文件存在: $file"
    else
        print_error "文件缺失: $file"
    fi
done

print_header "3. 示例文件检查 / Example Files Check"

EXAMPLE_FILES=(
    "examples/README.md"
    "examples/task_simple_scraping.yaml"
    "examples/task_news_extraction.json"
    "examples/task_product_extraction.yaml"
    "examples/task_bjhdedu_list.yaml"
    "examples/task_bjhdedu_list_crawl.yaml"
    "examples/task_chinese_llm_deepseek.json"
    "examples/task_chinese_llm_qwen.yaml"
)

for file in "${EXAMPLE_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "示例文件存在: $file"
    else
        print_warning "示例文件缺失: $file"
    fi
done

print_header "4. Python 依赖检查 / Python Dependencies Check"

print_info "检查 requirements.txt 内容..."

REQUIRED_PACKAGES=(
    "fastapi"
    "uvicorn"
    "pydantic"
    "sqlalchemy"
    "psycopg2-binary"
    "alembic"
    "rq"
    "redis"
    "minio"
    "crawl4ai"
    "httpx"
    "pyyaml"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if grep -q "$package" requirements.txt; then
        VERSION=$(grep "$package" requirements.txt)
        print_success "依赖存在: $VERSION"
    else
        print_error "依赖缺失: $package"
    fi
done

print_header "5. Docker 配置检查 / Docker Configuration Check"

print_info "验证 Dockerfile..."
if [ -f "Dockerfile" ]; then
    if grep -q "FROM python" Dockerfile; then
        print_success "Dockerfile 基础镜像正确"
    else
        print_error "Dockerfile 基础镜像配置错误"
    fi
    
    if grep -q "COPY requirements.txt" Dockerfile; then
        print_success "Dockerfile requirements.txt 复制配置存在"
    else
        print_error "Dockerfile requirements.txt 复制配置缺失"
    fi
    
    if grep -q "RUN pip install" Dockerfile; then
        print_success "Dockerfile pip install 配置存在"
    else
        print_error "Dockerfile pip install 配置缺失"
    fi
fi

print_info "验证 docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    # 检查服务定义
    SERVICES=("postgres" "redis" "minio" "api" "worker")
    for service in "${SERVICES[@]}"; do
        if grep -q "$service:" docker-compose.yml; then
            print_success "服务定义存在: $service"
        else
            print_error "服务定义缺失: $service"
        fi
    done
    
    # 检查端口映射
    if grep -q "8000:8000" docker-compose.yml; then
        print_success "API 端口映射配置正确"
    else
        print_error "API 端口映射配置缺失"
    fi
    
    # 检查健康检查
    if grep -q "healthcheck:" docker-compose.yml; then
        print_success "健康检查配置存在"
    else
        print_warning "健康检查配置缺失"
    fi
    
    # 检查卷配置
    if grep -q "volumes:" docker-compose.yml; then
        print_success "卷配置存在"
    else
        print_warning "卷配置缺失"
    fi
fi

print_header "6. 环境变量配置检查 / Environment Variables Check"

if [ -f ".env.example" ]; then
    print_success ".env.example 文件存在"
    
    # 检查关键环境变量
    ENV_VARS=(
        "API_KEY"
        "POSTGRES_HOST"
        "POSTGRES_PORT"
        "POSTGRES_DB"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "REDIS_HOST"
        "REDIS_PORT"
        "MINIO_ENDPOINT"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
        "MINIO_BUCKET"
        "DEFAULT_LLM_PROVIDER"
        "DEFAULT_LLM_MODEL"
    )
    
    for var in "${ENV_VARS[@]}"; do
        if grep -q "^$var=" .env.example || grep -q "^# $var=" .env.example; then
            print_success "环境变量定义存在: $var"
        else
            print_warning "环境变量定义缺失: $var"
        fi
    done
else
    print_error ".env.example 文件缺失"
fi

if [ -f ".env" ]; then
    print_info ".env 文件存在（已配置）"
else
    print_warning ".env 文件不存在（将使用默认配置）"
fi

print_header "7. Python 代码语法检查 / Python Syntax Check"

if command -v python3 &> /dev/null; then
    print_info "使用 python3 检查语法..."
    
    PYTHON_FILES=(
        "app/main.py"
        "app/core/config.py"
        "app/core/database.py"
        "app/services/crawler_service.py"
        "app/workers/crawl_worker.py"
    )
    
    for file in "${PYTHON_FILES[@]}"; do
        if [ -f "$file" ]; then
            if python3 -m py_compile "$file" 2>/dev/null; then
                print_success "语法正确: $file"
            else
                print_error "语法错误: $file"
            fi
        fi
    done
else
    print_warning "python3 未安装，跳过语法检查"
fi

print_header "8. YAML 文件语法检查 / YAML Syntax Check"

if command -v python3 &> /dev/null; then
    print_info "检查 YAML 文件语法..."
    
    YAML_FILES=(
        "examples/task_bjhdedu_list_crawl.yaml"
        "examples/task_simple_scraping.yaml"
        "examples/task_product_extraction.yaml"
        "examples/task_chinese_llm_qwen.yaml"
    )
    
    for file in "${YAML_FILES[@]}"; do
        if [ -f "$file" ]; then
            if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
                print_success "YAML 语法正确: $file"
            else
                print_error "YAML 语法错误: $file"
            fi
        fi
    done
else
    print_warning "python3 未安装，跳过 YAML 语法检查"
fi

print_header "9. JSON 文件语法检查 / JSON Syntax Check"

if command -v python3 &> /dev/null; then
    print_info "检查 JSON 文件语法..."
    
    JSON_FILES=(
        "examples/task_news_extraction.json"
        "examples/task_chinese_llm_deepseek.json"
        "examples/task_chinese_news_deepseek.json"
    )
    
    for file in "${JSON_FILES[@]}"; do
        if [ -f "$file" ]; then
            if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
                print_success "JSON 语法正确: $file"
            else
                print_error "JSON 语法错误: $file"
            fi
        fi
    done
else
    print_warning "python3 未安装，跳过 JSON 语法检查"
fi

print_header "10. Docker Compose 配置验证 / Docker Compose Validation"

if command -v docker &> /dev/null; then
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        DOCKER_COMPOSE=""
    fi
    
    if [ -n "$DOCKER_COMPOSE" ]; then
        print_info "验证 Docker Compose 配置..."
        if $DOCKER_COMPOSE config > /dev/null 2>&1; then
            print_success "Docker Compose 配置有效"
        else
            print_error "Docker Compose 配置无效"
            $DOCKER_COMPOSE config 2>&1 | head -20
        fi
    else
        print_warning "Docker Compose 未安装"
    fi
else
    print_warning "Docker 未安装"
fi

print_header "11. API 端点定义检查 / API Endpoints Check"

print_info "检查 API 路由定义..."

API_ENDPOINTS=(
    "health.router"
    "tasks.router"
    "import_export.router"
    "runs.router"
)

if [ -f "app/main.py" ]; then
    for endpoint in "${API_ENDPOINTS[@]}"; do
        if grep -q "$endpoint" app/main.py; then
            print_success "API 路由已包含: $endpoint"
        else
            print_error "API 路由缺失: $endpoint"
        fi
    done
fi

print_header "12. 数据库模型检查 / Database Models Check"

print_info "检查数据库模型定义..."

if [ -d "app/models" ]; then
    MODEL_FILES=$(find app/models -name "*.py" -type f | wc -l)
    if [ $MODEL_FILES -gt 0 ]; then
        print_success "找到 $MODEL_FILES 个模型文件"
    else
        print_warning "未找到模型文件"
    fi
fi

print_header "13. 测试脚本检查 / Test Scripts Check"

TEST_SCRIPTS=(
    "validate.sh"
    "test_bjhdedu_crawl.sh"
)

for script in "${TEST_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            print_success "测试脚本存在且可执行: $script"
        else
            print_warning "测试脚本存在但不可执行: $script (运行: chmod +x $script)"
        fi
    else
        print_warning "测试脚本缺失: $script"
    fi
done

print_header "14. 文档完整性检查 / Documentation Check"

DOC_FILES=(
    "README.md"
    "QUICKSTART.md"
    "DEPLOYMENT.md"
    "CHINESE_LLM_GUIDE.md"
    "BJHDEDU_CRAWL_GUIDE.md"
)

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        LINES=$(wc -l < "$doc")
        if [ $LINES -gt 10 ]; then
            print_success "文档存在且有内容: $doc ($LINES 行)"
        else
            print_warning "文档存在但内容较少: $doc ($LINES 行)"
        fi
    else
        print_warning "文档缺失: $doc"
    fi
done

print_header "15. Git 配置检查 / Git Configuration Check"

if [ -f ".gitignore" ]; then
    print_success ".gitignore 文件存在"
    
    # 检查关键忽略项
    IGNORE_PATTERNS=(
        ".env"
        "__pycache__"
        "*.pyc"
        ".venv"
        "venv"
    )
    
    for pattern in "${IGNORE_PATTERNS[@]}"; do
        if grep -q "$pattern" .gitignore; then
            print_success "忽略模式存在: $pattern"
        else
            print_warning "忽略模式缺失: $pattern"
        fi
    done
else
    print_error ".gitignore 文件缺失"
fi

print_header "16. 安全配置检查 / Security Configuration Check"

print_info "检查安全相关配置..."

# 检查是否使用默认密码
if [ -f ".env" ]; then
    if grep -q "your-secure-api-key-change-this" .env; then
        print_warning "检测到默认 API Key，建议修改"
    else
        print_success "API Key 已自定义"
    fi
    
    if grep -q "minioadmin" .env; then
        print_warning "检测到默认 MinIO 凭据，建议修改"
    else
        print_success "MinIO 凭据已自定义"
    fi
fi

# 检查 .env 是否被忽略
if [ -f ".gitignore" ]; then
    if grep -q "^\.env$" .gitignore; then
        print_success ".env 文件已在 .gitignore 中"
    else
        print_error ".env 文件未在 .gitignore 中（安全风险）"
    fi
fi

print_header "检查结果汇总 / Check Summary"

echo ""
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${YELLOW}警告: $WARNINGS${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        print_success "所有检查通过！系统配置完整且正确。"
        print_success "All checks passed! System configuration is complete and correct."
        exit 0
    else
        print_warning "检查通过，但有 $WARNINGS 个警告需要注意。"
        print_warning "Checks passed, but $WARNINGS warnings need attention."
        exit 0
    fi
else
    print_error "发现 $FAILED 个错误，请修复后再继续。"
    print_error "Found $FAILED errors, please fix before proceeding."
    exit 1
fi
