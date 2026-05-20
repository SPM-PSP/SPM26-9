import os
import tempfile
from core.logger import Logger, init, get, debug, info, warning, error

def test_logger_basic():
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化日志
        logger = Logger(tmpdir, level="DEBUG")
        log_path = logger.get_log_path()
        
        # 写入日志
        logger.debug("TestModule", "Debug message")
        logger.info("TestModule", "Info message")
        logger.warning("TestModule", "Warning message")
        logger.error("TestModule", "Error message")
        
        # 验证文件存在且内容正确
        assert os.path.exists(log_path)
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "[DEBUG] [TestModule] Debug message" in content
            assert "[ERROR] [TestModule] Error message" in content
        
        # 验证最近条目
        recent = logger.get_recent_entries(count=2)
        assert "Warning message" in recent or "Error message" in recent

def test_logger_module_level():
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化模块级日志
        init(tmpdir, level="INFO")
        logger = get()
        
        # 调用模块级函数
        debug("Test", "Should not appear (INFO level)")
        info("Test", "Info message")
        error("Test", "Error message")
        
        # 验证内容
        with open(logger.get_log_path(), "r", encoding="utf-8") as f:
            content = f.read()
            assert "Should not appear" not in content
            assert "[INFO] [Test] Info message" in content