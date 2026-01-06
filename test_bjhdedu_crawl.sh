#!/bin/bash
# 北京海淀教育网站爬取测试脚本
# Beijing Haidian Education Website Crawl Test Script
# 
# 此脚本用于自动化测试整个爬取流程
# This script automates the entire crawl testing process

set -e  # Exit on error

# 颜色定义 / Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置 / Configuration
API_KEY="${API_KEY:-your-secure-api-key-change-this}"
API_URL="${API_URL:-http://localhost:8000}"
WAIT_TIME=5
MAX_WAIT_ITERATIONS=60  # 最多等待 5 分钟 / Max wait 5 minutes

# 函数定义 / Function definitions

print_header() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "需要 $1 命令 / $1 command is required"
        return 1
    fi
    print_success "$1 已安装 / $1 is installed"
    return 0
}

# 主测试流程 / Main test flow

print_header "第0步: 环境检查 / Step 0: Environment Check"

# 检查必需的命令
check_command "docker" || exit 1
check_command "curl" || exit 1

if command -v python3 &> /dev/null; then
    print_success "python3 已安装 / python3 is installed"
    HAS_PYTHON=true
else
    print_warning "python3 未安装，JSON 输出将不会被格式化 / python3 not installed, JSON output won't be formatted"
    HAS_PYTHON=false
fi

# 检查 Docker Compose
if docker compose version &> /dev/null; then
    print_success "Docker Compose (v2) 已安装"
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    print_success "Docker Compose (v1) 已安装"
    DOCKER_COMPOSE="docker-compose"
else
    print_error "Docker Compose 未安装 / Docker Compose is not installed"
    exit 1
fi

print_header "第1步: 配置文件完整性检查 / Step 1: Configuration Integrity Check"

