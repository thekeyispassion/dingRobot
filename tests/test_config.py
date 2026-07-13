"""配置管理 — 单元测试"""
import pytest
import os
import tempfile
from interfaces.config import load_config, mask_key, Config


class TestMaskKey:
    def test_normal_key(self):
        assert mask_key("sk-1234567890abcdef") == "sk-1****cdef"

    def test_short_key(self):
        assert mask_key("short") == "***"

    def test_empty_key(self):
        assert mask_key("") == "***"


class TestLoadConfigDefaults:
    def test_no_config_file_returns_defaults(self):
        """无配置文件时返回默认值"""
        config = load_config("/nonexistent/path/config.yaml")
        assert isinstance(config, Config)
        assert config.llm_model == "qwen-plus"
        assert config.dingtalk_mode == "openclaw"
        assert config.llm_configured is False

    def test_placeholder_key_not_configured(self):
        """占位符 key 视为未配置"""
        config = Config()
        config.llm_api_key = "your-api-key-here"
        assert config.llm_configured is False

    def test_real_key_is_configured(self):
        """真实 key 视为已配置"""
        config = Config()
        config.llm_api_key = "sk-real-key-123456"
        assert config.llm_configured is True


class TestLoadConfigFromFile:
    def test_load_valid_yaml(self):
        """从 YAML 文件加载配置"""
        yaml_content = """llm:
  api_key: "sk-test-key-123"
  base_url: "https://test.api.com/v1"
  model: "test-model"
dingtalk:
  mode: "standalone"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            config = load_config(tmp_path)
            assert config.llm_api_key == "sk-test-key-123"
            assert config.llm_base_url == "https://test.api.com/v1"
            assert config.llm_model == "test-model"
            assert config.dingtalk_mode == "standalone"
            assert config.llm_configured is True
        finally:
            os.unlink(tmp_path)

    def test_partial_yaml_keeps_defaults(self):
        """部分配置保持默认值"""
        yaml_content = """llm:
  api_key: "sk-minimal"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            config = load_config(tmp_path)
            assert config.llm_api_key == "sk-minimal"
            assert config.llm_model == "qwen-plus"  # default
            assert config.dingtalk_mode == "openclaw"  # default
        finally:
            os.unlink(tmp_path)


class TestEnvVarOverride:
    def test_env_var_overrides(self):
        """环境变量覆盖配置"""
        os.environ["DDTALK_LLM_KEY"] = "sk-env-key"
        os.environ["DDTALK_LLM_MODEL"] = "env-model"

        try:
            config = load_config("/nonexistent/path/config.yaml")
            # env vars are applied on top of defaults when no config.yaml
            assert config.llm_api_key == "sk-env-key"
            assert config.llm_model == "env-model"
        finally:
            del os.environ["DDTALK_LLM_KEY"]
            del os.environ["DDTALK_LLM_MODEL"]
