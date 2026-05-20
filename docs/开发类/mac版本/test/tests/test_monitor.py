import time
from core.monitor import PerfMonitor, SLA

def test_perf_monitor_basic():
    # 初始化监控器
    monitor = PerfMonitor()
    
    # 测量耗时
    with monitor.measure("image_encode") as timer:
        time.sleep(0.01)
    
    # 断言指标
    assert len(monitor.metrics) == 1
    metric = monitor.metrics[0]
    assert metric["name"] == "image_encode"
    assert metric["elapsed"] > 0.0
    assert metric["threshold"] == SLA["image_encode"]
    assert metric["warning"] is False  # 0.01s < 80% of 2.0s

def test_perf_monitor_warning():
    # 初始化监控器
    monitor = PerfMonitor()
    
    # 模拟超过阈值的操作（80% of 0.5s = 0.4s）
    with monitor.measure("json_parse") as timer:
        time.sleep(0.41)
    
    # 断言告警
    metric = monitor.metrics[0]
    assert metric["warning"] is True