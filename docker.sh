#!/bin/bash

# Helper script for Docker commands
# Usage: ./docker.sh [command]

COMPOSE_FILE="build/docker-compose.yml"

case "$1" in
  up)
    echo "🚀 Starting containers..."
    docker-compose -f $COMPOSE_FILE up -d
    ;;
  down)
    echo "🛑 Stopping containers..."
    docker-compose -f $COMPOSE_FILE down
    ;;
  restart)
    echo "🔄 Restarting containers..."
    docker-compose -f $COMPOSE_FILE restart
    ;;
  logs)
    echo "📋 Showing logs..."
    docker-compose -f $COMPOSE_FILE logs -f
    ;;
  ps)
    echo "📊 Container status..."
    docker-compose -f $COMPOSE_FILE ps
    ;;
  build)
    echo "🔨 Building images..."
    docker-compose -f $COMPOSE_FILE build --no-cache
    ;;
  rebuild)
    echo "🔨 Rebuilding and restarting..."
    docker-compose -f $COMPOSE_FILE down
    docker-compose -f $COMPOSE_FILE build --no-cache
    docker-compose -f $COMPOSE_FILE up -d
    ;;
  clean)
    echo "🧹 Cleaning Docker resources..."
    docker system prune -f
    ;;
  shell)
    echo "🐚 Opening shell in web container..."
    docker-compose -f $COMPOSE_FILE exec web sh
    ;;
  *)
    echo "Docker Helper Script"
    echo ""
    echo "Usage: ./docker.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up        - Start containers"
    echo "  down      - Stop containers"
    echo "  restart   - Restart containers"
    echo "  logs      - Show logs (follow mode)"
    echo "  ps        - Show container status"
    echo "  build     - Build images"
    echo "  rebuild   - Rebuild and restart everything"
    echo "  clean     - Clean unused Docker resources"
    echo "  shell     - Open shell in web container"
    echo ""
    exit 1
    ;;
esac
