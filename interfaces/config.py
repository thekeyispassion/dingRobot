"""配置管理 — 从 config.yaml / 环境变量加载配置"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """应用配置"""
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    dingtalk_mode: str = "openclaw"  # "openclaw" | "standalone"

    @property
    def llm_configured(self) -> bool:
        """是否已配置 LLM——有 key 且不是占位符"""
        return bool(self.llm_api_key) and "your-" not in self.llm_api_key


def _find_project_root() -> str:
    """向上查找项目根目录（包含 skills/ 目录的目录）"""
    current = os.path.dirname(os.path.abspath(__file__))
    while current != "/":
        if os.path.isdir(os.path.join(current, "skills")):
            return current
        current = os.path.dirname(current)
    # 回退：interfaces/ 的上级目录
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_yaml(path: str) -> dict:
    """加载 YAML 文件（无依赖，仅支持简单嵌套）"""
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {}
    current_section = result
    section_stack = []

    for line in content.split("\n"):
        stripped = line.strip()
        # 跳过空行和注释
        if not stripped or stripped.startswith("#"):
            continue

        # 计算缩进
        indent = len(line) - len(line.lstrip(" "))

        # 处理 section 头
        if stripped.endswith(":") and not stripped.startswith("-"):
            section_name = stripped[:-1].strip()
            new_section = {}
            if indent == 0:
                result[section_name] = new_section
                current_section = new_section
                section_stack = [(indent, new_section)]
            else:
                while section_stack and section_stack[-1][0] >= indent:
                    section_stack.pop()
                parent = section_stack[-1][1] if section_stack else result
                parent[section_name] = new_section
                current_section = new_section
                section_stack.append((indent, new_section))
            continue

        # 处理键值对
        if ":" in stripped and not stripped.startswith("-"):
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            current_section[key] = value

    return result


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置

    优先级: config.yaml > 环境变量 > 默认值

    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml

    Returns:
        Config 对象
    """
    if config_path is None:
        root = _find_project_root()
        config_path = os.path.join(root, "config.yaml")

    config = Config()

    # 1. 尝试加载 config.yaml
    yaml_data = _load_yaml(config_path)
    if yaml_data:
        llm = yaml_data.get("llm", {})
        dingtalk = yaml_data.get("dingtalk", {})

        config.llm_api_key = llm.get("api_key", config.llm_api_key)
        config.llm_base_url = llm.get("base_url", config.llm_base_url)
        config.llm_model = llm.get("model", config.llm_model)
        config.dingtalk_mode = dingtalk.get("mode", config.dingtalk_mode)

    # 2. 环境变量覆盖
    config.llm_api_key = os.environ.get("DDTALK_LLM_KEY", config.llm_api_key)
    config.llm_base_url = os.environ.get("DDTALK_LLM_URL", config.llm_base_url)
    config.llm_model = os.environ.get("DDTALK_LLM_MODEL", config.llm_model)
    config.dingtalk_mode = os.environ.get("DDTALK_DINGTALK_MODE", config.dingtalk_mode)

    return config


def mask_key(key: str) -> str:
    """脱敏显示密钥"""
    if not key or len(key) <= 8:
        return "***"
    return key[:4] + "****" + key[-4:]


# 全局单例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