# 检查关键文件
FILES=(
    "docker-compose.yml"
    "requirements.txt"
    ".env.example"
    "examples/task_bjhdedu_list_crawl.yaml"
    "app/main.py"
    "app/services/crawler_service.py"
    "app/workers/crawl_worker.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "文件存在: $file"
    else
        print_error "文件缺失: $file"
        exit 1
    fi
done

# 验证 Docker Compose 配置
print_info "验证 Docker Compose 配置..."
if $DOCKER_COMPOSE config > /dev/null 2>&1; then
    print_success "Docker Compose 配置有效"
else
    print_error "Docker Compose 配置无效"
    exit 1
fi

# 验证 YAML 文件语法
print_info "验证 YAML 任务文件..."
if $HAS_PYTHON; then
    YAML_ERROR=0
    # Test the main task file
    if ! python3 -c "import yaml; yaml.safe_load(open('examples/task_bjhdedu_list_crawl.yaml'))" 2>/dev/null; then
        print_error "YAML 文件语法错误: examples/task_bjhdedu_list_crawl.yaml"
        # Show detailed error for debugging
        python3 -c "import yaml; yaml.safe_load(open('examples/task_bjhdedu_list_crawl.yaml'))" 2>&1 | head -5
        YAML_ERROR=1
    fi
    
    if [ $YAML_ERROR -eq 0 ]; then
        print_success "YAML 文件语法正确"
    else
        exit 1
    fi
else
    print_warning "跳过 YAML 验证（需要 python3）"
fi

print_header "第2步: 启动 Docker 服务 / Step 2: Start Docker Services"

print_info "检查现有容器状态..."
$DOCKER_COMPOSE ps

print_info "启动所有服务..."
$DOCKER_COMPOSE up -d

print_info "等待服务启动 (45秒)..."
sleep 45

print_info "检查容器状态..."
$DOCKER_COMPOSE ps

print_header "第3步: 服务健康检查 / Step 3: Service Health Check"

# PostgreSQL 健康检查
print_info "检查 PostgreSQL..."
for i in {1..10}; do
    if docker compose exec -T postgres pg_isready -U mercury4ai > /dev/null 2>&1; then
        print_success "PostgreSQL 正常"
        break
    elif [ $i -eq 10 ]; then
        print_error "PostgreSQL 连接失败"
        docker compose logs postgres
        exit 1
    else
        print_warning "等待 PostgreSQL... ($i/10)"
        sleep 3
    fi
done

# Redis 健康检查
print_info "检查 Redis..."
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis 正常"
else
    print_error "Redis 连接失败"
    docker compose logs redis
    exit 1
fi

# MinIO 健康检查
print_info "检查 MinIO..."
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    print_success "MinIO 正常"
else
    print_error "MinIO 连接失败"
    docker compose logs minio
    exit 1
fi

# API 健康检查
print_info "检查 API 服务..."
for i in {1..10}; do
    if curl -sf -H "X-API-Key: $API_KEY" "$API_URL/api/health" > /dev/null 2>&1; then
        print_success "API 服务正常"
        break
    elif [ $i -eq 10 ]; then
        print_error "API 服务连接失败"
        docker compose logs api
        exit 1
    else
        print_warning "等待 API 服务... ($i/10)"
        sleep 3
    fi
done

# 显示健康检查详情
print_info "获取健康检查详情..."
HEALTH_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/health")
if $HAS_PYTHON; then
    echo "$HEALTH_RESPONSE" | python3 -m json.tool
else
    echo "$HEALTH_RESPONSE"
fi

print_header "第4步: Worker 服务检查 / Step 4: Worker Service Check"

print_info "检查 Worker 容器状态..."
if $DOCKER_COMPOSE ps | grep -q "worker.*Up"; then
    print_success "Worker 服务正在运行"
else
    print_error "Worker 服务未运行"
    $DOCKER_COMPOSE ps
    exit 1
fi

print_info "检查 Redis 队列..."
QUEUE_LENGTH=$(docker compose exec -T redis redis-cli LLEN "rq:queue:crawl_tasks" 2>/dev/null || echo "0")
print_info "当前队列长度: $QUEUE_LENGTH"

print_header "第5步: 导入爬取任务 / Step 5: Import Crawl Task"

print_info "导入 bjhdedu 爬取任务..."
TASK_RESPONSE=$(curl -s -X POST "$API_URL/api/tasks/import?format=yaml" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: text/plain" \
  --data-binary @examples/task_bjhdedu_list_crawl.yaml)

if [ $? -ne 0 ]; then
    print_error "任务导入请求失败"
    exit 1
fi

# 提取任务 ID
if $HAS_PYTHON; then
    TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
else
    TASK_ID=$(echo "$TASK_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "$TASK_ID" ]; then
    print_error "无法获取任务 ID"
    echo "响应内容:"
    echo "$TASK_RESPONSE"
    exit 1
fi

print_success "任务已创建: $TASK_ID"

# 验证任务详情
print_info "获取任务详情..."
TASK_DETAIL=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/tasks/$TASK_ID")
if $HAS_PYTHON; then
    echo "$TASK_DETAIL" | python3 -m json.tool
else
    echo "$TASK_DETAIL"
fi

print_header "第6步: 执行爬取任务 / Step 6: Execute Crawl Task"

print_info "启动任务运行..."
RUN_RESPONSE=$(curl -s -X POST "$API_URL/api/tasks/$TASK_ID/run" \
  -H "X-API-Key: $API_KEY")

if [ $? -ne 0 ]; then
    print_error "任务启动请求失败"
    exit 1
fi

# 提取运行 ID
if $HAS_PYTHON; then
    RUN_ID=$(echo "$RUN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('run_id', ''))" 2>/dev/null)
else
    RUN_ID=$(echo "$RUN_RESPONSE" | grep -o '"run_id":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "$RUN_ID" ]; then
    print_error "无法获取运行 ID"
    echo "响应内容:"
    echo "$RUN_RESPONSE"
    exit 1
fi

print_success "任务已启动: $RUN_ID"

print_header "第7步: 监控任务进度 / Step 7: Monitor Task Progress"

print_info "等待任务完成..."
ITERATION=0
while [ $ITERATION -lt $MAX_WAIT_ITERATIONS ]; do
    RUN_STATUS_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/runs/$RUN_ID")
    
    if $HAS_PYTHON; then
        STATUS=$(echo "$RUN_STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)
    else
        STATUS=$(echo "$RUN_STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    fi
    
    print_info "当前状态: $STATUS (第 $((ITERATION+1)) 次检查)"
    
    if [ "$STATUS" = "completed" ]; then
        print_success "任务执行成功！"
        break
    elif [ "$STATUS" = "failed" ]; then
        print_error "任务执行失败！"
        echo "状态详情:"
        if $HAS_PYTHON; then
            echo "$RUN_STATUS_RESPONSE" | python3 -m json.tool
        else
            echo "$RUN_STATUS_RESPONSE"
        fi
        
        print_info "查看 Worker 日志:"
        docker compose logs --tail=50 worker
        exit 1
    fi
    
    sleep $WAIT_TIME
    ITERATION=$((ITERATION+1))
done

if [ $ITERATION -ge $MAX_WAIT_ITERATIONS ]; then
    print_error "任务超时（等待超过 $((MAX_WAIT_ITERATIONS * WAIT_TIME)) 秒）"
    print_info "当前状态: $STATUS"
    print_info "查看 Worker 日志:"
    docker compose logs --tail=50 worker
    exit 1
fi

print_header "第8步: 查看运行结果 / Step 8: View Run Results"

print_info "获取运行状态详情..."
RUN_DETAIL=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/runs/$RUN_ID")
if $HAS_PYTHON; then
    echo "$RUN_DETAIL" | python3 -m json.tool
else
    echo "$RUN_DETAIL"
fi

print_info "获取爬取结果..."
RUN_RESULT=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/runs/$RUN_ID/result")

if [ $? -eq 0 ]; then
    print_success "成功获取结果"
    
    # 保存结果到文件
    RESULT_FILE="/tmp/bjhdedu_crawl_result_$(date +%Y%m%d_%H%M%S).json"
    echo "$RUN_RESULT" > "$RESULT_FILE"
    print_info "结果已保存到: $RESULT_FILE"
    
    if $HAS_PYTHON; then
        echo "结果预览（前100行）:"
        echo "$RUN_RESULT" | python3 -m json.tool | head -100
        
        # 提取关键统计信息
        print_info "结果统计:"
        TOTAL_DOCS=$(echo "$RUN_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_documents', 0))" 2>/dev/null || echo "0")
        print_info "文档总数: $TOTAL_DOCS"
        
        TOTAL_IMAGES=$(echo "$RUN_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_images', 0))" 2>/dev/null || echo "0")
        print_info "图片总数: $TOTAL_IMAGES"
    else
        echo "结果预览（前50行）:"
        echo "$RUN_RESULT" | head -50
    fi
else
    print_error "获取结果失败"
fi

print_header "第9步: 获取日志和工件 / Step 9: Get Logs and Artifacts"

print_info "获取 MinIO 路径和下载链接..."
RUN_LOGS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/runs/$RUN_ID/logs")

if [ $? -eq 0 ]; then
    print_success "成功获取日志信息"
    if $HAS_PYTHON; then
        echo "$RUN_LOGS" | python3 -m json.tool
    else
        echo "$RUN_LOGS"
    fi
else
    print_error "获取日志失败"
fi

print_header "第10步: 验证数据完整性 / Step 10: Verify Data Integrity"

# 检查数据库记录
print_info "检查数据库记录..."
TASK_COUNT=$(docker compose exec -T postgres psql -U mercury4ai -d mercury4ai -t -c "SELECT COUNT(*) FROM crawl_task;" 2>/dev/null | tr -d ' ')
print_info "任务总数: $TASK_COUNT"

RUN_COUNT=$(docker compose exec -T postgres psql -U mercury4ai -d mercury4ai -t -c "SELECT COUNT(*) FROM crawl_task_run;" 2>/dev/null | tr -d ' ')
print_info "运行总数: $RUN_COUNT"

DOC_COUNT=$(docker compose exec -T postgres psql -U mercury4ai -d mercury4ai -t -c "SELECT COUNT(*) FROM document;" 2>/dev/null | tr -d ' ')
print_info "文档总数: $DOC_COUNT"

# 检查 MinIO 存储
print_info "检查 MinIO 存储..."
MINIO_OBJECTS=$(docker compose exec -T redis redis-cli --raw KEYS "mercury4ai*" 2>/dev/null | wc -l)
print_info "Redis 中的 MinIO 键数: $MINIO_OBJECTS"

print_header "第11步: 清理测试数据 / Step 11: Cleanup Test Data"

print_info "是否删除测试任务？(y/n)"
if [ "${AUTO_CLEANUP:-false}" = "true" ]; then
    CLEANUP="y"
    print_info "自动清理模式，删除测试任务..."
else
    read -t 10 -r CLEANUP || CLEANUP="n"
fi

if [ "$CLEANUP" = "y" ] || [ "$CLEANUP" = "Y" ]; then
    print_info "删除任务: $TASK_ID"
    DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/api/tasks/$TASK_ID" -H "X-API-Key: $API_KEY")
    if [ $? -eq 0 ]; then
        print_success "测试任务已删除"
    else
        print_warning "删除任务失败，请手动清理"
    fi
else
    print_info "保留测试任务，任务 ID: $TASK_ID"
    print_info "运行 ID: $RUN_ID"
    print_info "手动删除命令:"
    echo "  curl -X DELETE \"$API_URL/api/tasks/$TASK_ID\" -H \"X-API-Key: $API_KEY\""
fi

print_header "测试完成总结 / Test Summary"

print_success "所有测试步骤完成！"
echo ""
echo "测试信息 / Test Information:"
echo "  - 任务 ID / Task ID: $TASK_ID"
echo "  - 运行 ID / Run ID: $RUN_ID"
echo "  - 结果文件 / Result File: $RESULT_FILE"
echo "  - API URL: $API_URL"
echo ""
echo "访问方式 / Access Methods:"
echo "  - API 文档 / API Docs: $API_URL/docs"
echo "  - MinIO 控制台 / MinIO Console: http://localhost:9001"
echo "    用户名 / Username: minioadmin"
echo "    密码 / Password: minioadmin"
echo ""
echo "查看日志 / View Logs:"
echo "  docker compose logs -f worker"
echo "  docker compose logs -f api"
echo ""
print_success "测试成功完成！/ Test completed successfully!"
