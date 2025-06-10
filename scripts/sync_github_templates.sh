#!/bin/bash

# RAG-chat GitHub模板同步脚本
# 此脚本将docs/github_templates中的模板文件同步到.github目录

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$PROJECT_ROOT/docs/github_templates"
TARGET_DIR="$PROJECT_ROOT/.github"

echo "同步GitHub模板..."
echo "源目录: $SOURCE_DIR"
echo "目标目录: $TARGET_DIR"

# 确保目标目录存在
mkdir -p "$TARGET_DIR"

# 同步ISSUE_TEMPLATE目录
if [ -d "$SOURCE_DIR/ISSUE_TEMPLATE" ]; then
  echo "同步ISSUE_TEMPLATE目录..."
  mkdir -p "$TARGET_DIR/ISSUE_TEMPLATE"
  cp -r "$SOURCE_DIR/ISSUE_TEMPLATE/"* "$TARGET_DIR/ISSUE_TEMPLATE/"
  echo "ISSUE_TEMPLATE目录同步完成"
fi

# 同步PULL_REQUEST_TEMPLATE目录(如果存在)
if [ -d "$SOURCE_DIR/PULL_REQUEST_TEMPLATE" ]; then
  echo "同步PULL_REQUEST_TEMPLATE目录..."
  mkdir -p "$TARGET_DIR/PULL_REQUEST_TEMPLATE"
  cp -r "$SOURCE_DIR/PULL_REQUEST_TEMPLATE/"* "$TARGET_DIR/PULL_REQUEST_TEMPLATE/"
  echo "PULL_REQUEST_TEMPLATE目录同步完成"
fi

# 同步根目录下的其他模板文件
for file in "$SOURCE_DIR"/*.md; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    echo "同步文件: $filename"
    cp "$file" "$TARGET_DIR/"
  fi
done

echo "GitHub模板同步完成" 